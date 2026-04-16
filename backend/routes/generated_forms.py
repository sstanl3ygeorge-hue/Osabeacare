"""
Generated Forms routes for form generation, management, and submission.

Handles:
- Form CRUD operations (create, read, update)
- Form PDF generation and document saving
- Form sending to employees
- Form signoff and archiving
- Bulk form generation
- Application and document imports
- Public form access via token
"""

import os
import io
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from pydantic import BaseModel, ConfigDict

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
    SENDER_EMAIL
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["Generated Forms"])


# ==================== STATUS CLASS ====================
class FormStatus:
    DRAFT = "draft"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    SIGNED_OFF = "signed_off"
    ARCHIVED = "archived"


# ==================== PYDANTIC MODELS ====================

class GeneratedFormCreate(BaseModel):
    template_id: str
    employee_id: str
    form_data: Dict[str, Any] = {}


class GeneratedFormUpdate(BaseModel):
    form_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    employee_signature: Optional[str] = None
    employee_signed_at: Optional[str] = None
    admin_signature: Optional[str] = None
    admin_signed_at: Optional[str] = None
    notes: Optional[str] = None


class GeneratedFormResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    template_id: str
    template_name: Optional[str] = None
    template_category: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    form_data: Dict[str, Any] = {}
    status: str
    employee_signature: Optional[str] = None
    employee_signed_at: Optional[str] = None
    admin_signature: Optional[str] = None
    admin_signed_at: Optional[str] = None
    admin_signoff_by: Optional[str] = None
    pdf_url: Optional[str] = None
    locked: bool = False
    notes: Optional[str] = None
    version: int = 1
    access_token: Optional[str] = None
    created_at: str
    updated_at: str
    sent_at: Optional[str] = None
    viewed_at: Optional[str] = None
    completed_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    signed_off_at: Optional[str] = None
    requirement_id: Optional[str] = None


# Form type to requirement mapping for imports
FORM_TYPE_TO_REQUIREMENT = {
    "reference": {"requirement_id": None, "category": "H_References"},
    "reference_1": {"requirement_id": "reference_1", "category": "H_References"},
    "reference_2": {"requirement_id": "reference_2", "category": "H_References"},
    "health_screening": {"requirement_id": "health_screening", "category": "F_Health_Screening"},
    "contract": {"requirement_id": "contract", "category": "L_Contract"},
    "induction": {"requirement_id": "induction", "category": "J_Induction_Shadowing_Observations"},
    "handbook": {"requirement_id": "handbook", "category": "O_Other"},
    "recruitment_checklist": {"requirement_id": "recruitment_checklist", "category": "B_Recruitment_Checklist"},
    "personal_info": {"requirement_id": "personal_info", "category": "C_Personal_Information"},
    "interview_record": {"requirement_id": "interview_record", "category": "D_Interview"},
    "equal_opportunities": {"requirement_id": "equal_opportunities", "category": "E_Equal_Opportunities"},
    "application_form": {"requirement_id": "application_form", "category": "A_Application_Form"},
}


# ==================== LAZY IMPORTS ====================

def get_resend():
    """Lazy import of resend module"""
    import resend
    return resend


def get_put_object():
    """Lazy import of put_object from server.py"""
    from server import put_object
    return put_object


def get_document_status():
    """Lazy import of DocumentStatus from server.py"""
    from server import DocumentStatus
    return DocumentStatus


def get_auto_fill_employee_data():
    """Lazy import of auto_fill_employee_data from server.py"""
    from server import auto_fill_employee_data
    return auto_fill_employee_data


def get_auto_generate_form_pdf():
    """Lazy import of auto_generate_form_pdf from server.py"""
    from server import auto_generate_form_pdf
    return auto_generate_form_pdf


def get_folder_for_form_func():
    """Lazy import of get_folder_for_form from server.py"""
    from server import get_folder_for_form
    return get_folder_for_form


def get_generate_document_filename_func():
    """Lazy import of generate_document_filename from server.py"""
    from server import generate_document_filename
    return generate_document_filename


# ==================== FORM ENDPOINTS ====================

