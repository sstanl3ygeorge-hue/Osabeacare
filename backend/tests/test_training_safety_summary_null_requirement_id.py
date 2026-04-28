import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import server


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def to_list(self, _limit):
        return list(self._rows)


class _FakeCollection:
    def __init__(self, rows):
        self._rows = rows

    def find(self, *_args, **_kwargs):
        return _FakeCursor(self._rows)

    async def find_one(self, query, *_args, **_kwargs):
        for row in self._rows:
            if row.get("id") == query.get("id"):
                return row
        return None


class _FakeDB:
    def __init__(self, employees, training_records):
        self.employees = _FakeCollection(employees)
        self.training_records = _FakeCollection(training_records)


def test_training_safety_summary_handles_null_requirement_id(monkeypatch):
    fake_db = _FakeDB(
        employees=[{"id": "emp-1", "role": "care_worker"}],
        training_records=[
            {
                "id": "tr-1",
                "employee_id": "emp-1",
                "requirement_id": None,
                "training_name": "Malformed record",
                "verified": True,
                "status": "verified",
            }
        ],
    )
    monkeypatch.setattr(server, "db", fake_db)

    warnings = []

    def _capture_warning(message):
        warnings.append(message)

    monkeypatch.setattr(server.logger, "warning", _capture_warning)

    result = asyncio.run(server.get_employee_training_safety_summary("emp-1"))

    assert isinstance(result, dict)
    assert "status_band" in result
    assert any("records_missing_requirement_id=1" in w for w in warnings)
