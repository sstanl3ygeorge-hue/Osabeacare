"""
PDF Templates & Exports routes for form PDF generation.

Handles:
- PDF template CRUD operations
- Form submission PDF generation
- PDF downloads and viewing
- PDF field mappings
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    log_audit_action
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["PDF Templates & Exports"])


# ==================== PYDANTIC MODELS ====================

class PDFTemplateResponse(BaseModel):
    """Response model for PDF templates"""
    model_config = ConfigDict(extra="ignore")
    id: str
    form_type: str
    name: str
    version: str
    file_url: Optional[str] = None
    storage_path: Optional[str] = None
    is_active: bool = False
    mapping_config: Optional[Dict[str, Any]] = None
    created_by: str
    created_by_name: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class PDFExportResponse(BaseModel):
    """Response model for generated PDF exports"""
    model_config = ConfigDict(extra="ignore")
    id: str
    submission_id: str
    template_id: Optional[str] = None
    employee_id: str
    employee_name: str
    form_type: str
    file_url: str
    storage_path: str
    created_at: str
    created_by: str


# ==================== LAZY IMPORTS ====================

def get_app_name():
    """Get APP_NAME from server.py"""
    from server import APP_NAME
    return APP_NAME


def get_put_object():
    """Lazy import of put_object from server.py"""
    from server import put_object
    return put_object


def get_get_object():
    """Lazy import of get_object from server.py"""
    from server import get_object
    return get_object


def get_form_based_requirements():
    """Lazy import of FORM_BASED_REQUIREMENTS from server.py"""
    from server import FORM_BASED_REQUIREMENTS
    return FORM_BASED_REQUIREMENTS


def get_pdf_field_mappings():
    """Lazy import of PDF_FIELD_MAPPINGS from server.py"""
    from server import PDF_FIELD_MAPPINGS
    return PDF_FIELD_MAPPINGS


def get_generate_application_form_pdf():
    """Lazy import of generate_application_form_pdf from server.py"""
    from server import generate_application_form_pdf
    return generate_application_form_pdf


def get_generate_staff_health_pdf():
    """Lazy import of generate_staff_health_pdf from server.py"""
    from server import generate_staff_health_pdf
    return generate_staff_health_pdf


# ==================== PDF TEMPLATE ENDPOINTS ====================

@router.get("/pdf-templates")
async def list_pdf_templates(
    form_type: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """List all PDF templates, optionally filtered by form type"""
    db = get_db()
    
    query = {}
    if form_type:
        query["form_type"] = form_type
    
    templates = await db.form_pdf_templates.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return templates


@router.get("/pdf-templates/{template_id}")
async def get_pdf_template(template_id: str, user: dict = Depends(require_admin)):
    """Get a specific PDF template"""
    db = get_db()
    
    template = await db.form_pdf_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")
    return template


@router.post("/pdf-templates", response_model=PDFTemplateResponse)
async def create_pdf_template(
    form_type: str = Form(...),
    name: str = Form(...),
    version: str = Form("1.0"),
    file: UploadFile = File(...),
    user: dict = Depends(require_admin)
):
    """
    Upload a new PDF template for a form type.
    The template PDF is stored in object storage and can be used for reference.
    """
    db = get_db()
    put_object = get_put_object()
    APP_NAME = get_app_name()
    FORM_BASED_REQUIREMENTS = get_form_based_requirements()
    PDF_FIELD_MAPPINGS = get_pdf_field_mappings()
    
    template_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Validate form type exists
    if form_type not in FORM_BASED_REQUIREMENTS and form_type not in PDF_FIELD_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown form type: {form_type}")
    
    # Upload file to storage
    content = await file.read()
    storage_path = f"{APP_NAME}/pdf-templates/{form_type}/{template_id}_{file.filename}"
    content_type = file.content_type or "application/pdf"
    
    result = put_object(storage_path, content, content_type)
    
    # Get default mapping for this form type
    default_mapping = PDF_FIELD_MAPPINGS.get(form_type, {})
    
    template_doc = {
        "id": template_id,
        "form_type": form_type,
        "name": name,
        "version": version,
        "file_url": result.get("path"),
        "storage_path": storage_path,
        "original_filename": file.filename,
        "is_active": False,  # Not active by default
        "mapping_config": default_mapping,
        "created_by": user['user_id'],
        "created_by_name": user.get('name', 'Unknown'),
        "created_at": now,
        "updated_at": now
    }
    
    await db.form_pdf_templates.insert_one(template_doc)
    
    await log_audit_action(user['user_id'], "pdf_template_created", "pdf_template", template_id, {
        "form_type": form_type,
        "name": name,
        "version": version
    })
    
    return {**template_doc, "_id": None}


@router.put("/pdf-templates/{template_id}/activate")
async def activate_pdf_template(template_id: str, user: dict = Depends(require_admin)):
    """Mark a PDF template as active (deactivates other templates for the same form type)"""
    db = get_db()
    
    template = await db.form_pdf_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")
    
    form_type = template["form_type"]
    now = datetime.now(timezone.utc).isoformat()
    
    # Deactivate all other templates for this form type
    await db.form_pdf_templates.update_many(
        {"form_type": form_type, "id": {"$ne": template_id}},
        {"$set": {"is_active": False, "updated_at": now}}
    )
    
    # Activate this template
    await db.form_pdf_templates.update_one(
        {"id": template_id},
        {"$set": {"is_active": True, "updated_at": now}}
    )
    
    await log_audit_action(user['user_id'], "pdf_template_activated", "pdf_template", template_id, {
        "form_type": form_type
    })
    
    return {"success": True, "message": f"Template activated for {form_type}"}


@router.delete("/pdf-templates/{template_id}")
async def delete_pdf_template(template_id: str, user: dict = Depends(require_admin)):
    """Delete a PDF template"""
    db = get_db()
    
    template = await db.form_pdf_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")
    
    await db.form_pdf_templates.delete_one({"id": template_id})
    
    await log_audit_action(user['user_id'], "pdf_template_deleted", "pdf_template", template_id, {
        "form_type": template["form_type"],
        "name": template["name"]
    })
    
    return {"success": True, "message": "Template deleted"}


# ==================== PDF GENERATION ENDPOINTS ====================

@router.post("/form-submissions/{submission_id}/generate-pdf")
async def generate_form_pdf(submission_id: str, user: dict = Depends(require_admin)):
    """
    Generate a completed PDF from a form submission.
    
    This endpoint:
    1. Loads structured data from form_submissions (source of truth)
    2. Loads active template config for the form type (if any)
    3. Renders a completed PDF using the template layout + structured data
    4. Saves the generated PDF as an export artifact
    5. Returns the PDF file URL
    
    The PDF is purely an export artifact - form_submissions remains the source of truth.
    """
    db = get_db()
    put_object = get_put_object()
    APP_NAME = get_app_name()
    PDF_FIELD_MAPPINGS = get_pdf_field_mappings()
    generate_application_form_pdf = get_generate_application_form_pdf()
    generate_staff_health_pdf = get_generate_staff_health_pdf()
    
    # Get the form submission
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    # Get form_type - application forms may use requirement_id instead
    form_type = submission.get("form_type") or submission.get("requirement_id")
    employee_id = submission.get("employee_id")
    
    # Get employee data
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get active template for this form type (if any)
    active_template = await db.form_pdf_templates.find_one({
        "form_type": form_type,
        "is_active": True
    })
    
    # Get mapping config - use template's config if available, otherwise use default
    mapping_config = None
    if active_template and active_template.get("mapping_config"):
        mapping_config = active_template["mapping_config"]
    elif form_type in PDF_FIELD_MAPPINGS:
        mapping_config = PDF_FIELD_MAPPINGS[form_type]
    
    # Application forms have their own dedicated generator - no mapping required
    if form_type != "application_form" and not mapping_config:
        raise HTTPException(status_code=400, detail=f"No PDF mapping configured for form type: {form_type}")
    
    # Prepare submission data with metadata
    submission_data = submission.get("data", {}) or submission.get("form_data", {})
    submission_data["_submitted_at"] = submission.get("submitted_at", "")
    submission_data["_verified"] = submission.get("verified", False)
    submission_data["_status"] = submission.get("status", "submitted")
    
    # Generate PDF based on form type
    if form_type == "application_form":
        pdf_bytes = await generate_application_form_pdf(submission_data, employee)
    elif form_type == "staff_health_questionnaire":
        pdf_bytes = await generate_staff_health_pdf(submission_data, employee, mapping_config)
    else:
        # Generic PDF generation for other form types (can be extended)
        raise HTTPException(status_code=400, detail=f"PDF generation not yet implemented for form type: {form_type}")
    
    # Save generated PDF to storage
    export_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    employee_name = f"{employee.get('first_name', '')}_{employee.get('last_name', '')}".replace(' ', '_')
    filename = f"{form_type}_{employee_name}_{timestamp}.pdf"
    storage_path = f"{APP_NAME}/pdf-exports/{form_type}/{export_id}_{filename}"
    
    result = put_object(storage_path, pdf_bytes, "application/pdf")
    
    # Save export record
    export_doc = {
        "id": export_id,
        "submission_id": submission_id,
        "template_id": active_template["id"] if active_template else None,
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
        "employee_code": employee.get("employee_code", ""),
        "form_type": form_type,
        "file_url": result.get("path"),
        "storage_path": storage_path,
        "filename": filename,
        "created_at": now,
        "created_by": user['user_id'],
        "created_by_name": user.get('name', 'Unknown')
    }
    
    await db.form_pdf_exports.insert_one(export_doc)
    
    await log_audit_action(user['user_id'], "pdf_generated", "form_submission", submission_id, {
        "export_id": export_id,
        "form_type": form_type,
        "employee_id": employee_id
    })
    
    return {
        "success": True,
        "export_id": export_id,
        "file_url": result.get("path"),
        "filename": filename,
        "message": "PDF generated successfully"
    }


@router.get("/form-submissions/{submission_id}/download-pdf")
async def download_form_pdf(submission_id: str, user: dict = Depends(get_current_user)):
    """
    Download the most recent PDF export for a form submission.
    Returns the actual PDF file bytes for download.
    If no export exists and user is admin, generates one on-the-fly.
    """
    db = get_db()
    get_object = get_get_object()
    
    # Check for existing export
    export = await db.form_pdf_exports.find_one(
        {"submission_id": submission_id},
        sort=[("created_at", -1)]
    )
    
    if export and export.get("file_url"):
        # Retrieve and return the actual PDF file
        file_path = export.get("file_url")
        filename = export.get("filename", "form.pdf")
        
        try:
            content, content_type = get_object(file_path)
            safe_filename = filename.replace('"', '\\"')
            
            return Response(
                content=content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_filename}"',
                    "Cache-Control": "private, max-age=3600"
                }
            )
        except Exception as e:
            # File exists in DB but not in storage - mark as corrupted
            logger.error(f"PDF file retrieval failed for export {export.get('id')}: {e}")
            await log_audit_action(
                user['user_id'], "file_retrieval_failed", "form_pdf_export", export.get('id'),
                {"file_path": file_path, "error": str(e), "submission_id": submission_id}
            )
            raise HTTPException(
                status_code=500, 
                detail="PDF file not found in storage. Record may be corrupted. Please regenerate the PDF."
            )
    
    # No export exists - generate one (requires admin)
    # For non-admins, return error
    if user.get('role') not in ['admin', 'super_admin']:
        raise HTTPException(status_code=404, detail="No PDF export found. Admin can generate one.")
    
    # Generate PDF on-the-fly and return the file bytes directly
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    # Generate the PDF (this also saves to storage)
    result = await generate_form_pdf(submission_id, user)
    
    # Now retrieve and return the generated file
    file_path = result.get("file_url")
    filename = result.get("filename", "form.pdf")
    
    try:
        content, content_type = get_object(file_path)
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to retrieve newly generated PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve generated PDF")


@router.get("/form-submissions/{submission_id}/view-pdf")
async def view_form_pdf(submission_id: str, user: dict = Depends(get_current_user)):
    """
    View the most recent PDF export for a form submission inline.
    Returns the actual PDF file for browser viewing (not download).
    """
    db = get_db()
    get_object = get_get_object()
    
    # Check for existing export
    export = await db.form_pdf_exports.find_one(
        {"submission_id": submission_id},
        sort=[("created_at", -1)]
    )
    
    if not export or not export.get("file_url"):
        raise HTTPException(status_code=404, detail="No PDF export found for this submission")
    
    file_path = export.get("file_url")
    filename = export.get("filename", "form.pdf")
    
    try:
        content, content_type = get_object(file_path)
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        # File exists in DB but not in storage
        logger.error(f"PDF file retrieval failed for viewing: {e}")
        await log_audit_action(
            user['user_id'], "file_retrieval_failed", "form_pdf_export", export.get('id'),
            {"file_path": file_path, "error": str(e), "action": "view"}
        )
        raise HTTPException(
            status_code=500, 
            detail="PDF file not found in storage. Record may be corrupted."
        )


@router.get("/pdf-exports")
async def list_pdf_exports(
    form_type: Optional[str] = None,
    employee_id: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """List PDF exports with optional filters"""
    db = get_db()
    
    query = {}
    if form_type:
        query["form_type"] = form_type
    if employee_id:
        query["employee_id"] = employee_id
    
    exports = await db.form_pdf_exports.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return exports


@router.get("/pdf-field-mappings/{form_type}")
async def get_pdf_field_mapping(form_type: str, user: dict = Depends(require_admin)):
    """Get the field mapping configuration for a form type"""
    PDF_FIELD_MAPPINGS = get_pdf_field_mappings()
    
    if form_type not in PDF_FIELD_MAPPINGS:
        raise HTTPException(status_code=404, detail=f"No field mapping found for form type: {form_type}")
    
    return PDF_FIELD_MAPPINGS[form_type]