@router.post("/generated-forms/{form_id}/regenerate-pdf")
async def regenerate_form_pdf(form_id: str, user: dict = Depends(require_manager_or_admin)):
    """
    Force regenerate PDF for a completed form.
    Use this when a form is completed but has no PDF evidence.
    """
    db = get_db()
    auto_generate_form_pdf = get_auto_generate_form_pdf()
    
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    if form['status'] not in ['completed', 'completed_imported', 'signed_off', 'reviewed']:
        raise HTTPException(status_code=400, detail="Form must be in completed status to generate PDF")
    
    # Clear existing pdf_url to force regeneration
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$unset": {"pdf_url": ""}}
    )
    
    await auto_generate_form_pdf(form_id, user)
    
    updated_form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    
    return {
        "success": True,
        "message": "PDF regenerated successfully",
        "pdf_url": updated_form.get('pdf_url'),
        "document_id": updated_form.get('saved_as_document_id')
    }


@router.post("/generated-forms", response_model=GeneratedFormResponse)
async def create_generated_form(form: GeneratedFormCreate, user: dict = Depends(require_manager_or_admin)):
    db = get_db()
    auto_fill_employee_data = get_auto_fill_employee_data()
    
    form_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get template
    template = await db.templates.find_one({"id": form.template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": form.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Auto-fill employee data
    auto_filled = await auto_fill_employee_data(form.employee_id)
    merged_data = {**auto_filled, **form.form_data}
    
    # Generate access token for employee/external access
    access_token = str(uuid.uuid4())
    
    form_doc = {
        "id": form_id,
        "template_id": form.template_id,
        "template_name": template['name'],
        "template_category": template['category'],
        "employee_id": form.employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee.get('employee_code') or employee.get('applicant_reference') or '',
        "form_data": merged_data,
        "status": FormStatus.DRAFT,
        "employee_signature": None,
        "employee_signed_at": None,
        "admin_signature": None,
        "admin_signed_at": None,
        "admin_signoff_by": None,
        "pdf_url": None,
        "locked": False,
        "notes": None,
        "version": 1,
        "access_token": access_token,
        "created_at": now,
        "updated_at": now,
        "created_by": user['user_id'],
        "sent_at": None,
        "viewed_at": None,
        "completed_at": None,
        "reviewed_at": None,
        "signed_off_at": None
    }
    await db.generated_forms.insert_one(form_doc)
    
    await log_audit_action(user['user_id'], "create_form", "generated_form", form_id, {
        "template_name": template['name'],
        "employee_id": form.employee_id
    })
    
    return GeneratedFormResponse(**form_doc)


@router.get("/generated-forms", response_model=List[GeneratedFormResponse])
async def get_generated_forms(
    employee_id: Optional[str] = None,
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    db = get_db()
    
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if template_id:
        query["template_id"] = template_id
    if status:
        query["status"] = status
    
    forms = await db.generated_forms.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [GeneratedFormResponse(**f) for f in forms]


@router.get("/generated-forms/{form_id}", response_model=GeneratedFormResponse)
async def get_generated_form(form_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return GeneratedFormResponse(**form)


# Public access endpoint for employees to complete forms via access token
@router.get("/forms/access/{access_token}")
async def get_form_by_token(access_token: str):
    db = get_db()
    
    form = await db.generated_forms.find_one({"access_token": access_token}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or link expired")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is locked and cannot be edited")
    
    # Mark as viewed if not already
    if not form.get('viewed_at'):
        await db.generated_forms.update_one(
            {"id": form['id']},
            {"$set": {"viewed_at": datetime.now(timezone.utc).isoformat()}}
        )
        await log_audit_action("system", "form_viewed", "generated_form", form['id'], {"access_type": "token"})
    
    # Get template for form fields
    template = await db.templates.find_one({"id": form['template_id']}, {"_id": 0})
    
    return {
        "form": GeneratedFormResponse(**form),
        "template": template
    }


@router.put("/forms/access/{access_token}/submit")
async def submit_form_by_token(access_token: str, data: dict):
    db = get_db()
    
    form = await db.generated_forms.find_one({"access_token": access_token}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or link expired")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is locked and cannot be edited")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "form_data": {**form['form_data'], **data.get('form_data', {})},
        "status": FormStatus.COMPLETED,
        "completed_at": now,
        "updated_at": now
    }
    
    # Handle employee signature
    if data.get('employee_signature'):
        update_data['employee_signature'] = data['employee_signature']
        update_data['employee_signed_at'] = now
    
    await db.generated_forms.update_one({"id": form['id']}, {"$set": update_data})
    
    await log_audit_action("employee", "form_completed", "generated_form", form['id'], {"access_type": "token"})
    
    return {"message": "Form submitted successfully"}


@router.put("/generated-forms/{form_id}", response_model=GeneratedFormResponse)
async def update_generated_form(form_id: str, update: GeneratedFormUpdate, user: dict = Depends(require_manager_or_admin)):
    db = get_db()
    auto_generate_form_pdf = get_auto_generate_form_pdf()
    
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is locked and cannot be edited")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = now
    
    # Track if we're completing the form (need to auto-generate PDF)
    should_generate_pdf = False
    
    # Track status changes
    if update.status:
        if update.status == FormStatus.SENT and not form.get('sent_at'):
            update_data['sent_at'] = now
        elif update.status == FormStatus.COMPLETED and not form.get('completed_at'):
            update_data['completed_at'] = now
            should_generate_pdf = True
        elif update.status == FormStatus.REVIEWED and not form.get('reviewed_at'):
            update_data['reviewed_at'] = now
        elif update.status == FormStatus.SIGNED_OFF and not form.get('signed_off_at'):
            update_data['signed_off_at'] = now
            update_data['admin_signoff_by'] = user['user_id']
            should_generate_pdf = True
    
    await db.generated_forms.update_one({"id": form_id}, {"$set": update_data})
    
    # Auto-generate PDF evidence on completion
    if should_generate_pdf and not form.get('pdf_url'):
        try:
            await auto_generate_form_pdf(form_id, user)
        except Exception as e:
            logger.error(f"Failed to auto-generate PDF for form {form_id}: {e}")
    
    await log_audit_action(user['user_id'], "update_form", "generated_form", form_id, {"status": update.status})
    
    updated_form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    return GeneratedFormResponse(**updated_form)


@router.post("/generated-forms/{form_id}/send")
async def send_form_to_employee(form_id: str, send_email: bool = True, user: dict = Depends(require_manager_or_admin)):
    db = get_db()
    resend = get_resend()
    
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    employee = await db.employees.find_one({"id": form['employee_id']}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update status
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {"status": FormStatus.SENT, "sent_at": now, "updated_at": now}}
    )
    
    # Generate access link
    access_link = f"{os.environ.get('FRONTEND_URL', '')}/form/{form['access_token']}"
    
    # Send email if configured
    if send_email and resend.api_key:
        try:
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [employee['email']],
                "subject": f"Form to complete: {form['template_name']}",
                "html": f"""
                <h2>Form Request from Osabea Healthcare Solutions</h2>
                <p>Dear {employee['first_name']},</p>
                <p>Please complete the following form:</p>
                <p><strong>{form['template_name']}</strong></p>
                <p><a href="{access_link}" style="display: inline-block; padding: 12px 24px; background-color: #0F5C5E; color: white; text-decoration: none; border-radius: 8px;">Complete Form</a></p>
                <p>Or copy this link: {access_link}</p>
                <p>Thank you,<br>Osabea Healthcare Solutions Team</p>
                """
            })
        except Exception as e:
            logger.error(f"Failed to send form email: {e}")
    
    await log_audit_action(user['user_id'], "send_form", "generated_form", form_id, {"employee_email": employee['email']})
    
    return {"message": "Form sent", "access_link": access_link}


