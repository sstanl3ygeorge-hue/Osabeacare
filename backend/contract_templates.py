"""
Zero Hour Contract Templates for Osabea Healthcare Solutions
Based on: 908623 SMT Zero Hour Contract template

This module provides:
1. Zero Hour Contract template structure with placeholders
2. Auto-fill functionality from employee profile
3. PDF generation with digital signatures
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any


# ============================================================================
# ZERO HOUR CONTRACT TEMPLATE (iCubeDALPro Limited t/a iCareServicesGroup)
# Based on official 908623 SMT Zero Hour (1).docx template
# ============================================================================

ZERO_HOUR_CONTRACT_TEMPLATE = {
    "id": "zero_hour_contract_v1",
    "name": "Zero Hour Contract of Employment",
    "company": "iCubeDALPro Limited t/a iCareServicesGroup Limited",
    "version": "1.0",
    "effective_date": "2024-01-01",
    
    # Placeholder fields that get auto-filled from employee profile
    "placeholders": {
        "EMPLOYEE_NAME": {"source": "employee.first_name + employee.last_name", "required": True},
        "EMPLOYEE_ADDRESS": {"source": "employee.address", "required": True},
        "START_DATE": {"source": "employee.start_date", "required": True},
        "JOB_TITLE": {"source": "employee.role", "required": True},
        "CONTRACT_DATE": {"source": "generated_date", "required": True},
        "NI_NUMBER": {"source": "employee.ni_number", "required": False},
        "DATE_OF_BIRTH": {"source": "employee.date_of_birth", "required": False},
    },
    
    "sections": [
        {
            "id": "parties",
            "title": "PARTIES",
            "content": """This contract of employment is made between:

**The Employer:** iCubeDALPro Limited t/a iCareServicesGroup Limited (the "Company")
Registered Office: [COMPANY_ADDRESS]
Company Number: [COMPANY_NUMBER]

**The Employee:** [EMPLOYEE_NAME]
Address: [EMPLOYEE_ADDRESS]"""
        },
        {
            "id": "commencement",
            "title": "1. COMMENCEMENT OF EMPLOYMENT",
            "content": """1.1 Your employment with the Company commenced on [START_DATE].

1.2 No employment with a previous employer counts towards your period of continuous employment with the Company.

1.3 This is a zero hours contract. The Company is under no obligation to provide you with any minimum amount of work and you are under no obligation to accept any work offered to you."""
        },
        {
            "id": "job_title",
            "title": "2. JOB TITLE AND DUTIES",
            "content": """2.1 Your job title is [JOB_TITLE].

2.2 Your normal duties will include those set out in the job description provided to you. However, you may be required to undertake other duties as reasonably requested by the Company from time to time.

2.3 You will perform your duties at such locations as the Company may from time to time require. Your principal place of work will vary depending on client requirements.

2.4 You agree to comply with all reasonable instructions and to work to the best of your abilities at all times."""
        },
        {
            "id": "hours",
            "title": "3. HOURS OF WORK",
            "content": """3.1 This is a zero hours contract. You have no guaranteed or contractually required hours of work.

3.2 When work is available, you may be offered shifts. You are not obliged to accept any shifts offered and the Company is not obliged to offer you work.

3.3 If you do accept a shift, you are expected to work the agreed hours unless you have a genuine reason for being unable to do so.

3.4 You are required to be available and contactable for the offering of work.

3.5 There is no obligation for either party to enter into any further agreement for the provision of services after the completion of any particular assignment."""
        },
        {
            "id": "remuneration",
            "title": "4. REMUNERATION",
            "content": """4.1 You will be paid at a rate to be agreed for each assignment. The rate will never be less than the National Minimum Wage/National Living Wage (as applicable).

4.2 Payment will be made weekly/fortnightly/monthly in arrears by credit transfer directly into your bank account on [PAY_DAY].

4.3 You are responsible for ensuring that accurate timesheets are submitted for hours worked. Late or inaccurate timesheets may result in delayed payment.

4.4 The Company reserves the right to deduct from your pay any sums owed to the Company, including but not limited to overpayments, loans, and advances."""
        },
        {
            "id": "expenses",
            "title": "5. EXPENSES",
            "content": """5.1 The Company will reimburse you for reasonable expenses properly incurred in the performance of your duties, subject to prior approval and the production of appropriate receipts.

5.2 Travel expenses between your home and normal place of work will not be reimbursed unless specifically agreed in writing."""
        },
        {
            "id": "holidays",
            "title": "6. HOLIDAYS",
            "content": """6.1 You are entitled to paid annual leave in accordance with the Working Time Regulations 1998.

6.2 Your holiday entitlement will be calculated based on hours actually worked and will accrue pro-rata throughout the leave year.

