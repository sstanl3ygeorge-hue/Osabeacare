"""
Compliance Management Routes Module

This module handles CQC compliance-related endpoints including:
- Organization policies management (CRUD, upload, review tracking)
- Insurance/certificates management (CRUD, upload, expiry tracking)
- Incident logs management (CRUD, audit trail)
- Compliance dashboard and reports
- CQC evidence mapping

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Response
from fastapi.responses import StreamingResponse
import io
from pydantic import BaseModel, ConfigDict

from .dependencies import (
    get_db,
    get_current_user,
    get_current_worker,
    require_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Compliance Management"])


async def _require_active_worker_employee(worker: dict, db) -> str:
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to worker account")
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "status": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.get("status") != "active":
        raise HTTPException(status_code=403, detail="Incident reporting is only available for active employees")
    return employee_id


# ==================== MODELS ====================

class OrgPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    category: str
    version: str
    status: str  # missing, active, expired, under_review, due_soon
    required: Optional[bool] = True
    conditional: Optional[bool] = False
    review_period_months: Optional[int] = 12
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    review_date: Optional[str] = None  # Next review due date
    last_reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_status: Optional[str] = None  # current, due_soon, overdue
    assigned_staff_count: Optional[int] = 0
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class InsuranceDocCreate(BaseModel):
    name: str
    insurance_type: str  # public_liability, employers_liability, fire_safety_certificate, etc.
    category: Optional[str] = "insurance"  # insurance, regulatory, safety
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    policy_number: Optional[str] = None
    provider: Optional[str] = None
    notes: Optional[str] = None
    required: Optional[bool] = True
    conditional: Optional[bool] = False
    renewal_period_months: Optional[int] = 12
    requires_expiry_date: Optional[bool] = True
    valid_until_replaced: Optional[bool] = False


class InsuranceDocResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    insurance_type: str
    category: Optional[str] = "insurance"
    required: Optional[bool] = True
    conditional: Optional[bool] = False
    renewal_period_months: Optional[int] = 12
    requires_expiry_date: Optional[bool] = True
    valid_until_replaced: Optional[bool] = False
    status: str  # valid, expiring_soon, expired, missing
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    policy_number: Optional[str] = None
    provider: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class IncidentLogCreate(BaseModel):
    incident_type: str  # incident, outbreak, near_miss, complaint
    title: str
    description: str
    date_occurred: str
    location: Optional[str] = None
    people_involved: Optional[str] = None
    persons_involved: Optional[str] = None
    witnesses: Optional[str] = None
    immediate_actions_taken: Optional[str] = None
    immediate_actions: Optional[str] = None
    injury_or_harm: Optional[str] = None
    safeguarding_concern: Optional[bool] = False
    escalation_required: Optional[bool] = False
    escalation_details: Optional[str] = None
    learning_outcome: Optional[str] = None
    prevention_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    related_shift_id: Optional[str] = None
    service_user_id: Optional[str] = None
    is_reportable: Optional[bool] = False
    report_category: Optional[str] = None
    reported_to_authority: Optional[bool] = False
    reported_at: Optional[str] = None
    report_reference: Optional[str] = None
    report_notes: Optional[str] = None


class IncidentLogUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    people_involved: Optional[str] = None
    witnesses: Optional[str] = None
    immediate_actions_taken: Optional[str] = None
    injury_or_harm: Optional[str] = None
    safeguarding_concern: Optional[bool] = None
    escalation_required: Optional[bool] = None
    escalation_details: Optional[str] = None
    learning_outcome: Optional[str] = None
    prevention_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    action_taken: Optional[str] = None
    is_reportable: Optional[bool] = None
    report_category: Optional[str] = None
    reported_to_authority: Optional[bool] = None
    reported_at: Optional[str] = None
    report_reference: Optional[str] = None
    report_notes: Optional[str] = None


class InsuranceDocUpdate(BaseModel):
    """Update model for insurance/certificates with audit trail"""
    name: Optional[str] = None
    expiry_date: Optional[str] = None
    policy_number: Optional[str] = None
    provider: Optional[str] = None
    issue_date: Optional[str] = None
    notes: Optional[str] = None
    reason: str  # Required for audit trail


class OrgPolicyAmend(BaseModel):
    """Amendment model for policies with audit trail"""
    name: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    review_date: Optional[str] = None
    notes: Optional[str] = None
    reason: str  # Required for audit trail


class IncidentLogAmend(BaseModel):
    """Amendment model for incidents with audit trail"""
    title: Optional[str] = None
    description: Optional[str] = None
    incident_type: Optional[str] = None
    status: Optional[str] = None
    action_taken: Optional[str] = None
    date_occurred: Optional[str] = None
    location: Optional[str] = None
    people_involved: Optional[str] = None
    persons_involved: Optional[str] = None
    witnesses: Optional[str] = None
    immediate_actions_taken: Optional[str] = None
    immediate_actions: Optional[str] = None
    injury_or_harm: Optional[str] = None
    safeguarding_concern: Optional[bool] = None
    escalation_required: Optional[bool] = None
    escalation_details: Optional[str] = None
    learning_outcome: Optional[str] = None
    prevention_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    is_reportable: Optional[bool] = None
    report_category: Optional[str] = None
    reported_to_authority: Optional[bool] = None
    reported_at: Optional[str] = None
    report_reference: Optional[str] = None
    report_notes: Optional[str] = None
    reason: str  # Required for audit trail


class IncidentLogResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    incident_type: str
    reference_number: str
    title: str
    description: str
    date_occurred: str
    location: Optional[str] = None
    people_involved: Optional[str] = None
    persons_involved: Optional[str] = None
    witnesses: Optional[str] = None
    immediate_actions_taken: Optional[str] = None
    immediate_actions: Optional[str] = None
    injury_or_harm: Optional[str] = None
    safeguarding_concern: Optional[bool] = False
    escalation_required: Optional[bool] = False
    escalation_details: Optional[str] = None
    learning_outcome: Optional[str] = None
    prevention_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    status: str  # open, investigating, resolved, closed
    reported_by: str
    reported_at: str
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    related_shift_id: Optional[str] = None
    service_user_id: Optional[str] = None
    reporter_type: Optional[str] = None
    submitted_by_employee_id: Optional[str] = None
    action_taken: Optional[str] = None
    follow_up_item_id: Optional[str] = None
    follow_up_due_date: Optional[str] = None
    follow_up_status: Optional[str] = None
    is_reportable: Optional[bool] = False
    report_category: Optional[str] = None
    reported_to_authority: Optional[bool] = False
    reported_at: Optional[str] = None
    report_reference: Optional[str] = None
    report_notes: Optional[str] = None
    notes: Optional[List[Dict[str, Any]]] = None
    created_at: str
    updated_at: str


class WorkerIncidentCreate(BaseModel):
    incident_type: str = "incident"
    occurred_at: str
    description: str
    location_text: str
    title: Optional[str] = None
    people_involved: Optional[str] = None
    witnesses: Optional[str] = None
    immediate_actions_taken: Optional[str] = None
    injury_or_harm: Optional[str] = None
    safeguarding_concern: Optional[bool] = False
    escalation_required: Optional[bool] = False
    escalation_details: Optional[str] = None
    learning_outcome: Optional[str] = None
    prevention_actions: Optional[str] = None
    related_shift_id: Optional[str] = None
    note: Optional[str] = None
    service_user_id: Optional[str] = None


class IncidentNoteCreate(BaseModel):
    note: str


def _normalize_and_validate_reportable_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize incident reportability fields and enforce minimal reportable completeness."""
    is_reportable = bool(payload.get("is_reportable"))
    reported_to_authority = bool(payload.get("reported_to_authority"))

    report_category = (payload.get("report_category") or "").strip()
    report_reference = (payload.get("report_reference") or "").strip()
    report_notes = (payload.get("report_notes") or "").strip()
    reported_at = payload.get("reported_at")

    if not is_reportable:
        payload["is_reportable"] = False
        payload["report_category"] = None
        payload["reported_to_authority"] = False
        payload["reported_at"] = None
        payload["report_reference"] = None
        payload["report_notes"] = None
        return payload

    if not report_category:
        raise HTTPException(status_code=400, detail="Report category is required when incident is reportable")
    if not report_notes:
        raise HTTPException(status_code=400, detail="Report notes are required when incident is reportable")
    if reported_to_authority and (not reported_at or not report_reference):
        raise HTTPException(
            status_code=400,
            detail="Reported date and reference are required when incident is marked reported to authority",
        )

    payload["is_reportable"] = True
    payload["report_category"] = report_category
    payload["reported_to_authority"] = reported_to_authority
    payload["reported_at"] = reported_at if reported_to_authority else None
    payload["report_reference"] = report_reference if reported_to_authority else None
    payload["report_notes"] = report_notes
    return payload


