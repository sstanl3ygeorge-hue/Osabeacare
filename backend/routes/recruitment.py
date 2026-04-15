"""
Recruitment Pipeline Routes Module

This module handles recruitment-related endpoints including:
- Applicant listing and pipeline view
- Staff employee listing
- Recruitment approval and revocation
- DBS register
- Onboarding status management

Extracted from server.py for modularity.
"""

import os
import uuid
import logging
import jwt
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    UserRole,
    log_audit_action,
    JWT_SECRET,
    SENDER_EMAIL,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recruitment Pipeline"])


# ==================== CONSTANTS ====================
# These mirror the values in server.py for consistency

class EmployeeStatus:
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW = "interview"
    COMPLIANCE_REVIEW = "compliance_review"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PersonStage:
    APPLICANT = "applicant"
    EMPLOYEE = "employee"
    ARCHIVED = "archived"


APPLICANT_STATUSES = [
    EmployeeStatus.NEW,
    EmployeeStatus.SCREENING,
    EmployeeStatus.INTERVIEW,
    EmployeeStatus.COMPLIANCE_REVIEW
]

EMPLOYEE_STATUSES = [
    EmployeeStatus.ONBOARDING,
    EmployeeStatus.ACTIVE,
    EmployeeStatus.INACTIVE
]


class OnboardingStatus:
    NEW = "new"
    DOCUMENTS_PENDING = "documents_pending"
    UNDER_REVIEW = "under_review"
    READY_FOR_PLACEMENT = "ready_for_placement"
    ACTIVE = "active"
    ARCHIVED = "archived"


# ==================== MODELS ====================

class RecruitmentApprovalRequest(BaseModel):
    notes: Optional[str] = None


class EmploymentReviewSignOffRequest(BaseModel):
    notes: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

async def generate_employee_code() -> str:
    """Generate unique employee code in format EMP-XXXX"""
    db = get_db()
    
    # Find the highest existing code
    last_emp = await db.employees.find_one(
        {"employee_code": {"$regex": "^EMP-\\d+$"}},
        sort=[("employee_code", -1)]
    )
    
    if last_emp and last_emp.get("employee_code"):
        try:
            last_num = int(last_emp["employee_code"].split("-")[1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1001
    else:
        new_num = 1001
    
    return f"EMP-{new_num:04d}"


async def calculate_completion_percentage_simple(employee_id: str) -> int:
    """
    Simple completion percentage calculation.
    For full calculation with all requirements, the main server.py version is used.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return 0
    
    # Basic fields completion
    fields = ["first_name", "last_name", "email", "phone", "date_of_birth", "ni_number"]
    completed = sum(1 for f in fields if employee.get(f))
    
    # Document count
    doc_count = await db.employee_documents.count_documents({
        "employee_id": employee_id,
        "verified": True
    })
    
    # Training count
    training_count = await db.training_records.count_documents({
        "employee_id": employee_id,
        "verified": True
    })
    
    # Simple calculation
    total_weight = len(fields) + 10  # fields + docs + training
    completed_weight = completed + min(doc_count, 5) + min(training_count, 5)
    
    return min(100, int((completed_weight / total_weight) * 100))


# ==================== APPLICANT ENDPOINTS ====================

@router.get("/recruitment/applicants")
async def get_applicants(
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get applicant-stage people only.
    These are candidates who have NOT been recruited yet.
    
    Applicant statuses: new, screening, interview, compliance_review
    """
    db = get_db()
    
    query = {"status": {"$in": APPLICANT_STATUSES}}
    
    if status and status in APPLICANT_STATUSES:
        query["status"] = status
    
    if role:
        query["role"] = role
    
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"applicant_reference": {"$regex": search, "$options": "i"}}
        ]
    
    applicants = await db.employees.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with computed fields
    result = []
    for app in applicants:
        completion = await calculate_completion_percentage_simple(app['id'])
        result.append({
            "id": app["id"],
            "applicant_reference": app.get("applicant_reference"),
            "first_name": app["first_name"],
            "last_name": app["last_name"],
            "email": app["email"],
            "phone": app.get("phone"),
            "role": app.get("role"),
            "status": app["status"],
            "person_stage": PersonStage.APPLICANT,
            "recruitment_approved": app.get("recruitment_approved", False),
            "completion_percentage": completion,
            "created_at": app.get("created_at"),
            "updated_at": app.get("updated_at")
        })
    
    return result


