import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.worker_dashboard as worker_dashboard


class _FakeCollection:
    def __init__(self, responder):
        self._responder = responder

    async def find_one(self, query=None, projection=None, sort=None):
        return self._responder(query or {}, projection, sort)


class _FakeDb:
    def __init__(self, *, form_status: str, health_status):
        self.employees = _FakeCollection(self._employees_find_one)
        self.form_progress = _FakeCollection(self._form_progress_find_one)
        self.form_submissions = _FakeCollection(self._form_submissions_find_one)
        self.health_declarations = _FakeCollection(self._health_declarations_find_one)
        self._form_status = form_status
        self._health_status = health_status

    def _employees_find_one(self, query, projection, sort):
        if query.get("id") == "emp-1":
            return {"id": "emp-1", "role": "healthcare_assistant"}
        return None

    def _form_progress_find_one(self, query, projection, sort):
        return None

    def _form_submissions_find_one(self, query, projection, sort):
        if query.get("employee_id") != "emp-1":
            return None
        if query.get("form_type") != "staff_health_questionnaire":
            return None
        return {
            "id": "sub-1",
            "employee_id": "emp-1",
            "form_type": "staff_health_questionnaire",
            "status": self._form_status,
            "submitted_at": "2026-04-23T10:00:00+00:00",
        }

    def _health_declarations_find_one(self, query, projection, sort):
        if query.get("employee_id") != "emp-1":
            return None
        if self._health_status is None:
            return None
        return {"employee_id": "emp-1", "status": self._health_status}


def _make_client(monkeypatch, *, form_status: str, health_status):
    fake_db = _FakeDb(form_status=form_status, health_status=health_status)
    monkeypatch.setattr(worker_dashboard, "get_db", lambda: fake_db)
    monkeypatch.setattr(
        worker_dashboard,
        "get_worker_form_definitions",
        lambda: {
            "staff_health_questionnaire": {
                "name": "Staff Health Questionnaire",
                "description": "Health declaration form",
                "required": True,
            }
        },
    )

    app = FastAPI()
    app.include_router(worker_dashboard.router, prefix="/api")
    app.dependency_overrides[worker_dashboard.get_current_worker] = lambda: {"employee_id": "emp-1"}
    return TestClient(app)


@pytest.mark.parametrize(
    "health_status,expected_status",
    [
        (None, "submitted"),
        ("not_fit", "submitted"),
        ("requires_review", "submitted"),
        ("fit", "verified"),
        ("conditional", "verified"),
    ],
)
def test_worker_forms_health_status_alignment(monkeypatch, health_status, expected_status):
    client = _make_client(
        monkeypatch,
        form_status="signed_off",
        health_status=health_status,
    )
    response = client.get("/api/worker/forms")
    assert response.status_code == 200
    payload = response.json()
    forms = payload.get("forms", [])
    assert len(forms) == 1
    health_form = forms[0]
    assert health_form["id"] == "staff_health_questionnaire"
    assert health_form["status"] == expected_status

