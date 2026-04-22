"""
CV and Document Extraction routes for AI-powered document processing.

Handles:
- Worker CV extraction status and verification
- Admin CV review, approval, and rejection
- Profile extraction from application forms
- Extraction result management (apply, discard, review)
- Employment history extraction

IMPORTANT: Extracted values update PROFILE DATA only. 
They do NOT complete compliance evidence requirements.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    get_current_worker,
    require_admin,
    require_manager_or_admin,
    log_audit_action
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["CV Extractions"])


def _looks_like_pdf_document(document: dict) -> bool:
    if not isinstance(document, dict):
        return False
    filename = (
        document.get("original_filename")
        or document.get("file_name")
        or document.get("file_url")
        or ""
    )
    content_type = (
        document.get("mime_type")
        or document.get("content_type")
        or document.get("file_type")
        or ""
    )
    filename = str(filename).lower()
    content_type = str(content_type).lower()
    return content_type == "application/pdf" or filename.endswith(".pdf") or ".pdf?" in filename


# ==================== PYDANTIC MODELS ====================

class CVRejectRequest(BaseModel):
    reason: str
    request_action: Optional[str] = "explain_or_reupload"  # "explain_gap", "reupload", "explain_or_reupload"


class ApplyExtractionRequest(BaseModel):
    fields_to_apply: List[str]


class CVExtractionResponse(BaseModel):
    extraction_id: str
    status: str
    employment_history: Optional[list] = None
    gaps_detected: Optional[list] = None
    education: Optional[list] = None
    skills: Optional[list] = None


# ==================== LAZY IMPORTS ====================

def get_current_worker():
    """Lazy import of get_current_worker from server.py"""
    from server import get_current_worker
    return get_current_worker


def get_cv_extraction_service():
    """Lazy import of _extract_cv_employment_history_helper from server.py"""
    from server import _extract_cv_employment_history_helper
    return _extract_cv_employment_history_helper


def get_validate_file_content():
    """Lazy import of validate_file_content from server.py"""
    from server import validate_file_content
    return validate_file_content


def get_put_object():
    """Lazy import of put_object from supabase_storage"""
    from supabase_storage import put_object
    return put_object


def get_app_name():
    """Get APP_NAME from server.py"""
    from server import APP_NAME
    return APP_NAME


def get_detect_cv_gaps():
    """Delegate to canonical coverage-aware detector via server wrapper."""
    from server import detect_cv_gaps
    return detect_cv_gaps


def get_storage_object():
    """Lazy import of get_object from server.py."""
    from server import get_object
    return get_object


def get_create_gap_record():
    """Lazy import of create_gap_record from employment_gap_engine."""
    from employment_gap_engine import create_gap_record
    return create_gap_record


async def persist_cv_gap_records(db, employee_id: str, gaps: list, created_by: str) -> int:
    """Persist CV-detected gaps into the canonical employment_gaps store."""
    create_gap_record = get_create_gap_record()
    new_gaps = 0

    for gap in gaps or []:
        existing_gap = await db.employment_gaps.find_one({
            "employee_id": employee_id,
            "gap_start": gap.get("gap_start"),
            "gap_end": gap.get("gap_end"),
        })
        if existing_gap:
            continue

        gap_record = create_gap_record(employee_id, gap, created_by=created_by)
        gap_record["source"] = "cv_review"
        await db.employment_gaps.update_one(
            {"id": gap_record["id"]},
            {"$setOnInsert": gap_record},
            upsert=True
        )
        new_gaps += 1

    return new_gaps


async def read_cv_file_bytes(file_url: str) -> bytes:
    """Read CV bytes from either a storage path or an absolute URL."""
    if file_url.startswith(("http://", "https://")):
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(file_url)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to download CV file")
            return response.content

    get_object = get_storage_object()
    file_content, _ = get_object(file_url)
    return file_content


def build_cv_review_extraction_response(extraction_result: dict, employment_history: list, gaps_detected: list) -> dict:
    """Return the response shape expected by the Employment Review dialog."""
    education = extraction_result.get("education", []) or []
    skills = extraction_result.get("skills", []) or []

    return {
        **extraction_result,
        "employment_history": employment_history,
        "jobs_found": extraction_result.get("jobs_found") or extraction_result.get("total_jobs_found") or len(employment_history),
        "education_found": extraction_result.get("education_found") or len(education),
        "skills_found": extraction_result.get("skills_found") or len(skills),
        "gaps_detected": len(gaps_detected),
        "gaps": [
            {
                **gap,
                "start_date": gap.get("gap_start"),
                "end_date": gap.get("gap_end"),
                "message": f"Employment gap requires explanation ({gap.get('duration_months')} months)",
            }
            for gap in gaps_detected
        ],
    }




# ==================== ADMIN LINK CV ENDPOINT ====================

@router.post("/admin/employees/{employee_id}/cv/link")
async def link_cv_document(
    employee_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Link an existing CV document as the active review CV.
    Sets cv_document_id on the employee so the Review CV button becomes available.
    """
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Find the best active PDF CV-like document for this employee.
    # Legacy DOC/DOCX uploads may exist as supporting evidence, but they must
    # never become the canonical review CV.
    cv_requirement_ids = ["cv", "resume", "curriculum_vitae"]
    cv_docs = await db.employee_documents.find(
        {
            "employee_id": employee_id,
            "requirement_id": {"$in": cv_requirement_ids},
            "status": {"$nin": ["superseded", "archived", "deleted"]},
            "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
        },
        {"_id": 0},
    ).sort("uploaded_at", -1).to_list(20)

    cv_doc = next((doc for doc in cv_docs if _looks_like_pdf_document(doc)), None)

    if not cv_doc:
        raise HTTPException(
            status_code=404,
            detail="No active PDF CV document found for this employee",
        )

    now = datetime.now(timezone.utc).isoformat()
    doc_id = cv_doc["id"]

    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"cv_document_id": doc_id, "cv_status": "uploaded", "updated_at": now}},
    )

    await log_audit_action(
        user.get("user_id"),
        "cv_document_linked",
        "employee",
        employee_id,
        {"document_id": doc_id, "action": "manual_link"},
    )

    logger.info("CV linked for employee=%s doc_id=%s by=%s", employee_id, doc_id, user.get("user_id"))

    return {
        "success": True,
        "cv_document_id": doc_id,
        "message": "CV linked as review document",
    }


