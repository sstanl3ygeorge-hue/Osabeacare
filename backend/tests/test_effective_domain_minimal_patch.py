import asyncio
import os
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import training_evaluator as te
import routes.competency as competency_module
import routes.appraisals as appraisals_module
from routes.dependencies import require_manager_or_admin, get_current_user


def test_nurse_required_training_matrix_includes_effective_domain_items(monkeypatch):
    fake_server = types.SimpleNamespace()

    class _SystemRole:
        UNKNOWN = "UNKNOWN"

    fake_server.SystemRole = _SystemRole
    fake_server.normalize_to_system_role = lambda role: "NURSE" if "nurse" in (role or "").lower() else _SystemRole.UNKNOWN
    fake_server.is_nurse_role = lambda system_role: system_role == "NURSE"
    fake_server.MANDATORY_ITEMS = {
        "training": [
            {"id": "manual_handling", "type": "training", "training_name": "Manual Handling", "mandatory_for_compliance": True},
            {"id": "mca_dols", "type": "training", "training_name": "MCA and DoLs", "mandatory_for_compliance": False},
        ],
        "nurse_specific": [
            {"id": "medication_competency", "type": "training", "training_name": "Medication"},
        ],
    }

    monkeypatch.setitem(sys.modules, "server", fake_server)

    required = asyncio.run(te.get_required_training_for_employee("emp-1", "Nurse"))
    ids = [item.get("id") for item in required]

    expected = {
        "medication_administration",
        "news2_clinical_observations",
        "sepsis_awareness",
        "pressure_ulcer_prevention",
        "mca_dols",
        "enhanced_infection_prevention",
    }
    for req_id in expected:
        assert req_id in ids

    assert ids.count("mca_dols") == 1


def test_competency_review_due_alias_helpers():
    resolved = competency_module._resolve_review_due_alias("2027-01-01", "2027-02-01")
    assert resolved == "2027-02-01"

    legacy_only = competency_module._resolve_review_due_alias("2027-01-01", None)
    assert legacy_only == "2027-01-01"

    enriched = competency_module._apply_review_due_alias({"review_due_date": "2027-03-01"})
    assert enriched["review_due_date"] == "2027-03-01"
    assert enriched["review_due_at"] == "2027-03-01"


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda d: d.get(field) or "", reverse=reverse)
        return self

    async def to_list(self, length):
        return list(self._docs[:length])


class _FakeCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                if projection:
                    include_keys = [k for k, include in projection.items() if include and k != "_id"]
                    if include_keys:
                        return {k: doc.get(k) for k in include_keys}
                    return dict(doc)
                return dict(doc)
        return None

    def find(self, query=None, projection=None):
        query = query or {}
        rows = []
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                if projection:
                    include_keys = [k for k, include in projection.items() if include and k != "_id"]
                    if include_keys:
                        rows.append({k: doc.get(k) for k in include_keys})
                    else:
                        rows.append(dict(doc))
                else:
                    rows.append(dict(doc))
        return _FakeCursor(rows)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))


class _FakeDb:
    def __init__(self):
        self.employees = _FakeCollection()
        self.appraisal_records = _FakeCollection()
        self.employees.docs.append({
            "id": "emp-1",
            "first_name": "Ada",
            "last_name": "Stone",
        })


def test_appraisal_create_and_list(monkeypatch):
    db = _FakeDb()

    async def _fake_manager():
        return {"user_id": "mgr-1", "role": "admin"}

    async def _fake_user():
        return {"user_id": "mgr-1", "role": "admin"}

    async def _fake_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(appraisals_module, "get_db", lambda: db)
    monkeypatch.setattr(appraisals_module, "log_audit_action", _fake_audit)

    app = FastAPI()
    app.include_router(appraisals_module.router)
    app.dependency_overrides[require_manager_or_admin] = _fake_manager
    app.dependency_overrides[get_current_user] = _fake_user

    client = TestClient(app)

    create_resp = client.post(
        "/employees/emp-1/appraisals",
        json={
            "appraisal_date": "2026-04-01",
            "reviewer": "Registered Manager",
            "notes": "Quarterly appraisal completed",
            "actions": ["Follow up on training refresh"],
            "next_due_at": "2026-10-01",
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json().get("success") is True

    list_resp = client.get("/employees/emp-1/appraisals")
    assert list_resp.status_code == 200
    items = list_resp.json().get("items", [])
    assert len(items) == 1
    assert items[0]["reviewer"] == "Registered Manager"
    assert items[0]["next_due_at"] == "2026-10-01"
