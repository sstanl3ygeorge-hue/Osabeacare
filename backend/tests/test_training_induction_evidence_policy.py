from datetime import datetime, timezone, timedelta

from reportlab.platypus import Table

from services.training_evaluator import (
    _resolve_effective_expiry_date,
    compute_training_record_status,
    calculate_training_expiry,
)
from induction_definitions import (
    CARE_CERTIFICATE_STANDARDS,
    INDUCTION_RULE_METADATA,
    TRAINING_TO_INDUCTION_MAP,
    get_induction_item_for_training,
)
from services.pdf_service import generate_admin_form_pdf, generate_induction_pdf_content
from services.pdf_service import create_pdf_styles


def _std_by_id(std_id: str):
    return next((s for s in CARE_CERTIFICATE_STANDARDS if s.get("id") == std_id), None)


def test_external_certificate_with_explicit_expiry_uses_explicit_expiry():
    record = {
        "completion_date": "2026-01-15",
        "expiry_date": "2028-03-31",
        "completion_method": "certificate",
        "certificate_url": "https://example.com/cert.pdf",
        "requirement_id": "manual_handling",
    }
    assert _resolve_effective_expiry_date(record) == "2028-03-31"


def test_external_certificate_without_expiry_uses_normal_validity_policy():
    record = {
        "completion_date": "2026-01-01",
        "expiry_date": None,
        "completion_method": "certificate",
        "certificate_url": "https://example.com/cert.pdf",
        "requirement_id": "manual_handling",
    }
    expected = calculate_training_expiry("2026-01-01", "manual_handling")
    assert _resolve_effective_expiry_date(record) == expected


def test_internal_questionnaire_evidence_gets_90_day_expiry():
    completion = "2026-01-01"
    expected = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%d")
    record = {
        "completion_date": completion,
        "expiry_date": None,
        "source_type": "form_submission",
        "completion_method": "manual",
        "requirement_id": "health_safety",
    }
    assert _resolve_effective_expiry_date(record) == expected


def test_internal_temporary_evidence_becomes_expired_after_90_days():
    completion_dt = datetime.now(timezone.utc) - timedelta(days=120)
    record = {
        "completion_date": completion_dt.strftime("%Y-%m-%d"),
        "expiry_date": None,
        "source_type": "form_submission",
        "completion_method": "manual",
        "requirement_id": "health_safety",
        "verified": True,
    }
    computed = compute_training_record_status(record)
    assert computed["computed_status"] == "expired"


def test_equality_and_diversity_is_manual_only_and_not_auto_completed_from_training():
    standard = _std_by_id("equality_diversity")
    assert standard is not None
    assert standard.get("training_sync") is None
    assert INDUCTION_RULE_METADATA["equality_diversity"]["completion_type"] == "manual"
    assert TRAINING_TO_INDUCTION_MAP.get("equality_diversity") is None


def test_safeguarding_and_bls_still_auto_map_to_induction():
    assert get_induction_item_for_training("safeguarding") == "safeguarding_adults"
    assert get_induction_item_for_training("bls") == "basic_life_support"


def test_induction_pdf_includes_signed_off_by_column_and_renders():
    form_data = {
        "start_date": "2026-01-01",
        "completion_date": "2026-01-10",
        "inductor_name": "Admin User",
        "checklist_items": [
            {
                "name": "Safeguarding Adults",
                "completed": True,
                "completed_date": "2026-01-10",
                "completed_by": "Manager A",
            }
        ],
        "notes": "All good",
    }

    styles = create_pdf_styles()
    elements = generate_induction_pdf_content(form_data, styles)
    tables = [el for el in elements if isinstance(el, Table)]
    assert any(getattr(t, "_ncols", 0) == 4 for t in tables)

    pdf_bytes = generate_admin_form_pdf(
        "induction_checklist",
        form_data,
        {"first_name": "Test", "last_name": "User", "employee_code": "E001"},
        {"name": "Admin User"},
    )
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 0
