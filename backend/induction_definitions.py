"""
Canonical induction definitions and status function.

Single source of truth for:
- 15 Care Certificate Standards
- Training → Induction auto-complete mapping
- Induction name → training pattern matching
- Canonical induction status computation
"""

from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# 15 Care Certificate Standards (Adults ONLY)
# =============================================================================
CARE_CERTIFICATE_STANDARDS = [
    {"id": "understand_your_role",    "num": 1,  "name": "Understand Your Role",                                                     "training_sync": None,                    "auto_complete": "manual"},
    {"id": "personal_development",    "num": 2,  "name": "Your Personal Development",                                                "training_sync": None,                    "auto_complete": "manual"},
    {"id": "duty_of_care",            "num": 3,  "name": "Duty of Care",                                                             "training_sync": None,                    "auto_complete": "manual"},
    {"id": "equality_diversity",      "num": 4,  "name": "Equality and Diversity",                                                   "training_sync": "equality_diversity",    "auto_complete": "training"},
    {"id": "work_person_centred",     "num": 5,  "name": "Work in a Person-Centred Way",                                             "training_sync": None,                    "auto_complete": "manual"},
    {"id": "communication",           "num": 6,  "name": "Communication",                                                            "training_sync": None,                    "auto_complete": "interview"},
    {"id": "privacy_dignity",         "num": 7,  "name": "Privacy and Dignity",                                                      "training_sync": None,                    "auto_complete": "manual"},
    {"id": "fluids_nutrition",        "num": 8,  "name": "Fluids and Nutrition",                                                     "training_sync": "food_hygiene",          "auto_complete": "training"},
    {"id": "awareness_mental_health", "num": 9,  "name": "Awareness of Mental Health, Dementia and Learning Disabilities",           "training_sync": "mental_health",         "auto_complete": "training"},
    {"id": "safeguarding_adults",     "num": 10, "name": "Safeguarding Adults",                                                      "training_sync": "safeguarding_adults",   "auto_complete": "training"},
    {"id": "basic_life_support",      "num": 11, "name": "Basic Life Support",                                                       "training_sync": "basic_life_support",    "auto_complete": "training"},
    {"id": "health_safety",           "num": 12, "name": "Health and Safety",                                                        "training_sync": "health_safety",         "auto_complete": "training"},
    {"id": "handling_information",    "num": 13, "name": "Handling Information",                                                     "training_sync": "information_governance","auto_complete": "training"},
    {"id": "infection_control",       "num": 14, "name": "Infection Prevention and Control",                                         "training_sync": "infection_control",     "auto_complete": "training"},
    {"id": "shadow_shift",            "num": 15, "name": "Shadow Shift Completed",                                                   "training_sync": None,                    "auto_complete": "manual"},
]

INDUCTION_TOTAL = 15

# Lookup helpers
_STANDARDS_BY_ID = {s["id"]: s for s in CARE_CERTIFICATE_STANDARDS}
_STANDARDS_BY_NUM = {s["num"]: s for s in CARE_CERTIFICATE_STANDARDS}
_STANDARDS_BY_NAME_LOWER = {s["name"].lower(): s for s in CARE_CERTIFICATE_STANDARDS}

DIRECT_CARE_ROLES = [
    "healthcare_assistant",
    "support_worker",
    "care_assistant",
    "senior_care_assistant",
    "team_leader",
    "nurse",
    "senior_nurse",
]

