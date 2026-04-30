"""
Agreement routes for managing employee agreements, acknowledgements, and submissions.

Handles:
- Agreement forms (contract_acceptance, handbook_acknowledgement)
- Agreement templates
- Agreement submissions with verification workflow
- CQC compliance checks for worker self-signing

CRITICAL CQC COMPLIANCE:
- Contracts MUST be signed by the worker themselves
- Admin cannot sign contracts on behalf of workers
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action
)
from agreement_document_service import (
    CONTRACT_AGREEMENT_TYPE,
    HANDBOOK_AGREEMENT_TYPE,
    read_employee_agreement_state,
    resolve_employee_agreement_state,
)

logger = logging.getLogger(__name__)

AGREEMENT_TEMPLATE_IDS = {
    "contract_acceptance": "ZERO_HOUR_CONTRACT_V1",
    "handbook_acknowledgement": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
}

# ==================== ROUTER ====================
router = APIRouter(tags=["Agreements"])


def _canonical_latest_payload(resolved: dict) -> dict:
    return {
        "source_record_id": resolved.get("source_record_id"),
        "status": resolved.get("status"),
        "template_version": resolved.get("template_version"),
        "latest_active": resolved.get("latest_active"),
    }


async def _guard_acknowledgement_target_is_latest(*, db, employee_id: str, agreement_type: str, acknowledgement_id: str):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    canonical_type = (
        HANDBOOK_AGREEMENT_TYPE
        if agreement_type in {HANDBOOK_AGREEMENT_TYPE, "employee_handbook_acknowledgement"}
        else CONTRACT_AGREEMENT_TYPE
    )
    resolved = await read_employee_agreement_state(db, employee, canonical_type)
    latest_source_id = resolved.get("source_record_id")
    if latest_source_id and acknowledgement_id and acknowledgement_id != latest_source_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "stale_target",
                "message": "Acknowledgement target is not the canonical latest active record",
                "canonical_latest": _canonical_latest_payload(resolved),
            },
        )
    return resolved


# ==================== PYDANTIC MODELS ====================

class AgreementSendInput(BaseModel):
    """Input for sending an agreement form."""
    agreement_type: str  # AgreementType value
    version_label: str  # e.g., "Contract-v3"
    custom_message: Optional[str] = None
    due_days: int = 14


class AgreementCompleteInput(BaseModel):
    """Input for completing an agreement."""
    agreement_type: str
    completion_mode: str  # AgreementCompletionMode value
    version_acknowledged: str
    call_note: Optional[str] = None  # For phone-assisted mode
    signed_document_id: Optional[str] = None  # Optional supporting evidence


class AgreementRegenerateInput(BaseModel):
    reason: str
    agreement_type: Optional[str] = None
    submission_id: Optional[str] = None


class AgreementRecoverInput(BaseModel):
    agreement_type: str
    reason: str
    render_fields: Optional[dict] = None


# ==================== LAZY SERVICE IMPORTS ====================
# Services remain in server.py due to complex dependencies

def get_agreement_acknowledgement_service():
    """Lazy import of AgreementAcknowledgementService from server.py"""
    from server import AgreementAcknowledgementService
    return AgreementAcknowledgementService


def get_agreement_submission_service():
    """Lazy import of AgreementSubmissionService from server.py"""
    from server import AgreementSubmissionService
    return AgreementSubmissionService


# ==================== AGREEMENT ENDPOINTS ====================

@router.post("/employees/{employee_id}/agreements/send")
async def send_agreement_form(
    employee_id: str,
    data: AgreementSendInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Send an agreement form to employee via secure link.
    
    Agreement types:
    - contract_acceptance: Employment contract acknowledgement
    - handbook_acknowledgement: Company handbook acknowledgement
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    AgreementAcknowledgementService = get_agreement_acknowledgement_service()
    result = await AgreementAcknowledgementService.send_agreement_form(
        employee_id=employee_id,
        agreement_type=data.agreement_type,
        version_label=data.version_label,
        sent_by=user['user_id'],
        custom_message=data.custom_message,
        due_days=data.due_days
    )
    
    return result


@router.post("/employees/{employee_id}/agreements/complete")
async def complete_agreement(
    employee_id: str,
    data: AgreementCompleteInput,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Complete an agreement acknowledgement.
    
    Completion modes:
    - self_completed: Employee filled via secure link
    - admin_assisted: Admin filled on employee's behalf (NOT for contracts)
    - phone_assisted: Admin recorded during phone call (include call_note)
    
    CQC COMPLIANCE NOTE:
    - Contracts MUST be signed by the worker themselves
    - Admin cannot sign contracts on behalf of workers
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # CQC COMPLIANCE: Block admin signing of contracts
    if data.agreement_type == 'contract_acceptance' and data.completion_mode in ['admin_assisted', 'phone_assisted']:
        raise HTTPException(
            status_code=403, 
            detail="CQC Compliance: Contracts must be signed by the worker themselves using their digital signature. Admin cannot sign contracts on behalf of workers."
        )
    
    assisted_by = user['user_id'] if data.completion_mode in ['admin_assisted', 'phone_assisted'] else None
    completed_by = employee_id if data.completion_mode == 'self_completed' else user['user_id']
    
    AgreementAcknowledgementService = get_agreement_acknowledgement_service()
    result = await AgreementAcknowledgementService.complete_agreement(
        employee_id=employee_id,
        data=data.model_dump(),
        completed_by=completed_by,
        assisted_by=assisted_by
    )
    
    return result


@router.get("/employees/{employee_id}/agreements")
async def get_employee_agreements(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all agreement acknowledgements and pending requests for an employee."""
    AgreementAcknowledgementService = get_agreement_acknowledgement_service()
    return await AgreementAcknowledgementService.get_employee_agreements(employee_id)