def _normalize_incident_alias_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep modern and legacy incident field names in sync."""
    alias_pairs = [
        ("people_involved", "persons_involved"),
        ("immediate_actions_taken", "immediate_actions"),
        ("learning_outcome", "lessons_learned"),
        ("prevention_actions", "corrective_actions"),
    ]
    for modern_field, legacy_field in alias_pairs:
        modern_value = payload.get(modern_field)
        legacy_value = payload.get(legacy_field)
        if modern_value in (None, "") and legacy_value not in (None, ""):
            payload[modern_field] = legacy_value
        elif legacy_value in (None, "") and modern_value not in (None, ""):
            payload[legacy_field] = modern_value
    return payload


def _normalize_incident_status(status: Optional[str]) -> Optional[str]:
    if not status:
        return status
    normalized = status.strip().lower()
    if normalized in {"under_review", "investigating"}:
        return "reviewing"
    return normalized


def _incident_followup_due_date(base_iso: str) -> str:
    """Return ad-hoc follow-up due date (base date + 7 days) as YYYY-MM-DD."""
    try:
        base_dt = datetime.fromisoformat(str(base_iso).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        base_dt = datetime.now(timezone.utc)
    return (base_dt + timedelta(days=7)).date().isoformat()


async def _sync_incident_report_followup(
    db,
    incident_doc: Dict[str, Any],
    acting_user_id: Optional[str],
    now_iso: str,
) -> Dict[str, Optional[str]]:
    """
    Keep one recurring_compliance report_followup row in sync with incident flags/status.
    """
    incident_id = str(incident_doc.get("id") or "").strip()
    recurring_collection = getattr(db, "recurring_compliance", None)
    if recurring_collection is None:
        return {
            "follow_up_item_id": None,
            "follow_up_due_date": None,
            "follow_up_status": None,
        }
    if not incident_id:
        return {
            "follow_up_item_id": None,
            "follow_up_due_date": None,
            "follow_up_status": None,
        }

    status_value = _normalize_incident_status(incident_doc.get("status")) or "open"
    should_close = status_value == "closed"
    requires_followup = bool(
        incident_doc.get("safeguarding_concern") or incident_doc.get("escalation_required")
    )

    existing = await recurring_collection.find_one(
        {"item_type": "report_followup", "linked_incident_id": incident_id},
        {"_id": 0},
    )

    if should_close:
        if existing:
            await recurring_collection.update_one(
                {"id": existing.get("id")},
                {
                    "$set": {
                        "is_active": False,
                        "status": "closed",
                        "closed_at": now_iso,
                        "closed_by": acting_user_id,
                        "updated_at": now_iso,
                    }
                },
            )
            return {
                "follow_up_item_id": existing.get("id"),
                "follow_up_due_date": existing.get("next_due_date"),
                "follow_up_status": "closed",
            }
        return {
            "follow_up_item_id": None,
            "follow_up_due_date": None,
            "follow_up_status": None,
        }

    if requires_followup:
        due_date = _incident_followup_due_date(now_iso)
        assigned_to = acting_user_id or incident_doc.get("reported_by")
        followup_name = f"Incident Follow-up: {incident_doc.get('reference_number') or incident_id}"
        followup_description = (
            "Follow-up required for safeguarding/escalation incident. "
            "Track closure actions and evidence."
        )

        if existing:
            await recurring_collection.update_one(
                {"id": existing.get("id")},
                {
                    "$set": {
                        "item_name": followup_name,
                        "description": followup_description,
                        "frequency": "ad_hoc",
                        "frequency_days": None,
                        "assigned_to": assigned_to,
                        "next_due_date": due_date,
                        "is_active": True,
                        "status": "open",
                        "updated_at": now_iso,
                    }
                },
            )
            return {
                "follow_up_item_id": existing.get("id"),
                "follow_up_due_date": due_date,
                "follow_up_status": "open",
            }

        followup_id = str(uuid.uuid4())
        employee_id = (
            str(incident_doc.get("submitted_by_employee_id") or "").strip()
            or str(incident_doc.get("reported_by") or "").strip()
            or f"incident-{incident_id}"
        )

        await recurring_collection.insert_one(
            {
                "id": followup_id,
                "employee_id": employee_id,
                "item_type": "report_followup",
                "item_name": followup_name,
                "description": followup_description,
                "frequency": "ad_hoc",
                "frequency_days": None,
                "next_due_date": due_date,
                "last_completed_date": None,
                "assigned_to": assigned_to,
                "escalate_to": None,
                "linked_report_id": None,
                "linked_incident_id": incident_id,
                "reminder_schedule": [14, 7, 0],
                "reminders_sent": [],
                "escalation_threshold_days": 7,
                "escalation_sent": False,
                "completion_history": [],
                "is_active": True,
                "status": "open",
                "created_at": now_iso,
                "created_by": acting_user_id,
                "updated_at": now_iso,
            }
        )
        return {
            "follow_up_item_id": followup_id,
            "follow_up_due_date": due_date,
            "follow_up_status": "open",
        }

    if existing:
        return {
            "follow_up_item_id": existing.get("id"),
            "follow_up_due_date": existing.get("next_due_date"),
            "follow_up_status": "open" if existing.get("is_active", True) else "closed",
        }

    return {
        "follow_up_item_id": None,
        "follow_up_due_date": None,
        "follow_up_status": None,
    }


class StaffMeetingCreate(BaseModel):
    meeting_date: str
    meeting_type: str
    employee_ids: List[str] = []
    agenda: str
    notes: str
    actions_required: Optional[str] = None
    next_meeting_date: Optional[str] = None


class StaffMeetingAmend(BaseModel):
    meeting_date: Optional[str] = None
    meeting_type: Optional[str] = None
    employee_ids: Optional[List[str]] = None
    agenda: Optional[str] = None
    notes: Optional[str] = None
    actions_required: Optional[str] = None
    next_meeting_date: Optional[str] = None
    actions_status: Optional[str] = None
    reason: str


class StaffMeetingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    meeting_date: str
    meeting_type: str
    employee_ids: List[str] = []
    agenda: str
    notes: str
    actions_required: Optional[str] = None
    next_meeting_date: Optional[str] = None
    actions_status: str  # open, closed
    actions_closed_at: Optional[str] = None
    actions_closed_by: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str


class EmployerAuditCreate(BaseModel):
    audit_type: str
    audit_date: str
    completed_by: str
    overall_outcome: str
    findings: str
    actions_required: Optional[str] = None
    next_review_date: Optional[str] = None
    status: Optional[str] = "open"
    # Client-file audit extensions
    service_user_id: Optional[str] = None
    checklist: Optional[Dict[str, Any]] = None


class EmployerAuditAmend(BaseModel):
    audit_type: Optional[str] = None
    audit_date: Optional[str] = None
    completed_by: Optional[str] = None
    overall_outcome: Optional[str] = None
    findings: Optional[str] = None
    actions_required: Optional[str] = None
    next_review_date: Optional[str] = None
    status: Optional[str] = None
    reason: str
    # Client-file audit extensions
    service_user_id: Optional[str] = None
    checklist: Optional[Dict[str, Any]] = None


class EmployerAuditResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    audit_type: str
    audit_date: str
    completed_by: str
    overall_outcome: str
    findings: str
    actions_required: Optional[str] = None
    next_review_date: Optional[str] = None
    status: str  # open, closed
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str
    # Client-file audit extensions
    service_user_id: Optional[str] = None
    checklist: Optional[Dict[str, Any]] = None


def _build_worker_incident_view(incident: Dict[str, Any]) -> Dict[str, Any]:
    status = _normalize_incident_status(incident.get("status")) or "open"
    status_label = {
        "open": "Submitted",
        "reviewing": "Under review",
        "under_review": "Under review",
        "investigating": "Under review",
        "resolved": "Resolved",
        "closed": "Closed",
    }.get(status, status.replace("_", " ").title())

    progress_summary = {
        "open": "Your report has been submitted and is awaiting review.",
        "reviewing": "Your report is being reviewed.",
        "under_review": "Your report is being reviewed.",
        "investigating": "Your report is being reviewed.",
        "resolved": "Review is complete and the case outcome has been recorded.",
        "closed": "Review is complete and the incident has been closed.",
    }.get(status, "Your report is being processed.")

    action_taken = incident.get("action_taken")
    outcome_summary = action_taken.strip() if isinstance(action_taken, str) and action_taken.strip() else None

    return {
        "id": incident.get("id"),
        "reference_number": incident.get("reference_number"),
        "incident_type": incident.get("incident_type"),
        "title": incident.get("title"),
        "description": incident.get("description"),
        "date_occurred": incident.get("date_occurred"),
        "location": incident.get("location"),
        "people_involved": incident.get("people_involved") or incident.get("persons_involved"),
        "witnesses": incident.get("witnesses"),
        "immediate_actions_taken": incident.get("immediate_actions_taken") or incident.get("immediate_actions"),
        "injury_or_harm": incident.get("injury_or_harm"),
        "safeguarding_concern": bool(incident.get("safeguarding_concern")),
        "escalation_required": bool(incident.get("escalation_required")),
        "escalation_details": incident.get("escalation_details"),
        "learning_outcome": incident.get("learning_outcome") or incident.get("lessons_learned"),
        "prevention_actions": incident.get("prevention_actions") or incident.get("corrective_actions"),
        "status": status,
        "status_label": status_label,
        "progress_summary": progress_summary,
        "outcome_summary": outcome_summary,
        "reported_at": incident.get("reported_at"),
        "reviewed_at": incident.get("reviewed_at"),
        "closed_at": incident.get("closed_at"),
        "updated_at": incident.get("updated_at"),
        "related_shift_id": incident.get("related_shift_id"),
        "service_user_id": incident.get("service_user_id"),
    }


# ==================== CONSTANTS ====================

CORE_POLICIES = [
    # Core Policies - Essential Safeguarding & Safety (ALL REQUIRED by CQC)
    {"name": "Safeguarding Adults Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Safeguarding Children Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Mental Capacity Act & DoLS Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Health & Safety Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Fire Safety Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "First Aid Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Equality, Diversity & Inclusion Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Whistleblowing Policy", "category": "Core", "required": True, "review_period_months": 12},
    
    # Clinical Policies - Care & Medical (REQUIRED for domiciliary care)
    {"name": "Medication Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Infection Prevention & Control Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Manual Handling Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "COSHH Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Care Planning Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "End of Life Care Policy", "category": "Clinical", "required": False, "conditional": True, "review_period_months": 24},
    {"name": "Nutrition & Hydration Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Pressure Ulcer Prevention Policy", "category": "Clinical", "required": False, "conditional": True, "review_period_months": 24},
    
    # Operational Policies - Day-to-Day Operations (REQUIRED)
    {"name": "Lone Working Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Risk Assessment Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Record Keeping Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Confidentiality Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Complaints Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Incident Reporting Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Business Continuity Policy", "category": "Operational", "required": True, "review_period_months": 24},
    {"name": "Service User Feedback Policy", "category": "Operational", "required": True, "review_period_months": 12},
    
    # Governance Policies - HR & Regulatory (REQUIRED)
    {"name": "Recruitment & Selection Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "DBS & Vetting Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Induction & Probation Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Training & Development Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Supervision & Appraisal Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Disciplinary & Grievance Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Data Protection & GDPR Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Code of Conduct", "category": "Governance", "required": True, "review_period_months": 12},
]


# ==================== POLICY ROUTES ====================

@router.post("/compliance/seed-policies")
async def seed_org_policies(user: dict = Depends(require_admin)):
    """Seed core organisation policies as placeholders with review tracking"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    
    for policy in CORE_POLICIES:
        existing = await db.org_policies.find_one({"name": policy["name"]})
        if not existing:
            policy_doc = {
                "id": str(uuid.uuid4()),
                "name": policy["name"],
                "category": policy["category"],
                "version": "v1.0",
                "status": "missing",
                "required": policy.get("required", True),
                "conditional": policy.get("conditional", False),
                "review_period_months": policy.get("review_period_months", 12),
                "file_url": None,
                "original_filename": None,
                "review_date": None,
                "last_reviewed_at": None,
                "reviewed_by": None,
                "assigned_staff_count": 0,
                "notes": None,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id']
            }
            await db.org_policies.insert_one(policy_doc)
            created += 1
    
    return {"message": f"Created {created} policy placeholders", "total": len(CORE_POLICIES)}


