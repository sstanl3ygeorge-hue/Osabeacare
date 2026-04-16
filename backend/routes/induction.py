"""
Induction Checklist Routes - CQC Compliant Care Certificate Tracking.

This module handles:
- Induction checklist management (15 Care Certificate standards)
- Auto-sync with verified training records
- Checklist status tracking (pending/in_progress/completed)
- Admin tools for reset and migration
"""

import io
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .dependencies import (
    get_db, get_current_user, require_admin, require_manager_or_admin,
    log_audit_action
)
from services.pdf_service import generate_admin_form_pdf

router = APIRouter(tags=["Induction Checklist"])


# Default induction checklist items for all care roles
# CQC Care Certificate 15 Standards for Adult Care
DEFAULT_INDUCTION_ITEMS = [
    {"id": "understand_your_role",     "name": "Understand Your Role",                                                     "mandatory": True, "order": 1,  "training_link": None},
    {"id": "personal_development",     "name": "Your Personal Development",                                                  "mandatory": True, "order": 2,  "training_link": None},
    {"id": "duty_of_care",             "name": "Duty of Care",                                                               "mandatory": True, "order": 3,  "training_link": None},
    {"id": "equality_diversity",       "name": "Equality and Diversity",                                                     "mandatory": True, "order": 4,  "training_link": "equality_diversity"},
    {"id": "work_person_centred",      "name": "Work in a Person-Centred Way",                                               "mandatory": True, "order": 5,  "training_link": None},
    {"id": "communication",            "name": "Communication",                                                              "mandatory": True, "order": 6,  "training_link": None},
    {"id": "privacy_dignity",          "name": "Privacy and Dignity",                                                        "mandatory": True, "order": 7,  "training_link": None},
    {"id": "fluids_nutrition",         "name": "Fluids and Nutrition",                                                       "mandatory": True, "order": 8,  "training_link": "food_hygiene"},
    {"id": "awareness_mental_health",  "name": "Awareness of Mental Health, Dementia and Learning Disabilities",             "mandatory": True, "order": 9,  "training_link": None},
    {"id": "safeguarding_adults",      "name": "Safeguarding Adults",                                                        "mandatory": True, "order": 10, "training_link": "safeguarding"},
    {"id": "basic_life_support",       "name": "Basic Life Support",                                                         "mandatory": True, "order": 11, "training_link": "bls"},
    {"id": "health_safety",            "name": "Health and Safety",                                                          "mandatory": True, "order": 12, "training_link": "health_safety"},
    {"id": "handling_information",     "name": "Handling Information",                                                       "mandatory": True, "order": 13, "training_link": "data_protection"},
    {"id": "infection_control",        "name": "Infection Prevention and Control",                                           "mandatory": True, "order": 14, "training_link": "infection_control"},
    {"id": "shadow_shift",             "name": "Shadow Shift Completed",                                                     "mandatory": True, "order": 15, "training_link": None},
]

# Mapping of induction items to training requirement codes for auto-completion
INDUCTION_TRAINING_MAP = {
    "Safeguarding Adults": ["safeguarding", "safeguard_adults", "safeguarding_adults"],
    "Basic Life Support": ["bls", "basic_life_support", "resuscitation"],
    "Health and Safety": ["health_safety", "health_and_safety", "cstf_health"],
    "Infection Prevention and Control": ["infection_control", "infection_prevention", "cstf_infection"],
    "Equality and Diversity": ["equality_diversity", "equality", "edi", "cstf_equality"],
    "Fluids and Nutrition": ["food_hygiene", "food_safety", "nutrition"],
    "Handling Information": ["data_protection", "gdpr", "information_governance"],
}


class InductionItemUpdate(BaseModel):
    item_name: str
    status: str  # pending, completed
    notes: Optional[str] = None


