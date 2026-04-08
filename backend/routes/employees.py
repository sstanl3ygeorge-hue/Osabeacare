"""
Employee CRUD Routes Module

This module handles core employee operations including:
- Employee/Applicant CRUD
- Personal details management
- Employment history
- Declarations
- Archive/Restore functionality

NOTE: Employee training, professional registrations, and contract endpoints
remain in server.py due to complex dependencies.

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
    UserRole,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Employee Management"])


# ==================== CONSTANTS ====================

class EmployeeStatus:
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW = "interview"
    COMPLIANCE_REVIEW = "compliance_review"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PersonStage:
    APPLICANT = "applicant"
    EMPLOYEE = "employee"
    ARCHIVED = "archived"


APPLICANT_STATUSES = [
    EmployeeStatus.NEW,
    EmployeeStatus.SCREENING,
    EmployeeStatus.INTERVIEW,
    EmployeeStatus.COMPLIANCE_REVIEW
]

EMPLOYEE_STATUSES = [
    EmployeeStatus.ONBOARDING,
    EmployeeStatus.ACTIVE,
    EmployeeStatus.INACTIVE
]


def get_person_stage(status: str) -> str:
    """Determine person stage from status"""
    if status in APPLICANT_STATUSES:
        return PersonStage.APPLICANT
    elif status in EMPLOYEE_STATUSES:
        return PersonStage.EMPLOYEE
    elif status == EmployeeStatus.ARCHIVED:
        return PersonStage.ARCHIVED
    return PersonStage.APPLICANT


# ==================== MODELS ====================

class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "Healthcare Assistant"
    status: Optional[str] = EmployeeStatus.NEW
    date_of_birth: Optional[str] = None
    ni_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None


class EmployeeResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    employee_code: Optional[str] = None
    applicant_reference: Optional[str] = None
    date_of_birth: Optional[str] = None
    ni_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    completion_percentage: Optional[int] = 0
    recruitment_approved: Optional[bool] = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        extra = "ignore"


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    date_of_birth: Optional[str] = None
    ni_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None


class PersonalDetailsUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    ni_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postcode: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None


class EmploymentHistoryEntry(BaseModel):
    employer: str
    job_title: str
    start_date: str
    end_date: Optional[str] = None
    is_current: bool = False
    duties: Optional[str] = None
    reason_for_leaving: Optional[str] = None


class DeclarationsUpdate(BaseModel):
    has_criminal_convictions: Optional[bool] = None
    criminal_convictions_details: Optional[str] = None
    has_disciplinary_actions: Optional[bool] = None
    disciplinary_actions_details: Optional[str] = None
    fit_to_work: Optional[bool] = None
    health_conditions: Optional[str] = None
    dbs_consent: Optional[bool] = None


# ==================== HELPER FUNCTIONS ====================

async def generate_employee_code() -> str:
    """Generate unique employee code in format EMP-XXXX"""
    db = get_db()
    
    last_emp = await db.employees.find_one(
        {"employee_code": {"$regex": "^EMP-\\d+$"}},
        sort=[("employee_code", -1)]
    )
    
    if last_emp and last_emp.get("employee_code"):
        try:
            last_num = int(last_emp["employee_code"].split("-")[1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1001
    else:
        new_num = 1001
    
    return f"EMP-{new_num:04d}"


async def calculate_basic_completion(employee: dict) -> int:
    """Calculate basic completion percentage"""
    db = get_db()
    
    # Basic fields
    fields = ["first_name", "last_name", "email", "phone", "date_of_birth", "ni_number"]
    completed = sum(1 for f in fields if employee.get(f))
    
    # Documents
    doc_count = await db.employee_documents.count_documents({
        "employee_id": employee["id"],
        "verified": True
    })
    
    total = len(fields) + 5  # fields + expected documents
    completed_total = completed + min(doc_count, 5)
    
    return min(100, int((completed_total / total) * 100))


# ==================== EMPLOYEE CRUD ====================

@router.post("/employees/simple", response_model=EmployeeResponse)
async def create_employee_simple(
    employee: EmployeeCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Create a new employee/applicant record (simplified version).
    
    For the full version with all features, use the endpoint in server.py.
    """
    db = get_db()
    
    employee_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Determine initial stage based on status
    initial_status = employee.status or EmployeeStatus.NEW
    person_stage = get_person_stage(initial_status)
    
    employee_doc = {
        "id": employee_id,
        **employee.model_dump(),
        "completion_percentage": 0,
        "created_at": now,
        "updated_at": now
    }
    
    # Assign appropriate identifier
    if person_stage == PersonStage.EMPLOYEE:
        employee_code = await generate_employee_code()
        employee_doc["employee_code"] = employee_code
    else:
        applicant_ref = f"APP-{uuid.uuid4().hex[:8].upper()}"
        employee_doc["applicant_reference"] = applicant_ref
        employee_doc["employee_code"] = None
    
    await db.employees.insert_one(employee_doc)
    
    await log_audit_action(
        user['user_id'],
        "create_employee",
        "employee",
        employee_id,
        {"email": employee.email}
    )
    
    return EmployeeResponse(**employee_doc)


