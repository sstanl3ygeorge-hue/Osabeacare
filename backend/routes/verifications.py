"""
Verification routes for Identity, Address (POA), and Right to Work (RTW) checks.

Handles:
- Document extraction using AI/Vision (RTW, Identity, Address)
- Recording verification checks
- Unified verify-and-stamp actions
- Stamp-all endpoints for final document processing

This implements the 3-Layer verification model:
- Layer 1: Evidence (uploaded documents)
- Layer 2: Verification (admin checks and methods)
- Layer 3: Result (extracted details, match confirmations)
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
router = APIRouter(tags=["Verifications"])


# ==================== PYDANTIC MODELS ====================

class RTWExtractionRequest(BaseModel):
    """Request model for RTW document extraction."""
    document_id: Optional[str] = Field(None, description="Document ID to extract from")
    file_base64: Optional[str] = Field(None, description="Base64 encoded file content for direct extraction")
    file_type: Optional[str] = Field("image/png", description="MIME type of the file")


class IdentityExtractionRequest(BaseModel):
    """Request model for Identity document extraction."""
    document_id: Optional[str] = Field(None, description="Document ID to extract from")
    file_base64: Optional[str] = Field(None, description="Base64 encoded file content for direct extraction")
    file_type: Optional[str] = Field("image/png", description="MIME type of the file")


class AddressExtractionRequest(BaseModel):
    """Request model for Address/POA document extraction."""
    document_id: Optional[str] = Field(None, description="Document ID to extract from")
    file_base64: Optional[str] = Field(None, description="Base64 encoded file content for direct extraction")
    file_type: Optional[str] = Field("image/png", description="MIME type of the file")


class IdentityCheckInput(BaseModel):
    """
    Input for recording an Identity verification check.
    
    Identity 3-Layer Model:
    - Layer 1: Evidence (Passport, Driving License, ID Card)
    - Layer 2: Verification (original_document_seen, copy_verified, digital_id_verification)
    - Layer 3: Identity Result (document details, name/DOB match, photo match)
    """
    method: str = Field(..., description="Identity verification method")
    checked_at: str = Field(..., description="Date check was performed (YYYY-MM-DD)")
    outcome: str = Field(default="verified", description="Check outcome (verified, failed, follow_up_required)")
    
    document_type: Optional[str] = Field(None, description="Document type (passport, driving_licence, national_id, brp)")
    full_name_on_document: Optional[str] = Field(None, description="Full name as shown on document")
    date_of_birth: Optional[str] = Field(None, description="Date of birth on document (YYYY-MM-DD)")
    document_number: Optional[str] = Field(None, description="Document number/passport number")
    issue_date: Optional[str] = Field(None, description="Document issue date (YYYY-MM-DD)")
    expiry_date: Optional[str] = Field(None, description="Document expiry date (YYYY-MM-DD)")
    nationality: Optional[str] = Field(None, description="Nationality on document")
    
    name_matches_application: bool = Field(default=False, description="Name matches application form")
    dob_matches_application: bool = Field(default=False, description="DOB matches application form")
    photo_match_confirmed: bool = Field(default=False, description="Photo matches applicant")
    
    evidence_document_ids: List[str] = Field(default_factory=list, description="IDs of linked evidence files")
    proof_document_id: Optional[str] = Field(None, description="ID of proof-of-check file")
    notes: Optional[str] = Field(None, description="Verification notes")


class AddressVerificationInput(BaseModel):
    """
    Input for recording a Proof of Address verification check.
    
    POA 3-Layer Model:
    - Layer 1: Evidence (Utility bills, bank statements, council tax)
    - Layer 2: Verification (original_document_seen, copy_verified)
    - Layer 3: Address Result (document count, types, address match, recency)
    
    POA requires configurable minimum document count (default: 2).
    """
    method: str = Field(..., description="Address verification method")
    checked_at: str = Field(..., description="Date check was performed (YYYY-MM-DD)")
    outcome: str = Field(default="verified", description="Check outcome (verified, failed, follow_up_required)")
    
    documents_received_count: int = Field(default=0, description="Number of documents received")
    documents_required_count: int = Field(default=2, description="Minimum documents required")
    verified_documents: List[dict] = Field(default_factory=list, description="List of verified documents")
    
    extracted_address_line1: Optional[str] = Field(None, description="Address line 1 from document")
    extracted_address_line2: Optional[str] = Field(None, description="Address line 2 from document")
    extracted_city: Optional[str] = Field(None, description="City from document")
    extracted_postcode: Optional[str] = Field(None, description="Postcode from document")
    
    address_matches_application: bool = Field(default=False, description="Address matches application form")
    all_documents_sufficiently_recent: bool = Field(default=False, description="All documents within recency limits")
    
    evidence_document_ids: List[str] = Field(default_factory=list, description="IDs of linked evidence files")
    proof_document_id: Optional[str] = Field(None, description="ID of proof-of-check file")
    notes: Optional[str] = Field(None, description="Verification notes")


class UnifiedVerifyStampInput(BaseModel):
    """Input for combined verify + stamp action (Identity & PoA only)"""
    document_id: str
    method: str
    stamp_type: str  # 'original_seen' or 'copy_verified'
    checks_confirmed: dict  # { document_genuine: bool, details_match: bool, date_valid: bool }
    ai_validation: Optional[dict] = None


class StampAllInput(BaseModel):
    """Input for stamping all documents (evidence + verification proof)"""
    evidence_file_ids: List[str]
    stamp_verification_proof: bool = True


# ==================== LAZY IMPORTS ====================

def get_check_record_service():
    """Lazy import of CheckRecordService from server.py"""
    from server import CheckRecordService
    return CheckRecordService


def get_document_extraction_service():
    """Lazy import of DocumentExtractionService from server.py"""
    from server import DocumentExtractionService
    return DocumentExtractionService


def get_storage_helpers():
    """Lazy import of storage helpers from server.py"""
    from server import download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf
    return download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf


# ==================== RTW EXTRACTION ENDPOINT ====================

@router.post("/rtw/extract")
async def extract_rtw_document(
    request: RTWExtractionRequest,
    employee_id: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Extract Right to Work fields from a document using GPT Vision.
    
    Supports two modes:
    1. Extract from existing document: Provide `document_id`
    2. Direct extraction: Provide `file_base64` (for preview before upload)
    """
    db = get_db()
    DocumentExtractionService = get_document_extraction_service()
    
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        images = []
        employee_name = None
        
        if request.document_id:
            doc = await db.employee_documents.find_one({"id": request.document_id}, {"_id": 0})
            if not doc:
                doc = await db.employee_documents.find_one(
                    {"evidence_files.file_id": request.document_id},
                    {"_id": 0}
                )
            
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            emp_id = doc.get("employee_id") or employee_id
            if emp_id:
                emp = await db.employees.find_one({"id": emp_id}, {"_id": 0, "first_name": 1, "last_name": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
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
            if employee_id:
                emp = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            file_type = request.file_type or "image/png"
            if file_type == "application/pdf" or file_type.endswith("/pdf"):
                file_content = base64.b64decode(request.file_base64)
                images = await DocumentExtractionService._convert_to_images(file_content, file_type)
            else:
                images = [request.file_base64]
        
        else:
            raise HTTPException(status_code=400, detail="Provide either document_id or file_base64")
        
        if not images:
            raise HTTPException(status_code=400, detail="Could not convert document to images for extraction")
        
        result = await DocumentExtractionService._extract_right_to_work(
            images=images,
            api_key=api_key,
            employee_name=employee_name
        )
        
        await log_audit_action(user['user_id'], "extract_rtw_document", "rtw_extraction", request.document_id or "direct", {
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
        logger.error(f"RTW extraction failed: {e}")
        return {"success": False, "error": str(e), "extraction": None}


# ==================== IDENTITY EXTRACTION ENDPOINT ====================

@router.post("/identity/extract")
async def extract_identity_document(
    request: IdentityExtractionRequest,
    employee_id: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Extract Identity document fields using GPT Vision.
    
    Extracts fields for the Identity Result Panel:
    - document_type (passport, driving_licence, national_id, brp)
    - full_name_on_document
    - date_of_birth
    - document_number
    - issue_date
    - expiry_date
    - nationality
    """
    db = get_db()
    DocumentExtractionService = get_document_extraction_service()
    
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        images = []
        employee_name = None
        employee_dob = None
        
        if request.document_id:
            doc = await db.employee_documents.find_one({"id": request.document_id}, {"_id": 0})
            if not doc:
                doc = await db.employee_documents.find_one(
                    {"evidence_files.file_id": request.document_id},
                    {"_id": 0}
                )
            
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            emp_id = doc.get("employee_id") or employee_id
            if emp_id:
                emp = await db.employees.find_one({"id": emp_id}, {"_id": 0, "first_name": 1, "last_name": 1, "date_of_birth": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
                    employee_dob = emp.get("date_of_birth")
            
            file_url = doc.get("file_url")
            file_type = doc.get("file_type") or "image/png"
            
            if not file_url and doc.get("evidence_files"):
                for ef in doc.get("evidence_files", []):
                    if ef.get("file_id") == request.document_id or ef.get("status") not in ["rejected", "superseded"]:
                        file_url = ef.get("file_url")
                        file_type = ef.get("file_type") or file_type
                        break
            
            if file_url and file_url.startswith("data:"):
                _, encoded = file_url.split(",", 1)
                file_content = base64.b64decode(encoded)
                images = await DocumentExtractionService._convert_to_images(file_content, file_type)
            elif file_url:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(file_url)
                    if resp.status_code == 200:
                        file_content = resp.content
                        images = await DocumentExtractionService._convert_to_images(file_content, file_type)
        
        elif request.file_base64:
            if employee_id:
                emp = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "date_of_birth": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
                    employee_dob = emp.get("date_of_birth")
            
            file_type = request.file_type or "image/png"
            if file_type == "application/pdf" or file_type.endswith("/pdf"):
                file_content = base64.b64decode(request.file_base64)
                images = await DocumentExtractionService._convert_to_images(file_content, file_type)
            else:
                images = [request.file_base64]
        
        else:
            raise HTTPException(status_code=400, detail="Provide either document_id or file_base64")
        
        if not images:
            raise HTTPException(status_code=400, detail="Could not extract images from document")
        
        result = await DocumentExtractionService._extract_identity(
            images=images,
            api_key=api_key,
            employee_name=employee_name,
            employee_dob=employee_dob
        )
        
        await log_audit_action(user['user_id'], "extract_identity_document", "identity_extraction", request.document_id or "direct", {
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
        logger.error(f"Identity extraction failed: {e}")
        return {"success": False, "error": str(e), "extraction": None}


# ==================== ADDRESS EXTRACTION ENDPOINT ====================

@router.post("/address/extract")
async def extract_address_document(
    request: AddressExtractionRequest,
    employee_id: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Extract Proof of Address document fields using GPT Vision.
    
    Extracts fields for POA verification:
    - document_type (utility_bill, bank_statement, council_tax, etc.)
    - document_date
    - address_line1, address_line2, city, postcode
    - recency_status (valid/invalid based on document type rules)
    """
    db = get_db()
    DocumentExtractionService = get_document_extraction_service()
    
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        images = []
        employee_name = None
        employee_address = None
        
        if request.document_id:
            doc = await db.employee_documents.find_one({"id": request.document_id}, {"_id": 0})
            if not doc:
                doc = await db.employee_documents.find_one(
                    {"evidence_files.file_id": request.document_id},
                    {"_id": 0}
                )
            
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            emp_id = doc.get("employee_id") or employee_id
            if emp_id:
                emp = await db.employees.find_one({"id": emp_id}, {"_id": 0, "first_name": 1, "last_name": 1, "address": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
                    employee_address = emp.get("address")
            
            file_url = doc.get("file_url")
            file_type = doc.get("file_type") or "image/png"
            
            if not file_url and doc.get("evidence_files"):
                for ef in doc.get("evidence_files", []):
                    if ef.get("file_id") == request.document_id or ef.get("status") not in ["rejected", "superseded"]:
                        file_url = ef.get("file_url")
                        file_type = ef.get("file_type") or file_type
                        break
            
            if file_url and file_url.startswith("data:"):
                _, encoded = file_url.split(",", 1)
                file_content = base64.b64decode(encoded)
                images = await DocumentExtractionService._convert_to_images(file_content, file_type)
            elif file_url:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(file_url)
                    if resp.status_code == 200:
                        file_content = resp.content
                        images = await DocumentExtractionService._convert_to_images(file_content, file_type)
        
        elif request.file_base64:
            if employee_id:
                emp = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "address": 1})
                if emp:
                    employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
                    employee_address = emp.get("address")
            
            file_type = request.file_type or "image/png"
            if file_type == "application/pdf" or file_type.endswith("/pdf"):
                file_content = base64.b64decode(request.file_base64)
                images = await DocumentExtractionService._convert_to_images(file_content, file_type)
            else:
                images = [request.file_base64]
        
        else:
            raise HTTPException(status_code=400, detail="Provide either document_id or file_base64")
        
        if not images:
            raise HTTPException(status_code=400, detail="Could not extract images from document")
        
        result = await DocumentExtractionService._extract_proof_of_address(
            images=images,
            api_key=api_key,
            employee_name=employee_name,
            employee_address=employee_address
        )
        
        await log_audit_action(user['user_id'], "extract_address_document", "address_extraction", request.document_id or "direct", {
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
        logger.error(f"Address extraction failed: {e}")
        return {"success": False, "error": str(e), "extraction": None}


# ==================== IDENTITY CHECK ENDPOINTS ====================

@router.post("/employees/{employee_id}/identity/check")
async def record_identity_check(
    employee_id: str,
    data: IdentityCheckInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Record an Identity verification check.
    
    Methods:
    - original_document_seen: Physical document seen in person
    - copy_verified: Copy of document verified
    - digital_id_verification: Digital ID verification service used
    - other_documented_verification: Other documented verification method
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    CheckRecordService = get_check_record_service()
    result = await CheckRecordService.record_identity_verification(
        employee_id=employee_id,
        data=data.model_dump(),
        recorded_by=user['user_id']
    )
    
    return result


@router.get("/employees/{employee_id}/identity/check")
async def get_identity_check(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get the current Identity verification for an employee with computed status."""
    CheckRecordService = get_check_record_service()
    current = await CheckRecordService.get_current_identity_check(employee_id)
    return {"current": current}


# ==================== ADDRESS CHECK ENDPOINTS ====================

@router.post("/employees/{employee_id}/address/check")
async def record_address_check(
    employee_id: str,
    data: AddressVerificationInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Record a Proof of Address verification check.
    
    POA requires minimum 2 documents (configurable).
    Each document has recency rules based on type.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    CheckRecordService = get_check_record_service()
    result = await CheckRecordService.record_address_verification(
        employee_id=employee_id,
        data=data.model_dump(),
        recorded_by=user['user_id']
    )
    
    return result


@router.get("/employees/{employee_id}/address/check")
async def get_address_check(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get the current Address verification for an employee with computed status."""
    CheckRecordService = get_check_record_service()
    current = await CheckRecordService.get_current_address_check(employee_id)
    return {"current": current}


# Legacy endpoint for backwards compatibility
@router.post("/employees/{employee_id}/address/verify")
async def record_address_verification(
    employee_id: str,
    data: AddressVerificationInput,
    user: dict = Depends(require_manager_or_admin)
):
    """Record address verification status (legacy endpoint)."""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    CheckRecordService = get_check_record_service()
    result = await CheckRecordService.record_address_verification(
        employee_id=employee_id,
        data=data.model_dump(),
        recorded_by=user['user_id']
    )
    
    return result


@router.get("/employees/{employee_id}/address/verification")
async def get_address_verification(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get the current address verification status for an employee (legacy endpoint)."""
    CheckRecordService = get_check_record_service()
    current = await CheckRecordService.get_current_address_check(employee_id)
    return {"current": current}


# ==================== UNIFIED VERIFY-AND-STAMP ENDPOINTS ====================

@router.post("/employees/{employee_id}/identity/verify-and-stamp")
async def verify_and_stamp_identity(
    employee_id: str,
    data: UnifiedVerifyStampInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    UNIFIED: Record identity verification AND apply stamp in ONE atomic action.
    
    Ensures:
    - No document can be stamped without verification recorded
    - No verification can be recorded without stamp applied
    - Complete audit trail for NHS/CQC compliance
    """
    db = get_db()
    download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf = get_storage_helpers()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    checks = data.checks_confirmed
    if not checks.get('document_genuine') or not checks.get('details_match'):
        raise HTTPException(status_code=400, detail="All verification checks must be confirmed")
    
    document = await db.employee_documents.find_one({"id": data.document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Require checklist completion before final verification.
    if not document.get("file_viewed"):
        raise HTTPException(
            status_code=400,
            detail="Must complete review checklist before verification. Call /start-review endpoint first."
        )
    
    now = datetime.now(timezone.utc).isoformat()
    admin_name = user.get('name', 'Admin')
    
    # STEP 1: Record the verification check
    verification_record = {
        "method": data.method,
        "checked_at": now,
        "checked_by": user['user_id'],
        "checked_by_name": admin_name,
        "outcome": "verified",
        "checks_confirmed": checks,
        "stamp_type": data.stamp_type
    }
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "identity_verification": verification_record,
            "identity_verified": True,
            "identity_verified_at": now,
            "identity_verified_by": user['user_id'],
            "updated_at": now
        }}
    )
    
    # STEP 2: Apply the visual stamp to the document
    stamp_data = {
        "stamp_type": data.stamp_type,
        "document_type": "Identity Document",
        "employee_name": employee.get('name') or f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "verified_by_name": admin_name,
        "verified_at": now,
        "verification_id": str(uuid.uuid4())[:8].upper()
    }
    
    stamped_url = None

    try:
        file_url = document.get('file_url')
        if file_url:
            file_bytes = await download_file_from_storage(file_url)
            if file_bytes and document.get('file_type') == 'application/pdf':
                stamped_bytes = add_verification_stamp_to_pdf(file_bytes, stamp_data)
                stamped_filename = f"stamped_{document.get('file_name', 'document.pdf')}"
                stamped_url = await upload_file_to_storage(
                    stamped_bytes, 
                    stamped_filename, 
                    f"employees/{employee_id}/identity"
                )
    except Exception as e:
        logging.error(f"Failed to apply stamp to identity document: {e}")

    document_update = {
        "status": "approved",
        "verified": True,
        "verified_at": now,
        "verified_by": user['user_id'],
        "verified_by_name": admin_name,
        "review_status": "approved",
        "review_reason": None,
        "reviewed_at": now,
        "reviewed_by": user['user_id'],
        "reviewed_by_name": admin_name,
        "rejection_reason": None,
        "amendment_reason": None,
        "rejected_at": None,
        "amendment_requested_at": None,
        "rejected_by": None,
        "rejected_by_name": None,
        "updated_at": now
    }

    if stamped_url:
        document_update["stamped_file_url"] = stamped_url
        document_update["verification_stamp"] = stamp_data

    await db.employee_documents.update_one(
        {"id": data.document_id},
        {"$set": document_update}
    )
    
    # STEP 3: Log audit trail
    await log_audit_action(
        user['user_id'],
        "verify_and_stamp_identity",
        "employee",
        employee_id,
        {
            "document_id": data.document_id,
            "method": data.method,
            "stamp_type": data.stamp_type,
            "checks_confirmed": checks
        }
    )
    
    return {
        "success": True,
        "message": "Identity verified and stamped successfully",
        "verification": verification_record,
        "stamp_applied": stamped_url is not None
    }


@router.post("/employees/{employee_id}/address/verify-and-stamp")
async def verify_and_stamp_address(
    employee_id: str,
    data: UnifiedVerifyStampInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    UNIFIED: Record address verification AND apply stamp in ONE atomic action.
    
    For Proof of Address:
    - AI validates document date (<6 months for bank, <9 for council tax)
    - Admin confirms checks
    - Stamp applied automatically
    """
    db = get_db()
    download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf = get_storage_helpers()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    checks = data.checks_confirmed
    if not checks.get('document_genuine') or not checks.get('details_match') or not checks.get('date_valid'):
        raise HTTPException(status_code=400, detail="All verification checks must be confirmed")
    
    document = await db.employee_documents.find_one({"id": data.document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Require checklist completion before final verification.
    if not document.get("file_viewed"):
        raise HTTPException(
            status_code=400,
            detail="Must complete review checklist before verification. Call /start-review endpoint first."
        )
    
    now = datetime.now(timezone.utc).isoformat()
    admin_name = user.get('name', 'Admin')
    
    # STEP 1: Record the verification check
    verification_record = {
        "method": data.method,
        "checked_at": now,
        "checked_by": user['user_id'],
        "checked_by_name": admin_name,
        "outcome": "verified",
        "checks_confirmed": checks,
        "stamp_type": data.stamp_type,
        "ai_validation": data.ai_validation
    }
    
    # Get existing verified docs count
    existing_verified = await db.employee_documents.count_documents({
        "employee_id": employee_id,
        "requirement_id": "proof_of_address",
        "status": {"$in": ["verified", "approved", "accepted"]},
        "id": {"$ne": data.document_id}
    })
    
    total_verified = existing_verified + 1
    is_complete = total_verified >= 2  # NHS requires 2 PoA documents
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "address_verification": verification_record,
            "address_documents_verified_count": total_verified,
            "address_verified": is_complete,
            "address_verified_at": now if is_complete else None,
            "address_verified_by": user['user_id'] if is_complete else None,
            "updated_at": now
        }}
    )
    
    # STEP 2: Apply the visual stamp to the document
    stamp_data = {
        "stamp_type": data.stamp_type,
        "document_type": "Proof of Address",
        "employee_name": employee.get('name') or f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "verified_by_name": admin_name,
        "verified_at": now,
        "verification_id": str(uuid.uuid4())[:8].upper()
    }
    
    stamped_url = None

    try:
        file_url = document.get('file_url')
        if file_url:
            file_bytes = await download_file_from_storage(file_url)
            if file_bytes and document.get('file_type') == 'application/pdf':
                stamped_bytes = add_verification_stamp_to_pdf(file_bytes, stamp_data)
                stamped_filename = f"stamped_{document.get('file_name', 'document.pdf')}"
                stamped_url = await upload_file_to_storage(
                    stamped_bytes, 
                    stamped_filename, 
                    f"employees/{employee_id}/address"
                )
    except Exception as e:
        logging.error(f"Failed to apply stamp to address document: {e}")

    document_update = {
        "status": "approved",
        "verified": True,
        "verified_at": now,
        "verified_by": user['user_id'],
        "verified_by_name": admin_name,
        "review_status": "approved",
        "review_reason": None,
        "reviewed_at": now,
        "reviewed_by": user['user_id'],
        "reviewed_by_name": admin_name,
        "rejection_reason": None,
        "amendment_reason": None,
        "rejected_at": None,
        "amendment_requested_at": None,
        "rejected_by": None,
        "rejected_by_name": None,
        "updated_at": now
    }

    if stamped_url:
        document_update["stamped_file_url"] = stamped_url
        document_update["verification_stamp"] = stamp_data

    await db.employee_documents.update_one(
        {"id": data.document_id},
        {"$set": document_update}
    )
    
    # STEP 3: Log audit trail
    await log_audit_action(
        user['user_id'],
        "verify_and_stamp_address",
        "employee",
        employee_id,
        {
            "document_id": data.document_id,
            "method": data.method,
            "stamp_type": data.stamp_type,
            "checks_confirmed": checks,
            "documents_verified_count": total_verified,
            "is_complete": is_complete
        }
    )
    
    return {
        "success": True,
        "message": f"Address document verified and stamped. {total_verified}/2 documents verified.",
        "verification": verification_record,
        "stamp_applied": stamped_url is not None,
        "documents_verified_count": total_verified,
        "is_complete": is_complete
    }


# ==================== RTW STAMP-ALL ENDPOINT ====================

@router.post("/employees/{employee_id}/right_to_work/stamp-all")
async def stamp_all_rtw_documents(
    employee_id: str,
    data: StampAllInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    FINAL STEP: Stamp ALL RTW documents (evidence + verification proof) atomically.
    
    This is the culmination of the verification process:
    1. Employee uploaded evidence (passport/BRP/share code)
    2. Admin reviewed and accepted evidence
    3. Admin did online check (Home Office)
    4. Admin uploaded proof of check
    5. Admin recorded check details
    6. NOW: Admin confirms and stamps EVERYTHING
    
    Both documents get the same Verification ID for audit linking.
    """
    db = get_db()
    download_file_from_storage, upload_file_to_storage, add_verification_stamp_to_pdf = get_storage_helpers()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    verification_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now(timezone.utc).isoformat()
    admin_name = user.get('name', 'Admin')
    employee_name = employee.get('name') or f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    stamped_count = 0
    errors = []
    
    # STEP 1: Stamp all evidence documents
    for doc_id in data.evidence_file_ids:
        try:
            document = await db.employee_documents.find_one({"id": doc_id})
            if not document:
                errors.append(f"Document {doc_id} not found")
                continue
            
            stamp_data = {
                "stamp_type": "original_seen",
                "document_type": "Right to Work Evidence",
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
                            f"employees/{employee_id}/rtw"
                        )
                except Exception as e:
                    logging.error(f"Failed to stamp RTW evidence {doc_id}: {e}")
            
            await db.employee_documents.update_one(
                {"id": doc_id},
                {"$set": {
                    "stamped_file_url": stamped_url,
                    "verification_stamp": stamp_data,
                    "status": "verified",
                    "verified_at": now,
                    "verified_by": user['user_id'],
                    "review_status": "verified",
                    "review_reason": None,
                    "reviewed_at": now,
                    "reviewed_by": user['user_id'],
                    "reviewed_by_name": admin_name,
                    "updated_at": now
                }}
            )
            stamped_count += 1
            
        except Exception as e:
            logging.error(f"Error stamping evidence {doc_id}: {e}")
            errors.append(f"Failed to stamp {doc_id}")
    
    # STEP 2: Stamp verification proof document (if exists and requested)
    if data.stamp_verification_proof:
        rtw_check = await db.employees.find_one(
            {"id": employee_id},
            {"rtw_check": 1, "right_to_work_check": 1}
        )
        
        check_data = rtw_check.get('rtw_check') or rtw_check.get('right_to_work_check') if rtw_check else None
        if check_data:
            proof_doc_id = check_data.get('proof_document_id') or check_data.get('evidence_document_id')
            if proof_doc_id:
                try:
                    proof_doc = await db.employee_documents.find_one({"id": proof_doc_id})
                    if proof_doc and not proof_doc.get('verification_stamp'):
                        stamp_data = {
                            "stamp_type": "online_check",
                            "document_type": "RTW Verification Proof",
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
                                        f"employees/{employee_id}/rtw"
                                    )
                            except Exception as e:
                                logging.error(f"Failed to stamp RTW proof: {e}")
                        
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
                    logging.error(f"Error stamping verification proof: {e}")
    
    # STEP 3: Update employee RTW status
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "rtw_fully_verified": True,
            "rtw_verification_id": verification_id,
            "rtw_stamped_at": now,
            "rtw_stamped_by": user['user_id'],
            "updated_at": now
        }}
    )
    
    # STEP 4: Log audit trail
    await log_audit_action(
        user['user_id'],
        "stamp_all_rtw_documents",
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
