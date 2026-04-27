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

import io
import json
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from PyPDF2 import PdfReader

from .dependencies import (
    get_db,
    get_current_user,
    get_current_user_or_worker,
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
from agreement_document_service import (
    CONTRACT_AGREEMENT_TYPE,
    CANONICAL_CONTRACT_TEMPLATE_PREFIX,
    ensure_agreement_rendered,
    ContractRenderError,
)

# Import work readiness check
from work_readiness_engine import can_sign_contract
from supabase_storage import download_file_from_storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Contracts"])

REISSUE_ELIGIBLE_STATUSES = {
    "rejected",
    "rejected_reopen_required",
    "signed",
    "fully_executed",
    "pending_signature",
    "action_required",
}

REISSUE_STATUS_ALIASES = {
    "rejected_reopen_required": "rejected_reopen_required",
    "rejected": "rejected",
    "signed": "signed",
    "fully_executed": "fully_executed",
    "pending_signature": "pending_signature",
    "action_required": "action_required",
}

_UNRESOLVED_CONTRACT_PATTERNS = [
    r"\bTBC\b",
    r"insert amount",
    r"£\s*\(insert amount\)",
    r"Ł\s*\(insert amount\)",
    r"June\s*2023",
    r"Page\s*3\s*of\s*5",
    r"Company ConfidentialSMT1",
    r"\(insert[^)]*\)",
    r"\{\{[^{}]+\}\}",
    r"Logo \(if required\)",
]

_REQUIRED_CONTRACT_RENDER_FIELDS = (
    "contract_start_date",
    "continuous_service_date",
    "hourly_rate",
    "company_address",
)


def _has_unresolved_contract_markers(text: str) -> bool:
    hay = str(text or "")
    for pattern in _UNRESOLVED_CONTRACT_PATTERNS:
        if re.search(pattern, hay, flags=re.IGNORECASE):
            return True
    return False


def _extract_missing_contract_fields(render_issue: str) -> list[str]:
    """
    Parse known required contract field names from renderer error text.
    Keeps API responses structured for admin UX recovery actions.
    """
    message = str(render_issue or "")
    lower = message.lower()
    missing = []
    for field in _REQUIRED_CONTRACT_RENDER_FIELDS:
        if field.lower() in lower:
            missing.append(field)
    return missing


def _build_contract_doc_for_signature(
    *,
    employee: dict,
    employee_id: str,
    template_id: str,
    actor_user_id: Optional[str],
    now_iso: str,
    extra_fields: Optional[dict] = None,
    render_record: Optional[dict] = None,
) -> dict:
    """
    Build a generated contract record in the same shape as the existing
    /contract/generate flow, with optional extra metadata fields.
    """
    filled_contract = fill_contract_template(employee)
    render_record = render_record or {}
    rendered_file_url = (
        render_record.get("rendered_contract_pdf_url")
        or render_record.get("rendered_file_url")
    )
    canonical_ok = str(render_record.get("template_version") or "").startswith(CANONICAL_CONTRACT_TEMPLATE_PREFIX)
    contract_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "template_id": template_id,
        "template_name": filled_contract["name"],
        "template_version": render_record.get("template_version") or filled_contract["version"],
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
        "generated_at": now_iso,
        "generated_by": actor_user_id,
        "signed_at": None,
        "signed_by": None,
        "rendered_file_url": rendered_file_url,
        "rendered_contract_pdf_url": rendered_file_url,
        "rendered_at": render_record.get("rendered_at") or now_iso,
        "render_issue": None if canonical_ok else "non_canonical_contract_template",
        "canonical_contract_render": bool(canonical_ok),
        "canonical_template_source": render_record.get("template_source_name"),
    }
    if extra_fields:
        contract_doc.update(extra_fields)
    return contract_doc


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
    user: dict = Depends(get_current_user_or_worker)
):
    """
    Check if an employee is eligible to sign their contract.
    Based on work readiness requirements.
    """
    db = get_db()
    if user.get("is_worker") and user.get("employee_id") != employee_id:
        raise HTTPException(status_code=403, detail="You can only check your own contract eligibility")

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    result = await can_sign_contract(db, employee_id)
    
    return {
        "employee_id": employee_id,
        "can_sign": result.get("can_sign", False),
        "reason": result.get("reason"),
        "blockers": result.get("blockers", []),
        "completed": result.get("completed", []),
        "progress_percentage": result.get("progress_percentage", 0),
        "total_requirements": result.get("total_requirements", 0),
        "completed_count": result.get("completed_count", 0),
        "debug": result.get("debug", {}),
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

    try:
        render_record = await ensure_agreement_rendered(db, employee, CONTRACT_AGREEMENT_TYPE)
    except ContractRenderError as exc:
        render_issue = str(exc)
        raise HTTPException(
            status_code=409,
            detail={
                "status": "action_required",
                "render_issue": render_issue,
                "missing_fields": _extract_missing_contract_fields(render_issue),
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "action_required",
                "render_issue": f"Failed to render canonical contract: {exc}",
            },
        ) from exc

    if not str(render_record.get("template_version") or "").startswith(CANONICAL_CONTRACT_TEMPLATE_PREFIX):
        raise HTTPException(
            status_code=409,
            detail={
                "status": "action_required",
                "render_issue": "Non-canonical contract template/version detected",
            },
        )
    
    now_iso = datetime.now(timezone.utc).isoformat()
    contract_doc = _build_contract_doc_for_signature(
        employee=employee,
        employee_id=employee_id,
        template_id=template_id,
        actor_user_id=user.get("user_id"),
        now_iso=now_iso,
        render_record=render_record,
    )
    contract_id = contract_doc["id"]
    
    await db.generated_contracts.insert_one(contract_doc)
    
    # Update employee record
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "pending_contract_id": contract_id,
            "pending_contract_generated_at": now_iso,
            "updated_at": now_iso
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
    can_sign_result = await can_sign_contract(db, employee_id)
    
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

    template_version = str(contract.get("template_version") or "")
    is_canonical = template_version.startswith(CANONICAL_CONTRACT_TEMPLATE_PREFIX)
    if (not is_canonical) or contract.get("render_issue") or not (
        contract.get("rendered_contract_pdf_url") or contract.get("rendered_file_url")
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "status": "action_required",
                "render_issue": contract.get("render_issue") or "Contract is not canonical/signable. Regenerate using canonical renderer.",
            },
        )

    # Guard against stale/badly-rendered historical contracts that still carry
    # unresolved placeholders/TBC markers in their stored content.
    if _has_unresolved_contract_markers(json.dumps(contract.get("filled_sections") or [])):
        raise HTTPException(
            status_code=409,
            detail={
                "status": "action_required",
                "render_issue": "Contract contains unresolved placeholders. Regenerate before signing.",
            },
        )

    # Defense in depth: inspect the rendered PDF text when retrievable.
    contract_pdf_url = contract.get("rendered_contract_pdf_url") or contract.get("rendered_file_url")
    if contract_pdf_url:
        try:
            pdf_bytes = await download_file_from_storage(contract_pdf_url)
            if pdf_bytes:
                text = "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(pdf_bytes)).pages)
                if _has_unresolved_contract_markers(text):
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "status": "action_required",
                            "render_issue": "Contract PDF contains unresolved placeholders. Regenerate before signing.",
                        },
                    )
        except HTTPException:
            raise
        except Exception:
            # Non-fatal for signing flow if PDF cannot be fetched/parsed in this
            # preflight check; canonical/template checks above remain enforced.
            pass
    
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

