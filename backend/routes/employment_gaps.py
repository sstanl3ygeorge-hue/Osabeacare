"""
Employment Gaps Routes Module

This module handles employment gap verification endpoints including:
- Getting employment gaps for an employee
- Explaining gaps with reason types
- Uploading evidence documents for gaps
- Verifying gap explanations (admin)
- Requesting additional information
- Auto-detecting gaps from employment history

CQC Requirement: All employment gaps must be explained and verified.

Extracted from server.py for modularity.
"""

import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

# Import from employment_gap_engine
from employment_gap_engine import evaluate_gaps_compliance

# Import detect_cv_gaps from server (it's defined there)
# Note: This creates a dependency on server.py but avoids code duplication
def _get_detect_cv_gaps():
    """Lazy import to avoid circular imports"""
    from server import detect_cv_gaps
    return detect_cv_gaps

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Employment Gaps"])


# ==================== MODELS ====================

class GapExplanationInput(BaseModel):
    """Input model for explaining an employment gap"""
    explanation: str
    reason_type: Optional[str] = None
    evidence_document_id: Optional[str] = None


class GapVerificationInput(BaseModel):
    """Input model for verifying a gap explanation"""
    verified: bool
    verification_notes: Optional[str] = None
    requires_further_info: bool = False


# ==================== ENDPOINTS ====================

@router.get("/employees/{employee_id}/employment-gaps")
async def get_employment_gaps(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get employment gap detection and verification status.
    
    Returns:
    - has_gaps: whether gaps exist
    - gaps: list of detected gaps with verification status
    - evaluation: compliance evaluation (is_complete, blockers)
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get gap records
    gap_records = await db.employment_gaps.find(
        {"employee_id": employee_id}
    ).sort("gap_start", 1).to_list(50)
    
    # Remove _id from records
    for gap in gap_records:
        gap.pop("_id", None)
    
    # If no gap records but employee has employment_gaps field, use that
    if not gap_records and employee.get("employment_gaps"):
        gap_records = employee.get("employment_gaps", [])
    
    # Evaluate compliance
    evaluation = evaluate_gaps_compliance(gap_records)
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "has_gaps": evaluation.get("has_gaps", False),
        "total_gaps": evaluation.get("total_gaps", 0),
        "gaps": gap_records,
        "evaluation": evaluation
    }


@router.post("/employees/{employee_id}/employment-gaps/{gap_id}/explain")
async def explain_employment_gap(
    employee_id: str,
    gap_id: str,
    explanation: str,
    reason_type: Optional[str] = None,
    evidence_document_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Provide explanation for an employment gap.
    
    CQC requires explanations for significant gaps.
    Valid reason types: 
    - education, caring_responsibilities, illness, travel, 
    - career_break, redundancy, unemployment, other
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find the gap record
    gap = await db.employment_gaps.find_one({
        "employee_id": employee_id,
        "id": gap_id
    })
    
    if not gap:
        # Check if gap is in employee.employment_gaps array
        emp_gaps = employee.get("employment_gaps", [])
        gap_dict = next((g for g in emp_gaps if g.get("id") == gap_id), None)
        
        if not gap_dict:
            raise HTTPException(status_code=404, detail="Gap not found")
        
        # Migrate gap to collection
        gap_dict["employee_id"] = employee_id
        gap_dict["id"] = gap_id
        await db.employment_gaps.insert_one(gap_dict)
        gap = gap_dict
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update gap with explanation
    update_data = {
        "explanation": explanation.strip(),
        "reason_type": reason_type,
        "evidence_document_id": evidence_document_id,
        "explained_at": now,
        "explained_by": user.get("user_id") or user.get("id"),
        "status": "explained",
        "verification_status": "pending"
    }
    
    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap_id},
        {"$set": update_data}
    )
    
    await log_audit_action(
        user.get("user_id") or user.get("id"),
        "employment_gap_explained",
        "employment_gap",
        gap_id,
        {
            "employee_id": employee_id,
            "reason_type": reason_type,
            "has_evidence": bool(evidence_document_id)
        }
    )
    
    updated_gap = await db.employment_gaps.find_one(
        {"employee_id": employee_id, "id": gap_id},
        {"_id": 0}
    )
    
    return {
        "success": True,
        "message": "Gap explanation submitted",
        "gap": updated_gap
    }


