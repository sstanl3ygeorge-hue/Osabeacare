"""
Shift + Assignment MVP routes.

MVP constraints:
- Exactly one ACTIVE worker assignment per shift
- service_user_id is optional
- location_text and role_required are required
- only active employees are shift-eligible
- overlap prevention required
- audit logging on all mutations
- no availability or recurrence engine in this module
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from .dependencies import (
    get_db,
    require_manager_or_admin,
    get_current_worker,
    log_audit_action,
)

router = APIRouter(tags=["Shifts"])


SHIFT_STATUSES = {"open", "assigned", "completed", "cancelled"}
ASSIGNMENT_STATUSES = {"active", "completed", "cancelled"}
SHIFT_TRANSITIONS = {
    "open": {"assigned", "cancelled"},
    "assigned": {"open", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class ShiftCreateRequest(BaseModel):
    start_at: str
    end_at: str
    location_text: str = Field(..., min_length=2)
    role_required: str = Field(..., min_length=2)
    service_user_id: Optional[str] = None
    notes: Optional[str] = None


class ShiftUpdateRequest(BaseModel):
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    location_text: Optional[str] = Field(default=None, min_length=2)
    role_required: Optional[str] = Field(default=None, min_length=2)
    service_user_id: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    cancel_reason: Optional[str] = None


class AssignWorkerRequest(BaseModel):
    employee_id: str
    notes: Optional[str] = None


class UnassignWorkerRequest(BaseModel):
    reason: Optional[str] = None


class WorkerShiftResponseRequest(BaseModel):
    note: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_required_text(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if len(text) < 2:
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    return text


def _parse_iso(value: str, field_name: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid ISO datetime for {field_name}")


def _ensure_valid_window(start_at: str, end_at: str) -> tuple[datetime, datetime]:
    start_dt = _parse_iso(start_at, "start_at")
    end_dt = _parse_iso(end_at, "end_at")
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    return start_dt, end_dt


def _intervals_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


async def _get_shift_or_404(shift_id: str) -> Dict[str, Any]:
    db = get_db()
    shift = await db.shifts.find_one({"id": shift_id}, {"_id": 0})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


def _assert_transition(current_status: str, next_status: str):
    if current_status == next_status:
        return
    allowed = SHIFT_TRANSITIONS.get(current_status, set())
    if next_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid shift status transition: {current_status} -> {next_status}",
        )


async def _get_active_assignment_for_shift(shift_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    return await db.shift_assignments.find_one(
        {"shift_id": shift_id, "status": "active"},
        {"_id": 0}
    )


async def _get_latest_assignment_for_shift(shift_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    items = await db.shift_assignments.find(
        {"shift_id": shift_id},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(1)
    return items[0] if items else None


async def _require_active_worker_employee(worker: dict, db) -> str:
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to worker account")
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "status": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.get("status") != "active":
        raise HTTPException(status_code=403, detail="Shift access is only available for active employees")
    return employee_id


async def _assert_employee_is_active(employee_id: str):
    db = get_db()
    employee = await db.employees.find_one(
        {"id": employee_id},
        {"_id": 0, "id": 1, "status": 1, "first_name": 1, "last_name": 1}
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.get("status") != "active":
        raise HTTPException(status_code=409, detail="Only active employees are shift-eligible")
    return employee


async def _assert_no_overlap_for_employee(
    employee_id: str,
    start_dt: datetime,
    end_dt: datetime,
    *,
    exclude_shift_id: Optional[str] = None,
):
    db = get_db()
    active_assignments = await db.shift_assignments.find(
        {"employee_id": employee_id, "status": "active"},
        {"_id": 0}
    ).to_list(500)

    for assignment in active_assignments:
        if exclude_shift_id and assignment.get("shift_id") == exclude_shift_id:
            continue
        existing_start_raw = assignment.get("shift_start_at")
        existing_end_raw = assignment.get("shift_end_at")
        if not existing_start_raw or not existing_end_raw:
            shift = await db.shifts.find_one({"id": assignment.get("shift_id")}, {"_id": 0, "start_at": 1, "end_at": 1})
            if not shift:
                continue
            existing_start_raw = shift.get("start_at")
            existing_end_raw = shift.get("end_at")
        existing_start = _parse_iso(existing_start_raw, "existing_shift_start_at")
        existing_end = _parse_iso(existing_end_raw, "existing_shift_end_at")
        if _intervals_overlap(start_dt, end_dt, existing_start, existing_end):
            raise HTTPException(
                status_code=409,
                detail="Employee already has an overlapping active shift assignment",
            )


@router.post("/shifts")
async def create_shift(
    payload: ShiftCreateRequest,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    start_dt, end_dt = _ensure_valid_window(payload.start_at, payload.end_at)
    now = _now_iso()
    shift_id = str(uuid.uuid4())

    shift_doc = {
        "id": shift_id,
        "start_at": start_dt.isoformat(),
        "end_at": end_dt.isoformat(),
        "location_text": _normalize_required_text(payload.location_text, "location_text"),
        "role_required": _normalize_required_text(payload.role_required, "role_required"),
        "service_user_id": payload.service_user_id,
        "notes": payload.notes,
        "status": "open",
        "assigned_employee_id": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("user_id"),
        "updated_by": user.get("user_id"),
    }
    await db.shifts.insert_one(shift_doc)
    await log_audit_action(
        user.get("user_id"),
        "shift_created",
        "shift",
        shift_id,
        {
            "start_at": shift_doc["start_at"],
            "end_at": shift_doc["end_at"],
            "location_text": shift_doc["location_text"],
            "role_required": shift_doc["role_required"],
        },
    )
    return {"success": True, "shift": shift_doc}


@router.get("/shifts")
async def list_shifts(
    status: Optional[str] = Query(default=None),
    from_at: Optional[str] = Query(default=None),
    to_at: Optional[str] = Query(default=None),
    service_user_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    query: Dict[str, Any] = {}
    if status:
        if status not in SHIFT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        query["status"] = status
    if from_at:
        _parse_iso(from_at, "from_at")
        query.setdefault("end_at", {})
        query["end_at"]["$gte"] = from_at
    if to_at:
        _parse_iso(to_at, "to_at")
        query.setdefault("start_at", {})
        query["start_at"]["$lte"] = to_at
    if service_user_id:
        query["service_user_id"] = service_user_id

    shifts = await db.shifts.find(query, {"_id": 0}).sort("start_at", 1).to_list(500)
    shift_ids = [shift.get("id") for shift in shifts if shift.get("id")]
    latest_by_shift_id: Dict[str, Dict[str, Any]] = {}
    if shift_ids:
        assignments = await db.shift_assignments.find(
            {"shift_id": {"$in": shift_ids}},
            {"_id": 0}
        ).sort("updated_at", -1).to_list(2000)
        for assignment in assignments:
            sid = assignment.get("shift_id")
            if sid and sid not in latest_by_shift_id:
                latest_by_shift_id[sid] = assignment
    for shift in shifts:
        shift["latest_assignment"] = latest_by_shift_id.get(shift.get("id"))
    return {"shifts": shifts, "total": len(shifts)}


@router.get("/shifts/{shift_id}")
async def get_shift(
    shift_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    shift = await _get_shift_or_404(shift_id)
    assignment = await _get_active_assignment_for_shift(shift_id)
    latest_assignment = await _get_latest_assignment_for_shift(shift_id)
    return {"shift": shift, "active_assignment": assignment, "latest_assignment": latest_assignment}


@router.patch("/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    payload: ShiftUpdateRequest,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    shift = await _get_shift_or_404(shift_id)
    update: Dict[str, Any] = {}
    assignment_old_status: Optional[str] = None
    assignment_new_status: Optional[str] = None

    next_status = payload.status or shift.get("status")
    if payload.status:
        if payload.status not in SHIFT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid shift status")
        _assert_transition(shift.get("status"), payload.status)
        update["status"] = payload.status

    next_start = payload.start_at or shift.get("start_at")
    next_end = payload.end_at or shift.get("end_at")
    start_dt, end_dt = _ensure_valid_window(next_start, next_end)

    active_assignment = await _get_active_assignment_for_shift(shift_id)
    if active_assignment and (payload.start_at is not None or payload.end_at is not None):
        raise HTTPException(
            status_code=409,
            detail="Cannot change shift time while an active assignment exists. Unassign first.",
        )

    if payload.start_at is not None:
        update["start_at"] = start_dt.isoformat()
    if payload.end_at is not None:
        update["end_at"] = end_dt.isoformat()
    if payload.location_text is not None:
        update["location_text"] = _normalize_required_text(payload.location_text, "location_text")
    if payload.role_required is not None:
        update["role_required"] = _normalize_required_text(payload.role_required, "role_required")
    if payload.service_user_id is not None:
        update["service_user_id"] = payload.service_user_id
    if payload.notes is not None:
        update["notes"] = payload.notes

    if update.get("status") == "open":
        # Guard: "open" means no active assignment.
        if active_assignment:
            raise HTTPException(status_code=409, detail="Cannot set shift to open while assignment is active")
        update["assigned_employee_id"] = None
    if update.get("status") == "cancelled":
        cancel_reason = (payload.cancel_reason or "").strip()
        if len(cancel_reason) < 3:
            raise HTTPException(status_code=400, detail="cancel_reason must be at least 3 characters")
        update["cancelled_reason"] = cancel_reason
        update["cancelled_at"] = _now_iso()
        update["cancelled_by"] = user.get("user_id")

    if update.get("status") in {"completed", "cancelled"} and active_assignment:
        assignment_status = "completed" if update["status"] == "completed" else "cancelled"
        assignment_old_status = active_assignment.get("status")
        assignment_new_status = assignment_status
        assignment_update = {"status": assignment_status, "updated_at": _now_iso(), "ended_at": _now_iso(), "ended_by": user.get("user_id")}
        if assignment_status == "cancelled" and update.get("cancelled_reason"):
            assignment_update["unassign_reason"] = update.get("cancelled_reason")
        await db.shift_assignments.update_one(
            {"id": active_assignment["id"]},
            {"$set": assignment_update},
        )
        update["assigned_employee_id"] = None

    if not update:
        return {"success": True, "shift": shift, "message": "No changes applied"}

    update["updated_at"] = _now_iso()
    update["updated_by"] = user.get("user_id")
    await db.shifts.update_one({"id": shift_id}, {"$set": update})
    updated = await _get_shift_or_404(shift_id)

    audit_action = "shift_updated"
    if update.get("status") == "cancelled":
        audit_action = "shift_cancelled"
    elif update.get("status") == "completed":
        audit_action = "shift_completed"

    await log_audit_action(
        user.get("user_id"),
        audit_action,
        "shift",
        shift_id,
        {
            "changes": update,
            "old_status": shift.get("status"),
            "new_status": updated.get("status"),
            "old_assigned_employee_id": shift.get("assigned_employee_id"),
            "new_assigned_employee_id": updated.get("assigned_employee_id"),
            "old_assignment_status": assignment_old_status,
            "new_assignment_status": assignment_new_status,
        },
    )
    return {"success": True, "shift": updated}


@router.post("/shifts/{shift_id}/assign")
async def assign_worker_to_shift(
    shift_id: str,
    payload: AssignWorkerRequest,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    shift = await _get_shift_or_404(shift_id)
    if shift.get("status") in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Cannot assign worker to completed/cancelled shift")

    existing_assignment = await _get_active_assignment_for_shift(shift_id)
    if existing_assignment:
        raise HTTPException(status_code=409, detail="Shift already has an active worker assignment")

    employee = await _assert_employee_is_active(payload.employee_id)
    start_dt = _parse_iso(shift.get("start_at"), "shift.start_at")
    end_dt = _parse_iso(shift.get("end_at"), "shift.end_at")
    await _assert_no_overlap_for_employee(payload.employee_id, start_dt, end_dt, exclude_shift_id=shift_id)

    now = _now_iso()
    assignment_id = str(uuid.uuid4())
    assignment_doc = {
        "id": assignment_id,
        "shift_id": shift_id,
        "employee_id": payload.employee_id,
        "status": "active",
        "assigned_at": now,
        "assigned_by": user.get("user_id"),
        "notes": payload.notes,
        # Snapshot for overlap checks / audit trace
        "shift_start_at": shift.get("start_at"),
        "shift_end_at": shift.get("end_at"),
        "location_text": shift.get("location_text"),
        "role_required": shift.get("role_required"),
        "service_user_id": shift.get("service_user_id"),
        "created_at": now,
        "updated_at": now,
        "worker_response_status": "pending",
        "worker_response_note": None,
        "worker_responded_at": None,
    }
    await db.shift_assignments.insert_one(assignment_doc)
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {"status": "assigned", "assigned_employee_id": payload.employee_id, "updated_at": now, "updated_by": user.get("user_id")}},
    )
    updated_shift = await _get_shift_or_404(shift_id)
    await log_audit_action(
        user.get("user_id"),
        "shift_assignment_created",
        "shift_assignment",
        assignment_id,
        {
            "shift_id": shift_id,
            "employee_id": payload.employee_id,
            "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            "old_shift_status": shift.get("status"),
            "new_shift_status": "assigned",
            "old_assignment_status": None,
            "new_assignment_status": "active",
        },
    )
    return {"success": True, "shift": updated_shift, "assignment": assignment_doc}


@router.post("/shifts/{shift_id}/unassign")
async def unassign_worker_from_shift(
    shift_id: str,
    payload: UnassignWorkerRequest,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    shift = await _get_shift_or_404(shift_id)
    assignment = await _get_active_assignment_for_shift(shift_id)
    if not assignment:
        raise HTTPException(status_code=409, detail="Shift has no active assignment to remove")
    if shift.get("status") in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Cannot unassign from completed/cancelled shift")

    now = _now_iso()
    await db.shift_assignments.update_one(
        {"id": assignment["id"]},
        {"$set": {"status": "cancelled", "ended_at": now, "ended_by": user.get("user_id"), "unassign_reason": payload.reason, "updated_at": now}},
    )
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {"status": "open", "assigned_employee_id": None, "updated_at": now, "updated_by": user.get("user_id")}},
    )
    updated_shift = await _get_shift_or_404(shift_id)
    await log_audit_action(
        user.get("user_id"),
        "shift_assignment_cancelled",
        "shift_assignment",
        assignment["id"],
        {
            "shift_id": shift_id,
            "reason": payload.reason,
            "old_shift_status": shift.get("status"),
            "new_shift_status": "open",
            "old_assignment_status": assignment.get("status"),
            "new_assignment_status": "cancelled",
        },
    )
    return {"success": True, "shift": updated_shift}


@router.post("/shifts/{shift_id}/complete")
async def complete_shift(
    shift_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    shift = await _get_shift_or_404(shift_id)
    if shift.get("status") == "completed":
        return {"success": True, "shift": shift, "message": "Shift already completed"}
    if shift.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled shifts cannot be completed")
    if shift.get("status") == "open":
        raise HTTPException(status_code=409, detail="Cannot complete unassigned shift")
    if shift.get("status") != "assigned":
        raise HTTPException(status_code=409, detail="Shift cannot be completed from its current status")

    assignment = await _get_active_assignment_for_shift(shift_id)
    if not assignment:
        raise HTTPException(status_code=409, detail="Cannot complete shift without an active assignment")

    now = _now_iso()
    await db.shift_assignments.update_one(
        {"id": assignment["id"]},
        {"$set": {"status": "completed", "ended_at": now, "ended_by": user.get("user_id"), "updated_at": now}},
    )

    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {"status": "completed", "assigned_employee_id": None, "updated_at": now, "updated_by": user.get("user_id")}},
    )
    updated_shift = await _get_shift_or_404(shift_id)
    await log_audit_action(
        user.get("user_id"),
        "shift_completed",
        "shift",
        shift_id,
        {
            "had_active_assignment": True,
            "old_shift_status": shift.get("status"),
            "new_shift_status": "completed",
            "old_assignment_status": assignment.get("status"),
            "new_assignment_status": "completed",
        },
    )
    return {"success": True, "shift": updated_shift}


@router.get("/worker/shifts")
async def list_worker_shifts(
    include_completed: bool = Query(default=False),
    worker: dict = Depends(get_current_worker),
):
    db = get_db()
    employee_id = await _require_active_worker_employee(worker, db)

    assignment_statuses = ["active"] if not include_completed else ["active", "completed", "cancelled"]
    assignments = await db.shift_assignments.find(
        {"employee_id": employee_id, "status": {"$in": assignment_statuses}},
        {"_id": 0}
    ).sort("shift_start_at", 1).to_list(500)

    shift_ids = [a.get("shift_id") for a in assignments if a.get("shift_id")]
    shifts = []
    if shift_ids:
        shifts = await db.shifts.find({"id": {"$in": shift_ids}}, {"_id": 0}).to_list(500)
    shifts_by_id = {s.get("id"): s for s in shifts}

    result = []
    for assignment in assignments:
        shift = shifts_by_id.get(assignment.get("shift_id"))
        if not shift:
            continue
        cancellation_reason = assignment.get("unassign_reason") or shift.get("cancelled_reason")
        result.append({
            "assignment_id": assignment.get("id"),
            "assignment_status": assignment.get("status"),
            "assigned_at": assignment.get("assigned_at"),
            "worker_response_status": assignment.get("worker_response_status"),
            "worker_response_note": assignment.get("worker_response_note"),
            "worker_responded_at": assignment.get("worker_responded_at"),
            "cancellation_reason": cancellation_reason,
            "shift": shift,
        })
    return {"shifts": result, "total": len(result)}


@router.get("/worker/shifts/{shift_id}")
async def get_worker_shift(
    shift_id: str,
    worker: dict = Depends(get_current_worker),
):
    db = get_db()
    employee_id = await _require_active_worker_employee(worker, db)

    assignment = await db.shift_assignments.find_one(
        {"shift_id": shift_id, "employee_id": employee_id, "status": {"$in": ["active", "completed", "cancelled"]}},
        {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Shift not found for this worker")
    shift = await _get_shift_or_404(shift_id)
    return {"assignment": assignment, "shift": shift}


@router.post("/worker/shifts/{shift_id}/accept")
async def accept_worker_shift(
    shift_id: str,
    payload: WorkerShiftResponseRequest,
    worker: dict = Depends(get_current_worker),
):
    db = get_db()
    employee_id = await _require_active_worker_employee(worker, db)

    shift = await _get_shift_or_404(shift_id)
    if shift.get("status") in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="This shift is no longer active")

    assignment = await db.shift_assignments.find_one(
        {"shift_id": shift_id, "employee_id": employee_id, "status": "active"},
        {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Active assignment not found for this shift")

    previous_response_status = assignment.get("worker_response_status") or "pending"
    now = _now_iso()
    await db.shift_assignments.update_one(
        {"id": assignment["id"]},
        {"$set": {
            "worker_response_status": "accepted",
            "worker_response_note": payload.note,
            "worker_responded_at": now,
            "updated_at": now,
        }},
    )
    updated_assignment = await db.shift_assignments.find_one({"id": assignment["id"]}, {"_id": 0})
    await log_audit_action(
        f"worker:{employee_id}",
        "worker_shift_accepted",
        "shift_assignment",
        assignment["id"],
        {
            "shift_id": shift_id,
            "note": payload.note,
            "worker_employee_id": employee_id,
            "old_shift_status": shift.get("status"),
            "new_shift_status": shift.get("status"),
            "old_assignment_status": assignment.get("status"),
            "new_assignment_status": assignment.get("status"),
            "old_worker_response_status": previous_response_status,
            "new_worker_response_status": "accepted",
        },
    )
    return {"success": True, "assignment": updated_assignment, "shift": shift}


@router.post("/worker/shifts/{shift_id}/reject")
async def reject_worker_shift(
    shift_id: str,
    payload: WorkerShiftResponseRequest,
    worker: dict = Depends(get_current_worker),
):
    db = get_db()
    employee_id = await _require_active_worker_employee(worker, db)

    shift = await _get_shift_or_404(shift_id)
    if shift.get("status") in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="This shift is no longer active")

    assignment = await db.shift_assignments.find_one(
        {"shift_id": shift_id, "employee_id": employee_id, "status": "active"},
        {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Active assignment not found for this shift")
    if assignment.get("worker_response_status") == "accepted":
        raise HTTPException(status_code=409, detail="Accepted shifts cannot be rejected. Ask admin to unassign.")

    previous_response_status = assignment.get("worker_response_status") or "pending"
    now = _now_iso()
    await db.shift_assignments.update_one(
        {"id": assignment["id"]},
        {"$set": {
            "status": "cancelled",
            "worker_response_status": "rejected",
            "worker_response_note": payload.note,
            "worker_responded_at": now,
            "ended_at": now,
            "ended_by": f"worker:{employee_id}",
            "unassign_reason": payload.note,
            "updated_at": now,
        }},
    )
    await db.shifts.update_one(
        {"id": shift_id},
        {"$set": {
            "status": "open",
            "assigned_employee_id": None,
            "updated_at": now,
            "updated_by": f"worker:{employee_id}",
        }},
    )
    updated_shift = await _get_shift_or_404(shift_id)
    updated_assignment = await db.shift_assignments.find_one({"id": assignment["id"]}, {"_id": 0})
    await log_audit_action(
        f"worker:{employee_id}",
        "worker_shift_rejected",
        "shift_assignment",
        assignment["id"],
        {
            "shift_id": shift_id,
            "note": payload.note,
            "worker_employee_id": employee_id,
            "old_shift_status": shift.get("status"),
            "new_shift_status": "open",
            "old_assignment_status": assignment.get("status"),
            "new_assignment_status": "cancelled",
            "old_worker_response_status": previous_response_status,
            "new_worker_response_status": "rejected",
        },
    )
    return {"success": True, "assignment": updated_assignment, "shift": updated_shift}
