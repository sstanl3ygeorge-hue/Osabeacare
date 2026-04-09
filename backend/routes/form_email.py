"""
Form Email Routes - Send forms via email and public form completion.

This module handles:
- Sending form requests to employees via email
- Public form completion (token-based, no auth required)
- Form-to-requirement mapping
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from .dependencies import (
    get_db, get_current_user, require_manager_or_admin,
    log_audit_action
)

router = APIRouter(tags=["Form Email"])


# Form to requirement mapping
FORM_TO_REQUIREMENT_MAPPING = {
    "staff_health_questionnaire": "staff_health_questionnaire",
    "staff_personal_info": "staff_personal_info",
    "hmrc_starter_checklist": "hmrc_starter_checklist",
    "interview_record": "interview_record",
    "equal_opportunities": "equal_opportunities",
    "induction": "induction",
    "recruitment_checklist": "recruitment_checklist",
    "application_form": "application_form"
}


@router.post("/employees/{employee_id}/send-form")
async def send_form_to_employee_email(
    employee_id: str,
    form_type: str = Query(..., description="Form type: staff_health_questionnaire, staff_personal_info, hmrc_starter_checklist, interview_record"),
    message: Optional[str] = Query(None, description="Optional custom message"),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Send a form request to an employee via email.
    
    Creates an email request with a secure token link for form completion.
    The employee can complete the form without logging in.
    
    Forms are linked to requirement slots and appear in What's Needed after submission.
    """
    # Import from server lazily to avoid circular imports
    from server import FORM_BASED_REQUIREMENTS, EmailRequestService, RequestType
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.get('email'):
        raise HTTPException(status_code=400, detail="Employee has no email address")
    
    # Validate form type
    if form_type not in FORM_BASED_REQUIREMENTS:
        raise HTTPException(status_code=400, detail=f"Invalid form type: {form_type}")
    
    form_template = FORM_BASED_REQUIREMENTS[form_type]
    form_name = form_template.get('name', form_type.replace('_', ' ').title())
    
    # Map to requirement ID
    requirement_id = FORM_TO_REQUIREMENT_MAPPING.get(form_type, form_type)
    
    # Check for existing pending request
    existing = await db.email_requests.find_one({
        "person_id": employee_id,
        "requirement_id": requirement_id,
        "request_type": RequestType.COMPLETE_FORM.value,
        "status": {"$in": ["pending_send", "sent", "clicked", "action_started"]}
    })
    
    if existing:
        return {
            "status": "duplicate",
            "message": f"A form request for {form_name} is already pending",
            "existing_request_id": existing.get("id")
        }
    
    # Create email request via EmailRequestService
    result = await EmailRequestService.create_request(
        person_id=employee_id,
        person_type="employee",
        requirement_id=requirement_id,
        request_type=RequestType.COMPLETE_FORM,
        due_days=14,
        context={"custom_message": message, "form_name": form_name} if message else {"form_name": form_name},
        admin_id=user.get('user_id')
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("reason"))
    
    await log_audit_action(user['user_id'], "form_request_sent", "employee", employee_id, {
        "form_type": form_type,
        "requirement_id": requirement_id
    })
    
    return {
        "status": "success",
        "message": f"Form request sent to {employee.get('email')}",
        "form_type": form_type,
        "request_id": result.get("request_id")
    }


