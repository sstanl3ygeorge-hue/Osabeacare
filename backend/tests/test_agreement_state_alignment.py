import os
import sys
import asyncio
from types import SimpleNamespace

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from agreement_document_service import (  # noqa: E402
    CONTRACT_AGREEMENT_TYPE,
    resolve_employee_agreement_state,
)


class _FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, spec):
        if isinstance(spec, list):
            for field, direction in reversed(spec):
                reverse = int(direction) == -1
                self.docs.sort(key=lambda d: str(d.get(field) or ""), reverse=reverse)
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self.docs)
        return list(self.docs[:length])


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def _matches(self, doc, query):
        for key, value in (query or {}).items():
            if key == "$or":
                if not any(self._matches(doc, part) for part in value):
                    return False
                continue
            if isinstance(value, dict):
                if "$ne" in value and doc.get(key) == value["$ne"]:
                    return False
                if "$exists" in value:
                    exists = key in doc and doc.get(key) is not None
                    if bool(value["$exists"]) != exists:
                        return False
                if "$in" in value and doc.get(key) not in value["$in"]:
                    return False
                continue
            if doc.get(key) != value:
                return False
        return True

    async def find_one(self, query=None, projection=None, sort=None):
        rows = [d for d in self.docs if self._matches(d, query or {})]
        if sort:
            for field, direction in reversed(sort):
                reverse = int(direction) == -1
                rows.sort(key=lambda d: str(d.get(field) or ""), reverse=reverse)
        if not rows:
            return None
        doc = dict(rows[0])
        if projection and projection.get("_id") == 0:
            doc.pop("_id", None)
        return doc

    def find(self, query=None, projection=None):
        rows = [dict(d) for d in self.docs if self._matches(d, query or {})]
        if projection and projection.get("_id") == 0:
            for row in rows:
                row.pop("_id", None)
        return _FakeCursor(rows)


class _FakeDb:
    def __init__(self):
        self.agreement_acknowledgements = _FakeCollection([])
        self.generated_contracts = _FakeCollection([])
        self.org_settings = _FakeCollection([{"company_name": "Osabea", "company_address": "Addr A"}])
        self.contract_templates = _FakeCollection([])


def test_latest_generated_contract_overrides_stale_rejected_ack(monkeypatch):
    db = _FakeDb()
    employee = {"id": "emp-1", "name": "Test User"}
    db.agreement_acknowledgements.docs = [
        {
            "id": "ack-old",
            "employee_id": "emp-1",
            "agreement_type": "contract_acceptance",
            "status": "rejected",
            "verification_status": "rejected",
            "contract_state": "rejected_reopen_required",
            "template_version": "contract_acceptance_v_old",
            "rendered_contract_pdf_url": "https://example.test/old.pdf",
        }
    ]
    db.generated_contracts.docs = [
        {
            "id": "contract-v1",
            "employee_id": "emp-1",
            "status": "rejected_reopen_required",
            "generated_at": "2026-04-20T10:00:00+00:00",
            "template_version": "contract_acceptance_v_old",
        },
        {
            "id": "contract-v2",
            "employee_id": "emp-1",
            "status": "awaiting_worker_signature",
            "generated_at": "2026-04-27T10:00:00+00:00",
            "template_version": "contract_acceptance_v_new",
            "rendered_contract_pdf_url": "https://example.test/new.pdf",
        },
    ]

    async def _ensure(_db, _employee, _agreement_type):
        return {
            "id": "ack-old",
            "employee_id": "emp-1",
            "agreement_type": "contract_acceptance",
            "status": "rejected",
            "verification_status": "rejected",
        }

    monkeypatch.setattr("agreement_document_service.ensure_agreement_rendered", _ensure)

    state = asyncio.run(resolve_employee_agreement_state(db, employee, CONTRACT_AGREEMENT_TYPE))
    assert state["contract_state"] == "awaiting_worker_signature"
    assert state["status"] == "awaiting_worker_signature"
    assert state["rejected"] is False
    assert state["can_sign"] is True
    assert state["acknowledgement"]["active_contract_id"] == "contract-v2"
