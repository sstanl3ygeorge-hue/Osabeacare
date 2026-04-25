"""
Audit & Email Templates routes for compliance tracking and templated notifications.

Handles:
- Email template CRUD and sending
- Admin audit trail recording and viewing
- Training audit reports and exports
- Compliance audit actions
"""

import os
import io
import csv
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, List

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
    SENDER_EMAIL
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["Audit & Email Templates"])


# ==================== PYDANTIC MODELS ====================

class SendEmailRequest(BaseModel):
    template_key: str
    employee_id: str
    custom_data: Optional[Dict[str, str]] = None


# ==================== COMPLIANCE AUDIT ACTIONS ====================
# Define compliance-relevant audit actions for filtering

COMPLIANCE_AUDIT_ACTIONS = {
    # Document actions
    "upload_evidence", "document_uploaded", "document_replaced", "document_removed", "document_verified",
    "verify_requirement", "unverify_requirement", "delete_evidence", "remove_evidence",
    # Policy actions
    "policy_assigned", "policy_viewed", "policy_acknowledged", "policy_admin_reviewed",
    "policy_uploaded", "policy_unassigned", "policy_withdrawn",
    # Status changes
    "status_change", "refresh_status", "update_employee",
    # Form actions (if they generate evidence)
    "signoff_form", "complete_form",
    # Training
    "upload_training_certificate", "verify_training",
    # Organisation settings
    "org_settings_updated"
}


# ==================== LAZY IMPORTS ====================

def get_resend():
    """Lazy import of resend module"""
    import resend
    return resend


def get_email_templates():
    """Lazy import of EMAIL_TEMPLATES from server.py"""
    from server import EMAIL_TEMPLATES
    return EMAIL_TEMPLATES


def get_log_audit_change():
    """Lazy import of log_audit_change from server.py"""
    from server import log_audit_change
    return log_audit_change


def get_training_audit_export():
    """Lazy import of get_training_audit_export from server.py"""
    from server import get_training_audit_export
    return get_training_audit_export


def get_evaluate_employee_training_status():
    """Lazy import of evaluate_employee_training_status from server.py"""
    from server import evaluate_employee_training_status
    return evaluate_employee_training_status


def get_employees_repo():
    """Lazy import of employees_repo from server.py"""
    from server import employees_repo
    return employees_repo


# ==================== EMAIL TEMPLATE ENDPOINTS ====================

@router.get("/email-templates")
async def get_email_templates_list(user: dict = Depends(require_manager_or_admin)):
    """Get all available email templates"""
    EMAIL_TEMPLATES = get_email_templates()
    return EMAIL_TEMPLATES


@router.get("/email-templates/{template_key}")
async def get_email_template(template_key: str, user: dict = Depends(require_manager_or_admin)):
    """Get a specific email template by key"""
    EMAIL_TEMPLATES = get_email_templates()
    
    if template_key not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Email template not found")
    return EMAIL_TEMPLATES[template_key]


@router.post("/send-email")
async def send_templated_email(request: SendEmailRequest, user: dict = Depends(require_manager_or_admin)):
    """Send an email using a template"""
    db = get_db()
    resend = get_resend()
    EMAIL_TEMPLATES = get_email_templates()
    
    if not resend.api_key:
        raise HTTPException(status_code=503, detail="Email service not configured")
    
    if request.template_key not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": request.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    template = EMAIL_TEMPLATES[request.template_key]
    
    # Build template variables
    variables = {
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee.get('employee_code') or employee.get('applicant_reference') or 'N/A',
        "portal_url": os.environ.get('PORTAL_URL', 'https://portal.osabea.care'),
        **(request.custom_data or {})
    }
    
    # Substitute variables in template
    subject = template['subject']
    body = template['body']
    for key, value in variables.items():
        body = body.replace(f"{{{key}}}", str(value))
        subject = subject.replace(f"{{{key}}}", str(value))
    
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [employee['email']],
            "subject": subject,
            "html": f"<div style='font-family: Arial, sans-serif; line-height: 1.6;'>{body.replace(chr(10), '<br>')}</div>"
        })
        
        await log_audit_action(user['user_id'], "send_email", "email", request.template_key, {
            "employee_id": request.employee_id,
            "template": request.template_key
        })
        
        return {"message": "Email sent successfully", "recipient": employee['email']}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


# ==================== ADMIN AUDIT ENDPOINTS ====================

@router.post("/admin/audit-change")
async def record_audit_change(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    field_name: str = Query(...),
    old_value: str = Query(default=None),
    new_value: str = Query(default=None),
    reason: str = Query(..., min_length=10),
    action: str = Query(default="field_updated"),
    user: dict = Depends(require_admin)
):
    """
    Record an admin change with before/after values and reason.
    Used for CQC compliance audit trail.
    """
    log_audit_change = get_log_audit_change()
    
    audit_entry = await log_audit_change(
        user_id=user['user_id'],
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        reason=reason
    )
    
    return {
        "success": True,
        "audit_id": audit_entry["id"],
        "message": "Change recorded in audit trail"
    }


