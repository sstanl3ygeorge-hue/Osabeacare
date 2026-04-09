"""
Email Notification Engine Routes - Automated compliance & recruitment notifications.

This module handles:
- CV gap detection notifications
- Reference verification alerts
- Document expiry notifications (30/60 days)
- Training expiry alerts
- Missing mandatory items notifications
- Unverified submission alerts
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from .dependencies import (
    get_db, get_current_user, require_admin,
    log_audit_action
)

router = APIRouter(tags=["Email Notifications"])

# Configuration
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@osabea.care')
PORTAL_URL = os.environ.get('PORTAL_URL', 'https://app.osabeacares.co.uk')


# Notification Types
class NotificationType:
    # Recruitment triggers
    CV_GAP_DETECTED = "cv_gap_detected"
    REFERENCE_NOT_VERIFIED = "reference_not_verified"
    REFERENCE_MISMATCH = "reference_mismatch"
    MISSING_PROOF_OF_ADDRESS = "missing_proof_of_address"
    
    # Compliance triggers
    DOCUMENT_EXPIRING_60_DAYS = "document_expiring_60_days"
    DOCUMENT_EXPIRING_30_DAYS = "document_expiring_30_days"
    TRAINING_EXPIRED = "training_expired"
    MISSING_MANDATORY_ITEM = "missing_mandatory_item"
    UNVERIFIED_SUBMISSION = "unverified_submission"


# Email Templates for Notifications
NOTIFICATION_TEMPLATES = {
    NotificationType.CV_GAP_DETECTED: {
        "subject": "Employment Gap Requires Explanation - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Employment Gap Detected</h2>
            <p>Dear {employee_name},</p>
            <p>We have identified a gap in your employment history that requires explanation:</p>
            <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
                <strong>Gap Period:</strong> {gap_start} to {gap_end}<br>
                <strong>Duration:</strong> {gap_days} days<br>
                <strong>Between:</strong> {previous_job} → {next_job}
            </div>
            <p>Please log in to provide an explanation for this gap:</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Explain Gap</a></p>
            <p>Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">CV Gap Alert: {employee_name}</h2>
            <p>An employment gap has been detected for <strong>{employee_name}</strong>:</p>
            <div style="background: #f8f9fa; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
                <strong>Gap Period:</strong> {gap_start} to {gap_end}<br>
                <strong>Duration:</strong> {gap_days} days<br>
                <strong>Between:</strong> {previous_job} → {next_job}
            </div>
            <p>The employee has been notified to provide an explanation.</p>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee Profile</a></p>
        </div>
        """
    },
    
    NotificationType.REFERENCE_NOT_VERIFIED: {
        "subject": "Reference Verification Required - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Reference Verification Required</h2>
            <p>Dear {employee_name},</p>
            <p>Your reference from <strong>{reference_name}</strong> at <strong>{reference_company}</strong> requires verification.</p>
            <p>Please ensure your reference contact details are correct and that your referee is available to respond.</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Update Reference</a></p>
            <p>Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Reference Pending: {employee_name}</h2>
            <p>Reference {reference_num} for <strong>{employee_name}</strong> requires verification.</p>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee Profile</a></p>
        </div>
        """
    },
    
    NotificationType.DOCUMENT_EXPIRING_30_DAYS: {
        "subject": "Document Expiring Soon - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Document Expiring in 30 Days</h2>
            <p>Dear {employee_name},</p>
            <p>Your <strong>{document_name}</strong> is due to expire on <strong>{expiry_date}</strong>.</p>
            <p>Please upload your renewed document as soon as possible.</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Upload Document</a></p>
            <p>Kind regards,<br><strong>Osabea Compliance Team</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Document Expiring: {employee_name}</h2>
            <p><strong>{document_name}</strong> for {employee_name} expires on <strong>{expiry_date}</strong>.</p>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee</a></p>
        </div>
        """
    },
    
    NotificationType.DOCUMENT_EXPIRING_60_DAYS: {
        "subject": "Document Expiring in 60 Days - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ffc107;">Document Expiring in 60 Days</h2>
            <p>Dear {employee_name},</p>
            <p>Your <strong>{document_name}</strong> will expire on <strong>{expiry_date}</strong>.</p>
            <p>Please plan to renew this document before expiry.</p>
            <p>Kind regards,<br><strong>Osabea Compliance Team</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ffc107;">Document Expiring (60 days): {employee_name}</h2>
            <p><strong>{document_name}</strong> for {employee_name} expires on <strong>{expiry_date}</strong>.</p>
        </div>
        """
    },
    
    NotificationType.TRAINING_EXPIRED: {
        "subject": "Training Expired - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Training Has Expired</h2>
            <p>Dear {employee_name},</p>
            <p>Your <strong>{training_name}</strong> training expired on <strong>{expiry_date}</strong>.</p>
            <p>Please complete your refresher training as soon as possible.</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Training</a></p>
            <p>Kind regards,<br><strong>Osabea Training Team</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Training Expired: {employee_name}</h2>
            <p><strong>{training_name}</strong> for {employee_name} expired on <strong>{expiry_date}</strong>.</p>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee</a></p>
        </div>
        """
    },
    
    NotificationType.MISSING_MANDATORY_ITEM: {
        "subject": "Missing Compliance Document - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Missing Compliance Document</h2>
            <p>Dear {employee_name},</p>
            <p>Your compliance record is missing: <strong>{document_name}</strong> ({category}).</p>
            <p>Please upload this document to complete your compliance requirements.</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Upload Document</a></p>
            <p>Kind regards,<br><strong>Osabea Compliance Team</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Missing Document: {employee_name}</h2>
            <p><strong>{document_name}</strong> ({category}) is missing for {employee_name}.</p>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee</a></p>
        </div>
        """
    },
    
    NotificationType.UNVERIFIED_SUBMISSION: {
        "subject": "Unverified Submission Awaiting Review",
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ffc107;">Unverified Submission</h2>
            <p><strong>{document_name}</strong> submitted by {employee_name} on {uploaded_at} is awaiting verification.</p>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Review Now</a></p>
        </div>
        """
    }
}


