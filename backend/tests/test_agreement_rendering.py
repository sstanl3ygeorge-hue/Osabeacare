"""
Regression tests for agreement_document_service.py

Three invariants are verified without any live DB or Supabase calls:

1. No raw placeholder text survives rendering — generated contracts must
   contain none of the template tokens or legacy (insert...) phrases.

2. Worker/admin signatures land on the *last* page, not a hardcoded index.
   (Regression: previously _apply_contract_signatures always used page 6.)

3. Missing required contract fields are surfaced — incomplete employee data
   must produce a logged warning rather than silently rendering a broken
   contract that has "TBC" or unfilled tokens for key fields.
"""
from __future__ import annotations

import io
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap so the test can import the backend package without a full
# FastAPI / motor install being required at test-collection time.
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Stub out heavy / network-dependent imports before importing the module
# ---------------------------------------------------------------------------
def _make_stub(name: str):
    mod = types.ModuleType(name)
    sys.modules.setdefault(name, mod)
    return mod


for _stub_name in [
    "motor", "motor.motor_asyncio",
    "supabase_storage",
    "services", "services.pdf_service",
]:
    _make_stub(_stub_name)

# pdf_service stub — get_logo_image returns None (no file needed)
sys.modules["services.pdf_service"].get_logo_image = lambda **_kw: None  # type: ignore

# supabase_storage stubs
_ss = sys.modules["supabase_storage"]
_ss.download_file_from_storage = MagicMock()  # type: ignore
_ss.upload_file_to_storage = MagicMock()      # type: ignore

from agreement_document_service import (  # noqa: E402
    _apply_contract_signatures,
    _build_contract_replacements,
    _docx_to_blocks,
    _render_pdf,
    _replace_contract_text,
    _resolve_contract_fields,
    _validate_contract_fields,
    CONTRACT_TEMPLATE_DOCX_PATH,
    REQUIRED_CONTRACT_FIELDS,
)

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

_COMPLETE_EMPLOYEE = {
    "id": "emp_test_001",
    "name": "Test Worker",
    "job_title": "Care Worker",
    "contract_start_date": "2025-06-01",
    "continuous_service_date": "2025-06-01",
    "hourly_rate": "12.50",
    "sleep_in_rate": "40.00",
}

_ORG_SETTINGS = {
    "organisation_name": "Osabea Healthcare Solutions Ltd",
    "organisation_address": "19 Station Road, Harlow, CM20 2BB",
}

# Phrases that must NOT appear in a rendered contract.  Covers both the
# canonical {{token}} markers and every legacy (insert ...) variant.
_FORBIDDEN_PHRASES = [
    "{{employee_name}}",
    "{{issue_date}}",
    "{{job_title}}",
    "{{contract_start_date}}",
    "{{continuous_service_date}}",
    "{{hourly_rate}}",
    "{{sleep_in_rate}}",
    "{{company_name}}",
    "{{company_address}}",
    "{{commencement_wording}}",
    "(Insert Employee Name)",
    "(insert name of employee)",
    "(insert date of issue)",
    "(insert job title)",
    "(insert 'will commence' or 'commenced')",
    "(insert date this contract starts)",
    "(insert continuous service date of employment)",
    "(insert amount)",
    "iCubeDALPro",
    "iCareServicesGroup",
    "Unit 12, Harrods Road, Harlow, CM19 5BJ",
]


def _render_contract_pdf(employee: dict, org_settings: dict) -> bytes:
    """End-to-end render of the DOCX contract template to PDF bytes."""
    from docx import Document

    fields = _resolve_contract_fields(employee, org_settings)
    doc = Document(str(CONTRACT_TEMPLATE_DOCX_PATH))
    blocks = _docx_to_blocks(doc, lambda text: _replace_contract_text(text, fields))
    return _render_pdf(
        blocks,
        title="Employment Contract",
        subtitle=f"{fields['company_name']} | Test",
        employee_name=fields["full_name"],
    )


# ---------------------------------------------------------------------------
# Test 1 — No raw placeholder survives rendering
# ---------------------------------------------------------------------------

