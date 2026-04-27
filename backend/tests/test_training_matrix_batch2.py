import asyncio
import os
import sys
from types import SimpleNamespace

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

    async def find_one(self, query, *_args, **_kwargs):
        for row in self._rows:
            if row.get("id") == query.get("id"):
                return row
        return None


class _FakeDB:
    def __init__(self, *, employees, training_records, proposed_items, documents):
        self.employees = _FakeCollection(employees)
        self.training_records = _FakeCollection(training_records)
        self.proposed_training_items = _FakeCollection(proposed_items)
        self.employee_documents = _FakeCollection(documents)


def _run_matrix(monkeypatch, *, training_eval, training_records=None, proposed_items=None):
    fake_db = _FakeDB(
        employees=[{"id": "emp-1", "role": "care_worker", "first_name": "Test", "last_name": "Worker"}],
        training_records=training_records or [],
        proposed_items=proposed_items or [],
        documents=[],
    )
    monkeypatch.setattr(server, "db", fake_db)

    async def _fake_eval(_employee_id, _role):
        return training_eval

    monkeypatch.setattr(server, "evaluate_employee_training_status", _fake_eval)
    return asyncio.run(server.get_employee_training_matrix("emp-1", user={"role": "admin"}))


def test_dols_verified_without_mca_creates_dependency_warning(monkeypatch):
    payload = _run_matrix(
        monkeypatch,
        training_eval={
            "overall": "missing",
            "evaluatedAt": "2026-01-01T00:00:00+00:00",
            "items": [
                {"code": "deprivation_of_liberty_safeguards", "title": "DoLS", "status": "verified", "blocker": True, "is_currently_blocking": False},
                {"code": "mental_capacity_act", "title": "MCA", "status": "missing", "blocker": True, "is_currently_blocking": True},
            ],
        },
    )

    warnings = payload.get("dependency_warnings", [])
    assert len(warnings) == 1
    assert warnings[0]["code"] == "dols_requires_mca"
    assert payload["completion_summary"]["dependency_warning_total"] == 1
    assert any(b.get("status") == "dependency_warning" for b in payload["readiness_blockers"])


def test_mca_verified_without_dols_keeps_dols_missing_blocker(monkeypatch):
    payload = _run_matrix(
        monkeypatch,
        training_eval={
            "overall": "missing",
            "evaluatedAt": "2026-01-01T00:00:00+00:00",
            "items": [
                {"code": "mental_capacity_act", "title": "MCA", "status": "verified", "blocker": True, "is_currently_blocking": False},
                {"code": "deprivation_of_liberty_safeguards", "title": "DoLS", "status": "missing", "blocker": True, "is_currently_blocking": True},
            ],
        },
    )

    dols_item = next(i for i in payload["items"] if i["code"] == "deprivation_of_liberty_safeguards")
    assert dols_item["status"] == "missing"
    assert any(b.get("code") == "deprivation_of_liberty_safeguards" for b in payload["readiness_blockers"])


def test_mapped_proposed_item_is_pending_review_not_missing(monkeypatch):
    payload = _run_matrix(
        monkeypatch,
        training_eval={
            "overall": "missing",
            "evaluatedAt": "2026-01-01T00:00:00+00:00",
            "items": [
                {"code": "manual_handling", "title": "Manual Handling", "status": "missing", "blocker": True, "is_currently_blocking": True},
            ],
        },
        proposed_items=[
            {
                "id": "p1",
                "employee_id": "emp-1",
                "status": "proposed",
                "mapped_training_code": "manual_handling",
                "raw_course_title": "CSTF Moving and Handling",
            }
        ],
    )

    assert payload["items"][0]["status"] == "pending_review"
    assert payload["completion_summary"]["pending_review_total"] == 1
    assert payload["completion_summary"]["verified_total"] == 0


def test_verified_record_increases_verified_total(monkeypatch):
    payload = _run_matrix(
        monkeypatch,
        training_eval={
            "overall": "current",
            "evaluatedAt": "2026-01-01T00:00:00+00:00",
            "items": [
                {"code": "fire_safety", "title": "Fire Safety", "status": "verified", "blocker": True, "is_currently_blocking": False},
                {"code": "manual_handling", "title": "Manual Handling", "status": "missing", "blocker": True, "is_currently_blocking": True},
            ],
        },
        training_records=[
            {"id": "r1", "employee_id": "emp-1", "requirement_id": "fire_safety", "training_name": "Fire Safety", "verified": True, "completion_date": "2026-01-01", "record_status": "active"},
        ],
    )

    assert payload["completion_summary"]["verified_total"] == 1
    assert payload["completion_summary"]["required_total"] == len(payload["role_required_requirements"])
    assert payload["completion_summary"]["required_total"] == len(payload["items"])


def test_all_qualifications_excludes_raw_unmapped_proposed(monkeypatch):
    payload = _run_matrix(
        monkeypatch,
        training_eval={
            "overall": "missing",
            "evaluatedAt": "2026-01-01T00:00:00+00:00",
            "items": [
                {"code": "infection_control", "title": "Infection Control", "status": "missing", "blocker": True, "is_currently_blocking": True},
            ],
        },
        proposed_items=[
            {
                "id": "p-unmapped",
                "employee_id": "emp-1",
                "status": "proposed",
                "raw_course_title": "Some Unmapped Specialist Course",
            }
        ],
    )

    all_titles = {str(x.get("title", "")) for x in payload["all_qualifications"]}
    assert "Some Unmapped Specialist Course" not in all_titles
    assert len(payload["unmapped_items"]) == 1
    assert payload["unmapped_items"][0]["status"] == "unmapped"


