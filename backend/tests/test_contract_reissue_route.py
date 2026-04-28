import os
import sys
from types import SimpleNamespace
import types
import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure motor import remains available even when other tests stub modules.
sys.modules.setdefault("motor", types.ModuleType("motor"))
motor_asyncio_mod = sys.modules.setdefault("motor.motor_asyncio", types.ModuleType("motor.motor_asyncio"))
if not hasattr(motor_asyncio_mod, "AsyncIOMotorClient"):
    class _FakeAsyncIOMotorClient:  # pragma: no cover - import compatibility stub
        pass
    motor_asyncio_mod.AsyncIOMotorClient = _FakeAsyncIOMotorClient

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
            self._docs.sort(key=lambda d: (d.get(field) is None, d.get(field)), reverse=reverse)
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

    async def find_one(self, query=None, projection=None, sort=None):
        docs = list(self.docs)
        if sort:
            for field, direction in reversed(list(sort)):
                reverse = int(direction) == -1
                docs.sort(key=lambda d: (d.get(field) is None, d.get(field)), reverse=reverse)
        for d in docs:
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
        to_store = dict(document)
        to_store.setdefault("_id", f"mongo-{to_store.get('id') or len(self.docs)}")
        self.docs.append(to_store)
        return SimpleNamespace(inserted_id=document.get("id"))

    async def update_one(self, query, update, upsert=False):
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
        if upsert:
            new_doc = dict(query or {})
            for k, v in (update.get("$setOnInsert") or {}).items():
                new_doc[k] = v
            for k, v in (update.get("$set") or {}).items():
                new_doc[k] = v
            for k in (update.get("$unset") or {}).keys():
                new_doc.pop(k, None)
            self.docs.append(new_doc)
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
        self.agreement_acknowledgements = _FakeCollection([])
        self.audit_logs = _FakeCollection([])
        self.org_settings = _FakeCollection([{"id": "default", "company_name": "Osabea Healthcare"}])


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
    async def _ensure_agreement_rendered(_db, employee, agreement_type):
        assert agreement_type == "contract_acceptance"
        return {
            "template_version": "contract_acceptance_v_testcanon123",
            "template_source_name": "zero_hour_contract_template.docx",
            "rendered_at": "2026-04-27T00:00:00+00:00",
            "rendered_file_url": f"https://example.test/contracts/{employee['id']}.pdf",
            "rendered_contract_pdf_url": f"https://example.test/contracts/{employee['id']}.pdf",
        }
    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _ensure_agreement_rendered)
    async def _download_file(_url):
        pdf_b64 = (
            "JVBERi0xLjMKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5k"
            "b2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9Db3VudCAxIC9LaWRzIFszIDAgUl0gPj4K"
            "ZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3gg"
            "WzAgMCA2MTIgNzkyXSAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8PCA+PiA+PgplbmRv"
            "YmoKNCAwIG9iago8PCAvTGVuZ3RoIDQ0ID4+CnN0cmVhbQpCVCAvRjEgMTIgVGYgNzIgNzIw"
            "IFRkIChDbGVhbiBDb250cmFjdCBURVhUKSBUaiBFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYK"
            "MCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxMCAwMDAwMCBuIAowMDAwMDAwMDYx"
            "IDAwMDAwIG4gCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDIyMCAwMDAwMCBuIAp0cmFp"
            "bGVyCjw8IC9TaXplIDUgL1Jvb3QgMSAwIFIgPj4Kc3RhcnR4cmVmCjMxMwolJUVPRgo="
        )
        return base64.b64decode(pdf_b64)
    monkeypatch.setattr(contracts, "download_file_from_storage", _download_file)
    async def _ensure_agreement_rendered(_db, employee, agreement_type):
        assert agreement_type == "contract_acceptance"
        return {
            "template_version": "contract_acceptance_v_testcanon123",
            "template_source_name": "zero_hour_contract_template.docx",
            "rendered_at": "2026-04-27T00:00:00+00:00",
            "rendered_file_url": f"https://example.test/contracts/{employee['id']}.pdf",
            "rendered_contract_pdf_url": f"https://example.test/contracts/{employee['id']}.pdf",
            "employee_name": f"{employee.get('first_name','')} {employee.get('last_name','')}".strip(),
        }
    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _ensure_agreement_rendered)

    app = FastAPI()
    app.include_router(contracts.router, prefix="/api")
    app.dependency_overrides[contracts.require_manager_or_admin] = lambda: {
        "user_id": "admin-1",
        "role": "admin",
        "name": "Admin User",
    }
    app.dependency_overrides[contracts.get_current_user] = lambda: {
        "user_id": "admin-1",
        "role": "admin",
        "name": "Admin User",
    }
    app.dependency_overrides[contracts.get_current_user_or_worker] = lambda: {
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
    fake_db.agreement_acknowledgements.docs = [
        {
            "id": "agr_contract_acceptance_emp-1",
            "employee_id": "emp-1",
            "agreement_type": "contract_acceptance",
            "status": "rejected",
            "contract_state": "rejected_reopen_required",
            "verification_status": "rejected",
            "rendered_file_url": "https://example.test/old-contract.pdf",
            "rendered_contract_pdf_url": "https://example.test/old-contract.pdf",
            "rejection_reason": "Old version rejected",
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
    ack = next(x for x in fake_db.agreement_acknowledgements.docs if x["agreement_type"] == "contract_acceptance")

    assert new["status"] == "pending_signature"
    assert str(new["template_version"]).startswith("contract_acceptance_v_")
    assert old["superseded_by_contract_id"] == new_id
    assert new["reissued_from_contract_id"] == "old-1"
    assert emp["pending_contract_id"] == new_id
    assert ack["contract_state"] == "awaiting_worker_signature"
    assert ack["verification_status"] == "pending"
    assert ack.get("active_contract_id") == new_id


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

    async def _ensure_agreement_rendered(_db, employee, agreement_type):
        assert agreement_type == "contract_acceptance"
        return {
            "template_version": "contract_acceptance_v_testcanon123",
            "template_source_name": "zero_hour_contract_template.docx",
            "rendered_at": "2026-04-27T00:00:00+00:00",
            "rendered_file_url": f"https://example.test/contracts/{employee['id']}.pdf",
            "rendered_contract_pdf_url": f"https://example.test/contracts/{employee['id']}.pdf",
        }

    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _ensure_agreement_rendered)

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


def test_generate_uses_canonical_template_family(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post("/api/employees/emp-1/contract/generate", json={})
    assert res.status_code == 200
    payload = res.json()
    created = next(x for x in fake_db.generated_contracts.docs if x["id"] == payload["contract_id"])
    assert str(created.get("template_version", "")).startswith("contract_acceptance_v_")
    assert created.get("canonical_contract_render") is True
    assert created.get("rendered_file_url")
    assert payload["status"] == "awaiting_worker_signature"
    assert payload["signable"] is True


def test_generate_succeeds_without_existing_contract(monkeypatch):
    fake_db = _FakeDb()
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
        }
    ]
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post("/api/employees/emp-1/contract/generate", json={})
    assert res.status_code == 200
    payload = res.json()
    created = next(x for x in fake_db.generated_contracts.docs if x["id"] == payload["contract_id"])
    assert str(created.get("template_version", "")).startswith("contract_acceptance_v_")
    assert created["status"] == "pending_signature"
    assert payload["status"] == "awaiting_worker_signature"
    assert payload["signable"] is True


def test_generate_normalization_supersedes_older_active_contract(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="pending_signature")
    fake_db.generated_contracts.docs[0]["template_version"] = "contract_acceptance_v_oldlegacy"
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post("/api/employees/emp-1/contract/generate", json={"normalization_mode": True})
    assert res.status_code == 200

    payload = res.json()
    new_doc = next(x for x in fake_db.generated_contracts.docs if x["id"] == payload["contract_id"])
    old_doc = next(x for x in fake_db.generated_contracts.docs if x["id"] == "old-1")

    assert old_doc["status"] == "superseded"
    assert old_doc["superseded_by_contract_id"] == new_doc["id"]
    assert str(new_doc.get("template_version", "")).startswith("contract_acceptance_v_")
    assert payload["signable"] is True


def test_generate_with_active_contract_requires_normalization_mode(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="awaiting_worker_signature")
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post("/api/employees/emp-1/contract/generate", json={})
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "already_has_active_contract"
    assert detail["contract_id"] == "old-1"


def test_generate_and_reissue_use_same_template_family(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    gen = client.post("/api/employees/emp-1/contract/generate", json={})
    assert gen.status_code == 200
    generated = next(x for x in fake_db.generated_contracts.docs if x["id"] == gen.json()["contract_id"])

    rei = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Need regenerate after mismatch", "source_contract_id": generated["id"]},
    )
    assert rei.status_code == 409
    detail = rei.json()["detail"]
    assert detail["code"] == "already_has_active_contract"
    assert detail["status"] == "awaiting_worker_signature"
    assert detail["contract_id"] == generated["id"]

    assert str(generated.get("template_version", "")).startswith("contract_acceptance_v_")


def test_reissue_blocks_when_canonical_render_fails(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    async def _bad_render(_db, _employee, _type):
        raise contracts.ContractRenderError("missing company_address")
    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _bad_render)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Need reissue after mismatch", "source_contract_id": "old-1"},
    )
    assert res.status_code == 409
    body = res.json()
    assert body["detail"]["status"] == "action_required"
    assert "render_issue" in body["detail"]
    assert "company_address" in body["detail"].get("missing_fields", [])


