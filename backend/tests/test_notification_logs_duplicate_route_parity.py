import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.email_notifications as email_notifications
import routes.notifications as notifications


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._limit = None

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda item: item.get(field, ""), reverse=reverse)
        return self

    def limit(self, value):
        self._limit = value
        return self

    async def to_list(self, length):
        effective_limit = self._limit if self._limit is not None else length
        if effective_limit is None:
            return list(self._docs)
        return list(self._docs[:effective_limit])


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
            elif actual != expected:
                return False
        return True

    async def find_one(self, query=None, projection=None):
        for doc in self.docs:
            if self._matches(doc, query or {}):
                return dict(doc)
        return None

    def find(self, query=None, projection=None):
        filtered = [dict(doc) for doc in self.docs if self._matches(doc, query or {})]
        return _FakeCursor(filtered)


class _FakeDb:
    def __init__(self):
        self.notification_logs = _FakeCollection([])


def _seed_logs(db, total=120):
    docs = []
    for index in range(total):
        docs.append(
            {
                "id": f"log-{index}",
                "employee_id": "emp-1" if index % 2 == 0 else "emp-2",
                "notification_type": "training_expired" if index % 3 == 0 else "missing_mandatory_item",
                "status": "sent" if index % 4 == 0 else "failed",
                "sent_at": f"2026-04-24T10:{index:02d}:00+00:00",
            }
        )
    db.notification_logs.docs.extend(docs)


def _extract_duplicate_paths():
    notifications_routes = set()
    email_notifications_routes = set()

    for route in notifications.router.routes:
        for method in sorted(getattr(route, "methods", set())):
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                notifications_routes.add((method, route.path))

    for route in email_notifications.router.routes:
        for method in sorted(getattr(route, "methods", set())):
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                email_notifications_routes.add((method, route.path))

    return notifications_routes & email_notifications_routes


def _build_client(monkeypatch, *, include_notifications, include_email_notifications, override_auth=True):
    fake_db = _FakeDb()
    _seed_logs(fake_db)

    monkeypatch.setattr(notifications, "get_db", lambda: fake_db)
    monkeypatch.setattr(email_notifications, "get_db", lambda: fake_db)

    app = FastAPI()
    if include_notifications:
        app.include_router(notifications.router, prefix="/api")
    if include_email_notifications:
        app.include_router(email_notifications.router, prefix="/api")

    if override_auth:
        admin_user = {"user_id": "admin-1", "role": "admin", "email": "admin@example.com"}
        app.dependency_overrides[notifications.require_admin] = lambda: admin_user
        app.dependency_overrides[email_notifications.require_admin] = lambda: admin_user

    return TestClient(app), fake_db


def test_notification_logs_duplicate_path_is_confirmed():
    assert _extract_duplicate_paths() == {("GET", "/notifications/logs")}


def test_notification_logs_requires_admin_auth(monkeypatch):
    client, _ = _build_client(
        monkeypatch,
        include_notifications=True,
        include_email_notifications=True,
        override_auth=False,
    )

    response = client.get("/api/notifications/logs")
    assert response.status_code == 401


def test_effective_owner_matches_canonical_response_shape_sort_and_default_pagination(monkeypatch):
    effective_client, _ = _build_client(
        monkeypatch,
        include_notifications=True,
        include_email_notifications=True,
    )
    canonical_client, _ = _build_client(
        monkeypatch,
        include_notifications=True,
        include_email_notifications=False,
    )
    legacy_client, _ = _build_client(
        monkeypatch,
        include_notifications=False,
        include_email_notifications=True,
    )

    effective_response = effective_client.get("/api/notifications/logs")
    canonical_response = canonical_client.get("/api/notifications/logs")
    legacy_response = legacy_client.get("/api/notifications/logs")

    assert effective_response.status_code == 200
    assert canonical_response.status_code == 200
    assert legacy_response.status_code == 200

    effective_payload = effective_response.json()
    canonical_payload = canonical_response.json()
    legacy_payload = legacy_response.json()

    assert set(effective_payload.keys()) == {"logs", "count"}
    assert effective_payload == canonical_payload

    # notifications.py default limit is 100; email_notifications.py default is 50.
    assert effective_payload["count"] == 100
    assert legacy_payload["count"] == 50

    sent_times = [item["sent_at"] for item in effective_payload["logs"]]
    assert sent_times == sorted(sent_times, reverse=True)


def test_filters_match_canonical_and_apply_employee_and_notification_type(monkeypatch):
    effective_client, _ = _build_client(
        monkeypatch,
        include_notifications=True,
        include_email_notifications=True,
    )
    canonical_client, _ = _build_client(
        monkeypatch,
        include_notifications=True,
        include_email_notifications=False,
    )

    query = "employee_id=emp-1&notification_type=training_expired&limit=30"
    effective_response = effective_client.get(f"/api/notifications/logs?{query}")
    canonical_response = canonical_client.get(f"/api/notifications/logs?{query}")

    assert effective_response.status_code == 200
    assert effective_response.json() == canonical_response.json()

    payload = effective_response.json()
    assert payload["count"] > 0
    for log in payload["logs"]:
        assert log["employee_id"] == "emp-1"
        assert log["notification_type"] == "training_expired"


def test_status_query_behavior_matches_canonical_and_differs_from_legacy(monkeypatch):
    effective_client, _ = _build_client(
        monkeypatch,
        include_notifications=True,
        include_email_notifications=True,
    )
    canonical_client, _ = _build_client(
        monkeypatch,
        include_notifications=True,
        include_email_notifications=False,
    )
    legacy_client, _ = _build_client(
        monkeypatch,
        include_notifications=False,
        include_email_notifications=True,
    )

    query = "employee_id=emp-1&status=sent&limit=100"
    effective_response = effective_client.get(f"/api/notifications/logs?{query}")
    canonical_response = canonical_client.get(f"/api/notifications/logs?{query}")
    legacy_response = legacy_client.get(f"/api/notifications/logs?{query}")

    assert effective_response.status_code == 200
    assert canonical_response.status_code == 200
    assert legacy_response.status_code == 200

    effective_payload = effective_response.json()
    canonical_payload = canonical_response.json()
    legacy_payload = legacy_response.json()

    # notifications.py has no status filter; unknown query param is ignored.
    assert effective_payload == canonical_payload
    # email_notifications.py applies status filter, so this should diverge.
    assert effective_payload["count"] != legacy_payload["count"]
    assert all(item["status"] == "sent" for item in legacy_payload["logs"])