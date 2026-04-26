import os
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.contracts as contracts


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, spec, direction=None):
        if isinstance(spec, list):
            sort_spec = list(spec)
        else:
            sort_spec = [(spec, direction if direction is not None else 1)]
        for field, dirn in reversed(sort_spec):
            reverse = int(dirn) == -1
            self._docs.sort(key=lambda d: d.get(field), reverse=reverse)
        return self

    def limit(self, count):
        self._docs = self._docs[:count]
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self._docs)
        return list(self._docs[:length])


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.fail_insert = False
        self.force_mark_in_progress_conflict = False

    def _match_condition(self, actual, expected):
        if isinstance(expected, dict):
            for op, val in expected.items():
                if op == "$in":
                    if actual not in val:
                        return False
                elif op == "$ne":
                    if actual == val:
                        return False
                elif op == "$exists":
                    exists = actual is not None
                    if bool(val) != exists:
                        return False
                else:
                    raise AssertionError(f"Unsupported operator {op}")
            return True
        return actual == expected

    def _matches(self, doc, query):
        for key, value in (query or {}).items():
            if key == "$and":
                if not all(self._matches(doc, q) for q in value):
                    return False
                continue
            if key == "$or":
                if not any(self._matches(doc, q) for q in value):
                    return False
                continue
            if not self._match_condition(doc.get(key), value):
                return False
        return True

    async def find_one(self, query=None, projection=None):
        for d in self.docs:
            if self._matches(d, query or {}):
                out = dict(d)
                if projection and projection.get("_id") == 0:
                    out.pop("_id", None)
                return out
        return None

    def find(self, query=None, projection=None):
        filtered = [dict(d) for d in self.docs if self._matches(d, query or {})]
        if projection and projection.get("_id") == 0:
            for row in filtered:
                row.pop("_id", None)
        return _FakeCursor(filtered)

    async def insert_one(self, document):
        if self.fail_insert:
            raise RuntimeError("simulated insert failure")
        self.docs.append(dict(document))
        return SimpleNamespace(inserted_id=document.get("id"))

    async def update_one(self, query, update):
        # Simulate race conflict specifically for mark-in-progress lock update.
        if self.force_mark_in_progress_conflict and "$set" in update and update["$set"].get("reissue_in_progress") is True:
            return SimpleNamespace(modified_count=0)
        for i, d in enumerate(self.docs):
            if self._matches(d, query or {}):
                merged = dict(d)
                for k, v in (update.get("$set") or {}).items():
                    merged[k] = v
                for k in (update.get("$unset") or {}).keys():
                    merged.pop(k, None)
                self.docs[i] = merged
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)

    async def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._matches(d, query or {}):
                self.docs.pop(i)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)


class _FakeDb:
    def __init__(self):
        self.employees = _FakeCollection([])
        self.generated_contracts = _FakeCollection([])
        self.audit_logs = _FakeCollection([])


def _build_client(monkeypatch, fake_db):
    monkeypatch.setattr(contracts, "get_db", lambda: fake_db)

    async def _can_sign(_db, _employee_id):
        return {"can_sign": True}

    audit_events = []

    async def _log_audit_action(user_id, action, resource_type, resource_id, details=None):
        audit_events.append(
            {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
            }
        )

    monkeypatch.setattr(contracts, "can_sign_contract", _can_sign)
    monkeypatch.setattr(contracts, "log_audit_action", _log_audit_action)

    app = FastAPI()
    app.include_router(contracts.router, prefix="/api")
    app.dependency_overrides[contracts.require_manager_or_admin] = lambda: {
        "user_id": "admin-1",
        "role": "admin",
        "name": "Admin User",
    }
    return TestClient(app), audit_events


