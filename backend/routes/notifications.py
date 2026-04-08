"""
Email and Notifications Routes Module

This module handles email and notification-related endpoints including:
- Email sending via templates
- Email request management (create, track, cancel, resend)
- Notification triggers (recruitment, expiries, unverified submissions)
- Email logs and templates listing

Extracted from server.py for modularity.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Email & Notifications"])


# ==================== MODELS ====================

class CreateRequestPayload(BaseModel):
    person_id: str
    person_type: str = "employee"
    request_type: str  # RequestType value
    requirement_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    template_variant: str = "default"
    due_days: int = 14
    expiry_days: int = 30
    context: Optional[Dict[str, Any]] = None
    send_immediately: bool = True


# ==================== EMAIL TEMPLATES & SENDERS ====================

@router.get("/email/senders")
async def get_email_senders(user: dict = Depends(require_admin)):
    """Get all configured email senders"""
    # Import here to avoid circular imports
    from email_service import SENDER_REGISTRY
    
    senders = []
    for key, config in SENDER_REGISTRY.items():
        senders.append({
            "sender_key": config.sender_key,
            "from_address": config.from_address,
            "from_name": config.from_name,
            "reply_to": config.reply_to,
            "from_header": config.from_header
        })
    return {"senders": senders}


@router.get("/email/templates")
async def get_email_templates(
    category: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Get all registered email templates, optionally filtered by category"""
    from email_service import TEMPLATE_REGISTRY
    
    templates = []
    for key, template in TEMPLATE_REGISTRY.items():
        if category and template.category.value != category:
            continue
        templates.append({
            "template_key": template.template_key,
            "category": template.category.value,
            "sender_key": template.sender_key,
            "subject_template": template.subject_template,
            "requires_secure_link": template.requires_secure_link,
            "secure_link_action": template.secure_link_action,
            "description": template.description,
            "has_employee_template": template.employee_body_template is not None,
            "has_admin_template": template.admin_body_template is not None
        })
    return {"templates": templates, "count": len(templates)}


@router.get("/email/logs")
async def get_email_logs(
    employee_id: Optional[str] = None,
    template_key: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(require_admin)
):
    """Get email logs from the email_logs collection"""
    from email_service import EmailService
    
    logs = await EmailService.get_logs(
        employee_id=employee_id,
        template_key=template_key,
        category=category,
        status=status,
        limit=limit
    )
    return {"logs": logs, "count": len(logs)}


@router.post("/email/verify-action-token")
async def verify_action_token(token: str):
    """Verify a secure action token from an email link"""
    from email_service import verify_secure_action_token
    
    result = verify_secure_action_token(token)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired action token")
    
    return {
        "valid": True,
        "person_id": result.person_id,
        "person_type": result.person_type,
        "action_type": result.action_type,
        "requirement_id": result.requirement_id,
        "related_entity_type": result.related_entity_type,
        "related_entity_id": result.related_entity_id,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None
    }


@router.post("/email/send")
async def send_email_via_service(
    template_key: str,
    recipient_email: EmailStr,
    recipient_type: str,
    employee_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    context: Dict[str, Any] = {},
    user: dict = Depends(require_admin)
):
    """Send an email using the EmailService (admin only)"""
    from email_service import EmailService, get_template
    
    db = get_db()
    
    # Validate template exists
    template = get_template(template_key)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template_key}")
    
    # If employee_id provided, get employee name automatically
    if employee_id and "employee_name" not in context:
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        if employee:
            context["employee_name"] = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    result = await EmailService.send_template(
        template_key=template_key,
        recipient_email=recipient_email,
        recipient_type=recipient_type,
        context=context,
        employee_id=employee_id,
        requirement_id=requirement_id
    )
    
    return result


@router.get("/email/categories")
async def get_email_categories(user: dict = Depends(require_admin)):
    """Get all email categories"""
    from email_service import EmailCategory
    
    return {
        "categories": [
            {"key": c.value, "name": c.value.replace("_", " ").title()}
            for c in EmailCategory
        ]
    }


# ==================== EMAIL REQUESTS ====================

@router.post("/email-requests")
async def create_email_request(
    payload: CreateRequestPayload,
    user: dict = Depends(require_admin)
):
    """Create a new email request with duplicate checking"""
    from email_automation import EmailRequestService, RequestType
    
    try:
        request_type = RequestType(payload.request_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid request type: {payload.request_type}")
    
    result = await EmailRequestService.create_request(
        person_id=payload.person_id,
        person_type=payload.person_type,
        request_type=request_type,
        requirement_id=payload.requirement_id,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        template_variant=payload.template_variant,
        due_days=payload.due_days,
        expiry_days=payload.expiry_days,
        context=payload.context,
        send_immediately=payload.send_immediately,
        admin_id=user.get("user_id")
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["reason"])
    
    return result


@router.get("/email-requests/types")
async def get_request_types(user: dict = Depends(require_admin)):
    """Get available request types"""
    return {
        "request_types": [
            {"key": "upload_document", "name": "Upload Document", "description": "Request document upload"},
            {"key": "explain_gap", "name": "Explain Gap", "description": "Request CV gap explanation"},
            {"key": "review_reference", "name": "Review Reference", "description": "Request reference update"},
            {"key": "verify_reference", "name": "Verify Reference", "description": "Verify reference details"},
            {"key": "upload_training", "name": "Upload Training", "description": "Request training certificate"},
            {"key": "complete_form", "name": "Complete Form", "description": "Request form completion"},
            {"key": "confirm_details", "name": "Confirm Details", "description": "Request detail confirmation"},
        ],
        "statuses": [
            {"key": "pending_send", "name": "Pending Send"},
            {"key": "sent", "name": "Sent"},
            {"key": "opened", "name": "Opened"},
            {"key": "clicked", "name": "Clicked"},
            {"key": "action_started", "name": "Action Started"},
            {"key": "submitted", "name": "Submitted"},
            {"key": "completed", "name": "Completed"},
            {"key": "expired", "name": "Expired"},
            {"key": "cancelled", "name": "Cancelled"},
            {"key": "failed", "name": "Failed"},
            {"key": "superseded", "name": "Superseded"},
        ]
    }


@router.post("/email-requests/validate-token")
async def validate_action_token(token: str):
    """Validate a secure action token from an email link"""
    from email_automation import EmailRequestService
    
    result = await EmailRequestService.validate_and_use_token(token)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["reason"])
    
    return result