@router.post("/employees/{employee_id}/contract/reissue")
async def reissue_employee_contract(
    employee_id: str,
    request: Request,
    user: dict = Depends(require_manager_or_admin),
):
    """
    Reissue the latest non-superseded contract for worker re-signing.
    This preserves the old contract record/artifacts and immediately
    creates a replacement pending-signature contract.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        body = await request.json()
    except Exception:
        body = {}

    reason = str((body or {}).get("reason") or "").strip()
    source_contract_id = (body or {}).get("source_contract_id")
    idempotency_key = str((body or {}).get("idempotency_key") or "").strip() or None

    if not reason:
        raise HTTPException(status_code=400, detail="reason is required")

    # Early idempotency replay when caller supplies a source contract id.
    # This guarantees stable replay even after latest contract changes due to
    # a successful first reissue.
    if idempotency_key and source_contract_id:
        source_scoped_reissue = await db.generated_contracts.find_one(
            {
                "employee_id": employee_id,
                "reissue_idempotency_key": idempotency_key,
                "reissued_from_contract_id": source_contract_id,
            },
            {"_id": 0},
        )
        if source_scoped_reissue:
            old_contract = await db.generated_contracts.find_one(
                {"id": source_contract_id},
                {"_id": 0},
            )
            can_sign_result = await can_sign_contract(db, employee_id)
            return {
                "message": "Contract reissued",
                "employee_id": employee_id,
                "old_contract": {
                    "id": (old_contract or {}).get("id"),
                    "status": (old_contract or {}).get("status"),
                    "superseded_at": (old_contract or {}).get("superseded_at"),
                    "superseded_by_contract_id": (old_contract or {}).get("superseded_by_contract_id"),
                },
                "new_contract": {
                    "id": source_scoped_reissue.get("id"),
                    "status": source_scoped_reissue.get("status"),
                    "template_id": source_scoped_reissue.get("template_id"),
                    "template_version": source_scoped_reissue.get("template_version"),
                    "generated_at": source_scoped_reissue.get("generated_at"),
                    "reissued_from_contract_id": source_scoped_reissue.get("reissued_from_contract_id"),
                },
                "worker_action": {
                    "can_sign": can_sign_result.get("can_sign", False),
                    "contract_status": source_scoped_reissue.get("status"),
                    "sign_route": f"/employees/{employee_id}/contract/sign",
                },
            }

        conflicting_reissue_for_source = await db.generated_contracts.find_one(
            {
                "employee_id": employee_id,
                "reissue_idempotency_key": idempotency_key,
                "reissued_from_contract_id": {"$exists": True, "$ne": source_contract_id},
            },
            {"_id": 0},
        )
        if conflicting_reissue_for_source:
            raise HTTPException(
                status_code=409,
                detail="idempotency_key already used for a different source_contract_id",
            )

    latest_contract = await db.generated_contracts.find(
        {
            "employee_id": employee_id,
            "status": {"$ne": "superseded"},
            "$or": [
                {"superseded_by_contract_id": {"$exists": False}},
                {"superseded_by_contract_id": None},
            ],
        },
    ).sort([("generated_at", -1), ("created_at", -1), ("_id", -1)]).limit(1).to_list(length=1)

    if not latest_contract:
        raise HTTPException(status_code=404, detail="No contract available to reissue")

    current_contract = latest_contract[0]

    if source_contract_id and source_contract_id != current_contract.get("id"):
        raise HTTPException(
            status_code=409,
            detail="source_contract_id does not match latest contract",
        )
    effective_source_contract_id = current_contract.get("id")

    # Idempotency is scoped to employee_id + source_contract_id.
    if idempotency_key:
        existing_reissue = await db.generated_contracts.find_one(
            {
                "employee_id": employee_id,
                "reissue_idempotency_key": idempotency_key,
                "reissued_from_contract_id": effective_source_contract_id,
            },
            {"_id": 0},
        )
        if existing_reissue:
            existing_source_contract_id = existing_reissue.get("reissued_from_contract_id")
            if existing_source_contract_id != effective_source_contract_id:
                raise HTTPException(
                    status_code=409,
                    detail="idempotency_key already used for a different source_contract_id",
                )

            old_contract = await db.generated_contracts.find_one(
                {"id": existing_source_contract_id},
                {"_id": 0},
            )
            can_sign_result = await can_sign_contract(db, employee_id)
            return {
                "message": "Contract reissued",
                "employee_id": employee_id,
                "old_contract": {
                    "id": (old_contract or {}).get("id"),
                    "status": (old_contract or {}).get("status"),
                    "superseded_at": (old_contract or {}).get("superseded_at"),
                    "superseded_by_contract_id": (old_contract or {}).get("superseded_by_contract_id"),
                },
                "new_contract": {
                    "id": existing_reissue.get("id"),
                    "status": existing_reissue.get("status"),
                    "template_id": existing_reissue.get("template_id"),
                    "template_version": existing_reissue.get("template_version"),
                    "generated_at": existing_reissue.get("generated_at"),
                    "reissued_from_contract_id": existing_reissue.get("reissued_from_contract_id"),
                },
                "worker_action": {
                    "can_sign": can_sign_result.get("can_sign", False),
                    "contract_status": existing_reissue.get("status"),
                    "sign_route": f"/employees/{employee_id}/contract/sign",
                },
            }
        conflicting_reissue = await db.generated_contracts.find_one(
            {
                "employee_id": employee_id,
                "reissue_idempotency_key": idempotency_key,
                "reissued_from_contract_id": {"$exists": True, "$ne": effective_source_contract_id},
            },
            {"_id": 0},
        )
        if conflicting_reissue:
            raise HTTPException(
                status_code=409,
                detail="idempotency_key already used for a different source_contract_id",
            )

    raw_current_status = current_contract.get("status")
    normalized_current_status = str(raw_current_status or "").strip().lower()
    current_status = REISSUE_STATUS_ALIASES.get(normalized_current_status, normalized_current_status)
    if current_status not in REISSUE_ELIGIBLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Latest contract status '{raw_current_status}' is not eligible for reissue",
        )

    # If an active pending-signature contract already exists, do not attempt a
    # fresh render/reissue (which may fail on missing optional render fields).
    # Instead, normalize acknowledgement pointers so worker/admin views reflect
    # the existing signable contract.
    if current_status == "pending_signature":
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.employees.update_one(
            {"id": employee_id},
            {
                "$set": {
                    "pending_contract_id": current_contract.get("id"),
                    "pending_contract_generated_at": current_contract.get("generated_at") or now_iso,
                    "contract_signed": False,
                    "contract_signed_at": None,
                    "contract_id": None,
                    "updated_at": now_iso,
                }
            },
        )
        await db.agreement_acknowledgements.update_one(
            {"employee_id": employee_id, "agreement_type": "contract_acceptance"},
            {
                "$set": {
                    "employee_id": employee_id,
                    "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
                    "agreement_type": "contract_acceptance",
                    "status": "pending_signature",
                    "contract_state": "awaiting_worker_signature",
                    "verification_status": "pending",
                    "acknowledged": False,
                    "acknowledged_at": None,
                    "signed_at": None,
                    "worker_signed_at": None,
                    "worker_signer_name": None,
                    "signed_document_url": None,
                    "worker_signed_contract_pdf_url": None,
                    "executed_contract_pdf_url": None,
                    "template_version": current_contract.get("template_version"),
                    "rendered_contract_pdf_url": (
                        current_contract.get("rendered_contract_pdf_url")
                        or current_contract.get("rendered_file_url")
                        or current_contract.get("file_url")
                    ),
                    "rendered_file_url": (
                        current_contract.get("rendered_contract_pdf_url")
                        or current_contract.get("rendered_file_url")
                        or current_contract.get("file_url")
                    ),
                    "active_contract_id": current_contract.get("id"),
                    "updated_at": now_iso,
                },
                "$unset": {
                    "rejection_reason": "",
                    "rejected_at": "",
                    "rejected_by": "",
                    "rejected_by_name": "",
                },
                "$setOnInsert": {
                    "id": f"agr_contract_acceptance_{employee_id}",
                    "created_at": now_iso,
                },
            },
            upsert=True,
        )
        can_sign_result = await can_sign_contract(db, employee_id)
        return {
            "message": "Contract already pending signature",
            "employee_id": employee_id,
            "old_contract": None,
            "new_contract": {
                "id": current_contract.get("id"),
                "status": current_contract.get("status"),
                "template_id": current_contract.get("template_id"),
                "template_version": current_contract.get("template_version"),
                "generated_at": current_contract.get("generated_at"),
                "reissued_from_contract_id": current_contract.get("reissued_from_contract_id"),
            },
            "worker_action": {
                "can_sign": can_sign_result.get("can_sign", False),
                "contract_status": current_contract.get("status"),
                "sign_route": f"/employees/{employee_id}/contract/sign",
            },
        }

    # Validate current employee data before mutating old contract state.
    validation = validate_contract_data(employee)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Employee data incomplete: {', '.join(validation['missing_fields'])}",
        )
    try:
        render_record = await ensure_agreement_rendered(db, employee, CONTRACT_AGREEMENT_TYPE)
    except ContractRenderError as exc:
        render_issue = str(exc)
        raise HTTPException(
            status_code=409,
            detail={
                "status": "action_required",
                "render_issue": render_issue,
                "missing_fields": _extract_missing_contract_fields(render_issue),
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "action_required",
                "render_issue": f"Failed to render canonical contract: {exc}",
            },
        ) from exc
    if not str(render_record.get("template_version") or "").startswith(CANONICAL_CONTRACT_TEMPLATE_PREFIX):
        raise HTTPException(
            status_code=409,
            detail={
                "status": "action_required",
                "render_issue": "Non-canonical contract template/version detected",
            },
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    reissue_attempt_id = str(uuid.uuid4())
    employee_pointer_snapshot = {
        "pending_contract_id": employee.get("pending_contract_id"),
        "pending_contract_generated_at": employee.get("pending_contract_generated_at"),
        "contract_signed": employee.get("contract_signed"),
        "contract_signed_at": employee.get("contract_signed_at"),
        "contract_id": employee.get("contract_id"),
        "updated_at": employee.get("updated_at"),
    }
    contract_ack_snapshot = await db.agreement_acknowledgements.find_one(
        {"employee_id": employee_id, "agreement_type": "contract_acceptance"},
        {"_id": 0},
    )
    template_id = current_contract.get("template_id") or "zero_hour_contract_v1"
    new_contract_doc = _build_contract_doc_for_signature(
        employee=employee,
        employee_id=employee_id,
        template_id=template_id,
        actor_user_id=user.get("user_id"),
        now_iso=now_iso,
        render_record=render_record,
        extra_fields={
            "reissued_from_contract_id": current_contract["id"],
            "reissue_reason": reason,
            "reissue_idempotency_key": idempotency_key,
        },
    )
    new_contract_id = new_contract_doc["id"]

    # Race guard + transitional lock: mark the old contract as being reissued
    # before creating replacement artifacts, so failures can be compensated.
    mark_in_progress_result = await db.generated_contracts.update_one(
        {
            "_id": current_contract["_id"],
            "id": current_contract["id"],
            "employee_id": employee_id,
            "$and": [
                {"status": current_status},
                {"status": {"$ne": "superseded"}},
                {
                    "$or": [
                        {"superseded_by_contract_id": {"$exists": False}},
                        {"superseded_by_contract_id": None},
                    ]
                },
                {
                    "$or": [
                        {"reissue_in_progress": {"$exists": False}},
                        {"reissue_in_progress": None},
                        {"reissue_in_progress": False},
                    ]
                },
            ],
        },
        {
            "$set": {
                "reissue_in_progress": True,
                "reissue_started_at": now_iso,
                "reissue_attempt_id": reissue_attempt_id,
                "reissue_target_contract_id": new_contract_id,
            }
        },
    )
    if mark_in_progress_result.modified_count == 0:
        # If another request won with same idempotency scope, return replay.
        if idempotency_key:
            existing_reissue = await db.generated_contracts.find_one(
                {
                    "employee_id": employee_id,
                    "reissue_idempotency_key": idempotency_key,
                    "reissued_from_contract_id": effective_source_contract_id,
                },
                {"_id": 0},
            )
            if existing_reissue:
                can_sign_result = await can_sign_contract(db, employee_id)
                return {
                    "message": "Contract reissued",
                    "employee_id": employee_id,
                    "old_contract": {
                        "id": effective_source_contract_id,
                        "status": "superseded",
                        "superseded_at": None,
                        "superseded_by_contract_id": existing_reissue.get("id"),
                    },
                    "new_contract": {
                        "id": existing_reissue.get("id"),
                        "status": existing_reissue.get("status"),
                        "template_id": existing_reissue.get("template_id"),
                        "template_version": existing_reissue.get("template_version"),
                        "generated_at": existing_reissue.get("generated_at"),
                        "reissued_from_contract_id": existing_reissue.get("reissued_from_contract_id"),
                    },
                    "worker_action": {
                        "can_sign": can_sign_result.get("can_sign", False),
                        "contract_status": existing_reissue.get("status"),
                        "sign_route": f"/employees/{employee_id}/contract/sign",
                    },
                }
        raise HTTPException(status_code=409, detail="Contract already superseded or reissued")

    inserted_new_contract = False
    try:
        await db.generated_contracts.insert_one(new_contract_doc)
        inserted_new_contract = True

        finalize_old_result = await db.generated_contracts.update_one(
            {
                "_id": current_contract["_id"],
                "employee_id": employee_id,
                "reissue_in_progress": True,
                "reissue_attempt_id": reissue_attempt_id,
                "$or": [
                    {"superseded_by_contract_id": {"$exists": False}},
                    {"superseded_by_contract_id": None},
                ],
            },
            {
                "$set": {
                    "status": "superseded",
                    "superseded_at": now_iso,
                    "superseded_by": user.get("user_id"),
                    "supersede_reason": reason,
                    "superseded_by_contract_id": new_contract_id,
                },
                "$unset": {
                    "reissue_in_progress": "",
                    "reissue_started_at": "",
                    "reissue_attempt_id": "",
                    "reissue_target_contract_id": "",
                },
            },
        )
        if finalize_old_result.modified_count == 0:
            raise RuntimeError("Failed to finalize superseded old contract")

        employee_pointer_result = await db.employees.update_one(
            {"id": employee_id},
            {
                "$set": {
                    "pending_contract_id": new_contract_id,
                    "pending_contract_generated_at": now_iso,
                    "contract_signed": False,
                    "contract_signed_at": None,
                    "contract_id": None,
                    "updated_at": now_iso,
                }
            },
        )
        if employee_pointer_result.modified_count == 0:
            raise RuntimeError("Failed to update employee contract pointers")

        # Keep worker dashboard in sync with the new pending contract. The
        # dashboard contract card is sourced from agreement_acknowledgements.
        await db.agreement_acknowledgements.update_one(
            {"employee_id": employee_id, "agreement_type": "contract_acceptance"},
            {
                "$set": {
                    "employee_id": employee_id,
                    "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
                    "agreement_type": "contract_acceptance",
                    "status": "pending_signature",
                    "contract_state": "awaiting_worker_signature",
                    "verification_status": "pending",
                    "acknowledged": False,
                    "acknowledged_at": None,
                    "signed_at": None,
                    "worker_signed_at": None,
                    "worker_signer_name": None,
                    "signed_document_url": None,
                    "worker_signed_contract_pdf_url": None,
                    "executed_contract_pdf_url": None,
                    "template_version": new_contract_doc.get("template_version"),
                    "rendered_contract_pdf_url": (
                        new_contract_doc.get("rendered_file_url")
                        or current_contract.get("rendered_contract_pdf_url")
                        or current_contract.get("rendered_file_url")
                    ),
                    "rendered_file_url": (
                        new_contract_doc.get("rendered_file_url")
                        or current_contract.get("rendered_contract_pdf_url")
                        or current_contract.get("rendered_file_url")
                    ),
                    "reissued_from_contract_id": current_contract.get("id"),
                    "active_contract_id": new_contract_id,
                    "updated_at": now_iso,
                },
                "$unset": {
                    "rejection_reason": "",
                    "rejected_at": "",
                    "rejected_by": "",
                    "rejected_by_name": "",
                },
                "$setOnInsert": {
                    "id": f"agr_contract_acceptance_{employee_id}",
                    "created_at": now_iso,
                },
            },
            upsert=True,
        )

        await log_audit_action(
            user["user_id"],
            "contract_reissued",
            "contract",
            new_contract_id,
            {
                "event_type": "contract_reissued",
                "employee_id": employee_id,
                "old_contract_id": current_contract["id"],
                "new_contract_id": new_contract_id,
                "old_status": current_status,
                "new_status": new_contract_doc["status"],
                "reason": reason,
                "actor_user_id": user.get("user_id"),
                "actor_role": user.get("role"),
                "timestamp": now_iso,
                "idempotency_key": idempotency_key,
                "source": "contracts.reissue_endpoint",
                "route": f"POST /employees/{employee_id}/contract/reissue",
            },
        )
    except Exception as reissue_exc:
        # Best-effort compensation to avoid deadlock: remove the new contract
        # if present and restore the old contract to its previous state.
        try:
            if inserted_new_contract:
                await db.generated_contracts.delete_one({"id": new_contract_id, "employee_id": employee_id})
            await db.generated_contracts.update_one(
                {
                    "_id": current_contract["_id"],
                    "employee_id": employee_id,
                },
                {
                    "$set": {
                        "status": current_status,
                    },
                    "$unset": {
                        "reissue_in_progress": "",
                        "reissue_started_at": "",
                        "reissue_attempt_id": "",
                        "reissue_target_contract_id": "",
                        "superseded_at": "",
                        "superseded_by": "",
                        "supersede_reason": "",
                        "superseded_by_contract_id": "",
                    },
                },
            )
            await db.employees.update_one(
                {"id": employee_id},
                {
                    "$set": {
                        "pending_contract_id": employee_pointer_snapshot.get("pending_contract_id"),
                        "pending_contract_generated_at": employee_pointer_snapshot.get("pending_contract_generated_at"),
                        "contract_signed": employee_pointer_snapshot.get("contract_signed"),
                        "contract_signed_at": employee_pointer_snapshot.get("contract_signed_at"),
                        "contract_id": employee_pointer_snapshot.get("contract_id"),
                        "updated_at": employee_pointer_snapshot.get("updated_at"),
                    }
                },
            )
            if contract_ack_snapshot:
                await db.agreement_acknowledgements.update_one(
                    {"employee_id": employee_id, "agreement_type": "contract_acceptance"},
                    {"$set": contract_ack_snapshot},
                    upsert=True,
                )
            else:
                await db.agreement_acknowledgements.delete_one(
                    {"employee_id": employee_id, "agreement_type": "contract_acceptance"}
                )
        except Exception as rollback_exc:
            logger.exception(
                "Contract reissue rollback failed employee_id=%s old_contract_id=%s new_contract_id=%s err=%s",
                employee_id,
                current_contract.get("id"),
                new_contract_id,
                rollback_exc,
            )
        raise HTTPException(
            status_code=500,
            detail="Failed to reissue contract safely; previous state restored where possible",
        ) from reissue_exc

    can_sign_result = await can_sign_contract(db, employee_id)
    return {
        "message": "Contract reissued",
        "employee_id": employee_id,
        "old_contract": {
            "id": current_contract["id"],
            "status": current_status,
            "superseded_at": now_iso,
            "superseded_by_contract_id": new_contract_id,
        },
        "new_contract": {
            "id": new_contract_id,
            "status": new_contract_doc["status"],
            "template_id": new_contract_doc.get("template_id"),
            "template_version": new_contract_doc.get("template_version"),
            "generated_at": new_contract_doc.get("generated_at"),
            "reissued_from_contract_id": current_contract["id"],
        },
        "worker_action": {
            "can_sign": can_sign_result.get("can_sign", False),
            "contract_status": new_contract_doc["status"],
            "sign_route": f"/employees/{employee_id}/contract/sign",
        },
    }

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
