"""
Single source of truth for Onboarding Forms (Tier 1 fix #1).

Both the backend compliance engine (unified_compliance_engine.py) and the
worker dashboard (routes/worker_dashboard.py + server.py
WORKER_FORM_DEFINITIONS) used to define their own list of "required forms",
producing inconsistent counts (admin: 6/7, worker: 7/7, gate: 5/5).

This module is the canonical list. Every surface that shows or counts
onboarding forms MUST import from here.

Notes:
- `interview_record` and `pre_interview_questionnaire` are deliberately NOT
  in this list. They belong to the interview lifecycle, not the onboarding
  forms tracker. The interview has its own dedicated panel.
- `equal_opportunities` is optional (required=False). It still appears in
  the list (so workers can fill it) and counts as complete when filled, but
  does not block recruitment approval.
- `fit_proper_persons` is role-gated to managers/directors only.
"""

from typing import List, Optional


CANONICAL_ONBOARDING_FORMS: List[dict] = [
    {
        "id": "staff_health_questionnaire",
        "name": "Staff Health Questionnaire",
        "description": "Medical history and health declarations",
        "required": True,
        "sensitive": True,
        "source": "worker",
    },
    {
        "id": "staff_personal_info",
        "name": "Staff Personal Information",
        "description": "Contact details, NI number, bank details",
        "required": True,
        "sensitive": True,
        "source": "worker",
    },
    {
        "id": "hmrc_starter_checklist",
        "name": "HMRC Starter Checklist",
        "description": "Tax code and employment status",
        "required": True,
        "sensitive": True,
        "source": "worker",
    },
    {
        "id": "equal_opportunities",
        "name": "Equal Opportunities Monitoring",
        "description": "Equality & diversity monitoring (optional, non-blocking)",
        "required": False,
        "sensitive": True,
        "source": "worker",
    },
    {
        "id": "emergency_contacts",
        "name": "Emergency Contacts",
        "description": "Next of kin and emergency contact details",
        "required": True,
        "source": "worker",
    },
    {
        "id": "conflict_of_interest",
        "name": "Conflict of Interest Declaration",
        "description": "Secondary employment, relationships or financial interests (NHS standard)",
        "required": True,
        "sensitive": True,
        "source": "worker",
    },
    {
        "id": "fit_proper_persons",
        "name": "Fit and Proper Persons Declaration",
        "description": "CQC Regulation 5 — declaration for managers and directors confirming fitness to hold position",
        "required": True,
        "sensitive": True,
        "source": "worker",
        "role_aware": True,
        "roles_required": ["manager", "registered_manager", "director", "nursing_director"],
    },
]


# Items that are NEVER counted in the onboarding-forms tracker, regardless of
# how they are tagged elsewhere. Source-of-truth for both backend and frontend
# filters.
NON_ONBOARDING_FORM_KEYS = frozenset({
    "interview_record",
    "pre_interview_questionnaire",
    "recruitment_checklist",
    "induction",
    "application_form",
})


def get_applicable_onboarding_forms(employee_role: Optional[str] = None) -> List[dict]:
    """
    Return the canonical list filtered for a specific employee's role.
    role_aware items are included only if the role matches.
    """
    role = (employee_role or "").lower()
    out: List[dict] = []
    for form in CANONICAL_ONBOARDING_FORMS:
        if form.get("role_aware") and form.get("roles_required"):
            if not any(r in role for r in form["roles_required"]):
                continue
        out.append(form)
    return out


def get_required_onboarding_form_ids(employee_role: Optional[str] = None) -> List[str]:
    """IDs of forms that BLOCK recruitment approval (excludes optional ones)."""
    return [
        f["id"]
        for f in get_applicable_onboarding_forms(employee_role)
        if f.get("required") is True
    ]


def get_all_onboarding_form_ids(employee_role: Optional[str] = None) -> List[str]:
    """All applicable onboarding form IDs (required + optional)."""
    return [f["id"] for f in get_applicable_onboarding_forms(employee_role)]
