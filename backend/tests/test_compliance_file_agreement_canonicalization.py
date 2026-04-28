import asyncio
import os
import sys
from types import SimpleNamespace

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import server  # noqa: E402
import agreement_document_service  # noqa: E402


class _FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, *args, **kwargs):
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

    async def find_one(self, query=None, projection=None, sort=None):
        query = query or {}
        for d in self.docs:
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                return dict(d)
        return None

    def find(self, query=None, projection=None):
        query = query or {}
        out = []
        for d in self.docs:
            ok = True
            for k, v in query.items():
                if isinstance(v, dict) and "$in" in v:
                    if d.get(k) not in v["$in"]:
                        ok = False
                        break
                elif d.get(k) != v:
                    ok = False
                    break
            if ok:
                out.append(dict(d))
        return _FakeCursor(out)


class _FakeDb:
    def __init__(self):
        self.employees = _FakeCollection(
            [{"id": "emp-1", "first_name": "Olumide", "last_name": "OBEMBE", "role": "healthcare_assistant"}]
        )
        self.employee_documents = _FakeCollection([])
        self.document_extractions = _FakeCollection([])
        self.email_requests = _FakeCollection([])
        self.agreement_submissions = _FakeCollection(
            [
                {
                    "id": "sub-handbook-1",
                    "employee_id": "emp-1",
                    "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
                    "template_version": "handbook_acknowledgement_v_00d5c51e4bd4",
                    "verification_status": "awaiting_review",
                }
            ]
        )
        self.references = _FakeCollection([])
        self.org_settings = _FakeCollection([{"company_name": "Osabea", "company_address": "Suite FA4D"}])
        self.form_submissions = _FakeCollection([])


def test_compliance_file_agreement_rows_use_canonical_resolver(monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(server, "db", fake_db)

    async def _none(*args, **kwargs):
        return None

    async def _empty(*args, **kwargs):
        return []

    async def _fake_eval(*args, **kwargs):
        return {"status": "ok"}

    async def _fake_agr_state(db, employee, agreement_type):
        if agreement_type == "contract_acceptance":
            return {
                "agreement_type": "contract_acceptance",
                "acknowledgement": {"id": "ack-old-null"},
                "status": "pending_signature",
                "raw_status": "awaiting_worker_signature",
                "contract_state": "pending_signature",
                "state_label": "Action required: please review and sign your contract",
                "template_version": "contract_acceptance_v_87d36a6c5859",
                "can_sign": True,
                "signed": False,
                "verified": False,
                "rejected": False,
                "has_acknowledgement": True,
            }
        return {
            "agreement_type": "handbook_acknowledgement",
            "acknowledgement": {"id": "ack-hb-1"},
            "status": "pending",
            "state_label": "Action required: please review and acknowledge the handbook",
            "template_version": "handbook_acknowledgement_v_00d5c51e4bd4",
            "can_sign": True,
            "signed": False,
            "verified": False,
            "rejected": False,
            "has_acknowledgement": True,
        }

    monkeypatch.setattr(server.CheckRecordService, "get_current_rtw_check", _none)
    monkeypatch.setattr(server.CheckRecordService, "get_current_dbs_check", _none)
    monkeypatch.setattr(server.CheckRecordService, "get_current_identity_check", _none)
    monkeypatch.setattr(server.CheckRecordService, "get_current_address_check", _none)
    monkeypatch.setattr(server.CheckRecordService, "get_rtw_check_history", _empty)
    monkeypatch.setattr(server.CheckRecordService, "get_dbs_check_history", _empty)
    async def _fake_get_agreements(employee_id):
        return {"acknowledgements": [], "pending_requests": []}

    monkeypatch.setattr(server.AgreementAcknowledgementService, "get_employee_agreements", _fake_get_agreements)
    monkeypatch.setattr(server.ReferenceIntegrityService, "get_reference_integrity", _none)
    monkeypatch.setattr(server, "evaluate_employee_training_status", _fake_eval)
    monkeypatch.setattr(server, "get_unified_employee_status", lambda *a, **k: _fake_eval())
    monkeypatch.setattr(server, "_build_employment_history_compliance_row", lambda *a, **k: _fake_eval())
    monkeypatch.setattr(agreement_document_service, "resolve_employee_agreement_state", _fake_agr_state)

    data = asyncio.run(server.get_compliance_file("emp-1", user={"id": "u1", "role": "admin"}))
    rows = data["sections"]["agreements"]["rows"]
    contract = [r for r in rows if r["key"] == "contract_acceptance"][0]
    handbook = [r for r in rows if r["key"] in {"handbook_acknowledgement", "employee_handbook_acknowledgement"}][0]

    assert contract["status"] == "pending_signature"
    assert contract["acknowledgement_data"]["raw_status"] == "awaiting_worker_signature"
    assert contract["template_version"] == "contract_acceptance_v_87d36a6c5859"
    assert contract["can_sign"] is True
    assert contract["latest_active"] is True
    assert contract["source_record_id"] == "ack-old-null"

    assert handbook["template_version"] == "handbook_acknowledgement_v_00d5c51e4bd4"
    assert handbook["can_acknowledge"] is not None
    assert handbook["latest_active"] is not None
    assert handbook["source_record_id"] == "ack-hb-1"
