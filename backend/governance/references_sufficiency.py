"""Reference sufficiency validation (CQC Regulation 19).

Two verified references is not enough on its own for clinical/care roles — at
least one of the two must be an **employment reference**, or there must be a
recorded explanation for why an alternative reference (character / academic)
is acceptable.

This module is a pure, DB-agnostic helper. Callers pass the relevant employee
role and a list of the employee's reference slots as plain dicts; the function
returns a structured verdict that endpoints and the readiness engine use.

Persisted schema per reference slot (lives on ``db.references.ref{n}``):

    type: "employment" | "character" | "academic"
    is_employment_reference: bool
    explanation_required: bool
    explanation_reason: str | None
    explanation_provided_by: user_id | None
    explanation_provided_at: ISO datetime | None

These five fields are additive and default to ``None`` / ``False`` on legacy
records; the helpers here treat missing values as "unspecified, not
employment".
"""
from __future__ import annotations

from typing import Iterable, List, Optional


# ---------------------------------------------------------------------------
# Role gating
# ---------------------------------------------------------------------------

# Roles for which CQC Reg 19 requires the organisation to have taken
# reasonable steps to obtain an employment reference. We normalise loosely so
# "Healthcare Assistant", "health_care_assistant", "HCA", and "Staff Nurse"
# all land on True.
_EMPLOYMENT_REFERENCE_ROLE_TOKENS = (
    "healthcare_assistant",
    "health_care_assistant",
    "healthcare assistant",
    "health care assistant",
    "hca",
    "support worker",
    "support_worker",
    "care assistant",
    "care_assistant",
    "nurse",
    "midwife",
    "doctor",
    "clinical",
)

VALID_REFERENCE_TYPES = ("employment", "character", "academic")


def _normalise_role(role: Optional[str]) -> str:
    if not role:
        return ""
    return str(role).strip().lower().replace("-", "_")


def role_requires_employment_reference(role: Optional[str]) -> bool:
    """Return True if the role is clinical/care and therefore must have at
    least one employment reference (or a recorded explanation)."""
    norm = _normalise_role(role)
    if not norm:
        return False
    for token in _EMPLOYMENT_REFERENCE_ROLE_TOKENS:
        tok = token.lower()
        if tok in norm:
            return True
        # also match underscored variants
        if tok.replace(" ", "_") in norm:
            return True
    return False


# ---------------------------------------------------------------------------
# Type inference
# ---------------------------------------------------------------------------

# relationship_type values coming back on the referee form that imply an
# employment relationship.
_EMPLOYMENT_RELATIONSHIP_VALUES = {
    "line manager",
    "senior manager",
    "hr manager",
    "director",
    "supervisor",
    "colleague (senior)",
    "colleague",
}

_ACADEMIC_TOKENS = ("tutor", "lecturer", "professor", "academic", "university", "college")
_CHARACTER_TOKENS = ("personal", "character", "friend", "family", "neighbour", "neighbor")


def classify_reference_type(ref_slot: dict) -> str:
    """Infer the canonical reference type from a reference slot.

    Priority:
      1. Explicit ``type`` field on the slot (if a valid value).
      2. Explicit ``is_employment_reference`` boolean on the slot.
      3. ``relationship_type`` from the referee response.
      4. ``relationship`` free-text from the declared referee.

    Falls back to ``"character"`` when nothing is specified — that is the
    safer default for compliance (forces the explanation path rather than
    silently treating an unknown relationship as employment).
    """
    if not isinstance(ref_slot, dict):
        return "character"

    # 1. Explicit stored type
    stored = ref_slot.get("type")
    if isinstance(stored, str) and stored.lower() in VALID_REFERENCE_TYPES:
        return stored.lower()

    # 2. Boolean flag
    flag = ref_slot.get("is_employment_reference")
    if flag is True:
        return "employment"
    if flag is False and stored is None:
        # explicit non-employment with no other signal → character
        pass  # fall through to response / declared inference

    response = ref_slot.get("response") or {}
    declared = ref_slot.get("declared") or {}

    rel_type = (response.get("relationship_type") or "").strip().lower()
    if rel_type:
        if rel_type in _EMPLOYMENT_RELATIONSHIP_VALUES:
            return "employment"
        if any(tok in rel_type for tok in _ACADEMIC_TOKENS):
            return "academic"
        if any(tok in rel_type for tok in _CHARACTER_TOKENS):
            return "character"

    declared_rel = (declared.get("relationship") or "").strip().lower()
    if declared_rel:
        if any(tok in declared_rel for tok in ("manager", "supervisor", "employer", "hr", "director")):
            return "employment"
        if any(tok in declared_rel for tok in _ACADEMIC_TOKENS):
            return "academic"
        if any(tok in declared_rel for tok in _CHARACTER_TOKENS):
            return "character"

    # Referee job title can be a last hint for employment (if they clearly
    # hold a role at an organisation).
    if (declared.get("job_title") or response.get("referee_job_title")):
        org = declared.get("organisation") or response.get("referee_organisation") or ""
        if org:
            return "employment"

    return "character"


