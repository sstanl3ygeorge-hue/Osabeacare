import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agreement_document_service import HandbookRenderError
import unified_compliance_engine as uce


class AsyncCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    async def to_list(self, length=None):
        if length is None:
            return list(self.docs)
        return list(self.docs)[:length]


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def find_one(self, query=None, projection=None):
        query = query or {}
        for doc in self.docs:
            matched = True
            for key, value in query.items():
                if isinstance(value, dict):
                    if "$in" in value and doc.get(key) not in value["$in"]:
                        matched = False
                        break
                    if "$nin" in value and doc.get(key) in value["$nin"]:
                        matched = False
                        break
                elif doc.get(key) != value:
                    matched = False
                    break
            if matched:
                return dict(doc)
        return None

    def find(self, query=None, projection=None):
        query = query or {}
        docs = []
        for doc in self.docs:
            if "employee_id" in query and doc.get("employee_id") != query["employee_id"]:
                continue
            docs.append(dict(doc))
        return AsyncCursor(docs)


class FakeDB:
    def __init__(self):
        employee_id = "emp-1"
        self.employees = FakeCollection([
            {
                "id": employee_id,
                "first_name": "Olumide",
                "last_name": "OBEMBE",
                "role": "healthcare_assistant",
                "status": "onboarding",
            }
        ])
        self.users = FakeCollection([])
        self.employee_documents = FakeCollection([
            {
                "id": "doc-rtw",
                "employee_id": employee_id,
                "requirement_id": "right_to_work",
                "status": "approved",
                "review_status": "approved",
                "verified": True,
                "verification_stamp": "copy_verified",
                "stamped_file_url": "https://example.com/rtw.pdf",
                "is_active": True,
            },
            {
                "id": "doc-dbs",
                "employee_id": employee_id,
                "requirement_id": "dbs",
                "status": "approved",
                "review_status": "approved",
                "verified": True,
                "verification_stamp": "copy_verified",
                "stamped_file_url": "https://example.com/dbs.pdf",
                "is_active": True,
            },
            {
                "id": "doc-identity",
                "employee_id": employee_id,
                "requirement_id": "identity",
                "status": "approved",
                "review_status": "approved",
                "verified": True,
                "verification_stamp": "copy_verified",
                "stamped_file_url": "https://example.com/identity.pdf",
                "is_active": True,
            },
            {
                "id": "doc-poa-1",
                "employee_id": employee_id,
                "requirement_id": "proof_of_address",
                "status": "approved",
                "review_status": "approved",
                "verified": True,
                "verification_stamp": "copy_verified",
                "stamped_file_url": "https://example.com/poa1.pdf",
                "is_active": True,
            },
            {
                "id": "doc-poa-2",
                "employee_id": employee_id,
                "requirement_id": "proof_of_address",
                "status": "approved",
                "review_status": "approved",
                "verified": True,
                "verification_stamp": "copy_verified",
                "stamped_file_url": "https://example.com/poa2.pdf",
                "is_active": True,
            },
        ])
        self.training_records = FakeCollection([])
        self.form_submissions = FakeCollection([
            {"employee_id": employee_id, "form_type": "interview_record", "status": "signed_off"},
            {"employee_id": employee_id, "form_type": "staff_health_questionnaire", "status": "signed_off"},
            {"employee_id": employee_id, "form_type": "staff_personal_info", "status": "signed_off"},
            {"employee_id": employee_id, "form_type": "hmrc_starter_checklist", "status": "signed_off"},
            {"employee_id": employee_id, "form_type": "emergency_contacts", "status": "signed_off"},
        ])
        self.induction_checklists = FakeCollection([])
        self.agreement_acknowledgements = FakeCollection([
            {
                "id": "agr_contract",
                "employee_id": employee_id,
                "agreement_type": "contract_acceptance",
                "contract_state": "awaiting_company_countersignature",
                "status": "awaiting_company_countersignature",
                "verification_status": "awaiting_company_countersignature",
                "worker_signed_contract_pdf_url": "https://example.com/worker-signed.pdf",
                "worker_signed_at": "2026-04-21T17:13:10+00:00",
            },
            {
                "id": "agr_handbook",
                "employee_id": employee_id,
                "agreement_type": "handbook_acknowledgement",
                "status": "rejected",
                "verification_status": "rejected",
                "rejection_reason": "incomplete",
            },
        ])
        self.references = FakeCollection([
            {
                "employee_id": employee_id,
                "ref1": {"verification": {"status": "verified"}},
                "ref2": {"verification": {"status": "verified"}},
            }
        ])
        self.dbs_checks = FakeCollection([])
        self.rtw_checks = FakeCollection([])
        self.verification_documents = FakeCollection([])
        self.agreement_submissions = FakeCollection([])
        self.employment_gaps = FakeCollection([])


def test_readiness_blockers_split_legal_vs_internal(monkeypatch):
    async def fake_training_status(employee_id, role):
        return {
            "items": [
                {"code": "safeguarding", "title": "Safeguarding", "status": "verified", "record_id": "tr1", "verified": True},
                {"code": "manual_handling", "title": "Manual Handling", "status": "verified", "record_id": "tr2", "verified": True},
                {"code": "infection_control", "title": "Infection Control", "status": "verified", "record_id": "tr3", "verified": True},
                {"code": "basic_life_support", "title": "Basic Life Support", "status": "verified", "record_id": "tr4", "verified": True},
                {"code": "fire_safety", "title": "Fire Safety", "status": "verified", "record_id": "tr5", "verified": True},
                {"code": "health_safety", "title": "Health & Safety", "status": "verified", "record_id": "tr6", "verified": True},
                {"code": "information_governance", "title": "Information Governance", "status": "verified", "record_id": "tr7", "verified": True},
                {"code": "prevent", "title": "Prevent", "status": "verified", "record_id": "tr8", "verified": True},
            ],
            "blockerCount": 0,
        }

    async def fake_induction_status(db, employee_id, induction_record=None):
        return {
            "total": 15,
            "completed": 15,
            "blocking": False,
            "items": [
                {"id": f"item-{i}", "num": i, "name": f"Item {i}", "completed": True, "synced_from_training": False, "training_sync": None}
                for i in range(1, 16)
            ],
        }

    async def fake_build_agreement_rendering(db, employee, agreement_type):
        if agreement_type == uce.HANDBOOK_AGREEMENT_TYPE:
            raise HandbookRenderError("required field(s) missing or unresolved: company_address")
        return {"pdf_bytes": b"", "template_version": "test"}

    monkeypatch.setattr("services.training_evaluator.evaluate_employee_training_status", fake_training_status)
    monkeypatch.setattr(uce, "get_employee_induction_status", fake_induction_status)
    monkeypatch.setattr(uce, "build_agreement_rendering", fake_build_agreement_rendering)

    result = asyncio.run(
        uce.get_unified_employee_status("emp-1", FakeDB(), user_role="admin", include_details=True)
    )

    assert result["progress"]["percentage"] == 94
    assert result["legal_blockers"] == []
    assert len(result["internal_blockers"]) == 2

    reasons = [b["reason"] for b in result["internal_blockers"]]
    assert "Employment Contract: Awaiting company countersignature" in reasons
    assert any("Employee Handbook: Acknowledgement rejected and PDF unavailable because required field(s) missing or unresolved: company_address" == r for r in reasons)

    for blocker in result["internal_blockers"]:
        assert blocker["blocker_class"] == "internal"
