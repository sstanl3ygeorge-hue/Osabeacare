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
    {"id": "manual_handling", "name": "Manual Handling / Moving & Handling", "induction_sync": None},  # No matching Care Certificate standard for moving & handling
    {"id": "fire_safety", "name": "Fire Safety", "induction_sync": "fire_safety"},
    {"id": "health_safety", "name": "Health & Safety", "induction_sync": "health_safety"},
    {"id": "basic_life_support", "name": "Basic Life Support (BLS)", "induction_sync": "basic_life_support"},
    {"id": "infection_control", "name": "Infection Prevention & Control", "induction_sync": "infection_control"},
    # P0 ADDITIONS - Mandatory per NHS/CQC requirements
    {"id": "information_governance", "name": "Information Governance / GDPR / Data Protection", "induction_sync": None},
    {"id": "prevent", "name": "Prevent (Counter-Terrorism Awareness)", "induction_sync": None},
]

# 15 Care Certificate Standards for Induction (Adults ONLY - NO Safeguarding Children)
# These are the official NHS Care Certificate standards for adult social care
# Auto-complete mapping: When training is verified, corresponding induction item auto-completes
CARE_CERTIFICATE_STANDARDS = [
    {"id": "understand_your_role", "num": 1, "name": "Understand Your Role", "training_sync": None, "auto_complete": "manual"},
    {"id": "personal_development", "num": 2, "name": "Your Personal Development", "training_sync": None, "auto_complete": "manual"},
    {"id": "duty_of_care", "num": 3, "name": "Duty of Care", "training_sync": None, "auto_complete": "manual"},
    {"id": "equality_diversity", "num": 4, "name": "Equality and Diversity", "training_sync": "equality_diversity", "auto_complete": "training"},
    {"id": "work_person_centred", "num": 5, "name": "Work in a Person-Centred Way", "training_sync": None, "auto_complete": "manual"},
    {"id": "communication", "num": 6, "name": "Communication", "training_sync": None, "auto_complete": "interview"},
    {"id": "privacy_dignity", "num": 7, "name": "Privacy and Dignity", "training_sync": None, "auto_complete": "manual"},
    {"id": "fluids_nutrition", "num": 8, "name": "Fluids and Nutrition", "training_sync": "food_hygiene", "auto_complete": "training"},
    {"id": "awareness_mental_health", "num": 9, "name": "Awareness of Mental Health, Dementia and Learning Disabilities", "training_sync": "mental_health", "auto_complete": "training"},
    {"id": "safeguarding_adults", "num": 10, "name": "Safeguarding Adults", "training_sync": "safeguarding_adults", "auto_complete": "training"},
    {"id": "basic_life_support", "num": 11, "name": "Basic Life Support", "training_sync": "basic_life_support", "auto_complete": "training"},
    {"id": "health_safety", "num": 12, "name": "Health and Safety", "training_sync": "health_safety", "auto_complete": "training"},
    {"id": "handling_information", "num": 13, "name": "Handling Information", "training_sync": "information_governance", "auto_complete": "training"},
    {"id": "infection_control", "num": 14, "name": "Infection Prevention and Control", "training_sync": "infection_control", "auto_complete": "training"},
    {"id": "shadow_shift", "num": 15, "name": "Shadow Shift Completed", "training_sync": None, "auto_complete": "manual"},
]

# Training → Induction Auto-Complete Mapping (P0 CRITICAL)
# When a training is verified, automatically mark the corresponding induction item as complete
TRAINING_TO_INDUCTION_MAP = {
    # Training ID → Induction ID
    "safeguarding_adults": "safeguarding_adults",
    "safeguarding": "safeguarding_adults",
    "manual_handling": None,  # No matching Care Certificate standard for manual handling
    "moving_handling": None,  # No matching Care Certificate standard for manual handling
    "fire_safety": "fire_safety",
    "health_safety": "health_safety",
    "health_and_safety": "health_safety",
    "basic_life_support": "basic_life_support",
    "bls": "basic_life_support",
    "infection_control": "infection_control",
    "infection_prevention": "infection_control",
    "information_governance": "handling_information",
    "gdpr": "handling_information",
    "data_protection": "handling_information",
    "equality_diversity": "equality_diversity",
    "equality_and_diversity": "equality_diversity",
    "food_hygiene": "fluids_nutrition",
    "nutrition": "fluids_nutrition",
    "mental_health": "awareness_mental_health",
    "dementia": "awareness_mental_health",
    "learning_disabilities": "awareness_mental_health",
    "medication_administration": None,  # No direct induction mapping
    "medication_awareness": None,
}

# Documents required for ALL roles
REQUIRED_DOCUMENTS = [
    {"id": "right_to_work", "name": "Right to Work", "requires_stamp": True, "category": "identity"},
    {"id": "dbs", "name": "DBS Certificate", "requires_stamp": True, "category": "safety"},
    {"id": "identity", "name": "Identity Document", "requires_stamp": True, "category": "identity"},
    {"id": "proof_of_address", "name": "Proof of Address", "requires_stamp": True, "min_count": 2, "category": "identity"},
]

