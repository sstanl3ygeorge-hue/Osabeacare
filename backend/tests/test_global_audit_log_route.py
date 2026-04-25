"""Targeted tests for GET /api/audit/global-log endpoint."""
import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.audit_email as audit_email_module


# ---------------------------------------------------------------------------
# Minimal fake infrastructure
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda d: d.get(field, ""), reverse=reverse)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
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
            if key == "$and":
                if not all(_FakeCollection._matches(doc, sub) for sub in expected):
                    return False
                continue
            if key == "$or":
                if not any(_FakeCollection._matches(doc, sub) for sub in expected):
                    return False
                continue
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$gte" in expected and actual < expected["$gte"]:
                    return False
                if "$lte" in expected and actual > expected["$lte"]:
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False
        return True

    def find(self, query=None, projection=None):
        return _FakeCursor([dict(d) for d in self.docs if self._matches(d, query)])

    async def find_one(self, query=None, projection=None):
        matches = [d for d in self.docs if self._matches(d, query)]
        return dict(matches[0]) if matches else None


class _FakeDb:
    def __init__(self, audit_logs=None, users=None):
        self.audit_logs = _FakeCollection(audit_logs or [])
        self.users = _FakeCollection(users or [])


def _make_app(monkeypatch, db):
    monkeypatch.setattr(audit_email_module, "get_db", lambda: db)

    # Stub auth: require_manager_or_admin returns a manager user
    async def _fake_manager():
        return {"user_id": "mgr-001", "role": "branch_manager", "email": "mgr@example.com"}

    from routes.dependencies import require_manager_or_admin
    app = FastAPI()
    app.include_router(audit_email_module.router)

    # Override auth dependency
    app.dependency_overrides[require_manager_or_admin] = _fake_manager

    return TestClient(app)


# ---------------------------------------------------------------------------
# Sample log documents
# ---------------------------------------------------------------------------

_LOG_A = {
    "id": "log-a",
    "user_id": "usr-1",
    "action": "shift_attendance_approved",
    "resource_type": "shift_attendance",
    "resource_id": "att-001",
    "details": {"shift_id": "sh-1", "employee_id": "emp-1"},
    "timestamp": "2026-04-20T10:00:00Z",
}

_LOG_B = {
    "id": "log-b",
    "user_id": "usr-2",
    "action": "activate_service_user_care_plan",
    "resource_type": "service_user_care_plan",
    "resource_id": "cp-001",
    "details": {"service_user_id": "su-1"},
    "timestamp": "2026-04-21T09:00:00Z",
}

_LOG_C = {
    "id": "log-c",
    "user_id": "usr-1",
    "action": "create_incident",
    "resource_type": "incident_log",
    "resource_id": "inc-001",
    "details": {"type": "incident"},
    "timestamp": "2026-04-22T08:00:00Z",
}

_USERS = [
    {"user_id": "usr-1", "name": "Alice Manager", "email": "alice@example.com"},
    {"user_id": "usr-2", "name": "Bob Admin", "email": "bob@example.com"},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_global_log_returns_all_when_no_filters(monkeypatch):
    """With no filters all logs are returned, newest first."""
    db = _FakeDb(audit_logs=[_LOG_A, _LOG_B, _LOG_C], users=_USERS)
    client = _make_app(monkeypatch, db)

    resp = client.get("/audit/global-log")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    # Newest first (LOG_C has latest timestamp)
    assert data["logs"][0]["id"] == "log-c"
    # Actor name should be enriched
    assert data["logs"][0]["actor_name"] == "Alice Manager"


def test_global_log_filter_by_resource_type(monkeypatch):
    """resource_type filter narrows results correctly."""
    db = _FakeDb(audit_logs=[_LOG_A, _LOG_B, _LOG_C], users=_USERS)
    client = _make_app(monkeypatch, db)

    resp = client.get("/audit/global-log", params={"resource_type": "shift_attendance"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["logs"][0]["resource_type"] == "shift_attendance"
    assert data["logs"][0]["action"] == "shift_attendance_approved"


def test_global_log_filter_by_action(monkeypatch):
    """action filter narrows results correctly."""
    db = _FakeDb(audit_logs=[_LOG_A, _LOG_B, _LOG_C], users=_USERS)
    client = _make_app(monkeypatch, db)

    resp = client.get("/audit/global-log", params={"action": "create_incident"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["logs"][0]["id"] == "log-c"


def test_global_log_filter_by_date_from(monkeypatch):
    """date_from filters to logs on or after that date."""
    db = _FakeDb(audit_logs=[_LOG_A, _LOG_B, _LOG_C], users=_USERS)
    client = _make_app(monkeypatch, db)

    # Only LOG_C is on 2026-04-22
    resp = client.get("/audit/global-log", params={"date_from": "2026-04-22"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["logs"][0]["id"] == "log-c"


def test_global_log_filter_by_date_range(monkeypatch):
    """date_from + date_to works together."""
    db = _FakeDb(audit_logs=[_LOG_A, _LOG_B, _LOG_C], users=_USERS)
    client = _make_app(monkeypatch, db)

    # Should capture LOG_A and LOG_B (Apr 20–21), exclude LOG_C (Apr 22)
    resp = client.get("/audit/global-log", params={"date_from": "2026-04-20", "date_to": "2026-04-21"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    ids = {d["id"] for d in data["logs"]}
    assert ids == {"log-a", "log-b"}


def test_global_log_empty_when_no_match(monkeypatch):
    """Returns empty list gracefully when no logs match filters."""
    db = _FakeDb(audit_logs=[_LOG_A, _LOG_B, _LOG_C], users=_USERS)
    client = _make_app(monkeypatch, db)

    resp = client.get("/audit/global-log", params={"action": "nonexistent_action"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["logs"] == []