async def send_notification_email(notification_type: str, to_email: str, recipient_type: str, template_data: dict, employee_id: str):
    """Send notification email and log it"""
    # Import email service lazily
    try:
        from server import EmailService
    except ImportError:
        return {"status": "error", "reason": "EmailService not available"}
    
    db = get_db()
    
    template = NOTIFICATION_TEMPLATES.get(notification_type)
    if not template:
        return {"status": "error", "reason": f"No template for {notification_type}"}
    
    body_key = "admin_body" if recipient_type == "admin" else "employee_body"
    body_template = template.get(body_key)
    if not body_template:
        return {"status": "error", "reason": f"No {recipient_type} body template"}
    
    subject = template["subject"].format(**template_data)
    body = body_template.format(**template_data)
    
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        await EmailService.send_email(to_email, subject, body)
        status = "sent"
    except Exception as e:
        status = f"failed: {str(e)}"
    
    # Log notification
    await db.notification_logs.insert_one({
        "id": f"notif_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{employee_id[:8]}",
        "employee_id": employee_id,
        "notification_type": notification_type,
        "recipient_email": to_email,
        "recipient_type": recipient_type,
        "subject": subject,
        "status": status,
        "sent_at": now,
        "template_data": template_data
    })
    
    return {"status": status}


@router.post("/notifications/trigger-recruitment/{employee_id}")
async def trigger_recruitment_notifications(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """Trigger recruitment-related notifications for an employee"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    employee_email = employee.get('email')
    notifications_sent = []
    
    base_data = {
        "employee_name": employee_name,
        "portal_link": f"{PORTAL_URL}/portal/profile",
        "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}"
    }
    
    # Check for unverified references
    for ref_num in [1, 2]:
        ref_status = employee.get(f"reference_{ref_num}_verified")
        ref_name = employee.get(f"reference_{ref_num}_name")
        ref_company = employee.get(f"reference_{ref_num}_company")
        
        if ref_name and not ref_status:
            template_data = {
                **base_data,
                "reference_num": ref_num,
                "reference_name": ref_name or "Unknown",
                "reference_company": ref_company or "Unknown"
            }
            
            if employee_email:
                await send_notification_email(NotificationType.REFERENCE_NOT_VERIFIED, employee_email, "employee", template_data, employee_id)
            await send_notification_email(NotificationType.REFERENCE_NOT_VERIFIED, ADMIN_EMAIL, "admin", template_data, employee_id)
            notifications_sent.append(f"reference_{ref_num}_not_verified")
    
    return {"message": "Recruitment notifications triggered", "notifications_sent": notifications_sent}


@router.post("/notifications/check-expiries")
async def check_and_notify_expiries(user: dict = Depends(require_admin)):
    """Check all employees for expiring documents and training, send notifications"""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    thirty_days = now + timedelta(days=30)
    sixty_days = now + timedelta(days=60)
    
    notifications_sent = {"30_day": 0, "60_day": 0, "expired": 0}
    
    employees = await db.employees.find(
        {"status": {"$in": ["active", "onboarding"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1}
    ).to_list(1000)
    
    for emp in employees:
        employee_id = emp["id"]
        employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        employee_email = emp.get("email")
        
        base_data = {
            "employee_name": employee_name,
            "portal_link": f"{PORTAL_URL}/portal/profile",
            "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}"
        }
        
        # Check documents for expiry
        expiring_docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "expiry_date": {"$lte": sixty_days.isoformat(), "$gte": now.isoformat()},
            "status": {"$nin": ["superseded", "expired"]}
        }, {"_id": 0}).to_list(50)
        
        for item in expiring_docs:
            expiry_str = item.get('expiry_date')
            if not expiry_str:
                continue
            
            try:
                expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                continue
            
            template_data = {
                **base_data,
                "document_name": item.get('requirement_id', '').replace('_', ' ').title(),
                "expiry_date": expiry_date.strftime('%d %B %Y')
            }
            
            if expiry_date <= thirty_days:
                notification_type = NotificationType.DOCUMENT_EXPIRING_30_DAYS
                notifications_sent["30_day"] += 1
            elif expiry_date <= sixty_days:
                notification_type = NotificationType.DOCUMENT_EXPIRING_60_DAYS
                notifications_sent["60_day"] += 1
            else:
                continue
            
            if employee_email:
                await send_notification_email(notification_type, employee_email, "employee", template_data, employee_id)
            await send_notification_email(notification_type, ADMIN_EMAIL, "admin", template_data, employee_id)
        
        # Check training for expiry
        training_records = await db.training_records.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
        
        for record in training_records:
            expiry_str = record.get('expiry_date')
            if not expiry_str:
                continue
            
            try:
                expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                continue
            
            template_data = {
                **base_data,
                "training_name": record.get('training_id', '').replace('_', ' ').title(),
                "expiry_date": expiry_date.strftime('%d %B %Y'),
                "portal_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=training",
                "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=training"
            }
            
            if expiry_date < now:
                # Already expired - check if recently notified
                recent_notification = await db.notification_logs.find_one({
                    "employee_id": employee_id,
                    "notification_type": NotificationType.TRAINING_EXPIRED,
                    "template_data.training_name": record.get('training_id'),
                    "sent_at": {"$gte": (now - timedelta(days=7)).isoformat()}
                })
                
                if not recent_notification:
                    if employee_email:
                        await send_notification_email(NotificationType.TRAINING_EXPIRED, employee_email, "employee", template_data, employee_id)
                    await send_notification_email(NotificationType.TRAINING_EXPIRED, ADMIN_EMAIL, "admin", template_data, employee_id)
                    notifications_sent["expired"] += 1
    
    return {
        "message": "Expiry check complete",
        "notifications_sent": notifications_sent,
        "checked_employees": len(employees)
    }


@router.get("/notifications/logs")
async def get_notification_logs(
    employee_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(require_admin)
):
    """Get notification logs with optional filters"""
    db = get_db()
    
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if notification_type:
        query["notification_type"] = notification_type
    if status:
        query["status"] = status
    
    logs = await db.notification_logs.find(query, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "count": len(logs)}


@router.post("/notifications/trigger-missing-items/{employee_id}")
async def trigger_missing_items_notification(employee_id: str, user: dict = Depends(require_admin)):
    """Trigger notifications for missing mandatory compliance items"""
    # Import MANDATORY_ITEMS from server lazily
    from server import MANDATORY_ITEMS
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    employee_email = employee.get('email')
    
    # Get compliance status
    compliance_items = await db.compliance_status.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    compliance_map = {item['requirement_id']: item for item in compliance_items}
    
    missing_items = []
    
    for category, items in MANDATORY_ITEMS.items():
        for item in items:
            item_id = item['id']
            status = compliance_map.get(item_id, {})
            
            # Check if missing (no evidence files and not verified)
            if not status.get('evidence_files') and not status.get('verified'):
                missing_items.append({
                    "document_name": item.get('name', item_id.replace('_', ' ').title()),
                    "category": category.replace('_', ' ').title()
                })
    
    if not missing_items:
        return {"message": "No missing items found", "missing_count": 0}
    
    notifications_sent = 0
    for item in missing_items:
        template_data = {
            "employee_name": employee_name,
            "document_name": item['document_name'],
            "category": item['category'],
            "portal_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist",
            "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist"
        }
        
        if employee_email:
            await send_notification_email(
                NotificationType.MISSING_MANDATORY_ITEM,
                employee_email,
                "employee",
                template_data,
                employee_id
            )
        
        await send_notification_email(
            NotificationType.MISSING_MANDATORY_ITEM,
            ADMIN_EMAIL,
            "admin",
            template_data,
            employee_id
        )
        notifications_sent += 1
    
    return {"message": "Notifications sent", "missing_count": len(missing_items), "notifications_sent": notifications_sent}


@router.post("/notifications/unverified-submissions")
async def notify_unverified_submissions(user: dict = Depends(require_admin)):
    """Send notifications for all unverified document submissions"""
    db = get_db()
    now = datetime.now(timezone.utc)
    
    # Find all compliance items with evidence but not verified
    pipeline = [
        {"$match": {
            "evidence_files": {"$exists": True, "$ne": []},
            "verified": {"$ne": True}
        }},
        {"$lookup": {
            "from": "employees",
            "localField": "employee_id",
            "foreignField": "id",
            "as": "employee"
        }},
        {"$unwind": "$employee"}
    ]
    
    unverified_items = await db.compliance_status.aggregate(pipeline).to_list(500)
    
    notifications_sent = 0
    
    for item in unverified_items:
        employee = item.get('employee', {})
        employee_id = employee.get('id')
        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        
        # Check if already notified recently
        recent_notification = await db.notification_logs.find_one({
            "employee_id": employee_id,
            "notification_type": NotificationType.UNVERIFIED_SUBMISSION,
            "template_data.document_name": item.get('requirement_id'),
            "sent_at": {"$gte": (now - timedelta(days=1)).isoformat()}
        })
        
        if recent_notification:
            continue
        
        template_data = {
            "employee_name": employee_name,
            "document_name": item.get('requirement_id', '').replace('_', ' ').title(),
            "uploaded_at": item.get('updated_at', 'Unknown'),
            "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist"
        }
        
        await send_notification_email(
            NotificationType.UNVERIFIED_SUBMISSION,
            ADMIN_EMAIL,
            "admin",
            template_data,
            employee_id
        )
        notifications_sent += 1
    
    return {"message": "Unverified submission check complete", "notifications_sent": notifications_sent}