def test_reissue_hydrates_company_address_from_org_company_address(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.org_settings.docs = [{"id": "default", "company_address": "Suite FA4D, 1 St Faith's Street, Maidstone Kent"}]
    client, _ = _build_client(monkeypatch, fake_db)

    captured = {}

    async def _ensure_with_capture(_db, employee, agreement_type):
        captured["employee"] = dict(employee)
        return {
            "template_version": "contract_acceptance_v_testcanon123",
            "template_source_name": "zero_hour_contract_template.docx",
            "rendered_at": "2026-04-27T00:00:00+00:00",
            "rendered_file_url": f"https://example.test/contracts/{employee['id']}.pdf",
            "rendered_contract_pdf_url": f"https://example.test/contracts/{employee['id']}.pdf",
        }

    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _ensure_with_capture)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Contract rejected, recover from company address source", "source_contract_id": "old-1"},
    )
    assert res.status_code == 200

    # Reissue succeeds without manual modal typing when company_address exists in org settings.
    assert res.json()["new_contract"]["status"] == "pending_signature"


def test_reissue_hydrates_hourly_rate_from_nested_pay_record(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.employees.docs[0].pop("hourly_rate", None)
    fake_db.employees.docs[0]["employment_details"] = {"hourly_rate": "12.98"}
    client, _ = _build_client(monkeypatch, fake_db)

    async def _ensure_with_hourly(_db, employee, agreement_type):
        assert employee.get("hourly_rate") == "12.98"
        return {
            "template_version": "contract_acceptance_v_testcanon123",
            "template_source_name": "zero_hour_contract_template.docx",
            "rendered_at": "2026-04-27T00:00:00+00:00",
            "rendered_file_url": f"https://example.test/contracts/{employee['id']}.pdf",
            "rendered_contract_pdf_url": f"https://example.test/contracts/{employee['id']}.pdf",
        }

    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _ensure_with_hourly)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Contract rejected, recover from pay record source", "source_contract_id": "old-1"},
    )
    assert res.status_code == 200
    assert fake_db.employees.docs[0]["hourly_rate"] == "12.98"


