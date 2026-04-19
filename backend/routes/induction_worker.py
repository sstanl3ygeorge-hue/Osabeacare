"""
Worker-facing Care Certificate induction routes.

Endpoints for workers to:
  - List their assigned hybrid induction forms
  - View a form schema (with role-aware prompts)
  - Save a draft
  - Submit a form for admin sign-off

Admin-facing sign-off / return / status endpoints are in routes/induction.py.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import get_db, get_current_worker, log_audit_action
from care_certificate_config import (
    HYBRID_FORM_IDS,
    get_config_for_item,
    get_all_hybrid_forms,
)
from care_certificate_forms import (
    get_worker_form_schema,
    validate_worker_form_submission,
    get_all_worker_form_ids,
)
from induction_definitions import get_employee_induction_status

router = APIRouter(tags=["Care Certificate — Worker"])

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_submission(db, employee_id: str, form_id: str) -> Optional[dict]:
    return await db.induction_item_submissions.find_one(
        {"employee_id": employee_id, "form_id": form_id},
        {"_id": 0},
    )


# ─── Pydantic models ─────────────────────────────────────────────────────────

class FormSavePayload(BaseModel):
    data: dict  # field_key -> value
    is_draft: bool = True


class FormSubmitPayload(BaseModel):
    data: dict  # field_key -> value


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/worker/induction/overview")
async def worker_induction_overview(worker: dict = Depends(get_current_worker)):
    """
    Full induction status for the logged-in worker.

    Returns all 15 Care Certificate items with their current status,
    which items need worker action, and overall checklist state.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=403, detail="Worker not linked to employee record.")

    role_normalized = worker.get("role_normalized") or worker.get("role") or ""

    induction_status = await get_employee_induction_status(db, employee_id)
    items = induction_status.get("items", [])

    # For each hybrid item, fetch submission state from induction_item_submissions
    submission_map = {}
    if any(i.get("completion_type") == "hybrid" for i in items):
        async for sub in db.induction_item_submissions.find(
            {"employee_id": employee_id}, {"_id": 0}
        ):
            submission_map[sub["form_id"]] = sub

    result_items = []
    for item in items:
        cfg = get_config_for_item(item.get("code", ""))
        form_id = cfg.get("worker_form_id") if cfg else None
        sub = submission_map.get(form_id) if form_id else None

        entry = {
            "code": item.get("code"),
            "standard_number": cfg.get("standard_number") if cfg else None,
            "title": item.get("title") or item.get("name"),
            "completion_type": item.get("completion_type"),
            "status": item.get("status"),
            "rule_status": item.get("rule_status"),
            "next_action": item.get("next_action"),
            "synced_from_training": item.get("synced_from_training", False),
        }

        # Hybrid items: add worker-specific submission info
        if form_id:
            entry["form_id"] = form_id
            if sub:
                entry["submission_status"] = sub.get("status")  # draft|submitted|returned|signed_off
                entry["has_draft"] = bool(sub.get("draft_data"))
                entry["submitted_at"] = sub.get("submitted_at")
                entry["return_reason"] = sub.get("return_reason")
            else:
                entry["submission_status"] = None
                entry["has_draft"] = False
                entry["submitted_at"] = None
                entry["return_reason"] = None

            # Worker-friendly next action
            sub_status = (sub or {}).get("status")
            if sub_status == "signed_off":
                entry["worker_action"] = None
            elif sub_status == "submitted":
                entry["worker_action"] = "awaiting_review"
            elif sub_status == "returned":
                entry["worker_action"] = "resubmit"
            elif sub_status == "draft":
                entry["worker_action"] = "complete_form"
            else:
                entry["worker_action"] = "start_form"

        result_items.append(entry)

    # Sort by standard_number
    result_items.sort(key=lambda x: x.get("standard_number") or 99)

    return {
        "employee_id": employee_id,
        "overall_status": induction_status.get("overall_status"),
        "completed": induction_status.get("completed"),
        "total": induction_status.get("total"),
        "items": result_items,
    }


