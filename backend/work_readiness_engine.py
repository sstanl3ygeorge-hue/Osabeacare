"""
Work Readiness Engine (Gate 2)

This module evaluates whether an APPROVED employee is ready to start work.
Separate from Recruitment Approval (Gate 1), this checks post-recruitment items.

Gate 1 (Recruitment Approval): Can we hire this person?
Gate 2 (Work Readiness): Can this person start working?

Work Readiness Blockers include:
- Contract not completed/verified
- Handbook not completed/verified
- Induction not completed/verified
- Health questionnaire not completed/reviewed
- Role-specific competency not completed
- Required training not satisfied
- Expired/invalid critical documents (RTW, DBS, identity, NMC)
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta

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
    # Training
    "training": "Required Training",
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
    # BUILD RESULT
    # ==========================================================================
    
    can_work = len(blockers) == 0
    
    # Determine stage identity
    is_recruitment_approved = person.get("recruitment_approved", False)
    stage_identity = "employee" if is_recruitment_approved else "applicant"
    
    # Work readiness status
    if can_work:
        readiness_status = "READY_TO_WORK"
    elif len(blockers) <= 3:
        readiness_status = "READY_WITH_CONDITIONS"
    else:
        readiness_status = "NOT_READY"
    
    return {
        "employee_id": person.get("id"),
        "employee_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
        "role": role,
        "role_normalized": role_normalized,
        "stage_identity": stage_identity,
        "recruitment_approved": is_recruitment_approved,
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