def test_reissue_prefers_org_address_over_stale_employee_override(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.org_settings.docs = [{"id": "default", "company_address": "Address A"}]
    fake_db.employees.docs[0]["contract_render_overrides"] = {"company_address": "Stale Address B"}
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Recover using canonical org address", "source_contract_id": "old-1"},
    )
    assert res.status_code == 200
    assert fake_db.org_settings.docs[0]["company_address"] == "Address A"
    assert fake_db.employees.docs[0]["contract_render_overrides"]["company_address"] == "Stale Address B"


def test_explicit_render_field_override_updates_org_address_for_reissue(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.org_settings.docs = [{"id": "default", "company_address": "Address A"}]
    client, _ = _build_client(monkeypatch, fake_db)

    patch_res = client.patch(
        "/api/employees/emp-1/contract/render-fields",
        json={"company_address": "Address B"},
    )
    assert patch_res.status_code == 200
    assert fake_db.org_settings.docs[0]["company_address"] == "Address B"

    reissue_res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Recover after explicit override", "source_contract_id": "old-1"},
    )
    assert reissue_res.status_code == 200


def test_patch_render_fields_saves_employee_and_org_values(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.patch(
        "/api/employees/emp-1/contract/render-fields",
        json={
            "hourly_rate": "12.5",
            "contract_start_date": "2026-04-01",
            "continuous_service_date": "2026-04-01",
            "company_address": "19 Station Road, Harlow, CM20 2BB",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["fields"]["hourly_rate"] == "12.50"
    assert payload["fields"]["company_address"] == "19 Station Road, Harlow, CM20 2BB"

    employee = fake_db.employees.docs[0]
    assert employee["hourly_rate"] == "12.50"
    assert employee["contract_start_date"] == "2026-04-01"
    assert employee["continuous_service_date"] == "2026-04-01"
    assert employee["contract_render_overrides"]["company_address"] == "19 Station Road, Harlow, CM20 2BB"

    org = fake_db.org_settings.docs[0]
    assert org["company_address"] == "19 Station Road, Harlow, CM20 2BB"
    assert org["organisation_address"] == "19 Station Road, Harlow, CM20 2BB"


def test_patch_render_fields_then_reissue_succeeds(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    client, _ = _build_client(monkeypatch, fake_db)

    async def _requires_fields(_db, employee, _type):
        if not employee.get("hourly_rate"):
            raise contracts.ContractRenderError("missing hourly_rate, company_address")
        if not (fake_db.org_settings.docs and fake_db.org_settings.docs[0].get("company_address")):
            raise contracts.ContractRenderError("missing company_address")
        return {
            "template_version": "contract_acceptance_v_testcanon123",
            "template_source_name": "zero_hour_contract_template.docx",
            "rendered_at": "2026-04-27T00:00:00+00:00",
            "rendered_file_url": f"https://example.test/contracts/{employee['id']}.pdf",
            "rendered_contract_pdf_url": f"https://example.test/contracts/{employee['id']}.pdf",
        }

    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _requires_fields)

    missing_res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Need reissue after bad render", "source_contract_id": "old-1"},
    )
    assert missing_res.status_code == 409
    assert set(missing_res.json()["detail"]["missing_fields"]) == {"hourly_rate", "company_address"}

    patch_res = client.patch(
        "/api/employees/emp-1/contract/render-fields",
        json={
            "hourly_rate": "13.25",
            "company_address": "1 Care Road, London, SW1A 1AA",
            "contract_start_date": "2026-04-01",
            "continuous_service_date": "2026-04-01",
        },
    )
    assert patch_res.status_code == 200

    reissue_res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "Need reissue after bad render", "source_contract_id": "old-1"},
    )
    assert reissue_res.status_code == 200
    assert reissue_res.json()["new_contract"]["status"] == "pending_signature"


