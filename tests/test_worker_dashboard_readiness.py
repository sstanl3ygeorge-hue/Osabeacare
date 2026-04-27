"""Unit tests for the worker-dashboard employment-readiness state machine.

Covers the 5-state canonical model in ``compute_employment_readiness``:
    ready_for_work
    awaiting_final_company_action
    action_required_from_you
    admin_review_in_progress
    system_issue_preventing_completion

These tests are deliberately pure (no DB, no FastAPI) so they stay fast and can
be run in isolation.
"""
from __future__ import annotations

import os
import sys

# Make backend/ importable when running pytest from repo root.
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND = os.path.join(_REPO, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routes.worker_dashboard import (  # noqa: E402
    EMPLOYMENT_READINESS_STATES,
    build_worker_tasks,
    compute_employment_readiness,
)


def _call(**overrides):
    """Call the helper with sensible defaults (blank slate) and overrides."""
    base = dict(
        is_active_employee=False,
        contract_worker_signed=False,
        contract_fully_executed=False,
        contract_rejected=False,
        handbook_acknowledged=False,
        handbook_verified=False,
        handbook_rejected=False,
        handbook_system_issue=False,
    )
    base.update(overrides)
    return compute_employment_readiness(**base)


def _types(blockers):
    return {b["type"] for b in blockers}


def _classifications(blockers):
    return {b["classification"] for b in blockers}


def test_states_tuple_is_canonical():
    assert EMPLOYMENT_READINESS_STATES == (
        "ready_for_work",
        "awaiting_final_company_action",
        "action_required_from_you",
        "admin_review_in_progress",
        "system_issue_preventing_completion",
    )


def test_active_employee_still_surfaces_missing_required_actions():
    state, label, blockers = _call(is_active_employee=True)
    assert state == "action_required_from_you"
    assert label == "Action required from you"
    assert "contract_unsigned" in _types(blockers)
    assert "handbook_unacknowledged" in _types(blockers)


def test_fully_cleared_worker_is_ready():
    state, _, blockers = _call(
        contract_worker_signed=True,
        contract_fully_executed=True,
        handbook_acknowledged=True,
        handbook_verified=True,
    )
    assert state == "ready_for_work"
    assert blockers == []


def test_blank_slate_is_action_required_from_worker():
    """Nothing signed, nothing acknowledged — worker has to act."""
    state, label, blockers = _call()
    assert state == "action_required_from_you"
    assert label == "Action required from you"
    assert "contract_unsigned" in _types(blockers)
    assert "handbook_unacknowledged" in _types(blockers)
    assert _classifications(blockers) == {"worker_action"}


def test_worker_signed_awaiting_countersign_is_company_action():
    """Olumide OBEMBE scenario: worker signed contract, handbook done too,
    waiting only on the company's final countersignature."""
    state, label, blockers = _call(
        contract_worker_signed=True,
        contract_fully_executed=False,
        handbook_acknowledged=True,
        handbook_verified=True,
    )
    assert state == "awaiting_final_company_action"
    assert label == "Awaiting final company action"
    assert "contract_awaiting_company_countersignature" in _types(blockers)
    # Must NOT blame the worker in this state
    assert "worker_action" not in _classifications(blockers)


def test_handbook_render_issue_is_system_not_worker():
    """Handbook rejected due to render/config problem must surface as a system
    issue, NOT as 'action required from you'."""
    state, label, blockers = _call(
        contract_worker_signed=True,
        contract_fully_executed=True,
        handbook_system_issue=True,
        # An underlying 'rejected' flag might co-exist — system_issue must win.
        handbook_rejected=True,
    )
    assert state == "system_issue_preventing_completion"
    assert label == "System issue preventing completion"
    types_ = _types(blockers)
    assert "handbook_system_issue" in types_
    # The worker-blaming 'handbook_rejected' blocker must not be raised
    # when the real cause is a system issue.
    assert "handbook_rejected" not in types_


def test_handbook_rejected_without_system_issue_is_worker_action():
    state, _, blockers = _call(
        contract_worker_signed=True,
        contract_fully_executed=True,
        handbook_rejected=True,
    )
    assert state == "action_required_from_you"
    assert "handbook_rejected" in _types(blockers)


def test_contract_rejected_is_worker_action():
    state, _, blockers = _call(
        contract_rejected=True,
        handbook_acknowledged=True,
        handbook_verified=True,
    )
    assert state == "action_required_from_you"
    assert "contract_rejected" in _types(blockers)


def test_handbook_acknowledged_awaiting_admin_is_admin_review():
    """Everything done from worker and company sides, admin just needs to verify
    the handbook ack."""
    state, label, blockers = _call(
        contract_worker_signed=True,
        contract_fully_executed=True,
        handbook_acknowledged=True,
        handbook_verified=False,
    )
    assert state == "admin_review_in_progress"
    assert label == "Admin review in progress"
    assert "handbook_awaiting_verification" in _types(blockers)
    assert _classifications(blockers) == {"admin_action"}


def test_worker_blocker_beats_company_blocker():
    """If there is any worker action pending, that's the surfaced state even if
    a company-side blocker also exists."""
    state, _, _ = _call(
        contract_worker_signed=False,          # worker hasn't signed yet
        handbook_acknowledged=True,            # admin pending on handbook
    )
    assert state == "action_required_from_you"


def test_system_issue_beats_worker_action():
    """System/config issue takes priority — don't send worker chasing phantom
    actions when the real problem is on the company's setup side."""
    state, _, _ = _call(
        handbook_system_issue=True,
        contract_worker_signed=False,  # would otherwise be worker_action
    )
    assert state == "system_issue_preventing_completion"


def test_each_blocker_has_required_keys():
    """Every blocker the helper produces must carry the classification fields
    the frontend relies on to pick a colour and wording."""
    _, _, blockers = _call()  # blank slate → multiple blockers
    required = {"type", "classification", "label", "actor"}
    valid_classifications = {
        "worker_action", "company_action", "admin_action", "system_issue",
    }
    for b in blockers:
        assert required.issubset(b.keys()), b
        assert b["classification"] in valid_classifications, b


def test_worker_tasks_include_equality_training_when_pending():
    tasks = build_worker_tasks(
        {"items": [{"code": "equality_diversity", "title": "Equality and Diversity", "status": "missing"}]},
        readiness_blockers=[],
        contract_status={},
    )
    assert any(task.get("key") == "equality_and_diversity" for task in tasks)


def test_worker_tasks_include_sign_new_contract_when_pending_signature():
    tasks = build_worker_tasks(
        {"items": []},
        readiness_blockers=[],
        contract_status={"contract_state": "pending_signature", "can_sign": True},
    )
    assert any(task.get("key") == "sign_new_contract" for task in tasks)
