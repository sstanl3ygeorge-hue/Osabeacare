import os
import sys
import asyncio

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from routes.worker_dashboard import _canonicalize_health_form_worker_status


class _FakeHealthDeclCollection:
    def __init__(self, declaration):
        self._declaration = declaration

    async def find_one(self, *args, **kwargs):
        return self._declaration


class _FakeDb:
    def __init__(self, declaration):
        self.health_declarations = _FakeHealthDeclCollection(declaration)


def _resolve_status(db, employee_id: str, form_id: str, status: str) -> str:
    return asyncio.run(
        _canonicalize_health_form_worker_status(db, employee_id, form_id, status)
    )


def test_health_form_submitted_stays_submitted_without_declaration():
    db = _FakeDb(None)
    status = _resolve_status(db, "emp-1", "staff_health_questionnaire", "submitted")
    assert status == "submitted"


def test_health_form_signed_off_without_declaration_downgrades_to_submitted():
    db = _FakeDb(None)
    status = _resolve_status(db, "emp-1", "staff_health_questionnaire", "signed_off")
    assert status == "submitted"


def test_health_form_reviewed_with_fit_outcome_maps_to_verified():
    db = _FakeDb({"status": "fit"})
    status = _resolve_status(db, "emp-1", "staff_health_questionnaire", "reviewed")
    assert status == "verified"


def test_health_form_approved_with_conditional_outcome_maps_to_verified():
    db = _FakeDb({"status": "conditional"})
    status = _resolve_status(db, "emp-1", "staff_health_questionnaire", "approved")
    assert status == "verified"


def test_health_form_signed_off_with_not_fit_downgrades_to_submitted():
    db = _FakeDb({"status": "not_fit"})
    status = _resolve_status(db, "emp-1", "staff_health_questionnaire", "signed_off")
    assert status == "submitted"


def test_health_form_signed_off_with_requires_review_downgrades_to_submitted():
    db = _FakeDb({"status": "requires_review"})
    status = _resolve_status(db, "emp-1", "staff_health_questionnaire", "signed_off")
    assert status == "submitted"


def test_non_health_form_status_unchanged():
    db = _FakeDb(None)
    status = _resolve_status(db, "emp-1", "staff_personal_info", "signed_off")
    assert status == "signed_off"