@router.get("/forms/complete/{token}")
async def get_form_for_completion(token: str):
    """
    Public endpoint - Get form data for completion using token.
    No authentication required.
    """
    # Import from server lazily to avoid circular imports
    from server import FORM_BASED_REQUIREMENTS, EmailRequestService, RequestType
    
    db = get_db()
    
    # Validate token
    result = await EmailRequestService.validate_and_use_token(token)
    
    if result.get("status") not in ["valid", "valid_no_request"]:
        raise HTTPException(status_code=400, detail=result.get("reason", "Invalid or expired token"))
    
    request_data = result.get("request")
    token_data = result.get("token_data", {})
    
    # Handle both EmailRequest object and dict from token_data
    if request_data:
        # EmailRequest object - access attributes directly
        request_type = getattr(request_data, 'request_type', None)
        if hasattr(request_type, 'value'):
            request_type = request_type.value
        if request_type != RequestType.COMPLETE_FORM.value:
            raise HTTPException(status_code=400, detail="This token is not for form completion")
        employee_id = getattr(request_data, 'person_id', None)
        requirement_id = getattr(request_data, 'requirement_id', None)
        request_id_val = getattr(request_data, 'id', None)
    elif token_data:
        # Fallback to token_data dict
        if token_data.get("action_type") != "complete_form":
            raise HTTPException(status_code=400, detail="This token is not for form completion")
        employee_id = token_data.get("person_id")
        requirement_id = token_data.get("requirement_id")
        request_id_val = None
    else:
        raise HTTPException(status_code=400, detail="Request not found")
    
    # Get employee data for auto-fill
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Determine form type from requirement_id
    form_type = requirement_id
    for ft, req_id in FORM_TO_REQUIREMENT_MAPPING.items():
        if req_id == requirement_id:
            form_type = ft
            break
    
    if form_type not in FORM_BASED_REQUIREMENTS:
        raise HTTPException(status_code=400, detail=f"Form type not found: {form_type}")
    
    form_template = FORM_BASED_REQUIREMENTS[form_type]
    
    # Build auto-fill data from employee - comprehensive mapping
    auto_fill_data = {}
    
    # Core fields
    if employee.get('first_name'):
        auto_fill_data['first_name'] = employee['first_name']
    if employee.get('last_name'):
        auto_fill_data['last_name'] = employee['last_name']
    if employee.get('email'):
        auto_fill_data['email'] = employee['email']
    if employee.get('phone'):
        auto_fill_data['phone'] = employee['phone']
        auto_fill_data['mobile'] = employee['phone']
    if employee.get('date_of_birth'):
        auto_fill_data['date_of_birth'] = employee['date_of_birth']
        auto_fill_data['dob'] = employee['date_of_birth']
    if employee.get('ni_number'):
        auto_fill_data['ni_number'] = employee['ni_number']
        auto_fill_data['national_insurance_number'] = employee['ni_number']
    
    # Address fields
    if employee.get('address'):
        auto_fill_data['address'] = employee['address']
        auto_fill_data['address_line_1'] = employee['address']
    if employee.get('address_line_2'):
        auto_fill_data['address_line_2'] = employee['address_line_2']
    if employee.get('city'):
        auto_fill_data['city'] = employee['city']
    if employee.get('postcode'):
        auto_fill_data['postcode'] = employee['postcode']
    
    # Emergency contact
    if employee.get('emergency_contact_name'):
        auto_fill_data['emergency_contact_name'] = employee['emergency_contact_name']
    if employee.get('emergency_contact_phone'):
        auto_fill_data['emergency_contact_phone'] = employee['emergency_contact_phone']
    if employee.get('emergency_contact_relationship'):
        auto_fill_data['emergency_contact_relationship'] = employee['emergency_contact_relationship']
    
    # Next of kin
    if employee.get('next_of_kin_name'):
        auto_fill_data['next_of_kin_name'] = employee['next_of_kin_name']
    if employee.get('next_of_kin_phone'):
        auto_fill_data['next_of_kin_phone'] = employee['next_of_kin_phone']
    if employee.get('next_of_kin_relationship'):
        auto_fill_data['next_of_kin_relationship'] = employee['next_of_kin_relationship']
    
    # Bank details (from HMRC/payroll forms)
    if employee.get('bank_name'):
        auto_fill_data['bank_name'] = employee['bank_name']
    if employee.get('bank_sort_code'):
        auto_fill_data['bank_sort_code'] = employee['bank_sort_code']
    if employee.get('bank_account_number'):
        auto_fill_data['bank_account_number'] = employee['bank_account_number']
    
    # Generate full name variants
    full_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    if full_name:
        auto_fill_data['full_name'] = full_name
        auto_fill_data['name'] = full_name
        auto_fill_data['employee_name'] = full_name
    
    return {
        "employee_id": employee_id,
        "employee_name": full_name,
        "form_type": form_type,
        "requirement_id": requirement_id,
        "request_id": request_id_val,
        "form_template": form_template,
        "auto_fill_data": auto_fill_data
    }


@router.post("/forms/complete/{token}")
async def submit_form_via_token(token: str, form_data: dict):
    """
    Public endpoint - Submit a completed form using token.
    No authentication required - uses token for verification.
    
    Creates a form submission record and updates the email request status.
    """
    # Import from server lazily to avoid circular imports
    from server import FORM_BASED_REQUIREMENTS, EmailRequestService, RequestType
    
    db = get_db()
    
    # Validate token
    result = await EmailRequestService.validate_and_use_token(token)
    
    if result.get("status") not in ["valid", "valid_no_request"]:
        raise HTTPException(status_code=400, detail=result.get("reason", "Invalid or expired token"))
    
    request_data = result.get("request")
    token_data = result.get("token_data", {})
    
    # Handle both EmailRequest object and dict from token_data
    if request_data:
        employee_id = getattr(request_data, 'person_id', None)
        requirement_id = getattr(request_data, 'requirement_id', None)
        request_id_val = getattr(request_data, 'id', None)
    elif token_data:
        employee_id = token_data.get("person_id")
        requirement_id = token_data.get("requirement_id")
        request_id_val = None
    else:
        raise HTTPException(status_code=400, detail="Request not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Determine form type
    form_type = requirement_id
    for ft, req_id in FORM_TO_REQUIREMENT_MAPPING.items():
        if req_id == requirement_id:
            form_type = ft
            break
    
    now = datetime.now(timezone.utc).isoformat()
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    # Create form submission
    submission_id = str(uuid.uuid4())
    submission = {
        "id": submission_id,
        "employee_id": employee_id,
        "form_type": form_type,
        "requirement_id": requirement_id,
        "submitted_data": form_data,
        "submitted_at": now,
        "submitted_by": None,  # Public submission
        "submitted_by_name": employee_name,
        "verified": False,
        "status": "submitted",
        "source": "email_link",
        "request_id": request_id_val
    }
    
    await db.form_submissions.insert_one(submission)
    
    # Update email request status
    if request_id_val:
        await db.email_requests.update_one(
            {"id": request_id_val},
            {"$set": {
                "status": "completed",
                "completed_at": now,
                "completion_data": {"submission_id": submission_id}
            }}
        )
    
    # Create document record for requirement slot
    doc_id = str(uuid.uuid4())
    doc_record = {
        "id": doc_id,
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "document_type_id": form_type,
        "original_filename": f"{form_type}_submission.json",
        "file_url": None,  # Data stored in form_submissions
        "mime_type": "application/json",
        "file_size": 0,
        "uploaded_at": now,
        "uploaded_by": None,
        "uploaded_by_name": employee_name,
        "verified": False,
        "status": "active",
        "source": "form_submission",
        "form_submission_id": submission_id
    }
    
    await db.employee_documents.insert_one(doc_record)
    
    return {
        "status": "success",
        "message": "Form submitted successfully. It will be reviewed by the recruitment team.",
        "submission_id": submission_id,
        "document_id": doc_id
    }
