"""
Worker Portal Routes Module

This module handles worker self-service portal endpoints including:
- Notifications
- Profile data and completion wizard
- CV gap explanations
- Reference mismatch explanations

NOTE: The main /worker/dashboard endpoint remains in server.py due to its
complexity and dependencies on many shared functions. It will be refactored
in a future phase.

Extracted from server.py for modularity.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_worker,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/worker", tags=["Worker Portal"])


# ==================== NOTIFICATIONS ====================

@router.get("/notifications")
async def get_worker_notifications(
    worker: dict = Depends(get_current_worker),
    unread_only: bool = Query(default=False)
):
    """Get notifications for the current worker."""
    db = get_db()
    employee_id = worker.get("employee_id")
    
    query = {"employee_id": employee_id}
    if unread_only:
        query["read"] = False
    
    notifications = await db.worker_notifications.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    unread_count = await db.worker_notifications.count_documents({
        "employee_id": employee_id,
        "read": False
    })
    
    return {
        "notifications": notifications,
        "unread_count": unread_count
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    worker: dict = Depends(get_current_worker)
):
    """Mark a notification as read."""
    db = get_db()
    employee_id = worker.get("employee_id")
    
    result = await db.worker_notifications.update_one(
        {"id": notification_id, "employee_id": employee_id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": result.modified_count > 0}


@router.get("/notifications/{notification_id}/read")
async def mark_notification_read_get(
    notification_id: str,
    worker: dict = Depends(get_current_worker)
):
    """Mark a notification as read (GET method for compatibility)."""
    return await mark_notification_read(notification_id, worker)


# ==================== PROFILE DATA & COMPLETION ====================

@router.get("/profile-data")
async def get_worker_profile_data(worker: dict = Depends(get_current_worker)):
    """
    Get current worker profile data for pre-populating the ProfileCompletionWizard.
    
    Returns existing data that was extracted from offline PDF application forms
    so the worker can review and complete missing fields.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Build profile data from employee record
    profile_data = {
        "personal": {
            "date_of_birth": employee.get("date_of_birth", ""),
            "ni_number": employee.get("ni_number", ""),
            "phone": employee.get("phone") or employee.get("mobile") or ""
        },
        "address": {
            "line1": "",
            "line2": "",
            "city": "",
            "county": "",
            "postcode": ""
        },
        "reference_1": {
            "name": "",
            "email": "",
            "phone": "",
            "organization": "",
            "job_title": "",
            "relationship": ""
        },
        "reference_2": {
            "name": "",
            "email": "",
            "phone": "",
            "organization": "",
            "job_title": "",
            "relationship": ""
        },
        "emergency_contact": {
            "name": "",
            "phone": "",
            "relationship": "",
            "address": ""
        }
    }
    
    # Address - check multiple possible field names
    addr = employee.get("address", {})
    if isinstance(addr, dict):
        profile_data["address"]["line1"] = addr.get("line1") or addr.get("line_1") or ""
        profile_data["address"]["line2"] = addr.get("line2") or addr.get("line_2") or ""
        profile_data["address"]["city"] = addr.get("city") or addr.get("town") or ""
        profile_data["address"]["county"] = addr.get("county") or ""
        profile_data["address"]["postcode"] = addr.get("postcode") or ""
    else:
        # Address stored as flat fields
        profile_data["address"]["line1"] = employee.get("address_line_1") or employee.get("address") or ""
        profile_data["address"]["line2"] = employee.get("address_line_2") or ""
        profile_data["address"]["city"] = employee.get("city") or employee.get("town") or ""
        profile_data["address"]["county"] = employee.get("county") or ""
        profile_data["address"]["postcode"] = employee.get("postcode") or ""
    
    # References - check employee record
    ref_1 = employee.get("reference_1") or {}
    ref_2 = employee.get("reference_2") or {}
    
    if ref_1:
        profile_data["reference_1"] = {
            "name": ref_1.get("name") or "",
            "email": ref_1.get("email") or "",
            "phone": ref_1.get("phone") or "",
            "organization": ref_1.get("organization") or ref_1.get("organisation") or "",
            "job_title": ref_1.get("job_title") or ref_1.get("position") or "",
            "relationship": ref_1.get("relationship") or ""
        }
    
    if ref_2:
        profile_data["reference_2"] = {
            "name": ref_2.get("name") or "",
            "email": ref_2.get("email") or "",
            "phone": ref_2.get("phone") or "",
            "organization": ref_2.get("organization") or ref_2.get("organisation") or "",
            "job_title": ref_2.get("job_title") or ref_2.get("position") or "",
            "relationship": ref_2.get("relationship") or ""
        }
    
    # Also check employee_references collection for stored references
    stored_refs = await db.employee_references.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("reference_number", 1).limit(2).to_list(2)
    
    for idx, ref in enumerate(stored_refs):
        ref_key = f"reference_{idx + 1}"
        if not profile_data[ref_key]["name"]:
            profile_data[ref_key] = {
                "name": ref.get("referee_name") or "",
                "email": ref.get("referee_email") or "",
                "phone": ref.get("referee_phone") or "",
                "organization": ref.get("referee_organisation") or "",
                "job_title": ref.get("referee_position") or "",
                "relationship": ref.get("referee_relationship") or ""
            }
    
    # Emergency Contact
    ec = employee.get("emergency_contact") or employee.get("next_of_kin") or {}
    if ec:
        profile_data["emergency_contact"] = {
            "name": ec.get("name") or employee.get("next_of_kin_name") or "",
            "phone": ec.get("phone") or ec.get("contact_number") or employee.get("next_of_kin_phone") or "",
            "relationship": ec.get("relationship") or employee.get("next_of_kin_relationship") or "",
            "address": ec.get("address") or ""
        }
    
    return {
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "profile_data": profile_data,
        "import_source": employee.get("import_source"),
        "profile_completion_needed": employee.get("profile_completion_needed", False)
    }


