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

def _get_put_object():
    """Lazy import of put_object from server.py"""
    from server import put_object
    return put_object

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Employment Gaps"])

CANONICAL_GAP_STATUSES = {
    "pending",
    "explained",
    "needs_more_info",
    "verified",
    "rejected",
    "reopened",
}


def _canonicalize_gap_status(
    status: Optional[str],
    verification_status: Optional[str] = None,
    verified: Optional[bool] = None,
) -> str:
    normalized_status = (status or "").strip().lower()
    normalized_verification_status = (verification_status or "").strip().lower()

    legacy_map = {
        "detected": "pending",
        "requires_info": "needs_more_info",
    }

    if normalized_status in legacy_map:
        normalized_status = legacy_map[normalized_status]
    if normalized_verification_status in legacy_map:
        normalized_verification_status = legacy_map[normalized_verification_status]

    if normalized_status in CANONICAL_GAP_STATUSES:
        return normalized_status

    if normalized_verification_status in CANONICAL_GAP_STATUSES:
        return normalized_verification_status

    if verified is True:
        return "verified"

    return "pending"


def _build_gap_compatibility_fields(status: str) -> dict:
    return {
        "verification_status": status,
        "verified": status == "verified",
        "requires_further_info": status == "needs_more_info",
    }


def _normalize_gap_record(gap: dict) -> dict:
    normalized_gap = dict(gap)
    record_id = normalized_gap.get("id") or normalized_gap.get("gap_id")
    if not record_id:
        record_id = f"gap_{uuid.uuid4().hex[:12]}"

    status = _canonicalize_gap_status(
        normalized_gap.get("status"),
        normalized_gap.get("verification_status"),
        normalized_gap.get("verified"),
    )

    normalized_gap["id"] = record_id
    normalized_gap["gap_id"] = record_id
    normalized_gap["status"] = status
    normalized_gap.update(_build_gap_compatibility_fields(status))

    return normalized_gap


async def _get_gap_record(db, employee_id: str, gap_id: str) -> Optional[dict]:
    gap = await db.employment_gaps.find_one(
        {
            "employee_id": employee_id,
            "$or": [{"id": gap_id}, {"gap_id": gap_id}],
        }
    )

    if gap:
        gap.pop("_id", None)
        return _normalize_gap_record(gap)

    return None


async def _ensure_gap_record(db, employee: dict, employee_id: str, gap_id: str) -> Optional[dict]:
    gap = await _get_gap_record(db, employee_id, gap_id)
    if gap:
        return gap

    emp_gaps = employee.get("employment_gaps", [])
    legacy_gap = next(
        (
            g for g in emp_gaps
            if g.get("id") == gap_id or g.get("gap_id") == gap_id
        ),
        None,
    )

    if not legacy_gap:
        return None

    normalized_gap = _normalize_gap_record({**legacy_gap, "employee_id": employee_id})
    await db.employment_gaps.insert_one(normalized_gap)
    return normalized_gap


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


