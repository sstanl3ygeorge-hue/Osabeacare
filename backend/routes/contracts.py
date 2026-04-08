"""
Contract Management Routes Module

This module handles contract-related endpoints including:
- Contract templates listing
- Contract preview and generation
- Contract signing (worker and admin)
- Contract status tracking
- Contract superseding

CQC Requirement: Workers must sign their own contracts.

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query

from .dependencies import (
    get_db,
    get_current_user,
    get_current_worker,
    require_manager_or_admin,
    log_audit_action,
)

# Import contract template utilities
from contract_templates import (
    ZERO_HOUR_CONTRACT_TEMPLATE,
    get_contract_template_info,
    validate_contract_data,
    fill_contract_template,
)

# Import work readiness check
from work_readiness_engine import can_sign_contract

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Contracts"])


# ==================== CONTRACT TEMPLATES ====================

@router.get("/contract-templates")
async def list_contract_templates(user: dict = Depends(get_current_user)):
    """List available contract templates."""
    return {
        "templates": [
            get_contract_template_info()
        ]
    }


@router.get("/contract-templates/{template_id}")
async def get_contract_template(
    template_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific contract template with full sections."""
    if template_id != ZERO_HOUR_CONTRACT_TEMPLATE["id"]:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "template": {
            **ZERO_HOUR_CONTRACT_TEMPLATE,
            "sections": [
                {"id": s["id"], "title": s["title"], "content": s["content"]}
                for s in ZERO_HOUR_CONTRACT_TEMPLATE["sections"]
            ]
        }
    }


# ==================== CONTRACT ELIGIBILITY ====================

