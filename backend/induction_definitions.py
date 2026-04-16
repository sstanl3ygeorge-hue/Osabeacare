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
    }, {"_id": 0, "training_name": 1, "requirement_id": 1, "code": 1}).to_list(100)

    training_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$regex": "training|safeguard|fire|manual|infection|health|bls|basic_life"},
        "verification_stamp": {"$nin": [None, "", "not_verified"]}
    }, {"_id": 0, "requirement_id": 1}).to_list(50)

    verified_set = _build_verified_training_set(training_records, training_docs)

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

        # Check stored record (by id, then name, then num)
        record = id_status.get(std_id) or name_status.get(std_name.lower()) or num_status.get(std_num)
        is_completed = record["completed"] if record else False
        completed_at = record.get("completed_at") if record else None
        completed_by = record.get("completed_by_name") if record else None
        synced_from_training = record.get("synced_from_training", False) if record else False

        # Auto-sync: check verified training
        if not is_completed and is_training_verified_for_item(std_name, verified_set):
            is_completed = True
            synced_from_training = True

        if is_completed:
            completed_count += 1

        result_items.append({
            "id": std_id,
            "num": std_num,
            "name": std_name,
            "mandatory": True,
            "status": "completed" if is_completed else "pending",
            "completed": is_completed,
            "completed_at": completed_at,
            "completed_by_name": completed_by,
            "synced_from_training": synced_from_training,
            "training_sync": training_sync,
        })

    if completed_count == INDUCTION_TOTAL:
        overall = "completed"
    elif completed_count > 0:
        overall = "in_progress"
    else:
        overall = "not_started"

    return {
        "employee_id": employee_id,
        "items": result_items,
        "completed": completed_count,
        "total": INDUCTION_TOTAL,
        "overall_status": overall,
        "blocking": completed_count < INDUCTION_TOTAL,
    }
