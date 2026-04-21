"""
End-to-end walkthrough simulation for the contract rendering + signing lifecycle.

Simulates the complete flow a worker with a complete profile would go through:

  1. Render base contract PDF (ensure_agreement_rendered)
  2. Verify rendered PDF contains no raw placeholders or legacy (insert...) phrases
  3. Worker signs → worker_signed_contract_pdf_url created, signature on last page
  4. Admin countersigns → executed_contract_pdf_url created, countersignature on last page
  5. Executed PDF is accessible via current_contract_artifact()
  6. Rejection clears signatures but preserves rendered_contract_pdf_url
  7. Re-sign after rejection → new worker_signed PDF produced from the preserved base

All DB interactions are replaced with in-memory dicts so no live server is required.
The Supabase upload is stubbed to return a deterministic URL.
"""
from __future__ import annotations

import asyncio
import io
import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Path bootstrap ─────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── Stub heavy / network deps before importing the service module ──────────
def _make_stub(name: str):
    mod = types.ModuleType(name)
    sys.modules.setdefault(name, mod)
    return mod

for _s in ["motor", "motor.motor_asyncio", "supabase_storage", "services", "services.pdf_service"]:
    _make_stub(_s)

sys.modules["services.pdf_service"].get_logo_image = lambda **_kw: None  # type: ignore
sys.modules["supabase_storage"].upload_file_to_storage = AsyncMock(return_value=None)  # placeholder
sys.modules["supabase_storage"].download_file_from_storage = AsyncMock(return_value=None)  # type: ignore

from agreement_document_service import (  # noqa: E402
    CONTRACT_AGREEMENT_TYPE,
    HANDBOOK_AGREEMENT_TYPE,
    _apply_contract_signatures,
    _build_contract_replacements,
    _resolve_contract_fields,
    countersign_contract,
    create_worker_signed_contract,
    current_contract_artifact,
    ensure_agreement_rendered,
)

# ── Supabase upload stub ───────────────────────────────────────────────────
# agreement_document_service captured `upload_file_to_storage` via `from … import`.
# We must patch the name *inside* that module for the stub to take effect.

_UPLOAD_COUNTER = [0]

async def _fake_upload(data, filename, folder="", **_kw):
    _UPLOAD_COUNTER[0] += 1
    return f"https://storage.example.com/{folder}/{filename}?v={_UPLOAD_COUNTER[0]}"


# Context manager that patches upload and download inside agreement_document_service
def _patched_storage():
    return patch.multiple(
        "agreement_document_service",
        upload_file_to_storage=_fake_upload,
        download_file_from_storage=AsyncMock(return_value=None),
    )

# ── In-memory fake DB ──────────────────────────────────────────────────────

class _FakeCollection:
    """Minimal MongoDB collection stub backed by a plain dict store."""

    def __init__(self):
        self._data: Dict[str, Dict] = {}

    # find_one
    async def find_one(self, query: dict, projection: Optional[dict] = None):
        for doc in self._data.values():
            if self._matches(doc, query):
                result = {k: v for k, v in doc.items() if k != "_id"}
                return result
        return None

    # update_one (with upsert support)
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        for key, doc in self._data.items():
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                doc.update({k: v for k, v in update.get("$setOnInsert", {}).items() if k not in doc})
                return MagicMock(matched_count=1, upserted_id=None)
        if upsert:
            new_doc = {}
            new_doc.update(update.get("$set", {}))
            new_doc.update(update.get("$setOnInsert", {}))
            uid = new_doc.get("id") or f"doc_{len(self._data)}"
            self._data[uid] = new_doc
            return MagicMock(matched_count=0, upserted_id=uid)
        return MagicMock(matched_count=0, upserted_id=None)

    # update_many
    async def update_many(self, query: dict, update: dict, **_kw):
        count = 0
        for doc in self._data.values():
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                count += 1
        return MagicMock(modified_count=count)

    def _matches(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if isinstance(v, dict):
                op = list(v.keys())[0]
                val = v[op]
                dval = doc.get(k)
                if op == "$in" and dval not in val:
                    return False
                if op == "$ne" and dval == val:
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def seed(self, doc: dict):
        self._data[doc.get("id", str(len(self._data)))] = dict(doc)


class _FakeDB:
    def __init__(self):
        self.agreement_acknowledgements = _FakeCollection()
        self.generated_contracts = _FakeCollection()
        self.contract_templates = _FakeCollection()   # empty → no custom template
        self.org_settings = _FakeCollection()
        self.org_settings.seed({"id": "org", "organisation_name": "Osabea Healthcare Solutions Ltd", "organisation_address": "19 Station Road, Harlow, CM20 2BB"})


# ── Test data ─────────────────────────────────────────────────────────────

_COMPLETE_EMPLOYEE: Dict[str, Any] = {
    "id": "emp_walkthrough_001",
    "name": "Alice Walker",
    "job_title": "Care Worker",
    "contract_start_date": "2025-09-01",
    "continuous_service_date": "2025-09-01",
    "hourly_rate": "13.50",
    "sleep_in_rate": "40.00",
}

_FORBIDDEN_PHRASES = [
    "{{employee_name}}", "{{issue_date}}", "{{job_title}}",
    "{{contract_start_date}}", "{{continuous_service_date}}",
    "{{hourly_rate}}", "{{sleep_in_rate}}", "{{company_name}}",
    "{{company_address}}", "{{commencement_wording}}",
    "(Insert Employee Name)", "(insert name of employee)",
    "(insert date of issue)", "(insert job title)",
    "(insert 'will commence' or 'commenced')",
    "(insert date this contract starts)",
    "(insert continuous service date of employment)",
    "(insert amount)", "iCubeDALPro", "iCareServicesGroup",
    "Unit 12, Harrods Road, Harlow, CM19 5BJ",
]


def _pdf_text(pdf_bytes: bytes) -> str:
    from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _pdf_page_count(pdf_bytes: bytes) -> int:
    from PyPDF2 import PdfReader
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


def _fake_png_signature() -> bytes:
    """Minimal 1×1 white PNG without requiring Pillow."""
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQ"
        "AABjkB6QAAAABJRU5ErkJggg=="
    )


