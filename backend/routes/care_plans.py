"""
Service User Care Plan routes - Phase 2A backend foundation.

Scope:
- Canonical care plan versions in service_user_care_plans
- Admin/manager access only
- Single active version per service user
- Statuses: draft, active, superseded, archived
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Response
from pydantic import BaseModel, Field, ConfigDict

from .dependencies import (
    get_db,
    require_manager_or_admin,
    log_audit_action,
)

router = APIRouter(tags=["Service User Care Plans"])

CARE_PLAN_STATUSES = {"draft", "active", "superseded", "archived"}
CARE_PLAN_SECTION_STATUSES = {"missing", "draft", "complete", "review_due"}
CARE_PLAN_REQUIRED_SECTIONS = [
    "Personal information / This is me",
    "Consent and capacity",
    "Mobility and falls",
    "Nutrition and hydration",
    "Medication",
    "Personal care",
    "Mental wellbeing",
    "Health conditions",
    "Risk assessments",
    "Daily notes / monitoring link",
    "Care plan review",
]


def _default_section_statuses() -> Dict[str, str]:
    return {section_name: "missing" for section_name in CARE_PLAN_REQUIRED_SECTIONS}


def _normalize_section_statuses(section_statuses: Optional[Dict[str, Any]]) -> Dict[str, str]:
    normalized = _default_section_statuses()
    for section_name, status in (section_statuses or {}).items():
        if section_name in normalized and status in CARE_PLAN_SECTION_STATUSES:
            normalized[section_name] = status
    return normalized


def _serialize_care_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(plan)
    serialized["section_statuses"] = _normalize_section_statuses(plan.get("section_statuses"))
    serialized["reviewed_at"] = plan.get("reviewed_at")
    serialized["reviewed_by"] = plan.get("reviewed_by")
    serialized["review_notes"] = plan.get("review_notes") or ""
    serialized["next_review_due_at"] = plan.get("next_review_due_at") or plan.get("review_due_at")
    return serialized


async def _get_care_plan_or_404(service_user_id: str, care_plan_id: str) -> Dict[str, Any]:
    db = get_db()
    plan = await db.service_user_care_plans.find_one(
        {"id": care_plan_id, "service_user_id": service_user_id},
        {"_id": 0},
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Care plan not found")
    return plan


class CarePlanCreate(BaseModel):
    care_plan_title: str = Field(..., min_length=1)
    goals: List[str] = Field(default_factory=list)
    needs_summary: str = ""
    support_instructions: str = ""
    effective_from: Optional[str] = None
    review_due_at: Optional[str] = None


class CarePlanUpdate(BaseModel):
    care_plan_title: Optional[str] = None
    goals: Optional[List[str]] = None
    needs_summary: Optional[str] = None
    support_instructions: Optional[str] = None
    effective_from: Optional[str] = None
    review_due_at: Optional[str] = None


class CarePlanArchiveRequest(BaseModel):
    replacement_care_plan_id: Optional[str] = None


class CarePlanSectionStatusUpdateRequest(BaseModel):
    section_name: str
    status: str


class CarePlanReviewRecordRequest(BaseModel):
    review_notes: str = ""
    reviewed_at: Optional[str] = None
    next_review_due_at: Optional[str] = None


class CarePlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    service_user_id: str
    version_number: int
    status: str
    care_plan_title: str
    goals: List[str] = []
    needs_summary: str = ""
    support_instructions: str = ""
    effective_from: Optional[str] = None
    review_due_at: Optional[str] = None
    section_statuses: Dict[str, str] = Field(default_factory=_default_section_statuses)
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    superseded_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_notes: str = ""
    next_review_due_at: Optional[str] = None


async def _require_service_user_or_404(service_user_id: str) -> Dict[str, Any]:
    db = get_db()
    service_user = await db.service_users.find_one(
        {"id": service_user_id},
        {"_id": 0, "id": 1, "full_name": 1, "service_user_code": 1},
    )
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    return service_user


@router.post("/service-users/{service_user_id}/care-plans", response_model=CarePlanResponse)
async def create_care_plan_draft(
    service_user_id: str,
    payload: CarePlanCreate,
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    db = get_db()

    latest = await db.service_user_care_plans.find_one(
        {"service_user_id": service_user_id},
        {"_id": 0, "version_number": 1},
        sort=[("version_number", -1)],
    )
    next_version = int((latest or {}).get("version_number") or 0) + 1
    now = datetime.now(timezone.utc).isoformat()
    care_plan_id = str(uuid.uuid4())

    doc = {
        "id": care_plan_id,
        "service_user_id": service_user_id,
        "version_number": next_version,
        "status": "draft",
        "care_plan_title": payload.care_plan_title,
        "goals": payload.goals or [],
        "needs_summary": payload.needs_summary or "",
        "support_instructions": payload.support_instructions or "",
        "effective_from": payload.effective_from,
        "review_due_at": payload.review_due_at,
        "section_statuses": _default_section_statuses(),
        "created_by": user.get("user_id"),
        "created_at": now,
        "updated_at": now,
        "approved_by": None,
        "approved_at": None,
        "superseded_by": None,
        "reviewed_at": None,
        "reviewed_by": None,
        "review_notes": "",
        "next_review_due_at": payload.review_due_at,
    }
    await db.service_user_care_plans.insert_one(doc)

    await log_audit_action(
        user.get("user_id"),
        "create_service_user_care_plan",
        "service_user_care_plan",
        care_plan_id,
        {
            "service_user_id": service_user_id,
            "version_number": next_version,
            "status": "draft",
            "title": payload.care_plan_title,
        },
    )

    return _serialize_care_plan(doc)


@router.get("/service-users/{service_user_id}/care-plans", response_model=List[CarePlanResponse])
async def list_service_user_care_plans(
    service_user_id: str,
    include_archived: bool = Query(default=False),
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    db = get_db()
    query: Dict[str, Any] = {"service_user_id": service_user_id}
    if not include_archived:
        query["status"] = {"$ne": "archived"}

    plans = await db.service_user_care_plans.find(query, {"_id": 0}).sort("version_number", -1).to_list(200)
    return [_serialize_care_plan(plan) for plan in plans]


@router.get("/service-users/{service_user_id}/care-plans/{care_plan_id}", response_model=CarePlanResponse)
async def get_service_user_care_plan(
    service_user_id: str,
    care_plan_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    plan = await _get_care_plan_or_404(service_user_id, care_plan_id)
    return _serialize_care_plan(plan)


@router.put("/service-users/{service_user_id}/care-plans/{care_plan_id}", response_model=CarePlanResponse)
async def update_service_user_care_plan_draft(
    service_user_id: str,
    care_plan_id: str,
    payload: CarePlanUpdate,
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    db = get_db()
    existing = await _get_care_plan_or_404(service_user_id, care_plan_id)
    if existing.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft care plans can be updated")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        return _serialize_care_plan(existing)
    if "review_due_at" in update_data:
        update_data["next_review_due_at"] = update_data["review_due_at"]
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.service_user_care_plans.update_one(
        {"id": care_plan_id},
        {"$set": update_data},
    )
    updated = await db.service_user_care_plans.find_one({"id": care_plan_id}, {"_id": 0})

    await log_audit_action(
        user.get("user_id"),
        "update_service_user_care_plan",
        "service_user_care_plan",
        care_plan_id,
        {
            "service_user_id": service_user_id,
            "updated_fields": list(update_data.keys()),
        },
    )

    return _serialize_care_plan(updated)


@router.post("/service-users/{service_user_id}/care-plans/{care_plan_id}/activate", response_model=CarePlanResponse)
async def activate_service_user_care_plan_draft(
    service_user_id: str,
    care_plan_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    db = get_db()
    plan = await _get_care_plan_or_404(service_user_id, care_plan_id)
    if plan.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft care plans can be activated")

    now = datetime.now(timezone.utc).isoformat()

    # Supersede any currently active care plan for this service user.
    active_plan = await db.service_user_care_plans.find_one(
        {"service_user_id": service_user_id, "status": "active"},
        {"_id": 0, "id": 1},
    )
    if active_plan and active_plan.get("id") != care_plan_id:
        await db.service_user_care_plans.update_one(
            {"id": active_plan["id"]},
            {
                "$set": {
                    "status": "superseded",
                    "superseded_by": care_plan_id,
                    "updated_at": now,
                }
            },
        )

    await db.service_user_care_plans.update_one(
        {"id": care_plan_id},
        {
            "$set": {
                "status": "active",
                "approved_by": user.get("user_id"),
                "approved_at": now,
                "effective_from": plan.get("effective_from") or now,
                "superseded_by": None,
                "updated_at": now,
            }
        },
    )
    activated = await db.service_user_care_plans.find_one({"id": care_plan_id}, {"_id": 0})

    await log_audit_action(
        user.get("user_id"),
        "activate_service_user_care_plan",
        "service_user_care_plan",
        care_plan_id,
        {
            "service_user_id": service_user_id,
            "version_number": plan.get("version_number"),
            "superseded_previous_active": active_plan.get("id") if active_plan else None,
        },
    )

    return _serialize_care_plan(activated)


@router.post("/service-users/{service_user_id}/care-plans/{care_plan_id}/archive", response_model=CarePlanResponse)
async def archive_service_user_care_plan(
    service_user_id: str,
    care_plan_id: str,
    payload: Optional[CarePlanArchiveRequest] = None,
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    db = get_db()
    plan = await _get_care_plan_or_404(service_user_id, care_plan_id)

    status = plan.get("status")
    payload = payload or CarePlanArchiveRequest()
    if status not in CARE_PLAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid care plan status")
    if status == "archived":
        return _serialize_care_plan(plan)
    if status == "active":
        replacement_id = (payload.replacement_care_plan_id or "").strip()
        if not replacement_id:
            raise HTTPException(
                status_code=400,
                detail="Active care plan cannot be archived without an active replacement",
            )
        replacement = await db.service_user_care_plans.find_one(
            {"id": replacement_id, "service_user_id": service_user_id},
            {"_id": 0, "id": 1, "status": 1},
        )
        if not replacement or replacement.get("status") != "active":
            raise HTTPException(
                status_code=400,
                detail="Replacement care plan must exist and be active",
            )

    now = datetime.now(timezone.utc).isoformat()
    await db.service_user_care_plans.update_one(
        {"id": care_plan_id},
        {"$set": {"status": "archived", "updated_at": now}},
    )
    archived = await db.service_user_care_plans.find_one({"id": care_plan_id}, {"_id": 0})

    await log_audit_action(
        user.get("user_id"),
        "archive_service_user_care_plan",
        "service_user_care_plan",
        care_plan_id,
        {
            "service_user_id": service_user_id,
            "previous_status": status,
            "replacement_care_plan_id": payload.replacement_care_plan_id,
        },
    )

    return _serialize_care_plan(archived)


@router.patch("/service-users/{service_user_id}/care-plans/{care_plan_id}/section-status", response_model=CarePlanResponse)
async def update_care_plan_section_status(
    service_user_id: str,
    care_plan_id: str,
    payload: CarePlanSectionStatusUpdateRequest,
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    db = get_db()
    plan = await _get_care_plan_or_404(service_user_id, care_plan_id)
    if plan.get("status") not in {"draft", "active"}:
        raise HTTPException(status_code=400, detail="Section status can only be updated on draft or active care plans")
    if payload.section_name not in CARE_PLAN_REQUIRED_SECTIONS:
        raise HTTPException(status_code=400, detail="Invalid section_name")
    if payload.status not in CARE_PLAN_SECTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid section status")

    section_statuses = _normalize_section_statuses(plan.get("section_statuses"))
    section_statuses[payload.section_name] = payload.status
    now = datetime.now(timezone.utc).isoformat()
    await db.service_user_care_plans.update_one(
        {"id": care_plan_id},
        {"$set": {"section_statuses": section_statuses, "updated_at": now}},
    )
    updated = await db.service_user_care_plans.find_one({"id": care_plan_id}, {"_id": 0})

    await log_audit_action(
        user.get("user_id"),
        "update_service_user_care_plan_section_status",
        "service_user_care_plan",
        care_plan_id,
        {
            "service_user_id": service_user_id,
            "section_name": payload.section_name,
            "status": payload.status,
        },
    )

    return _serialize_care_plan(updated)


@router.post("/service-users/{service_user_id}/care-plans/{care_plan_id}/record-review", response_model=CarePlanResponse)
async def record_care_plan_review(
    service_user_id: str,
    care_plan_id: str,
    payload: CarePlanReviewRecordRequest,
    user: dict = Depends(require_manager_or_admin),
):
    await _require_service_user_or_404(service_user_id)
    db = get_db()
    plan = await _get_care_plan_or_404(service_user_id, care_plan_id)
    if plan.get("status") != "active":
        raise HTTPException(status_code=400, detail="Only active care plans can be reviewed")

    reviewed_at_value = payload.reviewed_at or datetime.now(timezone.utc).isoformat()
    reviewed_at = datetime.fromisoformat(reviewed_at_value.replace("Z", "+00:00"))
    next_review_due_at = payload.next_review_due_at
    if next_review_due_at:
        datetime.fromisoformat(next_review_due_at.replace("Z", "+00:00"))
    else:
        next_review_due_at = (reviewed_at + timedelta(days=28)).isoformat()

    update_data = {
        "reviewed_at": reviewed_at.isoformat(),
        "reviewed_by": user.get("user_id"),
        "review_notes": (payload.review_notes or "").strip(),
        "next_review_due_at": next_review_due_at,
        "review_due_at": next_review_due_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.service_user_care_plans.update_one({"id": care_plan_id}, {"$set": update_data})
    updated = await db.service_user_care_plans.find_one({"id": care_plan_id}, {"_id": 0})

    await log_audit_action(
        user.get("user_id"),
        "record_service_user_care_plan_review",
        "service_user_care_plan",
        care_plan_id,
        {
            "service_user_id": service_user_id,
            "reviewed_at": update_data["reviewed_at"],
            "next_review_due_at": next_review_due_at,
        },
    )

    return _serialize_care_plan(updated)


@router.get("/service-users/{service_user_id}/care-plans/{care_plan_id}/download-pdf")
async def download_service_user_care_plan_pdf(
    service_user_id: str,
    care_plan_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    service_user = await _require_service_user_or_404(service_user_id)
    db = get_db()
    plan = await db.service_user_care_plans.find_one(
        {"id": care_plan_id, "service_user_id": service_user_id},
        {"_id": 0},
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Care plan not found")

    from services.pdf_service import generate_service_user_care_plan_pdf

    pdf_bytes = generate_service_user_care_plan_pdf(
        care_plan_data=plan,
        service_user_data=service_user,
        admin_data={
            "downloaded_by": user.get("name") or user.get("email") or user.get("user_id"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    await log_audit_action(
        user.get("user_id"),
        "download_service_user_care_plan_pdf",
        "service_user_care_plan",
        care_plan_id,
        {
            "service_user_id": service_user_id,
            "status": plan.get("status"),
            "version_number": plan.get("version_number"),
        },
    )

    su_code = str(service_user.get("service_user_code") or service_user_id)
    safe_su_code = su_code.replace("/", "-").replace("\\", "-").replace(":", "-")
    filename = f"care_plan_{safe_su_code}_v{plan.get('version_number') or '0'}_{care_plan_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
