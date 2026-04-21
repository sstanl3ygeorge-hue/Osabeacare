"""
Agreement Templates - Real template definitions for structured agreements

Each template defines:
- metadata (id, name, version, description)
- sections (display groups)
- fields (structured input fields with types/validation)
- legal_text (read-only contract content with placeholder substitution)
- declaration (required acknowledgement)
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum


class FieldType(str, Enum):
    TEXT = "text"
    DATE = "date"
    NUMBER = "number"
    CURRENCY = "currency"
    EMAIL = "email"
    PHONE = "phone"
    CHECKBOX = "checkbox"
    SELECT = "select"
    READONLY = "readonly"
    TEXTAREA = "textarea"
    SIGNATURE = "signature"


class AgreementField(BaseModel):
    key: str
    label: str
    field_type: FieldType
    required: bool = True
    placeholder: Optional[str] = None
    default_value: Optional[Any] = None
    options: Optional[List[Dict[str, str]]] = None  # For select fields
    validation: Optional[Dict] = None  # min, max, pattern, etc.
    help_text: Optional[str] = None


class AgreementSection(BaseModel):
    key: str
    title: str
    description: Optional[str] = None
    fields: List[AgreementField]
    read_only: bool = False  # If true, section is display-only (legal text)


class CompletionMode(str, Enum):
    SELF = "self"
    ADMIN_ASSISTED = "admin_assisted"
    PHONE_ASSISTED = "phone_assisted"


# ============================================================================
# ZERO HOUR CONTRACT TEMPLATE V1
# ============================================================================

ZERO_HOUR_CONTRACT_V1 = {
    "template_id": "ZERO_HOUR_CONTRACT_V1",
    "template_name": "Zero Hour Contract - Statement of Main Terms",
    "version": "1.0",
    "version_date": "2024-10-01",
    "description": "Statement of Main Terms of Employment for Zero Hour Contract workers",
    "company_name": "Osabea Healthcare Solutions Ltd",
    "company_address": "Osabea Healthcare Solutions Ltd, Harlow",
    
    "sections": [
        {
            "key": "employee_details",
            "title": "Employee Details",
            "description": "Personal and employment information",
            "read_only": False,
            "fields": [
                {
                    "key": "employee_name",
                    "label": "Full Legal Name",
                    "field_type": "text",
                    "required": True,
                    "placeholder": "Enter your full legal name",
                    "help_text": "As it appears on your official documents"
                },
                {
                    "key": "job_title",
                    "label": "Job Title",
                    "field_type": "text",
                    "required": True,
                    "placeholder": "e.g. Healthcare Assistant, Support Worker"
                },
                {
                    "key": "start_date",
                    "label": "Contract Start Date",
                    "field_type": "date",
                    "required": True,
                    "help_text": "The date this contract starts/started"
                },
                {
                    "key": "continuous_service_date",
                    "label": "Continuous Service Date",
                    "field_type": "date",
                    "required": True,
                    "help_text": "When your continuous employment began"
                }
            ]
        },
        {
            "key": "pay_and_hours",
            "title": "Pay & Hours",
            "description": "Remuneration and working arrangements",
            "read_only": False,
            "fields": [
                {
                    "key": "hourly_rate",
                    "label": "Hourly Rate",
                    "field_type": "currency",
                    "required": True,
                    "placeholder": "e.g. 12.50",
                    "help_text": "Your pay rate per hour in GBP"
                },
                {
                    "key": "sleep_in_rate",
                    "label": "Sleep-in Rate (per night)",
                    "field_type": "currency",
                    "required": False,
                    "default_value": "40.00",
                    "help_text": "Payment for sleeping in at client premises"
                },
                {
                    "key": "payment_method",
                    "label": "Payment Method",
                    "field_type": "readonly",
                    "required": False,
                    "default_value": "Bank Transfer - Monthly in arrears on the last working day of the month"
                }
            ]
        },
        {
            "key": "legal_terms",
            "title": "Legal Terms & Conditions",
            "description": "Read carefully before signing",
            "read_only": True,
            "fields": []
        },
        {
            "key": "holiday_and_leave",
            "title": "Holiday & Leave Entitlement",
            "description": "Annual leave and other paid leave",
            "read_only": True,
            "fields": []
        },
        {
            "key": "declaration",
            "title": "Declaration",
            "description": "Please read and confirm your acceptance",
            "read_only": False,
            "fields": [
                {
                    "key": "confirm_read_statement",
                    "label": "I acknowledge receipt of this Statement and confirm that I have read and understood all terms",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "confirm_read_handbook",
                    "label": "I confirm I have read the Employee Handbook which sets out the principal rules, policies and procedures relating to my employment",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "confirm_holiday_agreement",
                    "label": "For the purpose of statutory holiday entitlement under the Working Time Regulations (as amended), I agree that the holiday section of this Statement will be held to be a 'relevant agreement'",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "signature_name",
                    "label": "Typed Full Name (Signature)",
                    "field_type": "signature",
                    "required": True,
                    "placeholder": "Type your full legal name as signature",
                    "help_text": "This serves as your electronic signature"
                },
                {
                    "key": "signature_date",
                    "label": "Date",
                    "field_type": "date",
                    "required": True
                }
            ]
        }
    ],
    
    "legal_text_sections": {
        "legal_terms": """
