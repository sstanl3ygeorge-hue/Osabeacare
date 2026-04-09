"""
Admin Operations Routes Module

This module handles administrative endpoints including:
- Organization settings
- Email reminders and document expiry alerts
- System health and audit endpoints

Extracted from server.py for modularity.
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    UserRole,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin Operations"])


# ==================== ORGANIZATION SETTINGS ====================

class OrgSettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    tagline: Optional[str] = None
    primary_color: Optional[str] = None
    logo_url: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None


@router.get("/org-settings")
async def get_org_settings():
    """
    Get organization settings for branding.
    Public endpoint - no auth required for basic branding.
    """
    db = get_db()
    
    settings = await db.org_settings.find_one({"id": "default"}, {"_id": 0})
    
    if not settings:
        # Return defaults
        return {
            "id": "default",
            "company_name": "Osabea Healthcare",
            "tagline": "Care Recruitment Excellence",
            "primary_color": "#2563EB",
            "logo_url": None,
            "support_email": "info@osabeacaresolutions.co.uk",
            "support_phone": None
        }
    
    return settings


@router.put("/org-settings")
async def update_org_settings(
    settings: OrgSettingsUpdate,
    user: dict = Depends(require_admin)
):
    """Update organization settings. Admin only."""
    db = get_db()
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        k: v for k, v in settings.model_dump().items() if v is not None
    }
    update_data["updated_at"] = now
    update_data["updated_by"] = user.get("user_id")
    
    result = await db.org_settings.update_one(
        {"id": "default"},
        {
            "$set": update_data,
            "$setOnInsert": {"id": "default", "created_at": now}
        },
        upsert=True
    )
    
    _ = result  # Acknowledge update result
    
    await log_audit_action(
        user.get("user_id"),
        "update_org_settings",
        "org_settings",
        "default",
        update_data
    )
    
    return await get_org_settings()


# ==================== DOCUMENT EXPIRY ALERTS ====================

@router.get("/admin/document-expiry-alerts")
async def get_document_expiry_alerts(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """
    Get documents expiring within specified days.
    Used by DocumentExpiryAlerts admin component.
    """
    db = get_db()
    
    now = datetime.now(timezone.utc)
    cutoff = (now + timedelta(days=days)).isoformat()
    
    # Get expiring documents - use global constant for sync
    from server import EXCLUDED_DOC_STATUSES
    expiring_docs = await db.employee_documents.find(
        {
            "expiry_date": {"$lte": cutoff, "$gt": now.isoformat()},
            "status": {"$nin": EXCLUDED_DOC_STATUSES}
        },
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(100)
    
    # Enrich with employee names
    for doc in expiring_docs:
        emp = await db.employees.find_one(
            {"id": doc.get("employee_id")},
            {"_id": 0, "first_name": 1, "last_name": 1, "email": 1}
        )
        if emp:
            doc["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            doc["employee_email"] = emp.get("email")
        
        # Calculate days until expiry
        if doc.get("expiry_date"):
            try:
                exp_date = datetime.fromisoformat(doc["expiry_date"].replace("Z", "+00:00"))
                doc["days_until_expiry"] = (exp_date - now).days
            except (ValueError, AttributeError):
                doc["days_until_expiry"] = None
    
    # Get expiring training
    expiring_training = await db.training_records.find(
        {
            "expiry_date": {"$lte": cutoff, "$gt": now.isoformat()},
            "record_status": {"$ne": "superseded"}
        },
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(100)
    
    # Enrich training with employee names
    for record in expiring_training:
        emp = await db.employees.find_one(
            {"id": record.get("employee_id")},
            {"_id": 0, "first_name": 1, "last_name": 1, "email": 1}
        )
        if emp:
            record["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            record["employee_email"] = emp.get("email")
        
        # Calculate days until expiry
        if record.get("expiry_date"):
            try:
                exp_date = datetime.fromisoformat(record["expiry_date"].replace("Z", "+00:00"))
                record["days_until_expiry"] = (exp_date - now).days
            except (ValueError, AttributeError):
                record["days_until_expiry"] = None
    
    return {
        "documents": expiring_docs,
        "training": expiring_training,
        "total_expiring": len(expiring_docs) + len(expiring_training),
        "as_of": now.isoformat()
    }


# ==================== EMAIL REMINDER TRIGGERS ====================

@router.post("/admin/send-all-expiry-reminders")
async def send_all_expiry_reminders(
    user: dict = Depends(require_admin)
):
    """
    Manually trigger expiry reminder emails for all items expiring soon.
    Used by "Send All Reminders" button in admin dashboard.
    """
    db = get_db()
    
    now = datetime.now(timezone.utc)
    sent_count = 0
    errors = []
    
    # Get items expiring in next 30 days
    cutoff = (now + timedelta(days=30)).isoformat()
    
    # Document reminders
    expiring_docs = await db.employee_documents.find(
        {
            "expiry_date": {"$lte": cutoff, "$gt": now.isoformat()},
            "status": "verified"
        },
        {"_id": 0}
    ).to_list(200)
    
    for doc in expiring_docs:
        try:
            emp = await db.employees.find_one(
                {"id": doc.get("employee_id")},
                {"_id": 0, "email": 1, "first_name": 1}
            )
            if emp and emp.get("email"):
                # Record reminder sent
                await db.reminder_logs.insert_one({
                    "id": str(uuid.uuid4()),
                    "type": "document_expiry",
                    "document_id": doc.get("id"),
                    "employee_id": doc.get("employee_id"),
                    "email": emp.get("email"),
                    "sent_at": now.isoformat(),
                    "triggered_by": user.get("user_id")
                })
                sent_count += 1
        except Exception as e:
            errors.append(f"Doc {doc.get('id')}: {str(e)}")
    
    # Training reminders
    expiring_training = await db.training_records.find(
        {
            "expiry_date": {"$lte": cutoff, "$gt": now.isoformat()},
            "record_status": {"$ne": "superseded"}
        },
        {"_id": 0}
    ).to_list(200)
    
    for record in expiring_training:
        try:
            emp = await db.employees.find_one(
                {"id": record.get("employee_id")},
                {"_id": 0, "email": 1, "first_name": 1}
            )
            if emp and emp.get("email"):
                await db.reminder_logs.insert_one({
                    "id": str(uuid.uuid4()),
                    "type": "training_expiry",
                    "training_id": record.get("id"),
                    "employee_id": record.get("employee_id"),
                    "email": emp.get("email"),
                    "sent_at": now.isoformat(),
                    "triggered_by": user.get("user_id")
                })
                sent_count += 1
        except Exception as e:
            errors.append(f"Training {record.get('id')}: {str(e)}")
    
    await log_audit_action(
        user.get("user_id"),
        "send_all_expiry_reminders",
        "system",
        "reminders",
        {"sent_count": sent_count, "errors": len(errors)}
    )
    
    return {
        "success": True,
        "reminders_sent": sent_count,
        "errors": errors[:10] if errors else []  # Limit error list
    }


# ==================== SYSTEM AUDIT ====================

@router.get("/admin/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Get audit logs with optional filtering."""
    db = get_db()
    
    query = {}
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    if resource_type:
        query["resource_type"] = resource_type
    
    logs = await db.audit_logs.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "logs": logs,
        "count": len(logs)
    }


@router.get("/admin/system-health")
async def get_system_health(user: dict = Depends(require_admin)):
    """Get system health metrics."""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    
    # Collection counts
    employees_count = await db.employees.count_documents({})
    documents_count = await db.employee_documents.count_documents({})
    training_count = await db.training_records.count_documents({})
    users_count = await db.users.count_documents({})
    
    # Recent activity
    recent_logins = await db.audit_logs.count_documents({
        "action": {"$in": ["login", "worker_login"]},
        "timestamp": {"$gte": (now - timedelta(hours=24)).isoformat()}
    })
    
    recent_uploads = await db.employee_documents.count_documents({
        "uploaded_at": {"$gte": (now - timedelta(hours=24)).isoformat()}
    })
    
    return {
        "status": "healthy",
        "timestamp": now.isoformat(),
        "collections": {
            "employees": employees_count,
            "documents": documents_count,
            "training_records": training_count,
            "users": users_count
        },
        "activity_24h": {
            "logins": recent_logins,
            "document_uploads": recent_uploads
        }
    }
