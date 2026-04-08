"""
Bulk Schedules Routes Module

This module handles scheduled bulk request endpoints including:
- Creating, listing, updating scheduled bulk requests
- Enabling/disabling schedules
- Running schedules manually
- Getting schedule execution history
- Quick setup for training reminders

CQC Requirement: Automated compliance renewal reminders.

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from .dependencies import (
    get_db,
    require_manager_or_admin,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bulk Schedules"])


# ==================== MODELS ====================

class ScheduleTriggerType(str, Enum):
    """When to trigger the bulk request."""
    DAYS_BEFORE_EXPIRY = "days_before_expiry"
    FIXED_INTERVAL = "fixed_interval"
    MANUAL = "manual"


class ScheduleTargetType(str, Enum):
    """What type of items the schedule targets."""
    DOCUMENTS = "documents"
    TRAINING = "training"
    FORMS = "forms"


class ScheduledBulkRequestInput(BaseModel):
    """Create or update a scheduled bulk request definition."""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    is_enabled: bool = True
    target_type: ScheduleTargetType
    trigger_type: ScheduleTriggerType = ScheduleTriggerType.DAYS_BEFORE_EXPIRY
    days_before_expiry: int = Field(60, ge=1, le=365)
    target_rules: Dict[str, Any] = Field(default_factory=lambda: {
        "employee_statuses": ["onboarding", "active"],
        "document_types": [],
        "training_codes": [],
        "form_types": [],
        "role_ids": [],
        "only_expiring": True
    })
    request_payload: Dict[str, Any] = Field(default_factory=lambda: {
        "due_days": 14,
        "custom_message": None,
        "auto_detect_missing": False
    })


# ==================== SERVICE CLASS ====================

class ScheduledBulkRequestService:
    """
    Service for managing scheduled bulk requests with durable execution.
    """
    
    @staticmethod
    async def create_schedule(data: dict, created_by: str) -> dict:
        """Create a new schedule definition."""
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        
        schedule = {
            "id": f"schedule_{uuid.uuid4().hex[:12]}",
            **data,
            "created_at": now,
            "created_by": created_by,
            "updated_at": now,
            "last_run_at": None,
            "next_run_at": None,
            "total_runs": 0,
            "total_requests_created": 0
        }
        
        await db.scheduled_bulk_requests.insert_one(schedule)
        schedule.pop("_id", None)
        return schedule
    
    @staticmethod
    async def list_schedules(include_disabled: bool = False) -> List[dict]:
        """List all schedule definitions."""
        db = get_db()
        query = {} if include_disabled else {"is_enabled": True}
        schedules = await db.scheduled_bulk_requests.find(query, {"_id": 0}).to_list(100)
        return schedules
    
    @staticmethod
    async def get_schedule(schedule_id: str) -> Optional[dict]:
        """Get a specific schedule."""
        db = get_db()
        return await db.scheduled_bulk_requests.find_one({"id": schedule_id}, {"_id": 0})
    
    @staticmethod
    async def update_schedule(schedule_id: str, data: dict, updated_by: str) -> Optional[dict]:
        """Update a schedule definition."""
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        
        # Remove protected fields
        data.pop("id", None)
        data.pop("created_at", None)
        data.pop("created_by", None)
        
        data["updated_at"] = now
        data["updated_by"] = updated_by
        
        result = await db.scheduled_bulk_requests.find_one_and_update(
            {"id": schedule_id},
            {"$set": data},
            return_document=True
        )
        
        if result:
            result.pop("_id", None)
        return result
    
    @staticmethod
    async def enable_schedule(schedule_id: str, user_id: str) -> bool:
        """Enable a schedule."""
        db = get_db()
        result = await db.scheduled_bulk_requests.update_one(
            {"id": schedule_id},
            {"$set": {
                "is_enabled": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id
            }}
        )
        return result.modified_count > 0
    
    @staticmethod
    async def disable_schedule(schedule_id: str, user_id: str) -> bool:
        """Disable a schedule."""
        db = get_db()
        result = await db.scheduled_bulk_requests.update_one(
            {"id": schedule_id},
            {"$set": {
                "is_enabled": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id
            }}
        )
        return result.modified_count > 0
    
    @staticmethod
    async def get_run_history(schedule_id: str, limit: int = 20) -> List[dict]:
        """Get execution history for a schedule."""
        db = get_db()
        runs = await db.scheduled_bulk_runs.find(
            {"schedule_id": schedule_id},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit).to_list(limit)
        return runs


# ==================== ENDPOINTS ====================

@router.post("/bulk/schedules")
async def create_bulk_schedule(
    schedule: ScheduledBulkRequestInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Create a new scheduled bulk request definition.
    
    Schedules automatically generate document/training renewal requests
    based on expiry dates, using the existing email request lifecycle.
    """
    result = await ScheduledBulkRequestService.create_schedule(
        data=schedule.model_dump(),
        created_by=user['user_id']
    )
    return result


@router.get("/bulk/schedules")
async def list_bulk_schedules(
    include_disabled: bool = False,
    user: dict = Depends(require_manager_or_admin)
):
    """List all scheduled bulk request definitions."""
    schedules = await ScheduledBulkRequestService.list_schedules(include_disabled)
    return {"schedules": schedules, "total": len(schedules)}