INDUCTION_RULE_METADATA = {
    "understand_your_role": {
        "description": "Confirms the worker understands their duties, boundaries, supervision route, and role expectations.",
        "completion_type": "hybrid",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "completion_rules": ["Worker must submit a self-assessment form. Admin must sign off."],
        "next_action": "Worker must complete and submit the self-assessment form.",
    },
    "personal_development": {
        "description": "Confirms the worker understands supervision, appraisal, and development expectations.",
        "completion_type": "hybrid",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "completion_rules": ["Worker must submit a self-assessment form. Admin must sign off."],
        "next_action": "Worker must complete and submit the self-assessment form.",
    },
    "duty_of_care": {
        "description": "Confirms the worker understands duty of care, concerns, incidents, and escalation.",
        "completion_type": "hybrid",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "completion_rules": ["Worker must submit a self-assessment form. Admin must sign off."],
        "next_action": "Worker must complete and submit the self-assessment form.",
    },
    "equality_diversity": {
        "description": "Confirms equality, diversity, inclusion, and human rights training is verified.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching training record must exist."],
        "next_action": "Upload, review, and verify matching training evidence.",
    },
    "work_person_centred": {
        "description": "Confirms the worker understands person-centred care and individual preferences.",
        "completion_type": "hybrid",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "completion_rules": ["Worker must submit a self-assessment form. Admin must sign off."],
        "next_action": "Worker must complete and submit the self-assessment form.",
    },
    "communication": {
        "description": "Confirms communication expectations have been discussed and assessed for the role.",
        "completion_type": "hybrid",
        "evidence_sources": ["interview_assessment", "manager_signoff"],
        "completion_rules": ["Interview content can support this item, but manager sign-off is still required until interview rules are fully role-aware."],
        "next_action": "Manager must sign off communication after reviewing interview/application evidence.",
    },
    "privacy_dignity": {
        "description": "Confirms the worker understands privacy, dignity, consent, and respect.",
        "completion_type": "hybrid",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "completion_rules": ["Worker must submit a self-assessment form. Admin must sign off."],
        "next_action": "Worker must complete and submit the self-assessment form.",
    },
    "fluids_nutrition": {
        "description": "Confirms nutrition, hydration, and food safety evidence relevant to care work.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching food hygiene, nutrition, or fluids training record must exist."],
        "next_action": "Upload, review, and verify matching training evidence.",
    },
    "awareness_mental_health": {
        "description": "Confirms awareness of mental health, dementia, and learning disability support.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching mental health, dementia, or learning disability training record must exist."],
        "next_action": "Upload, review, and verify matching training evidence.",
    },
    "safeguarding_adults": {
        "description": "Confirms adult safeguarding training evidence is verified.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching safeguarding adults training record must exist."],
        "next_action": "Upload, review, and verify safeguarding training evidence.",
    },
    "basic_life_support": {
        "description": "Confirms basic life support or equivalent resuscitation evidence is verified.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching basic life support training record must exist."],
        "next_action": "Upload, review, and verify basic life support evidence.",
    },
    "health_safety": {
        "description": "Confirms health and safety training evidence is verified.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching health and safety training record must exist."],
        "next_action": "Upload, review, and verify health and safety evidence.",
    },
    "handling_information": {
        "description": "Confirms information governance, confidentiality, GDPR, or data protection evidence is verified.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching information governance or data protection training record must exist."],
        "next_action": "Upload, review, and verify information governance evidence.",
    },
    "infection_control": {
        "description": "Confirms infection prevention and control training evidence is verified.",
        "completion_type": "automatic",
        "evidence_sources": ["verified_training_record"],
        "completion_rules": ["A verified matching infection prevention and control training record must exist."],
        "next_action": "Upload, review, and verify infection control evidence.",
    },
    "shadow_shift": {
        "description": "Confirms supervised shadowing has been completed and witnessed before unsupervised work.",
        "completion_type": "manual",
        "evidence_sources": ["manager_signoff", "witness_note"],
        "completion_rules": ["Admin must record a supervisor or witness note."],
        "next_action": "Record the shadow shift supervisor/witness note.",
    },
}

# =============================================================================
# Default induction items for creating new checklists (used by write paths)
# =============================================================================
DEFAULT_INDUCTION_ITEMS = [
    {"id": s["id"], "name": s["name"], "mandatory": True, "order": s["num"], "training_link": s.get("training_sync")}
    for s in CARE_CERTIFICATE_STANDARDS
]

# =============================================================================
# Training → Induction Auto-Complete Mapping (P0 CRITICAL)
# When a training is verified, automatically mark the corresponding induction item
# =============================================================================
TRAINING_TO_INDUCTION_MAP = {
    # Training ID → Induction Standard ID
    "safeguarding_adults": "safeguarding_adults",
    "safeguarding": "safeguarding_adults",
    "safeguard_adults": "safeguarding_adults",
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
    # No induction mapping
    "fire_safety": None,
    "manual_handling": None,
    "moving_handling": None,
    "medication_administration": None,
    "medication_awareness": None,
    "prevent": None,
}