@router.get("/recruitment/pipeline")
async def get_recruitment_pipeline(user: dict = Depends(get_current_user)):
    """
    Get recruitment pipeline summary with counts per status.
    Shows applicants grouped by their recruitment stage.
    """
    db = get_db()
    
    pipeline_counts = {}
    
    for status in APPLICANT_STATUSES:
        count = await db.employees.count_documents({"status": status})
        pipeline_counts[status] = count
    
    # Get all applicants for detailed view
    applicants = await db.employees.find(
        {"status": {"$in": APPLICANT_STATUSES}},
        {"_id": 0}
    ).to_list(1000)
    
    # Group by status
    grouped = {status: [] for status in APPLICANT_STATUSES}
    for app in applicants:
        status = app.get("status", EmployeeStatus.NEW)
        if status in grouped:
            grouped[status].append({
                "id": app["id"],
                "applicant_reference": app.get("applicant_reference"),
                "name": f"{app.get('first_name', '')} {app.get('last_name', '')}".strip(),
                "email": app.get("email"),
                "role": app.get("role"),
                "created_at": app.get("created_at"),
                "recruitment_approved": app.get("recruitment_approved", False)
            })
    
    return {
        "summary": {
            "total_applicants": sum(pipeline_counts.values()),
            "counts_by_status": pipeline_counts
        },
        "stages": [
            {"status": EmployeeStatus.NEW, "label": "New Applications", "applicants": grouped[EmployeeStatus.NEW]},
            {"status": EmployeeStatus.SCREENING, "label": "Screening", "applicants": grouped[EmployeeStatus.SCREENING]},
            {"status": EmployeeStatus.INTERVIEW, "label": "Interview", "applicants": grouped[EmployeeStatus.INTERVIEW]},
            {"status": EmployeeStatus.COMPLIANCE_REVIEW, "label": "Compliance Review", "applicants": grouped[EmployeeStatus.COMPLIANCE_REVIEW]}
        ]
    }