# Canonical alias map: maps any legacy/variant requirement_id to the canonical REQUIRED_DOCUMENTS id.
# This is the SINGLE SOURCE OF TRUTH for requirement matching across the application.
# Worker dashboard and unified engine MUST use the same alias set.
DOC_REQUIREMENT_ALIASES: dict[str, str] = {
    # Identity aliases
    "identity_documents": "identity",
    "identity_evidence": "identity",
    "identity_rtw": "identity",
    "passport": "identity",
    "id_document": "identity",
    # Identity extended variants (legacy / upload-slot IDs that must stay in Identity only)
    "proof_of_identity": "identity",     # legacy admin-import ID
    "identity_document": "identity",     # singular form variant
    "identity_evidence_2": "identity",   # numbered upload-slot variant
    "identity_evidence_3": "identity",
    "identity_upload": "identity",       # generic upload-slot variant
    # Right-to-work aliases
    "right_to_work_documents": "right_to_work",
    "right_to_work_evidence": "right_to_work",
    "rtw": "right_to_work",
    # DBS aliases
    "dbs_certificate": "dbs",
    "dbs_evidence": "dbs",
    # Proof-of-address aliases
    "poa": "proof_of_address",
    "address_evidence": "proof_of_address",
    "address_proof": "proof_of_address",  # legacy variant used in drawer / admin imports
}

# Requirement IDs that must NEVER be counted as evidence for a canonical requirement,
# even if they contain the canonical name as a substring.
# These are check-record or verification categories, not uploadable evidence.
# MUST stay in sync with worker_dashboard.py exclude_patterns.
DOC_REQUIREMENT_EXCLUSIONS: frozenset[str] = frozenset({
    # DBS exclusions — check records, not certificate evidence
    "dbs_check", "dbs_status_check", "dbs_update",
    # RTW exclusions — check records, not evidence documents
    "right_to_work_check",
    # Identity exclusions — verification records, not uploadable identity docs
    "identity_check", "identity_verification", "identity_verifications",
    # PoA exclusions — verification records
    "address_check", "address_verification",
})

