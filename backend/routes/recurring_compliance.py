"""
Recurring Compliance routes for tracking supervision, competency assessments,
spot checks, training refresh, and report follow-ups.

This module implements strict, auditable recurring compliance tracking for:
- Regular supervision
- Competency assessments (every 6 months)
- Spot checks
- Training refresh/support tracking
- Report/concern follow-up

CRITICAL CONSTRAINTS:
- Every item must be: assigned, due-dated, statused, auditable, repeatable
- Status is NEVER stored stale - always computed from next_due_date
"""

import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

import resend

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
    SENDER_EMAIL,
    REPLY_TO_EMAIL
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["Recurring Compliance"])

# ==================== EMAIL CONFIG ====================
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@osabeacares.co.uk')

# ==================== ENUMS ====================

class RecurringItemType(str, Enum):
    SUPERVISION = "supervision"
    COMPETENCY_ASSESSMENT = "competency_assessment"
    SPOT_CHECK = "spot_check"
    TRAINING_REFRESH = "training_refresh"
    REPORT_FOLLOWUP = "report_followup"


class RecurringFrequency(str, Enum):
    MONTHLY = "monthly"
    BI_MONTHLY = "bi_monthly"
    QUARTERLY = "quarterly"
    SIX_MONTHLY = "six_monthly"
    ANNUAL = "annual"
    AD_HOC = "ad_hoc"  # For report_followup with explicit due dates


class RecurringItemStatus(str, Enum):
    SCHEDULED = "scheduled"    # > 30 days out
    UPCOMING = "upcoming"      # 15-30 days before due
    DUE = "due"               # 1-14 days before due
    OVERDUE = "overdue"       # Past due date
    COMPLETED = "completed"   # Most recent completion


class CompletionOutcome(str, Enum):
    SATISFACTORY = "satisfactory"
    NEEDS_IMPROVEMENT = "needs_improvement"
    ACTION_REQUIRED = "action_required"
    NOT_APPLICABLE = "not_applicable"


# ==================== CONSTANTS ====================

# Default frequencies per item type
RECURRING_ITEM_DEFAULTS = {
    "supervision": {
        "frequency": "monthly",
        "frequency_days": 30,
        "name": "Monthly Supervision",
        "description": "Regular 1:1 supervision meeting to discuss performance, wellbeing and development"
    },
    "competency_assessment": {
        "frequency": "six_monthly",
        "frequency_days": 182,
        "name": "Competency Assessment",
        "description": "Formal assessment of competency in role-specific skills"
    },
    "spot_check": {
        "frequency": "monthly",
        "frequency_days": 30,
        "name": "Spot Check",
        "description": "Unannounced observation of work practice"
    },
    "training_refresh": {
        "frequency": "annual",
        "frequency_days": 365,
        "name": "Training Refresh",
        "description": "Refresher training to maintain competency"
    },
    "report_followup": {
        "frequency": "ad_hoc",
        "frequency_days": None,
        "name": "Report/Concern Follow-up",
        "description": "Follow-up action on a reported concern or incident"
    }
}

# Frequency to days mapping
FREQUENCY_DAYS_MAP = {
    "monthly": 30,
    "bi_monthly": 60,
    "quarterly": 91,
    "six_monthly": 182,
    "annual": 365,
    "ad_hoc": None
}

# Reminder schedule (days before due)
RECURRING_REMINDER_SCHEDULE = [14, 7, 0]  # 14 days, 7 days, on due date
ESCALATION_THRESHOLD_DAYS = 7  # Escalate if overdue > 7 days


# ==================== PYDANTIC MODELS ====================

class RecurringItemCreate(BaseModel):
    employee_id: str
    item_type: str  # RecurringItemType value
    item_name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    next_due_date: str  # Required
    assigned_to: str  # User ID
    escalate_to: Optional[str] = None
    linked_report_id: Optional[str] = None
    linked_incident_id: Optional[str] = None


