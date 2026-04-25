"""
PDF Service - Unified PDF generation for admin forms with company logo support.

Supports:
- Interview Record
- Induction Checklist Certificate
- Spot Check Record
- Other admin forms

Logo placement: Top left of first page only
Logo can be configured via COMPANY_LOGO_URL environment variable
"""

import os
import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
import requests
from typing import Dict, Any, Optional, List
from xml.sax.saxutils import escape

# Company logo URL - configurable via environment variable
LOGO_URL = os.environ.get("COMPANY_LOGO_URL", None)

# Brand colors
PRIMARY_COLOR = HexColor("#0D6E6E")  # Teal
SECONDARY_COLOR = HexColor("#1A1A2E")  # Dark blue
ACCENT_COLOR = HexColor("#F4B942")  # Gold
TEXT_PRIMARY = HexColor("#1F2937")
TEXT_SECONDARY = HexColor("#6B7280")
BORDER_COLOR = HexColor("#E5E7EB")

def get_logo_image(width=50*mm, height=20*mm) -> Optional[Image]:
    """
    Fetch and return logo image.
    Falls back to local osabea_logo.png if COMPANY_LOGO_URL is not configured.
    """
    # Try COMPANY_LOGO_URL first
    if LOGO_URL:
        try:
            if LOGO_URL.startswith('/') or LOGO_URL.startswith('./'):
                if os.path.exists(LOGO_URL):
                    return Image(LOGO_URL, width=width, height=height)
            else:
                response = requests.get(LOGO_URL, timeout=5)
                if response.status_code == 200:
                    logo_data = io.BytesIO(response.content)
                    return Image(logo_data, width=width, height=height)
        except Exception as e:
            print(f"Failed to load logo from URL: {e}")

    # Fallback to local osabea_logo.png
    try:
        local_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'osabea_logo.png')
        if os.path.exists(local_logo):
            return Image(local_logo, width=width, height=height)
    except Exception as e:
        print(f"Failed to load local logo: {e}")
    
    return None


def create_pdf_styles():
    """Create consistent PDF styles for all admin forms."""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='FormTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=PRIMARY_COLOR,
        spaceAfter=6*mm,
        alignment=TA_CENTER
    ))
    
    # Company name style
    styles.add(ParagraphStyle(
        name='CompanyName',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=SECONDARY_COLOR,
        spaceAfter=2*mm,
        alignment=TA_CENTER
    ))
    
    # Subtitle style
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=TEXT_SECONDARY,
        spaceAfter=4*mm,
        alignment=TA_CENTER
    ))
    
    # Section header style
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=PRIMARY_COLOR,
        spaceBefore=6*mm,
        spaceAfter=3*mm,
        borderPadding=2*mm
    ))
    
    # Field label style
    styles.add(ParagraphStyle(
        name='FieldLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=TEXT_SECONDARY,
        spaceBefore=1*mm
    ))
    
    # Field value style
    styles.add(ParagraphStyle(
        name='FieldValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=TEXT_PRIMARY,
        spaceAfter=2*mm
    ))
    
    # Notes style
    styles.add(ParagraphStyle(
        name='Notes',
        parent=styles['Normal'],
        fontSize=9,
        textColor=TEXT_PRIMARY,
        leftIndent=5*mm,
        spaceBefore=2*mm,
        spaceAfter=2*mm,
        backColor=HexColor("#F9FAFB"),
        borderPadding=3*mm
    ))
    
    # Footer style
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=TEXT_SECONDARY,
        alignment=TA_CENTER
    ))
    
    return styles