class GapReopenRequest(BaseModel):
    """Input model for reopening a previously verified gap"""
    reason: str


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

    gap_records = [_normalize_gap_record(gap) for gap in gap_records]
    
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
    
    gap = await _ensure_gap_record(db, employee, employee_id, gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")
    
    now = datetime.now(timezone.utc).isoformat()
    canonical_status = "explained"
    
    # Update gap with explanation
    update_data = {
        "explanation": explanation.strip(),
        "reason_type": reason_type,
        "evidence_document_id": evidence_document_id,
        "explained_at": now,
        "explained_by": user.get("user_id") or user.get("id"),
        "explanation_submitted_by_role": user.get("role") or "unknown",
        "explanation_submitted_by_name": user.get("name") or user.get("email"),
        "explanation_source": "worker_or_applicant_submission",
        "status": canonical_status,
        "status_updated_at": now,
        "updated_at": now,
        **_build_gap_compatibility_fields(canonical_status),
    }
    
    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap["id"]},
        {"$set": update_data}
    )
    
    await log_audit_action(
        user.get("user_id") or user.get("id"),
        "employment_gap_explained",
        "employment_gap",
        gap["id"],
        {
            "employee_id": employee_id,
            "reason_type": reason_type,
            "has_evidence": bool(evidence_document_id)
        }
    )
    
    updated_gap = await db.employment_gaps.find_one(
        {"employee_id": employee_id, "id": gap["id"]},
        {"_id": 0}
    )
    
    return {
        "success": True,
        "message": "Gap explanation submitted",
        "gap": _normalize_gap_record(updated_gap)
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
    
    put_object = _get_put_object()
    
    # Generate safe filename and upload to object storage
    safe_filename = f"{gap_id}_{uuid.uuid4().hex[:8]}_{file.filename}"
    storage_path = f"gap_documents/{employee_id}/{safe_filename}"
    content_type = file.content_type or "application/octet-stream"
    put_object(storage_path, content, content_type)
    
    file_url = storage_path
    
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
    normalized_gap = await _get_gap_record(db, employee_id, gap_id)
    if not normalized_gap:
        raise HTTPException(status_code=404, detail="Gap not found")

    doc_record["gap_id"] = normalized_gap["id"]

    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": normalized_gap["id"]},
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
    verified: Optional[bool] = None,
    approved: Optional[bool] = None,
    verification_notes: Optional[str] = None,
    notes: Optional[str] = None,
    rejection_reason: Optional[str] = None,
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
    
    gap = await _get_gap_record(db, employee_id, gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")
    
    now = datetime.now(timezone.utc).isoformat()
    resolved_verified = verified if verified is not None else approved
    resolved_notes = verification_notes if verification_notes is not None else notes

    if resolved_verified is None and not requires_further_info:
        raise HTTPException(status_code=400, detail="Either verified or approved must be provided")
    
    if requires_further_info:
        status = "needs_more_info"
    elif resolved_verified:
        status = "verified"
    else:
        status = "rejected"

    rejection_text = rejection_reason.strip() if rejection_reason else None
    review_notes = resolved_notes.strip() if isinstance(resolved_notes, str) and resolved_notes.strip() else None
    
    update_data = {
        "status": status,
        "verified_at": now if resolved_verified else None,
        "verified_by": user.get("user_id") if resolved_verified else None,
        "verified_by_name": user.get("name", user.get("email", "Admin")) if resolved_verified else None,
        "verification_notes": review_notes,
        "rejection_reason": rejection_text if status == "rejected" else gap.get("rejection_reason"),
        "status_updated_at": now,
        "updated_at": now,
        **_build_gap_compatibility_fields(status),
    }

    if status != "verified":
        update_data["verified_at"] = None
        update_data["verified_by"] = None
        update_data["verified_by_name"] = None
    if status != "needs_more_info":
        update_data["requires_further_info"] = False
    
    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap["id"]},
        {"$set": update_data}
    )

    # Invalidate employment review sign-off when a gap is rejected or needs more info
    if status != "verified" and employee.get("employment_review_signed_off"):
        await db.employees.update_one({"id": employee_id}, {"$unset": {
            "employment_review_signed_off": "",
            "employment_review_signed_off_by": "",
            "employment_review_signed_off_by_name": "",
            "employment_review_signed_off_at": "",
            "employment_review_notes": "",
        }})
        await log_audit_action(
            user.get("user_id"),
            "employment_review_sign_off_invalidated",
            "employee",
            employee_id,
            {"reason": "gap_status_changed", "triggered_by": "verify_employment_gap", "new_gap_status": status}
        )

    await log_audit_action(
        user.get("user_id"),
        f"employment_gap_{status}",
        "employment_gap",
        gap["id"],
        {
            "employee_id": employee_id,
            "status": status,
            "notes": review_notes,
            "rejection_reason": rejection_text
        }
    )
    
    return {
        "success": True,
        "message": f"Gap marked as {status}",
        "gap_id": gap["id"],
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
    
    gap = await _get_gap_record(db, employee_id, gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")
    
    now = datetime.now(timezone.utc).isoformat()
    canonical_status = "needs_more_info"
    
    # Update gap status
    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap["id"]},
        {"$set": {
            "status": canonical_status,
            "info_request_message": request_message,
            "info_requested_at": now,
            "info_requested_by": user.get("user_id"),
            "status_updated_at": now,
            "updated_at": now,
            **_build_gap_compatibility_fields(canonical_status),
        }}
    )

    # Invalidate employment review sign-off — requesting info means review is incomplete
    if employee.get("employment_review_signed_off"):
        await db.employees.update_one({"id": employee_id}, {"$unset": {
            "employment_review_signed_off": "",
            "employment_review_signed_off_by": "",
            "employment_review_signed_off_by_name": "",
            "employment_review_signed_off_at": "",
            "employment_review_notes": "",
        }})
        await log_audit_action(
            user.get("user_id"),
            "employment_review_sign_off_invalidated",
            "employee",
            employee_id,
            {"reason": "gap_info_requested", "triggered_by": "request_gap_info", "gap_id": gap["id"]}
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
        "action_url": f"/worker/employment-gaps/{gap['id']}",
        "created_at": now,
        "read": False
    })
    
    await log_audit_action(
        user.get("user_id"),
        "employment_gap_info_requested",
        "employment_gap",
        gap["id"],
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


@router.post("/employees/{employee_id}/employment-gaps/{gap_id}/reopen")
async def reopen_employment_gap(
    employee_id: str,
    gap_id: str,
    request: GapReopenRequest,
    user: dict = Depends(require_admin)
):
    """Reopen a previously reviewed or verified employment gap with an audit reason."""
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reopen reason must be at least 5 characters")

    gap = await _get_gap_record(db, employee_id, gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")

    now = datetime.now(timezone.utc).isoformat()
    previous_status = gap.get("status", "pending")
    canonical_status = "reopened"

    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": gap["id"]},
        {"$set": {
            "status": canonical_status,
            "verified": False,
            "verified_at": None,
            "verified_by": None,
            "verified_by_name": None,
            "reopened_at": now,
            "reopened_by": user.get("user_id"),
            "reopened_by_name": user.get("name", user.get("email", "Admin")),
            "reopen_reason": request.reason.strip(),
            "reopened_from_status": previous_status,
            "status_updated_at": now,
            "updated_at": now,
            **_build_gap_compatibility_fields(canonical_status),
        }}
    )

    await log_audit_action(
        user.get("user_id"),
        "employment_gap_reopened",
        "employment_gap",
        gap["id"],
        {
            "employee_id": employee_id,
            "previous_status": previous_status,
            "reason": request.reason.strip(),
        }
    )

    # Invalidate employment review sign-off — reopening a gap means the review is incomplete
    if employee.get("employment_review_signed_off"):
        await db.employees.update_one({"id": employee_id}, {"$unset": {
            "employment_review_signed_off": "",
            "employment_review_signed_off_by": "",
            "employment_review_signed_off_by_name": "",
            "employment_review_signed_off_at": "",
            "employment_review_notes": "",
        }})
        await log_audit_action(
            user.get("user_id"),
            "employment_review_sign_off_invalidated",
            "employee",
            employee_id,
            {"reason": "gap_reopened", "triggered_by": "reopen_employment_gap", "gap_id": gap["id"], "previous_status": previous_status}
        )

    updated_gap = await db.employment_gaps.find_one(
        {"employee_id": employee_id, "id": gap["id"]},
        {"_id": 0}
    )

    return {
        "success": True,
        "message": "Gap reopened",
        "gap": _normalize_gap_record(updated_gap),
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
        normalized_detected_gap = _normalize_gap_record({
            **gap,
            "id": gap.get("id") or gap.get("gap_id") or f"gap_{uuid.uuid4().hex[:12]}",
        })

        # Check if gap already exists
        existing = await db.employment_gaps.find_one({
            "employee_id": employee_id,
            "gap_start": normalized_detected_gap.get("gap_start"),
            "gap_end": normalized_detected_gap.get("gap_end")
        })
        
        if not existing:
            gap_record = {
                "employee_id": employee_id,
                **normalized_detected_gap,
                "status": "pending",
                **_build_gap_compatibility_fields("pending"),
                "detected_at": now
            }
            await db.employment_gaps.insert_one(gap_record)
            new_gaps += 1
    
    return {
        "success": True,
        "total_gaps_detected": len(detected_gaps),
        "new_gaps_created": new_gaps,
        "gaps": [_normalize_gap_record(gap) for gap in detected_gaps]
    }
