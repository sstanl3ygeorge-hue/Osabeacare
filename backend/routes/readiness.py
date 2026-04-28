"""
Readiness routes for employee work readiness and audit readiness evaluations.

Handles:
- Single employee readiness calculation (SINGLE SOURCE OF TRUTH)
- Readiness summary for all employees
- Recruitment approval check (Gate 1)
- Work readiness check (Gate 2)
- POA (Proof of Address) freshness evaluation
- Audit readiness dashboard

These endpoints provide authoritative readiness calculations used across
all UI components (dashboard, profile, list badges, exports).
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from stageGates import StageGateService

from .dependencies import (
    get_db,
    get_current_user,
    require_manager_or_admin,
    require_admin,
    log_audit_action
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["Readiness"])


# ==================== LAZY IMPORTS ====================

def get_compliance_requirements_func():
    """Lazy import of get_compliance_requirements_for_employee from server.py"""
    from server import get_compliance_requirements_for_employee
    return get_compliance_requirements_for_employee


def get_work_readiness_3tier_func():
    """Lazy import of calculate_work_readiness_3tier from server.py"""
    from server import calculate_work_readiness_3tier
    return calculate_work_readiness_3tier


def get_employee_training_status_func():
    """Lazy import of evaluate_employee_training_status from server.py"""
    from server import evaluate_employee_training_status
    return evaluate_employee_training_status


def get_training_blocker_config_func():
    """Lazy import of get_training_blocker_config from server.py"""
    from server import get_training_blocker_config
    return get_training_blocker_config


def get_compliance_file_data_func():
    """Lazy import of get_compliance_file_data from server.py"""
    from server import get_compliance_file_data
    return get_compliance_file_data


def get_evaluate_recruitment_approval_func():
    """Lazy import of evaluate_recruitment_approval from server.py"""
    from server import evaluate_recruitment_approval
    return evaluate_recruitment_approval


async def get_employee_agreements_data(employee_id: str) -> dict:
    """
    Get agreement/acknowledgement data for an employee.
    Used by work readiness engine to check contract and handbook status.
    """
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0}) or {"id": employee_id}
    try:
        from agreement_document_service import (
            CONTRACT_AGREEMENT_TYPE,
            HANDBOOK_AGREEMENT_TYPE,
            resolve_employee_agreement_state,
        )

        contract_state = await resolve_employee_agreement_state(db, employee, CONTRACT_AGREEMENT_TYPE)
        handbook_state = await resolve_employee_agreement_state(db, employee, HANDBOOK_AGREEMENT_TYPE)

        acknowledgements = []
        for state in (contract_state, handbook_state):
            if not state:
                continue
            acknowledgements.append({
                "agreement_type": state.get("agreement_type"),
                "status": state.get("status"),
                "raw_status": state.get("raw_status"),
                "latest_active": bool(state.get("latest_active")),
                "source_record_id": state.get("source_record_id"),
                "template_version": state.get("template_version"),
                "can_sign": state.get("can_sign"),
                "can_acknowledge": state.get("can_acknowledge"),
                "current_lifecycle": state.get("current_lifecycle"),
            })

        return {"acknowledgements": acknowledgements}
    except Exception:
        # Typed incomplete fallback: preserve route shape while avoiding raw legacy rows.
        return {
            "acknowledgements": [
                {
                    "agreement_type": "contract_acceptance",
                    "status": "incomplete",
                    "raw_status": None,
                    "latest_active": False,
                    "source_record_id": None,
                    "template_version": None,
                    "can_sign": False,
                    "can_acknowledge": None,
                    "current_lifecycle": "unavailable",
                },
                {
                    "agreement_type": "handbook_acknowledgement",
                    "status": "incomplete",
                    "raw_status": None,
                    "latest_active": False,
                    "source_record_id": None,
                    "template_version": None,
                    "can_sign": None,
                    "can_acknowledge": False,
                    "current_lifecycle": "unavailable",
                },
            ]
        }


def get_evaluate_work_readiness_func():
    """Lazy import of evaluate_work_readiness from server.py"""
    from server import evaluate_work_readiness
    return evaluate_work_readiness


def get_evaluate_poa_compliance_func():
    """Lazy import of evaluate_poa_compliance from server.py"""
    from server import evaluate_poa_compliance
    return evaluate_poa_compliance


def get_poa_freshness_status_enum():
    """Lazy import of PoAFreshnessStatus enum from server.py"""
    from server import PoAFreshnessStatus
    return PoAFreshnessStatus


def get_employees_repo():
    """Lazy import of employees_repo from server.py"""
    from server import employees_repo
    return employees_repo


def get_employee_status():
    """Lazy import of EmployeeStatus from server.py"""
    from server import EmployeeStatus
    return EmployeeStatus


def get_onboarding_status():
    """Lazy import of OnboardingStatus from server.py"""
    from server import OnboardingStatus
    return OnboardingStatus


def get_calculate_employee_compliance():
    """Lazy import of calculate_employee_compliance from server.py"""
    from server import calculate_employee_compliance
    return calculate_employee_compliance


def get_excluded_doc_statuses() -> set[str]:
    """Lazy import of excluded document statuses."""
    from server import EXCLUDED_DOC_STATUSES
    return EXCLUDED_DOC_STATUSES


def get_unified_employee_status_func():
    """Lazy import of canonical unified status calculator."""
    from unified_compliance_engine import get_unified_employee_status
    return get_unified_employee_status


def get_service_user_onboarding_readiness_func():
    """Lazy import of service-user onboarding readiness reader."""
    from routes.service_users import get_service_user_onboarding_readiness
    return get_service_user_onboarding_readiness


async def adapt_unified_status_to_legacy_readiness(unified_status: dict, employee: dict) -> dict:
    """Map canonical unified status to legacy readiness response shape."""
    checks = unified_status.get("checks", {}) or {}
    blockers = unified_status.get("blockers", []) or []
    category_details = unified_status.get("category_details", {}) or {}

    form_items = category_details.get("forms", {}).get("items", []) or []
    training_items = category_details.get("training", {}).get("items", []) or []
    document_items = category_details.get("documents", {}).get("items", []) or []
    reference_items = category_details.get("references", {}).get("items", []) or []

    blocked_reasons = [
        {
            "code": blocker.get("id") or blocker.get("gate") or "unknown",
            "message": blocker.get("reason") or blocker.get("label") or "Requirement incomplete"
        }
        for blocker in blockers
    ]

    def _find_item(items: list[dict], item_id: str) -> dict:
        for item in items:
            if item.get("id") == item_id:
                return item
        return {}

    def _is_expired_from_documents(item: dict) -> bool:
        now_date = datetime.now(timezone.utc).date()
        for doc in item.get("documents", []) or []:
            expiry_str = doc.get("expiry_date")
            if not expiry_str:
                continue
            try:
                expiry_date = datetime.fromisoformat(str(expiry_str).replace("Z", "+00:00")).date()
            except (ValueError, TypeError):
                continue
            if expiry_date < now_date:
                return True
        return False

    rtw_doc_item = _find_item(document_items, "right_to_work")
    dbs_doc_item = _find_item(document_items, "dbs")
    id_doc_item = _find_item(document_items, "identity")

    rtw_passed = bool(checks.get("right_to_work"))
    dbs_passed = bool(checks.get("dbs"))
    id_passed = bool(checks.get("identity"))

    # Unified output does not currently expose explicit RTW/DBS check expiry booleans.
    # Use document expiry only as the least-misleading approximation for legacy expired flags.
    rtw_expired = _is_expired_from_documents(rtw_doc_item)
    dbs_expired = _is_expired_from_documents(dbs_doc_item)
    id_expired = _is_expired_from_documents(id_doc_item)

    rtw_has_upload = bool(rtw_doc_item.get("has_upload", False))
    dbs_has_upload = bool(dbs_doc_item.get("has_upload", False))
    id_has_upload = bool(id_doc_item.get("has_upload", False))

    health_item = _find_item(form_items, "staff_health_questionnaire")
    interview_item = _find_item(form_items, "interview_record")

    health_submitted = bool(health_item.get("submitted", False))
    health_decl = await db.health_declarations.find_one(
        {"employee_id": employee.get("id")},
        {"_id": 0, "status": 1, "reviewed_at": 1, "reviewed_by": 1},
        sort=[("reviewed_at", -1), ("submitted_at", -1), ("declaration_date", -1)],
    )
    health_status = (health_decl or {}).get("status")
    health_verified = health_status in {"fit", "conditional"}
    interview_submitted = bool(interview_item.get("submitted", False))
    interview_verified = bool(interview_item.get("verified", checks.get("interview_record", False)))

    training_legacy_items = []
    training_blockers = []
    training_warnings = []
    for item in training_items:
        completed = bool(item.get("completed"))
        invalid_reason = item.get("invalid_reason")
        has_record = bool(item.get("has_record"))
        status = "completed" if completed else "missing"
        if not completed and has_record:
            if isinstance(invalid_reason, str) and "expired" in invalid_reason.lower():
                status = "expired"
            else:
                status = "awaiting_review"
        entry = {
            "code": item.get("id"),
            "label": item.get("name"),
            "status": status,
            "blocker": not completed,
            "detail": invalid_reason or "Training requirement incomplete",
        }
        training_legacy_items.append(entry)
        if entry["blocker"]:
            if status == "awaiting_review":
                training_warnings.append(entry)
            else:
                training_blockers.append(entry)

    training_passed = bool(checks.get("mandatory_training"))

    references_verified = sum(1 for item in reference_items if item.get("completed"))
    poa_verified_count = int(_find_item(document_items, "proof_of_address").get("verified_count", 0) or 0)
    poa_required_count = int(_find_item(document_items, "proof_of_address").get("required_count", 2) or 2)

    # Preserve legacy tri-state status semantics using canonical blocker severities.
    has_critical_blocker = any((b.get("severity") or "").lower() == "critical" for b in blockers)
    has_any_blocker = len(blockers) > 0

    if not has_any_blocker:
        final_status = "READY_TO_WORK"
        label = "Ready to Work"
        color = "green"
    elif has_critical_blocker:
        final_status = "NOT_READY"
        label = "Not Ready to Work"
        color = "red"
    else:
        final_status = "READY_WITH_CONDITIONS"
        label = "Ready with Conditions"
        color = "amber"

    return {
        "ready": final_status == "READY_TO_WORK",
        "status": final_status,
        "label": label,
        "color": color,
        "blockedReasons": blocked_reasons,
        "checks": {
            "recruitmentApproved": employee.get("recruitment_approved", False),
            "referencesVerified": {
                "required": 2,
                "verified": references_verified,
                "passed": bool(checks.get("reference_1")) and bool(checks.get("reference_2"))
            },
            "proofOfAddress": {
                "required": poa_required_count,
                "verified": poa_verified_count,
                "passed": bool(checks.get("proof_of_address"))
            },
            "rightToWork": {
                "passed": rtw_passed,
                "missing": (not rtw_passed) and (not rtw_expired) and (not rtw_has_upload),
                "expired": rtw_expired
            },
            "dbs": {
                "passed": dbs_passed,
                "missing": (not dbs_passed) and (not dbs_expired) and (not dbs_has_upload),
                "expired": dbs_expired
            },
            "id": {
                "passed": id_passed,
                "missing": (not id_passed) and (not id_expired) and (not id_has_upload),
                "expired": id_expired
            },
            "healthForm": {
                "passed": health_verified,
                "submitted": health_submitted,
                "verified": health_verified,
                "outcome": health_status or "missing",
                "reviewed_at": (health_decl or {}).get("reviewed_at"),
                "reviewed_by": (health_decl or {}).get("reviewed_by"),
            },
            "interviewForm": {
                "passed": interview_verified,
                "submitted": interview_submitted,
                "verified": interview_verified
            },
            "training": {
                "passed": training_passed,
                "blockerCount": len(training_blockers),
                "warningCount": len(training_warnings),
                "overall": "complete" if training_passed else "incomplete",
                # Legacy training evaluator exposed richer diagnostics; adapter keeps best-effort item parity from structured unified data.
                "items": training_legacy_items
            }
        },
        "calculatedAt": datetime.now(timezone.utc).isoformat(),
        "source_of_truth": "unified_employee_status_adapter"
    }


def calculate_audit_score(ready: int, review: int, pending: int, 
                         policies_missing: int, insurance_missing: int, 
                         critical_missing: int) -> dict:
    """Calculate overall audit readiness score"""
    total_staff = ready + review + pending
    if total_staff == 0:
        staff_score = 100
    else:
        staff_score = int((ready / total_staff) * 100)
    
    # Deduct points for missing items
    penalty = min(50, (policies_missing * 2) + (insurance_missing * 5) + (critical_missing * 3))
    overall = max(0, min(100, staff_score - penalty))
    
    if overall >= 80:
        status = "Audit Ready"
        color = "success"
    elif overall >= 60:
        status = "Needs Attention"
        color = "warning"
    else:
        status = "Critical Issues"
        color = "error"
    
    return {
        "score": overall,
        "status": status,
        "color": color,
        "staff_readiness": staff_score
    }


def _extract_requirement_rows(compliance_requirements: Any) -> List[Dict[str, Any]]:
    if not compliance_requirements:
        return []
    if isinstance(compliance_requirements, list):
        return [row for row in compliance_requirements if isinstance(row, dict)]
    if isinstance(compliance_requirements, dict):
        statuses = compliance_requirements.get("statuses") or {}
        requirements = statuses.get("requirements")
        if isinstance(requirements, list):
            return [row for row in requirements if isinstance(row, dict)]
    return []


def _safe_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _append_unique(target: List[str], value: str):
    if value and value not in target:
        target.append(value)


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _make_alert_row(
    title: str,
    category: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    link_target: str,
    source: str,
    *,
    due_date: Optional[str] = None,
    expiry_date: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "title": title,
        "category": category,
        "severity": severity,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "due_date": due_date,
        "expiry_date": expiry_date,
        "link_target": link_target,
        "source": source,
    }


# ==================== READINESS ENDPOINTS ====================

# NOTE: readiness-summary MUST be defined BEFORE {employee_id}/readiness
# to prevent FastAPI from matching "readiness-summary" as an employee_id

@router.get("/employees/readiness-summary")
async def get_employees_readiness_summary(
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get readiness summary for all employees (employee-scope only).
    
    Returns counts by readiness status for dashboard widgets.
    """
    employees_repo = get_employees_repo()
    get_compliance_requirements_for_employee = get_compliance_requirements_func()
    calculate_work_readiness_3tier = get_work_readiness_3tier_func()
    
    # Get all employees (not applicants)
    employees = await employees_repo.list_employees(
        filter_dict={"status": status} if status else None,
        projection={"_id": 0, "id": 1, "status": 1, "role": 1, "recruitment_approved": 1}
    )
    
    summary = {
        "total_employees": len(employees),
        "ready_to_work": 0,
        "ready_with_conditions": 0,
        "not_ready": 0,
        "by_blocking_reason": {}
    }
    
    for emp in employees:
        requirements = await get_compliance_requirements_for_employee(emp['id'], emp.get('role', ''))
        readiness = await calculate_work_readiness_3tier(emp['id'], requirements, emp, emp.get('role', ''))
        
        status_key = readiness.get('status', 'NOT_READY')
        if status_key == 'READY_TO_WORK':
            summary['ready_to_work'] += 1
        elif status_key == 'READY_WITH_CONDITIONS':
            summary['ready_with_conditions'] += 1
        else:
            summary['not_ready'] += 1
            
            # Track blocking reasons
            for reason in readiness.get('reasons', []):
                code = reason.get('code', 'unknown')
                if code not in summary['by_blocking_reason']:
                    summary['by_blocking_reason'][code] = 0
                summary['by_blocking_reason'][code] += 1
    
    return summary


