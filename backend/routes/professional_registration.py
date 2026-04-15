"""
Professional Registration Routes Module

This module handles professional registration endpoints including:
- Listing employee professional registrations (NMC, GMC, HCPC, Social Work England)
- Adding/updating professional registrations
- Verifying professional registrations (admin only)
- Getting registration requirements by role

NHS Requirement: Clinical staff must maintain valid professional registration.

Extracted from server.py for modularity.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

from work_readiness_engine import ROLE_REGISTRATION_REQUIREMENTS
from unified_compliance_engine import get_unified_employee_status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Professional Registration"])


# ==================== MODELS ====================

class ProfessionalRegistrationRequest(BaseModel):
    """Request model for adding/updating professional registration"""
    body: str  # NMC, GMC, HCPC, Social Work England
    registration_number: str
    registration_status: str = "active"  # active, lapsed, suspended, applied
    registration_expiry_date: Optional[str] = None
    certificate_url: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.get("/employees/{employee_id}/professional-registrations")
async def get_professional_registrations(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all professional registrations for an employee"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    role = employee.get("system_role", employee.get("role", "healthcare_assistant")).lower()
    role_normalized = role.replace(" ", "_")
    
    # Get role requirements
    role_req = ROLE_REGISTRATION_REQUIREMENTS.get(role_normalized, {})
    
    registrations = employee.get("professional_registrations", [])
    
    return {
        "employee_id": employee_id,
        "registrations": registrations,
        "role": role,
        "registration_required": role_req.get("required", False),
        "required_body": role_req.get("body"),
        "required_body_name": role_req.get("body_name"),
        "check_url": role_req.get("check_url")
    }


@router.post("/employees/{employee_id}/professional-registration")
async def add_professional_registration(
    employee_id: str,
    request: ProfessionalRegistrationRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """Add or update professional registration for an employee"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if registration body is valid
    valid_bodies = ["NMC", "GMC", "HCPC", "Social Work England"]
    if request.body not in valid_bodies:
        raise HTTPException(status_code=400, detail=f"Invalid registration body. Must be one of: {valid_bodies}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    registration = {
        "body": request.body,
        "registration_number": request.registration_number,
        "registration_status": request.registration_status,
        "registration_expiry_date": request.registration_expiry_date,
        "certificate_url": request.certificate_url,
        "verified": False,
        "verified_by": None,
        "verified_by_name": None,
        "verified_at": None,
        "added_by": user['user_id'],
        "added_at": now
    }
    
    # Check if registration for this body already exists
    existing_registrations = employee.get("professional_registrations", [])
    existing_idx = next((i for i, r in enumerate(existing_registrations) if r.get("body") == request.body), None)
    
    if existing_idx is not None:
        # Update existing
        existing_registrations[existing_idx] = {**existing_registrations[existing_idx], **registration}
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {"professional_registrations": existing_registrations, "updated_at": now}}
        )
        action = "updated"
    else:
        # Add new
        await db.employees.update_one(
            {"id": employee_id},
            {
                "$push": {"professional_registrations": registration},
                "$set": {"updated_at": now}
            }
        )
        action = "added"
    
    await log_audit_action(
        user['user_id'],
        f"professional_registration_{action}",
        "employee",
        employee_id,
        {
            "body": request.body,
            "registration_number": request.registration_number,
            "action": action
        }
    )
    
    return {"success": True, "action": action, "registration": registration}


@router.post("/employees/{employee_id}/professional-registration/verify")
async def verify_professional_registration(
    employee_id: str,
    registration_body: str,
    user: dict = Depends(require_admin)
):
    """Mark professional registration as verified (admin only)"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    registrations = employee.get("professional_registrations", [])
    
    # Find matching registration
    reg_idx = next((i for i, r in enumerate(registrations) if r.get("body") == registration_body), None)
    
    if reg_idx is None:
        raise HTTPException(status_code=404, detail=f"No registration found for {registration_body}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update verification
    registrations[reg_idx]["verified"] = True
    registrations[reg_idx]["verified_by"] = user['user_id']
    registrations[reg_idx]["verified_by_name"] = user.get('name', user.get('email', 'Admin'))
    registrations[reg_idx]["verified_at"] = now
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "professional_registrations": registrations,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "professional_registration_verified",
        "employee",
        employee_id,
        {
            "body": registration_body,
            "registration_number": registrations[reg_idx].get("registration_number")
        }
    )
    
    # Check if this enables promotion using the canonical readiness engine.
    unified_status = await get_unified_employee_status(
        employee_id,
        db,
        user_role="admin",
        include_details=False
    )
    can_promote = unified_status.get("can_promote", False)
    checks = unified_status.get("checks", {})
    
    return {
        "success": True,
        "verified": True,
        "can_promote_now": can_promote,
        "missing_checks": [k for k, v in checks.items() if v is False] if not can_promote else []
    }


@router.get("/professional-registration-requirements")
async def get_registration_requirements(user: dict = Depends(get_current_user)):
    """Get professional registration requirements for all roles"""
    return {
        "requirements": ROLE_REGISTRATION_REQUIREMENTS,
        "valid_bodies": [
            {"value": "NMC", "label": "NMC (Nursing & Midwifery Council)", "url": "https://www.nmc.org.uk/registration/search/"},
            {"value": "GMC", "label": "GMC (General Medical Council)", "url": "https://www.gmc-uk.org/registration-and-licensing"},
            {"value": "HCPC", "label": "HCPC (Health & Care Professions Council)", "url": "https://www.hcpc-uk.org/check-the-register/"},
            {"value": "Social Work England", "label": "Social Work England", "url": "https://www.socialworkengland.org.uk/register/"}
        ]
    }