@router.get("/employees-simple/list")
async def list_employees_simple(
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """
    List employees with optional filtering (simplified version).
    
    For the full version with all features, use /employees endpoint in server.py.
    """
    db = get_db()
    
    query = {}
    
    # Stage filter
    if stage == PersonStage.APPLICANT:
        query["status"] = {"$in": APPLICANT_STATUSES}
    elif stage == PersonStage.EMPLOYEE:
        query["status"] = {"$in": EMPLOYEE_STATUSES}
    elif status:
        query["status"] = status
    else:
        # Exclude archived by default
        query["status"] = {"$ne": EmployeeStatus.ARCHIVED}
    
    if role:
        query["role"] = role
    
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"employee_code": {"$regex": search, "$options": "i"}},
            {"applicant_reference": {"$regex": search, "$options": "i"}}
        ]
    
    employees = await db.employees.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    # Add person_stage
    for emp in employees:
        emp["person_stage"] = get_person_stage(emp.get("status", EmployeeStatus.NEW))
    
    return employees


@router.get("/employees/{employee_id}/details")
async def get_employee_details(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get detailed employee information"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee["person_stage"] = get_person_stage(employee.get("status", EmployeeStatus.NEW))
    employee["completion_percentage"] = await calculate_basic_completion(employee)
    
    # Get document count
    doc_count = await db.employee_documents.count_documents({"employee_id": employee_id})
    employee["document_count"] = doc_count
    
    # Get training count
    training_count = await db.training_records.count_documents({"employee_id": employee_id})
    employee["training_count"] = training_count
    
    return employee


@router.put("/employees/{employee_id}/update")
async def update_employee_simple(
    employee_id: str,
    update_data: EmployeeUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update employee information (simplified version)"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_doc = {
        k: v for k, v in update_data.model_dump().items() if v is not None
    }
    update_doc["updated_at"] = now
    update_doc["updated_by"] = user.get("user_id")
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_doc})
    
    await log_audit_action(
        user['user_id'],
        "update_employee",
        "employee",
        employee_id,
        update_doc
    )
    
    updated = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    return updated


@router.put("/employees/{employee_id}/personal-details-update")
async def update_personal_details(
    employee_id: str,
    details: PersonalDetailsUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update employee personal details"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_doc = {
        k: v for k, v in details.model_dump().items() if v is not None
    }
    update_doc["updated_at"] = now
    update_doc["updated_by"] = user.get("user_id")
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_doc})
    
    await log_audit_action(
        user['user_id'],
        "update_personal_details",
        "employee",
        employee_id,
        {"fields_updated": list(update_doc.keys())}
    )
    
    return {"success": True, "message": "Personal details updated"}