class RecurringItemCompletion(BaseModel):
    completed_date: str
    outcome: str
    notes: str
    evidence_url: Optional[str] = None
    support_action_required: Optional[str] = None
    follow_up_due_date: Optional[str] = None


class RecurringItemUpdate(BaseModel):
    item_name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    next_due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    escalate_to: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== NOTIFICATION TEMPLATES ====================

class RecurringNotificationType:
    COMPLIANCE_DUE_14_DAYS = "compliance_due_14_days"
    COMPLIANCE_DUE_7_DAYS = "compliance_due_7_days"
    COMPLIANCE_DUE_NOW = "compliance_due_now"
    COMPLIANCE_OVERDUE = "compliance_overdue"
    COMPLIANCE_ESCALATION = "compliance_escalation"


RECURRING_COMPLIANCE_TEMPLATES = {
    "compliance_due_14_days": {
        "subject": "Upcoming: {item_name} due in 14 days - {employee_name}",
        "body": "<h2>Upcoming Compliance Item</h2><p><strong>Employee:</strong> {employee_name}</p><p><strong>Item:</strong> {item_name}</p><p><strong>Due:</strong> {due_date}</p>"
    },
    "compliance_due_7_days": {
        "subject": "Reminder: {item_name} due in 7 days - {employee_name}",
        "body": "<h2>7-Day Reminder</h2><p><strong>Employee:</strong> {employee_name}</p><p><strong>Item:</strong> {item_name}</p><p><strong>Due:</strong> {due_date}</p>"
    },
    "compliance_due_now": {
        "subject": "DUE TODAY: {item_name} - {employee_name}",
        "body": "<h2>Due Today</h2><p><strong>Employee:</strong> {employee_name}</p><p><strong>Item:</strong> {item_name}</p><p><strong>Due:</strong> {due_date}</p>"
    },
    "compliance_overdue": {
        "subject": "OVERDUE: {item_name} - {employee_name}",
        "body": "<h2>Overdue Item</h2><p><strong>Employee:</strong> {employee_name}</p><p><strong>Item:</strong> {item_name}</p><p><strong>Days Overdue:</strong> {days_overdue}</p>"
    },
    "compliance_escalation": {
        "subject": "ESCALATION: {item_name} overdue {days_overdue} days - {employee_name}",
        "body": "<h2>Escalation Required</h2><p><strong>Employee:</strong> {employee_name}</p><p><strong>Item:</strong> {item_name}</p><p><strong>Days Overdue:</strong> {days_overdue}</p>"
    }
}


# ==================== HELPER FUNCTIONS ====================