@router.get("/profile-completion-status")
async def get_profile_completion_status(worker: dict = Depends(get_current_worker)):
    """
    Check what sections of the profile are complete.
    Used by ProfileCompletionWizard to show progress.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Define required sections and their fields
    sections = {
        "personal_details": {
            "complete": False,
            "required_fields": ["date_of_birth", "ni_number", "phone"],
            "missing_fields": []
        },
        "address": {
            "complete": False,
            "required_fields": ["address_line_1", "city", "postcode"],
            "missing_fields": []
        },
        "employment_history": {
            "complete": False,
            "required_fields": ["employment_history"],
            "missing_fields": []
        },
        "references": {
            "complete": False,
            "required_fields": ["reference_1", "reference_2"],
            "missing_fields": []
        },
        "emergency_contacts": {
            "complete": False,
            "required_fields": ["emergency_contact"],
            "missing_fields": []
        }
    }
    
    # Check Personal Details
    has_dob = bool(employee.get("date_of_birth"))
    has_ni = bool(employee.get("ni_number"))
    has_phone = bool(employee.get("phone") or employee.get("mobile"))
    
    if not has_dob:
        sections["personal_details"]["missing_fields"].append("date_of_birth")
    if not has_ni:
        sections["personal_details"]["missing_fields"].append("ni_number")
    if not has_phone:
        sections["personal_details"]["missing_fields"].append("phone")
    
    sections["personal_details"]["complete"] = has_dob and has_ni and has_phone
    
    # Check Address - support both flat fields and nested dict
    addr = employee.get("address", {})
    if isinstance(addr, dict):
        has_address = bool(employee.get("address_line_1") or addr.get("line1") or addr.get("line_1"))
        has_city = bool(employee.get("city") or employee.get("town") or addr.get("city") or addr.get("town"))
        has_postcode = bool(employee.get("postcode") or addr.get("postcode"))
    else:
        has_address = bool(employee.get("address_line_1") or addr)
        has_city = bool(employee.get("city") or employee.get("town"))
        has_postcode = bool(employee.get("postcode"))
    
    if not has_address:
        sections["address"]["missing_fields"].append("address_line_1")
    if not has_city:
        sections["address"]["missing_fields"].append("city")
    if not has_postcode:
        sections["address"]["missing_fields"].append("postcode")
    
    sections["address"]["complete"] = has_address and has_city and has_postcode
    
    # Check Employment History
    has_employment = bool(employee.get("employment_history") and len(employee.get("employment_history", [])) > 0)
    has_cv = bool(employee.get("cv_file_url") or employee.get("cv_extracted_data"))
    
    if not has_employment and not has_cv:
        sections["employment_history"]["missing_fields"].append("employment_history_or_cv")
    
    sections["employment_history"]["complete"] = has_employment or has_cv
    
    # Check References
    ref_count = 0
    refs = await db.employee_references.find({"employee_id": employee_id}, {"_id": 0}).to_list(10)
    ref_count = len([r for r in refs if r.get("referee_name") or r.get("referee_email")])
    
    # Also check inline references
    if employee.get("reference_1") and (employee.get("reference_1", {}).get("name") or employee.get("reference_1", {}).get("email")):
        ref_count += 1
    if employee.get("reference_2") and (employee.get("reference_2", {}).get("name") or employee.get("reference_2", {}).get("email")):
        ref_count += 1
    
    if ref_count < 1:
        sections["references"]["missing_fields"].append("reference_1")
    if ref_count < 2:
        sections["references"]["missing_fields"].append("reference_2")
    
    sections["references"]["complete"] = ref_count >= 2
    
    # Check Emergency Contact
    ec = employee.get("emergency_contact") or employee.get("next_of_kin") or {}
    has_ec_name = bool(ec.get("name") or employee.get("next_of_kin_name"))
    has_ec_phone = bool(ec.get("phone") or ec.get("contact_number") or employee.get("next_of_kin_phone"))
    
    if not has_ec_name:
        sections["emergency_contacts"]["missing_fields"].append("emergency_contact_name")
    if not has_ec_phone:
        sections["emergency_contacts"]["missing_fields"].append("emergency_contact_phone")
    
    sections["emergency_contacts"]["complete"] = has_ec_name and has_ec_phone
    
    # Calculate overall completion
    completed_sections = sum(1 for s in sections.values() if s["complete"])
    total_sections = len(sections)
    
    # Determine if wizard is needed
    profile_complete = completed_sections == total_sections
    needs_wizard = employee.get("profile_completion_needed", False) or not profile_complete
    
    return {
        "profile_complete": profile_complete,
        "needs_wizard": needs_wizard,
        "completed_sections": completed_sections,
        "total_sections": total_sections,
        "completion_percentage": int((completed_sections / total_sections) * 100),
        "sections": sections,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    }


# ==================== PROFILE UPDATE ====================

class ProfileUpdateRequest(BaseModel):
    section: str  # personal, address, reference_1, reference_2, emergency_contact
    data: Dict[str, Any]


@router.post("/profile/update")
async def update_worker_profile(
    request: ProfileUpdateRequest,
    worker: dict = Depends(get_current_worker)
):
    """
    Update a section of the worker's profile.
    Used by ProfileCompletionWizard to save progress.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_doc = {"updated_at": now}
    
    if request.section == "personal":
        if request.data.get("date_of_birth"):
            update_doc["date_of_birth"] = request.data["date_of_birth"]
        if request.data.get("ni_number"):
            update_doc["ni_number"] = request.data["ni_number"].upper().strip()
        if request.data.get("phone"):
            update_doc["phone"] = request.data["phone"]
    
    elif request.section == "address":
        update_doc["address_line_1"] = request.data.get("line1", "")
        update_doc["address_line_2"] = request.data.get("line2", "")
        update_doc["city"] = request.data.get("city", "")
        update_doc["county"] = request.data.get("county", "")
        update_doc["postcode"] = request.data.get("postcode", "").upper().strip()
        # Also update nested address for consistency
        update_doc["address"] = {
            "line1": request.data.get("line1", ""),
            "line2": request.data.get("line2", ""),
            "city": request.data.get("city", ""),
            "county": request.data.get("county", ""),
            "postcode": request.data.get("postcode", "").upper().strip()
        }
    
    elif request.section in ["reference_1", "reference_2"]:
        ref_num = 1 if request.section == "reference_1" else 2
        ref_data = {
            "name": request.data.get("name", ""),
            "email": request.data.get("email", ""),
            "phone": request.data.get("phone", ""),
            "organization": request.data.get("organization", ""),
            "job_title": request.data.get("job_title", ""),
            "relationship": request.data.get("relationship", "")
        }
        update_doc[request.section] = ref_data
        
        # Also update/create in employee_references collection
        ref_id = f"{employee_id}_ref_{ref_num}"
        await db.employee_references.update_one(
            {"employee_id": employee_id, "reference_number": ref_num},
            {
                "$set": {
                    "id": ref_id,
                    "employee_id": employee_id,
                    "reference_number": ref_num,
                    "referee_name": ref_data["name"],
                    "referee_email": ref_data["email"],
                    "referee_phone": ref_data["phone"],
                    "referee_organisation": ref_data["organization"],
                    "referee_position": ref_data["job_title"],
                    "referee_relationship": ref_data["relationship"],
                    "status": "pending",
                    "updated_at": now,
                    "source": "worker_profile_wizard"
                },
                "$setOnInsert": {
                    "created_at": now
                }
            },
            upsert=True
        )
    
    elif request.section == "emergency_contact":
        ec_data = {
            "name": request.data.get("name", ""),
            "phone": request.data.get("phone", ""),
            "relationship": request.data.get("relationship", ""),
            "address": request.data.get("address", "")
        }
        update_doc["emergency_contact"] = ec_data
        # Also update legacy fields
        update_doc["next_of_kin_name"] = ec_data["name"]
        update_doc["next_of_kin_phone"] = ec_data["phone"]
        update_doc["next_of_kin_relationship"] = ec_data["relationship"]
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown section: {request.section}")
    
    # Update employee
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": update_doc}
    )
    
    # Check if profile is now complete
    status = await get_profile_completion_status(worker)
    
    # If complete, remove the profile_completion_needed flag
    if status["profile_complete"]:
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {"profile_completion_needed": False}}
        )
    
    await log_audit_action(
        employee_id,
        "profile_update",
        "employee",
        employee_id,
        {"section": request.section, "via": "worker_portal"}
    )
    
    return {
        "success": True,
        "section": request.section,
        "profile_complete": status["profile_complete"],
        "completion_percentage": status["completion_percentage"]
    }


