"""
Recruitment Approval Engine

This module provides the control point that determines whether an applicant
can be approved for recruitment based on role-specific requirements.

The approval engine:
1. Checks all required blockers for the person's role
2. Shows exactly what is missing
3. Prevents approval until blockers are cleared
4. Records who approved and when
5. Moves applicant → employee/onboarding cleanly
"""

from typing import Optional
from datetime import datetime, timezone

# =============================================================================
# ROLE-SPECIFIC APPROVAL REQUIREMENTS
# =============================================================================

# These requirements MUST be verified before recruitment approval
ROLE_APPROVAL_REQUIREMENTS = {
    "healthcare_assistant": [
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "reference_1",
        "reference_2",
        "interview_record",
        "recruitment_checklist",
        "staff_health_questionnaire",
        "staff_personal_info",  # Match the actual key used in compliance file
        "employment_history_verification",  # Employment gap verification
    ],
    "nurse": [
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "reference_1",
        "reference_2",
        "interview_record",
        "recruitment_checklist",
        "staff_health_questionnaire",
        "staff_personal_info",
        "nmc_registration",  # Nurse-specific
        "employment_history_verification",  # Employment gap verification
    ],
    "senior_carer": [
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "reference_1",
        "reference_2",
        "interview_record",
        "recruitment_checklist",
        "staff_health_questionnaire",
        "staff_personal_info",
        "employment_history_verification",  # Employment gap verification
    ],
    "support_worker": [
        "right_to_work",
        "identity",
        "proof_of_address",
        "dbs",
        "reference_1",
        "reference_2",
        "interview_record",
        "recruitment_checklist",
        "staff_health_questionnaire",
        "staff_personal_info",
    ],
}

# Default requirements for unknown roles (use HCA as fallback)
DEFAULT_APPROVAL_REQUIREMENTS = ROLE_APPROVAL_REQUIREMENTS["healthcare_assistant"]

# Requirement labels for display
REQUIREMENT_LABELS = {
    "right_to_work": "Right to Work",
    "identity": "Identity Documents",
    "proof_of_address": "Proof of Address",
    "dbs": "DBS Certificate",
    "reference_1": "Reference 1",
    "reference_2": "Reference 2",
    "interview_record": "Interview Record",
    "recruitment_checklist": "Recruitment Compliance Checklist",
    "staff_health_questionnaire": "Staff Health Questionnaire",
    "staff_personal_info": "Staff Personal Information",
    "nmc_registration": "NMC Registration",
    "clinical_competency": "Clinical Competency",
    "induction": "Induction & Competency Assessment",
    "care_certificate": "Care Certificate",
    "employment_history_verification": "Employment History Verification",
}

# =============================================================================
# NON-BLOCKING REQUIREMENTS (warnings only)
# =============================================================================

# These do NOT block recruitment approval
NON_BLOCKING_REQUIREMENTS = {
    "equal_opportunities",
    "hmrc_starter_checklist",
    "cv",
    "application_form",
    "training",  # Training scan uploads
    "contract_acceptance",  # Agreements can be post-approval
    "handbook_acknowledgement",
    "induction",  # Post-approval / readiness blocker
    "care_certificate",  # Post-approval / readiness blocker
    "clinical_competency",  # Can be post-approval for non-nurse
}


# =============================================================================
# REQUIREMENT READINESS HELPERS
# =============================================================================

def is_requirement_approval_ready(req: dict) -> bool:
    """
    Determine if a requirement is ready for approval.
    
    Different requirement types have different readiness criteria:
    - Documents: must be verified
    - References: must be verified
    - Forms: must be submitted and (verified or awaiting_review acceptable for non-blocking)
    - Agreements: must be verified
    - Checks: must be verified
    - PoA: must have 2+ valid documents within 12 months AND verified
    - Employment gaps: all gaps must be verified
    """
    if not req:
        return False
    
    row_type = req.get("row_type", "")
    status = req.get("status", "")
    is_verified = req.get("is_verified", False)
    key = req.get("key", "")
    
    # Special handling for employment history verification
    if key == "employment_history_verification":
        gap_evaluation = req.get("gap_evaluation", {})
        if gap_evaluation:
            # If no gaps, requirement is met
            if not gap_evaluation.get("has_gaps"):
                return True
            # All gaps must be verified
            return gap_evaluation.get("is_complete", False)
        # Fallback to is_verified
        return is_verified
    
    # Special handling for PoA - must check freshness
    if key in ["address_verification", "proof_of_address"]:
        freshness = req.get("freshness", {})
        if freshness:
            # Must be complete (2+ valid documents within 12 months) AND verified
            is_fresh_complete = freshness.get("is_complete", False)
            return is_verified and is_fresh_complete
        # Fallback to just verified if freshness data not available
        return is_verified
    
    # For evidence/document requirements
    if row_type in {"evidence", "check"}:
        return is_verified
    
    # For reference requirements
    if row_type == "reference":
        return is_verified
    
    # For form requirements
    if row_type == "form":
        # Forms must be verified (not just submitted) for approval blockers
        return is_verified or status == "verified"
    
    # For agreement requirements
    if row_type in {"form_acknowledgement", "agreement"}:
        return is_verified or status == "verified"
    
    # Fallback - check if verified
    return is_verified