@router.get("/employees/{employee_id}/readiness")
async def get_employee_readiness(employee_id: str, user: dict = Depends(get_current_user)):
    """
    Get authoritative readiness calculation for an employee.
    
    This is the SINGLE SOURCE OF TRUTH for readiness.
    All UI components (dashboard, profile, list badges, exports) must use this same calculation.
    
    Returns:
        - ready: boolean - whether employee can work
        - status: "NOT_READY" | "READY_WITH_CONDITIONS" | "READY_TO_WORK"
        - blockedReasons: Array of reasons with stable codes
        - checks: Detailed check status for each requirement category
        - calculatedAt: ISO timestamp
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    get_unified_employee_status = get_unified_employee_status_func()
    unified_status = await get_unified_employee_status(
        employee_id,
        db,
        user_role="admin",
        include_details=True,
    )

    if unified_status.get("error") == "Employee not found":
        raise HTTPException(status_code=404, detail="Employee not found")

    adapted_response = await adapt_unified_status_to_legacy_readiness(unified_status, employee)

    # Temporary parity logging for rollout safety.
    logger.info(
        "readiness_adapter employee_id=%s blockers=%s status=%s ready=%s",
        employee_id,
        unified_status.get("blocker_count", 0),
        adapted_response.get("status"),
        adapted_response.get("ready"),
    )

    return adapted_response


# ==================== RECRUITMENT APPROVAL ENGINE ENDPOINTS ====================

@router.get("/employees/{employee_id}/recruitment-approval-check")
async def check_recruitment_approval(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Preview recruitment approval readiness.
    
    Returns:
    - can_approve: whether applicant can be approved now
    - blockers: list of requirements blocking approval
    - warnings: non-blocking issues
    - verified_count / required_count: progress tracking
    """
    db = get_db()
    get_compliance_file_data = get_compliance_file_data_func()
    evaluate_recruitment_approval = get_evaluate_recruitment_approval_func()
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        # P0 stability: timeout heavy helpers and return fallback instead of 502
        compliance_file = await asyncio.wait_for(get_compliance_file_data(employee_id, employee), timeout=8.0)
        sections = compliance_file.get("sections", {})
        evaluation = evaluate_recruitment_approval(employee, sections)
    except asyncio.TimeoutError:
        logger.warning("recruitment-approval-check timeout employee_id=%s", employee_id)
        return {
            "employee_id": employee_id,
            "can_approve": False,
            "status_unavailable": True,
            "message": "Status checks temporarily unavailable",
            "blockers": [],
            "warnings": [],
            "verified_count": 0,
            "required_count": 0,
            "blocker_count": 0,
        }
    except Exception as exc:
        logger.warning("recruitment-approval-check error employee_id=%s error=%s", employee_id, exc)
        return {
            "employee_id": employee_id,
            "can_approve": False,
            "status_unavailable": True,
            "message": "Status checks temporarily unavailable",
            "blockers": [],
            "warnings": [],
            "verified_count": 0,
            "required_count": 0,
            "blocker_count": 0,
        }

    # Attach canonical interview truth from stage-gate resolver.
    stage_gate = StageGateService(db)
    try:
        gate = await asyncio.wait_for(stage_gate.evaluate_recruitment_gate(employee_id), timeout=8.0)
    except Exception as exc:
        logger.warning("recruitment-approval-check gate fallback employee_id=%s error=%s", employee_id, exc)
        gate = {"allowed": False, "blocking_items": [], "warning_items": []}
    interview = gate.get("interview") or {
        "exists": False,
        "completed": False,
        "passed": None,
        "score": None,
        "pass_mark": None,
        "reviewed_at": None,
        "source_record_id": None,
    }

    blockers = list(evaluation.get("blockers", []))
    blockers = [b for b in blockers if b.get("requirement_key") != "interview_record"]

    if not interview.get("exists"):
        blockers.append({
            "requirement_key": "interview_record",
            "label": "Interview Record",
            "reason": "No interview assessment record found",
            "section": "forms",
        })
    elif not interview.get("completed"):
        blockers.append({
            "requirement_key": "interview_record",
            "label": "Interview Record",
            "reason": "Interview record exists but is still draft/incomplete",
            "section": "forms",
        })
    elif interview.get("passed") is False:
        blockers.append({
            "requirement_key": "interview_record",
            "label": "Interview Record",
            "reason": "Interview outcome is failed",
            "section": "forms",
        })
    elif interview.get("passed") is None:
        blockers.append({
            "requirement_key": "interview_record",
            "label": "Interview Record",
            "reason": "Interview completed but no pass/fail outcome is recorded",
            "section": "forms",
        })

    required_keys = list(evaluation.get("required_keys", []))
    verified_keys = [k for k in evaluation.get("verified_keys", []) if k != "interview_record"]
    if interview.get("exists") and interview.get("completed") and interview.get("passed") is True and "interview_record" in required_keys:
        verified_keys.append("interview_record")

    blocker_count = len(blockers)
    required_count = int(evaluation.get("required_count", len(required_keys)))
    verified_count = len(set(verified_keys))

    evaluation["blockers"] = blockers
    evaluation["blocker_count"] = blocker_count
    evaluation["verified_keys"] = list(dict.fromkeys(verified_keys))
    evaluation["verified_count"] = verified_count
    evaluation["required_count"] = required_count
    evaluation["can_approve"] = blocker_count == 0

    evaluation["interview"] = interview
    evaluation["gate"] = gate
    evaluation["source_of_truth"] = {
        "interview": "form_submissions.requirement_id=interview_record"
    }

    # Domain-level blocker slices for UI summaries.
    get_unified_employee_status = get_unified_employee_status_func()
    try:
        unified_status = await asyncio.wait_for(
            get_unified_employee_status(
                employee_id,
                db,
                user_role="admin",
                include_details=False,
            ),
            timeout=8.0,
        )
    except Exception as exc:
        logger.warning("recruitment-approval-check uce fallback employee_id=%s error=%s", employee_id, exc)
        unified_status = {}
    uce_blockers = unified_status.get("blockers", []) if isinstance(unified_status, dict) else []

    def _domain_entries(domain_name: str):
        return [
            {
                "id": b.get("id") or b.get("gate"),
                "label": b.get("label"),
                "reason": b.get("reason"),
                "severity": b.get("severity", "critical"),
            }
            for b in uce_blockers
            if (b.get("category") or "").lower() == domain_name
        ]

    evaluation["domains"] = {
        "documents": {"blockers": _domain_entries("documents")},
        "references": {"blockers": _domain_entries("references")},
        "training": {"blockers": _domain_entries("training")},
        "agreements": {"blockers": _domain_entries("agreements")},
        "employment_history": {
            "blockers": [
                {
                    "id": b.get("id") or b.get("gate"),
                    "label": b.get("label"),
                    "reason": b.get("reason"),
                    "severity": b.get("severity", "critical"),
                }
                for b in uce_blockers
                if (b.get("id") or b.get("gate")) in {"employment_gaps", "employment_history_verification"}
            ]
        },
    }
    
    return evaluation