@router.get("/compliance/policies", response_model=List[OrgPolicyResponse])
async def get_org_policies(
    category: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all organisation policies with review status tracking"""
    db = get_db()
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    policies = await db.org_policies.find(query, {"_id": 0}).sort("category", 1).to_list(100)
    
    # Compute review status based on review date and last reviewed
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    
    # Get assignment counts per policy
    assignments_pipeline = [
        {"$match": {"status": {"$ne": "removed"}}},
        {"$group": {"_id": "$policy_id", "count": {"$sum": 1}}}
    ]
    assignment_counts = {}
    try:
        assignments = await db.policy_assignments.aggregate(assignments_pipeline).to_list(1000)
        for a in assignments:
            assignment_counts[a["_id"]] = a["count"]
    except Exception:
        pass
    
    for policy in policies:
        # Update assigned staff count
        policy["assigned_staff_count"] = assignment_counts.get(policy["id"], 0)
        
        # Determine review status
        if policy.get("review_date"):
            try:
                review_str = policy["review_date"]
                if isinstance(review_str, datetime):
                    review_date = review_str if review_str.tzinfo else review_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(review_str):
                    review_date = datetime.fromisoformat(review_str.replace('Z', '+00:00'))
                else:
                    review_date = datetime.fromisoformat(f"{review_str}T00:00:00+00:00")
                
                if review_date < now:
                    policy["review_status"] = "overdue"
                    if policy["status"] == "active":
                        policy["status"] = "expired"
                elif review_date < now + thirty_days:
                    policy["review_status"] = "due_soon"
                else:
                    policy["review_status"] = "current"
            except Exception:
                policy["review_status"] = None
        else:
            policy["review_status"] = None if policy["status"] == "missing" else "current"
    
    return policies


@router.get("/compliance/policies/{policy_id}", response_model=OrgPolicyResponse)
async def get_org_policy(policy_id: str, user: dict = Depends(get_current_user)):
    """Get a specific organisation policy"""
    db = get_db()
    policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/compliance/policies/{policy_id}/upload")
async def upload_org_policy_document(
    policy_id: str,
    file: UploadFile = File(...),
    review_months: int = Query(12, description="Months until next review"),
    user: dict = Depends(require_admin)
):
    """Upload a policy document file"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc)
    review_date = (now + timedelta(days=review_months * 30)).isoformat()
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="policies")
        file_url = result.get("url")
    
    update = {
        "file_url": file_url,
        "original_filename": file.filename,
        "status": "active",
        "review_date": review_date,
        "last_reviewed_at": now.isoformat(),
        "reviewed_by": user['user_id'],
        "updated_at": now.isoformat()
    }
    
    await db.org_policies.update_one({"id": policy_id}, {"$set": update})
    
    await log_audit_action(
        user['user_id'],
        "upload_policy",
        "org_policy",
        policy_id,
        {"filename": file.filename, "review_months": review_months}
    )
    
    return {"message": "Policy uploaded", "file_url": file_url, "review_date": review_date}


@router.put("/compliance/policies/{policy_id}", response_model=OrgPolicyResponse)
async def update_org_policy(
    policy_id: str,
    updates: OrgPolicyAmend,
    user: dict = Depends(require_admin)
):
    """Update policy metadata with audit trail"""
    db = get_db()
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Store amendment history
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "org_policy",
        "entity_id": policy_id,
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": updates.reason,
        "changes": {},
        "previous_values": {}
    }
    
    update_dict = {"updated_at": now}
    for field, value in updates.model_dump(exclude_none=True, exclude={'reason'}).items():
        if field in policy and policy[field] != value:
            amendment["changes"][field] = value
            amendment["previous_values"][field] = policy[field]
            update_dict[field] = value
    
    if amendment["changes"]:
        await db.amendments.insert_one(amendment)
        await db.org_policies.update_one({"id": policy_id}, {"$set": update_dict})
    
    updated = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    return updated


@router.get("/compliance/policies/{policy_id}/file")
async def get_policy_file_url(policy_id: str, user: dict = Depends(get_current_user)):
    """Stream policy file bytes inline for preview."""
    db = get_db()
    policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0, "file_url": 1, "original_filename": 1})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if not policy.get("file_url"):
        raise HTTPException(status_code=404, detail="No file uploaded for this policy")
    from server import retrieve_file_bytes
    file_bytes, content_type = await retrieve_file_bytes(policy.get("file_url"))
    filename = policy.get("original_filename") or f"policy_{policy_id}.pdf"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/compliance/policies/{policy_id}/download")
async def download_policy_file(policy_id: str, user: dict = Depends(get_current_user)):
    """Stream policy file bytes as attachment."""
    db = get_db()
    policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0, "file_url": 1, "original_filename": 1})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if not policy.get("file_url"):
        raise HTTPException(status_code=404, detail="No file uploaded for this policy")
    from server import retrieve_file_bytes
    file_bytes, content_type = await retrieve_file_bytes(policy.get("file_url"))
    filename = policy.get("original_filename") or f"policy_{policy_id}.pdf"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/compliance/policies/{policy_id}/replace")
