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
import logging
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
from induction_definitions import (
    DEFAULT_INDUCTION_ITEMS,
    INDUCTION_NAME_TO_TRAINING_PATTERNS,
    get_induction_rule_metadata_by_name,
    get_employee_induction_status,
    is_training_verified_for_item,
    ensure_checklist_list_format,
)

router = APIRouter(tags=["Induction Checklist"])
logger = logging.getLogger(__name__)

# DEFAULT_INDUCTION_ITEMS, INDUCTION_NAME_TO_TRAINING_PATTERNS imported from induction_definitions

# Legacy alias kept for fix endpoint's is_verified inner function
INDUCTION_TRAINING_MAP = {
    "Safeguarding Adults": ["safeguarding", "safeguard_adults", "safeguarding_adults"],
    "Basic Life Support": ["bls", "basic_life_support", "resuscitation"],
    "Health and Safety": ["health_safety", "health_and_safety", "cstf_health"],
    "Infection Prevention and Control": ["infection_control", "infection_prevention", "cstf_infection"],
    "Equality and Diversity": ["equality_diversity", "equality", "edi", "cstf_equality"],
    "Fluids and Nutrition": ["food_hygiene", "food_safety", "nutrition"],
    "Handling Information": ["data_protection", "gdpr", "information_governance"],
}


class ShadowShiftDetailsPayload(BaseModel):
    shift_date: str
    location_unit: str
    supervisor_name: str
    summary_notes: str
    ready_for_deployment: bool
    follow_up_actions: Optional[str] = None


class InductionItemUpdate(BaseModel):
    item_name: str
    status: str  # pending, completed
    notes: Optional[str] = None
    shadow_shift_signoff: Optional[ShadowShiftDetailsPayload] = None


def _without_mongo_id(document: dict) -> dict:
    """Return a shallow copy safe for Mongo $set updates."""
    return {k: v for k, v in (document or {}).items() if k != "_id"}


def _normalise_shadow_shift_signoff(
    details: ShadowShiftDetailsPayload,
    user_id: str,
    reviewer_name: str,
    recorded_at: str,
) -> dict:
    required_values = {
        "shift_date": details.shift_date,
        "location_unit": details.location_unit,
        "supervisor_name": details.supervisor_name,
        "summary_notes": details.summary_notes,
    }
    missing = [label for label, value in required_values.items() if not str(value or "").strip()]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Shadow Shift sign-off is missing required fields: {', '.join(missing)}",
        )
    if details.ready_for_deployment is False and not str(details.follow_up_actions or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Follow-up actions are required when the shadow shift outcome is not ready for deployment.",
        )

    return {
        "shift_date": details.shift_date.strip(),
        "location_unit": details.location_unit.strip(),
        "supervisor_name": details.supervisor_name.strip(),
        "summary_notes": details.summary_notes.strip(),
        "ready_for_deployment": bool(details.ready_for_deployment),
        "follow_up_actions": (details.follow_up_actions or "").strip(),
        "recorded_by": user_id,
        "recorded_by_name": reviewer_name,
        "recorded_at": recorded_at,
    }


@router.get("/employees/{employee_id}/induction-checklist")
async def get_induction_checklist(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get induction checklist for an employee.
    If no checklist exists, returns default template.
    AUTO-SYNCS with verified training records via canonical function.
    """
    db = get_db()
    
    # Check employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    # Use canonical induction status function
    induction_status = await get_employee_induction_status(db, employee_id)
    
    # Map canonical items to the shape InductionChecklistPanel expects
    items = []
    for item in induction_status["items"]:
        items.append({
            "id": item["id"],
            "code": item.get("code"),
            "name": item["name"],
            "title": item.get("title") or item["name"],
            "description": item.get("description"),
            "mandatory": item["mandatory"],
            "status": item["status"],
            "rule_status": item.get("rule_status"),
            "completion_type": item.get("completion_type"),
            "evidence_sources": item.get("evidence_sources", []),
            "completion_rules": item.get("completion_rules", []),
            "completion_reason": item.get("completion_reason"),
            "status_reason": item.get("status_reason"),
            "next_action": item.get("next_action"),
            "required_for_unsupervised_work": item.get("required_for_unsupervised_work", True),
            "role_relevance": item.get("role_relevance"),
            "linked_evidence_ids": item.get("linked_evidence_ids", []),
            "linked_evidence": item.get("linked_evidence", []),
            "notes": item.get("notes"),
            "shadow_shift_signoff": item.get("shadow_shift_signoff"),
            "completed_at": item["completed_at"],
            "completed_by_name": item["completed_by_name"],
            "synced_from_training": item["synced_from_training"],
            "manual_action_allowed": item.get("manual_action_allowed", True),
        })
    
    now = datetime.now(timezone.utc).isoformat()
    completed_count = induction_status["completed"]
    overall_status = induction_status["overall_status"]
    # Map "not_started" to "pending" for frontend compat
    if overall_status == "not_started":
        overall_status = "pending"
    
    return {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "role": induction_status.get("role"),
        "role_normalized": induction_status.get("role_normalized"),
        "role_rule_warning": induction_status.get("role_rule_warning"),
        "rule_todos": induction_status.get("rule_todos", []),
        "items": items,
        "overall_status": overall_status,
        "started_at": now if completed_count > 0 else None,
        "completed_at": now if overall_status == "completed" else None,
        "auto_synced": any(i["synced_from_training"] for i in induction_status["items"]),
    }


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

    # Normalise items to list format (handles legacy dict-format records from UCE)
    ensure_checklist_list_format(checklist)
    
    shadow_shift_details = None
    if payload.item_name == "Shadow Shift Completed" and payload.status in ("completed", "pending"):
        if payload.status == "completed" or payload.shadow_shift_signoff:
            if not payload.shadow_shift_signoff:
                raise HTTPException(
                    status_code=422,
                    detail="Shadow Shift sign-off requires structured shift details.",
                )
            shadow_shift_details = _normalise_shadow_shift_signoff(
                payload.shadow_shift_signoff,
                user["user_id"],
                reviewer_name,
                now,
            )
            if payload.status == "completed" and not shadow_shift_details["ready_for_deployment"]:
                raise HTTPException(
                    status_code=422,
                    detail="Shadow Shift cannot be completed unless the outcome confirms ready for deployment.",
                )
            payload.notes = shadow_shift_details["summary_notes"]

    rule_metadata = get_induction_rule_metadata_by_name(payload.item_name)
    if payload.status == "completed" and rule_metadata.get("completion_type") == "automatic":
        raise HTTPException(
            status_code=422,
            detail="This induction item is completed automatically from verified evidence and cannot be manually completed."
        )

    # Find and update the specific item
    item_found = False
    for item in checklist["items"]:
        if item["name"] == payload.item_name:
            item["status"] = payload.status
            item["notes"] = payload.notes
            if shadow_shift_details is not None:
                item["shadow_shift_signoff"] = shadow_shift_details
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
            "shadow_shift_signoff": shadow_shift_details,
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
        {"$set": _without_mongo_id(checklist)},
        upsert=True
    )
    
    # Log audit
    await log_audit_action(user['user_id'], "induction_item_updated", "induction_checklist", employee_id, {
        "item_name": payload.item_name,
        "status": payload.status,
        "shadow_shift_ready_for_deployment": (
            shadow_shift_details.get("ready_for_deployment") if shadow_shift_details else None
        ),
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

    # Use canonical induction status (Stage 2: no more direct DB reads)
    induction_status = await get_employee_induction_status(db, employee_id)

    if induction_status["overall_status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Induction is not yet completed (status: {induction_status['overall_status']})"
        )

    # Build form_data expected by generate_induction_pdf_content
    checklist_items = []
    for item in induction_status["items"]:
        checklist_items.append({
            "name": item.get("name", ""),
            "completed": item.get("completed", False),
            "completed_date": item.get("completed_at", "")[:10] if item.get("completed_at") else "-",
            "completed_by": item.get("completed_by_name") or "",
            "notes": "",
        })

    # Fetch stored checklist for start/completion timestamps
    stored_checklist = await db.induction_checklists.find_one({"employee_id": employee_id}, {"_id": 0, "started_at": 1, "completed_at": 1, "notes": 1})

    form_data = {
        "start_date": (stored_checklist or {}).get("started_at", "")[:10] if (stored_checklist or {}).get("started_at") else "N/A",
        "completion_date": (stored_checklist or {}).get("completed_at", "")[:10] if (stored_checklist or {}).get("completed_at") else "N/A",
        "inductor_name": user.get("name") or user.get("email", "Admin"),
        "checklist_items": checklist_items,
        "notes": (stored_checklist or {}).get("notes") or "",
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


# ─────────────────────────────────────────────────────────────────────────────
# Care Certificate — Admin sign-off / return / submission-view endpoints
# ─────────────────────────────────────────────────────────────────────────────

from care_certificate_config import MANUAL_ITEM_CODES, HYBRID_ITEM_CODES, get_all_hybrid_forms, get_config_for_item


class HybridSignOffPayload(BaseModel):
    notes: Optional[str] = None


class HybridReturnPayload(BaseModel):
    return_reason: str


class ShadowShiftSignOffPayload(BaseModel):
    notes: Optional[str] = None
    shadow_shift_signoff: Optional[ShadowShiftDetailsPayload] = None


def _resolve_induction_item_target(item_identifier: str, submission: dict = None) -> dict:
    """
    Resolve canonical UI ids to the persisted induction submission/checklist target.

    Accepts the canonical item code used by the checklist UI, the worker form id
    used by worker submissions, or an existing submission id for compatibility.
    """
    cfg = get_config_for_item(item_identifier)
    resolved_by = "item_code" if cfg else None

    if not cfg:
        for hybrid in get_all_hybrid_forms():
            if hybrid.get("form_id") == item_identifier:
                cfg = get_config_for_item(hybrid.get("code"))
                resolved_by = "worker_form_id"
                break

    if not cfg and submission:
        submission_code = submission.get("item_code")
        if submission_code:
            cfg = get_config_for_item(submission_code)
            resolved_by = "submission_id"

    return {
        "cfg": cfg,
        "item_code": cfg.get("code") if cfg else item_identifier,
        "form_id": cfg.get("worker_form_id") if cfg else None,
        "resolved_by": resolved_by or "unresolved",
    }


@router.get("/employees/{employee_id}/induction/items/{item_code}/submission")
async def get_item_submission(
    employee_id: str,
    item_code: str,
    user: dict = Depends(require_manager_or_admin),
):
    """
    Admin: view the worker's submitted form for a hybrid induction item.
    Returns schema, submitted answers, and current submission status.
    """
    from care_certificate_forms import get_worker_form_schema
    db = get_db()

    submission_by_id = await db.induction_item_submissions.find_one(
        {"employee_id": employee_id, "id": item_code}, {"_id": 0}
    )
    target = _resolve_induction_item_target(item_code, submission_by_id)
    cfg = target["cfg"]
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Unknown induction item code: {item_code}")
    if cfg.get("completion_type") != "hybrid":
        raise HTTPException(status_code=400, detail="This item is not a hybrid form item.")

    form_id = target["form_id"]

    employee = await db.employees.find_one(
        {"id": employee_id}, {"_id": 0, "role": 1, "role_normalized": 1}
    )
    role_normalized = (employee or {}).get("role_normalized") or (employee or {}).get("role") or ""

    submission = submission_by_id or await db.induction_item_submissions.find_one(
        {"employee_id": employee_id, "form_id": form_id}, {"_id": 0}
    )

    schema = get_worker_form_schema(form_id, role_normalized)

    return {
        "item_code": target["item_code"],
        "form_id": form_id,
        "resolved_by": target["resolved_by"],
        "schema": schema,
        "submission": submission or {},
        "submission_status": (submission or {}).get("status"),
        "submitted_at": (submission or {}).get("submitted_at"),
        "submitted_data": (submission or {}).get("submitted_data"),
        "return_reason": (submission or {}).get("return_reason"),
        "admin_notes": (submission or {}).get("admin_notes"),
    }


@router.post("/employees/{employee_id}/induction/items/{item_code}/signoff")
async def signoff_induction_item(
    employee_id: str,
    item_code: str,
    payload: HybridSignOffPayload,
    user: dict = Depends(require_manager_or_admin),
):
    """
    Admin: sign off a hybrid or manual induction item.

    For hybrid items: requires submission status = 'submitted'.
    For manual (shadow_shift): structured shadow shift details are required; no worker submission needed.
    """
    db = get_db()

    submission_by_id = await db.induction_item_submissions.find_one(
        {"employee_id": employee_id, "id": item_code}, {"_id": 0}
    )
    target = _resolve_induction_item_target(item_code, submission_by_id)
    cfg = target["cfg"]
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Unknown induction item code: {item_code}")

    resolved_item_code = target["item_code"]
    completion_type = cfg.get("completion_type")
    if completion_type == "automatic":
        raise HTTPException(status_code=400, detail="Automatic items cannot be manually signed off.")

    now = datetime.now(timezone.utc).isoformat()

    admin = await db.users.find_one(
        {"$or": [{"user_id": user["user_id"]}, {"id": user["user_id"]}]},
        {"_id": 0, "name": 1, "first_name": 1, "last_name": 1, "email": 1},
    )
    admin_name = (admin or {}).get("name") or ""
    if not admin_name and admin:
        admin_name = f"{admin.get('first_name','')} {admin.get('last_name','')}".strip() or admin.get("email", "Admin")

    # ── Pre-flight: load checklist BEFORE writing anything ────────────────────
    # Fetched here so that a missing checklist fails atomically before any DB write.
    item_name = cfg["title"]
    logger.info(
        "induction signoff requested employee_id=%s input_item=%s resolved_item=%s form_id=%s resolved_by=%s payload_keys=%s",
        employee_id,
        item_code,
        resolved_item_code,
        target.get("form_id"),
        target.get("resolved_by"),
        list((payload.model_dump(exclude_none=True) or {}).keys()),
    )
    checklist = await db.induction_checklists.find_one({"employee_id": employee_id})

    if not checklist:
        # Auto-initialise on first sign-off rather than requiring a separate /fix call.
        from induction_definitions import DEFAULT_INDUCTION_ITEMS
        now_init = now
        checklist = {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "items": [
                {
                    "id": item_def["id"],
                    "name": item_def["name"],
                    "mandatory": item_def["mandatory"],
                    "status": "pending",
                    "completed_at": None,
                    "completed_by": None,
                    "completed_by_name": None,
                    "notes": None,
                }
                for item_def in DEFAULT_INDUCTION_ITEMS
            ],
            "overall_status": "pending",
            "started_at": None,
            "completed_at": None,
            "created_at": now_init,
            "updated_at": now_init,
        }
        await db.induction_checklists.insert_one({k: v for k, v in checklist.items() if k != "_id"})

    # Normalise items to list format (handles legacy dict-format records from UCE)
    ensure_checklist_list_format(checklist)

    # ── Hybrid items ──────────────────────────────────────────────────────────
    shadow_shift_details = None

    if completion_type == "hybrid":
        form_id = target["form_id"]
        submission = submission_by_id or await db.induction_item_submissions.find_one(
            {"employee_id": employee_id, "form_id": form_id}, {"_id": 0}
        )
        if not submission or submission.get("status") != "submitted":
            raise HTTPException(
                status_code=409,
                detail="Worker has not submitted this form yet. Cannot sign off.",
            )

        submission_filter = (
            {"employee_id": employee_id, "id": submission.get("id")}
            if submission.get("id")
            else {"employee_id": employee_id, "form_id": form_id}
        )
        await db.induction_item_submissions.update_one(
            submission_filter,
            {"$set": {
                "status": "signed_off",
                "signoff_by": user["user_id"],
                "signoff_by_name": admin_name,
                "signoff_at": now,
                "admin_notes": payload.notes,
                "updated_at": now,
            }},
        )

    # ── Manual items (shadow_shift) ───────────────────────────────────────────
    elif completion_type == "manual":
        if not payload.shadow_shift_signoff:
            raise HTTPException(
                status_code=422,
                detail="Structured Shadow Shift sign-off details are required for manual items.",
            )
        shadow_shift_details = _normalise_shadow_shift_signoff(
            payload.shadow_shift_signoff,
            user["user_id"],
            admin_name,
            now,
        )
        if not shadow_shift_details["ready_for_deployment"]:
            raise HTTPException(
                status_code=422,
                detail="Shadow Shift cannot be completed unless the outcome confirms ready for deployment.",
            )
        payload.notes = shadow_shift_details["summary_notes"]
    else:
        shadow_shift_details = None

    item_found = False
    for item in checklist["items"]:
        # Match by canonical id first (robust), then fall back to name string (legacy)
        if item.get("id") == resolved_item_code or item.get("id") == item_code or item.get("name") == item_name:
            item["status"] = "completed"
            item["completed_at"] = now
            item["completed_by"] = user["user_id"]
            item["completed_by_name"] = admin_name
            item["notes"] = payload.notes
            if completion_type == "manual" and shadow_shift_details is not None:
                item["shadow_shift_signoff"] = shadow_shift_details
            item_found = True
            break

    if not item_found:
        # Item missing from persisted checklist (legacy record or partially-initialised checklist).
        # Upsert the item rather than hard-failing — mirrors the behaviour of the generic update route.
        logger.warning(
            "signoff_induction_item: item_code=%r not found in checklist for employee=%r; upserting.",
            resolved_item_code, employee_id,
        )
        from induction_definitions import _STANDARDS_BY_ID
        std = _STANDARDS_BY_ID.get(resolved_item_code, {})
        new_item = {
            "id": resolved_item_code,
            "name": item_name,
            "mandatory": std.get("mandatory", True),
            "order": std.get("num"),
            "status": "completed",
            "completed_at": now,
            "completed_by": user["user_id"],
            "completed_by_name": admin_name,
            "notes": payload.notes,
        }
        if completion_type == "manual" and shadow_shift_details is not None:
            new_item["shadow_shift_signoff"] = shadow_shift_details
        checklist["items"].append(new_item)

    # Recalculate overall_status
    mandatory_completed = sum(1 for i in checklist["items"] if i.get("mandatory") and i["status"] == "completed")
    mandatory_total = sum(1 for i in checklist["items"] if i.get("mandatory"))
    any_completed = any(i["status"] == "completed" for i in checklist["items"])

    if mandatory_completed >= mandatory_total:
        checklist["overall_status"] = "completed"
        checklist["completed_at"] = now
    elif any_completed:
        checklist["overall_status"] = "in_progress"
        checklist.setdefault("started_at", now)
    else:
        checklist["overall_status"] = "pending"

    checklist["updated_at"] = now

    await db.induction_checklists.update_one(
        {"employee_id": employee_id}, {"$set": _without_mongo_id(checklist)}
    )

    await log_audit_action(
        user["user_id"], "induction_item_signed_off", "induction_checklist", employee_id,
        {
            "item_code": resolved_item_code,
            "completion_type": completion_type,
            "resolved_from": item_code,
            "resolved_by": target.get("resolved_by"),
            "admin_notes": payload.notes,
            "shadow_shift_ready_for_deployment": (
                shadow_shift_details.get("ready_for_deployment") if shadow_shift_details else None
            ),
        },
    )

    return {
        "ok": True,
        "item_code": resolved_item_code,
        "resolved_from": item_code,
        "resolved_by": target.get("resolved_by"),
        "signed_off_at": now,
        "signed_off_by": admin_name,
        "overall_status": checklist["overall_status"],
    }


@router.post("/employees/{employee_id}/induction/items/{item_code}/return")
async def return_induction_item(
    employee_id: str,
    item_code: str,
    payload: HybridReturnPayload,
    user: dict = Depends(require_manager_or_admin),
):
    """
    Admin: return a submitted hybrid induction form to the worker for correction.
    A return_reason is required.
    """
    db = get_db()

    submission_by_id = await db.induction_item_submissions.find_one(
        {"employee_id": employee_id, "id": item_code}, {"_id": 0}
    )
    target = _resolve_induction_item_target(item_code, submission_by_id)
    cfg = target["cfg"]
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Unknown induction item code: {item_code}")
    if cfg.get("completion_type") != "hybrid":
        raise HTTPException(status_code=400, detail="Only hybrid items can be returned for correction.")

    if not payload.return_reason.strip():
        raise HTTPException(status_code=422, detail="return_reason cannot be empty.")

    form_id = target["form_id"]
    now = datetime.now(timezone.utc).isoformat()

    submission = submission_by_id or await db.induction_item_submissions.find_one(
        {"employee_id": employee_id, "form_id": form_id}, {"_id": 0}
    )
    if not submission or submission.get("status") not in ("submitted", "signed_off"):
        raise HTTPException(
            status_code=409,
            detail="No submitted form found for this item. Cannot return.",
        )

    logger.info(
        "induction return requested employee_id=%s input_item=%s resolved_item=%s form_id=%s resolved_by=%s",
        employee_id,
        item_code,
        target.get("item_code"),
        form_id,
        target.get("resolved_by"),
    )
    submission_filter = (
        {"employee_id": employee_id, "id": submission.get("id")}
        if submission.get("id")
        else {"employee_id": employee_id, "form_id": form_id}
    )
    await db.induction_item_submissions.update_one(
        submission_filter,
        {"$set": {
            "status": "returned",
            "return_reason": payload.return_reason,
            "returned_at": now,
            "updated_at": now,
        }},
    )

    await log_audit_action(
        user["user_id"], "induction_item_returned", "induction_checklist", employee_id,
        {
            "item_code": target.get("item_code"),
            "form_id": form_id,
            "resolved_from": item_code,
            "resolved_by": target.get("resolved_by"),
            "return_reason": payload.return_reason,
        },
    )

    return {
        "ok": True,
        "item_code": target.get("item_code"),
        "form_id": form_id,
        "resolved_from": item_code,
        "resolved_by": target.get("resolved_by"),
        "returned_at": now,
        "return_reason": payload.return_reason,
    }


@router.get("/employees/{employee_id}/induction/care-certificate/status")
async def get_care_certificate_status(
    employee_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    """
    Admin: full Care Certificate status for an employee.

    Returns per-item detail including:
    - automatic item evidence links
    - hybrid item submission status and admin action required flag
    - manual item completion state
    - overall readiness (all 15 mandatory items complete)
    """
    from care_certificate_forms import get_worker_form_schema
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    induction_status = await get_employee_induction_status(db, employee_id)
    role_normalized = induction_status.get("role_normalized") or ""

    # Load all submissions in one query
    submission_map = {}
    async for sub in db.induction_item_submissions.find(
        {"employee_id": employee_id}, {"_id": 0}
    ):
        submission_map[sub["form_id"]] = sub

    items = []
    admin_action_required = 0

    for item in induction_status.get("items", []):
        code = item.get("code", "")
        cfg = get_config_for_item(code)
        form_id = cfg.get("worker_form_id") if cfg else None
        sub = submission_map.get(form_id) if form_id else None

        entry = {
            "code": code,
            "standard_number": cfg.get("standard_number") if cfg else None,
            "title": item.get("title") or item.get("name"),
            "completion_type": item.get("completion_type"),
            "status": item.get("status"),
            "rule_status": item.get("rule_status"),
            "mandatory": item.get("mandatory", True),
            "completed_at": item.get("completed_at"),
            "completed_by_name": item.get("completed_by_name"),
            "notes": item.get("notes"),
            "shadow_shift_signoff": item.get("shadow_shift_signoff"),
            "synced_from_training": item.get("synced_from_training", False),
            "linked_evidence": item.get("linked_evidence", []),
        }

        if form_id and sub:
            entry["submission_status"] = sub.get("status")
            entry["submitted_at"] = sub.get("submitted_at")
            entry["signoff_at"] = sub.get("signoff_at")
            entry["signoff_by_name"] = sub.get("signoff_by_name")
            entry["return_reason"] = sub.get("return_reason")
            entry["admin_notes"] = sub.get("admin_notes")
            # Flag items needing admin action
            if sub.get("status") == "submitted":
                entry["admin_action"] = "signoff_or_return"
                admin_action_required += 1
            else:
                entry["admin_action"] = None
        elif form_id:
            entry["submission_status"] = None
            entry["admin_action"] = None
        
        items.append(entry)

    items.sort(key=lambda x: x.get("standard_number") or 99)

    mandatory_done = sum(1 for i in items if i.get("mandatory") and i.get("status") == "completed")
    mandatory_total = sum(1 for i in items if i.get("mandatory"))

    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name','')} {employee.get('last_name','')}".strip(),
        "role": induction_status.get("role"),
        "overall_status": induction_status.get("overall_status"),
        "mandatory_completed": mandatory_done,
        "mandatory_total": mandatory_total,
        "admin_action_required_count": admin_action_required,
        "items": items,
    }
