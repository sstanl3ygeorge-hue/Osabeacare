"""Unit tests for the Supervisions domain (Phase 1 — Step 2).

Covers:
    - compute_supervision_summary() pure helper
    - Readiness integration (supervision summary → governance readiness)
    - Schema / enum validation on the route models
    - Applicant-guard rejection through the shared guard
    - Create / complete / cancel flow against a fake Mongo
    - Cancellation never silently clears the required cadence

All pure / mocked — no live Mongo.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND = os.path.join(_REPO, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from governance.supervisions_summary import compute_supervision_summary  # noqa: E402
from governance.readiness import compute_worker_governance_readiness  # noqa: E402
from governance.guards import _guard_employee_not_applicant  # noqa: E402
from routes import supervisions as sup_route  # noqa: E402
from routes.supervisions import (  # noqa: E402
    SUPERVISION_CADENCE,
    SUPERVISION_OUTCOMES,
    SUPERVISION_STATUSES,
    SUPERVISION_TYPES,
    SupervisionCancel,
    SupervisionComplete,
    SupervisionCreate,
    cancel_supervision,
    complete_supervision,
    create_supervision,
    list_supervisions,
)


def _run(coro):
    return asyncio.run(coro)


NOW = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ════════════════════════════════════════════════════════════════════════════
# compute_supervision_summary — pure helper
# ════════════════════════════════════════════════════════════════════════════

def test_summary_empty_returns_zeros():
    s = compute_supervision_summary([], now=NOW)
    assert s["due_soon_count"] == 0
    assert s["overdue_count"] == 0
    assert s["completed_count"] == 0
    assert s["last_completed_at"] is None
    assert s["next_due_at"] is None
    assert s["overdue"] is False
    assert s["due_within_14d"] is False


def test_summary_scheduled_within_14d_is_due_soon():
    row = {"status": "scheduled", "scheduled_at": _iso(NOW + timedelta(days=10))}
    s = compute_supervision_summary([row], now=NOW)
    assert s["due_soon_count"] == 1
    assert s["due_within_14d"] is True
    assert s["overdue"] is False


def test_summary_scheduled_in_past_is_overdue():
    row = {"status": "scheduled", "scheduled_at": _iso(NOW - timedelta(days=2))}
    s = compute_supervision_summary([row], now=NOW)
    assert s["overdue_count"] == 1
    assert s["overdue"] is True
    assert s["due_within_14d"] is False


def test_summary_completed_with_future_next_due_no_blocker():
    row = {
        "status": "completed",
        "completed_at": _iso(NOW - timedelta(days=5)),
        "next_due_at": _iso(NOW + timedelta(days=60)),
    }
    s = compute_supervision_summary([row], now=NOW)
    assert s["completed_count"] == 1
    assert s["last_completed_at"] == row["completed_at"]
    assert s["next_due_at"] == row["next_due_at"]
    assert s["overdue"] is False
    assert s["due_within_14d"] is False


def test_summary_cadence_next_due_beats_fallback():
    row = {
        "status": "completed",
        "completed_at": _iso(NOW - timedelta(days=10)),
        "next_due_at": _iso(NOW + timedelta(days=50)),  # snapshot
    }
    cadence = _iso(NOW + timedelta(days=3))  # cadence says due soon
    s = compute_supervision_summary([row], cadence_next_due_at=cadence, now=NOW)
    assert s["next_due_at"] == cadence
    assert s["due_within_14d"] is True


def test_summary_cadence_overdue_sets_blocker_even_when_rows_completed():
    row = {"status": "completed", "completed_at": _iso(NOW - timedelta(days=100)),
           "next_due_at": _iso(NOW - timedelta(days=5))}
    s = compute_supervision_summary([row], cadence_next_due_at=row["next_due_at"], now=NOW)
    assert s["overdue"] is True


def test_summary_cancelled_alone_is_not_a_blocker():
    """A single cancelled row must not raise overdue by itself — only the
    cadence row's next_due_date determines the required next occurrence."""
    row = {"status": "cancelled", "scheduled_at": _iso(NOW - timedelta(days=3))}
    s = compute_supervision_summary([row], now=NOW)
    assert s["cancelled_count"] == 1
    assert s["overdue"] is False
    assert s["due_within_14d"] is False


def test_summary_cancelled_does_not_clear_cadence_next_due():
    """Cancellation of one occurrence must not suppress a true cadence
    overdue signal — the cadence row is the truth source."""
    rows = [
        {"status": "cancelled", "scheduled_at": _iso(NOW - timedelta(days=3))},
    ]
    s = compute_supervision_summary(
        rows,
        cadence_next_due_at=_iso(NOW - timedelta(days=1)),
        now=NOW,
    )
    assert s["overdue"] is True


# ════════════════════════════════════════════════════════════════════════════
# Readiness integration
# ════════════════════════════════════════════════════════════════════════════

