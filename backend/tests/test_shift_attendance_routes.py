import os
import sys
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.shifts as shifts


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda d: d.get(field, ""), reverse=reverse)
        return self

    async def to_list(self, length):
        if length is None:
            return list(self._docs)
        return list(self._docs[:length])


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    @staticmethod
    def _matches(doc, query):
        for key, expected in (query or {}).items():
            if key == "$or":
                if not any(_FakeCollection._matches(doc, q) for q in expected):
                    return False
                continue
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
                if "$gte" in expected and (actual is None or actual < expected["$gte"]):
                    return False
                if "$lte" in expected and (actual is None or actual > expected["$lte"]):
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, query=None, projection=None):
        for doc in self.docs:
            if self._matches(doc, query or {}):
                return dict(doc)
        return None

    def find(self, query=None, projection=None):
        filtered = [dict(d) for d in self.docs if self._matches(d, query or {})]
        return _FakeCursor(filtered)

    async def insert_one(self, document):
        self.docs.append(dict(document))
        return SimpleNamespace(inserted_id=document.get("id"))

    async def update_one(self, query, update):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query or {}):
                merged = dict(doc)
                if "$set" in update:
                    merged.update(update["$set"])
                self.docs[index] = merged
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


class _FakeDb:
    def __init__(self):
        self.shifts = _FakeCollection([])
        self.shift_assignments = _FakeCollection([])
        self.shift_attendance_records = _FakeCollection([])
        self.care_locations = _FakeCollection([])
        self.employees = _FakeCollection(
            [
                {"id": "emp-active", "status": "active", "first_name": "A", "last_name": "Worker"},
                {"id": "emp-other", "status": "active", "first_name": "B", "last_name": "Worker"},
            ]
        )


def _seed_shift(db, shift_id="shift-1", status="assigned"):
    db.shifts.docs.append(
        {
            "id": shift_id,
            "start_at": "2026-06-01T09:00:00+00:00",
            "end_at": "2026-06-01T17:00:00+00:00",
            "location_text": "Main Location",
            "role_required": "Care Worker",
            "service_user_id": None,
            "care_location_id": None,
            "notes": None,
            "status": status,
            "assigned_employee_id": "emp-active",
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-01T00:00:00+00:00",
            "created_by": "mgr-1",
            "updated_by": "mgr-1",
        }
    )


def _seed_assignment(db, assignment_id="as-1", shift_id="shift-1", employee_id="emp-active", status="active"):
    db.shift_assignments.docs.append(
        {
            "id": assignment_id,
            "shift_id": shift_id,
            "employee_id": employee_id,
            "status": status,
            "assigned_at": "2026-05-01T00:00:00+00:00",
            "assigned_by": "mgr-1",
            "notes": None,
            "shift_start_at": "2026-06-01T09:00:00+00:00",
            "shift_end_at": "2026-06-01T17:00:00+00:00",
            "location_text": "Main Location",
            "role_required": "Care Worker",
            "service_user_id": None,
            "care_location_id": None,
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-01T00:00:00+00:00",
            "worker_response_status": "accepted",
            "worker_response_note": None,
            "worker_responded_at": "2026-05-01T00:00:00+00:00",
        }
    )


@pytest.fixture
def attendance_client(monkeypatch):
    fake_db = _FakeDb()
    audit_events = []

    async def _fake_audit(user_id, action, entity_type, entity_id, details=None):
        audit_events.append(
            {
                "user_id": user_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details or {},
            }
        )

    monkeypatch.setattr(shifts, "get_db", lambda: fake_db)
    monkeypatch.setattr(shifts, "log_audit_action", _fake_audit)

    app = FastAPI()
    app.include_router(shifts.router, prefix="/api")
    app.dependency_overrides[shifts.require_manager_or_admin] = lambda: {"user_id": "mgr-1", "role": "admin"}
    app.dependency_overrides[shifts.get_current_worker] = lambda: {"employee_id": "emp-active", "role": "worker"}
    return TestClient(app), fake_db, audit_events


def test_worker_clock_in_creates_open_attendance(attendance_client):
    client, db, _ = attendance_client
    _seed_shift(db)
    _seed_assignment(db)

    response = client.post("/api/worker/shifts/shift-1/clock-in", json={"note": "arrived"})
    assert response.status_code == 200
    row = response.json()["attendance"]
    assert row["status"] == "open"
    assert row["clock_in_note"] == "arrived"
    assert row["approved_for_timesheet"] is False