@router.post("/employees/{employee_id}/agreements/{acknowledgement_id}/verify")
async def verify_agreement_acknowledgement(
    employee_id: str,
    acknowledgement_id: str,
    notes: Optional[str] = Body(None),
    user: dict = Depends(require_manager_or_admin)
):
    """Verify an agreement acknowledgement."""
    db = get_db()
    existing = await db.agreement_acknowledgements.find_one(
        {"id": acknowledgement_id, "employee_id": employee_id},
        {"_id": 0, "agreement_type": 1},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Acknowledgement not found")
    await _guard_acknowledgement_target_is_latest(
        db=db,
        employee_id=employee_id,
        agreement_type=existing.get("agreement_type") or HANDBOOK_AGREEMENT_TYPE,
        acknowledgement_id=acknowledgement_id,
    )
    AgreementAcknowledgementService = get_agreement_acknowledgement_service()
    result = await AgreementAcknowledgementService.verify_agreement(
        acknowledgement_id=acknowledgement_id,
        verified_by=user['user_id'],
        notes=notes
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Acknowledgement not found")
    
    return result


@router.post("/employees/{employee_id}/agreements/{acknowledgement_id}/reject")
async def reject_agreement_acknowledgement(
    employee_id: str,
    acknowledgement_id: str,
    reason: str = Body(..., embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """Reject an agreement acknowledgement."""
    db = get_db()
    existing = await db.agreement_acknowledgements.find_one(
        {"id": acknowledgement_id, "employee_id": employee_id},
        {"_id": 0, "agreement_type": 1},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Acknowledgement not found")
    await _guard_acknowledgement_target_is_latest(
        db=db,
        employee_id=employee_id,
        agreement_type=existing.get("agreement_type") or HANDBOOK_AGREEMENT_TYPE,
        acknowledgement_id=acknowledgement_id,
    )
    AgreementAcknowledgementService = get_agreement_acknowledgement_service()
    result = await AgreementAcknowledgementService.reject_agreement(
        acknowledgement_id=acknowledgement_id,
        rejected_by=user['user_id'],
        reason=reason
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Acknowledgement not found")
    
    return result


@router.post("/employees/{employee_id}/agreements/{acknowledgement_id}/unverify")
async def unverify_agreement_acknowledgement(
    employee_id: str,
    acknowledgement_id: str,
    reason: str = Body(..., embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Unverify an agreement acknowledgement (for error correction).
    
    CQC Audit: This action is logged with reason and reverses a verification.
    Use when an agreement was verified by accident or needs re-review.
    """
    if not reason or len(reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Reason must be at least 3 characters")

    db = get_db()
    existing = await db.agreement_acknowledgements.find_one(
        {"id": acknowledgement_id, "employee_id": employee_id},
        {"_id": 0, "agreement_type": 1},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Acknowledgement not found")
    await _guard_acknowledgement_target_is_latest(
        db=db,
        employee_id=employee_id,
        agreement_type=existing.get("agreement_type") or HANDBOOK_AGREEMENT_TYPE,
        acknowledgement_id=acknowledgement_id,
    )

    AgreementAcknowledgementService = get_agreement_acknowledgement_service()
    result = await AgreementAcknowledgementService.unverify_agreement(
        acknowledgement_id=acknowledgement_id,
        unverified_by=user['user_id'],
        reason=reason.strip()
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Acknowledgement not found")
    
    return result


@router.post("/employees/{employee_id}/agreements/{acknowledgement_id}/regenerate")
async def regenerate_agreement_acknowledgement(
    employee_id: str,
    acknowledgement_id: str,
    data: AgreementRegenerateInput = Body(...),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Admin recovery action: wipe an acknowledgement row back to a clean,
    freshly-rendered "pending" state.

    Use this when a handbook acknowledgement is stuck in a bad state —
    e.g. an old rejected or self-completed row remains after the render
    pipeline was fixed, or the rendered PDF link is broken — and the
    worker needs a clean slate to re-acknowledge.

    For contracts this action is intentionally restricted: admins cannot
    discard a worker's executed signature; use reject/unverify instead.
    """
    reason = (data.reason or "").strip()
    if not reason or len(reason) < 3:
        raise HTTPException(status_code=400, detail="Reason must be at least 3 characters")

    db = get_db()
    existing = await db.agreement_acknowledgements.find_one(
        {"id": acknowledgement_id, "employee_id": employee_id},
        {"_id": 0},
    )
    # Handbook-only fallback when acknowledgement id is missing/null in payloads.
    # Allows admin recovery by employee + type, optionally constrained by submission.
    if not existing and acknowledgement_id in {"", "null", "none", "__fallback__", "fallback"}:
        requested_type = (data.agreement_type or "").strip().lower()
        if requested_type and requested_type != "handbook_acknowledgement":
            raise HTTPException(
                status_code=403,
                detail="Fallback regenerate is only allowed for handbook_acknowledgement",
            )
        lookup_query = {
            "employee_id": employee_id,
            "agreement_type": "handbook_acknowledgement",
        }
        if data.submission_id:
            lookup_query["submission_id"] = data.submission_id
        existing = await db.agreement_acknowledgements.find_one(lookup_query, {"_id": 0})
        if not existing:
            existing = await db.agreement_acknowledgements.find_one(
                {
                    "employee_id": employee_id,
                    "agreement_type": "handbook_acknowledgement",
                },
                {"_id": 0},
            )
    if not existing:
        raise HTTPException(status_code=404, detail="Acknowledgement not found")
    if not employee_id:
        raise HTTPException(status_code=400, detail="Employee ID is required")

    agreement_type = existing.get("agreement_type")
    await _guard_acknowledgement_target_is_latest(
        db=db,
        employee_id=employee_id,
        agreement_type=agreement_type or HANDBOOK_AGREEMENT_TYPE,
        acknowledgement_id=existing.get("id") or acknowledgement_id,
    )
    template_id = existing.get("template_id") or AGREEMENT_TEMPLATE_IDS.get(agreement_type)
    if not template_id:
        raise HTTPException(status_code=400, detail="Agreement template is not configured")
    # CQC: do not let regenerate be used to bypass a worker-signed contract.
    if agreement_type == "contract_acceptance":
        raise HTTPException(
            status_code=403,
            detail=(
                "Contracts cannot be regenerated through this endpoint. "
                "Use reject or unverify to return a contract to the worker."
            ),
        )

    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    now_iso = datetime.now(timezone.utc).isoformat()

    # Snapshot the old row into the audit log and reset rejected rows back to a
    # generation-ready pending state before re-rendering.
    snapshot = {k: v for k, v in existing.items() if k != "_id"}
    if existing.get("status") == "rejected" or existing.get("verification_status") == "rejected":
        await db.agreement_acknowledgements.update_one(
            {"id": acknowledgement_id, "employee_id": employee_id},
            {
                "$set": {
                    "status": "pending",
                    "verification_status": "pending",
                    "template_id": template_id,
                    "updated_at": now_iso,
                }
            },
        )

    from agreement_document_service import ensure_agreement_rendered
    try:
        fresh = await ensure_agreement_rendered(db, employee, agreement_type)
    except Exception as exc:
        logger.exception(
            "Failed to regenerate agreement employee_id=%s acknowledgement_id=%s agreement_type=%s",
            employee_id,
            acknowledgement_id,
            agreement_type,
        )
        raise HTTPException(status_code=500, detail="Failed to regenerate agreement") from exc

    await log_audit_action(
        user["user_id"],
        "regenerate_agreement_acknowledgement",
        "agreement_acknowledgements",
        acknowledgement_id,
        {
            "employee_id": employee_id,
            "agreement_type": agreement_type,
            "reason": reason,
            "regenerated_at": now_iso,
            "previous_row": snapshot,
            "fallback_lookup": bool(acknowledgement_id in {"", "null", "none", "__fallback__", "fallback"}),
            "submission_id": data.submission_id,
        },
    )

    return {
        "success": True,
        "message": "Acknowledgement regenerated. Worker can now re-acknowledge.",
        "agreement": fresh,
    }


@router.post("/employees/{employee_id}/agreements/recover")
async def recover_agreement(
    employee_id: str,
    data: AgreementRecoverInput = Body(...),
    user: dict = Depends(require_manager_or_admin),
):
    """
    Unified admin recovery endpoint for stuck agreements.

    - contract_acceptance: apply optional render_fields, then reissue
    - handbook_acknowledgement: supersede stale rows and rebuild a fresh pending row
    """
    agreement_type = (data.agreement_type or "").strip().lower()
    reason = (data.reason or "").strip()
    if agreement_type not in {"contract_acceptance", "handbook_acknowledgement"}:
        raise HTTPException(status_code=400, detail="agreement_type must be contract_acceptance or handbook_acknowledgement")
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Reason must be at least 3 characters")

    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    now_iso = datetime.now(timezone.utc).isoformat()

    if agreement_type == "contract_acceptance":
        # Optional inline render-fields save to break dead-end recovery loops.
        render_fields = data.render_fields or {}
        if render_fields:
            from .contracts import update_contract_render_fields

            class _InlineRequest:
                def __init__(self, payload: dict):
                    self._payload = payload

                async def json(self):
                    return self._payload

            await update_contract_render_fields(
                employee_id=employee_id,
                request=_InlineRequest(
                    {
                        "hourly_rate": render_fields.get("hourly_rate"),
                        "contract_start_date": render_fields.get("contract_start_date"),
                        "continuous_service_date": render_fields.get("continuous_service_date"),
                        "company_address": render_fields.get("company_address"),
                    }
                ),
                user=user,
            )

        from .contracts import reissue_employee_contract
        # Reuse hardened reissue flow (idempotency, race-guard, compensation).

        class _InlineRequest:
            def __init__(self, payload: dict):
                self._payload = payload

            async def json(self):
                return self._payload

        reissue_result = await reissue_employee_contract(
            employee_id=employee_id,
            request=_InlineRequest(
                {
                    "reason": reason,
                    "source_contract_id": (data.render_fields or {}).get("source_contract_id"),
                    "idempotency_key": (data.render_fields or {}).get("idempotency_key"),
                }
            ),
            user=user,
        )
        return {
            "success": True,
            "agreement_type": agreement_type,
            "message": "Contract recovered and reissued.",
            "result": reissue_result,
        }

    # handbook_acknowledgement recovery
    rows = await db.agreement_acknowledgements.find(
        {"employee_id": employee_id, "agreement_type": "handbook_acknowledgement"},
        {"_id": 0},
    ).to_list(200)
    if not rows:
        rows = []

    def _is_not_superseded(row):
        if str(row.get("status") or "").strip().lower() == "superseded":
            return False
        if row.get("superseded_by_acknowledgement_id"):
            return False
        return True

    active_rows = [r for r in rows if _is_not_superseded(r)]
    sort_rows = active_rows or rows
    sort_rows = sorted(
        sort_rows,
        key=lambda r: (
            str(r.get("updated_at") or ""),
            str(r.get("created_at") or ""),
            str(r.get("id") or ""),
        ),
        reverse=True,
    )
    target = sort_rows[0] if sort_rows else None

    if target:
        # Archive all non-target handbook rows for clean active-state resolution.
        for row in rows:
            if row.get("id") == target.get("id"):
                continue
            await db.agreement_acknowledgements.update_one(
                {"id": row.get("id"), "employee_id": employee_id},
                {
                    "$set": {
                        "status": "superseded",
                        "verification_status": "superseded",
                        "superseded_at": now_iso,
                        "superseded_by": user.get("user_id"),
                        "supersede_reason": reason,
                        "updated_at": now_iso,
                    }
                },
            )

        # Reset target to fresh worker-actionable pending state.
        await db.agreement_acknowledgements.update_one(
            {"id": target.get("id"), "employee_id": employee_id},
            {
                "$set": {
                    "status": "pending",
                    "verification_status": "pending",
                    "acknowledged": False,
                    "acknowledged_at": None,
                    "recovered_at": now_iso,
                    "recovered_by": user.get("user_id"),
                    "recover_reason": reason,
                    "updated_at": now_iso,
                },
                "$unset": {
                    "rejection_reason": "",
                    "rejected_at": "",
                    "rejected_by": "",
                    "rejected_by_name": "",
                    "system_issue": "",
                },
            },
        )

    from agreement_document_service import ensure_agreement_rendered
    try:
        fresh = await ensure_agreement_rendered(db, employee, "handbook_acknowledgement")
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "action_required",
                "render_issue": str(exc),
                "missing_fields": [],
            },
        ) from exc

    await log_audit_action(
        user["user_id"],
        "recover_agreement",
        "agreement_acknowledgements",
        target.get("id") if target else f"agr_handbook_acknowledgement_{employee_id}",
        {
            "employee_id": employee_id,
            "agreement_type": "handbook_acknowledgement",
            "reason": reason,
            "route": f"POST /employees/{employee_id}/agreements/recover",
            "timestamp": now_iso,
        },
    )

    return {
        "success": True,
        "agreement_type": agreement_type,
        "message": "Handbook acknowledgement recovered.",
        "agreement": fresh,
    }


@router.post("/admin/agreements/supersede-admin-contracts")
async def supersede_admin_signed_contracts(
    user: dict = Depends(require_admin)
):
    """
    CQC Compliance Fix: Mark all admin-signed contracts as superseded.
    
    This endpoint marks existing contracts that were signed by admins 
    (not by workers themselves) as 'superseded'. Workers will need to 
    sign new contracts using their digital signature.
    
    Only Super Admins can run this.
    """
    db = get_db()
    
    # Find all contract acknowledgements that were admin-assisted
    admin_contracts = await db.agreement_acknowledgements.find({
        "agreement_type": "contract_acceptance",
        "completion_mode": {"$in": ["admin_assisted", "phone_assisted"]},
        "status": {"$ne": "superseded"}
    }).to_list(length=1000)
    
    if not admin_contracts:
        return {
            "success": True,
            "message": "No admin-signed contracts found to supersede",
            "count": 0
        }
    
    now = datetime.now(timezone.utc)
    superseded_count = 0
    employee_ids = set()
    
    for contract in admin_contracts:
        # Mark as superseded (not deleted - keep for audit trail)
        await db.agreement_acknowledgements.update_one(
            {"_id": contract["_id"]},
            {
                "$set": {
                    "status": "superseded",
                    "superseded_at": now.isoformat(),
                    "superseded_by": user["user_id"],
                    "superseded_reason": "CQC Compliance: Admin-signed contracts require worker re-signature"
                }
            }
        )
        superseded_count += 1
        employee_ids.add(contract.get("employee_id"))
    
    # Log audit action
    await log_audit_action(
        user["user_id"], 
        "supersede_admin_contracts", 
        "system", 
        "batch_operation", 
        {
            "count": superseded_count,
            "employee_ids": list(employee_ids),
            "reason": "CQC Compliance Fix"
        }
    )
    
    return {
        "success": True,
        "message": f"Superseded {superseded_count} admin-signed contracts for {len(employee_ids)} employees. Workers must sign new contracts.",
        "count": superseded_count,
        "affected_employees": len(employee_ids)
    }


# ==================== AGREEMENT TEMPLATE ENDPOINTS ====================

@router.get("/agreement-templates")
async def list_agreement_templates(
    user: dict = Depends(get_current_user)
):
    """Get all available agreement templates."""
    from agreement_templates import get_all_templates, get_template_summary
    
    templates = get_all_templates()
    summaries = []
    for template_id in templates:
        summary = get_template_summary(template_id)
        if summary:
            summaries.append(summary)
    
    return {"templates": summaries}


@router.get("/agreement-templates/{template_id}")
async def get_agreement_template(
    template_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific agreement template with full content."""
    from agreement_templates import get_template
    
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


# ==================== AGREEMENT SUBMISSION ENDPOINTS ====================

@router.post("/employees/{employee_id}/agreement-submissions")
async def create_agreement_submission(
    employee_id: str,
    template_id: str = Body(...),
    form_data: dict = Body(...),
    completion_mode: str = Body(...),  # self, admin_assisted, phone_assisted
    admin_note: Optional[str] = Body(None),
    user: dict = Depends(get_current_user)
):
    """
    Create a new agreement submission from a template.
    
    completion_mode:
    - self: Employee completed on their own
    - admin_assisted: Admin filled on employee's behalf
    - phone_assisted: Admin recorded during phone call (requires admin_note)
    """
    db = get_db()
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        AgreementSubmissionService = get_agreement_submission_service()
        submission = await AgreementSubmissionService.create_submission(
            employee_id=employee_id,
            template_id=template_id,
            form_data=form_data,
            completion_mode=completion_mode,
            completed_by=user['user_id'],
            admin_note=admin_note
        )
        return submission
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employees/{employee_id}/agreement-submissions")
async def get_employee_agreement_submissions(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all agreement submissions for an employee."""
    AgreementSubmissionService = get_agreement_submission_service()
    submissions = await AgreementSubmissionService.get_employee_submissions(employee_id)
    return {"submissions": submissions}


@router.get("/agreement-submissions/{submission_id}")
async def get_agreement_submission(
    submission_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific agreement submission."""
    AgreementSubmissionService = get_agreement_submission_service()
    submission = await AgreementSubmissionService.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Also get the template for rendering
    from agreement_templates import get_template
    template = get_template(submission.get("template_id"))
    
    return {
        "submission": submission,
        "template": template
    }


@router.post("/agreement-submissions/{submission_id}/verify")
async def verify_agreement_submission(
    submission_id: str,
    notes: Optional[str] = Body(None, embed=True),
    user: dict = Depends(require_admin)
):
    """Verify an agreement submission."""
    AgreementSubmissionService = get_agreement_submission_service()
    result = await AgreementSubmissionService.verify_submission(
        submission_id=submission_id,
        verified_by=user['user_id'],
        notes=notes
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return result


@router.post("/agreement-submissions/{submission_id}/reject")
async def reject_agreement_submission(
    submission_id: str,
    reason: str = Body(..., embed=True),
    user: dict = Depends(require_admin)
):
    """Reject an agreement submission."""
    if not reason or len(reason.strip()) < 10:
        raise HTTPException(status_code=400, detail="Rejection reason must be at least 10 characters")
    
    AgreementSubmissionService = get_agreement_submission_service()
    result = await AgreementSubmissionService.reject_submission(
        submission_id=submission_id,
        rejected_by=user['user_id'],
        reason=reason.strip()
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return result


@router.post("/agreement-submissions/{submission_id}/unverify")
async def unverify_agreement_submission(
    submission_id: str,
    reason: str = Body(..., embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Unverify an agreement submission (for error correction).
    
    CQC Audit: Logs reason and reverses verification status.
    """
    if not reason or len(reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Reason must be at least 3 characters")
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get current state for audit
    current = await db.agreement_submissions.find_one({"id": submission_id})
    if not current:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    result = await db.agreement_submissions.find_one_and_update(
        {"id": submission_id},
        {
            "$set": {
                "verification_status": "pending",
                "unverified_at": now,
                "unverified_by": user['user_id'],
                "unverify_reason": reason.strip(),
                "verified_at": None,
                "verified_by": None
            }
        },
        return_document=True
    )
    
    if result:
        await log_audit_action(user['user_id'], "unverify_agreement_submission", "agreement_submissions", submission_id, {
            "status": "unverified",
            "reason": reason.strip(),
            "previous_status": current.get("verification_status"),
            "employee_id": current.get("employee_id"),
            "template_id": current.get("template_id")
        })
        result.pop("_id", None)
    
    return result


@router.get("/agreement-submissions/{submission_id}/pdf")
async def export_agreement_submission_pdf(
    submission_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Export an agreement submission as PDF.
    
    Returns HTML that can be rendered to PDF on the client side,
    or can be processed by a PDF generation service.
    """
    AgreementSubmissionService = get_agreement_submission_service()
    submission = await AgreementSubmissionService.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    from agreement_templates import get_template
    template = get_template(submission.get("template_id"))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    html_content = AgreementSubmissionService.generate_pdf_content(submission, template)
    
    return {
        "submission_id": submission_id,
        "html_content": html_content,
        "filename": f"{template.get('template_id')}_{submission.get('employee_id')}_{submission.get('completed_at', '')[:10]}.pdf"
    }
