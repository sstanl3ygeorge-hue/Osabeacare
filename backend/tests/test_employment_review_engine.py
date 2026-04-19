import sys
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from employment_review_engine import build_employment_review_from_employee  # noqa: E402


TODAY = date.today()


def years_ago(years: int, month: int = 1) -> str:
    return f"{TODAY.year - years}-{month:02d}"


def build_review(history, existing_gaps=None, explanations=None, **employee_overrides):
    employee = {
        "id": "emp_test",
        "employment_history": history,
        **employee_overrides,
    }
    return build_employment_review_from_employee(
        employee,
        existing_gaps or [],
        explanations or [],
        as_of_date=TODAY,
    )


def gap_segments(review):
    return [segment for segment in review["segments"] if segment["type"] == "gap"]


def employment_segments(review):
    return [segment for segment in review["segments"] if segment["type"] == "employment"]


def test_full_10_year_employment_with_no_gaps():
    review = build_review([
        {
            "employer_name": "Continuous Care Ltd",
            "job_title": "Support Worker",
            "start_date": years_ago(11),
            "end_date": None,
        }
    ])

    assert review["status"] == "awaiting_admin_review"
    assert review["top_summary"]["employment_segments"] == 1
    assert review["top_summary"]["gap_segments"] == 0
    assert review["coverage"]["total_days_covered"] > 0
    assert review["coverage"]["informational_only"] is True


def test_pre_history_gap_is_modelled_as_separate_segment():
    review = build_review([
        {
            "employer_name": "Recent Care Ltd",
            "job_title": "Care Assistant",
            "start_date": years_ago(2),
            "end_date": None,
        }
    ])

    gaps = gap_segments(review)
    assert any(gap["gap_type"] == "pre_history" for gap in gaps)
    assert review["status"] == "in_progress"
    assert review["top_summary"]["missing_gaps"] >= 1


def test_inter_employment_gap_is_modelled_as_separate_segment():
    review = build_review([
        {
            "employer_name": "First Care",
            "job_title": "HCA",
            "start_date": years_ago(11),
            "end_date": f"{TODAY.year - 3}-01",
        },
        {
            "employer_name": "Second Care",
            "job_title": "Support Worker",
            "start_date": f"{TODAY.year - 3}-04",
            "end_date": None,
        },
    ])

    gaps = gap_segments(review)
    assert any(gap["gap_type"] == "inter_entry" for gap in gaps)
    assert review["top_summary"]["missing_gaps"] >= 1


def test_trailing_gap_is_modelled_as_separate_segment():
    review = build_review([
        {
            "employer_name": "Previous Care",
            "job_title": "Care Assistant",
            "start_date": years_ago(11),
            "end_date": f"{TODAY.year - 1}-01",
        }
    ])

    gaps = gap_segments(review)
    assert any(gap["gap_type"] == "trailing" for gap in gaps)
    assert review["status"] == "in_progress"


def test_multiple_separate_gaps_are_preserved():
    review = build_review([
        {
            "employer_name": "Care One",
            "job_title": "HCA",
            "start_date": years_ago(11),
            "end_date": f"{TODAY.year - 7}-01",
        },
        {
            "employer_name": "Care Two",
            "job_title": "HCA",
            "start_date": f"{TODAY.year - 7}-04",
            "end_date": f"{TODAY.year - 4}-01",
        },
        {
            "employer_name": "Care Three",
            "job_title": "Support Worker",
            "start_date": f"{TODAY.year - 4}-05",
            "end_date": None,
        },
    ])

    gaps = gap_segments(review)
    assert len([gap for gap in gaps if gap["gap_type"] == "inter_entry"]) == 2
    assert [gap["order"] for gap in review["segments"]] == sorted(segment["order"] for segment in review["segments"])


def test_explanation_matches_gap_by_date_range():
    base_review = build_review([
        {
            "employer_name": "First Care",
            "job_title": "HCA",
            "start_date": years_ago(11),
            "end_date": f"{TODAY.year - 3}-01",
        },
        {
            "employer_name": "Second Care",
            "job_title": "Support Worker",
            "start_date": f"{TODAY.year - 3}-04",
            "end_date": None,
        },
    ])
    target_gap = gap_segments(base_review)[0]

    review = build_review(
        [
            {
                "employer_name": "First Care",
                "job_title": "HCA",
                "start_date": years_ago(11),
                "end_date": f"{TODAY.year - 3}-01",
            },
            {
                "employer_name": "Second Care",
                "job_title": "Support Worker",
                "start_date": f"{TODAY.year - 3}-04",
                "end_date": None,
            },
        ],
        explanations=[
            {
                "gap_start": target_gap["start_date"],
                "gap_end": target_gap["end_date"],
                "reason_type": "education",
                "explanation": "Completed training.",
            }
        ],
    )

    matched_gap = gap_segments(review)[0]
    assert matched_gap["status"] == "explained"
    assert matched_gap["explanation"]["matched_by"] == "date_range"
    assert review["top_summary"]["explained_gaps"] == 1
    assert review["can_sign_off"] is False
    assert "require admin verification" in review["gap_actions"]["blocked_sign_off_reasons"][0]


