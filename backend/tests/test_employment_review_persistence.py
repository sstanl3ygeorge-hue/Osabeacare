import asyncio
import copy
import sys
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from employment_review_persistence import sign_off_current_employment_review, upsert_employment_review  # noqa: E402


TODAY = date.today()


def years_ago(years: int, month: int = 1) -> str:
    return f"{TODAY.year - years}-{month:02d}"


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args, **_kwargs):
        self.rows = sorted(self.rows, key=lambda row: row.get("gap_start") or "")
        return self

    async def to_list(self, _limit):
        return copy.deepcopy(self.rows)


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.update_calls = []

    async def find_one(self, query, projection=None):
        for row in self.rows:
            if self._matches(row, query):
                return copy.deepcopy(self._project(row, projection))
        return None

    def find(self, query, projection=None):
        rows = [
            self._project(row, projection)
            for row in self.rows
            if self._matches(row, query)
        ]
        return FakeCursor(rows)

    async def update_one(self, query, update, upsert=False):
        self.update_calls.append((copy.deepcopy(query), copy.deepcopy(update), upsert))
        for index, row in enumerate(self.rows):
            if self._matches(row, query):
                updated = copy.deepcopy(row)
                updated.update(copy.deepcopy(update.get("$set", {})))
                self.rows[index] = updated
                return
        if upsert:
            inserted = copy.deepcopy(query)
            inserted.update(copy.deepcopy(update.get("$setOnInsert", {})))
            inserted.update(copy.deepcopy(update.get("$set", {})))
            self.rows.append(inserted)

    def _matches(self, row, query):
        return all(row.get(key) == value for key, value in query.items())

    def _project(self, row, projection):
        if not projection:
            return row
        if projection.get("_id") == 0 and len(projection) == 1:
            return row
        projected = {}
        include_keys = [key for key, value in projection.items() if value and key != "_id"]
        if include_keys:
            for key in include_keys:
                if key in row:
                    projected[key] = row[key]
            return projected
        return {key: value for key, value in row.items() if key != "_id"}


class FakeDB:
    def __init__(self, employees=None, gaps=None, reviews=None):
        self.employees = FakeCollection(employees)
        self.employment_gaps = FakeCollection(gaps)
        self.employment_reviews = FakeCollection(reviews)


def run(coro):
    return asyncio.run(coro)


def continuous_employee(employee_id="emp_persist"):
    return {
        "id": employee_id,
        "employment_history": [
            {
                "employer_name": "Continuous Care Ltd",
                "job_title": "Support Worker",
                "start_date": years_ago(11),
                "end_date": None,
            }
        ],
    }


def gapped_history():
    return [
        {
            "employer_name": "First Care",
            "job_title": "HCA",
            "start_date": years_ago(11),
            "end_date": f"{TODAY.year - 3}-01",
        },
        {
            "employer_name": "Second Care",
            "job_title": "Support Worker",
            "start_date": f"{TODAY.year - 3}-04",
            "end_date": None,
        },
    ]


def test_create_current_review_for_employee_with_no_prior_review():
    db = FakeDB(employees=[continuous_employee()])

    review = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY, actor_id="admin_1"))

    assert review["employee_id"] == "emp_persist"
    assert review["version"] == 1
    assert review["current"] is True
    assert review["timeline_fingerprint"]
    assert len(db.employment_reviews.rows) == 1
    assert db.employment_reviews.rows[0]["employee_id"] == "emp_persist"


def test_rebuild_same_timeline_does_not_bump_version():
    db = FakeDB(employees=[continuous_employee()])

    first = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))
    second = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))

    assert first["version"] == 1
    assert second["version"] == 1
    assert first["timeline_fingerprint"] == second["timeline_fingerprint"]
    assert len(db.employment_reviews.rows) == 1


def test_rebuild_bumps_version_when_timeline_materially_changes():
    employee = continuous_employee()
    db = FakeDB(employees=[employee])

    first = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))
    db.employees.rows[0]["employment_history"][0]["job_title"] = "Senior Support Worker"
    second = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))

    assert first["version"] == 1
    assert second["version"] == 2
    assert first["timeline_fingerprint"] != second["timeline_fingerprint"]


def test_preserve_matched_verified_gap_decision():
    employee = {"id": "emp_gap", "employment_history": gapped_history()}
    gap = {
        "employee_id": "emp_gap",
        "gap_id": "gap_1",
        "gap_start": f"{TODAY.year - 3}-01",
        "gap_end": f"{TODAY.year - 3}-04",
        "status": "verified",
        "verified_by": "admin_1",
        "verified_at": "2026-04-19T10:00:00Z",
        "explanation": "Training course accepted.",
    }
    db = FakeDB(employees=[employee], gaps=[gap])

    review = run(upsert_employment_review(db, "emp_gap", as_of_date=TODAY))
    gap_segments = [segment for segment in review["segments"] if segment["type"] == "gap"]

    assert gap_segments[0]["status"] == "verified"
    assert gap_segments[0]["admin_review"]["reviewed_by"] == "admin_1"