# =============================================================================
# Induction item name → training patterns (for name-based matching)
# Canonical merge of all three previously competing maps
# =============================================================================
INDUCTION_NAME_TO_TRAINING_PATTERNS = {
    "safeguarding adults": ["safeguarding", "safeguard", "safeguard_adults", "safeguarding_adults"],
    "basic life support": ["bls", "basic life", "basic_life", "basic_life_support", "resuscitation", "cpr"],
    "health and safety": ["health_safety", "health safety", "health & safety", "h&s", "cstf_health", "health_and_safety"],
    "infection prevention and control": ["infection", "infection control", "infection_control", "infection prevention", "ipc", "cstf_infection"],
    "equality and diversity": ["equality", "diversity", "equality_diversity", "edi", "cstf_equality", "equality_and_diversity"],
    "fluids and nutrition": ["food_hygiene", "food safety", "nutrition", "fluids", "food hygiene"],
    "handling information": ["data_protection", "gdpr", "data protection", "information governance", "ig", "information_governance"],
    "communication": ["communication"],
    "awareness of mental health, dementia and learning disabilities": ["dementia", "mental health", "learning disabilities", "mental_health"],
    "shadow shift completed": ["shadow shift", "shadow_shift", "shadowing"],
}


# =============================================================================
# Pure helper functions
# =============================================================================

def normalize_training_name(name: str) -> str:
    """Normalize a training name for fuzzy matching."""
    name = name.lower().strip()
    for char in ['&', '/', '-', ',', '(', ')', ':']:
        name = name.replace(char, ' ')
    return ' '.join(name.split())


def normalize_role_for_induction(role: str) -> str:
    """Normalize employee role names for induction applicability rules."""
    value = (role or "").lower().strip()
    value = value.replace("&", "and").replace("/", " ")
    value = " ".join(value.replace("-", " ").replace("_", " ").split())

    if not value:
        return "unknown"
    if "nurse" in value:
        return "senior_nurse" if any(term in value for term in ["senior", "lead", "manager"]) else "nurse"
    if any(term in value for term in ["healthcare assistant", "health care assistant", "hca"]):
        return "healthcare_assistant"
    if "support worker" in value:
        return "support_worker"
    if "care assistant" in value:
        return "senior_care_assistant" if "senior" in value else "care_assistant"
    if any(term in value for term in ["team leader", "support lead", "senior support"]):
        return "team_leader"
    return value.replace(" ", "_")


def get_induction_rule_metadata(item_id: str) -> dict:
    """Return rule metadata for an induction item."""
    meta = INDUCTION_RULE_METADATA.get(item_id, {})
    return {
        "description": meta.get("description") or "Induction requirement for this role.",
        "applicable_roles": meta.get("applicable_roles") or DIRECT_CARE_ROLES,
        "required_for_unsupervised_work": meta.get("required_for_unsupervised_work", True),
        "completion_type": meta.get("completion_type") or "manual",
        "evidence_sources": meta.get("evidence_sources") or ["manager_signoff"],
        "completion_rules": meta.get("completion_rules") or ["Admin sign-off is required."],
        "next_action": meta.get("next_action") or "Admin review is required.",
    }


def get_induction_rule_metadata_by_name(item_name: str) -> dict:
    """Return rule metadata by display name for write-path validation."""
    standard = _STANDARDS_BY_NAME_LOWER.get((item_name or "").lower().strip())
    if not standard:
        return {}
    return get_induction_rule_metadata(standard["id"])