# ==================== WORKER CV ENDPOINTS ====================

@router.get("/worker/cv-extraction-status")
async def get_worker_cv_extraction_status(user: dict = Depends(get_current_worker)):
    """
    Get status of CV extraction including employment history and detected gaps.
    Shows worker what was extracted and what gaps need explanation.
    """
    db = get_db()
    
    # Get worker's employee_id from user
    employee_id = user.get("employee_id")
    if not employee_id:
        # Fallback: check if user is linked to an employee
        employee = await db.employees.find_one({"email": user.get("email")}, {"_id": 0, "id": 1})
        if employee:
            employee_id = employee["id"]
        else:
            return {
                "has_cv": False,
                "extraction_status": "no_cv_uploaded",
                "needs_verification": False,
            }
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return {
            "has_cv": False,
            "extraction_status": "no_cv_uploaded",
            "needs_verification": False,
        }
    
    cv_document_id = employee.get("cv_document_id")
    cv_status = (employee.get("cv_status") or "").lower()
    replacement_required = cv_status in {
        "rejected",
        "replacement_requested",
        "missing",
        "replacement_required",
    }
    cv_extracted_history = employee.get("cv_extracted_employment_history", [])
    cv_gaps = employee.get("cv_gaps_detected", [])
    cv_education = employee.get("cv_extracted_education", [])
    cv_skills = employee.get("cv_extracted_skills", [])
    cv_extracted_at = employee.get("cv_extracted_at")
    cv_verified = employee.get("cv_extraction_verified", False)
    cv_overlaps = employee.get("cv_overlaps_detected", [])
    
    if not cv_document_id:
        return {
            "has_cv": False,
            "extraction_status": "no_cv_uploaded",
            "needs_verification": False,
            "replacement_required": False,
            "can_upload_cv": True,
            "cv_status": "missing",
        }

    # Get CV document info
    cv_doc = await db.employee_documents.find_one({"id": cv_document_id}, {"_id": 0})
    cv_doc_is_pdf = _looks_like_pdf_document(cv_doc)
    active_cv_exists = bool(
        cv_doc
        and cv_doc.get("file_url")
        and cv_doc.get("status") not in ["superseded", "archived", "deleted", "rejected", "invalidated"]
        and cv_doc.get("review_status") not in ["rejected", "amendment_requested", "invalidated"]
        and cv_doc.get("is_active") is not False
        and cv_doc_is_pdf
    )
    if not active_cv_exists:
        return {
            "has_cv": False,
            "extraction_status": "no_active_cv",
            "needs_verification": False,
            "replacement_required": True,
            "can_upload_cv": True,
            "cv_status": "missing",
        }
    
    # Count gaps needing explanation
    unexplained_gaps = [g for g in cv_gaps if not g.get("explanation") and g.get("needs_explanation", True)]
    
    return {
        "has_cv": not replacement_required,
        "extraction_status": "approved" if cv_status == "approved" else ("replacement_required" if replacement_required else "awaiting_admin_review"),
        "needs_verification": False,
        "replacement_required": replacement_required,
        "can_upload_cv": replacement_required,
        "cv_status": cv_status or "uploaded",
        # verified means admin-approved only — cv_status = "approved" is set exclusively by the admin approve endpoint
        "verified": cv_status == "approved",
        "verified_at": employee.get("cv_extraction_verified_at"),
        "cv_document": {
            "id": cv_document_id,
            "file_name": cv_doc.get("file_name") if cv_doc else None,
            "file_url": cv_doc.get("file_url") if cv_doc else None,
            "uploaded_at": cv_doc.get("uploaded_at") if cv_doc else None
        },
        "extracted_at": cv_extracted_at,
        "employment_history": {
            "jobs_found": len(cv_extracted_history),
            "entries": cv_extracted_history
        },
        "education": cv_education,
        "skills": cv_skills,
        "gaps": {
            "total": len(cv_gaps),
            "unexplained": len(unexplained_gaps),
            "all_explained": len(unexplained_gaps) == 0,
            "entries": cv_gaps
        },
        "overlaps": {
            "total": len(cv_overlaps),
            "entries": cv_overlaps
        },
    }