@router.get("/bulk/schedules/{schedule_id}")
async def get_bulk_schedule(
    schedule_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Get a specific schedule definition."""
    schedule = await ScheduledBulkRequestService.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.put("/bulk/schedules/{schedule_id}")
async def update_bulk_schedule(
    schedule_id: str,
    data: dict = Body(...),
    user: dict = Depends(require_manager_or_admin)
):
    """Update a schedule definition."""
    result = await ScheduledBulkRequestService.update_schedule(
        schedule_id=schedule_id,
        data=data,
        updated_by=user['user_id']
    )
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return result


@router.post("/bulk/schedules/{schedule_id}/enable")
async def enable_bulk_schedule(
    schedule_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Enable a schedule for automatic execution."""
    success = await ScheduledBulkRequestService.enable_schedule(schedule_id, user['user_id'])
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "enabled", "schedule_id": schedule_id}


@router.post("/bulk/schedules/{schedule_id}/disable")
async def disable_bulk_schedule(
    schedule_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Disable a schedule. Stops future runs but does NOT delete history
    or cancel already-created pending requests.
    """
    success = await ScheduledBulkRequestService.disable_schedule(schedule_id, user['user_id'])
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "disabled", "schedule_id": schedule_id}


@router.post("/bulk/schedules/{schedule_id}/run-now")
async def run_bulk_schedule_now(
    schedule_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Manually trigger a schedule execution immediately.
    Useful for testing or one-off runs.
    """
    # Note: Complex execution logic remains in server.py
    # This endpoint delegates to server.py's ScheduledBulkRequestService
    from server import ScheduledBulkRequestService as ServerService
    
    schedule = await ServerService.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    result = await ServerService.execute_schedule(schedule, triggered_by=user['user_id'])
    return result


@router.get("/bulk/schedules/{schedule_id}/history")
async def get_bulk_schedule_history(
    schedule_id: str,
    limit: int = 20,
    user: dict = Depends(require_manager_or_admin)
):
    """Get execution history for a schedule."""
    schedule = await ScheduledBulkRequestService.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    runs = await ScheduledBulkRequestService.get_run_history(schedule_id, limit)
    return {"schedule_id": schedule_id, "runs": runs, "total": len(runs)}


@router.post("/bulk/schedules/run-all-due")
async def run_all_due_schedules(
    user: dict = Depends(require_manager_or_admin)
):
    """
    Check and run all schedules that are due for execution.
    Called by cron job or manually.
    """
    # Note: Complex execution logic remains in server.py
    from server import ScheduledBulkRequestService as ServerService
    
    results = await ServerService.run_all_due_schedules(triggered_by=user['user_id'])
    return results


@router.post("/bulk/schedules/quick-setup-training-reminders")
async def quick_setup_training_reminders(
    user: dict = Depends(require_manager_or_admin)
):
    """
    Quick setup: Creates 3 training renewal reminder schedules at 60, 30, and 7 days.
    
    This creates a complete multi-threshold reminder system for training certificates:
    - 60 days before expiry: Early warning
    - 30 days before expiry: Standard reminder  
    - 7 days before expiry: Urgent final notice
    """
    db = get_db()
    
    # Check if training schedules already exist
    existing = await db.scheduled_bulk_requests.find({
        "target_type": "training",
        "name": {"$regex": "Training Renewal"}
    }, {"_id": 0}).to_list(10)
    
    if len(existing) >= 3:
        return {
            "status": "already_configured",
            "message": "Training renewal reminders are already set up",
            "existing_schedules": [{"id": s["id"], "name": s["name"], "is_enabled": s.get("is_enabled", True)} for s in existing]
        }
    
    # Define the 3 reminder thresholds
    reminder_configs = [
        {
            "name": "Training Renewal - 60 Day Early Warning",
            "description": "Sends early reminders 60 days before training expires.",
            "days_before_expiry": 60,
            "custom_message": "Your training certification is due to expire in approximately 60 days. Please start planning your renewal now."
        },
        {
            "name": "Training Renewal - 30 Day Reminder",
            "description": "Standard reminder 30 days before expiry.",
            "days_before_expiry": 30,
            "custom_message": "Your training certification will expire in 30 days. Please upload your renewed certificate."
        },
        {
            "name": "Training Renewal - 7 Day Urgent Notice",
            "description": "Urgent final notice 7 days before expiry.",
            "days_before_expiry": 7,
            "custom_message": "URGENT: Your training certification expires in 7 days. Immediate action required."
        }
    ]
    
    created_schedules = []
    
    for config in reminder_configs:
        # Skip if similar schedule exists
        existing_similar = await db.scheduled_bulk_requests.find_one({
            "target_type": "training",
            "days_before_expiry": config["days_before_expiry"]
        })
        if existing_similar:
            created_schedules.append({
                "id": existing_similar["id"],
                "name": existing_similar["name"],
                "status": "already_exists"
            })
            continue
        
        schedule_data = {
            "name": config["name"],
            "description": config["description"],
            "is_enabled": True,
            "target_type": "training",
            "trigger_type": "days_before_expiry",
            "days_before_expiry": config["days_before_expiry"],
            "target_rules": {
                "employee_statuses": ["onboarding", "active"],
                "training_codes": [],
                "only_expiring": True
            },
            "request_payload": {
                "due_days": 14,
                "custom_message": config["custom_message"]
            }
        }
        
        schedule = await ScheduledBulkRequestService.create_schedule(
            data=schedule_data,
            created_by=user['user_id']
        )
        
        created_schedules.append({
            "id": schedule["id"],
            "name": schedule["name"],
            "days_before_expiry": config["days_before_expiry"],
            "status": "created"
        })
    
    return {
        "status": "configured",
        "message": "Training renewal reminder schedules created",
        "schedules": created_schedules
    }
