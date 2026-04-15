"""
Promotion Routes Module

This module handles employee promotion-related endpoints including:
- Getting promotion status and eligibility
- Auto-promotion when all checks pass
- Force promotion with admin override

NHS Status Flow: Applicant → Onboarding → Active Employee

Extracted from server.py for modularity.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

from unified_compliance_engine import get_unified_employee_status

EMPLOYEE_STATUS_ACTIVE = "active"
LEGACY_EMPLOYEE_STATUS_ACTIVE = "active_employee"


async def get_canonical_promotion_status(employee_id: str, db) -> tuple[bool, dict]:
    unified_status = await get_unified_employee_status(
        employee_id,
        db,
        user_role="admin",
        include_details=False
    )
    if unified_status.get("error"):
        raise HTTPException(status_code=404, detail=unified_status["error"])
    return unified_status.get("can_promote", False), unified_status.get("checks", {})

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Promotion"])


# ==================== MODELS ====================

class ForcePromoteRequest(BaseModel):
    """Request model for force promotion (admin override)"""
    reason: str
    notes: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.get("/employees/{employee_id}/promotion-status")
async def get_promotion_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Check if employee is ready for automatic promotion to active.
    Returns detailed check status for each requirement.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    can_promote, checks = await get_canonical_promotion_status(employee_id, db)
    
    # Get current status
    current_status = employee.get("status", "applicant")
    
    # Count passed vs failed
    passed = sum(1 for k, v in checks.items() if v is True and not k.endswith("_error"))
    total = sum(1 for k, v in checks.items() if isinstance(v, bool))
    
    # Get missing checks
    missing = [k for k, v in checks.items() if v is False]
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "current_status": current_status,
        "can_promote": can_promote,
        "checks": checks,
        "passed_count": passed,
        "total_count": total,
        "missing_checks": missing,
        "nhs_status": "Unconditional Offer" if can_promote else "Conditional Offer"
    }


@router.post("/employees/{employee_id}/auto-promote")
async def auto_promote_to_active(
    employee_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Automatically promote employee to active if all checks pass.
    This endpoint should be called after significant compliance changes.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    current_status = employee.get("status", "applicant")
    
    # Already active
    if current_status in (EMPLOYEE_STATUS_ACTIVE, LEGACY_EMPLOYEE_STATUS_ACTIVE):
        return {
            "success": True,
            "message": "Employee is already active",
            "promoted": False,
            "status": current_status
        }
    
    # Check if can promote
    can_promote, checks = await get_canonical_promotion_status(employee_id, db)
    
    if not can_promote:
        missing = [k for k, v in checks.items() if v is False]
        return {
            "success": False,
            "message": "Cannot promote - not all checks passed",
            "promoted": False,
            "status": current_status,
            "missing_checks": missing
        }
    
    # Promote to active
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "status": EMPLOYEE_STATUS_ACTIVE,
        "promoted_at": now,
        "promoted_via": "auto",
        "updated_at": now
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    # Audit log
    await log_audit_action(
        user['user_id'],
        "auto_promoted_to_active",
        "employee",
        employee_id,
        {
            "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
            "previous_status": current_status,
            "new_status": EMPLOYEE_STATUS_ACTIVE,
            "checks_passed": [k for k, v in checks.items() if v is True],
            "triggered_by": "system_auto"
        }
    )
    
    # Note: Promotion email is sent via try_auto_promote_worker in server.py
    
    return {
        "success": True,
        "message": "Employee promoted to active status",
        "promoted": True,
        "previous_status": current_status,
        "new_status": EMPLOYEE_STATUS_ACTIVE,
        "promoted_at": now
    }


@router.post("/employees/{employee_id}/force-promote")
async def force_promote_to_active(
    employee_id: str,
    request: ForcePromoteRequest,
    user: dict = Depends(require_admin)
):
    """
    Admin override to promote someone before all checks complete.
    RARE - only for emergencies. Full audit trail required.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    current_status = employee.get("status", "applicant")
    
    if current_status in (EMPLOYEE_STATUS_ACTIVE, LEGACY_EMPLOYEE_STATUS_ACTIVE):
        raise HTTPException(status_code=400, detail="Employee is already active")
    
    if len(request.reason) < 10:
        raise HTTPException(status_code=400, detail="Reason must be at least 10 characters")
    
    # Get missing checks for audit
    can_promote, checks = await get_canonical_promotion_status(employee_id, db)
    missing_checks = [k for k, v in checks.items() if v is False]
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Record the override
    override_record = {
        "employee_id": employee_id,
        "promoted_by": user['user_id'],
        "promoted_by_name": user.get('name', user.get('email', 'Unknown')),
        "promoted_at": now,
        "reason": request.reason,
        "notes": request.notes,
        "missing_checks": missing_checks
    }
    
    await db.manual_promotions.insert_one(override_record)
    
    # Update employee status
    update_data = {
        "status": EMPLOYEE_STATUS_ACTIVE,
        "promoted_at": now,
        "promoted_via": "manual_override",
        "promoted_by": user['user_id'],
        "updated_at": now
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    # Audit log
    await log_audit_action(
        user['user_id'],
        "manual_promotion_to_active",
        "employee",
        employee_id,
        {
            "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
            "previous_status": current_status,
            "new_status": EMPLOYEE_STATUS_ACTIVE,
            "reason": request.reason,
            "notes": request.notes,
            "missing_checks": missing_checks,
            "override": True
        }
    )
    
    return {
        "success": True,
        "message": "Employee manually promoted to active status",
        "employee_id": employee_id,
        "missing_checks_ignored": missing_checks
    }