async def replace_policy_document(
    policy_id: str,
    file: UploadFile = File(...),
    review_months: int = Query(12),
    reason: str = Query(..., description="Reason for replacement"),
    user: dict = Depends(require_admin)
):
    """Replace a policy document with audit trail"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc)
    
    # Store replacement in amendments
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "org_policy",
        "entity_id": policy_id,
        "amendment_type": "file_replacement",
        "amended_by": user['user_id'],
        "amended_at": now.isoformat(),
        "reason": reason,
        "previous_values": {
            "file_url": policy.get("file_url"),
            "original_filename": policy.get("original_filename")
        }
    }
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="policies")
        file_url = result.get("url")
    
    review_date = (now + timedelta(days=review_months * 30)).isoformat()
    
    amendment["new_values"] = {
        "file_url": file_url,
        "original_filename": file.filename
    }
    
    await db.amendments.insert_one(amendment)
    
    await db.org_policies.update_one(
        {"id": policy_id},
        {"$set": {
            "file_url": file_url,
            "original_filename": file.filename,
            "version": f"v{int(policy.get('version', 'v1.0').replace('v', '').split('.')[0]) + 1}.0",
            "review_date": review_date,
            "last_reviewed_at": now.isoformat(),
            "reviewed_by": user['user_id'],
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Policy replaced", "file_url": file_url}


@router.delete("/compliance/policies/{policy_id}/file")
async def delete_policy_file(
    policy_id: str,
    reason: str = Query(..., description="Reason for deletion"),
    user: dict = Depends(require_admin)
):
    """Delete a policy file with audit trail"""
    db = get_db()
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "org_policy",
        "entity_id": policy_id,
        "amendment_type": "file_deletion",
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": reason,
        "previous_values": {
            "file_url": policy.get("file_url"),
            "original_filename": policy.get("original_filename")
        }
    }
    
    await db.amendments.insert_one(amendment)
    
    await db.org_policies.update_one(
        {"id": policy_id},
        {"$set": {
            "file_url": None,
            "original_filename": None,
            "status": "missing",
            "updated_at": now
        }}
    )
    
    return {"message": "Policy file deleted"}


@router.put("/compliance/policies/{policy_id}/amend")
async def amend_policy(
    policy_id: str,
    amendment: OrgPolicyAmend,
    user: dict = Depends(require_admin)
):
    """Amend policy metadata with audit trail"""
    db = get_db()
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return await update_org_policy(policy_id, amendment, user)


@router.get("/compliance/policies/{policy_id}/history")
async def get_policy_history(policy_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for a policy"""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "org_policy", "entity_id": policy_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


# ==================== INSURANCE ROUTES ====================

@router.post("/compliance/seed-insurance")
async def seed_insurance_docs(user: dict = Depends(require_admin)):
    """Seed required insurance/certificate types"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    required_certs = [
        {"name": "Public Liability Insurance", "insurance_type": "public_liability", "category": "insurance", "required": True, "renewal_period_months": 12},
        {"name": "Employers Liability Insurance", "insurance_type": "employers_liability", "category": "insurance", "required": True, "renewal_period_months": 12},
        {"name": "Professional Indemnity Insurance", "insurance_type": "professional_indemnity", "category": "insurance", "required": False, "conditional": True, "renewal_period_months": 12},
        {"name": "CQC Registration Certificate", "insurance_type": "cqc_registration", "category": "regulatory", "required": True, "renewal_period_months": 0, "valid_until_replaced": True},
        {"name": "ICO Registration", "insurance_type": "ico_registration", "category": "regulatory", "required": True, "renewal_period_months": 12},
        {"name": "HSE Law Poster Display Check", "insurance_type": "hse_poster", "category": "regulatory", "required": True, "renewal_period_months": 0, "valid_until_replaced": True},
        {"name": "PAT Testing Certificate", "insurance_type": "pat_testing", "category": "safety", "required": True, "renewal_period_months": 12},
        {"name": "Fire Risk Assessment", "insurance_type": "fire_risk", "category": "safety", "required": True, "renewal_period_months": 12},
        {"name": "Fire Safety Certificate/Checks", "insurance_type": "fire_safety_certificate", "category": "safety", "required": True, "renewal_period_months": 12},
        {"name": "Gas Safety Certificate", "insurance_type": "gas_safety", "category": "safety", "required": False, "conditional": True, "renewal_period_months": 12},
        {"name": "Electrical Installation Certificate", "insurance_type": "electrical", "category": "safety", "required": False, "conditional": True, "renewal_period_months": 60},
        {"name": "Legionella Risk Assessment", "insurance_type": "legionella", "category": "safety", "required": False, "conditional": True, "renewal_period_months": 24},
        {"name": "Waste Contract", "insurance_type": "waste_contract", "category": "safety", "required": False, "conditional": True, "renewal_period_months": 12},
    ]
    
    created = 0
    for cert in required_certs:
        existing = await db.insurance_docs.find_one({"insurance_type": cert["insurance_type"]})
        if not existing:
            doc = {
                "id": str(uuid.uuid4()),
                "name": cert["name"],
                "insurance_type": cert["insurance_type"],
                "category": cert.get("category", "insurance"),
                "required": cert.get("required", True),
                "conditional": cert.get("conditional", False),
                "renewal_period_months": cert.get("renewal_period_months", 12),
                "requires_expiry_date": not cert.get("valid_until_replaced", False),
                "valid_until_replaced": cert.get("valid_until_replaced", False),
                "status": "missing",
                "file_url": None,
                "original_filename": None,
                "expiry_date": None,
                "issue_date": None,
                "policy_number": None,
                "provider": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id']
            }
            await db.insurance_docs.insert_one(doc)
            created += 1
    
    return {"message": f"Created {created} certificate placeholders", "total": len(required_certs)}


@router.post("/compliance/insurance", response_model=InsuranceDocResponse)
async def create_insurance_doc(
    payload: InsuranceDocCreate,
    user: dict = Depends(require_admin)
):
    """Create a provider-level certificate/check register record."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    insurance_type = (payload.insurance_type or "").strip().lower().replace(" ", "_")
    if not insurance_type:
        raise HTTPException(status_code=400, detail="insurance_type is required")

    existing = await db.insurance_docs.find_one({"insurance_type": insurance_type}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="Certificate/check type already exists. Amend the existing record instead.")

    valid_until_replaced = bool(payload.valid_until_replaced)
    requires_expiry_date = bool(payload.requires_expiry_date) if payload.requires_expiry_date is not None else (not valid_until_replaced)
    if valid_until_replaced:
        requires_expiry_date = False
    if requires_expiry_date and not payload.expiry_date:
        raise HTTPException(status_code=400, detail="expiry_date is required for this certificate/check type")

    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "insurance_type": insurance_type,
        "category": payload.category or "insurance",
        "required": payload.required if payload.required is not None else True,
        "conditional": payload.conditional if payload.conditional is not None else False,
        "renewal_period_months": payload.renewal_period_months if payload.renewal_period_months is not None else 12,
        "requires_expiry_date": requires_expiry_date,
        "valid_until_replaced": valid_until_replaced,
        "status": "missing",
        "file_url": None,
        "original_filename": None,
        "expiry_date": payload.expiry_date,
        "issue_date": payload.issue_date,
        "policy_number": payload.policy_number,
        "provider": payload.provider,
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
        "created_by": user['user_id']
    }

    await db.insurance_docs.insert_one(doc)
    await log_audit_action(
        user['user_id'],
        "create_insurance_register_record",
        "insurance_doc",
        doc["id"],
        {
            "insurance_type": insurance_type,
            "category": doc["category"],
            "required": doc["required"],
            "conditional": doc["conditional"],
        }
    )

    doc.pop("_id", None)
    return doc


