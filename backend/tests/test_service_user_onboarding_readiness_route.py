import os
import sys
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.service_users as service_users


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    async def to_list(self, length):
        return list(self._docs[:length])


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    @staticmethod
    def _matches(doc, query):
        query = query or {}
        for key, expected in query.items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, query=None, projection=None, sort=None):
        matches = [doc for doc in self.docs if self._matches(doc, query)]
        if sort:
            for field, direction in reversed(sort):
                reverse = direction == -1
                matches.sort(key=lambda item: item.get(field, ""), reverse=reverse)
        return dict(matches[0]) if matches else None

    def find(self, query=None, projection=None):
        matches = [dict(doc) for doc in self.docs if self._matches(doc, query)]
        return _FakeCursor(matches)


class _FakeDb:
    def __init__(self, service_users_docs=None, documents_docs=None, care_plan_docs=None):
        self.service_users = _FakeCollection(service_users_docs or [])
        self.service_user_documents = _FakeCollection(documents_docs or [])
        self.service_user_care_plans = _FakeCollection(care_plan_docs or [])


def _make_app(monkeypatch, db):
    monkeypatch.setattr(service_users, "get_db", lambda: db)

    app = FastAPI()
    app.include_router(service_users.router, prefix="/api")
    app.dependency_overrides[service_users.require_manager_or_admin] = lambda: {
        "user_id": "mgr-1",
        "role": "admin",
    }
    return TestClient(app)


def test_onboarding_readiness_ready(monkeypatch):
    now = datetime.now(timezone.utc)
    future_due = (now + timedelta(days=21)).isoformat()

    db = _FakeDb(
        service_users_docs=[
            {
                "id": "su-1",
                "full_name": "Service User One",
                "date_of_birth": "1950-01-01",
                "nhs_number": "1234567890",
                "address_line_1": "1 Street",
                "postcode": "AB1 2CD",
                "phone": "07000000000",
                "emergency_contact_name": "Relative",
                "emergency_contact_phone": "07111111111",
                "emergency_contact_relationship": "Daughter",
                "gp_name": "Dr One",
                "gp_surgery": "Surgery One",
                "gp_phone": "07222222222",
                "notes": "",
            }
        ],
        documents_docs=[
            {
                "id": "doc-consent",
                "service_user_id": "su-1",
                "section_id": "2_consent_contracts",
                "document_type": "consent_form",
                "title": "Consent form",
                "notes": "",
            },
            {
                "id": "doc-risk",
                "service_user_id": "su-1",
                "section_id": "5_risk_assessments",
                "document_type": "risk_assessment",
                "title": "Risk assessment",
                "notes": "",
            },
        ],
        care_plan_docs=[
            {
                "id": "cp-1",
                "service_user_id": "su-1",
                "status": "active",
                "next_review_due_at": future_due,
                "section_statuses": {
                    "Personal information / This is me": "complete",
                    "Consent and capacity": "complete",
                    "Mobility and falls": "complete",
                    "Nutrition and hydration": "complete",
                    "Medication": "complete",
                    "Personal care": "complete",
                    "Mental wellbeing": "complete",
                    "Health conditions": "complete",
                    "Risk assessments": "complete",
                    "Daily notes / monitoring link": "complete",
                    "Care plan review": "complete",
                },
            }
        ],
    )

    client = _make_app(monkeypatch, db)
    response = client.get("/api/service-users/su-1/onboarding-readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["overall_status"] == "ready"
    assert payload["counts"]["missing"] == 0

    rows = {row["key"]: row for row in payload["rows"]}
    assert rows["active_care_plan_exists"]["status"] == "ready"
    assert rows["care_plan_sections_complete"]["status"] == "ready"
    assert rows["review_date_not_overdue"]["status"] == "ready"


def test_onboarding_readiness_missing_when_no_active_plan(monkeypatch):
    db = _FakeDb(
        service_users_docs=[
            {
                "id": "su-2",
                "full_name": "Service User Two",
                "date_of_birth": None,
                "nhs_number": "",
                "address_line_1": "",
                "postcode": "",
                "phone": "",
                "emergency_contact_name": "",
                "emergency_contact_phone": "",
                "emergency_contact_relationship": "",
                "gp_name": "",
                "gp_surgery": "",
                "gp_phone": "",
                "notes": "PEEP required on admission",
            }
        ],
        documents_docs=[],
        care_plan_docs=[],
    )

    client = _make_app(monkeypatch, db)
    response = client.get("/api/service-users/su-2/onboarding-readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["overall_status"] == "missing"

    rows = {row["key"]: row for row in payload["rows"]}
    assert rows["active_care_plan_exists"]["status"] == "missing"
    assert rows["personal_details_complete"]["status"] == "missing"
    assert rows["peep_recorded_if_applicable"]["status"] == "missing"


def test_onboarding_readiness_review_due(monkeypatch):
    now = datetime.now(timezone.utc)
    overdue_due = (now - timedelta(days=1)).isoformat()

    db = _FakeDb(
        service_users_docs=[
            {
                "id": "su-3",
                "full_name": "Service User Three",
                "date_of_birth": "1955-01-01",
                "nhs_number": "123",
                "address_line_1": "1 Street",
                "postcode": "AB1",
                "phone": "0700",
                "emergency_contact_name": "Relative",
                "emergency_contact_phone": "0711",
                "emergency_contact_relationship": "Son",
                "gp_name": "Dr",
                "gp_surgery": "Surgery",
                "gp_phone": "0722",
                "notes": "",
            }
        ],
        documents_docs=[
            {
                "id": "doc-consent-2",
                "service_user_id": "su-3",
                "section_id": "2_consent_contracts",
                "document_type": "consent_form",
                "title": "Consent form",
                "notes": "",
            },
            {
                "id": "doc-risk-2",
                "service_user_id": "su-3",
                "section_id": "5_risk_assessments",
                "document_type": "risk_assessment",
                "title": "Risk assessment",
                "notes": "",
            },
        ],
        care_plan_docs=[
            {
                "id": "cp-3",
                "service_user_id": "su-3",
                "status": "active",
                "next_review_due_at": overdue_due,
                "section_statuses": {
                    "Personal information / This is me": "complete",
                    "Consent and capacity": "complete",
                    "Mobility and falls": "complete",
                    "Nutrition and hydration": "complete",
                    "Medication": "complete",
                    "Personal care": "complete",
                    "Mental wellbeing": "complete",
                    "Health conditions": "complete",
                    "Risk assessments": "complete",
                    "Daily notes / monitoring link": "complete",
                    "Care plan review": "complete",
                },
            }
        ],
    )

    client = _make_app(monkeypatch, db)
    response = client.get("/api/service-users/su-3/onboarding-readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["overall_status"] == "review_due"

    rows = {row["key"]: row for row in payload["rows"]}
    assert rows["review_date_not_overdue"]["status"] == "review_due"