def test_overdue_supervision_feeds_overdue_actions_state():
    sup = compute_supervision_summary(
        [{"status": "scheduled", "scheduled_at": _iso(NOW - timedelta(days=1))}],
        now=NOW,
    )
    r = compute_worker_governance_readiness(supervisions=sup)
    assert r["governance_readiness"] == "overdue_actions"
    assert any(b["type"] == "supervision_overdue" for b in r["governance_blockers"])


def test_due_soon_supervision_feeds_attention_required():
    sup = compute_supervision_summary(
        [{"status": "scheduled", "scheduled_at": _iso(NOW + timedelta(days=5))}],
        now=NOW,
    )
    r = compute_worker_governance_readiness(supervisions=sup)
    assert r["governance_readiness"] == "attention_required"
    assert r["governance_blockers"] == []
    assert any(a["type"] == "supervision_due_soon" for a in r["governance_alerts"])


def test_completed_with_future_next_due_is_on_track():
    sup = compute_supervision_summary(
        [{
            "status": "completed",
            "completed_at": _iso(NOW - timedelta(days=3)),
            "next_due_at": _iso(NOW + timedelta(days=60)),
        }],
        cadence_next_due_at=_iso(NOW + timedelta(days=60)),
        now=NOW,
    )
    r = compute_worker_governance_readiness(supervisions=sup)
    assert r["governance_readiness"] == "on_track"


# ════════════════════════════════════════════════════════════════════════════
# Schema / enum
# ════════════════════════════════════════════════════════════════════════════

def test_supervision_types_are_canonical():
    assert SUPERVISION_TYPES == (
        "probation", "routine", "return_to_work", "performance",
        "safeguarding_followup", "capability", "ad_hoc",
    )


def test_supervision_statuses_are_canonical():
    assert SUPERVISION_STATUSES == ("scheduled", "completed", "overdue", "cancelled")


def test_every_supervision_type_has_cadence_frequency():
    for t in SUPERVISION_TYPES:
        assert t in SUPERVISION_CADENCE, t


def test_create_model_validates():
    SupervisionCreate(
        employee_id="emp-1",
        supervisor_id="u-1",
        supervision_type="routine",
        scheduled_at=_iso(NOW),
    )


# ════════════════════════════════════════════════════════════════════════════
# Route-level tests — fake Mongo
# ════════════════════════════════════════════════════════════════════════════

