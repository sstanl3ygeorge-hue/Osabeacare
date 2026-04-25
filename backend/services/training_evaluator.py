"""
Canonical Training Evaluator — Single Source of Truth.

All training-status computation, validity/expiry logic, and blocker
configuration lives here.  Async functions that need the database use
a module-level ``_db`` reference injected via ``set_db()``.

Functions that need ``MANDATORY_ITEMS`` or role-normalisation helpers
import them lazily from ``server`` to avoid circular imports.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging
import re
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database handle — injected once at startup by server.py
# ---------------------------------------------------------------------------
_db = None


def set_db(db_instance):
    """Inject the Motor database handle (called once from server.py startup)."""
    global _db
    _db = db_instance


def _get_db():
    if _db is None:
        raise RuntimeError("training_evaluator.set_db() has not been called")
    return _db


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXPIRY_WARNING_DAYS = 30  # Show "Expiring Soon" when within 30 days
TEMP_INTERNAL_EVIDENCE_VALIDITY_DAYS = 90

TRAINING_VALIDITY_PERIODS = {
    "safeguarding": 365,
    "safeguarding_of_vulnerable_adults": 365,
    "moving_and_handling": 365,
    "manual_handling": 365,
    "health_and_safety": 365,
    "infection_control": 365,
    "infection_control_and_hygiene": 365,
    "medication_administration": 365,
    "food_hygiene_nutrition_and_hydration": 365,
    "food_hygiene": 365,
    "first_aid_awareness": 1095,  # 3 years
    "first_aid": 1095,
    "fire_safety": 365,
    "covid_19": 365,
    "default": 365,  # Default to annual
}

TRAINING_BLOCKER_CONFIG = {
    "safeguarding": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "safeguarding_training_missing",
        "reason_message": "Safeguarding training required",
    },
    "manual_handling": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "manual_handling_training_missing",
        "reason_message": "Manual Handling training required",
    },
    "moving_and_handling": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "moving_handling_training_missing",
        "reason_message": "Moving and Handling training required",
    },
    "medication_administration": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "medication_training_missing",
        "reason_message": "Medication training required",
    },
    "infection_control": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "infection_control_training_missing",
        "reason_message": "Infection Control training required",
    },
    "bls": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "bls_training_missing",
        "reason_message": "Basic Life Support training required",
    },
    "basic_life_support": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "bls_training_missing",
        "reason_message": "Basic Life Support training required",
    },
    "fire_safety": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "fire_safety_training_missing",
        "reason_message": "Fire Safety training required",
    },
    "health_safety": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "health_safety_training_missing",
        "reason_message": "Health & Safety training required",
    },
    "information_governance": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "information_governance_training_missing",
        "reason_message": "Information Governance / GDPR training required",
    },
    "prevent": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "prevent_training_missing",
        "reason_message": "Prevent (Counter-Terrorism Awareness) training required",
    },
    "news2_clinical_observations": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "news2_clinical_observations_missing",
        "reason_message": "NEWS2 / Clinical Observations training required",
    },
    "sepsis_awareness": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "sepsis_awareness_training_missing",
        "reason_message": "Sepsis Awareness training required",
    },
    "pressure_ulcer_prevention": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "pressure_ulcer_prevention_training_missing",
        "reason_message": "Pressure Ulcer Prevention training required",
    },
    "enhanced_infection_prevention": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "enhanced_infection_prevention_training_missing",
        "reason_message": "Enhanced Infection Prevention / Clinical IPC training required",
    },
    "mca_dols": {
        "blocker_for_work": True,
        "evidence_required": True,
        "reason_code": "mca_dols_training_missing",
        "reason_message": "MCA / DoLS training required",
    },
}


NURSE_EFFECTIVE_REQUIRED_TRAININGS = [
    {
        "id": "medication_administration",
        "name": "Medication Administration Training",
        "type": "training",
        "training_name": "Medication Administration",
        "mandatory_for_compliance": True,
    },
    {
        "id": "news2_clinical_observations",
        "name": "NEWS2 / Clinical Observations",
        "type": "training",
        "training_name": "NEWS2 / Clinical Observations",
        "mandatory_for_compliance": True,
    },
    {
        "id": "sepsis_awareness",
        "name": "Sepsis Awareness",
        "type": "training",
        "training_name": "Sepsis Awareness",
        "mandatory_for_compliance": True,
    },
    {
        "id": "pressure_ulcer_prevention",
        "name": "Pressure Ulcer Prevention",
        "type": "training",
        "training_name": "Pressure Ulcer Prevention",
        "mandatory_for_compliance": True,
    },
    {
        "id": "mca_dols",
        "name": "MCA & DoLS Training",
        "type": "training",
        "training_name": "MCA and DoLs",
        "mandatory_for_compliance": True,
    },
    {
        "id": "enhanced_infection_prevention",
        "name": "Enhanced Infection Prevention / Clinical IPC",
        "type": "training",
        "training_name": "Enhanced Infection Prevention / Clinical IPC",
        "mandatory_for_compliance": True,
    },
]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def get_training_validity_days(requirement_id: str) -> int:
    """Get validity period in days for a training requirement."""
    req_lower = requirement_id.lower().replace(" ", "_").replace("-", "_")
    return TRAINING_VALIDITY_PERIODS.get(req_lower, TRAINING_VALIDITY_PERIODS["default"])


def calculate_training_expiry(completion_date: str, requirement_id: str) -> str:
    """Calculate expiry date based on completion date and requirement validity period."""
    validity_days = get_training_validity_days(requirement_id)
    completion = (
        datetime.fromisoformat(completion_date.replace("Z", "+00:00"))
        if "T" in completion_date
        else datetime.strptime(completion_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    )
    expiry = completion + timedelta(days=validity_days)
    return expiry.strftime("%Y-%m-%d")


def normalize_date_only(date_value) -> Optional[str]:
    """Normalize a date value to YYYY-MM-DD format."""
    if not date_value:
        return None
    if isinstance(date_value, str):
        if len(date_value) == 10 and date_value[4] == "-" and date_value[7] == "-":
            return date_value
        if "T" in date_value:
            return date_value.split("T")[0]
        try:
            dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return date_value


def _parse_iso_or_date(date_value):
    """Parse YYYY-MM-DD or ISO datetime into an aware UTC datetime."""
    if not date_value:
        return None
    if isinstance(date_value, datetime):
        return date_value if date_value.tzinfo else date_value.replace(tzinfo=timezone.utc)
    if isinstance(date_value, str):
        if "T" in date_value:
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        return datetime.strptime(date_value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return None


def _format_date_only(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _is_external_certificate_evidence(record: dict) -> bool:
    """Return True when the training evidence is from an external certificate path."""
    source_type = (record.get("source_type") or "").strip().lower()
    completion_method = (record.get("completion_method") or "").strip().lower()

    if completion_method == "certificate":
        return True
    if record.get("certificate_url"):
        return True
    if record.get("source_document_id") or record.get("certificate_document_id"):
        return True
    return source_type in {"certificate", "certificate_extraction", "replacement", "migrated"}


def _is_internal_temporary_evidence(record: dict) -> bool:
    """Return True when evidence is internal/questionnaire/manual and should be temporary."""
    source_type = (record.get("source_type") or "").strip().lower()
    completion_method = (record.get("completion_method") or "").strip().lower()

    if source_type in {"form_submission", "structured_form"}:
        return True
    if completion_method == "manual":
        return True
    # Fallback: if not certificate-backed but marked completed, treat as temporary.
    return not _is_external_certificate_evidence(record)


def _resolve_effective_expiry_date(record: dict) -> Optional[str]:
    """Resolve expiry policy by evidence type.

    - Internal course/questionnaire evidence: max 90 days from completion.
    - External certificate evidence: normal training expiry policy.
    """
    completion_date = record.get("completion_date")
    if not completion_date:
        return record.get("expiry_date")

    completion_dt = _parse_iso_or_date(completion_date)
    if not completion_dt:
        return record.get("expiry_date")

    raw_expiry = record.get("expiry_date")
    raw_expiry_dt = _parse_iso_or_date(raw_expiry) if raw_expiry else None

    if _is_internal_temporary_evidence(record):
        temp_expiry_dt = completion_dt + timedelta(days=TEMP_INTERNAL_EVIDENCE_VALIDITY_DAYS)
        if raw_expiry_dt and raw_expiry_dt < temp_expiry_dt:
            return _format_date_only(raw_expiry_dt)
        return _format_date_only(temp_expiry_dt)

    if _is_external_certificate_evidence(record):
        if raw_expiry_dt:
            return _format_date_only(raw_expiry_dt)
        requirement_id = (
            record.get("requirement_id")
            or record.get("mapped_training_code")
            or record.get("code")
            or record.get("training_name")
            or "default"
        )
        normalized_completion = normalize_date_only(completion_date)
        if isinstance(normalized_completion, datetime):
            normalized_completion = _format_date_only(normalized_completion)
        if not isinstance(normalized_completion, str):
            normalized_completion = _format_date_only(completion_dt)
        return calculate_training_expiry(normalized_completion, str(requirement_id))

    return raw_expiry


def compute_training_record_status(record: dict) -> dict:
    """SINGLE SOURCE OF TRUTH for training record status."""
    completion_date = record.get("completion_date")
    expiry_date = _resolve_effective_expiry_date(record)
    verified = record.get("verified", False)

    if not completion_date:
        return {
            "computed_status": "not_started",
            "renewal_status": None,
            "days_until_expiry": None,
            "status_label": "Not Started",
            "status_color": "gray",
        }

    if not expiry_date:
        return {
            "computed_status": "completed",
            "renewal_status": "no_expiry",
            "days_until_expiry": None,
            "status_label": "Completed" if not verified else "Verified",
            "status_color": "green",
        }

    try:
        now = datetime.now(timezone.utc)
        if isinstance(expiry_date, str):
            if "T" in expiry_date:
                exp_dt = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
            else:
                exp_dt = datetime.strptime(expiry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            exp_dt = expiry_date

        days_until_expiry = (exp_dt - now).days
        expiry_date_str = exp_dt.strftime("%Y-%m-%d")

        if days_until_expiry < 0:
            return {
                "computed_status": "expired",
                "renewal_status": "expired",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Expired ({abs(days_until_expiry)}d ago)",
                "status_color": "red",
            }
        elif days_until_expiry <= EXPIRY_WARNING_DAYS:
            return {
                "computed_status": "needs_renewal",
                "renewal_status": "expiring_soon",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Expires in {days_until_expiry}d",
                "status_color": "amber",
            }
        else:
            return {
                "computed_status": "completed",
                "renewal_status": "valid",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Valid ({days_until_expiry}d left)",
                "status_color": "green",
            }
    except Exception as e:
        logger.error(f"Error computing training status: {e}")
        return {
            "computed_status": "completed",
            "renewal_status": "unknown",
            "days_until_expiry": None,
            "status_label": "Completed",
            "status_color": "green",
        }


def enrich_training_record_with_computed_status(record: dict) -> dict:
    """Enrich a training record with computed status fields."""
    computed = compute_training_record_status(record)
    enriched = dict(record)
    enriched["computed_status"] = computed["computed_status"]
    enriched["renewal_status"] = computed["renewal_status"]
    enriched["days_until_expiry"] = computed["days_until_expiry"]
    enriched["status_label"] = computed["status_label"]
    enriched["status_color"] = computed["status_color"]

    if computed["computed_status"] == "expired":
        enriched["status"] = "expired"
    elif computed["computed_status"] == "needs_renewal":
        enriched["status"] = "expiring"
    elif computed["computed_status"] == "not_started":
        enriched["status"] = "not_started"
    else:
        if record.get("status") not in ["completed", "verified"]:
            enriched["status"] = "completed"
    return enriched


def get_training_blocker_config(requirement_id: str) -> dict:
    """Get blocker configuration for a training requirement."""
    req_lower = requirement_id.lower().replace(" ", "_").replace("-", "_")
    return TRAINING_BLOCKER_CONFIG.get(
        req_lower,
        {
            "blocker_for_work": False,
            "evidence_required": True,
            "reason_code": f"{req_lower}_training_missing",
            "reason_message": f"{requirement_id} training required",
        },
    )


def normalize_training_text(value: str) -> str:
    """Normalize extracted training text for deterministic matching."""
    if not value:
        return ""
    normalized = value.lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_training_key(value: str) -> str:
    """Normalize extracted training text to the underscore-key alias format."""
    return normalize_training_text(value).replace(" ", "_")


# ---------------------------------------------------------------------------
# Canonical mandatory training equivalencies
# ---------------------------------------------------------------------------
CANONICAL_TRAINING_EQUIVALENCIES = {
    "basic_life_support": [
        "Basic Life Support",
        "BLS",
        "CSTF Resuscitation Adults",
        "CSTF Resuscitation Adults Levels 1, 2 & 3",
        "CSTF Resuscitation Adults Levels 1, 2 & 3 (Practical)",
    ],
    "manual_handling": [
        "Manual Handling",
        "Moving and Handling",
        "CSTF Moving & Handling Levels 1 & 2",
        "CSTF Manual Handling & Moving of People",
    ],
    "fire_safety": [
        "Fire Safety",
        "CSTF Fire Safety",
        "CSTF Fire Safety Online Training Module",
    ],
    "infection_control": [
        "Infection Control",
        "Infection Prevention and Control",
        "CSTF Infection Prevention & Control",
        "CSTF Infection Prevention and Control (Levels 1 & 2)",
    ],
    "information_governance": [
        "Information Governance",
        "Handling Information",
        "CSTF Information Governance",
    ],
    "prevent": [
        "Prevent",
        "CSTF Preventing Radicalisation",
    ],
    "safeguarding_adults": [
        "Safeguarding Adults",
        "CSTF Safeguarding Adults",
        "Adult Safeguarding Level 1",
        "Adult Safeguarding Level 2",
    ],
    "safeguarding_children": [
        "Safeguarding Children",
        "CSTF Safeguarding Children",
        "Safeguarding Children Levels 1 & 2",
    ],
    "health_and_safety": [
        "Health and Safety",
        "Health & Safety",
        "Health Safety and Welfare",
        "CSTF Health, Safety and Welfare",
    ],
}

# Legacy mandatory IDs in MANDATORY_ITEMS still use these names.
LEGACY_REQUIREMENT_TO_CANONICAL = {
    "bls": "basic_life_support",
    "health_safety": "health_and_safety",
}

# Safeguarding policy:
# - dual (default): safeguarding = adults AND children
# - combined: legacy generic safeguarding evidence can satisfy both components
SAFEGUARDING_COMPOSITE_POLICY = os.environ.get("SAFEGUARDING_COMPOSITE_POLICY", "dual").strip().lower()

_SAFEGUARDING_CHILD_ROLE_KEYWORDS = (
    "child",
    "children",
    "young_people",
    "young_people",
    "paediatric",
    "pediatric",
    "nursery",
    "school",
    "family_support",
    "childcare",
    "fostering",
)
_SAFEGUARDING_BOTH_ROLE_KEYWORDS = (
    "mixed",
    "adult_and_child",
    "adults_and_children",
    "adult_child",
    "children_and_adults",
    "children_adults",
)


def get_safeguarding_requirement_mode(role: str = "") -> str:
    """Return the safeguarding mode for the supplied role.

    Modes:
      - adult_only
      - children_only
      - both
      - generic_or_adult (safe default for adult-care workflows)
    """
    role_key = normalize_training_text(role).replace(" ", "_")
    if not role_key:
        return "generic_or_adult"

    if any(keyword in role_key for keyword in _SAFEGUARDING_BOTH_ROLE_KEYWORDS):
        return "both"

    if any(keyword in role_key for keyword in _SAFEGUARDING_CHILD_ROLE_KEYWORDS):
        return "children_only"

    return "generic_or_adult"


# ---------------------------------------------------------------------------
# Training name aliases — maps variant names to canonical requirement IDs.
# Used by resolve_training_record to match extracted names to mandatory codes.
# ---------------------------------------------------------------------------
TRAINING_ALIASES = {
    # BLS / Basic Life Support
    "bls": "basic_life_support",
    "adult_bls": "basic_life_support",
    "resuscitation": "basic_life_support",
    "adult_basic_life_support": "basic_life_support",
    "cstf_adult_basic_life_support": "basic_life_support",
    "cstf_resuscitation": "basic_life_support",
    "cstf_resuscitation_adults": "basic_life_support",
    "resuscitation_adults": "basic_life_support",
    "adult_resuscitation": "basic_life_support",
    # Safeguarding
    "safeguarding_adults": "safeguarding",
    "safeguarding_adults_level_1": "safeguarding",
    "safeguarding_adults_level_2": "safeguarding",
    "safeguarding_adults_levels_1_and_2": "safeguarding",
    "cstf_safeguarding_adults": "safeguarding",
    "cstf_safeguarding_adults_level_1": "safeguarding",
    "cstf_safeguarding_adults_level_2": "safeguarding",
    "cstf_safeguarding_adults_levels_1_and_2": "safeguarding",
    "safeguarding_children": "safeguarding",
    "cstf_safeguarding_children": "safeguarding",
    "safeguarding_of_vulnerable_adults": "safeguarding",
    "safeguarding_vulnerable_adults": "safeguarding",
    # Manual handling
    "moving_and_handling": "manual_handling",
    "moving_&_handling": "manual_handling",
    "cstf_moving_and_handling": "manual_handling",
    "moving_and_handling_levels_1_and_2": "manual_handling",
    "cstf_moving_and_handling_levels_1_and_2": "manual_handling",
    "manual_handling_people": "manual_handling",
    "people_moving_and_handling": "manual_handling",
    # Fire safety
    "cstf_fire_safety": "fire_safety",
    "fire_safety_awareness": "fire_safety",
    "fire_safety_practical": "fire_safety",
    "cstf_fire_safety_practical": "fire_safety",
    "fire_awareness": "fire_safety",
    # Infection control
    "infection_prevention_and_control": "infection_control",
    "infection_prevention_&_control": "infection_control",
    "cstf_infection_prevention_and_control": "infection_control",
    "infection_prevention_and_control_levels_1_and_2": "infection_control",
    "cstf_infection_prevention_and_control_levels_1_and_2": "infection_control",
    "infection_prevention_control": "infection_control",
    "ipc": "infection_control",
    # Health & Safety
    "health_and_safety": "health_safety",
    "health_safety_and_welfare": "health_safety",
    "health,_safety_and_welfare": "health_safety",
    "health_and_safety_and_welfare": "health_safety",
    "health_safety_welfare": "health_safety",
    "cstf_health_safety_and_welfare": "health_safety",
    "cstf_health_and_safety_and_welfare": "health_safety",
    "cstf_health_safety_welfare": "health_safety",
    # Information governance / GDPR
    "gdpr": "information_governance",
    "data_security": "information_governance",
    "data_protection": "information_governance",
    "data_security_awareness": "information_governance",
    "cstf_information_governance": "information_governance",
    "information_governance_and_data_security": "information_governance",
    "information_governance_gdpr": "information_governance",
    # Prevent
    "prevent": "prevent",
    "preventing_radicalisation": "prevent",
    "preventing_radicalization": "prevent",
    "preventing_radicalisation_awareness": "prevent",
    "preventing_radicalization_awareness": "prevent",
    "counter_terrorism": "prevent",
    "counter-terrorism": "prevent",
    "cstf_preventing_radicalisation": "prevent",
    "cstf_preventing_radicalization": "prevent",
    "cstf_prevent": "prevent",
    # Medication
    "safe_handling_and_administration_of_medication": "medication_administration",
    "safe_handling_&_administration_of_medication": "medication_administration",
    "medication": "medication_administration",
    "medication_administration": "medication_administration",
    # Nurse effective training aliases
    "news2": "news2_clinical_observations",
    "news_2": "news2_clinical_observations",
    "clinical_observations": "news2_clinical_observations",
    "news2_clinical_observations": "news2_clinical_observations",
    "sepsis": "sepsis_awareness",
    "sepsis_awareness": "sepsis_awareness",
    "pressure_ulcer_prevention": "pressure_ulcer_prevention",
    "pressure_ulcer": "pressure_ulcer_prevention",
    "pressure_area_care": "pressure_ulcer_prevention",
    "mca_and_dols": "mca_dols",
    "mental_capacity_act": "mca_dols",
    "dols": "mca_dols",
    "enhanced_infection_prevention": "enhanced_infection_prevention",
    "clinical_ipc": "enhanced_infection_prevention",
    "enhanced_ipc": "enhanced_infection_prevention",
    # Common CSTF non-mandatory-but-trackable aliases
    "cstf_equality_diversity_and_human_rights": "equality_diversity",
    "equality_diversity_and_human_rights": "equality_diversity",
    "equality_diversity": "equality_diversity",
    "cstf_nhs_conflict_resolution": "conflict_resolution",
    "nhs_conflict_resolution": "conflict_resolution",
    "conflict_resolution": "conflict_resolution",
}

# Apply explicit canonical equivalencies (single source of truth layer).
for canonical_code, aliases in CANONICAL_TRAINING_EQUIVALENCIES.items():
    TRAINING_ALIASES[canonical_code] = canonical_code
    for alias in aliases:
        key = normalize_training_key(alias)
        TRAINING_ALIASES[key] = canonical_code

# Legacy ID compatibility aliases.
for legacy_code, canonical_code in LEGACY_REQUIREMENT_TO_CANONICAL.items():
    TRAINING_ALIASES[legacy_code] = canonical_code

# Strict safeguarding separation by default.
TRAINING_ALIASES["safeguarding_adults"] = "safeguarding_adults"
TRAINING_ALIASES["safeguarding_children"] = "safeguarding_children"
TRAINING_ALIASES["cstf_safeguarding_adults"] = "safeguarding_adults"
TRAINING_ALIASES["cstf_safeguarding_children"] = "safeguarding_children"
TRAINING_ALIASES["adult_safeguarding_level_1"] = "safeguarding_adults"
TRAINING_ALIASES["adult_safeguarding_level_2"] = "safeguarding_adults"
TRAINING_ALIASES["safeguarding_children_levels_1_2"] = "safeguarding_children"


def _record_quality_score(record: dict) -> int:
    """Lower = better quality record for lookup preference.
    
    Priority: verified > completed-with-date > completed > not-started.
    """
    verified = record.get("verified", False)
    has_completion = bool(record.get("completion_date"))
    if record.get("verification_status") == "rejected":
        return 4
    if not has_completion:
        return 5
    if verified:
        return 0
    return 2  # completed but unverified


def build_training_records_lookup(records: list) -> dict:
    """Build a lookup dict keyed by all normalised forms of each record's identifiers.

    When multiple records map to the same key, the highest-quality record wins
    (verified > completed > unverified > rejected > not-started).

    Keys stored per record:
      - requirement_id  (as-is)
      - requirement_id with underscores→hyphens
      - requirement_id with hyphens→underscores
      - training_name → lowercase, spaces→underscores
      - training_name → lowercase, spaces→underscores, &→and
      - training_id   (as-is, if present)
    """
    lookup = {}
    lookup_scores = {}  # track quality score per key
    for record in records:
        keys = []
        req_id = record.get("requirement_id")
        t_name = record.get("training_name", "")
        t_id = record.get("training_id")

        if req_id:
            keys.append(req_id)
            keys.append(req_id.replace("_", "-"))
            keys.append(req_id.replace("-", "_"))
        if t_name:
            normalised = normalize_training_key(t_name)
            keys.append(normalised)
            keys.append(normalised.replace("&", "and"))
            # Add canonical alias if this name maps to one
            canon = TRAINING_ALIASES.get(normalised) or TRAINING_ALIASES.get(normalised.replace("&", "and"))
            if canon:
                keys.append(canon)
        if t_id:
            keys.append(t_id)
        # Also key by canonical alias of requirement_id
        if req_id:
            canon_req = TRAINING_ALIASES.get(req_id)
            if canon_req:
                keys.append(canon_req)

        score = _record_quality_score(record)
        for k in keys:
            if not k:
                continue
            existing_score = lookup_scores.get(k)
            if existing_score is None or score < existing_score:
                lookup[k] = record
                lookup_scores[k] = score
    return lookup


def resolve_training_record(lookup: dict, req_id: str, training_name: str = None):
    """Look up a training record using the canonical fallback sequence.

    Attempts: exact → alias → training_name normalised → underscore↔hyphen variants.
    Returns the matched record dict or None.
    """
    record = lookup.get(req_id)
    if record:
        return record
    # Check canonical alias of req_id
    canon = TRAINING_ALIASES.get(req_id)
    if canon:
        record = lookup.get(canon)
        if record:
            return record
    if training_name:
        alt = normalize_training_key(training_name)
        record = lookup.get(alt)
        if record:
            return record
        # Check alias of training_name
        canon_name = TRAINING_ALIASES.get(alt) or TRAINING_ALIASES.get(alt.replace("&", "and"))
        if canon_name:
            record = lookup.get(canon_name)
            if record:
                return record
    record = lookup.get(req_id.replace("_", "-"))
    if record:
        return record
    record = lookup.get(req_id.replace("-", "_"))
    if record:
        return record
    return None


# ---------------------------------------------------------------------------
# Canonical mandatory-training helpers (lazy-import MANDATORY_ITEMS)
# ---------------------------------------------------------------------------

def get_canonical_mandatory_training_ids() -> set:
    """Return the set of training IDs flagged as mandatory for compliance."""
    from server import MANDATORY_ITEMS
    return {
        item["id"]
        for item in MANDATORY_ITEMS["training"]
        if item.get("mandatory_for_compliance")
    }


def is_mandatory_training_canonical(training_id: str) -> bool:
    """Check whether *training_id* (normalised code) is compliance-mandatory."""
    return training_id in get_canonical_mandatory_training_ids()


# Keyword map used by resolve_mandatory_training_code to find canonical codes.
_MANDATORY_KEYWORD_MAP = {
    "safeguarding_adults": ["safeguarding adults", "adult safeguarding", "protection of adults"],
    "safeguarding_children": ["safeguarding children", "child safeguarding", "child protection"],
    "manual_handling": ["manual handling", "moving and handling", "people handling", "moving & handling"],
    "fire_safety": ["fire safety", "fire awareness", "fire marshal", "fire warden"],
    "health_and_safety": ["health and safety", "health safety", "health safety and welfare", "health and safety and welfare", "h s awareness"],
    "basic_life_support": ["basic life support", "bls", "first aid", "resuscitation", "cpr"],
    "infection_control": ["infection control", "infection prevention", "ipc"],
    "information_governance": ["information governance", "data protection", "gdpr", "confidentiality"],
    "prevent": ["prevent", "counter terrorism", "radicalisation", "prevent duty"],
    "news2_clinical_observations": ["news2", "news 2", "clinical observations", "vital signs"],
    "sepsis_awareness": ["sepsis"],
    "pressure_ulcer_prevention": ["pressure ulcer", "pressure sore", "tissue viability"],
    "mca_dols": ["mca", "mental capacity", "dols", "deprivation of liberty"],
    "enhanced_infection_prevention": ["clinical ipc", "enhanced infection prevention", "infection prevention level 2"],
}


def resolve_mandatory_training_code(training_name: str):
    """Resolve a training name to its canonical mandatory requirement ID.

    Returns the canonical code (e.g. ``"safeguarding"``) when the name
    matches a mandatory training, or ``None`` if no match is found.
    Uses the keyword map, then falls back to TRAINING_ALIASES.
    """
    if not training_name:
        return None
    name_lower = normalize_training_text(training_name)
    # Alias match
    normalised = normalize_training_key(name_lower)
    canon = TRAINING_ALIASES.get(normalised)
    if canon:
        # keep explicit safeguards strict unless combined policy is configured
        if canon == "safeguarding" and SAFEGUARDING_COMPOSITE_POLICY != "combined":
            return None
        return canon
    # Keyword match
    for code, keywords in _MANDATORY_KEYWORD_MAP.items():
        if any(kw in name_lower for kw in keywords):
            return code
    return None


# ---------------------------------------------------------------------------
# Async functions (require _db)
# ---------------------------------------------------------------------------

# Statuses that mean the requirement is currently satisfied (not blocking).
_SATISFIED_STATUSES = frozenset({"verified", "due_soon"})


def _record_requires_reverification(record: Optional[dict]) -> bool:
    if not record:
        return False
    if record.get("source_evidence_removed"):
        return True
    if record.get("needs_review"):
        return True
    reason = (record.get("needs_review_reason") or "").strip().lower()
    return reason in {
        "source_certificate_deleted",
        "certificate_evidence_removed_by_admin",
        "evidence_replaced_reverification_required",
    }


async def get_required_training_for_employee(employee_id: str, role: str) -> List[dict]:
    """Return merged list of required training for an employee.

    For HCA / support-worker roles the default mandatory set is filtered to
    only the 8 items that carry ``mandatory_for_compliance: True``.
    Role-conditional items (safeguarding_l2/l3) are excluded unless the
    employee's normalised role appears in the item's ``role_required`` list.

    Nurses get the full generic set *plus* nurse-specific training.
    """
    from server import MANDATORY_ITEMS, normalize_to_system_role, is_nurse_role, SystemRole

    all_training = MANDATORY_ITEMS["training"]
    system_role = normalize_to_system_role(role) if role else SystemRole.UNKNOWN

    if is_nurse_role(system_role):
        # Nurses: full generic list + nurse-specific training + effective-domain
        # nurse clinical training requirements.
        items = all_training.copy()
        nurse_training = [i for i in MANDATORY_ITEMS["nurse_specific"] if i.get("type") == "training"]
        items.extend(nurse_training)
        items.extend(get_nurse_effective_required_training_items())

        # Dedupe by requirement id to avoid duplicate matrix rows when an item
        # exists in both generic and nurse-specific sources.
        deduped = {}
        for item in items:
            item_id = item.get("id")
            if item_id:
                deduped[item_id] = item
        items = list(deduped.values())
    else:
        # HCA / support-worker / unknown: only mandatory-for-compliance items,
        # plus any item whose role_required list includes the raw role.
        normalised_role = (role or "").strip().lower().replace(" ", "_")
        items = []
        for item in all_training:
            if item.get("mandatory_for_compliance"):
                items.append(item)
            elif normalised_role and normalised_role in (item.get("role_required") or []):
                items.append(item)
            # else: skip — not mandatory and not role-required

    return items


def get_nurse_effective_required_training_items() -> List[dict]:
    """Return additive nurse Effective-domain clinical training requirements."""
    return [dict(item) for item in NURSE_EFFECTIVE_REQUIRED_TRAININGS]


async def evaluate_employee_training_status(employee_id: str, role: str = "") -> dict:
    """
    CANONICAL TRAINING EVALUATOR — Single Source of Truth.

    Returns:
        overall, blockerCount, warningCount, items[], evaluatedAt
    """
    db = _get_db()
    required_training = await get_required_training_for_employee(employee_id, role)

    training_records = await db.training_records.find(
        {"employee_id": employee_id, "record_status": {"$nin": ["superseded", "deleted"]}},
        {"_id": 0},
    ).to_list(100)

    records_by_req = build_training_records_lookup(training_records)

    items = []
    blocker_count = 0
    warning_count = 0
    has_missing = False
    has_expired = False
    has_due_soon = False

    for req in required_training:
        req_id = req.get("id") or req.get("training_name", "").lower().replace(" ", "_")
        training_name = req.get("training_name") or req.get("name", req_id)

        blocker_config = get_training_blocker_config(req_id)
        is_blocker = blocker_config.get("blocker_for_work", False)
        evidence_required = blocker_config.get("evidence_required", True)

        if req_id == "safeguarding":
            adults_record = resolve_training_record(records_by_req, "safeguarding_adults", "Safeguarding Adults")
            children_record = resolve_training_record(records_by_req, "safeguarding_children", "Safeguarding Children")
            generic_record = resolve_training_record(records_by_req, "safeguarding", "Safeguarding")
            safeguarding_mode = get_safeguarding_requirement_mode(role)

            def _component_status(record: Optional[dict], label: str) -> str:
                if not record or not record.get("completion_date"):
                    return "missing"
                if record.get("verification_status") == "rejected":
                    return "rejected"
                if _record_requires_reverification(record):
                    return "awaiting_review"
                if not record.get("verified", False):
                    return "awaiting_review"
                computed = compute_training_record_status(record)
                if computed.get("computed_status") == "expired":
                    return "expired"
                if computed.get("computed_status") == "needs_renewal":
                    return "due_soon"
                return "verified"

            generic_status = _component_status(generic_record, "generic")
            adults_status = _component_status(adults_record, "adults")
            children_status = _component_status(children_record, "children")

            generic_ok = generic_status in _SATISFIED_STATUSES
            adults_ok = adults_status in _SATISFIED_STATUSES
            children_ok = children_status in _SATISFIED_STATUSES

            if SAFEGUARDING_COMPOSITE_POLICY == "combined" and generic_ok:
                status = "verified"
                detail = "Safeguarding verified"
            elif safeguarding_mode in ("generic_or_adult", "adult_only"):
                if generic_ok:
                    status = "verified"
                    detail = "Safeguarding verified"
                elif adults_ok:
                    status = "verified"
                    detail = "Safeguarding Adults verified"
                elif children_ok:
                    status = "missing"
                    detail = "Safeguarding Adults or generic Safeguarding required for this role"
                    has_missing = True
                else:
                    status = "missing"
                    detail = "Safeguarding training not recorded"
                    has_missing = True
            elif safeguarding_mode == "children_only":
                if generic_ok:
                    status = "verified"
                    detail = "Safeguarding verified"
                elif children_ok:
                    status = "verified"
                    detail = "Safeguarding Children verified"
                elif adults_ok:
                    status = "missing"
                    detail = "Safeguarding Children or generic Safeguarding required for this role"
                    has_missing = True
                else:
                    status = "missing"
                    detail = "Safeguarding training not recorded"
                    has_missing = True
            else:  # both
                if generic_ok:
                    status = "verified"
                    detail = "Safeguarding verified"
                elif adults_ok and children_ok:
                    status = "verified"
                    detail = "Safeguarding Adults and Children verified"
                elif adults_ok or children_ok:
                    status = "partial"
                    detail = "Safeguarding partially complete - both Adults and Children are required"
                    has_missing = True
                else:
                    status = "missing"
                    detail = "Safeguarding training not recorded"
                    has_missing = True

            if is_blocker and status not in _SATISFIED_STATUSES:
                blocker_count += 1
            elif status not in _SATISFIED_STATUSES:
                warning_count += 1

            items.append({
                "code": req_id,
                "requirement": req_id,
                "title": training_name,
                "status": status,
                "blocker": is_blocker,
                "is_currently_blocking": is_blocker and status not in _SATISFIED_STATUSES,
                "detail": detail,
                "expires_at": None,
                "verified": status in _SATISFIED_STATUSES,
                "evidence_required": evidence_required,
                "record_id": (
                    generic_record.get("id") if generic_record else (
                        adults_record.get("id") if adults_record else (
                            children_record.get("id") if children_record else None
                        )
                    )
                ),
                "rejection_reason": None,
                "breakdown": {
                    "mode": safeguarding_mode,
                    "generic": generic_status,
                    "adults": adults_status,
                    "children": children_status,
                },
            })
            continue

        record = resolve_training_record(records_by_req, req_id, training_name)

        if not record:
            items.append({
                "code": req_id,
                "title": training_name,
                "status": "missing",
                "blocker": is_blocker,
                "is_currently_blocking": is_blocker,  # missing → always blocking if can_block
                "detail": f"{training_name} training not recorded",
                "expires_at": None,
                "verified": False,
                "evidence_required": evidence_required,
                "record_id": None,
                "rejection_reason": None,
            })
            has_missing = True
            if is_blocker:
                blocker_count += 1
            else:
                warning_count += 1
            continue

        computed = compute_training_record_status(record)
        computed_status = computed.get("computed_status")
        verified = record.get("verified", False)
        expiry_date = record.get("expiry_date")

        if computed_status == "not_started":
            status = "missing"
            has_missing = True
            detail = f"{training_name} training not completed"
            if is_blocker:
                blocker_count += 1
            else:
                warning_count += 1
        elif record.get("verification_status") == "rejected":
            status = "rejected"
            detail = f"{training_name} rejected: {record.get('rejection_reason', 'see admin')}"
            if is_blocker:
                blocker_count += 1
            else:
                warning_count += 1
        elif _record_requires_reverification(record):
            if evidence_required:
                status = "awaiting_review"
                detail = f"{training_name} evidence replaced/removed - awaiting re-verification"
            else:
                status = "completed"
                detail = f"{training_name} evidence replaced/removed - awaiting re-verification"
            if is_blocker:
                blocker_count += 1
            else:
                warning_count += 1
        elif not verified:
            # Policy: only verified records are compliant.
            # Unverified records (completed, awaiting_review) are visible but non-compliant.
            if evidence_required:
                status = "awaiting_review"
                detail = f"{training_name} submitted but awaiting verification"
            else:
                status = "completed"
                detail = f"{training_name} completed — awaiting verification"
            if is_blocker:
                blocker_count += 1
            else:
                warning_count += 1
        elif computed_status == "expired":
            status = "expired"
            has_expired = True
            detail = f"{training_name} expired on {expiry_date}"
            if is_blocker:
                blocker_count += 1
            else:
                warning_count += 1
        elif computed_status == "needs_renewal":
            status = "due_soon"
            has_due_soon = True
            days_left = computed.get("days_until_expiry", 0)
            detail = f"{training_name} expires in {days_left} days"
            warning_count += 1
        else:
            status = "verified"
            detail = f"{training_name} valid" + (f" until {expiry_date}" if expiry_date else "")

        items.append({
            "code": req_id,
            "requirement": req_id,
            "title": training_name,
            "status": status,
            "blocker": is_blocker,
            "is_currently_blocking": is_blocker and status not in _SATISFIED_STATUSES,
            "detail": detail,
            "expires_at": expiry_date,
            "verified": verified,
            "evidence_required": evidence_required,
            "completion_date": record.get("completion_date"),
            "days_until_expiry": computed.get("days_until_expiry"),
            "certificate_url": record.get("certificate_url"),
            "record_id": record.get("id"),
            "source_document_id": record.get("source_document_id") or record.get("certificate_document_id") or record.get("document_id"),
            "rejection_reason": record.get("rejection_reason") if status == "rejected" else None,
        })

    # Verified-only policy: "current" requires at least one verified item
    # and zero blockers.  If every required item is non-verified
    # (completed / awaiting_review / rejected) with nothing verified,
    # overall must NOT be "current".
    has_any_verified = any(i.get("status") == "verified" for i in items)

    if has_expired:
        overall = "overdue"
    elif has_missing:
        overall = "missing"
    elif has_due_soon:
        overall = "due_soon"
    elif not has_any_verified or blocker_count > 0:
        overall = "missing"
    else:
        overall = "current"

    return {
        "overall": overall,
        "blockerCount": blocker_count,
        "warningCount": warning_count,
        "items": items,
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
    }