def test_verified_health_safety_welfare_hydrates_mandatory_row(monkeypatch):
    payload = _run_matrix(
        monkeypatch,
        training_eval={
            "overall": "current",
            "evaluatedAt": "2026-01-01T00:00:00+00:00",
            "items": [
                {"code": "health_and_safety", "title": "CSTF Health, Safety and Welfare", "status": "verified", "blocker": True, "is_currently_blocking": False},
            ],
        },
        training_records=[
            {
                "id": "r-hsw",
                "employee_id": "emp-1",
                "requirement_id": "health_safety_welfare",
                "training_name": "CSTF Health, Safety and Welfare",
                "verified": True,
                "verified_by": "Verifier User",
                "verified_at": "2026-01-10T10:00:00+00:00",
                "source_document_id": "doc-1",
                "certificate_url": "https://example.com/cert.pdf",
                "completion_date": "2026-01-01",
                "expiry_date": "2027-01-01",
                "record_status": "active",
            },
        ],
    )

    req = payload["role_required_requirements"][0]
    assert req["canonical_code"] == "health_safety_welfare"
    assert req["status"] == "verified"
    assert req["verified"] is True
    assert req["completed_at"] == "2026-01-01"
    assert req["expires_at"] == "2027-01-01"
    assert req["source_document_id"] == "doc-1"
    assert req["verified_by"] == "Verifier User"


def test_optional_custom_qualification_appears_and_does_not_block(monkeypatch):
    payload = _run_matrix(
        monkeypatch,
        training_eval={
            "overall": "current",
            "evaluatedAt": "2026-01-01T00:00:00+00:00",
            "items": [
                {"code": "manual_handling", "title": "Manual Handling", "status": "verified", "blocker": True, "is_currently_blocking": False},
            ],
        },
        training_records=[
            {
                "id": "r-opt-1",
                "employee_id": "emp-1",
                "requirement_id": "additional_tissue_viability",
                "training_name": "Tissue Viability",
                "verified": True,
                "completion_date": "2026-02-01",
                "expiry_date": "2027-02-01",
                "source_document_id": "doc-opt-1",
                "record_status": "active",
            }
        ],
    )

    titles = {str(item.get("title")) for item in payload["all_qualifications"]}
    assert "Tissue Viability" in titles
    assert payload["completion_summary"]["missing_total"] == 0
    # Required blockers should not include optional custom rows.
    assert all(
        str(blocker.get("code", "")).startswith("additional_") is False
        for blocker in payload["readiness_blockers"]
    )


class _MutableCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def find_one(self, query, *_args, **_kwargs):
        for row in self.rows:
            if all(row.get(k) == v for k, v in query.items()):
                return dict(row)
        return None

    async def update_one(self, query, update, *_args, **_kwargs):
        for idx, row in enumerate(self.rows):
            if all(row.get(k) == v for k, v in query.items()):
                row = dict(row)
                row.update(update.get("$set", {}))
                self.rows[idx] = row
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)

    async def insert_one(self, row, *_args, **_kwargs):
        self.rows.append(dict(row))
        return SimpleNamespace(inserted_id=row.get("id"))

    def find(self, *_args, **_kwargs):
        return _FakeCursor(self.rows)


def test_unmapped_review_approval_creates_additional_training_record(monkeypatch):
    proposed = {
        "id": "prop-1",
        "employee_id": "emp-1",
        "status": "proposed",
        "raw_course_title": "Rare Specialist Course",
        "mapped_training_code": None,
        "mapped_training_title": None,
        "source_document_id": "doc-1",
        "completed_at": "2026-03-01",
        "expires_at": "2027-03-01",
    }

    fake_db = SimpleNamespace(
        proposed_training_items=_MutableCollection([proposed]),
        employee_documents=_MutableCollection([{"id": "doc-1", "file_url": "https://example.com/doc.pdf", "original_filename": "doc.pdf"}]),
        training_records=_MutableCollection([]),
    )
    monkeypatch.setattr(server, "db", fake_db)

    async def _fake_find_active(*_args, **_kwargs):
        return []

    def _fake_pick_best(_records):
        return None

    async def _fake_reconcile(*_args, **_kwargs):
        return {"superseded": 0}

    monkeypatch.setattr("governance.training_dedup.find_active_canonical_records", _fake_find_active)
    monkeypatch.setattr("governance.training_dedup.pick_best_training_record", _fake_pick_best)
    monkeypatch.setattr("governance.training_dedup.reconcile_active_training_records", _fake_reconcile)

    review_item = server.TrainingIntakeReviewItem(
        item_id="prop-1",
        approve=True,
        mapped_training_code=None,
        mapped_training_title=None,
        completed_at="2026-03-01",
        expires_at="2027-03-01",
        notes="approve custom optional",
    )
    result = asyncio.run(
        server.TrainingIntakeService.review_proposed_items(
            employee_id="emp-1",
            items=[review_item],
            reviewer_id="admin-1",
            reviewer_name="Admin One",
        )
    )

    assert result["approved"] == 1
    assert len(fake_db.training_records.rows) == 1
    created = fake_db.training_records.rows[0]
    assert created["requirement_id"].startswith("additional_")
    assert created["training_name"] == "Rare Specialist Course"