# ==================== WORK READINESS ENGINE ENDPOINTS (GATE 2) ====================

@router.get("/employees/{employee_id}/work-readiness-check")
async def check_work_readiness(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Evaluate work readiness (Gate 2) - Can this employee start work?
    
    This is separate from recruitment approval (Gate 1).
    Checks:
    - Contract and handbook acknowledgement verified
    - Induction and health questionnaire completed/verified
    - Role-specific competency (care certificate / clinical competency)
    - Required training matrix satisfied
    - Critical documents not expired (RTW, DBS, Identity, NMC)
    
    Returns:
    - can_work: whether employee can start work now
    - readiness_status: READY_TO_WORK | READY_WITH_CONDITIONS | NOT_READY
    - blockers: list of requirements blocking work
    - warnings: non-blocking issues (e.g., expiring soon)
    - verified_count / required_count: progress tracking
    """
    db = get_db()
    get_compliance_file_data = get_compliance_file_data_func()
    evaluate_employee_training_status = get_employee_training_status_func()
    evaluate_work_readiness = get_evaluate_work_readiness_func()
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get compliance file sections
    compliance_file = await get_compliance_file_data(employee_id, employee)
    sections = compliance_file.get("sections", {})
    
    # Get agreements data
    agreements_data = await get_employee_agreements_data(employee_id)
    
    # Get training status
    role = employee.get("role", "")
    training_status = await evaluate_employee_training_status(employee_id, role)
    
    # Evaluate work readiness
    evaluation = await evaluate_work_readiness(
        person=employee,
        compliance_sections=sections,
        agreements_data=agreements_data,
        training_status=training_status,
        db=db
    )

    # Parity gate: UCE is the authoritative truth source for all readiness signals.
    # If UCE marks the employee as NOT work-ready, we must downgrade the WRE result
    # so the WorkReadinessPanel never shows green while the header banner shows red.
    try:
        get_unified_employee_status = get_unified_employee_status_func()
        uce_status = await get_unified_employee_status(
            employee_id, db, user_role="admin", include_details=False
        )
        if not uce_status.get("error"):
            uce_is_work_ready = uce_status.get("is_work_ready", False)
            if not uce_is_work_ready:
                evaluation["can_work"] = False
                evaluation["readiness_status"] = "NOT_READY"
                # Merge UCE blockers not already represented by WRE keys
                wre_keys = {b.get("requirement_key") for b in evaluation.get("blockers", [])}
                for uce_blocker in uce_status.get("blockers", []):
                    blocker_id = uce_blocker.get("id") or uce_blocker.get("gate") or ""
                    if blocker_id and blocker_id not in wre_keys:
                        evaluation.setdefault("blockers", []).append({
                            "requirement_key": blocker_id,
                            "label": uce_blocker.get("label", blocker_id.replace("_", " ").title()),
                            "reason": uce_blocker.get("reason", "Requirement not met"),
                            "category": uce_blocker.get("category", "compliance"),
                            "section": "compliance",
                        })
                evaluation["blocker_count"] = len(evaluation.get("blockers", []))
    except Exception:
        # UCE parity is best-effort; WRE result stands if UCE is unavailable
        pass

    return evaluation


# ==================== PROOF OF ADDRESS FRESHNESS ENDPOINTS ====================

@router.get("/employees/{employee_id}/poa-freshness")
async def get_poa_freshness(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get Proof of Address freshness evaluation.
    
    Policy: 2 documents within 12 months required.
    
    Returns:
    - overall_status: complete | partial | review_needed | incomplete
    - valid_count: documents within 12 months
    - expired_count: documents older than 12 months
    - unclear_count: documents without extractable date (need manual review)
    - documents: list with freshness details for each
    - blockers: list of issues
    """
    db = get_db()
    evaluate_poa_compliance = get_evaluate_poa_compliance_func()
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get PoA documents - use global constant for sync
    excluded_doc_statuses = get_excluded_doc_statuses()
    poa_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$in": ["proof_of_address", "proof_of_address_evidence", "address_proof", "proof_of_address_2", "proof_of_address_3", "proof_of_address_4", "proof_of_address_5"]},
        "status": {"$nin": EXCLUDED_DOC_STATUSES}
    }, {"_id": 0}).to_list(50)
    
    # Enrich with extraction data
    for doc in poa_docs:
        extraction = await db.document_extractions.find_one(
            {"document_id": doc.get("id")},
            {"_id": 0}
        )
        if extraction:
            doc["extraction_result"] = extraction
            # Get document date from extraction
            fields = extraction.get("fields", {})
            if fields.get("document_date"):
                doc["extracted_date"] = fields["document_date"]
    
    # Evaluate freshness
    evaluation = evaluate_poa_compliance(poa_docs)
    evaluation["employee_id"] = employee_id
    evaluation["employee_name"] = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    return evaluation


