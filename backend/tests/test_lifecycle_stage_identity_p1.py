from backend.stage_identity import (
    build_stage_filter,
    get_stage_identity,
    normalize_lifecycle_status,
)


def test_status_to_stage_matrix():
    assert get_stage_identity({"status": "new"}) == "applicant"
    assert get_stage_identity({"status": "screening"}) == "applicant"
    assert get_stage_identity({"status": "interview"}) == "applicant"
    assert get_stage_identity({"status": "compliance_review"}) == "applicant"
    assert get_stage_identity({"status": "onboarding"}) == "employee"
    assert get_stage_identity({"status": "active"}) == "employee"
    assert get_stage_identity({"status": "inactive"}) == "employee"


def test_stale_recruitment_approved_cannot_override_status():
    # Lifecycle authority is status; telemetry fields cannot override it.
    person = {"status": "screening", "recruitment_approved": True}
    assert get_stage_identity(person) == "applicant"


def test_active_employee_normalizes_to_active():
    assert normalize_lifecycle_status("active_employee") == "active"
    assert get_stage_identity({"status": "active_employee"}) == "employee"


def test_promoted_employee_remains_resolvable_in_employee_filter():
    filt = build_stage_filter("employee")
    statuses = filt.get("status", {}).get("$in", [])
    assert "onboarding" in statuses
    assert "active" in statuses
    # Keep legacy boundary compatibility for reads only.
    assert "active_employee" in statuses