def test_explanation_matches_gap_by_legacy_gap_id():
    review = build_review(
        [
            {
                "employer_name": "First Care",
                "job_title": "HCA",
                "start_date": years_ago(11),
                "end_date": f"{TODAY.year - 3}-01",
            },
            {
                "employer_name": "Second Care",
                "job_title": "Support Worker",
                "start_date": f"{TODAY.year - 3}-04",
                "end_date": None,
            },
        ],
        explanations=[
            {
                "gap_id": "gap_1",
                "reason_type": "family_care",
                "explanation": "Caring responsibilities.",
            }
        ],
    )

    matched_gap = gap_segments(review)[0]
    assert matched_gap["status"] == "explained"
    assert matched_gap["explanation"]["matched_by"] == "legacy_gap_id"


def test_unmatched_applicant_notes_are_kept_separate():
    review = build_review(
        [
            {
                "employer_name": "Continuous Care Ltd",
                "job_title": "Support Worker",
                "start_date": years_ago(11),
                "end_date": None,
            }
        ],
        explanations=[
            {
                "gap_start": years_ago(5),
                "gap_end": years_ago(4),
                "reason_type": "travel",
                "explanation": "Travelled abroad.",
            }
        ],
    )

    assert gap_segments(review) == []
    assert len(review["unmatched_applicant_notes"]) == 1
    assert review["top_summary"]["unmatched_notes"] == 1


def test_invalid_missing_dates_make_review_cannot_assess():
    review = build_review([
        {
            "employer_name": "Missing Dates Ltd",
            "job_title": "Care Assistant",
            "start_date": None,
            "end_date": None,
        },
        {
            "employer_name": "Valid Care",
            "job_title": "HCA",
            "start_date": years_ago(3),
            "end_date": None,
        },
    ])

    assert review["status"] == "cannot_assess"
    assert review["cannot_assess"] is True
    assert len(review["invalid_entries"]) == 1
    assert review["diagnostics"]["analysis_status"] == "cannot_assess"


def test_verified_gap_preserves_admin_decision():
    history = [
        {
            "employer_name": "First Care",
            "job_title": "HCA",
            "start_date": years_ago(11),
            "end_date": f"{TODAY.year - 3}-01",
        },
        {
            "employer_name": "Second Care",
            "job_title": "Support Worker",
            "start_date": f"{TODAY.year - 3}-04",
            "end_date": None,
        },
    ]
    base_gap = gap_segments(build_review(history))[0]
    review = build_review(
        history,
        existing_gaps=[
            {
                "gap_id": base_gap["gap_id"],
                "gap_start": base_gap["start_date"],
                "gap_end": base_gap["end_date"],
                "status": "verified",
                "verified_by": "admin_1",
                "verified_by_name": "Manager",
                "verified_at": "2026-04-19T10:00:00Z",
                "explanation": "Training course accepted.",
            }
        ],
    )

    gap = gap_segments(review)[0]
    assert gap["status"] == "verified"
    assert gap["admin_review"]["reviewed_by"] == "admin_1"
    assert review["top_summary"]["verified_gaps"] == 1
    assert review["status"] == "awaiting_admin_review"


def test_rejected_gap_blocks_sign_off():
    history = [
        {
            "employer_name": "First Care",
            "job_title": "HCA",
            "start_date": years_ago(11),
            "end_date": f"{TODAY.year - 3}-01",
        },
        {
            "employer_name": "Second Care",
            "job_title": "Support Worker",
            "start_date": f"{TODAY.year - 3}-04",
            "end_date": None,
        },
    ]
    base_gap = gap_segments(build_review(history))[0]
    review = build_review(
        history,
        existing_gaps=[
            {
                "gap_id": base_gap["gap_id"],
                "gap_start": base_gap["start_date"],
                "gap_end": base_gap["end_date"],
                "status": "rejected",
                "rejection_reason": "Insufficient detail.",
            }
        ],
    )

    assert gap_segments(review)[0]["status"] == "rejected"
    assert review["status"] == "in_progress"
    assert review["can_sign_off"] is False
    assert review["top_summary"]["rejected_gaps"] == 1


def test_sign_off_is_invalidated_when_timeline_changes():
    original_history = [
        {
            "employer_name": "Continuous Care Ltd",
            "job_title": "Support Worker",
            "start_date": years_ago(11),
            "end_date": None,
        }
    ]
    original = build_review(original_history)
    signed_fingerprint = original["diagnostics"]["timeline_fingerprint"]

    changed_history = [
        {
            "employer_name": "Continuous Care Ltd",
            "job_title": "Senior Support Worker",
            "start_date": years_ago(11),
            "end_date": None,
        }
    ]
    changed = build_review(
        changed_history,
        employment_review_signed_off=True,
        employment_review_signed_version=1,
        employment_review_signed_timeline_fingerprint=signed_fingerprint,
        employment_review_signed_off_by="admin_1",
        employment_review_signed_off_at="2026-04-19T10:00:00Z",
    )

    assert changed["sign_off"]["signed_off"] is False
    assert changed["sign_off"]["invalidated"] is True
    assert changed["status"] == "awaiting_admin_review"
    assert "timeline has changed" in changed["sign_off"]["invalidated_reason"]