## Statement of Main Terms of Employment

This Statement sets out the particulars of main terms of employment under which **Osabea Healthcare Solutions Ltd** (the employer referred to as 'the Company') whose address is Unit 12, Harrods Road, Harlow, CM19 5BJ employs **{{employee_name}}** (referred to as 'employee', 'you', 'your' etc.).

Any changes or amendments to these terms will be confirmed in writing within one month of them occurring.

### Agreements in Force
There are no collective agreements affecting your terms and conditions of employment.

### Job Title
You are employed as **{{job_title}}**. The Company reserves the right to require you to perform other duties from time to time, which may include work in other departments, and it is a condition of your employment that you are prepared to do this.

### Commencement Date
Your employment with the Company under this contract commenced on **{{start_date}}**. Your period of continuous employment began on **{{continuous_service_date}}**.

### Probationary Period
The first 6 months of your employment are served as a probationary period. During this period your work performance and general suitability will be assessed. Receipt of written confirmation will signify that your probationary period has been successfully passed. However, if your work performance is not up to the required standard, or you are considered to be generally unsuitable, we may either extend your probationary period or terminate your employment at any time.

### Criminal Records Checks
Your employment with the Company is conditional upon receipt of a satisfactory enhanced DBS certificate. It will be essential for you to co-operate fully with the application process to obtain future DBS checks, as and when required.

### Notification of Criminal Matters
You are required to notify your Manager immediately if you are questioned or arrested by the police or charged, cautioned, or convicted in connection with any criminal matter. You are also required to notify your Manager immediately if you are suspended from work by any other employer or have any allegations made against you inside or outside of work that could relate to or impact on the safeguarding of children and vulnerable adults.

### Permission to Work in the UK
Where you have a time limit on your right to work in the UK and you provided documents to the company for your initial pre-employment check from List B, the Company will undertake a follow up check.

### Place of Work
Your normal place of work is at the address above. However, you are required to travel to and work at various locations and sites as determined by the needs of the business.

### Pay
Your wage will be paid at the rate of **£{{hourly_rate}}** per hour by Bank Transfer at monthly intervals in arrears on the last working day of the month.

The Company has the right to deduct from your pay, or otherwise to require repayment by other means, any sum which you owe to the Company including, without limitation, any overpayment of pay or expenses, loans made to you by the Company, or any other item identified in this Statement and/or the Employee Handbook as being repayable by you to the Company.

### Hours of Work
Given the nature of the business, your hours of work will vary according to the specific needs of the business. It will not always be possible to provide you with work and you will be notified of any hours required. The Company will endeavour to allocate suitable work to you when such work is available.

The days on which you are required to work are Monday to Sunday. When work is offered on a given day, it will be anytime on the 24 hour clock. You will not be required to work for more than 15 hours per day, or 50 hours per week, or on more than 6 days per week.

If you will be required to sleep in at the clients premises, you will be paid **£{{sleep_in_rate}}** per night.

