import pytest

from work_readiness_engine import can_sign_contract


class _Cursor:
    def __init__(self, items):
        self._items = items

    async def to_list(self, _length):
        return list(self._items)


class _Collection:
    def __init__(self, items=None):
        self._items = items or []

    async def find_one(self, query, projection=None):
        for item in self._items:
            ok = True
            for k, v in query.items():
                if item.get(k) != v:
                    ok = False
                    break
            if ok:
                return dict(item)
        return None

    def find(self, query):
        return _Cursor([])


class _DB:
    def __init__(self, employee):
        self.employees = _Collection([employee])
        self.form_submissions = _Collection([])
        self.training_records = _Collection([])


@pytest.mark.asyncio
async def test_can_sign_contract_uses_unified_references_category_when_check_key_missing(monkeypatch):
    employee = {
        "id": "emp_ref_category_ok",
        "role": "support worker",
        # Modern slot-based reference truth (no legacy references[] needed)
        "reference_1_status": "verified",
        "reference_2_status": "verified",
    }
    db = _DB(employee)

    async def _fake_unified_status(_employee_id, _db, user_role="admin", include_details=True):
        return {
            "error": None,
            "checks": {
                "right_to_work": True,
                "dbs": True,
                "identity": True,
                "proof_of_address": True,
                "staff_health_questionnaire": True,
                "staff_personal_info": True,
                "hmrc_starter_checklist": True,
                "emergency_contacts": True,
                "mandatory_training": True,
                "induction": True,
                # intentionally omit "references" key to trigger category fallback path
            },
            "categories": {
                "references": {"total": 2, "completed": 2},
            },
            "category_details": {
                "training": {
                    "total": 8,
                    "completed": 8,
                    "items": [{"name": "T", "completed": True}] * 8,
                },
                "induction": {"total": 15, "completed": 15},
                "references": {"total": 2, "completed": 2},
            },
        }

    async def _fake_read_agreement_state(_db, _employee, agreement_type):
        if agreement_type == "handbook_acknowledgement":
            return {"status": "verified", "system_issue": False}
        return {"status": "pending_signature", "render_issue": None}

    monkeypatch.setattr(
        "unified_compliance_engine.get_unified_employee_status",
        _fake_unified_status,
        raising=True,
    )
    monkeypatch.setattr(
        "agreement_document_service.read_employee_agreement_state",
        _fake_read_agreement_state,
        raising=True,
    )
    monkeypatch.setattr(
        "agreement_document_service.get_current_contract_template_version",
        lambda _db: "v1",
        raising=True,
    )
    monkeypatch.setattr(
        "agreement_document_service.needs_unsigned_contract_render_repair",
        lambda _state, _version: False,
        raising=True,
    )

    result = await can_sign_contract(db, employee["id"])
    assert result["can_sign"] is True
    assert result["progress_percentage"] >= 100


@pytest.mark.asyncio
async def test_can_sign_contract_reports_render_readiness_failure_as_explicit_blocker(monkeypatch):
    employee = {
        "id": "emp_render_gate",
        "role": "support worker",
        "reference_1_status": "verified",
        "reference_2_status": "verified",
    }
    db = _DB(employee)

    async def _fake_unified_status(_employee_id, _db, user_role="admin", include_details=True):
        return {
            "error": None,
            "checks": {
                "right_to_work": True,
                "dbs": True,
                "identity": True,
                "proof_of_address": True,
                "staff_health_questionnaire": True,
                "staff_personal_info": True,
                "hmrc_starter_checklist": True,
                "emergency_contacts": True,
                "mandatory_training": True,
                "induction": True,
                "references": True,
            },
            "categories": {},
            "category_details": {
                "training": {
                    "total": 8,
                    "completed": 8,
                    "items": [{"name": "T", "completed": True}] * 8,
                },
                "induction": {"total": 15, "completed": 15},
            },
        }

    async def _fake_read_agreement_state(_db, _employee, agreement_type):
        if agreement_type == "handbook_acknowledgement":
            return {"status": "verified", "system_issue": False}
        return {"status": "pending_signature", "render_issue": "stale render"}

    monkeypatch.setattr(
        "unified_compliance_engine.get_unified_employee_status",
        _fake_unified_status,
        raising=True,
    )
    monkeypatch.setattr(
        "agreement_document_service.read_employee_agreement_state",
        _fake_read_agreement_state,
        raising=True,
    )
    monkeypatch.setattr(
        "agreement_document_service.get_current_contract_template_version",
        lambda _db: "v2",
        raising=True,
    )
    monkeypatch.setattr(
        "agreement_document_service.needs_unsigned_contract_render_repair",
        lambda _state, _version: True,
        raising=True,
    )

    result = await can_sign_contract(db, employee["id"])
    assert result["can_sign"] is False
    assert any("stale render" in b.lower() for b in result["blockers"])
