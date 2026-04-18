"""
Training Management Routes Module

This module handles training-related endpoints including:
- Training records CRUD
- Training verification and approval
- Training audit and compliance reports
- Training matrix and requirements

NOTE: Some endpoints depend on helper functions that still reside in server.py.
These will be migrated to a training_service.py module in a future phase.

Extracted from server.py for modularity.
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Body, Form
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Training Management"])


# ==================== TRAINING MODELS ====================

class TrainingRecordCreate(BaseModel):
    employee_id: str
    requirement_id: str
    training_name: str
    training_type: Optional[str] = None
    completion_date: Optional[str] = None
    expiry_date: Optional[str] = None
    certificate_url: Optional[str] = None
    notes: Optional[str] = None


class TrainingRecordResponse(BaseModel):
    id: str
    employee_id: Optional[str] = None
    requirement_id: Optional[str] = None
    training_name: Optional[str] = None
    training_type: Optional[str] = None
    completion_date: Optional[str] = None
    expiry_date: Optional[str] = None
    certificate_url: Optional[str] = None
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    record_status: Optional[str] = "active"
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        extra = "ignore"


class TrainingRecordUpdateRequest(BaseModel):
    completion_date: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None


# ==================== TRAINING RECORDS CRUD ====================

@router.post("/training-records", response_model=TrainingRecordResponse)
async def create_training_record(
    record: TrainingRecordCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new training record."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    record_id = str(uuid.uuid4())
    record_data = {
        "id": record_id,
        **record.model_dump(),
        "verified": False,
        "record_status": "active",
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("user_id")
    }
    
    await db.training_records.insert_one(record_data)
    
    await log_audit_action(
        user.get("user_id"),
        "create_training_record",
        "training_record",
        record_id,
        {"employee_id": record.employee_id, "training_name": record.training_name}
    )
    
    return TrainingRecordResponse(**record_data)


@router.post("/employees/{employee_id}/training/backfill-from-proposed")
async def backfill_training_records_from_proposed(
    employee_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Backfill: create preliminary training_records for mandatory proposed items
    that don't yet have a corresponding training_record.

    Fixes the state where proposed items exist (from extraction) but the
    Mandatory tab shows 'Missing' because the evaluator only queries
    training_records.
    """
    db = get_db()
    from services.training_evaluator import resolve_mandatory_training_code
    now = datetime.now(timezone.utc).isoformat()

    proposed = await db.proposed_training_items.find(
        {"employee_id": employee_id, "status": {"$in": ["proposed", "approved"]}},
        {"_id": 0},
    ).to_list(200)

    if not proposed:
        return {"success": True, "created": 0, "message": "No proposed items to backfill"}

    created = 0
    for item in proposed:
        name = item.get("raw_course_title") or item.get("mapped_training_title") or ""
        code = resolve_mandatory_training_code(name)
        if not code:
            code = item.get("mapped_training_code")
            if not code:
                continue

        existing = await db.training_records.find_one({
            "employee_id": employee_id,
            "requirement_id": code,
            "record_status": "active",
        })
        if existing:
            continue

        await db.training_records.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "training_name": name,
            "requirement_id": code,
            "mandatory": True,
            "completion_date": item.get("completion_date") or item.get("completed_at"),
            "expiry_date": item.get("expiry_date") or item.get("expires_at"),
            "status": "completed",
            "certificate_url": None,
            "verified": False,
            "completion_method": "certificate",
            "record_status": "active",
            "source_document_id": item.get("source_document_id"),
            "intake_item_id": item.get("id"),
            "ai_extracted": True,
            "created_at": now,
            "updated_at": now,
        })
        created += 1

    if created:
        await log_audit_action(
            user.get("user_id"),
            "training_backfill_from_proposed",
            "employee",
            employee_id,
            {"created_count": created},
        )
        logger.info(f"Backfilled {created} training_records from proposed items for employee {employee_id}")

    return {
        "success": True,
        "created": created,
        "message": f"Created {created} preliminary training record(s) from proposed items",
    }