def get_block_reason(req: dict) -> str:
    """
    Generate a human-readable reason why a requirement is blocking approval.
    """
    if not req:
        return "Requirement not found"
    
    row_type = req.get("row_type", "")
    status = req.get("status", "")
    is_verified = req.get("is_verified", False)
    is_rejected = req.get("is_rejected", False)
    key = req.get("key", "")
    
    # Handle rejection first
    if is_rejected or status == "rejected":
        return "Rejected - needs resubmission"
    
    # Special handling for PoA freshness
    if key in ["address_verification", "proof_of_address"]:
        freshness = req.get("freshness", {})
        if freshness:
            valid_count = freshness.get("valid_count", 0)
            expired_count = freshness.get("expired_count", 0)
            unclear_count = freshness.get("unclear_count", 0)
            required = freshness.get("required_count", 2)
            
            if unclear_count > 0:
                return f"PoA: {unclear_count} document(s) need date verification"
            if expired_count > 0 and valid_count < required:
                return f"PoA: {expired_count} document(s) expired (older than 12 months)"
            if valid_count < required:
                return f"PoA: {valid_count}/{required} valid documents (within 12 months)"
            if not is_verified:
                return f"PoA: {valid_count} valid documents awaiting verification"
    
    # Evidence/Document requirements
    if row_type in {"evidence", "check"}:
        if status == "not_started" or status == "not_completed":
            return "No evidence submitted"
        if status == "awaiting_review":
            return "Awaiting verification"
        if status == "sent":
            return "Awaiting response"
        return "Not verified"
    
    # Reference requirements
    if row_type == "reference":
        if status == "not_started" or status == "not_declared":
            return "Reference not declared"
        if status == "declared":
            return "Request not sent"
        if status == "sent" or status == "request_sent":
            return "Awaiting referee response"
        if status == "response_received":
            return "Response received - awaiting verification"
        return "Not verified"
    
    # Form requirements
    if row_type == "form":
        if status == "not_completed" or status == "not_started":
            return "Form not completed"
        if status == "recorded" or status == "draft":
            return "Form saved as draft - needs submission"
        if status == "submitted" or status == "awaiting_review":
            return "Submitted - awaiting verification"
        return "Not verified"
    
    # Agreement requirements
    if row_type in {"form_acknowledgement", "agreement"}:
        if status == "not_completed" or status == "not_started":
            return "Agreement not completed"
        if status == "awaiting_review":
            return "Awaiting verification"
        return "Not verified"
    
    return "Requirement incomplete"


def get_requirement_label(key: str) -> str:
    """Get display label for a requirement key."""
    return REQUIREMENT_LABELS.get(key, key.replace("_", " ").title())


# =============================================================================
# MAIN EVALUATION FUNCTION
# =============================================================================