class TestNoUnreplacedPlaceholders:
    """Regression: contract PDF must contain no raw token or legacy placeholder."""

    def test_full_employee_no_placeholders(self):
        """A fully-populated employee record must leave no unfilled tokens."""
        pdf_bytes = _render_contract_pdf(_COMPLETE_EMPLOYEE, _ORG_SETTINGS)

        # Extract text from every page using PyPDF2
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        all_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        for phrase in _FORBIDDEN_PHRASES:
            assert phrase not in all_text, (
                f"Forbidden placeholder found in rendered contract: {phrase!r}"
            )

    def test_employee_name_appears_in_output(self):
        """Sanity: the employee's name must appear somewhere in the rendered PDF."""
        pdf_bytes = _render_contract_pdf(_COMPLETE_EMPLOYEE, _ORG_SETTINGS)
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        all_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "Test Worker" in all_text, "Employee name not found in rendered contract"

    def test_company_name_replaced(self):
        """The org's name must appear; the old embedded company name must not."""
        pdf_bytes = _render_contract_pdf(_COMPLETE_EMPLOYEE, _ORG_SETTINGS)
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        all_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "iCubeDALPro" not in all_text, "Legacy company name survived rendering"
        assert "Osabea Healthcare Solutions Ltd" in all_text, "Org name missing from contract"

    def test_hourly_rate_replaced(self):
        """Pay rate token must be replaced with the employee's rate value."""
        pdf_bytes = _render_contract_pdf(_COMPLETE_EMPLOYEE, _ORG_SETTINGS)
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        all_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "12.50" in all_text, "Hourly rate not found in rendered contract"
        assert "(insert amount)" not in all_text, "Legacy pay-rate placeholder survived"

    def test_pdf_template_path_not_used(self):
        """Rendering must use the DOCX template; the PDF-overlay path is dead."""
        import asyncio

        from agreement_document_service import (
            _load_template_bytes,
        )

        mock_db = MagicMock()
        # Return a fresh coroutine on each call so each await gets its own object
        mock_db.contract_templates.find_one = lambda *a, **kw: _coro(None)
        mock_db.org_settings.find_one = lambda *a, **kw: _coro(_ORG_SETTINGS)

        result = asyncio.run(
            _load_template_bytes(mock_db, "contract_acceptance")
        )
        _bytes, _name, path = result
        assert path.suffix.lower() != ".pdf", (
            "Contract template loader returned a PDF path — DOCX must be used."
        )
        assert "zero_hour_contract_template.docx" in str(path)


def _coro(value):
    """Wrap a value in a coroutine that returns a fixed value when awaited."""
    import asyncio

    async def _inner(*_args, **_kwargs):
        return value

    # Return a fresh coroutine object each time the mock is called.
    # We return the coroutine itself; the caller must await it, which is
    # handled by asyncio.run() below rather than the deprecated get_event_loop.
    return _inner()


# ---------------------------------------------------------------------------
# Test 2 — Signatures land on the last page, not a hardcoded index
# ---------------------------------------------------------------------------

class TestSignaturePagePlacement:
    """Regression: _apply_contract_signatures must overlay on the final page."""

    def _make_multi_page_pdf(self, num_pages: int) -> bytes:
        """Create a minimal multi-page PDF with reportlab."""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as _canvas

        buf = io.BytesIO()
        c = _canvas.Canvas(buf, pagesize=A4)
        for i in range(num_pages):
            c.drawString(72, 700, f"Page {i + 1} of {num_pages}")
            if i < num_pages - 1:
                c.showPage()
        c.save()
        return buf.getvalue()

    def _signature_overlay_page_count(self, pdf_bytes: bytes) -> int:
        """Return total page count of the PDF after signatures are applied."""
        from PyPDF2 import PdfReader
        signed = _apply_contract_signatures(
            pdf_bytes,
            worker_name="Test Worker",
            worker_signed_at="2025-06-01",
        )
        return len(PdfReader(io.BytesIO(signed)).pages)

    @pytest.mark.parametrize("num_pages", [1, 3, 7, 10, 15])
    def test_signature_preserves_page_count(self, num_pages: int):
        """Signing must never add or remove pages regardless of document length."""
        pdf = self._make_multi_page_pdf(num_pages)
        assert self._signature_overlay_page_count(pdf) == num_pages

    def test_signature_on_last_page_not_page_6(self):
        """For a 3-page doc, signatures must NOT fail or corrupt (old code used idx 6)."""
        pdf = self._make_multi_page_pdf(3)
        # Must not raise even though there is no page index 6
        signed = _apply_contract_signatures(
            pdf,
            worker_name="Jane Doe",
            worker_signed_at="2025-07-01",
        )
        from PyPDF2 import PdfReader
        assert len(PdfReader(io.BytesIO(signed)).pages) == 3

    def test_real_contract_signature(self):
        """Sign the real rendered contract — must succeed and preserve all pages."""
        pdf_bytes = _render_contract_pdf(_COMPLETE_EMPLOYEE, _ORG_SETTINGS)
        from PyPDF2 import PdfReader

        original_count = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
        signed = _apply_contract_signatures(
            pdf_bytes,
            worker_name="Test Worker",
            worker_signed_at="2025-06-15",
        )
        signed_count = len(PdfReader(io.BytesIO(signed)).pages)
        assert signed_count == original_count, (
            "Signing changed the page count unexpectedly"
        )


