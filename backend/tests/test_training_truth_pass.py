import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import training_evaluator as te


class _FakeCursor:
    def __init__(self, records):
        self._records = records

    async def to_list(self, _limit):
        return list(self._records)


class _FakeCollection:
    def __init__(self, records):
        self._records = records

    def find(self, *_args, **_kwargs):
        return _FakeCursor(self._records)


class _FakeDB:
    def __init__(self, records):
        self.training_records = _FakeCollection(records)


async def _run_eval(monkeypatch, records, required_training, role="Healthcare Assistant"):
    te.set_db(_FakeDB(records))

    async def _fake_required_training(_employee_id, _role=""):
        return required_training

    monkeypatch.setattr(te, "get_required_training_for_employee", _fake_required_training)
    return await te.evaluate_employee_training_status("emp-123", role)


def _days_from_now(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


def test_verified_mandatory_training_counts_as_compliant(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_verified",
            "employee_id": "emp-123",
            "requirement_id": "manual_handling",
            "training_name": "Manual Handling",
            "verified": True,
            "completion_date": _days_from_now(-30),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "manual_handling", "name": "Manual Handling"}],
    ))

    assert result["blockerCount"] == 0
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["verified"] is True


def test_unverified_canonical_training_does_not_count(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_unverified",
            "employee_id": "emp-123",
            "requirement_id": "manual_handling",
            "training_name": "Manual Handling",
            "verified": False,
            "completion_date": _days_from_now(-30),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "manual_handling", "name": "Manual Handling"}],
    ))

    assert result["blockerCount"] == 1
    assert result["items"][0]["status"] == "awaiting_review"
    assert result["items"][0]["verified"] is False


def test_proposed_items_outside_training_records_do_not_count(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[],
        required_training=[{"id": "manual_handling", "name": "Manual Handling"}],
    ))

    assert result["blockerCount"] == 1
    assert result["items"][0]["status"] == "missing"
    assert result["items"][0]["record_id"] is None


def test_expired_verified_training_does_not_count(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_expired",
            "employee_id": "emp-123",
            "requirement_id": "fire_safety",
            "training_name": "Fire Safety",
            "verified": True,
            "completion_date": _days_from_now(-400),
            "expiry_date": _days_from_now(-2),
            "record_status": "active",
        }],
        required_training=[{"id": "fire_safety", "name": "Fire Safety"}],
    ))

    assert result["blockerCount"] == 1
    assert result["items"][0]["status"] == "expired"
    assert result["items"][0]["verified"] is True


def test_due_soon_verified_training_still_counts(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_due_soon",
            "employee_id": "emp-123",
            "requirement_id": "basic_life_support",
            "training_name": "Basic Life Support",
            "verified": True,
            "completion_date": _days_from_now(-300),
            "expiry_date": _days_from_now(10),
            "record_status": "active",
        }],
        required_training=[{"id": "basic_life_support", "name": "Basic Life Support"}],
    ))

    assert result["blockerCount"] == 0
    assert result["warningCount"] == 1
    assert result["items"][0]["status"] == "due_soon"
    assert result["items"][0]["verified"] is True


def test_duplicate_training_records_count_once_with_verified_winning(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[
            {
                "id": "tr_verified",
                "employee_id": "emp-123",
                "requirement_id": "manual_handling",
                "training_name": "Manual Handling",
                "verified": True,
                "completion_date": _days_from_now(-120),
                "expiry_date": _days_from_now(200),
                "record_status": "active",
            },
            {
                "id": "tr_unverified_newer",
                "employee_id": "emp-123",
                "requirement_id": "manual_handling",
                "training_name": "Manual Handling",
                "verified": False,
                "completion_date": _days_from_now(-10),
                "expiry_date": _days_from_now(350),
                "record_status": "active",
            },
        ],
        required_training=[{"id": "manual_handling", "name": "Manual Handling"}],
    ))

    assert len(result["items"]) == 1
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["record_id"] == "tr_verified"
    assert result["blockerCount"] == 0


def test_infection_prevention_and_control_alias_satisfies_infection_control(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_ipc",
            "employee_id": "emp-123",
            "requirement_id": "",
            "training_name": "Infection Prevention and Control",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(120),
            "record_status": "active",
        }],
        required_training=[{"id": "infection_control", "name": "Infection Control"}],
    ))

    assert result["blockerCount"] == 0
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["record_id"] == "tr_ipc"


