"""
Public Document Upload Routes - Email link upload flow.

This module handles:
- Validating upload tokens from email links
- Public document upload (no auth required)
- Debug endpoint for checking uploaded documents
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Form, File, UploadFile
import logging

from .dependencies import get_db

router = APIRouter(tags=["Public Upload"])

logger = logging.getLogger(__name__)

# Human-readable requirement names mapping
REQUIREMENT_DISPLAY_NAMES = {
    "right_to_work": "Right to Work",
    "dbs_certificate": "DBS Certificate",
    "dbs": "DBS Certificate",
    "identity": "Photo ID / Identity Document",
    "proof_of_address": "Proof of Address",
    "cv": "CV / Resume",
    "passport": "Passport",
    "driving_licence": "Driving Licence",
    "training_certificate": "Training Certificate",
    "qualification": "Qualification Certificate",
    "reference_1": "Reference 1",
    "reference_2": "Reference 2",
}


@router.get("/public/validate-upload-token")
async def validate_upload_token(
    token: str, 
    request_id: Optional[str] = None,
    requirement: Optional[str] = None
):
    """
    PUBLIC endpoint - Validate a document upload token from email link.
    No authentication required.
    
    Returns:
    - person name (employee/applicant)
    - requirement being requested
    - token expiry status
    - allowed file types
    """
    # Import lazily to avoid circular imports
    from server import EmailRequestService
    
    db = get_db()
    
    try:
        result = await EmailRequestService.validate_and_use_token(token, request_id)
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    if result.get("status") not in ["valid", "valid_no_request"]:
        raise HTTPException(status_code=400, detail=result.get("reason", "Invalid or expired token"))
    
    request_data = result.get("request")
    token_data = result.get("token_data", {})
    
    # Extract data from request or token
    if request_data:
        person_id = getattr(request_data, 'person_id', None)
        person_type = getattr(request_data, 'person_type', 'employee')
        requirement_id = getattr(request_data, 'requirement_id', None)
        request_id_val = getattr(request_data, 'id', None)
        action_type = getattr(request_data, 'request_type', None)
        if hasattr(action_type, 'value'):
            action_type = action_type.value
    else:
        person_id = token_data.get("person_id")
        person_type = token_data.get("person_type", "employee")
        requirement_id = token_data.get("requirement_id")
        request_id_val = request_id
        action_type = token_data.get("action_type")
    
    # Use requirement from query param if not in token/request (fallback)
    if not requirement_id and requirement:
        requirement_id = requirement
    
    # Get person details
    person = await db.employees.find_one({"id": person_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    person_name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
    
    # Get requirement display name
    requirement_name = REQUIREMENT_DISPLAY_NAMES.get(
        requirement_id, 
        requirement_id.replace("_", " ").title() if requirement_id else "Document"
    )
    
    # Determine allowed file types based on requirement
    if requirement_id in ["cv", "resume"]:
        allowed_types = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        allowed_extensions = [".pdf", ".doc", ".docx"]
    else:
        allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/webp"]
        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    
    return {
        "status": "valid",
        "request_id": request_id_val,
        "person_id": person_id,
        "person_type": person_type,
        "person_name": person_name,
        "requirement_id": requirement_id,
        "requirement_name": requirement_name,
        "allowed_file_types": allowed_types,
        "allowed_extensions": allowed_extensions,
        "max_file_size_mb": 10,
        "instructions": f"Please upload your {requirement_name}. Accepted formats: {', '.join(allowed_extensions)}"
    }


@router.post("/public/upload-document")
async def public_upload_document(
    token: str = Form(...),
    request_id: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """
    PUBLIC endpoint - Upload a document using a secure token from email link.
    No authentication required.
    
    This endpoint:
    1. Validates the token
    2. Uploads the file to storage
    3. Creates the document record linked to the person
    4. Marks the email request as submitted
    """
    # Import lazily to avoid circular imports
    from server import EmailRequestService, put_object, APP_NAME
    
    db = get_db()
    
    # Validate token first
    try:
        result = await EmailRequestService.validate_and_use_token(token, request_id)
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    if result.get("status") not in ["valid", "valid_no_request"]:
        raise HTTPException(status_code=400, detail=result.get("reason", "Invalid or expired token"))
    
    request_data = result.get("request")
    token_data = result.get("token_data", {})
    
    # Extract data
    if request_data:
        person_id = getattr(request_data, 'person_id', None)
        person_type = getattr(request_data, 'person_type', 'employee')
        requirement_id = getattr(request_data, 'requirement_id', None)
        request_id_val = getattr(request_data, 'id', None)
    else:
        person_id = token_data.get("person_id")
        requirement_id = token_data.get("requirement_id")
        request_id_val = request_id
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file size (max 10MB)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    # Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx"]
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Accepted: {', '.join(allowed_extensions)}")
    
    # Get person details
    person = await db.employees.find_one({"id": person_id}, {"_id": 0})
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Upload file to storage
    try:
        person_name_safe = f"{person.get('first_name', 'unknown')}{person.get('last_name', '')}".replace(" ", "")
        timestamp = datetime.now(timezone.utc).strftime('%d-%m-%Y_%H%M%S')
        safe_filename = f"{person_name_safe}_{requirement_id}_{timestamp}{file_ext}"
        storage_path = f"{APP_NAME}/documents/{person_id}/{requirement_id}/{safe_filename}"
        
        logger.info(f"Public upload: Uploading file to storage path: {storage_path}")
        
        put_object(storage_path, file_content, file.content_type or "application/octet-stream")
        file_url = storage_path
        
        logger.info(f"Public upload: File uploaded successfully to {storage_path}")
    except Exception as e:
        logger.error(f"Public upload: File storage failed - {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    # Get requirement name and config
    req_name = REQUIREMENT_DISPLAY_NAMES.get(
        requirement_id, 
        requirement_id.replace("_", " ").title() if requirement_id else "Document"
    )
    
    # Create document record
    document_id = str(uuid.uuid4())
    document_record = {
        "id": document_id,
        "employee_id": person_id,
        "document_type_id": requirement_id,
        "document_type_name": req_name,
        "category": "C_Compliance",
        "requirement_id": requirement_id,
        "requirement_name": req_name,
        "document_label": file.filename,
        "file_url": file_url,
        "original_filename": file.filename,
        "status": "uploaded",
        "uploaded_by": None,
        "uploaded_by_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
        "uploaded_at": now,
        "reviewed_by": None,
        "reviewed_at": None,
        "expiry_date": None,
        "version_number": 1,
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source_type": "email_upload_link",
        "email_request_id": request_id_val,
        "notes": f"Uploaded via email link by {person.get('first_name', '')} {person.get('last_name', '')}",
        "created_at": now,
        "updated_at": now
    }
    
    logger.info(f"PUBLIC_UPLOAD_DIAGNOSTIC: Inserting document record: document_id={document_id}")
    
    await db.employee_documents.insert_one(document_record)
    
    # Link submission to email request
    if request_id_val:
        try:
            await EmailRequestService.link_submission(
                request_id=request_id_val,
                submission_id=document_id,
                submission_type="document_upload"
            )
            
            await db.email_requests.update_one(
                {"id": request_id_val},
                {"$set": {"status": "submitted", "resolved_at": now}}
            )
        except Exception as e:
            logger.warning(f"Failed to link submission to request: {e}")
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": None,
        "user_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
        "action": "public_document_upload",
        "entity_type": "employee_document",
        "entity_id": document_id,
        "created_at": now,
        "metadata": {
            "employee_id": person_id,
            "requirement_id": requirement_id,
            "requirement_name": req_name,
            "file_name": file.filename,
            "source": "email_upload_link",
            "request_id": request_id_val
        }
    })
    
    logger.info(f"Public document upload complete: {req_name} for {person_id} via email link")
    
    return {
        "status": "success",
        "message": f"Your {req_name} has been uploaded successfully. It will be reviewed by the team.",
        "document_id": document_id,
        "requirement": req_name,
        "next_steps": [
            "Your document has been received",
            "Our team will verify it within 2-3 working days",
            "You will be notified once verification is complete"
        ]
    }


@router.get("/public/debug-documents/{person_id}")
async def debug_person_documents(person_id: str):
    """
    PUBLIC DEBUG endpoint - Check what documents exist for a person.
    Used to verify public uploads are being stored correctly.
    
    This endpoint is for debugging only and should be disabled in final production.
    """
    db = get_db()
    
    # Get person details
    person = await db.employees.find_one({"id": person_id}, {"_id": 0, "first_name": 1, "last_name": 1, "person_stage": 1, "applicant_reference": 1})
    if not person:
        return {"status": "error", "message": "Person not found", "person_id": person_id}
    
    # Get all documents for this person
    all_docs = await db.employee_documents.find(
        {"employee_id": person_id},
        {"_id": 0, "id": 1, "requirement_id": 1, "document_type_id": 1, "status": 1, "source_type": 1, "file_url": 1, "uploaded_at": 1, "original_filename": 1}
    ).to_list(100)
    
    # Group by requirement_id
    by_requirement = {}
    for doc in all_docs:
        req_id = doc.get("requirement_id", "NO_REQ_ID")
        if req_id not in by_requirement:
            by_requirement[req_id] = []
        by_requirement[req_id].append(doc)
    
    # Check specifically for public uploads
    public_uploads = [d for d in all_docs if d.get("source_type") == "email_upload_link"]
    
    return {
        "status": "success",
        "person_id": person_id,
        "person_name": f"{person.get('first_name', '')} {person.get('last_name', '')}",
        "person_stage": person.get("person_stage"),
        "applicant_reference": person.get("applicant_reference"),
        "total_documents": len(all_docs),
        "public_upload_documents": len(public_uploads),
        "documents_by_requirement": {
            req_id: [
                {
                    "id": d.get("id"),
                    "status": d.get("status"),
                    "source_type": d.get("source_type"),
                    "file_url": bool(d.get("file_url")),
                    "uploaded_at": d.get("uploaded_at"),
                    "filename": d.get("original_filename")
                }
                for d in docs
            ]
            for req_id, docs in by_requirement.items()
        },
        "public_uploads": [
            {
                "id": d.get("id"),
                "requirement_id": d.get("requirement_id"),
                "status": d.get("status"),
                "uploaded_at": d.get("uploaded_at"),
                "filename": d.get("original_filename")
            }
            for d in public_uploads
        ]
    }