@router.post("/generated-forms/{form_id}/signoff")
async def signoff_form(form_id: str, admin_signature: str, notes: Optional[str] = None, user: dict = Depends(require_admin)):
    db = get_db()
    DocumentStatus = get_document_status()
    
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is already signed off and locked")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "status": FormStatus.SIGNED_OFF,
        "admin_signature": admin_signature,
        "admin_signed_at": now,
        "admin_signoff_by": user['user_id'],
        "signed_off_at": now,
        "locked": True,
        "updated_at": now
    }
    if notes:
        update_data['notes'] = notes
    
    await db.generated_forms.update_one({"id": form_id}, {"$set": update_data})
    
    # Link to employee document if template is linked
    template = await db.templates.find_one({"id": form['template_id']}, {"_id": 0})
    if template and template.get('linked_document_type_id'):
        existing_doc = await db.employee_documents.find_one({
            "employee_id": form['employee_id'],
            "document_type_id": template['linked_document_type_id']
        })
        
        if existing_doc:
            await db.employee_documents.update_one(
                {"id": existing_doc['id']},
                {"$set": {
                    "status": DocumentStatus.APPROVED,
                    "reviewed_by": user['user_id'],
                    "reviewed_at": now,
                    "notes": f"Signed off via generated form: {form_id}"
                }}
            )
        else:
            doc_id = str(uuid.uuid4())
            doc_type = await db.document_types.find_one({"id": template['linked_document_type_id']}, {"_id": 0})
            await db.employee_documents.insert_one({
                "id": doc_id,
                "employee_id": form['employee_id'],
                "document_type_id": template['linked_document_type_id'],
                "document_type_name": doc_type['name'] if doc_type else template['name'],
                "category": doc_type['category'] if doc_type else template['category'],
                "file_url": None,
                "original_filename": f"{template['name']} - Signed Form",
                "status": DocumentStatus.APPROVED,
                "uploaded_by": user['user_id'],
                "uploaded_at": now,
                "reviewed_by": user['user_id'],
                "reviewed_at": now,
                "expiry_date": None,
                "notes": f"Generated form signed off: {form_id}",
                "version_number": 1,
                "generated_form_id": form_id,
                "created_at": now
            })
    
    await log_audit_action(user['user_id'], "signoff_form", "generated_form", form_id, {"locked": True})
    
    updated_form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    return GeneratedFormResponse(**updated_form)


