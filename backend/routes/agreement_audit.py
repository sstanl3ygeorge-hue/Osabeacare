"""
Phase A Truth Audit - one-off diagnostic endpoint.

Returns the raw output of every code path that computes contract /
handbook state for a single employee, side-by-side, so we can see which
function is the liar when admin and worker dashboards diverge.

Usage:
    GET /api/admin/agreement-audit/{employee_id}

Output is a JSON document with top-level sections:
  1. can_sign_contract_result      - from work_readiness_engine
  2. read_employee_agreement_state - contract + handbook canonical resolver
  3. get_employee_agreements       - legacy acknowledgements + pending requests
  4. worker_dashboard_agreements   - exactly what the worker portal sees
  5. admin_compliance_file_rows    - exactly what the admin compliance file sees
  6. divergence_summary            - computed flags highlighting mismatches

Admin-only. Safe to call repeatedly - read-only, no side effects.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict
import logging

from .dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["diagnostics"])


def _ensure_admin(user: dict) -> None:
    role = (user or {}).get("role") or ""
    if role not in {"admin", "super_admin", "registered_manager"}:
        raise HTTPException(status_code=403, detail="Admin/Manager role required")


def _coerce_bool(value: Any) -> bool:
    """Best-effort truthy interpretation used for divergence comparisons."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "verified", "completed", "fully_executed"}
    return bool(value)