def test_reissue_uses_existing_canonical_artifact_when_render_fields_missing(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="signed")
    # Ensure latest contract has canonical rendered artifact to reuse.
    fake_db.generated_contracts.docs[0]["template_version"] = "contract_acceptance_v_testcanon123"
    fake_db.generated_contracts.docs[0]["rendered_contract_pdf_url"] = "https://example.test/contracts/existing-canonical.pdf"
    fake_db.generated_contracts.docs[0]["rendered_file_url"] = "https://example.test/contracts/existing-canonical.pdf"
    client, _ = _build_client(monkeypatch, fake_db)

    async def _bad_render(_db, _employee, _type):
        raise contracts.ContractRenderError("missing hourly_rate, company_address")

    monkeypatch.setattr(contracts, "ensure_agreement_rendered", _bad_render)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "reopen with existing canonical artifact", "source_contract_id": "old-1"},
    )
    assert res.status_code == 200
    payload = res.json()
    new_contract_id = payload["new_contract"]["id"]
    new_row = next(x for x in fake_db.generated_contracts.docs if x["id"] == new_contract_id)
    assert new_row["status"] == "pending_signature"
    assert new_row["rendered_contract_pdf_url"] == "https://example.test/contracts/existing-canonical.pdf"
    assert new_row["rendered_file_url"] == "https://example.test/contracts/existing-canonical.pdf"


