import os
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.care_locations as care_locations


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda item: item.get(field, ""), reverse=reverse)
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
                if not any(_FakeCollection._matches(doc, part) for part in expected):
                    return False
                continue

            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$regex" in expected:
                    needle = str(expected.get("$regex", "")).lower()
                    hay = str(actual or "").lower()
                    if needle not in hay:
                        return False
                    continue
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
        matches = [dict(doc) for doc in self.docs if self._matches(doc, query or {})]
        return _FakeCursor(matches)

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
        self.care_locations = _FakeCollection([])


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

    monkeypatch.setattr(care_locations, "get_db", lambda: fake_db)
    monkeypatch.setattr(care_locations, "log_audit_action", _fake_log_audit_action)

    app = FastAPI()
    app.include_router(care_locations.router, prefix="/api")
    app.dependency_overrides[care_locations.require_manager_or_admin] = lambda: {
        "user_id": "mgr-1",
        "role": "admin",
    }

    return TestClient(app), fake_db, audit_events


def _create_location(client, *, name="Oak House", location_type="care_home"):
    payload = {
        "name": name,
        "location_type": location_type,
        "address_line_1": "12 High Street",
        "city": "London",
        "postcode": "SW1A 1AA",
        "contact_name": "Jane Manager",
        "contact_phone": "07123456789",
        "qr_enabled": False,
        "geofence_enabled": False,
        "geofence_lat": None,
        "geofence_lng": None,
        "geofence_radius_m": None,
    }
    response = client.post("/api/care-locations", json=payload)
    assert response.status_code == 200
    return response.json()["care_location"]


def test_create_care_location(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_location(client)

    assert created["id"]
    assert created["name"] == "Oak House"
    assert created["location_type"] == "care_home"
    assert created["is_active"] is True


def test_list_care_locations(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    _create_location(client, name="B House")
    _create_location(client, name="A House")

    listed = client.get("/api/care-locations")
    assert listed.status_code == 200
    rows = listed.json()["care_locations"]
    assert len(rows) == 2
    assert [row["name"] for row in rows] == ["A House", "B House"]


def test_get_care_location_by_id(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_location(client)

    fetched = client.get(f"/api/care-locations/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["care_location"]["id"] == created["id"]


def test_update_care_location(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_location(client)

    updated = client.put(
        f"/api/care-locations/{created['id']}",
        json={
            "name": "Oak House Updated",
            "location_type": "supported_living",
            "contact_phone": "07999999999",
        },
    )
    assert updated.status_code == 200
    payload = updated.json()["care_location"]
    assert payload["name"] == "Oak House Updated"
    assert payload["location_type"] == "supported_living"
    assert payload["contact_phone"] == "07999999999"


def test_archive_sets_inactive(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_location(client)

    archived = client.post(f"/api/care-locations/{created['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["care_location"]["is_active"] is False


def test_restore_sets_active(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    created = _create_location(client)
    archive = client.post(f"/api/care-locations/{created['id']}/archive")
    assert archive.status_code == 200

    restored = client.post(f"/api/care-locations/{created['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["care_location"]["is_active"] is True


def test_invalid_location_type_rejected(monkeypatch):
    client, _, _ = _make_app(monkeypatch)
    response = client.post(
        "/api/care-locations",
        json={
            "name": "Invalid Place",
            "location_type": "hospital",
            "address_line_1": "1 Road",
            "city": "Leeds",
            "postcode": "LS1 1AA",
            "contact_name": "Person",
            "contact_phone": "07000000000",
            "qr_enabled": False,
            "geofence_enabled": False,
            "geofence_lat": None,
            "geofence_lng": None,
            "geofence_radius_m": None,
        },
    )
    assert response.status_code == 400
    assert "location_type must be one of" in response.json()["detail"]


def test_audit_events_written_for_create_update_archive_restore(monkeypatch):
    client, _, audit_events = _make_app(monkeypatch)
    created = _create_location(client)

    update_response = client.put(
        f"/api/care-locations/{created['id']}",
        json={"city": "Bristol"},
    )
    assert update_response.status_code == 200

    archive_response = client.post(f"/api/care-locations/{created['id']}/archive")
    assert archive_response.status_code == 200

    restore_response = client.post(f"/api/care-locations/{created['id']}/restore")
    assert restore_response.status_code == 200

    actions = [entry["action"] for entry in audit_events]
    assert "care_location_created" in actions
    assert "care_location_updated" in actions
    assert "care_location_archived" in actions
    assert "care_location_restored" in actions
