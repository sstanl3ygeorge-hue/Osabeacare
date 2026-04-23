import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unified_compliance_engine import _dedupe_blockers


def test_health_questionnaire_blockers_collapse_to_single_concept():
    blockers = [
        {
            "id": "staff_health_questionnaire",
            "gate": "staff_health_questionnaire",
            "label": "Staff Health Questionnaire",
            "reason": "Staff Health Questionnaire: Awaiting verification",
            "severity": "pending",
            "category": "forms",
        },
        {
            "id": "health_questionnaire",
            "gate": "health_questionnaire",
            "label": "Staff Health Questionnaire",
            "reason": "Staff Health Questionnaire: Health declaration not reviewed",
            "severity": "pending",
            "category": "forms",
        },
    ]

    collapsed = _dedupe_blockers(blockers)
    assert len(collapsed) == 1
    assert collapsed[0]["label"] == "Staff Health Questionnaire"
    assert "Health declaration not reviewed" in collapsed[0]["reason"]


def test_non_health_blockers_remain_distinct_by_gate():
    blockers = [
        {
            "id": "contract",
            "gate": "contract_signed",
            "label": "Employment Contract",
            "reason": "Employment Contract: Awaiting worker signature",
            "severity": "critical",
            "category": "agreements",
        },
        {
            "id": "contract",
            "gate": "contract_countersignature",
            "label": "Employment Contract",
            "reason": "Employment Contract: Awaiting company countersignature",
            "severity": "pending",
            "category": "agreements",
        },
    ]

    collapsed = _dedupe_blockers(blockers)
    assert len(collapsed) == 2