@router.get("/training-records", response_model=List[TrainingRecordResponse])
async def get_training_records(
    employee_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    verified: Optional[bool] = None,
    include_superseded: bool = False,
    user: dict = Depends(get_current_user)
):
    """Get training records with optional filtering."""
    db = get_db()
    
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if requirement_id:
        query["requirement_id"] = requirement_id
    if verified is not None:
        query["verified"] = verified
    if not include_superseded:
        query["record_status"] = {"$ne": "superseded"}
    
    records = await db.training_records.find(query, {"_id": 0}).to_list(1000)
    
    return [TrainingRecordResponse(**r) for r in records]


@router.get("/training-records/{record_id}", response_model=TrainingRecordResponse)
async def get_training_record(
    record_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific training record."""
    db = get_db()
    
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    return TrainingRecordResponse(**record)


@router.put("/training-records/{record_id}", response_model=TrainingRecordResponse)
async def update_training_record(
    record_id: str,
    update: TrainingRecordUpdateRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """Update a training record."""
    db = get_db()
    
    record = await db.training_records.find_one({"id": record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = now
    update_data["updated_by"] = user.get("user_id")
    
    await db.training_records.update_one({"id": record_id}, {"$set": update_data})
    
    updated = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    
    await log_audit_action(
        user.get("user_id"),
        "update_training_record",
        "training_record",
        record_id,
        update_data
    )
    
    return TrainingRecordResponse(**updated)


@router.delete("/training-records/{record_id}")
async def delete_training_record(
    record_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Delete a training record (soft delete - marks as superseded)."""
    db = get_db()
    
    record = await db.training_records.find_one({"id": record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.training_records.update_one(
        {"id": record_id},
        {
            "$set": {
                "record_status": "superseded",
                "superseded_at": now,
                "superseded_by": user.get("user_id"),
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user.get("user_id"),
        "delete_training_record",
        "training_record",
        record_id,
        {"employee_id": record.get("employee_id")}
    )
    
    return {"success": True, "message": "Training record deleted"}


# ==================== TRAINING VERIFICATION ====================

@router.post("/training-records/{record_id}/verify")
async def verify_training_record(
    record_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Verify a training record."""
    db = get_db()
    
    record = await db.training_records.find_one({"id": record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.training_records.update_one(
        {"id": record_id},
        {
            "$set": {
                "verified": True,
                "verified_by": user.get("user_id"),
                "verified_at": now,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user.get("user_id"),
        "verify_training_record",
        "training_record",
        record_id,
        {"employee_id": record.get("employee_id"), "training_name": record.get("training_name")}
    )
    
    return {"success": True, "message": "Training record verified"}


@router.post("/training-records/{record_id}/unverify")
async def unverify_training_record(
    record_id: str,
    reason: str = Body(..., embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """Remove verification from a training record."""
    db = get_db()
    
    record = await db.training_records.find_one({"id": record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.training_records.update_one(
        {"id": record_id},
        {
            "$set": {
                "verified": False,
                "unverified_by": user.get("user_id"),
                "unverified_at": now,
                "unverify_reason": reason,
                "updated_at": now
            },
            "$unset": {
                "verified_by": "",
                "verified_at": ""
            }
        }
    )
    
    await log_audit_action(
        user.get("user_id"),
        "unverify_training_record",
        "training_record",
        record_id,
        {"reason": reason}
    )
    
    return {"success": True, "message": "Training verification removed"}


# ==================== TRAINING EXPIRY ALERTS ====================

@router.get("/admin/training-expiry-alerts")
async def get_training_expiry_alerts(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """
    Get training records expiring within specified days.
    Used by admin dashboard for expiry management.
    """
    db = get_db()
    
    now = datetime.now(timezone.utc)
    cutoff = (now + timedelta(days=days)).isoformat()
    
    expiring = await db.training_records.find(
        {
            "expiry_date": {"$lte": cutoff, "$gt": now.isoformat()},
            "record_status": {"$ne": "superseded"}
        },
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(200)
    
    # Enrich with employee info
    for record in expiring:
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
    
    # Categorize by urgency
    critical = [r for r in expiring if r.get("days_until_expiry", 999) <= 7]
    warning = [r for r in expiring if 7 < r.get("days_until_expiry", 999) <= 14]
    upcoming = [r for r in expiring if 14 < r.get("days_until_expiry", 999) <= 30]
    
    return {
        "total": len(expiring),
        "critical": critical,
        "warning": warning,
        "upcoming": upcoming,
        "as_of": now.isoformat()
    }


@router.get("/training/expiring-summary")
async def get_training_expiring_summary(
    user: dict = Depends(get_current_user)
):
    """Get summary of training expiring in different time windows."""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    
    # Count expiring in different windows
    exp_7 = (now + timedelta(days=7)).isoformat()
    exp_14 = (now + timedelta(days=14)).isoformat()
    exp_30 = (now + timedelta(days=30)).isoformat()
    exp_60 = (now + timedelta(days=60)).isoformat()
    exp_90 = (now + timedelta(days=90)).isoformat()
    
    base_query = {"record_status": {"$ne": "superseded"}}
    
    critical = await db.training_records.count_documents({
        **base_query,
        "expiry_date": {"$lte": exp_7, "$gt": now.isoformat()}
    })
    
    warning = await db.training_records.count_documents({
        **base_query,
        "expiry_date": {"$lte": exp_14, "$gt": exp_7}
    })
    
    upcoming_30 = await db.training_records.count_documents({
        **base_query,
        "expiry_date": {"$lte": exp_30, "$gt": exp_14}
    })
    
    upcoming_60 = await db.training_records.count_documents({
        **base_query,
        "expiry_date": {"$lte": exp_60, "$gt": exp_30}
    })
    
    upcoming_90 = await db.training_records.count_documents({
        **base_query,
        "expiry_date": {"$lte": exp_90, "$gt": exp_60}
    })
    
    return {
        "critical_7_days": critical,
        "warning_14_days": warning,
        "upcoming_30_days": upcoming_30,
        "upcoming_60_days": upcoming_60,
        "upcoming_90_days": upcoming_90,
        "total_expiring_90_days": critical + warning + upcoming_30 + upcoming_60 + upcoming_90,
        "as_of": now.isoformat()
    }


# ==================== TRAINING CATALOGUE ====================

@router.get("/admin/training-catalogue")
async def get_training_catalogue(user: dict = Depends(get_current_user)):
    """Get the training catalogue with all available training types."""
    db = get_db()
    
    catalogue = await db.training_catalogue.find({}, {"_id": 0}).to_list(100)
    
    return {
        "items": catalogue,
        "count": len(catalogue)
    }


@router.get("/admin/training-catalogue/status")
async def get_training_catalogue_status(user: dict = Depends(get_current_user)):
    """Get training catalogue status and statistics."""
    db = get_db()
    
    total = await db.training_catalogue.count_documents({})
    mandatory = await db.training_catalogue.count_documents({"is_mandatory": True})
    role_specific = await db.training_catalogue.count_documents({"role_specific": {"$exists": True, "$ne": []}})
    
    return {
        "total_items": total,
        "mandatory_count": mandatory,
        "role_specific_count": role_specific,
        "seeded": total > 0
    }


# ==================== TRAINING RECORD HISTORY ====================

@router.get("/training-records/{record_id}/history")
async def get_training_record_history(
    record_id: str,
    user: dict = Depends(get_current_user)
):
    """Get the change history of a training record."""
    db = get_db()
    
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    # Get audit logs for this record
    history = await db.audit_logs.find(
        {"resource_type": "training_record", "resource_id": record_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(50)
    
    # Get any superseded versions
    superseded = await db.training_records.find(
        {
            "employee_id": record.get("employee_id"),
            "requirement_id": record.get("requirement_id"),
            "record_status": "superseded"
        },
        {"_id": 0}
    ).sort("superseded_at", -1).to_list(10)
    
    return {
        "current": record,
        "audit_history": history,
        "superseded_versions": superseded
    }
