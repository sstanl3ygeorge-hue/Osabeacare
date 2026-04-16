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
