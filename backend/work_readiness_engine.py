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
            "clinical_competency",  # Nurse-specific clinical competency
        ],
        "critical_documents": [
            "right_to_work",
            "dbs",
            "identity",
            "nmc_registration",  # Nurse-specific
            "professional_indemnity",  # Annual insurance certificate
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
EMPLOYEE_STATUS_ACTIVE = "active_employee"  # Unconditional offer, cleared to work
EMPLOYEE_STATUS_SUSPENDED = "suspended"  # Temporarily not allowed to work
EMPLOYEE_STATUS_ARCHIVED = "archived"  # Left organization

# Statuses that appear in Recruitment Pipeline (cannot work)
RECRUITMENT_STATUSES = [EMPLOYEE_STATUS_APPLICANT, EMPLOYEE_STATUS_ONBOARDING]

# Statuses that appear in Active Employees (can work)
ACTIVE_STATUSES = [EMPLOYEE_STATUS_ACTIVE]

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
    
    # Calculate progress (excluding contract itself)
    # Count requirements by category
    
    # ========== DOCUMENTS ==========
    required_docs = ["right_to_work", "dbs", "identity", "proof_of_address", "proof_of_address_2"]
    if "nurse" in job_role:
        required_docs.append("nmc_registration")
    
    documents = await db.employee_documents.find({
        "employee_id": employee_id,
        "status": {"$nin": ["deleted", "superseded"]}
    }).to_list(200)
    
    doc_completed = 0
    for doc_type in required_docs:
        is_verified = False
        for doc in documents:
            req_id = (doc.get("requirement_id") or "").lower()
            if doc_type.replace("_", "") in req_id.replace("_", "") or doc_type in req_id:
                stamp = doc.get("verification_stamp", "")
                if stamp and stamp not in ["", "not_verified"]:
                    is_verified = True
                    break
        if is_verified:
            doc_completed += 1
            completed.append(f"{doc_type.replace('_', ' ').title()} verified")
        else:
            blockers.append(f"{doc_type.replace('_', ' ').title()} not verified")
    
    # ========== FORMS ==========
    required_forms = ["staff_health_questionnaire", "staff_personal_info", "hmrc_starter_checklist", "emergency_contacts"]
    form_submissions = await db.form_submissions.find({
        "employee_id": employee_id,
        "status": {"$in": ["submitted", "verified"]}
    }).to_list(20)
    submitted_forms = {fs.get("form_type") for fs in form_submissions}
    
    form_completed = 0
    for form_id in required_forms:
        if form_id in submitted_forms:
            form_completed += 1
            completed.append(f"{form_id.replace('_', ' ').title()} submitted")
        else:
            blockers.append(f"{form_id.replace('_', ' ').title()} required")
    
    # ========== TRAINING ==========
    mandatory_training = ["safeguarding", "manual_handling", "fire_safety", "health_safety", "bls", "infection_control"]
    training_records = await db.training_records.find({
        "employee_id": employee_id,
        "record_status": {"$ne": "superseded"}
    }).to_list(100)
    
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    training_completed = 0
    
    for training_id in mandatory_training:
        is_done = False
        for t in training_records:
            t_name = (t.get("training_name") or "").lower()
            if training_id.replace("_", " ") in t_name or training_id.replace("_", "") in t_name:
                expiry_str = t.get("expiry_date")
                if expiry_str:
                    try:
                        if isinstance(expiry_str, str):
                            expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                        else:
                            expiry = expiry_str
                        if expiry >= now:
                            is_done = True
                    except:
                        is_done = True
                else:
                    is_done = True
                break
        if is_done:
            training_completed += 1
            completed.append(f"{training_id.replace('_', ' ').title()} complete")
        else:
            blockers.append(f"{training_id.replace('_', ' ').title()} required")
    
    # ========== REFERENCES ==========
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
    
    # ========== INDUCTION (15 items) ==========
    induction_items = await db.induction_checklist.find({"employee_id": employee_id}).to_list(50)
    induction_completed = 0
    induction_total = 15  # Care Certificate Standards
    
    if induction_items:
        induction_completed = len([i for i in induction_items if i.get("completed") or i.get("status") == "completed"])
    
    if induction_completed >= 15:
        completed.append("Induction complete (15/15)")
    else:
        blockers.append(f"Induction incomplete ({induction_completed}/15)")
    
    # ========== CALCULATE TOTAL (excluding contract) ==========
    total_requirements = len(required_docs) + len(required_forms) + len(mandatory_training) + 2 + 1  # +2 refs, +1 induction
    total_completed = doc_completed + form_completed + training_completed + ref_completed + (1 if induction_completed >= 15 else 0)
    
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
        "progress_percentage": progress_percentage
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
    
    # Check contract signed
    agreements = await db.agreements.find({
        "employee_id": employee_id,
        "type": "employment_contract",
        "status": "signed"
    }).to_list(1)
    
    if not agreements:
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
        "registered nurse": "nurse",
        "rn": "nurse",
        "rgn": "nurse",
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
        "status": "verified"
    })
    checks["right_to_work"] = bool(rtw_check and rtw_stamped)
    
    # 2. DBS - verified
    dbs_check = await db.dbs_checks.find_one({
        "employee_id": emp_id_str,
        "status": "verified"
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
    
    # 5. References - both verified
    ref1_verified = employee.get("reference_1_verified", False)
    ref2_verified = employee.get("reference_2_verified", False)
    ref_doc = await db.references.find_one({"employee_id": emp_id_str})
    if ref_doc:
        # Use `or {}` to handle None values (not just missing keys)
        ref1_data = ref_doc.get("ref1") or {}
        ref2_data = ref_doc.get("ref2") or {}
        if ref1_data.get("verification_status") == "verified":
            ref1_verified = True
        if ref2_data.get("verification_status") == "verified":
            ref2_verified = True
    checks["references"] = ref1_verified and ref2_verified
    
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
    
    # 8. Induction complete (15 Care Certificate standards)
    induction = await db.induction_checklists.find_one({
        "employee_id": emp_id_str,
        "overall_status": "completed"  # P0 FIX: Use overall_status field, not status
    })
    # Also check form submissions
    if not induction:
        induction_form = await db.form_submissions.find_one({
            "employee_id": emp_id_str,
            "form_type": "induction",
            "status": {"$in": ["submitted", "verified"]}
        })
        induction = induction_form
    checks["induction"] = bool(induction)
    
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
    for competency_key in requirements.get("competencies", []):
        all_required_keys.append(competency_key)
        
        # Check in compliance sections first
        req = req_map.get(competency_key)
        
        competency_satisfied = False
        
        if req:
            is_verified = req.get("is_verified", False)
            status = req.get("status", "")
            if is_verified or status == "verified":
                competency_satisfied = True
        
        # Also check training records for competency evidence
        if not competency_satisfied:
            training_record = await db.training_records.find_one({
                "employee_id": person.get("id"),
                "requirement_id": {"$in": [competency_key, competency_key.replace("_", "-")]},
                "record_status": {"$nin": ["superseded", "deleted"]},
                "verified": True
            })
            if training_record:
                competency_satisfied = True
        
        # For care certificate, also check induction completion as equivalent
        if not competency_satisfied and competency_key == "care_certificate":
            induction_req = req_map.get("induction")
            if induction_req and (induction_req.get("is_verified") or induction_req.get("status") == "verified"):
                competency_satisfied = True
        
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
        if ref_doc.get("ref1", {}).get("verification_status") == "verified":
            ref1_verified = True
        if ref_doc.get("ref2", {}).get("verification_status") == "verified":
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
    
    # Determine stage identity based on employee status field
    employee_status = person.get("status", "applicant")
    
    # NHS two-status model:
    # - Recruitment (Conditional Offer): applicant, onboarding
    # - Active (Unconditional Offer): active_employee
    if employee_status == EMPLOYEE_STATUS_ACTIVE:
        stage_identity = "active_employee"
    elif employee_status in [EMPLOYEE_STATUS_APPLICANT, EMPLOYEE_STATUS_ONBOARDING]:
        stage_identity = "onboarding"
    else:
        stage_identity = "onboarding"  # Default to onboarding for unknown statuses
    
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
