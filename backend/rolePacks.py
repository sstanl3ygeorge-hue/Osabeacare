"""
rolePacks.py - Role-Based Requirement Configuration

Single source of truth for what each role needs for compliance.
Used by:
- Requirement generation on application/screening
- Compliance page rendering
- Stage gate checks (recruitment approval)
- Expiry/reminder scheduling
"""

# =============================================================================
# REQUIREMENT TYPES
# =============================================================================
# Not all requirements behave the same way

REQUIREMENT_TYPES = {
    "document": [
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "training_scan"
    ],
    "reference": [
        "reference_1",
        "reference_2"
    ],
    "form": [
        "application_form",
        "equal_opportunities",
        "induction",
        "clinical_competency"
    ],
    "registration": [
        "nmc_registration"
    ],
    "system": [
        "cv"
    ]
}

def get_requirement_type(requirement_key: str) -> str:
    """Get the type category for a requirement key"""
    for req_type, keys in REQUIREMENT_TYPES.items():
        if requirement_key in keys:
            return req_type
    return "document"  # default


# =============================================================================
# REQUIREMENT METADATA
# =============================================================================
# Per-requirement configuration

REQUIREMENT_METADATA = {
    "cv": {
        "label": "CV / Resume",
        "type": "system",
        "required": True,
        "blocking": False,
        "extraction_enabled": True
    },
    "application_form": {
        "label": "Application Form",
        "type": "form",
        "required": True,
        "blocking": True
    },
    "equal_opportunities": {
        "label": "Equal Opportunities Form",
        "type": "form",
        "required": True,
        "blocking": False
    },
    "reference_1": {
        "label": "Reference 1",
        "type": "reference",
        "required": True,
        "blocking": True,
        "integrity_check": True
    },
    "reference_2": {
        "label": "Reference 2",
        "type": "reference",
        "required": True,
        "blocking": True,
        "integrity_check": True
    },
    "right_to_work": {
        "label": "Right to Work",
        "type": "document",
        "required": True,
        "blocking": True,
        "extraction_enabled": True,
        "expiry_tracked": True,
        "check_required": True
    },
    "identity": {
        "label": "Identity",
        "type": "document",
        "required": True,
        "blocking": True,
        "extraction_enabled": True,
        "check_required": True
    },
    "proof_of_address": {
        "label": "Proof of Address",
        "type": "document",
        "required": True,
        "blocking": True,
        "extraction_enabled": True,
        "check_required": True,
        "multi_file": True,
        "min_files": 2,
        "validity_months": 12
    },
    "dbs": {
        "label": "DBS Certificate",
        "type": "document",
        "required": True,
        "blocking": True,
        "extraction_enabled": True,
        "expiry_tracked": True,
        "check_required": True
    },
    "nmc_registration": {
        "label": "NMC Registration",
        "type": "registration",
        "required": True,
        "blocking": True,
        "expiry_tracked": True,
        "verification_required": True
    },
    "training_scan": {
        "label": "Training Certificates",
        "type": "document",
        "required": True,
        "blocking": False,
        "extraction_enabled": True,
        "smart_extraction": True,
        "multi_file": True
    },
    "clinical_competency": {
        "label": "Clinical Competency Assessment",
        "type": "form",
        "required": True,
        "blocking": True
    },
    "induction": {
        "label": "Induction",
        "type": "form",
        "required": True,
        "blocking": True
    }
}


# =============================================================================
# ROLE PACKS
# =============================================================================

ROLE_PACK_HEALTHCARE_ASSISTANT = {
    "role": "healthcare_assistant",
    "label": "Healthcare Assistant",
    "interview_template": "interview_hca_v1",
    
    "requirements": [
        # Application stage
        "cv",
        "application_form",
        "equal_opportunities",
        
        # References
        "reference_1",
        "reference_2",
        
        # Identity & Compliance
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        
        # Training & Induction
        "training_scan",
        "induction"
    ],
    
    "policies": {
        "dbs_required_before_approval": True,
        "poa_validity_months": 12,
        "min_references": 2,
        "rtw_check_required": True
    }
}

ROLE_PACK_NURSE = {
    "role": "nurse",
    "label": "Nurse",
    "interview_template": "interview_nurse_v1",
    
    "requirements": [
        # Application stage
        "cv",
        "application_form",
        "equal_opportunities",
        
        # References
        "reference_1",
        "reference_2",
        
        # Identity & Compliance
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        
        # Professional Registration (key difference)
        "nmc_registration",
        
        # Training & Clinical
        "training_scan",
        "clinical_competency",
        "induction"
    ],
    
    "policies": {
        "dbs_required_before_approval": True,
        "poa_validity_months": 12,
        "min_references": 2,
        "rtw_check_required": True,
        "nmc_required": True
    }
}