@router.get("/admin/agreement-audit/{employee_id}")
async def agreement_audit(employee_id: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Return every code-path view of this employee contract + handbook."""
    _ensure_admin(current_user)

    db = get_db()
    from work_readiness_engine import can_sign_contract
    from agreement_document_service import read_employee_agreement_state
    import server

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    output: Dict[str, Any] = {
        "employee_id": employee_id,
        "employee_name": employee.get("full_name") or employee.get("name"),
        "person_stage": employee.get("person_stage") or employee.get("lifecycle_stage"),
    }

    # 1. can_sign_contract (work_readiness_engine)
    try:
        output["can_sign_contract_result"] = await can_sign_contract(db, employee_id)
    except Exception as exc:
        output["can_sign_contract_result"] = {"error": f"{type(exc).__name__}: {exc}"}

    # 2. read_employee_agreement_state canonical resolver
    output["read_employee_agreement_state"] = {}
    for agreement_type in ("contract_acceptance", "handbook_acknowledgement"):
        try:
            state = await read_employee_agreement_state(db, employee, agreement_type)
            output["read_employee_agreement_state"][agreement_type] = {
                "status": state.get("status"),
                "verified": state.get("verified"),
                "has_acknowledgement": state.get("has_acknowledgement"),
                "acknowledged_at": (state.get("acknowledgement") or {}).get("acknowledged_at"),
                "worker_signed_at": (state.get("acknowledgement") or {}).get("worker_signed_at"),
                "verified_at": (state.get("acknowledgement") or {}).get("verified_at"),
                "verification_status": (state.get("acknowledgement") or {}).get("verification_status"),
                "template_version": state.get("template_version"),
                "state_label": state.get("state_label"),
                "rendered_file_url": bool(state.get("rendered_file_url") or state.get("rendered_contract_pdf_url")),
                "source_record_id": state.get("source_record_id"),
            }
        except Exception as exc:
            output["read_employee_agreement_state"][agreement_type] = {"error": f"{type(exc).__name__}: {exc}"}

    # 3. legacy acknowledgements
    try:
        agreements = await server.AgreementAcknowledgementService.get_employee_agreements(employee_id)
        output["get_employee_agreements"] = {
            "acknowledgements_count": len(agreements.get("acknowledgements", []) or []),
            "pending_requests_count": len(agreements.get("pending_requests", []) or []),
            "acknowledgements_summary": [
                {
                    "id": a.get("id") or a.get("acknowledgement_id"),
                    "agreement_type": a.get("agreement_type"),
                    "status": a.get("status"),
                    "verification_status": a.get("verification_status"),
                    "verified_at": a.get("verified_at"),
                    "worker_signed_at": a.get("worker_signed_at"),
                    "template_version": a.get("template_version"),
                    "superseded_by_contract_id": a.get("superseded_by_contract_id"),
                }
                for a in (agreements.get("acknowledgements") or [])
            ],
        }
    except Exception as exc:
        output["get_employee_agreements"] = {"error": f"{type(exc).__name__}: {exc}"}

    # 4. worker dashboard agreements
    try:
        from routes.worker_dashboard import _build_worker_dashboard_payload
        wd_payload = await _build_worker_dashboard_payload(employee_id, current_user)
        wd_agreements = wd_payload.get("agreements") or []
    except Exception:
        wd_agreements = []
        for a in (output.get("get_employee_agreements", {}).get("acknowledgements_summary") or []):
            wd_agreements.append(a)
    output["worker_dashboard_agreements"] = [
        {
            "id": a.get("id"),
            "agreement_type": a.get("agreement_type"),
            "status": a.get("status"),
            "verified": a.get("verified"),
            "verification_status": a.get("verification_status"),
            "can_sign": a.get("can_sign"),
            "locked": a.get("locked") or a.get("is_locked"),
            "lifecycle_status": a.get("lifecycle_status"),
            "state_label": a.get("state_label"),
        }
        for a in wd_agreements
        if a.get("agreement_type") in {"contract_acceptance", "handbook_acknowledgement", "employee_handbook_acknowledgement"}
        or a.get("id") in {"contract_acceptance", "handbook_acknowledgement", "employee_handbook_acknowledgement"}
    ]

    # 5. admin compliance-file rows
    admin_contract_row: Dict[str, Any] = {}
    admin_handbook_row: Dict[str, Any] = {}
    try:
        import server as _server
        cf = await _server.get_compliance_file(employee_id, current_user)
        agreements_section = ((cf or {}).get("sections") or {}).get("agreements") or {}
        for r in (agreements_section.get("rows") or []):
            key = r.get("key") or r.get("agreement_type")
            if key == "contract_acceptance":
                admin_contract_row = r
            elif key in {"handbook_acknowledgement", "employee_handbook_acknowledgement"}:
                admin_handbook_row = r
    except Exception as exc:
        logger.info("agreement_audit admin_compliance_file_unavailable employee_id=%s error=%s", employee_id, exc)

    output["admin_compliance_file_rows"] = {
        "contract_acceptance": {
            "contract_signing_unlocked": admin_contract_row.get("contract_signing_unlocked"),
            "contract_signing_lock_reason": admin_contract_row.get("contract_signing_lock_reason"),
            "contract_signing_blockers_count": len(admin_contract_row.get("contract_signing_blockers") or []),
            "is_verified": admin_contract_row.get("is_verified"),
            "status": admin_contract_row.get("status"),
            "state_label": admin_contract_row.get("state_label") or admin_contract_row.get("status_summary"),
        },
        "handbook_acknowledgement": {
            "is_verified": admin_handbook_row.get("is_verified"),
            "status": admin_handbook_row.get("status"),
            "state_label": admin_handbook_row.get("state_label") or admin_handbook_row.get("status_summary"),
        },
    }

    # 6. divergence summary
    contract_state = output["read_employee_agreement_state"].get("contract_acceptance", {}) or {}
    handbook_state = output["read_employee_agreement_state"].get("handbook_acknowledgement", {}) or {}
    can_sign_result = output.get("can_sign_contract_result") or {}

    worker_contract = next(
        (a for a in output["worker_dashboard_agreements"] if a.get("agreement_type") == "contract_acceptance" or a.get("id") == "contract_acceptance"),
        {},
    )
    worker_handbook = next(
        (a for a in output["worker_dashboard_agreements"] if a.get("agreement_type") in {"handbook_acknowledgement", "employee_handbook_acknowledgement"} or a.get("id") in {"handbook_acknowledgement", "employee_handbook_acknowledgement"}),
        {},
    )

    divergences = []
    engine_can_sign = bool(can_sign_result.get("can_sign"))
    admin_unlocked_raw = admin_contract_row.get("contract_signing_unlocked")
    if admin_unlocked_raw is None and admin_contract_row:
        divergences.append({
            "field": "contract.admin.contract_signing_unlocked",
            "engine_says": f"can_sign={engine_can_sign}",
            "admin_says": "contract_signing_unlocked=None (indeterminate - silent-fail bug)",
            "impact": "Admin UI would fall through to Worker can now sign while worker shows Locked.",
        })
    elif admin_unlocked_raw is not None and bool(admin_unlocked_raw) != engine_can_sign:
        divergences.append({
            "field": "contract.engine.can_sign vs admin.contract_signing_unlocked",
            "engine_says": f"can_sign={engine_can_sign}, blockers={can_sign_result.get('blockers')}",
            "admin_says": f"contract_signing_unlocked={admin_unlocked_raw}",
            "impact": "Admin and engine disagree on whether worker can sign.",
        })

    worker_locked_raw = worker_contract.get("locked")
    if isinstance(worker_locked_raw, bool):
        worker_can_sign = not worker_locked_raw
        if worker_can_sign != engine_can_sign:
            divergences.append({
                "field": "contract.engine.can_sign vs worker.locked",
                "engine_says": f"can_sign={engine_can_sign}",
                "worker_says": f"locked={worker_locked_raw} (implies can_sign={worker_can_sign})",
                "impact": "Worker dashboard disagrees with engine.",
            })

    resolver_hb_verified = _coerce_bool(handbook_state.get("verified")) or handbook_state.get("status") == "verified"
    worker_hb_verified = _coerce_bool(worker_handbook.get("verified"))
    if resolver_hb_verified != worker_hb_verified:
        divergences.append({
            "field": "handbook.verified",
            "resolver_says": resolver_hb_verified,
            "worker_says": worker_hb_verified,
            "impact": "Admin and worker see different handbook verification state.",
        })

    resolver_contract_status = contract_state.get("status")
    worker_contract_status = worker_contract.get("status") or worker_contract.get("lifecycle_status")
    if resolver_contract_status and worker_contract_status and resolver_contract_status != worker_contract_status:
        divergences.append({
            "field": "contract.status",
            "resolver_says": resolver_contract_status,
            "worker_says": worker_contract_status,
            "impact": "Admin badge and worker status pill may disagree.",
        })

    output["divergence_summary"] = {
        "divergence_count": len(divergences),
        "divergences": divergences,
        "verdict": "ALL_AGREE" if not divergences else f"DIVERGENT ({len(divergences)} mismatches - see above)",
    }

    logger.info(
        "agreement_audit employee_id=%s divergences=%d",
        employee_id,
        len(divergences),
    )
    return output
