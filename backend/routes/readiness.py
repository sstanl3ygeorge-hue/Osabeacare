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
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query

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
    
    # Get agreement submissions
    agreement_submissions = await db.agreement_submissions.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "acknowledgements": agreement_submissions
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


def get_unified_employee_status_func():
    """Lazy import of canonical unified status calculator."""
    from unified_compliance_engine import get_unified_employee_status
    return get_unified_employee_status


def adapt_unified_status_to_legacy_readiness(unified_status: dict, employee: dict) -> dict:
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
    health_verified = bool(health_item.get("verified", checks.get("staff_health_questionnaire", False)))
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
                "verified": health_verified
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

    adapted_response = adapt_unified_status_to_legacy_readiness(unified_status, employee)

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
    
    # Get compliance file sections
    compliance_file = await get_compliance_file_data(employee_id, employee)
    sections = compliance_file.get("sections", {})
    
    # Evaluate approval readiness
    evaluation = evaluate_recruitment_approval(employee, sections)
    
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
    from server import EXCLUDED_DOC_STATUSES
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