class FakeCollection:
    def __init__(self):
        self.docs: List[Dict[str, Any]] = []

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                return dict(d)
        return None

    def find(self, query, projection=None):
        matched = []
        for d in self.docs:
            ok = True
            for k, v in query.items():
                if isinstance(v, dict):
                    if "$in" in v and d.get(k) not in v["$in"]:
                        ok = False; break
                elif k == "$or":
                    pass  # simple: accept all
                elif d.get(k) != v:
                    ok = False; break
            if ok:
                matched.append(dict(d))

        class _Cursor:
            def __init__(self, items): self._items = items
            async def to_list(self, limit): return self._items[:limit]
        # Treat $or queries as "include the row" — good enough for unit tests.
        if "$or" in query:
            matched = [dict(d) for d in self.docs
                       if all(d.get(k) == v for k, v in query.items() if k != "$or")]
        return _Cursor(matched)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update):
        for i, d in enumerate(self.docs):
            if all(d.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                if "$set" in update:
                    d.update(update["$set"])
                return


class FakeDB:
    def __init__(self, employees=None):
        self.employees = FakeCollection()
        self.supervisions = FakeCollection()
        self.recurring_compliance = FakeCollection()
        for emp in (employees or []):
            self.employees.docs.append(dict(emp))


ADMIN = {"user_id": "admin-1", "name": "Admin One", "role": "admin"}


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    """Inject a fresh FakeDB for every route test via get_db patching."""
    db = FakeDB(employees=[
        {"id": "emp-1", "status": "active", "person_stage": "employee"},
        {"id": "app-1", "status": "screening", "person_stage": "applicant"},
    ])
    from routes import dependencies as deps
    monkeypatch.setattr(deps, "db", db)
    # Also patch the governance.guards module which imports get_db via deps.
    yield db


def test_create_supervision_creates_evidence_and_cadence_row(_patch_db):
    db = _patch_db
    payload = SupervisionCreate(
        employee_id="emp-1",
        supervisor_id="u-1",
        supervision_type="routine",
        scheduled_at=_iso(NOW + timedelta(days=7)),
        summary="First routine",
    )
    doc = _run(create_supervision(payload, user=ADMIN))
    assert doc["status"] == "scheduled"
    assert doc["supervision_type"] == "routine"
    assert doc["recurring_compliance_id"]
    assert len(db.supervisions.docs) == 1
    assert len(db.recurring_compliance.docs) == 1
    rc = db.recurring_compliance.docs[0]
    assert rc["item_type"] == "supervision"
    assert rc["item_name"] == "routine"
    assert rc["frequency"] == "quarterly"
    # Audit trail stamped
    assert doc["audit_trail"][0]["action"] == "schedule_supervision"
    assert doc["created_by"] == "admin-1"


def test_create_supervision_rejects_applicant(_patch_db):
    payload = SupervisionCreate(
        employee_id="app-1",
        supervisor_id="u-1",
        supervision_type="routine",
        scheduled_at=_iso(NOW),
    )
    with pytest.raises(HTTPException) as exc:
        _run(create_supervision(payload, user=ADMIN))
    assert exc.value.status_code == 403


def test_create_supervision_rejects_invalid_type(_patch_db):
    payload = SupervisionCreate(
        employee_id="emp-1",
        supervisor_id="u-1",
        supervision_type="not_a_real_type",
        scheduled_at=_iso(NOW),
    )
    with pytest.raises(HTTPException) as exc:
        _run(create_supervision(payload, user=ADMIN))
    assert exc.value.status_code == 400


def test_complete_supervision_pushes_next_due_to_cadence(_patch_db):
    db = _patch_db
    payload = SupervisionCreate(
        employee_id="emp-1", supervisor_id="u-1",
        supervision_type="routine", scheduled_at=_iso(NOW),
    )
    created = _run(create_supervision(payload, user=ADMIN))

    completion = SupervisionComplete(
        completed_at=_iso(NOW),
        outcome="satisfactory",
        summary="Good",
        notes="None",
        actions=[],
    )
    result = _run(complete_supervision(created["id"], completion, user=ADMIN))
    assert result["status"] == "completed"
    assert result["outcome"] == "satisfactory"
    assert result["next_due_at"] is not None
    # Cadence row updated with last_completed_date and new next_due_date.
    rc = db.recurring_compliance.docs[0]
    assert rc["last_completed_date"] == _iso(NOW)
    assert rc["next_due_date"] == result["next_due_at"]
    # Audit trail has both create and complete entries.
    actions = [e["action"] for e in result["audit_trail"]]
    assert "schedule_supervision" in actions
    assert "complete_supervision" in actions


def test_complete_supervision_rejects_bad_outcome(_patch_db):
    payload = SupervisionCreate(
        employee_id="emp-1", supervisor_id="u-1",
        supervision_type="routine", scheduled_at=_iso(NOW),
    )
    created = _run(create_supervision(payload, user=ADMIN))
    completion = SupervisionComplete(
        completed_at=_iso(NOW), outcome="bogus",
    )
    with pytest.raises(HTTPException) as exc:
        _run(complete_supervision(created["id"], completion, user=ADMIN))
    assert exc.value.status_code == 400


def test_cancel_supervision_leaves_cadence_active(_patch_db):
    """Cancelling one occurrence must NOT deactivate the cadence row."""
    db = _patch_db
    payload = SupervisionCreate(
        employee_id="emp-1", supervisor_id="u-1",
        supervision_type="routine", scheduled_at=_iso(NOW + timedelta(days=7)),
    )
    created = _run(create_supervision(payload, user=ADMIN))

    result = _run(cancel_supervision(
        created["id"],
        SupervisionCancel(reason="supervisor_unavailable"),
        user=ADMIN,
    ))
    assert result["status"] == "cancelled"
    assert result["cancelled_reason"] == "supervisor_unavailable"
    # Cadence row still active.
    rc = db.recurring_compliance.docs[0]
    assert rc["is_active"] is True
    # Audit trail records the cancellation.
    actions = [e["action"] for e in result["audit_trail"]]
    assert actions[-1] == "cancel_supervision"
    assert result["audit_trail"][-1]["reason"] == "supervisor_unavailable"


def test_list_supervisions_rejects_applicant(_patch_db):
    # The path-level guard triggers via Depends() when FastAPI calls the
    # endpoint; we invoke the dependency directly to assert the 403.
    with pytest.raises(HTTPException) as exc:
        _run(_guard_employee_not_applicant("app-1", db=_patch_db))
    assert exc.value.status_code == 403


def test_list_supervisions_returns_items_and_summary_for_employee(_patch_db):
    db = _patch_db
    payload = SupervisionCreate(
        employee_id="emp-1", supervisor_id="u-1",
        supervision_type="routine",
        scheduled_at=_iso(NOW + timedelta(days=5)),
    )
    _run(create_supervision(payload, user=ADMIN))
    # Mark the just-created supervision verified so the verified-only
    # summary path counts it.
    db.supervisions.docs[0]["verification_status"] = "verified"

    # Emulate the path-level guard returning the employee doc.
    emp = _run(_guard_employee_not_applicant("emp-1", db=db))
    result = _run(list_supervisions(
        employee_id="emp-1", user=ADMIN, employee=emp,
    ))
    assert "items" in result and "summary" in result
    assert len(result["items"]) == 1
    # Summary must expose the UI fields the employee page renders.
    summary = result["summary"]
    for key in ("due_soon_count", "overdue_count", "completed_count",
                "last_completed_at", "next_due_at", "overdue"):
        assert key in summary