def generate_admin_form_pdf(
    form_type: str,
    form_data: Dict[str, Any],
    employee_data: Dict[str, Any],
    admin_data: Dict[str, Any]
) -> bytes:
    """
    Generate PDF for any admin form with company logo.
    
    Args:
        form_type: Type of form (interview_record, induction_checklist, spot_check)
        form_data: Dictionary of form field values
        employee_data: Employee details (name, id, code, etc.)
        admin_data: Admin/assessor details (name, timestamp)
    
    Returns:
        BytesIO object containing PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    styles = create_pdf_styles()
    elements = []
    
    # ===== HEADER WITH LOGO =====
    header_data = []
    
    # Logo (if available)
    logo = get_logo_image()
    if logo:
        header_data.append([logo, ""])
    
    # Company name and document type
    company_name = "Osabea Healthcare Solutions"
    header_data.append([
        Paragraph(company_name, styles['CompanyName']),
        ""
    ])
    header_data.append([
        Paragraph("Compliance Document", styles['Subtitle']),
        ""
    ])
    
    if header_data:
        header_table = Table(header_data, colWidths=[100*mm, 70*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 5*mm))
    
    # Horizontal line
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5*mm))
    
    # Form title based on type
    form_titles = {
        'interview_record': 'Interview Record',
        'induction_checklist': 'Induction Completion Certificate',
        'spot_check': 'Spot Check Record'
    }
    title = form_titles.get(form_type, form_type.replace('_', ' ').title())
    elements.append(Paragraph(title, styles['FormTitle']))
    
    # ===== EMPLOYEE INFO TABLE =====
    employee_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip() or employee_data.get('name', 'Unknown')
    employee_code = employee_data.get('employee_code') or employee_data.get('applicant_reference') or employee_data.get('id', '')[:8]
    
    info_data = [
        ['Employee:', employee_name],
        ['Employee ID:', employee_code],
        ['Date:', datetime.now(timezone.utc).strftime('%d %B %Y')],
        ['Completed by:', admin_data.get('name', 'System Admin')],
    ]
    
    info_table = Table(info_data, colWidths=[35*mm, 135*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=6*mm))
    
    # ===== FORM-SPECIFIC CONTENT =====
    if form_type == 'interview_record':
        elements.extend(generate_interview_pdf_content(form_data, styles))
    elif form_type == 'induction_checklist':
        elements.extend(generate_induction_pdf_content(form_data, styles))
    elif form_type == 'spot_check':
        elements.extend(generate_spotcheck_pdf_content(form_data, styles))
    else:
        # Generic form fields
        elements.extend(generate_generic_pdf_content(form_data, styles))
    
    # ===== FOOTER =====
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5*mm))
    
    footer_text = f"Generated by Osabea Healthcare Solutions Compliance System on {datetime.now(timezone.utc).strftime('%d %B %Y %H:%M UTC')}"
    elements.append(Paragraph(footer_text, styles['Footer']))
    elements.append(Paragraph("This is an official compliance document. Store securely.", styles['Footer']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_interview_pdf_content(form_data: Dict[str, Any], styles) -> list:
    """Generate interview record specific PDF content."""
    elements = []
    
    # Interview Information Section
    elements.append(Paragraph("Interview Information", styles['SectionHeader']))
    
    interview_info = [
        ['Interview Date:', form_data.get('interview_date', 'N/A')],
        ['Interview Method:', form_data.get('interview_method', 'N/A')],
        ['Interviewer:', form_data.get('interviewer_name', 'N/A')],
    ]
    
    info_table = Table(interview_info, colWidths=[40*mm, 130*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#F9FAFB")),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))
    
    # Assessment Scores Section
    elements.append(Paragraph("Assessment Scores", styles['SectionHeader']))
    
    scores = [
        ['Criterion', 'Score (1-5)'],
        ['Communication Skills', str(form_data.get('communication_score', '-'))],
        ['Experience Match', str(form_data.get('experience_score', '-'))],
        ['Values Alignment', str(form_data.get('values_score', '-'))],
    ]
    
    score_table = Table(scores, colWidths=[90*mm, 80*mm])
    score_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 4*mm))
    
    # Availability
    if form_data.get('availability'):
        elements.append(Paragraph("Availability", styles['SectionHeader']))
        elements.append(Paragraph(str(form_data.get('availability')), styles['Notes']))
    
    # Strengths
    if form_data.get('strengths'):
        elements.append(Paragraph("Strengths", styles['SectionHeader']))
        elements.append(Paragraph(str(form_data.get('strengths')), styles['Notes']))
    
    # Areas for Development
    if form_data.get('areas_for_development'):
        elements.append(Paragraph("Areas for Development", styles['SectionHeader']))
        elements.append(Paragraph(str(form_data.get('areas_for_development')), styles['Notes']))
    
    # Notes
    if form_data.get('notes'):
        elements.append(Paragraph("Additional Notes", styles['SectionHeader']))
        elements.append(Paragraph(str(form_data.get('notes')), styles['Notes']))
    
    # Decision Section
    elements.append(Paragraph("Interview Decision", styles['SectionHeader']))
    decision = form_data.get('decision', 'Pending')
    decision_color = {
        'Approve': HexColor("#10B981"),
        'Reject': HexColor("#EF4444"),
        'On Hold': HexColor("#F59E0B")
    }.get(decision, TEXT_PRIMARY)
    
    decision_style = ParagraphStyle(
        name='Decision',
        parent=styles['FieldValue'],
        fontSize=14,
        textColor=decision_color,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph(f"Decision: {decision}", decision_style))
    
    return elements


def generate_induction_pdf_content(form_data: Dict[str, Any], styles) -> list:
    """Generate induction checklist certificate PDF content."""
    elements = []
    
    # Certification Statement
    elements.append(Paragraph("Certificate of Induction Completion", styles['SectionHeader']))
    
    cert_text = """
    This certifies that the above-named employee has successfully completed their 
    induction programme as required by the Care Quality Commission (CQC) standards.
    """
    elements.append(Paragraph(cert_text, styles['FieldValue']))
    elements.append(Spacer(1, 4*mm))
    
    # Induction Details
    induction_info = [
        ['Induction Start Date:', form_data.get('start_date', 'N/A')],
        ['Completion Date:', form_data.get('completion_date', datetime.now(timezone.utc).strftime('%d %B %Y'))],
        ['Inductor Name:', form_data.get('inductor_name', 'N/A')],
    ]
    
    info_table = Table(induction_info, colWidths=[45*mm, 125*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))
    
    # Checklist Items
    elements.append(Paragraph("Completed Induction Items", styles['SectionHeader']))
    
    checklist_items = form_data.get('checklist_items', [])
    if isinstance(checklist_items, list):
        checklist_data = [['Item', 'Status', 'Completed']]
        for item in checklist_items:
            if isinstance(item, dict):
                checklist_data.append([
                    item.get('name', 'Unknown'),
                    'Completed' if item.get('completed', False) else 'Pending',
                    item.get('completed_date', '-')
                ])
            else:
                checklist_data.append([str(item), 'Completed', '-'])
        
        if len(checklist_data) > 1:
            checklist_table = Table(checklist_data, colWidths=[80*mm, 45*mm, 45*mm])
            checklist_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ]))
            elements.append(checklist_table)
    
    # Notes
    if form_data.get('notes'):
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph("Additional Notes", styles['SectionHeader']))
        elements.append(Paragraph(str(form_data.get('notes')), styles['Notes']))
    
    return elements


def generate_spotcheck_pdf_content(form_data: Dict[str, Any], styles) -> list:
    """Generate spot check record PDF content."""
    elements = []
    
    # Spot Check Details
    elements.append(Paragraph("Spot Check Details", styles['SectionHeader']))
    
    type_labels = {
        'observation': 'Direct Observation',
        'document_review': 'Document Review',
        'competency_check': 'Competency Check',
        'medication_check': 'Medication Check'
    }
    
    area_labels = {
        'moving_handling': 'Moving & Handling',
        'medication': 'Medication Administration',
        'record_keeping': 'Record Keeping',
        'communication': 'Communication',
        'infection_control': 'Infection Control',
        'dignity_respect': 'Dignity & Respect',
        'safeguarding': 'Safeguarding'
    }
    
    check_info = [
        ['Check Date:', form_data.get('date', datetime.now(timezone.utc).strftime('%d %B %Y'))],
        ['Check Type:', type_labels.get(form_data.get('type'), form_data.get('type', 'N/A'))],
        ['Area Assessed:', area_labels.get(form_data.get('area'), form_data.get('area', 'N/A'))],
        ['Assessor:', form_data.get('assessor_name', 'N/A')],
    ]
    
    info_table = Table(check_info, colWidths=[35*mm, 135*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#F9FAFB")),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))
    
    # Outcome
    elements.append(Paragraph("Assessment Outcome", styles['SectionHeader']))
    outcome = form_data.get('outcome', 'N/A')
    outcome_colors = {
        'pass': HexColor("#10B981"),
        'needs_improvement': HexColor("#F59E0B"),
        'fail': HexColor("#EF4444")
    }
    outcome_labels = {
        'pass': 'PASS - Meets Expected Standards',
        'needs_improvement': 'NEEDS IMPROVEMENT - Minor Issues Identified',
        'fail': 'FAIL - Significant Concerns'
    }
    
    outcome_style = ParagraphStyle(
        name='Outcome',
        parent=styles['FieldValue'],
        fontSize=12,
        textColor=outcome_colors.get(outcome, TEXT_PRIMARY),
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph(outcome_labels.get(outcome, outcome.upper()), outcome_style))
    elements.append(Spacer(1, 4*mm))
    
    # Observations/Notes
    if form_data.get('notes'):
        elements.append(Paragraph("Observations & Notes", styles['SectionHeader']))
        elements.append(Paragraph(str(form_data.get('notes')), styles['Notes']))
    
    # Follow-up
    if form_data.get('follow_up_required'):
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph("Follow-up Required", styles['SectionHeader']))
        follow_up_date = form_data.get('follow_up_date', 'To be scheduled')
        elements.append(Paragraph(f"Follow-up Date: {follow_up_date}", styles['FieldValue']))
    
    return elements


def generate_reference_response_pdf(
    response_data: Dict[str, Any],
    declared_data: Dict[str, Any],
    employee_data: Dict[str, Any],
    reference_num: int,
    mismatch_data: Optional[Dict[str, Any]] = None,
    sufficiency_data: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generate PDF for a referee response with company logo.
    
    Args:
        response_data: Referee's submitted form data
        declared_data: What the applicant declared about this referee
        employee_data: Employee details
        reference_num: Reference number (1 or 2)
        mismatch_data: Optional mismatch detection data
    
    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    styles = create_pdf_styles()
    elements = []
    
    # ===== HEADER WITH LOGO =====
    logo = get_logo_image()
    if logo:
        logo_table = Table([[logo]], colWidths=[170*mm])
        logo_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(logo_table)
        elements.append(Spacer(1, 3*mm))
    else:
        elements.append(Paragraph("Osabea Healthcare Solutions", styles['CompanyName']))
        elements.append(Spacer(1, 3*mm))
    
    elements.append(Paragraph(f"Employment Reference — Referee {reference_num}", styles['FormTitle']))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5*mm))
    
    # Employee info
    employee_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip() or 'Unknown'
    info_data = [
        ['Applicant:', employee_name],
        ['Employee Code:', employee_data.get('employee_code') or employee_data.get('applicant_reference') or ''],
        ['Reference Number:', str(reference_num)],
        ['Received:', response_data.get('received_at', response_data.get('submitted_at', 'N/A'))],
    ]
    info_table = Table(info_data, colWidths=[35*mm, 135*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))
    
    # ===== DECLARED VS RETURNED COMPARISON =====
    elements.append(Paragraph("Declared vs Returned Comparison", styles['SectionHeader']))
    
    comparison_data = [
        ['', 'Declared by Applicant', 'Returned by Referee'],
        ['Name', declared_data.get('name', 'N/A'), response_data.get('referee_full_name', 'N/A')],
        ['Organisation', declared_data.get('organisation') or declared_data.get('company', 'N/A'), response_data.get('referee_organisation', 'N/A')],
        ['Email', declared_data.get('email', 'N/A'), response_data.get('referee_work_email', 'N/A')],
    ]
    comp_table = Table(comparison_data, colWidths=[30*mm, 70*mm, 70*mm])
    comp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(comp_table)
    elements.append(Spacer(1, 3*mm))
    
    # Mismatch warning
    if mismatch_data and mismatch_data.get('detected'):
        mismatch_style = ParagraphStyle('MismatchWarn', parent=styles['FieldValue'], textColor=HexColor("#DC2626"), fontSize=10, fontName='Helvetica-Bold')
        elements.append(Paragraph("⚠ MISMATCH DETECTED", mismatch_style))
        for reason in (mismatch_data.get('reasons') or []):
            elements.append(Paragraph(f"  • {reason}", styles['FieldValue']))
        elements.append(Spacer(1, 3*mm))
    
    # ===== EMPLOYMENT DETAILS =====
    elements.append(Paragraph("Employment Details", styles['SectionHeader']))
    employment_fields = [
        ('Relationship Type', 'relationship_type'),
        ('Known From', 'known_from_date'),
        ('Known To', 'known_to_date'),
        ('Employment Dates Confirmed', 'employment_dates_confirm'),
        ('Job Title Held', 'job_title_held'),
        ('Reason for Leaving', 'reason_for_leaving'),
    ]
    for label, key in employment_fields:
        val = response_data.get(key)
        if val is not None and val != '':
            display_val = 'Yes' if val is True else ('No' if val is False else str(val))
            elements.append(Paragraph(f"<b>{label}:</b> {display_val}", styles['FieldValue']))
            elements.append(Spacer(1, 1*mm))
    elements.append(Spacer(1, 3*mm))
    
    # ===== PERFORMANCE ASSESSMENT =====
    elements.append(Paragraph("Performance Assessment", styles['SectionHeader']))
    perf_fields = [
        ('Performance Rating', 'performance_rating'),
        ('Reliability', 'reliability'),
        ('Professionalism', 'professionalism'),
        ('Teamwork', 'teamwork'),
    ]
    perf_data = [['Criterion', 'Rating']]
    for label, key in perf_fields:
        val = response_data.get(key)
        if val is not None:
            perf_data.append([label, str(val)])
    
    if len(perf_data) > 1:
        perf_table = Table(perf_data, colWidths=[85*mm, 85*mm])
        perf_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
            ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
        ]))
        elements.append(perf_table)
    elements.append(Spacer(1, 3*mm))
    
    # ===== SUITABILITY & SAFEGUARDING =====
    elements.append(Paragraph("Suitability & Safeguarding", styles['SectionHeader']))
    safeguard_fields = [
        ('Safeguarding Concerns', 'safeguarding_concerns'),
        ('Safeguarding Details', 'safeguarding_details'),
        ('Disciplinary Record', 'disciplinary_record'),
        ('Disciplinary Details', 'disciplinary_details'),
        ('Would Re-employ', 'would_re_employ'),
        ('Re-employ Notes', 're_employ_notes'),
        ('Suitable for Vulnerable Care', 'care_vulnerable_suitable'),
        ('Care Suitability Notes', 'care_suitability_notes'),
    ]
    for label, key in safeguard_fields:
        val = response_data.get(key)
        if val is not None and val != '':
            display_val = 'Yes' if val is True else ('No' if val is False else str(val))
            # Highlight concerns in red
            if ('concern' in str(val).lower() or val is True) and 'concern' in key:
                elements.append(Paragraph(f"<b>{label}:</b> <font color='#DC2626'>{display_val}</font>", styles['FieldValue']))
            else:
                elements.append(Paragraph(f"<b>{label}:</b> {display_val}", styles['FieldValue']))
            elements.append(Spacer(1, 1*mm))
    elements.append(Spacer(1, 3*mm))
    
    # ===== ADDITIONAL COMMENTS =====
    if response_data.get('additional_comments'):
        elements.append(Paragraph("Additional Comments", styles['SectionHeader']))
        elements.append(Paragraph(str(response_data['additional_comments']), styles['Notes']))
        elements.append(Spacer(1, 3*mm))
    
    # ===== DECLARATIONS =====
    elements.append(Paragraph("Referee Declarations", styles['SectionHeader']))
    if response_data.get('declaration_accurate'):
        elements.append(Paragraph("✓ Information provided is accurate to the best of their knowledge", styles['FieldValue']))
    if response_data.get('declaration_authority'):
        elements.append(Paragraph("✓ Has authority to provide this reference", styles['FieldValue']))
    elements.append(Spacer(1, 3*mm))

    # ===== REFERENCE SUFFICIENCY (CQC Reg 19) =====
    if sufficiency_data:
        elements.append(Paragraph("Reference Sufficiency (CQC Reg 19)", styles['SectionHeader']))
        ref_type = sufficiency_data.get('type') or 'unspecified'
        is_emp = sufficiency_data.get('is_employment_reference')
        elements.append(Paragraph(
            f"<b>Type:</b> {ref_type} &nbsp;&nbsp; <b>Employment Reference:</b> {'Yes' if is_emp else 'No'}",
            styles['FieldValue'],
        ))
        explanation = sufficiency_data.get('explanation_reason')
        if explanation:
            elements.append(Paragraph(f"<b>Explanation for non-employment reference:</b>", styles['FieldValue']))
            elements.append(Paragraph(str(explanation), styles['Notes']))
            provided_by = sufficiency_data.get('explanation_provided_by')
            provided_at = sufficiency_data.get('explanation_provided_at')
            if provided_by or provided_at:
                elements.append(Paragraph(
                    f"<i>Recorded by {provided_by or 'admin'} on {provided_at or 'N/A'}</i>",
                    styles['FieldValue'],
                ))
        elements.append(Spacer(1, 3*mm))
    
    # ===== FOOTER =====
    elements.append(Spacer(1, 6*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5*mm))
    footer_text = f"Generated by Osabea Healthcare Solutions Compliance System on {datetime.now(timezone.utc).strftime('%d %B %Y %H:%M UTC')}"
    elements.append(Paragraph(footer_text, styles['Footer']))
    elements.append(Paragraph("This is an official compliance document. Store securely.", styles['Footer']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_pre_interview_pdf(
    form_data: Dict[str, Any],
    employee_data: Dict[str, Any],
    questions_config: Optional[List[Dict[str, Any]]] = None
) -> bytes:
    """
    Generate PDF for a pre-interview questionnaire response with company logo.
    
    Args:
        form_data: Worker's submitted questionnaire answers
        employee_data: Employee details
        questions_config: Optional role-specific question definitions
    
    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    styles = create_pdf_styles()
    elements = []
    
    # ===== HEADER WITH LOGO =====
    logo = get_logo_image()
    if logo:
        logo_table = Table([[logo]], colWidths=[170*mm])
        logo_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(logo_table)
        elements.append(Spacer(1, 3*mm))
    else:
        elements.append(Paragraph("Osabea Healthcare Solutions", styles['CompanyName']))
        elements.append(Spacer(1, 3*mm))
    
    elements.append(Paragraph("Interview Questionnaire", styles['FormTitle']))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5*mm))
    
    # Employee info
    employee_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip() or 'Unknown'
    info_data = [
        ['Applicant:', employee_name],
        ['Employee Code:', employee_data.get('employee_code') or employee_data.get('applicant_reference') or ''],
        ['Role:', employee_data.get('role', 'N/A')],
        ['Date:', datetime.now(timezone.utc).strftime('%d %B %Y')],
    ]
    info_table = Table(info_data, colWidths=[35*mm, 135*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))
    
    # ===== QUESTIONNAIRE RESPONSES =====
    # If we have questions config, use structured display
    if questions_config:
        for i, question in enumerate(questions_config):
            q_id = question.get('id', f'q{i+1}')
            q_text = question.get('question') or question.get('label', f'Question {i+1}')
            answer = form_data.get(q_id, 'No answer provided')
            
            if isinstance(answer, bool):
                answer = 'Yes' if answer else 'No'
            elif answer is None:
                answer = 'No answer provided'
            
            # Question number and text
            q_style = ParagraphStyle(
                f'Q{i}',
                parent=styles['FieldLabel'],
                fontSize=10,
                fontName='Helvetica-Bold',
                textColor=PRIMARY_COLOR,
                spaceBefore=4*mm
            )
            elements.append(Paragraph(f"Q{i+1}. {q_text}", q_style))
            elements.append(Paragraph(str(answer), styles['Notes']))
    else:
        # Fallback: render all form_data fields
        elements.append(Paragraph("Responses", styles['SectionHeader']))
        skip_keys = {'_submitted_at', '_verified', '_status', 'submitted_at', 'ip_address', 'user_agent'}
        
        q_num = 1
        for key, value in form_data.items():
            if key.startswith('_') or key in skip_keys:
                continue
            
            label = key.replace('_', ' ').title()
            if isinstance(value, bool):
                value = 'Yes' if value else 'No'
            elif value is None:
                value = 'N/A'
            
            elements.append(Paragraph(f"<b>{label}:</b>", styles['FieldLabel']))
            elements.append(Paragraph(str(value), styles['Notes']))
            q_num += 1
    
    # ===== FOOTER =====
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5*mm))
    footer_text = f"Generated by Osabea Healthcare Solutions Compliance System on {datetime.now(timezone.utc).strftime('%d %B %Y %H:%M UTC')}"
    elements.append(Paragraph(footer_text, styles['Footer']))
    elements.append(Paragraph("This is an official compliance document. Store securely.", styles['Footer']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_generic_pdf_content(form_data: Dict[str, Any], styles) -> list:
    """Generate generic form PDF content for any form type."""
    elements = []
    
    elements.append(Paragraph("Form Data", styles['SectionHeader']))
    
    for key, value in form_data.items():
        if key.startswith('_'):
            continue  # Skip metadata fields
        
        label = key.replace('_', ' ').title()
        elements.append(Paragraph(label, styles['FieldLabel']))
        
        if isinstance(value, bool):
            value_str = "Yes" if value else "No"
        elif isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        elif value is None:
            value_str = "N/A"
        else:
            value_str = str(value)
        
        elements.append(Paragraph(value_str, styles['FieldValue']))
    
    return elements


def _pdf_value(value: Any) -> str:
    """Return a safe printable value for ReportLab Paragraph content."""
    if value is None or value == "":
        return "N/A"
    if isinstance(value, bool):
        value = "Yes" if value else "No"
    elif isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    elif isinstance(value, dict):
        value = "; ".join(f"{k}: {v}" for k, v in value.items())
    return escape(str(value)).replace("\n", "<br/>")


def generate_scored_interview_pdf_content(form_data: Dict[str, Any], styles) -> list:
    """Generate the current Osabea scored interview assessment PDF content."""
    elements = []

    elements.append(Paragraph("Interview Details", styles["SectionHeader"]))
    details = [
        ["Candidate Name", _pdf_value(form_data.get("candidate_name"))],
        ["Job Title", _pdf_value(form_data.get("vacancy_job_title") or form_data.get("position_applied"))],
        ["Interview Date", _pdf_value(form_data.get("interview_date"))],
        ["Interview Method", _pdf_value(form_data.get("interview_method") or form_data.get("interview_type"))],
        ["Interviewer", _pdf_value(form_data.get("interviewer_name"))],
        ["Panel Members", _pdf_value(form_data.get("panel_members"))],
    ]
    details_table = Table(details, colWidths=[45 * mm, 125 * mm])
    details_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Part 1 - Scored Interview Assessment", styles["SectionHeader"]))
    assessment_items = form_data.get("assessment_items") or []
    question_scores = form_data.get("question_scores") or {}
    question_notes = form_data.get("question_notes") or {}

    if assessment_items:
        for index, item in enumerate(assessment_items, start=1):
            question_id = item.get("question_id")
            score = item.get("admin_score")
            if score is None and question_id:
                score = question_scores.get(question_id)
            notes = item.get("admin_notes")
            if notes is None and question_id:
                notes = question_notes.get(question_id)

            elements.append(Paragraph(
                f"Q{index}. {_pdf_value(item.get('question_text'))}",
                styles["FieldLabel"]
            ))
            meta = []
            if item.get("category"):
                meta.append(f"Category: {_pdf_value(item.get('category')).replace('_', ' ')}")
            if item.get("skills_assessed"):
                meta.append(f"Skills assessed: {_pdf_value(item.get('skills_assessed'))}")
            if meta:
                elements.append(Paragraph(" | ".join(meta), styles["Footer"]))
            rows = [
                [Paragraph("Worker answer", styles["FieldLabel"]), Paragraph(_pdf_value(item.get("worker_answer")), styles["FieldValue"])],
                [Paragraph("Admin score", styles["FieldLabel"]), Paragraph(_pdf_value(score), styles["FieldValue"])],
                [Paragraph("Admin notes", styles["FieldLabel"]), Paragraph(_pdf_value(notes), styles["FieldValue"])],
            ]
            table = Table(rows, colWidths=[35 * mm, 135 * mm])
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 3 * mm))
    else:
        elements.append(Paragraph("No scored question snapshot was saved for this interview record.", styles["Notes"]))

    elements.append(Paragraph("Part 2 - Administrative Interview Fields", styles["SectionHeader"]))
    admin_rows = [
        ["Requires Work Permit", _pdf_value(form_data.get("requires_work_permit"))],
        ["Right to Work proof taken", _pdf_value(form_data.get("rtw_proof_taken"))],
        ["Hours wanted", _pdf_value(form_data.get("hours_wanted"))],
        ["Flexible working", _pdf_value(form_data.get("flexible_working"))],
        ["Driving licence", _pdf_value(form_data.get("has_driving_licence"))],
        ["Annual leave booked", _pdf_value(form_data.get("annual_leave_booked"))],
        ["Notice period", _pdf_value(form_data.get("notice_period"))],
        ["Available start date", _pdf_value(form_data.get("start_date"))],
    ]
    admin_table = Table(admin_rows, colWidths=[55 * mm, 115 * mm])
    admin_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    elements.append(admin_table)
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Decision and Final Score", styles["SectionHeader"]))
    decision_rows = [
        ["Total Score", f"{_pdf_value(form_data.get('total_score'))} / {_pdf_value(form_data.get('max_score'))}"],
        ["Pass Threshold", _pdf_value(form_data.get("pass_score"))],
        ["Percentage", f"{_pdf_value(form_data.get('percentage'))}%"],
        ["Result", "Passed" if form_data.get("passed") else "Failed / further review"],
        ["Decision", _pdf_value(form_data.get("decision"))],
        ["Candidate Questions", _pdf_value(form_data.get("candidate_questions"))],
        ["Overall Impression", _pdf_value(form_data.get("overall_impression"))],
        ["Additional Notes", _pdf_value(form_data.get("notes"))],
    ]
    decision_table = Table(decision_rows, colWidths=[45 * mm, 125 * mm])
    decision_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    elements.append(decision_table)

    return elements


