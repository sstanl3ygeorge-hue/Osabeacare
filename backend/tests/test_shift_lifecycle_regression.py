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
        return list(self._docs if length is None else self._docs[:length])


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
                if "$set" in update:
                    merged = dict(doc)
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
        self.audit_logs = _FakeCollection([])
        self.care_locations = _FakeCollection([])
        self.service_users = _FakeCollection([
            {"id": "su-1", "full_name": "Alex Example"},
        ])
        self.employees = _FakeCollection(
            [
                {
                    "id": "emp-active",
                    "first_name": "Active",
                    "last_name": "Worker",
                    "status": "active",
                    "role": "Healthcare Assistant",
                },
                {
                    "id": "emp-onboarding",
                    "first_name": "Onboard",
                    "last_name": "Worker",
                    "status": "onboarding",
                    "role": "Healthcare Assistant",
                },
                {
                    "id": "emp-nurse",
                    "first_name": "Nina",
                    "last_name": "Nurse",
                    "status": "active",
                    "role": "Nurse",
                },
                {
                    "id": "emp-rn",
                    "first_name": "Rory",
                    "last_name": "Registered",
                    "status": "active",
                    "role": "RN",
                },
            ]
        )


def _seed_shift(db, *, shift_id, status="open", assigned_employee_id=None, start_at=None, end_at=None, role_required="Care Worker"):
    db.shifts.docs.append(
        {
            "id": shift_id,
            "start_at": start_at or "2026-05-01T09:00:00+00:00",
            "end_at": end_at or "2026-05-01T17:00:00+00:00",
            "location_text": "Main Branch",
            "role_required": role_required,
            "service_user_id": None,
            "notes": None,
            "status": status,
            "assigned_employee_id": assigned_employee_id,
            "created_at": "2026-04-24T10:00:00+00:00",
            "updated_at": "2026-04-24T10:00:00+00:00",
            "created_by": "mgr-1",
            "updated_by": "mgr-1",
        }
    )


def _seed_assignment(
    db,
    *,
    assignment_id,
    shift_id,
    employee_id,
    status="active",
    worker_response_status="pending",
    shift_start_at="2026-05-01T09:00:00+00:00",
    shift_end_at="2026-05-01T17:00:00+00:00",
):
    db.shift_assignments.docs.append(
        {
            "id": assignment_id,
            "shift_id": shift_id,
            "employee_id": employee_id,
            "status": status,
            "assigned_at": "2026-04-24T10:00:00+00:00",
            "assigned_by": "mgr-1",
            "notes": None,
            "shift_start_at": shift_start_at,
            "shift_end_at": shift_end_at,
            "location_text": "Main Branch",
            "role_required": "Care Worker",
            "service_user_id": None,
            "created_at": "2026-04-24T10:00:00+00:00",
            "updated_at": "2026-04-24T10:00:00+00:00",
            "worker_response_status": worker_response_status,
            "worker_response_note": None,
            "worker_responded_at": None,
        }
    )