@router.post("/generated-forms/{form_id}/save-as-document")
async def save_form_as_document(form_id: str, user: dict = Depends(require_manager_or_admin)):
    """Convert a completed form to a PDF document and save to employee's folder"""
    db = get_db()
    put_object = get_put_object()
    DocumentStatus = get_document_status()
    get_folder_for_form = get_folder_for_form_func()
    generate_document_filename = get_generate_document_filename_func()
    
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    employee = await db.employees.find_one({"id": form['employee_id']}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    template = await db.templates.find_one({"id": form['template_id']}, {"_id": 0})
    template_name = form.get('template_name') or (template['name'] if template else 'Form')
    
    folder = get_folder_for_form(template_name)
    employee_name = f"{employee['first_name']} {employee['last_name']}"
    filename = generate_document_filename(employee_name, template_name)
    
    # Generate PDF using ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('FormTitle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=20)
    elements.append(Paragraph(template_name, title_style))
    
    # Employee info
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=10, spaceAfter=5)
    elements.append(Paragraph(f"<b>Employee:</b> {employee_name} ({employee.get('employee_code') or employee.get('applicant_reference') or 'N/A'})", info_style))
    elements.append(Paragraph(f"<b>Role:</b> {employee.get('role', 'N/A')}", info_style))
    elements.append(Paragraph(f"<b>Date:</b> {datetime.now(timezone.utc).strftime('%d/%m/%Y')}", info_style))
    elements.append(Spacer(1, 20))
    
    # Form data
    form_data = form.get('form_data', {})
    if form_data:
        elements.append(Paragraph("<b>Form Data</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        table_data = [['Field', 'Value']]
        for key, value in form_data.items():
            if value:
                display_key = key.replace('_', ' ').title()
                display_value = str(value)[:100]
                table_data.append([display_key, display_value])
        
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[200, 300])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004D4D')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFA')]),
            ]))
            elements.append(table)
    
    elements.append(Spacer(1, 30))
    
    # Signatures section
    if form.get('employee_signature') or form.get('admin_signature'):
        elements.append(Paragraph("<b>Signatures</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        if form.get('employee_signature'):
            elements.append(Paragraph(f"Employee Signature: {form['employee_signature']}", info_style))
            if form.get('employee_signed_at'):
                elements.append(Paragraph(f"Signed: {form['employee_signed_at'][:10]}", info_style))
        
        if form.get('admin_signature'):
            elements.append(Paragraph(f"Admin Signature: {form['admin_signature']}", info_style))
            if form.get('admin_signed_at'):
                elements.append(Paragraph(f"Signed: {form['admin_signed_at'][:10]}", info_style))
    
    # Status footer
    elements.append(Spacer(1, 30))
    status_text = f"Status: {form.get('status', 'Unknown').upper()}"
    if form.get('locked'):
        status_text += " (LOCKED)"
    elements.append(Paragraph(f"<i>{status_text}</i>", info_style))
    elements.append(Paragraph(f"<i>Generated: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}</i>", info_style))
    
    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Upload PDF to storage
    now = datetime.now(timezone.utc).isoformat()
    file_path = f"osabea-care/documents/{employee['id']}/{folder}/{filename}"
    put_object(file_path, pdf_content, "application/pdf")
    
    # Find or create document type
    doc_type = await db.document_types.find_one(
        {"name": {"$regex": template_name, "$options": "i"}},
        {"_id": 0}
    )
    
    if not doc_type:
        doc_type = await db.document_types.find_one(
            {"category": {"$regex": folder.replace('_', ' '), "$options": "i"}},
            {"_id": 0}
        )
    
    doc_type_id = doc_type['id'] if doc_type else str(uuid.uuid4())
    doc_type_name = doc_type['name'] if doc_type else template_name
    
    # Create employee document record
    doc_id = str(uuid.uuid4())
    emp_doc = {
        "id": doc_id,
        "employee_id": employee['id'],
        "document_type_id": doc_type_id,
        "document_type_name": doc_type_name,
        "category": folder,
        "file_url": file_path,
        "original_filename": filename,
        "status": DocumentStatus.APPROVED,
        "uploaded_by": user['user_id'],
        "uploaded_at": now,
        "reviewed_by": user['user_id'],
        "reviewed_at": now,
        "expiry_date": None,
        "notes": f"Auto-generated from form submission. Form ID: {form_id}",
        "version_number": 1,
        "verified": False,
        "source_type": "form_submission",
        "source_form_id": form_id,
        "created_at": now
    }
    
    await db.employee_documents.insert_one(emp_doc)
    
    # Update form with PDF URL
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {"pdf_url": file_path, "saved_as_document_id": doc_id}}
    )
    
    await log_audit_action(user['user_id'], "save_form_as_document", "generated_form", form_id, {
        "document_id": doc_id,
        "filename": filename,
        "folder": folder
    })
    
    return {
        "success": True,
        "document_id": doc_id,
        "filename": filename,
        "folder": folder,
        "file_url": file_path
    }


