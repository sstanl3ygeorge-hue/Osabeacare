"""
Service User Feedback & Complaints Handling Routes

CQC Compliance modules for:
- Service User Feedback (CQC "Caring" evidence)
- Complaints Handling (CQC regulatory requirement)

Extracted from server.py - Phase 37
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    log_audit_action
)

router = APIRouter(tags=["Feedback & Complaints"])


# ==================== SERVICE USER FEEDBACK ====================

@router.get("/service-user-feedback")
async def get_service_user_feedback(
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get all service user feedback records"""
    db = get_db()
    
    feedback_records = await db.service_user_feedback.find(
        {},
        {"_id": 0}
    ).sort("date_received", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with employee names
    for record in feedback_records:
        if record.get("employee_id"):
            emp = await db.employees.find_one(
                {"id": record["employee_id"]},
                {"_id": 0, "first_name": 1, "last_name": 1}
            )
            if emp:
                record["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
    
    total = await db.service_user_feedback.count_documents({})
    
    return {
        "feedback": feedback_records,
        "total": total
    }


@router.get("/service-user-feedback/stats")
async def get_service_user_feedback_stats(user: dict = Depends(get_current_user)):
    """Get statistics for service user feedback"""
    db = get_db()
    
    total = await db.service_user_feedback.count_documents({})
    compliments = await db.service_user_feedback.count_documents({"feedback_type": "compliment"})
    suggestions = await db.service_user_feedback.count_documents({"feedback_type": "suggestion"})
    concerns = await db.service_user_feedback.count_documents({"feedback_type": "concern"})
    complaints_count = await db.service_user_feedback.count_documents({"feedback_type": "complaint"})
    
    # Calculate average rating
    pipeline = [
        {"$match": {"rating": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}}
    ]
    avg_result = await db.service_user_feedback.aggregate(pipeline).to_list(1)
    avg_rating = avg_result[0]["avg_rating"] if avg_result else None
    
    return {
        "total": total,
        "compliments": compliments,
        "suggestions": suggestions,
        "concerns": concerns,
        "complaints": complaints_count,
        "average_rating": avg_rating
    }


@router.post("/service-user-feedback")
async def create_service_user_feedback(
    feedback: dict,
    user: dict = Depends(get_current_user)
):
    """Create a new service user feedback record"""
    db = get_db()
    
    feedback_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    feedback_record = {
        "id": feedback_id,
        "service_user_id": feedback.get("service_user_id"),
        "service_user_name": feedback.get("service_user_name"),
        "employee_id": feedback.get("employee_id"),
        "feedback_type": feedback.get("feedback_type", "compliment"),
        "rating": feedback.get("rating", 5),
        "title": feedback.get("title", ""),
        "description": feedback.get("description", ""),
        "date_received": feedback.get("date_received", now.isoformat()),
        "recorded_by": user.get("user_id"),
        "recorded_by_name": user.get("email"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.service_user_feedback.insert_one(feedback_record)
    
    await log_audit_action(
        user["user_id"],
        "create_feedback",
        "service_user_feedback",
        feedback_id,
        {"feedback_type": feedback_record["feedback_type"], "rating": feedback_record["rating"]}
    )
    
    return {"success": True, "id": feedback_id, "message": "Feedback recorded successfully"}


# ==================== COMPLAINTS HANDLING ====================

@router.get("/complaints")
async def get_complaints(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all complaints"""
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status
    
    complaints_records = await db.complaints.find(
        query,
        {"_id": 0}
    ).sort("date_received", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with employee names
    for record in complaints_records:
        if record.get("employee_id") and record["employee_id"] != "unknown":
            emp = await db.employees.find_one(
                {"id": record["employee_id"]},
                {"_id": 0, "first_name": 1, "last_name": 1}
            )
            if emp:
                record["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
    
    total = await db.complaints.count_documents(query)
    
    return {
        "complaints": complaints_records,
        "total": total
    }


@router.get("/complaints/stats")
async def get_complaints_stats(user: dict = Depends(get_current_user)):
    """Get statistics for complaints"""
    db = get_db()
    
    total = await db.complaints.count_documents({})
    open_count = await db.complaints.count_documents({"status": "received"})
    investigating = await db.complaints.count_documents({"status": "investigating"})
    awaiting = await db.complaints.count_documents({"status": "awaiting_response"})
    resolved = await db.complaints.count_documents({"status": "resolved"})
    closed = await db.complaints.count_documents({"status": "closed"})
    
    # Calculate average resolution time
    pipeline = [
        {"$match": {"status": {"$in": ["resolved", "closed"]}, "resolved_at": {"$exists": True}}},
        {"$project": {
            "resolution_days": {
                "$divide": [
                    {"$subtract": [
                        {"$dateFromString": {"dateString": "$resolved_at"}},
                        {"$dateFromString": {"dateString": "$date_received"}}
                    ]},
                    86400000
                ]
            }
        }},
        {"$group": {"_id": None, "avg_days": {"$avg": "$resolution_days"}}}
    ]
    try:
        avg_result = await db.complaints.aggregate(pipeline).to_list(1)
        avg_resolution_days = avg_result[0]["avg_days"] if avg_result else None
    except Exception:
        avg_resolution_days = None
    
    return {
        "total": total,
        "open": open_count,
        "investigating": investigating,
        "awaiting_response": awaiting,
        "resolved": resolved,
        "closed": closed,
        "avg_resolution_days": avg_resolution_days
    }


@router.get("/complaints/{complaint_id}")
async def get_complaint_by_id(
    complaint_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a single complaint by ID"""
    db = get_db()
    
    complaint = await db.complaints.find_one({"id": complaint_id}, {"_id": 0})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    if complaint.get("employee_id") and complaint["employee_id"] != "unknown":
        emp = await db.employees.find_one(
            {"id": complaint["employee_id"]},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if emp:
            complaint["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
    
    return complaint


@router.post("/complaints")
async def create_complaint(
    complaint: dict,
    user: dict = Depends(get_current_user)
):
    """Create a new complaint record"""
    db = get_db()
    
    complaint_id = str(uuid.uuid4())
    
    # Generate reference number
    count = await db.complaints.count_documents({})
    reference_number = f"CMP-{datetime.now().strftime('%Y%m')}-{str(count + 1).zfill(4)}"
    
    now = datetime.now(timezone.utc)
    
    complaint_record = {
        "id": complaint_id,
        "reference_number": reference_number,
        "complainant_name": complaint.get("complainant_name", ""),
        "complainant_relationship": complaint.get("complainant_relationship", ""),
        "complainant_contact": complaint.get("complainant_contact", ""),
        "employee_id": complaint.get("employee_id"),
        "category": complaint.get("category", ""),
        "severity": complaint.get("severity", "medium"),
        "status": "received",
        "title": complaint.get("title", ""),
        "description": complaint.get("description", ""),
        "date_received": complaint.get("date_received", now.isoformat()),
        "date_of_incident": complaint.get("date_of_incident"),
        "desired_outcome": complaint.get("desired_outcome", ""),
        "notes": [],
        "recorded_by": user.get("user_id"),
        "recorded_by_name": user.get("email"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.complaints.insert_one(complaint_record)
    
    await log_audit_action(
        user["user_id"],
        "create_complaint",
        "complaint",
        complaint_id,
        {"reference_number": reference_number, "category": complaint_record["category"], "severity": complaint_record["severity"]}
    )
    
    return {"success": True, "id": complaint_id, "reference_number": reference_number, "message": "Complaint logged successfully"}


@router.patch("/complaints/{complaint_id}/status")
async def update_complaint_status(
    complaint_id: str,
    data: dict,
    user: dict = Depends(get_current_user)
):
    """Update complaint status"""
    db = get_db()
    
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    valid_statuses = ["received", "investigating", "awaiting_response", "resolved", "closed"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    now = datetime.now(timezone.utc)
    
    update_data = {
        "status": new_status,
        "updated_at": now.isoformat()
    }
    
    if new_status in ["resolved", "closed"]:
        update_data["resolved_at"] = now.isoformat()
    
    result = await db.complaints.update_one(
        {"id": complaint_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Add status change note
    await db.complaints.update_one(
        {"id": complaint_id},
        {"$push": {
            "notes": {
                "text": f"Status changed to: {new_status}",
                "created_by": user.get("email"),
                "created_at": now.isoformat()
            }
        }}
    )
    
    await log_audit_action(
        user["user_id"],
        "update_complaint_status",
        "complaint",
        complaint_id,
        {"new_status": new_status}
    )
    
    return {"success": True, "message": f"Status updated to {new_status}"}


@router.post("/complaints/{complaint_id}/notes")
async def add_complaint_note(
    complaint_id: str,
    data: dict,
    user: dict = Depends(get_current_user)
):
    """Add a note to a complaint"""
    db = get_db()
    
    note_text = data.get("note")
    if not note_text:
        raise HTTPException(status_code=400, detail="Note text is required")
    
    now = datetime.now(timezone.utc)
    
    note = {
        "text": note_text,
        "created_by": user.get("email"),
        "created_at": now.isoformat()
    }
    
    result = await db.complaints.update_one(
        {"id": complaint_id},
        {
            "$push": {"notes": note},
            "$set": {"updated_at": now.isoformat()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    await log_audit_action(
        user["user_id"],
        "add_complaint_note",
        "complaint",
        complaint_id,
        {}
    )
    
    return {"success": True, "message": "Note added successfully"}
