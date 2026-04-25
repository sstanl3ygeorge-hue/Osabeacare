"""
Spot Check Routes - CQC Compliant Supervision & Monitoring.

This module handles:
- Spot check recording (observation, document review, competency check)
- Scheduling and tracking follow-ups
- PDF report generation
- Spot check options/types
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from io import BytesIO
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor

from .dependencies import (
    get_db, get_current_user, require_manager_or_admin,
    log_audit_action
)

router = APIRouter(tags=["Spot Checks"])


# Spot check types and areas
SPOT_CHECK_TYPES = [
    {"value": "observation", "label": "Direct Observation"},
    {"value": "document_review", "label": "Document Review"},
    {"value": "competency_check", "label": "Competency Check"},
    {"value": "medication_check", "label": "Medication Check"}
]

SPOT_CHECK_AREAS = [
    {"value": "moving_handling", "label": "Moving & Handling"},
    {"value": "medication", "label": "Medication Administration"},
    {"value": "record_keeping", "label": "Record Keeping"},
    {"value": "communication", "label": "Communication"},
    {"value": "infection_control", "label": "Infection Control"},
    {"value": "dignity_respect", "label": "Dignity & Respect"},
    {"value": "safeguarding", "label": "Safeguarding"}
]


class SpotCheckCreateRequest(BaseModel):
    employee_name: Optional[str] = None
    type: str  # observation, document_review, competency_check, medication_check
    area: str  # moving_handling, medication, record_keeping, etc.
    outcome: str  # pass, needs_improvement, fail
    notes: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[str] = None


class SpotCheckScheduleRequest(BaseModel):
    type: str
    area: str
    scheduled_date: str
    notes: Optional[str] = None


class SpotCheckRecordOutcomeRequest(BaseModel):
    outcome: str  # pass, needs_improvement, fail
    notes: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[str] = None


@router.get("/employees/{employee_id}/spot-checks")
async def get_spot_checks(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all spot checks for an employee"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    checks = await db.spot_checks.find(
        {"employee_id": employee_id}
    ).sort("check_date", -1).to_list(100)
    
    formatted = []
    for c in checks:
        c.pop("_id", None)
        formatted.append(c)
    
    return {"spot_checks": formatted}


@router.post("/employees/{employee_id}/spot-checks")
async def create_spot_check(
    employee_id: str,
    payload: SpotCheckCreateRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """Record a new spot check"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get checker name
    checker = await db.users.find_one(
        {"$or": [{"user_id": user['user_id']}, {"id": user['user_id']}]}, 
        {"_id": 0, "name": 1, "first_name": 1, "last_name": 1, "email": 1}
    )
    checker_name = checker.get('name') if checker else user.get('email', 'Admin')
    if not checker_name and checker:
        checker_name = f"{checker.get('first_name', '')} {checker.get('last_name', '')}".strip() or checker.get('email', 'Admin')
    
    employee_name = payload.employee_name or f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    now = datetime.now(timezone.utc).isoformat()
    
    spot_check_id = str(uuid.uuid4())
    
    spot_check = {
        "id": spot_check_id,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "type": payload.type,
        "area": payload.area,
        "outcome": payload.outcome,
        "check_date": now,
        "checked_by": user['user_id'],
        "checked_by_name": checker_name,
        "notes": payload.notes,
        "follow_up_required": payload.follow_up_required,
        "follow_up_date": payload.follow_up_date,
        "follow_up_completed": False,
        "created_at": now
    }
    
    await db.spot_checks.insert_one(spot_check)
    
    # Log audit
    # Calculate next spot check due date (monthly)
    next_due = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%d')
    
    await log_audit_action(user['user_id'], "spot_check_recorded", "spot_check", spot_check_id, {
        "employee_id": employee_id,
        "type": payload.type,
        "area": payload.area,
        "outcome": payload.outcome
    })
    
    return {
        "success": True,
        "id": spot_check_id,
        "outcome": payload.outcome,
        "next_due_date": next_due
    }