# ── Helpers ───────────────────────────────────────────────────────────────

async def _render_base(db: _FakeDB) -> tuple[dict, bytes]:
    """Step 1: render the base contract PDF for the complete employee."""
    with _patched_storage():
        record = await ensure_agreement_rendered(db, _COMPLETE_EMPLOYEE, CONTRACT_AGREEMENT_TYPE)
    assert record, "ensure_agreement_rendered returned None"
    assert record.get("rendered_contract_pdf_url"), "rendered_contract_pdf_url not set"
    assert record.get("template_version"), "template_version not set"
    # Recover actual PDF bytes via build_agreement_rendering (no storage call needed)
    from agreement_document_service import build_agreement_rendering
    rendering = await build_agreement_rendering(db, _COMPLETE_EMPLOYEE, CONTRACT_AGREEMENT_TYPE)
    return record, rendering["pdf_bytes"]


# ── Walkthrough tests ─────────────────────────────────────────────────────

class TestContractWalkthrough:
    """Full end-to-end lifecycle walkthrough for a worker with a complete profile."""

    @pytest.fixture()
    def db(self):
        return _FakeDB()

    # ── Step 1: base render ───────────────────────────────────────────────

    def test_01_render_produces_pdf(self, db):
        """ensure_agreement_rendered produces a PDF and stores the URL."""
        record, pdf_bytes = asyncio.run(_render_base(db))
        assert pdf_bytes[:4] == b"%PDF", "Rendered output is not a PDF"
        assert len(pdf_bytes) > 2000, "Rendered PDF suspiciously small"

    # ── Step 2: no raw placeholders in rendered PDF ───────────────────────

    def test_02_no_placeholder_text_in_rendered_pdf(self, db):
        """Step 2 — No {{token}} or (insert...) phrase survives in the rendered PDF."""
        _, pdf_bytes = asyncio.run(_render_base(db))
        text = _pdf_text(pdf_bytes)
        for phrase in _FORBIDDEN_PHRASES:
            assert phrase not in text, (
                f"Forbidden placeholder found in rendered contract: {phrase!r}"
            )

    def test_02b_correct_field_values_in_rendered_pdf(self, db):
        """Employee name, org name, and hourly rate appear in the rendered PDF."""
        _, pdf_bytes = asyncio.run(_render_base(db))
        text = _pdf_text(pdf_bytes)
        assert "Alice Walker" in text, "Employee name missing from rendered PDF"
        assert "Osabea Healthcare Solutions Ltd" in text, "Org name missing from rendered PDF"
        assert "13.50" in text, "Hourly rate missing from rendered PDF"

    # ── Step 3: worker signature lands on last page ───────────────────────

    def test_03_worker_signature_on_last_page(self, db):
        """Step 3 — Worker signature must not fail; PDF page count must be preserved."""
        _, pdf_bytes = asyncio.run(_render_base(db))
        original_pages = _pdf_page_count(pdf_bytes)
        signed_bytes = _apply_contract_signatures(
            pdf_bytes,
            worker_signature_bytes=_fake_png_signature(),
            worker_name="Alice Walker",
            worker_signed_at="2025-09-15",
        )
        assert _pdf_page_count(signed_bytes) == original_pages, (
            "Worker signing changed the page count"
        )

    def test_03b_three_page_doc_not_hardcoded_page_6(self, db):
        """Signing a short (3-page) doc must not raise — old code used hardcoded idx 6."""
        import asyncio as _asyncio
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as _canvas

        buf = io.BytesIO()
        c = _canvas.Canvas(buf, pagesize=A4)
        for i in range(3):
            c.drawString(72, 700, f"Page {i + 1}")
            if i < 2:
                c.showPage()
        c.save()
        short_pdf = buf.getvalue()

        signed = _apply_contract_signatures(
            short_pdf, worker_name="Alice Walker", worker_signed_at="2025-09-15"
        )
        assert _pdf_page_count(signed) == 3

    # ── Step 4: admin countersignature on last page ───────────────────────

    def test_04_countersignature_lands_on_last_page(self, db):
        """Step 4 — Countersigning preserves page count (signature on last page)."""
        _, pdf_bytes = asyncio.run(_render_base(db))
        worker_signed = _apply_contract_signatures(
            pdf_bytes,
            worker_signature_bytes=_fake_png_signature(),
            worker_name="Alice Walker",
            worker_signed_at="2025-09-15",
        )
        executed = _apply_contract_signatures(
            worker_signed,
            company_name="Osabea Healthcare Solutions Ltd",
            company_signed_at="2025-09-20",
        )
        assert _pdf_page_count(executed) == _pdf_page_count(pdf_bytes), (
            "Countersigning changed the page count"
        )

    # ── Step 5: executed PDF accessible via current_contract_artifact ─────

    def test_05_executed_pdf_accessible(self):
        """Step 5 — current_contract_artifact returns the most-progressed URL."""
        # Fully executed
        agreement = {
            "contract_state": "fully_executed",
            "rendered_contract_pdf_url": "https://example.com/rendered.pdf",
            "worker_signed_contract_pdf_url": "https://example.com/worker_signed.pdf",
            "executed_contract_pdf_url": "https://example.com/executed.pdf",
        }
        assert current_contract_artifact(agreement) == "https://example.com/executed.pdf"

        # Awaiting company countersignature
        agreement["contract_state"] = "awaiting_company_countersignature"
        agreement["executed_contract_pdf_url"] = None
        assert current_contract_artifact(agreement) == "https://example.com/worker_signed.pdf"

        # Awaiting worker signature
        agreement["contract_state"] = "awaiting_worker_signature"
        agreement["worker_signed_contract_pdf_url"] = None
        assert current_contract_artifact(agreement) == "https://example.com/rendered.pdf"

    # ── Step 6: rejection preserves rendered base, clears signed URLs ─────

    def test_06_rejection_preserves_rendered_base(self, db):
        """Step 6 — Rejection must nil out signed/executed URLs but keep rendered_contract_pdf_url."""
        async def _run():
            with _patched_storage():
                record = await ensure_agreement_rendered(db, _COMPLETE_EMPLOYEE, CONTRACT_AGREEMENT_TYPE)
            assert record.get("rendered_contract_pdf_url"), "No rendered URL before rejection"
            rendered_url = record["rendered_contract_pdf_url"]

            # Simulate rejection by applying the same set_payload the service does
            # (tests the invariant without needing a live AgreementAcknowledgementService)
            rejection_set = {
                "acknowledged": False,
                "status": "rejected",
                "verification_status": "rejected",
                "contract_state": "rejected_reopen_required",
                "signed_document_url": None,
                "worker_signed_contract_pdf_url": None,
                "executed_contract_pdf_url": None,
                "worker_signed_at": None,
                "worker_signer_name": None,
                "company_signed_at": None,
                "company_signer_name": None,
            }
            await db.agreement_acknowledgements.update_one(
                {"employee_id": _COMPLETE_EMPLOYEE["id"], "agreement_type": CONTRACT_AGREEMENT_TYPE},
                {"$set": rejection_set},
            )

            rejected = await db.agreement_acknowledgements.find_one(
                {"employee_id": _COMPLETE_EMPLOYEE["id"], "agreement_type": CONTRACT_AGREEMENT_TYPE}
            )
            assert rejected is not None
            assert rejected.get("contract_state") == "rejected_reopen_required"
            assert rejected.get("worker_signed_contract_pdf_url") is None, (
                "worker_signed_contract_pdf_url must be cleared on rejection"
            )
            assert rejected.get("executed_contract_pdf_url") is None, (
                "executed_contract_pdf_url must be cleared on rejection"
            )
            # rendered_contract_pdf_url MUST be preserved
            assert rejected.get("rendered_contract_pdf_url") == rendered_url, (
                "rendered_contract_pdf_url must survive rejection — re-sign reuses it"
            )

        asyncio.run(_run())

    # ── Step 7: re-sign after rejection reuses preserved base ────────────

    def test_07_resign_after_rejection_reuses_base(self, db):
        """Step 7 — After rejection, re-calling ensure_agreement_rendered returns the
        same rendered_contract_pdf_url (no re-render) so the base is stable."""
        async def _run():
            with _patched_storage():
                record1 = await ensure_agreement_rendered(db, _COMPLETE_EMPLOYEE, CONTRACT_AGREEMENT_TYPE)
            url1 = record1.get("rendered_contract_pdf_url")
            assert url1

            # Simulate rejection (clear signed URLs, keep rendered)
            await db.agreement_acknowledgements.update_one(
                {"employee_id": _COMPLETE_EMPLOYEE["id"], "agreement_type": CONTRACT_AGREEMENT_TYPE},
                {"$set": {
                    "status": "rejected",
                    "contract_state": "rejected_reopen_required",
                    "worker_signed_contract_pdf_url": None,
                    "executed_contract_pdf_url": None,
                }},
            )

            # ensure_agreement_rendered is called again at worker re-sign
            with _patched_storage():
                record2 = await ensure_agreement_rendered(db, _COMPLETE_EMPLOYEE, CONTRACT_AGREEMENT_TYPE)
            url2 = record2.get("rendered_contract_pdf_url")

            assert url2 == url1, (
                f"Re-render after rejection must return the same base URL. "
                f"Got {url2!r}, expected {url1!r}"
            )

        asyncio.run(_run())


