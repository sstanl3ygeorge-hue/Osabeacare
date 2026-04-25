import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.readiness as readiness


class _FakeSummaryCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def find_one(self, query=None, projection=None):
        employee_id = (query or {}).get("employee_id")
        for doc in self.docs:
            if doc.get("employee_id") == employee_id:
                return dict(doc)
        return None


class _FakeDb:
    def __init__(self, summary_docs=None):
        self.employee_compliance_summary = _FakeSummaryCollection(summary_docs or [])


class _FakeEmployeesRepo:
    def __init__(self, employees):
        self._employees = list(employees)

    async def list_employees(self, projection=None):
        return list(self._employees)


def _make_app(monkeypatch):
    employees = [
        {"id": "e-compliant", "first_name": "Alice", "last_name": "Green", "role": "Care Assistant", "job_title": "Care Assistant"},
        {"id": "e-missing", "first_name": "Ben", "last_name": "Blue", "role": "Care Assistant", "job_title": "Care Assistant"},
        {"id": "e-expired", "first_name": "Cara", "last_name": "Stone", "role": "Nurse", "job_title": "Nurse"},
        {"id": "e-expiring", "first_name": "Dan", "last_name": "Hill", "role": "Support Worker", "job_title": "Support Worker"},
    ]

    requirements_by_employee = {
        "e-compliant": [
            {"id": "rtw", "name": "Right to Work", "status": "complete"},
            {"id": "dbs", "name": "DBS", "status": "complete"},
        ],
        "e-missing": [
            {"id": "employment_history_verification", "name": "Employment History", "status": "missing"},
            {"id": "dbs", "name": "DBS", "status": "pending"},
        ],
        "e-expired": [
            {"id": "dbs", "name": "DBS", "status": "expired"},
        ],
        "e-expiring": [
            {"id": "rtw", "name": "Right to Work", "status": "expiring_soon"},
        ],
    }

    summary_docs = [
        {
            "employee_id": "e-missing",
            "blockers": [{"reason": "Missing right to work evidence"}],
            "warnings": [{"message": "Reference check pending"}],
        }
    ]

    async def _fake_get_compliance_requirements_for_employee(employee_id, role):
        return {"statuses": {"requirements": requirements_by_employee.get(employee_id, [])}}

    async def _fake_calculate_work_readiness_3tier(employee_id, requirements, employee_data, role):
        if employee_id == "e-missing":
            return {
                "status": "NOT_READY",
                "reasons": [
                    {"type": "hard_block", "message": "Employment history not verified"},
                    {"type": "conditional", "message": "Reference checks still in progress"},
                ],
            }
        if employee_id == "e-expired":
            return {
                "status": "NOT_READY",
                "reasons": [{"type": "hard_block", "message": "DBS has expired"}],
            }
        if employee_id == "e-expiring":
            return {
                "status": "READY_WITH_CONDITIONS",
                "reasons": [{"type": "conditional", "message": "RTW expires soon"}],
            }
        return {"status": "READY_TO_WORK", "reasons": []}

    monkeypatch.setattr(readiness, "get_employees_repo", lambda: _FakeEmployeesRepo(employees))
    monkeypatch.setattr(readiness, "get_compliance_requirements_func", lambda: _fake_get_compliance_requirements_for_employee)
    monkeypatch.setattr(readiness, "get_work_readiness_3tier_func", lambda: _fake_calculate_work_readiness_3tier)
    monkeypatch.setattr(readiness, "get_db", lambda: _FakeDb(summary_docs))

    app = FastAPI()
    app.include_router(readiness.router, prefix="/api")
    app.dependency_overrides[readiness.require_manager_or_admin] = lambda: {"user_id": "mgr-1", "role": "admin"}

    return TestClient(app)


def test_staff_compliance_dashboard_all(monkeypatch):
    client = _make_app(monkeypatch)

    response = client.get("/api/staff/compliance-dashboard")
    assert response.status_code == 200

    payload = response.json()
    assert payload["filter"] == "all"
    assert payload["total"] == 4

    rows = {row["employee_id"]: row for row in payload["items"]}

    assert rows["e-compliant"]["overall_status"] == "compliant"
    assert rows["e-compliant"]["compliant"] is True

    assert rows["e-missing"]["overall_status"] == "missing"
    assert "Employment History" in rows["e-missing"]["missing_items"]
    assert "Missing right to work evidence" in rows["e-missing"]["blockers"]
    assert "Reference checks still in progress" in rows["e-missing"]["warnings"]

    assert rows["e-expired"]["overall_status"] == "expired"
    assert "DBS" in rows["e-expired"]["expired_items"]

    assert rows["e-expiring"]["overall_status"] == "expiring"
    assert "Right to Work" in rows["e-expiring"]["expiring_soon"]


def test_staff_compliance_dashboard_filter(monkeypatch):
    client = _make_app(monkeypatch)

    response = client.get("/api/staff/compliance-dashboard", params={"status": "expired"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["filter"] == "expired"
    assert payload["total"] == 1
    assert payload["items"][0]["employee_id"] == "e-expired"


def test_staff_compliance_dashboard_invalid_filter(monkeypatch):
    client = _make_app(monkeypatch)

    response = client.get("/api/staff/compliance-dashboard", params={"status": "bad-value"})
    assert response.status_code == 400