@router.post("/generated-forms/{form_id}/archive")
async def archive_form(form_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {"status": FormStatus.ARCHIVED, "updated_at": now}}
    )
    
    await log_audit_action(user['user_id'], "archive_form", "generated_form", form_id, {})
    
    return {"message": "Form archived"}


@router.post("/generated-forms/bulk")
async def bulk_generate_forms(
    employee_id: str = Query(...),
    template_ids: List[str] = Query(...),
    user: dict = Depends(require_manager_or_admin)
):
    """Generate multiple forms for a single employee"""
    db = get_db()
    auto_fill_employee_data = get_auto_fill_employee_data()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    auto_filled = await auto_fill_employee_data(employee_id)
    
    created_forms = []
    errors = []
    
    for template_id in template_ids:
        try:
            template = await db.templates.find_one({"id": template_id}, {"_id": 0})
            if not template:
                errors.append(f"Template {template_id} not found")
                continue
            
            existing = await db.generated_forms.find_one({
                "template_id": template_id,
                "employee_id": employee_id,
                "status": {"$nin": ["archived", "signed_off"]}
            })
            
            if existing:
                errors.append(f"Active form already exists for {template['name']}")
                continue
            
            form_id = str(uuid.uuid4())
            access_token = str(uuid.uuid4())
            
            form_doc = {
                "id": form_id,
                "template_id": template_id,
                "template_name": template['name'],
                "template_category": template['category'],
                "employee_id": employee_id,
                "employee_name": f"{employee['first_name']} {employee['last_name']}",
                "employee_code": employee.get('employee_code') or employee.get('applicant_reference') or '',
                "form_data": auto_filled,
                "status": FormStatus.DRAFT,
                "employee_signature": None,
                "employee_signed_at": None,
                "admin_signature": None,
                "admin_signed_at": None,
                "admin_signoff_by": None,
                "pdf_url": None,
                "locked": False,
                "notes": None,
                "version": 1,
                "access_token": access_token,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id'],
                "sent_at": None,
                "viewed_at": None,
                "completed_at": None,
                "reviewed_at": None,
                "signed_off_at": None
            }
            await db.generated_forms.insert_one(form_doc)
            created_forms.append({
                "id": form_id,
                "template_name": template['name'],
                "status": "created"
            })
            
            await log_audit_action(user['user_id'], "bulk_create_form", "generated_form", form_id, {
                "template_name": template['name'],
                "employee_id": employee_id
            })
            
        except Exception as e:
            errors.append(f"Error creating form for template {template_id}: {str(e)}")
    
    return {
        "created": len(created_forms),
        "forms": created_forms,
        "errors": errors
    }