@router.post("/employees/{employee_id}/employment-history-add")
async def add_employment_history(
    employee_id: str,
    entry: EmploymentHistoryEntry,
    user: dict = Depends(require_manager_or_admin)
):
    """Add employment history entry"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    history = employee.get("employment_history", [])
    new_entry = {
        "id": str(uuid.uuid4()),
        **entry.model_dump(),
        "added_at": now,
        "added_by": user.get("user_id")
    }
    history.append(new_entry)
    
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "employment_history": history,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "add_employment_history",
        "employee",
        employee_id,
        {"employer": entry.employer, "job_title": entry.job_title}
    )
    
    return {"success": True, "entry_id": new_entry["id"]}


@router.put("/employees/{employee_id}/declarations-update")
async def update_declarations(
    employee_id: str,
    declarations: DeclarationsUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update employee declarations"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_doc = {
        k: v for k, v in declarations.model_dump().items() if v is not None
    }
    
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "declarations": update_doc,
                "declarations_updated_at": now,
                "declarations_updated_by": user.get("user_id"),
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "update_declarations",
        "employee",
        employee_id,
        {"fields_updated": list(update_doc.keys())}
    )
    
    return {"success": True, "message": "Declarations updated"}


# ==================== ARCHIVE / RESTORE ====================

@router.post("/employees/{employee_id}/archive-employee")
async def archive_employee(
    employee_id: str,
    reason: str = Body(..., embed=True),
    user: dict = Depends(require_admin)
):
    """Archive an employee"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.get("status") == EmployeeStatus.ARCHIVED:
        return {"status": "already_archived", "message": "Employee is already archived"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "status": EmployeeStatus.ARCHIVED,
                "previous_status": employee.get("status"),
                "archived_at": now,
                "archived_by": user.get("user_id"),
                "archive_reason": reason,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "archive_employee",
        "employee",
        employee_id,
        {"reason": reason, "previous_status": employee.get("status")}
    )
    
    return {"success": True, "message": "Employee archived"}


@router.post("/employees/{employee_id}/restore-employee")
async def restore_employee(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """Restore an archived employee"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.get("status") != EmployeeStatus.ARCHIVED:
        return {"status": "not_archived", "message": "Employee is not archived"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Restore to previous status or default to onboarding
    restore_status = employee.get("previous_status", EmployeeStatus.ONBOARDING)
    
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "status": restore_status,
                "restored_at": now,
                "restored_by": user.get("user_id"),
                "updated_at": now
            },
            "$unset": {
                "archived_at": "",
                "archived_by": "",
                "archive_reason": ""
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "restore_employee",
        "employee",
        employee_id,
        {"restored_to_status": restore_status}
    )
    
    return {"success": True, "message": f"Employee restored to {restore_status}"}


# ==================== EMPLOYEE SEARCH ====================

@router.get("/employee-stats/search")
async def search_employees(
    q: str = Query(..., min_length=2),
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Search employees by name, email, or code"""
    db = get_db()
    
    query = {
        "$or": [
            {"first_name": {"$regex": q, "$options": "i"}},
            {"last_name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"employee_code": {"$regex": q, "$options": "i"}},
            {"applicant_reference": {"$regex": q, "$options": "i"}}
        ],
        "status": {"$ne": EmployeeStatus.ARCHIVED}
    }
    
    results = await db.employees.find(
        query,
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1, 
         "employee_code": 1, "applicant_reference": 1, "role": 1, "status": 1}
    ).limit(limit).to_list(limit)
    
    # Add full name for convenience
    for r in results:
        r["full_name"] = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
    
    return {
        "results": results,
        "count": len(results),
        "query": q
    }


# ==================== EMPLOYEE COUNTS ====================

@router.get("/employee-stats/counts")
async def get_employee_counts(user: dict = Depends(get_current_user)):
    """Get employee counts by status and stage"""
    db = get_db()
    
    counts = {
        "by_status": {},
        "by_stage": {
            "applicant": 0,
            "employee": 0,
            "archived": 0
        },
        "total": 0
    }
    
    # Count by status
    all_statuses = APPLICANT_STATUSES + EMPLOYEE_STATUSES + [EmployeeStatus.ARCHIVED]
    for status in all_statuses:
        count = await db.employees.count_documents({"status": status})
        counts["by_status"][status] = count
        counts["total"] += count
        
        # Aggregate by stage
        if status in APPLICANT_STATUSES:
            counts["by_stage"]["applicant"] += count
        elif status in EMPLOYEE_STATUSES:
            counts["by_stage"]["employee"] += count
        elif status == EmployeeStatus.ARCHIVED:
            counts["by_stage"]["archived"] += count
    
    return counts
