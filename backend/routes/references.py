"""
References Management Routes Module

This module handles employee reference-related endpoints including:
- Reference CRUD operations
- Reference verification (simple verification - see server.py for ReferenceIntegrityService)
- Reference status tracking

Note: Advanced integrity checks and mismatch handling are in server.py using ReferenceIntegrityService.
Those will be migrated here in a future refactoring phase.

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, EmailStr

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["References Management"])


# ==================== MODELS ====================

class ReferenceCreate(BaseModel):
    referee_name: str
    referee_email: EmailStr
    referee_phone: Optional[str] = None
    referee_organisation: Optional[str] = None
    referee_job_title: Optional[str] = None
    referee_relationship: Optional[str] = None
    is_professional: bool = True
    years_known: Optional[int] = None


class ReferenceUpdate(BaseModel):
    referee_name: Optional[str] = None
    referee_email: Optional[EmailStr] = None
    referee_phone: Optional[str] = None
    referee_organisation: Optional[str] = None
    referee_job_title: Optional[str] = None
    referee_relationship: Optional[str] = None


# ==================== REFERENCE CRUD ====================

@router.get("/references/{employee_id}")
async def get_references_for_employee(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get all references for an employee from the references collection.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get from db.references collection
    refs = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    
    # Get from employee_references collection (alternative storage)
    emp_refs = await db.employee_references.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).to_list(10)
    
    result = {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "references_collection": refs,
        "employee_references_collection": emp_refs,
        "reference_1": {},
        "reference_2": {}
    }
    
    # Build reference_1 from various sources
    for ref_num in [1, 2]:
        ref_key = f"reference_{ref_num}"
        ref_data = {}
        
        # From references collection
        if refs:
            coll_ref = refs.get(f"ref{ref_num}") or {}
            if coll_ref:
                ref_data.update({
                    "declared": coll_ref.get("declared") or {},
                    "request": coll_ref.get("request") or {},
                    "response": coll_ref.get("response") or {},
                    "verification_status": coll_ref.get("verification_status", "pending"),
                    "verified": coll_ref.get("verification_status") == "verified"
                })
        
        # From employee_references collection
        emp_ref = next((r for r in emp_refs if r.get("reference_number") == ref_num), None)
        if emp_ref:
            ref_data["employee_reference"] = {
                "referee_name": emp_ref.get("referee_name"),
                "referee_email": emp_ref.get("referee_email"),
                "referee_phone": emp_ref.get("referee_phone"),
                "referee_organisation": emp_ref.get("referee_organisation"),
                "status": emp_ref.get("status"),
                "created_at": emp_ref.get("created_at")
            }
        
        # From employee record itself
        ref_data["employee_fields"] = {
            "name": employee.get(f"reference_{ref_num}_name"),
            "email": employee.get(f"reference_{ref_num}_email"),
            "phone": employee.get(f"reference_{ref_num}_phone"),
            "company": employee.get(f"reference_{ref_num}_company"),
            "verified": employee.get(f"reference_{ref_num}_verified", False),
            "request_status": employee.get(f"reference_{ref_num}_request_status")
        }
        
        result[ref_key] = ref_data
    
    return result


@router.post("/references/{employee_id}/{ref_num}/create")
async def create_reference(
    employee_id: str,
    ref_num: int,
    reference: ReferenceCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """LEGACY: Not used by current frontend. Use add_referee_details in server.py instead."""
    raise HTTPException(
        status_code=409,
        detail=(
            "Legacy reference create endpoint is disabled. "
            "Use POST /employees/{employee_id}/references/{ref_num} instead."
        )
    )


@router.put("/references/{employee_id}/{ref_num}/update")
async def update_reference(
    employee_id: str,
    ref_num: int,
    reference: ReferenceUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """LEGACY: Not used by current frontend. Use change_referee_details in server.py instead."""
    raise HTTPException(
        status_code=409,
        detail=(
            "Legacy reference update endpoint is disabled. "
            "Use POST /references/{employee_id}/{ref_num}/change-referee instead."
        )
    )


# ==================== REFERENCE VERIFICATION (Simple) ====================

@router.post("/references/{employee_id}/{ref_num}/verify")
async def verify_reference(
    employee_id: str,
    ref_num: int,
    notes: Optional[str] = Body(None, embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """
    LEGACY: Not used by current frontend. Use verify_or_reject_reference
    in referee_outreach.py or verify_reference in server.py instead.
    """
    raise HTTPException(
        status_code=409,
        detail=(
            "Legacy reference verify endpoint is disabled. "
            "Use the canonical employee reference lifecycle verification flow instead."
        )
    )


# ==================== REFERENCE STATUS ====================

@router.get("/references/{employee_id}/status")
async def get_references_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get overall reference status for an employee."""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    refs = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    
    statuses = []
    for ref_num in [1, 2]:
        ref_key = f"ref{ref_num}"
        ref_data = (refs.get(ref_key) or {}) if refs else {}
        
        has_declared = bool((ref_data.get("declared") or {}).get("name") or employee.get(f"reference_{ref_num}_name"))
        has_request = bool((ref_data.get("request") or {}).get("sent_at") or employee.get(f"reference_{ref_num}_request_status") == "sent")
        has_response = bool(ref_data.get("response") or employee.get(f"reference_{ref_num}_response_data"))
        is_verified = ref_data.get("verification_status") == "verified" or employee.get(f"reference_{ref_num}_verified", False)
        is_rejected = ref_data.get("verification_status") == "rejected" or employee.get(f"reference_{ref_num}_rejected", False)
        
        if is_verified:
            status = "verified"
        elif is_rejected:
            status = "rejected"
        elif has_response:
            status = "response_received"
        elif has_request:
            status = "request_sent"
        elif has_declared:
            status = "declared"
        else:
            status = "not_started"
        
        statuses.append({
            "reference_number": ref_num,
            "status": status,
            "has_declared": has_declared,
            "has_request": has_request,
            "has_response": has_response,
            "is_verified": is_verified,
            "is_rejected": is_rejected
        })
    
    # Overall status
    all_verified = all(s["is_verified"] for s in statuses)
    any_rejected = any(s["is_rejected"] for s in statuses)
    
    return {
        "employee_id": employee_id,
        "references": statuses,
        "all_verified": all_verified,
        "any_rejected": any_rejected,
        "overall_status": "complete" if all_verified else ("rejected" if any_rejected else "incomplete")
    }


