import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routes import recruitment


class _Cursor:
    def __init__(self, docs):
        self.docs = list(docs)

    async def to_list(self, _limit=None):
        return list(self.docs)


class _Employees:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query, projection=None):
        statuses = query.get("status", {}).get("$in", [])
        rows = [d for d in self.docs if d.get("status") in statuses]
        return _Cursor(rows)

    async def find_one(self, query, projection=None):
        target_id = query.get("id")
        statuses = query.get("status", {}).get("$in", [])
        for row in self.docs:
            if row.get("id") == target_id and row.get("status") in statuses:
                return dict(row)
        return None


class _Db:
    def __init__(self, docs):
        self.employees = _Employees(docs)


def test_applicants_list_does_not_call_uce(monkeypatch):
    db = _Db(
        [
            {
                "id": "a1",
                "status": "new",
                "first_name": "A",
                "last_name": "One",
                "email": "a1@test",
                "completion_percentage": 91,
                "completed_requirements": 10,
                "total_requirements": 11,
                "blockers_count": 0,
                "awaiting_review_count": 1,
            }
        ]
    )
    monkeypatch.setattr(recruitment, "get_db", lambda: db)

    async def _boom(*args, **kwargs):
        raise AssertionError("UCE should not be called for list endpoint")

    monkeypatch.setitem(sys.modules, "unified_compliance_engine", type("M", (), {"get_unified_employee_status": _boom}))

    result = asyncio.run(recruitment.get_applicants(user={"id": "u"}))
    assert len(result) == 1
    assert result[0]["completion_percentage"] == 91
    assert result[0]["completed_requirements"] == 10


def test_applicants_list_handles_malformed_progress_fields(monkeypatch):
    db = _Db(
        [
            {
                "id": "a2",
                "status": "screening",
                "first_name": "B",
                "last_name": "Two",
                "email": "a2@test",
                "completion_percentage": None,
                "completed_requirements": None,
                "total_requirements": None,
            }
        ]
    )
    monkeypatch.setattr(recruitment, "get_db", lambda: db)
    result = asyncio.run(recruitment.get_applicants(user={"id": "u"}))
    assert len(result) == 1
    assert result[0]["completion_percentage"] == 0
    assert result[0]["completed_requirements"] == 0
    assert result[0]["total_requirements"] == 0

