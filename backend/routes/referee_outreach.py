"""
NHS-Level Referee Outreach System Routes.

This module handles:
- Sending reference requests to referees via email
- Public referee form completion (no auth required)
- Reference review and verification workflow
- 2-step verification (Manager review -> Admin verify)
- Mismatch detection and documentation
"""

import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from .dependencies import (
    get_db, get_current_user, require_admin, require_manager_or_admin,
    log_audit_action, SENDER_EMAIL
)

router = APIRouter(tags=["Referee Outreach"])

# Get portal URL from environment
PORTAL_URL = os.environ.get('PORTAL_URL', os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:3000'))

# Referee form template - comprehensive NHS-compliant reference form
REFEREE_FORM_TEMPLATE = {
    "id": "referee_reference_form",
    "name": "Employment Reference Request",
    "sections": [
        {
            "id": "referee_details",
            "title": "Your Details (Referee)",
            "fields": [
                {"id": "referee_full_name", "label": "Your Full Name", "type": "text", "required": True},
                {"id": "referee_job_title", "label": "Your Job Title/Role", "type": "text", "required": True},
                {"id": "referee_organisation", "label": "Organisation Name", "type": "text", "required": True},
                {"id": "referee_work_email", "label": "Work Email", "type": "text", "required": True},
                {"id": "referee_phone", "label": "Contact Phone", "type": "text", "required": True},
            ]
        },
        {
            "id": "relationship",
            "title": "Your Relationship to the Applicant",
            "fields": [
                {"id": "relationship_type", "label": "Relationship", "type": "select", "required": True,
                 "options": ["Line Manager", "Senior Manager", "HR Manager", "Director", "Supervisor", "Colleague (Senior)", "Other"]},
                {"id": "relationship_other", "label": "If Other, please specify", "type": "text", "required": False,
                 "conditional_on": "relationship_type", "conditional_value": "Other"},
                {"id": "known_from_date", "label": "Known the applicant since (date)", "type": "date", "required": True},
                {"id": "known_to_date", "label": "Until (date)", "type": "date", "required": False},
                {"id": "employment_dates_confirm", "label": "Can you confirm the employment dates provided by the applicant?", "type": "select", "required": True,
                 "options": ["Yes - dates are correct", "No - dates differ", "Unable to confirm"]},
                {"id": "employment_dates_notes", "label": "If dates differ, please provide correct dates", "type": "textarea", "required": False,
                 "conditional_on": "employment_dates_confirm", "conditional_value": "No - dates differ"},
            ]
        },
        {
            "id": "suitability",
            "title": "Suitability Assessment",
            "fields": [
                {"id": "job_title_held", "label": "Job title held by the applicant", "type": "text", "required": True},
                {"id": "reason_for_leaving", "label": "Reason for leaving (if known)", "type": "textarea", "required": False},
                {"id": "performance_rating", "label": "Overall performance while employed", "type": "select", "required": True,
                 "options": ["Excellent", "Good", "Satisfactory", "Below expectations", "Unable to comment"]},
                {"id": "reliability", "label": "Reliability and timekeeping", "type": "select", "required": True,
                 "options": ["Excellent", "Good", "Satisfactory", "Concerns noted", "Unable to comment"]},
                {"id": "professionalism", "label": "Professionalism and conduct", "type": "select", "required": True,
                 "options": ["Excellent", "Good", "Satisfactory", "Concerns noted", "Unable to comment"]},
                {"id": "teamwork", "label": "Ability to work with others", "type": "select", "required": True,
                 "options": ["Excellent", "Good", "Satisfactory", "Concerns noted", "Unable to comment"]},
                {"id": "safeguarding_concerns", "label": "Are you aware of any safeguarding concerns?", "type": "select", "required": True,
                 "options": ["No concerns", "Yes - see notes", "Unable to comment"]},
                {"id": "safeguarding_notes", "label": "Safeguarding details (if applicable)", "type": "textarea", "required": False,
                 "conditional_on": "safeguarding_concerns", "conditional_value": "Yes - see notes"},
                {"id": "disciplinary_record", "label": "Any disciplinary issues on record?", "type": "select", "required": True,
                 "options": ["No issues", "Yes - see notes", "Unable to comment"]},
                {"id": "disciplinary_notes", "label": "Disciplinary details (if applicable)", "type": "textarea", "required": False,
                 "conditional_on": "disciplinary_record", "conditional_value": "Yes - see notes"},
                {"id": "would_re_employ", "label": "Would you re-employ this person?", "type": "select", "required": True,
                 "options": ["Yes", "Yes with reservations", "No", "Unable to comment"]},
                {"id": "re_employ_notes", "label": "Additional comments on re-employment", "type": "textarea", "required": False},
            ]
        },
        {
            "id": "care_suitability",
            "title": "Suitability for Care Work",
            "fields": [
                {"id": "care_vulnerable_suitable", "label": "Is this person suitable to work with vulnerable adults or children?", "type": "select", "required": True,
                 "options": ["Yes - suitable", "Yes with conditions", "No", "Unable to comment"]},
                {"id": "care_suitability_notes", "label": "Any additional comments on suitability for care work", "type": "textarea", "required": False},
            ]
        },
        {
            "id": "declaration",
            "title": "Declaration",
            "fields": [
                {"id": "declaration_accurate", "label": "I confirm that the information provided is true and accurate to the best of my knowledge", "type": "checkbox", "required": True},
                {"id": "declaration_authority", "label": "I confirm I have authority to provide this reference on behalf of my organisation", "type": "checkbox", "required": True},
            ]
        }
    ]
}


class ReferenceVerifyRequest(BaseModel):
    action: str  # 'verify' or 'reject'
    notes: Optional[str] = None
    mismatch_reason: Optional[str] = None


@router.post("/employees/{employee_id}/send-reference-request")
async def send_reference_request_to_referee(
    employee_id: str,
    reference_num: int = Query(..., description="Reference number: 1 or 2"),
    message: Optional[str] = Query(None, description="Optional custom message to referee"),
    force_resend: bool = Query(False, description="If true, resend even when a pending request exists"),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Send a reference request directly to the referee via email.
    
    Creates a secure token link for the referee to complete the reference form
    without needing to log in.
    
    NHS-Level Requirements:
    - Referee email must be provided
    - Request status tracked: requested -> awaiting_response -> submitted -> awaiting_review -> verified
    - Response attached to correct requirement slot (reference_1 or reference_2)
    """
    # Lazy import resend to avoid circular imports
    try:
        import resend
    except ImportError:
        resend = None
    
    db = get_db()
    
    if reference_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="reference_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get referee details from declared data
    prefix = f"reference_{reference_num}_"
    referee_name = employee.get(f"{prefix}name")
    referee_email = employee.get(f"{prefix}email")
    
    if not referee_email:
        raise HTTPException(status_code=400, detail=f"Reference {reference_num} email not provided. Update employee profile first.")
    
    if not referee_name:
        raise HTTPException(status_code=400, detail=f"Reference {reference_num} name not provided. Update employee profile first.")
    
    # Check if request already pending
    existing_status = employee.get(f"{prefix}request_status")
    if existing_status in ["requested", "awaiting_response"] and not force_resend:
        return {
            "status": "duplicate",
            "message": "Reference request already sent and awaiting response",
            "current_status": existing_status
        }
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee with request tracking
    update_fields = {
        f"{prefix}request_status": "requested",
        f"{prefix}request_sent_at": now,
        f"{prefix}request_token": token
    }

    # Track resend metadata when explicitly resending an existing pending request
    if force_resend and existing_status in ["requested", "awaiting_response"]:
        update_fields[f"{prefix}resend_count"] = int(employee.get(f"{prefix}resend_count", 0) or 0) + 1
        update_fields[f"{prefix}last_reminder_at"] = now

    await db.employees.update_one(
        {"id": employee_id},
        {"$set": update_fields}
    )
    
    # Prepare email
    applicant_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    referee_form_url = f"{PORTAL_URL}/referee/complete/{token}"
    
    email_subject = f"Reference Request for {applicant_name}"
    email_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #0d6c6c;">Employment Reference Request</h2>
        <p>Dear {referee_name},</p>
        <p>We are conducting pre-employment checks for <strong>{applicant_name}</strong> who has applied 
        for a position with Osabea Healthcare Solutions and has provided your details as a referee.</p>
        {f'<p style="color: #555; border-left: 3px solid #0d6c6c; padding-left: 15px; margin: 20px 0;">{message}</p>' if message else ''}
        <p>We would be grateful if you could complete the online reference form by clicking the link below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{referee_form_url}" style="background-color: #0d6c6c; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                Complete Reference Form
            </a>
        </p>
        <p>This secure link is unique to you and will expire in 30 days.</p>
        <p>If you have any questions or prefer to provide the reference by phone, please contact our recruitment team.</p>
        <p>Thank you for your assistance with this important process.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #888; font-size: 12px;">Osabea Healthcare Solutions - Safer Recruitment</p>
        <p style="color: #888; font-size: 12px;">This email contains a secure link - please do not forward.</p>
    </div>
    """
    
    # Send email
    email_sent = False
    try:
        if resend and resend.api_key:
            resend.Emails.send({
                "from": SENDER_EMAIL,
                "to": [referee_email],
                "subject": email_subject,
                "html": email_body
            })
            email_sent = True
            
            # Update status to awaiting_response
            await db.employees.update_one(
                {"id": employee_id},
                {"$set": {f"{prefix}request_status": "awaiting_response"}}
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send referee email: {e}")
    
    await log_audit_action(user['user_id'], "send_reference_request", "employee", employee_id, {
        "reference_num": reference_num,
        "referee_name": referee_name,
        "referee_email": referee_email,
        "email_sent": email_sent
    })
    
    return {
        "status": "success" if email_sent else "email_failed",
        "message": f"Reference request sent to {referee_name} ({referee_email})" if email_sent else "Request created but email failed",
        "reference_num": reference_num,
        "referee_email": referee_email,
        "request_status": "awaiting_response" if email_sent else "requested"
    }


@router.get("/referee/complete/{token}")
async def get_referee_form(token: str):
    """
    Public endpoint - Get referee form for completion using token.
    No authentication required.
    """
    db = get_db()
    
    # Find employee by reference request token
    employee = await db.employees.find_one({
        "$or": [
            {"reference_1_request_token": token},
            {"reference_2_request_token": token}
        ]
    }, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid or expired reference link")
    
    # Determine which reference this is for
    ref_num = 1 if employee.get("reference_1_request_token") == token else 2
    prefix = f"reference_{ref_num}_"
    
    # Check if already submitted
    current_status = employee.get(f"{prefix}request_status")
    if current_status in ["submitted", "awaiting_review", "verified", "rejected"]:
        raise HTTPException(status_code=400, detail="This reference has already been submitted")
    
    # Check token age (30 day expiry)
    sent_at = employee.get(f"{prefix}request_sent_at")
    if sent_at:
        try:
            sent_date = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            if (datetime.now(timezone.utc) - sent_date).days > 30:
                raise HTTPException(status_code=400, detail="This reference link has expired. Please contact the recruitment team.")
        except (ValueError, TypeError):
            pass
    
    # Get applicant info for context
    applicant_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    declared_referee_name = employee.get(f"{prefix}name", "")
    declared_company = employee.get(f"{prefix}company", "")
    declared_job_title = employee.get(f"{prefix}job_title", "")
    
    return {
        "employee_id": employee['id'],
        "reference_num": ref_num,
        "applicant_name": applicant_name,
        "declared_referee_details": {
            "name": declared_referee_name,
            "company": declared_company,
            "job_title": declared_job_title
        },
        "form_template": REFEREE_FORM_TEMPLATE
    }


@router.post("/referee/complete/{token}")
async def submit_referee_form(token: str, form_data: dict):
    """
    Public endpoint - Submit referee reference form.
    No authentication required - uses token for verification.
    
    Attaches response to employee record and correct requirement slot.
    """
    db = get_db()
    
    # Find employee
    employee = await db.employees.find_one({
        "$or": [
            {"reference_1_request_token": token},
            {"reference_2_request_token": token}
        ]
    }, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid or expired reference link")
    
    ref_num = 1 if employee.get("reference_1_request_token") == token else 2
    prefix = f"reference_{ref_num}_"
    requirement_id = f"reference_{ref_num}"
    
    # Check if already submitted
    current_status = employee.get(f"{prefix}request_status")
    if current_status in ["submitted", "awaiting_review", "verified", "rejected"]:
        raise HTTPException(status_code=400, detail="This reference has already been submitted")
    
    # Validate required fields
    required_fields = ["referee_full_name", "referee_job_title", "referee_organisation", "referee_work_email",
                       "relationship_type", "known_from_date", "performance_rating", "reliability",
                       "professionalism", "care_vulnerable_suitable", "declaration_accurate", "declaration_authority"]
    
    missing = [f for f in required_fields if not form_data.get(f)]
    if missing:
        raise HTTPException(status_code=400, detail=f"Required fields missing: {', '.join(missing[:5])}")
    
    if not form_data.get("declaration_accurate") or not form_data.get("declaration_authority"):
        raise HTTPException(status_code=400, detail="Both declarations must be confirmed")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Detect mismatches between declared and returned details
    declared_name = employee.get(f"{prefix}name", "").lower().strip()
    returned_name = form_data.get("referee_full_name", "").lower().strip()
    declared_company = employee.get(f"{prefix}company", "").lower().strip()
    returned_company = form_data.get("referee_organisation", "").lower().strip()
    
    mismatch_detected = False
    mismatch_reasons = []
    
    if declared_name and returned_name and declared_name != returned_name:
        mismatch_detected = True
        mismatch_reasons.append(f"Name: declared '{employee.get(f'{prefix}name')}' vs returned '{form_data.get('referee_full_name')}'")
    
    if declared_company and returned_company and declared_company != returned_company:
        mismatch_detected = True
        mismatch_reasons.append(f"Organisation: declared '{employee.get(f'{prefix}company')}' vs returned '{form_data.get('referee_organisation')}'")
    
    # Update employee with response data
    update_data = {
        f"{prefix}request_status": "submitted",
        f"{prefix}response_received_at": now,
        f"{prefix}response_data": form_data,
        f"{prefix}mismatch_detected": mismatch_detected,
    }
    
    # Clear token after use (security)
    update_data[f"{prefix}request_token"] = None
    
    await db.employees.update_one({"id": employee['id']}, {"$set": update_data})
    
    # Create form submission for audit trail
    submission_id = str(uuid.uuid4())
    submission_doc = {
        "id": submission_id,
        "employee_id": employee['id'],
        "requirement_id": requirement_id,
        "form_type": "referee_reference_form",
        "data": form_data,
        "submitted_at": now,
        "submitted_by": None,
        "submitted_by_name": form_data.get("referee_full_name", "Referee"),
        "verified": False,
        "status": "submitted",
        "source": "external_referee",
        "mismatch_detected": mismatch_detected,
        "mismatch_reasons": mismatch_reasons if mismatch_detected else []
    }
    
    await db.form_submissions.insert_one(submission_doc)
    
    # Create document record for requirement slot
    doc_id = str(uuid.uuid4())
    doc_record = {
        "id": doc_id,
        "employee_id": employee['id'],
        "requirement_id": requirement_id,
        "document_type_id": requirement_id,
        "original_filename": f"reference_{ref_num}_response.json",
        "file_url": None,  # Data stored in response_data
        "mime_type": "application/json",
        "file_size": 0,
        "uploaded_at": now,
        "uploaded_by": None,
        "uploaded_by_name": form_data.get("referee_full_name", "Referee"),
        "verified": False,
        "status": "active",
        "source": "external_referee_response",
        "form_submission_id": submission_id
    }
    
    await db.employee_documents.insert_one(doc_record)

    await log_audit_action("system", "reference_response_received", "employee", employee['id'], {
        "reference_num": ref_num,
        "requirement_id": requirement_id,
        "submission_id": submission_id,
        "token_consumed": True,
        "mismatch_detected": mismatch_detected
    })
    
    return {
        "status": "success",
        "message": "Thank you. Your reference has been submitted and will be reviewed by the recruitment team.",
        "submission_id": submission_id,
        "mismatch_detected": mismatch_detected
    }


@router.post("/employees/{employee_id}/review-reference")
async def review_reference(
    employee_id: str,
    reference_num: int = Query(..., description="Reference number: 1 or 2"),
    mismatch_notes: Optional[str] = Query(None, description="Notes explaining any mismatches"),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Review a reference (step 1 of 2-step verification).
    Manager or Admin can review.
    
    If mismatch is detected, notes are required.
    """
    db = get_db()
    
    if reference_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="reference_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    prefix = f"reference_{reference_num}_"
    
    # Check reference has been submitted
    current_status = employee.get(f"{prefix}request_status")
    if current_status not in ["submitted", "awaiting_review"]:
        raise HTTPException(status_code=400, detail="Reference must be submitted before review")
    
    # If mismatch detected, require notes
    mismatch_detected = employee.get(f"{prefix}mismatch_detected", False)
    if mismatch_detected and not mismatch_notes:
        raise HTTPException(status_code=400, detail="Mismatch detected - notes explaining the mismatch are required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        f"{prefix}request_status": "awaiting_review",
        f"{prefix}reviewed": True,
        f"{prefix}reviewed_by": user['user_id'],
        f"{prefix}reviewed_at": now,
    }
    
    if mismatch_notes:
        update_data[f"{prefix}mismatch_notes"] = mismatch_notes
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "review_reference", "employee", employee_id, {
        "reference_num": reference_num,
        "mismatch_detected": mismatch_detected,
        "mismatch_notes": mismatch_notes
    })
    
    return {
        "status": "success",
        "message": f"Reference {reference_num} reviewed. Ready for final verification.",
        "reviewed_by": user.get('email'),
        "next_step": "verify_reference"
    }


@router.post("/employees/{employee_id}/references/{reference_num}/verify")
async def verify_or_reject_reference(
    employee_id: str,
    reference_num: int,
    request: ReferenceVerifyRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Verify or reject a reference.
    
    Actions:
    - verify: Mark reference as verified
    - reject: Mark reference as rejected with reason
    
    Mismatch handling:
    - earlier_employment: Referee is from earlier employment
    - personal_reference: Referee is personal/professional reference
    - changed_employers: Applicant changed employers since declaration
    - other: Other reason (specify in notes)
    """
    db = get_db()
    
    if reference_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="reference_num must be 1 or 2")
    
    if request.action not in ['verify', 'reject', 'request_replacement']:
        raise HTTPException(status_code=400, detail="action must be 'verify', 'reject', or 'request_replacement'")
    
    if request.action in ['reject', 'request_replacement'] and not request.notes:
        raise HTTPException(status_code=400, detail="Reason (notes) is required")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    prefix = f"reference_{reference_num}_"
    requirement_id = f"reference_{reference_num}"
    now = datetime.now(timezone.utc).isoformat()
    
    if request.action == 'verify':
        # Verify the reference
        update_data = {
            f"{prefix}request_status": "verified",
            f"{prefix}verified": True,
            f"{prefix}verified_by": user['user_id'],
            f"{prefix}verified_at": now,
            f"{prefix}verification_notes": request.notes,
        }
        
        if request.mismatch_reason:
            update_data[f"{prefix}mismatch_documented"] = True
            update_data[f"{prefix}mismatch_reason"] = request.mismatch_reason
        
        await db.employees.update_one({"id": employee_id}, {"$set": update_data})
        
        # Update document record as verified
        await db.employee_documents.update_one(
            {"employee_id": employee_id, "requirement_id": requirement_id},
            {"$set": {
                "verified": True, 
                "verified_by": user['user_id'], 
                "verified_at": now,
                "status": "verified"
            }}
        )
        
        await log_audit_action(user['user_id'], "verify_reference", "employee", employee_id, {
            "reference_num": reference_num,
            "action": "verified",
            "mismatch_reason": request.mismatch_reason,
            "notes": request.notes,
            "employee_id": employee_id
        })
        
        return {
            "status": "success",
            "message": f"Reference {reference_num} verified",
            "verified_at": now
        }
    elif request.action == 'reject':
        # Reject the reference and clear data for fresh input
        update_data = {
            f"{prefix}request_status": "rejected",
            f"{prefix}verified": False,
            f"{prefix}rejected_by": user['user_id'],
            f"{prefix}rejected_at": now,
            f"{prefix}rejection_reason": request.notes,
            f"{prefix}request_token": None,
            # Clear all reference data fields so worker can re-enter
            f"{prefix}name": None,
            f"{prefix}email": None,
            f"{prefix}phone": None,
            f"{prefix}company": None,
            f"{prefix}position": None,
            f"{prefix}relationship": None,
            f"{prefix}years_known": None,
            f"{prefix}declared": False,
            f"{prefix}response_data": None,
            f"{prefix}response_received_at": None,
            f"{prefix}reviewed": False,
            f"{prefix}reviewed_by": None,
            f"{prefix}reviewed_at": None,
        }
        
        await db.employees.update_one({"id": employee_id}, {"$set": update_data})
        
        # Update document record as rejected
        await db.employee_documents.update_many(
            {"employee_id": employee_id, "requirement_id": requirement_id},
            {"$set": {
                "verified": False, 
                "status": "rejected",
                "rejected_by": user['user_id'],
                "rejected_at": now,
                "rejection_reason": request.notes,
                "is_active": False
            }}
        )
        
        # Also clear from db.references collection if exists
        await db.references.update_one(
            {"employee_id": employee_id},
            {"$set": {
                f"ref{reference_num}": {},
                f"ref{reference_num}_status": "rejected",
                f"ref{reference_num}_rejected_at": now,
                f"ref{reference_num}_rejection_reason": request.notes
            }}
        )
        
        await log_audit_action(user['user_id'], "reject_reference", "employee", employee_id, {
            "reference_num": reference_num,
            "action": "rejected",
            "reason": request.notes,
            "employee_id": employee_id,
            "data_cleared": True
        })
        
        return {
            "status": "success",
            "message": f"Reference {reference_num} rejected and data cleared",
            "rejected_at": now
        }
    elif request.action == 'request_replacement':
        # Request replacement — clear current referee data so worker.can_provide_new = True.
        # Sets rejected=True + clears name so existing worker_dashboard gating (data_cleared) fires.
        # Additionally stores replacement-specific metadata to distinguish from a plain rejection.
        update_data = {
            # Existing gating reads: is_rejected AND not referee_name → data_cleared → can_provide_new
            f"{prefix}request_status": "rejected",
            f"{prefix}rejected": True,
            f"{prefix}rejected_by": user['user_id'],
            f"{prefix}rejected_at": now,
            f"{prefix}rejection_reason": request.notes,
            f"{prefix}request_token": None,
            # Clear referee data so worker can re-enter new details
            f"{prefix}name": None,
            f"{prefix}email": None,
            f"{prefix}phone": None,
            f"{prefix}company": None,
            f"{prefix}position": None,
            f"{prefix}relationship": None,
            f"{prefix}years_known": None,
            f"{prefix}declared": False,
            f"{prefix}response_data": None,
            f"{prefix}response_received_at": None,
            f"{prefix}reviewed": False,
            f"{prefix}reviewed_by": None,
            f"{prefix}reviewed_at": None,
            # Replacement-specific metadata (distinguishes from plain reject in audit + canonical_status)
            f"{prefix}replacement_requested_at": now,
            f"{prefix}replacement_requested_by": user['user_id'],
            f"{prefix}replacement_reason": request.notes,
        }
        await db.employees.update_one({"id": employee_id}, {"$set": update_data})

        # Update all matching document records so no stale active row remains
        await db.employee_documents.update_many(
            {"employee_id": employee_id, "requirement_id": requirement_id},
            {"$set": {
                "verified": False,
                "status": "rejected",
                "rejected_by": user['user_id'],
                "rejected_at": now,
                "rejection_reason": request.notes,
                "is_active": False
            }}
        )

        # Keep db.references consistent with cleared replacement state
        await db.references.update_one(
            {"employee_id": employee_id},
            {"$set": {
                f"ref{reference_num}": {},
                f"ref{reference_num}_status": "rejected",
                f"ref{reference_num}_rejected_at": now,
                f"ref{reference_num}_rejection_reason": request.notes
            }}
        )

        await log_audit_action(user['user_id'], "request_reference_replacement", "employee", employee_id, {
            "reference_num": reference_num,
            "reason": request.notes,
            "employee_id": employee_id,
            "data_cleared": True
        })

        return {
            "status": "success",
            "message": f"Replacement requested for Reference {reference_num}. Worker has been notified to provide new referee details.",
            "replacement_requested_at": now
        }


@router.post("/employees/{employee_id}/verify-reference-strict")
async def verify_reference_strict(
    employee_id: str,
    reference_num: int = Query(..., description="Reference number: 1 or 2"),
    user: dict = Depends(require_admin)  # ADMIN ONLY for final verification
):
    """
    Verify a reference (step 2 of 2-step verification).
    ADMIN ONLY - final verification.
    
    Reference must be reviewed first.
    Response must exist (cannot verify without returned reference).
    """
    db = get_db()
    
    if reference_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="reference_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    prefix = f"reference_{reference_num}_"
    requirement_id = f"reference_{reference_num}"
    
    # Check reference has response
    response_data = employee.get(f"{prefix}response_data")
    if not response_data:
        raise HTTPException(status_code=400, detail="Cannot verify reference without returned response")
    
    # Check reference has been reviewed
    reviewed = employee.get(f"{prefix}reviewed", False)
    if not reviewed:
        raise HTTPException(status_code=400, detail="Reference must be reviewed before final verification")
    
    # Check mismatch is documented if detected
    mismatch_detected = employee.get(f"{prefix}mismatch_detected", False)
    mismatch_notes = employee.get(f"{prefix}mismatch_notes")
    if mismatch_detected and not mismatch_notes:
        raise HTTPException(status_code=400, detail="Mismatch detected but not documented. Review must include mismatch notes.")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee
    update_data = {
        f"{prefix}request_status": "verified",
        f"{prefix}verified": True,
        f"{prefix}verified_by": user['user_id'],
        f"{prefix}verified_at": now,
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    # Update document record as verified
    await db.employee_documents.update_one(
        {"employee_id": employee_id, "requirement_id": requirement_id, "source": "external_referee_response"},
        {"$set": {"verified": True, "verified_by": user['user_id'], "verified_at": now}}
    )
    
    await log_audit_action(user['user_id'], "verify_reference", "employee", employee_id, {
        "reference_num": reference_num,
        "two_step_verification": True
    })
    
    return {
        "status": "success",
        "message": f"Reference {reference_num} verified (2-step verification complete)",
        "verified_by": user.get('email')
    }


@router.get("/employees/{employee_id}/reference-status")
async def get_reference_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get detailed reference status for an employee including mismatch indicators.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    references = []
    
    for ref_num in [1, 2]:
        prefix = f"reference_{ref_num}_"
        
        declared = {
            "name": employee.get(f"{prefix}name"),
            "company": employee.get(f"{prefix}company"),
            "email": employee.get(f"{prefix}email"),
            "phone": employee.get(f"{prefix}phone"),
            "job_title": employee.get(f"{prefix}job_title"),
            "relationship": employee.get(f"{prefix}relationship"),
            "from_cv": employee.get(f"{prefix}from_cv"),
            "override_reason": employee.get(f"{prefix}override_reason"),
        }
        
        response_data = employee.get(f"{prefix}response_data") or {}
        returned = {
            "name": response_data.get("referee_full_name"),
            "company": response_data.get("referee_organisation"),
            "email": response_data.get("referee_work_email"),
            "phone": response_data.get("referee_phone"),
            "job_title": response_data.get("referee_job_title"),
            "relationship": response_data.get("relationship_type"),
        }
        
        ref_status = {
            "reference_num": ref_num,
            "declared": declared,
            "returned": returned,
            "request_status": employee.get(f"{prefix}request_status"),
            "request_sent_at": employee.get(f"{prefix}request_sent_at"),
            "response_received_at": employee.get(f"{prefix}response_received_at"),
            "mismatch_detected": employee.get(f"{prefix}mismatch_detected", False),
            "mismatch_notes": employee.get(f"{prefix}mismatch_notes"),
            "reviewed": employee.get(f"{prefix}reviewed", False),
            "reviewed_by": employee.get(f"{prefix}reviewed_by"),
            "reviewed_at": employee.get(f"{prefix}reviewed_at"),
            "verified": employee.get(f"{prefix}verified", False),
            "verified_by": employee.get(f"{prefix}verified_by"),
            "verified_at": employee.get(f"{prefix}verified_at"),
            "response_data": response_data if user.get('role') in ['admin', 'manager'] else None
        }
        
        references.append(ref_status)
    
    return {"references": references}