@router.post("/generated-forms/import-application")
async def import_application_form(
    employee_id: str = Form(...),
    application_file: UploadFile = File(...),
    cv_file: Optional[UploadFile] = File(None),
    user: dict = Depends(require_manager_or_admin)
):
    """Import an existing completed application form and optionally a CV"""
    db = get_db()
    put_object = get_put_object()
    auto_fill_employee_data = get_auto_fill_employee_data()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    application_template = await db.templates.find_one(
        {"name": {"$regex": "Application Form", "$options": "i"}},
        {"_id": 0}
    )
    
    if not application_template:
        raise HTTPException(status_code=404, detail="Application Form template not found")
    
    now = datetime.now(timezone.utc).isoformat()
    form_id = str(uuid.uuid4())
    access_token = str(uuid.uuid4())
    
    # Upload application file
    try:
        app_file_content = await application_file.read()
        app_file_path = f"osabea-care/forms/{employee_id}/{form_id}/{application_file.filename}"
        put_object(app_file_path, app_file_content, application_file.content_type or "application/pdf")
        app_file_url = app_file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload application file: {str(e)}")
    
    # Upload CV if provided
    cv_file_url = None
    cv_doc_id = None
    if cv_file:
        cv_file_ext = "." + cv_file.filename.split(".")[-1].lower() if cv_file.filename and "." in cv_file.filename else ""
        if cv_file_ext != ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF CV files are supported")
        try:
            cv_content = await cv_file.read()
            cv_path = f"osabea-care/documents/{employee_id}/{str(uuid.uuid4())}/{cv_file.filename}"
            put_object(cv_path, cv_content, cv_file.content_type or "application/pdf")
            cv_file_url = cv_path
            
            cv_doc_type = await db.document_types.find_one(
                {"name": {"$regex": "CV|Resume", "$options": "i"}},
                {"_id": 0}
            )
            
            if cv_doc_type:
                cv_doc_id = str(uuid.uuid4())
                cv_doc = {
                    "id": cv_doc_id,
                    "employee_id": employee_id,
                    "document_type_id": cv_doc_type['id'],
                    "document_type_name": cv_doc_type['name'],
                    "requirement_id": "cv",
                    "requirement_name": "CV / Resume",
                    "category": "A_Application_Form",
                    "file_url": cv_file_url,
                    "original_filename": cv_file.filename,
                    "status": "uploaded",
                    "is_active": True,
                    "source_type": "imported",
                    "notes": "Imported with application form",
                    "uploaded_at": now,
                    "uploaded_by": user['user_id'],
                    "expiry_date": None,
                    "version_number": 1,
                    "verified": False,
                    "created_at": now,
                    "updated_at": now
                }
                
                existing_cv = await db.employee_documents.find_one({
                    "employee_id": employee_id,
                    "requirement_id": "cv"
                })
                if existing_cv:
                    cv_doc["version_number"] = existing_cv.get("version_number", 1) + 1
                    await db.employee_documents.update_one(
                        {"id": existing_cv["id"]},
                        {"$set": {
                            "file_url": cv_file_url,
                            "original_filename": cv_file.filename,
                            "version_number": cv_doc["version_number"],
                            "status": "uploaded",
                            "is_active": True,
                            "uploaded_at": now,
                            "updated_at": now
                        }}
                    )
                    cv_doc_id = existing_cv["id"]
                else:
                    await db.employee_documents.insert_one(cv_doc)
                if cv_doc_id:
                    await db.employee_documents.update_many(
                        {
                            "employee_id": employee_id,
                            "id": {"$ne": cv_doc_id},
                            "requirement_id": {"$in": ["cv", "resume", "curriculum_vitae"]},
                            "status": {"$nin": ["superseded", "archived", "deleted"]}
                        },
                        {"$set": {
                            "status": "superseded",
                            "is_active": False,
                            "superseded_at": now,
                            "updated_at": now
                        }}
                    )
                    await db.employees.update_one(
                        {"id": employee_id},
                        {"$set": {
                            "cv_document_id": cv_doc_id,
                            "updated_at": now
                        }}
                    )
        except Exception as e:
            logger.warning(f"Failed to upload CV: {str(e)}")
    
    auto_filled = await auto_fill_employee_data(employee_id)
    
    form_doc = {
        "id": form_id,
        "template_id": application_template['id'],
        "template_name": application_template['name'],
        "template_category": application_template.get('category', 'Application'),
        "employee_id": employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee.get('employee_code') or employee.get('applicant_reference') or '',
        "form_data": auto_filled,
        "status": "completed_imported",
        "employee_signature": None,
        "employee_signed_at": None,
        "admin_signature": None,
        "admin_signed_at": None,
        "admin_signoff_by": None,
        "pdf_url": app_file_url,
        "locked": True,
        "notes": f"Imported from existing application. Original file: {application_file.filename}",
        "version": 1,
        "access_token": access_token,
        "created_at": now,
        "updated_at": now,
        "created_by": user['user_id'],
        "sent_at": None,
        "viewed_at": now,
        "completed_at": now,
        "reviewed_at": None,
        "signed_off_at": None,
        "imported": True,
        "original_filename": application_file.filename
    }
    
    await db.generated_forms.insert_one(form_doc)
    
    # Also create employee document record for Application Form
    app_doc_type = await db.document_types.find_one(
        {"name": {"$regex": "Application Form", "$options": "i"}},
        {"_id": 0}
    )
    
    if app_doc_type:
        app_doc_id = str(uuid.uuid4())
        app_doc = {
            "id": app_doc_id,
            "employee_id": employee_id,
            "document_type_id": app_doc_type['id'],
            "document_type_name": "Application Form",
            "file_url": app_file_url,
            "original_filename": application_file.filename,
            "status": "approved",
            "notes": "Imported - existing completed application",
            "uploaded_at": now,
            "uploaded_by": user['user_id'],
            "expiry_date": None,
            "created_at": now,
            "updated_at": now
        }
        await db.employee_documents.insert_one(app_doc)
    
    await log_audit_action(user['user_id'], "import_application", "generated_form", form_id, {
        "template_name": application_template['name'],
        "employee_id": employee_id,
        "original_file": application_file.filename,
        "cv_included": cv_file is not None
    })
    
    return {
        "success": True,
        "form_id": form_id,
        "form_status": "completed_imported",
        "application_file": application_file.filename,
        "cv_file": cv_file.filename if cv_file else None,
        "cv_document_id": cv_doc_id,
        "message": "Application form imported successfully"
    }


