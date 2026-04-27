import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.training_taxonomy import map_training_title_to_canonical
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


def _days_from_now(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


def test_safeguarding_adults_maps_to_split_key():
    code, _ = map_training_title_to_canonical("CSTF Safeguarding Adults Levels 1 and 2")
    assert code == "safeguarding_adults"


def test_safeguarding_children_maps_to_split_key():
    code, _ = map_training_title_to_canonical("CSTF Safeguarding Children Levels 1 and 2")
    assert code == "safeguarding_children"


def test_adult_resuscitation_maps_to_adult_bls():
    code, _ = map_training_title_to_canonical("CSTF Resuscitation Adults Levels 1, 2 & 3 (Practical)")
    assert code == "basic_life_support_adults"


def test_paediatric_resuscitation_maps_to_paediatric_bls():
    code, _ = map_training_title_to_canonical("CSTF Resuscitation Paediatric Levels 2 and 3 Practical")
    assert code == "paediatric_basic_life_support"


def test_mca_maps_to_mental_capacity_act():
    code, _ = map_training_title_to_canonical("Mental Capacity Act")
    assert code == "mental_capacity_act"


def test_dols_maps_to_deprivation_of_liberty_safeguards():
    code, _ = map_training_title_to_canonical("Deprivation of Liberty Safeguards (DoLS)")
    assert code == "deprivation_of_liberty_safeguards"


async def _run_eval(records, required_training):
    te.set_db(_FakeDB(records))

    async def _fake_required_training(_employee_id, _role=""):
        return required_training

    original = te.get_required_training_for_employee
    te.get_required_training_for_employee = _fake_required_training
    try:
        return await te.evaluate_employee_training_status("emp-1", "Nurse")
    finally:
        te.get_required_training_for_employee = original


def test_mca_does_not_satisfy_dols():
    result = asyncio.run(
        _run_eval(
            records=[
                {
                    "id": "tr-mca",
                    "employee_id": "emp-1",
                    "requirement_id": "mental_capacity_act",
                    "training_name": "Mental Capacity Act",
                    "verified": True,
                    "completion_date": _days_from_now(-20),
                    "expiry_date": _days_from_now(200),
                    "record_status": "active",
                }
            ],
            required_training=[{"id": "deprivation_of_liberty_safeguards", "name": "Deprivation of Liberty Safeguards"}],
        )
    )
    assert result["items"][0]["status"] in {"missing", "awaiting_review"}
    assert result["blockerCount"] == 1


def test_dols_does_not_satisfy_mca():
    result = asyncio.run(
        _run_eval(
            records=[
                {
                    "id": "tr-dols",
                    "employee_id": "emp-1",
                    "requirement_id": "deprivation_of_liberty_safeguards",
                    "training_name": "Deprivation of Liberty Safeguards",
                    "verified": True,
                    "completion_date": _days_from_now(-20),
                    "expiry_date": _days_from_now(200),
                    "record_status": "active",
                }
            ],
            required_training=[{"id": "mental_capacity_act", "name": "Mental Capacity Act"}],
        )
    )
    assert result["items"][0]["status"] in {"missing", "awaiting_review"}
    assert result["blockerCount"] == 1