@router.get("/worker/cv-extraction-preview")
async def get_worker_cv_extraction_preview(user: dict = Depends(get_current_user)):
    """
    Get preview of CV extraction for worker to review before confirming.
    """
    raise HTTPException(status_code=403, detail="CV extraction review is completed by admin")

    db = get_db()
    
    employee_id = user.get("employee_id")
    if not employee_id:
        employee = await db.employees.find_one({"email": user.get("email")}, {"_id": 0, "id": 1})
        if employee:
            employee_id = employee["id"]
        else:
            raise HTTPException(status_code=404, detail="Employee not found")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    cv_document_id = employee.get("cv_document_id")
    if not cv_document_id:
        raise HTTPException(status_code=404, detail="No CV uploaded")
    
    cv_doc = await db.employee_documents.find_one({"id": cv_document_id}, {"_id": 0})
    if not cv_doc:
        raise HTTPException(status_code=404, detail="CV document not found")
    
    cv_extraction = cv_doc.get("cv_extraction")
    if not cv_extraction:
        raise HTTPException(status_code=404, detail="No extraction data available")
    
    return {
        "extraction": cv_extraction,
        "cv_document": {
            "id": cv_document_id,
            "file_name": cv_doc.get("file_name"),
            "file_url": cv_doc.get("file_url")
        },
        "verified": employee.get("cv_extraction_verified", False)
    }


