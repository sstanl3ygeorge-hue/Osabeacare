from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_HISTORICAL_STATUSES = {
    "superseded",
    "rejected",
    "invalidated",
    "deleted",
    "archived",
    "uploaded_in_error",
    "removed",
    "replaced",
}

_ACCEPTED_EVIDENCE_STATUSES = {
    "accepted",
    "verified",
    "approved",
}

_ACTIVE_CHECK_STATUSES = {
    "verified",
    "completed",
    "accepted",
    "pending",
    "awaiting_review",
    "awaiting_verification",
    "in_progress",
}


def _to_lower(v: Any) -> str:
    return str(v or "").strip().lower()


def _parse_dt(v: Any) -> datetime:
    if not v:
        return datetime.min.replace(tzinfo=timezone.utc)
    s = str(v)
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _is_historical_document(doc: Dict[str, Any]) -> bool:
    if doc.get("is_active") is False:
        return True
    status = _to_lower(doc.get("status"))
    review_status = _to_lower(doc.get("review_status"))
    if status in _HISTORICAL_STATUSES:
        return True
    if review_status in _HISTORICAL_STATUSES:
        return True
    return False


def _doc_is_accepted(doc: Dict[str, Any]) -> bool:
    if _to_lower(doc.get("status")) in _ACCEPTED_EVIDENCE_STATUSES:
        return True
    if _to_lower(doc.get("review_status")) in _ACCEPTED_EVIDENCE_STATUSES:
        return True
    if doc.get("verified") is True:
        return True
    stamp = _to_lower(doc.get("verification_stamp"))
    if stamp and stamp != "not_verified":
        return True
    return False


def _check_is_active(check: Dict[str, Any]) -> bool:
    if check.get("is_active") is False:
        return False
    status = _to_lower(check.get("status") or check.get("verification_status"))
    if not status:
        return True
    return status in _ACTIVE_CHECK_STATUSES


def _check_is_verified(check: Dict[str, Any]) -> bool:
    status = _to_lower(check.get("status") or check.get("verification_status"))
    return bool(
        check.get("verified") is True
        or status in {"verified", "completed", "accepted"}
    )


async def resolve_compliance_requirement_state(
    employee_id: str,
    requirement_id: str,
    *,
    context: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Read-only canonical resolver for a single compliance requirement state.

    Context contract:
    - context["documents"]: list[dict] of requirement evidence docs
    - context["check_rows"]: list[dict] of verification/check rows
    - context["source_errors"]: optional list[str] from upstream readers
    """
    requirement_id = str(requirement_id or "").strip()
    warnings: List[str] = []
    source_errors = list((context or {}).get("source_errors") or [])

    raw_docs = list((context or {}).get("documents") or [])
    raw_checks = list((context or {}).get("check_rows") or [])

    if not requirement_id:
        return {
            "requirement_id": requirement_id,
            "effective_state": "status_unavailable",
            "status": "status_unavailable",
            "status_unavailable": True,
            "has_accepted_evidence": False,
            "has_check_record": False,
            "verified": False,
            "document_count": 0,
            "warnings": ["missing_requirement_id"],
            "raw_refs": {"documents": [], "check_rows": []},
        }

    docs: List[Dict[str, Any]] = []
    skipped_null_req = 0
    for d in raw_docs:
        if not isinstance(d, dict):
            warnings.append("malformed_document_row")
            continue
        req = d.get("requirement_id")
        if req is None or str(req).strip() == "":
            skipped_null_req += 1
            continue
        if _to_lower(req) != _to_lower(requirement_id):
            continue
        if _is_historical_document(d):
            continue
        docs.append(d)
    if skipped_null_req:
        warnings.append(f"null_requirement_id_docs_skipped:{skipped_null_req}")

    checks: List[Dict[str, Any]] = []
    for c in raw_checks:
        if not isinstance(c, dict):
            warnings.append("malformed_check_row")
            continue
        req = c.get("requirement_id")
        if req is not None and str(req).strip() and _to_lower(req) != _to_lower(requirement_id):
            continue
        if not _check_is_active(c):
            continue
        checks.append(c)

    docs.sort(key=lambda x: _parse_dt(x.get("updated_at") or x.get("created_at") or x.get("uploaded_at")), reverse=True)
    checks.sort(key=lambda x: _parse_dt(x.get("updated_at") or x.get("created_at") or x.get("checked_at")), reverse=True)

    has_accepted_evidence = any(_doc_is_accepted(d) for d in docs)
    has_check_record = len(checks) > 0
    verified = any(_check_is_verified(c) for c in checks)

    status_unavailable = bool(source_errors)
    if status_unavailable:
        warnings.extend([f"source_error:{e}" for e in source_errors if e])

    if status_unavailable:
        effective_state = "status_unavailable"
        status = "status_unavailable"
    elif verified:
        effective_state = "verified"
        status = "verified"
    elif has_accepted_evidence and not has_check_record:
        effective_state = "awaiting_check"
        status = "pending"
    elif has_accepted_evidence and has_check_record:
        effective_state = "awaiting_verification"
        status = "pending"
    elif docs and not has_accepted_evidence:
        effective_state = "evidence_under_review"
        status = "pending"
    else:
        effective_state = "not_started"
        status = "incomplete"

    return {
        "requirement_id": requirement_id,
        "effective_state": effective_state,
        "status": status,
        "status_unavailable": status_unavailable,
        "has_accepted_evidence": has_accepted_evidence,
        "has_check_record": has_check_record,
        "verified": verified,
        "document_count": len(docs),
        "warnings": warnings,
        "raw_refs": {
            "documents": [d.get("id") for d in docs if isinstance(d, dict)],
            "check_rows": [c.get("id") for c in checks if isinstance(c, dict)],
        },
    }

