import importlib.util
from pathlib import Path
import asyncio

import pytest


_RESOLVER_PATH = Path(__file__).resolve().parents[1] / "services" / "compliance_requirement_resolver.py"
_SPEC = importlib.util.spec_from_file_location("compliance_requirement_resolver", _RESOLVER_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_MOD)
resolve_compliance_requirement_state = _MOD.resolve_compliance_requirement_state


def test_malformed_rows_return_typed_fallback():
    result = asyncio.run(resolve_compliance_requirement_state(
        "emp-1",
        "right_to_work_documents",
        context={
            "documents": ["bad-row", {"id": "d1", "requirement_id": "right_to_work_documents", "status": "accepted"}],
            "check_rows": ["bad-check"],
            "source_errors": ["check_source_timeout"],
        },
    ))
    assert result["status_unavailable"] is True
    assert result["status"] == "status_unavailable"
    assert any("malformed_document_row" in w for w in result["warnings"])
    assert any("malformed_check_row" in w for w in result["warnings"])


def test_stale_rejected_ignored_when_active_accepted_exists():
    result = asyncio.run(resolve_compliance_requirement_state(
        "emp-1",
        "proof_of_address",
        context={
            "documents": [
                {
                    "id": "old-rejected",
                    "requirement_id": "proof_of_address",
                    "status": "rejected",
                    "is_active": False,
                    "updated_at": "2026-01-01T00:00:00+00:00",
                },
                {
                    "id": "active-accepted",
                    "requirement_id": "proof_of_address",
                    "status": "accepted",
                    "is_active": True,
                    "updated_at": "2026-02-01T00:00:00+00:00",
                },
            ],
            "check_rows": [],
        },
    ))
    assert result["status_unavailable"] is False
    assert result["has_accepted_evidence"] is True
    assert result["effective_state"] == "awaiting_check"
    assert "old-rejected" not in result["raw_refs"]["documents"]


def test_accepted_evidence_missing_check_returns_pending_awaiting_check():
    result = asyncio.run(resolve_compliance_requirement_state(
        "emp-1",
        "identity_documents",
        context={
            "documents": [
                {"id": "doc-1", "requirement_id": "identity_documents", "status": "accepted", "is_active": True}
            ],
            "check_rows": [],
        },
    ))
    assert result["has_accepted_evidence"] is True
    assert result["has_check_record"] is False
    assert result["verified"] is False
    assert result["effective_state"] == "awaiting_check"
    assert result["status"] == "pending"


def test_null_requirement_id_docs_skipped_with_warning():
    result = asyncio.run(resolve_compliance_requirement_state(
        "emp-1",
        "dbs_certificate",
        context={
            "documents": [
                {"id": "null-req", "requirement_id": None, "status": "accepted"},
                {"id": "blank-req", "requirement_id": "", "status": "accepted"},
            ],
            "check_rows": [],
        },
    ))
    assert result["document_count"] == 0
    assert any("null_requirement_id_docs_skipped" in w for w in result["warnings"])
    assert result["effective_state"] == "not_started"


def test_no_active_evidence_or_check_safe_incomplete_state():
    result = asyncio.run(resolve_compliance_requirement_state(
        "emp-1",
        "right_to_work_documents",
        context={"documents": [], "check_rows": []},
    ))
    assert result["status_unavailable"] is False
    assert result["has_accepted_evidence"] is False
    assert result["has_check_record"] is False
    assert result["verified"] is False
    assert result["effective_state"] == "not_started"
    assert result["status"] == "incomplete"