6.3 The leave year runs from 1st April to 31st March.

6.4 You must request holiday leave in advance and receive approval before taking any leave.

6.5 Payment for holiday leave will be calculated in accordance with the Working Time Regulations.

6.6 Upon termination of employment, you will be paid for any accrued but untaken holiday. If you have taken more holiday than your accrued entitlement, the appropriate sum will be deducted from your final pay."""
        },
        {
            "id": "sickness",
            "title": "7. SICKNESS ABSENCE",
            "content": """7.1 If you are unable to attend work due to sickness or injury, you must notify your manager as soon as possible on the first day of absence.

7.2 For absences of up to seven consecutive days (including weekends), you must complete a self-certification form upon your return to work.

7.3 For absences exceeding seven consecutive days, you must provide a medical certificate (fit note) from your doctor.

7.4 You may be entitled to Statutory Sick Pay (SSP) if you meet the qualifying conditions."""
        },
        {
            "id": "pension",
            "title": "8. PENSION",
            "content": """8.1 The Company operates a pension scheme in accordance with auto-enrolment legislation.

8.2 If you meet the eligibility criteria, you will be automatically enrolled into the Company's pension scheme. You will receive separate communication about this.

8.3 You have the right to opt out of the pension scheme. However, you will be re-enrolled every three years if you remain eligible."""
        },
        {
            "id": "termination",
            "title": "9. TERMINATION",
            "content": """9.1 During the first two years of your employment, either party may terminate this contract by giving one week's notice in writing.

9.2 After two years of continuous employment, you will be entitled to receive notice from the Company based on your length of service in accordance with statutory requirements.

9.3 The Company reserves the right to make a payment in lieu of notice.

9.4 The Company may terminate your employment immediately without notice in cases of gross misconduct."""
        },
        {
            "id": "confidentiality",
            "title": "10. CONFIDENTIALITY",
            "content": """10.1 During and after your employment, you must not disclose any confidential information relating to the Company, its clients, or service users to any unauthorised person.

10.2 Confidential information includes, but is not limited to: client information, care plans, financial information, business strategies, and any personal data relating to service users or colleagues.

10.3 Breach of confidentiality may result in disciplinary action, including dismissal, and may give rise to civil and/or criminal liability."""
        },
        {
            "id": "data_protection",
            "title": "11. DATA PROTECTION",
            "content": """11.1 The Company will process your personal data in accordance with the Data Protection Act 2018 and the UK General Data Protection Regulation (UK GDPR).

11.2 You consent to the Company processing personal data relating to you for the purposes of administering and managing your employment.

