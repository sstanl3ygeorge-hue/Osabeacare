"""
Smart Verification System Routes
================================

Implements the dual-evidence model for CQC compliance:
- Evidence Tab: Employee uploads (passport, utility bill, DBS cert)
- Verification Tab: Admin uploads proof of verification (gov.uk screenshot, checklist PDF)

Compliance progress only counts when VERIFICATION is approved, not just evidence upload.
"""

import os
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field, validator
from motor.motor_asyncio import AsyncIOMotorClient
import logging

from .dependencies import get_current_user, require_manager_or_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["Smart Verification"])

# MongoDB connection - will be set by main app
db = None

def set_db(database):
    global db
    db = database


# =============================================================================
# MODELS
# =============================================================================

class AIExtractionResult(BaseModel):
    """Result of AI document extraction"""
    extracted_name: Optional[str] = None
    extracted_address: Optional[str] = None
    extracted_date: Optional[str] = None
    document_type: Optional[str] = None
    confidence_scores: dict = {}
    validation_results: dict = {}
    raw_extraction: dict = {}


VALID_REQUIREMENT_IDS = {"right_to_work", "identity", "proof_of_address", "dbs"}
VALID_VERIFICATION_METHODS = {"video_call", "in_person", "online_check"}
VALID_REASON_CODES = {"address_mismatch", "document_too_old", "name_mismatch", "unclear", "wrong_type", "other"}


class VerificationChecklist(BaseModel):
    """Admin verification checklist submission"""
    requirement_id: str  # e.g., "right_to_work", "identity", "proof_of_address", "dbs"
    employee_id: str
    evidence_document_id: Optional[str] = None
    
    # Common fields
    verification_method: str = Field(..., description="'video_call' or 'in_person' or 'online_check'")
    document_appears_genuine: bool = False
    details_match_profile: bool = False
    
    # Identity specific
    photo_matches_applicant: Optional[bool] = None
    security_features_verified: Optional[bool] = None
    expiry_date_valid: Optional[bool] = None
    
    # Proof of Address specific
    address_matches_declared: Optional[bool] = None
    document_within_6_months: Optional[bool] = None
    document_type_acceptable: Optional[bool] = None
    name_matches_employee: Optional[bool] = None
    
    # RTW specific
    share_code_verified: Optional[bool] = None
    right_to_work_confirmed: Optional[bool] = None
    work_restrictions: Optional[str] = None
    share_code_used: Optional[str] = None
    
    # DBS specific
    dbs_update_service_checked: Optional[bool] = None
    dbs_status: Optional[str] = None  # 'no_new_info', 'has_new_info'
    certificate_number_matches: Optional[bool] = None
    
    # General notes
    admin_notes: Optional[str] = None

    @validator('requirement_id')
    def validate_requirement_id(cls, v):
        if v not in VALID_REQUIREMENT_IDS:
            raise ValueError(f"Invalid requirement_id. Must be one of: {', '.join(VALID_REQUIREMENT_IDS)}")
        return v

    @validator('verification_method')
    def validate_verification_method(cls, v):
        if v not in VALID_VERIFICATION_METHODS:
            raise ValueError(f"Invalid verification_method. Must be one of: {', '.join(VALID_VERIFICATION_METHODS)}")
        return v

    @validator('document_appears_genuine')
    def must_confirm_genuine(cls, v):
        if not v:
            raise ValueError("document_appears_genuine must be confirmed as True before submitting checklist")
        return v

    @validator('details_match_profile')
    def must_confirm_details_match(cls, v):
        if not v:
            raise ValueError("details_match_profile must be confirmed as True before submitting checklist")
        return v


class AmendmentRequest(BaseModel):
    """Request for employee to amend/re-upload document"""
    document_id: str
    reason_code: str  # 'address_mismatch', 'document_too_old', 'name_mismatch', 'unclear', 'wrong_type', 'other'
    reason_details: Optional[str] = None

    @validator('reason_code')
    def validate_reason_code(cls, v):
        if v not in VALID_REASON_CODES:
            raise ValueError(f"Invalid reason_code. Must be one of: {', '.join(VALID_REASON_CODES)}")
        return v


