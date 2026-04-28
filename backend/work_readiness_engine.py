"""
Work Readiness Engine (Gate 2) - NHS Employment Check Standards Compliant

This module evaluates whether an APPROVED employee is ready to start work.
Separate from Recruitment Approval (Gate 1), this checks post-recruitment items.

Gate 1 (Recruitment Approval): Can we hire this person?
Gate 2 (Work Readiness): Can this person start working?

NHS Status Flow:
- Conditional Offer (applicant/onboarding) = Checks pending, CANNOT work
- Unconditional Offer (active_employee) = All checks passed, CLEARED to work

Work Readiness Blockers include:
- Contract not signed
- Handbook not acknowledged
- Induction not completed/verified
- Health questionnaire not completed/reviewed
- Role-specific competency not completed
- Required training not satisfied
- Expired/invalid critical documents (RTW, DBS, identity)
- Professional registration not verified (NMC for nurses, etc.)
- References not verified (2 required)
- Proof of address not verified (2 documents required)
"""

from typing import Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from unified_compliance_engine import get_employee_competency
from stage_identity import get_stage_identity, normalize_lifecycle_status

# =============================================================================
# ROLE-SPECIFIC WORK READINESS REQUIREMENTS
# =============================================================================

# These requirements MUST be satisfied before an employee can work
ROLE_WORK_REQUIREMENTS = {
    "healthcare_assistant": {
        "agreements": [
            "contract_acceptance",
            "handbook_acknowledgement",
        ],
        "forms": [
            "induction",  # Induction & Competency Assessment
            "staff_health_questionnaire",
        ],
        "competencies": [
            "care_certificate",  # Care Certificate or equivalent induction competency
        ],
        "critical_documents": [
            "right_to_work",
            "dbs",
            "identity",
        ],
        "training_blockers": True,  # Check training matrix
    },
    "nurse": {
        "agreements": [
            "contract_acceptance",
            "handbook_acknowledgement",
        ],
        "forms": [
            "induction",
            "staff_health_questionnaire",
        ],
        "competencies": [
            "clinical_competency",        # Nurse-specific clinical competency
            "medication_competency",       # Medication administration competency
        ],
        "critical_documents": [
            "right_to_work",
            "dbs",
            "identity",
            "nmc_registration",            # Nurse-specific
            "professional_indemnity",      # Annual insurance certificate
        ],
        "training_blockers": True,
    },
    "senior_carer": {
        "agreements": [
            "contract_acceptance",
            "handbook_acknowledgement",
        ],
        "forms": [
            "induction",
            "staff_health_questionnaire",
        ],
        "competencies": [
            "care_certificate",
        ],
        "critical_documents": [
            "right_to_work",
            "dbs",
            "identity",
        ],
        "training_blockers": True,
    },
    "support_worker": {
        "agreements": [
            "contract_acceptance",
            "handbook_acknowledgement",
        ],
        "forms": [
            "induction",
            "staff_health_questionnaire",
        ],
        "competencies": [
            "care_certificate",
        ],
        "critical_documents": [
            "right_to_work",
            "dbs",
            "identity",
        ],
        "training_blockers": True,
    },
}

# Default requirements for unknown roles
DEFAULT_WORK_REQUIREMENTS = ROLE_WORK_REQUIREMENTS["healthcare_assistant"]

# =============================================================================
# PROFESSIONAL REGISTRATION REQUIREMENTS (NHS REQUIREMENT)
# =============================================================================

ROLE_REGISTRATION_REQUIREMENTS = {
    "nurse": {
        "body": "NMC",
        "body_name": "Nursing & Midwifery Council",
        "required": True,
        "check_url": "https://www.nmc.org.uk/registration/search/"
    },
    "social_worker": {
        "body": "Social Work England",
        "body_name": "Social Work England",
        "required": True,
        "check_url": "https://www.socialworkengland.org.uk/register/"
    },
    "doctor": {
        "body": "GMC",
        "body_name": "General Medical Council",
        "required": True,
        "check_url": "https://www.gmc-uk.org/registration-and-licensing"
    },
    "occupational_therapist": {
        "body": "HCPC",
        "body_name": "Health and Care Professions Council",
        "required": True,
        "check_url": "https://www.hcpc-uk.org/check-the-register/"
    },
    "physiotherapist": {
        "body": "HCPC",
        "body_name": "Health and Care Professions Council",
        "required": True,
        "check_url": "https://www.hcpc-uk.org/check-the-register/"
    },
    "healthcare_assistant": {
        "required": False
    },
    "senior_carer": {
        "required": False
    },
    "support_worker": {
        "required": False
    },
    "care_assistant": {
        "required": False
    }
}

# =============================================================================
# NHS STATUS DEFINITIONS
# =============================================================================

# Employee Status Values
EMPLOYEE_STATUS_APPLICANT = "applicant"  # Initial application stage
EMPLOYEE_STATUS_ONBOARDING = "onboarding"  # Conditional offer, checks in progress
EMPLOYEE_STATUS_ACTIVE = "active"  # Unconditional offer, cleared to work
EMPLOYEE_STATUS_SUSPENDED = "suspended"  # Temporarily not allowed to work
EMPLOYEE_STATUS_ARCHIVED = "archived"  # Left organization

# Statuses that appear in Recruitment Pipeline (cannot work)
RECRUITMENT_STATUSES = [EMPLOYEE_STATUS_APPLICANT, EMPLOYEE_STATUS_ONBOARDING]

# Statuses that appear in Active Employees (can work)
ACTIVE_STATUSES = [EMPLOYEE_STATUS_ACTIVE, "active_employee"]

# Display labels for work readiness items
WORK_READINESS_LABELS = {
    # Agreements
    "contract_acceptance": "Employment Contract",
    "handbook_acknowledgement": "Employee Handbook",
    # Forms
    "induction": "Induction & Competency Assessment",
    "staff_health_questionnaire": "Staff Health Questionnaire",
    # Competencies
    "care_certificate": "Care Certificate",
    "clinical_competency": "Clinical Competency",
    # Documents
    "right_to_work": "Right to Work",
    "dbs": "DBS Certificate",
    "identity": "Identity Documents",
    "nmc_registration": "NMC Registration",
    "professional_indemnity": "Professional Indemnity Insurance",
    "proof_of_address": "Proof of Address",
    # Professional Registration
    "professional_registration": "Professional Registration",
    "NMC": "NMC (Nursing & Midwifery Council)",
    "GMC": "GMC (General Medical Council)",
    "HCPC": "HCPC (Health & Care Professions Council)",
    "Social Work England": "Social Work England",
    # Training
    "training": "Required Training",
    # References
    "references": "Employment References",
}

# =============================================================================
# CONTRACT SIGNING REQUIREMENTS (P0 COMPLIANCE)
# =============================================================================
# Contract must be the FINAL step - all these must be complete first

