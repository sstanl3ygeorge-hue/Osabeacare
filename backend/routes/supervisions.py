"""
Supervisions domain — Phase 1 governance.

Owns the ``supervisions`` collection (evidence of individual supervision
meetings).  Due dates live in ``recurring_compliance`` (the cadence engine);
this module never duplicates cadence logic.

Hard rules (from PHASE_1_GOVERNANCE_PLAN.md §A):
  - One cadence row per (employee_id, item_type="supervision") owns "next
    due" and reminders.  The domain record carries a snapshot of the
    last computed ``next_due_at`` for UI convenience only.
  - Every admin route uses ``require_employee_not_applicant`` so this
    surface can never render for applicants.
  - Readiness ONLY counts ``verification_status == "verified"`` rows — the
    verified-only gate is centralised in ``get_supervision_summary``.
  - Audit fields are produced by ``governance.audit.*`` helpers so every
    transition is traceable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .dependencies import get_db, require_manager_or_admin
from .recurring_compliance import (
    FREQUENCY_DAYS_MAP,
    RECURRING_REMINDER_SCHEDULE,
    ESCALATION_THRESHOLD_DAYS,
    calculate_next_due_date,
)

# Import the governance plumbing built in Step 1.
import sys
import os as _os
_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
from governance.audit import new_audit_metadata, stamp_update  # noqa: E402
from governance.guards import require_employee_not_applicant  # noqa: E402
from governance.supervisions_summary import (  # noqa: E402
    compute_supervision_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Supervisions"])


# ════════════════════════════════════════════════════════════════════════════
# Enums & cadence defaults
# ════════════════════════════════════════════════════════════════════════════

SUPERVISION_TYPES = (
    "probation",
    "routine",
    "return_to_work",
    "performance",
    "safeguarding_followup",
    "capability",
    "ad_hoc",
)

SUPERVISION_STATUSES = (
    "scheduled",
    "completed",
    "overdue",
    "cancelled",
)

SUPERVISION_OUTCOMES = (
    "satisfactory",
    "needs_improvement",
    "action_required",
    "not_applicable",
)

# Cadence per supervision type.  Values are keys in FREQUENCY_DAYS_MAP so we
# reuse the existing cadence engine rather than inventing parallel durations.
SUPERVISION_CADENCE = {
    "probation":             "monthly",      # 30d — new starter close monitoring
    "routine":               "quarterly",    # 91d — baseline managerial supervision
    "return_to_work":        "ad_hoc",       # one-off
    "performance":           "monthly",      # close cadence during a plan
    "safeguarding_followup": "ad_hoc",       # event-driven
    "capability":            "monthly",      # close cadence during a plan
    "ad_hoc":                "ad_hoc",
}

RECURRING_ITEM_TYPE = "supervision"


# ════════════════════════════════════════════════════════════════════════════
# Pydantic models
# ════════════════════════════════════════════════════════════════════════════

class ActionItem(BaseModel):
    description: str
    due_at: Optional[str] = None
    owner_id: Optional[str] = None
    status: str = "open"


class SupervisionCreate(BaseModel):
    employee_id: str
    supervisor_id: str
    supervision_type: str
    scheduled_at: str
    role_scope: List[str] = Field(default_factory=lambda: ["any"])
    summary: Optional[str] = None
    notes: Optional[str] = None


class SupervisionPatch(BaseModel):
    supervisor_id: Optional[str] = None
    supervision_type: Optional[str] = None
    scheduled_at: Optional[str] = None
    role_scope: Optional[List[str]] = None
    summary: Optional[str] = None
    notes: Optional[str] = None


class SupervisionComplete(BaseModel):
    completed_at: str
    outcome: str
    summary: Optional[str] = None
    notes: Optional[str] = None
    actions: List[ActionItem] = Field(default_factory=list)


class SupervisionCancel(BaseModel):
    reason: str


# ════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ════════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_enum(value: str, allowed, field: str) -> None:
    if value not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field}. Must be one of: {list(allowed)}",
        )


async def _upsert_cadence_row(
    db,
    *,
    employee_id: str,
    supervision_type: str,
    next_due_date: str,
    assigned_to: str,
    user: dict,
) -> str:
    """Ensure the (employee, supervision) cadence row exists and owns next-due.

    Returns the recurring_compliance id.  Never writes cadence data on the
    supervisions row itself — supervision rows snapshot ``next_due_at`` only
    for UI display.
    """
    frequency = SUPERVISION_CADENCE.get(supervision_type, "ad_hoc")
    existing = await db.recurring_compliance.find_one(
        {
            "employee_id": employee_id,
            "item_type": RECURRING_ITEM_TYPE,
            "item_name": supervision_type,
            "is_active": True,
        },
        {"_id": 0, "id": 1},
    )
    if existing:
        await db.recurring_compliance.update_one(
            {"id": existing["id"]},
            {"$set": {
                "next_due_date": next_due_date,
                "frequency": frequency,
                "frequency_days": FREQUENCY_DAYS_MAP.get(frequency),
                "assigned_to": assigned_to,
                "updated_at": _now_iso(),
            }},
        )
        return existing["id"]

    import uuid as _uuid
    rc_id = str(_uuid.uuid4())
    now = _now_iso()
    await db.recurring_compliance.insert_one({
        "id": rc_id,
        "employee_id": employee_id,
        "item_type": RECURRING_ITEM_TYPE,
        "item_name": supervision_type,
        "description": f"Supervision cadence ({supervision_type})",
        "frequency": frequency,
        "frequency_days": FREQUENCY_DAYS_MAP.get(frequency),
        "next_due_date": next_due_date,
        "last_completed_date": None,
        "assigned_to": assigned_to,
        "escalate_to": None,
        "linked_report_id": None,
        "linked_incident_id": None,
        "reminder_schedule": RECURRING_REMINDER_SCHEDULE,
        "reminders_sent": [],
        "escalation_threshold_days": ESCALATION_THRESHOLD_DAYS,
        "escalation_sent": False,
        "completion_history": [],
        "is_active": True,
        "created_at": now,
        "created_by": (user or {}).get("user_id", "system"),
        "updated_at": now,
    })
    return rc_id


async def _cadence_next_due(db, employee_id: str) -> Optional[str]:
    """Return the earliest active cadence next_due_date for this employee's
    supervision cadence rows.  Used for the summary helper input."""
    rows = await db.recurring_compliance.find(
        {
            "employee_id": employee_id,
            "item_type": RECURRING_ITEM_TYPE,
            "is_active": True,
        },
        {"_id": 0, "next_due_date": 1},
    ).to_list(50)
    dates = [r.get("next_due_date") for r in rows if r.get("next_due_date")]
    return min(dates) if dates else None


async def get_supervision_summary(db, employee_id: str) -> Dict[str, Any]:
    """Fetch verified-only supervision rows + cadence and summarise them.

    Verified-only gate is enforced here so the readiness helper never sees
    unverified evidence.  Cancelled rows are still returned (they are
    cancelled events, not unverified evidence) so the helper can distinguish
    cancellations from completions.
    """
    rows = await db.supervisions.find(
        {
            "employee_id": employee_id,
            "$or": [
                {"verification_status": "verified"},
                {"status": {"$in": ["scheduled", "cancelled", "overdue"]}},
            ],
        },
        {"_id": 0},
    ).to_list(500)
    cadence_next = await _cadence_next_due(db, employee_id)
    return compute_supervision_summary(rows, cadence_next_due_at=cadence_next)


# ════════════════════════════════════════════════════════════════════════════
# Routes — admin / manager only, always guarded against applicant context
# ════════════════════════════════════════════════════════════════════════════

@router.post("/supervisions")
async def create_supervision(
    payload: SupervisionCreate,
    user: dict = Depends(require_manager_or_admin),
):
    """Schedule a new supervision.

    Creates the evidence row AND upserts the cadence row.  Cadence ``next
    due`` is set to ``scheduled_at`` (the cadence engine will compute the
    next cycle once the supervision is completed).
    """
    _validate_enum(payload.supervision_type, SUPERVISION_TYPES, "supervision_type")
    db = get_db()

    # Applicant guard — enforced here because POST has the employee_id in
    # the body rather than the path.  Same function, same 403.
    from governance.guards import _guard_employee_not_applicant
    await _guard_employee_not_applicant(payload.employee_id, db=db)

    rc_id = await _upsert_cadence_row(
        db,
        employee_id=payload.employee_id,
        supervision_type=payload.supervision_type,
        next_due_date=payload.scheduled_at,
        assigned_to=payload.supervisor_id,
        user=user,
    )

    meta = new_audit_metadata(user, action="schedule_supervision")
    doc = {
        **meta,
        "employee_id": payload.employee_id,
        "supervisor_id": payload.supervisor_id,
        "supervision_type": payload.supervision_type,
        "role_scope": payload.role_scope or ["any"],
        "scheduled_at": payload.scheduled_at,
        "completed_at": None,
        "status": "scheduled",
        "outcome": None,
        "summary": payload.summary,
        "notes": payload.notes,
        "actions": [],
        "next_due_at": payload.scheduled_at,
        "recurring_compliance_id": rc_id,
    }
    await db.supervisions.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/supervisions/{employee_id}")
async def list_supervisions(
    employee_id: str,
    user: dict = Depends(require_manager_or_admin),
    employee: dict = Depends(require_employee_not_applicant),
):
    """List supervision records for an employee, newest first.

    The path-level ``require_employee_not_applicant`` dependency blocks
    applicant access before the query runs.
    """
    db = get_db()
    rows = await db.supervisions.find(
        {"employee_id": employee_id},
        {"_id": 0},
    ).to_list(1000)
    rows.sort(
        key=lambda r: (r.get("scheduled_at") or r.get("created_at") or ""),
        reverse=True,
    )
    summary = await get_supervision_summary(db, employee_id)
    return {"items": rows, "summary": summary}


@router.patch("/supervisions/{supervision_id}")
async def patch_supervision(
    supervision_id: str,
    payload: SupervisionPatch,
    user: dict = Depends(require_manager_or_admin),
):
    """Edit pre-completion fields only.  Cannot patch completed rows —
    use a new supervision for follow-up outcomes instead."""
    db = get_db()
    record = await db.supervisions.find_one({"id": supervision_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Supervision not found")
    if record.get("status") in ("completed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit supervision in status '{record['status']}'",
        )

    # Enforce applicant guard via the shared helper.
    from governance.guards import _guard_employee_not_applicant
    await _guard_employee_not_applicant(record["employee_id"], db=db)

    updates: Dict[str, Any] = {}
    if payload.supervision_type is not None:
        _validate_enum(payload.supervision_type, SUPERVISION_TYPES, "supervision_type")
        updates["supervision_type"] = payload.supervision_type
    for field in ("supervisor_id", "scheduled_at", "role_scope", "summary", "notes"):
        val = getattr(payload, field)
        if val is not None:
            updates[field] = val

    if not updates:
        return record

    stamp_update(record, user, action="edit_supervision", to=updates)
    record.update(updates)
    # If schedule moved, sync cadence row.
    if "scheduled_at" in updates or "supervision_type" in updates:
        await _upsert_cadence_row(
            db,
            employee_id=record["employee_id"],
            supervision_type=record["supervision_type"],
            next_due_date=record["scheduled_at"],
            assigned_to=record["supervisor_id"],
            user=user,
        )
        record["next_due_at"] = record["scheduled_at"]

    await db.supervisions.update_one(
        {"id": supervision_id},
        {"$set": {
            **updates,
            "updated_at": record["updated_at"],
            "updated_by": record["updated_by"],
            "audit_trail": record["audit_trail"],
            "next_due_at": record.get("next_due_at"),
        }},
    )
    return record


@router.post("/supervisions/{supervision_id}/complete")
async def complete_supervision(
    supervision_id: str,
    payload: SupervisionComplete,
    user: dict = Depends(require_manager_or_admin),
):
    """Mark a supervision completed and push next-due to the cadence row."""
    _validate_enum(payload.outcome, SUPERVISION_OUTCOMES, "outcome")
    db = get_db()
    record = await db.supervisions.find_one({"id": supervision_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Supervision not found")
    if record.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Supervision already completed")
    if record.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot complete a cancelled supervision")

    from governance.guards import _guard_employee_not_applicant
    await _guard_employee_not_applicant(record["employee_id"], db=db)

    try:
        completed_dt = datetime.fromisoformat(
            payload.completed_at.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid completed_at (must be ISO-8601)")

    frequency = SUPERVISION_CADENCE.get(record["supervision_type"], "ad_hoc")
    next_due_at = calculate_next_due_date(completed_dt, frequency)

    actions_dicts = [a.model_dump() if hasattr(a, "model_dump") else a.dict() for a in payload.actions]

    stamp_update(
        record, user,
        action="complete_supervision",
        from_=record.get("status"),
        to="completed",
        outcome=payload.outcome,
        notes=payload.notes,
        actions=actions_dicts,
    )
    update_fields = {
        "status": "completed",
        "completed_at": payload.completed_at,
        "outcome": payload.outcome,
        "summary": payload.summary if payload.summary is not None else record.get("summary"),
        "notes": payload.notes if payload.notes is not None else record.get("notes"),
        "actions": actions_dicts,
        "next_due_at": next_due_at,
        "updated_at": record["updated_at"],
        "updated_by": record["updated_by"],
        "audit_trail": record["audit_trail"],
    }
    record.update(update_fields)
    await db.supervisions.update_one({"id": supervision_id}, {"$set": update_fields})

    # Update cadence row so the engine owns the next cycle.
    rc_id = record.get("recurring_compliance_id")
    cadence_patch = {
        "last_completed_date": payload.completed_at,
        "next_due_date": next_due_at,
        "reminders_sent": [],
        "escalation_sent": False,
        "updated_at": _now_iso(),
    }
    if rc_id:
        await db.recurring_compliance.update_one({"id": rc_id}, {"$set": cadence_patch})
    return record


@router.post("/supervisions/{supervision_id}/cancel")
async def cancel_supervision(
    supervision_id: str,
    payload: SupervisionCancel,
    user: dict = Depends(require_manager_or_admin),
):
    """Cancel a scheduled supervision.  Cadence row is NOT deactivated —
    cancelling one occurrence must not silently clear the required cadence.
    A replacement scheduled_at can be set via PATCH on a fresh row.
    """
    db = get_db()
    record = await db.supervisions.find_one({"id": supervision_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Supervision not found")
    if record.get("status") in ("completed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel supervision in status '{record['status']}'",
        )

    from governance.guards import _guard_employee_not_applicant
    await _guard_employee_not_applicant(record["employee_id"], db=db)

    stamp_update(
        record, user,
        action="cancel_supervision",
        from_=record.get("status"),
        to="cancelled",
        reason=payload.reason,
    )
    update_fields = {
        "status": "cancelled",
        "cancelled_reason": payload.reason,
        "updated_at": record["updated_at"],
        "updated_by": record["updated_by"],
        "audit_trail": record["audit_trail"],
    }
    record.update(update_fields)
    await db.supervisions.update_one({"id": supervision_id}, {"$set": update_fields})
    # Cadence row deliberately left active — see module docstring.
    return record
