"""
Regression test: Expiring training must NOT inflate "% In Date" scores.

Critical for CQC audits — training expiring within 30-90 days should reduce
compliance percentages, not falsely increase them.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

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


def test_expiring_training_does_not_count_as_out_of_date(monkeypatch):
    """
    Expiring training (expires within 30 days) should NOT count as out_of_date.
    Expiring status will display as amber in UI without affecting percentages.
    Only actually expired (days < 0) counts as out_of_date.
    """
    now = datetime.now(timezone.utc)
    employee_id = "emp-test-expiring"
    
    # Create two training records: one verified + in_date, one expiring (but not yet expired)
    training_records = [
        {
            "id": "rec-safeguarding-good",
            "employee_id": employee_id,
            "requirement_id": "safeguarding",
            "training_name": "Safeguarding Adults",
            "verification_status": "verified",
            "verified": True,
            "completion_date": (now - timedelta(days=365)).isoformat(),
            "expiry_date": (now + timedelta(days=180)).isoformat(),  # 6 months away - SAFE
            "record_status": "active",
        },
        {
            "id": "rec-manual-handling-expiring",
            "employee_id": employee_id,
            "requirement_id": "manual_handling",
            "training_name": "Manual Handling",
            "verification_status": "verified",
            "verified": True,
            "completion_date": (now - timedelta(days=365)).isoformat(),
            "expiry_date": (now + timedelta(days=20)).isoformat(),  # 20 days away - EXPIRING
            "record_status": "active",
        },
    ]
    
    fake_db = _FakeDB(
        employees=[
            {
                "id": employee_id,
                "first_name": "Test",
                "last_name": "User",
                "role": "care_worker",
                "status": "active",
                "lifecycle": "Active Workforce",
                "start_date": "2020-01-01",
                "probation_end_date": "2020-04-01",
                "next_appraisal_date": "2026-01-01",
            }
        ],
        training_records=training_records,
        proposed_items=[],
    )
    monkeypatch.setattr(server, "db", fake_db)
    
    model = asyncio.run(server.build_training_matrix_read_model())
    
    # Find the column stats for these two trainings
    safeguarding_stats = model["column_stats"].get("safeguarding", {})
    manual_handling_stats = model["column_stats"].get("manual_handling", {})
    
    assert safeguarding_stats, "Safeguarding column not found"
    assert manual_handling_stats, "Manual handling column not found"
    
    # Safeguarding: verified + not expiring = should be in_date
    assert safeguarding_stats["in_date"] > 0, "Verified non-expiring training should count as in_date"
    assert safeguarding_stats["out_of_date"] == 0, "Verified non-expiring training should NOT count as out_of_date"
    
    # Manual handling: verified AND expiring = should NOT count as out_of_date
    # (expiring just shows amber in UI, doesn't affect percentage)
    assert manual_handling_stats["out_of_date"] == 0, \
        "Expiring training must NOT count as out_of_date (only actually expired does)"
    assert manual_handling_stats["in_date"] == 0, \
        "Expiring training also shouldn't be counted as in_date (it's pending)"
    
    # Manual handling percentage should be 0% because expiring doesn't count as in_date
    manual_handling_pct = model["column_percentages"].get("manual_handling", -1)
    assert manual_handling_pct == 0, \
        f"Expiring training should give 0% in_date percentage, got {manual_handling_pct}%"


def test_expired_training_also_counts_as_out_of_date(monkeypatch):
    """
    Expired training (expiry date in past) must also count as out_of_date.
    """
    now = datetime.now(timezone.utc)
    employee_id = "emp-test-expired"
    
    training_records = [
        {
            "id": "rec-infection-control-expired",
            "employee_id": employee_id,
            "requirement_id": "infection_control",
            "training_name": "Infection Control",
            "verification_status": "verified",
            "verified": True,
            "completion_date": (now - timedelta(days=730)).isoformat(),
            "expiry_date": (now - timedelta(days=30)).isoformat(),  # 30 days PAST due
            "record_status": "active",
        },
    ]
    
    fake_db = _FakeDB(
        employees=[
            {
                "id": employee_id,
                "first_name": "Test",
                "last_name": "User",
                "role": "care_worker",
                "status": "active",
                "lifecycle": "Active Workforce",
                "start_date": "2020-01-01",
                "probation_end_date": "2020-04-01",
                "next_appraisal_date": "2026-01-01",
            }
        ],
        training_records=training_records,
        proposed_items=[],
    )
    monkeypatch.setattr(server, "db", fake_db)
    
    model = asyncio.run(server.build_training_matrix_read_model())
    
    infection_control_stats = model["column_stats"].get("infection_control", {})
    assert infection_control_stats, "Infection control column not found"
    
    # Expired training should be counted as out_of_date
    assert infection_control_stats["out_of_date"] > 0, "Expired training should count as out_of_date"
    assert infection_control_stats["in_date"] == 0, "Expired training must NOT count as in_date"
    
    # Percentage should be 0% for a column with only expired training
    infection_control_pct = model["column_percentages"].get("infection_control", -1)
    assert infection_control_pct == 0, f"Expired training should give 0% in_date, got {infection_control_pct}%"
