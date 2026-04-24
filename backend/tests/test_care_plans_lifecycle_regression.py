import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.care_plans as care_plans


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda item: item.get(field, ""), reverse=reverse)
        return self

    async def to_list(self, length):
        return list(self._docs[:length])


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    @staticmethod
    def _matches(doc, query):
        for key, expected in (query or {}).items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, query=None, projection=None, sort=None):
        matches = [doc for doc in self.docs if self._matches(doc, query or {})]
        if sort:
            field, direction = sort[0]
            matches.sort(key=lambda item: item.get(field, ""), reverse=direction == -1)
        return dict(matches[0]) if matches else None

    def find(self, query=None, projection=None):
        matches = [dict(doc) for doc in self.docs if self._matches(doc, query or {})]
        return _FakeCursor(matches)

    async def insert_one(self, document):
        self.docs.append(dict(document))

    async def update_one(self, query, update):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query or {}):
                updated = dict(doc)
                if "$set" in update:
                    updated.update(update["$set"])
                self.docs[index] = updated
                return


class _FakeDb:
    def __init__(self):
        self.service_users = _FakeCollection(
            [
                {"id": "su-1", "full_name": "Service User One", "service_user_code": "SU-0001"},
                {"id": "su-2", "full_name": "Service User Two", "service_user_code": "SU-0002"},
            ]
        )
        self.service_user_care_plans = _FakeCollection([])


def _make_app(monkeypatch):
    fake_db = _FakeDb()
    audit_events = []

    async def _fake_log_audit_action(user_id, action, resource_type, resource_id, details=None):
        audit_events.append(
            {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
            }
        )

    monkeypatch.setattr(care_plans, "get_db", lambda: fake_db)
    monkeypatch.setattr(care_plans, "log_audit_action", _fake_log_audit_action)

    app = FastAPI()
    app.include_router(care_plans.router, prefix="/api")
    app.dependency_overrides[care_plans.require_manager_or_admin] = lambda: {
        "user_id": "mgr-1",
        "role": "admin",
    }

    return TestClient(app), fake_db, audit_events


def _create_draft(client, service_user_id="su-1", title="Care Plan v1"):
    response = client.post(
        f"/api/service-users/{service_user_id}/care-plans",
        json={
            "care_plan_title": title,
            "goals": ["Goal A"],
            "needs_summary": "Needs",
            "support_instructions": "Support",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_draft_care_plan(monkeypatch):
    client, _, _ = _make_app(monkeypatch)

    created = _create_draft(client)

    assert created["service_user_id"] == "su-1"
    assert created["status"] == "draft"
    assert created["version_number"] == 1
    assert created["care_plan_title"] == "Care Plan v1"


def test_list_care_plans_for_service_user(monkeypatch):
    client, _, _ = _make_app(monkeypatch)

    first = _create_draft(client, title="Version 1")
    second = _create_draft(client, title="Version 2")

    archive_response = client.post(
        f"/api/service-users/su-1/care-plans/{first['id']}/archive",
        json={},
    )
    assert archive_response.status_code == 200

    listed = client.get("/api/service-users/su-1/care-plans")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == second["id"]


def test_get_care_plan_by_id(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_draft(client)

    fetched = client.get(f"/api/service-users/su-1/care-plans/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_update_draft_succeeds(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_draft(client)

    updated = client.put(
        f"/api/service-users/su-1/care-plans/{created['id']}",
        json={"care_plan_title": "Updated Title", "goals": ["New Goal"]},
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["care_plan_title"] == "Updated Title"
    assert payload["goals"] == ["New Goal"]


def test_update_active_is_blocked(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_draft(client)

    activated = client.post(f"/api/service-users/su-1/care-plans/{created['id']}/activate")
    assert activated.status_code == 200

    blocked = client.put(
        f"/api/service-users/su-1/care-plans/{created['id']}",
        json={"care_plan_title": "Should Fail"},
    )
    assert blocked.status_code == 400
    assert "Only draft care plans can be updated" in blocked.json()["detail"]


def test_activate_draft_creates_active_version(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_draft(client)

    activated = client.post(f"/api/service-users/su-1/care-plans/{created['id']}/activate")
    assert activated.status_code == 200
    payload = activated.json()
    assert payload["status"] == "active"
    assert payload["approved_by"] == "mgr-1"
    assert payload["approved_at"] is not None
    assert payload["effective_from"] is not None


def test_activate_second_draft_supersedes_previous_active(monkeypatch):
    client, fake_db, _ = _make_app(monkeypatch)
    first = _create_draft(client, title="v1")
    second = _create_draft(client, title="v2")

    activate_first = client.post(f"/api/service-users/su-1/care-plans/{first['id']}/activate")
    assert activate_first.status_code == 200

    activate_second = client.post(f"/api/service-users/su-1/care-plans/{second['id']}/activate")
    assert activate_second.status_code == 200
    assert activate_second.json()["status"] == "active"

    first_after = next(item for item in fake_db.service_user_care_plans.docs if item["id"] == first["id"])
    assert first_after["status"] == "superseded"
    assert first_after["superseded_by"] == second["id"]


def test_archive_draft_succeeds(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_draft(client)

    archived = client.post(f"/api/service-users/su-1/care-plans/{created['id']}/archive", json={})
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_archive_active_without_replacement_is_blocked(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_draft(client)

    activated = client.post(f"/api/service-users/su-1/care-plans/{created['id']}/activate")
    assert activated.status_code == 200

    blocked = client.post(f"/api/service-users/su-1/care-plans/{created['id']}/archive", json={})
    assert blocked.status_code == 400
    assert "without an active replacement" in blocked.json()["detail"]


def test_service_user_id_mismatch_is_not_found(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_draft(client, service_user_id="su-1")

    mismatch = client.get(f"/api/service-users/su-2/care-plans/{created['id']}")
    assert mismatch.status_code == 404
    assert mismatch.json()["detail"] == "Care plan not found"


def test_audit_events_written_for_create_update_activate_archive(monkeypatch):
    client, _, audit_events = _make_app(monkeypatch)
    created = _create_draft(client)

    update_response = client.put(
        f"/api/service-users/su-1/care-plans/{created['id']}",
        json={"needs_summary": "Updated needs"},
    )
    assert update_response.status_code == 200

    activate_response = client.post(f"/api/service-users/su-1/care-plans/{created['id']}/activate")
    assert activate_response.status_code == 200

    replacement = _create_draft(client, title="Replacement")
    replacement_activate = client.post(f"/api/service-users/su-1/care-plans/{replacement['id']}/activate")
    assert replacement_activate.status_code == 200

    archive_response = client.post(
        f"/api/service-users/su-1/care-plans/{created['id']}/archive",
        json={"replacement_care_plan_id": replacement['id']},
    )
    assert archive_response.status_code == 200

    actions = [entry["action"] for entry in audit_events]
    assert "create_service_user_care_plan" in actions
    assert "update_service_user_care_plan" in actions
    assert "activate_service_user_care_plan" in actions
    assert "archive_service_user_care_plan" in actions


def test_download_care_plan_pdf_returns_pdf_and_logs_audit(monkeypatch):
    client, _, audit_events = _make_app(monkeypatch)
    created = _create_draft(client, title="PDF Plan")

    response = client.get(f"/api/service-users/su-1/care-plans/{created['id']}/download-pdf")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert "attachment; filename=" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF")

    actions = [entry["action"] for entry in audit_events]
    assert "download_service_user_care_plan_pdf" in actions