def test_sign_off_invalidated_when_timeline_changes():
    employee = continuous_employee()
    db = FakeDB(employees=[employee])

    first = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))
    db.employment_reviews.rows[0]["sign_off"] = {
        "signed_off": True,
        "previous_signed_off": True,
        "version_signed": first["version"],
        "signed_off_by": "admin_1",
        "signed_off_at": "2026-04-19T10:00:00Z",
        "timeline_fingerprint": first["timeline_fingerprint"],
        "invalidated": False,
        "invalidated_reason": None,
    }
    db.employment_reviews.rows[0]["status"] = "fully_accounted"
    db.employees.rows[0]["employment_history"][0]["job_title"] = "Senior Support Worker"

    second = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))

    assert second["version"] == 2
    assert second["sign_off"]["signed_off"] is False
    assert second["sign_off"]["previous_signed_off"] is True
    assert second["sign_off"]["invalidated"] is True
    assert "timeline has changed" in second["sign_off"]["invalidated_reason"]


def test_preserve_current_sign_off_when_timeline_is_unchanged():
    db = FakeDB(employees=[continuous_employee()])

    first = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))
    db.employment_reviews.rows[0]["sign_off"] = {
        "signed_off": True,
        "previous_signed_off": True,
        "version_signed": first["version"],
        "signed_off_by": "admin_1",
        "signed_off_at": "2026-04-19T10:00:00Z",
        "timeline_fingerprint": first["timeline_fingerprint"],
        "invalidated": False,
        "invalidated_reason": None,
    }
    db.employment_reviews.rows[0]["status"] = "fully_accounted"

    second = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))

    assert second["version"] == 1
    assert second["status"] == "fully_accounted"
    assert second["sign_off"]["signed_off"] is True


def test_preserved_sign_off_invalidates_when_gap_status_reopens_without_timeline_change():
    employee = {"id": "emp_gap", "employment_history": gapped_history()}
    verified_gap = {
        "employee_id": "emp_gap",
        "gap_id": "gap_1",
        "gap_start": f"{TODAY.year - 3}-01",
        "gap_end": f"{TODAY.year - 3}-04",
        "status": "verified",
        "verified_by": "admin_1",
        "verified_at": "2026-04-19T10:00:00Z",
        "explanation": "Training course accepted.",
    }
    db = FakeDB(employees=[employee], gaps=[verified_gap])

    signed = run(sign_off_current_employment_review(db, "emp_gap", actor_id="admin_1"))
    db.employment_gaps.rows[0]["status"] = "reopened"
    db.employment_gaps.rows[0]["verified"] = False
    rebuilt = run(upsert_employment_review(db, "emp_gap", as_of_date=TODAY))

    assert rebuilt["version"] == signed["version"]
    assert rebuilt["sign_off"]["signed_off"] is False
    assert rebuilt["sign_off"]["invalidated"] is True
    assert "no longer meets sign-off eligibility" in rebuilt["sign_off"]["invalidated_reason"]


def test_preserve_unmatched_notes():
    employee = continuous_employee()
    employee["gap_explanations"] = [
        {
            "gap_start": years_ago(5),
            "gap_end": years_ago(4),
            "reason_type": "travel",
            "explanation": "Travelled abroad.",
        }
    ]
    db = FakeDB(employees=[employee])

    review = run(upsert_employment_review(db, "emp_persist", as_of_date=TODAY))

    assert len(review["unmatched_applicant_notes"]) == 1
    assert review["top_summary"]["unmatched_notes"] == 1


def test_sign_off_current_review_persists_versioned_decision():
    db = FakeDB(employees=[continuous_employee()])

    review = run(sign_off_current_employment_review(
        db,
        "emp_persist",
        actor_id="admin_1",
        actor_name="Admin One",
        notes="Reviewed and accepted.",
    ))

    assert review["status"] == "fully_accounted"
    assert review["sign_off"]["signed_off"] is True
    assert review["sign_off"]["version_signed"] == review["version"]
    assert review["sign_off"]["timeline_fingerprint"] == review["timeline_fingerprint"]
    assert db.employment_reviews.rows[0]["sign_off"]["signed_off"] is True


def test_sign_off_current_review_blocks_unverified_explained_gap():
    employee = {"id": "emp_gap", "employment_history": gapped_history()}
    gap = {
        "employee_id": "emp_gap",
        "gap_id": "gap_1",
        "gap_start": f"{TODAY.year - 3}-01",
        "gap_end": f"{TODAY.year - 3}-04",
        "status": "explained",
        "explanation": "Training course submitted.",
    }
    db = FakeDB(employees=[employee], gaps=[gap])

    try:
        run(sign_off_current_employment_review(db, "emp_gap", actor_id="admin_1"))
    except ValueError as exc:
        assert "require admin verification" in str(exc)
    else:
        raise AssertionError("Expected sign-off to fail for explained but unverified gap")