@pytest.fixture
def shift_client(monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(shifts, "get_db", lambda: fake_db)

    app = FastAPI()
    app.include_router(shifts.router, prefix="/api")
    app.dependency_overrides[shifts.require_manager_or_admin] = lambda: {
        "user_id": "mgr-1",
        "role": "admin",
        "name": "Manager",
    }
    app.dependency_overrides[shifts.get_current_worker] = lambda: {
        "employee_id": "emp-active",
        "role": "worker",
    }
    return TestClient(app), fake_db


def test_cannot_assign_onboarding_employee(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-1", status="open")

    response = client.post("/api/shifts/s-1/assign", json={"employee_id": "emp-onboarding"})

    assert response.status_code == 409
    assert "shift-eligible" in response.json()["detail"]


@pytest.mark.parametrize("shift_status", ["completed", "cancelled"])
def test_cannot_assign_completed_or_cancelled_shift(shift_client, shift_status):
    client, db = shift_client
    _seed_shift(db, shift_id=f"s-{shift_status}", status=shift_status)

    response = client.post(
        f"/api/shifts/s-{shift_status}/assign",
        json={"employee_id": "emp-active"},
    )

    assert response.status_code == 409
    assert "completed/cancelled" in response.json()["detail"]


def test_cannot_complete_open_unassigned_shift(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-open", status="open")

    response = client.post("/api/shifts/s-open/complete")

    assert response.status_code == 409
    assert "unassigned" in response.json()["detail"]


def test_cannot_edit_time_with_active_assignment(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-2", status="assigned", assigned_employee_id="emp-active")
    _seed_assignment(db, assignment_id="a-2", shift_id="s-2", employee_id="emp-active")

    response = client.patch(
        "/api/shifts/s-2",
        json={
            "start_at": "2026-05-01T10:00:00+00:00",
            "end_at": "2026-05-01T18:00:00+00:00",
        },
    )

    assert response.status_code == 409
    assert "active assignment exists" in response.json()["detail"]


def test_cannot_reject_after_accepting(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-3", status="assigned", assigned_employee_id="emp-active")
    _seed_assignment(db, assignment_id="a-3", shift_id="s-3", employee_id="emp-active")

    accept_response = client.post("/api/worker/shifts/s-3/accept", json={"note": "I can do this"})
    reject_response = client.post("/api/worker/shifts/s-3/reject", json={"note": "actually no"})

    assert accept_response.status_code == 200
    assert reject_response.status_code == 409
    assert "cannot be rejected" in reject_response.json()["detail"].lower()


def test_worker_cannot_accept_or_reject_cancelled_assignment(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-4", status="cancelled")
    _seed_assignment(
        db,
        assignment_id="a-4",
        shift_id="s-4",
        employee_id="emp-active",
        status="cancelled",
    )

    accept_response = client.post("/api/worker/shifts/s-4/accept", json={"note": "ok"})
    reject_response = client.post("/api/worker/shifts/s-4/reject", json={"note": "not ok"})

    assert accept_response.status_code == 409
    assert reject_response.status_code == 409
    assert "no longer active" in accept_response.json()["detail"].lower()
    assert "no longer active" in reject_response.json()["detail"].lower()


def test_overlap_prevention_blocks_second_active_assignment(shift_client):
    client, db = shift_client
    _seed_shift(
        db,
        shift_id="s-5a",
        status="open",
        start_at="2026-05-01T09:00:00+00:00",
        end_at="2026-05-01T13:00:00+00:00",
    )
    _seed_shift(
        db,
        shift_id="s-5b",
        status="open",
        start_at="2026-05-01T12:00:00+00:00",
        end_at="2026-05-01T16:00:00+00:00",
    )

    first_assign = client.post("/api/shifts/s-5a/assign", json={"employee_id": "emp-active"})
    second_assign = client.post("/api/shifts/s-5b/assign", json={"employee_id": "emp-active"})

    assert first_assign.status_code == 200
    assert second_assign.status_code == 409
    assert "overlapping active shift assignment" in second_assign.json()["detail"].lower()


def test_shift_assignment_blocks_obvious_nurse_hca_mismatch(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-role-mismatch", status="open", role_required="Registered Nurse")

    response = client.post("/api/shifts/s-role-mismatch/assign", json={"employee_id": "emp-active"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Worker role does not match shift role requirement"


def test_shift_assignment_allows_tolerant_nurse_match_for_rn_label(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-role-rn", status="open", role_required="Nurse")

    response = client.post("/api/shifts/s-role-rn/assign", json={"employee_id": "emp-rn"})

    assert response.status_code == 200
    assert response.json()["assignment"]["employee_id"] == "emp-rn"


def test_shift_assignment_keeps_legacy_unknown_role_labels_permissive(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-role-legacy", status="open", role_required="Complex Package Team A")

    response = client.post("/api/shifts/s-role-legacy/assign", json={"employee_id": "emp-active"})

    assert response.status_code == 200
    assert response.json()["assignment"]["employee_id"] == "emp-active"


def test_cancel_assigned_shift_records_reason_and_closes_assignment(shift_client):
    client, db = shift_client
    _seed_shift(db, shift_id="s-6", status="assigned", assigned_employee_id="emp-active")
    _seed_assignment(db, assignment_id="a-6", shift_id="s-6", employee_id="emp-active", status="active")

    response = client.patch(
        "/api/shifts/s-6",
        json={"status": "cancelled", "cancel_reason": "Client canceled visit"},
    )

    assert response.status_code == 200

    shift = next(item for item in db.shifts.docs if item["id"] == "s-6")
    assignment = next(item for item in db.shift_assignments.docs if item["id"] == "a-6")

    assert shift["status"] == "cancelled"
    assert shift["cancelled_reason"] == "Client canceled visit"
    assert shift["assigned_employee_id"] is None

    assert assignment["status"] == "cancelled"
    assert assignment["unassign_reason"] == "Client canceled visit"
    assert assignment.get("ended_at") is not None


def test_create_shift_normalizes_blank_optional_ids_to_none(shift_client):
    client, _ = shift_client

    response = client.post(
        "/api/shifts",
        json={
            "start_at": "2026-05-03T09:00:00Z",
            "end_at": "2026-05-03T17:00:00Z",
            "location_text": "london",
            "role_required": "HCA",
            "service_user_id": "   ",
            "care_location_id": "none",
            "notes": None,
        },
    )

    assert response.status_code == 200
    shift = response.json()["shift"]
    assert shift["service_user_id"] is None
    assert shift["care_location_id"] is None


def test_create_shift_invalid_optional_ids_return_400(shift_client):
    client, _ = shift_client

    invalid_service_user = client.post(
        "/api/shifts",
        json={
            "start_at": "2026-05-04T09:00:00Z",
            "end_at": "2026-05-04T17:00:00Z",
            "location_text": "london",
            "role_required": "HCA",
            "service_user_id": "unknown-su",
            "care_location_id": None,
        },
    )
    assert invalid_service_user.status_code == 400
    assert invalid_service_user.json()["detail"] == "Invalid service_user_id"

    invalid_care_location = client.post(
        "/api/shifts",
        json={
            "start_at": "2026-05-05T09:00:00Z",
            "end_at": "2026-05-05T17:00:00Z",
            "location_text": "london",
            "role_required": "HCA",
            "service_user_id": None,
            "care_location_id": "unknown-location",
        },
    )
    assert invalid_care_location.status_code == 400
    assert invalid_care_location.json()["detail"] == "Invalid care_location_id"


def test_list_and_detail_hydrate_service_user_name(shift_client):
    client, db = shift_client

    db.shifts.docs.append(
        {
            "id": "s-service-user",
            "start_at": "2026-05-01T09:00:00+00:00",
            "end_at": "2026-05-01T11:00:00+00:00",
            "location_text": "Alex Example visit",
            "role_required": "Care Worker",
            "service_user_id": "su-1",
            "care_location_id": None,
            "notes": None,
            "status": "open",
            "assigned_employee_id": None,
            "created_at": "2026-04-24T10:00:00+00:00",
            "updated_at": "2026-04-24T10:00:00+00:00",
            "created_by": "mgr-1",
            "updated_by": "mgr-1",
        }
    )

    list_response = client.get("/api/shifts")
    detail_response = client.get("/api/shifts/s-service-user")

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert list_response.json()["shifts"][0]["service_user_name"] == "Alex Example"
    assert detail_response.json()["shift"]["service_user_name"] == "Alex Example"


def test_worker_shift_hydrates_service_user_name(shift_client):
    client, db = shift_client

    _seed_shift(db, shift_id="s-worker", status="assigned", assigned_employee_id="emp-active")
    db.shifts.docs[-1]["service_user_id"] = "su-1"
    db.shifts.docs[-1]["location_text"] = "Alex Example visit"
    _seed_assignment(db, assignment_id="a-worker", shift_id="s-worker", employee_id="emp-active")

    response = client.get("/api/worker/shifts")

    assert response.status_code == 200
    assert response.json()["shifts"][0]["shift"]["service_user_name"] == "Alex Example"