def is_employment_reference(ref_slot: dict) -> bool:
    return classify_reference_type(ref_slot) == "employment"


# ---------------------------------------------------------------------------
# Verified-state detection
# ---------------------------------------------------------------------------

def _slot_is_verified(ref_slot: dict) -> bool:
    if not isinstance(ref_slot, dict):
        return False
    verification = ref_slot.get("verification") or {}
    if verification.get("verified") is True:
        return True
    if verification.get("status") == "verified":
        return True
    # legacy flat key fallback
    return bool(ref_slot.get("verification_status") == "verified")


def _slot_has_explanation(ref_slot: dict) -> bool:
    reason = (ref_slot or {}).get("explanation_reason")
    return bool(reason and str(reason).strip())


# ---------------------------------------------------------------------------
# Top-level verdict
# ---------------------------------------------------------------------------

def evaluate_reference_sufficiency(
    role: Optional[str],
    reference_slots: Iterable[dict],
) -> dict:
    """Evaluate whether the set of reference slots satisfies Reg 19 sufficiency.

    Args:
        role: the employee/applicant role string (``employee.role``).
        reference_slots: iterable of reference slot dicts (each is the full
            ``ref1``/``ref2`` sub-document, including ``verification``,
            ``response``, ``declared`` and the new sufficiency fields).

    Returns:
        {
            "role_requires_employment_reference": bool,
            "verified_count": int,
            "employment_reference_count": int,
            "employment_reference_verified_count": int,
            "explanation_present": bool,
            "explanation_reason": str | None,
            "sufficient": bool,
            "requires_explanation": bool,
            "blocker_reason": str | None,
        }
    """
    slots: List[dict] = [s for s in reference_slots if isinstance(s, dict)]

    requires = role_requires_employment_reference(role)

    verified_slots = [s for s in slots if _slot_is_verified(s)]
    verified_count = len(verified_slots)

    employment_slots = [s for s in slots if is_employment_reference(s)]
    employment_reference_count = len(employment_slots)
    employment_reference_verified_count = len(
        [s for s in employment_slots if _slot_is_verified(s)]
    )

    explanation_slots = [s for s in slots if _slot_has_explanation(s)]
    explanation_present = bool(explanation_slots)
    explanation_reason = (
        explanation_slots[0].get("explanation_reason") if explanation_slots else None
    )

    sufficient = True
    requires_explanation = False
    blocker_reason: Optional[str] = None

    if requires:
        if employment_reference_verified_count >= 1:
            # Employment reference present & verified — sufficient.
            pass
        elif explanation_present:
            # No employment reference, but the explanation has been recorded
            # and the two references are otherwise verified.
            pass
        else:
            sufficient = False
            requires_explanation = True
            blocker_reason = (
                "Role requires at least one employment reference. "
                "Either obtain an employment reference, or record why "
                "alternative references are acceptable."
            )

    return {
        "role_requires_employment_reference": requires,
        "verified_count": verified_count,
        "employment_reference_count": employment_reference_count,
        "employment_reference_verified_count": employment_reference_verified_count,
        "explanation_present": explanation_present,
        "explanation_reason": explanation_reason,
        "sufficient": sufficient,
        "requires_explanation": requires_explanation,
        "blocker_reason": blocker_reason,
    }


# ---------------------------------------------------------------------------
# Verify-time pre-commit check
# ---------------------------------------------------------------------------

def evaluate_verify_request(
    role: Optional[str],
    existing_slots: Iterable[dict],
    this_slot_proposed: dict,
    explanation_reason: Optional[str] = None,
) -> dict:
    """Evaluate sufficiency *as if* the admin had just verified ``this_slot_proposed``.

    Used by the verify endpoint to decide whether to block the operation and
    demand an explanation input, before any DB write.

    ``this_slot_proposed`` should already carry the admin's chosen ``type`` /
    ``is_employment_reference`` / (optional) ``explanation_reason``.

    Returns the same verdict dict as :func:`evaluate_reference_sufficiency`,
    evaluated against the post-verify state.
    """
    proposed = dict(this_slot_proposed or {})
    # Force verified=True in the projected state.
    proposed_verification = dict(proposed.get("verification") or {})
    proposed_verification["verified"] = True
    proposed_verification["status"] = "verified"
    proposed["verification"] = proposed_verification

    if explanation_reason and not proposed.get("explanation_reason"):
        proposed["explanation_reason"] = explanation_reason

    # Build the projected slot list. `this_slot_proposed` replaces the slot
    # with the matching reference number if we can find it, else appended.
    projected: List[dict] = []
    replaced = False
    this_num = proposed.get("reference_num") or proposed.get("ref_num")
    for s in existing_slots:
        if not isinstance(s, dict):
            continue
        if this_num is not None and s.get("reference_num") == this_num:
            projected.append(proposed)
            replaced = True
        else:
            projected.append(s)
    if not replaced:
        projected.append(proposed)

    return evaluate_reference_sufficiency(role, projected)