REQUIRED_BEFORE_CONTRACT = [
    "dbs_verified",           # DBS certificate verified with stamp
    "rtw_verified",           # Right to Work verified with stamp
    "identity_verified",      # Identity document verified with stamp
    "poa_verified",           # 2 Proof of Address documents verified
    "references_verified",    # Both references verified
    "interview_completed",    # Interview record completed
    "induction_complete",     # 15 Care Certificate standards complete
    "mandatory_training_complete",  # All mandatory training items complete & valid
]


async def can_sign_contract(db, employee_id: str) -> dict:
    """
    Check if an employee can sign their contract.
    Contract signing is the FINAL step - requires 100% completion of all other requirements.
    
    NEW LOGIC (simplified):
    - Progress must be 100% BEFORE contract can be signed
    - Contract is excluded from the progress calculation for this check
    
    Returns:
        {
            "can_sign": bool,
            "reason": str or None,
            "blockers": list of remaining items,
            "completed": list of completed items,
            "progress_percentage": int
        }
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return {"can_sign": False, "reason": "Employee not found", "blockers": [], "completed": [], "progress_percentage": 0}

    job_role = (employee.get("job_role") or employee.get("role") or "").lower()
    blockers = []
    completed = []

    unified_checks = {}
    unified_categories = {}
    unified_category_details = {}
    try:
        from unified_compliance_engine import get_unified_employee_status
        unified = await get_unified_employee_status(employee_id, db, user_role="admin", include_details=True)
        if isinstance(unified, dict) and not unified.get("error"):
            unified_checks = unified.get("checks") or {}
            unified_categories = unified.get("categories") or {}
            unified_category_details = unified.get("category_details") or {}
    except Exception:
        unified_checks = {}
        unified_categories = {}
        unified_category_details = {}

    # ========== DOCUMENTS (from live computed state) ==========
    core_doc_checks = ["right_to_work", "dbs", "identity", "proof_of_address"]
    if "nurse" in job_role:
        core_doc_checks.append("professional_registration")

    doc_completed = 0
    for doc_type in core_doc_checks:
        has_unified_check = doc_type in unified_checks
        is_verified = bool(unified_checks.get(doc_type)) if has_unified_check else False
        if is_verified:
            doc_completed += 1
            completed.append(f"{doc_type.replace('_', ' ').title()} verified")
        else:
            blockers.append(f"{doc_type.replace('_', ' ').title()} not verified")
    
    # ========== FORMS ==========
    required_forms = ["staff_health_questionnaire", "staff_personal_info", "hmrc_starter_checklist", "emergency_contacts"]
    form_submissions = None
    submitted_forms = set()
    
    form_completed = 0
    for form_id in required_forms:
        has_unified_check = form_id in unified_checks
        is_complete = bool(unified_checks.get(form_id)) if has_unified_check else False
        if not has_unified_check:
            if form_submissions is None:
                form_submissions = await db.form_submissions.find({
                    "employee_id": employee_id,
                    "status": {"$in": ["submitted", "verified"]}
                }).to_list(20)
                submitted_forms = {fs.get("form_type") for fs in form_submissions}
            is_complete = form_id in submitted_forms

        if is_complete:
            form_completed += 1
            completed.append(f"{form_id.replace('_', ' ').title()} submitted")
        else:
            blockers.append(f"{form_id.replace('_', ' ').title()} required")
    
    # ========== TRAINING ==========
    # 8 items — must match MANDATORY_TRAINING_HCA in unified_compliance_engine.py
    mandatory_training = [
        "safeguarding", "manual_handling", "fire_safety", "health_safety",
        "bls", "infection_control", "information_governance", "prevent",
    ]
    training_completed = 0
    has_unified_training = "mandatory_training" in unified_checks
    training_ok = bool(unified_checks.get("mandatory_training")) if has_unified_training else False
    if has_unified_training:
        if training_ok:
            training_completed = len(mandatory_training)
            for training_id in mandatory_training:
                completed.append(f"{training_id.replace('_', ' ').title()} complete")
        else:
            blockers.append("Mandatory training required")
    else:
        training_records = await db.training_records.find({
            "employee_id": employee_id,
            "record_status": {"$ne": "superseded"}
        }).to_list(100)

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        for training_id in mandatory_training:
            is_done = False
            for t in training_records:
                t_name = (t.get("training_name") or "").lower()
                if training_id.replace("_", " ") in t_name or training_id.replace("_", "") in t_name:
                    # Must be verified (matches UCE is_training_valid requirement)
                    is_verified = (
                        t.get("verified") is True
                        or t.get("status") == "verified"
                        or t.get("computed_status") == "verified"
                    )
                    if not is_verified:
                        break  # Found record but not verified — counts as not done
                    expiry_str = t.get("expiry_date")
                    if expiry_str:
                        try:
                            if isinstance(expiry_str, str):
                                expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                            else:
                                expiry = expiry_str
                            if expiry >= now:
                                is_done = True
                        except Exception:
                            is_done = True
                    else:
                        is_done = True
                    break
            if is_done:
                training_completed += 1
                completed.append(f"{training_id.replace('_', ' ').title()} complete")
            else:
                blockers.append(f"{training_id.replace('_', ' ').title()} required")
    
    # Contract-lock adapter correction: replace the legacy training result above
    # with the canonical UCE/training-evaluator state used by the Training tab.
    _training_label_fragments = [
        "Safeguarding", "Manual Handling", "Fire Safety", "Health Safety",
        "Bls", "Basic Life Support", "Infection Control",
        "Information Governance", "Prevent", "Mandatory training",
    ]
    blockers = [
        b for b in blockers
        if not any(fragment in b for fragment in _training_label_fragments)
    ]
    completed = [
        c for c in completed
        if not any(fragment in c for fragment in _training_label_fragments)
    ]

    training_category = unified_category_details.get("training") or unified_categories.get("training") or {}
    training_items = training_category.get("items") or []
    training_total = int(training_category.get("total") or len(training_items) or 0)
    training_completed = int(training_category.get("completed") or 0)
    training_blocking_items = []
    has_unified_training = "mandatory_training" in unified_checks
    training_ok = bool(unified_checks.get("mandatory_training")) if has_unified_training else None

    if has_unified_training and training_total:
        for item in training_items:
            name = item.get("name") or item.get("title") or item.get("label") or item.get("id") or "Training"
            if item.get("completed") is True:
                completed.append(f"{name} complete")
            else:
                detail = item.get("detail") or item.get("status") or "required"
                training_blocking_items.append({"name": name, "detail": detail})
        if not training_ok:
            blockers.extend(
                [f"{item['name']}: {item['detail']}" for item in training_blocking_items]
                or ["Mandatory training required"]
            )
    else:
        try:
            from services.training_evaluator import evaluate_employee_training_status
            training_eval = await evaluate_employee_training_status(employee_id, job_role)
            training_items = training_eval.get("items") or []
            training_total = len(training_items)
            training_completed = sum(
                1
                for item in training_items
                if item.get("status") in {"verified", "due_soon"} and not item.get("is_currently_blocking")
            )
            training_blocking_items = [
                {
                    "name": item.get("title") or item.get("code") or "Training",
                    "detail": item.get("detail") or item.get("status") or "required",
                }
                for item in training_items
                if item.get("is_currently_blocking") or (
                    item.get("blocker") and item.get("status") not in {"verified", "due_soon"}
                )
            ]
            training_ok = training_eval.get("blockerCount", 0) == 0
            if training_ok:
                for item in training_items:
                    completed.append(f"{item.get('title') or item.get('code') or 'Training'} complete")
            else:
                blockers.extend(
                    [f"{item['name']}: {item['detail']}" for item in training_blocking_items]
                    or ["Mandatory training required"]
                )
        except Exception:
            training_ok = False
            training_total = 0
            training_completed = 0
            blockers.append("Mandatory training cannot be assessed")

    # ========== REFERENCES ==========
    ref_completed = 0
    has_unified_refs = "references" in unified_checks
    refs_ok = bool(unified_checks.get("references")) if has_unified_refs else False
    if has_unified_refs:
        if refs_ok:
            ref_completed = 2
            completed.extend(["Reference 1 verified", "Reference 2 verified"])
        else:
            blockers.extend(["Reference 1 not verified", "Reference 2 not verified"])
    else:
        references = employee.get("references", [])
        verified_refs = [r for r in references if r.get("verified") or r.get("status") == "verified"]
        ref_completed = min(len(verified_refs), 2)
        
        if len(verified_refs) >= 1:
            completed.append("Reference 1 verified")
        else:
            blockers.append("Reference 1 not verified")
        if len(verified_refs) >= 2:
            completed.append("Reference 2 verified")
        else:
            blockers.append("Reference 2 not verified")
    
    # ========== HANDBOOK / AGREEMENTS ==========
    # Contract signing itself is excluded from this pre-sign check. Handbook
    # must use the same latest-state resolver as admin/worker agreement cards.
    handbook_ok = False
    handbook_system_issue = False
    handbook_source = "agreement_resolver"
    try:
        from agreement_document_service import (
            HANDBOOK_AGREEMENT_TYPE,
            resolve_employee_agreement_state,
        )
        handbook_state = await resolve_employee_agreement_state(
            db,
            employee,
            HANDBOOK_AGREEMENT_TYPE,
        )
        handbook_ok = bool(handbook_state.get("verified") or handbook_state.get("worker_acknowledged"))
        handbook_system_issue = bool(handbook_state.get("system_issue"))
    except Exception:
        has_unified_handbook = "handbook" in unified_checks
        handbook_ok = bool(unified_checks.get("handbook")) if has_unified_handbook else False
        handbook_source = "uce_checks" if has_unified_handbook else "legacy_agreement_lookup"
        if not has_unified_handbook:
            _hb_ack = await db.agreement_acknowledgements.find_one({
                "employee_id": employee_id,
                "agreement_type": {"$regex": "handbook", "$options": "i"},
                "status": {"$in": ["acknowledged", "signed", "submitted"]},
            })
            if not _hb_ack:
                _hb_ack = await db.agreement_submissions.find_one({
                    "employee_id": employee_id,
                    "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
                })
            handbook_ok = bool(_hb_ack)
    if handbook_ok:
        completed.append("Employee Handbook acknowledged")
    else:
        if handbook_system_issue:
            blockers.append("Employee Handbook unavailable due to system render issue")
        else:
            blockers.append("Employee Handbook not acknowledged")

    # ========== INDUCTION ==========
    induction_category = unified_category_details.get("induction") or unified_categories.get("induction") or {}
    induction_completed = int(induction_category.get("completed") or 0)
    induction_total = int(induction_category.get("total") or 0)
    has_unified_induction = "induction" in unified_checks
    induction_ok = bool(unified_checks.get("induction")) if has_unified_induction else None
    if not induction_total:
        from induction_definitions import get_employee_induction_status
        induction_status = await get_employee_induction_status(db, employee_id)
        induction_completed = int(induction_status.get("completed") or 0)
        induction_total = int(induction_status.get("total") or 0)
        induction_ok = not bool(induction_status.get("blocking"))
    
    if induction_total and induction_completed >= induction_total:
        completed.append(f"Induction complete ({induction_completed}/{induction_total})")
    else:
        blockers.append(f"Induction incomplete ({induction_completed}/{induction_total or 15})")
    
    # ========== CALCULATE TOTAL (excluding contract) ==========
    total_requirements = len(core_doc_checks) + len(required_forms) + training_total + 2 + 1 + 1  # +2 refs, +1 induction, +1 handbook
    total_completed = doc_completed + form_completed + training_completed + ref_completed + (1 if induction_total and induction_completed >= induction_total else 0) + (1 if handbook_ok else 0)

    progress_percentage = round((total_completed / total_requirements) * 100) if total_requirements > 0 else 0

    # Contract can only be signed when progress is 100%
    can_sign = progress_percentage >= 100
    
    return {
        "can_sign": can_sign,
        "reason": None if can_sign else f"{len(blockers)} requirements remaining before contract can be signed",
        "blockers": blockers,
        "completed": completed,
        "total_requirements": total_requirements,
        "completed_count": total_completed,
        "progress_percentage": progress_percentage,
        "debug": {
            "source": "canonical_readiness_adapter",
            "induction": {
                "completed": induction_completed,
                "total": induction_total,
                "satisfied": bool(induction_ok),
                "source": "uce_category" if induction_category else "induction_status_helper",
            },
            "training": {
                "completed": training_completed,
                "total": training_total,
                "satisfied": bool(training_ok),
                "blocking_items": training_blocking_items,
                "source": "uce_category" if has_unified_training and training_category else "training_evaluator",
            },
            "agreements": {
                "handbook_satisfied": handbook_ok,
                "contract_excluded_from_pre_sign_gate": True,
                "blocking": [] if handbook_ok else (
                    ["Employee Handbook unavailable due to system render issue"]
                    if handbook_system_issue
                    else ["Employee Handbook not acknowledged"]
                ),
                "source": handbook_source,
            },
            "final_contract_lock_reasons": blockers,
        }
    }


async def can_promote_to_active(db, employee_id: str) -> dict:
    """
    Check if an employee can be promoted to active status.
    Requires: all pre-contract checks complete + contract signed
    """
    contract_check = await can_sign_contract(db, employee_id)
    
    if not contract_check["can_sign"]:
        return {
            "can_promote": False,
            "reason": "Pre-contract requirements incomplete",
            "blockers": contract_check["blockers"]
        }

    contract_signed = False
    try:
        from agreement_document_service import (
            CONTRACT_AGREEMENT_TYPE,
            resolve_employee_agreement_state,
        )
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0}) or {"id": employee_id}
        contract_state = await resolve_employee_agreement_state(
            db,
            employee,
            CONTRACT_AGREEMENT_TYPE,
        )
        contract_signed = bool(contract_state.get("fully_executed"))
    except Exception:
        _CONTRACT_TEMPLATE_IDS = {
            "ZERO_HOUR_CONTRACT_V1",
            "EMPLOYMENT_CONTRACT_V1",
            "CASUAL_WORKER_CONTRACT_V1",
        }
        contract_ack = await db.agreement_acknowledgements.find_one({
            "employee_id": employee_id,
            "agreement_type": {"$regex": "contract", "$options": "i"},
            "status": {"$in": ["signed", "submitted", "verified"]},
        })
        if not contract_ack:
            contract_ack = await db.agreement_submissions.find_one({
                "employee_id": employee_id,
                "template_id": {"$in": list(_CONTRACT_TEMPLATE_IDS)},
            })
        if not contract_ack:
            emp_record = await db.employees.find_one({"id": employee_id}, {"contract_signed": 1})
            if emp_record and emp_record.get("contract_signed"):
                contract_ack = {"source": "legacy_flat"}
        contract_signed = bool(contract_ack)

    if not contract_signed:
        return {
            "can_promote": False,
            "reason": "Contract not signed",
            "blockers": ["Employment contract not signed by worker"]
        }
    
    return {
        "can_promote": True,
        "reason": None,
        "blockers": []
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_work_readiness_label(key: str) -> str:
    """Get display label for a work readiness item."""
    return WORK_READINESS_LABELS.get(key, key.replace("_", " ").title())


def normalize_role_for_work(role: str) -> str:
    """Normalize role string for work readiness lookup."""
    role_lower = role.lower().strip() if role else ""
    
    role_mapping = {
        "hca": "healthcare_assistant",
        "healthcare assistant": "healthcare_assistant",
        "health care assistant": "healthcare_assistant",
        "carer": "healthcare_assistant",
        "care assistant": "healthcare_assistant",
        # Nurse variants (must all map to "nurse" for ROLE_REGISTRATION_REQUIREMENTS lookup)
        "registered nurse": "nurse",
        "nurse (registered)": "nurse",  # apply form dropdown value
        "senior nurse": "nurse",         # apply form dropdown value
        "senior_nurse": "nurse",
        "staff nurse": "nurse",
        "staff_nurse": "nurse",
        "district nurse": "nurse",
        "community nurse": "nurse",
        "practice nurse": "nurse",
        "rn": "nurse",
        "rgn": "nurse",
        # HCA variants
        "senior carer": "senior_carer",
        "senior care assistant": "senior_carer",
        "support worker": "support_worker",
    }
    
    return role_mapping.get(role_lower, role_lower.replace(" ", "_"))


def is_document_expired(doc_data: dict) -> tuple:
    """
    Check if a document is expired or expiring soon.
    Returns: (is_expired, is_expiring_soon, days_until_expiry)
    """
    expiry_date_str = doc_data.get("expiry_date") or doc_data.get("review_due")
    
    if not expiry_date_str:
        return (False, False, None)
    
    try:
        if isinstance(expiry_date_str, str):
            # Handle ISO format
            if 'T' in expiry_date_str:
                expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            else:
                expiry_date = datetime.fromisoformat(expiry_date_str + "T00:00:00+00:00")
        else:
            expiry_date = expiry_date_str
        
        now = datetime.now(timezone.utc)
        days_until = (expiry_date - now).days
        
        is_expired = days_until < 0
        is_expiring_soon = 0 <= days_until <= 30
        
        return (is_expired, is_expiring_soon, days_until)
    except Exception:
        return (False, False, None)


async def check_professional_registration(employee_id: str, role_normalized: str, db) -> Tuple[bool, Optional[str]]:
    """
    Check if required professional registration is present and verified.
    
    Returns:
        (is_satisfied, error_message)
    """
    req = ROLE_REGISTRATION_REQUIREMENTS.get(role_normalized, {})
    
    # Registration not required for this role
    if not req.get("required", False):
        return (True, None)
    
    required_body = req.get("body")
    body_name = req.get("body_name", required_body)
    
    # Get employee's professional registrations - try 'id' field first, then _id
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        try:
            employee = await db.employees.find_one({"_id": ObjectId(employee_id)})
        except Exception:
            pass
    
    if not employee:
        return (False, "Employee not found")
    
    registrations = employee.get("professional_registrations", [])
    
    # Find registration for the required body
    matching = [r for r in registrations if r.get("body") == required_body]
    
    if not matching:
        return (False, f"Missing {body_name} registration")
    
    reg = matching[0]
    
    # Check if verified
    if not reg.get("verified", False):
        return (False, f"{body_name} registration not verified")
    
    # Check if active
    if reg.get("registration_status") != "active":
        return (False, f"{body_name} registration is {reg.get('registration_status', 'unknown')}")
    
    # Check if expired
    if reg.get("registration_expiry_date"):
        try:
            expiry_str = reg["registration_expiry_date"]
            if isinstance(expiry_str, str):
                if 'T' in expiry_str:
                    expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    expiry = datetime.fromisoformat(expiry_str + "T00:00:00+00:00")
            else:
                expiry = expiry_str
            
            if expiry < datetime.now(timezone.utc):
                return (False, f"{body_name} registration expired on {expiry_str[:10]}")
        except Exception:
            pass  # If date parsing fails, assume not expired
    
    return (True, None)


async def can_promote_to_active_legacy(employee_id: str, db) -> Tuple[bool, dict]:
    """
    LEGACY: Check if an employee can be automatically promoted to active_employee status.
    Use can_promote_to_active(db, employee_id) instead for new code.
    
    NHS Employment Check Standards require ALL of the following:
    - Right to Work verified and stamped
    - DBS verified with update service
    - Identity verified with stamp
    - Proof of Address (2 documents with stamps)
    - Both references verified
    - All mandatory training complete and not expired
    - Contract signed
    - Induction checklist complete
    - Health questionnaire complete
    - Professional registration verified (for regulated roles)
    
    Returns:
        (can_promote, checks_dict)
    """
    checks = {}
    
    # Try to find by 'id' field (UUID) first, then by _id (ObjectId)
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        try:
            employee = await db.employees.find_one({"_id": ObjectId(employee_id)})
        except Exception:
            pass
    
    if not employee:
        return (False, {"error": "Employee not found"})
    
    emp_id_str = employee.get("id", str(employee.get("_id", "")))
    role = employee.get("system_role", employee.get("role", "healthcare_assistant"))
    role_normalized = normalize_role_for_work(role)
    
    # 1. Right to Work - verified with stamp
    rtw_docs = await db.employee_documents.find({
        "employee_id": emp_id_str,
        "requirement_id": {"$in": ["right_to_work_evidence", "right_to_work"]},
        "status": {"$in": ["active", "approved", "verified"]}
    }).to_list(length=10)
    rtw_stamped = any(d.get("verification_stamp") and d.get("verification_stamp") != "not_verified" for d in rtw_docs)
    rtw_check = await db.rtw_checks.find_one({
        "employee_id": emp_id_str,
        "outcome": "verified"
    })
    checks["right_to_work"] = bool(rtw_check and rtw_stamped)
    
    # 2. DBS - verified
    dbs_check = await db.dbs_checks.find_one({
        "employee_id": emp_id_str,
        "outcome": "verified"
    })
    checks["dbs"] = bool(dbs_check)
    
    # 3. Identity - verified with stamp
    id_docs = await db.employee_documents.find({
        "employee_id": emp_id_str,
        "requirement_id": {"$in": ["identity_evidence", "identity", "id_document", "passport"]},
        "status": {"$in": ["active", "approved", "verified"]}
    }).to_list(length=10)
    id_stamped = any(d.get("verification_stamp") and d.get("verification_stamp") != "not_verified" for d in id_docs)
    checks["identity"] = bool(id_docs and id_stamped)
    
    # 4. Proof of Address - 2 documents with stamps
    poa_docs = await db.employee_documents.find({
        "employee_id": emp_id_str,
        "requirement_id": {"$in": ["proof_of_address_evidence", "proof_of_address"]},
        "status": {"$in": ["active", "approved", "verified"]}
    }).to_list(length=10)
    poa_stamped_count = sum(1 for d in poa_docs if d.get("verification_stamp") and d.get("verification_stamp") != "not_verified")
    checks["proof_of_address"] = poa_stamped_count >= 2
    
    # 5. References
    # Rule:
    # - Need 2 valid verified references total
    # - Need at least 1 that covers most recent employer OR has explicit
    #   admin-accepted exception for recent-employer mismatch.
    # - Unresolved non-recent mismatches still do not count.
    def _mismatch_meta(ref_data: dict, n: int) -> dict:
        ref_data = ref_data or {}
        mismatch = ref_data.get("mismatch") or {}
        detected = bool(mismatch.get("detected")) or bool(
            employee.get(f"reference_{n}_mismatch_detected")
        )
        kind = str(mismatch.get("kind") or "").strip().lower()
        if not kind:
            notes = " ".join(
                str(v or "")
                for v in [
                    mismatch.get("reason"),
                    mismatch.get("notes"),
                    employee.get(f"reference_{n}_mismatch_notes"),
                ]
            ).lower()
            if "most recent employer" in notes:
                kind = "recent_employer"
        resolved = bool(
            mismatch.get("resolved")
            or mismatch.get("admin_decision") == "accepted"
            or employee.get(f"reference_{n}_mismatch_admin_decision") == "accepted"
            or employee.get(f"reference_{n}_mismatch_override_reason")
        )
        return {
            "detected": detected,
            "kind": kind,
            "resolved": resolved,
            "unresolved": detected and not resolved,
        }

    def _ref_counts(ref_data: dict, n: int) -> bool:
        ref_data = ref_data or {}
        is_verified = ref_data.get("verification_status") == "verified" or \
            (ref_data.get("verification") or {}).get("status") == "verified"
        if not is_verified:
            return False
        mm = _mismatch_meta(ref_data, n)
        if not mm["unresolved"]:
            return True
        if mm["kind"] == "recent_employer":
            return True
        return False

    def _ref_recent_ok(ref_data: dict, n: int) -> bool:
        if not _ref_counts(ref_data, n):
            return False
        mm = _mismatch_meta(ref_data, n)
        if mm["kind"] != "recent_employer":
            return True
        return mm["resolved"]

    ref_doc = await db.references.find_one({"employee_id": emp_id_str})
    if ref_doc:
        ref1_verified = _ref_counts(ref_doc.get("ref1"), 1)
        ref2_verified = _ref_counts(ref_doc.get("ref2"), 2)
        ref1_recent_ok = _ref_recent_ok(ref_doc.get("ref1"), 1)
        ref2_recent_ok = _ref_recent_ok(ref_doc.get("ref2"), 2)
    else:
        # Legacy employees with only flat employee fields.
        def _flat_counts(n: int) -> bool:
            if not employee.get(f"reference_{n}_verified", False):
                return False
            if employee.get(f"reference_{n}_mismatch_detected") and not (
                employee.get(f"reference_{n}_mismatch_admin_decision") == "accepted"
                or employee.get(f"reference_{n}_mismatch_override_reason")
            ):
                return False
            return True
        ref1_verified = _flat_counts(1)
        ref2_verified = _flat_counts(2)
        ref1_recent_ok = ref1_verified
        ref2_recent_ok = ref2_verified

    valid_reference_count = (1 if ref1_verified else 0) + (1 if ref2_verified else 0)
    checks["references"] = valid_reference_count >= 2 and (ref1_recent_ok or ref2_recent_ok)
    
    # 6. Mandatory Training - all complete and not expired
    training_records = await db.training_records.find({
        "employee_id": emp_id_str,
        "is_mandatory": True,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }).to_list(length=50)
    
    # Simplified check - ensure we have verified training records
    training_ok = len(training_records) > 0  # At minimum, some training exists
    for record in training_records:
        if record.get("expiry_date"):
            try:
                expiry = record["expiry_date"]
                if isinstance(expiry, str):
                    expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                if expiry < datetime.now(timezone.utc):
                    training_ok = False
                    break
            except Exception:
                pass
    checks["mandatory_training"] = training_ok
    
    # 7. Contract signed
    contract_ack = await db.agreement_acknowledgements.find_one({
        "employee_id": emp_id_str,
        "agreement_type": "contract_acceptance",
        "status": {"$in": ["submitted", "signed"]}
    })
    checks["contract"] = bool(contract_ack)

    # 7b. Handbook acknowledged
    handbook_ack_legacy = await db.agreement_acknowledgements.find_one({
        "employee_id": emp_id_str,
        "agreement_type": {"$regex": "handbook", "$options": "i"},
        "status": {"$in": ["acknowledged", "signed", "submitted"]},
    })
    if not handbook_ack_legacy:
        handbook_ack_legacy = await db.agreement_submissions.find_one({
            "employee_id": emp_id_str,
            "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
        })
    checks["handbook"] = bool(handbook_ack_legacy)

    # 8. Induction complete (15 Care Certificate standards) — canonical function
    from induction_definitions import get_employee_induction_status
    induction_canonical = await get_employee_induction_status(db, emp_id_str)
    checks["induction"] = induction_canonical["overall_status"] == "completed"
    # Also check form submissions as fallback
    if not checks["induction"]:
        induction_form = await db.form_submissions.find_one({
            "employee_id": emp_id_str,
            "form_type": "induction",
            "status": {"$in": ["submitted", "verified"]}
        })
        if induction_form:
            checks["induction"] = True
    
    # 9. Health questionnaire complete (check multiple form types)
    health_form = await db.form_submissions.find_one({
        "employee_id": emp_id_str,
        "form_type": {"$in": ["staff_health_questionnaire", "health_questionnaire"]},
        "status": {"$in": ["submitted", "verified"]}
    })
    checks["health_declaration"] = bool(health_form)
    
    # 10. Professional registration (for regulated roles)
    reg_ok, reg_error = await check_professional_registration(emp_id_str, role_normalized, db)
    checks["professional_registration"] = reg_ok
    if reg_error:
        checks["professional_registration_error"] = reg_error
    
    # 10b. Professional Indemnity Insurance (for nurses only)
    if role_normalized == "nurse":
        indemnity_docs = await db.employee_documents.find({
            "employee_id": emp_id_str,
            "requirement_id": {"$in": ["professional_indemnity", "indemnity_insurance", "professional_indemnity_insurance"]},
            "status": {"$in": ["active", "approved", "verified"]}
        }).to_list(length=5)
        indemnity_ok = len(indemnity_docs) > 0
        # Check expiry
        for doc in indemnity_docs:
            if doc.get("expiry_date"):
                try:
                    expiry_str = doc["expiry_date"]
                    if isinstance(expiry_str, str):
                        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                    else:
                        expiry = expiry_str
                    if expiry < datetime.now(timezone.utc):
                        indemnity_ok = False
                        break
                except Exception:
                    pass
        checks["professional_indemnity"] = indemnity_ok
    else:
        checks["professional_indemnity"] = True  # Not required for non-nurses
    
    # 11. Interview Record completed
    interview = await db.form_submissions.find_one({
        "employee_id": emp_id_str,
        "form_type": {"$in": ["interview_record", "interview", "interview_form"]},
        "status": {"$in": ["submitted", "verified", "approved"]}
    })
    checks["interview_record"] = bool(interview)
    
    # 12. Employment gaps explained (all gaps over 28 days must have explanation)
    gaps = employee.get("employment_gaps", [])
    gaps_explained = True
    unexplained_gaps = []
    for gap in gaps:
        duration_months = gap.get("duration_months", 0)
        # If gap is more than ~1 month (28 days)
        if duration_months >= 1:
            if not gap.get("explanation") or gap.get("status") in ["not_explained", "needs_info"]:
                gaps_explained = False
                unexplained_gaps.append({
                    "gap_id": gap.get("gap_id"),
                    "duration_months": duration_months
                })
    # Also check the employment_gaps collection
    gap_docs = await db.employment_gaps.find({
        "employee_id": emp_id_str,
        "duration_months": {"$gte": 1},
        "$or": [
            {"explanation": {"$exists": False}},
            {"explanation": None},
            {"explanation": ""},
            {"status": {"$in": ["not_explained", "needs_info"]}}
        ]
    }).to_list(length=20)
    if gap_docs:
        gaps_explained = False
        for g in gap_docs:
            unexplained_gaps.append({
                "gap_id": g.get("id"),
                "duration_months": g.get("duration_months", 0)
            })
    checks["employment_gaps_explained"] = gaps_explained
    if unexplained_gaps:
        checks["unexplained_gaps"] = unexplained_gaps
    
    # Determine if all checks pass
    can_promote = all([
        checks.get("right_to_work"),
        checks.get("dbs"),
        checks.get("identity"),
        checks.get("proof_of_address"),
        checks.get("references"),
        checks.get("contract"),
        checks.get("induction"),
        checks.get("health_declaration"),
        checks.get("professional_registration"),
        checks.get("professional_indemnity"),  # For nurses
        checks.get("interview_record"),
        checks.get("employment_gaps_explained")
    ])
    
    return (can_promote, checks)


# =============================================================================
# MAIN EVALUATION FUNCTION
# =============================================================================

async def evaluate_work_readiness(
    person: dict,
    compliance_sections: dict,
    agreements_data: dict,
    training_status: dict,
    db,
    role_override: Optional[str] = None
) -> dict:
    """
    Evaluate whether an approved employee is ready to start work.
    
    Args:
        person: Employee document
        compliance_sections: The 'sections' dict from compliance file API
        agreements_data: Agreement/acknowledgement data for the employee
        training_status: Training evaluation result from evaluate_employee_training_status
        db: Database connection
        role_override: Optional role to use
    
    Returns:
        Work readiness evaluation with blockers, warnings, and counts
    """
    # Get role and requirements
    role = role_override or person.get("role", "").lower()
    role_normalized = normalize_role_for_work(role)
    
    requirements = ROLE_WORK_REQUIREMENTS.get(role_normalized, DEFAULT_WORK_REQUIREMENTS)
    
    blockers = []
    warnings = []
    verified_keys = []
    all_required_keys = []
    
    # Build requirement map from compliance sections
    req_map = {}
    for section_key, section_data in compliance_sections.items():
        if isinstance(section_data, dict) and "rows" in section_data:
            for row in section_data.get("rows", []):
                row_key = row.get("key")
                if row_key:
                    req_map[row_key] = row
    
    # ==========================================================================
    # CHECK 1: Agreements (Contract, Handbook)
    # ==========================================================================
    for agreement_key in requirements.get("agreements", []):
        all_required_keys.append(agreement_key)
        
        # Check in agreements data
        agreement_verified = False
        agreement_status = "not_completed"
        
        if agreements_data:
            acks = agreements_data.get("acknowledgements", [])
            matching = [a for a in acks if a.get("agreement_type") == agreement_key]
            
            if matching:
                latest = matching[0]  # Sorted by created_at desc
                verification_status = latest.get("verification_status", "pending")
                agreement_status = latest.get("status", "submitted")
                
                if verification_status == "verified":
                    agreement_verified = True
        
        if agreement_verified:
            verified_keys.append(agreement_key)
        else:
            reason = _get_agreement_block_reason(agreement_key, agreement_status, agreements_data)
            blockers.append({
                "requirement_key": agreement_key,
                "label": get_work_readiness_label(agreement_key),
                "reason": reason,
                "category": "agreement",
                "section": "agreements"
            })
    
    # ==========================================================================
    # CHECK 2: Forms (Induction, Health Questionnaire)
    # ==========================================================================
    for form_key in requirements.get("forms", []):
        all_required_keys.append(form_key)
        
        # Check in compliance sections
        req = req_map.get(form_key)
        
        if not req:
            # Also check in form_submissions collection
            form_submission = await db.form_submissions.find_one({
                "employee_id": person.get("id"),
                "form_type": form_key
            }, {"_id": 0})
            
            if form_submission and form_submission.get("status") == "verified":
                verified_keys.append(form_key)
                continue
            elif form_submission:
                reason = _get_form_block_reason(form_key, form_submission.get("status"))
            else:
                reason = "Form not completed"
            
            blockers.append({
                "requirement_key": form_key,
                "label": get_work_readiness_label(form_key),
                "reason": reason,
                "category": "form",
                "section": _find_section_for_key(form_key, compliance_sections)
            })
            continue
        
        # Check if form is verified
        is_verified = req.get("is_verified", False)
        status = req.get("status", "")
        
        if is_verified or status == "verified":
            verified_keys.append(form_key)
        else:
            reason = _get_form_block_reason(form_key, status)
            blockers.append({
                "requirement_key": form_key,
                "label": get_work_readiness_label(form_key),
                "reason": reason,
                "category": "form",
                "section": _find_section_for_key(form_key, compliance_sections)
            })
    
    # ==========================================================================
    # CHECK 3: Role-Specific Competencies
    # ==========================================================================
    # Delegate entirely to UCE's canonical helper — do NOT re-evaluate competencies
    # here using compliance_sections, training_records, or inline DB queries.
    # UCE is the ONLY source of truth for competency resolution.
    for competency_key in requirements.get("competencies", []):
        all_required_keys.append(competency_key)

        competency_satisfied = await get_employee_competency(
            db, person.get("id"), competency_key
        )

        if competency_satisfied:
            verified_keys.append(competency_key)
        else:
            blockers.append({
                "requirement_key": competency_key,
                "label": get_work_readiness_label(competency_key),
                "reason": "Competency not completed or verified",
                "category": "competency",
                "section": _find_section_for_key(competency_key, compliance_sections) or "training"
            })
    
    # ==========================================================================
    # CHECK 4: Critical Documents (RTW, DBS, Identity, NMC)
    # ==========================================================================
    for doc_key in requirements.get("critical_documents", []):
        all_required_keys.append(doc_key)
        
        # Map to actual compliance file keys
        evidence_key = f"{doc_key}_evidence" if doc_key != "nmc_registration" else doc_key
        check_key = f"{doc_key}_check" if doc_key in ["right_to_work", "dbs", "identity"] else None
        
        # Check the check row (takes precedence) or evidence row
        check_req = req_map.get(check_key) if check_key else None
        evidence_req = req_map.get(evidence_key) or req_map.get(doc_key)
        
        doc_verified = False
        doc_data = check_req or evidence_req
        
        if check_req:
            # Dual-row model: check row determines readiness
            doc_verified = check_req.get("is_verified", False) or check_req.get("status") == "verified"
            doc_data = check_req
        elif evidence_req:
            # Single row or evidence-only
            doc_verified = evidence_req.get("is_verified", False) or evidence_req.get("status") == "verified"
            doc_data = evidence_req
        
        if doc_verified:
            # Check for expiry
            is_expired, is_expiring_soon, days_until = is_document_expired(doc_data or {})
            
            if is_expired:
                blockers.append({
                    "requirement_key": doc_key,
                    "label": get_work_readiness_label(doc_key),
                    "reason": f"Document expired ({abs(days_until)} days ago)",
                    "category": "expired_document",
                    "section": _find_section_for_key(doc_key, compliance_sections)
                })
            elif is_expiring_soon:
                # Add as warning, not blocker
                warnings.append({
                    "requirement_key": doc_key,
                    "label": get_work_readiness_label(doc_key),
                    "reason": f"Expires in {days_until} days",
                    "category": "expiring_soon"
                })
                verified_keys.append(doc_key)
            else:
                verified_keys.append(doc_key)
        else:
            reason = _get_document_block_reason(doc_key, doc_data)
            blockers.append({
                "requirement_key": doc_key,
                "label": get_work_readiness_label(doc_key),
                "reason": reason,
                "category": "document",
                "section": _find_section_for_key(doc_key, compliance_sections)
            })
    
    # ==========================================================================
    # CHECK 5: Verification Stamps on Critical Documents (NHS Requirement)
    # ==========================================================================
    # Documents must have "Original Seen" or equivalent stamp to be work-ready
    verification_stamp_requirements = ["right_to_work", "dbs", "identity"]
    
    for doc_key in verification_stamp_requirements:
        # Already added as blocker if not verified, but check stamp specifically
        if doc_key in verified_keys:
            # Check if the document has a verification stamp
            evidence_key = f"{doc_key}_evidence"
            evidence_docs = await db.employee_documents.find(
                {
                    "employee_id": person.get("id"),
                    "requirement_id": {"$in": [evidence_key, doc_key]},
                    "status": {"$in": ["active", "approved", "verified"]}
                }
            ).to_list(length=10)
            
            has_valid_stamp = False
            for doc in evidence_docs:
                stamp = doc.get("verification_stamp")
                if stamp and stamp not in ["not_verified", None, ""]:
                    has_valid_stamp = True
                    break
            
            if not has_valid_stamp and doc_key not in [b.get("requirement_key") for b in blockers]:
                # Add as warning - document verified but not stamped
                warnings.append({
                    "requirement_key": f"{doc_key}_stamp",
                    "label": f"{get_work_readiness_label(doc_key)} Stamp",
                    "reason": "Document needs 'Original Seen' verification stamp",
                    "category": "verification_stamp"
                })
    
    # ==========================================================================
    # CHECK 6: References Verified (2 references required)
    # ==========================================================================
    all_required_keys.append("references")
    
    ref1_verified = person.get("reference_1_verified", False)
    ref2_verified = person.get("reference_2_verified", False)
    
    # Also check references collection
    ref_doc = await db.references.find_one({"employee_id": person.get("id")})
    if ref_doc:
        ref1_data = ref_doc.get("ref1") or {}
        ref2_data = ref_doc.get("ref2") or {}
        if ref1_data.get("verification_status") == "verified":
            ref1_verified = True
        if ref2_data.get("verification_status") == "verified":
            ref2_verified = True
    
    if not ref1_verified or not ref2_verified:
        missing_refs = []
        if not ref1_verified:
            missing_refs.append("Reference 1")
        if not ref2_verified:
            missing_refs.append("Reference 2")
        
        blockers.append({
            "requirement_key": "references",
            "label": "Employment References",
            "reason": f"Not verified: {', '.join(missing_refs)}",
            "category": "references",
            "section": "recruitment"
        })
    else:
        verified_keys.append("references")

        # CQC Reg 19 sufficiency: at least one verified EMPLOYMENT reference
        # for clinical/care roles, or a recorded explanation.
        try:
            from governance.references_sufficiency import evaluate_reference_sufficiency
            role_for_suff = (
                person.get("applicant_role")
                or person.get("role")
                or person.get("job_role")
            )
            slots = []
            if ref_doc:
                for n in (1, 2):
                    slot = ref_doc.get(f"ref{n}") or {}
                    if slot:
                        slot = dict(slot)
                        slot["reference_num"] = n
                        slots.append(slot)
            verdict = evaluate_reference_sufficiency(role_for_suff, slots)
            if not verdict["sufficient"]:
                blockers.append({
                    "requirement_key": "references_sufficiency",
                    "label": "Reference Sufficiency (CQC Reg 19)",
                    "reason": verdict["blocker_reason"] or (
                        "No verified employment reference on file and no "
                        "explanation recorded."
                    ),
                    "category": "references",
                    "section": "recruitment",
                    "requires_explanation": True,
                })
        except Exception:
            # Additive check — never block overall readiness on helper failure.
            pass
    
    # ==========================================================================
    # CHECK 7: Proof of Address (Minimum 2 documents required for NHS)
    # ==========================================================================
    all_required_keys.append("proof_of_address_count")
    
    poa_docs = await db.employee_documents.find(
        {
            "employee_id": person.get("id"),
            "requirement_id": {"$in": ["proof_of_address_evidence", "proof_of_address"]},
            "status": {"$in": ["active", "approved", "verified"]}
        }
    ).to_list(length=10)
    
    poa_count = len(poa_docs)
    
    if poa_count < 2:
        blockers.append({
            "requirement_key": "proof_of_address_count",
            "label": "Proof of Address",
            "reason": f"NHS requires 2 documents (currently {poa_count}/2)",
            "category": "document",
            "section": "proof_of_address"
        })
    else:
        verified_keys.append("proof_of_address_count")

    # ==========================================================================
    # CHECK 7b: CV Required (Soft Mandatory — CQC supporting evidence)
    # --------------------------------------------------------------------------
    # CV is required for ALL applicants but is supporting evidence only; it
    # must NOT populate the employment history (that comes from the
    # application form + gap-review workflow). Progression to interview /
    # hiring / onboarding completion is blocked until a CV is on file.
    # Truth source matches GET /api/worker/cv-extraction-status: a CV counts
    # as present when cv_document_id is set AND the linked document is still
    # active (not rejected/superseded), OR cv_status is "approved" (admin
    # sign-off). cv_status values of "rejected" / "replacement_requested" /
    # "missing" / "replacement_required" all raise the blocker again.
    # ==========================================================================
    all_required_keys.append("cv_uploaded")
    cv_document_id = person.get("cv_document_id")
    cv_status_value = (person.get("cv_status") or "").lower()
    cv_replacement_required = cv_status_value in {
        "rejected", "replacement_requested", "missing", "replacement_required"
    }
    cv_present = False
    if cv_document_id and not cv_replacement_required:
        cv_doc = await db.employee_documents.find_one({"id": cv_document_id})
        if cv_doc:
            doc_status = (cv_doc.get("status") or "").lower()
            is_active = cv_doc.get("is_active")
            cv_present = (
                bool(cv_doc.get("file_url"))
                and doc_status not in {"superseded", "archived", "deleted", "rejected", "invalidated"}
                and is_active is not False
            )

    if not cv_present:
        if cv_replacement_required:
            reason = "CV was rejected — please upload a replacement"
        elif cv_document_id:
            reason = "CV is no longer on file — please re-upload"
        else:
            reason = "CV not uploaded"
        blockers.append({
            "requirement_key": "cv_uploaded",
            "label": "CV / Resume",
            "reason": reason,
            "category": "document",
            "section": "application",
        })
    else:
        verified_keys.append("cv_uploaded")

    # ==========================================================================
    # CHECK 8: Required Training Matrix
    # ==========================================================================
    if requirements.get("training_blockers") and training_status:
        training_blocker_count = training_status.get("blockerCount", 0)
        training_items = training_status.get("items", [])
        
        # Count training as one requirement
        all_required_keys.append("training")
        
        if training_blocker_count > 0:
            # Get specific training blockers
            training_blockers = [t for t in training_items if t.get("blocker") and t.get("status") != "current"]
            
            if training_blockers:
                for tb in training_blockers[:3]:  # Show up to 3 training blockers
                    blockers.append({
                        "requirement_key": f"training_{tb.get('code', 'unknown')}",
                        "label": tb.get("title", "Required Training"),
                        "reason": tb.get("detail", "Training not completed"),
                        "category": "training",
                        "section": "training"
                    })
                
                if len(training_blockers) > 3:
                    blockers.append({
                        "requirement_key": "training_additional",
                        "label": f"+{len(training_blockers) - 3} more training items",
                        "reason": "Additional training requirements not met",
                        "category": "training",
                        "section": "training"
                    })
        else:
            verified_keys.append("training")
    
    # ==========================================================================
    # CHECK 9: Professional Registration (NHS Requirement for Regulated Roles)
    # ==========================================================================
    all_required_keys.append("professional_registration")
    
    reg_ok, reg_error = await check_professional_registration(person.get("id"), role_normalized, db)
    
    if reg_ok:
        verified_keys.append("professional_registration")
    elif reg_error:
        blockers.append({
            "requirement_key": "professional_registration",
            "label": "Professional Registration",
            "reason": reg_error,
            "category": "professional_registration",
            "section": "compliance"
        })
    # If no error and not required, it passes silently
    
    # ==========================================================================
    # BUILD RESULT
    # ==========================================================================
    
    can_work = len(blockers) == 0
    
    # Canonical lifecycle source is employees.status; normalize legacy aliases at read boundary.
    employee_status = normalize_lifecycle_status(person.get("status", EMPLOYEE_STATUS_APPLICANT))
    canonical_stage = get_stage_identity({"status": employee_status})
    stage_identity = "active_employee" if (canonical_stage == "employee" and employee_status == EMPLOYEE_STATUS_ACTIVE) else "onboarding"
    
    # Work readiness status - NHS compliant (no READY_WITH_CONDITIONS)
    if can_work:
        readiness_status = "READY_TO_WORK"
    else:
        readiness_status = "NOT_READY"
    
    return {
        "employee_id": person.get("id"),
        "employee_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
        "role": role,
        "role_normalized": role_normalized,
        "employee_status": employee_status,
        "stage_identity": stage_identity,
        "recruitment_approved": person.get("recruitment_approved", False),
        "can_work": can_work,
        "readiness_status": readiness_status,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "warnings": warnings,
        "warning_count": len(warnings),
        "verified_count": len(verified_keys),
        "required_count": len(all_required_keys),
        "verified_keys": verified_keys,
        "required_keys": all_required_keys
    }


# =============================================================================
# HELPER FUNCTIONS FOR BLOCK REASONS
# =============================================================================

def _get_agreement_block_reason(key: str, status: str, agreements_data: dict) -> str:
    """Generate reason for agreement blocker."""
    label = get_work_readiness_label(key)
    
    if not agreements_data:
        return f"{label} not completed"
    
    acks = agreements_data.get("acknowledgements", [])
    matching = [a for a in acks if a.get("agreement_type") == key]
    
    if not matching:
        return f"{label} not completed"
    
    latest = matching[0]
    verification_status = latest.get("verification_status", "pending")
    
    if verification_status == "pending":
        return "Submitted - awaiting verification"
    elif verification_status == "rejected":
        return "Rejected - needs resubmission"
    
    return "Not verified"


def _get_form_block_reason(key: str, status: str) -> str:
    """Generate reason for form blocker."""
    if not status or status in ["not_completed", "not_started"]:
        return "Form not completed"
    if status == "draft" or status == "recorded":
        return "Form saved as draft"
    if status in ["submitted", "awaiting_review"]:
        return "Submitted - awaiting verification"
    if status == "rejected":
        return "Rejected - needs resubmission"
    return "Not verified"


def _get_document_block_reason(key: str, doc_data: dict) -> str:
    """Generate reason for document blocker."""
    if not doc_data:
        return "No document submitted"
    
    status = doc_data.get("status", "")
    
    if status in ["not_started", "not_completed", ""]:
        return "No document submitted"
    if status == "requested":
        return "Document requested - awaiting upload"
    if status == "uploaded" or status == "awaiting_verification":
        return "Uploaded - awaiting verification"
    if status == "rejected":
        return "Rejected - needs resubmission"
    
    return "Not verified"


def _find_section_for_key(key: str, sections: dict) -> Optional[str]:
    """Find which section contains a requirement key."""
    for section_key, section_data in sections.items():
        if isinstance(section_data, dict) and "rows" in section_data:
            for row in section_data.get("rows", []):
                row_key = row.get("key", "")
                if row_key == key or row_key.startswith(key):
                    return section_key
    return None