@router.post("/employees/{employee_id}/employment-gaps/{gap_id}/upload-document")
async def upload_gap_document(
    employee_id: str,
    gap_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Upload supporting document for gap explanation.
    
    Accepts: PDF, images (jpg, png), Word documents
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "application/msword", 
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPEG, PNG, DOC, DOCX")
    
    # Read file content
    content = await file.read()
    
    # Create uploads directory
    upload_dir = Path("/app/uploads/gap_documents") / employee_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate safe filename
    safe_filename = f"{gap_id}_{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = upload_dir / safe_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    file_url = f"/uploads/gap_documents/{employee_id}/{safe_filename}"
    
    # Store document reference
    now = datetime.now(timezone.utc).isoformat()
    doc_record = {
        "id": f"gap_doc_{uuid.uuid4().hex[:12]}",
        "employee_id": employee_id,
        "gap_id": gap_id,
        "file_name": file.filename,
        "file_url": file_url,
        "file_type": file.content_type,
        "file_size": len(content),
        "uploaded_at": now,
        "uploaded_by": user.get("user_id") or user.get("id")
    }
    
    await db.gap_documents.insert_one(doc_record)
    
    # Update gap with document reference
    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap_id},
        {"$set": {"evidence_document_id": doc_record["id"], "updated_at": now}}
    )
    
    doc_record.pop("_id", None)
    return {
        "success": True,
        "document": doc_record
    }


@router.post("/employees/{employee_id}/employment-gaps/{gap_id}/verify")
async def verify_employment_gap(
    employee_id: str,
    gap_id: str,
    verified: bool,
    verification_notes: Optional[str] = None,
    requires_further_info: bool = False,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Admin verification of gap explanation.
    
    Sets gap as:
    - verified: explanation accepted
    - rejected: explanation not sufficient
    - requires_info: more information needed
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    gap = await db.employment_gaps.find_one({
        "employee_id": employee_id,
        "id": gap_id
    })
    
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if requires_further_info:
        status = "requires_info"
    elif verified:
        status = "verified"
    else:
        status = "rejected"
    
    update_data = {
        "verification_status": status,
        "verified": verified if not requires_further_info else None,
        "verified_at": now if verified else None,
        "verified_by": user.get("user_id") if verified else None,
        "verified_by_name": user.get("name", user.get("email", "Admin")) if verified else None,
        "verification_notes": verification_notes,
        "requires_further_info": requires_further_info,
        "updated_at": now
    }
    
    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap_id},
        {"$set": update_data}
    )
    
    await log_audit_action(
        user.get("user_id"),
        f"employment_gap_{status}",
        "employment_gap",
        gap_id,
        {
            "employee_id": employee_id,
            "status": status,
            "notes": verification_notes
        }
    )
    
    return {
        "success": True,
        "message": f"Gap marked as {status}",
        "gap_id": gap_id,
        "status": status
    }


@router.post("/employees/{employee_id}/employment-gaps/{gap_id}/request-info")
async def request_gap_info(
    employee_id: str,
    gap_id: str,
    request_message: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Request additional information about a gap from the employee.
    Creates a notification for the employee.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    gap = await db.employment_gaps.find_one({
        "employee_id": employee_id,
        "id": gap_id
    })
    
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update gap status
    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap_id},
        {"$set": {
            "verification_status": "requires_info",
            "info_request_message": request_message,
            "info_requested_at": now,
            "info_requested_by": user.get("user_id"),
            "updated_at": now
        }}
    )
    
    # Create notification for employee
    notification_id = str(uuid.uuid4())
    await db.worker_notifications.insert_one({
        "id": notification_id,
        "employee_id": employee_id,
        "type": "gap_info_requested",
        "title": "Additional Information Required",
        "message": f"More information is needed about an employment gap in your history: {request_message}",
        "priority": "high",
        "action_url": f"/worker/employment-gaps/{gap_id}",
        "created_at": now,
        "read": False
    })
    
    await log_audit_action(
        user.get("user_id"),
        "employment_gap_info_requested",
        "employment_gap",
        gap_id,
        {
            "employee_id": employee_id,
            "request_message": request_message
        }
    )
    
    return {
        "success": True,
        "message": "Information request sent",
        "notification_id": notification_id
    }


@router.post("/employees/{employee_id}/detect-employment-gaps")
async def detect_employment_gaps(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Re-run gap detection on employee's employment history.
    Creates gap records for any new gaps found.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employment_history = employee.get("employment_history", [])
    
    if not employment_history:
        return {
            "success": True,
            "message": "No employment history to analyze",
            "gaps_found": 0
        }
    
    # Detect gaps using lazy import
    detect_cv_gaps = _get_detect_cv_gaps()
    detected_gaps = detect_cv_gaps(employment_history)
    
    now = datetime.now(timezone.utc).isoformat()
    new_gaps = 0
    
    for gap in detected_gaps:
        # Check if gap already exists
        existing = await db.employment_gaps.find_one({
            "employee_id": employee_id,
            "gap_start": gap.get("gap_start"),
            "gap_end": gap.get("gap_end")
        })
        
        if not existing:
            gap_record = {
                "id": f"gap_{uuid.uuid4().hex[:12]}",
                "employee_id": employee_id,
                **gap,
                "status": "detected",
                "verification_status": "pending",
                "detected_at": now
            }
            await db.employment_gaps.insert_one(gap_record)
            new_gaps += 1
    
    return {
        "success": True,
        "total_gaps_detected": len(detected_gaps),
        "new_gaps_created": new_gaps,
        "gaps": detected_gaps
    }
