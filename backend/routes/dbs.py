"""
DBS (Disclosure and Barring Service) routes for managing DBS certificates,
Update Service checks, and the DBS Register.

Handles:
- DBS Register (organization-wide view)
- DBS document extraction (using AI/Vision)
- DBS check recording and retrieval
- DBS document stamping

IMPORTANT: DBS certificates do NOT have a statutory expiry date.
The "review_due_at" is an INTERNAL POLICY date, not certificate expiry.
"""

import os
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from .dependencies import (
    get_db,
    get_current_user,
    require_manager_or_admin,
    log_audit_action
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["DBS"])


# ==================== PYDANTIC MODELS ====================

class DBSExtractionRequest(BaseModel):
    """Request model for DBS document extraction."""
    document_id: Optional[str] = Field(None, description="Document ID to extract from")
    file_base64: Optional[str] = Field(None, description="Base64 encoded file content for direct extraction")
    file_type: Optional[str] = Field("image/png", description="MIME type of the file")


class DBSCheckInput(BaseModel):
    """
    Input for recording a DBS verification check.
    
    DBS 3-Layer Model (mirroring RTW):
    - Layer 1: Evidence (DBS Certificate / Update Service Screenshot)
    - Layer 2: Verification (dbs_certificate_review / dbs_update_service_check)
    - Layer 3: DBS Result (certificate details, Update Service status, clearance)
    
    IMPORTANT: DBS certificates do NOT have a statutory expiry date.
    The review_due_at is your INTERNAL POLICY date.
    """
    # Check method and date
    method: str = Field(..., description="DBS check method (dbs_certificate_review, dbs_update_service_check)")
    checked_at: str = Field(..., description="Date check was performed (YYYY-MM-DD)")
    outcome: str = Field(default="verified", description="Check outcome (verified, failed, follow_up_required)")
    
    # Certificate details (DBS Result - Layer 3)
    dbs_level: Optional[str] = Field(None, description="DBS level (basic, standard, enhanced, enhanced_barred)")
    certificate_number: Optional[str] = Field(None, description="12-digit DBS certificate number")
    certificate_issue_date: Optional[str] = Field(None, description="Certificate issue date (YYYY-MM-DD)")
    name_on_certificate: Optional[str] = Field(None, description="Name as shown on certificate")
    workforce: Optional[str] = Field(None, description="Workforce type (adult, child, adult_and_child)")
    
    # Update Service specific (for dbs_update_service_check method)
    update_service_registered: bool = Field(default=False, description="Whether registered with DBS Update Service")
    update_service_status: Optional[str] = Field(None, description="Update Service status (active, not_registered, expired)")
    last_status_check_date: Optional[str] = Field(None, description="Date of last Update Service status check (YYYY-MM-DD)")
    update_service_check_result: Optional[str] = Field(None, description="Result of Update Service check (no_change, changed)")
    
    # Recheck tracking
    recheck_required: bool = Field(default=True, description="Whether periodic recheck is required (policy-based)")
    next_recheck_date: Optional[str] = Field(None, description="Next recheck due date (YYYY-MM-DD)")
    review_due_at: Optional[str] = Field(None, description="Review due date - alias for next_recheck_date (YYYY-MM-DD)")
    
    # Result details
    result_status: Optional[str] = Field(None, description="Result status (clear, information_present, pending_review)")
    information_present: bool = Field(default=False, description="Whether certificate shows any information/disclosures")
    result_summary: Optional[str] = Field(None, description="Brief result summary (e.g., 'Clear - no information')")
    
    # Linked evidence/proof
    evidence_document_id: Optional[str] = Field(None, description="ID of proof-of-check file (certificate/screenshot)")
    proof_document_id: Optional[str] = Field(None, description="ID of proof-of-check file - alias for evidence_document_id")
    linked_evidence_ids: List[str] = Field(default_factory=list, description="IDs of all linked evidence files")
    
    # Notes
    notes: Optional[str] = Field(None, description="Review notes (especially for information_present cases)")


class StampAllInput(BaseModel):
    """Input for stamping all documents (evidence + verification proof)"""
    evidence_file_ids: List[str]
    stamp_verification_proof: bool = True


# ==================== LAZY IMPORTS ====================
# Services and helpers remain in server.py due to complex dependencies

def get_employee_dbs_summary_func():
    """Lazy import of get_employee_dbs_summary from server.py"""
    from server import get_employee_dbs_summary
    return get_employee_dbs_summary


def get_check_record_service():
    """Lazy import of CheckRecordService from server.py"""
    from server import CheckRecordService
    return CheckRecordService


