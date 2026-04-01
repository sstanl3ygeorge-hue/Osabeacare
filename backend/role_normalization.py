"""
role_normalization.py - Role normalization and mapping

Normalizes user-provided role strings to canonical role keys.
"""

# =============================================================================
# ROLE ALIASES
# =============================================================================
# Maps various input strings to canonical role keys

ROLE_ALIASES = {
    # Healthcare Assistant variants
    "healthcare_assistant": "healthcare_assistant",
    "healthcare assistant": "healthcare_assistant",
    "hca": "healthcare_assistant",
    "health care assistant": "healthcare_assistant",
    "healthcare-assistant": "healthcare_assistant",
    
    # Care Assistant variants
    "care_assistant": "care_assistant",
    "care assistant": "care_assistant",
    "ca": "care_assistant",
    "carer": "care_assistant",
    "care-assistant": "care_assistant",
    
    # Senior Care Assistant variants
    "senior_care_assistant": "senior_care_assistant",
    "senior care assistant": "senior_care_assistant",
    "senior carer": "senior_care_assistant",
    "sca": "senior_care_assistant",
    
    # Support Worker variants
    "support_worker": "support_worker",
    "support worker": "support_worker",
    "sw": "support_worker",
    "support-worker": "support_worker",
    
    # Nurse variants
    "nurse": "nurse",
    "registered_nurse": "nurse",
    "registered nurse": "nurse",
    "rn": "nurse",
    "staff_nurse": "nurse",
    "staff nurse": "nurse",
}

# Default role if normalization fails
DEFAULT_ROLE = "healthcare_assistant"

# Supported roles (canonical keys)
SUPPORTED_ROLES = [
    "healthcare_assistant",
    "nurse",
    "care_assistant",
    "senior_care_assistant",
    "support_worker",
]


def normalize_role(role_input: str) -> str:
    """
    Normalize a role string to a canonical role key.
    
    Args:
        role_input: Raw role string from user input
        
    Returns:
        Canonical role key (e.g., "healthcare_assistant", "nurse")
    """
    if not role_input:
        return DEFAULT_ROLE
    
    # Lowercase and strip
    normalized = role_input.lower().strip()
    
    # Check direct alias match
    if normalized in ROLE_ALIASES:
        return ROLE_ALIASES[normalized]
    
    # Check if already a canonical key
    if normalized in SUPPORTED_ROLES:
        return normalized
    
    # Partial match fallback
    for alias, canonical in ROLE_ALIASES.items():
        if alias in normalized or normalized in alias:
            return canonical
    
    # Default fallback
    return DEFAULT_ROLE


def is_supported_role(role: str) -> bool:
    """Check if a role is supported"""
    return normalize_role(role) in SUPPORTED_ROLES


def get_role_label(role: str) -> str:
    """Get human-readable label for a role"""
    labels = {
        "healthcare_assistant": "Healthcare Assistant",
        "nurse": "Nurse",
        "care_assistant": "Care Assistant",
        "senior_care_assistant": "Senior Care Assistant",
        "support_worker": "Support Worker",
    }
    canonical = normalize_role(role)
    return labels.get(canonical, role.replace("_", " ").title())