@router.get("/recruitment/applicants/{applicant_id}")
async def get_applicant(
    applicant_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific applicant by ID."""
    db = get_db()
    
    applicant = await db.employees.find_one(
        {"id": applicant_id, "status": {"$in": APPLICANT_STATUSES}},
        {"_id": 0}
    )
    
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")
    
    applicant["person_stage"] = PersonStage.APPLICANT
    applicant["completion_percentage"] = await calculate_completion_percentage_simple(applicant_id)
    
    return applicant


# ==================== STAFF EMPLOYEE ENDPOINTS ====================

@router.get("/staff/employees")
async def get_staff_employees(
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = False,
    user: dict = Depends(get_current_user)
):
    """
    Get employee-stage staff only.
    These are people who have been recruited and can/have worked.
    
    Employee statuses: onboarding, active, inactive
    
    By default, excludes inactive employees unless include_inactive=true.
    """
    db = get_db()
    
    if status and status in EMPLOYEE_STATUSES:
        query = {"status": status}
    elif include_inactive:
        query = {"status": {"$in": EMPLOYEE_STATUSES}}
    else:
        # Default: exclude inactive
        query = {"status": {"$in": [EmployeeStatus.ONBOARDING, EmployeeStatus.ACTIVE]}}
    
    if role:
        query["role"] = role
    
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"employee_code": {"$regex": search, "$options": "i"}}
        ]
    
    employees = await db.employees.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with basic computed fields
    for emp in employees:
        emp['person_stage'] = PersonStage.EMPLOYEE
        emp['completion_percentage'] = await calculate_completion_percentage_simple(emp['id'])
    
    return employees


@router.get("/onboarding-statuses")
async def get_onboarding_statuses(user: dict = Depends(get_current_user)):
    """Get list of available onboarding status options"""
    return [
        OnboardingStatus.NEW,
        OnboardingStatus.DOCUMENTS_PENDING,
        OnboardingStatus.UNDER_REVIEW,
        OnboardingStatus.READY_FOR_PLACEMENT,
        OnboardingStatus.ACTIVE,
        OnboardingStatus.ARCHIVED
    ]


# ==================== RECRUITMENT APPROVAL ====================

@router.post("/employees/{employee_id}/approve-recruitment")
async def approve_recruitment(
    employee_id: str,
    approval: RecruitmentApprovalRequest,
    user: dict = Depends(require_admin)
):
    """
    Approve an employee for recruitment/activation.
    
    This is a SEPARATE gate from compliance verification:
    - Compliance = operational readiness (documents, training, etc.)
    - Recruitment Approval = human decision that person should be hired
    
    EMPLOYEE CODE ASSIGNMENT:
    - If person doesn't have employee_code yet (was applicant), assign one now.
    
    STAGE TRANSITION:
    - On approval, status transitions from applicant-stage to onboarding (employee-stage)
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.get("recruitment_approved"):
        return {
            "status": "already_approved",
            "employee_code": employee.get("employee_code"),
            "recruitment_approved_at": employee.get("recruitment_approved_at"),
            "recruitment_approved_by": employee.get("recruitment_approved_by")
        }
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "recruitment_approved": True,
        "recruitment_approved_by": user['user_id'],
        "recruitment_approved_at": now,
        "recruitment_approval_notes": approval.notes,
        "updated_at": now
    }
    
    # Assign employee_code if not present (applicant → employee transition)
    employee_code = employee.get("employee_code")
    if not employee_code:
        employee_code = await generate_employee_code()
        update_data["employee_code"] = employee_code
        logger.info(f"Assigned employee_code {employee_code} on recruitment approval for {employee_id}")
    
    # STAGE TRANSITION: Move from applicant status to onboarding
    current_status = employee.get("status", EmployeeStatus.NEW)
    if current_status in APPLICANT_STATUSES:
        update_data["status"] = EmployeeStatus.ONBOARDING
        update_data["previous_status"] = current_status
        logger.info(f"Transitioned {employee_id} from {current_status} to onboarding on recruitment approval")
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": update_data}
    )
    
    await log_audit_action(
        user['user_id'],
        "recruitment_approved",
        "employee",
        employee_id,
        {
            "notes": approval.notes,
            "employee_code_assigned": employee_code if not employee.get("employee_code") else None,
            "status_changed_from": current_status if current_status in APPLICANT_STATUSES else None,
            "status_changed_to": EmployeeStatus.ONBOARDING if current_status in APPLICANT_STATUSES else None
        }
    )

    # ── Create worker account + send portal invite ────────────────────────────────
    # Fetch the refreshed employee (has employee_code and new status)
    updated_employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    invite_sent = False
    try:
        from server import create_worker_account_on_approval, send_welcome_email_with_magic_link
        await create_worker_account_on_approval(updated_employee)
        invite_sent = await send_welcome_email_with_magic_link(updated_employee, employee_code)
        invite_status = "sent" if invite_sent else "failed"
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "portal_invite_status": invite_status,
                "portal_invite_sent_at": now if invite_sent else None,
            }}
        )
        if not invite_sent:
            logger.warning(f"Portal invite not sent for {employee_id} — check RESEND_API_KEY and FRONTEND_URL env vars")
    except Exception as exc:
        logger.error(f"Failed to send portal invite for {employee_id}: {exc}")

    return {
        "status": "approved",
        "employee_id": employee_id,
        "employee_code": employee_code,
        "recruitment_approved": True,
        "recruitment_approved_by": user['user_id'],
        "recruitment_approved_at": now,
        "portal_invite_sent": invite_sent,
        "stage_transition": {
            "from": current_status if current_status in APPLICANT_STATUSES else None,
            "to": EmployeeStatus.ONBOARDING if current_status in APPLICANT_STATUSES else None
        }
    }