# ==================== CV GAP EXPLANATIONS ====================

class GapExplanationRequest(BaseModel):
    explanation_type: str  # unemployed, caring, education, health, travel, other
    explanation_text: Optional[str] = None


@router.post("/cv-gaps/{gap_id}/explain")
async def explain_cv_gap(
    gap_id: str,
    request: GapExplanationRequest,
    worker: dict = Depends(get_current_worker)
):
    """
    Worker provides explanation for a detected CV gap.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    gaps = employee.get("cv_gaps_detected", [])
    
    # Find the gap
    gap_found = False
    for gap in gaps:
        if gap.get("id") == gap_id:
            gap["explained"] = True
            gap["explanation_type"] = request.explanation_type
            gap["explanation_text"] = request.explanation_text
            gap["explained_at"] = datetime.now(timezone.utc).isoformat()
            gap_found = True
            break
    
    if not gap_found:
        raise HTTPException(status_code=404, detail="Gap not found")
    
    # Check if all gaps are now explained
    all_explained = all(g.get("explained", False) for g in gaps)
    
    # Update employee
    now = datetime.now(timezone.utc).isoformat()
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "cv_gaps_detected": gaps,
                "cv_gaps_all_explained": all_explained,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        employee_id,
        "gap_explanation_submitted",
        "employee",
        employee_id,
        {"gap_id": gap_id, "explanation_type": request.explanation_type}
    )
    
    return {
        "success": True,
        "gap_id": gap_id,
        "all_gaps_explained": all_explained
    }


# ==================== REFERENCE MISMATCH EXPLANATIONS ====================

@router.get("/reference-mismatches")
async def get_reference_mismatches(worker: dict = Depends(get_current_worker)):
    """
    Get any reference mismatches that need worker explanation.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    
    # Check employee_references for any mismatches needing explanation
    refs = await db.employee_references.find(
        {
            "employee_id": employee_id,
            "$or": [
                {"mismatch_detected": True, "mismatch_explained": {"$ne": True}},
                {"verification_status": "mismatch"}
            ]
        },
        {"_id": 0}
    ).to_list(10)
    
    mismatches = []
    for ref in refs:
        if ref.get("mismatch_details"):
            mismatches.append({
                "reference_number": ref.get("reference_number"),
                "referee_name": ref.get("referee_name"),
                "mismatch_details": ref.get("mismatch_details"),
                "needs_explanation": not ref.get("mismatch_explained", False)
            })
    
    return {
        "mismatches": mismatches,
        "needs_action": len([m for m in mismatches if m["needs_explanation"]]) > 0
    }


class MismatchExplanationRequest(BaseModel):
    explanation_type: str  # typo, name_change, different_role, other
    explanation_text: str


@router.post("/reference-mismatches/{ref_num}/explain")
async def explain_reference_mismatch(
    ref_num: int,
    request: MismatchExplanationRequest,
    worker: dict = Depends(get_current_worker)
):
    """
    Worker provides explanation for a reference mismatch.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    
    now = datetime.now(timezone.utc).isoformat()
    
    result = await db.employee_references.update_one(
        {"employee_id": employee_id, "reference_number": ref_num},
        {
            "$set": {
                "mismatch_explained": True,
                "mismatch_explanation_type": request.explanation_type,
                "mismatch_explanation_text": request.explanation_text,
                "mismatch_explained_at": now,
                "updated_at": now
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Reference not found")
    
    await log_audit_action(
        employee_id,
        "reference_mismatch_explained",
        "employee_reference",
        f"{employee_id}_ref_{ref_num}",
        {"explanation_type": request.explanation_type}
    )
    
    return {
        "success": True,
        "reference_number": ref_num
    }
