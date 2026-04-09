"""
Pre-Employment Gates Routes.

This module handles:
- Pre-employment gates status (interview, contract, references, DBS, etc.)
- Manual gate updates
- Integration with unified compliance engine
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import (
    get_db, get_current_user, require_manager_or_admin,
    log_audit_action
)

router = APIRouter(tags=["Pre-Employment Gates"])


class PreEmploymentGatesUpdate(BaseModel):
    """Update pre-employment gates status"""
    interview_completed: Optional[bool] = None
    contract_signed: Optional[bool] = None


@router.get("/employees/{employee_id}/pre-employment-gates")
async def get_pre_employment_gates(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get pre-employment gates status for an employee.
    
    P0 FIX: Now uses get_unified_employee_status() - SINGLE SOURCE OF TRUTH.
    This endpoint returns the SAME data as /unified-progress, just formatted for gates UI.
    
    Standards:
    - CIA Triad: Integrity (same data as all other views)
    - 5 E's: Clear labels, verified items NEVER shown as blockers
    - NHS Level: Complete employment checks (12 for HCA, 14 for Nurse)
    - CQC Level: Audit-ready
    """
    db = get_db()
    
    # Import get_unified_employee_status from server (lazy import to avoid circular)
    from server import get_unified_employee_status
    
    # P0 FIX: SINGLE SOURCE OF TRUTH - unified_compliance_engine
    unified_status = await get_unified_employee_status(employee_id, db, user_role="admin")
    
    if unified_status.get("error"):
        raise HTTPException(status_code=404, detail=unified_status["error"])
    
    role = unified_status.get("role", "Healthcare Assistant")
    is_nurse = "nurse" in role.lower()
    checks = unified_status.get("checks", {})
    
    # Build gates from unified checks (SAME data, different format)
    gates = {
        "interview_record": {
            "num": 1,
            "passed": checks.get("interview_record", False),
            "label": "Interview Record",
            "requirement": "Must be completed by admin"
        },
        "contract_signed": {
            "num": 2,
            "passed": checks.get("contract", False),
            "label": "Contract Signed",
            "requirement": "Must be signed by worker"
        },
        "proof_of_id": {
            "num": 3,
            "passed": checks.get("proof_of_id", False),
            "label": "Proof of ID",
            "requirement": "Passport or driving licence"
        },
        "proof_of_address": {
            "num": 4,
            "passed": checks.get("proof_of_address", False),
            "label": "Proof of Address",
            "requirement": "Utility bill or bank statement"
        },
        "proof_of_ni": {
            "num": 5,
            "passed": checks.get("proof_of_ni", False),
            "label": "Proof of NI",
            "requirement": "National Insurance document"
        },
        "right_to_work": {
            "num": 6,
            "passed": checks.get("right_to_work", False),
            "label": "Right to Work",
            "requirement": "UK work authorization"
        },
        "dbs_check": {
            "num": 7,
            "passed": checks.get("dbs", False),
            "label": "DBS Check",
            "requirement": "Enhanced DBS with adults barred list"
        },
        "reference_1": {
            "num": 8,
            "passed": checks.get("reference_1", False),
            "label": "Reference 1",
            "requirement": "Professional reference verified"
        },
        "reference_2": {
            "num": 9,
            "passed": checks.get("reference_2", False),
            "label": "Reference 2",
            "requirement": "Professional reference verified"
        },
        "mandatory_training": {
            "num": 10,
            "passed": checks.get("mandatory_training_complete", False),
            "label": "Mandatory Training",
            "requirement": "All required training completed"
        },
        "induction": {
            "num": 11,
            "passed": checks.get("induction", False),
            "label": "Induction Complete",
            "requirement": "Care Certificate 15 standards"
        },
        "health_declaration": {
            "num": 12,
            "passed": checks.get("health_declaration", False),
            "label": "Health Declaration",
            "requirement": "Staff health questionnaire"
        }
    }
    
    # Add nurse-specific gates
    if is_nurse:
        gates["nmc_registration"] = {
            "num": 13,
            "passed": checks.get("nmc_registration", False),
            "label": "NMC Registration",
            "requirement": "Valid NMC PIN verified"
        }
        gates["clinical_competency"] = {
            "num": 14,
            "passed": checks.get("clinical_competency", False),
            "label": "Clinical Competency",
            "requirement": "Competency assessment passed"
        }
    
    # Count passed/total
    total_gates = len(gates)
    passed_gates = sum(1 for g in gates.values() if g["passed"])
    
    return {
        "employee_id": employee_id,
        "role": role,
        "gates": gates,
        "summary": {
            "passed": passed_gates,
            "total": total_gates,
            "percentage": round((passed_gates / total_gates) * 100) if total_gates > 0 else 0,
            "all_passed": passed_gates == total_gates
        },
        "blockers": unified_status["blockers"],  # SAME blockers as unified-progress
        "raw_checks": checks
    }


@router.put("/employees/{employee_id}/pre-employment-gates")
async def update_pre_employment_gates(
    employee_id: str,
    payload: PreEmploymentGatesUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Manually update pre-employment gate status.
    Used for legacy records or manual overrides.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {"updated_at": now}
    
    if payload.interview_completed is not None:
        update_data["interview_completed"] = payload.interview_completed
        update_data["interview_completed_at"] = now if payload.interview_completed else None
    
    if payload.contract_signed is not None:
        update_data["contract_signed"] = payload.contract_signed
        update_data["contract_signed_at"] = now if payload.contract_signed else None
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "pre_employment_gates_updated", "employee", employee_id, update_data)
    
    return {"success": True, "updated": update_data}