@router.post("/employees/{employee_id}/revoke-recruitment-approval")
async def revoke_recruitment_approval(
    employee_id: str,
    reason: str = Query(..., description="Reason for revoking approval"),
    user: dict = Depends(require_admin)
):
    """
    Revoke recruitment approval (SUPER_ADMIN only).
    This will prevent the employee from being activated.
    """
    db = get_db()
    
    if user.get('role') != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only Super Admin can revoke recruitment approval")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.get("recruitment_approved"):
        return {"status": "not_approved", "message": "Employee was not approved"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "recruitment_approved": False,
            "recruitment_approval_revoked_by": user['user_id'],
            "recruitment_approval_revoked_at": now,
            "recruitment_approval_revoked_reason": reason,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "recruitment_approval_revoked",
        "employee",
        employee_id,
        {"reason": reason, "previous_approved_by": employee.get("recruitment_approved_by")}
    )
    
    return {
        "status": "revoked",
        "employee_id": employee_id,
        "reason": reason
    }


@router.get("/employees/{employee_id}/recruitment-approval-status")
async def get_recruitment_approval_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get recruitment approval status for an employee"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {
        "employee_id": employee_id,
        "recruitment_approved": employee.get("recruitment_approved", False),
        "recruitment_approved_by": employee.get("recruitment_approved_by"),
        "recruitment_approved_at": employee.get("recruitment_approved_at"),
        "recruitment_approval_notes": employee.get("recruitment_approval_notes"),
        "can_be_activated": employee.get("recruitment_approved", False),
        "portal_invite_status": employee.get("portal_invite_status"),
        "portal_invite_sent_at": employee.get("portal_invite_sent_at"),
    }


# ==================== EMPLOYMENT REVIEW SIGN-OFF ====================

@router.post("/employees/{employee_id}/employment-review/sign-off")
async def sign_off_employment_review(
    employee_id: str,
    request: EmploymentReviewSignOffRequest = EmploymentReviewSignOffRequest(),
    user: dict = Depends(require_admin)
):
    """
    Admin sign-off on Employment Review.

    Stores a dated, attributed record on the employee document that the
    employment history and gap verification have been reviewed by this user.

    Guards:
    - Employment history must exist on the profile.
    - All recorded employment gaps must be resolved (no pending / needs_info /
      rejected / explained-awaiting-verification entries in employment_gaps).

    Written fields:
    - employment_review_signed_off      bool
    - employment_review_signed_off_by   user_id
    - employment_review_signed_off_at   ISO timestamp
    - employment_review_notes           str | null
    """
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # ── Guard 1: application record must exist ──────────────────────────────
    # Accept structured submission OR uploaded application PDF document —
    # same sources the UI uses for applicationAvailable.
    application_submission = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "$or": [
            {"requirement_id": "application_form"},
            {"form_type": "application_form"},
        ],
    }, {"_id": 0, "id": 1})
    application_pdf = await db.employee_documents.find_one({
        "employee_id": employee_id,
        "requirement_id": "application_form_pdf",
        "status": {"$nin": ["deleted", "superseded", "archived"]},
    }, {"_id": 0, "id": 1})
    if not application_submission and not application_pdf:
        raise HTTPException(
            status_code=400,
            detail="An application record must be on file before signing off Employment Review."
        )

    # ── Guard 2: declarations must be on file ────────────────────────────────
    # Declarations are on file once the declarations sub-object has been saved
    # (EditDeclarationsDialog always writes dbs_consent_given).
    declarations = employee.get("declarations") or {}
    if "dbs_consent_given" not in declarations:
        raise HTTPException(
            status_code=400,
            detail="Applicant declarations must be recorded before signing off Employment Review."
        )

    # ── Guard 3: employment history must exist ───────────────────────────────
    employment_history = employee.get("employment_history") or []
    if not employment_history:
        raise HTTPException(
            status_code=400,
            detail="Employment history is required before signing off Employment Review."
        )

    # ── Guard 4: all gaps must be resolved ───────────────────────────────────
    unresolved = await db.employment_gaps.find({
        "employee_id": employee_id,
        "status": {"$in": ["pending", "needs_more_info", "reopened", "rejected", "explained"]}
    }).to_list(10)

    if unresolved:
        raise HTTPException(
            status_code=400,
            detail=f"{len(unresolved)} employment gap(s) are not fully resolved. "
                   "Verify or resolve all gaps before signing off."
        )

    now = datetime.now(timezone.utc).isoformat()

    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "employment_review_signed_off": True,
            "employment_review_signed_off_by": user["user_id"],
            "employment_review_signed_off_at": now,
            "employment_review_notes": request.notes,
            "updated_at": now,
        }}
    )

    await log_audit_action(
        user["user_id"],
        "employment_review_signed_off",
        "employee",
        employee_id,
        {
            "signed_off_by": user["user_id"],
            "signed_off_at": now,
            "notes": request.notes,
            "employment_history_count": len(employment_history),
        }
    )

    return {
        "signed_off": True,
        "signed_off_by": user["user_id"],
        "signed_off_at": now,
        "notes": request.notes,
    }


