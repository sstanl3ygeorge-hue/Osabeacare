import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


class _FakeEmployeesCollection:
    async def find_one(self, query, _projection):
        return {"id": query["id"], "role": "Healthcare Assistant"}


class _FakeDB:
    employees = _FakeEmployeesCollection()


def test_compute_unified_progress_internal_uses_unified_status(monkeypatch):
    async def _fake_unified_status(employee_id, _db, user_role="admin", include_details=True):
        assert employee_id == "emp-100"
        assert user_role == "admin"
        assert include_details is True
        return {
            "progress": {"percentage": 100, "completed": 24, "total": 24},
            "categories": {
                "training": {"completed": 8, "total": 8},
                "agreements": {"completed": 2, "total": 2},
            },
            "blockers": [],
        }

    monkeypatch.setattr(server, "db", _FakeDB())
    monkeypatch.setattr(server, "get_unified_employee_status", _fake_unified_status)

    result = asyncio.run(server.compute_unified_progress_internal("emp-100"))

    assert result["overall_percentage"] == 100
    assert result["completed_requirements"] == 24
    assert result["total_requirements"] == 24
    assert result["categories"]["training"] == {"completed": 8, "total": 8}
    assert result["blockers"] == []


def test_compute_unified_progress_internal_preserves_canonical_blockers(monkeypatch):
    async def _fake_unified_status(_employee_id, _db, user_role="admin", include_details=True):
        return {
            "progress": {"percentage": 92, "completed": 22, "total": 24},
            "categories": {
                "training": {"completed": 8, "total": 8},
                "agreements": {"completed": 1, "total": 2},
            },
            "blockers": [
                {"label": "Employee Handbook", "reason": "Employee Handbook: Not acknowledged by worker"},
            ],
        }

    monkeypatch.setattr(server, "db", _FakeDB())
    monkeypatch.setattr(server, "get_unified_employee_status", _fake_unified_status)

    result = asyncio.run(server.compute_unified_progress_internal("emp-200"))

    assert result["overall_percentage"] == 92
    assert result["categories"]["agreements"] == {"completed": 1, "total": 2}
    assert result["blockers"] == ["Employee Handbook: Not acknowledged by worker"]
