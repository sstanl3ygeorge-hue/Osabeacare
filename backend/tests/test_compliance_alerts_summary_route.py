"""Targeted tests for GET /api/compliance/alerts-summary endpoint."""
import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.readiness as readiness_module


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
            if key == "$or":
                if not any(_FakeCollection._matches(doc, sub) for sub in expected):
                    return False
                continue

            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$exists" in expected:
                    exists = key in doc and doc.get(key) is not None
                    if bool(expected["$exists"]) != exists:
                        return False
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$lte" in expected and not (actual <= expected["$lte"]):
                    return False
                if "$gte" in expected and not (actual >= expected["$gte"]):
                    return False
            elif actual != expected:
                return False

        return True

    def _project(self, doc, projection):
        if not projection:
            return dict(doc)
        include_keys = [k for k, v in projection.items() if v and k != "_id"]
        if not include_keys:
            return dict(doc)
        return {k: doc.get(k) for k in include_keys}

    def find(self, query=None, projection=None):
        rows = [self._project(d, projection) for d in self.docs if self._matches(d, query)]
        return _FakeCursor(rows)

    async def find_one(self, query=None, projection=None, sort=None):
        rows = [self._project(d, projection) for d in self.docs if self._matches(d, query)]
        if sort:
            for field, direction in reversed(sort):
                reverse = direction == -1
                rows.sort(key=lambda r: r.get(field, ""), reverse=reverse)
        return dict(rows[0]) if rows else None


class _FakeDb:
    def __init__(self):
        self.employee_documents = _FakeCollection([
            {
                "employee_id": "emp-1",
                "document_type": "dbs",
                "expiry_date": "2026-01-01T10:00:00Z",
                "status": "active",
            },
            {
                "employee_id": "emp-2",
                "document_type": "right_to_work",
                "expiry_date": "2027-12-01T10:00:00Z",
                "status": "active",
            },
        ])
        self.training_records = _FakeCollection([
            {
                "employee_id": "emp-1",
                "training_name": "Safeguarding",
                "expiry_date": "2026-05-01T10:00:00Z",
                "record_status": "active",
            },
            {
                "employee_id": "emp-2",
                "training_name": "Medication",
                "expiry_date": "2028-05-01T10:00:00Z",
                "record_status": "active",
            },
        ])
        self.employees = _FakeCollection([
            {"id": "emp-1", "first_name": "Ada", "last_name": "Stone"},
            {"id": "emp-2", "first_name": "Ben", "last_name": "Lee"},
        ])
        self.service_user_care_plans = _FakeCollection([
            {
                "id": "cp-1",
                "service_user_id": "su-1",
                "care_plan_title": "Care Plan A",
                "status": "active",
                "next_review_due_at": "2026-01-05T10:00:00Z",
            },
            {
                "id": "cp-2",
                "service_user_id": "su-2",
                "care_plan_title": "Care Plan B",
                "status": "active",
                "next_review_due_at": "2028-01-05T10:00:00Z",
            },
        ])
        self.service_users = _FakeCollection([
            {"id": "su-1", "full_name": "Grace Young", "service_user_code": "SU-1"},
            {"id": "su-2", "full_name": "Imran Cole", "service_user_code": "SU-2"},
        ])
        self.incident_logs = _FakeCollection([
            {
                "id": "inc-1",
                "incident_type": "safeguarding",
                "safeguarding_concern": True,
                "status": "open",
                "date_occurred": "2026-04-20T09:00:00Z",
                "service_user_id": "su-1",
                "service_user_name": "Grace Young",
            },
            {
                "id": "inc-2",
                "incident_type": "incident",
                "safeguarding_concern": False,
                "status": "open",
                "date_occurred": "2026-04-20T10:00:00Z",
                "service_user_id": "su-2",
            },
        ])


def _make_client(monkeypatch):
    db = _FakeDb()

    monkeypatch.setattr(readiness_module, "get_db", lambda: db)
    monkeypatch.setattr(readiness_module, "get_excluded_doc_statuses", lambda: {"deleted", "replaced"})

    async def _fake_staff_dashboard(status: str = "all", user=None):
        assert status == "missing"
        return {
            "items": [
                {
                    "employee_id": "emp-1",
                    "employee_name": "Ada Stone",
                    "missing_items": ["DBS", "Right to work"],
                }
            ]
        }

    monkeypatch.setattr(readiness_module, "get_staff_compliance_dashboard", _fake_staff_dashboard)

    async def _fake_onboarding_reader(service_user_id: str, user=None):
        if service_user_id == "su-1":
            return {"overall_status": "missing", "missing_count": 2, "review_due_count": 0}
        return {"overall_status": "ready", "missing_count": 0, "review_due_count": 0}

    monkeypatch.setattr(
        readiness_module,
        "get_service_user_onboarding_readiness_func",
        lambda: _fake_onboarding_reader,
    )

    async def _fake_manager():
        return {"user_id": "mgr-1", "role": "branch_manager"}

    from routes.dependencies import require_manager_or_admin

    app = FastAPI()
    app.include_router(readiness_module.router)
    app.dependency_overrides[require_manager_or_admin] = _fake_manager

    return TestClient(app)


def test_alerts_summary_returns_normalized_alert_rows(monkeypatch):
    client = _make_client(monkeypatch)

    response = client.get("/compliance/alerts-summary")
    assert response.status_code == 200

    payload = response.json()
    assert "alerts" in payload
    assert "counts" in payload
    assert payload["total"] > 0

    first = payload["alerts"][0]
    assert "title" in first
    assert "category" in first
    assert "severity" in first
    assert "entity_type" in first
    assert "entity_id" in first
    assert "entity_name" in first
    assert "link_target" in first
    assert "source" in first

    severities = {row.get("severity") for row in payload["alerts"]}
    assert "urgent" in severities
    assert "warning" in severities
    assert "missing" in severities
    assert "safeguarding" in severities


def test_alerts_summary_limit_is_applied(monkeypatch):
    client = _make_client(monkeypatch)

    response = client.get("/compliance/alerts-summary", params={"limit": 2})
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["alerts"]) == 2