### Notice
Up to 1 month's service you are required to give the Company 1 week's notice and 2 weeks' notice thereafter to terminate your employment. You are entitled to receive the following periods of notice from the Company to terminate your employment:
- Over 1 month but under 2 years' continuous service - 1 week
- Over 2 years' continuous service - 1 week for each complete year of service to a maximum of 12 weeks after 12 years

### Data Protection
The Company has developed guidelines for the processing of personal data to meet the requirements of current legislation. The Company will keep personal information on you and disclose such information when required in accordance with the Employee Handbook.
        """,
        
        "holiday_and_leave": """
## Holiday & Leave Entitlement

### Holiday Entitlement
You are entitled to **5.6 weeks** of paid annual holiday per holiday year. In your first holiday year your entitlement will be proportionate to the amount of time left in the holiday year.

Given the nature of the business, it will sometimes be necessary for you to work on bank and public holidays, and you will receive payment at your normal rate for those hours worked.

Payment for holidays will be calculated on the basis of your average rate per hour over the 52 paid weeks immediately prior to the holiday.

It is our policy to encourage you to take all of your holiday entitlement in the current holiday year. We do not permit holidays to be carried forward and no payment in lieu will be made in respect of untaken holidays other than in the event of termination of your employment.

### Other Paid Leave Entitlement
You may take the following types of paid leave subject to any qualifying criteria and notification requirements which may apply:
- Maternity, paternity, adoption and shared parental leave with pay in line with statutory entitlements
- Parental bereavement leave with pay in line with statutory entitlements
- Eligible employees are entitled to neonatal care leave and pay in line with statutory entitlements

### Sickness Absence
Payments for periods of absence due to sickness will be made in accordance with the current Statutory Sick Pay (SSP) scheme where applicable. The conditions relating to and the procedure you must follow in the event of periods of absence from work due to sickness are set out in the Employee Handbook.

### Pension
The Company operates a pension scheme that meets the requirements of automatic enrolment and into which you will be enrolled subject to meeting the requirements of the scheme. Further details (including the right to opt-out) are available from your Line Manager.
        """
    }
}


# ============================================================================
# EMPLOYEE HANDBOOK ACKNOWLEDGEMENT TEMPLATE V1
# ============================================================================

EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1 = {
    "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
    "template_name": "Employee Handbook Acknowledgement",
    "version": "1.0",
    "version_date": "2024-10-01",
    "review_date": "2027-03-10",
    "description": "Acknowledgement of receipt and understanding of the Employee Handbook",
    "company_name": "Osabea Healthcare Solutions Ltd",
    "handbook_title": "Osabea Healthcare Solutions Employee Handbook",
    "handbook_issue_date": "October 2024",
    
    "sections": [
        {
            "key": "handbook_details",
            "title": "Handbook Information",
            "description": "Details of the Employee Handbook being acknowledged",
            "read_only": True,
            "fields": [
                {
                    "key": "handbook_title",
                    "label": "Handbook Title",
                    "field_type": "readonly",
                    "required": False,
                    "default_value": "Osabea Healthcare Solutions Employee Handbook"
                },
                {
                    "key": "handbook_version",
                    "label": "Version / Issue Date",
                    "field_type": "readonly",
                    "required": False,
                    "default_value": "October 2024"
                },
                {
                    "key": "handbook_review_date",
                    "label": "Review Date",
                    "field_type": "readonly",
                    "required": False,
                    "default_value": "10/03/2027"
                }
            ]
        },
        {
            "key": "employee_details",
            "title": "Employee Details",
            "description": "Your personal information",
            "read_only": False,
            "fields": [
                {
                    "key": "employee_name",
                    "label": "Full Legal Name",
                    "field_type": "text",
                    "required": True,
                    "placeholder": "Enter your full legal name"
                },
                {
                    "key": "employee_role",
                    "label": "Job Role",
                    "field_type": "text",
                    "required": True,
                    "placeholder": "e.g. Healthcare Assistant, Support Worker"
                }
            ]
        },
        {
            "key": "handbook_contents",
            "title": "Handbook Contents Overview",
            "description": "The Employee Handbook covers the following key areas",
            "read_only": True,
            "fields": []
        },
        {
            "key": "acknowledgements",
            "title": "Acknowledgement Statements",
            "description": "Please confirm each statement below",
            "read_only": False,
            "fields": [
                {
                    "key": "ack_received",
                    "label": "I acknowledge that I have received a copy of the Osabea Healthcare Solutions Employee Handbook dated October 2024",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "ack_read",
                    "label": "I confirm that I have read and understood the contents of the Employee Handbook",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "ack_policies",
                    "label": "I understand that the policies and procedures contained in the Handbook apply to my employment",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "ack_updates",
                    "label": "I understand that the Company reserves the right to amend, modify, or update the Handbook at any time and that I will be notified of any significant changes",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "ack_ask_questions",
                    "label": "I understand that if I have any questions about the Handbook or my employment, I should speak to my Line Manager or HR",
                    "field_type": "checkbox",
                    "required": True
                },
                {
                    "key": "ack_compliance",
                    "label": "I agree to comply with the policies, procedures, and standards set out in the Handbook during my employment",
                    "field_type": "checkbox",
                    "required": True
                }
            ]
        },
        {
            "key": "declaration",
            "title": "Declaration & Signature",
            "description": "Complete your acknowledgement",
            "read_only": False,
            "fields": [
                {
                    "key": "signature_name",
                    "label": "Typed Full Legal Name (Signature)",
                    "field_type": "signature",
                    "required": True,
                    "placeholder": "Type your full legal name as signature",
                    "help_text": "This serves as your electronic signature"
                },
                {
                    "key": "signature_date",
                    "label": "Date",
                    "field_type": "date",
                    "required": True
                }
            ]
        }
    ],
    
    "legal_text_sections": {
        "handbook_contents": """
