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

from induction_definitions import (
    CARE_CERTIFICATE_STANDARDS,
    TRAINING_TO_INDUCTION_MAP,
    normalize_training_name,
    get_induction_item_for_training,
    get_employee_induction_status,
)
from agreement_document_service import (
    HANDBOOK_AGREEMENT_TYPE,
    resolve_employee_agreement_state,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS - NHS Employment Check Standards
# =============================================================================

# Mandatory Training for Healthcare Assistants (8 items - P0 CRITICAL)
# NHS Employment Check Standards + CQC Requirements
MANDATORY_TRAINING_HCA = [
    {"id": "safeguarding_adults", "name": "Safeguarding Adults", "induction_sync": "safeguarding_adults"},
    {"id": "manual_handling", "name": "Manual Handling / Moving & Handling", "induction_sync": "health_safety"},
    {"id": "fire_safety", "name": "Fire Safety", "induction_sync": "health_safety"},
    {"id": "health_safety", "name": "Health & Safety", "induction_sync": "health_safety"},
    {"id": "basic_life_support", "name": "Basic Life Support (BLS)", "induction_sync": "basic_life_support"},
    {"id": "infection_control", "name": "Infection Prevention & Control", "induction_sync": "infection_control"},
    # P0 ADDITIONS - Mandatory per NHS/CQC requirements
    {"id": "information_governance", "name": "Information Governance / GDPR / Data Protection", "induction_sync": None},
    {"id": "prevent", "name": "Prevent (Counter-Terrorism Awareness)", "induction_sync": None},
]

# CARE_CERTIFICATE_STANDARDS and TRAINING_TO_INDUCTION_MAP imported from induction_definitions

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

LEGAL_BLOCKER_IDS: frozenset[str] = frozenset({
    "right_to_work",
    "dbs",
    "identity",
    "proof_of_address",
    "reference_1",
    "reference_2",
    "interview_record",
    "staff_health_questionnaire",
    "employment_gaps",
    "induction",
    "mandatory_training",
    "nmc_registration",
    "professional_indemnity",
    "medication_competency",
    "clinical_competency",
})

INTERNAL_BLOCKER_IDS: frozenset[str] = frozenset({
    "contract",
    "handbook",
    "internal_policy_acknowledgement",
})


def get_clear_label(item_id: str) -> str:
    """Get user-friendly label for an item (Easy to Learn - 5 E's)"""
    return CLEAR_LABELS.get(item_id, item_id.replace("_", " ").title())


def _classify_blocker(item_id: str, category: str) -> str:
    """Return the canonical blocker class for readiness/audit surfaces."""
    if item_id in INTERNAL_BLOCKER_IDS or category == "agreements":
        return "internal"
    if item_id in LEGAL_BLOCKER_IDS:
        return "legal"
    return "legal"


# Items that are always the admin's responsibility to progress
# (worker cannot self-serve these — admin must record or verify them).
_ADMIN_OWNED_ITEM_IDS: frozenset[str] = frozenset({
    "interview_record",
    "reference_1",
    "reference_2",
})

# Items that are worker-owned to submit/upload/acknowledge in the first instance.
# When severity is "pending" (submitted, awaiting review), ownership flips to admin.
_WORKER_OWNED_ITEM_IDS: frozenset[str] = frozenset({
    "right_to_work",
    "dbs",
    "identity",
    "proof_of_address",
    "contract",
    "handbook",
    "staff_health_questionnaire",
    "staff_personal_info",
    "hmrc_starter_checklist",
    "emergency_contacts",
    "employment_gaps",
    "induction",
    "mandatory_training",
    "nmc_registration",
    "gmc_registration",
    "professional_indemnity",
    "medication_competency",
    "clinical_competency",
    "information_governance",
    "prevent",
})


def _derive_blocker_owner(item_id: str, category: str, severity: str, reason: str) -> str:
    """
    Derive which party must act to clear this blocker, from existing fields only.

    Returns: "worker" | "admin" | "system"

    Rules (no new truth — pure presentation classification):
    - Handbook/agreement render failures (PDF unavailable because ...) → system
    - Admin-owned items (interview_record, references) → admin
    - Worker-owned items with severity=pending (submitted, awaiting admin review) → admin
    - Worker-owned items otherwise → worker
    - Unknown items fall back to admin (safe default: admin triage).
    """
    reason_lc = (reason or "").lower()
    if "pdf unavailable" in reason_lc or "render" in reason_lc and "blocked" in reason_lc:
        return "system"
    if item_id in _ADMIN_OWNED_ITEM_IDS:
        return "admin"
    if item_id in _WORKER_OWNED_ITEM_IDS:
        return "admin" if severity == "pending" else "worker"
    if category == "documents":
        return "admin" if severity == "pending" else "worker"
    return "admin"


def _build_blocker(
    item_id: str,
    gate: str,
    label: str,
    reason: str,
    category: str,
    severity: str,
    **extra: Any,
) -> dict:
    blocker = {
        "id": item_id,
        "gate": gate,
        "label": label,
        "reason": reason,
        "category": category,
        "severity": severity,
        "blocker_class": _classify_blocker(item_id, category),
        "owner": _derive_blocker_owner(item_id, category, severity, reason),
    }
    blocker.update(extra)
    return blocker


def _blocker_concept_key(blocker: dict) -> str:
    """
    Canonical concept key for blocker de-duplication.

    Health questionnaire can surface under legacy/canonical ids across
    aggregation paths. Collapse these into one operational concept.
    """
    blocker_id = (blocker.get("id") or "").strip().lower()
    gate = (blocker.get("gate") or "").strip().lower()

    if blocker_id in {"staff_health_questionnaire", "health_questionnaire"} or gate in {
        "staff_health_questionnaire",
        "health_questionnaire",
    }:
        return "staff_health_questionnaire"

    # Keep other concepts distinct by gate to avoid hiding separate blockers
    # under the same requirement id.
    return f"{blocker_id}|{gate}"


def _dedupe_blockers(blockers: list[dict]) -> list[dict]:
    """
    Collapse duplicate blocker concepts while preserving the most actionable item.
    """
    if not blockers:
        return blockers

    severity_rank = {"critical": 3, "pending": 2, "warning": 1}
    chosen: dict[str, dict] = {}

    for blocker in blockers:
        key = _blocker_concept_key(blocker)
        existing = chosen.get(key)
        if existing is None:
            chosen[key] = blocker
            continue

        current_reason = str(blocker.get("reason") or "").lower()
        existing_reason = str(existing.get("reason") or "").lower()
        current_score = (
            severity_rank.get(str(blocker.get("severity") or "warning").lower(), 0),
            1 if "health declaration" in current_reason else 0,
            len(current_reason),
        )
        existing_score = (
            severity_rank.get(str(existing.get("severity") or "warning").lower(), 0),
            1 if "health declaration" in existing_reason else 0,
            len(existing_reason),
        )
        if current_score > existing_score:
            chosen[key] = blocker

    return list(chosen.values())


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


# normalize_training_name and get_induction_item_for_training imported from induction_definitions


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
        # Create new checklist in list format (canonical format for all write paths)
        from induction_definitions import CARE_CERTIFICATE_STANDARDS as _STDS
        new_items = []
        for std in _STDS:
            entry = {
                "id": std["id"],
                "name": std["name"],
                "mandatory": True,
                "status": "pending",
                "completed_at": None,
                "completed_by": None,
                "completed_by_name": None,
                "notes": None,
            }
            if std["id"] == induction_item_id:
                entry.update({
                    "status": "completed",
                    "completed": True,
                    "completed_at": now,
                    "completed_by": verified_by,
                    "completed_by_name": verified_by_name or verified_by,
                    "auto_completed_from": f"training:{training_id}",
                    "training_name": training_name,
                })
            new_items.append(entry)

        await db.induction_checklists.insert_one({
            "id": f"induction_{employee_id}",
            "employee_id": employee_id,
            "items": new_items,
            "overall_status": "in_progress",
            "total_items": 15,
            "created_at": now,
            "updated_at": now
        })
        
        result["auto_completed"] = True
        result["message"] = f"Created induction checklist and auto-completed '{induction_item['name']}' from {training_name} training"
    else:
        # Update existing checklist — normalise to list format first
        from induction_definitions import ensure_checklist_list_format
        ensure_checklist_list_format(checklist)
        items = checklist["items"]  # guaranteed list after normalisation

        item_found = False
        for i, item in enumerate(items):
            item_name_lower = item.get("name", "").lower()
            target_lower = induction_item.get("name", "").lower()
            if item.get("id") == induction_item_id or item_name_lower == target_lower:
                if item.get("status") == "completed" or item.get("completed"):
                    result["message"] = f"Induction item '{induction_item['name']}' already completed"
                    return result
                items[i].update({
                    "status": "completed",
                    "completed": True,
                    "completed_at": now,
                    "completed_by": verified_by,
                    "completed_by_name": verified_by_name or verified_by,
                    "auto_completed_from": f"training:{training_id}",
                    "training_name": training_name,
                })
                item_found = True
                break

        if not item_found:
            result["message"] = f"Induction item for '{induction_item['name']}' not found in checklist"
            return result

        # Recalculate overall_status after item update
        completed_count = sum(1 for it in items if it.get("status") == "completed" or it.get("completed"))

        if completed_count >= 15:
            overall_status = "completed"
        elif completed_count > 0:
            overall_status = "in_progress"
        else:
            overall_status = "pending"

        update_fields = {
            "items": items,
            "overall_status": overall_status,
            "updated_at": now
        }
        if overall_status == "completed":
            update_fields["completed_at"] = now

        await db.induction_checklists.update_one(
            {"employee_id": employee_id},
            {"$set": update_fields}
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
        # RTW always requires proof on the check record. The compliance-file
        # workflow accepts either proof_document_id or evidence_document_id, so
        # unified readiness must use the same proof test.
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
            _proof_satisfied = bool(
                rtw_check.get("proof_document_id")
                or rtw_check.get("evidence_document_id")
            )

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
                # Identity / PoA / other — docs directly verified.
                # If min_count > 1 (e.g. Proof of Address requires 2 docs),
                # only mark "verified" when the count requirement is actually met.
                if min_count > 1 and verified_count < min_count:
                    verification_status = "partially_verified"
                else:
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
            elif verification_status == "partially_verified":
                blocker_msg = f"{get_clear_label(req_id)}: {verified_count} of {min_count} verified — {min_count - verified_count} more required"
                severity = "pending"
            elif verification_status in ("check_required", "reupload_required"):
                blocker_msg = f"{get_clear_label(req_id)}: {verification_status.replace('_', ' ').title()}"
                severity = "critical"
            else:
                blocker_msg = f"{get_clear_label(req_id)}: Missing"
                severity = "critical"
            
            blockers.append(_build_blocker(
                req_id,
                req_id,
                get_clear_label(req_id),
                blocker_msg,
                "documents",
                severity,
                has_upload=len(matching_docs) > 0,
                has_verification=req_id in [v.get("requirement_id") for v in verification_docs],
                verification_status=verification_status,
            ))
    
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

    def reference_mismatch_meta(reference: Any, ref_num: int) -> dict:
        reference = reference if isinstance(reference, dict) else {}
        mismatch = reference.get("mismatch")
        if not isinstance(mismatch, dict):
            mismatch = {}

        detected = bool(mismatch.get("detected")) or bool(employee.get(f"reference_{ref_num}_mismatch_detected"))
        kind = str(mismatch.get("kind") or "").strip().lower()
        if not kind:
            notes = " ".join(
                str(v or "")
                for v in [
                    mismatch.get("reason"),
                    mismatch.get("notes"),
                    employee.get(f"reference_{ref_num}_mismatch_notes"),
                ]
            ).lower()
            if "most recent employer" in notes:
                kind = "recent_employer"

        admin_accepted = bool(
            mismatch.get("admin_decision") == "accepted"
            or employee.get(f"reference_{ref_num}_mismatch_admin_decision") == "accepted"
            or employee.get(f"reference_{ref_num}_mismatch_override_reason")
        )
        resolved = bool(mismatch.get("resolved") or admin_accepted)
        unresolved = detected and not resolved
        return {
            "detected": detected,
            "kind": kind,
            "resolved": resolved,
            "unresolved": unresolved,
        }

    def reference_counts_toward(reference: Any, ref_num: int) -> bool:
        if not reference_is_verified(reference):
            return False
        mm = reference_mismatch_meta(reference, ref_num)
        if not mm["unresolved"]:
            return True
        # Unresolved recent-employer mismatch does not invalidate this slot
        # automatically; enforce recent-employer sufficiency at aggregate level.
        if mm["kind"] == "recent_employer":
            return True
        return False

    def reference_satisfies_recent_rule(reference: Any, ref_num: int) -> bool:
        if not reference_counts_toward(reference, ref_num):
            return False
        mm = reference_mismatch_meta(reference, ref_num)
        if mm["kind"] != "recent_employer":
            return True
        return mm["resolved"]

    ref1_verified = False
    ref2_verified = False
    ref1_counts = False
    ref2_counts = False
    ref1_recent_ok = False
    ref2_recent_ok = False

    if ref_doc:
        ref1 = ref_doc.get("ref1")
        ref2 = ref_doc.get("ref2")
        ref1_verified = reference_is_verified(ref1)
        ref2_verified = reference_is_verified(ref2)
        ref1_counts = reference_counts_toward(ref1, 1)
        ref2_counts = reference_counts_toward(ref2, 2)
        ref1_recent_ok = reference_satisfies_recent_rule(ref1, 1)
        ref2_recent_ok = reference_satisfies_recent_rule(ref2, 2)
    else:
        # Legacy fallback when canonical reference document does not exist.
        legacy_references = references if isinstance(references, list) else []
        for idx, ref in enumerate(legacy_references[:2]):
            is_verified = reference_is_verified(ref)
            if idx == 0:
                ref1_verified = is_verified
                ref1_counts = is_verified
                ref1_recent_ok = is_verified
            else:
                ref2_verified = is_verified
                ref2_counts = is_verified
                ref2_recent_ok = is_verified

        if employee.get("reference_1_verified"):
            ref1_verified = True
            ref1_counts = True
            ref1_recent_ok = True
        if employee.get("reference_2_verified"):
            ref2_verified = True
            ref2_counts = True
            ref2_recent_ok = True

    valid_reference_count = (1 if ref1_counts else 0) + (1 if ref2_counts else 0)
    recent_employer_requirement_met = ref1_recent_ok or ref2_recent_ok

    checks["reference_1"] = ref1_counts
    checks["reference_2"] = ref2_counts
    checks["references"] = valid_reference_count >= 2 and recent_employer_requirement_met
    
    categories["references"]["items"] = [
        {"id": "reference_1", "name": "Reference 1", "completed": ref1_counts},
        {"id": "reference_2", "name": "Reference 2", "completed": ref2_counts},
    ]
    categories["references"]["completed"] = valid_reference_count
    
    if not ref1_counts:
        blockers.append(_build_blocker(
            "reference_1",
            "reference_1",
            "Reference 1",
            "Reference 1: Not verified / unresolved mismatch",
            "references",
            "critical",
        ))
    if not ref2_counts:
        blockers.append(_build_blocker(
            "reference_2",
            "reference_2",
            "Reference 2",
            "Reference 2: Not verified / unresolved mismatch",
            "references",
            "critical",
        ))
    if valid_reference_count >= 2 and not recent_employer_requirement_met:
        blockers.append(_build_blocker(
            "references",
            "references",
            "References",
            "At least one reference must cover the most recent employer, or be explicitly accepted by admin",
            "references",
            "pending",
        ))
    
    # ==========================================================================
    # CHECK 3: MANDATORY TRAINING (8 items)
    # ==========================================================================
    
    # Use the same canonical training evaluator as the employee Training tab.
    # This prevents stale legacy name matching from reintroducing blockers that
    # the detailed training matrix has already marked verified/current.
    try:
        from services.training_evaluator import evaluate_employee_training_status

        training_eval = await evaluate_employee_training_status(emp_id, role)
        training_items = training_eval.get("items", [])
        categories["training"]["total"] = len(training_items)
        categories["training"]["completed"] = 0

        for training_item in training_items:
            t_id = training_item.get("code") or ""
            t_name = training_item.get("title") or t_id.replace("_", " ").title()
            status = training_item.get("status")
            is_satisfied = status in {"verified", "due_soon"}
            is_blocking = bool(training_item.get("is_currently_blocking"))

            checks[f"training_{t_id}"] = is_satisfied
            if is_satisfied:
                categories["training"]["completed"] += 1

            categories["training"]["items"].append({
                "id": t_id,
                "name": t_name,
                "completed": is_satisfied,
                "has_record": bool(training_item.get("record_id")),
                "verified": bool(training_item.get("verified")),
                "expiry_date": training_item.get("expires_at"),
                "status": status,
                "invalid_reason": None if is_satisfied else training_item.get("detail"),
            })

            if is_blocking:
                blockers.append(_build_blocker(
                    t_id,
                    "mandatory_training",
                    t_name,
                    training_item.get("detail") or f"{t_name}: Not compliant",
                    "training",
                    "pending" if status in {"awaiting_review", "completed"} else "critical",
                ))

        checks["mandatory_training"] = training_eval.get("blockerCount", 0) == 0
    except Exception as exc:
        categories["training"]["completed"] = 0
        checks["mandatory_training"] = False
        blockers.append(_build_blocker(
            "mandatory_training",
            "mandatory_training",
            "Mandatory Training",
            f"Cannot assess mandatory training: {str(exc)}",
            "training",
            "critical",
        ))
    
    # ==========================================================================
    # CHECK 4: INDUCTION CHECKLIST (15 Care Certificate Standards)
    # Delegates to canonical induction_definitions.get_employee_induction_status()
    # ==========================================================================
    
    induction_status = await get_employee_induction_status(db, emp_id, induction_record=induction_record)
    
    for item in induction_status["items"]:
        categories["induction"]["items"].append({
            "id": item["id"],
            "num": item["num"],
            "name": item["name"],
            "completed": item["completed"],
            "auto_synced": item["synced_from_training"],
            "training_sync": item["training_sync"],
        })
    
    categories["induction"]["completed"] = induction_status["completed"]
    checks["induction"] = not induction_status["blocking"]
    
    if induction_status["blocking"]:
        blockers.append(_build_blocker(
            "induction",
            "induction",
            f"Induction Checklist ({induction_status['completed']}/15 complete)",
            f"Induction: {induction_status['completed']} of 15 Care Certificate standards complete",
            "induction",
            "pending" if induction_status["completed"] > 0 else "critical",
        ))
    
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

        # CQC GATE TIGHTENING: staff_health_questionnaire must also have a
        # reviewed health declaration with an acceptable clinical outcome.
        # A generic "verified form" stamp alone is insufficient: CQC expects
        # an occupational health-style outcome. Require
        # db.health_declarations.status in {"fit", "conditional"} for this
        # employee. Pure read, additive check.
        if form_id == "staff_health_questionnaire" and is_verified:
            health_decl = await db.health_declarations.find_one(
                {"employee_id": emp_id},
                {"_id": 0, "status": 1, "reviewed_at": 1, "reviewed_by": 1},
                sort=[("reviewed_at", -1)],
            )
            decl_status = (health_decl or {}).get("status")
            if decl_status not in ("fit", "conditional"):
                is_verified = False
                # Surface the reason so the blocker appended below is accurate.
                matched_form = matched_form  # unchanged; just preserve original form state
                # Force is_submitted to keep pending severity rather than critical
                # when a declaration exists but isn't yet reviewed.
                if health_decl is None:
                    health_reason = "Health declaration not reviewed"
                else:
                    health_reason = f"Health declaration status '{decl_status or 'unreviewed'}' — requires fit or conditional outcome"
            else:
                health_reason = None
        else:
            health_reason = None

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
            # If this is the health questionnaire and the form was verified but
            # the declaration outcome is not fit/conditional, surface the real
            # reason so admins know a clinical review is still required.
            if form_id == "staff_health_questionnaire" and health_reason:
                reason = f"{get_clear_label(form_id)}: {health_reason}"
                severity = "pending"
            blockers.append(_build_blocker(
                form_id,
                form_id,
                get_clear_label(form_id),
                reason,
                "forms",
                severity,
            ))
    
    # ==========================================================================
    # CHECK 6: AGREEMENTS (Contract, Handbook)
    # ==========================================================================
    
    # Contract
    # Check old-format acknowledgements first (agreement_acknowledgements collection)
    contract_ack = None
    for ack in agreements:
        ack_type = (ack.get("agreement_type") or "").lower()
        if "contract" in ack_type:
            if ack.get("status") in [
                "signed",
                "submitted",
                "verified",
                "awaiting_company_countersignature",
                "fully_executed",
                "rejected",
            ]:
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

    contract_state = (contract_ack or {}).get("contract_state")
    contract_verification_status = (contract_ack or {}).get("verification_status")
    contract_worker_signed = bool(
        (contract_ack or {}).get("worker_signed_contract_pdf_url")
        or (contract_ack or {}).get("worker_signed_at")
        or contract_state == "awaiting_company_countersignature"
        or contract_state == "fully_executed"
    )
    contract_fully_executed = bool(
        contract_state == "fully_executed"
        or contract_verification_status == "verified"
    )
    contract_rejected = bool(contract_verification_status == "rejected")
    checks["contract"] = contract_fully_executed
    
    # Handbook
    handbook_state = await resolve_employee_agreement_state(db, employee, HANDBOOK_AGREEMENT_TYPE)
    handbook_ack = handbook_state.get("acknowledgement") or {}
    handbook_render_issue = handbook_state.get("render_issue")
    handbook_acknowledged = bool(handbook_state.get("worker_acknowledged"))
    handbook_verified = bool(handbook_state.get("verified"))
    handbook_rejected = bool(handbook_state.get("rejected"))
    checks["handbook"] = handbook_verified or handbook_acknowledged

    categories["agreements"]["items"] = [
        {
            "id": "contract",
            "name": "Employment Contract",
            "completed": contract_fully_executed,
            "status": contract_state or ("rejected" if contract_rejected else "awaiting_worker_signature"),
            "worker_signed": contract_worker_signed,
            "awaiting_company_countersignature": contract_state == "awaiting_company_countersignature",
        },
        {
            "id": "handbook",
            "name": "Employee Handbook",
            "completed": checks["handbook"],
            "status": handbook_state.get("status") or ("rejected" if handbook_rejected else ("acknowledged" if handbook_acknowledged else "pending")),
            "render_issue": handbook_render_issue,
        },
    ]
    categories["agreements"]["completed"] = (1 if contract_fully_executed else 0) + (1 if checks["handbook"] else 0)

    if contract_rejected:
        blockers.append(_build_blocker(
            "contract",
            "contract_signed",
            "Employment Contract",
            "Employment Contract: Rejected and reopened for worker signature",
            "agreements",
            "required",
            contract_state=contract_state,
        ))
    elif contract_state == "awaiting_company_countersignature":
        blockers.append(_build_blocker(
            "contract",
            "contract_countersignature",
            "Employment Contract",
            "Employment Contract: Awaiting company countersignature",
            "agreements",
            "required",
            contract_state=contract_state,
        ))
    elif not contract_fully_executed:
        blockers.append(_build_blocker(
            "contract",
            "contract_signed",
            "Employment Contract",
            "Employment Contract: Awaiting worker signature",
            "agreements",
            "critical",
            contract_state=contract_state or "awaiting_worker_signature",
        ))

    if handbook_render_issue and handbook_rejected:
        blockers.append(_build_blocker(
            "handbook",
            "handbook_acknowledged",
            "Employee Handbook",
            f"Employee Handbook: Acknowledgement rejected and PDF unavailable because {handbook_render_issue}",
            "agreements",
            "required",
        ))
    elif handbook_render_issue and not checks["handbook"]:
        blockers.append(_build_blocker(
            "handbook",
            "handbook_render",
            "Employee Handbook",
            f"Employee Handbook: PDF unavailable because {handbook_render_issue}",
            "agreements",
            "required",
        ))
    elif handbook_rejected:
        blockers.append(_build_blocker(
            "handbook",
            "handbook_acknowledged",
            "Employee Handbook",
            "Employee Handbook: Acknowledgement rejected - worker action required",
            "agreements",
            "required",
        ))
    elif not checks["handbook"]:
        blockers.append(_build_blocker(
            "handbook",
            "handbook_acknowledged",
            "Employee Handbook",
            "Employee Handbook: Awaiting worker acknowledgement",
            "agreements",
            "required",
        ))
    
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
        blockers.append(_build_blocker(
            "employment_gaps",
            "employment_gaps",
            "Employment Gaps",
            f"Employment Gaps: {blocker_reason}",
            "other",
            "pending",
            count=gap_count,
        ))
    
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
            blockers.append(_build_blocker(
                "nmc_registration",
                "nmc_registration",
                "NMC Registration",
                "NMC Registration: Not verified or expired",
                "professional",
                "critical",
            ))
        
        # Professional Indemnity Insurance
        indemnity_docs = find_docs_for_requirement("professional_indemnity")
        indemnity_verified = any(is_document_verified_with_stamp(d) for d in indemnity_docs)
        checks["professional_indemnity"] = indemnity_verified
        
        if not indemnity_verified:
            blockers.append(_build_blocker(
                "professional_indemnity",
                "professional_indemnity",
                "Professional Indemnity Insurance",
                "Professional Indemnity Insurance: Not uploaded or verified",
                "professional",
                "critical",
            ))

        # Medication Administration Competency (nurse-specific gate)
        # All resolution logic is delegated to get_employee_competency() — do NOT inline here.
        med_comp_complete = await get_employee_competency(db, emp_id, "medication_competency")
        checks["medication_competency"] = med_comp_complete

        if not med_comp_complete:
            blockers.append(_build_blocker(
                "medication_competency",
                "medication_competency",
                "Medication Administration Competency",
                "Medication Administration Competency: Not completed or verified",
                "competency",
                "critical",
            ))

        # Clinical Competency Assessment (nurse-specific gate)
        # All resolution logic is delegated to get_employee_competency() — do NOT inline here.
        clin_comp_complete = await get_employee_competency(db, emp_id, "clinical_competency")
        checks["clinical_competency"] = clin_comp_complete

        if not clin_comp_complete:
            blockers.append(_build_blocker(
                "clinical_competency",
                "clinical_competency",
                "Clinical Competency Assessment",
                "Clinical Competency Assessment: Not completed or verified",
                "competency",
                "critical",
            ))
    
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
    
    # Collapse duplicate concepts (especially health questionnaire legacy/canonical
    # id variants) before sorting, so operational checklists surface one item.
    blockers = _dedupe_blockers(blockers)

    # Sort blockers by severity (critical first)
    severity_order = {"critical": 0, "pending": 1, "warning": 2}
    blockers.sort(key=lambda b: severity_order.get(b.get("severity", "warning"), 2))
    legal_blockers = [b for b in blockers if b.get("blocker_class") == "legal"]
    internal_blockers = [b for b in blockers if b.get("blocker_class") == "internal"]
    
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
        "legal_blockers": legal_blockers,
        "legal_blocker_count": len(legal_blockers),
        "internal_blockers": internal_blockers,
        "internal_blocker_count": len(internal_blockers),
        
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
            "mandatory_training": {"passed": checks.get("mandatory_training", False), "label": "Mandatory Training (8 items)"},
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
        "legal_blockers": data.get("legal_blockers"),
        "legal_blocker_count": data.get("legal_blocker_count"),
        "internal_blockers": data.get("internal_blockers"),
        "internal_blocker_count": data.get("internal_blocker_count"),
        "categories": data.get("categories"),
        "category_details": data.get("category_details"),  # Worker needs this for dashboard sync
        "is_work_ready": data.get("is_work_ready"),
        # Don't expose detailed checks or internal gates to workers
    }
    return filtered


# =============================================================================
# INDUCTION AUTO-SYNC FUNCTION (DEPRECATED — Stage 2)
# =============================================================================
# This function is no longer called anywhere. Training → induction sync is now
# handled exclusively by auto_complete_induction_from_training() (called on each
# training verification) and the canonical get_employee_induction_status() (read
# path). Retained temporarily for rollback safety; remove in Stage 3.

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