@router.get("/employees/{employee_id}/induction-checklist")
async def get_induction_checklist(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get induction checklist for an employee.
    If no checklist exists, returns default template.
    AUTO-SYNCS with verified training records.
    """
    db = get_db()
    
    # Check employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    # Get verified trainings for this employee
    verified_trainings = await db.training_records.find({
        "employee_id": employee_id,
        "verified": True,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0, "training_name": 1, "requirement_id": 1, "code": 1, "verified_by": 1, "verified_at": 1}).to_list(100)
    
    # Build set of verified training names/codes for matching
    verified_set = set()
    verified_info = {}
    for tr in verified_trainings:
        name = (tr.get('training_name') or '').lower()
        code = (tr.get('code') or tr.get('requirement_id') or '').lower()
        if name:
            verified_set.add(name)
            verified_info[name] = tr
        if code:
            verified_set.add(code)
            verified_info[code] = tr
    
    # Mapping from induction item name to training patterns (extended)
    INDUCTION_TO_TRAINING_MAP = {
        "Safeguarding Adults": ["safeguarding", "safeguard", "safeguarding adults", "safeguard_adults"],
        "Safeguarding Children": ["safeguarding children", "child protection", "safeguard_children"],
        "Basic Life Support": ["basic life support", "bls", "basic_life_support", "resuscitation", "cpr"],
        "Health and Safety": ["health and safety", "health_safety", "h&s", "cstf_health"],
        "Infection Prevention and Control": ["infection control", "infection_control", "infection prevention", "ipc", "cstf_infection"],
        "Equality and Diversity": ["equality", "diversity", "equality_diversity", "edi", "cstf_equality"],
        "Fluids and Nutrition": ["food hygiene", "food_hygiene", "nutrition", "fluids"],
        "Handling Information": ["data protection", "gdpr", "data_protection", "information governance", "ig"],
        "Shadow Shift Completed": ["shadow shift", "shadow_shift", "shadowing"],
    }
    
    def is_training_verified(item_name):
        """Check if a training item is verified based on training records"""
        item_lower = item_name.lower()
        
        # Direct match
        if item_lower in verified_set:
            return True, verified_info.get(item_lower)
        
        # Check via mapping
        patterns = INDUCTION_TO_TRAINING_MAP.get(item_name, [])
        for pattern in patterns:
            if pattern.lower() in verified_set:
                return True, verified_info.get(pattern.lower())
            # Also check if any verified training contains this pattern
            for v_name in verified_set:
                if pattern.lower() in v_name or v_name in pattern.lower():
                    return True, verified_info.get(v_name)
        
        return False, None
    
    now = datetime.now(timezone.utc).isoformat()
    checklist = await db.induction_checklists.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not checklist:
        # Create default structure with auto-sync
        items = []
        for item_def in DEFAULT_INDUCTION_ITEMS:
            is_verified, training_info = is_training_verified(item_def["name"])
            items.append({
                "id": item_def["id"],
                "name": item_def["name"],
                "mandatory": item_def["mandatory"],
                "status": "completed" if is_verified else "pending",
                "completed_at": training_info.get("verified_at") if is_verified and training_info else None,
                "completed_by_name": f"Auto (Training: {training_info.get('training_name', 'Verified')})" if is_verified and training_info else None,
                "synced_from_training": is_verified
            })
        
        completed_count = sum(1 for i in items if i["status"] == "completed")
        overall_status = "completed" if completed_count == len(items) else "in_progress" if completed_count > 0 else "pending"
        
        return {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "items": items,
            "overall_status": overall_status,
            "started_at": now if completed_count > 0 else None,
            "completed_at": now if overall_status == "completed" else None,
            "auto_synced": True
        }
    
    # Existing checklist - sync with verified trainings
    items_updated = False
    for item in checklist.get("items", []):
        # Only update pending items that have verified training
        if item.get("status") != "completed":
            is_verified, training_info = is_training_verified(item["name"])
            if is_verified:
                item["status"] = "completed"
                item["completed_at"] = training_info.get("verified_at") if training_info else now
                item["completed_by_name"] = f"Auto (Training: {training_info.get('training_name', 'Verified')})" if training_info else "Auto-synced"
                item["synced_from_training"] = True
                items_updated = True
    
    # Recalculate overall status
    completed_count = sum(1 for i in checklist.get("items", []) if i.get("status") == "completed")
    total_count = len(checklist.get("items", []))
    
    if completed_count == total_count:
        checklist["overall_status"] = "completed"
        checklist["completed_at"] = checklist.get("completed_at") or now
    elif completed_count > 0:
        checklist["overall_status"] = "in_progress"
        checklist["started_at"] = checklist.get("started_at") or now
    else:
        checklist["overall_status"] = "pending"
    
    # Save updates if items were synced
    if items_updated:
        await db.induction_checklists.update_one(
            {"employee_id": employee_id},
            {"$set": {
                "items": checklist["items"],
                "overall_status": checklist["overall_status"],
                "started_at": checklist.get("started_at"),
                "completed_at": checklist.get("completed_at"),
                "updated_at": now,
                "last_auto_sync": now
            }}
        )
    
    checklist["auto_synced"] = items_updated
    return checklist


@router.put("/employees/{employee_id}/induction-checklist")
async def update_induction_checklist(
    employee_id: str,
    payload: InductionItemUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Update an induction checklist item.
    Creates checklist if it doesn't exist.
    """
    db = get_db()
    
    # Check employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get reviewer name
    reviewer = await db.users.find_one(
        {"$or": [{"user_id": user['user_id']}, {"id": user['user_id']}]}, 
        {"_id": 0, "name": 1, "first_name": 1, "last_name": 1, "email": 1}
    )
    reviewer_name = reviewer.get('name') if reviewer else user.get('email', 'Admin')
    if not reviewer_name and reviewer:
        reviewer_name = f"{reviewer.get('first_name', '')} {reviewer.get('last_name', '')}".strip() or reviewer.get('email', 'Admin')
    
    # Get or create checklist
    checklist = await db.induction_checklists.find_one({"employee_id": employee_id})
    
    if not checklist:
        # Create new checklist with default items
        checklist = {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "employee_name": employee_name,
            "items": [{"id": item["id"], "name": item["name"], "mandatory": item["mandatory"], "status": "pending", "completed_at": None, "completed_by": None, "completed_by_name": None, "notes": None} for item in DEFAULT_INDUCTION_ITEMS],
            "overall_status": "pending",
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now
        }
    
    # Enforce notes for Shadow Shift Completed manual sign-off
    if payload.item_name == "Shadow Shift Completed" and payload.status == "completed":
        if not payload.notes or not payload.notes.strip():
            raise HTTPException(
                status_code=422,
                detail="Shadow Shift sign-off requires a supervisor/witness note (notes field cannot be empty)."
            )

    # Find and update the specific item
    item_found = False
    for item in checklist["items"]:
        if item["name"] == payload.item_name:
            item["status"] = payload.status
            item["notes"] = payload.notes
            if payload.status == "completed":
                item["completed_at"] = now
                item["completed_by"] = user['user_id']
                item["completed_by_name"] = reviewer_name
            else:
                item["completed_at"] = None
                item["completed_by"] = None
                item["completed_by_name"] = None
            item_found = True
            break
    
    if not item_found:
        # Add new item
        checklist["items"].append({
            "name": payload.item_name,
            "mandatory": False,
            "status": payload.status,
            "notes": payload.notes,
            "completed_at": now if payload.status == "completed" else None,
            "completed_by": user['user_id'] if payload.status == "completed" else None,
            "completed_by_name": reviewer_name if payload.status == "completed" else None
        })
    
    # Calculate overall status
    completed_count = sum(1 for i in checklist["items"] if i["status"] == "completed")
    mandatory_completed = sum(1 for i in checklist["items"] if i.get("mandatory") and i["status"] == "completed")
    mandatory_total = sum(1 for i in checklist["items"] if i.get("mandatory"))
    
    if completed_count == 0:
        checklist["overall_status"] = "pending"
        checklist["started_at"] = None
    elif mandatory_completed >= mandatory_total:
        checklist["overall_status"] = "completed"
        checklist["completed_at"] = now
    else:
        checklist["overall_status"] = "in_progress"
        if not checklist.get("started_at"):
            checklist["started_at"] = now
    
    checklist["updated_at"] = now
    
    # Upsert
    await db.induction_checklists.update_one(
        {"employee_id": employee_id},
        {"$set": checklist},
        upsert=True
    )
    
    # Log audit
    await log_audit_action(user['user_id'], "induction_item_updated", "induction_checklist", employee_id, {
        "item_name": payload.item_name,
        "status": payload.status,
        "overall_status": checklist["overall_status"]
    })
    
    return {
        "success": True,
        "overall_status": checklist["overall_status"],
        "completed_count": completed_count,
        "total_count": len(checklist["items"]),
        "mandatory_completed": mandatory_completed,
        "mandatory_total": mandatory_total
    }


@router.post("/employees/{employee_id}/induction-checklist/reset")
async def reset_induction_checklist(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """
    Reset induction checklist for an employee (admin only).
    Useful for re-induction after extended absence.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await db.induction_checklists.delete_one({"employee_id": employee_id})
    
    await log_audit_action(user['user_id'], "induction_checklist_reset", "induction_checklist", employee_id, {})
    
    return {"success": True, "message": "Induction checklist reset"}


@router.post("/employees/{employee_id}/induction-checklist/fix")
async def fix_induction_checklist(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """
    Fix induction checklist for an employee:
    1. Migrate to the official 15 Care Certificate standards
    2. Sync training completions with induction items
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get verified trainings
    training_records = await db.training_records.find({
        "employee_id": employee_id,
        "verified": True
    }, {"_id": 0}).to_list(50)
    
    training_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "verification_stamp": {"$nin": [None, "", "not_verified"]}
    }, {"_id": 0}).to_list(100)
    
    # Build verified training names
    verified_trainings = set()
    for tr in training_records:
        name = (tr.get("training_name") or "").lower()
        if name:
            verified_trainings.add(name)
    for doc in training_docs:
        req_id = (doc.get("requirement_id") or "").lower()
        if req_id:
            verified_trainings.add(req_id)
    
    def is_verified(item_name):
        item_lower = item_name.lower()
        # Direct match
        if item_lower in verified_trainings:
            return True
        # Check via INDUCTION_TRAINING_MAP
        if item_name in INDUCTION_TRAINING_MAP:
            patterns = INDUCTION_TRAINING_MAP[item_name]
            for pattern in patterns:
                if any(pattern.lower() in vt for vt in verified_trainings):
                    return True
        return False
    
    # Get existing checklist
    existing = await db.induction_checklists.find_one({"employee_id": employee_id})
    existing_items = {i.get("name"): i for i in (existing.get("items", []) if existing else [])}
    
    # Build new items list using DEFAULT_INDUCTION_ITEMS (15 items), preserving completed status
    new_items = []
    completed_count = 0
    
    for item_def in DEFAULT_INDUCTION_ITEMS:
        item_name = item_def["name"]
        existing_item = existing_items.get(item_name)
        
        # Check if completed in existing record or from verified training
        is_complete = False
        completed_at = None
        completed_by = None
        completed_by_name = None
        
        if existing_item and existing_item.get("status") == "completed":
            is_complete = True
            completed_at = existing_item.get("completed_at")
            completed_by = existing_item.get("completed_by")
            completed_by_name = existing_item.get("completed_by_name")
        elif is_verified(item_name):
            is_complete = True
            completed_at = now
            completed_by_name = "Auto-synced from training"
        
        if is_complete:
            completed_count += 1
        
        new_items.append({
            "id": item_def["id"],
            "name": item_name,
            "mandatory": item_def["mandatory"],
            "status": "completed" if is_complete else "pending",
            "completed_at": completed_at,
            "completed_by": completed_by,
            "completed_by_name": completed_by_name,
            "notes": None
        })
    
    # Determine overall status
    mandatory_completed = sum(1 for i in new_items if i.get("mandatory") and i["status"] == "completed")
    mandatory_total = sum(1 for i in new_items if i.get("mandatory"))
    
    if completed_count == 0:
        overall_status = "pending"
    elif mandatory_completed >= mandatory_total:
        overall_status = "completed"
    else:
        overall_status = "in_progress"
    
    # Upsert checklist
    checklist_data = {
        "id": existing.get("id") if existing else str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_name": employee_name,
        "items": new_items,
        "overall_status": overall_status,
        "started_at": existing.get("started_at") if existing else (now if completed_count > 0 else None),
        "completed_at": now if overall_status == "completed" else None,
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
        "fixed_at": now,
        "fixed_reason": "Migrated to 15 Care Certificate standards"
    }
    
    await db.induction_checklists.update_one(
        {"employee_id": employee_id},
        {"$set": checklist_data},
        upsert=True
    )
    
    await log_audit_action(user['user_id'], "induction_checklist_fixed", "induction_checklist", employee_id, {
        "items_count": len(new_items),
        "completed_count": completed_count,
        "synced_from_trainings": len(verified_trainings)
    })
    
    return {
        "success": True,
        "message": f"Induction checklist migrated to 15 Care Certificate standards: {completed_count}/{len(new_items)} complete",
        "items_count": len(new_items),
        "completed_count": completed_count,
        "synced_trainings": list(verified_trainings)[:10]
    }


