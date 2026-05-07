import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def to_list(self, _limit):
        return list(self._rows)


class _FakeCollection:
    def __init__(self, rows=None):
        self._rows = rows or []

    def find(self, *_args, **_kwargs):
        return _FakeCursor(self._rows)


class _FakeDB:
    def __init__(self, *, employees, training_records, proposed_items):
        self.employees = _FakeCollection(employees)
        self.training_records = _FakeCollection(training_records)
        self.proposed_training_items = _FakeCollection(proposed_items)


def _build_fake_records_for_scope_all(employee_id):
    records = []
    for col in server._training_matrix_columns():
        if col.get("scope") != "all":
            continue
        records.append(
            {
                "id": f"rec-{col['id']}",
                "employee_id": employee_id,
                "requirement_id": col["id"],
                "training_name": col["name"],
                "verification_status": "verified",
                "verified": True,
                "completion_date": "2026-01-10",
                "expiry_date": "2027-01-10",
                "record_status": "active",
            }
        )
    return records


def _setup_non_nurse_matrix(monkeypatch):
    employee_id = "emp-non-nurse"
    fake_db = _FakeDB(
        employees=[
            {
                "id": employee_id,
                "first_name": "Audit",
                "last_name": "User",
                "role": "administrator",
                "status": "active",
                "lifecycle": "Active Workforce",
                "start_date": "2025-01-01",
                "probation_end_date": "2025-04-01",
                "next_appraisal_date": "2026-01-01",
            }
        ],
        training_records=_build_fake_records_for_scope_all(employee_id),
        proposed_items=[],
    )
    monkeypatch.setattr(server, "db", fake_db)


def test_average_excludes_non_applicable_columns(monkeypatch):
    _setup_non_nurse_matrix(monkeypatch)

    model = asyncio.run(server.build_training_matrix_read_model())

    nurse_column_ids = [c["id"] for c in model["columns"] if c.get("scope") == "nurse"]
    assert nurse_column_ids, "Expected at least one nurse-only column"

    # Nurse-only columns are not applicable and must not reduce average.
    assert all(model["column_applicability"][col_id] is False for col_id in nurse_column_ids)
    assert all(model["column_percentages"][col_id] == 0 for col_id in nurse_column_ids)

    assert model["average_percentage"] == 100


def test_csv_export_shows_na_for_non_applicable_columns(monkeypatch):
    _setup_non_nurse_matrix(monkeypatch)

    response = asyncio.run(server.export_training_matrix(format="csv", user={"name": "Audit"}))
    csv_text = response.body.decode("utf-8")

    assert "Training % In Date" in csv_text
    assert "N/A" in csv_text
    assert "Average,100%" in csv_text
