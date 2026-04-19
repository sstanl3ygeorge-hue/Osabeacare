import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from employment_gap_engine import (  # noqa: E402
    compute_coverage_summary,
    detect_employment_gaps_with_coverage,
    parse_employment_date,
)


def test_parse_employment_date_accepts_month_only_dates():
    parsed = parse_employment_date("2020-03")

    assert parsed is not None
    assert parsed.year == 2020
    assert parsed.month == 3
    assert parsed.day == 1


def test_parse_employment_date_preserves_full_iso_dates():
    parsed = parse_employment_date("2020-03-15")

    assert parsed is not None
    assert parsed.year == 2020
    assert parsed.month == 3
    assert parsed.day == 15


def test_coverage_counts_mixed_month_and_full_dates():
    history = [
        {
            "employer_name": "Care Provider One",
            "job_title": "Care Assistant",
            "start_date": "2019-01",
            "end_date": "2021-06-15",
        },
        {
            "employer_name": "Care Provider Two",
            "job_title": "Support Worker",
            "start_date": "2021-07",
            "end_date": None,
        },
    ]

    coverage = compute_coverage_summary(history)

    assert coverage["total_days_covered"] > 0
    assert coverage["coverage_percent"] > 0
    assert coverage["earliest_entry_date"] == "2019-01-01"


def test_gap_detection_generates_gaps_for_month_only_dates():
    history = [
        {
            "employer_name": "First Employer",
            "job_title": "Care Assistant",
            "start_date": "2019-01",
            "end_date": "2020-01",
        },
        {
            "employer_name": "Second Employer",
            "job_title": "Support Worker",
            "start_date": "2020-03",
            "end_date": None,
        },
    ]

    gaps = detect_employment_gaps_with_coverage(history)

    assert any(gap.get("gap_type") == "inter_entry" for gap in gaps)
    assert any(gap.get("gap_start") == "2020-01" and gap.get("gap_end") == "2020-03" for gap in gaps)


def test_coverage_uses_supplied_canonical_gap_statuses():
    history = [
        {
            "employer_name": "First Employer",
            "job_title": "Care Assistant",
            "start_date": "2019-01",
            "end_date": "2020-01",
        },
        {
            "employer_name": "Second Employer",
            "job_title": "Support Worker",
            "start_date": "2020-03",
            "end_date": None,
        },
    ]

    detected_gaps = detect_employment_gaps_with_coverage(history)
    verified_gaps = [
        {**gap, "status": "verified", "verification_status": "verified", "verified": True}
        for gap in detected_gaps
    ]
    coverage = compute_coverage_summary(history, gap_records=verified_gaps)

    assert coverage["total_days_covered"] > 0
    assert coverage["meets_10_year_requirement"] is True
