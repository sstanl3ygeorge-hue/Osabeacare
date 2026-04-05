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
from typing import Dict, Any, Optional

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
    Returns None if logo URL is not configured or fetch fails.
    """
    if not LOGO_URL:
        return None
    
    try:
        # Handle local file paths
        if LOGO_URL.startswith('/') or LOGO_URL.startswith('./'):
            if os.path.exists(LOGO_URL):
                return Image(LOGO_URL, width=width, height=height)
            return None
        
        # Handle URLs
        response = requests.get(LOGO_URL, timeout=5)
        if response.status_code == 200:
            logo_data = io.BytesIO(response.content)
            return Image(logo_data, width=width, height=height)
    except Exception as e:
        print(f"Failed to load logo: {e}")
    
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
    employee_code = employee_data.get('employee_code', employee_data.get('id', '')[:8])
    
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