def get_document_extraction_service():
    """Lazy import of DocumentExtractionService from server.py"""
    from server import DocumentExtractionService
    return DocumentExtractionService


def get_employee_status():
    """Lazy import of EmployeeStatus from server.py"""
    from server import EmployeeStatus
    return EmployeeStatus


def get_storage_helpers():
    """Lazy import of storage helpers from server.py"""
    from server import download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf
    return download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf


# ==================== DBS REGISTER ENDPOINT ====================

@router.get("/dbs-register")
async def get_dbs_register(
    status_filter: Optional[str] = None,
    needs_attention: bool = False,
    user: dict = Depends(get_current_user)
):
    """
    DBS Register - Single source of truth for DBS status across all employees.
    Uses get_employee_dbs_summary() to compute all values.
    """
    db = get_db()
    EmployeeStatus = get_employee_status()
    get_employee_dbs_summary = get_employee_dbs_summary_func()
    
    # Get all non-archived employees
    employees = await db.employees.find(
        {"status": {"$ne": EmployeeStatus.ARCHIVED}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1, "email": 1}
    ).to_list(1000)
    
    register = []
    for emp in employees:
        # Use the SINGLE computed DBS summary function
        dbs_summary = await get_employee_dbs_summary(emp["id"])
        
        # Apply filters
        if status_filter and dbs_summary["dbs_status"] != status_filter:
            continue
        if needs_attention and not dbs_summary["needs_attention"]:
            continue
        
        register.append({
            "employee_id": emp["id"],
            "employee_name": f"{emp['first_name']} {emp['last_name']}",
            "role": emp.get("role", ""),
            "email": emp.get("email", ""),
            **dbs_summary
        })
    
    # Sort: needs_attention first, then by next_dbs_review_due
    register.sort(key=lambda x: (
        not x.get("needs_attention", False),  # needs_attention=True first
        x.get("next_dbs_review_due") or "9999"  # earliest review due first
    ))
    
    # Summary stats
    stats = {
        "total": len(register),
        "current": len([r for r in register if r["dbs_status"] == "current"]),
        "certificate_only": len([r for r in register if r["dbs_status"] == "certificate_only"]),
        "pending_verification": len([r for r in register if r["dbs_status"] == "pending_verification"]),
        "review_due_soon": len([r for r in register if r["dbs_status"] == "review_due_soon"]),
        "review_overdue": len([r for r in register if r["dbs_status"] == "review_overdue"]),
        "missing": len([r for r in register if r["dbs_status"] == "missing"]),
        "needs_attention": len([r for r in register if r["needs_attention"]])
    }
    
    return {
        "register": register,
        "stats": stats
    }


# ==================== DBS EXTRACTION ENDPOINT ====================