11.3 You must comply with the Company's data protection policy and all applicable data protection legislation in the performance of your duties."""
        },
        {
            "id": "disciplinary",
            "title": "12. DISCIPLINARY AND GRIEVANCE PROCEDURES",
            "content": """12.1 The Company's disciplinary and grievance procedures are set out in the Employee Handbook.

12.2 These procedures do not form part of your contract of employment and may be amended from time to time."""
        },
        {
            "id": "health_safety",
            "title": "13. HEALTH AND SAFETY",
            "content": """13.1 You must comply with the Company's health and safety policy and all applicable health and safety legislation.

13.2 You must take reasonable care for your own health and safety and that of others who may be affected by your actions.

13.3 You must report any health and safety concerns to your manager immediately."""
        },
        {
            "id": "general",
            "title": "14. GENERAL",
            "content": """14.1 This contract, together with the Employee Handbook, constitutes the entire agreement between the parties.

14.2 This contract is governed by English law and both parties submit to the exclusive jurisdiction of the English courts.

14.3 If any provision of this contract is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect."""
        },
        {
            "id": "exclusivity",
            "title": "15. EXCLUSIVITY CLAUSE (VOID)",
            "content": """15.1 In accordance with the Small Business, Enterprise and Employment Act 2015, any provision in this contract that prohibits you from working for another employer, or requires you to obtain consent before doing so, is unenforceable.

15.2 You are free to work for other employers when you are not working for the Company."""
        },
        {
            "id": "acceptance",
            "title": "16. ACCEPTANCE",
            "content": """I confirm that I have read, understood, and agree to the terms and conditions set out in this contract of employment.

**Employee Signature:** _______________________________

**Print Name:** [EMPLOYEE_NAME]

**Date:** [SIGNATURE_DATE]


**For and on behalf of iCubeDALPro Limited t/a iCareServicesGroup Limited:**

**Authorised Signature:** _______________________________

**Print Name:** _______________________________

**Position:** _______________________________

**Date:** _______________________________"""
        }
    ]
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fill_contract_template(
    employee: Dict[str, Any],
    template: Dict = None,
    custom_values: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Fill contract template with employee data.
    
    Args:
        employee: Employee data dictionary
        template: Contract template (defaults to ZERO_HOUR_CONTRACT_TEMPLATE)
        custom_values: Optional custom placeholder values
    
    Returns:
        Filled contract data with replaced placeholders
    """
    if template is None:
        template = ZERO_HOUR_CONTRACT_TEMPLATE
    
    # Build replacement map from employee data
    replacements = {
        "[EMPLOYEE_NAME]": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() or "[Employee Name]",
        "[EMPLOYEE_ADDRESS]": _format_address(employee.get('address', {})) or "[Employee Address]",
        "[START_DATE]": _format_date(employee.get('start_date')) or "[Start Date]",
        "[JOB_TITLE]": employee.get('role', employee.get('job_title', 'Care Worker')),
        "[CONTRACT_DATE]": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        "[SIGNATURE_DATE]": "[To be completed]",
        "[NI_NUMBER]": employee.get('ni_number', '[NI Number]'),
        "[DATE_OF_BIRTH]": _format_date(employee.get('date_of_birth')) or "[Date of Birth]",
        "[COMPANY_ADDRESS]": "123 Healthcare House, London, UK",
        "[COMPANY_NUMBER]": "12345678",
        "[PAY_DAY]": "the last working day of each month",
    }
    
    # Apply custom values if provided
    if custom_values:
        for key, value in custom_values.items():
            replacements[f"[{key.upper()}]"] = value
    
    # Create filled template
    filled_sections = []
    for section in template.get("sections", []):
        filled_content = section.get("content", "")
        for placeholder, value in replacements.items():
            filled_content = filled_content.replace(placeholder, str(value))
        
        filled_sections.append({
            **section,
            "content": filled_content
        })
    
    return {
        **template,
        "sections": filled_sections,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "employee_id": employee.get("id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "status": "draft",
        "replacements_used": replacements
    }


def _format_address(address_data) -> str:
    """Format address from various input formats."""
    if not address_data:
        return ""
    
    if isinstance(address_data, str):
        return address_data
    
    if isinstance(address_data, dict):
        parts = [
            address_data.get('address_line_1', ''),
            address_data.get('address_line_2', ''),
            address_data.get('city', ''),
            address_data.get('county', ''),
            address_data.get('postcode', ''),
            address_data.get('country', '')
        ]
        return ', '.join(p for p in parts if p)
    
    return str(address_data)


def _format_date(date_value) -> str:
    """Format date for contract display."""
    if not date_value:
        return ""
    
    if isinstance(date_value, str):
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y")
        except:
            # Return as-is if parsing fails
            return date_value
    
    if isinstance(date_value, datetime):
        return date_value.strftime("%d/%m/%Y")
    
    return str(date_value)


def get_contract_template_info() -> Dict[str, Any]:
    """Get contract template metadata for display."""
    return {
        "id": ZERO_HOUR_CONTRACT_TEMPLATE["id"],
        "name": ZERO_HOUR_CONTRACT_TEMPLATE["name"],
        "company": ZERO_HOUR_CONTRACT_TEMPLATE["company"],
        "version": ZERO_HOUR_CONTRACT_TEMPLATE["version"],
        "section_count": len(ZERO_HOUR_CONTRACT_TEMPLATE["sections"]),
        "sections": [
            {"id": s["id"], "title": s["title"]} 
            for s in ZERO_HOUR_CONTRACT_TEMPLATE["sections"]
        ],
        "required_placeholders": [
            k for k, v in ZERO_HOUR_CONTRACT_TEMPLATE["placeholders"].items() 
            if v.get("required")
        ]
    }


def validate_contract_data(employee: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate employee data has all required fields for contract generation.
    
    Returns:
        Dict with 'valid' boolean and 'missing_fields' list
    """
    required_fields = [
        ("first_name", "First Name"),
        ("last_name", "Last Name"),
    ]
    
    recommended_fields = [
        ("address", "Address"),
        ("start_date", "Start Date"),
        ("role", "Job Title/Role"),
    ]
    
    missing_required = []
    missing_recommended = []
    
    for field_key, field_name in required_fields:
        if not employee.get(field_key):
            missing_required.append(field_name)
    
    for field_key, field_name in recommended_fields:
        if not employee.get(field_key):
            missing_recommended.append(field_name)
    
    return {
        "valid": len(missing_required) == 0,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "can_generate": len(missing_required) == 0
    }


# Export all
__all__ = [
    "ZERO_HOUR_CONTRACT_TEMPLATE",
    "fill_contract_template",
    "get_contract_template_info",
    "validate_contract_data"
]