def generate_structured_form_pdf(
    form_type: str,
    form_name: str,
    submission_data: Dict[str, Any],
    employee_data: Dict[str, Any],
    template_sections: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """
    Generate a branded PDF for any form type using its template sections/fields.

    If *template_sections* (the ``sections`` list from ``FORM_BASED_REQUIREMENTS``)
    is provided the PDF uses the proper section titles and field labels.
    Otherwise it falls back to a simple key→value dump.

    Returns raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = create_pdf_styles()
    elements = []

    # ── Header with logo ────────────────────────────────────────────────
    logo = get_logo_image()
    if logo:
        elements.append(logo)
        elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph("Osabea Healthcare Solutions", styles["CompanyName"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5 * mm))

    # Form title
    title = form_name or form_type.replace("_", " ").title()
    elements.append(Paragraph(title, styles["FormTitle"]))

    # ── Employee info table ─────────────────────────────────────────────
    emp_name = (
        f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip()
        or employee_data.get("name", "Unknown")
    )
    emp_code = (
        employee_data.get("employee_code")
        or employee_data.get("applicant_reference")
        or employee_data.get("id", "")[:8]
    )
    submitted_at = submission_data.get("_submitted_at") or submission_data.get("submitted_at", "")
    if submitted_at:
        try:
            submitted_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00")).strftime("%d %B %Y %H:%M")
        except Exception:
            pass

    info_rows = [
        ["Employee:", emp_name],
        ["Employee ID:", emp_code],
    ]
    if submitted_at:
        info_rows.append(["Submitted:", submitted_at])

    info_table = Table(info_rows, colWidths=[35 * mm, 135 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), TEXT_SECONDARY),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT_PRIMARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=6 * mm))

    # ── Body: structured sections or raw dump ───────────────────────────
    if form_type == "interview_record" and (
        submission_data.get("format_version") == "v2_osabea" or submission_data.get("assessment_items")
    ):
        elements.extend(generate_scored_interview_pdf_content(submission_data, styles))
    elif template_sections:
        for section in template_sections:
            section_title = section.get("title", "")
            if section_title:
                elements.append(Paragraph(section_title, styles["SectionHeader"]))

            fields = section.get("fields", [])
            if not fields:
                continue

            table_rows = []
            for field in fields:
                if field.get("type") == "info":
                    continue

                field_id = field.get("id", "")
                label = field.get("label", field_id.replace("_", " ").title())
                raw = submission_data.get(field_id)

                # Format value
                if raw is None:
                    val = "N/A"
                elif isinstance(raw, bool):
                    val = "Yes" if raw else "No"
                elif isinstance(raw, list):
                    val = ", ".join(str(v) for v in raw)
                elif isinstance(raw, dict):
                    parts = [f"{k}: {v}" for k, v in raw.items()]
                    val = "; ".join(parts) if parts else "N/A"
                else:
                    val = str(raw) if raw != "" else "N/A"

                # Checkboxes render as tick/cross
                if field.get("type") == "checkbox":
                    val = "\u2713 Yes" if raw else "\u2717 No"

                table_rows.append([
                    Paragraph(label, styles["FieldLabel"]),
                    Paragraph(val, styles["FieldValue"]),
                ])

            if table_rows:
                t = Table(table_rows, colWidths=[75 * mm, 95 * mm])
                t.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 3 * mm))
    else:
        # Fallback: raw key→value dump (for form types without a template)
        elements.extend(generate_generic_pdf_content(submission_data, styles))

    # ── Footer ──────────────────────────────────────────────────────────
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5 * mm))
    footer_text = f"Generated by Osabea Healthcare Solutions Compliance System on {datetime.now(timezone.utc).strftime('%d %B %Y %H:%M UTC')}"
    elements.append(Paragraph(footer_text, styles["Footer"]))
    elements.append(Paragraph("This is an official compliance document. Store securely.", styles["Footer"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_staff_meeting_record_pdf(
    meeting_data: Dict[str, Any],
    attendee_names: Optional[List[str]] = None,
    admin_data: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generate branded PDF evidence for an admin staff meeting record."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = create_pdf_styles()
    elements = []

    logo = get_logo_image()
    if logo:
        elements.append(logo)
        elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph("Osabea Healthcare Solutions", styles["CompanyName"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5 * mm))
    elements.append(Paragraph("Staff Meeting Record", styles["FormTitle"]))

    meeting_date = _pdf_value(meeting_data.get("meeting_date"))
    meeting_type = _pdf_value(meeting_data.get("meeting_type")).replace("_", " ")
    next_meeting_date = _pdf_value(meeting_data.get("next_meeting_date"))
    actions_status = _pdf_value(meeting_data.get("actions_status") or "open")

    info_rows = [
        ["Meeting Date", meeting_date],
        ["Meeting Type", meeting_type],
        ["Next Meeting Date", next_meeting_date],
        ["Actions Status", actions_status],
    ]
    info_table = Table(info_rows, colWidths=[45 * mm, 125 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))

    attendees = attendee_names or []
    attendee_value = "<br/>".join([escape(name) for name in attendees]) if attendees else "No attendees recorded"
    elements.append(Paragraph("Attendees", styles["SectionHeader"]))
    elements.append(Paragraph(attendee_value, styles["Notes"]))

    elements.append(Paragraph("Agenda", styles["SectionHeader"]))
    elements.append(Paragraph(_pdf_value(meeting_data.get("agenda")), styles["Notes"]))

    elements.append(Paragraph("Minutes / Notes", styles["SectionHeader"]))
    elements.append(Paragraph(_pdf_value(meeting_data.get("notes")), styles["Notes"]))

    elements.append(Paragraph("Actions Required", styles["SectionHeader"]))
    elements.append(Paragraph(_pdf_value(meeting_data.get("actions_required")), styles["Notes"]))

    elements.append(Paragraph("Record Timestamps", styles["SectionHeader"]))
    timestamp_rows = [
        ["Created At", _pdf_value(meeting_data.get("created_at"))],
        ["Updated At", _pdf_value(meeting_data.get("updated_at"))],
        ["Actions Closed At", _pdf_value(meeting_data.get("actions_closed_at"))],
        ["Actions Closed By", _pdf_value(meeting_data.get("actions_closed_by"))],
    ]
    timestamp_table = Table(timestamp_rows, colWidths=[45 * mm, 125 * mm])
    timestamp_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    elements.append(timestamp_table)

    downloaded_by = _pdf_value((admin_data or {}).get("downloaded_by"))
    downloaded_at = _pdf_value((admin_data or {}).get("downloaded_at"))
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5 * mm))
    elements.append(Paragraph(f"Downloaded by: {downloaded_by}", styles["Footer"]))
    elements.append(Paragraph(f"Downloaded at: {downloaded_at}", styles["Footer"]))
    elements.append(Paragraph("This is an official compliance document. Store securely.", styles["Footer"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_employer_audit_record_pdf(
    audit_data: Dict[str, Any],
    admin_data: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generate branded PDF evidence for an employer/provider audit checklist record."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = create_pdf_styles()
    elements = []

    logo = get_logo_image()
    if logo:
        elements.append(logo)
        elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph("Osabea Healthcare Solutions", styles["CompanyName"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5 * mm))
    elements.append(Paragraph("Employer Audit / Checklist Record", styles["FormTitle"]))

    info_rows = [
        ["Audit Type", _pdf_value(audit_data.get("audit_type")).replace("_", " ")],
        ["Audit Date", _pdf_value(audit_data.get("audit_date"))],
        ["Completed By", _pdf_value(audit_data.get("completed_by"))],
        ["Overall Outcome", _pdf_value(audit_data.get("overall_outcome")).replace("_", " ")],
        ["Status", _pdf_value(audit_data.get("status"))],
        ["Next Review Date", _pdf_value(audit_data.get("next_review_date"))],
    ]
    info_table = Table(info_rows, colWidths=[50 * mm, 120 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Findings", styles["SectionHeader"]))
    elements.append(Paragraph(_pdf_value(audit_data.get("findings")), styles["Notes"]))

    elements.append(Paragraph("Actions Required", styles["SectionHeader"]))
    elements.append(Paragraph(_pdf_value(audit_data.get("actions_required")), styles["Notes"]))

    elements.append(Paragraph("Record Timestamps", styles["SectionHeader"]))
    timestamp_rows = [
        ["Created At", _pdf_value(audit_data.get("created_at"))],
        ["Updated At", _pdf_value(audit_data.get("updated_at"))],
        ["Closed At", _pdf_value(audit_data.get("closed_at"))],
        ["Closed By", _pdf_value(audit_data.get("closed_by"))],
    ]
    timestamp_table = Table(timestamp_rows, colWidths=[50 * mm, 120 * mm])
    timestamp_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER_COLOR),
    ]))
    elements.append(timestamp_table)

    downloaded_by = _pdf_value((admin_data or {}).get("downloaded_by"))
    downloaded_at = _pdf_value((admin_data or {}).get("downloaded_at"))
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5 * mm))
    elements.append(Paragraph(f"Downloaded by: {downloaded_by}", styles["Footer"]))
    elements.append(Paragraph(f"Downloaded at: {downloaded_at}", styles["Footer"]))
    elements.append(Paragraph("This is an official compliance document. Store securely.", styles["Footer"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_service_user_care_plan_pdf(
    care_plan_data: Dict[str, Any],
    service_user_data: Optional[Dict[str, Any]] = None,
    admin_data: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generate branded PDF evidence for a single service-user care plan version."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = create_pdf_styles()
    elements = []

    logo = get_logo_image()
    if logo:
        elements.append(logo)
        elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph("Osabea Healthcare Solutions", styles["CompanyName"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=5 * mm))
    elements.append(Paragraph("Service User Care Plan", styles["FormTitle"]))

    service_user_name = _pdf_value((service_user_data or {}).get("full_name"))
    service_user_code = _pdf_value((service_user_data or {}).get("service_user_code"))
    info_rows = [
        ["Field", "Details"],
        ["Service User", service_user_name],
        ["Service User Code", service_user_code],
        ["Care Plan Title", _pdf_value(care_plan_data.get("care_plan_title"))],
        ["Version Number", _pdf_value(care_plan_data.get("version_number"))],
        ["Status", _pdf_value(care_plan_data.get("status"))],
    ]
    info_table = Table(info_rows, colWidths=[50 * mm, 120 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, BORDER_COLOR),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_COLOR),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))

    goals = care_plan_data.get("goals") or []
    if isinstance(goals, list):
        goals_text = "<br/>".join([f"- {_pdf_value(goal)}" for goal in goals]) if goals else "N/A"
    else:
        goals_text = _pdf_value(goals)

    elements.append(Paragraph("Goals", styles["SectionHeader"]))
    elements.append(Paragraph(goals_text, styles["Notes"]))

    elements.append(Paragraph("Needs Summary", styles["SectionHeader"]))
    elements.append(Paragraph(_pdf_value(care_plan_data.get("needs_summary")), styles["Notes"]))

    elements.append(Paragraph("Support Instructions", styles["SectionHeader"]))
    elements.append(Paragraph(_pdf_value(care_plan_data.get("support_instructions")), styles["Notes"]))

    elements.append(Paragraph("Lifecycle Dates", styles["SectionHeader"]))
    lifecycle_rows = [
        ["Lifecycle Field", "Value"],
        ["Effective From", _pdf_value(care_plan_data.get("effective_from"))],
        ["Review Due Date", _pdf_value(care_plan_data.get("review_due_at"))],
        ["Created At", _pdf_value(care_plan_data.get("created_at"))],
        ["Approved At", _pdf_value(care_plan_data.get("approved_at"))],
        ["Updated At", _pdf_value(care_plan_data.get("updated_at"))],
    ]
    lifecycle_table = Table(lifecycle_rows, colWidths=[50 * mm, 120 * mm])
    lifecycle_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, BORDER_COLOR),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_COLOR),
    ]))
    elements.append(lifecycle_table)

    downloaded_by = _pdf_value((admin_data or {}).get("downloaded_by"))
    downloaded_at = _pdf_value((admin_data or {}).get("downloaded_at"))
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=5 * mm))
    elements.append(Paragraph(f"Downloaded by: {downloaded_by}", styles["Footer"]))
    elements.append(Paragraph(f"Downloaded at: {downloaded_at}", styles["Footer"]))
    elements.append(Paragraph("This is an official care-plan evidence document. Store securely.", styles["Footer"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# SMART VERIFICATION SYSTEM - PDF Generation & Stamping
# =============================================================================

import fitz  # PyMuPDF - for stamping existing PDFs

class VerificationPDFGenerator:
    """Generates verification record PDFs for the Smart Verification System"""
    
    def __init__(self, company_name="Osabea Healthcare"):
        self.company_name = company_name
        self.styles = getSampleStyleSheet()
        self._setup_verification_styles()
    
    def _setup_verification_styles(self):
        """Setup custom styles for verification PDFs"""
        self.styles.add(ParagraphStyle(
            name='VerifMainTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=PRIMARY_COLOR,
            alignment=TA_CENTER,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='VerifSubTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=TEXT_SECONDARY,
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='VerifSectionHeader',
            parent=self.styles['Heading2'],
            fontSize=11,
            textColor=PRIMARY_COLOR,
            spaceBefore=15,
            spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='VerifChecklistItem',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='VerifApprovedBadge',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=HexColor('#16a34a'),  # Green
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='VerifFooter',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=TEXT_SECONDARY,
            alignment=TA_CENTER
        ))
    
    def generate_verification_pdf(
        self,
        employee_data: dict,
        requirement_id: str,
        requirement_label: str,
        checklist_data: dict,
        ai_extraction: dict = None,
        verification_method: str = None,
        admin_name: str = None,
        admin_notes: str = None,
        verification_id: str = None,
        verified_at: str = None
    ) -> bytes:
        """Generate a complete verification record PDF"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        elements = []
        
        # Logo
        logo = get_logo_image(width=40*mm, height=16*mm)
        if logo:
            elements.append(logo)
            elements.append(Spacer(1, 10))
        
        # Header
        elements.append(Paragraph(
            f"<b>{self.company_name.upper()}</b>",
            self.styles['VerifMainTitle']
        ))
        elements.append(Paragraph(
            "VERIFICATION RECORD",
            self.styles['VerifMainTitle']
        ))
        elements.append(Paragraph(
            f"Document Type: {requirement_label}",
            self.styles['VerifSubTitle']
        ))
        
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=15))
        
        # Employee Details
        elements.append(Paragraph("EMPLOYEE DETAILS", self.styles['VerifSectionHeader']))
        
        emp_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip()
        emp_table = Table([
            ["Name:", emp_name],
            ["Employee Code:", employee_data.get('employee_code') or employee_data.get('applicant_reference') or 'N/A'],
            ["Email:", employee_data.get('email', 'N/A')],
            ["Requirement:", requirement_label],
        ], colWidths=[100, 350])
        emp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(emp_table)
        
        # AI Extraction Results (if available)
        if ai_extraction and any(ai_extraction.values()):
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("AI DOCUMENT ANALYSIS", self.styles['VerifSectionHeader']))
            
            ai_rows = []
            if ai_extraction.get('extracted_name'):
                ai_rows.append(["Extracted Name:", ai_extraction['extracted_name']])
            if ai_extraction.get('extracted_address'):
                ai_rows.append(["Extracted Address:", ai_extraction['extracted_address']])
            if ai_extraction.get('extracted_date'):
                ai_rows.append(["Document Date:", ai_extraction['extracted_date']])
            if ai_extraction.get('document_type'):
                ai_rows.append(["Document Type:", ai_extraction['document_type']])
            
            if ai_rows:
                ai_table = Table(ai_rows, colWidths=[120, 330])
                ai_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                elements.append(ai_table)
            
            # Validation indicators
            validation = ai_extraction.get('validation_results', {})
            confidence = ai_extraction.get('confidence_scores', {})
            
            if validation:
                elements.append(Spacer(1, 6))
                for key, passed in validation.items():
                    if passed is None:
                        continue
                    check = "✓" if passed else "✗"
                    color = '#16a34a' if passed else '#dc2626'
                    label = key.replace('_', ' ').title()
                    
                    if key == 'name_match' and 'name_match' in confidence:
                        label = f"Name Match: {confidence['name_match']}% confidence"
                    elif key == 'address_match':
                        label = f"Address Match: {'Match' if passed else 'Mismatch'}"
                    elif key == 'date_valid':
                        label = f"Date Valid: {'Within 6 months' if passed else 'Older than 6 months'}"
                    
                    elements.append(Paragraph(
                        f"<font color='{color}'>{check} {label}</font>",
                        self.styles['VerifChecklistItem']
                    ))
        
        # Verification Checklist
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("ADMIN VERIFICATION CHECKLIST", self.styles['VerifSectionHeader']))
        
        method_labels = {
            'in_person': 'In Person - Original Document Seen',
            'video_call': 'Video Call Verification',
            'online_check': 'Online Check (gov.uk / DBS Update Service)'
        }
        elements.append(Paragraph(
            f"<b>Verification Method:</b> {method_labels.get(verification_method, verification_method or 'Not specified')}",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 8))
        
        # Checklist items
        checklist_fields = self._get_checklist_fields(requirement_id)
        for field_id, field_label in checklist_fields.items():
            value = checklist_data.get(field_id, False)
            check = "✓" if value else "☐"
            color = '#16a34a' if value else '#6b7280'
            elements.append(Paragraph(
                f"<font color='{color}'>[{check}] {field_label}</font>",
                self.styles['VerifChecklistItem']
            ))
        
        # Admin notes
        if admin_notes:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("<b>Admin Notes:</b>", self.styles['Normal']))
            elements.append(Paragraph(f"<i>{admin_notes}</i>", self.styles['Normal']))
        
        # Approval section
        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=10))
        elements.append(Paragraph("VERIFICATION APPROVAL", self.styles['VerifSectionHeader']))
        
        # Format date
        if verified_at:
            try:
                if isinstance(verified_at, str):
                    dt = datetime.fromisoformat(verified_at.replace('Z', '+00:00'))
                else:
                    dt = verified_at
                formatted_date = dt.strftime("%d %B %Y, %H:%M GMT")
            except Exception:
                formatted_date = str(verified_at)
        else:
            formatted_date = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M GMT")
        
        approval_table = Table([
            ["Verified By:", admin_name or 'System'],
            ["Verified At:", formatted_date],
            ["Verification ID:", verification_id or 'N/A'],
        ], colWidths=[100, 350])
        approval_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(approval_table)
        
        # Approved badge
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("[ ✓ APPROVED ]", self.styles['VerifApprovedBadge']))
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=8))
        elements.append(Paragraph(
            "This document is system-generated and forms part of the employee's "
            "compliance file for CQC audit purposes.",
            self.styles['VerifFooter']
        ))
        elements.append(Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%d %B %Y, %H:%M GMT')}",
            self.styles['VerifFooter']
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _get_checklist_fields(self, requirement_id: str) -> dict:
        """Get checklist field labels for a requirement type"""
        fields = {
            'identity': {
                'photo_matches_applicant': 'Photo matches the applicant',
                'security_features_verified': 'Security features verified (hologram, watermark, chip)',
                'document_appears_genuine': 'Document appears genuine (not altered)',
                'expiry_date_valid': 'Expiry date is valid',
                'details_match_profile': 'Details match employee profile',
            },
            'proof_of_address': {
                'address_matches_declared': 'Address matches declared address',
                'document_within_6_months': 'Document dated within 6 months',
                'document_type_acceptable': 'Document type is acceptable',
                'name_matches_employee': 'Name on document matches employee',
                'document_appears_genuine': 'Document appears genuine',
            },
            'right_to_work': {
                'share_code_verified': 'Share code verified on gov.uk',
                'right_to_work_confirmed': 'Right to work confirmed',
                'details_match_profile': 'Details match employee profile',
            },
            'dbs': {
                'dbs_update_service_checked': 'Certificate verified on DBS Update Service',
                'certificate_number_matches': 'Certificate number matches uploaded document',
                'details_match_profile': 'Details match employee profile',
            }
        }
        return fields.get(requirement_id, {})


class EvidenceStamper:
    """Stamps existing PDF documents with verification watermark"""
    
    STAMP_WIDTH = 150
    STAMP_HEIGHT = 60
    
    def stamp_pdf(
        self,
        pdf_bytes: bytes,
        admin_name: str,
        verified_at: str,
        verification_id: str,
        position: str = "top-right"
    ) -> bytes:
        """Add verification stamp to an existing PDF"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Parse date
            if verified_at:
                try:
                    if isinstance(verified_at, str):
                        dt = datetime.fromisoformat(verified_at.replace('Z', '+00:00'))
                    else:
                        dt = verified_at
                    date_str = dt.strftime("%d %b %Y")
                except Exception:
                    date_str = str(verified_at)[:10]
            else:
                date_str = datetime.now(timezone.utc).strftime("%d %b %Y")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_rect = page.rect
                
                margin = 10
                if position == "top-right":
                    x = page_rect.width - self.STAMP_WIDTH - margin
                    y = margin
                elif position == "top-left":
                    x = margin
                    y = margin
                elif position == "bottom-right":
                    x = page_rect.width - self.STAMP_WIDTH - margin
                    y = page_rect.height - self.STAMP_HEIGHT - margin
                else:
                    x = margin
                    y = page_rect.height - self.STAMP_HEIGHT - margin
                
                stamp_rect = fitz.Rect(x, y, x + self.STAMP_WIDTH, y + self.STAMP_HEIGHT)
                
                # Draw stamp background
                shape = page.new_shape()
                shape.draw_rect(stamp_rect)
                shape.finish(color=(0.1, 0.3, 0.5), fill=(1, 1, 1), width=1.5)
                shape.commit()
                
                # Add stamp text
                page.insert_text(
                    fitz.Point(x + 8, y + 15),
                    "✓ VERIFIED",
                    fontsize=12,
                    fontname="helv",
                    color=(0.086, 0.639, 0.290)
                )
                
                page.insert_text(
                    fitz.Point(x + 8, y + 28),
                    f"By: {admin_name[:25]}",
                    fontsize=8,
                    fontname="helv",
                    color=(0.3, 0.3, 0.3)
                )
                
                page.insert_text(
                    fitz.Point(x + 8, y + 40),
                    f"Date: {date_str}",
                    fontsize=8,
                    fontname="helv",
                    color=(0.3, 0.3, 0.3)
                )
                
                page.insert_text(
                    fitz.Point(x + 8, y + 52),
                    f"ID: {verification_id[:20]}",
                    fontsize=7,
                    fontname="helv",
                    color=(0.5, 0.5, 0.5)
                )
            
            output = io.BytesIO()
            doc.save(output)
            doc.close()
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            import logging
            logging.error(f"Error stamping PDF: {e}")
            return pdf_bytes
    
    def stamp_image(
        self,
        image_bytes: bytes,
        admin_name: str,
        verified_at: str,
        verification_id: str
    ) -> bytes:
        """Convert image to PDF and stamp it"""
        try:
            from PIL import Image as PILImage
            
            img = PILImage.open(io.BytesIO(image_bytes))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            pdf_buffer = io.BytesIO()
            img.save(pdf_buffer, format='PDF')
            pdf_buffer.seek(0)
            
            return self.stamp_pdf(
                pdf_buffer.getvalue(),
                admin_name,
                verified_at,
                verification_id
            )
        except Exception as e:
            import logging
            logging.error(f"Error stamping image: {e}")
            return image_bytes


# Convenience functions
def generate_verification_pdf(
    employee_data: dict,
    requirement_id: str,
    requirement_label: str,
    checklist_data: dict,
    **kwargs
) -> bytes:
    """Generate a verification record PDF"""
    generator = VerificationPDFGenerator()
    return generator.generate_verification_pdf(
        employee_data=employee_data,
        requirement_id=requirement_id,
        requirement_label=requirement_label,
        checklist_data=checklist_data,
        **kwargs
    )


def stamp_evidence_document(
    document_bytes: bytes,
    admin_name: str,
    verified_at: str,
    verification_id: str,
    is_image: bool = False
) -> bytes:
    """Stamp an evidence document with verification watermark"""
    stamper = EvidenceStamper()
    if is_image:
        return stamper.stamp_image(document_bytes, admin_name, verified_at, verification_id)
    return stamper.stamp_pdf(document_bytes, admin_name, verified_at, verification_id)