class VerificationApproval(BaseModel):
    """Final approval of verification document"""
    verification_document_id: str
    approved: bool
    rejection_reason: Optional[str] = None


# =============================================================================
# VERIFICATION CHECKLIST TEMPLATES
# =============================================================================

CHECKLIST_TEMPLATES = {
    "identity": {
        "title": "Identity Verification Checklist",
        "fields": [
            {"id": "photo_matches_applicant", "label": "Photo matches the applicant", "required": True},
            {"id": "security_features_verified", "label": "Security features verified (hologram, watermark, chip)", "required": True},
            {"id": "document_appears_genuine", "label": "Document appears genuine (not altered)", "required": True},
            {"id": "expiry_date_valid", "label": "Expiry date is valid", "required": True},
            {"id": "details_match_profile", "label": "Details match employee profile", "required": True},
        ],
        "verification_methods": ["in_person", "video_call"],
    },
    "proof_of_address": {
        "title": "Proof of Address Verification Checklist",
        "fields": [
            {"id": "address_matches_declared", "label": "Address matches declared address", "required": True},
            {"id": "document_within_6_months", "label": "Document dated within 6 months", "required": True},
            {"id": "document_type_acceptable", "label": "Document type is acceptable (utility bill, bank statement, council tax)", "required": True},
            {"id": "name_matches_employee", "label": "Name on document matches employee", "required": True},
            {"id": "document_appears_genuine", "label": "Document appears genuine", "required": True},
        ],
        "verification_methods": ["in_person", "video_call", "online_check"],
    },
    "right_to_work": {
        "title": "Right to Work Verification Checklist",
        "fields": [
            {"id": "share_code_verified", "label": "Share code verified on gov.uk", "required": True},
            {"id": "right_to_work_confirmed", "label": "Right to work confirmed", "required": True},
            {"id": "details_match_profile", "label": "Details match employee profile", "required": True},
        ],
        "verification_methods": ["online_check"],
        "extra_fields": [
            {"id": "share_code_used", "label": "Share code used", "type": "text"},
            {"id": "work_restrictions", "label": "Work restrictions (if any)", "type": "text"},
        ]
    },
    "dbs": {
        "title": "DBS Certificate Verification Checklist",
        "fields": [
            {"id": "dbs_update_service_checked", "label": "Certificate verified on DBS Update Service", "required": True},
            {"id": "certificate_number_matches", "label": "Certificate number matches uploaded document", "required": True},
            {"id": "details_match_profile", "label": "Details match employee profile", "required": True},
        ],
        "verification_methods": ["online_check"],
        "extra_fields": [
            {"id": "dbs_status", "label": "DBS Status", "type": "select", "options": ["no_new_info", "has_new_info"]},
        ]
    }
}


# =============================================================================
# AI EXTRACTION HELPERS
# =============================================================================