ROLE_PACK_CARE_ASSISTANT = {
    "role": "care_assistant",
    "label": "Care Assistant",
    "interview_template": "interview_ca_v1",
    
    "requirements": [
        "cv",
        "application_form",
        "equal_opportunities",
        "reference_1",
        "reference_2",
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "training_scan",
        "induction"
    ],
    
    "policies": {
        "dbs_required_before_approval": True,
        "poa_validity_months": 12,
        "min_references": 2,
        "rtw_check_required": True
    }
}

ROLE_PACK_SENIOR_CARE_ASSISTANT = {
    "role": "senior_care_assistant",
    "label": "Senior Care Assistant",
    "interview_template": "interview_sca_v1",
    
    "requirements": [
        "cv",
        "application_form",
        "equal_opportunities",
        "reference_1",
        "reference_2",
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "training_scan",
        "induction"
    ],
    
    "policies": {
        "dbs_required_before_approval": True,
        "poa_validity_months": 12,
        "min_references": 2,
        "rtw_check_required": True
    }
}

ROLE_PACK_SUPPORT_WORKER = {
    "role": "support_worker",
    "label": "Support Worker",
    "interview_template": "interview_sw_v1",
    
    "requirements": [
        "cv",
        "application_form",
        "equal_opportunities",
        "reference_1",
        "reference_2",
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "training_scan",
        "induction"
    ],
    
    "policies": {
        "dbs_required_before_approval": True,
        "poa_validity_months": 12,
        "min_references": 2,
        "rtw_check_required": True
    }
}


# =============================================================================
# ROLE PACKS REGISTRY
# =============================================================================

ROLE_PACKS = {
    "healthcare_assistant": ROLE_PACK_HEALTHCARE_ASSISTANT,
    "nurse": ROLE_PACK_NURSE,
    "care_assistant": ROLE_PACK_CARE_ASSISTANT,
    "senior_care_assistant": ROLE_PACK_SENIOR_CARE_ASSISTANT,
    "support_worker": ROLE_PACK_SUPPORT_WORKER,
}

def get_role_pack(role: str) -> dict:
    """Get the role pack for a given role, with fallback to healthcare_assistant"""
    return ROLE_PACKS.get(role, ROLE_PACK_HEALTHCARE_ASSISTANT)

def get_role_requirements(role: str) -> list:
    """Get the list of requirements for a role"""
    pack = get_role_pack(role)
    return pack.get("requirements", [])

def get_role_policies(role: str) -> dict:
    """Get the policies for a role"""
    pack = get_role_pack(role)
    return pack.get("policies", {})


# =============================================================================
# EXPIRY RULES
# =============================================================================
# Days before expiry to send reminders

EXPIRY_REMINDER_RULES = {
    "right_to_work": [90, 60, 30, 7],
    "dbs": [90, 60, 30, 7],
    "nmc_registration": [90, 60, 30, 7],
    "training_scan": [90, 60, 30, 7],
    "identity": [90, 60, 30, 7]  # if passport/ID has expiry
}

def get_expiry_reminder_days(requirement_key: str) -> list:
    """Get the reminder schedule for a requirement"""
    return EXPIRY_REMINDER_RULES.get(requirement_key, [30, 7])


# =============================================================================
# STAGE DEFINITIONS
# =============================================================================

RECRUITMENT_STAGES = [
    {"key": "new", "label": "New Application", "order": 1},
    {"key": "screening", "label": "Screening", "order": 2},
    {"key": "interview", "label": "Interview", "order": 3},
    {"key": "compliance_review", "label": "Compliance Review", "order": 4},
    {"key": "onboarding", "label": "Onboarding", "order": 5},
    {"key": "active", "label": "Active", "order": 6},
    {"key": "inactive", "label": "Inactive", "order": 7},
    {"key": "archived", "label": "Archived", "order": 8}
]

APPLICANT_STAGES = ["new", "screening", "interview", "compliance_review"]
EMPLOYEE_STAGES = ["onboarding", "active", "inactive"]


# =============================================================================
# STAGE GATES
# =============================================================================
# Requirements that must be satisfied before moving to next stage

STAGE_GATES = {
    "screening_to_interview": {
        "required_verified": [],
        "required_submitted": ["application_form"]
    },
    "interview_to_compliance_review": {
        "required_verified": [],
        "required_submitted": []
    },
    "compliance_review_to_recruitment_approval": {
        "required_verified": [
            "right_to_work",
            "identity",
            "proof_of_address",
            "dbs",
            "reference_1",
            "reference_2"
        ],
        "role_specific": {
            "nurse": ["nmc_registration"]
        }
    },
    "recruitment_approval_to_onboarding": {
        "required_verified": [],
        "agreements_required": ["contract_acceptance", "handbook_acknowledgement"]
    },
    "onboarding_to_active": {
        "required_verified": ["induction"],
        "role_specific": {
            "nurse": ["clinical_competency"]
        }
    }
}