@router.get("/admin/audit-trail/{entity_type}/{entity_id}")
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(get_current_user)
):
    """
    Get audit trail for a specific entity.
    """
    db = get_db()
    
    audit_entries = await db.audit_logs.find(
        {
            "entity_type": entity_type,
            "entity_id": entity_id
        },
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entries": audit_entries,
        "total": len(audit_entries)
    }


@router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    user_id: Optional[str] = None,
    compliance_only: bool = False,
    limit: int = 100,
    user: dict = Depends(require_manager_or_admin)
):
    db = get_db()
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    
    # Search by entity_id OR metadata.employee_id
    if entity_id:
        if employee_id:
            query["$or"] = [
                {"entity_id": entity_id},
                {"metadata.employee_id": entity_id},
                {"entity_id": employee_id},
                {"metadata.employee_id": employee_id}
            ]
        else:
            query["$or"] = [
                {"entity_id": entity_id},
                {"metadata.employee_id": entity_id}
            ]
    elif employee_id:
        query["$or"] = [
            {"entity_id": employee_id},
            {"metadata.employee_id": employee_id}
        ]
    
    if user_id:
        query["user_id"] = user_id
    
    # Filter to compliance-relevant actions only
    if compliance_only:
        query["action"] = {"$in": list(COMPLIANCE_AUDIT_ACTIONS)}
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Enrich with user names and transform metadata to details for frontend compatibility
    for log in logs:
        if log.get('user_id'):
            user_doc = await db.users.find_one({"user_id": log['user_id']}, {"_id": 0})
            if user_doc:
                log['user_name'] = user_doc.get('name', 'Unknown')
        # Copy metadata to details for frontend compatibility
        if 'metadata' in log and 'details' not in log:
            log['details'] = log['metadata']
    
    return logs


# ==================== TRAINING AUDIT ENDPOINTS ====================