def evaluate_recruitment_approval(
    person: dict, 
    compliance_sections: dict,
    role_override: Optional[str] = None
) -> dict:
    """
    Evaluate whether an applicant can be approved for recruitment.
    
    Args:
        person: Employee/applicant document
        compliance_sections: The 'sections' dict from compliance file API
        role_override: Optional role to use instead of person's role
    
    Returns:
        Approval evaluation result with blockers, warnings, and counts
    """
    # Get role and determine required items
    role = role_override or person.get("role", "").lower()
    
    # Normalize role
    role_normalized = normalize_role_for_approval(role)
    
    # Get required keys for this role
    required_keys = ROLE_APPROVAL_REQUIREMENTS.get(
        role_normalized, 
        DEFAULT_APPROVAL_REQUIREMENTS
    )
    
    # Build a map of all requirements from compliance sections
    req_map = {}
    for section_key, section_data in compliance_sections.items():
        if isinstance(section_data, dict) and "rows" in section_data:
            for row in section_data.get("rows", []):
                row_key = row.get("key")
                if row_key:
                    req_map[row_key] = row
    
    # Special handling for combined sections (e.g., right_to_work has both evidence and check)
    # For approval, we care about the evidence row being verified
    
    # Evaluate each required requirement
    blockers = []
    verified_keys = []
    
    for key in required_keys:
        req = req_map.get(key)
        
        if not req:
            # Requirement not found in compliance file
            blockers.append({
                "requirement_key": key,
                "label": get_requirement_label(key),
                "reason": "Requirement not found in compliance file",
                "section": None
            })
            continue
        
        if is_requirement_approval_ready(req):
            verified_keys.append(key)
        else:
            # Get section for navigation
            section = get_section_for_requirement(key, compliance_sections)
            
            blockers.append({
                "requirement_key": key,
                "label": get_requirement_label(key),
                "reason": get_block_reason(req),
                "section": section,
                "current_status": req.get("status"),
                "row_type": req.get("row_type")
            })
    
    # Build warnings for non-blocking requirements that aren't ready
    warnings = []
    for key in NON_BLOCKING_REQUIREMENTS:
        req = req_map.get(key)
        if req and not is_requirement_approval_ready(req):
            warnings.append({
                "requirement_key": key,
                "label": get_requirement_label(key),
                "reason": get_block_reason(req)
            })
    
    # Determine approval status
    can_approve = len(blockers) == 0
    
    # Determine stage identity
    is_already_approved = person.get("recruitment_approved", False)
    stage_identity = "employee" if is_already_approved else "applicant"
    
    return {
        "employee_id": person.get("id"),
        "employee_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
        "role": role,
        "role_normalized": role_normalized,
        "stage_identity": stage_identity,
        "recruitment_approved": is_already_approved,
        "can_approve": can_approve,
        "next_status_if_approved": "onboarding",
        "blockers": blockers,
        "blocker_count": len(blockers),
        "warnings": warnings,
        "warning_count": len(warnings),
        "verified_count": len(verified_keys),
        "required_count": len(required_keys),
        "verified_keys": verified_keys,
        "required_keys": required_keys
    }


def get_section_for_requirement(key: str, sections: dict) -> Optional[str]:
    """Find which section contains a requirement."""
    for section_key, section_data in sections.items():
        if isinstance(section_data, dict) and "rows" in section_data:
            for row in section_data.get("rows", []):
                if row.get("key") == key:
                    return section_key
    return None


def normalize_role_for_approval(role: str) -> str:
    """Normalize role string for approval lookup."""
    role_lower = role.lower().strip() if role else ""
    
    # Map common variations
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


# =============================================================================
# APPROVAL EXECUTION
# =============================================================================

async def execute_recruitment_approval(
    person: dict,
    compliance_sections: dict,
    approver_id: str,
    approver_name: str,
    db,
    generate_employee_code_func
) -> dict:
    """
    Execute the recruitment approval if all blockers are cleared.
    
    Returns:
        Result dict with success status, employee data, or error with blockers
    """
    # First evaluate
    evaluation = evaluate_recruitment_approval(person, compliance_sections)
    
    if not evaluation["can_approve"]:
        return {
            "success": False,
            "error": "Cannot approve - blockers exist",
            "evaluation": evaluation
        }
    
    # Already approved?
    if person.get("recruitment_approved"):
        return {
            "success": False,
            "error": "Already approved for recruitment",
            "evaluation": evaluation
        }
    
    # Generate employee code if not present
    employee_code = person.get("employee_code")
    if not employee_code:
        employee_code = await generate_employee_code_func()
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee document
    update_data = {
        "recruitment_approved": True,
        "recruitment_approved_by": approver_id,
        "recruitment_approved_by_name": approver_name,
        "recruitment_approved_at": now,
        "status": "onboarding",
        "employee_code": employee_code,
        "updated_at": now
    }
    
    await db.employees.update_one(
        {"id": person["id"]},
        {"$set": update_data}
    )
    
    # Write audit log
    await db.audit_log.insert_one({
        "id": f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}_{person['id'][:8]}",
        "employee_id": person["id"],
        "action": "recruitment_approved",
        "performed_by": approver_id,
        "performed_by_name": approver_name,
        "performed_at": now,
        "role": evaluation["role"],
        "stage_from": "applicant",
        "stage_to": "employee",
        "status_from": person.get("status"),
        "status_to": "onboarding",
        "blocker_count": 0,
        "verified_count": evaluation["verified_count"],
        "required_count": evaluation["required_count"],
        "employee_code": employee_code,
        "details": {
            "verified_keys": evaluation["verified_keys"]
        }
    })
    
    # Return updated data
    updated_person = await db.employees.find_one({"id": person["id"]}, {"_id": 0})
    
    return {
        "success": True,
        "message": "Recruitment approved successfully",
        "employee": updated_person,
        "employee_code": employee_code,
        "evaluation": evaluation
    }
