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
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, query=None, projection=None, sort=None):
        rows = [dict(doc) for doc in self.docs if self._matches(doc, query or {})]
        if sort:
            field, direction = sort[0]
            rows.sort(key=lambda d: d.get(field, ""), reverse=direction == -1)
        return rows[0] if rows else None

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
        self.shift_daily_notes = _FakeCollection([])
        self.care_locations = _FakeCollection([
            {"id": "loc-1", "name": "Main Home", "is_active": True}
        ])
        self.service_users = _FakeCollection([
            {"id": "su-1", "full_name": "Service User One", "service_user_code": "SU001"}
        ])
        self.employees = _FakeCollection([
            {"id": "emp-1", "status": "active", "first_name": "Alex", "last_name": "Carer", "employee_code": "EMP001"}
        ])


def _seed_shift(db, shift_id="shift-1"):
    db.shifts.docs.append(
        {
            "id": shift_id,
            "start_at": "2026-06-01T09:00:00+00:00",
            "end_at": "2026-06-01T17:00:00+00:00",
            "location_text": "Ward A",
            "role_required": "Care Worker",
            "service_user_id": "su-1",
            "care_location_id": "loc-1",
            "notes": None,
            "status": "assigned",
            "assigned_employee_id": "emp-1",
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-01T00:00:00+00:00",
            "created_by": "mgr-1",
            "updated_by": "mgr-1",
        }
    )


def _seed_assignment(db, shift_id="shift-1"):
    db.shift_assignments.docs.append(
        {
            "id": "as-1",
            "shift_id": shift_id,
            "employee_id": "emp-1",
            "status": "active",
            "assigned_at": "2026-05-01T00:00:00+00:00",
            "assigned_by": "mgr-1",
            "notes": None,
            "shift_start_at": "2026-06-01T09:00:00+00:00",
            "shift_end_at": "2026-06-01T17:00:00+00:00",
            "location_text": "Ward A",
            "role_required": "Care Worker",
            "service_user_id": "su-1",
            "care_location_id": "loc-1",
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-01T00:00:00+00:00",
            "worker_response_status": "accepted",
            "worker_response_note": None,
            "worker_responded_at": "2026-05-01T00:00:00+00:00",
        }
    )


@pytest.fixture
def daily_notes_client(monkeypatch):
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
    app.dependency_overrides[shifts.get_current_worker] = lambda: {"employee_id": "emp-1", "role": "worker"}
    return TestClient(app), fake_db, audit_events


def test_worker_can_create_shift_daily_note(daily_notes_client):
    client, db, _ = daily_notes_client
    _seed_shift(db)
    _seed_assignment(db)

    response = client.post(
        "/api/worker/shifts/shift-1/daily-notes",
        json={"note_text": "Ate full breakfast and hydrated well", "tags": ["nutrition", "mood"]},
    )
    assert response.status_code == 200
    payload = response.json()["daily_note"]
    assert payload["service_user_id"] == "su-1"
    assert payload["shift_id"] == "shift-1"
    assert payload["employee_id"] == "emp-1"
    assert payload["tags"] == ["nutrition", "mood"]


def test_worker_cannot_create_duplicate_shift_daily_note(daily_notes_client):
    client, db, _ = daily_notes_client
    _seed_shift(db)
    _seed_assignment(db)

    first = client.post(
        "/api/worker/shifts/shift-1/daily-notes",
        json={"note_text": "Initial observation", "tags": []},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/worker/shifts/shift-1/daily-notes",
        json={"note_text": "Second observation", "tags": ["mood"]},
    )
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_admin_can_list_service_user_daily_notes_timeline(daily_notes_client):
    client, db, _ = daily_notes_client
    _seed_shift(db)
    _seed_assignment(db)

    created = client.post(
        "/api/worker/shifts/shift-1/daily-notes",
        json={"note_text": "Client calm and cooperative", "tags": ["mood"]},
    )
    assert created.status_code == 200

    listed = client.get("/api/service-users/su-1/daily-notes")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    row = body["daily_notes"][0]
    assert row["employee_name"] == "Alex Carer"
    assert row["employee_code"] == "EMP001"
    assert row["shift_location_text"] == "Ward A"
    assert row["shift_role_required"] == "Care Worker"
    assert row["care_location_name"] == "Main Home"