@router.get("/employees/{employee_id}/can-sign-contract")
async def check_can_sign_contract(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Check if an employee is eligible to sign their contract.
    Based on work readiness requirements.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    result = await can_sign_contract(employee_id, employee.get("role", ""))
    
    return {
        "employee_id": employee_id,
        "can_sign": result.get("can_sign", False),
        "reason": result.get("reason"),
        "missing_requirements": result.get("missing_requirements", []),
        "completed_requirements": result.get("completed_requirements", [])
    }


# ==================== CONTRACT PREVIEW & GENERATION ====================

@router.get("/employees/{employee_id}/contract/preview")
async def preview_employee_contract(
    employee_id: str,
    template_id: str = "zero_hour_contract_v1",
    user: dict = Depends(get_current_user)
):
    """
    Preview a contract pre-filled with employee data.
    Used for admin review before sending to worker for signature.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate employee data
    validation = validate_contract_data(employee)
    
    # Fill template
    filled_contract = fill_contract_template(employee)
    
    return {
        "contract": filled_contract,
        "validation": validation,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "can_send": validation["valid"]
    }


@router.post("/employees/{employee_id}/contract/generate")
async def generate_employee_contract(
    employee_id: str,
    request: Request,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Generate a contract for an employee and save it for signature.
    This creates a pending contract that the worker must sign.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    template_id = body.get("template_id", "zero_hour_contract_v1")
    
    # Validate employee data
    validation = validate_contract_data(employee)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Employee data incomplete: {', '.join(validation['missing_fields'])}"
        )
    
    # Generate filled contract
    filled_contract = fill_contract_template(employee)
    
    now = datetime.now(timezone.utc)
    contract_id = str(uuid.uuid4())
    
    contract_doc = {
        "id": contract_id,
        "employee_id": employee_id,
        "template_id": template_id,
        "template_name": filled_contract["name"],
        "template_version": filled_contract["version"],
        "filled_sections": filled_contract["sections"],
        "employee_data_snapshot": {
            "first_name": employee.get("first_name"),
            "last_name": employee.get("last_name"),
            "email": employee.get("email"),
            "address": employee.get("address_line_1"),
            "postcode": employee.get("postcode"),
            "ni_number": employee.get("ni_number"),
            "role": employee.get("role"),
        },
        "status": "pending_signature",
        "generated_at": now.isoformat(),
        "generated_by": user.get("user_id"),
        "signed_at": None,
        "signed_by": None,
    }
    
    await db.generated_contracts.insert_one(contract_doc)
    
    # Update employee record
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "pending_contract_id": contract_id,
            "pending_contract_generated_at": now.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "generate_contract",
        "contract",
        contract_id,
        {"employee_id": employee_id, "template_id": template_id}
    )
    
    return {
        "contract_id": contract_id,
        "status": "pending_signature",
        "message": "Contract generated and ready for signature"
    }


# ==================== CONTRACT STATUS & LISTING ====================

@router.get("/employees/{employee_id}/contract/status")
async def get_contract_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get the current contract status for an employee."""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check for signed contract
    signed_contract = await db.generated_contracts.find_one({
        "employee_id": employee_id,
        "status": "signed"
    }, {"_id": 0})
    
    # Check for pending contract
    pending_contract = await db.generated_contracts.find_one({
        "employee_id": employee_id,
        "status": "pending_signature"
    }, {"_id": 0})
    
    # Check eligibility
    can_sign_result = await can_sign_contract(employee_id, employee.get("role", ""))
    
    return {
        "employee_id": employee_id,
        "has_signed_contract": signed_contract is not None,
        "signed_contract": signed_contract,
        "has_pending_contract": pending_contract is not None,
        "pending_contract": pending_contract,
        "can_sign_new_contract": can_sign_result.get("can_sign", False),
        "eligibility": can_sign_result
    }


@router.get("/employees/{employee_id}/contracts")
async def list_employee_contracts(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """List all contracts for an employee."""
    db = get_db()
    contracts = await db.generated_contracts.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("generated_at", -1).to_list(length=100)
    
    return {"contracts": contracts}


# ==================== CONTRACT SIGNING ====================

@router.post("/employees/{employee_id}/contract/sign")
async def sign_contract_legacy(
    employee_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Legacy contract signing endpoint.
    Signs the most recent pending contract for the employee.
    """
    db = get_db()
    
    # Find pending contract
    contract = await db.generated_contracts.find_one({
        "employee_id": employee_id,
        "status": "pending_signature"
    })
    
    if not contract:
        raise HTTPException(status_code=404, detail="No pending contract found")
    
    # Delegate to the main sign endpoint
    return await sign_employee_contract(employee_id, contract["id"], request, user)


@router.post("/employees/{employee_id}/contracts/{contract_id}/sign")
async def sign_employee_contract(
    employee_id: str,
    contract_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Worker signs their contract.
    CQC Requirement: Worker must sign their own contract.
    """
    db = get_db()
    
    # Verify user is the employee or an admin
    is_own_contract = user.get("employee_id") == employee_id
    is_admin = user.get("role") in ["admin", "super_admin", "manager"]
    
    if not is_own_contract and not is_admin:
        raise HTTPException(status_code=403, detail="You can only sign your own contract")
    
    contract = await db.generated_contracts.find_one({
        "id": contract_id,
        "employee_id": employee_id,
        "status": "pending_signature"
    })
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found or already signed")
    
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    # Get signature data
    signature_data = body.get("signature", "")
    acknowledgement = body.get("acknowledgement", False)
    
    if not acknowledgement:
        raise HTTPException(
            status_code=400, 
            detail="You must acknowledge that you have read and understood the contract"
        )
    
    now = datetime.now(timezone.utc)
    
    # Update contract
    await db.generated_contracts.update_one(
        {"id": contract_id},
        {
            "$set": {
                "status": "signed",
                "signed_at": now.isoformat(),
                "signed_by": user["user_id"],
                "signed_by_name": user.get("name", "Worker"),
                "signature_ip": body.get("ip_address"),
                "signature_data": signature_data,
                "completion_mode": "self_signed" if is_own_contract else "admin_assisted"
            }
        }
    )
    
    # Update employee record
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "contract_signed": True,
                "contract_signed_at": now.isoformat(),
                "contract_id": contract_id,
                "updated_at": now.isoformat()
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "sign_contract",
        "contract",
        contract_id,
        {"employee_id": employee_id, "completion_mode": "self_signed" if is_own_contract else "admin_assisted"}
    )
    
    return {
        "contract_id": contract_id,
        "status": "signed",
        "signed_at": now.isoformat(),
        "message": "Contract signed successfully"
    }


# ==================== CONTRACT SUPERSEDING ====================

@router.post("/employees/{employee_id}/contract/supersede")
async def supersede_employee_contract(
    employee_id: str,
    reason: str = Query(..., description="Reason for superseding the contract"),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Supersede the current contract with a new one.
    Used when contract terms change or errors need correction.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find current active contract
    current_contract = await db.generated_contracts.find_one({
        "employee_id": employee_id,
        "status": "signed"
    })
    
    if not current_contract:
        raise HTTPException(status_code=404, detail="No active contract to supersede")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Mark current contract as superseded
    await db.generated_contracts.update_one(
        {"id": current_contract["id"]},
        {
            "$set": {
                "status": "superseded",
                "superseded_at": now,
                "superseded_by": user.get("user_id"),
                "supersede_reason": reason
            }
        }
    )
    
    # Reset employee contract status
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "contract_signed": False,
                "contract_signed_at": None,
                "contract_id": None,
                "pending_contract_id": None,
                "updated_at": now
            }
        }
    )
    
    await log_audit_action(
        user['user_id'],
        "supersede_contract",
        "contract",
        current_contract["id"],
        {"employee_id": employee_id, "reason": reason}
    )
    
    return {
        "message": "Contract superseded",
        "superseded_contract_id": current_contract["id"],
        "reason": reason
    }