@router.get("/compliance/insurance", response_model=List[InsuranceDocResponse])
async def get_insurance_docs(
    category: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Get all insurance/certificate documents with expiry tracking"""
    db = get_db()
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    docs = await db.insurance_docs.find(query, {"_id": 0}).sort("category", 1).to_list(100)
    
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    
    for doc in docs:
        # Calculate status based on expiry
        if doc.get("valid_until_replaced") and doc.get("file_url"):
            doc["status"] = "valid"
        elif doc.get("expiry_date"):
            try:
                expiry_str = doc["expiry_date"]
                if isinstance(expiry_str, datetime):
                    expiry_date = expiry_str if expiry_str.tzinfo else expiry_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(expiry_str):
                    expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    expiry_date = datetime.fromisoformat(f"{expiry_str}T00:00:00+00:00")
                
                if expiry_date < now:
                    doc["status"] = "expired"
                elif expiry_date < now + thirty_days:
                    doc["status"] = "expiring_soon"
                else:
                    doc["status"] = "valid"
            except Exception:
                doc["status"] = "missing" if not doc.get("file_url") else "valid"
        else:
            doc["status"] = "missing" if not doc.get("file_url") else "valid"
    
    return docs


@router.post("/compliance/insurance/{insurance_id}/upload")
async def upload_insurance_doc(
    insurance_id: str,
    file: UploadFile = File(...),
    expiry_date: Optional[str] = None,
    issue_date: Optional[str] = None,
    policy_number: Optional[str] = None,
    provider: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Upload an insurance/certificate document"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="insurance")
        file_url = result.get("url")
    
    update = {
        "file_url": file_url,
        "original_filename": file.filename,
        "status": "valid",
        "issue_date": issue_date or now,
        "updated_at": now
    }
    
    if expiry_date:
        update["expiry_date"] = expiry_date
    if policy_number:
        update["policy_number"] = policy_number
    if provider:
        update["provider"] = provider
    
    await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update})
    
    await log_audit_action(
        user['user_id'],
        "upload_insurance",
        "insurance_doc",
        insurance_id,
        {"filename": file.filename}
    )
    
    return {"message": "Document uploaded", "file_url": file_url}


@router.post("/compliance/insurance/{insurance_id}/replace")
async def replace_insurance_doc(
    insurance_id: str,
    file: UploadFile = File(...),
    expiry_date: Optional[str] = None,
    issue_date: Optional[str] = None,
    policy_number: Optional[str] = None,
    provider: Optional[str] = None,
    reason: str = Query(...),
    user: dict = Depends(require_admin)
):
    """Replace an insurance document with audit trail"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "insurance_doc",
        "entity_id": insurance_id,
        "amendment_type": "file_replacement",
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": reason,
        "previous_values": {
            "file_url": doc.get("file_url"),
            "original_filename": doc.get("original_filename"),
            "expiry_date": doc.get("expiry_date")
        }
    }
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="insurance")
        file_url = result.get("url")
    
    amendment["new_values"] = {
        "file_url": file_url,
        "original_filename": file.filename,
        "expiry_date": expiry_date,
        "issue_date": issue_date,
        "policy_number": policy_number,
        "provider": provider
    }
    
    await db.amendments.insert_one(amendment)
    
    update = {
        "file_url": file_url,
        "original_filename": file.filename,
        "status": "valid",
        "issue_date": issue_date or now,
        "updated_at": now
    }
    if expiry_date:
        update["expiry_date"] = expiry_date
    if policy_number is not None:
        update["policy_number"] = policy_number
    if provider is not None:
        update["provider"] = provider
    
    await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update})
    
    return {"message": "Document replaced", "file_url": file_url}


@router.delete("/compliance/insurance/{insurance_id}/file")
async def delete_insurance_file(
    insurance_id: str,
    reason: str = Query(...),
    user: dict = Depends(require_admin)
):
    """Delete an insurance file with audit trail"""
    db = get_db()
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "insurance_doc",
        "entity_id": insurance_id,
        "amendment_type": "file_deletion",
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": reason,
        "previous_values": {
            "file_url": doc.get("file_url"),
            "original_filename": doc.get("original_filename")
        }
    }
    
    await db.amendments.insert_one(amendment)
    
    await db.insurance_docs.update_one(
        {"id": insurance_id},
        {"$set": {
            "file_url": None,
            "original_filename": None,
            "status": "missing",
            "updated_at": now
        }}
    )
    
    return {"message": "Insurance file deleted"}


@router.put("/compliance/insurance/{insurance_id}/amend")
async def amend_insurance(
    insurance_id: str,
    amendment: InsuranceDocUpdate,
    user: dict = Depends(require_admin)
):
    """Amend insurance metadata with audit trail"""
    db = get_db()
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amend_record = {
        "id": str(uuid.uuid4()),
        "entity_type": "insurance_doc",
        "entity_id": insurance_id,
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": amendment.reason,
        "changes": {},
        "previous_values": {}
    }
    
    update_dict = {"updated_at": now}
    for field, value in amendment.model_dump(exclude_none=True, exclude={'reason'}).items():
        if field in doc and doc[field] != value:
            amend_record["changes"][field] = value
            amend_record["previous_values"][field] = doc[field]
            update_dict[field] = value
    
    if amend_record["changes"]:
        await db.amendments.insert_one(amend_record)
        await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update_dict})
    
    updated = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0})
    return updated


