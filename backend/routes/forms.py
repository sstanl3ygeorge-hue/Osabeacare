"""
Forms Management Routes Module

This module handles form submission and generated form endpoints including:
- Form templates (health screening, induction, etc.)
- Form submissions CRUD
- Form verification and rejection
- PDF generation and download
- Generated forms (template-based forms)
- Auto-fill from employee data

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from .dependencies import (
    get_db,
    get_current_user,
    get_current_worker,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Forms & Submissions"])


# ==================== MODELS ====================

class FormSubmissionCreate(BaseModel):
    employee_id: str
    requirement_id: str  # e.g., "health_screening", "induction"
    form_type: str
    data: dict  # JSON form data


class FormSubmissionUpdate(BaseModel):
    data: Optional[dict] = None
    verified: Optional[bool] = None
    verified_by: Optional[str] = None
    notes: Optional[str] = None


class FormSubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_id: str
    requirement_id: Optional[str] = None
    form_type: str
    data: Optional[dict] = None
    form_data: Optional[dict] = None
    submitted_at: str
    submitted_by: Optional[str] = None
    submitted_by_name: Optional[str] = None
    verified: bool = False
    verified_by: Optional[str] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[str] = None
    rejected_by: Optional[str] = None
    rejected_by_name: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    review_status: Optional[str] = None
    review_reason: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    status: str = "submitted"
    version: int = 1
    notes: Optional[str] = None


class GeneratedFormCreate(BaseModel):
    template_id: str
    employee_id: str
    form_data: Dict[str, Any] = {}


class GeneratedFormUpdate(BaseModel):
    form_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    employee_signature: Optional[str] = None
    employee_signed_at: Optional[str] = None
    admin_signature: Optional[str] = None
    admin_signed_at: Optional[str] = None
    notes: Optional[str] = None


class GeneratedFormResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    template_id: str
    template_name: Optional[str] = None
    template_category: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    form_data: Dict[str, Any] = {}
    status: str
    employee_signature: Optional[str] = None
    employee_signed_at: Optional[str] = None
    admin_signature: Optional[str] = None
    admin_signed_at: Optional[str] = None
    admin_signoff_by: Optional[str] = None
    pdf_url: Optional[str] = None
    locked: bool = False
    notes: Optional[str] = None
    version: int = 1
    access_token: Optional[str] = None
    created_at: str
    updated_at: str
    sent_at: Optional[str] = None
    viewed_at: Optional[str] = None
    completed_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    signed_off_at: Optional[str] = None
    requirement_id: Optional[str] = None
    imported: bool = False
    original_filename: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

def get_form_requirements():
    """Get form-based requirements from server module"""
    # Import here to avoid circular imports - FORM_BASED_REQUIREMENTS stays in server.py
    # because it's a large constant used by multiple modules
    import sys
    server = sys.modules.get('server')
    if server and hasattr(server, 'FORM_BASED_REQUIREMENTS'):
        return server.FORM_BASED_REQUIREMENTS
    return {}


async def auto_fill_employee_data(employee_id: str) -> dict:
    """Get employee data for auto-filling forms"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return {}
    
    # Build full address
    address_parts = [
        employee.get("address_line_1", ""),
        employee.get("address_line_2", ""),
        employee.get("city", ""),
        employee.get("county", ""),
        employee.get("postcode", "")
    ]
    full_address = ", ".join([p for p in address_parts if p])
    
    return {
        "full_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "first_name": employee.get("first_name", ""),
        "last_name": employee.get("last_name", ""),
        "date_of_birth": employee.get("date_of_birth", ""),
        "email": employee.get("email", ""),
        "phone": employee.get("phone", ""),
        "mobile": employee.get("mobile", employee.get("phone", "")),
        "address": full_address,
        "full_address": full_address,
        "address_line_1": employee.get("address_line_1", ""),
        "address_line_2": employee.get("address_line_2", ""),
        "city": employee.get("city", ""),
        "county": employee.get("county", ""),
        "postcode": employee.get("postcode", ""),
        "role": employee.get("role", ""),
        "job_title": employee.get("role", ""),
        "employee_code": employee.get("employee_code") or employee.get("applicant_reference") or "",
        "ni_number": employee.get("ni_number", ""),
        "start_date": employee.get("start_date", ""),
        "emergency_contact_name": employee.get("emergency_contact_name", ""),
        "emergency_contact_phone": employee.get("emergency_contact_phone", ""),
        "emergency_contact_relationship": employee.get("emergency_contact_relationship", ""),
    }


