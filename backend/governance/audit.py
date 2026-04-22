"""
Shared audit metadata helpers for Phase 1 governance records.

Every new / extended governance collection (supervisions, competency_records,
spot_checks, incident_logs, care_plan_reviews, provider_profile) carries the
same audit shape so the worker dashboard, admin views, and inspection-pack
export can read them uniformly.

This module contains THE canonical audit shape.  Do not reimplement it inside
individual routes — import from here.

Record-level fields (written at create / update):
    id, created_at, created_by, updated_at, updated_by,
    verification_status, verified_at, verified_by, verified_by_name,
    audit_trail: list[AuditTrailEntry]

AuditTrailEntry fields:
    at, by, by_name, action, from, to, reason?, outcome?, notes?, actions?
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id(user: Optional[Dict[str, Any]]) -> str:
    if not user:
        return "system"
    return (
        user.get("user_id")
        or user.get("id")
        or user.get("employee_id")
        or "system"
    )


def _user_name(user: Optional[Dict[str, Any]]) -> str:
    if not user:
        return "System"
    name = user.get("name")
    if name:
        return name
    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    full = (first + " " + last).strip()
    return full or user.get("email") or "System"


def audit_trail_entry(
    *,
    user: Optional[Dict[str, Any]],
    action: str,
    from_: Any = None,
    to: Any = None,
    reason: Optional[str] = None,
    outcome: Optional[str] = None,
    notes: Optional[str] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build one append-only audit_trail entry.

    ``from_`` / ``to`` are generic (status strings, dicts, etc.) so any domain
    can record state transitions without subclassing.

    Only fields that are explicitly provided are included in the output —
    callers can rely on key presence to distinguish "not provided" from
    "explicitly empty".
    """
    entry: Dict[str, Any] = {
        "at": _now_iso(),
        "by": _user_id(user),
        "by_name": _user_name(user),
        "action": action,
    }
    if from_ is not None:
        entry["from"] = from_
    if to is not None:
        entry["to"] = to
    if reason is not None:
        entry["reason"] = reason
    if outcome is not None:
        entry["outcome"] = outcome
    if notes is not None:
        entry["notes"] = notes
    if actions is not None:
        entry["actions"] = list(actions)
    return entry


def new_audit_metadata(
    user: Optional[Dict[str, Any]],
    *,
    action: str = "create",
    record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the full audit block for a brand-new governance record.

    Usage:
        doc = {
            "employee_id": emp_id,
            **new_audit_metadata(user, action="schedule"),
            # domain-specific fields...
        }
    """
    now = _now_iso()
    by = _user_id(user)
    return {
        "id": record_id or str(uuid.uuid4()),
        "created_at": now,
        "created_by": by,
        "updated_at": now,
        "updated_by": by,
        "verification_status": "pending",
        "verified_at": None,
        "verified_by": None,
        "verified_by_name": None,
        "audit_trail": [
            audit_trail_entry(user=user, action=action),
        ],
    }


def stamp_update(
    record: Dict[str, Any],
    user: Optional[Dict[str, Any]],
    *,
    action: str,
    from_: Any = None,
    to: Any = None,
    reason: Optional[str] = None,
    outcome: Optional[str] = None,
    notes: Optional[str] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Mutate ``record`` in place with an update audit stamp and return it.

    - Updates ``updated_at`` and ``updated_by``.
    - Appends one entry to ``audit_trail`` (creating it if absent).
    - Never overwrites ``created_at`` / ``created_by``.
    """
    record["updated_at"] = _now_iso()
    record["updated_by"] = _user_id(user)
    record.setdefault("audit_trail", [])
    record["audit_trail"].append(
        audit_trail_entry(
            user=user,
            action=action,
            from_=from_,
            to=to,
            reason=reason,
            outcome=outcome,
            notes=notes,
            actions=actions,
        )
    )
    return record
