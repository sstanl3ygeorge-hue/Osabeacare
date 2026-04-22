"""Unit tests for governance.references_sufficiency."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from governance.references_sufficiency import (  # noqa: E402
    classify_reference_type,
    evaluate_reference_sufficiency,
    evaluate_verify_request,
    is_employment_reference,
    role_requires_employment_reference,
)


# ---------------------------------------------------------------------------
# role_requires_employment_reference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "role,expected",
    [
        ("Healthcare Assistant", True),
        ("healthcare_assistant", True),
        ("health care assistant", True),
        ("HCA", True),
        ("Staff Nurse", True),
        ("Senior Nurse", True),
        ("Registered Nurse", True),
        ("Midwife", True),
        ("Doctor", True),
        ("Support Worker", True),
        ("support_worker", True),
        ("Care Assistant", True),
        # Non-care roles
        ("Administrator", False),
        ("HR Manager", False),
        ("Finance Officer", False),
        ("", False),
        (None, False),
    ],
)
def test_role_requires_employment_reference(role, expected):
    assert role_requires_employment_reference(role) is expected


# ---------------------------------------------------------------------------
# classify_reference_type
# ---------------------------------------------------------------------------

def test_classify_respects_stored_type():
    assert classify_reference_type({"type": "academic"}) == "academic"
    assert classify_reference_type({"type": "Employment"}) == "employment"


def test_classify_respects_is_employment_flag():
    assert classify_reference_type({"is_employment_reference": True}) == "employment"


def test_classify_uses_response_relationship_type_for_employment():
    slot = {"response": {"relationship_type": "Line Manager"}}
    assert classify_reference_type(slot) == "employment"
    slot = {"response": {"relationship_type": "HR Manager"}}
    assert classify_reference_type(slot) == "employment"


def test_classify_detects_academic():
    slot = {"response": {"relationship_type": "University Tutor"}}
    assert classify_reference_type(slot) == "academic"


def test_classify_detects_character():
    slot = {"response": {"relationship_type": "Personal friend"}}
    assert classify_reference_type(slot) == "character"


def test_classify_defaults_to_character_when_unknown():
    assert classify_reference_type({}) == "character"
    assert classify_reference_type({"response": {}}) == "character"


def test_is_employment_reference_wrapper():
    assert is_employment_reference({"type": "employment"}) is True
    assert is_employment_reference({"type": "character"}) is False


# ---------------------------------------------------------------------------
# evaluate_reference_sufficiency
# ---------------------------------------------------------------------------

def _slot(verified=True, ref_type="employment", explanation=None):
    slot = {
        "type": ref_type,
        "is_employment_reference": ref_type == "employment",
        "verification": {"verified": verified, "status": "verified" if verified else "pending"},
    }
    if explanation:
        slot["explanation_reason"] = explanation
    return slot


def test_hca_with_one_employment_and_one_character_is_sufficient():
    v = evaluate_reference_sufficiency(
        "Healthcare Assistant",
        [_slot(ref_type="employment"), _slot(ref_type="character")],
    )
    assert v["role_requires_employment_reference"] is True
    assert v["employment_reference_verified_count"] == 1
    assert v["sufficient"] is True
    assert v["requires_explanation"] is False
    assert v["blocker_reason"] is None


def test_hca_with_two_character_refs_requires_explanation():
    v = evaluate_reference_sufficiency(
        "Healthcare Assistant",
        [_slot(ref_type="character"), _slot(ref_type="character")],
    )
    assert v["sufficient"] is False
    assert v["requires_explanation"] is True
    assert v["employment_reference_count"] == 0
    assert v["blocker_reason"] is not None


def test_hca_with_two_character_refs_and_explanation_is_sufficient():
    v = evaluate_reference_sufficiency(
        "Staff Nurse",
        [
            _slot(ref_type="character", explanation="Applicant's prior employer closed; references supplied by Colleague."),
            _slot(ref_type="character"),
        ],
    )
    assert v["sufficient"] is True
    assert v["requires_explanation"] is False
    assert v["explanation_present"] is True


def test_non_care_role_ignores_employment_requirement():
    v = evaluate_reference_sufficiency(
        "Administrator",
        [_slot(ref_type="character"), _slot(ref_type="character")],
    )
    assert v["role_requires_employment_reference"] is False
    assert v["sufficient"] is True
    assert v["requires_explanation"] is False


def test_unverified_employment_reference_does_not_satisfy():
    v = evaluate_reference_sufficiency(
        "Healthcare Assistant",
        [
            _slot(ref_type="employment", verified=False),
            _slot(ref_type="character"),
        ],
    )
    # Role still requires employment ref that is VERIFIED — none verified here.
    assert v["employment_reference_count"] == 1
    assert v["employment_reference_verified_count"] == 0
    assert v["sufficient"] is False
    assert v["requires_explanation"] is True


# ---------------------------------------------------------------------------
# evaluate_verify_request (pre-commit check on the verify endpoint)
# ---------------------------------------------------------------------------

def test_verify_of_employment_ref_satisfies_even_if_other_pending():
    other = _slot(ref_type="character", verified=False)
    other["reference_num"] = 2
    proposed = _slot(ref_type="employment", verified=False)
    proposed["reference_num"] = 1
    v = evaluate_verify_request(
        role="Healthcare Assistant",
        existing_slots=[other],
        this_slot_proposed=proposed,
    )
    assert v["sufficient"] is True
    assert v["employment_reference_verified_count"] == 1


def test_verify_of_character_ref_requires_explanation_for_hca():
    other_employment_unverified = _slot(ref_type="character", verified=False)
    other_employment_unverified["reference_num"] = 2
    proposed = _slot(ref_type="character", verified=False)
    proposed["reference_num"] = 1
    v = evaluate_verify_request(
        role="Healthcare Assistant",
        existing_slots=[other_employment_unverified],
        this_slot_proposed=proposed,
    )
    assert v["requires_explanation"] is True
    assert v["sufficient"] is False


def test_verify_with_inline_explanation_resolves_the_gap():
    other = _slot(ref_type="character", verified=True)
    other["reference_num"] = 2
    proposed = _slot(ref_type="character", verified=False)
    proposed["reference_num"] = 1
    v = evaluate_verify_request(
        role="Healthcare Assistant",
        existing_slots=[other],
        this_slot_proposed=proposed,
        explanation_reason="Candidate's last two employers have since closed — only personal references available.",
    )
    assert v["sufficient"] is True
    assert v["requires_explanation"] is False
    assert v["explanation_present"] is True


def test_verify_does_not_require_explanation_for_non_care_role():
    other = _slot(ref_type="character", verified=False)
    other["reference_num"] = 2
    proposed = _slot(ref_type="character", verified=False)
    proposed["reference_num"] = 1
    v = evaluate_verify_request(
        role="Office Administrator",
        existing_slots=[other],
        this_slot_proposed=proposed,
    )
    assert v["sufficient"] is True
    assert v["requires_explanation"] is False