# Forms required for ALL roles
# Source: "admin" = Admin creates/submits, "worker" = Worker fills via portal
REQUIRED_FORMS = [
    {"id": "interview_record", "name": "Interview Record", "source": "admin"},
    {"id": "staff_health_questionnaire", "name": "Staff Health Questionnaire", "source": "worker"},
    {"id": "staff_personal_info", "name": "Staff Personal Information", "source": "worker"},
    {"id": "hmrc_starter_checklist", "name": "HMRC Starter Checklist", "source": "worker"},
    {"id": "emergency_contacts", "name": "Emergency Contacts", "source": "worker"},
    # Note: equal_opportunities is optional (required: False) - not included in compliance count
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
    "staff_personal_info": "Staff Personal Information",
    "hmrc_starter_checklist": "HMRC Starter Checklist",
    "emergency_contacts": "Emergency Contacts",
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
    
    For CQC audit-readiness, we now also check if the stamp was burned into the document
    (indicated by stamped_file_url being present).
    """
    if not doc:
        return False

    # Hard-reject invalidated, rejected, or amendment-requested documents.
    # A stale verified=True or stamp must not override an active rejection.
    # Check BOTH status and review_status — review_status may be set after the
    # document status was last updated (e.g. admin reviewed but didn't change status).
    _dead_statuses = frozenset((
        "rejected", "amendment_requested", "invalidated",
        "deleted", "superseded", "uploaded_in_error",
    ))
    if (doc.get("status") or "").lower() in _dead_statuses:
        return False
    if (doc.get("review_status") or "").lower() in _dead_statuses:
        return False

    stamp = doc.get("verification_stamp", "")
    status = doc.get("status", "")
    verified_flag = doc.get("verified", False)
    stamped_file_url = doc.get("stamped_file_url")
    
    # Ensure stamp is a string (could be a dict in some cases)
    if isinstance(stamp, dict):
        stamp = stamp.get("type", "") or stamp.get("stamp_type", "") or ""
    if not isinstance(stamp, str):
        stamp = str(stamp) if stamp else ""
    
    # Ensure status is a string
    if isinstance(status, dict):
        status = status.get("status", "") or ""
    if not isinstance(status, str):
        status = str(status) if status else ""
    
    # Must have a valid stamp — only canonical values accepted
    valid_stamps = ["original_seen", "copy_verified", "certified_copy", "online_check", "verified"]
    has_valid_stamp = bool(stamp) and stamp.lower() in valid_stamps
    
    # Check if stamp was actually burned into document (best for CQC)
    has_burned_stamp = bool(stamped_file_url)
    
    # Also check if status indicates verified
    verified_statuses = ["verified", "approved", "active"]
    has_verified_status = status.lower() in verified_statuses if status else False
    
    # For full CQC compliance: has valid stamp AND burned into document
    # But also accept legacy: valid stamp without burn, or verified status
    return (has_valid_stamp and has_burned_stamp) or has_valid_stamp or (has_verified_status and verified_flag)


# =============================================================================
# COMPETENCY CANONICAL RESOLUTION — SINGLE SOURCE OF TRUTH
# =============================================================================

# All status values that mean "this competency is satisfied".
# UCE and WRE MUST both use this set — no inline string comparisons elsewhere.
_COMPETENCY_PASS_STATUSES: frozenset = frozenset({
    "competent",
    "completed",
    "passed",
    "verified",
    "approved",
})

# Canonical competency_type aliases.
# Key = canonical gate key (used in checks/blockers/readiness config).
# Value = list of accepted competency_type values in competency_records.
# Add legacy aliases here; do NOT add new write-side aliases.
_COMPETENCY_TYPE_ALIASES: dict = {
    "medication_competency": ["medication_competency", "medication"],  # "medication" is legacy
    "clinical_competency": ["clinical_competency"],
    "care_certificate": ["care_certificate"],
}


async def get_employee_competency(db, employee_id: str, competency_type: str) -> bool:
    """
    Canonical check: does this employee have a given competency satisfied?

    Resolution order (do NOT change without updating both UCE and WRE):
      1. competency_records  (primary — the Competency tab writes here)
      2. employee_documents  (legacy fallback only — old stamp-based workflow)

    Alias support and status normalisation are both applied at read level.
    New writes should always use the canonical competency_type key.

    Args:
        db: database connection
        employee_id: the employee's string id
        competency_type: canonical gate key, e.g. "medication_competency"

    Returns:
        True if the competency is satisfied, False otherwise.
    """
    aliases = _COMPETENCY_TYPE_ALIASES.get(competency_type, [competency_type])

    # ---- 1. competency_records (PRIMARY) ------------------------------------
    rec = await db.competency_records.find_one({
        "employee_id": employee_id,
        "competency_type": {"$in": aliases},
        "status": {"$in": list(_COMPETENCY_PASS_STATUSES)},
    })
    if rec:
        return True

    # ---- 2. employee_documents (LEGACY FALLBACK) ----------------------------
    docs = await db.employee_documents.find(
        {
            "employee_id": employee_id,
            "requirement_id": {"$in": aliases},
        },
        {"_id": 0},
    ).to_list(20)

    for doc in docs:
        # Hard-reject invalidated / rejected documents
        doc_status = (doc.get("status") or "").lower()
        if doc_status in {"rejected", "amendment_requested", "invalidated",
                          "deleted", "superseded", "uploaded_in_error"}:
            continue
        if doc_status in _COMPETENCY_PASS_STATUSES:
            return True
        if is_document_verified_with_stamp(doc):
            return True

    return False


def normalize_training_name(name: str) -> str:
    """
    Normalize training name for matching purposes.
    Removes special characters (&, /, -, etc.) and extra spaces.
    This ensures "Health & Safety" matches "health safety".
    """
    if not name:
        return ""
    # Convert to lowercase
    name = name.lower()
    # Replace common separators with space
    for char in ['&', '/', '-', ',', '(', ')', ':']:
        name = name.replace(char, ' ')
    # Collapse multiple spaces and strip
    name = ' '.join(name.split())
    return name


def get_induction_item_for_training(training_id: str, training_name: str = None) -> Optional[str]:
    """
    Get the induction item ID that should be auto-completed when a training is verified.
    Uses fuzzy matching if exact match not found.
    
    Returns: induction_item_id or None
    """
    # First try exact match from mapping
    normalized_id = normalize_training_name(training_id)
    
    # Direct mapping lookup
    if training_id in TRAINING_TO_INDUCTION_MAP:
        return TRAINING_TO_INDUCTION_MAP[training_id]
    
    if normalized_id in TRAINING_TO_INDUCTION_MAP:
        return TRAINING_TO_INDUCTION_MAP[normalized_id]
    
    # Try fuzzy matching on training name
    if training_name:
        normalized_name = normalize_training_name(training_name)
        
        # Check each mapping key
        for key, induction_id in TRAINING_TO_INDUCTION_MAP.items():
            normalized_key = normalize_training_name(key)
            if normalized_key in normalized_name or normalized_name in normalized_key:
                return induction_id
    
    return None


async def auto_complete_induction_from_training(
    db,
    employee_id: str,
    training_id: str,
    training_name: str,
    verified_by: str,
    verified_by_name: str = None
) -> dict:
    """
    Auto-complete the corresponding induction item when a training is verified.
    
    P0 CRITICAL: This ensures training verification syncs with induction checklist.
    
    Returns: {auto_completed: bool, induction_item: str, message: str}
    """
    result = {
        "auto_completed": False,
        "induction_item": None,
        "induction_item_name": None,
        "message": "No matching induction item"
    }
    
    # Find matching induction item
    induction_item_id = get_induction_item_for_training(training_id, training_name)
    
    if not induction_item_id:
        return result
    
    # Find the induction item details
    induction_item = next(
        (item for item in CARE_CERTIFICATE_STANDARDS if item["id"] == induction_item_id),
        None
    )
    
    if not induction_item:
        return result
    
    result["induction_item"] = induction_item_id
    result["induction_item_name"] = induction_item["name"]
    
    # Get or create induction checklist for employee
    checklist = await db.induction_checklists.find_one({"employee_id": employee_id})
    
    now = datetime.now(timezone.utc).isoformat()
    
    if not checklist:
        # Create new checklist with this item completed
        completed_items = {
            induction_item_id: {
                "completed": True,
                "completed_at": now,
                "completed_by": verified_by,
                "completed_by_name": verified_by_name or verified_by,
                "auto_completed_from": f"training:{training_id}",
                "training_name": training_name
            }
        }
        
        await db.induction_checklists.insert_one({
            "id": f"induction_{employee_id}",
            "employee_id": employee_id,
            "items": completed_items,
            "total_items": 15,
            "created_at": now,
            "updated_at": now
        })
        
        result["auto_completed"] = True
        result["message"] = f"Created induction checklist and auto-completed '{induction_item['name']}' from {training_name} training"
    else:
        # Update existing checklist
        items = checklist.get("items", [])
        
        # Handle both list and dict formats
        # P0 FIX: items can be a list of objects or a dict keyed by ID
        if isinstance(items, list):
            # Find the item in the list by matching standard number or name
            item_found = False
            for i, item in enumerate(items):
                item_num = item.get("standard_number") or item.get("num")
                item_name = item.get("name", "").lower()
                if (item_num == induction_item.get("num") or 
                    induction_item_id.lower() in item_name or
                    induction_item.get("name", "").lower() in item_name):
                    if item.get("completed") or item.get("status") == "completed":
                        result["message"] = f"Induction item '{induction_item['name']}' already completed"
                        return result
                    # Mark as completed
                    items[i]["completed"] = True
                    items[i]["status"] = "completed"
                    items[i]["completed_at"] = now
                    items[i]["completed_by"] = verified_by
                    items[i]["completed_by_name"] = verified_by_name or verified_by
                    items[i]["auto_completed_from"] = f"training:{training_id}"
                    items[i]["training_name"] = training_name
                    item_found = True
                    break
            
            if not item_found:
                result["message"] = f"Induction item for '{induction_item['name']}' not found in checklist"
                return result
        else:
            # Dict format (legacy)
            if items.get(induction_item_id, {}).get("completed"):
                result["message"] = f"Induction item '{induction_item['name']}' already completed"
                return result
            # Mark as completed
            items[induction_item_id] = {
                "completed": True,
                "completed_at": now,
                "completed_by": verified_by,
                "completed_by_name": verified_by_name or verified_by,
                "auto_completed_from": f"training:{training_id}",
                "training_name": training_name
            }
        
        await db.induction_checklists.update_one(
            {"employee_id": employee_id},
            {
                "$set": {
                    "items": items,
                    "updated_at": now
                }
            }
        )
        
        result["auto_completed"] = True
        result["message"] = f"Auto-completed induction item '{induction_item['name']}' from {training_name} training"
    
    # Log to audit trail
    try:
        await db.audit_logs.insert_one({
            "id": f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "action": "induction_auto_complete",
            "entity_type": "induction_checklist",
            "entity_id": f"induction_{employee_id}",
            "employee_id": employee_id,
            "user_id": verified_by,
            "user_name": verified_by_name,
            "details": {
                "training_id": training_id,
                "training_name": training_name,
                "induction_item_id": induction_item_id,
                "induction_item_name": induction_item["name"],
                "auto_completed": True
            },
            "timestamp": now
        })
    except Exception as e:
        logger.warning(f"Failed to log induction auto-complete audit: {e}")
    
    return result


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
    
    # Get all documents — exclude all dead/invalid statuses and inactive docs.
    # amendment_requested = admin asked for re-upload → not valid evidence
    # invalidated = explicitly voided → not valid evidence
    # review_status rejected/amendment_requested → supersedes a stale status field
    _DEAD_DOC_STATUSES = [
        "deleted", "superseded", "rejected", "amendment_requested",
        "invalidated", "uploaded_in_error", "removed", "archived",
        "misfiled", "moved", "replaced",
    ]
    all_docs = await db.employee_documents.find({
        "employee_id": emp_id,
        "status": {"$nin": _DEAD_DOC_STATUSES},
        "review_status": {"$nin": ["rejected", "amendment_requested", "invalidated"]},
        "$or": [
            {"is_active": True},
            {"is_active": {"$exists": False}},
        ],
    }, {"_id": 0}).to_list(500)
    _REUPLOAD_SIGNAL_STATUSES = [
        "rejected", "amendment_requested", "invalidated", "uploaded_in_error", "superseded",
    ]
    reupload_signal_docs = await db.employee_documents.find({
        "employee_id": emp_id,
        "$or": [
            {"status": {"$in": _REUPLOAD_SIGNAL_STATUSES}},
            {"review_status": {"$in": ["rejected", "amendment_requested", "invalidated"]}},
        ],
    }, {"_id": 0}).to_list(300)
    # Get training records (exclude deleted/superseded)
    all_training = await db.training_records.find({
        "employee_id": emp_id,
        "record_status": {"$nin": ["superseded", "deleted"]},
        "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
    }, {"_id": 0}).to_list(100)
    
    # Get form submissions
    # NOTE: "signed_off" is included — compliance-file endpoint treats it as admin-verified
    # and it must not remain a blocker when the summary already shows it as done.
    all_forms = await db.form_submissions.find({
        "employee_id": emp_id,
        "status": {"$in": ["submitted", "verified", "approved", "signed_off"]}
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
    
    # Get current DBS and RTW checks from dedicated collections.
    # Keep non-verified outcomes too, so UI can show check_in_progress/check_required.
    dbs_check = await db.dbs_checks.find_one(
        {"employee_id": emp_id, "is_current": True}, {"_id": 0}
    )
    rtw_check = await db.rtw_checks.find_one(
        {"employee_id": emp_id, "is_current": True}, {"_id": 0}
    )
    current_proof_doc_ids = {
        doc_id for doc_id in [
            (dbs_check or {}).get("proof_document_id"),
            (rtw_check or {}).get("proof_document_id"),
        ] if doc_id
    }
    
    # Get verification documents (NEW: Smart Verification System)
    verification_docs = await db.verification_documents.find({
        "employee_id": emp_id
    }, {"_id": 0}).to_list(50)
    
    # Build a map of approved verifications keyed by CANONICAL requirement_id.
    # A verification_document may store a legacy/alias requirement_id (e.g. "passport")
    # so resolve it through DOC_REQUIREMENT_ALIASES before indexing.
    approved_verifications = {}
    for vdoc in verification_docs:
        if vdoc.get("verification_approved"):
            raw_req = (vdoc.get("requirement_id") or "").lower().strip()
            canonical_req = DOC_REQUIREMENT_ALIASES.get(raw_req, raw_req)
            if canonical_req:
                approved_verifications[canonical_req] = vdoc
    
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

    def is_proof_role_document(doc: dict) -> bool:
        role = (doc.get("document_role") or "").lower().strip()
        source_type = (doc.get("source_type") or "").lower().strip()
        if role in {"proof", "verification_proof", "check_proof"}:
            return True
        if source_type in {"verification_proof", "check_proof"}:
            return True
        return False
    
    def find_docs_for_requirement(req_id: str) -> List[dict]:
        """Find all documents matching a requirement ID, using canonical aliases."""
        matches = []
        seen_ids: set = set()
        for doc in all_docs:
            if req_id in ("dbs", "right_to_work"):
                doc_id = doc.get("id")
                if is_proof_role_document(doc) or (doc_id and doc_id in current_proof_doc_ids):
                    continue
            raw_req_id = (doc.get("requirement_id") or "").lower().strip()
            if not raw_req_id:
                continue
            # Reject any requirement_id that is an explicit exclusion (check/verification
            # records that share a name prefix with the canonical evidence requirement).
            if raw_req_id in DOC_REQUIREMENT_EXCLUSIONS:
                continue
            doc_type = (doc.get("document_type_name") or "").lower()
            # Resolve via alias map first — exact canonical match
            canonical = DOC_REQUIREMENT_ALIASES.get(raw_req_id, raw_req_id)
            if canonical == req_id:
                doc_id = doc.get("id") or id(doc)
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    matches.append(doc)
                continue
            # Fallback: substring match on raw requirement_id (preserves legacy rows
            # that store partial names like "identity_evidence_2" not in the alias map).
            # Only applies when the raw_req_id is not already mapped to a DIFFERENT canonical.
            raw_canonical = DOC_REQUIREMENT_ALIASES.get(raw_req_id)
            if req_id == "identity" and raw_canonical is None:
                continue
            if "verification" in raw_req_id or "check" in raw_req_id:
                continue
            if raw_canonical is None and req_id in raw_req_id:
                doc_id = doc.get("id") or id(doc)
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    matches.append(doc)
                continue
            # Fallback: document_type_name substring match (for docs missing requirement_id)
            if not raw_req_id and (
                req_id.replace("_", " ") in doc_type
                or req_id.replace("_", "") in doc_type.replace(" ", "")
            ):
                doc_id = doc.get("id") or id(doc)
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    matches.append(doc)
        return matches

    def has_reupload_signal(req_id: str) -> bool:
        """True when requirement has historical rejected/invalidated evidence and no live doc."""
        for doc in reupload_signal_docs:
            if req_id in ("dbs", "right_to_work"):
                doc_id = doc.get("id")
                if is_proof_role_document(doc) or (doc_id and doc_id in current_proof_doc_ids):
                    continue
            raw_req_id = (doc.get("requirement_id") or "").lower().strip()
            if not raw_req_id:
                continue
            if raw_req_id in DOC_REQUIREMENT_EXCLUSIONS:
                continue
            canonical = DOC_REQUIREMENT_ALIASES.get(raw_req_id, raw_req_id)
            if canonical == req_id:
                return True
            raw_canonical = DOC_REQUIREMENT_ALIASES.get(raw_req_id)
            if req_id == "identity" and raw_canonical is None:
                continue
            if "verification" in raw_req_id or "check" in raw_req_id:
                continue
            if raw_canonical is None and req_id in raw_req_id:
                return True
        return False
    
    for doc_req in REQUIRED_DOCUMENTS:
        req_id = doc_req["id"]
        req_name = doc_req["name"]
        requires_stamp = doc_req.get("requires_stamp", True)
        min_count = doc_req.get("min_count", 1)
        
        categories["documents"]["total"] += 1
        
        # Find matching documents
        matching_docs = find_docs_for_requirement(req_id)

        # NEW: Check for approved verification documents FIRST.
        # Guardrail: identity verification alone must not keep Identity in
        # awaiting/verified state when no live identity upload exists.
        has_approved_verification = req_id in approved_verifications
        if req_id == "identity" and len(matching_docs) == 0:
            has_approved_verification = False

        # ── verified_count ───────────────────────────────────────────────────
        # DBS and RTW require a dedicated check record PLUS live evidence.
        # Document stamps alone MUST NOT make these requirements complete —
        # otherwise invalidating a check still shows the requirement as done.
        # For all other requirements: count verified stamps as before.
        if req_id in ("dbs", "right_to_work"):
            _active_check = dbs_check if req_id == "dbs" else rtw_check
            _check_verified = bool(_active_check and (_active_check.get("outcome") == "verified"))
            _has_live_evidence = len(matching_docs) > 0
            # Legacy path: when no formal check record exists at all, accept an
            # admin-verified document (doc.verified=True or status approved/verified).
            # This aligns with the /compliance-file endpoint evidence-row logic.
            # If ANY check record is present (even unverified), it takes priority.
            _dbs_rtw_reject_set = frozenset((
                "rejected", "amendment_requested", "invalidated",
                "deleted", "superseded", "uploaded_in_error",
            ))
            _legacy_doc_verified = (
                _active_check is None
                and any(
                    (doc.get("verified") is True or doc.get("status") in ("approved", "verified"))
                    and (doc.get("status") or "").lower() not in _dbs_rtw_reject_set
                    and (doc.get("review_status") or "").lower() not in _dbs_rtw_reject_set
                    for doc in matching_docs
                )
            )
            verified_count = 1 if (_has_live_evidence and (_check_verified or _legacy_doc_verified)) else 0
        else:
            verified_count = 0
            for doc in matching_docs:
                if is_document_verified_with_stamp(doc):
                    verified_count += 1
            # Approved verifications count for non-check-based requirements
            if has_approved_verification:
                verified_count = max(verified_count, 1)

        # ---------------------------------------------------------------------------
        # PROOF-OF-CHECK REQUIREMENT (single source of truth)
        # DBS Update Service check requires proof evidence on the check record.
        # RTW always requires proof_document_id on the check record.
        # If proof is required but absent the requirement is NOT complete.
        # ---------------------------------------------------------------------------
        _dbs_update_service_methods = {
            "update_service_check",
            "dbs_update_service",
            "dbs_update_service_check",
        }
        _dbs_proof_required = (
            req_id == "dbs"
            and dbs_check is not None
            and dbs_check.get("method", "") in _dbs_update_service_methods
        )
        _rtw_proof_required = req_id == "right_to_work" and rtw_check is not None
        _proof_satisfied = True
        if _dbs_proof_required:
            _proof_satisfied = bool(
                dbs_check.get("proof_document_id")
                or dbs_check.get("evidence_document_id")
            )
        elif _rtw_proof_required:
            _proof_satisfied = bool(rtw_check.get("proof_document_id"))

        is_complete = verified_count >= min_count and _proof_satisfied
        checks[req_id] = is_complete

        # Determine if any matching doc is directly verified (via verify_requirement
        # or verify_all, which write verified=True / status="approved" to
        # employee_documents but NOT to verification_documents).
        # Exclude any doc whose current status OR review_status indicates rejection.
        _reject_statuses = frozenset((
            "rejected", "amendment_requested", "invalidated",
            "deleted", "superseded", "uploaded_in_error",
        ))
        has_verified_docs = any(
            (doc.get("verified") is True or doc.get("status") in ("verified", "approved"))
            and (doc.get("status") or "").lower() not in _reject_statuses
            and (doc.get("review_status") or "").lower() not in _reject_statuses
            for doc in matching_docs
        )

        # ── verification_status (UI label, never stored) ──────────────────────
        # DBS and RTW: status is ONLY determined by the check record + evidence.
        # We deliberately skip has_approved_verification / has_verified_docs for
        # these two — doc stamps alone must not mark them as verified.
        if req_id in ("dbs", "right_to_work"):
            _active_check = dbs_check if req_id == "dbs" else rtw_check
            _check_verified = bool(_active_check and (_active_check.get("outcome") == "verified"))
            if not matching_docs:
                verification_status = "reupload_required" if has_reupload_signal(req_id) else "missing"
            elif _active_check is None and _legacy_doc_verified:
                # Admin verified the document directly; no formal check record yet.
                # Align with compliance-file evidence-row display.
                verification_status = "verified"
            elif _active_check is None:
                verification_status = "check_required"
            elif not _check_verified:
                verification_status = "check_in_progress"
            elif not _proof_satisfied:
                verification_status = "proof_required"
            else:
                verification_status = "verified"
        else:
            if has_approved_verification:
                verification_status = "verified"
            elif has_verified_docs:
                # Identity / PoA / other — docs directly verified
                verification_status = "verified"
            elif len(matching_docs) > 0:
                verification_status = "awaiting_review"
            else:
                verification_status = "reupload_required" if has_reupload_signal(req_id) else "missing"
        
        item_data = {
            "id": req_id,
            "name": get_clear_label(req_id),
            "completed": is_complete,
            "verified_count": verified_count,
            "required_count": min_count,
            "has_upload": len(matching_docs) > 0,
            "requires_stamp": requires_stamp,
            "has_approved_verification": has_approved_verification,
            "verification_status": verification_status,
        }
        
        if include_details:
            item_data["documents"] = matching_docs[:5]  # Limit for response size
        
        categories["documents"]["items"].append(item_data)
        
        if is_complete:
            categories["documents"]["completed"] += 1
        else:
            # Add to blockers with clear label - NEW: Updated messages for verification model
            if has_approved_verification:
                continue  # Should not happen, but skip if approved
            elif verification_status in ("awaiting_review", "check_in_progress", "proof_required"):
                blocker_msg = f"{get_clear_label(req_id)}: {verification_status.replace('_', ' ').title()}"
                severity = "pending"
            elif verification_status in ("check_required", "reupload_required"):
                blocker_msg = f"{get_clear_label(req_id)}: {verification_status.replace('_', ' ').title()}"
                severity = "critical"
            else:
                blocker_msg = f"{get_clear_label(req_id)}: Missing"
                severity = "critical"
            
            blockers.append({
                "id": req_id,
                "gate": req_id,
                "label": get_clear_label(req_id),
                "reason": blocker_msg,
                "category": "documents",
                "has_upload": len(matching_docs) > 0,
                "has_verification": req_id in [v.get("requirement_id") for v in verification_docs],
                "verification_status": verification_status,
                "severity": severity
            })
    
    # ==========================================================================
    # CHECK 2: REFERENCES (2 required)
    # ==========================================================================
    
    def reference_is_verified(reference: Any) -> bool:
        """Return verified status for canonical or legacy reference shapes."""
        if not isinstance(reference, dict):
            return False

        verification = reference.get("verification")
        if not isinstance(verification, dict):
            verification = {}

        return (
            verification.get("status") == "verified"
            or reference.get("verification_status") == "verified"
            or reference.get("verified") is True
            or reference.get("status") == "verified"
        )

    ref1_verified = False
    ref2_verified = False

    if ref_doc:
        ref1_verified = reference_is_verified(ref_doc.get("ref1"))
        ref2_verified = reference_is_verified(ref_doc.get("ref2"))
    else:
        # Legacy fallback when canonical reference document does not exist.
        legacy_references = references if isinstance(references, list) else []
        for idx, ref in enumerate(legacy_references[:2]):
            is_verified = reference_is_verified(ref)
            if idx == 0:
                ref1_verified = is_verified
            else:
                ref2_verified = is_verified

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
    # CHECK 3: MANDATORY TRAINING (8 items)
    # ==========================================================================
    
    # Build training lookup by NORMALIZED name (fixes "Health & Safety" vs "health safety" mismatch)
    training_by_name = {}
    for t in all_training:
        t_name = (t.get("training_name") or t.get("course_name") or "").lower()
        t_type = (t.get("training_type") or "").lower()
        # Only add non-empty keys
        if t_name:
            training_by_name[t_name] = t
        if t_type:
            training_by_name[t_type] = t
        # Also store by normalized name for better matching
        normalized = normalize_training_name(t_name)
        if normalized:
            training_by_name[normalized] = t
    
    verified_training = {}  # Track which trainings are verified (for induction sync)
    
    for training_req in MANDATORY_TRAINING_HCA:
        t_id = training_req["id"]
        t_name = training_req["name"]
        induction_sync_id = training_req.get("induction_sync")
        
        # Find matching training record using normalized names
        matched_training = None
        
        # Generate search terms (normalized)
        search_terms = [
            t_id,
            t_id.replace("_", " "),
            t_id.replace("_", ""),
            normalize_training_name(t_name),
            normalize_training_name(t_id.replace("_", " ")),
        ]
        # Remove duplicates and empty strings
        search_terms = [s for s in dict.fromkeys(search_terms) if s]
        
        for term in search_terms:
            for key, training in training_by_name.items():
                # Skip empty keys
                if not key:
                    continue
                # Normalize the key for comparison
                normalized_key = normalize_training_name(key)
                # Check both directions with normalized comparison
                if term in normalized_key or normalized_key in term:
                    matched_training = training
                    break
                # Also check exact key match
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
    
    # Build induction status map — supports both ID-keyed (UCE-created) and name-keyed (induction.py-created) items
    induction_status_map = {}
    induction_name_map = {}
    for item in induction_items:
        item_id = item.get("id") or item.get("standard_id")
        item_name = (item.get("name") or "").lower().strip()
        is_item_complete = item.get("status") == "completed"
        if item_id:
            induction_status_map[item_id] = is_item_complete
        if item_name:
            induction_name_map[item_name] = is_item_complete
    
    induction_completed_count = 0
    
    for standard in CARE_CERTIFICATE_STANDARDS:
        std_id = standard["id"]
        std_name = standard["name"]
        training_sync = standard.get("training_sync")
        
        # Check if completed in induction record (ID-based, then name-based fallback)
        is_completed = induction_status_map.get(std_id, False)
        if not is_completed:
            is_completed = induction_name_map.get(std_name.lower(), False)
        
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
        
        # Find matching form submission - PREFER VERIFIED forms over just submitted
        # P0 FIX: When multiple forms exist, use the verified one if available
        matched_form = None
        verified_form = None
        submitted_form = None
        
        for form in all_forms:
            form_type = (form.get("form_type") or "").lower()
            if form_id in form_type or form_type in form_id:
                # "signed_off" means the admin has processed and closed the form —
                # the compliance-file endpoint treats this as admin-verified, so align here.
                if form.get("verified") == True or form.get("status") == "signed_off":
                    verified_form = form
                elif form.get("status") in ["submitted", "verified", "approved"]:
                    if submitted_form is None:  # Keep first submitted
                        submitted_form = form
        
        # Prefer verified > submitted
        matched_form = verified_form or submitted_form
        
        # P0 FIX: Form is complete ONLY if verified by admin (not just submitted)
        # Also treat signed_off as admin-verified to align with compliance-file endpoint.
        is_verified = matched_form is not None and (
            matched_form.get("verified") == True
            or matched_form.get("status") == "signed_off"
        )
        is_submitted = matched_form is not None and matched_form.get("status") in ["submitted", "verified", "signed_off"]
        
        checks[form_id] = is_verified
        
        item_data = {
            "id": form_id,
            "name": get_clear_label(form_id),
            "completed": is_verified,
            "submitted": is_submitted,
            "verified": is_verified,
            "source": form_req.get("source"),
            "submitted_at": matched_form.get("submitted_at") if matched_form else None,
            "verified_at": matched_form.get("verified_at") if matched_form else None,
        }
        
        categories["forms"]["items"].append(item_data)
        
        if is_verified:
            categories["forms"]["completed"] += 1
        else:
            # Determine severity based on submission status
            severity = "pending" if is_submitted else "critical"
            reason = f"{get_clear_label(form_id)}: Awaiting verification" if is_submitted else f"{get_clear_label(form_id)}: Not completed"
            blockers.append({
                "id": form_id,
                "gate": form_id,
                "label": get_clear_label(form_id),
                "reason": reason,
                "category": "forms",
                "severity": severity
            })
    
    # ==========================================================================
    # CHECK 6: AGREEMENTS (Contract, Handbook)
    # ==========================================================================
    
    # Contract
    # Check old-format acknowledgements first (agreement_acknowledgements collection)
    contract_ack = None
    for ack in agreements:
        ack_type = (ack.get("agreement_type") or "").lower()
        if "contract" in ack_type:
            if ack.get("status") in ["signed", "submitted", "verified"]:
                contract_ack = ack
                break

    # Fallback: check new-format template submissions (agreement_submissions collection).
    # The compliance-file endpoint reads from this collection; if a contract was
    # completed via the template system it only exists here, not in acknowledgements.
    _CONTRACT_TEMPLATE_IDS = {
        "ZERO_HOUR_CONTRACT_V1",
        "EMPLOYMENT_CONTRACT_V1",
        "CASUAL_WORKER_CONTRACT_V1",
    }
    if not contract_ack:
        _contract_sub = await db.agreement_submissions.find_one(
            {
                "employee_id": emp_id,
                "template_id": {"$in": list(_CONTRACT_TEMPLATE_IDS)},
            },
            {"_id": 0},
        )
        if _contract_sub:
            contract_ack = _contract_sub  # treat as signed

    contract_signed = bool(contract_ack) or employee.get("contract_signed", False)
    checks["contract"] = contract_signed
    
    # Handbook
    # Check legacy acknowledgements first, then template-based submissions.
    handbook_ack = None
    for ack in agreements:
        ack_type = (ack.get("agreement_type") or "").lower()
        if "handbook" in ack_type:
            if ack.get("status") in ["acknowledged", "signed", "submitted"]:
                handbook_ack = ack
                break

    # Fallback: EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1 template submission
    if not handbook_ack:
        _handbook_sub = await db.agreement_submissions.find_one(
            {
                "employee_id": emp_id,
                "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
            },
            {"_id": 0},
        )
        if _handbook_sub:
            handbook_ack = _handbook_sub

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
    if not handbook_acknowledged:
        blockers.append({
            "id": "handbook",
            "gate": "handbook_acknowledged",
            "label": "Employee Handbook",
            "reason": "Employee Handbook: Not acknowledged by worker",
            "category": "agreements",
            "severity": "required"
        })
    
    # ==========================================================================
    # CHECK 7: EMPLOYMENT GAPS (if applicable)
    # ==========================================================================
    
    from employment_gap_engine import evaluate_gaps_compliance

    gap_records = await db.employment_gaps.find(
        {"employee_id": emp_id, "duration_months": {"$gte": 1}},
        {"_id": 0}
    ).to_list(50)
    if not gap_records:
        gap_records = [
            gap for gap in employee.get("employment_gaps", [])
            if gap.get("duration_months", 0) >= 1
        ]

    for gap in gap_records:
        if gap.get("status") == "needs_info":
            gap["status"] = "needs_more_info"
        elif gap.get("status") == "not_explained":
            gap["status"] = "pending"

    gap_evaluation = evaluate_gaps_compliance(gap_records)
    gaps_verified = not gap_evaluation.get("has_gaps", False) or gap_evaluation.get("is_complete", False)

    checks["employment_gaps_explained"] = gaps_verified

    if not gaps_verified:
        gap_count = gap_evaluation.get("total_gaps", len(gap_records))
        blocker_reason = "Employment gaps require verification"
        if gap_evaluation.get("pending_count", 0) > 0:
            blocker_reason = f"{gap_evaluation.get('pending_count')} employment gap(s) require explanation"
        elif gap_evaluation.get("explained_count", 0) > 0:
            blocker_reason = f"{gap_evaluation.get('explained_count')} employment gap explanation(s) awaiting admin verification"
        elif gap_evaluation.get("rejected_count", 0) > 0:
            blocker_reason = f"{gap_evaluation.get('rejected_count')} employment gap explanation(s) rejected"
        elif gap_evaluation.get("needs_info_count", 0) > 0:
            blocker_reason = f"More information requested for {gap_evaluation.get('needs_info_count')} employment gap(s)"
        blockers.append({
            "id": "employment_gaps",
            "gate": "employment_gaps",
            "label": "Employment Gaps",
            "reason": f"Employment Gaps: {blocker_reason}",
            "category": "other",
            "severity": "pending",
            "count": gap_count
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

        # Medication Administration Competency (nurse-specific gate)
        # All resolution logic is delegated to get_employee_competency() — do NOT inline here.
        med_comp_complete = await get_employee_competency(db, emp_id, "medication_competency")
        checks["medication_competency"] = med_comp_complete

        if not med_comp_complete:
            blockers.append({
                "id": "medication_competency",
                "gate": "medication_competency",
                "label": "Medication Administration Competency",
                "reason": "Medication Administration Competency: Not completed or verified",
                "category": "competency",
                "severity": "critical"
            })

        # Clinical Competency Assessment (nurse-specific gate)
        # All resolution logic is delegated to get_employee_competency() — do NOT inline here.
        clin_comp_complete = await get_employee_competency(db, emp_id, "clinical_competency")
        checks["clinical_competency"] = clin_comp_complete

        if not clin_comp_complete:
            blockers.append({
                "id": "clinical_competency",
                "gate": "clinical_competency",
                "label": "Clinical Competency Assessment",
                "reason": "Clinical Competency Assessment: Not completed or verified",
                "category": "competency",
                "severity": "critical"
            })
    
    # ==========================================================================
    # CALCULATE OVERALL PROGRESS
    
    # ==========================================================================
    # CALCULATE OVERALL PROGRESS
    # ==========================================================================
    
    total_requirements = sum(cat["total"] for cat in categories.values())
    completed_requirements = sum(cat["completed"] for cat in categories.values())
    
    # Add nurse-specific requirements to total
    # Nurse = 33 base + 1 (NMC) + 1 (medication_competency) + 1 (clinical_competency) = 36 requirements
    if is_nurse:
        total_requirements += 1  # NMC Registration
        if checks.get("professional_registration"):
            completed_requirements += 1
        total_requirements += 1  # Medication Administration Competency
        if checks.get("medication_competency"):
            completed_requirements += 1
        total_requirements += 1  # Clinical Competency Assessment
        if checks.get("clinical_competency"):
            completed_requirements += 1
    
    overall_percentage = round((completed_requirements / total_requirements) * 100) if total_requirements > 0 else 0
    
    # ==========================================================================
    # DETERMINE PROMOTION ELIGIBILITY
    # ==========================================================================
    
    # is_work_ready = all checks pass (applies to all statuses — ongoing compliance gate)
    is_work_ready = len(blockers) == 0
    
    # can_promote = all checks pass AND employee is still in the recruitment/onboarding pipeline.
    # Active employees who are already promoted must NOT see "Ready for Promotion" again.
    _promotable_statuses = {"applicant", "onboarding"}
    can_promote = is_work_ready and (employee.get("status", "applicant") in _promotable_statuses)
    
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
        "total_gates": 12 + (4 if is_nurse else 0),  # +NMC +indemnity +medication_competency +clinical_competency
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
        "category_details": data.get("category_details"),  # Worker needs this for dashboard sync
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