@router.post("/employees/{employee_id}/poa-freshness/override")
async def override_poa_freshness(
    employee_id: str,
    document_id: str,
    reason: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Manually override freshness status for a PoA document.
    
    Use when:
    - Document date could not be extracted but admin verifies it's valid
    - Document is slightly over 12 months but business needs justify approval
    
    Creates audit trail of the override.
    """
    import uuid
    db = get_db()
    PoAFreshnessStatus = get_poa_freshness_status_enum()
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Verify document exists and belongs to employee
    document = await db.employee_documents.find_one({
        "id": document_id,
        "employee_id": employee_id
    })
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get admin info
    admin = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    admin_name = admin.get("name", user['user_id']) if admin else user['user_id']
    
    # Update document with freshness override
    now = datetime.now(timezone.utc).isoformat()
    
    await db.employee_documents.update_one(
        {"id": document_id},
        {"$set": {
            "freshness_override": True,
            "freshness_status": PoAFreshnessStatus.MANUAL_OVERRIDE.value,
            "freshness_override_at": now,
            "freshness_override_by": user['user_id'],
            "freshness_override_by_name": admin_name,
            "freshness_override_reason": reason
        }}
    )
    
    # Write audit log
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "poa_freshness_override",
        "entity_type": "document",
        "entity_id": document_id,
        "employee_id": employee_id,
        "performed_by": user['user_id'],
        "performed_by_name": admin_name,
        "details": {
            "reason": reason,
            "document_file": document.get("file_name") or document.get("original_filename")
        },
        "created_at": now
    })
    
    return {
        "status": "success",
        "message": "Freshness override applied",
        "document_id": document_id,
        "freshness_status": PoAFreshnessStatus.MANUAL_OVERRIDE.value
    }


# ==================== AUDIT READINESS DASHBOARD ====================

@router.get("/dashboard/audit-readiness")
async def get_audit_readiness_dashboard(user: dict = Depends(require_manager_or_admin)):
    """Get audit readiness dashboard with smart compliance metrics"""
    db = get_db()
    EmployeeStatus = get_employee_status()
    OnboardingStatus = get_onboarding_status()
    get_calculate_employee_compliance_func = get_calculate_employee_compliance()
    
    # Get all active/onboarding employees
    employees = await db.employees.find(
        {"status": {"$in": [EmployeeStatus.ACTIVE, EmployeeStatus.ONBOARDING, EmployeeStatus.NEW, 
                           EmployeeStatus.SCREENING, EmployeeStatus.INTERVIEW, EmployeeStatus.COMPLIANCE_REVIEW]}},
        {"_id": 0, "id": 1, "role": 1, "onboarding_status": 1, "status": 1}
    ).to_list(500)
    
    # Initialize counters
    ready_for_placement = 0
    under_review = 0
    documents_pending = 0
    new_employees = 0
    active_employees = 0
    
    missing_critical = 0
    employees_with_missing_items = []
    
    # Onboarding status counts
    for emp in employees:
        status = emp.get("onboarding_status", "New")
        if status == OnboardingStatus.READY_FOR_PLACEMENT:
            ready_for_placement += 1
        elif status == OnboardingStatus.UNDER_REVIEW:
            under_review += 1
        elif status == OnboardingStatus.DOCUMENTS_PENDING:
            documents_pending += 1
        elif status == OnboardingStatus.NEW:
            new_employees += 1
        elif status == OnboardingStatus.ACTIVE:
            active_employees += 1
    
    # Check for critical missing items (sample first 50 employees)
    sample_employees = employees[:50]
    for emp in sample_employees:
        compliance = await get_calculate_employee_compliance_func(emp["id"], emp.get("role", ""))
        if compliance["missing_count"] > 0:
            critical_missing = [
                item["name"] for item in compliance["items"] 
                if item["status"] == "missing" and item["id"] in ["dbs", "identity_rtw", "references", "safeguarding"]
            ]
            if critical_missing:
                missing_critical += 1
                if len(employees_with_missing_items) < 10:
                    employees_with_missing_items.append({
                        "employee_id": emp["id"],
                        "missing_items": critical_missing
                    })
    
    # Expiring documents
    now = datetime.now(timezone.utc)
    exp_30 = (now + timedelta(days=30)).isoformat()
    
    expiring_dbs = await db.employee_documents.count_documents({
        "document_type": "dbs",
        "expiry_date": {"$lte": exp_30, "$gt": now.isoformat()}
    })
    
    expiring_training = await db.training_records.count_documents({
        "expiry_date": {"$lte": exp_30, "$gt": now.isoformat()}
    })
    
    # Organisation compliance
    policies_missing = await db.org_policies.count_documents({"status": "missing"})
    policies_total = await db.org_policies.count_documents({})
    
    insurance_missing = await db.insurance_docs.count_documents({"status": "missing"})
    insurance_expiring = await db.insurance_docs.count_documents({
        "expiry_date": {"$lte": exp_30, "$gt": now.isoformat()}
    })
    insurance_total = await db.insurance_docs.count_documents({})
    
    return {
        "staff_compliance": {
            "total_staff": len(employees),
            "ready_for_placement": ready_for_placement,
            "under_review": under_review,
            "documents_pending": documents_pending,
            "new_employees": new_employees,
            "active_employees": active_employees
        },
        "critical_alerts": {
            "missing_critical_items": missing_critical,
            "expiring_dbs": expiring_dbs,
            "expiring_training": expiring_training,
            "employees_with_issues": employees_with_missing_items
        },
        "organisation_compliance": {
            "policies_uploaded": policies_total - policies_missing,
            "policies_missing": policies_missing,
            "policies_total": policies_total,
            "insurance_valid": insurance_total - insurance_missing - insurance_expiring,
            "insurance_missing": insurance_missing,
            "insurance_expiring": insurance_expiring,
            "insurance_total": insurance_total
        },
        "audit_readiness_score": calculate_audit_score(
            ready_for_placement, under_review, documents_pending,
            policies_missing, insurance_missing, missing_critical
        )
    }


@router.get("/staff/compliance-dashboard")
async def get_staff_compliance_dashboard(
    status: str = Query(default="all"),
    user: dict = Depends(require_manager_or_admin),
):
    """
    Thin dashboard aggregation endpoint for cross-employee compliance triage.

    Reuses existing employee list + compliance requirement evaluation + readiness reasons,
    without introducing a second compliance engine.
    """
    allowed_filters = {"all", "compliant", "missing", "expiring", "expired"}
    normalized_filter = _safe_lower(status) or "all"
    if normalized_filter not in allowed_filters:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    employees_repo = get_employees_repo()
    get_compliance_requirements_for_employee = get_compliance_requirements_func()
    calculate_work_readiness_3tier = get_work_readiness_3tier_func()
    db = get_db()

    employees = await employees_repo.list_employees(
        projection={"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1, "job_title": 1}
    )

    missing_statuses = {"missing", "pending", "not_started", "not_completed", "awaiting_review", "rejected"}
    expiring_statuses = {"expiring", "expiring_soon", "due_soon", "urgent"}
    expired_statuses = {"expired", "overdue"}

    items: List[Dict[str, Any]] = []
    for employee in employees:
        employee_id = employee.get("id")
        if not employee_id:
            continue

        compliance_requirements = await get_compliance_requirements_for_employee(employee_id, employee.get("role", ""))
        requirement_rows = _extract_requirement_rows(compliance_requirements)

        missing_items: List[str] = []
        expiring_soon: List[str] = []
        expired_items: List[str] = []

        for requirement in requirement_rows:
            label = (
                requirement.get("name")
                or requirement.get("label")
                or requirement.get("title")
                or requirement.get("key")
                or requirement.get("id")
                or "Unknown requirement"
            )
            req_status = _safe_lower(requirement.get("status"))
            if req_status in expired_statuses:
                _append_unique(expired_items, label)
            elif req_status in expiring_statuses:
                _append_unique(expiring_soon, label)
            elif req_status in missing_statuses:
                _append_unique(missing_items, label)

        blockers: List[str] = []
        warnings: List[str] = []

        cached_summary = await db.employee_compliance_summary.find_one(
            {"employee_id": employee_id},
            {"_id": 0, "blockers": 1, "warnings": 1, "requirements": 1},
        )
        for blocker in (cached_summary or {}).get("blockers", []):
            blocker_message = blocker.get("reason") or blocker.get("label") or blocker.get("requirement")
            _append_unique(blockers, str(blocker_message or ""))
        for warning in (cached_summary or {}).get("warnings", []):
            warning_message = warning.get("message") or warning.get("label") or warning.get("requirement")
            _append_unique(warnings, str(warning_message or ""))

        readiness = await calculate_work_readiness_3tier(
            employee_id,
            requirement_rows,
            employee,
            employee.get("role", ""),
        )
        for reason in readiness.get("reasons", []) or []:
            reason_message = str(reason.get("message") or reason.get("code") or "").strip()
            if not reason_message:
                continue
            reason_type = _safe_lower(reason.get("type"))
            if reason_type in {"hard_block", "blocker"}:
                _append_unique(blockers, reason_message)
            else:
                _append_unique(warnings, reason_message)

        # Ensure employment gaps and interview signals are represented if pending.
        for requirement in requirement_rows:
            req_key = _safe_lower(requirement.get("key") or requirement.get("id"))
            req_status = _safe_lower(requirement.get("status"))
            req_name = requirement.get("name") or requirement.get("label") or req_key
            if req_key in {"employment_history_verification", "interview_record"} and req_status in missing_statuses.union(expired_statuses):
                _append_unique(missing_items, str(req_name))

        if expired_items:
            overall_status = "expired"
        elif missing_items:
            overall_status = "missing"
        elif expiring_soon:
            overall_status = "expiring"
        else:
            overall_status = "compliant"

        if normalized_filter != "all" and overall_status != normalized_filter:
            continue

        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() or employee_id
        role_or_job_title = employee.get("job_title") or employee.get("role") or "—"

        items.append({
            "employee_id": employee_id,
            "employee_name": employee_name,
            "role": role_or_job_title,
            "job_title": role_or_job_title,
            "overall_status": overall_status,
            "compliant": overall_status == "compliant",
            "missing_items": missing_items,
            "expiring_soon": expiring_soon,
            "expired_items": expired_items,
            "blockers": blockers,
            "warnings": warnings,
        })

    return {
        "filter": normalized_filter,
        "total": len(items),
        "items": items,
    }


@router.get("/compliance/alerts-summary")
async def get_compliance_alerts_summary(
    limit: int = Query(default=500, ge=1, le=1000),
    user: dict = Depends(require_manager_or_admin),
):
    """
    Read-only cross-system compliance alerts summary.

    Reuses existing collections and existing readiness/onboarding summaries.
    Does not create new workflows or engines.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    expiring_cutoff = now + timedelta(days=30)

    alerts: List[Dict[str, Any]] = []
    excluded_doc_statuses = get_excluded_doc_statuses()

    # ------------------------------------------------------------------
    # 1) Expired / expiring staff documents
    # ------------------------------------------------------------------
    employee_ids_for_docs = set()
    doc_rows = await db.employee_documents.find(
        {
            "expiry_date": {"$exists": True, "$ne": None},
            "status": {"$nin": list(excluded_doc_statuses)},
        },
        {"_id": 0, "employee_id": 1, "document_type": 1, "expiry_date": 1},
    ).to_list(5000)

    for row in doc_rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if employee_id:
            employee_ids_for_docs.add(employee_id)

    employee_lookup: Dict[str, str] = {}
    if employee_ids_for_docs:
        employee_rows = await db.employees.find(
            {"id": {"$in": list(employee_ids_for_docs)}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1},
        ).to_list(2000)
        for emp in employee_rows:
            emp_id = str(emp.get("id") or "").strip()
            if not emp_id:
                continue
            employee_lookup[emp_id] = (
                f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or emp_id
            )

    for row in doc_rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if not employee_id:
            continue
        expiry_date = row.get("expiry_date")
        expiry_dt = _parse_iso_datetime(expiry_date)
        if not expiry_dt:
            continue
        if expiry_dt <= now:
            severity = "urgent"
            title = f"Expired {row.get('document_type') or 'document'}"
        elif expiry_dt <= expiring_cutoff:
            severity = "warning"
            title = f"Expiring soon {row.get('document_type') or 'document'}"
        else:
            continue
        alerts.append(
            _make_alert_row(
                title=title,
                category="staff_documents",
                severity=severity,
                entity_type="employee",
                entity_id=employee_id,
                entity_name=employee_lookup.get(employee_id, employee_id),
                expiry_date=expiry_date,
                link_target=f"/portal/employees/{employee_id}",
                source="employee_documents",
            )
        )

    # ------------------------------------------------------------------
    # 2) Expired / expiring training
    # ------------------------------------------------------------------
    training_rows = await db.training_records.find(
        {
            "expiry_date": {"$exists": True, "$ne": None},
            "record_status": {"$ne": "superseded"},
        },
        {"_id": 0, "employee_id": 1, "training_name": 1, "expiry_date": 1},
    ).to_list(5000)

    for row in training_rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if not employee_id:
            continue
        expiry_date = row.get("expiry_date")
        expiry_dt = _parse_iso_datetime(expiry_date)
        if not expiry_dt:
            continue
        if expiry_dt <= now:
            severity = "urgent"
            title = f"Expired training: {row.get('training_name') or 'Training'}"
        elif expiry_dt <= expiring_cutoff:
            severity = "warning"
            title = f"Expiring soon training: {row.get('training_name') or 'Training'}"
        else:
            continue
        alerts.append(
            _make_alert_row(
                title=title,
                category="staff_training",
                severity=severity,
                entity_type="employee",
                entity_id=employee_id,
                entity_name=employee_lookup.get(employee_id, employee_id),
                expiry_date=expiry_date,
                link_target=f"/portal/employees/{employee_id}",
                source="training_records",
            )
        )

    # ------------------------------------------------------------------
    # 3) Missing staff compliance items (reuses existing dashboard logic)
    # ------------------------------------------------------------------
    missing_dashboard = await get_staff_compliance_dashboard(status="missing", user=user)
    for item in missing_dashboard.get("items", []):
        employee_id = str(item.get("employee_id") or "").strip()
        missing_items = [str(v).strip() for v in item.get("missing_items", []) if str(v).strip()]
        if not employee_id or not missing_items:
            continue
        alerts.append(
            _make_alert_row(
                title=f"Missing compliance items ({len(missing_items)})",
                category="staff_compliance",
                severity="missing",
                entity_type="employee",
                entity_id=employee_id,
                entity_name=item.get("employee_name") or employee_lookup.get(employee_id, employee_id),
                link_target=f"/portal/employees/{employee_id}",
                source="staff_compliance_dashboard",
            )
        )

    # ------------------------------------------------------------------
    # 4) Overdue active care plan reviews
    # ------------------------------------------------------------------
    care_plan_rows = await db.service_user_care_plans.find(
        {
            "status": "active",
            "next_review_due_at": {"$exists": True, "$ne": None},
        },
        {
            "_id": 0,
            "id": 1,
            "service_user_id": 1,
            "care_plan_title": 1,
            "next_review_due_at": 1,
        },
    ).to_list(2000)

    service_user_ids = {
        str(row.get("service_user_id") or "").strip()
        for row in care_plan_rows
        if str(row.get("service_user_id") or "").strip()
    }
    service_user_name_lookup: Dict[str, str] = {}
    if service_user_ids:
        service_user_rows = await db.service_users.find(
            {"id": {"$in": list(service_user_ids)}},
            {"_id": 0, "id": 1, "full_name": 1, "service_user_code": 1},
        ).to_list(2000)
        for su in service_user_rows:
            sid = str(su.get("id") or "").strip()
            if not sid:
                continue
            service_user_name_lookup[sid] = su.get("full_name") or su.get("service_user_code") or sid

    for row in care_plan_rows:
        due_date = row.get("next_review_due_at")
        due_dt = _parse_iso_datetime(due_date)
        if not due_dt or due_dt > now:
            continue
        service_user_id = str(row.get("service_user_id") or "").strip()
        if not service_user_id:
            continue
        plan_title = row.get("care_plan_title") or "Care plan"
        alerts.append(
            _make_alert_row(
                title=f"Overdue care plan review: {plan_title}",
                category="care_plan_review",
                severity="urgent",
                entity_type="service_user",
                entity_id=service_user_id,
                entity_name=service_user_name_lookup.get(service_user_id, service_user_id),
                due_date=due_date,
                link_target=f"/portal/service-users/{service_user_id}",
                source="service_user_care_plans",
            )
        )

    # ------------------------------------------------------------------
    # 5) Incomplete service-user onboarding (reuse existing onboarding endpoint)
    # ------------------------------------------------------------------
    onboarding_reader = get_service_user_onboarding_readiness_func()
    service_users = await db.service_users.find(
        {},
        {"_id": 0, "id": 1, "full_name": 1, "service_user_code": 1},
    ).to_list(500)

    for su in service_users:
        service_user_id = str(su.get("id") or "").strip()
        if not service_user_id:
            continue
        onboarding = await onboarding_reader(service_user_id=service_user_id, user=user)
        overall_status = _safe_lower(onboarding.get("overall_status"))
        if overall_status == "ready":
            continue
        missing_count = int(onboarding.get("missing_count") or 0)
        review_due_count = int(onboarding.get("review_due_count") or 0)
        if missing_count > 0:
            severity = "missing"
            title = f"Onboarding incomplete ({missing_count} missing)"
        else:
            severity = "warning"
            title = f"Onboarding review due ({review_due_count})"
        alerts.append(
            _make_alert_row(
                title=title,
                category="service_user_onboarding",
                severity=severity,
                entity_type="service_user",
                entity_id=service_user_id,
                entity_name=su.get("full_name") or su.get("service_user_code") or service_user_id,
                link_target=f"/portal/service-users/{service_user_id}",
                source="service_user_onboarding_readiness",
            )
        )

    # ------------------------------------------------------------------
    # 6) Open safeguarding incidents
    # ------------------------------------------------------------------
    safeguarding_rows = await db.incident_logs.find(
        {
            "status": {"$in": ["open", "reviewing", "under_review", "investigating"]},
            "$or": [
                {"safeguarding_concern": True},
                {"incident_type": "safeguarding"},
            ],
        },
        {
            "_id": 0,
            "id": 1,
            "incident_type": 1,
            "service_user_id": 1,
            "status": 1,
            "date_occurred": 1,
            "service_user_name": 1,
        },
    ).to_list(1000)

    safeguarding_incident_names: Dict[str, str] = {}
    for row in safeguarding_rows:
        incident_id = str(row.get("id") or "").strip()
        if not incident_id:
            continue
        service_user_id = str(row.get("service_user_id") or "").strip()
        entity_name = row.get("service_user_name") or service_user_name_lookup.get(service_user_id) or incident_id
        safeguarding_incident_names[incident_id] = entity_name
        alerts.append(
            _make_alert_row(
                title="Open safeguarding concern",
                category="incidents",
                severity="safeguarding",
                entity_type="incident",
                entity_id=incident_id,
                entity_name=entity_name,
                due_date=row.get("date_occurred"),
                link_target="/portal/compliance-centre",
                source="incident_logs",
            )
        )

    # ------------------------------------------------------------------
    # 7) Overdue safeguarding follow-up tasks (reuses recurring_compliance)
    # ------------------------------------------------------------------
    recurring_collection = getattr(db, "recurring_compliance", None)
    followup_rows = []
    if recurring_collection is not None:
        followup_rows = await recurring_collection.find(
            {
                "item_type": "report_followup",
                "is_active": True,
                "linked_incident_id": {"$exists": True, "$ne": None},
                "next_due_date": {"$exists": True, "$ne": None},
            },
            {
                "_id": 0,
                "id": 1,
                "linked_incident_id": 1,
                "next_due_date": 1,
            },
        ).to_list(3000)

    for row in followup_rows:
        incident_id = str(row.get("linked_incident_id") or "").strip()
        if not incident_id:
            continue
        if incident_id not in safeguarding_incident_names:
            continue
        due_value = row.get("next_due_date")
        due_dt = _parse_iso_datetime(due_value)
        if not due_dt or due_dt > now:
            continue

        alerts.append(
            _make_alert_row(
                title="Overdue safeguarding follow-up",
                category="incidents",
                severity="safeguarding",
                entity_type="incident",
                entity_id=incident_id,
                entity_name=safeguarding_incident_names.get(incident_id, incident_id),
                due_date=due_value,
                link_target="/portal/compliance-centre",
                source="recurring_compliance",
            )
        )

    # ------------------------------------------------------------------
    # 8) Overdue competency reviews (reuses competency_records)
    # ------------------------------------------------------------------
    competency_collection = getattr(db, "competency_records", None)
    competency_rows = []
    if competency_collection is not None:
        competency_rows = await competency_collection.find(
            {
                "$or": [
                    {"review_due_date": {"$exists": True, "$ne": None}},
                    {"review_due_at": {"$exists": True, "$ne": None}},
                ]
            },
            {
                "_id": 0,
                "id": 1,
                "employee_id": 1,
                "competency_name": 1,
                "review_due_date": 1,
                "review_due_at": 1,
            },
        ).to_list(5000)

    for row in competency_rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if not employee_id:
            continue
        due_value = row.get("review_due_at") or row.get("review_due_date")
        due_dt = _parse_iso_datetime(due_value)
        if not due_dt or due_dt > now:
            continue

        alerts.append(
            _make_alert_row(
                title=f"Overdue competency review: {row.get('competency_name') or 'Competency'}",
                category="staff_competency",
                severity="urgent",
                entity_type="employee",
                entity_id=employee_id,
                entity_name=employee_lookup.get(employee_id, employee_id),
                due_date=due_value,
                link_target=f"/portal/employees/{employee_id}?tab=competencies",
                source="competency_records",
            )
        )

    # ------------------------------------------------------------------
    # 9) Overdue appraisals (minimal appraisal evidence rows)
    # ------------------------------------------------------------------
    appraisal_collection = getattr(db, "appraisal_records", None)
    appraisal_rows = []
    if appraisal_collection is not None:
        appraisal_rows = await appraisal_collection.find(
            {"next_due_at": {"$exists": True, "$ne": None}},
            {
                "_id": 0,
                "id": 1,
                "employee_id": 1,
                "next_due_at": 1,
            },
        ).to_list(5000)

    for row in appraisal_rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if not employee_id:
            continue
        due_value = row.get("next_due_at")
        due_dt = _parse_iso_datetime(due_value)
        if not due_dt or due_dt > now:
            continue

        alerts.append(
            _make_alert_row(
                title="Overdue appraisal",
                category="staff_appraisal",
                severity="urgent",
                entity_type="employee",
                entity_id=employee_id,
                entity_name=employee_lookup.get(employee_id, employee_id),
                due_date=due_value,
                link_target=f"/portal/employees/{employee_id}?tab=appraisals",
                source="appraisal_records",
            )
        )

    severity_rank = {"urgent": 0, "safeguarding": 1, "missing": 2, "warning": 3}
    alerts.sort(
        key=lambda row: (
            severity_rank.get(_safe_lower(row.get("severity")), 9),
            row.get("due_date") or row.get("expiry_date") or "",
        )
    )

    limited = alerts[:limit]
    by_severity = {
        "urgent": 0,
        "warning": 0,
        "missing": 0,
        "safeguarding": 0,
    }
    for row in limited:
        sev = _safe_lower(row.get("severity"))
        if sev in by_severity:
            by_severity[sev] += 1

    return {
        "total": len(limited),
        "counts": by_severity,
        "alerts": limited,
        "as_of": now.isoformat(),
    }


# ==============================================================================
# DEBUG READINESS PAYLOAD — QA use; admin-only
# GET /employees/{employee_id}/readiness-debug
# ==============================================================================

@router.get("/employees/{employee_id}/readiness-debug")
async def get_readiness_debug(
    employee_id: str,
    user: dict = Depends(require_admin),
):
    """
    QA debug endpoint: returns every requirement evaluated for this employee,
    the source collection, verification status, and whether it is counted as
    complete.  Used to validate genuine 100% cases.

    Access: admin only.
    """
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    from unified_compliance_engine import get_unified_employee_status

    progress = await get_unified_employee_status(employee_id, db, user_role="admin", include_details=True)

    categories = progress.get("category_details") or {}
    blockers = progress.get("blockers") or []
    blocker_ids = {b.get("id") for b in blockers}

    # Build per-requirement debug rows from each category
    rows = []
    for category_name, cat_data in categories.items():
        for item in cat_data.get("items", []):
            req_id = item.get("id") or item.get("requirement") or ""
            rows.append({
                "requirement_key": req_id,
                "category": category_name,
                "name": item.get("name") or item.get("title") or req_id,
                "counted_as_complete": bool(item.get("completed")),
                "verified": bool(item.get("verified")),
                "status": item.get("status") or ("complete" if item.get("completed") else "incomplete"),
                "has_record": item.get("has_record", None),
                "expiry_date": item.get("expiry_date"),
                "is_blocker": req_id in blocker_ids,
                "blocker_detail": next(
                    (b.get("reason") for b in blockers if b.get("id") == req_id), None
                ),
            })

    # Summary
    overall_pct = progress.get("overall_percentage", 0) or 0
    completed_req = progress.get("completed_requirements", 0) or 0
    total_req = progress.get("total_requirements", 0) or 0
    awaiting = [b for b in blockers if b.get("severity") == "pending"]

    return {
        "employee_id": employee_id,
        "name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "overall_percentage": overall_pct,
            "completed_requirements": completed_req,
            "total_requirements": total_req,
            "blockers_count": len(blockers),
            "awaiting_review_count": len(awaiting),
            "is_100_percent_genuine": overall_pct == 100 and len(blockers) == 0,
        },
        "requirements": rows,
        "blockers": blockers,
    }