@router.put("/employees/{employee_id}/spot-checks/{spot_check_id}")
async def update_spot_check(
    employee_id: str,
    spot_check_id: str,
    payload: SpotCheckCreateRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """Update an existing spot check"""
    db = get_db()
    
    existing = await db.spot_checks.find_one({
        "id": spot_check_id,
        "employee_id": employee_id
    })
    
    if not existing:
        raise HTTPException(status_code=404, detail="Spot check not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "type": payload.type,
        "area": payload.area,
        "outcome": payload.outcome,
        "notes": payload.notes,
        "follow_up_required": payload.follow_up_required,
        "follow_up_date": payload.follow_up_date,
        "updated_at": now,
        "updated_by": user['user_id']
    }
    
    await db.spot_checks.update_one(
        {"id": spot_check_id},
        {"$set": update_data}
    )
    
    await log_audit_action(user['user_id'], "spot_check_updated", "spot_check", spot_check_id, {
        "employee_id": employee_id,
        "outcome": payload.outcome
    })
    
    return {"success": True, "id": spot_check_id, "outcome": payload.outcome}


@router.post("/employees/{employee_id}/spot-checks/schedule")
async def schedule_spot_check(
    employee_id: str,
    payload: SpotCheckScheduleRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Schedule a future spot check.
    Creates a record with 'scheduled' status.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get scheduler name
    scheduler = await db.users.find_one(
        {"$or": [{"user_id": user['user_id']}, {"id": user['user_id']}]}, 
        {"_id": 0, "name": 1, "email": 1}
    )
    scheduler_name = scheduler.get('name', scheduler.get('email', 'Admin')) if scheduler else 'Admin'
    
    spot_check_id = str(uuid.uuid4())
    
    spot_check = {
        "id": spot_check_id,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "type": payload.type,
        "area": payload.area,
        "outcome": "scheduled",  # Special status for scheduled checks
        "scheduled_date": payload.scheduled_date,
        "scheduled_by": user['user_id'],
        "scheduled_by_name": scheduler_name,
        "notes": payload.notes,
        "created_at": now,
        "status": "scheduled"
    }
    
    await db.spot_checks.insert_one(spot_check)
    
    await log_audit_action(user['user_id'], "spot_check_scheduled", "spot_check", spot_check_id, {
        "employee_id": employee_id,
        "scheduled_date": payload.scheduled_date
    })
    
    return {
        "success": True,
        "id": spot_check_id,
        "message": f"Spot check scheduled for {payload.scheduled_date}"
    }


@router.put("/employees/{employee_id}/spot-checks/{spot_check_id}/record-outcome")
async def record_spot_check_outcome(
    employee_id: str,
    spot_check_id: str,
    payload: SpotCheckRecordOutcomeRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Record the outcome of a scheduled spot check.
    Updates status from 'scheduled' to the actual outcome.
    """
    db = get_db()
    
    check = await db.spot_checks.find_one({"id": spot_check_id, "employee_id": employee_id})
    if not check:
        raise HTTPException(status_code=404, detail="Spot check not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get checker name
    checker = await db.users.find_one(
        {"$or": [{"user_id": user['user_id']}, {"id": user['user_id']}]}, 
        {"_id": 0, "name": 1, "email": 1}
    )
    checker_name = checker.get('name', checker.get('email', 'Admin')) if checker else 'Admin'
    
    update_data = {
        "outcome": payload.outcome,
        "check_date": now,
        "checked_by": user['user_id'],
        "checked_by_name": checker_name,
        "notes": payload.notes,
        "follow_up_required": payload.follow_up_required,
        "follow_up_date": payload.follow_up_date,
        "status": "completed"
    }
    
    await db.spot_checks.update_one(
        {"id": spot_check_id},
        {"$set": update_data}
    )
    
    await log_audit_action(user['user_id'], "spot_check_outcome_recorded", "spot_check", spot_check_id, {
        "employee_id": employee_id,
        "outcome": payload.outcome
    })
    
    return {
        "success": True,
        "outcome": payload.outcome,
        "message": f"Spot check completed with outcome: {payload.outcome}"
    }


@router.get("/spot-check-options")
async def get_spot_check_options(user: dict = Depends(get_current_user)):
    """Return spot check types and areas for dropdowns"""
    return {
        "types": SPOT_CHECK_TYPES,
        "areas": SPOT_CHECK_AREAS
    }


@router.get("/employees/{employee_id}/spot-checks/{check_id}/download-pdf")
async def download_spot_check_pdf(
    employee_id: str,
    check_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Generate and download a PDF report for a spot check.
    Includes full details, outcome, and any follow-up requirements.
    """
    db = get_db()
    
    # Get spot check
    check = await db.spot_checks.find_one({"id": check_id, "employee_id": employee_id}, {"_id": 0})
    if not check:
        raise HTTPException(status_code=404, detail="Spot check not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "role": 1})
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() if employee else "Unknown"
    
    # Generate PDF with branded styling
    from services.pdf_service import get_logo_image, PRIMARY_COLOR, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Create branded styles
    base_styles = getSampleStyleSheet()
    
    company_style = ParagraphStyle(
        name='CompanyName',
        parent=base_styles['Heading1'],
        fontSize=16,
        textColor=HexColor("#1A1A2E"),
        spaceAfter=2*mm,
        alignment=1  # TA_CENTER
    )
    
    title_style = ParagraphStyle(
        name='Title',
        parent=base_styles['Heading1'],
        fontSize=18,
        textColor=PRIMARY_COLOR,
        spaceAfter=6*mm,
        alignment=1  # TA_CENTER
    )
    
    footer_style = ParagraphStyle(
        name='Footer',
        parent=base_styles['Normal'],
        fontSize=8,
        textColor=TEXT_SECONDARY,
        alignment=1  # TA_CENTER
    )
    
    story = []
    
    # Header with logo
    logo = get_logo_image()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 3*mm))
    
    story.append(Paragraph("Osabea Healthcare Solutions", company_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5*mm))
    
    # Title
    story.append(Paragraph("Spot Check Record", title_style))
    
    # Build data table
    check_type_label = next((t['label'] for t in SPOT_CHECK_TYPES if t['value'] == check.get('type')), check.get('type', 'N/A'))
    area_label = next((a['label'] for a in SPOT_CHECK_AREAS if a['value'] == check.get('area')), check.get('area', 'N/A'))
    
    data = [
        ["Employee:", employee_name],
        ["Role:", employee.get('role', 'N/A') if employee else 'N/A'],
        ["Check Type:", check_type_label],
        ["Area:", area_label],
        ["Date:", check.get('check_date', 'N/A')[:10] if check.get('check_date') else 'N/A'],
        ["Checked By:", check.get('checked_by_name', 'N/A')],
        ["Outcome:", check.get('outcome', 'N/A').upper()],
        ["Notes:", check.get('notes', 'No notes recorded')],
        ["Follow-up Required:", "Yes" if check.get('follow_up_required') else "No"],
    ]
    
    if check.get('follow_up_date'):
        data.append(["Follow-up Date:", check['follow_up_date'][:10]])
    
    table = Table(data, colWidths=[50*mm, 120*mm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LINEBELOW', (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Outcome styling
    outcome = check.get('outcome', 'N/A')
    outcome_color = colors.green if outcome == 'pass' else colors.orange if outcome == 'needs_improvement' else colors.red
    
    outcome_style = ParagraphStyle('Outcome', parent=base_styles['Normal'], fontSize=14, textColor=outcome_color, fontName='Helvetica-Bold')
    story.append(Paragraph(f"OUTCOME: {outcome.upper()}", outcome_style))
    
    # Footer with timestamp
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5*mm))
    footer_text = f"Generated by Osabea Healthcare Solutions Compliance System on {datetime.now(timezone.utc).strftime('%d %B %Y %H:%M UTC')}"
    story.append(Paragraph(footer_text, footer_style))
    story.append(Paragraph("This is an official supervision record. Store securely.", footer_style))
    
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    filename = f"spot_check_{employee_name.replace(' ', '_')}_{check.get('check_date', '')[:10]}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