## Employee Handbook Contents

The Employee Handbook you are acknowledging contains comprehensive information about:

### Joining Our Organisation
- About Osabea Healthcare Solutions Ltd
- Our Values, Aims & Objectives
- Staff Structure

### Pay, Benefits & Pension
- Pay arrangements
- Pension scheme details
- Salary sacrifice options

### Holiday Entitlement & Conditions
- Annual leave entitlement (5.6 weeks)
- Bank holiday arrangements
- Holiday booking procedures

### Sickness/Absence, Payments & Conditions
- Reporting procedures
- Statutory Sick Pay (SSP)
- Return to work process

### Equal Opportunities & Diversity
- Our commitment to equality
- Protected characteristics
- Reporting discrimination

### Anti-Harassment & Bullying
- Definitions and examples
- Reporting procedures
- Support available

### Capability & Disciplinary Procedures
- Performance management
- Disciplinary rules
- Investigation process
- Appeal rights

### Grievance Procedure
- How to raise concerns
- Investigation process
- Resolution steps

### Health, Safety, Welfare & Hygiene
- Your responsibilities
- Reporting accidents
- Fire procedures
- First aid

### Safeguarding
- Your duty to safeguard
- Reporting concerns
- DBS requirements
- Training requirements

### Whistleblowing Procedure
- Protected disclosures
- How to report
- Protection from retaliation

### General Working Conditions
- Working hours
- Dress code
- Personal property
- Social media
- Data protection
- Confidentiality

### Notice to Terminate Employment
- Notice periods
- Return of property
- Final pay arrangements
        """
    }
}


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

AGREEMENT_TEMPLATES = {
    "ZERO_HOUR_CONTRACT_V1": ZERO_HOUR_CONTRACT_V1,
    "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1": EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1,
}


def get_template(template_id: str) -> Optional[Dict]:
    """Get a template by ID"""
    return AGREEMENT_TEMPLATES.get(template_id)


def get_all_templates() -> Dict[str, Dict]:
    """Get all available templates"""
    return AGREEMENT_TEMPLATES


def get_template_summary(template_id: str) -> Optional[Dict]:
    """Get template metadata without full content"""
    template = get_template(template_id)
    if not template:
        return None
    return {
        "template_id": template["template_id"],
        "template_name": template["template_name"],
        "version": template["version"],
        "version_date": template.get("version_date"),
        "description": template.get("description"),
        "company_name": template.get("company_name"),
        "section_count": len(template.get("sections", [])),
    }
