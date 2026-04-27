import os
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.agreements as agreements


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def _matches(self, doc, query):
        for key, value in (query or {}).items():
            if doc.get(key) != value:
                return False
        return True

    async def find_one(self, query=None, projection=None):
        for doc in self.docs:
            if self._matches(doc, query or {}):
                out = dict(doc)
                if projection and projection.get("_id") == 0:
                    out.pop("_id", None)
                return out
        return None

    async def update_one(self, query, update):
        for idx, doc in enumerate(self.docs):
            if self._matches(doc, query or {}):
                merged = dict(doc)
                for k, v in (update.get("$set") or {}).items():
                    merged[k] = v
                self.docs[idx] = merged
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


class _FakeDb:
    def __init__(self):
        self.agreement_acknowledgements = _FakeCollection([])
        self.employees = _FakeCollection([])


def _build_client(monkeypatch, db):
    monkeypatch.setattr(agreements, "get_db", lambda: db)

    async def _ensure_rendered(_db, _employee, agreement_type):
        return {
            "id": "ack-hb-1",
            "agreement_type": agreement_type,
            "rendered_file_url": "https://storage.test/handbook.pdf",
            "status": "pending",
            "verification_status": "pending",
        }

    async def _audit(*_args, **_kwargs):
        return None

    import agreement_document_service as agreement_doc_service
    monkeypatch.setattr(agreement_doc_service, "ensure_agreement_rendered", _ensure_rendered)
    monkeypatch.setattr(agreements, "log_audit_action", _audit)

    app = FastAPI()
    app.include_router(agreements.router, prefix="/api")
    app.dependency_overrides[agreements.require_manager_or_admin] = lambda: {
        "user_id": "admin-1",
        "role": "admin",
        "name": "Admin User",
    }
    app.dependency_overrides[agreements.get_current_user] = lambda: {
        "user_id": "admin-1",
        "role": "admin",
        "name": "Admin User",
    }
    return TestClient(app)


def test_handbook_regenerate_fallback_when_ack_id_missing(monkeypatch):
    db = _FakeDb()
    db.employees.docs.append({"id": "emp-1", "first_name": "A", "last_name": "B"})
    db.agreement_acknowledgements.docs.append(
        {
            "id": "ack-hb-1",
            "employee_id": "emp-1",
            "agreement_type": "handbook_acknowledgement",
            "status": "rejected",
            "verification_status": "rejected",
            "rendered_file_url": "https://storage.test/old.pdf",
        }
    )
    client = _build_client(monkeypatch, db)

    res = client.post(
        "/api/employees/emp-1/agreements/__fallback__/regenerate",
        json={
            "reason": "Reset handbook after bad state",
            "agreement_type": "handbook_acknowledgement",
        },
    )
    assert res.status_code == 200
    assert res.json().get("success") is True


def test_contract_reset_blocked_on_fallback_path(monkeypatch):
    db = _FakeDb()
    db.employees.docs.append({"id": "emp-1", "first_name": "A", "last_name": "B"})
    client = _build_client(monkeypatch, db)

    res = client.post(
        "/api/employees/emp-1/agreements/__fallback__/regenerate",
        json={
            "reason": "Trying to reset contract",
            "agreement_type": "contract_acceptance",
        },
    )
    assert res.status_code == 403