@router.post("/worker/cv-extraction-verify")
async def worker_verify_cv_extraction(
    corrections: Optional[dict] = None,
    user: dict = Depends(get_current_user)
):
    """
    Worker confirms that CV extraction is accurate (or provides corrections).
    """
    raise HTTPException(status_code=403, detail="CV extraction verification is completed by admin")

    db = get_db()
    detect_cv_gaps = get_detect_cv_gaps()
    
    employee_id = user.get("employee_id")
    if not employee_id:
        employee = await db.employees.find_one({"email": user.get("email")}, {"_id": 0, "id": 1})
        if employee:
            employee_id = employee["id"]
        else:
            raise HTTPException(status_code=404, detail="Employee not found")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    cv_document_id = employee.get("cv_document_id")
    if not cv_document_id:
        raise HTTPException(status_code=400, detail="No CV uploaded to verify")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # If corrections provided, apply them
    update_data = {
        "cv_extraction_verified": True,
        "cv_extraction_verified_at": now,
        "cv_extraction_verified_by": "worker_self",
        "updated_at": now
    }
    
    employment_history = employee.get("cv_extracted_employment_history", [])
    
    if corrections:
        if "employment_history" in corrections:
            update_data["cv_extracted_employment_history"] = corrections["employment_history"]
            employment_history = corrections["employment_history"]
        if "education" in corrections:
            update_data["cv_extracted_education"] = corrections["education"]
        if "skills" in corrections:
            update_data["cv_extracted_skills"] = corrections["skills"]
    
    # Recalculate gaps after corrections
    if employment_history:
        gaps = detect_cv_gaps(employment_history)
        update_data["cv_gaps_detected"] = gaps
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    # Log audit
    await log_audit_action(
        employee_id,
        "cv_extraction_verified_by_worker",
        "employee",
        employee_id,
        {"corrections_made": corrections is not None}
    )
    
    return {
        "success": True,
        "message": "CV extraction verified",
        "gaps_detected": len(update_data.get("cv_gaps_detected", []))
    }


# ==================== ADMIN CV REVIEW ENDPOINTS ====================

