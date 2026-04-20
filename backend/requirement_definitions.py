"""
requirement_definitions.py - Requirement metadata definitions

Single source of truth for requirement metadata.
Used by StageGateService to generate requirement slots.

Gate flags:
  blocks_recruitment  – if True this requirement must be satisfied before
                        approve-recruitment can complete without `force=true`.
  blocks_deployment   – if True this requirement must be satisfied before the
                        worker can be marked active / deployed to placements.
  verification_required – if True the slot must carry verified=True, not just
                          be present / uploaded.
"""

# =============================================================================
# REQUIREMENT_ID_ALIASES
# =============================================================================
# Maps legacy / worker-portal requirement_id patterns → canonical requirement_key.
# Worker-portal uploads store requirement_id, NOT requirement_key.
# The resolver uses this table for backward-compatible slot lookup.
REQUIREMENT_ID_ALIASES: dict[str, str] = {
    # Right to Work
    "right_to_work": "right_to_work",
    "rtw": "right_to_work",
    "right-to-work": "right_to_work",
    # Identity
    "identity": "identity",
    "id_document": "identity",
    "passport": "identity",
    "driving_licence": "identity",
    "driving_license": "identity",
    # Proof of Address
    "proof_of_address": "proof_of_address",
    "poa": "proof_of_address",
    "proof_of_address_1": "proof_of_address",
    "proof_of_address_2": "proof_of_address",
    # DBS
    "dbs": "dbs",
    "dbs_certificate": "dbs",
    "dbs_check": "dbs",
    # References
    "reference_1": "reference_1",
    "reference1": "reference_1",
    "ref1": "reference_1",
    "reference_2": "reference_2",
    "reference2": "reference_2",
    "ref2": "reference_2",
    # CV
    "cv": "cv",
    "resume": "cv",
    # Professional registration
    "nmc_registration": "nmc_registration",
    "nmc": "nmc_registration",
    "clinical_competency": "clinical_competency",
    # Induction / deployment-only
    "induction": "induction",
}


def resolve_requirement_key(requirement_id: str | None) -> str | None:
    """
    Resolve a raw requirement_id (worker-portal style) to a canonical
    requirement_key, falling back to an alias lookup and then substring scan.

    Returns None if the value cannot be mapped.
    """
    if not requirement_id:
        return None
    key = requirement_id.strip().lower()
    # Direct match
    if key in REQUIREMENT_DEFINITIONS:
        return key
    # Alias table
    if key in REQUIREMENT_ID_ALIASES:
        return REQUIREMENT_ID_ALIASES[key]
    # Substring scan of alias keys (handles "proof_of_address_2" etc.)
    for alias, canonical in REQUIREMENT_ID_ALIASES.items():
        if alias in key or key in alias:
            return canonical
    return None


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
        "blocks_recruitment": False,
        "blocks_deployment": False,
        "verification_required": False,
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
        "blocks_recruitment": True,
        "blocks_deployment": False,
        "verification_required": False,
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
        "blocks_recruitment": False,
        "blocks_deployment": False,
        "verification_required": False,
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
        "blocks_recruitment": True,
        "blocks_deployment": False,
        "verification_required": True,
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
        "blocks_recruitment": True,
        "blocks_deployment": False,
        "verification_required": True,
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
        "blocks_recruitment": True,
        "blocks_deployment": True,
        "verification_required": True,
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
        "blocks_recruitment": True,
        "blocks_deployment": True,
        "verification_required": True,
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
        "blocks_recruitment": True,
        "blocks_deployment": False,
        "verification_required": True,
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
        "blocks_recruitment": True,
        "blocks_deployment": True,
        "verification_required": True,
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
        "blocks_recruitment": True,
        "blocks_deployment": True,
        "verification_required": True,
        "supports_files": True,
        "supports_requests": False,
        "expiry_tracked": True,
        "policy": {}
    },

    # ----- TRAINING -----
    "training_scan": {
        "key": "training_scan",
        "label": "Training Certificates",
        "type": "document",
        "category": "Training",
        "blocking": False,
        "blocks_recruitment": False,
        "blocks_deployment": False,
        "verification_required": False,
        "supports_files": True,
        "supports_requests": True,
        "extraction_enabled": True,
        "smart_extraction": True,
        "multi_file": True,
        "policy": {}
    },

    # ----- PROFESSIONAL REGISTRATION DOCUMENTS -----
    "professional_indemnity": {
        "key": "professional_indemnity",
        "label": "Professional Indemnity Insurance",
        "type": "document",
        "category": "Professional Registration",
        "blocking": True,
        "blocks_recruitment": False,
        "blocks_deployment": True,
        "verification_required": True,
        "supports_files": True,
        "supports_requests": False,
        "expiry_tracked": True,
        "policy": {}
    },

    # ----- COMPETENCY & INDUCTION -----
    "clinical_competency": {
        "key": "clinical_competency",
        "label": "Clinical Competency Assessment",
        "type": "form",
        "category": "Competency",
        "blocking": True,
        "blocks_recruitment": True,
        "blocks_deployment": False,
        "verification_required": True,
        "supports_files": False,
        "supports_requests": False,
        "policy": {}
    },

    "medication_competency": {
        "key": "medication_competency",
        "label": "Medication Administration Competency",
        "type": "document",
        "category": "Competency",
        "blocking": True,
        "blocks_recruitment": False,
        "blocks_deployment": True,
        "verification_required": True,
        "supports_files": True,
        "supports_requests": False,
        "policy": {}
    },

    # ----- MANAGEMENT / CQC -----
    "fit_proper_persons": {
        "key": "fit_proper_persons",
        "label": "Fit and Proper Persons Declaration",
        "type": "form",
        "category": "Compliance",
        "blocking": True,
        "blocks_recruitment": False,
        "blocks_deployment": False,
        "verification_required": False,
        "supports_files": False,
        "supports_requests": False,
        "policy": {}
    },

    # induction and shadow shift are DEPLOYMENT-only; they must NOT block recruitment
    "induction": {
        "key": "induction",
        "label": "Induction",
        "type": "form",
        "category": "Onboarding",
        "blocking": True,
        "blocks_recruitment": False,
        "blocks_deployment": True,
        "verification_required": False,
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
        "blocks_recruitment": False,
        "blocks_deployment": False,
        "verification_required": False,
        "supports_files": True,
        "supports_requests": True,
        "policy": {}
    })


def get_requirement_type(requirement_key: str) -> str:
    """Get the type for a requirement key"""
    defn = get_requirement_definition(requirement_key)
    return defn.get("type", "document")


def is_blocking_requirement(requirement_key: str) -> bool:
    """Check if a requirement is blocking (legacy helper, kept for compat)"""
    defn = get_requirement_definition(requirement_key)
    return defn.get("blocking", False)


def blocks_recruitment(requirement_key: str) -> bool:
    """Return True if this requirement must pass before recruitment approval."""
    return get_requirement_definition(requirement_key).get("blocks_recruitment", False)


def blocks_deployment(requirement_key: str) -> bool:
    """Return True if this requirement must pass before deployment/activation."""
    return get_requirement_definition(requirement_key).get("blocks_deployment", False)


def verification_required(requirement_key: str) -> bool:
    """Return True if the slot must be explicitly verified (not just present)."""
    return get_requirement_definition(requirement_key).get("verification_required", False)
