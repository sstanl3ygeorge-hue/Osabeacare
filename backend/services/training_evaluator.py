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
}


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


def compute_training_record_status(record: dict) -> dict:
    """SINGLE SOURCE OF TRUTH for training record status."""
    completion_date = record.get("completion_date")
    expiry_date = record.get("expiry_date")
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


def build_training_records_lookup(records: list) -> dict:
    """Build a lookup dict keyed by all normalised forms of each record's identifiers.

    Keys stored per record (first-write wins):
      - requirement_id  (as-is)
      - requirement_id with underscores→hyphens
      - requirement_id with hyphens→underscores
      - training_name → lowercase, spaces→underscores
      - training_name → lowercase, spaces→underscores, &→and
      - training_id   (as-is, if present)
    """
    lookup = {}
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
            normalised = t_name.lower().replace(" ", "_")
            keys.append(normalised)
            keys.append(normalised.replace("&", "and"))
        if t_id:
            keys.append(t_id)

        for k in keys:
            if k and k not in lookup:
                lookup[k] = record
    return lookup


def resolve_training_record(lookup: dict, req_id: str, training_name: str = None):
    """Look up a training record using the canonical fallback sequence.

    Attempts: exact → training_name normalised → underscore↔hyphen variants.
    Returns the matched record dict or None.
    """
    record = lookup.get(req_id)
    if record:
        return record
    if training_name:
        alt = training_name.lower().replace(" ", "_")
        record = lookup.get(alt)
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


# ---------------------------------------------------------------------------
# Async functions (require _db)
# ---------------------------------------------------------------------------

async def get_required_training_for_employee(employee_id: str, role: str) -> List[dict]:
    """Return merged list of required training for an employee."""
    from server import MANDATORY_ITEMS, normalize_to_system_role, is_nurse_role, SystemRole

    items = MANDATORY_ITEMS["training"].copy()
    system_role = normalize_to_system_role(role) if role else SystemRole.UNKNOWN
    if is_nurse_role(system_role):
        nurse_training = [i for i in MANDATORY_ITEMS["nurse_specific"] if i.get("type") == "training"]
        items.extend(nurse_training)
    return items


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

        record = resolve_training_record(records_by_req, req_id, training_name)

        if not record:
            items.append({
                "code": req_id,
                "title": training_name,
                "status": "missing",
                "blocker": is_blocker,
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
            "title": training_name,
            "status": status,
            "blocker": is_blocker,
            "detail": detail,
            "expires_at": expiry_date,
            "verified": verified,
            "evidence_required": evidence_required,
            "completion_date": record.get("completion_date"),
            "days_until_expiry": computed.get("days_until_expiry"),
            "certificate_url": record.get("certificate_url"),
            "record_id": record.get("id"),
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