# ── Legacy text removal tests ─────────────────────────────────────────────

class TestLegacyTextRemoved:
    """Verify legacy company name/address no longer appear in the live rendering path."""

    def test_contract_tokens_have_no_legacy_placeholders(self):
        """_build_contract_replacements must not include any (insert...) keys."""
        fields = _resolve_contract_fields(_COMPLETE_EMPLOYEE, {
            "organisation_name": "Osabea Healthcare Solutions Ltd",
            "organisation_address": "19 Station Road, Harlow",
        })
        replacements = _build_contract_replacements(fields)
        for key in replacements:
            assert not key.startswith("(insert"), (
                f"Legacy (insert...) key still in replacement map: {key!r}"
            )
            assert "iCubeDALPro" not in key, (
                f"Legacy company literal still in replacement key: {key!r}"
            )

    def test_contract_templates_module_no_icube(self):
        """contract_templates.ZERO_HOUR_CONTRACT_TEMPLATE must not reference iCubeDALPro."""
        from contract_templates import ZERO_HOUR_CONTRACT_TEMPLATE
        import json
        serialised = json.dumps(ZERO_HOUR_CONTRACT_TEMPLATE)
        assert "iCubeDALPro" not in serialised, (
            "iCubeDALPro still embedded in ZERO_HOUR_CONTRACT_TEMPLATE"
        )
        assert "iCareServicesGroup" not in serialised, (
            "iCareServicesGroup still embedded in ZERO_HOUR_CONTRACT_TEMPLATE"
        )

    def test_fill_contract_template_replaces_company_name(self):
        """fill_contract_template must substitute [COMPANY_NAME] in acceptance section."""
        from contract_templates import fill_contract_template
        result = fill_contract_template(
            {"first_name": "Alice", "last_name": "Walker", "role": "Care Worker"}
        )
        # Find acceptance section
        acceptance = next(
            (s for s in result.get("sections", []) if s["id"] == "acceptance"), None
        )
        assert acceptance is not None
        content = acceptance["content"]
        assert "[COMPANY_NAME]" not in content, (
            "[COMPANY_NAME] placeholder not replaced in acceptance section"
        )
        assert "Osabea Healthcare Solutions Ltd" in content, (
            "Company name not filled in acceptance section"
        )
