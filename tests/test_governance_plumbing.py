"""Unit tests for the Phase 1 governance plumbing.

Covers:
    - compute_worker_governance_readiness() state machine
    - new_audit_metadata / stamp_update / audit_trail_entry
    - require_employee_not_applicant guard (pure async impl)

All tests are pure — no DB, no FastAPI server — so they run in isolation.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND = os.path.join(_REPO, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from governance.readiness import (  # noqa: E402
    GOVERNANCE_READINESS_STATES,
    compute_worker_governance_readiness,
)
from governance.audit import (  # noqa: E402
    audit_trail_entry,
    new_audit_metadata,
    stamp_update,
)
from governance.guards import _guard_employee_not_applicant  # noqa: E402
from fastapi import HTTPException  # noqa: E402


# ════════════════════════════════════════════════════════════════════════════
# readiness — state model contract
# ════════════════════════════════════════════════════════════════════════════

def test_governance_states_tuple_is_canonical():
    assert GOVERNANCE_READINESS_STATES == (
        "on_track",
        "attention_required",
        "overdue_actions",
        "high_risk_open_issue",
    )


def test_on_track_when_no_governance_items():
    result = compute_worker_governance_readiness()
    assert result["governance_readiness"] == "on_track"
    assert result["governance_readiness_label"] == "On track"
    assert result["governance_blockers"] == []
    assert result["governance_alerts"] == []
    # Summary still present with zeroed counts.
    assert result["governance_summary"]["supervisions"]["overdue"] is False
    assert result["governance_summary"]["competencies"]["critical_missing"] == 0


def test_on_track_when_all_summaries_empty_dicts():
    """Empty dicts must behave identically to omitted summaries."""
    result = compute_worker_governance_readiness(
        supervisions={},
        competencies={},
        spot_checks={},
        incidents={},
        care_plan_reviews={},
    )
    assert result["governance_readiness"] == "on_track"
    assert result["governance_blockers"] == []
    assert result["governance_alerts"] == []


# ════════════════════════════════════════════════════════════════════════════
# readiness — attention_required (alerts only)
# ════════════════════════════════════════════════════════════════════════════

def test_attention_required_for_supervision_due_soon():
    result = compute_worker_governance_readiness(
        supervisions={"due_within_14d": True},
    )
    assert result["governance_readiness"] == "attention_required"
    assert result["governance_blockers"] == []
    types = {a["type"] for a in result["governance_alerts"]}
    assert "supervision_due_soon" in types


def test_attention_required_for_competency_due_soon_only():
    result = compute_worker_governance_readiness(
        competencies={"noncritical_due_within_30d": 2},
    )
    assert result["governance_readiness"] == "attention_required"
    assert result["governance_blockers"] == []
    assert any(
        a["type"] == "competency_due_soon" for a in result["governance_alerts"]
    )


def test_attention_required_for_open_high_severity_incident_involving_worker():
    """An open high-severity incident is an ALERT, not a blocker — only
    critical-past-7d or missing safeguarding ref escalate to blocker."""
    result = compute_worker_governance_readiness(
        incidents={"open_high_severity_involving_worker": 1},
    )
    assert result["governance_readiness"] == "attention_required"
    assert result["governance_blockers"] == []
    assert any(
        a["type"] == "open_high_severity_incident"
        for a in result["governance_alerts"]
    )


# ════════════════════════════════════════════════════════════════════════════
# readiness — overdue_actions
# ════════════════════════════════════════════════════════════════════════════

def test_overdue_actions_for_overdue_supervision():
    result = compute_worker_governance_readiness(
        supervisions={"overdue": True},
    )
    assert result["governance_readiness"] == "overdue_actions"
    assert any(
        b["type"] == "supervision_overdue"
        for b in result["governance_blockers"]
    )


def test_overdue_actions_for_overdue_spot_check_followup():
    result = compute_worker_governance_readiness(
        spot_checks={"followup_overdue": True},
    )
    assert result["governance_readiness"] == "overdue_actions"
    assert any(
        b["type"] == "spot_check_followup_overdue"
        for b in result["governance_blockers"]
    )


def test_overdue_actions_for_overdue_care_plan_review_assigned():
    result = compute_worker_governance_readiness(
        care_plan_reviews={"assigned_overdue": 1},
    )
    assert result["governance_readiness"] == "overdue_actions"
    b = next(
        x for x in result["governance_blockers"]
        if x["type"] == "care_plan_review_overdue"
    )
    assert b["actor"] == "worker"
    assert b["classification"] == "overdue"


def test_overdue_actions_for_expired_critical_competency():
    result = compute_worker_governance_readiness(
        competencies={"critical_expired": 1},
    )
    assert result["governance_readiness"] == "overdue_actions"
    assert any(
        b["type"] == "critical_competency_expired"
        for b in result["governance_blockers"]
    )


def test_missing_critical_competency_is_blocker_not_alert():
    result = compute_worker_governance_readiness(
        competencies={"critical_missing": 1},
    )
    assert result["governance_readiness"] == "overdue_actions"
    assert result["governance_alerts"] == []


# ════════════════════════════════════════════════════════════════════════════
# readiness — high_risk_open_issue
# ════════════════════════════════════════════════════════════════════════════

def test_high_risk_for_critical_incident_open_past_7d():
    result = compute_worker_governance_readiness(
        incidents={"critical_open_past_7d": 1},
    )
    assert result["governance_readiness"] == "high_risk_open_issue"
    assert any(
        b["type"] == "critical_incident_open"
        and b["classification"] == "high_risk"
        for b in result["governance_blockers"]
    )


def test_high_risk_for_safeguarding_concern_missing_la_ref():
    result = compute_worker_governance_readiness(
        incidents={"safeguarding_missing_ref_over_24h": 1},
    )
    assert result["governance_readiness"] == "high_risk_open_issue"
    assert any(
        b["type"] == "safeguarding_ref_missing"
        for b in result["governance_blockers"]
    )


def test_high_risk_for_critical_spot_check_finding():
    result = compute_worker_governance_readiness(
        spot_checks={"critical_finding_open": True},
    )
    assert result["governance_readiness"] == "high_risk_open_issue"


# ════════════════════════════════════════════════════════════════════════════
# readiness — state priority
# ════════════════════════════════════════════════════════════════════════════

def test_high_risk_beats_overdue_when_both_present():
    result = compute_worker_governance_readiness(
        supervisions={"overdue": True},
        incidents={"critical_open_past_7d": 1},
    )
    assert result["governance_readiness"] == "high_risk_open_issue"
    # Both blockers must still be surfaced.
    types = {b["type"] for b in result["governance_blockers"]}
    assert "supervision_overdue" in types
    assert "critical_incident_open" in types


def test_overdue_beats_attention_when_both_present():
    result = compute_worker_governance_readiness(
        supervisions={"overdue": True, "due_within_14d": True},
    )
    # When overdue is true the "due_within_14d" alert is suppressed anyway.
    assert result["governance_readiness"] == "overdue_actions"


def test_every_blocker_and_alert_has_required_keys():
    result = compute_worker_governance_readiness(
        supervisions={"overdue": True, "due_within_14d": True, "open_worker_actions_overdue": 1},
        competencies={
            "critical_missing": 1,
            "critical_expired": 1,
            "critical_training_required": 1,
            "noncritical_due_within_30d": 1,
        },
        spot_checks={
            "fail_unclosed_overdue": True,
            "critical_finding_open": True,
            "followup_overdue": True,
            "next_periodic_due_within_30d": True,
            "followup_due_within_7d": True,
        },
        incidents={
            "critical_open_past_7d": 1,
            "safeguarding_missing_ref_over_24h": 1,
            "open_high_severity_involving_worker": 1,
        },
        care_plan_reviews={"assigned_overdue": 1, "assigned_due_within_7d": 1},
    )
    required = {"domain", "type", "label", "classification", "actor"}
    for b in result["governance_blockers"]:
        assert required.issubset(b.keys()), b
        assert b["classification"] in {"high_risk", "overdue"}
    for a in result["governance_alerts"]:
        assert required.issubset(a.keys()), a
        assert a["classification"] == "attention"


# ════════════════════════════════════════════════════════════════════════════
# readiness — provider profile is NOT in scope
# ════════════════════════════════════════════════════════════════════════════

def test_provider_profile_is_excluded_from_worker_governance():
    """Provider profile completeness lives on the organisation side and must
    NEVER flip worker governance state.  Even if a caller mis-passes a
    provider_profile kwarg the helper must refuse to consume it."""
    # The helper does not accept provider_profile — simulating a caller that
    # tried to add it must raise TypeError, not silently affect readiness.
    with pytest.raises(TypeError):
        compute_worker_governance_readiness(
            provider_profile={"incomplete": True},  # type: ignore[call-arg]
        )
    # And of course with zero worker-side items the worker is on_track
    # regardless of any org-side state.
    assert (
        compute_worker_governance_readiness()["governance_readiness"]
        == "on_track"
    )


# ════════════════════════════════════════════════════════════════════════════
# audit helpers
# ════════════════════════════════════════════════════════════════════════════

def test_new_audit_metadata_shape_for_create():
    user = {"user_id": "u-1", "name": "Admin One"}
    meta = new_audit_metadata(user, action="schedule")
    # Required record-level fields.
    for k in (
        "id", "created_at", "created_by", "updated_at", "updated_by",
        "verification_status", "verified_at", "verified_by",
        "verified_by_name", "audit_trail",
    ):
        assert k in meta, k
    assert meta["created_by"] == "u-1"
    assert meta["updated_by"] == "u-1"
    assert meta["verification_status"] == "pending"
    assert meta["verified_at"] is None
    assert len(meta["audit_trail"]) == 1
    first = meta["audit_trail"][0]
    assert first["action"] == "schedule"
    assert first["by"] == "u-1"
    assert first["by_name"] == "Admin One"
    assert "at" in first


def test_new_audit_metadata_uses_system_when_no_user():
    meta = new_audit_metadata(None)
    assert meta["created_by"] == "system"
    assert meta["audit_trail"][0]["by"] == "system"
    assert meta["audit_trail"][0]["by_name"] == "System"


def test_stamp_update_appends_entry_and_preserves_creation():
    user = {"user_id": "u-1", "name": "A"}
    record = new_audit_metadata(user, action="create")
    original_created_at = record["created_at"]
    original_created_by = record["created_by"]

    other = {"user_id": "u-2", "name": "B"}
    stamp_update(
        record, other,
        action="complete",
        from_="scheduled", to="completed",
        outcome="satisfactory",
        notes="no concerns",
    )

    assert record["created_at"] == original_created_at  # immutable
    assert record["created_by"] == original_created_by  # immutable
    assert record["updated_by"] == "u-2"
    assert len(record["audit_trail"]) == 2
    last = record["audit_trail"][-1]
    assert last["action"] == "complete"
    assert last["from"] == "scheduled"
    assert last["to"] == "completed"
    assert last["outcome"] == "satisfactory"
    assert last["notes"] == "no concerns"


def test_audit_trail_entry_omits_unset_optional_fields():
    entry = audit_trail_entry(user={"user_id": "u"}, action="verify")
    # Only the mandatory keys should be present.
    assert set(entry.keys()) == {"at", "by", "by_name", "action"}


def test_audit_trail_entry_includes_actions_when_provided():
    actions = [{"id": "a-1", "description": "x", "status": "open"}]
    entry = audit_trail_entry(
        user={"user_id": "u"}, action="complete", actions=actions
    )
    assert entry["actions"] == actions


# ════════════════════════════════════════════════════════════════════════════
# applicant guard
# ════════════════════════════════════════════════════════════════════════════

class _FakeEmployees:
    def __init__(self, doc):
        self._doc = doc

    async def find_one(self, query, projection=None):
        if self._doc is None:
            return None
        if query.get("id") != self._doc.get("id"):
            return None
        return dict(self._doc)


class _FakeDB:
    def __init__(self, employee_doc):
        self.employees = _FakeEmployees(employee_doc)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def test_applicant_guard_rejects_applicant_by_explicit_stage():
    db = _FakeDB({"id": "emp-1", "status": "new", "person_stage": "applicant"})
    with pytest.raises(HTTPException) as exc:
        _run(_guard_employee_not_applicant("emp-1", db=db))
    assert exc.value.status_code == 403


def test_applicant_guard_rejects_applicant_by_derived_stage_from_status():
    # No explicit person_stage; status "screening" derives to applicant.
    db = _FakeDB({"id": "emp-1", "status": "screening"})
    with pytest.raises(HTTPException) as exc:
        _run(_guard_employee_not_applicant("emp-1", db=db))
    assert exc.value.status_code == 403


def test_applicant_guard_allows_employee():
    db = _FakeDB({"id": "emp-1", "status": "active", "person_stage": "employee"})
    employee = _run(_guard_employee_not_applicant("emp-1", db=db))
    assert employee["id"] == "emp-1"


def test_applicant_guard_allows_onboarding_employee():
    db = _FakeDB({"id": "emp-1", "status": "onboarding"})
    employee = _run(_guard_employee_not_applicant("emp-1", db=db))
    assert employee["id"] == "emp-1"


def test_applicant_guard_allows_archived_for_audit_readability():
    """Historical records must remain readable for inspection/audit."""
    db = _FakeDB({"id": "emp-1", "status": "archived", "person_stage": "archived"})
    employee = _run(_guard_employee_not_applicant("emp-1", db=db))
    assert employee["id"] == "emp-1"


def test_applicant_guard_404_when_employee_missing():
    db = _FakeDB(None)
    with pytest.raises(HTTPException) as exc:
        _run(_guard_employee_not_applicant("emp-missing", db=db))
    assert exc.value.status_code == 404