def test_legacy_pending_contract_not_signable(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.generated_contracts.docs.append(
        {
            "id": "legacy-1",
            "employee_id": "emp-1",
            "status": "pending_signature",
            "template_version": "zero_hour_contract_v1",
            "rendered_file_url": None,
        }
    )
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contracts/legacy-1/sign",
        json={"acknowledgement": True},
    )
    assert res.status_code == 409
    assert res.json()["detail"]["status"] == "action_required"


def test_pending_contract_with_unresolved_placeholders_not_signable(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, status="rejected")
    fake_db.generated_contracts.docs.append(
        {
            "id": "legacy-unresolved-1",
            "employee_id": "emp-1",
            "status": "pending_signature",
            "template_version": "contract_acceptance_v_testcanon123",
            "rendered_file_url": "https://example.test/contracts/legacy-unresolved.pdf",
            "filled_sections": [{"content": "This Statement dated (insert date of issue)"}],
        }
    )
    client, _ = _build_client(monkeypatch, fake_db)
    res = client.post(
        "/api/employees/emp-1/contracts/legacy-unresolved-1/sign",
        json={"acknowledgement": True},
    )
    assert res.status_code == 409
    assert res.json()["detail"]["status"] == "action_required"
    assert "unresolved placeholders" in res.json()["detail"]["render_issue"].lower()


def test_reissue_pending_signature_blocks_with_structured_active_contract_error(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, contract_id="pending-1", status="pending_signature")
    fake_db.agreement_acknowledgements.docs = [
        {
            "id": "agr_contract_acceptance_emp-1",
            "employee_id": "emp-1",
            "agreement_type": "contract_acceptance",
            "status": "rejected",
            "contract_state": "rejected_reopen_required",
            "verification_status": "rejected",
            "rendered_file_url": "https://example.test/old-contract.pdf",
            "rendered_contract_pdf_url": "https://example.test/old-contract.pdf",
        }
    ]
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "repair pending state", "source_contract_id": "pending-1"},
    )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "already_has_active_contract"
    assert detail["status"] == "awaiting_worker_signature"
    assert detail["contract_id"] == "pending-1"
    ack = fake_db.agreement_acknowledgements.docs[0]
    assert ack["status"] == "pending_signature"
    assert ack["contract_state"] == "awaiting_worker_signature"
    assert ack["verification_status"] == "pending"


def test_latest_pending_signature_overrides_historical_rejected_for_reissue_decision(monkeypatch):
    fake_db = _FakeDb()
    _seed_employee_and_contract(fake_db, contract_id="old-rejected", status="rejected")
    fake_db.generated_contracts.docs.append(
        {
            "_id": "mongo-new-pending",
            "id": "new-pending",
            "employee_id": "emp-1",
            "status": "pending_signature",
            "template_id": "zero_hour_contract_v1",
            "generated_at": "2026-05-01T10:00:00+00:00",
            "created_at": "2026-05-01T10:00:00+00:00",
        }
    )
    client, _ = _build_client(monkeypatch, fake_db)

    res = client.post(
        "/api/employees/emp-1/contract/reissue",
        json={"reason": "should be blocked by latest pending", "source_contract_id": "new-pending"},
    )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "already_has_active_contract"
    assert detail["status"] == "awaiting_worker_signature"
    assert detail["contract_id"] == "new-pending"