# ==================== SEND PORTAL INVITE (ADMIN ACTION) ====================

@router.post("/employees/{employee_id}/send-portal-invite")
async def send_portal_invite(
    employee_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    (Re)send the worker portal access invite to an approved applicant.

    Idempotent: creates the worker account if it doesn’t exist yet,
    generates a fresh 7-day magic-link token, sends the welcome email,
    and records portal_invite_status / portal_invite_sent_at on the employee.
    """
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    email = employee.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Employee has no email address")

    employee_code = employee.get("employee_code") or employee_id[:8]
    now = datetime.now(timezone.utc).isoformat()

    # Ensure worker account exists
    existing_account = await db.worker_accounts.find_one({"employee_id": employee_id})
    if not existing_account:
        account_doc = {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "email": email.lower(),
            "password_hash": None,
            "has_password": False,
            "account_created_at": now,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "login_count": 0,
            "account_status": "active",
        }
        await db.worker_accounts.insert_one(account_doc)
        logger.info(f"Worker account created (send-portal-invite) for {employee_id}")

    # Generate fresh magic-link token (7 days)
    magic_token = jwt.encode(
        {
            "employee_id": employee_id,
            "email": email,
            "type": "worker_login",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    await db.magic_tokens.update_one(
        {"employee_id": employee_id, "email": email},
        {"$set": {
            "token": magic_token,
            "employee_id": employee_id,
            "email": email,
            "used": False,
            "created_at": now,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "purpose": "portal_invite",
        }},
        upsert=True,
    )

    frontend_url = os.environ.get("FRONTEND_URL", "https://app.osabeacares.co.uk")
    portal_link = f"{frontend_url}/worker/verify?token={magic_token}"

    # Compose email
    import resend as resend_module
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    org_settings = await db.org_settings.find_one({}, {"_id": 0})
    org_name = (org_settings or {}).get("organisation_name", "Osabea Healthcare Solutions")

    email_html = f"""
    <!DOCTYPE html><html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;">
    <div style="background:linear-gradient(135deg,#7c3aed,#a855f7);padding:32px;border-radius:12px 12px 0 0;text-align:center;">
        <h1 style="color:white;margin:0;">Your Worker Portal Access</h1>
    </div>
    <div style="background:#fff;padding:32px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;">
        <p style="font-size:16px;">Hi {emp_name},</p>
        <p>Your access to the <strong>{org_name}</strong> worker portal has been set up.</p>
        <p>Use the button below to log in and complete your onboarding:</p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{portal_link}" style="display:inline-block;background:#7c3aed;color:#fff;padding:16px 40px;
               border-radius:8px;text-decoration:none;font-weight:600;font-size:16px;">
                Access Your Portal
            </a>
        </div>
        <p style="color:#6b7280;font-size:13px;">This link is valid for 7 days. Employee code: <strong>{employee_code}</strong></p>
    </div>
    </body></html>
    """

    invite_sent = False
    try:
        if resend_module.api_key:
            await asyncio.to_thread(
                resend_module.Emails.send,
                {
                    "from": SENDER_EMAIL,
                    "to": [email],
                    "subject": f"Your {org_name} Worker Portal Access",
                    "html": email_html,
                },
            )
            invite_sent = True
        else:
            logger.warning("send-portal-invite: RESEND_API_KEY not set — email not sent")
    except Exception as exc:
        logger.error(f"send-portal-invite email failed for {employee_id}: {exc}")

    invite_status = "sent" if invite_sent else "failed"
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "portal_invite_status": invite_status,
            "portal_invite_sent_at": now if invite_sent else None,
        }}
    )

    await log_audit_action(
        user["user_id"],
        "send_portal_invite",
        "employee",
        employee_id,
        {"email": email, "invite_sent": invite_sent, "portal_link": portal_link},
    )

    return {
        "success": True,
        "invite_sent": invite_sent,
        "portal_link": portal_link,
        "employee_id": employee_id,
        "message": f"Invite {'sent to' if invite_sent else 'failed for'} {email}",
    }


@router.get("/employees/{employee_id}/recruitment-status")
async def get_recruitment_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get full recruitment status including stage and approval."""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    current_status = employee.get("status", EmployeeStatus.NEW)
    
    if current_status in APPLICANT_STATUSES:
        person_stage = PersonStage.APPLICANT
    elif current_status in EMPLOYEE_STATUSES:
        person_stage = PersonStage.EMPLOYEE
    else:
        person_stage = PersonStage.ARCHIVED
    
    return {
        "employee_id": employee_id,
        "status": current_status,
        "person_stage": person_stage,
        "is_applicant": current_status in APPLICANT_STATUSES,
        "is_employee": current_status in EMPLOYEE_STATUSES,
        "recruitment_approved": employee.get("recruitment_approved", False),
        "recruitment_approved_at": employee.get("recruitment_approved_at"),
        "employee_code": employee.get("employee_code")
    }


# ==================== RECRUITMENT STATISTICS ====================

@router.get("/recruitment/statistics")
async def get_recruitment_statistics(user: dict = Depends(get_current_user)):
    """Get recruitment pipeline statistics."""
    db = get_db()
    
    stats = {}
    
    # Applicant counts
    for status in APPLICANT_STATUSES:
        stats[f"applicants_{status}"] = await db.employees.count_documents({"status": status})
    
    stats["total_applicants"] = sum(stats[f"applicants_{s}"] for s in APPLICANT_STATUSES)
    
    # Employee counts
    for status in EMPLOYEE_STATUSES:
        stats[f"employees_{status}"] = await db.employees.count_documents({"status": status})
    
    stats["total_employees"] = sum(stats[f"employees_{s}"] for s in EMPLOYEE_STATUSES)
    
    # Approval pending
    stats["pending_approval"] = await db.employees.count_documents({
        "status": {"$in": APPLICANT_STATUSES},
        "recruitment_approved": {"$ne": True}
    })
    
    # Recently approved (last 30 days)
    thirty_days_ago = (datetime.now(timezone.utc).replace(day=1)).isoformat()
    stats["recently_approved"] = await db.employees.count_documents({
        "recruitment_approved": True,
        "recruitment_approved_at": {"$gte": thirty_days_ago}
    })
    
    return stats