async def extract_document_info_ai(file_url: str, document_type: str, employee_data: dict) -> AIExtractionResult:
    """
    Use AI (OpenAI) to extract information from document and validate against employee profile.
    """
    try:
        from services.openai_client import call_openai_vision_async, parse_json_response
        
        api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            logger.warning("No OpenAI API key found, skipping AI extraction")
            return AIExtractionResult()
        
        # Build extraction prompt based on document type
        if document_type == "proof_of_address":
            extraction_prompt = """Extract the following from this proof of address document:
1. Full name on the document
2. Full address (including postcode)
3. Document date (the date ON the document, not today)
4. Document type (utility bill, bank statement, council tax, etc.)

Return as JSON:
{
  "name": "extracted name",
  "address": "full address including postcode",
  "document_date": "YYYY-MM-DD format",
  "document_type": "type of document"
}"""
        elif document_type == "identity":
            extraction_prompt = """Extract the following from this identity document:
1. Full name
2. Date of birth
3. Document number
4. Expiry date
5. Document type (passport, driving licence, etc.)

Return as JSON:
{
  "name": "extracted name",
  "date_of_birth": "YYYY-MM-DD",
  "document_number": "number",
  "expiry_date": "YYYY-MM-DD",
  "document_type": "type"
}"""
        else:
            extraction_prompt = """Extract all relevant information from this document.
Return as JSON with appropriate fields."""
        
        response = await call_openai_vision_async(
            extraction_prompt,
            image_url_list=[file_url],
        )
        
        # Parse the response
        extracted_data = parse_json_response(response) if response else {}
        
        # Build validation results
        validation_results = {}
        confidence_scores = {}
        
        # Validate name match
        if "name" in extracted_data and employee_data:
            emp_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip().lower()
            extracted_name = extracted_data.get("name", "").lower()
            
            # Simple fuzzy match
            name_words_emp = set(emp_name.split())
            name_words_ext = set(extracted_name.split())
            common_words = name_words_emp & name_words_ext
            
            if len(name_words_emp) > 0:
                name_match_score = len(common_words) / len(name_words_emp)
                confidence_scores["name_match"] = round(name_match_score * 100)
                validation_results["name_match"] = name_match_score >= 0.5
            else:
                validation_results["name_match"] = False
                confidence_scores["name_match"] = 0
        
        # Validate address match for POA
        if document_type == "proof_of_address" and "address" in extracted_data and employee_data:
            emp_address = employee_data.get("address", "") or employee_data.get("declared_address", "")
            extracted_address = extracted_data.get("address", "")
            
            if emp_address and extracted_address:
                # Simple postcode match
                emp_postcode = emp_address.upper().replace(" ", "")[-7:]
                ext_postcode = extracted_address.upper().replace(" ", "")[-7:]
                
                postcode_match = emp_postcode in ext_postcode or ext_postcode in emp_postcode
                validation_results["address_match"] = postcode_match
                confidence_scores["address_match"] = 100 if postcode_match else 50
        
        # Validate document date for POA (within 6 months)
        if document_type == "proof_of_address" and "document_date" in extracted_data:
            try:
                doc_date = datetime.strptime(extracted_data["document_date"], "%Y-%m-%d")
                six_months_ago = datetime.now() - timedelta(days=180)
                
                validation_results["date_valid"] = doc_date >= six_months_ago
                days_old = (datetime.now() - doc_date).days
                confidence_scores["date_valid"] = max(0, 100 - (days_old / 180 * 100)) if days_old <= 180 else 0
            except ValueError:
                validation_results["date_valid"] = None
        
        return AIExtractionResult(
            extracted_name=extracted_data.get("name"),
            extracted_address=extracted_data.get("address"),
            extracted_date=extracted_data.get("document_date"),
            document_type=extracted_data.get("document_type"),
            confidence_scores=confidence_scores,
            validation_results=validation_results,
            raw_extraction=extracted_data
        )
        
    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        return AIExtractionResult()