@router.post("/admin/employees/{employee_id}/cv/review")
async def admin_review_cv(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """
    Admin triggers AI extraction on a worker's uploaded CV.
    """
    db = get_db()
    extract_cv_employment_history = get_cv_extraction_service()
    detect_cv_gaps = get_detect_cv_gaps()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    cv_document_id = employee.get("cv_document_id")
    if not cv_document_id:
        raise HTTPException(status_code=400, detail="No CV uploaded for this employee")
    
    cv_doc = await db.employee_documents.find_one({"id": cv_document_id}, {"_id": 0})
    if not cv_doc:
        raise HTTPException(status_code=404, detail="CV document not found")
    
    # Check if already extracted
    if cv_doc.get("cv_extraction"):
        extraction_result = cv_doc.get("cv_extraction") or {}
        employment_history = extraction_result.get("employment_history", [])
        gaps_detected = detect_cv_gaps(employment_history) if employment_history else []
        new_gap_count = await persist_cv_gap_records(
            db,
            employee_id,
            gaps_detected,
            created_by=user.get("user_id") or "admin"
        )

        now = datetime.now(timezone.utc).isoformat()
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "cv_extracted_employment_history": employment_history,
                "cv_extracted_education": extraction_result.get("education", []),
                "cv_extracted_skills": extraction_result.get("skills", []),
                "cv_gaps_detected": gaps_detected,
                "cv_status": "under_review",
                "cv_extraction_status": "reviewed",
                "cv_reviewed_at": now,
                "cv_reviewed_by": user.get("user_id"),
                "updated_at": now
            }}
        )

        return {
            "success": True,
            "message": "CV already extracted",
            "extraction": build_cv_review_extraction_response(extraction_result, employment_history, gaps_detected),
            "gaps_detected": len(gaps_detected),
            "new_gap_records": new_gap_count,
            "requires_action": len(gaps_detected) > 0,
            "already_extracted": True
        }
    
    # Get file content
    file_url = cv_doc.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="CV has no file URL")
    
    try:
        # Download file from the same storage shape used by evidence uploads.
        file_content = await read_cv_file_bytes(file_url)
        
        filename = cv_doc.get("file_name", "cv.pdf")
        
        # Trigger extraction
        extraction_result = await extract_cv_employment_history(
            file_content=file_content,
            filename=filename,
            employee_id=employee_id
        )
        
        # Save extraction to document
        now = datetime.now(timezone.utc).isoformat()
        await db.employee_documents.update_one(
            {"id": cv_document_id},
            {"$set": {
                "cv_extraction": extraction_result,
                "cv_extracted_at": now
            }}
        )
        
        # Update employee with extracted data
        employment_history = extraction_result.get("employment_history", [])
        gaps_detected = detect_cv_gaps(employment_history) if employment_history else []
        new_gap_count = await persist_cv_gap_records(
            db,
            employee_id,
            gaps_detected,
            created_by=user.get("user_id") or "admin"
        )
        
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "cv_extracted_employment_history": employment_history,
                "cv_extracted_education": extraction_result.get("education", []),
                "cv_extracted_skills": extraction_result.get("skills", []),
                "cv_gaps_detected": gaps_detected,
                "cv_status": "under_review",
                "cv_extraction_status": "reviewed",
                "cv_reviewed_at": now,
                "cv_reviewed_by": user.get("user_id"),
                "cv_extracted_at": now,
                "updated_at": now
            }}
        )
        
        return {
            "success": True,
            "message": "CV extraction complete",
            "extraction": build_cv_review_extraction_response(extraction_result, employment_history, gaps_detected),
            "gaps_detected": len(gaps_detected),
            "new_gap_records": new_gap_count,
            "requires_action": len(gaps_detected) > 0,
            "already_extracted": False
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CV extraction failed for {employee_id}: {e}")
        raise HTTPException(status_code=500, detail="CV extraction failed")


@router.post("/admin/employees/{employee_id}/cv/reject")
async def admin_reject_cv(
    employee_id: str,
    request: CVRejectRequest,
    user: dict = Depends(require_admin)
):
    """
    Admin rejects the CV with a reason, requesting worker to either explain gaps or upload a new CV.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee status
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "cv_status": "rejected",
            "cv_rejection_reason": request.reason,
            "cv_rejection_action": request.request_action,
            "cv_rejected_at": now,
            "cv_rejected_by": user.get("user_id"),
            "updated_at": now
        }}
    )
    
    # Create notification for worker
    notification_id = str(uuid.uuid4())
    await db.notifications.insert_one({
        "id": notification_id,
        "recipient_id": employee_id,
        "recipient_type": "employee",
        "type": "cv_rejected",
        "title": "CV Requires Attention",
        "message": f"Your CV has been reviewed: {request.reason}",
        "data": {
            "reason": request.reason,
            "action_required": request.request_action
        },
        "read": False,
        "created_at": now
    })
    
    # Log audit
    await log_audit_action(
        user.get("user_id"),
        "cv_rejected",
        "employee",
        employee_id,
        {"reason": request.reason, "action": request.request_action}
    )
    
    return {
        "success": True,
        "message": "CV rejected and worker notified",
        "notification_created": True
    }


@router.post("/admin/employees/{employee_id}/cv/approve")
async def admin_approve_cv(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """
    Admin approves the CV after reviewing extracted data.
    This marks the CV extraction as verified.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee record
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "cv_extraction_verified": True,
            "cv_extraction_verified_at": now,
            "cv_extraction_verified_by": user.get("user_id"),
            "cv_status": "approved",
            "updated_at": now
        }}
    )
    
    # Update document status
    from server import EXCLUDED_DOC_STATUSES
    cv_doc = await db.employee_documents.find_one(
        {"id": employee.get("cv_document_id"), "employee_id": employee_id},
        {"_id": 0}
    )
    
    if cv_doc:
        await db.employee_documents.update_one(
            {"id": cv_doc.get("id")},
            {"$set": {
                "status": "verified",
                "verified_at": now,
                "verified_by": user.get("user_id")
            }}
        )
    
    # Log audit
    await log_audit_action(
        user.get("user_id"),
        "cv_approved",
        "employee",
        employee_id,
        {"cv_document_id": cv_doc.get("id") if cv_doc else None}
    )
    
    return {
        "success": True,
        "message": "CV approved and employment history verified",
        "form_pre_populated": not existing_form and len(employment_history) > 0
    }


# ==================== PROFILE EXTRACTION ENDPOINTS ====================