@router.post("/email-requests/process-reminders")
async def process_email_reminders(user: dict = Depends(require_admin)):
    """Process scheduled reminders for all active requests"""
    from email_automation import EmailRequestService
    
    result = await EmailRequestService.process_reminders()
    return result


@router.post("/email-requests/process-expired")
async def process_expired_requests(user: dict = Depends(require_admin)):
    """Mark expired requests"""
    from email_automation import EmailRequestService
    
    result = await EmailRequestService.process_expired_requests()
    return result


@router.get("/email-requests")
async def list_email_requests(
    status: Optional[str] = None,
    person_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """List email requests with optional filters"""
    from email_automation import EmailRequestService
    
    db = get_db()
    
    if person_id:
        requests = await EmailRequestService.get_requests_for_person(
            person_id=person_id,
            status=status,
            limit=limit
        )
    elif status:
        requests = await db.email_requests.find(
            {"status": status}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
    else:
        requests = await EmailRequestService.get_pending_requests(limit=limit)
    
    return {"requests": requests, "count": len(requests)}


@router.get("/email-requests/{request_id}")
async def get_email_request(
    request_id: str,
    user: dict = Depends(require_admin)
):
    """Get a specific email request with events"""
    from email_automation import EmailRequestService
    
    request = await EmailRequestService.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    events = await EmailRequestService.get_request_events(request_id)
    
    return {
        "request": request.to_dict(),
        "events": events
    }


@router.post("/email-requests/{request_id}/track")
async def track_request_event(
    request_id: str,
    event_type: str,
    details: Optional[Dict[str, Any]] = None
):
    """Track an event on a request (can be called without auth for click tracking)"""
    from email_automation import EmailRequestService, EventType
    
    try:
        evt_type = EventType(event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
    
    result = await EmailRequestService.track_event(
        request_id=request_id,
        event_type=evt_type,
        details=details
    )
    
    return result


@router.post("/email-requests/{request_id}/track-click")
async def track_request_click(request_id: str):
    """Track click event for email link (no auth required)"""
    from email_automation import EmailRequestService, EventType
    
    result = await EmailRequestService.track_event(
        request_id=request_id,
        event_type=EventType.CLICKED,
        details={"source": "email_link"}
    )
    return result


@router.post("/email-requests/{request_id}/resend")
async def resend_email_request(
    request_id: str,
    user: dict = Depends(require_admin)
):
    """Resend email for an existing request"""
    from email_automation import EmailRequestService
    
    result = await EmailRequestService.resend_request(
        request_id=request_id,
        admin_id=user.get("user_id")
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["reason"])
    
    return result


@router.post("/email-requests/{request_id}/cancel")
async def cancel_email_request(
    request_id: str,
    reason: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Cancel an email request"""
    from email_automation import EmailRequestService
    
    result = await EmailRequestService.cancel_request(
        request_id=request_id,
        admin_id=user.get("user_id"),
        reason=reason
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["reason"])
    
    return result


@router.post("/email-requests/{request_id}/complete")
async def complete_email_request(
    request_id: str,
    notes: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Mark a request as completed (admin verification)"""
    from email_automation import EmailRequestService
    
    result = await EmailRequestService.mark_completed(
        request_id=request_id,
        admin_id=user.get("user_id"),
        notes=notes
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["reason"])
    
    return result


@router.post("/email-requests/{request_id}/link-submission")
async def link_submission_to_request(
    request_id: str,
    submission_id: str,
    submission_type: str,
    user: dict = Depends(get_current_user)
):
    """Link a submission to a request"""
    from email_automation import EmailRequestService
    
    result = await EmailRequestService.link_submission(
        request_id=request_id,
        submission_id=submission_id,
        submission_type=submission_type,
        actor_id=user.get("user_id")
    )
    
    return result


# ==================== NOTIFICATION LOGS ====================

@router.get("/notifications/logs")
async def get_notification_logs(
    employee_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """Get notification logs"""
    db = get_db()
    
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if notification_type:
        query["notification_type"] = notification_type
    
    logs = await db.notification_logs.find(
        query, {"_id": 0}
    ).sort("sent_at", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "count": len(logs)}
