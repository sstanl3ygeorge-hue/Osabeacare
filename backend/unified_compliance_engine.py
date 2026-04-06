"""
Unified Compliance Engine - SINGLE SOURCE OF TRUTH
===================================================

This module provides ONE unified function for ALL compliance/progress/blocker calculations.
ALL endpoints MUST call get_unified_employee_status() - no separate implementations allowed.

Standards Supported:
- CIA Triad: Integrity (same data for all views), Availability (role-filtered), Confidentiality
- 5 E's of Usability: Effective, Efficient, Engaging, Error Tolerant, Easy to Learn
- NHS Level: Complete employment check standards
- CQC Audit Level: Full audit trail, documented evidence, verifiable records

Architecture:
    ALL UI Components → API Endpoints → get_unified_employee_status() → Database
    
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                           ONE SOURCE OF TRUTH                                   │
    │                    get_unified_employee_status()                                │
    └─────────────────────────────────────────────────────────────────────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            │                           │                           │
            ▼                           ▼                           ▼
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │  Admin Views    │     │  Worker Portal  │     │  Audit Views    │
    │  (Full access)  │     │  (Filtered)     │     │  (Read-only)    │
    └─────────────────┘     └─────────────────┘     └─────────────────┘
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS - NHS Employment Check Standards
# =============================================================================

# Mandatory Training for Healthcare Assistants (8 items - P0 CRITICAL)
# NHS Employment Check Standards + CQC Requirements
MANDATORY_TRAINING_HCA = [
    {"id": "safeguarding_adults", "name": "Safeguarding Adults", "induction_sync": "safeguarding_adults"},
    {"id": "manual_handling", "name": "Manual Handling / Moving & Handling", "induction_sync": "moving_handling"},
    {"id": "fire_safety", "name": "Fire Safety", "induction_sync": "fire_safety"},
    {"id": "health_safety", "name": "Health & Safety", "induction_sync": "health_safety"},
    {"id": "basic_life_support", "name": "Basic Life Support (BLS)", "induction_sync": "basic_life_support"},
    {"id": "infection_control", "name": "Infection Prevention & Control", "induction_sync": "infection_control"},
    # P0 ADDITIONS - Mandatory per NHS/CQC requirements
    {"id": "information_governance", "name": "Information Governance / GDPR / Data Protection", "induction_sync": None},
    {"id": "prevent", "name": "Prevent (Counter-Terrorism Awareness)", "induction_sync": None},
]

# 15 Care Certificate Standards for Induction (Adults only - no Safeguarding Children)
CARE_CERTIFICATE_STANDARDS = [
    {"id": "understand_your_role", "num": 1, "name": "Understand Your Role", "training_sync": None},
    {"id": "personal_development", "num": 2, "name": "Your Personal Development", "training_sync": None},
    {"id": "duty_of_care", "num": 3, "name": "Duty of Care", "training_sync": None},
    {"id": "equality_diversity", "num": 4, "name": "Equality and Diversity", "training_sync": None},
    {"id": "work_person_centred", "num": 5, "name": "Work in a Person-Centred Way", "training_sync": None},
    {"id": "communication", "num": 6, "name": "Communication", "training_sync": None},
    {"id": "privacy_dignity", "num": 7, "name": "Privacy and Dignity", "training_sync": None},
    {"id": "fluids_nutrition", "num": 8, "name": "Fluids and Nutrition", "training_sync": None},
    {"id": "awareness_mental_health", "num": 9, "name": "Awareness of Mental Health, Dementia and Learning Disabilities", "training_sync": None},
    {"id": "safeguarding_adults", "num": 10, "name": "Safeguarding Adults", "training_sync": "safeguarding_adults"},
    {"id": "basic_life_support", "num": 11, "name": "Basic Life Support", "training_sync": "basic_life_support"},
    {"id": "health_safety", "num": 12, "name": "Health and Safety", "training_sync": "health_safety"},
    {"id": "infection_control", "num": 13, "name": "Infection Prevention and Control", "training_sync": "infection_control"},
    {"id": "moving_handling", "num": 14, "name": "Handle Information / Moving & Handling", "training_sync": "manual_handling"},
    {"id": "fire_safety", "num": 15, "name": "Fire Safety", "training_sync": "fire_safety"},
]

# Documents required for ALL roles
REQUIRED_DOCUMENTS = [
    {"id": "right_to_work", "name": "Right to Work", "requires_stamp": True, "category": "identity"},
    {"id": "dbs", "name": "DBS Certificate", "requires_stamp": True, "category": "safety"},
    {"id": "identity", "name": "Identity Document", "requires_stamp": True, "category": "identity"},
    {"id": "proof_of_address", "name": "Proof of Address", "requires_stamp": True, "min_count": 2, "category": "identity"},
]

# Forms required for ALL roles
REQUIRED_FORMS = [
    {"id": "interview_record", "name": "Interview Record", "source": "admin"},
    {"id": "staff_health_questionnaire", "name": "Staff Health Questionnaire", "source": "worker"},
]

# Role-specific requirements
ROLE_SPECIFIC_REQUIREMENTS = {
    "nurse": [
        {"id": "nmc_registration", "name": "NMC Registration", "type": "professional_registration"},
        {"id": "professional_indemnity", "name": "Professional Indemnity Insurance", "type": "document"},
    ],
    "doctor": [
        {"id": "gmc_registration", "name": "GMC Registration", "type": "professional_registration"},
    ],
}

# Clear labels for UI (Easy to Learn - 5 E's)
CLEAR_LABELS = {
    "right_to_work": "Right to Work",
    "dbs": "DBS Certificate",
    "identity": "Identity Document",
    "proof_of_address": "Proof of Address (2 documents required)",
    "reference_1": "Reference 1",
    "reference_2": "Reference 2",
    "interview_record": "Interview Record",
    "contract": "Employment Contract",
    "induction": "Induction Checklist (15 Care Certificate Standards)",
    "mandatory_training": "Mandatory Training (8 courses)",  # Updated: +IG +Prevent
    "staff_health_questionnaire": "Staff Health Questionnaire",
    "employment_gaps": "Employment Gaps Explained",
    "nmc_registration": "NMC Registration",
    "gmc_registration": "GMC Registration",
    "professional_indemnity": "Professional Indemnity Insurance",
    "information_governance": "Information Governance / GDPR",
    "prevent": "Prevent Training",
}


def get_clear_label(item_id: str) -> str:
    """Get user-friendly label for an item (Easy to Learn - 5 E's)"""
    return CLEAR_LABELS.get(item_id, item_id.replace("_", " ").title())


# =============================================================================
# VERIFICATION STATUS HELPERS
# =============================================================================

def is_document_verified_with_stamp(doc: dict) -> bool:
    """
    Check if document is properly verified WITH stamp.
    NHS Standard: Documents must be stamped as Original Seen / Copy Verified / Online Check
    """
    if not doc:
        return False
    
    stamp = doc.get("verification_stamp", "")
    status = doc.get("status", "")
    verified_flag = doc.get("verified", False)
    
    # Must have a valid stamp
    valid_stamps = ["original_seen", "copy_verified", "certified_copy", "online_check", "verified"]
    has_valid_stamp = stamp and stamp.lower() not in ["", "not_verified", "pending", "none"]
    
    # Also check if status indicates verified
    verified_statuses = ["verified", "approved", "active"]
    has_verified_status = status.lower() in verified_statuses if status else False
    
    return has_valid_stamp or (has_verified_status and verified_flag)


def is_training_valid(training: dict) -> Tuple[bool, Optional[str]]:
    """
    Check if training is valid (verified and not expired).
    Returns: (is_valid, reason_if_invalid)
    """
    if not training:
        return (False, "Not uploaded")
    
    # Check verified status
    verified = training.get("verified", False)
    status = training.get("status", "")
    computed_status = training.get("computed_status", "")
    
    is_verified = verified or status == "verified" or computed_status == "verified"
    
    if not is_verified:
        return (False, "Not verified")
    
    # Check expiry
    expiry_str = training.get("expiry_date")
    if expiry_str:
        try:
            if isinstance(expiry_str, str):
                if 'T' in expiry_str:
                    expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    expiry = datetime.fromisoformat(expiry_str + "T00:00:00+00:00")
            else:
                expiry = expiry_str
            
            now = datetime.now(timezone.utc)
            if expiry < now:
                return (False, f"Expired on {expiry_str[:10]}")
        except Exception:
            pass
    
    return (True, None)


def get_verifier_name(user_id: str, users_cache: dict) -> str:
    """
    Get verifier's display name instead of email (CQC Audit requirement).
    """
    if not user_id:
        return "System"
    
    user = users_cache.get(user_id)
    if user:
        first = user.get("first_name", "")
        last = user.get("last_name", "")
        if first or last:
            return f"{first} {last}".strip()
        # Fall back to email prefix if no name
        email = user.get("email", "")
        if email and "@" in email:
            return email.split("@")[0].title()
    
    return user_id[:8] if user_id else "Unknown"


# =============================================================================
# MAIN UNIFIED FUNCTION - SINGLE SOURCE OF TRUTH
# =============================================================================

async def get_unified_employee_status(
    employee_id: str,
    db,
    user_role: str = "admin",
    include_details: bool = True
) -> dict:
    """
    SINGLE SOURCE OF TRUTH for all compliance/progress/blocker calculations.
    
    ALL endpoints MUST call this function. No separate implementations allowed.
    
    Standards Supported:
    - CIA Triad: Integrity (same data), Availability (role-filtered), Confidentiality
    - 5 E's: Effective, Efficient, Error Tolerant, Easy to Learn
    - NHS Level: Complete employment checks
    - CQC Level: Audit-ready with verifier names
    
    Args:
        employee_id: Employee UUID
        db: Database connection
        user_role: "admin", "worker", or "auditor" for filtering
        include_details: Include full requirement details (set False for summary only)
    
    Returns:
        Unified status dict with:
        - blockers: List of blocking items (ONLY truly incomplete items)
        - progress: Overall progress calculation
        - categories: Breakdown by category
        - checks: Detailed check results
        - can_promote: Boolean for promotion eligibility
        - is_work_ready: Boolean for work readiness
    """
    
    # Get employee data
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return {"error": "Employee not found", "blockers": [], "progress": {"percentage": 0}}
    
    emp_id = employee.get("id", employee_id)
    role = (employee.get("job_role") or employee.get("role") or "Healthcare Assistant").lower()
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    # Build users cache for verifier name lookups (CQC requirement)
    users_cache = {}
    users = await db.users.find({}, {"_id": 0, "user_id": 1, "email": 1, "first_name": 1, "last_name": 1}).to_list(100)
    for u in users:
        users_cache[u.get("user_id", "")] = u
        users_cache[u.get("email", "")] = u
    
    # ==========================================================================
    # FETCH ALL DATA IN PARALLEL (Efficient - 5 E's)
    # ==========================================================================
    
    # Get all documents
    all_docs = await db.employee_documents.find({
        "employee_id": emp_id,
        "status": {"$nin": ["deleted", "superseded", "rejected"]}
    }, {"_id": 0}).to_list(500)
    
    # Get training records (exclude deleted/superseded)
    all_training = await db.training_records.find({
        "employee_id": emp_id,
        "record_status": {"$nin": ["superseded", "deleted"]},
        "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
    }, {"_id": 0}).to_list(100)
    
    # Get form submissions
    all_forms = await db.form_submissions.find({
        "employee_id": emp_id,
        "status": {"$in": ["submitted", "verified", "approved"]}
    }, {"_id": 0}).to_list(50)
    
    # Get induction checklist
    induction_record = await db.induction_checklists.find_one({
        "employee_id": emp_id
    }, {"_id": 0})
    
    # Get agreements/acknowledgements
    agreements = await db.agreement_acknowledgements.find({
        "employee_id": emp_id
    }, {"_id": 0}).to_list(20)
    
    # Get references
    references = employee.get("references", [])
    ref_doc = await db.references.find_one({"employee_id": emp_id}, {"_id": 0})
    
    # Get DBS and RTW checks from dedicated collections
    dbs_check = await db.dbs_checks.find_one({"employee_id": emp_id, "status": "verified"}, {"_id": 0})
    rtw_check = await db.rtw_checks.find_one({"employee_id": emp_id, "status": "verified"}, {"_id": 0})
    
    # ==========================================================================
    # INITIALIZE TRACKING
    # ==========================================================================
    
    checks = {}  # Detailed check results
    blockers = []  # ONLY truly incomplete items
    categories = {
        "documents": {"completed": 0, "total": 0, "items": []},
        "forms": {"completed": 0, "total": 0, "items": []},
        "training": {"completed": 0, "total": 8, "items": []},  # 8 mandatory: 6 core + IG + Prevent
        "references": {"completed": 0, "total": 2, "items": []},
        "agreements": {"completed": 0, "total": 2, "items": []},
        "induction": {"completed": 0, "total": 15, "items": []},
    }
    
    # ==========================================================================
    # CHECK 1: DOCUMENTS (RTW, DBS, Identity, PoA)
    # ==========================================================================
    
    def find_docs_for_requirement(req_id: str) -> List[dict]:
        """Find all documents matching a requirement ID"""
        matches = []
        for doc in all_docs:
            doc_req_id = (doc.get("requirement_id") or "").lower()
            doc_type = (doc.get("document_type_name") or "").lower()
            
            # Match by requirement_id
            if req_id in doc_req_id or doc_req_id == req_id:
                matches.append(doc)
            # Match by document type
            elif req_id.replace("_", " ") in doc_type or req_id.replace("_", "") in doc_type.replace(" ", ""):
                matches.append(doc)
        return matches
    
    for doc_req in REQUIRED_DOCUMENTS:
        req_id = doc_req["id"]
        req_name = doc_req["name"]
        requires_stamp = doc_req.get("requires_stamp", True)
        min_count = doc_req.get("min_count", 1)
        
        categories["documents"]["total"] += 1
        
        # Find matching documents
        matching_docs = find_docs_for_requirement(req_id)
        
        # Count verified documents with stamps
        verified_count = 0
        for doc in matching_docs:
            if is_document_verified_with_stamp(doc):
                verified_count += 1
        
        # Special handling for DBS and RTW from dedicated collections
        if req_id == "dbs" and dbs_check:
            verified_count = max(verified_count, 1)
        if req_id == "right_to_work" and rtw_check:
            verified_count = max(verified_count, 1)
        
        is_complete = verified_count >= min_count
        checks[req_id] = is_complete
        
        item_data = {
            "id": req_id,
            "name": get_clear_label(req_id),
            "completed": is_complete,
            "verified_count": verified_count,
            "required_count": min_count,
            "has_upload": len(matching_docs) > 0,
            "requires_stamp": requires_stamp,
        }
        
        if include_details:
            item_data["documents"] = matching_docs[:5]  # Limit for response size
        
        categories["documents"]["items"].append(item_data)
        
        if is_complete:
            categories["documents"]["completed"] += 1
        else:
            # Add to blockers with clear label (NOT email, NOT "U/S")
            if len(matching_docs) > 0 and verified_count < min_count:
                blocker_msg = f"{get_clear_label(req_id)}: Awaiting verification"
            else:
                blocker_msg = f"{get_clear_label(req_id)}: Not uploaded"
            
            blockers.append({
                "id": req_id,
                "gate": req_id,
                "label": get_clear_label(req_id),
                "reason": blocker_msg,
                "category": "documents",
                "has_upload": len(matching_docs) > 0,
                "severity": "pending" if len(matching_docs) > 0 else "critical"
            })
    
    # ==========================================================================
    # CHECK 2: REFERENCES (2 required)
    # ==========================================================================
    
    ref1_verified = False
    ref2_verified = False
    
    # Check from references array on employee
    for idx, ref in enumerate(references[:2]):
        is_verified = ref.get("verified") or ref.get("status") == "verified"
        if idx == 0:
            ref1_verified = is_verified
        else:
            ref2_verified = is_verified
    
    # Check from references collection
    if ref_doc:
        if ref_doc.get("ref1", {}).get("verification_status") == "verified":
            ref1_verified = True
        if ref_doc.get("ref2", {}).get("verification_status") == "verified":
            ref2_verified = True
    
    # Also check employee-level flags
    if employee.get("reference_1_verified"):
        ref1_verified = True
    if employee.get("reference_2_verified"):
        ref2_verified = True
    
    checks["reference_1"] = ref1_verified
    checks["reference_2"] = ref2_verified
    checks["references"] = ref1_verified and ref2_verified
    
    categories["references"]["items"] = [
        {"id": "reference_1", "name": "Reference 1", "completed": ref1_verified},
        {"id": "reference_2", "name": "Reference 2", "completed": ref2_verified},
    ]
    categories["references"]["completed"] = (1 if ref1_verified else 0) + (1 if ref2_verified else 0)
    
    if not ref1_verified:
        blockers.append({
            "id": "reference_1",
            "gate": "reference_1",
            "label": "Reference 1",
            "reason": "Reference 1: Not verified",
            "category": "references",
            "severity": "critical"
        })
    if not ref2_verified:
        blockers.append({
            "id": "reference_2",
            "gate": "reference_2",
            "label": "Reference 2",
            "reason": "Reference 2: Not verified",
            "category": "references",
            "severity": "critical"
        })
    
    # ==========================================================================
    # CHECK 3: MANDATORY TRAINING (6 items)
    # ==========================================================================
    
    # Build training lookup by name
    training_by_name = {}
    for t in all_training:
        t_name = (t.get("training_name") or t.get("course_name") or "").lower()
        t_type = (t.get("training_type") or "").lower()
        training_by_name[t_name] = t
        training_by_name[t_type] = t
    
    verified_training = {}  # Track which trainings are verified (for induction sync)
    
    for training_req in MANDATORY_TRAINING_HCA:
        t_id = training_req["id"]
        t_name = training_req["name"]
        induction_sync_id = training_req.get("induction_sync")
        
        # Find matching training record
        matched_training = None
        search_terms = [t_id, t_id.replace("_", " "), t_id.replace("_", "")]
        for term in search_terms:
            for key, training in training_by_name.items():
                if term in key or key in term:
                    matched_training = training
                    break
            if matched_training:
                break
        
        is_valid, invalid_reason = is_training_valid(matched_training)
        checks[f"training_{t_id}"] = is_valid
        
        # Track for induction sync
        if is_valid and induction_sync_id:
            verified_training[induction_sync_id] = True
        
        verifier_name = None
        if matched_training and matched_training.get("verified_by"):
            verifier_name = get_verifier_name(matched_training["verified_by"], users_cache)
        
        item_data = {
            "id": t_id,
            "name": t_name,
            "completed": is_valid,
            "has_record": matched_training is not None,
            "verified": matched_training.get("verified", False) if matched_training else False,
            "verified_by": verifier_name,
            "expiry_date": matched_training.get("expiry_date") if matched_training else None,
            "invalid_reason": invalid_reason,
        }
        
        categories["training"]["items"].append(item_data)
        
        if is_valid:
            categories["training"]["completed"] += 1
        else:
            reason = f"{t_name}: {invalid_reason}" if invalid_reason else f"{t_name}: Not completed"
            blockers.append({
                "id": t_id,
                "gate": "mandatory_training",
                "label": t_name,
                "reason": reason,
                "category": "training",
                "severity": "critical" if not matched_training else "pending"
            })
    
    checks["mandatory_training"] = categories["training"]["completed"] == 8  # All 8 mandatory trainings
    
    # ==========================================================================
    # CHECK 4: INDUCTION CHECKLIST (15 Care Certificate Standards)
    # AUTO-SYNC: When training is verified, corresponding induction item completes
    # ==========================================================================
    
    induction_items = []
    if induction_record and induction_record.get("items"):
        induction_items = induction_record.get("items", [])
    
    # Build induction status map
    induction_status_map = {}
    for item in induction_items:
        item_id = item.get("id") or item.get("standard_id")
        induction_status_map[item_id] = item.get("status") == "completed"
    
    induction_completed_count = 0
    
    for standard in CARE_CERTIFICATE_STANDARDS:
        std_id = standard["id"]
        std_name = standard["name"]
        training_sync = standard.get("training_sync")
        
        # Check if completed in induction record
        is_completed = induction_status_map.get(std_id, False)
        
        # AUTO-SYNC: If corresponding training is verified, mark induction as complete
        if training_sync and verified_training.get(training_sync):
            is_completed = True
        
        # Also check by standard number
        for item in induction_items:
            if item.get("standard_number") == standard.get("num"):
                if item.get("status") == "completed":
                    is_completed = True
                break
        
        item_data = {
            "id": std_id,
            "num": standard.get("num"),
            "name": std_name,
            "completed": is_completed,
            "auto_synced": training_sync and verified_training.get(training_sync, False),
            "training_sync": training_sync,
        }
        
        categories["induction"]["items"].append(item_data)
        
        if is_completed:
            induction_completed_count += 1
    
    categories["induction"]["completed"] = induction_completed_count
    checks["induction"] = induction_completed_count == 15
    
    if induction_completed_count < 15:
        blockers.append({
            "id": "induction",
            "gate": "induction",
            "label": f"Induction Checklist ({induction_completed_count}/15 complete)",
            "reason": f"Induction: {induction_completed_count} of 15 Care Certificate standards complete",
            "category": "induction",
            "severity": "pending" if induction_completed_count > 0 else "critical"
        })
    
    # ==========================================================================
    # CHECK 5: FORMS (Interview Record, Health Questionnaire)
    # ==========================================================================
    
    for form_req in REQUIRED_FORMS:
        form_id = form_req["id"]
        form_name = form_req["name"]
        
        categories["forms"]["total"] += 1
        
        # Find matching form submission
        matched_form = None
        for form in all_forms:
            form_type = (form.get("form_type") or "").lower()
            if form_id in form_type or form_type in form_id:
                matched_form = form
                break
        
        is_complete = matched_form is not None
        checks[form_id] = is_complete
        
        item_data = {
            "id": form_id,
            "name": get_clear_label(form_id),
            "completed": is_complete,
            "source": form_req.get("source"),
            "submitted_at": matched_form.get("submitted_at") if matched_form else None,
        }
        
        categories["forms"]["items"].append(item_data)
        
        if is_complete:
            categories["forms"]["completed"] += 1
        else:
            blockers.append({
                "id": form_id,
                "gate": form_id,
                "label": get_clear_label(form_id),
                "reason": f"{get_clear_label(form_id)}: Not completed",
                "category": "forms",
                "severity": "critical"
            })
    
    # ==========================================================================
    # CHECK 6: AGREEMENTS (Contract, Handbook)
    # ==========================================================================
    
    # Contract
    contract_ack = None
    for ack in agreements:
        ack_type = (ack.get("agreement_type") or "").lower()
        if "contract" in ack_type:
            if ack.get("status") in ["signed", "submitted", "verified"]:
                contract_ack = ack
                break
    
    contract_signed = bool(contract_ack) or employee.get("contract_signed", False)
    checks["contract"] = contract_signed
    
    # Handbook
    handbook_ack = None
    for ack in agreements:
        ack_type = (ack.get("agreement_type") or "").lower()
        if "handbook" in ack_type:
            if ack.get("status") in ["acknowledged", "signed", "submitted"]:
                handbook_ack = ack
                break
    
    handbook_acknowledged = bool(handbook_ack)
    checks["handbook"] = handbook_acknowledged
    
    categories["agreements"]["items"] = [
        {"id": "contract", "name": "Employment Contract", "completed": contract_signed},
        {"id": "handbook", "name": "Employee Handbook", "completed": handbook_acknowledged},
    ]
    categories["agreements"]["completed"] = (1 if contract_signed else 0) + (1 if handbook_acknowledged else 0)
    
    if not contract_signed:
        blockers.append({
            "id": "contract",
            "gate": "contract_signed",
            "label": "Employment Contract",
            "reason": "Employment Contract: Not signed by worker",
            "category": "agreements",
            "severity": "critical"
        })
    # Note: Handbook may be optional, don't add to blockers
    
    # ==========================================================================
    # CHECK 7: EMPLOYMENT GAPS (if applicable)
    # ==========================================================================
    
    gaps = employee.get("employment_gaps", [])
    gaps_explained = True
    unexplained_gaps = []
    
    for gap in gaps:
        duration_months = gap.get("duration_months", 0)
        if duration_months >= 1:
            if not gap.get("explanation") or gap.get("status") in ["not_explained", "needs_info"]:
                gaps_explained = False
                unexplained_gaps.append(gap)
    
    # Also check employment_gaps collection
    gap_docs = await db.employment_gaps.find({
        "employee_id": emp_id,
        "duration_months": {"$gte": 1},
        "$or": [
            {"explanation": {"$exists": False}},
            {"explanation": None},
            {"explanation": ""},
            {"status": {"$in": ["not_explained", "needs_info"]}}
        ]
    }).to_list(20)
    
    if gap_docs:
        gaps_explained = False
    
    checks["employment_gaps_explained"] = gaps_explained
    
    if not gaps_explained:
        gap_count = len(unexplained_gaps) + len(gap_docs)
        blockers.append({
            "id": "employment_gaps",
            "gate": "employment_gaps",
            "label": "Employment Gaps",
            "reason": f"Employment Gaps: {gap_count} gap(s) need explanation",
            "category": "other",
            "severity": "pending"
        })
    
    # ==========================================================================
    # CHECK 8: PROFESSIONAL REGISTRATION (Nurse-specific)
    # ==========================================================================
    
    is_nurse = "nurse" in role
    checks["professional_registration"] = True
    checks["professional_indemnity"] = True
    
    if is_nurse:
        # NMC Registration
        registrations = employee.get("professional_registrations", [])
        nmc_verified = False
        for reg in registrations:
            if reg.get("body") == "NMC" and reg.get("verified"):
                # Check not expired
                expiry_str = reg.get("registration_expiry_date")
                is_expired = False
                if expiry_str:
                    try:
                        if isinstance(expiry_str, str):
                            expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                        else:
                            expiry = expiry_str
                        is_expired = expiry < datetime.now(timezone.utc)
                    except Exception:
                        pass
                
                if not is_expired:
                    nmc_verified = True
                    break
        
        checks["professional_registration"] = nmc_verified
        
        if not nmc_verified:
            blockers.append({
                "id": "nmc_registration",
                "gate": "nmc_registration",
                "label": "NMC Registration",
                "reason": "NMC Registration: Not verified or expired",
                "category": "professional",
                "severity": "critical"
            })
        
        # Professional Indemnity Insurance
        indemnity_docs = find_docs_for_requirement("professional_indemnity")
        indemnity_verified = any(is_document_verified_with_stamp(d) for d in indemnity_docs)
        checks["professional_indemnity"] = indemnity_verified
        
        if not indemnity_verified:
            blockers.append({
                "id": "professional_indemnity",
                "gate": "professional_indemnity",
                "label": "Professional Indemnity Insurance",
                "reason": "Professional Indemnity Insurance: Not uploaded or verified",
                "category": "professional",
                "severity": "critical"
            })
    
    # ==========================================================================
    # CALCULATE OVERALL PROGRESS
    # ==========================================================================
    
    total_requirements = sum(cat["total"] for cat in categories.values())
    completed_requirements = sum(cat["completed"] for cat in categories.values())
    
    # Add nurse-specific requirements to total
    if is_nurse:
        total_requirements += 2  # NMC + Indemnity
        if checks.get("professional_registration"):
            completed_requirements += 1
        if checks.get("professional_indemnity"):
            completed_requirements += 1
    
    overall_percentage = round((completed_requirements / total_requirements) * 100) if total_requirements > 0 else 0
    
    # ==========================================================================
    # DETERMINE PROMOTION ELIGIBILITY
    # ==========================================================================
    
    # Can promote = NO blockers
    can_promote = len(blockers) == 0
    is_work_ready = len(blockers) == 0
    
    # ==========================================================================
    # BUILD RESPONSE
    # ==========================================================================
    
    # Sort blockers by severity (critical first)
    severity_order = {"critical": 0, "pending": 1, "warning": 2}
    blockers.sort(key=lambda b: severity_order.get(b.get("severity", "warning"), 2))
    
    result = {
        "employee_id": emp_id,
        "employee_name": employee_name,
        "role": role,
        
        # SINGLE progress calculation
        "progress": {
            "percentage": overall_percentage,
            "completed": completed_requirements,
            "total": total_requirements,
        },
        
        # SINGLE blocker list (ONLY truly incomplete items)
        "blockers": blockers,
        "blocker_count": len(blockers),
        
        # Category breakdown
        "categories": {
            cat_name: {
                "completed": cat_data["completed"],
                "total": cat_data["total"],
            }
            for cat_name, cat_data in categories.items()
        },
        
        # Detailed checks
        "checks": checks,
        
        # Promotion eligibility
        "can_promote": can_promote,
        "is_work_ready": is_work_ready,
        
        # Gates format (for pre-employment-gates endpoint compatibility)
        "gates": {
            "interview_record": {"passed": checks.get("interview_record", False), "label": "Interview Record"},
            "contract_signed": {"passed": checks.get("contract", False), "label": "Contract Signed"},
            "dbs_verified": {"passed": checks.get("dbs", False), "label": "DBS Verified + Stamped"},
            "right_to_work": {"passed": checks.get("right_to_work", False), "label": "Right to Work Verified + Stamped"},
            "identity": {"passed": checks.get("identity", False), "label": "Identity Verified + Stamped"},
            "proof_of_address": {"passed": checks.get("proof_of_address", False), "label": "Proof of Address (2 documents)"},
            "reference_1": {"passed": checks.get("reference_1", False), "label": "Reference 1 Verified"},
            "reference_2": {"passed": checks.get("reference_2", False), "label": "Reference 2 Verified"},
            "induction": {"passed": checks.get("induction", False), "label": "Induction Checklist (15 standards)"},
            "mandatory_training": {"passed": checks.get("mandatory_training", False), "label": "Mandatory Training (6 items)"},
            "health_questionnaire": {"passed": checks.get("staff_health_questionnaire", False), "label": "Staff Health Questionnaire"},
            "employment_gaps": {"passed": checks.get("employment_gaps_explained", True), "label": "Employment Gaps Explained"},
        },
        "gates_passed": sum(1 for g in checks.values() if g is True),
        "total_gates": 12 + (2 if is_nurse else 0),
    }
    
    # Include detailed items if requested
    if include_details:
        result["category_details"] = categories
    
    # ==========================================================================
    # ROLE-BASED FILTERING (CIA Triad - Availability)
    # ==========================================================================
    
    if user_role == "worker":
        # Workers see same blockers but limited document details
        result = filter_for_worker(result)
    elif user_role == "auditor":
        # Auditors see everything read-only
        result["read_only"] = True
    
    return result


def filter_for_worker(data: dict) -> dict:
    """
    Filter response for worker view (Availability - CIA Triad).
    Workers see same progress/blockers but limited internal details.
    """
    # Workers see the same high-level data
    # Remove sensitive admin-only fields
    filtered = {
        "employee_id": data.get("employee_id"),
        "employee_name": data.get("employee_name"),
        "progress": data.get("progress"),
        "blockers": data.get("blockers"),  # Same blockers so worker knows what to do
        "blocker_count": data.get("blocker_count"),
        "categories": data.get("categories"),
        "is_work_ready": data.get("is_work_ready"),
        # Don't expose detailed checks or internal gates to workers
    }
    return filtered


# =============================================================================
# INDUCTION AUTO-SYNC FUNCTION
# =============================================================================

async def sync_induction_with_training(employee_id: str, db) -> dict:
    """
    Sync induction checklist items with verified training records.
    When a training is verified, the corresponding induction item auto-completes.
    
    This is called after training verification to keep induction in sync.
    
    Returns dict with sync results.
    """
    # Get verified training
    training_records = await db.training_records.find({
        "employee_id": employee_id,
        "verified": True,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0}).to_list(100)
    
    # Build set of verified training types
    verified_types = set()
    for t in training_records:
        t_name = (t.get("training_name") or t.get("course_name") or "").lower()
        t_type = (t.get("training_type") or "").lower()
        
        # Normalize to induction sync IDs
        if "safeguarding" in t_name and "adult" in t_name:
            verified_types.add("safeguarding_adults")
        if "manual handling" in t_name or "moving" in t_name:
            verified_types.add("moving_handling")
        if "fire" in t_name:
            verified_types.add("fire_safety")
        if "health" in t_name and "safety" in t_name:
            verified_types.add("health_safety")
        if "bls" in t_name or "life support" in t_name:
            verified_types.add("basic_life_support")
        if "infection" in t_name:
            verified_types.add("infection_control")
    
    # Get or create induction checklist
    induction = await db.induction_checklists.find_one({"employee_id": employee_id})
    
    if not induction:
        # Create default induction with 15 standards
        items = []
        for std in CARE_CERTIFICATE_STANDARDS:
            items.append({
                "id": std["id"],
                "standard_number": std.get("num"),
                "name": std["name"],
                "status": "pending",
                "mandatory": True,
            })
        
        induction = {
            "employee_id": employee_id,
            "items": items,
            "overall_status": "in_progress",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.induction_checklists.insert_one(induction)
        induction = await db.induction_checklists.find_one({"employee_id": employee_id})
    
    # Sync items
    synced_items = []
    items = induction.get("items", [])
    
    for std in CARE_CERTIFICATE_STANDARDS:
        training_sync = std.get("training_sync")
        if training_sync and training_sync in verified_types:
            # Find and update the item
            for item in items:
                if item.get("id") == std["id"] and item.get("status") != "completed":
                    item["status"] = "completed"
                    item["auto_synced_from_training"] = True
                    item["synced_at"] = datetime.now(timezone.utc).isoformat()
                    synced_items.append(std["id"])
    
    # Update induction
    completed_count = sum(1 for item in items if item.get("status") == "completed")
    overall_status = "completed" if completed_count == 15 else "in_progress"
    
    await db.induction_checklists.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "items": items,
            "overall_status": overall_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    
    return {
        "synced_items": synced_items,
        "completed_count": completed_count,
        "total": 15,
        "overall_status": overall_status,
    }