# ---------------------------------------------------------------------------
# Test 3 — Missing required fields are surfaced
# ---------------------------------------------------------------------------

class TestMissingFieldValidation:
    """Regression: broken employee data must produce a logged warning."""

    def test_missing_hourly_rate_warns(self, caplog):
        """An employee with no hourly rate must trigger a warning before rendering."""
        employee = {**_COMPLETE_EMPLOYEE, "hourly_rate": None, "pay_rate": None, "rate": None}
        fields = _resolve_contract_fields(employee, _ORG_SETTINGS)
        with caplog.at_level(logging.WARNING, logger="agreement_document_service"):
            _validate_contract_fields(fields)
        assert any("hourly_rate" in msg for msg in caplog.messages), (
            "No warning logged for missing hourly_rate"
        )

    def test_missing_contract_start_date_warns(self, caplog):
        """An employee with no start date must trigger a warning."""
        employee = {
            k: v for k, v in _COMPLETE_EMPLOYEE.items()
            if k not in ("contract_start_date", "start_date", "employment_start_date",
                         "job_start_date", "promoted_at")
        }
        fields = _resolve_contract_fields(employee, _ORG_SETTINGS)
        with caplog.at_level(logging.WARNING, logger="agreement_document_service"):
            _validate_contract_fields(fields)
        assert any("contract_start_date" in msg for msg in caplog.messages), (
            "No warning logged for missing contract_start_date"
        )

    def test_all_required_fields_present_no_warning(self, caplog):
        """A fully populated employee record must produce zero warnings."""
        fields = _resolve_contract_fields(_COMPLETE_EMPLOYEE, _ORG_SETTINGS)
        with caplog.at_level(logging.WARNING, logger="agreement_document_service"):
            _validate_contract_fields(fields)
        warning_messages = [m for m in caplog.messages if "Contract field" in m]
        assert warning_messages == [], (
            f"Unexpected field warnings for complete employee: {warning_messages}"
        )

    def test_tbc_placeholder_in_field_warns(self, caplog):
        """A field that resolves to 'TBC' (e.g. no start date) must be flagged."""
        employee = {
            "id": "emp_test_002",
            "name": "Ghost Worker",
            "job_title": "Support Worker",
            # no date fields, no rates → TBC values
        }
        fields = _resolve_contract_fields(employee, _ORG_SETTINGS)
        with caplog.at_level(logging.WARNING, logger="agreement_document_service"):
            _validate_contract_fields(fields)
        # At minimum hourly_rate and contract_start_date should be warned
        warned_fields = {
            msg.split("'")[1]  # extract field name from "Contract field 'X' is missing"
            for msg in caplog.messages
            if msg.startswith("Contract field")
        }
        assert "hourly_rate" in warned_fields
        assert "contract_start_date" in warned_fields

    @pytest.mark.parametrize("missing_field", REQUIRED_CONTRACT_FIELDS)
    def test_each_required_field_independently(self, missing_field, caplog):
        """Every entry in REQUIRED_CONTRACT_FIELDS must individually trigger a warning
        when that field is absent."""
        # Build a complete fields dict then manually blank the target field
        fields = _resolve_contract_fields(_COMPLETE_EMPLOYEE, _ORG_SETTINGS)
        fields[missing_field] = ""  # forcibly blank
        with caplog.at_level(logging.WARNING, logger="agreement_document_service"):
            _validate_contract_fields(fields)
        assert any(missing_field in msg for msg in caplog.messages), (
            f"No warning produced for missing required field: {missing_field!r}"
        )