def get_induction_item_for_training(training_id: str, training_name: str = None) -> Optional[str]:
    """
    Get the induction item ID that should be auto-completed when a training is verified.
    Returns: induction standard ID or None.
    """
    normalized_id = normalize_training_name(training_id)

    if training_id in TRAINING_TO_INDUCTION_MAP:
        return TRAINING_TO_INDUCTION_MAP[training_id]

    if normalized_id in TRAINING_TO_INDUCTION_MAP:
        return TRAINING_TO_INDUCTION_MAP[normalized_id]

    if training_name:
        normalized_name = normalize_training_name(training_name)
        for key, induction_id in TRAINING_TO_INDUCTION_MAP.items():
            normalized_key = normalize_training_name(key)
            if normalized_key in normalized_name or normalized_name in normalized_key:
                return induction_id

    return None


def ensure_checklist_list_format(checklist: dict) -> dict:
    """
    Ensure a checklist document has its ``items`` field in list format.

    Some records were historically created by unified_compliance_engine with
    items as a dict keyed by standard ID::

        {"understand_your_role": {"completed": True, ...}, ...}

    This function converts that to the canonical list format expected by all
    write paths::

        [{"id": "understand_your_role", "name": "...", "status": "completed", ...}]

    Safe to call on already-list-format records (no-op).
    Returns the same dict object (mutated in place) for convenience.
    """
    items = checklist.get("items", [])
    if isinstance(items, dict):
        checklist["items"] = normalize_induction_items(items)
    return checklist


def normalize_induction_items(raw_items) -> list:
    """
    Normalize both list-format and dict-format induction items to a canonical list.

    List format (induction.py-created):
        [{id, name, status, completed_at, completed_by_name, ...}]
    Dict format (UCE auto-complete-created):
        {item_id: {completed: bool, completed_at, completed_by, ...}}

    Returns: list of normalized items keyed by standard ID.
    """
    if not raw_items:
        return []

    if isinstance(raw_items, dict):
        normalized = []
        for item_id, item_data in raw_items.items():
            if not isinstance(item_data, dict):
                continue
            std = _STANDARDS_BY_ID.get(item_id)
            is_complete = bool(item_data.get("completed"))
            normalized.append({
                "id": item_id,
                "num": std["num"] if std else None,
                "name": std["name"] if std else item_id.replace("_", " ").title(),
                "mandatory": True,
                "status": "completed" if is_complete else "pending",
                "completed": is_complete,
                "completed_at": item_data.get("completed_at"),
                "completed_by_name": item_data.get("completed_by_name") or item_data.get("completed_by"),
                "completed_by": item_data.get("completed_by"),
                "notes": item_data.get("notes"),
                "shadow_shift_signoff": item_data.get("shadow_shift_signoff"),
                "auto_completed_from": item_data.get("auto_completed_from"),
            })
        return normalized

    if isinstance(raw_items, list):
        normalized = []
        for item in raw_items:
            item_id = item.get("id") or item.get("standard_id")
            if not item_id:
                # Derive ID from name
                item_id = (item.get("name") or "").lower().replace(" ", "_").replace(",", "").replace("&", "and")
            is_complete = item.get("status") == "completed" or item.get("completed") is True
            std = _STANDARDS_BY_ID.get(item_id)
            normalized.append({
                "id": item_id,
                "num": item.get("standard_number") or item.get("num") or (std["num"] if std else None),
                "name": item.get("name") or (std["name"] if std else item_id),
                "mandatory": item.get("mandatory", True),
                "status": "completed" if is_complete else "pending",
                "completed": is_complete,
                "completed_at": item.get("completed_at"),
                "completed_by_name": item.get("completed_by_name"),
                "completed_by": item.get("completed_by"),
                "notes": item.get("notes"),
                "shadow_shift_signoff": item.get("shadow_shift_signoff"),
                "auto_completed_from": item.get("auto_completed_from"),
                "synced_from_training": item.get("synced_from_training", False),
            })
        return normalized

    return []


