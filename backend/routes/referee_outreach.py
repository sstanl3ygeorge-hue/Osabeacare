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
import asyncio
import logging
import resend
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from .dependencies import (
    get_db, get_current_user, require_admin, require_manager_or_admin,
    log_audit_action, SENDER_EMAIL
)
from governance.references_sufficiency import (
    VALID_REFERENCE_TYPES,
    classify_reference_type,
    evaluate_verify_request,
    role_requires_employment_reference,
)

router = APIRouter(tags=["Referee Outreach"])
logger = logging.getLogger(__name__)

# Get portal URL from environment
PORTAL_URL = os.environ.get('FRONTEND_URL', 'https://app.osabeacares.co.uk')

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
    # Reference sufficiency (CQC Reg 19) — admin declares the kind of reference
    # being verified. When the post-verify state would leave the employee with
    # no verified employment reference for a care role, the endpoint demands
    # ``explanation_reason`` before completing the verify.
    reference_type: Optional[str] = None  # 'employment' | 'character' | 'academic'
    is_employment_reference: Optional[bool] = None
    explanation_reason: Optional[str] = None


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
    logger.info(
        "EMAIL_OBS flow=reference_request_send stage=route_entry employee_id=%s recipient=unknown sender=%s resend_api_key_present=%s is_resend=%s",
        employee_id,
        SENDER_EMAIL,
        bool(resend.api_key),
        bool(force_resend),
    )
    
    db = get_db()
    
    if reference_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="reference_num must be 1 or 2")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get referee details from canonical references document first
    prefix = f"reference_{reference_num}_"
    references_doc = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    ref_key = f"ref{reference_num}"
    declared_ref = ((references_doc or {}).get(ref_key) or {}).get("declared") or {}

    # Fallback to legacy flat employee fields if needed
    referee_name = declared_ref.get("name") or employee.get(f"{prefix}name")
    referee_email = declared_ref.get("email") or employee.get(f"{prefix}email")
    
    if not referee_email:
        raise HTTPException(status_code=400, detail=f"Reference {reference_num} email not provided. Update employee profile first.")
    
    if not referee_name:
        raise HTTPException(status_code=400, detail=f"Reference {reference_num} name not provided. Update employee profile first.")
    
    # Check if request already pending - read from canonical references document
    existing_request = ((references_doc or {}).get(ref_key) or {}).get("request") or {}
    existing_status = existing_request.get("status")
    if existing_status in ["requested", "awaiting_response"] and not force_resend:
        return {
            "status": "duplicate",
            "message": "Reference request already sent and awaiting response",
            "current_status": existing_status
        }

    # Generate secure token
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).isoformat()

    # Write request tracking to canonical references document
    ref_request_fields = {
        f"{ref_key}.request.status": "requested",
        f"{ref_key}.request.sent_at": now,
        f"{ref_key}.request.token": token,
    }

    # Track resend metadata when explicitly resending an existing pending request
    if force_resend and existing_status in ["requested", "awaiting_response"]:
        ref_request_fields[f"{ref_key}.request.resend_count"] = int(existing_request.get("resend_count", 0) or 0) + 1
        ref_request_fields[f"{ref_key}.request.last_reminder_at"] = now

    await db.references.update_one(
        {"employee_id": employee_id},
        {"$set": ref_request_fields},
        upsert=True
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
    if not resend.api_key:
        raise HTTPException(status_code=503, detail="Email service unavailable")

    try:
        logger.info(
            "EMAIL_OBS flow=reference_request_send stage=before_resend_call employee_id=%s recipient=%s sender=%s resend_api_key_present=%s is_resend=%s",
            employee_id,
            referee_email,
            SENDER_EMAIL,
            bool(resend.api_key),
            bool(force_resend),
        )
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [referee_email],
            "subject": email_subject,
            "html": email_body
        })
        email_sent = True
        logger.info(
            "EMAIL_OBS flow=reference_request_send stage=after_resend_success employee_id=%s recipient=%s sender=%s resend_api_key_present=%s is_resend=%s",
            employee_id,
            referee_email,
            SENDER_EMAIL,
            bool(resend.api_key),
            bool(force_resend),
        )

        # Update status to awaiting_response
        await db.references.update_one(
            {"employee_id": employee_id},
            {"$set": {f"{ref_key}.request.status": "awaiting_response"}}
        )
    except Exception as e:
        logger.error(
            "EMAIL_OBS flow=reference_request_send stage=send_failure employee_id=%s recipient=%s sender=%s resend_api_key_present=%s is_resend=%s exception=%s",
            employee_id,
            referee_email,
            SENDER_EMAIL,
            bool(resend.api_key),
            bool(force_resend),
            str(e),
        )
        logger.error(f"Failed to send referee email: {e}")
    
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
    
    # Find references document by token - canonical store
    references_doc = await db.references.find_one({
        "$or": [
            {"ref1.request.token": token},
            {"ref2.request.token": token}
        ]
    }, {"_id": 0})

    if not references_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reference link")

    # Determine which reference this token belongs to
    ref_num = 1 if ((references_doc.get("ref1") or {}).get("request") or {}).get("token") == token else 2
    ref_key = f"ref{ref_num}"
    ref_data = references_doc.get(ref_key) or {}
    request_data = ref_data.get("request") or {}
    declared_data = ref_data.get("declared") or {}

    employee_id = references_doc.get("employee_id")
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid or expired reference link")

    # Check if already submitted
    current_status = request_data.get("status")
    if current_status in ["submitted", "awaiting_review", "verified", "rejected"]:
        raise HTTPException(status_code=400, detail="This reference has already been submitted")

    # Check token age (30 day expiry)
    sent_at = request_data.get("sent_at")
    if sent_at:
        try:
            sent_date = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            if (datetime.now(timezone.utc) - sent_date).days > 30:
                raise HTTPException(status_code=400, detail="This reference link has expired. Please contact the recruitment team.")
        except (ValueError, TypeError):
            pass

    # Get applicant info for context
    applicant_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()

    return {
        "employee_id": employee_id,
        "reference_num": ref_num,
        "applicant_name": applicant_name,
        "declared_referee_details": {
            "name": declared_data.get("name", ""),
            "company": declared_data.get("organisation", declared_data.get("company", "")),
            "job_title": declared_data.get("job_title", "")
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
    
    # Find references document by token - canonical store
    references_doc = await db.references.find_one({
        "$or": [
            {"ref1.request.token": token},
            {"ref2.request.token": token}
        ]
    }, {"_id": 0})

    if not references_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reference link")

    ref_num = 1 if ((references_doc.get("ref1") or {}).get("request") or {}).get("token") == token else 2
    ref_key = f"ref{ref_num}"
    requirement_id = f"reference_{ref_num}"
    ref_data = references_doc.get(ref_key) or {}
    request_data = ref_data.get("request") or {}
    declared_data = ref_data.get("declared") or {}

    employee_id = references_doc.get("employee_id")
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid or expired reference link")

    # Check if already submitted
    current_status = request_data.get("status")
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
    declared_name = (declared_data.get("name") or "").lower().strip()
    returned_name = form_data.get("referee_full_name", "").lower().strip()
    declared_company = (declared_data.get("organisation") or declared_data.get("company") or "").lower().strip()
    returned_company = form_data.get("referee_organisation", "").lower().strip()

    mismatch_detected = False
    mismatch_reasons = []

    if declared_name and returned_name and declared_name != returned_name:
        mismatch_detected = True
        mismatch_reasons.append(f"Name: declared '{declared_data.get('name')}' vs returned '{form_data.get('referee_full_name')}'")

    if declared_company and returned_company and declared_company != returned_company:
        mismatch_detected = True
        mismatch_reasons.append(f"Organisation: declared '{declared_data.get('organisation') or declared_data.get('company')}' vs returned '{form_data.get('referee_organisation')}'")

    # Write response and status to canonical references document; clear token after use
    response_doc = {**form_data, "received_at": now}
    ref_update = {
        f"{ref_key}.request.status": "submitted",
        f"{ref_key}.request.token": None,
        f"{ref_key}.response": response_doc,
        f"{ref_key}.mismatch.detected": mismatch_detected,
        f"{ref_key}.mismatch.reasons": mismatch_reasons if mismatch_detected else [],
    }

    await db.references.update_one({"employee_id": employee_id}, {"$set": ref_update})
    
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

    # Sync employee flat fields so ReferenceIntegrityService (work_readiness) can read the response.
    # The canonical store is db.references, but work_readiness reads from db.employees flat fields.
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            f"reference_{ref_num}_response_data": response_doc,
            f"reference_{ref_num}_response_received_at": now,
            f"reference_{ref_num}_evidence_source": "referee_response",
            f"reference_{ref_num}_request_status": "submitted",
        }}
    )

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

    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    ref_key = f"ref{reference_num}"
    references_doc = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    if not references_doc:
        raise HTTPException(status_code=404, detail="Reference record not found")

    ref_data = references_doc.get(ref_key) or {}
    request_data = ref_data.get("request") or {}

    # Check reference has been submitted
    current_status = request_data.get("status")
    if current_status not in ["submitted", "awaiting_review"]:
        raise HTTPException(status_code=400, detail="Reference must be submitted before review")

    # If mismatch detected, require notes
    mismatch_detected = (ref_data.get("mismatch") or {}).get("detected", False)
    if mismatch_detected and not mismatch_notes:
        raise HTTPException(status_code=400, detail="Mismatch detected - notes explaining the mismatch are required")

    now = datetime.now(timezone.utc).isoformat()

    review_fields = {
        f"{ref_key}.request.status": "awaiting_review",
        f"{ref_key}.review.reviewed": True,
        f"{ref_key}.review.reviewed_by": user['user_id'],
        f"{ref_key}.review.reviewed_at": now,
    }

    if mismatch_notes:
        review_fields[f"{ref_key}.mismatch.notes"] = mismatch_notes

    await db.references.update_one({"employee_id": employee_id}, {"$set": review_fields})

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

    if request.action not in ['verify', 'reject', 'request_replacement', 'request_different_referee']:
        raise HTTPException(status_code=400, detail="action must be 'verify', 'reject', 'request_replacement', or 'request_different_referee'")

    if request.action in ['reject', 'request_replacement', 'request_different_referee'] and not request.notes:
        raise HTTPException(status_code=400, detail="Reason (notes) is required")

    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    ref_key = f"ref{reference_num}"
    requirement_id = f"reference_{reference_num}"
    now = datetime.now(timezone.utc).isoformat()

    references_doc = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    if not references_doc:
        raise HTTPException(status_code=404, detail="Reference record not found")

    ref_data = references_doc.get(ref_key) or {}
    response_data = ref_data.get("response") or {}
    declared_data = ref_data.get("declared") or {}

    # 'request_different_referee' does NOT require a returned response — admin
    # may ask for a new referee as soon as a referee is declared (e.g. referee
    # unreachable, employer-of-record confirms they never worked there, etc).
    if request.action not in ('request_different_referee',) and not response_data:
        raise HTTPException(
            status_code=400,
            detail="Cannot verify or reject a reference without a returned response"
        )

    # For request_different_referee we only require that a referee was declared.
    if request.action == 'request_different_referee' and not declared_data.get("name"):
        raise HTTPException(
            status_code=400,
            detail="Cannot request a different referee until the current referee has been declared"
        )

    if request.action == 'verify':
        # ---- Reg 19 sufficiency pre-check -----------------------------------
        # Resolve role (applicant_role preferred, falls back to role).
        employee_full = await db.employees.find_one(
            {"id": employee_id},
            {"_id": 0, "role": 1, "applicant_role": 1, "job_role": 1},
        ) or {}
        role = (
            employee_full.get("applicant_role")
            or employee_full.get("role")
            or employee_full.get("job_role")
        )

        # Figure out the type the admin has asserted for this reference.
        admin_type = (request.reference_type or "").strip().lower() or None
        if admin_type and admin_type not in VALID_REFERENCE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"reference_type must be one of {VALID_REFERENCE_TYPES}",
            )

        # Build a projected version of THIS slot with the admin's choice,
        # then evaluate overall sufficiency after verify.
        proposed_slot = dict(ref_data)
        proposed_slot["reference_num"] = reference_num
        if admin_type:
            proposed_slot["type"] = admin_type
            proposed_slot["is_employment_reference"] = admin_type == "employment"
        elif request.is_employment_reference is True:
            proposed_slot["type"] = "employment"
            proposed_slot["is_employment_reference"] = True
        else:
            # Infer from response relationship_type if admin didn't state.
            inferred = classify_reference_type(ref_data)
            proposed_slot["type"] = inferred
            proposed_slot["is_employment_reference"] = inferred == "employment"

        if request.explanation_reason:
            proposed_slot["explanation_reason"] = request.explanation_reason

        # Other existing slots (not the one being verified) — still reflecting
        # current DB state.
        other_slots = []
        for other_num in (1, 2):
            if other_num == reference_num:
                continue
            other_slot = dict(references_doc.get(f"ref{other_num}") or {})
            other_slot["reference_num"] = other_num
            other_slots.append(other_slot)

        verdict = evaluate_verify_request(
            role=role,
            existing_slots=other_slots,
            this_slot_proposed=proposed_slot,
            explanation_reason=request.explanation_reason,
        )

        if not verdict["sufficient"] and verdict["requires_explanation"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "reference_sufficiency_explanation_required",
                    "message": (
                        "Role requires at least one employment reference. "
                        "Provide an explanation_reason describing why the "
                        "alternative references are acceptable."
                    ),
                    "requires_explanation": True,
                    "role": role,
                    "employment_reference_verified_count": verdict[
                        "employment_reference_verified_count"
                    ],
                    "verified_count": verdict["verified_count"] + 1,  # post-verify
                },
            )

        verification_fields = {
            f"{ref_key}.request.status": "verified",
            f"{ref_key}.verification.status": "verified",
            f"{ref_key}.verification.verified": True,
            f"{ref_key}.verification.verified_by": user['user_id'],
            f"{ref_key}.verification.verified_at": now,
            f"{ref_key}.verification.notes": request.notes,
            f"{ref_key}.verification.rejected_by": None,
            f"{ref_key}.verification.rejected_at": None,
            f"{ref_key}.verification.rejection_reason": None,
            # Sufficiency stamp
            f"{ref_key}.type": proposed_slot["type"],
            f"{ref_key}.is_employment_reference": proposed_slot["is_employment_reference"],
            f"{ref_key}.explanation_required": verdict["role_requires_employment_reference"]
                and verdict["employment_reference_verified_count"] == 0,
        }

        if request.explanation_reason:
            verification_fields[f"{ref_key}.explanation_reason"] = request.explanation_reason
            verification_fields[f"{ref_key}.explanation_provided_by"] = user['user_id']
            verification_fields[f"{ref_key}.explanation_provided_at"] = now

        if request.mismatch_reason:
            verification_fields[f"{ref_key}.mismatch.documented"] = True
            verification_fields[f"{ref_key}.mismatch.reason"] = request.mismatch_reason

        update_result = await db.references.update_one(
            {"employee_id": employee_id},
            {"$set": verification_fields}
        )
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Reference record not found")

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

        # Sync employee flat fields so ReferenceIntegrityService (work_readiness) can see verified.
        # Canonical store is db.references, but work_readiness HARD BLOCK C reads db.employees.
        prefix = f"reference_{reference_num}_"
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                f"{prefix}verified": True,
                f"{prefix}verified_at": now,
                f"{prefix}verified_by": user['user_id'],
            }}
        )

        await log_audit_action(user['user_id'], "verify_reference", "employee", employee_id, {
            "reference_num": reference_num,
            "action": "verified",
            "mismatch_reason": request.mismatch_reason,
            "notes": request.notes,
            "employee_id": employee_id,
            # Reg 19 sufficiency trail
            "reference_type": proposed_slot["type"],
            "is_employment_reference": proposed_slot["is_employment_reference"],
            "explanation_reason": request.explanation_reason,
            "role_requires_employment_reference": verdict["role_requires_employment_reference"],
            "employment_reference_verified_count_after": verdict[
                "employment_reference_verified_count"
            ],
        })

        return {
            "status": "success",
            "message": f"Reference {reference_num} verified",
            "verified_at": now
        }

    elif request.action == 'reject':
        rejection_fields = {
            f"{ref_key}.request.status": "rejected",
            f"{ref_key}.request.token": None,
            f"{ref_key}.verification.status": "rejected",
            f"{ref_key}.verification.verified": False,
            f"{ref_key}.verification.rejected_by": user['user_id'],
            f"{ref_key}.verification.rejected_at": now,
            f"{ref_key}.verification.rejection_reason": request.notes,
            # Clear declared and response so worker can re-enter
            f"{ref_key}.declared": {},
            f"{ref_key}.response": {},
            f"{ref_key}.review": {},
            f"{ref_key}.mismatch": {},
        }

        update_result = await db.references.update_one(
            {"employee_id": employee_id},
            {"$set": rejection_fields}
        )
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Reference record not found")

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
        replacement_fields = {
            f"{ref_key}.request.status": "rejected",
            f"{ref_key}.request.token": None,
            f"{ref_key}.verification.verified": False,
            f"{ref_key}.verification.rejected_by": user['user_id'],
            f"{ref_key}.verification.rejected_at": now,
            f"{ref_key}.verification.rejection_reason": request.notes,
            f"{ref_key}.verification.replacement_requested_at": now,
            f"{ref_key}.verification.replacement_requested_by": user['user_id'],
            f"{ref_key}.verification.replacement_reason": request.notes,
            # Clear declared and response so worker can re-enter new referee
            f"{ref_key}.declared": {},
            f"{ref_key}.response": {},
            f"{ref_key}.review": {},
            f"{ref_key}.mismatch": {},
        }

        await db.references.update_one({"employee_id": employee_id}, {"$set": replacement_fields})

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


    elif request.action == 'request_different_referee':
        # Distinct from 'request_replacement'. PRESERVES declared/response/
        # verification/review/mismatch so the original referee + their status
        # history remain intact in the document until the worker either:
        #   (a) provides a different referee — at which point the current slot
        #       is snapshotted into refN.history[] before being overwritten, or
        #   (b) justifies the existing referee (worker_justify_existing_referee)
        #       which leaves the slot untouched and records the justification.
        #
        # Flat employee fields get a new reference_N_request_status value of
        # 'replacement_requested' so work_readiness / worker dashboard can
        # surface the action-required state without pretending the reference
        # was rejected.
        prefix = f"reference_{reference_num}_"

        nested_fields = {
            f"{ref_key}.replacement_requested": True,
            f"{ref_key}.replacement_requested_by": user['user_id'],
            f"{ref_key}.replacement_requested_at": now,
            f"{ref_key}.replacement_requested_reason": request.notes,
            # Mirror into verification sub-doc for backwards-compat readers.
            f"{ref_key}.verification.replacement_requested_at": now,
            f"{ref_key}.verification.replacement_requested_by": user['user_id'],
            f"{ref_key}.verification.replacement_reason": request.notes,
            # Flip request.status so downstream surfaces recognise action-required.
            f"{ref_key}.request.status": "replacement_requested",
            # Clear any stale justification from a prior cycle.
            f"{ref_key}.justification": None,
        }
        await db.references.update_one({"employee_id": employee_id}, {"$set": nested_fields})

        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                f"{prefix}replacement_requested": True,
                f"{prefix}replacement_requested_by": user['user_id'],
                f"{prefix}replacement_requested_at": now,
                f"{prefix}replacement_requested_reason": request.notes,
                f"{prefix}request_status": "replacement_requested",
                f"{prefix}justification_reason": None,
                f"{prefix}justification_submitted_at": None,
                "updated_at": now,
            }}
        )

        await log_audit_action(
            user['user_id'],
            "request_different_referee",
            "employee",
            employee_id,
            {
                "reference_num": reference_num,
                "reason": request.notes,
                "employee_id": employee_id,
                "original_referee_name": declared_data.get("name"),
                "original_referee_email": declared_data.get("email"),
                "original_request_status_before": ref_data.get("request", {}).get("status"),
                "original_verification_status_before": (ref_data.get("verification") or {}).get("status"),
                "data_preserved": True,
            }
        )

        return {
            "status": "success",
            "message": (
                f"A different referee has been requested for Reference {reference_num}. "
                "The original referee details remain on file and the worker has been notified."
            ),
            "replacement_requested_at": now,
            "original_referee_preserved": True,
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

    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    ref_key = f"ref{reference_num}"
    requirement_id = f"reference_{reference_num}"

    references_doc = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    if not references_doc:
        raise HTTPException(status_code=404, detail="Reference record not found")

    ref_data = references_doc.get(ref_key) or {}
    response_data = ref_data.get("response") or {}
    review_data = ref_data.get("review") or {}
    mismatch_data = ref_data.get("mismatch") or {}

    # Check reference has response
    if not response_data:
        raise HTTPException(status_code=400, detail="Cannot verify reference without returned response")

    # Check reference has been reviewed
    if not review_data.get("reviewed", False):
        raise HTTPException(status_code=400, detail="Reference must be reviewed before final verification")

    # Check mismatch is documented if detected
    mismatch_detected = mismatch_data.get("detected", False)
    mismatch_notes = mismatch_data.get("notes")
    if mismatch_detected and not mismatch_notes:
        raise HTTPException(status_code=400, detail="Mismatch detected but not documented. Review must include mismatch notes.")

    now = datetime.now(timezone.utc).isoformat()

    await db.references.update_one(
        {"employee_id": employee_id},
        {"$set": {
            f"{ref_key}.request.status": "verified",
            f"{ref_key}.verification.verified": True,
            f"{ref_key}.verification.verified_by": user['user_id'],
            f"{ref_key}.verification.verified_at": now,
        }}
    )

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

    references_doc = await db.references.find_one({"employee_id": employee_id}, {"_id": 0}) or {}

    references = []

    for ref_num in [1, 2]:
        ref_key = f"ref{ref_num}"
        ref_data = references_doc.get(ref_key) or {}
        declared_data = ref_data.get("declared") or {}
        request_data = ref_data.get("request") or {}
        response_raw = ref_data.get("response") or {}
        review_data = ref_data.get("review") or {}
        verification_data = ref_data.get("verification") or {}
        mismatch_data = ref_data.get("mismatch") or {}

        declared = {
            "name": declared_data.get("name"),
            "company": declared_data.get("organisation") or declared_data.get("company"),
            "email": declared_data.get("email"),
            "phone": declared_data.get("phone"),
            "job_title": declared_data.get("job_title"),
            "relationship": declared_data.get("relationship"),
            "from_cv": declared_data.get("from_cv"),
            "override_reason": declared_data.get("override_reason"),
        }

        returned = {
            "name": response_raw.get("referee_full_name"),
            "company": response_raw.get("referee_organisation"),
            "email": response_raw.get("referee_work_email"),
            "phone": response_raw.get("referee_phone"),
            "job_title": response_raw.get("referee_job_title"),
            "relationship": response_raw.get("relationship_type"),
        }

        ref_status = {
            "reference_num": ref_num,
            "declared": declared,
            "returned": returned,
            "request_status": request_data.get("status"),
            "request_sent_at": request_data.get("sent_at"),
            "response_received_at": response_raw.get("received_at"),
            "mismatch_detected": mismatch_data.get("detected", False),
            "mismatch_notes": mismatch_data.get("notes"),
            "reviewed": review_data.get("reviewed", False),
            "reviewed_by": review_data.get("reviewed_by"),
            "reviewed_at": review_data.get("reviewed_at"),
            "verified": verification_data.get("verified", False),
            "verified_by": verification_data.get("verified_by"),
            "verified_at": verification_data.get("verified_at"),
            "response_data": response_raw if user.get('role') in ['admin', 'manager'] else None
        }

        references.append(ref_status)

    return {"references": references}


class AdminRecordReferenceRequest(BaseModel):
    """Admin manually records a reference received outside the secure email form."""
    referee_name: str
    referee_organisation: str
    referee_job_title: Optional[str] = None
    received_via: str  # email, letter, phone, fax
    received_at: str   # ISO date string
    performance_summary: Optional[str] = None
    safeguarding_concerns: Optional[str] = None
    would_re_employ: Optional[str] = None
    admin_notes: Optional[str] = None


@router.post("/employees/{employee_id}/references/{ref_num}/admin-record-response")
async def admin_record_reference_response(
    employee_id: str,
    ref_num: int,
    body: AdminRecordReferenceRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Admin records a reference received outside the secure email form
    (e.g. posted letter, emailed PDF, phone call confirmed in writing).

    Sets evidence_source = 'admin_uploaded_on_behalf' so that
    ReferenceIntegrityService.counts_toward_readiness() accepts it.
    Admin must then use the normal verify endpoint to complete the process.
    """
    db = get_db()

    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")

    if body.received_via not in ["email", "letter", "phone", "fax", "other"]:
        raise HTTPException(status_code=400, detail="received_via must be email, letter, phone, fax, or other")

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Ensure a reference record exists first
    references_doc = await db.references.find_one({"employee_id": employee_id}, {"_id": 0})
    ref_key = f"ref{ref_num}"
    ref_data = (references_doc or {}).get(ref_key) or {}

    # Guard: don't overwrite an already-verified reference
    if (ref_data.get("verification") or {}).get("verified"):
        raise HTTPException(status_code=400, detail="Reference is already verified. Reset it before recording a new response.")

    now = datetime.now(timezone.utc).isoformat()

    # Build a synthetic response document in the same shape as a secure-form submission
    response_doc = {
        "referee_full_name": body.referee_name,
        "referee_organisation": body.referee_organisation,
        "referee_job_title": body.referee_job_title,
        "performance_rating": body.performance_summary,
        "safeguarding_concerns": body.safeguarding_concerns or "No concerns",
        "would_re_employ": body.would_re_employ,
        "admin_notes": body.admin_notes,
        "received_via": body.received_via,
        "received_at": body.received_at,
        "recorded_at": now,
        "recorded_by": user['user_id'],
        "source": "admin_uploaded_on_behalf",
    }

    # Write to canonical db.references
    await db.references.update_one(
        {"employee_id": employee_id},
        {"$set": {
            f"{ref_key}.response": response_doc,
            f"{ref_key}.request.status": "submitted",
        }},
        upsert=True
    )

    # Sync employee flat fields so ReferenceIntegrityService reads the correct source
    prefix = f"reference_{ref_num}_"
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            f"{prefix}response_data": response_doc,
            f"{prefix}response_received_at": body.received_at,
            f"{prefix}evidence_source": "admin_uploaded_on_behalf",
            f"{prefix}request_status": "submitted",
        }}
    )

    await log_audit_action(user['user_id'], "admin_record_reference_response", "employee", employee_id, {
        "reference_num": ref_num,
        "referee_name": body.referee_name,
        "received_via": body.received_via,
        "received_at": body.received_at,
    })

    return {
        "status": "success",
        "message": f"Reference {ref_num} response recorded. Use the verify endpoint to complete verification.",
        "reference_num": ref_num,
        "evidence_source": "admin_uploaded_on_behalf",
        "next_step": f"POST /employees/{employee_id}/references/{ref_num}/verify with action=verify"
    }


# ==================== FLAG: RECENT EMPLOYER MISMATCH ====================

@router.post("/employees/{employee_id}/references/{ref_num}/flag-recent-employer-mismatch")
async def flag_recent_employer_mismatch(
    employee_id: str,
    ref_num: int,
    user: dict = Depends(require_manager_or_admin),
):
    """
    Admin flags that a reference does not cover the most recent employer as required by
    NHS Safer Recruitment. This:
      - Sets reference_{n}_mismatch_detected = True on db.employees
      - Sets specific mismatch_notes so the worker task card is descriptive
      - The worker will see an 'Action Required' card on their dashboard
      - Admin can review the explanation via POST /references/{id}/{n}/review-mismatch-explanation
    """
    if ref_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="Invalid reference number")

    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    now = datetime.now(timezone.utc).isoformat()
    prefix = f"reference_{ref_num}_"

    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            f"{prefix}mismatch_detected": True,
            f"{prefix}mismatch_notes": (
                "This reference does not appear to be from the most recent employer. "
                "NHS Safer Recruitment requires at least one reference from the most recent employer. "
                "Please provide an explanation or nominate a replacement referee."
            ),
            f"{prefix}mismatch_flagged_by": user['user_id'],
            f"{prefix}mismatch_flagged_at": now,
            "updated_at": now,
        }}
    )

    await log_audit_action(
        user['user_id'],
        "flag_recent_employer_mismatch",
        "employee",
        employee_id,
        {"reference_num": ref_num},
    )

    return {
        "status": "success",
        "message": f"Reference {ref_num} flagged: worker will see an explanation task on their dashboard.",
        "reference_num": ref_num,
        "next_step": (
            f"Once the worker submits an explanation, review it via "
            f"POST /references/{employee_id}/{ref_num}/review-mismatch-explanation"
        ),
    }


# ==========================================================================
# Reference sufficiency explanation (CQC Reg 19)
# ==========================================================================

class ReferenceSufficiencyExplanationRequest(BaseModel):
    reference_num: int  # 1 or 2 — the slot the explanation applies to
    explanation_reason: str


@router.post("/employees/{employee_id}/references/sufficiency-explanation")
async def record_reference_sufficiency_explanation(
    employee_id: str,
    request: ReferenceSufficiencyExplanationRequest,
    user: dict = Depends(require_manager_or_admin),
):
    """Record why a non-employment reference is acceptable for this applicant.

    Used when no verified employment reference can be obtained for a role
    that would normally require one. Satisfies CQC Regulation 19 audit trail.
    The explanation is stamped on the relevant reference slot and emitted
    to the audit log; it is surfaced in the compliance export.
    """
    db = get_db()

    if request.reference_num not in (1, 2):
        raise HTTPException(status_code=400, detail="reference_num must be 1 or 2")
    if not request.explanation_reason or not request.explanation_reason.strip():
        raise HTTPException(status_code=400, detail="explanation_reason is required")

    ref_key = f"ref{request.reference_num}"
    now = datetime.now(timezone.utc).isoformat()

    employee = await db.employees.find_one(
        {"id": employee_id}, {"_id": 0, "role": 1, "applicant_role": 1, "job_role": 1}
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    role = (
        employee.get("applicant_role")
        or employee.get("role")
        or employee.get("job_role")
    )

    await db.references.update_one(
        {"employee_id": employee_id},
        {"$set": {
            f"{ref_key}.explanation_reason": request.explanation_reason.strip(),
            f"{ref_key}.explanation_provided_by": user['user_id'],
            f"{ref_key}.explanation_provided_at": now,
            f"{ref_key}.explanation_required": role_requires_employment_reference(role),
        }},
        upsert=True,
    )

    await log_audit_action(
        user['user_id'],
        "record_reference_sufficiency_explanation",
        "employee",
        employee_id,
        {
            "reference_num": request.reference_num,
            "explanation_reason": request.explanation_reason.strip(),
            "role": role,
            "role_requires_employment_reference": role_requires_employment_reference(role),
        },
    )

    return {
        "status": "success",
        "reference_num": request.reference_num,
        "explanation_recorded_at": now,
    }

