"""
role_packs.py - Role-based requirement packs

Defines which requirements each role needs.
Used by StageGateService to generate requirement slots.
"""

from requirement_definitions import get_requirement_definition

# =============================================================================
# ROLE PACKS
# =============================================================================

ROLE_PACK_HEALTHCARE_ASSISTANT = {
    "role": "healthcare_assistant",
    "label": "Healthcare Assistant",
    
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
        "poa_min_files": 2,
        "min_references": 2
    }
}

ROLE_PACK_NURSE = {
    "role": "nurse",
    "label": "Nurse",
    
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
        "nmc_registration",
        "professional_indemnity",
        "training_scan",
        "clinical_competency",
        "medication_competency",
        "induction"
    ],
    
    "policies": {
        "dbs_required_before_approval": True,
        "poa_validity_months": 12,
        "poa_min_files": 2,
        "min_references": 2,
        "nmc_required": True
    }
}

ROLE_PACK_MANAGER = {
    "role": "manager",
    "label": "Manager / Director",

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
        "fit_proper_persons",
        "induction"
    ],

    "policies": {
        "dbs_required_before_approval": True,
        "poa_validity_months": 12,
        "poa_min_files": 2,
        "min_references": 2,
        "fit_proper_persons_required": True
    }
}

ROLE_PACK_CARE_ASSISTANT = {
    "role": "care_assistant",
    "label": "Care Assistant",
    
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
        "poa_min_files": 2,
        "min_references": 2
    }
}

ROLE_PACK_SENIOR_CARE_ASSISTANT = {
    "role": "senior_care_assistant",
    "label": "Senior Care Assistant",
    
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
        "poa_min_files": 2,
        "min_references": 2
    }
}

ROLE_PACK_SUPPORT_WORKER = {
    "role": "support_worker",
    "label": "Support Worker",
    
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
        "poa_min_files": 2,
        "min_references": 2
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
    # Manager / director variants — all get fit_proper_persons slot at intake
    "manager": ROLE_PACK_MANAGER,
    "registered_manager": ROLE_PACK_MANAGER,
    "director": ROLE_PACK_MANAGER,
    "nursing_director": ROLE_PACK_MANAGER,
    "operations_manager": ROLE_PACK_MANAGER,
}


def get_role_pack(role: str) -> dict:
    """Get the role pack for a given role, with fallback to healthcare_assistant"""
    return ROLE_PACKS.get(role, ROLE_PACK_HEALTHCARE_ASSISTANT)


def get_role_requirements(role: str) -> list:
    """Get the list of requirement keys for a role"""
    pack = get_role_pack(role)
    return pack.get("requirements", [])


def get_role_policies(role: str) -> dict:
    """Get the policies for a role"""
    pack = get_role_pack(role)
    return pack.get("policies", {})


def get_role_label(role: str) -> str:
    """Get the human-readable label for a role"""
    pack = get_role_pack(role)
    return pack.get("label", role.replace("_", " ").title())