@router.post("/dbs/extract")
async def extract_dbs_document(
    request: DBSExtractionRequest,
    employee_id: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Extract DBS certificate/Update Service screenshot fields using GPT Vision.
    
    This endpoint supports two modes:
    1. Extract from existing document: Provide `document_id`
    2. Direct extraction: Provide `file_base64` (for preview before upload)
    
    Returns extracted fields that can be used to pre-populate the DBS check form.
    
    For DBS Certificates:
    - Certificate number (12 digits)
    - DBS level (Basic, Standard, Enhanced)
    - Issue date
    - Name on certificate
    - Workforce type
    
    For Update Service Screenshots:
    - Status (No change to disclose / Changed - disclose new certificate)
    - Last check date
    - Certificate reference
    
    Note: DBS certificates do NOT have an expiry date. Any renewal policy is internal.
    """
    db = get_db()
    DocumentExtractionService = get_document_extraction_service()
    
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="LLM key not configured")
        
        images = []
        employee_name = None
        
        if request.document_id:
            # Mode 1: Extract from existing document
            doc = await db.employee_documents.find_one({"id": request.document_id}, {"_id": 0})
            if not doc:
                # Try finding by file_id in evidence_files
                doc = await db.employee_documents.find_one(
                    {"evidence_files.file_id": request.document_id},
                    {"_id": 0}
                )
            
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Get employee name for validation
            emp_id = doc.get("employee_id") or employee_id
            if emp_id:
                emp = await db.employees.find_one({"id": emp_id}, {"_id": 0, "first_name": 1, "last_name": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            # Get file content
            file_url = doc.get("file_url")
            file_type = doc.get("file_type") or doc.get("content_type") or "image/png"
            
            if not file_url and doc.get("evidence_files"):
                for ef in doc.get("evidence_files", []):
                    if ef.get("file_id") == request.document_id or ef.get("status") not in ["rejected", "superseded"]:
                        file_url = ef.get("file_url")
                        file_type = ef.get("file_type") or file_type
                        break
            
            if not file_url:
                raise HTTPException(status_code=404, detail="Document file not found")
            
            # Download file content
            if file_url.startswith("/api/"):
                file_content = doc.get("file_content")
                if not file_content:
                    raise HTTPException(status_code=400, detail="Cannot extract from this document - file content not directly accessible")
            elif file_url.startswith("data:"):
                _, encoded = file_url.split(",", 1)
                file_content = base64.b64decode(encoded)
            else:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(file_url)
                    if resp.status_code != 200:
                        raise HTTPException(status_code=400, detail="Could not download document file")
                    file_content = resp.content
            
            images = await DocumentExtractionService._convert_to_images(file_content, file_type)
        
        elif request.file_base64:
            # Mode 2: Direct extraction from base64
            logger.info(f"DBS Extraction: Direct extraction, file_type={request.file_type}")
            
            # Get employee name if employee_id provided
            if employee_id:
                emp = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            # If PDF, need to convert to images first
            file_type = request.file_type or "image/png"
            if file_type == "application/pdf" or file_type.endswith("/pdf"):
                logger.info("DBS Extraction: Converting PDF to images")
                try:
                    file_content = base64.b64decode(request.file_base64)
                    images = await DocumentExtractionService._convert_to_images(file_content, file_type)
                    logger.info(f"DBS Extraction: Converted PDF to {len(images)} images")
                except Exception as e:
                    logger.error(f"DBS Extraction: PDF conversion failed - {e}")
                    raise HTTPException(status_code=400, detail=f"Failed to convert PDF: {str(e)}")
            else:
                # Image - use directly
                images = [request.file_base64]
        
        else:
            raise HTTPException(status_code=400, detail="Provide either document_id or file_base64")
        
        if not images:
            raise HTTPException(status_code=400, detail="Could not extract images from document")
        
        logger.info(f"DBS Extraction: Processing {len(images)} image(s)")
        
        # Call the DBS extraction method
        result = await DocumentExtractionService._extract_dbs_enhanced(
            images=images,
            api_key=api_key,
            employee_name=employee_name
        )
        
        # Log audit
        await log_audit_action(user['user_id'], "extract_dbs_document", "dbs_extraction", request.document_id or "direct", {
            "employee_id": employee_id,
            "fields_extracted": list(result.get("fields", {}).keys()),
            "issues_count": len(result.get("issues", []))
        })
        
        return {
            "success": True,
            "extraction": {
                "fields": result.get("fields", {}),
                "metadata": result.get("metadata", {}),
                "issues": result.get("issues", [])
            },
            "employee_name": employee_name,
            "document_id": request.document_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DBS extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "extraction": None
        }


# ==================== DBS CHECK ENDPOINTS ====================

@router.post("/employees/{employee_id}/dbs/check")
async def record_dbs_check(
    employee_id: str,
    data: DBSCheckInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Record a DBS status check.
    
    Important: DBS certificates do NOT have a statutory expiry date.
    The "review_due_at" is your INTERNAL POLICY date, not certificate expiry.
    
    Methods:
    - update_service_check: DBS Update Service online check
    - manual_certificate_review: Manual review of certificate
    
    Example payload:
    {
        "method": "update_service_check",
        "checked_at": "2026-03-31",
        "outcome": "verified",
        "review_due_at": "2027-03-31",
        "certificate_number": "123456789012",
        "evidence_document_id": "doc_456",
        "notes": "Update Service status check - no changes to disclose."
    }
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    CheckRecordService = get_check_record_service()
    result = await CheckRecordService.record_dbs_check(
        employee_id=employee_id,
        data=data.model_dump(),
        recorded_by=user['user_id']
    )
    
    return result


@router.get("/employees/{employee_id}/dbs/check")
async def get_dbs_check(
    employee_id: str,
    include_history: bool = False,
    user: dict = Depends(get_current_user)
):
    """Get the current DBS check for an employee."""
    CheckRecordService = get_check_record_service()
    current = await CheckRecordService.get_current_dbs_check(employee_id)
    
    if include_history:
        history = await CheckRecordService.get_dbs_check_history(employee_id)
        return {
            "current": current,
            "history": history
        }
    
    return {"current": current}


# ==================== DBS STAMP ALL ENDPOINT ====================

@router.post("/employees/{employee_id}/dbs/stamp-all")
async def stamp_all_dbs_documents(
    employee_id: str,
    data: StampAllInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    FINAL STEP: Stamp ALL DBS documents (certificate + Update Service proof) atomically.
    Same flow as RTW stamp-all.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf = get_storage_helpers()
    
    verification_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now(timezone.utc).isoformat()
    admin_name = user.get('name', 'Admin')
    employee_name = employee.get('name') or f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    stamped_count = 0
    errors = []
    
    # STEP 1: Stamp all DBS certificate documents
    for doc_id in data.evidence_file_ids:
        try:
            document = await db.employee_documents.find_one({"id": doc_id})
            if not document:
                errors.append(f"Document {doc_id} not found")
                continue
            
            stamp_data = {
                "stamp_type": "original_seen",
                "document_type": "DBS Certificate",
                "employee_name": employee_name,
                "verified_by_name": admin_name,
                "verified_at": now,
                "verification_id": verification_id
            }
            
            file_url = document.get('file_url')
            stamped_url = None
            
            if file_url:
                try:
                    file_bytes = await download_file_from_storage(file_url)
                    if file_bytes and document.get('file_type') == 'application/pdf':
                        stamped_bytes = add_verification_stamp_to_pdf(file_bytes, stamp_data)
                        stamped_filename = f"stamped_{document.get('file_name', 'document.pdf')}"
                        stamped_url = await upload_file_to_storage(
                            stamped_bytes,
                            stamped_filename,
                            f"employees/{employee_id}/dbs"
                        )
                except Exception as e:
                    logging.error(f"Failed to stamp DBS evidence {doc_id}: {e}")
            
            await db.employee_documents.update_one(
                {"id": doc_id},
                {"$set": {
                    "stamped_file_url": stamped_url,
                    "verification_stamp": stamp_data,
                    "status": "verified",
                    "verified_at": now,
                    "verified_by": user['user_id'],
                    "updated_at": now
                }}
            )
            stamped_count += 1
            
        except Exception as e:
            logging.error(f"Error stamping DBS evidence {doc_id}: {e}")
            errors.append(f"Failed to stamp {doc_id}")
    
    # STEP 2: Stamp DBS Update Service proof (if exists)
    if data.stamp_verification_proof:
        dbs_check = await db.employees.find_one(
            {"id": employee_id},
            {"dbs_check": 1}
        )
        
        check_data = dbs_check.get('dbs_check') if dbs_check else None
        if check_data:
            proof_doc_id = check_data.get('evidence_document_id')
            if proof_doc_id:
                try:
                    proof_doc = await db.employee_documents.find_one({"id": proof_doc_id})
                    if proof_doc and not proof_doc.get('verification_stamp'):
                        stamp_data = {
                            "stamp_type": "online_check",
                            "document_type": "DBS Update Service Proof",
                            "employee_name": employee_name,
                            "verified_by_name": admin_name,
                            "verified_at": now,
                            "verification_id": verification_id
                        }
                        
                        file_url = proof_doc.get('file_url')
                        stamped_url = None
                        
                        if file_url:
                            try:
                                file_bytes = await download_file_from_storage(file_url)
                                if file_bytes and proof_doc.get('file_type') == 'application/pdf':
                                    stamped_bytes = add_verification_stamp_to_pdf(file_bytes, stamp_data)
                                    stamped_filename = f"stamped_{proof_doc.get('file_name', 'proof.pdf')}"
                                    stamped_url = await upload_file_to_storage(
                                        stamped_bytes,
                                        stamped_filename,
                                        f"employees/{employee_id}/dbs"
                                    )
                            except Exception as e:
                                logging.error(f"Failed to stamp DBS proof: {e}")
                        
                        await db.employee_documents.update_one(
                            {"id": proof_doc_id},
                            {"$set": {
                                "stamped_file_url": stamped_url,
                                "verification_stamp": stamp_data,
                                "updated_at": now
                            }}
                        )
                        stamped_count += 1
                except Exception as e:
                    logging.error(f"Error stamping DBS proof: {e}")
    
    # STEP 3: Update employee DBS status
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "dbs_fully_verified": True,
            "dbs_verification_id": verification_id,
            "dbs_stamped_at": now,
            "dbs_stamped_by": user['user_id'],
            "updated_at": now
        }}
    )
    
    # STEP 4: Log audit trail
    await log_audit_action(
        user['user_id'],
        "stamp_all_dbs_documents",
        "employee",
        employee_id,
        {
            "verification_id": verification_id,
            "evidence_files_stamped": len(data.evidence_file_ids),
            "proof_stamped": data.stamp_verification_proof,
            "total_stamped": stamped_count,
            "errors": errors if errors else None
        }
    )
    
    return {
        "success": True,
        "message": f"Successfully stamped {stamped_count} document(s) with verification ID {verification_id}",
        "verification_id": verification_id,
        "documents_stamped": stamped_count,
        "errors": errors if errors else None
    }