@router.post("/induction-checklists/migrate-all")
async def migrate_all_induction_checklists(
    user: dict = Depends(require_admin)
):
    """
    Migrate ALL existing induction checklists to the 15 Care Certificate standards.
    Admin only endpoint for one-time migration.
    """
    db = get_db()
    
    # Get all existing induction checklists that don't have exactly 15 items
    checklists = await db.induction_checklists.find({}).to_list(1000)
    migrated_count = 0
    skipped_count = 0
    errors = []
    
    for checklist in checklists:
        employee_id = checklist.get("employee_id")
        items = checklist.get("items", [])
        
        # Skip if already has 15 items
        if len(items) == 15:
            skipped_count += 1
            continue
        
        try:
            # Call the individual fix endpoint logic
            response = await fix_induction_checklist(employee_id, user)
            if response.get("success"):
                migrated_count += 1
        except Exception as e:
            errors.append({"employee_id": employee_id, "error": str(e)})
    
    return {
        "success": True,
        "message": f"Migration complete: {migrated_count} migrated, {skipped_count} already at 15 items",
        "migrated_count": migrated_count,
        "skipped_count": skipped_count,
        "errors": errors[:10]  # Limit errors shown
    }


@router.get("/employees/{employee_id}/induction-completion/download-pdf")
async def download_induction_completion_pdf(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Generate and download an Induction Completion Certificate as PDF.

    Only available when induction overall_status == 'completed'.
    Uses the shared pdf_service with company branding and the Care Certificate item table.
    """
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    checklist = await db.induction_checklists.find_one({"employee_id": employee_id}, {"_id": 0})
    if not checklist:
        raise HTTPException(status_code=404, detail="No induction checklist found for this employee")

    if checklist.get("overall_status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Induction is not yet completed (status: {checklist.get('overall_status', 'pending')})"
        )

    # Build form_data expected by generate_induction_pdf_content
    items = checklist.get("items", [])
    checklist_items = []
    for item in items:
        checklist_items.append({
            "name": item.get("name", ""),
            "completed": item.get("status") == "completed",
            "completed_date": item.get("completed_at", "")[:10] if item.get("completed_at") else "-",
            "completed_by": item.get("completed_by_name") or "",
            "notes": item.get("notes") or "",
        })

    form_data = {
        "start_date": checklist.get("started_at", "")[:10] if checklist.get("started_at") else "N/A",
        "completion_date": checklist.get("completed_at", "")[:10] if checklist.get("completed_at") else "N/A",
        "inductor_name": user.get("name") or user.get("email", "Admin"),
        "checklist_items": checklist_items,
        "notes": checklist.get("notes") or "",
    }

    employee_data = {
        "first_name": employee.get("first_name", ""),
        "last_name": employee.get("last_name", ""),
        "employee_code": employee.get("employee_code") or employee.get("id", "")[:8],
        "applicant_reference": employee.get("applicant_reference"),
    }

    admin_data = {
        "name": user.get("name") or user.get("email", "System"),
    }

    try:
        pdf_bytes = generate_admin_form_pdf("induction_checklist", form_data, employee_data, admin_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    emp_name_safe = f"{employee.get('first_name', '')}_{employee.get('last_name', '')}".replace(" ", "_")
    filename = f"Induction_Certificate_{emp_name_safe}_{datetime.now().strftime('%Y%m%d')}.pdf"

    await log_audit_action(user["user_id"], "download_induction_pdf", "induction_checklist", employee_id, {
        "filename": filename
    })

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )
