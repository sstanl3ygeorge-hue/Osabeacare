"""
Competency Records Routes - CQC Compliant Competency Tracking.

This module handles:
- Competency assessment records (medication, manual handling, etc.)
- Role-based competency requirements
- Scheduling future assessments
- Expiry tracking and reminders
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import (
    get_db, get_current_user, require_admin, require_manager_or_admin,
    log_audit_action
)

router = APIRouter(tags=["Competency Records"])


# Default competency types required for different roles
DEFAULT_COMPETENCY_REQUIREMENTS = {
    "healthcare_assistant": [
        {"competency_type": "manual_handling", "competency_name": "Moving & Handling", "is_critical": True, "review_frequency_months": 12},
        {"competency_type": "medication", "competency_name": "Medication Administration", "is_critical": True, "review_frequency_months": 12},
        {"competency_type": "safeguarding", "competency_name": "Safeguarding Adults", "is_critical": True, "review_frequency_months": 12},
    ],
    "senior_carer": [
        {"competency_type": "manual_handling", "competency_name": "Moving & Handling", "is_critical": True, "review_frequency_months": 12},
        {"competency_type": "medication", "competency_name": "Medication Administration", "is_critical": True, "review_frequency_months": 12},
        {"competency_type": "safeguarding", "competency_name": "Safeguarding Adults", "is_critical": True, "review_frequency_months": 12},
        {"competency_type": "supervision", "competency_name": "Staff Supervision", "is_critical": True, "review_frequency_months": 12},
    ],
    "nurse": [
        {"competency_type": "clinical_competency", "competency_name": "Clinical Competency", "is_critical": True, "review_frequency_months": 12},
        # Use "medication_competency" to match UCE/WRE gate key.
        # The engines accept both "medication" and "medication_competency" via alias map.
        {"competency_type": "medication_competency", "competency_name": "Medication Administration Competency", "is_critical": True, "review_frequency_months": 12},
        {"competency_type": "manual_handling", "competency_name": "Moving & Handling", "is_critical": True, "review_frequency_months": 12},
    ],
}

# All competency types available in the system
COMPETENCY_TYPES = [
    {"value": "medication", "label": "Medication Administration", "is_critical": True},
    # "medication_competency" is the canonical key expected by UCE / WRE readiness gates.
    {"value": "medication_competency", "label": "Medication Administration Competency (Nurse)", "is_critical": True},
    {"value": "manual_handling", "label": "Moving & Handling", "is_critical": True},
    {"value": "safeguarding", "label": "Safeguarding Adults", "is_critical": True},
    {"value": "dementia_care", "label": "Dementia Care", "is_critical": False},
    {"value": "learning_disabilities", "label": "Learning Disabilities", "is_critical": False},
    {"value": "mental_health", "label": "Mental Health Awareness", "is_critical": False},
    {"value": "end_of_life", "label": "End of Life Care", "is_critical": False},
    {"value": "catheter_care", "label": "Catheter Care", "is_critical": False},
    {"value": "stoma_care", "label": "Stoma Care", "is_critical": False},
    {"value": "peg_feeding", "label": "PEG Feeding", "is_critical": False},
    {"value": "wound_care", "label": "Wound Care", "is_critical": False},
    {"value": "diabetes", "label": "Diabetes Management", "is_critical": False},
    {"value": "epilepsy", "label": "Epilepsy Management", "is_critical": False},
    {"value": "parkinsons", "label": "Parkinson's Care", "is_critical": False},
    {"value": "choking", "label": "Choking Management", "is_critical": False},
    {"value": "challenging_behaviour", "label": "Challenging Behaviour", "is_critical": False},
    {"value": "clinical_competency", "label": "Clinical Competency", "is_critical": True},
    {"value": "supervision", "label": "Staff Supervision", "is_critical": False},
]


class CompetencyRecordCreate(BaseModel):
    competency_type: str
    competency_name: str
    status: str  # competent, not_competent, training_required
    review_due_date: Optional[str] = None
    review_due_at: Optional[str] = None
    notes: Optional[str] = None
    evidence_document_id: Optional[str] = None


class CompetencyScheduleRequest(BaseModel):
    competency_type: str
    competency_name: str
    scheduled_date: str
    notes: Optional[str] = None


class CompetencyRecordResultRequest(BaseModel):
    status: str  # competent, not_competent, training_required
    notes: Optional[str] = None
    review_due_date: Optional[str] = None
    review_due_at: Optional[str] = None


def _resolve_review_due_alias(review_due_date: Optional[str], review_due_at: Optional[str]) -> Optional[str]:
    """Prefer explicit review_due_at input, then fall back to review_due_date."""
    return review_due_at or review_due_date


def _apply_review_due_alias(record: dict) -> dict:
    """Ensure competency payload exposes both review_due_date and review_due_at."""
    due_value = record.get("review_due_date") or record.get("review_due_at")
    if due_value:
        record["review_due_date"] = due_value
        record["review_due_at"] = due_value
    return record


@router.get("/employees/{employee_id}/competencies")
async def get_employee_competencies(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all competency records for an employee"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    competencies = await db.competency_records.find(
        {"employee_id": employee_id}
    ).sort("assessed_at", -1).to_list(100)
    
    # Format for JSON serialization
    formatted = []
    for c in competencies:
        c.pop("_id", None)
        formatted.append(_apply_review_due_alias(c))
    
    return {"competencies": formatted}


@router.post("/employees/{employee_id}/competencies")
async def create_competency_record(
    employee_id: str,
    payload: CompetencyRecordCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new competency assessment record"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get assessor name
    assessor = await db.users.find_one(
        {"$or": [{"user_id": user['user_id']}, {"id": user['user_id']}]}, 
        {"_id": 0, "name": 1, "first_name": 1, "last_name": 1, "email": 1}
    )
    assessor_name = assessor.get('name') if assessor else user.get('email', 'Admin')
    if not assessor_name and assessor:
        assessor_name = f"{assessor.get('first_name', '')} {assessor.get('last_name', '')}".strip() or assessor.get('email', 'Admin')
    
    # Parse review_due_date
    review_due = _resolve_review_due_alias(payload.review_due_date, payload.review_due_at)
    
    competency_id = str(uuid.uuid4())
    
    competency = {
        "id": competency_id,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "competency_type": payload.competency_type,
        "competency_name": payload.competency_name,
        "status": payload.status,
        "assessed_by": user['user_id'],
        "assessed_by_name": assessor_name,
        "assessed_at": now,
        "review_due_date": review_due,
        "review_due_at": review_due,
        "notes": payload.notes,
        "evidence_document_id": payload.evidence_document_id,
        "created_at": now,
        "updated_at": now,
        "audit": {
            "created_by": user['user_id'],
            "created_by_name": assessor_name,
            "created_at": now,
            "assessment_history": [
                {
                    "status": payload.status,
                    "assessed_by": user['user_id'],
                    "assessed_by_name": assessor_name,
                    "assessed_at": now,
                    "notes": payload.notes
                }
            ]
        }
    }
    
    await db.competency_records.insert_one(competency)
    
    # Log audit
    await log_audit_action(user['user_id'], "competency_assessed", "competency_record", competency_id, {
        "employee_id": employee_id,
        "competency_type": payload.competency_type,
        "competency_name": payload.competency_name,
        "status": payload.status
    })
    
    return {"success": True, "id": competency_id, "status": payload.status}


@router.put("/employees/{employee_id}/competencies/{competency_id}")
async def update_competency_record(
    employee_id: str,
    competency_id: str,
    payload: CompetencyRecordCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update an existing competency assessment"""
    db = get_db()
    
    existing = await db.competency_records.find_one({
        "id": competency_id,
        "employee_id": employee_id
    })
    
    if not existing:
        raise HTTPException(status_code=404, detail="Competency record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get assessor name
    assessor = await db.users.find_one(
        {"$or": [{"user_id": user['user_id']}, {"id": user['user_id']}]}, 
        {"_id": 0, "name": 1, "first_name": 1, "last_name": 1, "email": 1}
    )
    assessor_name = assessor.get('name') if assessor else user.get('email', 'Admin')
    if not assessor_name and assessor:
        assessor_name = f"{assessor.get('first_name', '')} {assessor.get('last_name', '')}".strip() or assessor.get('email', 'Admin')
    
    # History entry
    history_entry = {
        "status": payload.status,
        "assessed_by": user['user_id'],
        "assessed_by_name": assessor_name,
        "assessed_at": now,
        "notes": payload.notes
    }
    
    update_data = {
        "status": payload.status,
        "assessed_by": user['user_id'],
        "assessed_by_name": assessor_name,
        "assessed_at": now,
        "review_due_date": _resolve_review_due_alias(payload.review_due_date, payload.review_due_at),
        "review_due_at": _resolve_review_due_alias(payload.review_due_date, payload.review_due_at),
        "notes": payload.notes,
        "evidence_document_id": payload.evidence_document_id,
        "updated_at": now,
        "audit.last_modified_by": user['user_id'],
        "audit.last_modified_by_name": assessor_name,
        "audit.last_modified_at": now
    }
    
    await db.competency_records.update_one(
        {"id": competency_id},
        {
            "$set": update_data,
            "$push": {"audit.assessment_history": history_entry}
        }
    )
    
    # Log audit
    await log_audit_action(user['user_id'], "competency_updated", "competency_record", competency_id, {
        "employee_id": employee_id,
        "old_status": existing.get("status"),
        "new_status": payload.status
    })
    
    return {"success": True, "id": competency_id, "status": payload.status}


@router.post("/employees/{employee_id}/competencies/schedule")
async def schedule_competency_assessment(
    employee_id: str,
    payload: CompetencyScheduleRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Schedule a future competency assessment.
    Creates a record with 'scheduled' status and sets up reminder dates.
    Reminders will be triggered at 60, 30, and 7 days before the scheduled date.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create the scheduled assessment record
    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "employee_id": employee_id,
        "competency_type": payload.competency_type,
        "competency_name": payload.competency_name,
        "status": "scheduled",
        "scheduled_date": payload.scheduled_date,
        "notes": payload.notes,
        "scheduled_by": user['user_id'],
        "scheduled_at": now,
        "created_at": now,
        "assessment_history": [{
            "date": now,
            "action": "scheduled",
            "scheduled_date": payload.scheduled_date,
            "by": user['user_id'],
            "notes": payload.notes
        }],
        # Reminder tracking
        "reminder_60_sent": False,
        "reminder_30_sent": False,
        "reminder_7_sent": False
    }
    
    await db.competency_records.insert_one(record)
    
    await log_audit_action(user['user_id'], "schedule_competency_assessment", "competency_record", record_id, {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "competency_type": payload.competency_type,
        "scheduled_date": payload.scheduled_date
    })
    
    return {
        "success": True,
        "id": record_id,
        "message": f"Assessment scheduled for {payload.scheduled_date}"
    }


@router.put("/employees/{employee_id}/competencies/{competency_id}/record-result")
async def record_competency_result(
    employee_id: str,
    competency_id: str,
    payload: CompetencyRecordResultRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Record the result of a competency assessment.
    Updates the status and sets the next review due date (defaults to 1 year from today).
    """
    db = get_db()
    
    record = await db.competency_records.find_one({"id": competency_id, "employee_id": employee_id})
    if not record:
        raise HTTPException(status_code=404, detail="Competency record not found")
    
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
    # Calculate review due date (default 1 year from today)
    if payload.review_due_at or payload.review_due_date:
        review_due = _resolve_review_due_alias(payload.review_due_date, payload.review_due_at)
    else:
        review_due = (now + timedelta(days=365)).strftime('%Y-%m-%d')
    
    # Get user info for history
    user_info = await db.users.find_one(
        {"$or": [{"user_id": user['user_id']}, {"id": user['user_id']}]},
        {"_id": 0, "name": 1, "email": 1}
    )
    user_name = user_info.get("name", user_info.get("email", "Admin")) if user_info else "Admin"
    
    # Add to history
    history_entry = {
        "date": now_str,
        "action": "result_recorded",
        "status": payload.status,
        "by": user['user_id'],
        "by_name": user_name,
        "notes": payload.notes
    }
    
    update_data = {
        "status": payload.status,
        "assessment_date": now_str,
        "assessed_by": user['user_id'],
        "assessed_by_name": user_name,
        "review_due_date": review_due,
        "review_due_at": review_due,
        "last_assessed": now_str,
        "notes": payload.notes
    }
    
    await db.competency_records.update_one(
        {"id": competency_id},
        {
            "$set": update_data,
            "$push": {"assessment_history": history_entry}
        }
    )
    
    await log_audit_action(user['user_id'], "record_competency_result", "competency_record", competency_id, {
        "employee_id": employee_id,
        "competency_type": record.get("competency_type"),
        "status": payload.status,
        "review_due_date": review_due
    })
    
    return {
        "success": True,
        "status": payload.status,
        "review_due_date": review_due,
        "message": f"Result recorded. Next review due: {review_due}"
    }


@router.get("/employees/{employee_id}/missing-competencies")
async def get_missing_competencies(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get missing or expiring competencies for an employee based on their role.
    Used for work readiness blocking and dashboard alerts.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "role": 1, "system_role": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Determine role requirements
    role = employee.get("role", "").lower().replace(" ", "_")
    system_role = employee.get("system_role", "HCA")
    
    # Map to competency requirements
    if system_role == "NURSE":
        role_key = "nurse"
    elif "senior" in role:
        role_key = "senior_carer"
    else:
        role_key = "healthcare_assistant"
    
    required = DEFAULT_COMPETENCY_REQUIREMENTS.get(role_key, DEFAULT_COMPETENCY_REQUIREMENTS["healthcare_assistant"])
    
    # Get existing competencies
    existing = await db.competency_records.find(
        {"employee_id": employee_id}
    ).to_list(100)
    
    existing_map = {c["competency_type"]: c for c in existing}
    
    missing = []
    expiring_soon = []
    now = datetime.now(timezone.utc)
    
    for req in required:
        comp_type = req["competency_type"]
        existing_comp = existing_map.get(comp_type)
        
        if not existing_comp:
            missing.append({
                "competency_type": comp_type,
                "competency_name": req["competency_name"],
                "is_critical": req.get("is_critical", True),
                "status": "missing"
            })
        elif existing_comp.get("status") != "competent":
            missing.append({
                "competency_type": comp_type,
                "competency_name": req["competency_name"],
                "is_critical": req.get("is_critical", True),
                "status": existing_comp.get("status"),
                "current_assessment": {
                    "assessed_at": existing_comp.get("assessed_at"),
                    "assessed_by_name": existing_comp.get("assessed_by_name")
                }
            })
        elif existing_comp.get("review_due_date") or existing_comp.get("review_due_at"):
            try:
                due_str = existing_comp.get("review_due_date") or existing_comp.get("review_due_at")
                if isinstance(due_str, str):
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                else:
                    due_date = due_str
                days_until = (due_date - now).days
                if days_until <= 30:
                    expiring_soon.append({
                        "competency_type": comp_type,
                        "competency_name": req["competency_name"],
                        "review_due_date": due_str,
                        "review_due_at": due_str,
                        "days_until_due": days_until,
                        "is_critical": req.get("is_critical", True)
                    })
            except (ValueError, TypeError):
                pass
    
    has_critical_missing = any(m.get("is_critical", True) for m in missing)
    
    return {
        "missing_competencies": missing,
        "expiring_soon": expiring_soon,
        "has_critical_missing": has_critical_missing,
        "role_requirements": required
    }


@router.get("/competency-types")
async def get_competency_types(user: dict = Depends(get_current_user)):
    """Return all available competency types"""
    return {"competency_types": COMPETENCY_TYPES}
