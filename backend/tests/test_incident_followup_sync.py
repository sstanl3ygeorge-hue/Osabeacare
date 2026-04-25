"""Targeted tests for incident -> recurring follow-up synchronization."""

import os
import sys
from copy import deepcopy

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.compliance as compliance_module
from routes.dependencies import require_admin


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda d: d.get(field, ""), reverse=reverse)
        return self

    async def to_list(self, length):
        return list(self._docs[:length])


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    @staticmethod
    def _matches(doc, query):
        if not query:
            return True

        for key, expected in query.items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$exists" in expected:
                    exists = key in doc and doc.get(key) is not None
                    if bool(expected["$exists"]) != exists:
                        return False
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False

        return True

    @staticmethod
    def _project(doc, projection):
        if not projection:
            return deepcopy(doc)
        include_keys = [k for k, v in projection.items() if v and k != "_id"]
        if not include_keys:
            return deepcopy(doc)
        return {k: deepcopy(doc.get(k)) for k in include_keys}

    def find(self, query=None, projection=None):
        rows = [self._project(d, projection) for d in self.docs if self._matches(d, query)]
        return _FakeCursor(rows)

    async def find_one(self, query=None, projection=None, sort=None):
        rows = [d for d in self.docs if self._matches(d, query)]
        if sort:
            for field, direction in reversed(sort):
                reverse = direction == -1
                rows.sort(key=lambda d: d.get(field, ""), reverse=reverse)
        if not rows:
            return None
        return self._project(rows[0], projection)

    async def insert_one(self, doc):
        self.docs.append(deepcopy(doc))

    async def count_documents(self, query):
        return sum(1 for d in self.docs if self._matches(d, query))

    async def update_one(self, query, update):
        for idx, row in enumerate(self.docs):
            if not self._matches(row, query):
                continue
            if "$set" in update:
                for key, value in update["$set"].items():
                    row[key] = value
            if "$push" in update:
                for key, value in update["$push"].items():
                    row.setdefault(key, [])
                    row[key].append(value)
            self.docs[idx] = row
            return


class _FakeDb:
    def __init__(self):
        self.incident_logs = _FakeCollection([])
        self.recurring_compliance = _FakeCollection([])
        self.shifts = _FakeCollection([])
        self.amendments = _FakeCollection([])


def _make_client(monkeypatch):
    fake_db = _FakeDb()

    async def _fake_admin_user():
        return {"user_id": "admin-user-1", "role": "admin", "email": "admin@test.local"}

    async def _noop_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(compliance_module, "get_db", lambda: fake_db)
    monkeypatch.setattr(compliance_module, "log_audit_action", _noop_audit)

    app = FastAPI()
    app.include_router(compliance_module.router)
    app.dependency_overrides[require_admin] = _fake_admin_user

    return TestClient(app), fake_db


def _create_incident_payload(**overrides):
    payload = {
        "incident_type": "incident",
        "title": "Test incident",
        "description": "Test incident body",
        "date_occurred": "2026-04-25",
        "location": "Office",
        "safeguarding_concern": False,
        "escalation_required": False,
    }
    payload.update(overrides)
    return payload


def test_safeguarding_incident_creates_followup(monkeypatch):
    client, db = _make_client(monkeypatch)

    response = client.post("/compliance/incidents", json=_create_incident_payload(safeguarding_concern=True))
    assert response.status_code == 200, response.text

    created = response.json()
    assert created.get("follow_up_status") == "open"
    assert created.get("follow_up_due_date")

    recurring = db.recurring_compliance.docs
    assert len(recurring) == 1
    row = recurring[0]
    assert row.get("item_type") == "report_followup"
    assert row.get("linked_incident_id") == created["id"]
    assert row.get("is_active") is True
    assert row.get("status") == "open"


def test_escalation_incident_update_creates_followup(monkeypatch):
    client, db = _make_client(monkeypatch)

    create_res = client.post("/compliance/incidents", json=_create_incident_payload())
    assert create_res.status_code == 200, create_res.text
    incident = create_res.json()
    assert incident.get("follow_up_status") in (None, "")

    update_res = client.put(
        f"/compliance/incidents/{incident['id']}",
        json={"escalation_required": True},
    )
    assert update_res.status_code == 200, update_res.text
    updated = update_res.json()

    assert updated.get("follow_up_status") == "open"
    assert updated.get("follow_up_due_date")

    recurring_rows = db.recurring_compliance.docs
    assert len(recurring_rows) == 1
    assert recurring_rows[0].get("linked_incident_id") == incident["id"]
    assert recurring_rows[0].get("is_active") is True


def test_closing_incident_closes_followup(monkeypatch):
    client, db = _make_client(monkeypatch)

    create_res = client.post("/compliance/incidents", json=_create_incident_payload(safeguarding_concern=True))
    assert create_res.status_code == 200, create_res.text
    incident = create_res.json()

    close_res = client.put(
        f"/compliance/incidents/{incident['id']}",
        json={"status": "closed"},
    )
    assert close_res.status_code == 200, close_res.text
    closed = close_res.json()

    assert closed.get("follow_up_status") == "closed"

    recurring_rows = db.recurring_compliance.docs
    assert len(recurring_rows) == 1
    assert recurring_rows[0].get("linked_incident_id") == incident["id"]
    assert recurring_rows[0].get("is_active") is False
    assert recurring_rows[0].get("status") == "closed"
