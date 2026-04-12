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
    """Create or update a reference for an employee."""
    db = get_db()
    
    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee record with reference info
    update_fields = {
        f"reference_{ref_num}_name": reference.referee_name,
        f"reference_{ref_num}_email": reference.referee_email,
        f"reference_{ref_num}_phone": reference.referee_phone,
        f"reference_{ref_num}_company": reference.referee_organisation,
        f"reference_{ref_num}_job_title": reference.referee_job_title,
        f"reference_{ref_num}_relationship": reference.referee_relationship,
        f"reference_{ref_num}_is_professional": reference.is_professional,
        f"reference_{ref_num}_years_known": reference.years_known,
        "updated_at": now
    }
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": update_fields}
    )
    
    # Also update references collection
    ref_key = f"ref{ref_num}"
    declared_data = {
        "name": reference.referee_name,
        "email": reference.referee_email,
        "phone": reference.referee_phone,
        "organisation": reference.referee_organisation,
        "job_title": reference.referee_job_title,
        "relationship": reference.referee_relationship,
        "is_professional": reference.is_professional,
        "years_known": reference.years_known,
        "created_at": now,
        "created_by": user.get("user_id")
    }
    
    await db.references.update_one(
        {"employee_id": employee_id},
        {
            "$set": {
                f"{ref_key}.declared": declared_data,
                f"{ref_key}.updated_at": now,
                "updated_at": now
            },
            "$setOnInsert": {
                "employee_id": employee_id,
                "created_at": now
            }
        },
        upsert=True
    )
    
    # Also update employee_references collection
    await db.employee_references.update_one(
        {"employee_id": employee_id, "reference_number": ref_num},
        {
            "$set": {
                "referee_name": reference.referee_name,
                "referee_email": reference.referee_email,
                "referee_phone": reference.referee_phone,
                "referee_organisation": reference.referee_organisation,
                "referee_position": reference.referee_job_title,
                "referee_relationship": reference.referee_relationship,
                "status": "pending",
                "updated_at": now,
                "source": "admin_entry"
            },
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "reference_number": ref_num,
                "created_at": now
            }
        },
        upsert=True
    )
    
    await log_audit_action(
        user['user_id'],
        "create_reference",
        "reference",
        f"{employee_id}_ref_{ref_num}",
        {"referee_name": reference.referee_name, "referee_email": reference.referee_email}
    )
    
    return {"success": True, "message": f"Reference {ref_num} created/updated"}


@router.put("/references/{employee_id}/{ref_num}/update")
async def update_reference(
    employee_id: str,
    ref_num: int,
    reference: ReferenceUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update an existing reference."""
    db = get_db()
    
    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Build update fields
    update_fields = {"updated_at": now}
    ref_updates = {}
    
    if reference.referee_name:
        update_fields[f"reference_{ref_num}_name"] = reference.referee_name
        ref_updates["name"] = reference.referee_name
    if reference.referee_email:
        update_fields[f"reference_{ref_num}_email"] = reference.referee_email
        ref_updates["email"] = reference.referee_email
    if reference.referee_phone:
        update_fields[f"reference_{ref_num}_phone"] = reference.referee_phone
        ref_updates["phone"] = reference.referee_phone
    if reference.referee_organisation:
        update_fields[f"reference_{ref_num}_company"] = reference.referee_organisation
        ref_updates["organisation"] = reference.referee_organisation
    if reference.referee_job_title:
        update_fields[f"reference_{ref_num}_job_title"] = reference.referee_job_title
        ref_updates["job_title"] = reference.referee_job_title
    if reference.referee_relationship:
        update_fields[f"reference_{ref_num}_relationship"] = reference.referee_relationship
        ref_updates["relationship"] = reference.referee_relationship
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_fields})
    
    # Update references collection
    if ref_updates:
        ref_key = f"ref{ref_num}"
        for k, v in ref_updates.items():
            await db.references.update_one(
                {"employee_id": employee_id},
                {"$set": {f"{ref_key}.declared.{k}": v, "updated_at": now}}
            )
    
    await log_audit_action(
        user['user_id'],
        "update_reference",
        "reference",
        f"{employee_id}_ref_{ref_num}",
        ref_updates
    )
    
    return {"success": True, "message": f"Reference {ref_num} updated"}


# ==================== REFERENCE VERIFICATION (Simple) ====================

@router.post("/references/{employee_id}/{ref_num}/verify")
async def verify_reference(
    employee_id: str,
    ref_num: int,
    notes: Optional[str] = Body(None, embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Simple reference verification.
    
    Note: For integrity-based verification with mismatch handling,
    use the endpoints in server.py that leverage ReferenceIntegrityService.
    """
    db = get_db()
    
    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee record
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                f"reference_{ref_num}_verified": True,
                f"reference_{ref_num}_verified_by": user.get("user_id"),
                f"reference_{ref_num}_verified_at": now,
                f"reference_{ref_num}_verification_notes": notes,
                "updated_at": now
            }
        }
    )
    
    # Update references collection
    ref_key = f"ref{ref_num}"
    await db.references.update_one(
        {"employee_id": employee_id},
        {
            "$set": {
                f"{ref_key}.verification_status": "verified",
                f"{ref_key}.verified_by": user.get("user_id"),
                f"{ref_key}.verified_at": now,
                f"{ref_key}.verification_notes": notes,
                "updated_at": now
            }
        }
    )
    
    # Update employee_references collection
    await db.employee_references.update_one(
        {"employee_id": employee_id, "reference_number": ref_num},
        {
            "$set": {
                "status": "verified",
                "verified_by": user.get("user_id"),
                "verified_at": now,
                "verification_notes": notes,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "verify_reference",
        "reference",
        f"{employee_id}_ref_{ref_num}",
        {"notes": notes}
    )
    
    return {"success": True, "message": f"Reference {ref_num} verified"}


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
