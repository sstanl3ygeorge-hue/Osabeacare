from datetime import datetime, timezone, timedelta

from reportlab.platypus import Table

from services.training_evaluator import (
    _resolve_effective_expiry_date,
    compute_training_record_status,
    calculate_training_expiry,
    derive_training_evidence_metadata,
)
from induction_definitions import (
    CARE_CERTIFICATE_STANDARDS,
    INDUCTION_RULE_METADATA,
    TRAINING_TO_INDUCTION_MAP,
    get_induction_item_for_training,
)
from care_certificate_config import get_config_for_item
from care_certificate_forms import get_worker_form_schema
from services.pdf_service import generate_admin_form_pdf, generate_induction_pdf_content
from services.pdf_service import create_pdf_styles
from services.pdf_service import generate_evidence_record_pdf


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


def test_derive_external_certificate_metadata_is_explicit_and_preserves_source_document():
    metadata = derive_training_evidence_metadata({
        "completion_method": "certificate",
        "certificate_url": "https://example.com/cert.pdf",
        "source_document_id": "doc-123",
    })
    assert metadata == {
        "source_type": "certificate",
        "evidence_type": "external_certificate",
        "source_document_id": "doc-123",
    }


def test_derive_internal_manual_metadata_defaults_to_internal_course():
    metadata = derive_training_evidence_metadata({
        "completion_method": "manual",
    })
    assert metadata == {
        "source_type": "internal_course",
        "evidence_type": "temporary_internal",
    }


def test_questionnaire_source_type_is_treated_as_temporary_internal():
    completion = datetime.now(timezone.utc) - timedelta(days=120)
    record = {
        "completion_date": completion.strftime("%Y-%m-%d"),
        "expiry_date": None,
        "source_type": "questionnaire",
        "evidence_type": "temporary_internal",
        "completion_method": "manual",
        "requirement_id": "health_safety",
        "verified": True,
    }
    computed = compute_training_record_status(record)
    assert computed["computed_status"] == "expired"


def test_equality_and_diversity_uses_hybrid_form_and_not_training_sync():
    standard = _std_by_id("equality_diversity")
    assert standard is not None
    assert standard.get("training_sync") is None
    assert INDUCTION_RULE_METADATA["equality_diversity"]["completion_type"] == "hybrid"
    assert TRAINING_TO_INDUCTION_MAP.get("equality_diversity") is None
    cfg = get_config_for_item("equality_diversity")
    assert cfg is not None
    assert cfg.get("completion_type") == "hybrid"
    assert cfg.get("worker_form_id") == "cc_equality_diversity"
    form_schema = get_worker_form_schema("cc_equality_diversity")
    assert form_schema.get("standard_code") == "equality_diversity"
    assert len(form_schema.get("fields", [])) >= 3


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


def test_evidence_record_pdf_renders_internal_temporary_notice():
    pdf_bytes = generate_evidence_record_pdf(
        "Training Evidence Record",
        {"first_name": "Test", "last_name": "User", "employee_code": "E001"},
        {
            "item_name": "Health and Safety",
            "evidence_type": "Temporary internal evidence",
            "source_label": "Internal course completion",
            "completed_at": "2026-01-10",
            "reviewed_label": "Verified by",
            "reviewed_by": "Manager A",
            "reviewed_at": "2026-01-11",
            "expiry_date": "2026-04-10",
            "record_reference": "rec-123",
            "notes": [
                "Temporary internal evidence valid for 90 days. External certificate required before expiry.",
            ],
        },
    )

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")
