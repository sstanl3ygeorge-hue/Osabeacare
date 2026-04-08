"""
Roles Routes Module

This module handles role-related endpoints including:
- Listing all available roles
- Getting requirements for a specific role
- Getting summary of all role requirements

NHS/CQC Requirement: Different roles have different compliance requirements.

Extracted from server.py for modularity.
"""

import logging
from fastapi import APIRouter, Depends

from .dependencies import (
    get_current_user,
)

# Import role-related data from interview_questions
from interview_questions import (
    get_role_requirements,
    ROLE_REQUIREMENTS_SUMMARY,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Roles"])


# ==================== ENDPOINTS ====================

@router.get("/roles")
async def get_roles():
    """
    Get list of all available roles.
    Used for dropdowns and role selection.
    """
    return [
        "Care Assistant",
        "Senior Care Assistant",
        "Support Worker",
        "Healthcare Assistant",
        "Live-in Carer",
        "Night Carer",
        "Team Leader",
        "Care Coordinator"
    ]


@router.get("/roles/{role}/requirements")
async def get_role_requirements_endpoint(
    role: str,
    user: dict = Depends(get_current_user)
):
    """
    Get complete requirements for a role.
    
    Returns:
    - Professional registration requirements
    - Mandatory training items
    - Document requirements
    - Interview question count
    - Total gates for promotion
    """
    requirements = get_role_requirements(role)
    is_nurse = "nurse" in role.lower()
    
    return {
        "role": role,
        "is_nurse_role": is_nurse,
        "requirements": requirements,
        "total_gates": 14 if is_nurse else 12,
        "gates_breakdown": {
            "base_gates": 12,
            "nurse_additional": 2 if is_nurse else 0,
            "nurse_additions": ["NMC Registration", "Professional Indemnity Insurance"] if is_nurse else []
        }
    }


@router.get("/roles/summary")
async def get_all_roles_summary(
    user: dict = Depends(get_current_user)
):
    """
    Get summary of all role requirements.
    
    Useful for admin dashboard to show role comparison.
    """
    return {
        "roles": ROLE_REQUIREMENTS_SUMMARY,
        "note": "Osabea Healthcare Solutions - Adults Only Care Services"
    }