def test_worker_cannot_clock_in_twice_if_open_exists(attendance_client):
    client, db, _ = attendance_client
    _seed_shift(db)
    _seed_assignment(db)
    first = client.post("/api/worker/shifts/shift-1/clock-in", json={})
    assert first.status_code == 200

    second = client.post("/api/worker/shifts/shift-1/clock-in", json={})
    assert second.status_code == 409
    assert "Attendance already exists" in second.json()["detail"]


def test_worker_clock_out_requires_open_record(attendance_client):
    client, db, _ = attendance_client
    _seed_shift(db)
    _seed_assignment(db)

    response = client.post("/api/worker/shifts/shift-1/clock-out", json={"note": "done"})
    assert response.status_code == 409
    assert "No open attendance record" in response.json()["detail"]


def test_worker_clock_out_moves_open_to_submitted(attendance_client):
    client, db, _ = attendance_client
    _seed_shift(db)
    _seed_assignment(db)
    created = client.post("/api/worker/shifts/shift-1/clock-in", json={"note": "start"})
    assert created.status_code == 200

    out = client.post("/api/worker/shifts/shift-1/clock-out", json={"note": "finish"})
    assert out.status_code == 200
    row = out.json()["attendance"]
    assert row["status"] == "submitted"
    assert row["clock_out_note"] == "finish"
    assert row["clock_out_at"] is not None


def test_admin_can_list_and_get_attendance(attendance_client):
    client, db, _ = attendance_client
    _seed_shift(db)
    _seed_assignment(db)
    clock_in = client.post("/api/worker/shifts/shift-1/clock-in", json={})
    attendance_id = clock_in.json()["attendance"]["id"]
    client.post("/api/worker/shifts/shift-1/clock-out", json={})

    listed = client.get("/api/shift-attendance")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/api/shift-attendance/{attendance_id}")
    assert fetched.status_code == 200
    assert fetched.json()["attendance"]["id"] == attendance_id


def test_admin_approve_only_submitted_and_sets_timesheet_flag(attendance_client):
    client, db, _ = attendance_client
    _seed_shift(db)
    _seed_assignment(db)
    created = client.post("/api/worker/shifts/shift-1/clock-in", json={})
    attendance_id = created.json()["attendance"]["id"]

    blocked = client.post(f"/api/shift-attendance/{attendance_id}/approve", json={"reason": "ok"})
    assert blocked.status_code == 409

    client.post("/api/worker/shifts/shift-1/clock-out", json={})
    approved = client.post(f"/api/shift-attendance/{attendance_id}/approve", json={"reason": "checked"})
    assert approved.status_code == 200
    row = approved.json()["attendance"]
    assert row["status"] == "approved"
    assert row["approved_for_timesheet"] is True
    assert row["reviewed_by"] == "mgr-1"

    shift = next(s for s in db.shifts.docs if s["id"] == "shift-1")
    assert shift["status"] == "assigned"


def test_admin_reject_requires_reason_and_only_submitted(attendance_client):
    client, db, _ = attendance_client
    _seed_shift(db)
    _seed_assignment(db)
    created = client.post("/api/worker/shifts/shift-1/clock-in", json={})
    attendance_id = created.json()["attendance"]["id"]
    client.post("/api/worker/shifts/shift-1/clock-out", json={})

    no_reason = client.post(f"/api/shift-attendance/{attendance_id}/reject", json={"reason": ""})
    assert no_reason.status_code == 400

    rejected = client.post(f"/api/shift-attendance/{attendance_id}/reject", json={"reason": "missing details"})
    assert rejected.status_code == 200
    row = rejected.json()["attendance"]
    assert row["status"] == "rejected"
    assert row["approved_for_timesheet"] is False
    assert row["review_note"] == "missing details"


def test_audit_events_written_for_attendance_flow(attendance_client):
    client, db, audit_events = attendance_client
    _seed_shift(db)
    _seed_assignment(db)

    created = client.post("/api/worker/shifts/shift-1/clock-in", json={"note": "in"})
    attendance_id = created.json()["attendance"]["id"]
    out = client.post("/api/worker/shifts/shift-1/clock-out", json={"note": "out"})
    assert out.status_code == 200
    approved = client.post(f"/api/shift-attendance/{attendance_id}/approve", json={"reason": "ok"})
    assert approved.status_code == 200

    actions = [event["action"] for event in audit_events]
    assert "shift_clock_in" in actions
    assert "shift_clock_out" in actions
    assert "shift_attendance_approved" in actions