@router.get("/compliance/insurance/{insurance_id}/history")
async def get_insurance_history(insurance_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for an insurance document"""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "insurance_doc", "entity_id": insurance_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


@router.get("/compliance/insurance/{insurance_id}/file")
async def get_insurance_file_url(insurance_id: str, user: dict = Depends(require_admin)):
    """Stream insurance file bytes inline for preview."""
    db = get_db()
    doc = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0, "file_url": 1, "original_filename": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    if not doc.get("file_url"):
        raise HTTPException(status_code=404, detail="No file uploaded")
    from server import retrieve_file_bytes
    file_bytes, content_type = await retrieve_file_bytes(doc.get("file_url"))
    filename = doc.get("original_filename") or f"insurance_{insurance_id}.pdf"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/compliance/insurance/{insurance_id}/download")
async def download_insurance_file(insurance_id: str, user: dict = Depends(require_admin)):
    """Stream insurance file bytes as attachment."""
    db = get_db()
    doc = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0, "file_url": 1, "original_filename": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    if not doc.get("file_url"):
        raise HTTPException(status_code=404, detail="No file uploaded")
    from server import retrieve_file_bytes
    file_bytes, content_type = await retrieve_file_bytes(doc.get("file_url"))
    filename = doc.get("original_filename") or f"insurance_{insurance_id}.pdf"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==================== INCIDENT ROUTES ====================

@router.get("/compliance/incidents", response_model=List[IncidentLogResponse])
async def get_incidents(
    incident_type: Optional[str] = None,
    status: Optional[str] = None,
    service_user_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all incident logs"""
    db = get_db()
    query = {}
    if incident_type:
        query["incident_type"] = incident_type
    if status:
        query["status"] = status
    if service_user_id:
        query["service_user_id"] = service_user_id
    
    incidents = await db.incident_logs.find(query, {"_id": 0}).sort("date_occurred", -1).to_list(1000)
    return incidents


@router.post("/compliance/incidents", response_model=IncidentLogResponse)
async def create_incident(incident: IncidentLogCreate, user: dict = Depends(require_admin)):
    """Create a new incident log"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate reference number
    count = await db.incident_logs.count_documents({})
    ref_number = f"INC-{datetime.now().year}-{str(count + 1).zfill(4)}"
    
    if incident.related_shift_id:
        shift_exists = await db.shifts.find_one({"id": incident.related_shift_id}, {"_id": 0, "id": 1})
        if not shift_exists:
            raise HTTPException(status_code=400, detail="Related shift not found")

    incident_payload = _normalize_incident_alias_fields(incident.model_dump())
    incident_payload = _normalize_and_validate_reportable_fields(incident_payload)
    incident_payload["status"] = _normalize_incident_status(incident_payload.get("status")) or "open"

    doc = {
        "id": str(uuid.uuid4()),
        "reference_number": ref_number,
        **incident_payload,
        "status": incident_payload.get("status") or "open",
        "notes": [],
        "action_taken": None,
        "reporter_type": "admin",
        "submitted_by_employee_id": None,
        "reported_by": user['user_id'],
        "reported_at": now,
        "closed_at": None,
        "closed_by": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.incident_logs.insert_one(doc)

    follow_up_fields = await _sync_incident_report_followup(
        db=db,
        incident_doc=doc,
        acting_user_id=user.get("user_id"),
        now_iso=now,
    )
    if follow_up_fields:
        await db.incident_logs.update_one({"id": doc["id"]}, {"$set": follow_up_fields})
        doc.update(follow_up_fields)
    
    await log_audit_action(
        user['user_id'],
        "create_incident",
        "incident_log",
        doc["id"],
        {
            "reference": ref_number,
            "type": incident.incident_type,
            "is_reportable": doc.get("is_reportable"),
            "reported_to_authority": doc.get("reported_to_authority"),
        },
    )
    
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/compliance/incidents/{incident_id}", response_model=IncidentLogResponse)
async def update_incident(
    incident_id: str,
    updates: IncidentLogUpdate,
    user: dict = Depends(require_admin)
):
    """Update an incident log"""
    db = get_db()
    
    incident = await db.incident_logs.find_one({"id": incident_id})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    now = datetime.now(timezone.utc).isoformat()
    incoming_updates = updates.model_dump(exclude_none=True)
    if "status" in incoming_updates:
        incoming_updates["status"] = _normalize_incident_status(incoming_updates.get("status"))
    effective_payload = {**incident, **incoming_updates}
    _normalize_incident_alias_fields(effective_payload)
    _normalize_and_validate_reportable_fields(effective_payload)

    update_dict = {"updated_at": now}
    for field, value in incoming_updates.items():
        update_dict[field] = value

    alias_fields = {
        "people_involved", "persons_involved", "immediate_actions_taken", "immediate_actions",
        "learning_outcome", "lessons_learned", "prevention_actions", "corrective_actions",
    }
    if any(field in incoming_updates for field in alias_fields):
        for field in alias_fields:
            if field in effective_payload:
                update_dict[field] = effective_payload[field]

    for field in ("is_reportable", "report_category", "reported_to_authority", "reported_at", "report_reference", "report_notes"):
        if field in effective_payload:
            update_dict[field] = effective_payload[field]

    if updates.status in {"reviewing", "under_review", "investigating", "resolved", "closed"}:
        update_dict["reviewed_by"] = user.get("user_id")
        update_dict["reviewed_at"] = now

    if updates.status == "closed":
        update_dict["closed_at"] = now
        update_dict["closed_by"] = user['user_id']

    await db.incident_logs.update_one({"id": incident_id}, {"$set": update_dict})
    await log_audit_action(
        user['user_id'],
        "update_incident",
        "incident_log",
        incident_id,
        {"changes": {k: v for k, v in update_dict.items() if k != "updated_at"}},
    )
    
    updated = await db.incident_logs.find_one({"id": incident_id}, {"_id": 0})
    follow_up_fields = await _sync_incident_report_followup(
        db=db,
        incident_doc=updated,
        acting_user_id=user.get("user_id"),
        now_iso=now,
    )
    if follow_up_fields:
        await db.incident_logs.update_one({"id": incident_id}, {"$set": follow_up_fields})
        updated.update(follow_up_fields)
    return updated


@router.put("/compliance/incidents/{incident_id}/amend")
async def amend_incident(
    incident_id: str,
    amendment: IncidentLogAmend,
    user: dict = Depends(require_admin)
):
    """Amend incident with audit trail"""
    db = get_db()
    
    incident = await db.incident_logs.find_one({"id": incident_id})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    now = datetime.now(timezone.utc).isoformat()
    amendment_fields = amendment.model_dump(exclude_none=True, exclude={'reason'})
    if "status" in amendment_fields:
        amendment_fields["status"] = _normalize_incident_status(amendment_fields.get("status"))
    effective_payload = {**incident, **amendment_fields}
    _normalize_incident_alias_fields(effective_payload)
    _normalize_and_validate_reportable_fields(effective_payload)
    
    amend_record = {
        "id": str(uuid.uuid4()),
        "entity_type": "incident_log",
        "entity_id": incident_id,
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": amendment.reason,
        "changes": {},
        "previous_values": {}
    }
    
    update_dict = {"updated_at": now}
    reportability_fields = {"is_reportable", "report_category", "reported_to_authority", "reported_at", "report_reference", "report_notes"}
    alias_fields = {
        "people_involved", "persons_involved", "immediate_actions_taken", "immediate_actions",
        "learning_outcome", "lessons_learned", "prevention_actions", "corrective_actions",
    }
    for field, value in amendment_fields.items():
        if field in reportability_fields:
            value = effective_payload.get(field)
        if field in alias_fields:
            value = effective_payload.get(field)
        if field in incident and incident[field] != value:
            amend_record["changes"][field] = value
            amend_record["previous_values"][field] = incident[field]
            update_dict[field] = value

    if any(field in amendment_fields for field in alias_fields):
        for field in alias_fields:
            next_value = effective_payload.get(field)
            if incident.get(field) != next_value:
                amend_record["changes"][field] = next_value
                amend_record["previous_values"][field] = incident.get(field)
                update_dict[field] = next_value

    if any(field in amendment_fields for field in reportability_fields):
        for field in reportability_fields:
            next_value = effective_payload.get(field)
            if incident.get(field) != next_value:
                amend_record["changes"][field] = next_value
                amend_record["previous_values"][field] = incident.get(field)
                update_dict[field] = next_value

    amended_status = update_dict.get("status")
    if amended_status in {"reviewing", "under_review", "investigating", "resolved", "closed"}:
        if incident.get("reviewed_by") != user.get("user_id"):
            amend_record["changes"]["reviewed_by"] = user.get("user_id")
            amend_record["previous_values"]["reviewed_by"] = incident.get("reviewed_by")
        if incident.get("reviewed_at") != now:
            amend_record["changes"]["reviewed_at"] = now
            amend_record["previous_values"]["reviewed_at"] = incident.get("reviewed_at")
        update_dict["reviewed_by"] = user.get("user_id")
        update_dict["reviewed_at"] = now

    if amended_status == "closed":
        if incident.get("closed_at") != now:
            amend_record["changes"]["closed_at"] = now
            amend_record["previous_values"]["closed_at"] = incident.get("closed_at")
        if incident.get("closed_by") != user.get("user_id"):
            amend_record["changes"]["closed_by"] = user.get("user_id")
            amend_record["previous_values"]["closed_by"] = incident.get("closed_by")
        update_dict["closed_at"] = now
        update_dict["closed_by"] = user.get("user_id")
    
    if amend_record["changes"]:
        await db.amendments.insert_one(amend_record)
        await db.incident_logs.update_one({"id": incident_id}, {"$set": update_dict})
    
    updated = await db.incident_logs.find_one({"id": incident_id}, {"_id": 0})
    follow_up_fields = await _sync_incident_report_followup(
        db=db,
        incident_doc=updated,
        acting_user_id=user.get("user_id"),
        now_iso=now,
    )
    if follow_up_fields:
        await db.incident_logs.update_one({"id": incident_id}, {"$set": follow_up_fields})
        updated.update(follow_up_fields)
    return updated


@router.get("/compliance/incidents/{incident_id}/history")
async def get_incident_history(incident_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for an incident"""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "incident_log", "entity_id": incident_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


@router.post("/compliance/incidents/{incident_id}/notes")
async def add_incident_note(
    incident_id: str,
    payload: IncidentNoteCreate,
    user: dict = Depends(require_admin),
):
    db = get_db()
    incident = await db.incident_logs.find_one({"id": incident_id}, {"_id": 0})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not payload.note or not payload.note.strip():
        raise HTTPException(status_code=400, detail="Note is required")

    now = datetime.now(timezone.utc).isoformat()
    note_entry = {
        "id": str(uuid.uuid4()),
        "text": payload.note.strip(),
        "author_id": user.get("user_id"),
        "author_email": user.get("email"),
        "author_type": "admin",
        "created_at": now,
    }
    await db.incident_logs.update_one(
        {"id": incident_id},
        {
            "$push": {"notes": note_entry},
            "$set": {"updated_at": now}
        },
    )
    await log_audit_action(
        user['user_id'],
        "incident_note_added",
        "incident_log",
        incident_id,
        {"note_id": note_entry["id"]},
    )
    return {"success": True, "note": note_entry}


@router.post("/worker/incidents")
async def create_worker_incident(
    payload: WorkerIncidentCreate,
    worker: dict = Depends(get_current_worker),
):
    db = get_db()
    employee_id = await _require_active_worker_employee(worker, db)

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    linked_service_user_id = payload.service_user_id
    if payload.related_shift_id:
        assignment = await db.shift_assignments.find_one(
            {"shift_id": payload.related_shift_id, "employee_id": employee_id},
            {"_id": 0, "id": 1}
        )
        if not assignment:
            raise HTTPException(status_code=400, detail="Related shift is not assigned to this worker")
        shift_doc = await db.shifts.find_one(
            {"id": payload.related_shift_id},
            {"_id": 0, "service_user_id": 1}
        )
        if shift_doc and shift_doc.get("service_user_id"):
            linked_service_user_id = shift_doc.get("service_user_id")

    now = datetime.now(timezone.utc).isoformat()
    count = await db.incident_logs.count_documents({})
    ref_number = f"INC-{datetime.now().year}-{str(count + 1).zfill(4)}"

    note_items = []
    if payload.note and payload.note.strip():
        note_items.append({
            "id": str(uuid.uuid4()),
            "text": payload.note.strip(),
            "author_type": "worker",
            "author_id": employee_id,
            "created_at": now,
        })

    doc = {
        "id": str(uuid.uuid4()),
        "reference_number": ref_number,
        "incident_type": payload.incident_type,
        "title": payload.title or f"Worker incident report ({payload.incident_type})",
        "description": payload.description,
        "date_occurred": payload.occurred_at,
        "location": payload.location_text,
        "people_involved": payload.people_involved,
        "persons_involved": payload.people_involved,
        "witnesses": payload.witnesses,
        "immediate_actions_taken": payload.immediate_actions_taken,
        "immediate_actions": payload.immediate_actions_taken,
        "injury_or_harm": payload.injury_or_harm,
        "safeguarding_concern": bool(payload.safeguarding_concern or payload.incident_type == "safeguarding"),
        "escalation_required": bool(payload.escalation_required),
        "escalation_details": payload.escalation_details,
        "learning_outcome": payload.learning_outcome,
        "prevention_actions": payload.prevention_actions,
        "root_cause": None,
        "corrective_actions": payload.prevention_actions,
        "lessons_learned": payload.learning_outcome,
        "status": "open",
        "action_taken": None,
        "related_shift_id": payload.related_shift_id,
        "service_user_id": linked_service_user_id,
        "notes": note_items,
        "reporter_type": "worker",
        "submitted_by_employee_id": employee_id,
        "reported_by": employee_id,
        "reported_by_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "reported_at": now,
        "closed_at": None,
        "closed_by": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "is_reportable": False,
        "report_category": None,
        "reported_to_authority": False,
        "reported_at": None,
        "report_reference": None,
        "report_notes": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.incident_logs.insert_one(doc)
    await log_audit_action(
        employee_id,
        "worker_create_incident",
        "incident_log",
        doc["id"],
        {"reference": ref_number, "incident_type": payload.incident_type, "related_shift_id": payload.related_shift_id},
    )
    return {"success": True, "incident": _build_worker_incident_view(doc)}


@router.get("/worker/incidents")
async def list_worker_incidents(worker: dict = Depends(get_current_worker)):
    db = get_db()
    employee_id = await _require_active_worker_employee(worker, db)

    incidents = await db.incident_logs.find(
        {"submitted_by_employee_id": employee_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return {"incidents": [_build_worker_incident_view(incident) for incident in incidents], "total": len(incidents)}


# ==================== STAFF MEETING ROUTES ====================

@router.get("/compliance/staff-meetings", response_model=List[StaffMeetingResponse])
async def get_staff_meetings(user: dict = Depends(require_admin)):
    """Get staff meeting records (admin-only)."""
    db = get_db()
    meetings = await db.staff_meeting_records.find({"_id": 0}).sort("meeting_date", -1).to_list(1000)
    return meetings


@router.get("/compliance/staff-meetings/{meeting_id}", response_model=StaffMeetingResponse)
async def get_staff_meeting(meeting_id: str, user: dict = Depends(require_admin)):
    """Get a single staff meeting record (admin-only)."""
    db = get_db()
    meeting = await db.staff_meeting_records.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Staff meeting record not found")
    return meeting


@router.post("/compliance/staff-meetings", response_model=StaffMeetingResponse)
async def create_staff_meeting(payload: StaffMeetingCreate, user: dict = Depends(require_admin)):
    """Create a staff meeting record (admin-only)."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    employee_ids = [emp_id for emp_id in (payload.employee_ids or []) if emp_id]
    if employee_ids:
        existing = await db.employees.find({"id": {"$in": employee_ids}}, {"_id": 0, "id": 1}).to_list(len(employee_ids))
        existing_ids = {emp.get("id") for emp in existing}
        missing_ids = [emp_id for emp_id in employee_ids if emp_id not in existing_ids]
        if missing_ids:
            raise HTTPException(status_code=400, detail=f"Unknown employee_ids: {', '.join(missing_ids)}")

    doc = {
        "id": str(uuid.uuid4()),
        "meeting_date": payload.meeting_date,
        "meeting_type": payload.meeting_type,
        "employee_ids": employee_ids,
        "agenda": payload.agenda,
        "notes": payload.notes,
        "actions_required": payload.actions_required,
        "next_meeting_date": payload.next_meeting_date,
        "actions_status": "open",
        "actions_closed_at": None,
        "actions_closed_by": None,
        "created_by": user["user_id"],
        "created_at": now,
        "updated_at": now,
    }

    await db.staff_meeting_records.insert_one(doc)
    await log_audit_action(
        user["user_id"],
        "create_staff_meeting_record",
        "staff_meeting_record",
        doc["id"],
        {
            "meeting_type": payload.meeting_type,
            "meeting_date": payload.meeting_date,
            "attendee_count": len(employee_ids),
        },
    )
    return doc


@router.put("/compliance/staff-meetings/{meeting_id}/amend", response_model=StaffMeetingResponse)
async def amend_staff_meeting(
    meeting_id: str,
    amendment: StaffMeetingAmend,
    user: dict = Depends(require_admin),
):
    """Amend staff meeting metadata with audit trail."""
    db = get_db()

    meeting = await db.staff_meeting_records.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Staff meeting record not found")

    now = datetime.now(timezone.utc).isoformat()
    amend_record = {
        "id": str(uuid.uuid4()),
        "entity_type": "staff_meeting_record",
        "entity_id": meeting_id,
        "amended_by": user["user_id"],
        "amended_at": now,
        "reason": amendment.reason,
        "changes": {},
        "previous_values": {},
    }

    update_dict = {"updated_at": now}
    payload = amendment.model_dump(exclude_none=True, exclude={"reason"})

    if "employee_ids" in payload:
        employee_ids = [emp_id for emp_id in (payload.get("employee_ids") or []) if emp_id]
        if employee_ids:
            existing = await db.employees.find({"id": {"$in": employee_ids}}, {"_id": 0, "id": 1}).to_list(len(employee_ids))
            existing_ids = {emp.get("id") for emp in existing}
            missing_ids = [emp_id for emp_id in employee_ids if emp_id not in existing_ids]
            if missing_ids:
                raise HTTPException(status_code=400, detail=f"Unknown employee_ids: {', '.join(missing_ids)}")
        payload["employee_ids"] = employee_ids

    for field, value in payload.items():
        if field in meeting and meeting[field] != value:
            amend_record["changes"][field] = value
            amend_record["previous_values"][field] = meeting[field]
            update_dict[field] = value

    if payload.get("actions_status") == "closed" and meeting.get("actions_status") != "closed":
        update_dict["actions_closed_at"] = now
        update_dict["actions_closed_by"] = user["user_id"]
    elif payload.get("actions_status") == "open" and meeting.get("actions_status") == "closed":
        update_dict["actions_closed_at"] = None
        update_dict["actions_closed_by"] = None

    if amend_record["changes"]:
        await db.amendments.insert_one(amend_record)
        await db.staff_meeting_records.update_one({"id": meeting_id}, {"$set": update_dict})

    updated = await db.staff_meeting_records.find_one({"id": meeting_id}, {"_id": 0})
    return updated


@router.get("/compliance/staff-meetings/{meeting_id}/history")
async def get_staff_meeting_history(meeting_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for a staff meeting record."""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "staff_meeting_record", "entity_id": meeting_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


@router.get("/compliance/staff-meetings/{meeting_id}/download-pdf")
async def download_staff_meeting_pdf(meeting_id: str, user: dict = Depends(require_admin)):
    """Download a staff meeting record as inspection-ready PDF evidence (admin-only)."""
    db = get_db()

    meeting = await db.staff_meeting_records.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Staff meeting record not found")

    attendee_ids = [emp_id for emp_id in (meeting.get("employee_ids") or []) if emp_id]
    attendees = []
    if attendee_ids:
        attendee_docs = await db.employees.find(
            {"id": {"$in": attendee_ids}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "employee_code": 1}
        ).to_list(len(attendee_ids))
        by_id = {doc.get("id"): doc for doc in attendee_docs}
        for emp_id in attendee_ids:
            emp = by_id.get(emp_id)
            if not emp:
                attendees.append(f"{emp_id} (not found)")
                continue
            full_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            code = emp.get("employee_code")
            attendees.append(f"{full_name} ({code})" if code else full_name)

    from services.pdf_service import generate_staff_meeting_record_pdf

    pdf_bytes = generate_staff_meeting_record_pdf(
        meeting_data=meeting,
        attendee_names=attendees,
        admin_data={
            "downloaded_by": user.get("name") or user.get("email") or user.get("user_id"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    await log_audit_action(
        user["user_id"],
        "download_staff_meeting_pdf",
        "staff_meeting_record",
        meeting_id,
        {
            "meeting_type": meeting.get("meeting_type"),
            "meeting_date": meeting.get("meeting_date"),
            "attendee_count": len(attendee_ids),
        },
    )

    meeting_date = str(meeting.get("meeting_date") or "record").replace(":", "-").replace("/", "-")
    filename = f"staff_meeting_{meeting_date}_{meeting_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==================== EMPLOYER AUDIT/CHECKLIST ROUTES ====================

@router.get("/compliance/employer-audits", response_model=List[EmployerAuditResponse])
async def get_employer_audits(user: dict = Depends(require_admin)):
    """Get employer/provider audit checklist records (admin-only)."""
    db = get_db()
    audits = await db.employer_audit_register.find({"_id": 0}).sort("audit_date", -1).to_list(1000)
    return audits


@router.get("/compliance/employer-audits/{audit_id}", response_model=EmployerAuditResponse)
async def get_employer_audit(audit_id: str, user: dict = Depends(require_admin)):
    """Get a single employer/provider audit checklist record (admin-only)."""
    db = get_db()
    audit = await db.employer_audit_register.find_one({"id": audit_id}, {"_id": 0})
    if not audit:
        raise HTTPException(status_code=404, detail="Employer audit record not found")
    return audit


@router.post("/compliance/employer-audits", response_model=EmployerAuditResponse)
async def create_employer_audit(payload: EmployerAuditCreate, user: dict = Depends(require_admin)):
    """Create an employer/provider audit checklist register record (admin-only)."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    status = (payload.status or "open").strip().lower()
    if status not in {"open", "closed"}:
        raise HTTPException(status_code=400, detail="status must be 'open' or 'closed'")

    doc = {
        "id": str(uuid.uuid4()),
        "audit_type": payload.audit_type,
        "audit_date": payload.audit_date,
        "completed_by": payload.completed_by,
        "overall_outcome": payload.overall_outcome,
        "findings": payload.findings,
        "actions_required": payload.actions_required,
        "next_review_date": payload.next_review_date,
        "status": status,
        "closed_at": now if status == "closed" else None,
        "closed_by": user["user_id"] if status == "closed" else None,
        "service_user_id": payload.service_user_id,
        "checklist": payload.checklist,
        "created_by": user["user_id"],
        "created_at": now,
        "updated_at": now,
    }

    await db.employer_audit_register.insert_one(doc)
    await log_audit_action(
        user["user_id"],
        "create_employer_audit_record",
        "employer_audit_record",
        doc["id"],
        {
            "audit_type": payload.audit_type,
            "audit_date": payload.audit_date,
            "status": status,
        },
    )
    return doc


@router.put("/compliance/employer-audits/{audit_id}/amend", response_model=EmployerAuditResponse)
async def amend_employer_audit(
    audit_id: str,
    amendment: EmployerAuditAmend,
    user: dict = Depends(require_admin),
):
    """Amend employer/provider audit checklist metadata with audit trail."""
    db = get_db()
    audit = await db.employer_audit_register.find_one({"id": audit_id})
    if not audit:
        raise HTTPException(status_code=404, detail="Employer audit record not found")

    now = datetime.now(timezone.utc).isoformat()
    amend_record = {
        "id": str(uuid.uuid4()),
        "entity_type": "employer_audit_record",
        "entity_id": audit_id,
        "amended_by": user["user_id"],
        "amended_at": now,
        "reason": amendment.reason,
        "changes": {},
        "previous_values": {},
    }

    payload = amendment.model_dump(exclude_none=True, exclude={"reason"})
    if "status" in payload:
        status = str(payload.get("status") or "").strip().lower()
        if status not in {"open", "closed"}:
            raise HTTPException(status_code=400, detail="status must be 'open' or 'closed'")
        payload["status"] = status

    update_dict = {"updated_at": now}
    for field, value in payload.items():
        if field in audit and audit[field] != value:
            amend_record["changes"][field] = value
            amend_record["previous_values"][field] = audit[field]
            update_dict[field] = value

    if payload.get("status") == "closed" and audit.get("status") != "closed":
        update_dict["closed_at"] = now
        update_dict["closed_by"] = user["user_id"]
    elif payload.get("status") == "open" and audit.get("status") == "closed":
        update_dict["closed_at"] = None
        update_dict["closed_by"] = None

    if amend_record["changes"]:
        await db.amendments.insert_one(amend_record)
        await db.employer_audit_register.update_one({"id": audit_id}, {"$set": update_dict})

    updated = await db.employer_audit_register.find_one({"id": audit_id}, {"_id": 0})
    return updated


@router.get("/compliance/employer-audits/{audit_id}/history")
async def get_employer_audit_history(audit_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for an employer/provider audit checklist record."""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "employer_audit_record", "entity_id": audit_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


@router.get("/compliance/employer-audits/{audit_id}/download-pdf")
async def download_employer_audit_pdf(audit_id: str, user: dict = Depends(require_admin)):
    """Download an employer/provider audit checklist record as inspection-ready PDF evidence (admin-only)."""
    db = get_db()
    audit = await db.employer_audit_register.find_one({"id": audit_id}, {"_id": 0})
    if not audit:
        raise HTTPException(status_code=404, detail="Employer audit record not found")

    from services.pdf_service import generate_employer_audit_record_pdf

    pdf_bytes = generate_employer_audit_record_pdf(
        audit_data=audit,
        admin_data={
            "downloaded_by": user.get("name") or user.get("email") or user.get("user_id"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    await log_audit_action(
        user["user_id"],
        "download_employer_audit_pdf",
        "employer_audit_record",
        audit_id,
        {
            "audit_type": audit.get("audit_type"),
            "audit_date": audit.get("audit_date"),
            "status": audit.get("status"),
        },
    )

    audit_date = str(audit.get("audit_date") or "record").replace(":", "-").replace("/", "-")
    filename = f"employer_audit_{audit_date}_{audit_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==================== COMPLIANCE REPORTS ====================

@router.get("/compliance/reports/staff-dbs")
async def get_staff_dbs_report(user: dict = Depends(require_admin)):
    """Get DBS compliance report for all staff"""
    db = get_db()
    
    employees = await db.employees.find(
        {"status": {"$in": ["onboarding", "active"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1,
         "dbs_status": 1, "dbs_certificate_number": 1,
         "dbs_issue_date": 1, "dbs_expiry_date": 1,
         "dbs_update_service_registered": 1}
    ).to_list(1000)

    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)

    report = []
    for emp in employees:
        dbs_expiry = emp.get("dbs_expiry_date")
        dbs_status = emp.get("dbs_status", "missing")

        # Recompute status from expiry date if present
        if dbs_expiry:
            try:
                exp_str = str(dbs_expiry)
                if 'T' in exp_str:
                    exp_dt = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                else:
                    exp_dt = datetime.fromisoformat(f"{exp_str}T00:00:00+00:00")
                if exp_dt < now:
                    dbs_status = "expired"
                elif exp_dt < now + thirty_days:
                    dbs_status = "expiring_soon"
                else:
                    dbs_status = "valid"
            except Exception:
                pass

        report.append({
            "employee_id": emp.get("id"),
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "role": emp.get("role"),
            "dbs_status": dbs_status,
            "dbs_certificate_number": emp.get("dbs_certificate_number"),
            "dbs_issue_date": emp.get("dbs_issue_date"),
            "dbs_expiry": dbs_expiry,
            "dbs_update_service_registered": emp.get("dbs_update_service_registered"),
        })

    return {"report": report, "total": len(report)}


@router.get("/compliance/reports/training")
async def get_training_compliance_report(user: dict = Depends(require_admin)):
    """Get training compliance report"""
    db = get_db()
    
    # Get all employees
    employees = await db.employees.find(
        {"status": {"$in": ["onboarding", "active"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1}
    ).to_list(1000)
    
    # Get training records (exclude superseded/cancelled)
    training = await db.training_records.find(
        {
            "employee_id": {"$in": [e["id"] for e in employees]},
            "record_status": {"$nin": ["superseded", "cancelled", "failed"]}
        },
        {"_id": 0}
    ).to_list(10000)
    
    # Group by employee
    training_by_emp = {}
    for t in training:
        emp_id = t.get("employee_id")
        if emp_id not in training_by_emp:
            training_by_emp[emp_id] = []
        training_by_emp[emp_id].append(t)
    
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    
    report = []
    for emp in employees:
        records = training_by_emp.get(emp["id"], [])
        completed = [r for r in records if r.get("record_status") in ("completed", "verified", "approved")]
        pending = [r for r in records if r.get("record_status") in ("pending", "in_progress", "submitted")]
        
        expiring_soon = []
        for r in completed:
            exp = r.get("expiry_date")
            if exp:
                try:
                    exp_str = str(exp)
                    if 'T' in exp_str:
                        exp_dt = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                    else:
                        exp_dt = datetime.fromisoformat(f"{exp_str}T00:00:00+00:00")
                    if now <= exp_dt <= now + thirty_days:
                        expiring_soon.append(r.get("training_name") or r.get("module_name") or "Training")
                except Exception:
                    pass
        
        report.append({
            "employee_id": emp["id"],
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "role": emp.get("role"),
            "completed_count": len(completed),
            "pending_count": len(pending),
            "expiring_soon": expiring_soon,
            "training_records": records,
            "training_count": len(records),
        })
    
    return {"report": report, "total": len(report)}