def compute_recurring_status(next_due_date_str: Optional[str]) -> tuple:
    """
    Compute status from next_due_date. Status is NEVER stored stale - always computed.
    
    Returns: (status, days_value)
    - days_value is positive for days until due, negative for days overdue
    """
    if not next_due_date_str:
        return "scheduled", 999
    
    try:
        if isinstance(next_due_date_str, str):
            if 'T' in next_due_date_str:
                next_due = datetime.fromisoformat(next_due_date_str.replace('Z', '+00:00'))
            else:
                next_due = datetime.strptime(next_due_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            next_due = next_due_date_str
        
        now = datetime.now(timezone.utc)
        days_until = (next_due.date() - now.date()).days
        
        if days_until < 0:
            return "overdue", days_until
        elif days_until <= 14:
            return "due", days_until
        elif days_until <= 30:
            return "upcoming", days_until
        else:
            return "scheduled", days_until
    except Exception as e:
        logger.error(f"Error computing recurring status: {e}")
        return "scheduled", 999


def calculate_next_due_date(completion_date: datetime, frequency: str) -> Optional[str]:
    """
    Calculate next due date after completion based on frequency.
    Returns ISO format date string.
    """
    if frequency == "ad_hoc":
        return None  # Ad-hoc items need explicit due date
    
    days = FREQUENCY_DAYS_MAP.get(frequency)
    if not days:
        return None
    
    next_due = completion_date + timedelta(days=days)
    return next_due.strftime('%Y-%m-%d')


# ==================== ENDPOINTS ====================

@router.post("/recurring-compliance")
async def create_recurring_item(
    item: RecurringItemCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new recurring compliance item for an employee."""
    db = get_db()
    employee = await db.employees.find_one({"id": item.employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    valid_types = ["supervision", "competency_assessment", "spot_check", "training_refresh", "report_followup"]
    if item.item_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid item_type. Must be one of: {valid_types}")
    
    defaults = RECURRING_ITEM_DEFAULTS.get(item.item_type, {})
    frequency = item.frequency or defaults.get("frequency")
    
    if item.item_type == "report_followup" and not (item.linked_report_id or item.linked_incident_id):
        raise HTTPException(status_code=400, detail="report_followup requires linked_report_id or linked_incident_id")
    
    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid.uuid4())
    
    doc = {
        "id": item_id,
        "employee_id": item.employee_id,
        "item_type": item.item_type,
        "item_name": item.item_name or defaults.get("name", item.item_type),
        "description": item.description or defaults.get("description", ""),
        "frequency": frequency,
        "frequency_days": FREQUENCY_DAYS_MAP.get(frequency) if frequency else None,
        "next_due_date": item.next_due_date,
        "last_completed_date": None,
        "assigned_to": item.assigned_to,
        "escalate_to": item.escalate_to,
        "linked_report_id": item.linked_report_id,
        "linked_incident_id": item.linked_incident_id,
        "reminder_schedule": RECURRING_REMINDER_SCHEDULE,
        "reminders_sent": [],
        "escalation_threshold_days": ESCALATION_THRESHOLD_DAYS,
        "escalation_sent": False,
        "completion_history": [],
        "is_active": True,
        "created_at": now,
        "created_by": user['user_id'],
        "updated_at": now
    }
    
    await db.recurring_compliance.insert_one(doc)
    
    await log_audit_action(user['user_id'], "recurring_compliance_created", "recurring_compliance", item_id, {
        "employee_id": item.employee_id, "item_type": item.item_type, "next_due_date": item.next_due_date
    })
    
    status, days = compute_recurring_status(item.next_due_date)
    doc["computed_status"] = status
    doc["days_until_due"] = days
    doc.pop("_id", None)
    
    return doc


@router.get("/recurring-compliance")
async def get_recurring_items(
    employee_id: Optional[str] = None,
    item_type: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    include_inactive: bool = False,
    user: dict = Depends(get_current_user)
):
    """Get recurring compliance items with computed status."""
    db = get_db()
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if item_type:
        query["item_type"] = item_type
    if assigned_to:
        query["assigned_to"] = assigned_to
    if not include_inactive:
        query["is_active"] = True
    
    items = await db.recurring_compliance.find(query, {"_id": 0}).to_list(1000)
    
    result = []
    for item in items:
        computed_status, days = compute_recurring_status(item.get("next_due_date"))
        item["computed_status"] = computed_status
        item["days_until_due"] = days if days >= 0 else 0
        item["days_overdue"] = abs(days) if days < 0 else 0
        
        if status and computed_status != status:
            continue
        result.append(item)
    
    status_priority = {"overdue": 0, "due": 1, "upcoming": 2, "scheduled": 3, "completed": 4}
    result.sort(key=lambda x: (status_priority.get(x.get("computed_status"), 5), x.get("days_until_due", 999)))
    
    return result


@router.get("/recurring-compliance/dashboard-summary")
async def get_recurring_compliance_summary(user: dict = Depends(get_current_user)):
    """Get organization-wide recurring compliance summary for dashboard."""
    db = get_db()
    items = await db.recurring_compliance.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    overdue_items = []
    due_items = []
    upcoming_items = []
    
    for item in items:
        status, days = compute_recurring_status(item.get("next_due_date"))
        item["computed_status"] = status
        item["days_value"] = days
        
        employee = await db.employees.find_one({"id": item["employee_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
        item["employee_name"] = f"{employee['first_name']} {employee['last_name']}" if employee else "Unknown"
        
        if status == "overdue":
            overdue_items.append(item)
        elif status == "due":
            due_items.append(item)
        elif status == "upcoming":
            upcoming_items.append(item)
    
    overdue_items.sort(key=lambda x: x.get("days_value", 0))
    due_items.sort(key=lambda x: x.get("days_value", 999))
    upcoming_items.sort(key=lambda x: x.get("days_value", 999))
    
    return {
        "summary": {"overdue": len(overdue_items), "due": len(due_items), "upcoming": len(upcoming_items), "total_active": len(items)},
        "overdue_items": overdue_items[:10],
        "due_items": due_items[:10],
        "upcoming_items": upcoming_items[:5]
    }


@router.get("/recurring-compliance/{item_id}")
async def get_recurring_item(item_id: str, user: dict = Depends(get_current_user)):
    """Get single recurring compliance item with full history."""
    db = get_db()
    item = await db.recurring_compliance.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Recurring compliance item not found")
    
    status, days = compute_recurring_status(item.get("next_due_date"))
    item["computed_status"] = status
    item["days_until_due"] = days if days >= 0 else 0
    item["days_overdue"] = abs(days) if days < 0 else 0
    
    employee = await db.employees.find_one({"id": item["employee_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
    item["employee_name"] = f"{employee['first_name']} {employee['last_name']}" if employee else "Unknown"
    
    assigned_user = await db.users.find_one({"user_id": item.get("assigned_to")}, {"_id": 0, "name": 1})
    item["assigned_to_name"] = assigned_user.get("name") if assigned_user else "Unassigned"
    
    return item


@router.put("/recurring-compliance/{item_id}")
async def update_recurring_item(item_id: str, update: RecurringItemUpdate, user: dict = Depends(require_manager_or_admin)):
    """Update a recurring compliance item."""
    db = get_db()
    existing = await db.recurring_compliance.find_one({"id": item_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Recurring compliance item not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {"updated_at": now}
    
    if update.item_name is not None:
        update_data["item_name"] = update.item_name
    if update.description is not None:
        update_data["description"] = update.description
    if update.frequency is not None:
        update_data["frequency"] = update.frequency
        update_data["frequency_days"] = FREQUENCY_DAYS_MAP.get(update.frequency)
    if update.next_due_date is not None:
        update_data["next_due_date"] = update.next_due_date
    if update.assigned_to is not None:
        update_data["assigned_to"] = update.assigned_to
    if update.escalate_to is not None:
        update_data["escalate_to"] = update.escalate_to
    if update.is_active is not None:
        update_data["is_active"] = update.is_active
    
    await db.recurring_compliance.update_one({"id": item_id}, {"$set": update_data})
    await log_audit_action(user['user_id'], "recurring_compliance_updated", "recurring_compliance", item_id, {"changes": update_data})
    
    updated = await db.recurring_compliance.find_one({"id": item_id}, {"_id": 0})
    status, days = compute_recurring_status(updated.get("next_due_date"))
    updated["computed_status"] = status
    updated["days_until_due"] = days
    
    return updated


@router.post("/recurring-compliance/{item_id}/complete")
async def record_completion(item_id: str, completion: RecurringItemCompletion, user: dict = Depends(require_manager_or_admin)):
    """
    Record completion of a recurring compliance item.
    Auto-calculates next_due_date based on frequency.
    """
    db = get_db()
    item = await db.recurring_compliance.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Recurring compliance item not found")
    
    valid_outcomes = ["satisfactory", "needs_improvement", "action_required", "not_applicable"]
    if completion.outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"Invalid outcome. Must be one of: {valid_outcomes}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        completed_dt = datetime.fromisoformat(completion.completed_date.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        completed_dt = datetime.strptime(completion.completed_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    completion_record = {
        "id": str(uuid.uuid4()),
        "completed_date": completion.completed_date,
        "completed_by": user['user_id'],
        "completed_by_name": user.get('name', 'Unknown'),
        "outcome": completion.outcome,
        "notes": completion.notes,
        "evidence_url": completion.evidence_url,
        "recorded_at": now
    }
    
    frequency = item.get("frequency")
    if frequency and frequency != "ad_hoc":
        next_due = calculate_next_due_date(completed_dt, frequency)
    else:
        next_due = completion.follow_up_due_date
    
    update_data = {
        "last_completed_date": completion.completed_date,
        "next_due_date": next_due,
        "reminders_sent": [],
        "escalation_sent": False,
        "updated_at": now
    }
    
    await db.recurring_compliance.update_one(
        {"id": item_id},
        {"$set": update_data, "$push": {"completion_history": completion_record}}
    )
    
    await log_audit_action(user['user_id'], "recurring_compliance_completed", "recurring_compliance", item_id, {
        "employee_id": item["employee_id"], "item_type": item["item_type"],
        "completed_date": completion.completed_date, "outcome": completion.outcome, "next_due_date": next_due
    })
    
    # Create follow-up for action_required competency assessments
    if item["item_type"] == "competency_assessment" and completion.outcome == "action_required":
        if completion.support_action_required and completion.follow_up_due_date:
            followup_id = str(uuid.uuid4())
            await db.recurring_compliance.insert_one({
                "id": followup_id,
                "employee_id": item["employee_id"],
                "item_type": "report_followup",
                "item_name": f"Competency Follow-up: {completion.support_action_required}",
                "description": f"Follow-up from competency assessment. Support needed: {completion.support_action_required}",
                "frequency": "ad_hoc",
                "frequency_days": None,
                "next_due_date": completion.follow_up_due_date,
                "last_completed_date": None,
                "assigned_to": item["assigned_to"],
                "escalate_to": item.get("escalate_to"),
                "linked_report_id": None,
                "linked_incident_id": None,
                "reminder_schedule": RECURRING_REMINDER_SCHEDULE,
                "reminders_sent": [],
                "escalation_threshold_days": ESCALATION_THRESHOLD_DAYS,
                "escalation_sent": False,
                "completion_history": [],
                "is_active": True,
                "parent_item_id": item_id,
                "created_at": now,
                "created_by": user['user_id'],
                "updated_at": now
            })
    
    return {
        "status": "completed",
        "item_id": item_id,
        "completion_record": completion_record,
        "next_due_date": next_due,
        "message": f"Completion recorded. Next due: {next_due}" if next_due else "Completion recorded."
    }


@router.get("/employees/{employee_id}/recurring-compliance")
async def get_employee_recurring_items(employee_id: str, user: dict = Depends(get_current_user)):
    """Get all recurring compliance items for an employee."""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    items = await db.recurring_compliance.find({"employee_id": employee_id, "is_active": True}, {"_id": 0}).to_list(100)
    
    overdue_count = due_count = upcoming_count = 0
    result = []
    
    for item in items:
        status, days = compute_recurring_status(item.get("next_due_date"))
        item["computed_status"] = status
        item["days_until_due"] = days if days >= 0 else 0
        item["days_overdue"] = abs(days) if days < 0 else 0
        
        if status == "overdue":
            overdue_count += 1
        elif status == "due":
            due_count += 1
        elif status == "upcoming":
            upcoming_count += 1
        
        result.append(item)
    
    result.sort(key=lambda x: ({"overdue": 0, "due": 1, "upcoming": 2}.get(x.get("computed_status"), 3), x.get("days_until_due", 999)))
    
    return {
        "employee_id": employee_id,
        "summary": {"total": len(result), "overdue": overdue_count, "due": due_count, "upcoming": upcoming_count},
        "items": result
    }


@router.post("/recurring-compliance/process-reminders")
async def process_recurring_reminders(user: dict = Depends(require_admin)):
    """Process reminders for all active recurring compliance items."""
    if not resend.api_key:
        return {"status": "skipped", "reason": "Email not configured"}
    
    db = get_db()
    items = await db.recurring_compliance.find({"is_active": True}, {"_id": 0}).to_list(1000)
    results = {"processed": 0, "reminders_sent": 0, "escalations_sent": 0, "errors": []}
    now = datetime.now(timezone.utc)
    
    for item in items:
        try:
            status, days = compute_recurring_status(item.get("next_due_date"))
            
            employee = await db.employees.find_one({"id": item["employee_id"]}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
            if not employee:
                continue
            
            assigned_user = await db.users.find_one({"user_id": item.get("assigned_to")}, {"_id": 0, "name": 1, "email": 1})
            employee_name = f"{employee['first_name']} {employee['last_name']}"
            
            template_data = {
                "employee_name": employee_name,
                "item_name": item["item_name"],
                "due_date": item.get("next_due_date"),
                "days_overdue": abs(days) if days < 0 else 0
            }
            
            reminders_sent = item.get("reminders_sent", [])
            sent_days = [r.get("days_before") for r in reminders_sent]
            
            notification_type = None
            recipient_email = assigned_user.get("email") if assigned_user else ADMIN_EMAIL
            
            if status == "overdue":
                days_overdue = abs(days)
                if days_overdue > item.get("escalation_threshold_days", ESCALATION_THRESHOLD_DAYS) and not item.get("escalation_sent"):
                    notification_type = "compliance_escalation"
                    recipient_email = ADMIN_EMAIL
                    await db.recurring_compliance.update_one({"id": item["id"]}, {"$set": {"escalation_sent": True}})
                    results["escalations_sent"] += 1
                elif "overdue" not in sent_days:
                    notification_type = "compliance_overdue"
                    await db.recurring_compliance.update_one({"id": item["id"]}, {"$push": {"reminders_sent": {"days_before": "overdue", "sent_at": now.isoformat()}}})
            elif days == 0 and 0 not in sent_days:
                notification_type = "compliance_due_now"
                await db.recurring_compliance.update_one({"id": item["id"]}, {"$push": {"reminders_sent": {"days_before": 0, "sent_at": now.isoformat()}}})
            elif days <= 7 and days > 0 and 7 not in sent_days:
                notification_type = "compliance_due_7_days"
                await db.recurring_compliance.update_one({"id": item["id"]}, {"$push": {"reminders_sent": {"days_before": 7, "sent_at": now.isoformat()}}})
            elif days <= 14 and days > 7 and 14 not in sent_days:
                notification_type = "compliance_due_14_days"
                await db.recurring_compliance.update_one({"id": item["id"]}, {"$push": {"reminders_sent": {"days_before": 14, "sent_at": now.isoformat()}}})
            
            if notification_type and recipient_email:
                template = RECURRING_COMPLIANCE_TEMPLATES.get(notification_type)
                if template:
                    try:
                        subject = template["subject"].format(**template_data)
                        body = template["body"].format(**template_data)
                        
                        await asyncio.to_thread(resend.Emails.send, {
                            "from": SENDER_EMAIL,
                            "to": [recipient_email],
                            "reply_to": REPLY_TO_EMAIL,
                            "subject": subject,
                            "html": body
                        })
                        
                        await db.notification_logs.insert_one({
                            "id": str(uuid.uuid4()),
                            "notification_type": notification_type,
                            "recipient_email": recipient_email,
                            "employee_id": item["employee_id"],
                            "related_entity_type": "recurring_compliance",
                            "related_entity_id": item["id"],
                            "sent_at": now.isoformat(),
                            "status": "sent"
                        })
                        results["reminders_sent"] += 1
                    except Exception as e:
                        results["errors"].append(f"Failed: {item['id']}: {str(e)}")
            
            results["processed"] += 1
        except Exception as e:
            results["errors"].append(f"Error: {item.get('id')}: {str(e)}")
    
    return results