def generate_verification_id() -> str:
    """Generate a unique verification ID for audit trail"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:6].upper()
    return f"VRF-{timestamp}-{random_part}"


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/checklist-template/{requirement_id}")
async def get_checklist_template(requirement_id: str):
    """Get the verification checklist template for a requirement type"""
    if requirement_id not in CHECKLIST_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"No checklist template for requirement: {requirement_id}")
    
    return CHECKLIST_TEMPLATES[requirement_id]


@router.post("/extract-document/{document_id}")
async def extract_document_with_ai(
    document_id: str,
    current_user: dict = Depends(require_manager_or_admin)
):
    """
    Run AI extraction on an evidence document and validate against employee profile.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get the document
    doc = await db.employee_documents.find_one({"id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get the employee
    employee = await db.employees.find_one({"id": doc["employee_id"]})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Determine document type from requirement_id
    requirement_id = doc.get("requirement_id", "")
    if "proof_of_address" in requirement_id or "poa" in requirement_id.lower():
        doc_type = "proof_of_address"
    elif "identity" in requirement_id:
        doc_type = "identity"
    elif "right_to_work" in requirement_id or "rtw" in requirement_id.lower():
        doc_type = "right_to_work"
    elif "dbs" in requirement_id:
        doc_type = "dbs"
    else:
        doc_type = "general"
    
    # Get file URL
    file_url = doc.get("file_url", "")
    
    # Run AI extraction
    extraction_result = await extract_document_info_ai(file_url, doc_type, employee)
    
    # Store extraction results on the document
    await db.employee_documents.update_one(
        {"id": document_id},
        {"$set": {
            "ai_extraction": extraction_result.dict(),
            "ai_extraction_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "document_id": document_id,
        "extraction": extraction_result.dict(),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
        "employee_address": employee.get("address") or employee.get("declared_address")
    }


@router.post("/submit-checklist")
async def submit_verification_checklist(
    checklist: VerificationChecklist,
    current_user: dict = Depends(require_manager_or_admin)
):
    """
    Submit admin verification checklist and generate verification document.
    This creates a system-generated verification record that can be approved.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get employee
    employee = await db.employees.find_one({"id": checklist.employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get evidence document if provided
    evidence_doc = None
    if checklist.evidence_document_id:
        evidence_doc = await db.employee_documents.find_one({"id": checklist.evidence_document_id})
    
    # Generate verification ID
    verification_id = generate_verification_id()
    
    # Create verification document record
    now = datetime.now(timezone.utc).isoformat()
    admin_name = current_user.get("email", "Unknown") if current_user else "System"
    admin_id = current_user.get("user_id", "system") if current_user else "system"
    
    verification_doc = {
        "id": str(uuid.uuid4()),
        "verification_id": verification_id,
        "employee_id": checklist.employee_id,
        "requirement_id": checklist.requirement_id,
        "evidence_document_id": checklist.evidence_document_id,
        "row_type": "verification",  # Key field - distinguishes from evidence
        
        # Checklist data
        "checklist_data": checklist.dict(),
        "verification_method": checklist.verification_method,
        
        # AI extraction results (if available)
        "ai_extraction": evidence_doc.get("ai_extraction") if evidence_doc else None,
        
        # Status
        "status": "pending_approval",  # Needs final approval to count
        "verification_approved": False,
        
        # Audit trail
        "submitted_by": admin_id,
        "submitted_by_name": admin_name,
        "submitted_at": now,
        "created_at": now,
        "updated_at": now,
    }
    
    await db.verification_documents.insert_one(verification_doc)
    
    # Update employee record to track verification progress
    update_field = f"{checklist.requirement_id}_verification_submitted"
    await db.employees.update_one(
        {"id": checklist.employee_id},
        {"$set": {
            update_field: True,
            f"{checklist.requirement_id}_verification_id": verification_doc["id"],
            "updated_at": now
        }}
    )
    
    return {
        "success": True,
        "verification_id": verification_id,
        "verification_document_id": verification_doc["id"],
        "status": "pending_approval",
        "message": "Checklist submitted. Please approve to complete verification."
    }


@router.post("/approve")
async def approve_verification(
    approval: VerificationApproval,
    current_user: dict = Depends(require_manager_or_admin)
):
    """
    Final approval of verification document. This is what makes compliance % increase.
    Generates verification PDF and stamps evidence document.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get verification document
    ver_doc = await db.verification_documents.find_one({"id": approval.verification_document_id})
    if not ver_doc:
        raise HTTPException(status_code=404, detail="Verification document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    admin_name = current_user.get("email", "Unknown") if current_user else "System"
    admin_id = current_user.get("user_id", "system") if current_user else "system"
    
    if approval.approved:
        # Get employee data for PDF generation
        employee = await db.employees.find_one({"id": ver_doc["employee_id"]}, {"_id": 0})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        requirement_id = ver_doc.get("requirement_id")
        verification_id = ver_doc.get("verification_id", generate_verification_id())
        
        # Requirement labels
        REQUIREMENT_LABELS = {
            'right_to_work': 'Right to Work',
            'dbs': 'DBS Certificate',
            'identity': 'Identity Document',
            'proof_of_address': 'Proof of Address'
        }
        requirement_label = REQUIREMENT_LABELS.get(requirement_id, requirement_id.replace('_', ' ').title())
        
        # Generate verification PDF
        verification_pdf_url = None
        stamped_evidence_url = None
        
        try:
            from services.pdf_service import generate_verification_pdf, stamp_evidence_document
            from emergentintegrations.cloud_storage import CloudStorage, StorageConfig
            
            CLOUD_STORAGE_URL = os.environ.get("CLOUD_STORAGE_URL")
            
            # Generate verification record PDF
            pdf_bytes = generate_verification_pdf(
                employee_data=employee,
                requirement_id=requirement_id,
                requirement_label=requirement_label,
                checklist_data=ver_doc.get("checklist_data", {}),
                ai_extraction=ver_doc.get("ai_extraction"),
                verification_method=ver_doc.get("verification_method"),
                admin_name=admin_name,
                admin_notes=ver_doc.get("checklist_data", {}).get("admin_notes"),
                verification_id=verification_id,
                verified_at=now
            )
            
            # Upload verification PDF to cloud storage
            if CLOUD_STORAGE_URL:
                storage = CloudStorage(StorageConfig(storage_url=CLOUD_STORAGE_URL))
                
                emp_code = employee.get('employee_code') or employee.get('applicant_reference') or 'unknown'
                pdf_filename = f"verification_{requirement_id}_{verification_id}.pdf"
                
                verification_pdf_url = await storage.upload_file_async(
                    file_data=pdf_bytes,
                    file_name=pdf_filename,
                    folder=f"employees/{emp_code}/verifications",
                    content_type="application/pdf"
                )
                logger.info(f"Verification PDF uploaded: {verification_pdf_url}")
            
            # Stamp the original evidence document if it exists
            evidence_doc_id = ver_doc.get("evidence_document_id")
            if evidence_doc_id and CLOUD_STORAGE_URL:
                evidence_doc = await db.employee_documents.find_one({"id": evidence_doc_id})
                if evidence_doc and evidence_doc.get("file_url"):
                    try:
                        # Download the original evidence
                        import httpx
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(evidence_doc["file_url"])
                            if resp.status_code == 200:
                                original_bytes = resp.content
                                
                                # Determine if image or PDF
                                file_type = evidence_doc.get("file_type", "").lower()
                                is_image = any(ext in file_type for ext in ['image', 'jpg', 'jpeg', 'png', 'gif'])
                                
                                # Stamp the document
                                stamped_bytes = stamp_evidence_document(
                                    document_bytes=original_bytes,
                                    admin_name=admin_name,
                                    verified_at=now,
                                    verification_id=verification_id,
                                    is_image=is_image
                                )
                                
                                # Upload stamped version
                                stamped_filename = f"stamped_{evidence_doc.get('file_name', 'evidence')}"
                                if not stamped_filename.endswith('.pdf'):
                                    stamped_filename = stamped_filename.rsplit('.', 1)[0] + '_stamped.pdf'
                                
                                stamped_evidence_url = await storage.upload_file_async(
                                    file_data=stamped_bytes,
                                    file_name=stamped_filename,
                                    folder=f"employees/{emp_code}/documents",
                                    content_type="application/pdf"
                                )
                                logger.info(f"Stamped evidence uploaded: {stamped_evidence_url}")
                    except Exception as stamp_err:
                        logger.error(f"Error stamping evidence document: {stamp_err}")
        
        except Exception as pdf_err:
            logger.error(f"Error generating verification PDF: {pdf_err}")
            # Continue with approval even if PDF generation fails
        
        # Approve verification
        update_data = {
            "status": "approved",
            "verification_approved": True,
            "approved_by": admin_id,
            "approved_by_name": admin_name,
            "approved_at": now,
            "review_status": "verified",
            "review_reason": None,
            "reviewed_at": now,
            "reviewed_by": admin_id,
            "reviewed_by_name": admin_name,
            "updated_at": now,
            "verification_pdf_url": verification_pdf_url,
        }
        
        await db.verification_documents.update_one(
            {"id": approval.verification_document_id},
            {"$set": update_data}
        )
        
        # Update employee record
        await db.employees.update_one(
            {"id": ver_doc["employee_id"]},
            {"$set": {
                f"{requirement_id}_verified": True,
                f"{requirement_id}_verified_at": now,
                f"{requirement_id}_verified_by": admin_name,
                f"{requirement_id}_verification_pdf_url": verification_pdf_url,
                "updated_at": now
            }}
        )
        
        # Update the evidence document with stamp info and stamped URL
        evidence_doc_id = ver_doc.get("evidence_document_id")
        if evidence_doc_id:
            evidence_update = {
                "verification_stamp": "verified",
                "verification_stamp_at": now,
                "verification_stamp_by": admin_id,
                "verification_stamp_by_name": admin_name,
                "verification_stamp_label": "Verified",
                "verification_stamp_audit_text": f"VERIFIED by {admin_name}",
                "verification_stamp_badge_color": "green",
                "linked_verification_id": approval.verification_document_id,
                "verification_id": verification_id,
                "updated_at": now
            }
            if stamped_evidence_url:
                evidence_update["stamped_file_url"] = stamped_evidence_url
            
            await db.employee_documents.update_one(
                {"id": evidence_doc_id},
                {"$set": evidence_update}
            )
        
        return {
            "success": True,
            "status": "approved",
            "message": "Verification approved. Document now counts toward compliance.",
            "verification_pdf_url": verification_pdf_url,
            "stamped_evidence_url": stamped_evidence_url,
            "verification_id": verification_id
        }
    else:
        # Reject verification
        await db.verification_documents.update_one(
            {"id": approval.verification_document_id},
            {"$set": {
                "status": "rejected",
                "verification_approved": False,
                "rejected_by": admin_id,
                "rejected_by_name": admin_name,
                "rejected_at": now,
                "rejection_reason": approval.rejection_reason,
                "review_status": "rejected",
                "review_reason": approval.rejection_reason,
                "reviewed_at": now,
                "reviewed_by": admin_id,
                "reviewed_by_name": admin_name,
                "updated_at": now
            }}
        )
        
        return {
            "success": True,
            "status": "rejected",
            "message": "Verification rejected."
        }


@router.post("/request-amendment")
async def request_amendment(
    request: AmendmentRequest,
    current_user: dict = Depends(require_manager_or_admin)
):
    """
    Request employee to amend/re-upload a document.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get the document
    doc = await db.employee_documents.find_one({"id": request.document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": doc["employee_id"]})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    admin_name = current_user.get("email", "Unknown") if current_user else "System"
    admin_id = current_user.get("user_id", "system") if current_user else "system"
    
    # Map reason codes to human-readable messages
    REASON_MESSAGES = {
        "address_mismatch": "The address on the document doesn't match your declared address. Please upload a document with your current address.",
        "document_too_old": "The document is older than 6 months. Please upload a more recent document.",
        "name_mismatch": "The name on the document doesn't match your profile. Please upload a document with your legal name.",
        "unclear": "The document is unclear or unreadable. Please upload a clearer copy.",
        "wrong_type": "The document type is not acceptable. Please upload an appropriate document.",
        "other": request.reason_details or "Please re-upload this document."
    }
    
    reason_message = REASON_MESSAGES.get(request.reason_code, request.reason_details or "Please re-upload this document.")
    
    # Update document status
    await db.employee_documents.update_one(
        {"id": request.document_id},
        {"$set": {
            "status": "amendment_requested",
            "amendment_requested_at": now,
            "amendment_requested_by": admin_id,
            "amendment_requested_by_name": admin_name,
            "amendment_reason_code": request.reason_code,
            "amendment_reason": reason_message,
            "review_status": "amendment_requested",
            "review_reason": reason_message,
            "reviewed_at": now,
            "reviewed_by": admin_id,
            "reviewed_by_name": admin_name,
            "updated_at": now
        }}
    )
    
    # Create amendment request record for tracking
    amendment_record = {
        "id": str(uuid.uuid4()),
        "document_id": request.document_id,
        "employee_id": doc["employee_id"],
        "requirement_id": doc.get("requirement_id"),
        "reason_code": request.reason_code,
        "reason_message": reason_message,
        "requested_by": admin_id,
        "requested_by_name": admin_name,
        "requested_at": now,
        "status": "pending",  # pending, completed, superseded
        "created_at": now
    }
    
    await db.amendment_requests.insert_one(amendment_record)
    
    # TODO: Send email notification to employee
    # This would use Resend integration
    
    return {
        "success": True,
        "amendment_request_id": amendment_record["id"],
        "message": "Amendment requested. Employee will be notified.",
        "reason_sent": reason_message
    }


@router.get("/employee/{employee_id}/status")
async def get_verification_status(employee_id: str):
    """
    Get the verification status for all requirements for an employee.
    Shows both evidence and verification document status.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    requirements = ["right_to_work", "dbs", "identity", "proof_of_address"]
    status_map = {}
    
    for req_id in requirements:
        # Get evidence documents
        evidence_docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": {"$regex": req_id, "$options": "i"},
            "status": {"$ne": "deleted"}
        }, {"_id": 0}).to_list(10)
        
        # Get verification documents
        verification_docs = await db.verification_documents.find({
            "employee_id": employee_id,
            "requirement_id": req_id
        }, {"_id": 0}).to_list(10)
        
        # Get pending amendments
        amendments = await db.amendment_requests.find({
            "employee_id": employee_id,
            "requirement_id": {"$regex": req_id, "$options": "i"},
            "status": "pending"
        }, {"_id": 0}).to_list(10)
        
        # Determine overall status
        has_evidence = len(evidence_docs) > 0
        has_verification = len(verification_docs) > 0
        verification_approved = any(v.get("verification_approved") for v in verification_docs)
        has_pending_amendment = len(amendments) > 0
        
        if verification_approved:
            overall_status = "verified"
        elif has_pending_amendment:
            overall_status = "amendment_requested"
        elif has_verification:
            overall_status = "pending_approval"
        elif has_evidence:
            overall_status = "evidence_uploaded"
        else:
            overall_status = "not_started"
        
        status_map[req_id] = {
            "overall_status": overall_status,
            "has_evidence": has_evidence,
            "has_verification": has_verification,
            "verification_approved": verification_approved,
            "has_pending_amendment": has_pending_amendment,
            "evidence_documents": evidence_docs,
            "verification_documents": verification_docs,
            "pending_amendments": amendments,
            "counts_toward_compliance": verification_approved  # KEY: Only counts if approved
        }
    
    return {
        "employee_id": employee_id,
        "requirements": status_map
    }


@router.post("/reopen/{verification_document_id}")
async def reopen_verification(
    verification_document_id: str,
    reason: str = Form(...),
    current_user: dict = Depends(require_manager_or_admin)
):
    """
    Reopen a previously approved verification for re-review.
    Creates audit trail of why it was reopened.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    ver_doc = await db.verification_documents.find_one({"id": verification_document_id})
    if not ver_doc:
        raise HTTPException(status_code=404, detail="Verification document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    admin_name = current_user.get("email", "Unknown") if current_user else "System"
    admin_id = current_user.get("user_id", "system") if current_user else "system"
    
    # Store the reopen in history
    reopen_record = {
        "reopened_at": now,
        "reopened_by": admin_id,
        "reopened_by_name": admin_name,
        "reason": reason,
        "previous_status": ver_doc.get("status"),
        "was_approved": ver_doc.get("verification_approved", False)
    }
    
    await db.verification_documents.update_one(
        {"id": verification_document_id},
        {
            "$set": {
                "status": "reopened",
                "verification_approved": False,
                "verified": False,
                "review_status": "pending",
                "review_reason": None,
                "reviewed_at": now,
                "reviewed_by": admin_id,
                "reviewed_by_name": admin_name,
                "updated_at": now
            },
            "$push": {
                "reopen_history": reopen_record
            }
        }
    )
    
    # Update employee record
    requirement_id = ver_doc.get("requirement_id")
    await db.employees.update_one(
        {"id": ver_doc["employee_id"]},
        {"$set": {
            f"{requirement_id}_verified": False,
            "updated_at": now
        }}
    )
    
    # Remove stamp from evidence if it was stamped
    evidence_doc_id = ver_doc.get("evidence_document_id")
    if evidence_doc_id:
        await db.employee_documents.update_one(
            {"id": evidence_doc_id},
            {"$unset": {
                "verification_stamp": "",
                "verification_stamp_at": "",
                "verification_stamp_by": "",
                "verification_stamp_by_name": "",
                "verification_stamp_label": "",
                "verification_stamp_audit_text": "",
                "verification_stamp_badge_color": ""
            }}
        )
    
    return {
        "success": True,
        "message": "Verification reopened for re-review.",
        "new_status": "reopened"
    }