# ==================== WORK READINESS DECISION (Gate 2 — formal record) ====================

from pydantic import BaseModel, Field  # noqa: E402  (kept local to this feature)


_VALID_READINESS_OUTCOMES = {"ready", "ready_with_conditions", "not_ready"}


class WorkReadinessDecisionInput(BaseModel):
    outcome: str = Field(..., description="One of: ready, ready_with_conditions, not_ready")
    rationale: str = Field(..., min_length=1, description="Why this decision was made")
    conditions: Optional[list[str]] = Field(
        default=None,
        description="Optional list of conditions attached to a ready_with_conditions outcome",
    )


@router.post("/employees/{employee_id}/work-readiness/approve")
async def approve_work_readiness(
    employee_id: str,
    payload: WorkReadinessDecisionInput,
    user: dict = Depends(require_admin),
):
    """
    Record a formal "fit for work" decision for an employee (CQC accountability).

    - Admin only.
    - Re-runs the canonical readiness check server-side; refuses to write a
      "ready" / "ready_with_conditions" outcome if the employee is not actually
      work-ready per the unified compliance engine.
    - Appends to db.work_readiness_decisions (append-only audit collection).
    - Emits an audit log entry so the timeline stays reconstructible.
    """
    import uuid

    db = get_db()

    if payload.outcome not in _VALID_READINESS_OUTCOMES:
        raise HTTPException(
            status_code=400,
            detail=f"outcome must be one of {sorted(_VALID_READINESS_OUTCOMES)}",
        )

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Canonical readiness check — UCE is the authoritative truth source.
    get_unified_employee_status = get_unified_employee_status_func()
    uce_status = await get_unified_employee_status(
        employee_id, db, user_role="admin", include_details=False
    )
    if uce_status.get("error"):
        raise HTTPException(
            status_code=500,
            detail=f"Readiness check failed: {uce_status.get('error')}",
        )

    is_work_ready = bool(uce_status.get("is_work_ready", False))
    uce_blockers = uce_status.get("blockers", []) or []

    # Refuse to write an approval outcome if the employee is not actually
    # work-ready. "not_ready" is always allowed (it records a negative decision).
    if payload.outcome in ("ready", "ready_with_conditions") and not is_work_ready:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "not_work_ready",
                "message": (
                    "Cannot record a ready outcome: the employee does not pass "
                    "the canonical work-readiness check."
                ),
                "blockers": uce_blockers,
            },
        )

    now = datetime.now(timezone.utc).isoformat()
    decided_by_id = user.get("user_id") or user.get("id")
    decided_by_name = (
        user.get("full_name")
        or user.get("name")
        or user.get("email")
        or decided_by_id
    )

    decision_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "decided_by": decided_by_id,
        "decided_by_name": decided_by_name,
        "decided_at": now,
        "outcome": payload.outcome,
        "rationale": payload.rationale,
        "conditions": payload.conditions or [],
        # Snapshot of the canonical check at decision time (append-only audit).
        "readiness_snapshot": {
            "is_work_ready": is_work_ready,
            "overall_percentage": uce_status.get("overall_percentage"),
            "blockers": uce_blockers,
        },
        "created_at": now,
    }

    await db.work_readiness_decisions.insert_one(decision_doc)

    await log_audit_action(
        decided_by_id,
        "approve_for_work",
        "employee",
        employee_id,
        {
            "outcome": payload.outcome,
            "rationale": payload.rationale,
            "conditions": payload.conditions or [],
            "employee_id": employee_id,
            "is_work_ready_snapshot": is_work_ready,
        },
    )

    # Strip internal fields before returning.
    decision_doc.pop("_id", None)
    return {
        "status": "success",
        "decision": decision_doc,
    }


@router.get("/employees/{employee_id}/work-readiness/decisions")
async def get_work_readiness_decisions(
    employee_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    """
    Return the append-only list of formal work-readiness decisions for an
    employee, newest first. Read-only; does not recompute readiness.
    """
    db = get_db()
    cursor = db.work_readiness_decisions.find(
        {"employee_id": employee_id},
        {"_id": 0},
    ).sort("decided_at", -1)
    decisions = await cursor.to_list(length=100)
    latest = decisions[0] if decisions else None
    return {
        "employee_id": employee_id,
        "latest": latest,
        "history": decisions,
        "count": len(decisions),
    }
