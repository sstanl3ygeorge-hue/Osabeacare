import os
import sys
import asyncio
import base64
import types

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

sys.modules.setdefault("motor", types.ModuleType("motor"))
motor_asyncio_mod = sys.modules.setdefault("motor.motor_asyncio", types.ModuleType("motor.motor_asyncio"))
class _FakeAsyncIOMotorClient:
    def __init__(self, *_args, **_kwargs):
        pass
    def __getitem__(self, _name):
        return types.SimpleNamespace()
motor_asyncio_mod.AsyncIOMotorClient = _FakeAsyncIOMotorClient

import server  # noqa: E402
import agreement_document_service as ads  # noqa: E402
import supabase_storage as ss  # noqa: E402


class _Collection:
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

    async def update_one(self, filt, update, upsert=False):
        for d in self.docs:
            ok = True
            for k, v in filt.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                d.update(update.get("$set", {}))
                return
        if upsert:
            doc = dict(filt)
            doc.update(update.get("$set", {}))
            self.docs.append(doc)


class _Db:
    def __init__(self):
        self.employees = _Collection([{"id": "emp-1", "employee_code": "EMP-1"}])
        self.agreement_acknowledgements = _Collection(
            [{"id": "ack-stale", "employee_id": "emp-1", "agreement_type": "contract_acceptance", "status": None}]
        )


def test_worker_sign_uses_latest_canonical_generated_contract(monkeypatch):
    db = _Db()
    monkeypatch.setattr(server, "db", db)

    async def _upload(*_a, **_k):
        return "https://files/signature.png"

    captured = {}

    async def _resolve(_db, _emp, _type):
        return {
            "status": "pending_signature",
            "raw_status": "awaiting_worker_signature",
            "source_record_id": "gc-latest",
            "agreement_type": "contract_acceptance",
            "can_sign": True,
            "template_version": "contract_acceptance_v_87d36a6c5859",
            "rendered_file_url": "https://files/contract.pdf",
        }

    async def _ensure(_db, _emp, _type):
        return {
            "id": "ack-stale",
            "template_version": "contract_acceptance_v_87d36a6c5859",
            "rendered_contract_pdf_url": "https://files/contract.pdf",
        }

    async def _create(_db, _emp, agreement, _sig, _name):
        captured["source_record_id"] = agreement.get("source_record_id")
        return {
            "id": "ack-stale",
            "contract_state": "awaiting_company_countersignature",
            "worker_signed_contract_pdf_url": "https://files/worker-signed.pdf",
            "rendered_contract_pdf_url": "https://files/contract.pdf",
            "worker_signed_at": "2026-04-28T10:00:00+00:00",
        }

    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(ss, "upload_file_to_storage", _upload)
    monkeypatch.setattr(server, "log_audit_action", _noop)
    monkeypatch.setattr(server, "try_auto_promote_worker", _noop)
    monkeypatch.setattr(ads, "resolve_employee_agreement_state", _resolve)
    monkeypatch.setattr(ads, "ensure_agreement_rendered", _ensure)
    monkeypatch.setattr(ads, "create_worker_signed_contract", _create)

    payload = server.ContractSignatureRequest(
        signature_base64=base64.b64encode(b"sig").decode("utf-8"),
        full_name="Test Worker",
    )
    result = asyncio.run(
        server.sign_contract(
            employee_id="emp-1",
            request=payload,
            worker={"employee_id": "emp-1"},
        )
    )

    assert result["success"] is True
    assert result["contract_state"] == "awaiting_company_countersignature"
    assert captured["source_record_id"] == "gc-latest"


def test_worker_sign_idempotent_if_already_signed(monkeypatch):
    db = _Db()
    monkeypatch.setattr(server, "db", db)

    async def _resolve(_db, _emp, _type):
        return {
            "status": "awaiting_company_countersignature",
            "rendered_file_url": "https://files/worker-signed.pdf",
            "signed_at": "2026-04-28T10:00:00+00:00",
        }

    async def _upload(*_a, **_k):
        return "https://files/signature.png"

    monkeypatch.setattr(ss, "upload_file_to_storage", _upload)
    monkeypatch.setattr(ads, "resolve_employee_agreement_state", _resolve)
    payload = server.ContractSignatureRequest(
        signature_base64=base64.b64encode(b"sig").decode("utf-8"),
        full_name="Test Worker",
    )
    result = asyncio.run(
        server.sign_contract(
            employee_id="emp-1",
            request=payload,
            worker={"employee_id": "emp-1"},
        )
    )
    assert result["success"] is True
    assert result["message"] == "Contract already signed"
