import os
import sys
import asyncio
from types import SimpleNamespace

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from routes import worker_dashboard as wd  # noqa: E402


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return self.docs if length is None else self.docs[:length]


class _Collection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def find_one(self, query=None, projection=None, sort=None):
        query = query or {}
        matches = []
        for d in self.docs:
            ok = True
            for k, v in query.items():
                if k == "$or":
                    continue
                if isinstance(v, dict) and "$ne" in v:
                    if d.get(k) == v["$ne"]:
                        ok = False
                        break
                elif d.get(k) != v:
                    ok = False
                    break
            if ok:
                matches.append(d)
        if not matches:
            return None
        return dict(matches[0])

    async def update_one(self, filt, update, upsert=False):
        for d in self.docs:
            ok = True
            for k, v in filt.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                d.update(update.get("$set", {}))
                for key in update.get("$unset", {}).keys():
                    d.pop(key, None)
                return SimpleNamespace(modified_count=1, matched_count=1)
        if upsert:
            new_doc = dict(filt)
            new_doc.update(update.get("$set", {}))
            self.docs.append(new_doc)
            return SimpleNamespace(modified_count=1, matched_count=0, upserted_id=new_doc.get("id"))
        return SimpleNamespace(modified_count=0, matched_count=0)

    def find(self, query=None, projection=None):
        return _Cursor([])


class _Db:
    def __init__(self):
        self.employees = _Collection([{"id": "emp-1", "first_name": "Olu", "last_name": "Mide"}])
        self.agreement_acknowledgements = _Collection(
            [
                {
                    "id": "hb-1",
                    "employee_id": "emp-1",
                    "agreement_type": "handbook_acknowledgement",
                    "status": "pending",
                    "verification_status": "pending",
                }
            ]
        )


def test_handbook_acknowledge_accepts_alias_and_updates_latest_active(monkeypatch):
    db = _Db()
    monkeypatch.setattr(wd, "get_db", lambda: db)
    async def _ensure(_db, _emp, _type):
        return {
            "id": "hb-1",
            "template_version": "handbook_acknowledgement_v_00d5c51e4bd4",
            "rendered_file_url": "https://files/handbook.pdf",
            "employee_name": "Olu Mide",
        }
    async def _audit(*a, **k):
        return None
    async def _noop(*a, **k):
        return None
    monkeypatch.setattr(wd, "ensure_agreement_rendered", _ensure)
    async def _resolve(_db, _emp, _type):
        return {
            "source_record_id": "hb-1",
            "status": "pending",
            "template_version": "handbook_acknowledgement_v_00d5c51e4bd4",
            "rendered_file_url": "https://files/handbook.pdf",
        }
    monkeypatch.setattr(wd, "resolve_employee_agreement_state", _resolve)
    monkeypatch.setattr(wd, "log_audit_action", _audit)
    monkeypatch.setattr(wd, "get_try_auto_promote_worker_func", lambda: _noop)

    payload = wd.AgreementAcknowledgeRequest(signer_name="Olu Mide")
    result = asyncio.run(
        wd.acknowledge_worker_agreement(
            agreement_type="employee_handbook_acknowledgement",
            payload=payload,
            worker={"employee_id": "emp-1"},
        )
    )
    assert result["success"] is True
    assert result["message"] == "Agreement acknowledged successfully"


def test_handbook_acknowledge_idempotent_when_already_acknowledged(monkeypatch):
    db = _Db()
    monkeypatch.setattr(wd, "get_db", lambda: db)
    async def _resolve(_db, _emp, _type):
        return {
            "id": "hb-1",
            "source_record_id": "hb-1",
            "status": "acknowledged",
            "template_version": "handbook_acknowledgement_v_00d5c51e4bd4",
            "rendered_file_url": "https://files/handbook.pdf",
        }
    monkeypatch.setattr(wd, "resolve_employee_agreement_state", _resolve)
    payload = wd.AgreementAcknowledgeRequest(signer_name="Olu Mide")
    result = asyncio.run(
        wd.acknowledge_worker_agreement(
            agreement_type="handbook_acknowledgement",
            payload=payload,
            worker={"employee_id": "emp-1"},
        )
    )
    assert result["success"] is True
    assert result["message"] == "Agreement already acknowledged"