@router.get("/employees/{employee_id}/extractions")
async def get_employee_extractions(
    employee_id: str,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all extraction results for an employee"""
    db = get_db()
    
    query = {"employee_id": employee_id}
    if status:
        query["status"] = status
    
    extractions = await db.profile_extractions.find(
        query,
        {"_id": 0}
    ).sort("extracted_at", -1).to_list(50)
    
    return {"extractions": extractions}


@router.get("/extractions/pending-review")
async def get_pending_extraction_reviews(
    limit: int = 50,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Get list of profile extractions awaiting admin review.
    (For document extractions, use /api/document-extractions/pending-review)
    """
    db = get_db()
    
    extractions = await db.profile_extractions.find(
        {"status": "pending_review"},
        {"_id": 0}
    ).sort("extracted_at", -1).limit(limit).to_list(limit)
    
    # Enrich with employee info
    for ext in extractions:
        emp = await db.employees.find_one(
            {"id": ext.get("employee_id")},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if emp:
            ext["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
    
    return {
        "extractions": extractions,
        "total": len(extractions)
    }


@router.get("/extractions/{extraction_id}")
async def get_extraction(extraction_id: str, user: dict = Depends(get_current_user)):
    """Get a specific extraction result"""
    db = get_db()
    
    extraction = await db.profile_extractions.find_one(
        {"id": extraction_id},
        {"_id": 0}
    )
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    return extraction


@router.post("/extractions/{extraction_id}/apply")
async def apply_extraction(
    extraction_id: str,
    request: ApplyExtractionRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Apply selected extracted fields to employee profile.
    
    SUPPORTS PARTIAL UPDATES: Only the selected fields are updated.
    
    IMPORTANT: This updates PROFILE DATA only. It does NOT:
    - Mark any compliance requirements as complete
    - Provide evidence for document requirements
    - Affect compliance percentage calculations
    """
    db = get_db()
    
    extraction = await db.profile_extractions.find_one(
        {"id": extraction_id},
        {"_id": 0}
    )
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    if extraction['status'] != 'pending_review':
        raise HTTPException(
            status_code=400, 
            detail=f"Extraction already processed (status: {extraction['status']})"
        )
    
    employee_id = extraction['employee_id']
    fields_to_apply = request.fields_to_apply
    
    if not fields_to_apply:
        raise HTTPException(status_code=400, detail="No fields selected to apply")
    
    # Build update dict from selected fields
    extracted_fields = extraction.get('extracted_fields', {})
    now = datetime.now(timezone.utc).isoformat()
    
    update_dict = {}
    applied_fields = []
    failed_fields = []
    
    for field_name in fields_to_apply:
        if field_name in extracted_fields:
            field_data = extracted_fields[field_name]
            value = field_data.get('value') if isinstance(field_data, dict) else field_data
            
            if value is not None and value != "":
                update_dict[field_name] = value
                applied_fields.append(field_name)
            else:
                failed_fields.append({"field": field_name, "reason": "Empty value"})
        else:
            failed_fields.append({"field": field_name, "reason": "Not in extraction"})
    
    # Apply updates
    if update_dict:
        update_dict["updated_at"] = now
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": update_dict}
        )
    
    # Update extraction status
    await db.profile_extractions.update_one(
        {"id": extraction_id},
        {"$set": {
            "status": "applied",
            "applied_at": now,
            "applied_by": user.get("user_id"),
            "applied_fields": applied_fields,
            "failed_fields": failed_fields
        }}
    )
    
    # Log audit
    await log_audit_action(
        user.get("user_id"),
        "extraction_applied",
        "employee",
        employee_id,
        {
            "extraction_id": extraction_id,
            "fields_applied": applied_fields,
            "fields_failed": [f["field"] for f in failed_fields]
        }
    )
    
    return {
        "success": True,
        "message": f"Applied {len(applied_fields)} fields to profile",
        "applied_fields": applied_fields,
        "failed_fields": failed_fields
    }


@router.post("/extractions/{extraction_id}/discard")
async def discard_extraction(
    extraction_id: str,
    reason: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """Discard an extraction without applying any fields"""
    db = get_db()
    
    extraction = await db.profile_extractions.find_one(
        {"id": extraction_id},
        {"_id": 0}
    )
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.profile_extractions.update_one(
        {"id": extraction_id},
        {"$set": {
            "status": "discarded",
            "discarded_at": now,
            "discarded_by": user.get("user_id"),
            "discard_reason": reason
        }}
    )
    
    # Log audit
    await log_audit_action(
        user.get("user_id"),
        "extraction_discarded",
        "profile_extraction",
        extraction_id,
        {"reason": reason, "employee_id": extraction.get("employee_id")}
    )
    
    return {
        "success": True,
        "message": "Extraction discarded"
    }