# ==================== ADMIN DRIFT REPORT (READ-ONLY) ====================

def _norm_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_verified_from_status(value: Optional[str]) -> bool:
    return _norm_text(value) == "verified"


@router.get("/admin/references/drift-report")
async def get_references_drift_report(
    employee_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    only_drifted: bool = True,
    user: dict = Depends(require_admin)
):
    """
    Admin-only read-only drift visibility for the three reference stores.

    Compares per reference slot:
    - employees flat reference fields
    - references collection declared/verification fields
    - employee_references collection
    """
    db = get_db()

    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    employee_query = {"id": employee_id} if employee_id else {}
    employees = await db.employees.find(
        employee_query,
        {
            "_id": 0,
            "id": 1,
            "first_name": 1,
            "last_name": 1,
            "reference_1_name": 1,
            "reference_1_email": 1,
            "reference_1_company": 1,
            "reference_1_verified": 1,
            "reference_2_name": 1,
            "reference_2_email": 1,
            "reference_2_company": 1,
            "reference_2_verified": 1,
        },
    ).sort("updated_at", -1).skip(offset).limit(limit).to_list(limit)

    if employee_id and not employees:
        raise HTTPException(status_code=404, detail="Employee not found")

    report_rows = []
    total_slots_checked = 0
    total_slot_mismatches = 0

    for emp in employees:
        emp_id = emp.get("id")
        refs_doc = await db.references.find_one({"employee_id": emp_id}, {"_id": 0})
        emp_refs = await db.employee_references.find(
            {"employee_id": emp_id},
            {
                "_id": 0,
                "reference_number": 1,
                "referee_name": 1,
                "referee_email": 1,
                "referee_organisation": 1,
                "status": 1,
            },
        ).to_list(10)

        by_num = {r.get("reference_number"): r for r in emp_refs if r.get("reference_number") in [1, 2]}
        employee_slot_results = {}
        employee_mismatches = 0

        for ref_num in [1, 2]:
            total_slots_checked += 1
            ref_key = f"ref{ref_num}"
            refs_ref = (refs_doc or {}).get(ref_key) or {}
            declared = refs_ref.get("declared") or {}
            emp_ref = by_num.get(ref_num) or {}

            employees_name = _norm_text(emp.get(f"reference_{ref_num}_name"))
            employees_email = _norm_text(emp.get(f"reference_{ref_num}_email"))
            employees_org = _norm_text(emp.get(f"reference_{ref_num}_company"))
            employees_verified = bool(emp.get(f"reference_{ref_num}_verified", False))

            references_name = _norm_text(declared.get("name"))
            references_email = _norm_text(declared.get("email"))
            references_org = _norm_text(declared.get("organisation"))
            references_verified = _is_verified_from_status(refs_ref.get("verification_status"))

            emp_refs_name = _norm_text(emp_ref.get("referee_name"))
            emp_refs_email = _norm_text(emp_ref.get("referee_email"))
            emp_refs_org = _norm_text(emp_ref.get("referee_organisation"))
            emp_refs_verified = _is_verified_from_status(emp_ref.get("status"))

            field_mismatches = []
            if len({employees_name, references_name, emp_refs_name} - {""}) > 1:
                field_mismatches.append("name")
            if len({employees_email, references_email, emp_refs_email} - {""}) > 1:
                field_mismatches.append("email")
            if len({employees_org, references_org, emp_refs_org} - {""}) > 1:
                field_mismatches.append("organisation")
            if len({employees_verified, references_verified, emp_refs_verified}) > 1:
                field_mismatches.append("verified_status")

            slot_mismatch_count = len(field_mismatches)
            total_slot_mismatches += slot_mismatch_count
            employee_mismatches += slot_mismatch_count

            employee_slot_results[f"reference_{ref_num}"] = {
                "mismatch_fields": field_mismatches,
                "employees": {
                    "name": emp.get(f"reference_{ref_num}_name"),
                    "email": emp.get(f"reference_{ref_num}_email"),
                    "organisation": emp.get(f"reference_{ref_num}_company"),
                    "verified": employees_verified,
                },
                "references": {
                    "name": declared.get("name"),
                    "email": declared.get("email"),
                    "organisation": declared.get("organisation"),
                    "verified": references_verified,
                    "verification_status": refs_ref.get("verification_status"),
                },
                "employee_references": {
                    "name": emp_ref.get("referee_name"),
                    "email": emp_ref.get("referee_email"),
                    "organisation": emp_ref.get("referee_organisation"),
                    "verified": emp_refs_verified,
                    "status": emp_ref.get("status"),
                },
            }

        row = {
            "employee_id": emp_id,
            "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "mismatch_count": employee_mismatches,
            "has_drift": employee_mismatches > 0,
            "references": employee_slot_results,
        }

        if not only_drifted or row["has_drift"]:
            report_rows.append(row)

    return {
        "report": "references_drift",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {"employee_id": employee_id, "offset": offset, "limit": limit, "only_drifted": only_drifted},
        "summary": {
            "employees_checked": len(employees),
            "employees_with_drift": sum(1 for r in report_rows if r.get("has_drift")),
            "reference_slots_checked": total_slots_checked,
            "slot_mismatch_count": total_slot_mismatches,
        },
        "results": report_rows,
    }