@router.get("/audit/employee/{employee_id}/training")
async def get_employee_training_audit(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get detailed training audit data for a specific employee.
    
    This is the canonical training audit export for CQC inspections.
    Includes verification metadata, blocking reasons, and evidence traceability.
    """
    db = get_db()
    get_training_audit_export_func = get_training_audit_export()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "role": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    training_audit = await get_training_audit_export_func(employee_id, employee.get("role", ""))
    
    await log_audit_action(user['user_id'], "view_training_audit", "employee", employee_id, {})
    
    return training_audit


@router.get("/audit/training/summary")
async def get_training_audit_summary(
    user: dict = Depends(get_current_user)
):
    """
    Get organization-wide training audit summary.
    
    Returns aggregate training compliance data for all employees,
    suitable for CQC compliance reporting and inspection preparation.
    """
    employees_repo = get_employees_repo()
    evaluate_employee_training_status = get_evaluate_employee_training_status()
    
    employees = await employees_repo.list_employees(
        projection={"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1, "employee_code": 1}
    )
    
    summary = {
        "total_employees": len(employees),
        "fully_compliant": 0,
        "with_warnings": 0,
        "with_blockers": 0,
        "training_items_verified": 0,
        "training_items_pending": 0,
        "training_items_missing": 0,
        "training_items_expired": 0,
        "blocked_employees": [],
        "warning_employees": [],
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
    
    for emp in employees:
        training_eval = await evaluate_employee_training_status(emp['id'], emp.get('role', ''))
        
        blocker_count = training_eval.get('blockerCount', 0)
        warning_count = training_eval.get('warningCount', 0)
        
        emp_info = {
            "id": emp['id'],
            "employee_code": emp.get('employee_code'),
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        }
        
        if blocker_count > 0:
            summary['with_blockers'] += 1
            blockers = [i for i in training_eval.get('items', []) if i.get('blocker') and i.get('status') in ['missing', 'expired', 'awaiting_review']]
            summary['blocked_employees'].append({
                **emp_info,
                "blocker_count": blocker_count,
                "blockers": [{"title": b.get('title'), "status": b.get('status'), "detail": b.get('detail')} for b in blockers]
            })
        elif warning_count > 0:
            summary['with_warnings'] += 1
            warnings = [i for i in training_eval.get('items', []) if not i.get('blocker') and i.get('status') in ['missing', 'expired', 'due_soon', 'awaiting_review']]
            summary['warning_employees'].append({
                **emp_info,
                "warning_count": warning_count,
                "warnings": [{"title": w.get('title'), "status": w.get('status'), "detail": w.get('detail')} for w in warnings]
            })
        else:
            summary['fully_compliant'] += 1
        
        # Count training items by status
        for item in training_eval.get('items', []):
            status = item.get('status')
            if status == 'verified':
                summary['training_items_verified'] += 1
            elif status == 'completed':
                summary['training_items_verified'] += 1
            elif status == 'awaiting_review':
                summary['training_items_pending'] += 1
            elif status == 'missing':
                summary['training_items_missing'] += 1
            elif status == 'expired':
                summary['training_items_expired'] += 1
            elif status == 'due_soon':
                summary['training_items_pending'] += 1
    
    await log_audit_action(user['user_id'], "view_training_audit_summary", "system", "training", {})
    
    return summary


@router.get("/audit/training/export")
async def export_training_audit_data(
    format: str = "json",
    user: dict = Depends(require_manager_or_admin)
):
    """
    Export complete training audit data for all employees.
    
    Suitable for:
    - CQC inspection evidence packages
    - Internal audit reports
    - Compliance documentation
    
    Format: 'json' or 'csv'
    """
    employees_repo = get_employees_repo()
    get_training_audit_export_func = get_training_audit_export()
    
    employees = await employees_repo.list_employees(
        projection={"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1, "employee_code": 1, "applicant_reference": 1, "email": 1}
    )
    
    export_data = []
    
    for emp in employees:
        training_audit = await get_training_audit_export_func(emp['id'], emp.get('role', ''))
        
        emp_export = {
            "employee_id": emp.get('employee_code') or emp.get('applicant_reference') or emp['id'],
            "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "employee_email": emp.get('email'),
            "role": emp.get('role'),
            "training_status": training_audit.get('overall_status'),
            "training_status_label": training_audit.get('overall_status_label'),
            "is_work_ready_from_training": training_audit.get('is_work_ready_from_training'),
            "blocker_count": training_audit.get('blocker_count'),
            "warning_count": training_audit.get('warning_count'),
            "total_required": training_audit.get('total_required'),
            "total_compliant": training_audit.get('total_compliant'),
            "blocking_reasons": training_audit.get('blocking_reasons', []),
            "items": training_audit.get('items', []),
            "evaluated_at": training_audit.get('evaluated_at')
        }
        export_data.append(emp_export)
    
    await log_audit_action(user['user_id'], "export_training_audit", "system", "training", {"format": format, "employee_count": len(employees)})
    
    if format == 'csv':
        # Flatten to CSV-friendly structure
        output = io.StringIO()
        fieldnames = [
            'employee_id', 'employee_name', 'email', 'role', 
            'training_status', 'is_work_ready', 'blocker_count', 'warning_count',
            'total_required', 'total_compliant', 'blocking_reasons'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for emp in export_data:
            writer.writerow({
                'employee_id': emp['employee_id'],
                'employee_name': emp['employee_name'],
                'email': emp['employee_email'],
                'role': emp['role'],
                'training_status': emp['training_status_label'],
                'is_work_ready': 'Yes' if emp['is_work_ready_from_training'] else 'No',
                'blocker_count': emp['blocker_count'],
                'warning_count': emp['warning_count'],
                'total_required': emp['total_required'],
                'total_compliant': emp['total_compliant'],
                'blocking_reasons': '; '.join(emp['blocking_reasons'])
            })
        
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="training_audit_{datetime.now().strftime("%Y%m%d")}.csv"'}
        )
    
    # Default: JSON
    return {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "total_employees": len(export_data),
        "employees": export_data
    }


# ==================== GLOBAL AUDIT LOG ====================

@router.get("/audit/global-log")
async def get_global_audit_log(
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=200, le=500),
    user: dict = Depends(require_manager_or_admin),
):
    """Read-only global audit log viewer. Reads from existing audit_logs collection.
    Filters on fields actually written by log_audit_action: resource_type, action, user_id, timestamp."""
    db = get_db()

    query: Dict = {}

    if resource_type:
        query["resource_type"] = resource_type
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id

    # timestamp is stored as ISO string by log_audit_action
    if date_from or date_to:
        ts_filter: Dict = {}
        if date_from:
            ts_filter["$gte"] = date_from
        if date_to:
            # include the full end day
            ts_filter["$lte"] = date_to + "T23:59:59Z"
        query["timestamp"] = ts_filter

    logs = (
        await db.audit_logs.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
        .to_list(limit)
    )

    # Enrich with actor name where possible
    user_cache: Dict = {}
    for log in logs:
        uid = log.get("user_id")
        if uid:
            if uid not in user_cache:
                u = await db.users.find_one({"user_id": uid}, {"_id": 0, "name": 1, "email": 1})
                user_cache[uid] = u.get("name") or u.get("email") or uid if u else uid
            log["actor_name"] = user_cache[uid]

    return {"logs": logs, "count": len(logs)}
