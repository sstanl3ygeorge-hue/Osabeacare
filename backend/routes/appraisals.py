"""
Minimal appraisal evidence routes.

This module intentionally adds only lightweight appraisal records and reuses
existing employee profile/compliance patterns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .dependencies import get_db, get_current_user, require_manager_or_admin, log_audit_action

router = APIRouter(tags=["Appraisals"])


class AppraisalCreate(BaseModel):
    appraisal_date: str
    reviewer: str
    notes: Optional[str] = None
    actions: Optional[List[str]] = None
    next_due_at: Optional[str] = None


@router.get("/employees/{employee_id}/appraisals")
async def list_employee_appraisals(
    employee_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    rows = await db.appraisal_records.find(
        {"employee_id": employee_id},
        {"_id": 0},
    ).sort("appraisal_date", -1).to_list(200)

    return {"items": rows}


@router.post("/employees/{employee_id}/appraisals")
async def create_employee_appraisal(
    employee_id: str,
    payload: AppraisalCreate,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()

    employee = await db.employees.find_one(
        {"id": employee_id},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1},
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    now = datetime.now(timezone.utc).isoformat()
    record_id = str(uuid.uuid4())
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()

    record = {
        "id": record_id,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "appraisal_date": payload.appraisal_date,
        "reviewer": payload.reviewer,
        "notes": payload.notes,
        "actions": payload.actions or [],
        "next_due_at": payload.next_due_at,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("user_id"),
    }

    await db.appraisal_records.insert_one(record)

    await log_audit_action(
        user.get("user_id"),
        "create_appraisal_record",
        "appraisal_record",
        record_id,
        {
            "employee_id": employee_id,
            "appraisal_date": payload.appraisal_date,
            "next_due_at": payload.next_due_at,
        },
    )

    return {"success": True, "id": record_id}