def _build_verified_training_set(training_records: list, training_docs: list = None) -> set:
    """Build a set of lowercase training names/codes from verified records."""
    verified = set()
    for tr in (training_records or []):
        name = (tr.get("training_name") or "").lower()
        code = (tr.get("code") or tr.get("requirement_id") or "").lower()
        if name:
            verified.add(name)
        if code:
            verified.add(code)

    for doc in (training_docs or []):
        req_id = (doc.get("requirement_id") or "").lower()
        if not req_id:
            continue
        verified.add(req_id)
        # Add common aliases for stamped training docs
        if "safeguard" in req_id:
            verified.update(["safeguarding adults", "safeguarding"])
        if "fire" in req_id:
            verified.add("fire safety")
        if "manual" in req_id or "moving" in req_id:
            verified.update(["moving & handling", "manual handling"])
        if "infection" in req_id:
            verified.update(["infection prevention & control", "infection control"])
        if "health" in req_id and "safety" in req_id:
            verified.add("health & safety")
        if "bls" in req_id or "basic_life" in req_id:
            verified.add("basic life support")

    return verified


def _build_training_evidence_by_induction(training_records: list, training_docs: list = None) -> dict:
    """Build linked evidence records keyed by induction item id.

    Each evidence entry includes:
        id, title, code, document_id, view_route,
        source, source_label,
        file_name, document_type,
        verified, verified_at, verified_by,
        uploaded_at
    """
    evidence_by_item = {}

    def _source_label(source: str) -> str:
        return {
            "worker_submission": "Worker submission",
            "admin_upload": "Admin upload",
            "application_upload": "Application upload",
            "training_record": "Training record",
            "training_document": "Training document",
            "hr_upload": "HR upload",
        }.get((source or "").lower(), source.replace("_", " ").title() if source else "Verified record")

    for tr in (training_records or []):
        training_name = tr.get("training_name") or tr.get("name") or ""
        training_code = tr.get("code") or tr.get("requirement_id") or training_name
        induction_id = get_induction_item_for_training(training_code, training_name)
        if not induction_id:
            continue
        doc_id = tr.get("source_document_id") or tr.get("certificate_document_id") or tr.get("document_id")
        raw_source = tr.get("upload_source") or tr.get("source") or "training_record"
        evidence_by_item.setdefault(induction_id, []).append({
            "type": "training_record",
            "id": tr.get("id") or tr.get("training_id") or tr.get("record_id"),
            "title": training_name or training_code,
            "code": training_code,
            "document_id": doc_id,
            "view_route": f"/employee-documents/{doc_id}/file" if doc_id else None,
            "source": "training_record",
            "source_label": _source_label(raw_source),
            "document_type": "training_certificate",
            "file_name": tr.get("original_filename") or tr.get("file_name"),
            "verified": True,
            "verified_at": tr.get("verified_at") or tr.get("updated_at"),
            "verified_by": tr.get("verified_by_name") or tr.get("verified_by"),
            "uploaded_at": tr.get("created_at") or tr.get("updated_at"),
        })

    for doc in (training_docs or []):
        req_id = doc.get("requirement_id") or ""
        title = doc.get("file_name") or doc.get("original_filename") or doc.get("document_name") or req_id
        induction_id = get_induction_item_for_training(req_id, title)
        if not induction_id:
            continue
        doc_id = doc.get("id") or doc.get("file_id") or doc.get("document_id")
        raw_source = doc.get("upload_source") or doc.get("source") or "admin_upload"
        evidence_by_item.setdefault(induction_id, []).append({
            "type": "training_document",
            "id": doc_id,
            "title": title,
            "code": req_id,
            "document_id": doc_id,
            "view_route": f"/employee-documents/{doc_id}/file" if doc_id else None,
            "source": raw_source,
            "source_label": _source_label(raw_source),
            "document_type": "training_document",
            "file_name": doc.get("original_filename") or doc.get("file_name"),
            "verified": True,
            "verified_at": doc.get("verified_at") or doc.get("updated_at"),
            "verified_by": doc.get("verified_by_name") or doc.get("verified_by"),
            "uploaded_at": doc.get("uploaded_at") or doc.get("created_at") or doc.get("updated_at"),
        })

    return evidence_by_item


def is_training_verified_for_item(item_name: str, verified_set: set) -> bool:
    """Check if a verified training matches the given induction item name."""
    item_lower = item_name.lower().strip()

    if item_lower in verified_set:
        return True

    patterns = INDUCTION_NAME_TO_TRAINING_PATTERNS.get(item_lower, [])
    for pattern in patterns:
        p_lower = pattern.lower()
        if p_lower in verified_set:
            return True
        for v_name in verified_set:
            if p_lower in v_name or v_name in p_lower:
                return True

    return False


