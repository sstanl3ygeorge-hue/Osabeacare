"""
requirement_definitions.py - Requirement metadata definitions

Single source of truth for requirement metadata.
Used by StageGateService to generate requirement slots.
"""

# =============================================================================
# REQUIREMENT DEFINITIONS
# =============================================================================
# Each requirement has metadata that controls its behavior

REQUIREMENT_DEFINITIONS = {
    # ----- SYSTEM -----
    "cv": {
        "key": "cv",
        "label": "CV / Resume",
        "type": "system",
        "category": "Application",
        "blocking": False,
        "supports_files": True,
        "supports_requests": False,
        "extraction_enabled": True,
        "policy": {}
    },
    
    "application_form": {
        "key": "application_form",
        "label": "Application Form",
        "type": "form",
        "category": "Application",
        "blocking": True,
        "supports_files": False,
        "supports_requests": False,
        "policy": {}
    },
    
    "equal_opportunities": {
        "key": "equal_opportunities",
        "label": "Equal Opportunities Form",
        "type": "form",
        "category": "Application",
        "blocking": False,
        "supports_files": False,
        "supports_requests": False,
        "policy": {}
    },
    
    # ----- REFERENCES -----
    "reference_1": {
        "key": "reference_1",
        "label": "Reference 1",
        "type": "reference",
        "category": "References",
        "blocking": True,
        "supports_files": True,
        "supports_requests": True,
        "integrity_check": True,
        "policy": {}
    },
    
    "reference_2": {
        "key": "reference_2",
        "label": "Reference 2",
        "type": "reference",
        "category": "References",
        "blocking": True,
        "supports_files": True,
        "supports_requests": True,
        "integrity_check": True,
        "policy": {}
    },
    
    # ----- IDENTITY & COMPLIANCE -----
    "right_to_work": {
        "key": "right_to_work",
        "label": "Right to Work",
        "type": "document",
        "category": "Right to Work",
        "blocking": True,
        "supports_files": True,
        "supports_requests": True,
        "extraction_enabled": True,
        "expiry_tracked": True,
        "check_required": True,
        "policy": {}
    },
    
    "identity": {
        "key": "identity",
        "label": "Identity",
        "type": "document",
        "category": "Identity & DBS",
        "blocking": True,
        "supports_files": True,
        "supports_requests": True,
        "extraction_enabled": True,
        "check_required": True,
        "policy": {}
    },
    
    "proof_of_address": {
        "key": "proof_of_address",
        "label": "Proof of Address",
        "type": "document",
        "category": "Identity & DBS",
        "blocking": True,
        "supports_files": True,
        "supports_requests": True,
        "extraction_enabled": True,
        "check_required": True,
        "multi_file": True,
        "policy": {
            "min_files": 2,
            "validity_months": 12
        }
    },
    
    "dbs": {
        "key": "dbs",
        "label": "DBS Certificate",
        "type": "document",
        "category": "Identity & DBS",
        "blocking": True,
        "supports_files": True,
        "supports_requests": True,
        "extraction_enabled": True,
        "expiry_tracked": True,
        "check_required": True,
        "policy": {
            "required_before_approval": True
        }
    },
    
    # ----- PROFESSIONAL REGISTRATION -----
    "nmc_registration": {
        "key": "nmc_registration",
        "label": "NMC Registration",
        "type": "registration",
        "category": "Professional Registration",
        "blocking": True,
        "supports_files": True,
        "supports_requests": False,
        "expiry_tracked": True,
        "verification_required": True,
        "policy": {}
    },
    
    # ----- TRAINING -----
    "training_scan": {
        "key": "training_scan",
        "label": "Training Certificates",
        "type": "document",
        "category": "Training",
        "blocking": False,
        "supports_files": True,
        "supports_requests": True,
        "extraction_enabled": True,
        "smart_extraction": True,
        "multi_file": True,
        "policy": {}
    },
    
    # ----- COMPETENCY & INDUCTION -----
    "clinical_competency": {
        "key": "clinical_competency",
        "label": "Clinical Competency Assessment",
        "type": "form",
        "category": "Competency",
        "blocking": True,
        "supports_files": False,
        "supports_requests": False,
        "policy": {}
    },
    
    "induction": {
        "key": "induction",
        "label": "Induction",
        "type": "form",
        "category": "Onboarding",
        "blocking": True,
        "supports_files": False,
        "supports_requests": False,
        "policy": {}
    },
}


def get_requirement_definition(requirement_key: str) -> dict:
    """Get the definition for a requirement key"""
    return REQUIREMENT_DEFINITIONS.get(requirement_key, {
        "key": requirement_key,
        "label": requirement_key,
        "type": "document",
        "category": "Other",
        "blocking": False,
        "supports_files": True,
        "supports_requests": True,
        "policy": {}
    })


def get_requirement_type(requirement_key: str) -> str:
    """Get the type for a requirement key"""
    defn = get_requirement_definition(requirement_key)
    return defn.get("type", "document")


def is_blocking_requirement(requirement_key: str) -> bool:
    """Check if a requirement is blocking"""
    defn = get_requirement_definition(requirement_key)
    return defn.get("blocking", False)