def _seed_employee_and_contract(fake_db, *, contract_id="old-1", status="rejected"):
    fake_db.employees.docs = [
        {
            "id": "emp-1",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "address_line_1": "1 Main St",
            "postcode": "SW1A 1AA",
            "ni_number": "QQ123456C",
            "role": "HCA",
            "contract_signed": status in ("signed", "fully_executed"),
            "contract_signed_at": "2026-04-01T10:00:00+00:00" if status in ("signed", "fully_executed") else None,
            "contract_id": contract_id if status in ("signed", "fully_executed") else None,
        }
    ]
    fake_db.generated_contracts.docs = [
        {
            "_id": "mongo-old-1",
            "id": contract_id,
            "employee_id": "emp-1",
            "status": status,
            "template_id": "zero_hour_contract_v1",
            "generated_at": "2026-04-01T10:00:00+00:00",
            "created_at": "2026-04-01T10:00:00+00:00",
        }
    ]


def test_reissue_success_links_and_employee_pointer(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Contract rejected, worker must re-sign", "source_contract_id": "old-1"},
    )
    assert res.status_code == 200
    payload = res.json()
    new_id = payload["new_contract"]["id"]

    old = next(x for x in fake_db.generated_contracts.docs if x["id"] == "old-1")
    new = next(x for x in fake_db.generated_contracts.docs if x["id"] == new_id)
    emp = fake_db.employees.docs[0]

    assert new["status"] == "pending_signature"
    assert old["superseded_by_contract_id"] == new_id
    assert new["reissued_from_contract_id"] == "old-1"
    assert emp["pending_contract_id"] == new_id


def test_source_contract_stale_returns_409(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, contract_id="latest-1", status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Need re-sign", "source_contract_id": "stale-999"},
    )
    assert res.status_code == 409


def test_idempotency_replay_returns_same_new_contract(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    body = {
        "reason": "Need re-sign with idempotency",
        "source_contract_id": "old-1",
        "idempotency_key": "idem-1",
    }
    first = client.post("/api/employees/emp-1/contract/reissue", json=body)
    second = client.post("/api/employees/emp-1/contract/reissue", json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["new_contract"]["id"] == second.json()["new_contract"]["id"]


def test_race_conflict_returns_409_and_no_duplicate(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.generated_contracts.force_mark_in_progress_conflict = True
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Race conflict", "source_contract_id": "old-1"},
    )
    assert res.status_code == 409
    assert len([x for x in fake_db.generated_contracts.docs if x.get("reissued_from_contract_id") == "old-1"]) == 0


def test_insert_failure_restores_old_contract_state(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.generated_contracts.fail_insert = True
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Simulate insert failure", "source_contract_id": "old-1"},
    )
    assert res.status_code == 500

    old = next(x for x in fake_db.generated_contracts.docs if x["id"] == "old-1")
    assert old["status"] == "rejected"
    assert old.get("superseded_by_contract_id") is None
    assert len([x for x in fake_db.generated_contracts.docs if x.get("reissued_from_contract_id") == "old-1"]) == 0


def test_audit_failure_rolls_back_employee_pointers(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="signed")
    original = dict(fake_db.employees.docs[0])
    monkeypatch.setattr(contracts, "get_db", lambda: fake_db)

    async def _can_sign(_db, _employee_id):
        return {"can_sign": True}

    async def _log_audit_action(*_args, **_kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(contracts, "can_sign_contract", _can_sign)
    monkeypatch.setattr(contracts, "log_audit_action", _log_audit_action)

    app = FastAPI()
    app.include_router(contracts.router, prefix="/api")
    app.dependency_overrides[contracts.require_manager_or_admin] = lambda: {
        "user_id": "admin-1",
        "role": "admin",
    }
    client = TestClient(app)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "simulate audit failure", "source_contract_id": "old-1"},
    )
    assert res.status_code == 500

    emp = fake_db.employees.docs[0]
    assert emp.get("pending_contract_id") == original.get("pending_contract_id")
    assert emp.get("pending_contract_generated_at") == original.get("pending_contract_generated_at")
    assert emp.get("contract_signed") == original.get("contract_signed")
    assert emp.get("contract_signed_at") == original.get("contract_signed_at")
    assert emp.get("contract_id") == original.get("contract_id")
