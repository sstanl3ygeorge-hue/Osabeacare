import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routes.forms import _extract_health_outcome_from_submission, _normalize_health_outcome


def test_normalize_health_outcome_aliases():
    assert _normalize_health_outcome("fit") == "fit"
    assert _normalize_health_outcome("Fit to Work") == "fit"
    assert _normalize_health_outcome("fit_with_adjustments") == "conditional"
    assert _normalize_health_outcome("rejected") == "not_fit"
    assert _normalize_health_outcome("pending") == "requires_review"
    assert _normalize_health_outcome("unknown-value") is None


def test_extract_health_outcome_prefers_known_fields():
    submission = {
        "form_data": {
            "health_outcome": "conditional",
            "status": "fit",
        }
    }
    assert _extract_health_outcome_from_submission(submission) == "conditional"


def test_extract_health_outcome_reads_fallback_payload():
    submission = {
        "data": {
            "final_decision": "not_fit",
        }
    }
    assert _extract_health_outcome_from_submission(submission) == "not_fit"


def test_extract_health_outcome_none_when_missing():
    submission = {"form_data": {"comments": "reviewed"}}
    assert _extract_health_outcome_from_submission(submission) is None