@router.get("/worker/induction/forms")
async def list_worker_induction_forms(worker: dict = Depends(get_current_worker)):
    """
    Return the list of hybrid induction forms assigned to this worker
    along with their submission state (not started / draft / submitted / returned / signed_off).
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=403, detail="Worker not linked to employee record.")

    role_normalized = worker.get("role_normalized") or worker.get("role") or ""

    # Fetch all submissions for this worker in one query
    submission_map = {}
    async for sub in db.induction_item_submissions.find(
        {"employee_id": employee_id}, {"_id": 0, "form_id": 1, "status": 1,
                                        "submitted_at": 1, "return_reason": 1,
                                        "draft_data": 1}
    ):
        submission_map[sub["form_id"]] = sub

    forms = []
    for hybrid in get_all_hybrid_forms():
        form_id = hybrid["form_id"]
        sub = submission_map.get(form_id)
        forms.append({
            "form_id": form_id,
            "standard_number": hybrid["standard_number"],
            "title": hybrid["title"],
            "standard_code": hybrid["code"],
            "submission_status": sub.get("status") if sub else None,
            "has_draft": bool(sub.get("draft_data")) if sub else False,
            "submitted_at": sub.get("submitted_at") if sub else None,
            "return_reason": sub.get("return_reason") if sub else None,
        })

    forms.sort(key=lambda x: x["standard_number"])
    return {"forms": forms, "total": len(forms)}


@router.get("/worker/induction/forms/{form_id}")
async def get_worker_induction_form(
    form_id: str,
    worker: dict = Depends(get_current_worker),
):
    """
    Return schema + any saved draft for a single hybrid form.
    Includes role-aware prompts resolved for this worker's role.
    """
    if form_id not in get_all_worker_form_ids():
        raise HTTPException(status_code=404, detail=f"Form '{form_id}' not found.")

    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=403, detail="Worker not linked to employee record.")

    role_normalized = worker.get("role_normalized") or worker.get("role") or ""
    schema = get_worker_form_schema(form_id, role_normalized)

    submission = await _get_submission(db, employee_id, form_id)

    return {
        "form_id": form_id,
        "schema": schema,
        "submission_status": submission.get("status") if submission else None,
        "draft_data": submission.get("draft_data") if submission else None,
        "submitted_data": (
            submission.get("submitted_data")
            if submission and submission.get("status") in ("returned",)
            else None
        ),
        "return_reason": submission.get("return_reason") if submission else None,
        "submitted_at": submission.get("submitted_at") if submission else None,
        "signoff_at": submission.get("signoff_at") if submission else None,
    }


@router.post("/worker/induction/forms/{form_id}/save")
async def save_worker_induction_form_draft(
    form_id: str,
    payload: FormSavePayload,
    worker: dict = Depends(get_current_worker),
):
    """
    Save a draft for a hybrid induction form.
    Workers can save progress without submitting.
    Not allowed if the form is already submitted and awaiting review.
    """
    if form_id not in get_all_worker_form_ids():
        raise HTTPException(status_code=404, detail=f"Form '{form_id}' not found.")

    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=403, detail="Worker not linked to employee record.")

    now = _now()
    submission = await _get_submission(db, employee_id, form_id)

    if submission and submission.get("status") == "submitted":
        raise HTTPException(
            status_code=409,
            detail="This form has already been submitted and is awaiting review. You cannot edit it now."
        )
    if submission and submission.get("status") == "signed_off":
        raise HTTPException(
            status_code=409,
            detail="This form has already been signed off and cannot be changed."
        )

    if submission:
        await db.induction_item_submissions.update_one(
            {"employee_id": employee_id, "form_id": form_id},
            {"$set": {
                "draft_data": payload.data,
                "status": "draft",
                "updated_at": now,
            }},
        )
    else:
        cfg_item = next(
            (h for h in get_all_hybrid_forms() if h["form_id"] == form_id), {}
        )
        await db.induction_item_submissions.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "worker_id": worker.get("employee_id"),
            "form_id": form_id,
            "item_code": cfg_item.get("code"),
            "standard_number": cfg_item.get("standard_number"),
            "status": "draft",
            "draft_data": payload.data,
            "submitted_data": None,
            "submitted_at": None,
            "signoff_by": None,
            "signoff_at": None,
            "admin_notes": None,
            "return_reason": None,
            "returned_at": None,
            "created_at": now,
            "updated_at": now,
        })

    return {"ok": True, "status": "draft", "saved_at": now}


@router.post("/worker/induction/forms/{form_id}/submit")
async def submit_worker_induction_form(
    form_id: str,
    payload: FormSubmitPayload,
    worker: dict = Depends(get_current_worker),
):
    """
    Submit a hybrid induction form for admin review / sign-off.
    Validates all required fields before accepting.
    Not allowed if already submitted or signed off.
    """
    if form_id not in get_all_worker_form_ids():
        raise HTTPException(status_code=404, detail=f"Form '{form_id}' not found.")

    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=403, detail="Worker not linked to employee record.")

    # Validate form data
    validation_errors = validate_worker_form_submission(form_id, payload.data)
    if validation_errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Form validation failed.", "errors": validation_errors},
        )

    now = _now()
    submission = await _get_submission(db, employee_id, form_id)

    if submission and submission.get("status") == "submitted":
        raise HTTPException(
            status_code=409,
            detail="This form is already submitted and awaiting review."
        )
    if submission and submission.get("status") == "signed_off":
        raise HTTPException(
            status_code=409,
            detail="This form has already been signed off."
        )

    cfg_item = next(
        (h for h in get_all_hybrid_forms() if h["form_id"] == form_id), {}
    )

    if submission:
        await db.induction_item_submissions.update_one(
            {"employee_id": employee_id, "form_id": form_id},
            {"$set": {
                "submitted_data": payload.data,
                "draft_data": None,
                "status": "submitted",
                "submitted_at": now,
                "return_reason": None,
                "returned_at": None,
                "updated_at": now,
            }},
        )
    else:
        await db.induction_item_submissions.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "worker_id": worker.get("employee_id"),
            "form_id": form_id,
            "item_code": cfg_item.get("code"),
            "standard_number": cfg_item.get("standard_number"),
            "status": "submitted",
            "draft_data": None,
            "submitted_data": payload.data,
            "submitted_at": now,
            "signoff_by": None,
            "signoff_at": None,
            "admin_notes": None,
            "return_reason": None,
            "returned_at": None,
            "created_at": now,
            "updated_at": now,
        })

    await log_audit_action(
        employee_id,
        "worker_induction_form_submitted",
        "induction_item_submissions",
        employee_id,
        {"form_id": form_id, "item_code": cfg_item.get("code")},
    )

    return {"ok": True, "status": "submitted", "submitted_at": now}
