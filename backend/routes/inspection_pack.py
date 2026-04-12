"""
Inspection Pack Generation Routes.

This module handles:
- CQC Inspection Pack generation (ZIP bundle)
- Aggregates existing policies, certificates, and staff data
- Generates cover sheet PDF
"""

import zipfile
from io import BytesIO
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

from .dependencies import get_db, get_current_user, log_audit_action

router = APIRouter(tags=["Inspection Pack"])


@router.get("/inspection-pack/generate")
async def generate_inspection_pack(
    include_policies: bool = True,
    include_certificates: bool = True,
    include_staff_summary: bool = True,
    user: dict = Depends(get_current_user)
):
    """
    Generate CQC Inspection Pack - bundles existing documents for inspector use.
    
    REUSES:
    - org_policies collection (existing governance documents)
    - insurance_docs collection (existing certificates)
    - CQC_EVIDENCE_MAPPING (existing CQC alignment)
    - generate_verification_stamp() (existing verification infrastructure)
    
    NO NEW COLLECTIONS - This aggregates and exports existing data
    
    Returns: ZIP file containing:
    - Cover sheet PDF with organisation summary
    - Policy documents folder
    - Certificates folder
    - Staff compliance summary
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    # Fetch all source data (REUSING existing collections)
    policies = await db.org_policies.find(
        {"status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    certificates = await db.insurance_docs.find(
        {"file_url": {"$ne": None}},
        {"_id": 0}
    ).to_list(50)
    
    # Get organisation stats (REUSING existing queries)
    employee_count = await db.employees.count_documents({"status": {"$in": ["active", "onboarding"]}})
    
    # Calculate work readiness stats
    employees = await db.employees.find(
        {"status": {"$in": ["active", "onboarding"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1}
    ).to_list(500)
    
    ready_count = 0
    supervised_count = 0
    not_ready_count = 0
    
    # Import get_unified_employee_status from server (lazy import)
    from server import get_unified_employee_status
    
    for emp in employees[:50]:  # Limit for performance
        try:
            status = await get_unified_employee_status(emp["id"], db, user_role="admin")
            readiness = status.get("readiness_tier", "NOT_READY")
            if readiness == "WORK_READY":
                ready_count += 1
            elif readiness == "SUPERVISED":
                supervised_count += 1
            else:
                not_ready_count += 1
        except Exception:
            not_ready_count += 1
    
    # Create ZIP file in memory
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Generate Cover Sheet PDF
        cover_buffer = BytesIO()
        doc = SimpleDocTemplate(cover_buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            textColor=colors.HexColor('#0d6c6c')
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#333333')
        )
        
        story = []
        
        # Header
        story.append(Paragraph("CQC INSPECTION PACK", title_style))
        story.append(Paragraph("Osabea Healthcare Solutions", styles['Heading2']))
        story.append(Paragraph(f"Generated: {now.strftime('%d %B %Y at %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Organisation Summary
        story.append(Paragraph("Organisation Summary", heading_style))
        
        org_data = [
            ["Organisation Name:", "Osabea Healthcare Solutions"],
            ["CQC Registration:", "Pending / Active"],
            ["Service Type:", "Domiciliary Care"],
            ["Generated Date:", now.strftime('%d/%m/%Y')],
        ]
        
        org_table = Table(org_data, colWidths=[2.5*inch, 4*inch])
        org_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(org_table)
        story.append(Spacer(1, 20))
        
        # Staff Summary
        story.append(Paragraph("Staff Compliance Summary", heading_style))
        
        staff_data = [
            ["Total Staff:", str(employee_count)],
            ["Work Ready:", str(ready_count)],
            ["Supervised Start:", str(supervised_count)],
            ["In Progress:", str(not_ready_count)],
        ]
        
        staff_table = Table(staff_data, colWidths=[2.5*inch, 4*inch])
        staff_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(staff_table)
        story.append(Spacer(1, 20))
        
        # Pack Contents
        story.append(Paragraph("Pack Contents", heading_style))
        
        contents = []
        if include_policies:
            contents.append(f"Policies: {len(policies)} documents")
        if include_certificates:
            contents.append(f"Certificates: {len(certificates)} documents")
        if include_staff_summary:
            contents.append(f"Staff Summary: {employee_count} employees")
        
        for item in contents:
            story.append(Paragraph(f"• {item}", styles['Normal']))
        
        story.append(Spacer(1, 30))
        
        # Policies List
        if include_policies and policies:
            story.append(Paragraph("Policies Included", heading_style))
            for i, policy in enumerate(policies[:20], 1):
                story.append(Paragraph(
                    f"{i}. {policy.get('name', 'Unnamed')} (v{policy.get('version', '1.0')})",
                    styles['Normal']
                ))
            if len(policies) > 20:
                story.append(Paragraph(f"... and {len(policies) - 20} more", styles['Italic']))
            story.append(Spacer(1, 20))
        
        # Certificates List
        if include_certificates and certificates:
            story.append(Paragraph("Certificates Included", heading_style))
            for i, cert in enumerate(certificates[:10], 1):
                expiry = cert.get('expiry_date', 'No expiry')
                if expiry and 'T' in str(expiry):
                    expiry = expiry[:10]
                story.append(Paragraph(
                    f"{i}. {cert.get('insurance_type', 'Certificate')} - Expires: {expiry}",
                    styles['Normal']
                ))
            story.append(Spacer(1, 20))
        
        # Footer
        story.append(Spacer(1, 40))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
        story.append(Paragraph(
            "This pack was automatically generated by Osabea Compliance Portal. "
            "All documents are current as of the generation date.",
            footer_style
        ))
        
        doc.build(story)
        cover_buffer.seek(0)
        zf.writestr("00_Cover_Sheet.pdf", cover_buffer.getvalue())
        
        # 2. Add Policies (as manifest - actual files would need file storage integration)
        if include_policies:
            policy_manifest = "POLICY MANIFEST\n" + "="*50 + "\n\n"
            for policy in policies:
                policy_manifest += f"Name: {policy.get('name', 'Unnamed')}\n"
                policy_manifest += f"Version: {policy.get('version', '1.0')}\n"
                policy_manifest += f"Effective Date: {policy.get('effective_date', 'N/A')}\n"
                policy_manifest += f"Review Date: {policy.get('review_date', 'N/A')}\n"
                policy_manifest += f"Status: {policy.get('status', 'N/A')}\n"
                if policy.get('file_url'):
                    policy_manifest += f"Document URL: {policy.get('file_url')}\n"
                policy_manifest += "\n" + "-"*30 + "\n\n"
            
            zf.writestr("01_Policies/policy_manifest.txt", policy_manifest)
        
        # 3. Add Certificates manifest
        if include_certificates:
            cert_manifest = "CERTIFICATE MANIFEST\n" + "="*50 + "\n\n"
            for cert in certificates:
                cert_manifest += f"Type: {cert.get('insurance_type', 'Certificate')}\n"
                cert_manifest += f"Provider: {cert.get('provider', 'N/A')}\n"
                cert_manifest += f"Policy Number: {cert.get('policy_number', 'N/A')}\n"
                cert_manifest += f"Expiry Date: {cert.get('expiry_date', 'N/A')}\n"
                if cert.get('file_url'):
                    cert_manifest += f"Document URL: {cert.get('file_url')}\n"
                cert_manifest += "\n" + "-"*30 + "\n\n"
            
            zf.writestr("02_Certificates/certificate_manifest.txt", cert_manifest)
        
        # 4. Add Staff Summary
        if include_staff_summary:
            staff_summary = "STAFF COMPLIANCE SUMMARY\n" + "="*50 + "\n\n"
            staff_summary += f"Generated: {now.strftime('%d %B %Y at %H:%M UTC')}\n\n"
            staff_summary += f"Total Staff: {employee_count}\n"
            staff_summary += f"Work Ready: {ready_count}\n"
            staff_summary += f"Supervised Start: {supervised_count}\n"
            staff_summary += f"In Progress: {not_ready_count}\n\n"
            
            staff_summary += "STAFF LIST\n" + "-"*30 + "\n\n"
            for emp in employees[:100]:
                staff_summary += f"- {emp.get('first_name', '')} {emp.get('last_name', '')} ({emp.get('role', 'N/A')})\n"
            
            if len(employees) > 100:
                staff_summary += f"\n... and {len(employees) - 100} more staff members\n"
            
            zf.writestr("03_Staff/staff_summary.txt", staff_summary)
        
        # 5. Add README
        readme = """CQC INSPECTION PACK
==================

This pack contains compliance documentation for CQC inspection purposes.

CONTENTS:
- 00_Cover_Sheet.pdf - Overview and summary
- 01_Policies/ - Organisation policies
- 02_Certificates/ - Insurance and safety certificates
- 03_Staff/ - Staff compliance summary

NOTES:
- All documents are current as of the generation date
- Policy and certificate files are referenced by URL
- Staff compliance is calculated using the unified compliance engine

For questions, contact: compliance@osabeacares.co.uk

Generated by Osabea Compliance Portal
"""
        zf.writestr("README.txt", readme)
    
    zip_buffer.seek(0)
    
    # Log the action
    await log_audit_action(user['user_id'], "generate_inspection_pack", "organisation", "inspection_pack", {
        "included_policies": include_policies,
        "included_certificates": include_certificates,
        "included_staff_summary": include_staff_summary,
        "policy_count": len(policies),
        "certificate_count": len(certificates),
        "staff_count": employee_count
    })
    
    filename = f"CQC_Inspection_Pack_{now.strftime('%Y%m%d_%H%M%S')}.zip"
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