# =============================================================================
# Canonical induction status function
# =============================================================================

async def get_employee_induction_status(
    db,
    employee_id: str,
    induction_record: dict = None,
) -> dict:
    """
    Canonical induction status for an employee.

    Reads the stored induction_checklists record and merges with verified
    training data to compute the authoritative status.

    Args:
        db: Database instance
        employee_id: Employee ID
        induction_record: Pre-fetched induction checklist doc (optional, fetched if None)

    Returns:
        {
            "employee_id": str,
            "items": [{id, num, name, mandatory, status, completed, completed_at,
                        completed_by_name, synced_from_training, training_sync}],
            "completed": int,
            "total": 15,
            "overall_status": "not_started" | "in_progress" | "completed",
            "blocking": bool,
        }
    """
    employee = await db.employees.find_one(
        {"id": employee_id},
        {"_id": 0, "role": 1, "role_applied": 1, "job_role": 1, "position": 1}
    )
    employee_role = (
        (employee or {}).get("role")
        or (employee or {}).get("role_applied")
        or (employee or {}).get("job_role")
        or (employee or {}).get("position")
        or ""
    )
    normalized_role = normalize_role_for_induction(employee_role)
    role_unknown = normalized_role == "unknown"

    # Fetch induction record if not pre-fetched
    if induction_record is None:
        induction_record = await db.induction_checklists.find_one(
            {"employee_id": employee_id}, {"_id": 0}
        )

    # Fetch verified training records
    training_records = await db.training_records.find({
        "employee_id": employee_id,
        "verified": True,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {
        "_id": 0,
        "id": 1,
        "training_id": 1,
        "record_id": 1,
        "training_name": 1,
        "name": 1,
        "requirement_id": 1,
        "code": 1,
        "verified_at": 1,
        "verified_by": 1,
        "verified_by_name": 1,
        "updated_at": 1,
        "created_at": 1,
        "source_document_id": 1,
        "certificate_document_id": 1,
        "document_id": 1,
        "file_name": 1,
        "original_filename": 1,
        "source": 1,
        "upload_source": 1,
    }).to_list(100)

    training_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$regex": "training|safeguard|fire|manual|infection|health|bls|basic_life"},
        "verification_stamp": {"$nin": [None, "", "not_verified"]}
    }, {
        "_id": 0,
        "id": 1,
        "file_id": 1,
        "document_id": 1,
        "file_name": 1,
        "original_filename": 1,
        "document_name": 1,
        "requirement_id": 1,
        "verified_at": 1,
        "verified_by": 1,
        "verified_by_name": 1,
        "updated_at": 1,
        "created_at": 1,
        "uploaded_at": 1,
        "source": 1,
        "upload_source": 1,
        "uploaded_by_name": 1,
    }).to_list(50)

    verified_set = _build_verified_training_set(training_records, training_docs)
    training_evidence_by_item = _build_training_evidence_by_induction(training_records, training_docs)

    # Normalize stored items
    raw_items = induction_record.get("items", []) if induction_record else []
    stored = normalize_induction_items(raw_items)

    # Build lookup maps from stored items
    id_status = {item["id"]: item for item in stored}
    name_status = {item["name"].lower().strip(): item for item in stored}
    num_status = {item["num"]: item for item in stored if item.get("num")}

    # Build final status for each of the 15 standards
    result_items = []
    completed_count = 0

    for standard in CARE_CERTIFICATE_STANDARDS:
        std_id = standard["id"]
        std_name = standard["name"]
        std_num = standard["num"]
        training_sync = standard.get("training_sync")
        rule = get_induction_rule_metadata(std_id)

        applicable_roles = rule["applicable_roles"]
        is_applicable = role_unknown or normalized_role in applicable_roles
        if not is_applicable:
            continue

        # Check stored record (by id, then name, then num)
        record = id_status.get(std_id) or name_status.get(std_name.lower()) or num_status.get(std_num)
        manually_completed = record["completed"] if record else False
        completed_at = record.get("completed_at") if record else None
        completed_by = record.get("completed_by_name") if record else None
        notes = record.get("notes") if record else None
        shadow_shift_signoff = record.get("shadow_shift_signoff") if record else None
        synced_from_training = record.get("synced_from_training", False) if record else False
        linked_evidence = training_evidence_by_item.get(std_id, [])
        has_verified_training = bool(linked_evidence) or is_training_verified_for_item(std_name, verified_set)
        completion_type = rule["completion_type"]

        is_completed = manually_completed
        rule_status = "incomplete"
        status_reason = rule["next_action"]
        completion_reason = None

        if completion_type == "automatic":
            is_completed = has_verified_training
            synced_from_training = has_verified_training
            if is_completed:
                rule_status = "complete"
                first_evidence = linked_evidence[0] if linked_evidence else {}
                completed_at = completed_at or first_evidence.get("verified_at")
                completed_by = completed_by or first_evidence.get("verified_by") or "Verified training record"
                completion_reason = "Completed automatically from verified training evidence."
                status_reason = completion_reason
            else:
                status_reason = "No verified matching training evidence is on file."
        elif completion_type == "hybrid":
            if manually_completed:
                rule_status = "complete"
                completion_reason = "Completed by manager sign-off after supporting evidence review."
                status_reason = completion_reason
            elif has_verified_training:
                rule_status = "pending_review"
                synced_from_training = True
                status_reason = "Supporting evidence exists, but manager sign-off is still required."
            else:
                status_reason = rule["next_action"]
        else:
            if manually_completed:
                rule_status = "complete"
                if std_id == "shadow_shift":
                    completion_reason = "Shadow shift signed off by manager."
                else:
                    completion_reason = "Completed by manager sign-off."
                status_reason = completion_reason
            elif std_id == "shadow_shift" and shadow_shift_signoff:
                rule_status = "pending_review"
                status_reason = "Shadow shift was recorded, but follow-up is required before sign-off."

        # Backward-compatible auto-sync guard for older training-linked manual data.
        if completion_type == "automatic" and not manually_completed and has_verified_training:
            is_completed = True
            synced_from_training = True

        if is_completed:
            completed_count += 1

        result_items.append({
            "id": std_id,
            "code": std_id,
            "num": std_num,
            "name": std_name,
            "title": std_name,
            "description": rule["description"],
            "mandatory": True,
            "applicable_roles": applicable_roles,
            "role_relevance": "Applies to this employee role" if not role_unknown else "Role unavailable; using direct-care induction rules",
            "required_for_unsupervised_work": rule["required_for_unsupervised_work"],
            "completion_type": completion_type,
            "evidence_sources": rule["evidence_sources"],
            "completion_rules": rule["completion_rules"],
            "rule_status": rule_status,
            "completion_reason": completion_reason,
            "status_reason": status_reason,
            "next_action": None if is_completed else rule["next_action"],
            "linked_evidence_ids": [e.get("id") for e in linked_evidence if e.get("id")],
            "linked_evidence": linked_evidence,
            "status": "completed" if is_completed else "pending",
            "completed": is_completed,
            "completed_at": completed_at,
            "completed_by_name": completed_by,
            "notes": notes,
            "shadow_shift_signoff": shadow_shift_signoff,
            "synced_from_training": synced_from_training,
            "training_sync": training_sync,
            "manual_action_allowed": completion_type in ["manual", "hybrid"],
        })

    total_count = len(result_items)
    if total_count and completed_count == total_count:
        overall = "completed"
    elif completed_count > 0:
        overall = "in_progress"
    else:
        overall = "not_started"

    return {
        "employee_id": employee_id,
        "role": employee_role,
        "role_normalized": normalized_role,
        "role_rule_warning": "Employee role is missing or not mapped; direct-care induction rules are shown by default." if role_unknown else None,
        "rule_todos": [
            "Interview and form question sets are not fully role-aware yet; communication remains manager sign-off supported by interview evidence.",
        ],
        "items": result_items,
        "completed": completed_count,
        "total": total_count,
        "overall_status": overall,
        "blocking": completed_count < total_count,
    }