@router.post("/generated-forms/import-document")
async def import_form_document(
    employee_id: str = Form(...),
    form_type: str = Form(...),
    document_file: UploadFile = File(...),
    reference_number: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Import an existing completed document for various form types.
    ENFORCES ONE FORM PER REQUIREMENT - updates existing rather than creating duplicates.
    """
    db = get_db()
    put_object = get_put_object()
    auto_fill_employee_data = get_auto_fill_employee_data()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if form_type not in FORM_TYPE_TO_REQUIREMENT:
        raise HTTPException(status_code=400, detail=f"Invalid form type. Valid types: {list(FORM_TYPE_TO_REQUIREMENT.keys())}")
    
    form_config = FORM_TYPE_TO_REQUIREMENT[form_type]
    requirement_id = form_config['requirement_id']
    category = form_config['category']
    
    display_names = {
        "reference_1": "Reference 1",
        "reference_2": "Reference 2",
        "health_screening": "Health Screening Questionnaire",
        "contract": "Contract Acknowledgement",
        "induction": "Induction & Competency Assessment",
        "handbook": "Employee Handbook Acknowledgement",
    }
    display_name = display_names.get(form_type, form_type.replace("_", " ").title())
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Upload file to storage
    try:
        file_content = await document_file.read()
        file_ext = document_file.filename.split('.')[-1] if '.' in document_file.filename else 'pdf'
        employee_name = f"{employee['first_name']}{employee['last_name']}"
        storage_filename = f"{employee_name}_{form_type}_{datetime.now(timezone.utc).strftime('%d-%m-%Y')}.{file_ext}"
        file_path = f"osabea-care/forms/{employee_id}/{requirement_id}/{storage_filename}"
        put_object(file_path, file_content, document_file.content_type or "application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    # CHECK FOR EXISTING FORM - UPDATE instead of creating duplicate
    existing_form = await db.generated_forms.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id
    })
    
    if existing_form:
        update_data = {
            "pdf_url": file_path,
            "status": "completed_imported",
            "locked": True,
            "notes": notes or f"Imported from existing document. Original file: {document_file.filename}",
            "original_filename": document_file.filename,
            "updated_at": now,
            "completed_at": now,
            "version": existing_form.get('version', 1) + 1
        }
        await db.generated_forms.update_one({"id": existing_form['id']}, {"$set": update_data})
        form_id = existing_form['id']
        action = "updated"
    else:
        form_id = str(uuid.uuid4())
        access_token = str(uuid.uuid4())
        auto_filled = await auto_fill_employee_data(employee_id)
        
        form_doc = {
            "id": form_id,
            "template_id": str(uuid.uuid4()),
            "template_name": display_name,
            "template_category": category,
            "employee_id": employee_id,
            "employee_name": f"{employee['first_name']} {employee['last_name']}",
            "employee_code": employee.get('employee_code') or employee.get('applicant_reference') or '',
            "form_data": auto_filled,
            "status": "completed_imported",
            "employee_signature": None,
            "employee_signed_at": None,
            "admin_signature": None,
            "admin_signed_at": None,
            "admin_signoff_by": None,
            "pdf_url": file_path,
            "locked": True,
            "notes": notes or f"Imported from existing document. Original file: {document_file.filename}",
            "version": 1,
            "access_token": access_token,
            "created_at": now,
            "updated_at": now,
            "created_by": user['user_id'],
            "sent_at": None,
            "viewed_at": now,
            "completed_at": now,
            "reviewed_at": None,
            "signed_off_at": None,
            "imported": True,
            "original_filename": document_file.filename,
            "requirement_id": requirement_id
        }
        await db.generated_forms.insert_one(form_doc)
        action = "created"
    
    # Also update/create employee document record
    existing_doc = await db.employee_documents.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id
    })
    
    if existing_doc:
        doc_update = {
            "file_url": file_path,
            "original_filename": document_file.filename,
            "status": "approved",
            "source_type": "imported",
            "source_form_id": form_id,
            "notes": notes or "Imported document (updated)",
            "uploaded_at": now,
            "updated_at": now,
            "version_number": existing_doc.get("version_number", 1) + 1
        }
        await db.employee_documents.update_one({"id": existing_doc["id"]}, {"$set": doc_update})
        doc_id = existing_doc["id"]
    else:
        doc_id = str(uuid.uuid4())
        doc_record = {
            "id": doc_id,
            "employee_id": employee_id,
            "document_type_id": str(uuid.uuid4()),
            "document_type_name": display_name,
            "requirement_id": requirement_id,
            "requirement_name": display_name,
            "category": category,
            "file_url": file_path,
            "original_filename": document_file.filename,
            "status": "approved",
            "source_type": "imported",
            "source_form_id": form_id,
            "notes": notes or "Imported document",
            "uploaded_at": now,
            "uploaded_by": user['user_id'],
            "expiry_date": None,
            "version_number": 1,
            "verified": False,
            "created_at": now,
            "updated_at": now
        }
        await db.employee_documents.insert_one(doc_record)
    
    await log_audit_action(user['user_id'], f"import_document_{action}", "generated_form", form_id, {
        "form_type": form_type,
        "requirement_id": requirement_id,
        "employee_id": employee_id,
        "original_file": document_file.filename
    })
    
    return {
        "success": True,
        "form_id": form_id,
        "document_id": doc_id,
        "form_type": form_type,
        "requirement_id": requirement_id,
        "form_status": "completed_imported",
        "action": action,
        "original_filename": document_file.filename,
        "message": f"{display_name} {action} successfully"
    }
