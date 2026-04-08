"""
References Management Routes Module

This module handles employee reference-related endpoints including:
- Reference CRUD operations
- Reference request sending
- Reference verification and integrity checks
- Mismatch handling and explanations

Extracted from server.py for modularity.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
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


class MismatchOverride(BaseModel):
    reason: str
    override_type: str  # 'accept', 'minor_discrepancy', 'explained'


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
            coll_ref = refs.get(f"ref{ref_num}", {})
            if coll_ref:
                ref_data.update({
                    "declared": coll_ref.get("declared", {}),
                    "request": coll_ref.get("request", {}),
                    "response": coll_ref.get("response", {}),
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


# ==================== REFERENCE VERIFICATION ====================

@router.post("/references/{employee_id}/{ref_num}/verify")
async def verify_reference(
    employee_id: str,
    ref_num: int,
    notes: Optional[str] = Body(None, embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """Verify a reference."""
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


@router.post("/references/{employee_id}/{ref_num}/reject")
async def reject_reference(
    employee_id: str,
    ref_num: int,
    reason: str = Body(..., embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """Reject a reference."""
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
                f"reference_{ref_num}_verified": False,
                f"reference_{ref_num}_rejected": True,
                f"reference_{ref_num}_rejected_by": user.get("user_id"),
                f"reference_{ref_num}_rejected_at": now,
                f"reference_{ref_num}_rejection_reason": reason,
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
                f"{ref_key}.verification_status": "rejected",
                f"{ref_key}.rejected_by": user.get("user_id"),
                f"{ref_key}.rejected_at": now,
                f"{ref_key}.rejection_reason": reason,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "reject_reference",
        "reference",
        f"{employee_id}_ref_{ref_num}",
        {"reason": reason}
    )
    
    return {"success": True, "message": f"Reference {ref_num} rejected"}


# ==================== REFERENCE INTEGRITY ====================

@router.get("/references/{employee_id}/{ref_num}/integrity")
async def get_reference_integrity(
    employee_id: str,
    ref_num: int,
    user: dict = Depends(get_current_user)
):
    """
    Check integrity between declared reference info and response data.
    Identifies mismatches that need attention.
    """
    db = get_db()
    
    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    refs = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    ref_key = f"ref{ref_num}"
    ref_data = refs.get(ref_key, {}) if refs else {}
    
    declared = ref_data.get("declared", {})
    response = ref_data.get("response", {})
    
    # Fallback to employee fields
    if not declared.get("name"):
        declared = {
            "name": employee.get(f"reference_{ref_num}_name"),
            "email": employee.get(f"reference_{ref_num}_email"),
            "organisation": employee.get(f"reference_{ref_num}_company"),
            "job_title": employee.get(f"reference_{ref_num}_job_title")
        }
    
    # Check for mismatches
    mismatches = []
    
    # Name mismatch
    if declared.get("name") and response.get("referee_name"):
        if declared["name"].lower().strip() != response["referee_name"].lower().strip():
            mismatches.append({
                "field": "name",
                "declared": declared["name"],
                "response": response["referee_name"],
                "severity": "high"
            })
    
    # Organisation mismatch
    if declared.get("organisation") and response.get("organisation"):
        if declared["organisation"].lower().strip() != response["organisation"].lower().strip():
            mismatches.append({
                "field": "organisation",
                "declared": declared["organisation"],
                "response": response["organisation"],
                "severity": "medium"
            })
    
    # Job title mismatch
    if declared.get("job_title") and response.get("applicant_job_title"):
        if declared["job_title"].lower().strip() != response["applicant_job_title"].lower().strip():
            mismatches.append({
                "field": "job_title",
                "declared": declared["job_title"],
                "response": response["applicant_job_title"],
                "severity": "low"
            })
    
    return {
        "employee_id": employee_id,
        "reference_number": ref_num,
        "has_mismatches": len(mismatches) > 0,
        "mismatches": mismatches,
        "declared": declared,
        "response": response,
        "verification_status": ref_data.get("verification_status", "pending"),
        "mismatch_explained": ref_data.get("mismatch_explained", False)
    }


@router.post("/references/{employee_id}/{ref_num}/override-mismatch")
async def override_reference_mismatch(
    employee_id: str,
    ref_num: int,
    override: MismatchOverride,
    user: dict = Depends(require_admin)
):
    """Admin override for reference mismatches."""
    db = get_db()
    
    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    ref_key = f"ref{ref_num}"
    await db.references.update_one(
        {"employee_id": employee_id},
        {
            "$set": {
                f"{ref_key}.mismatch_overridden": True,
                f"{ref_key}.mismatch_override_reason": override.reason,
                f"{ref_key}.mismatch_override_type": override.override_type,
                f"{ref_key}.mismatch_overridden_by": user.get("user_id"),
                f"{ref_key}.mismatch_overridden_at": now,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "override_reference_mismatch",
        "reference",
        f"{employee_id}_ref_{ref_num}",
        {"reason": override.reason, "override_type": override.override_type}
    )
    
    return {"success": True, "message": "Mismatch override recorded"}


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
        ref_data = refs.get(ref_key, {}) if refs else {}
        
        has_declared = bool(ref_data.get("declared", {}).get("name") or employee.get(f"reference_{ref_num}_name"))
        has_request = bool(ref_data.get("request", {}).get("sent_at") or employee.get(f"reference_{ref_num}_request_status") == "sent")
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


# ==================== REFERENCE RESET ====================

@router.post("/references/{employee_id}/{ref_num}/reset")
async def reset_reference(
    employee_id: str,
    ref_num: int,
    user: dict = Depends(require_admin)
):
    """Reset a reference to allow re-collection."""
    db = get_db()
    
    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Reset employee fields
    reset_fields = {
        f"reference_{ref_num}_verified": False,
        f"reference_{ref_num}_rejected": False,
        f"reference_{ref_num}_request_status": None,
        f"reference_{ref_num}_response_data": None,
        "updated_at": now
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": reset_fields})
    
    # Reset references collection
    ref_key = f"ref{ref_num}"
    await db.references.update_one(
        {"employee_id": employee_id},
        {
            "$set": {
                f"{ref_key}.verification_status": "pending",
                f"{ref_key}.request": {},
                f"{ref_key}.response": {},
                f"{ref_key}.reset_at": now,
                f"{ref_key}.reset_by": user.get("user_id"),
                "updated_at": now
            },
            "$unset": {
                f"{ref_key}.verified_by": "",
                f"{ref_key}.verified_at": "",
                f"{ref_key}.rejected_by": "",
                f"{ref_key}.rejected_at": ""
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "reset_reference",
        "reference",
        f"{employee_id}_ref_{ref_num}",
        {}
    )
    
    return {"success": True, "message": f"Reference {ref_num} reset"}