# ==================== FORM TEMPLATES ROUTES ====================

@router.get("/form-submissions/templates")
async def get_form_templates(user: dict = Depends(get_current_user)):
    """Get all available form templates"""
    FORM_BASED_REQUIREMENTS = get_form_requirements()
    templates = []
    for req_id, req_data in FORM_BASED_REQUIREMENTS.items():
        templates.append({
            "requirement_id": req_id,
            "name": req_data.get("name"),
            "form_type": req_data.get("form_type"),
            "auto_fill_fields": req_data.get("auto_fill_fields", []),
            "sections_count": len(req_data.get("sections", [])),
        })
    return templates


@router.get("/form-submissions/template/{requirement_id}")
async def get_form_template(requirement_id: str, user: dict = Depends(get_current_user)):
    """Get a specific form template schema"""
    FORM_BASED_REQUIREMENTS = get_form_requirements()
    if requirement_id not in FORM_BASED_REQUIREMENTS:
        raise HTTPException(status_code=404, detail=f"Form template not found: {requirement_id}")
    return FORM_BASED_REQUIREMENTS[requirement_id]


@router.get("/form-submissions/auto-fill/{requirement_id}/{employee_id}")
async def get_form_auto_fill(
    requirement_id: str,
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get auto-fill data for a form based on employee profile"""
    FORM_BASED_REQUIREMENTS = get_form_requirements()
    if requirement_id not in FORM_BASED_REQUIREMENTS:
        raise HTTPException(status_code=404, detail=f"Form template not found: {requirement_id}")
    
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    auto_fill_data = await auto_fill_employee_data(employee_id)
    template = FORM_BASED_REQUIREMENTS[requirement_id]
    
    # Map auto-fill fields from template
    result = {}
    for field_name in template.get("auto_fill_fields", []):
        if field_name in auto_fill_data:
            result[field_name] = auto_fill_data[field_name]
    
    # Also check sections for auto_fill definitions
    for section in template.get("sections", []):
        for field in section.get("fields", []):
            auto_fill_key = field.get("auto_fill")
            if auto_fill_key and auto_fill_key in auto_fill_data:
                result[field["id"]] = auto_fill_data[auto_fill_key]
    
    return {
        "requirement_id": requirement_id,
        "employee_id": employee_id,
        "auto_fill_data": result
    }


# ==================== FORM SUBMISSIONS CRUD ====================

@router.post("/form-submissions", response_model=FormSubmissionResponse)
async def create_form_submission(
    submission: FormSubmissionCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new form submission"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": submission.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check for existing submission (for supersede pattern)
    existing = await db.form_submissions.find_one({
        "employee_id": submission.employee_id,
        "requirement_id": submission.requirement_id,
        "status": {"$in": ["submitted", "verified"]}
    })
    
    version = 1
    if existing:
        # Mark existing as superseded
        await db.form_submissions.update_one(
            {"id": existing["id"]},
            {"$set": {"status": "superseded", "superseded_at": now}}
        )
        version = existing.get("version", 1) + 1
    
    submission_id = str(uuid.uuid4())
    submission_doc = {
        "id": submission_id,
        "employee_id": submission.employee_id,
        "requirement_id": submission.requirement_id,
        "form_type": submission.form_type,
        "data": submission.data,
        "form_data": submission.data,  # Alias for compatibility
        "submitted_at": now,
        "submitted_by": user.get("user_id"),
        "verified": False,
        "status": "submitted",
        "review_status": None,
        "review_reason": None,
        "reviewed_at": None,
        "reviewed_by": None,
        "reviewed_by_name": None,
        "version": version,
        "created_at": now,
        "updated_at": now,
    }
    
    await db.form_submissions.insert_one(submission_doc)
    
    # Get submitter name
    submitter = await db.users.find_one({"user_id": user.get("user_id")}, {"_id": 0})
    submission_doc["submitted_by_name"] = submitter.get("name") if submitter else None
    
    await log_audit_action(
        user['user_id'],
        "create_form_submission",
        "form_submission",
        submission_id,
        {"requirement_id": submission.requirement_id, "employee_id": submission.employee_id}
    )
    
    return FormSubmissionResponse(**submission_doc)


@router.get("/form-submissions")
async def list_form_submissions(
    employee_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    form_type: Optional[str] = None,
    status: Optional[str] = None,
    verified: Optional[bool] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """List form submissions with optional filters"""
    db = get_db()
    query = {}
    
    if employee_id:
        query["employee_id"] = employee_id
    if requirement_id:
        query["requirement_id"] = requirement_id
    if form_type:
        query["form_type"] = form_type
    if status:
        query["status"] = status
    elif verified is not None:
        query["verified"] = verified
    
    submissions = await db.form_submissions.find(query, {"_id": 0}).sort("submitted_at", -1).limit(limit).to_list(limit)
    
    # Enrich with user names
    user_ids = set()
    for s in submissions:
        if s.get("submitted_by"):
            user_ids.add(s["submitted_by"])
        if s.get("verified_by"):
            user_ids.add(s["verified_by"])
    
    users = {}
    if user_ids:
        user_docs = await db.users.find({"user_id": {"$in": list(user_ids)}}, {"_id": 0}).to_list(100)
        users = {u["user_id"]: u.get("name", "") for u in user_docs}
    
    for s in submissions:
        s["submitted_by_name"] = users.get(s.get("submitted_by"), "")
        s["verified_by_name"] = users.get(s.get("verified_by"), "")
    
    return submissions


@router.get("/form-submissions/{submission_id}")
async def get_form_submission(submission_id: str, user: dict = Depends(get_current_user)):
    """Get a specific form submission"""
    db = get_db()
    submission = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.put("/form-submissions/{submission_id}", response_model=FormSubmissionResponse)
async def update_form_submission(
    submission_id: str,
    update: FormSubmissionUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a form submission"""
    db = get_db()
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_dict = {"updated_at": now}
    
    if update.data is not None:
        update_dict["data"] = update.data
        update_dict["form_data"] = update.data
    if update.notes is not None:
        update_dict["notes"] = update.notes
    
    await db.form_submissions.update_one({"id": submission_id}, {"$set": update_dict})
    
    updated = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    return FormSubmissionResponse(**updated)


@router.post("/form-submissions/{submission_id}/verify")
async def verify_form_submission(
    submission_id: str,
    notes: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """Verify a form submission"""
    db = get_db()
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "verified": True,
            "verified_by": user.get("user_id"),
            "verified_at": now,
            "status": "verified",
            "review_status": "verified",
            "review_reason": None,
            "reviewed_at": now,
            "reviewed_by": user.get("user_id"),
            "reviewed_by_name": user.get("name"),
            "notes": notes,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "verify_form_submission",
        "form_submission",
        submission_id,
        {"employee_id": submission["employee_id"]}
    )
    
    return {"message": "Form submission verified", "id": submission_id}


@router.post("/form-submissions/{submission_id}/unverify")
async def unverify_form_submission(
    submission_id: str,
    reason: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Remove verification from a form submission (admin only)"""
    db = get_db()
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "verified": False,
            "verified_by": None,
            "verified_at": None,
            "status": "submitted",
            "review_status": "pending",
            "review_reason": None,
            "reviewed_at": now,
            "reviewed_by": user.get("user_id"),
            "reviewed_by_name": user.get("name"),
            "unverified_by": user.get("user_id"),
            "unverified_at": now,
            "unverify_reason": reason,
            "updated_at": now
        }}
    )
    
    return {"message": "Verification removed", "id": submission_id}


@router.post("/form-submissions/{submission_id}/reject")
async def reject_form_submission(
    submission_id: str,
    reason: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Reject a form submission with reason"""
    db = get_db()
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": user.get("user_id"),
            "rejected_by_name": user.get("name"),
            "rejected_at": now,
            "rejection_reason": reason,
            "review_status": "rejected",
            "review_reason": reason,
            "reviewed_at": now,
            "reviewed_by": user.get("user_id"),
            "reviewed_by_name": user.get("name"),
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "reject_form_submission",
        "form_submission",
        submission_id,
        {"reason": reason}
    )
    
    return {"message": "Form submission rejected", "id": submission_id}


@router.delete("/form-submissions/{submission_id}")
async def delete_form_submission(
    submission_id: str,
    user: dict = Depends(require_admin)
):
    """Delete a form submission (admin only)"""
    db = get_db()
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    await db.form_submissions.delete_one({"id": submission_id})
    
    await log_audit_action(
        user['user_id'],
        "delete_form_submission",
        "form_submission",
        submission_id,
        {"employee_id": submission["employee_id"]}
    )
    
    return {"message": "Form submission deleted", "id": submission_id}


# ==================== GENERATED FORMS ROUTES ====================

@router.post("/generated-forms", response_model=GeneratedFormResponse)
async def create_generated_form(
    form: GeneratedFormCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new generated form from a template"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get template
    template = await db.templates.find_one({"id": form.template_id, "active": True}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or inactive")
    
    # Get employee
    employee = await db.employees.find_one({"id": form.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Auto-fill employee data
    auto_fill_data = await auto_fill_employee_data(form.employee_id)
    merged_data = {**auto_fill_data, **form.form_data}
    
    form_id = str(uuid.uuid4())
    access_token = str(uuid.uuid4())
    
    form_doc = {
        "id": form_id,
        "template_id": form.template_id,
        "template_name": template.get("name"),
        "template_category": template.get("category"),
        "employee_id": form.employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_code": employee.get("employee_code"),
        "form_data": merged_data,
        "status": "draft",
        "locked": False,
        "version": 1,
        "access_token": access_token,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("user_id"),
    }
    
    await db.generated_forms.insert_one(form_doc)
    
    return GeneratedFormResponse(**form_doc)


@router.get("/generated-forms", response_model=List[GeneratedFormResponse])
async def list_generated_forms(
    employee_id: Optional[str] = None,
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """List generated forms with optional filters"""
    db = get_db()
    query = {}
    
    if employee_id:
        query["employee_id"] = employee_id
    if template_id:
        query["template_id"] = template_id
    if status:
        query["status"] = status
    
    forms = await db.generated_forms.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [GeneratedFormResponse(**f) for f in forms]


@router.get("/generated-forms/{form_id}", response_model=GeneratedFormResponse)
async def get_generated_form(form_id: str, user: dict = Depends(get_current_user)):
    """Get a specific generated form"""
    db = get_db()
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Generated form not found")
    return GeneratedFormResponse(**form)


@router.put("/generated-forms/{form_id}", response_model=GeneratedFormResponse)
async def update_generated_form(
    form_id: str,
    update: GeneratedFormUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a generated form"""
    db = get_db()
    form = await db.generated_forms.find_one({"id": form_id})
    if not form:
        raise HTTPException(status_code=404, detail="Generated form not found")
    
    if form.get("locked"):
        raise HTTPException(status_code=400, detail="Form is locked and cannot be edited")
    
    now = datetime.now(timezone.utc).isoformat()
    update_dict = {"updated_at": now}
    
    for field, value in update.model_dump(exclude_none=True).items():
        update_dict[field] = value
    
    await db.generated_forms.update_one({"id": form_id}, {"$set": update_dict})
    
    updated = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    return GeneratedFormResponse(**updated)


@router.post("/generated-forms/{form_id}/signoff")
async def signoff_generated_form(
    form_id: str,
    admin_signature: str,
    notes: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """Admin sign-off on a generated form"""
    db = get_db()
    form = await db.generated_forms.find_one({"id": form_id})
    if not form:
        raise HTTPException(status_code=404, detail="Generated form not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {
            "admin_signature": admin_signature,
            "admin_signed_at": now,
            "admin_signoff_by": user.get("user_id"),
            "signed_off_at": now,
            "status": "signed_off",
            "locked": True,
            "notes": notes,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "signoff_generated_form",
        "generated_form",
        form_id,
        {"employee_id": form["employee_id"]}
    )
    
    return {"message": "Form signed off", "id": form_id}


@router.post("/generated-forms/{form_id}/archive")
async def archive_generated_form(
    form_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Archive a generated form"""
    db = get_db()
    form = await db.generated_forms.find_one({"id": form_id})
    if not form:
        raise HTTPException(status_code=404, detail="Generated form not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {
            "status": "archived",
            "archived_at": now,
            "archived_by": user.get("user_id"),
            "updated_at": now
        }}
    )
    
    return {"message": "Form archived", "id": form_id}
