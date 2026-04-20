"""
test_reference_employment_crosscheck.py

Regression tests for the 3-tier reference-employment matching model.

Rule:
  - ok      : ref matched to most-recent / current employer
  - warning  : ref matched to an earlier (not most-recent) employer  ← VALID MATCH
  - alert    : ref matched to NO declared employer                    ← TRUE MISMATCH

A "warning" must NEVER be treated as a mismatch or gate blocker.
"""

import pytest
from reference_matching import (
    match_employers,
    identify_most_recent_employer,
    compliance_status_for_match,
    normalize_employer,
)


# ---------------------------------------------------------------------------
# Fixtures — concrete employer data matching the Medway QA finding scenario
# ---------------------------------------------------------------------------

CURRENT_EMPLOYER = {
    "employer_name": "Vankol Homes and Support Services",
    "position": "Senior Care Worker",
    "start_date": "2023-01",
    "end_date": "",
    "is_current": True,
}

EARLIER_EMPLOYER = {
    "employer_name": "Kent Community Health NHS Foundation Trust",
    "position": "Healthcare Assistant",
    "start_date": "2019-06",
    "end_date": "2022-12",
    "is_current": False,
}

EMPLOYMENT_HISTORY = [CURRENT_EMPLOYER, EARLIER_EMPLOYER]


# ---------------------------------------------------------------------------
# Test A — Reference matches current / most-recent employer → ok
# ---------------------------------------------------------------------------

class TestCaseA_CurrentEmployerMatch:
    """Reference organisation is the current employer."""

    def test_matched(self):
        matched, emp, reason = match_employers(
            "Vankol Homes and Support Services",
            EMPLOYMENT_HISTORY,
        )
        assert matched is True, "Should match current employer"
        assert emp is not None
        assert "Vankol" in emp["employer_name"]

    def test_is_most_recent(self):
        most_recent_norm = identify_most_recent_employer(EMPLOYMENT_HISTORY)
        matched, emp, reason = match_employers(
            "Vankol Homes and Support Services",
            EMPLOYMENT_HISTORY,
        )
        emp_norm = normalize_employer(emp["employer_name"])
        assert emp_norm == most_recent_norm, "Matched employer should be most recent"

    def test_compliance_status_ok(self):
        most_recent_norm = identify_most_recent_employer(EMPLOYMENT_HISTORY)
        matched, emp, reason = match_employers(
            "Vankol Homes and Support Services",
            EMPLOYMENT_HISTORY,
        )
        is_most_recent = normalize_employer(emp["employer_name"]) == most_recent_norm
        status = compliance_status_for_match(matched, emp, is_most_recent)
        assert status == "ok", f"Expected 'ok', got '{status}'"

    def test_matches_employment_history_true(self):
        matched, _, _ = match_employers("Vankol Homes and Support Services", EMPLOYMENT_HISTORY)
        assert matched is True


# ---------------------------------------------------------------------------
# Test B — Reference matches earlier employer → warning (valid match, not alert)
# ---------------------------------------------------------------------------

class TestCaseB_EarlierEmployerMatch:
    """
    Concrete example from Medway QA finding:
      Reference org:  "Kent Community Health NHS Foundation"
      Employment row: "Kent Community Health NHS Foundation Trust"
    The suffix difference ("Foundation" vs "Foundation Trust") must NOT prevent matching.
    """

    REF_ORG = "Kent Community Health NHS Foundation"

    def test_matched(self):
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        assert matched is True, (
            f"'Kent Community Health NHS Foundation' should match "
            f"'Kent Community Health NHS Foundation Trust' — got matched={matched}, reason={reason}"
        )

    def test_matched_employer_is_correct(self):
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        assert emp is not None
        assert "Kent Community Health" in emp["employer_name"]

    def test_is_not_most_recent(self):
        most_recent_norm = identify_most_recent_employer(EMPLOYMENT_HISTORY)
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        emp_norm = normalize_employer(emp["employer_name"])
        assert emp_norm != most_recent_norm, (
            "Kent Community Health should NOT be identified as the most-recent employer"
        )

    def test_compliance_status_warning_not_alert(self):
        most_recent_norm = identify_most_recent_employer(EMPLOYMENT_HISTORY)
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        is_most_recent = normalize_employer(emp["employer_name"]) == most_recent_norm
        status = compliance_status_for_match(matched, emp, is_most_recent)
        assert status == "warning", (
            f"Earlier-employer match must be 'warning', not '{status}'. "
            "This is a valid match — it must never surface as 'alert'."
        )

    def test_matches_employment_history_true(self):
        """matches_employment_history must be True — this IS a match."""
        matched, _, _ = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        assert matched is True, (
            "matches_employment_history must be True for an earlier-employer match. "
            "It must NEVER be False (which would imply 'no match')."
        )

    def test_no_blocker_for_warning(self):
        """A warning must not be treated as a gate blocker."""
        most_recent_norm = identify_most_recent_employer(EMPLOYMENT_HISTORY)
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        is_most_recent = normalize_employer(emp["employer_name"]) == most_recent_norm
        status = compliance_status_for_match(matched, emp, is_most_recent)
        assert status != "alert", (
            "'warning' must never be escalated to 'alert' for an earlier-employer match."
        )