def test_safeguarding_adult_role_with_adults_verified_is_satisfied(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_sg_adults",
            "employee_id": "emp-123",
            "requirement_id": "safeguarding_adults",
            "training_name": "Safeguarding Adults",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Healthcare Assistant",
    ))

    assert result["blockerCount"] == 0
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["detail"] == "Safeguarding Adults verified"


def test_safeguarding_adult_role_with_generic_verified_is_satisfied(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_sg_generic",
            "employee_id": "emp-123",
            "requirement_id": "safeguarding",
            "training_name": "Safeguarding",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Support Worker",
    ))

    assert result["blockerCount"] == 0
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["detail"] == "Safeguarding verified"


def test_safeguarding_adult_role_with_children_only_is_not_satisfied(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_sg_children",
            "employee_id": "emp-123",
            "requirement_id": "safeguarding_children",
            "training_name": "Safeguarding Children",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Healthcare Assistant",
    ))

    assert result["blockerCount"] == 1
    assert result["items"][0]["status"] == "missing"
    assert "Adults or generic Safeguarding required" in result["items"][0]["detail"]


def test_safeguarding_child_role_with_children_verified_is_satisfied(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_sg_children",
            "employee_id": "emp-123",
            "requirement_id": "safeguarding_children",
            "training_name": "Safeguarding Children",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Children Support Worker",
    ))

    assert result["blockerCount"] == 0
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["detail"] == "Safeguarding Children verified"


def test_safeguarding_child_role_with_adults_only_is_not_satisfied(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_sg_adults",
            "employee_id": "emp-123",
            "requirement_id": "safeguarding_adults",
            "training_name": "Safeguarding Adults",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Paediatric Support Worker",
    ))

    assert result["blockerCount"] == 1
    assert result["items"][0]["status"] == "missing"
    assert "Children or generic Safeguarding required" in result["items"][0]["detail"]


def test_safeguarding_both_role_with_only_adults_is_partial(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_sg_adults",
            "employee_id": "emp-123",
            "requirement_id": "safeguarding_adults",
            "training_name": "Safeguarding Adults",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Adult and Child Support Worker",
    ))

    assert result["blockerCount"] == 1
    assert result["items"][0]["status"] == "partial"
    assert "both Adults and Children are required" in result["items"][0]["detail"]


def test_safeguarding_both_role_with_both_verified_is_satisfied(monkeypatch):
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[
            {
                "id": "tr_sg_adults",
                "employee_id": "emp-123",
                "requirement_id": "safeguarding_adults",
                "training_name": "Safeguarding Adults",
                "verified": True,
                "completion_date": _days_from_now(-20),
                "expiry_date": _days_from_now(200),
                "record_status": "active",
            },
            {
                "id": "tr_sg_children",
                "employee_id": "emp-123",
                "requirement_id": "safeguarding_children",
                "training_name": "Safeguarding Children",
                "verified": True,
                "completion_date": _days_from_now(-20),
                "expiry_date": _days_from_now(200),
                "record_status": "active",
            },
        ],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Adults and Children Coordinator",
    ))

    assert result["blockerCount"] == 0
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["detail"] == "Safeguarding Adults and Children verified"


def test_safeguarding_combined_policy_keeps_generic_compatibility(monkeypatch):
    monkeypatch.setattr(te, "SAFEGUARDING_COMPOSITE_POLICY", "combined")
    result = asyncio.run(_run_eval(
        monkeypatch,
        records=[{
            "id": "tr_sg_generic",
            "employee_id": "emp-123",
            "requirement_id": "safeguarding",
            "training_name": "Safeguarding",
            "verified": True,
            "completion_date": _days_from_now(-20),
            "expiry_date": _days_from_now(200),
            "record_status": "active",
        }],
        required_training=[{"id": "safeguarding", "name": "Safeguarding"}],
        role="Adults and Children Coordinator",
    ))

    assert result["blockerCount"] == 0
    assert result["items"][0]["status"] == "verified"
    assert result["items"][0]["detail"] == "Safeguarding verified"