# ---------------------------------------------------------------------------
# Test C — Reference matches no declared employer → alert (true mismatch)
# ---------------------------------------------------------------------------

class TestCaseC_NoEmployerMatch:
    """Reference organisation has no match in employment history."""

    REF_ORG = "Sunrise Nursing Agency Ltd"

    def test_not_matched(self):
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        assert matched is False, f"Unknown organisation should not match. Got matched={matched}"
        assert emp is None
        assert reason == "none"

    def test_compliance_status_alert(self):
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        status = compliance_status_for_match(
            matched=matched,
            matching_employer=emp,
            is_most_recent=False,
        )
        assert status == "alert", f"No-match reference must be 'alert', got '{status}'"

    def test_matches_employment_history_false(self):
        matched, _, _ = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        assert matched is False

    def test_override_reason_downgrades_to_warning(self):
        """Admin-recorded override must downgrade alert → warning."""
        matched, emp, reason = match_employers(self.REF_ORG, EMPLOYMENT_HISTORY)
        status = compliance_status_for_match(
            matched=matched,
            matching_employer=emp,
            is_most_recent=False,
            override_reason="Applicant was placed via this agency during the gap period",
        )
        assert status == "warning", (
            "With override_reason, a no-match should downgrade to 'warning', not remain 'alert'."
        )


# ---------------------------------------------------------------------------
# Summary invariant
# ---------------------------------------------------------------------------

class TestSummaryInvariants:
    """High-level invariants that must always hold across all three cases."""

    def test_warning_is_not_a_mismatch(self):
        """
        The core regression guard: an earlier-employer reference must have
        matches_employment_history=True. This test prevents the bug from reappearing
        where warning-status refs were counted as unmatched.
        """
        ref_org = "Kent Community Health NHS Foundation"
        matched, emp, reason = match_employers(ref_org, EMPLOYMENT_HISTORY)
        # Core assertion
        assert matched is True, (
            "REGRESSION: 'warning' reference was incorrectly treated as unmatched. "
            "matches_employment_history must be True for any employer found in employment history."
        )

    def test_only_alert_is_true_mismatch(self):
        """Only status='alert' should ever have matches_employment_history=False."""
        test_cases = [
            ("Vankol Homes and Support Services", True),          # ok case
            ("Kent Community Health NHS Foundation", True),        # warning case
            ("Sunrise Nursing Agency Ltd", False),                 # alert case
        ]
        most_recent_norm = identify_most_recent_employer(EMPLOYMENT_HISTORY)
        for ref_org, expected_matched in test_cases:
            matched, emp, reason = match_employers(ref_org, EMPLOYMENT_HISTORY)
            assert matched == expected_matched, (
                f"Ref org '{ref_org}': expected matches_employment_history={expected_matched}, "
                f"got {matched} (reason={reason})"
            )
            if matched and emp:
                is_most_recent = normalize_employer(emp["employer_name"]) == most_recent_norm
                status = compliance_status_for_match(matched, emp, is_most_recent)
                assert status != "alert", (
                    f"Matched reference ('{ref_org}') must never have status='alert'. Got '{status}'."
                )
