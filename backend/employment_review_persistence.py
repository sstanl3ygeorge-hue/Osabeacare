"""
Persistence helpers for canonical Employment Review records.

This is the first persistence layer only. It stores one current review per
employee, but it does not switch existing UI, compliance-file, worker dashboard,
or write-path behaviour to the new model yet.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from employment_review_engine import (
    REVIEW_STATUS_FULLY_ACCOUNTED,
    build_employment_review_from_employee,
)


def _get_timeline_fingerprint(review: Dict[str, Any]) -> Optional[str]:
    return (review.get("diagnostics") or {}).get("timeline_fingerprint") or review.get("timeline_fingerprint")


def _build_invalidated_signoff_from_prior(prior_review: Dict[str, Any], reason: str) -> Dict[str, Any]:
    prior_signoff = prior_review.get("sign_off") or {}
    return {
        **prior_signoff,
        "signed_off": False,
        "previous_signed_off": bool(prior_signoff.get("signed_off") or prior_signoff.get("previous_signed_off")),
        "decision": None,
        "timeline_fingerprint": None,
        "invalidated": True,
        "invalidated_reason": reason,
    }


def _preserve_current_signoff_if_still_valid(review: Dict[str, Any], prior_review: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not prior_review:
        return review

    prior_signoff = prior_review.get("sign_off") or {}
    if not prior_signoff.get("signed_off"):
        return review

    prior_fingerprint = prior_review.get("timeline_fingerprint") or _get_timeline_fingerprint(prior_review)
    current_fingerprint = _get_timeline_fingerprint(review)
    same_timeline = prior_fingerprint and current_fingerprint and prior_fingerprint == current_fingerprint
    same_version = int(prior_review.get("version") or 1) == int(review.get("version") or 1)
    current_blockers = (review.get("gap_actions") or {}).get("blocked_sign_off_reasons") or []
    still_eligible = bool(review.get("can_sign_off")) and not current_blockers

    if same_timeline and same_version and still_eligible:
        preserved = {
            **prior_signoff,
            "signed_off": True,
            "previous_signed_off": True,
            "version_signed": prior_signoff.get("version_signed") or prior_review.get("version"),
            "timeline_fingerprint": current_fingerprint,
            "invalidated": False,
            "invalidated_reason": None,
        }
        review["sign_off"] = preserved
        review["status"] = REVIEW_STATUS_FULLY_ACCOUNTED
        review["status_label"] = "Fully accounted"
        review["status_reason"] = "Employment review was signed off for this review version and timeline."
        review["can_sign_off"] = False
        review.setdefault("gap_actions", {})["can_sign_off"] = False
        review.setdefault("gap_actions", {})["blocked_sign_off_reasons"] = []
    elif same_timeline and same_version:
        review["sign_off"] = _build_invalidated_signoff_from_prior(
            prior_review,
            "Current review no longer meets sign-off eligibility.",
        )

    return review


async def build_persistable_employment_review(
    db,
    employee_id: str,
    *,
    as_of_date: date | None = None,
) -> Dict[str, Any]:
    """Build the current canonical review plus persistence metadata."""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise ValueError("Employee not found")

    # Resolve stable case anchor: stored field > application_submitted_at > caller-supplied > now
    _stored_anchor = employee.get("employment_window_reference_date")
    _app_submitted = employee.get("application_submitted_at")
    if _stored_anchor:
        from datetime import date as _date_cls
        try:
            _anchor_dt = datetime.fromisoformat(_stored_anchor.replace("Z", "+00:00"))
            if _anchor_dt.tzinfo is None:
                _anchor_dt = _anchor_dt.replace(tzinfo=timezone.utc)
            resolved_as_of_date = _anchor_dt
        except (ValueError, AttributeError):
            resolved_as_of_date = as_of_date
    elif _app_submitted:
        try:
            _anchor_dt = datetime.fromisoformat(_app_submitted.replace("Z", "+00:00"))
            if _anchor_dt.tzinfo is None:
                _anchor_dt = _anchor_dt.replace(tzinfo=timezone.utc)
            resolved_as_of_date = _anchor_dt
        except (ValueError, AttributeError):
            resolved_as_of_date = as_of_date
    else:
        resolved_as_of_date = as_of_date  # None falls back to now() inside engine

    # Store the resolved anchor date string for later use by caller
    resolved_anchor_str = (
        resolved_as_of_date.strftime("%Y-%m-%d")
        if resolved_as_of_date is not None
        else None
    )

    prior_review = await db.employment_reviews.find_one(
        {"employee_id": employee_id, "current": True},
        {"_id": 0},
    )

    gap_records = await db.employment_gaps.find(
        {"employee_id": employee_id},
        {"_id": 0},
    ).sort("gap_start", 1).to_list(200)
    if not gap_records and employee.get("employment_gaps"):
        gap_records = [
            gap for gap in employee.get("employment_gaps", [])
            if isinstance(gap, dict)
        ]

    base_version = int((prior_review or {}).get("version") or 1)
    review_employee = {**employee, "employment_review_version": base_version}
    review = build_employment_review_from_employee(
        review_employee,
        gap_records or [],
        employee.get("gap_explanations") or [],
        as_of_date=resolved_as_of_date,
    )

    current_fingerprint = _get_timeline_fingerprint(review)
    prior_fingerprint = (prior_review or {}).get("timeline_fingerprint") or _get_timeline_fingerprint(prior_review or {})
    timeline_changed = bool(prior_review and prior_fingerprint and current_fingerprint and prior_fingerprint != current_fingerprint)

    if timeline_changed:
        review_employee["employment_review_version"] = base_version + 1
        review = build_employment_review_from_employee(
            review_employee,
            gap_records or [],
            employee.get("gap_explanations") or [],
            as_of_date=resolved_as_of_date,
        )
        current_fingerprint = _get_timeline_fingerprint(review)
        if (prior_review.get("sign_off") or {}).get("signed_off"):
            review["sign_off"] = _build_invalidated_signoff_from_prior(
                prior_review,
                "Employment review timeline has changed since sign-off.",
            )
    else:
        review = _preserve_current_signoff_if_still_valid(review, prior_review)

    now = datetime.now(timezone.utc).isoformat()
    review["current"] = True
    review["persisted_at"] = now
    review["updated_at"] = now
    review["timeline_fingerprint"] = current_fingerprint
    review["employment_window_reference_date"] = resolved_anchor_str
    review["source_counts"] = {
        "employment_history_rows": len(employee.get("employment_history") or []),
        "existing_gap_records": len(gap_records or []),
        "applicant_explanations": len(employee.get("gap_explanations") or []),
        "legacy_employee_gap_rows": len(employee.get("employment_gaps") or []),
    }
    review["legacy_metadata"] = {
        "gap_analysis_status": employee.get("gap_analysis_status"),
        "gap_analysis_error": employee.get("gap_analysis_error"),
        "employment_review_signed_off": employee.get("employment_review_signed_off"),
        "employment_review_signed_off_at": employee.get("employment_review_signed_off_at"),
        "employment_review_signed_off_by": employee.get("employment_review_signed_off_by"),
        "employment_review_signed_off_by_name": employee.get("employment_review_signed_off_by_name"),
    }
    return review


async def upsert_employment_review(
    db,
    employee_id: str,
    *,
    as_of_date: date | None = None,
    actor_id: str | None = None,
    reason: str = "manual_rebuild",
) -> Dict[str, Any]:
    """
    Build and persist the current canonical Employment Review record.

    This writes only to ``employment_reviews``. Legacy fields and old collections
    are intentionally left untouched in this pass.
    """
    review = await build_persistable_employment_review(
        db,
        employee_id,
        as_of_date=as_of_date,
    )
    now = datetime.now(timezone.utc).isoformat()
    review["last_rebuilt_at"] = now
    review["last_rebuilt_by"] = actor_id
    review["last_rebuild_reason"] = reason

    await db.employment_reviews.update_one(
        {"employee_id": employee_id, "current": True},
        {"$set": review, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    # Store the case anchor on the employee document once — never overwrite.
    if review.get("employment_window_reference_date"):
        await db.employees.update_one(
            {"id": employee_id, "employment_window_reference_date": {"$exists": False}},
            {"$set": {"employment_window_reference_date": review["employment_window_reference_date"]}},
        )

    return review


async def sign_off_current_employment_review(
    db,
    employee_id: str,
    *,
    actor_id: str | None = None,
    actor_name: str | None = None,
    notes: str | None = None,
) -> Dict[str, Any]:
    """
    Sign off the current canonical Employment Review version.

    The sign-off belongs to the persisted review version and timeline
    fingerprint. It is intentionally separate from legacy employee-level
    sign-off fields, which callers may still mirror for compatibility.
    """
    review = await upsert_employment_review(
        db,
        employee_id,
        actor_id=actor_id,
        reason="employment_review_pre_signoff_rebuild",
    )
    blocked_reasons = (review.get("gap_actions") or {}).get("blocked_sign_off_reasons") or []
    if review.get("cannot_assess") or not (review.get("gap_actions") or {}).get("can_sign_off") or blocked_reasons:
        detail = "; ".join(blocked_reasons) if blocked_reasons else review.get("status_reason") or "Employment review is not ready for sign-off."
        raise ValueError(detail)

    now = datetime.now(timezone.utc).isoformat()
    sign_off = {
        "signed_off": True,
        "previous_signed_off": True,
        "version_signed": review.get("version"),
        "signed_off_by": actor_id,
        "signed_off_by_name": actor_name,
        "signed_off_at": now,
        "decision": "signed_off",
        "notes": notes,
        "timeline_fingerprint": review.get("timeline_fingerprint") or _get_timeline_fingerprint(review),
        "invalidated": False,
        "invalidated_reason": None,
    }
    review["sign_off"] = sign_off
    review["status"] = REVIEW_STATUS_FULLY_ACCOUNTED
    review["status_label"] = "Fully accounted"
    review["status_reason"] = "Employment review was signed off for this review version and timeline."
    review["can_sign_off"] = False
    review.setdefault("gap_actions", {})["can_sign_off"] = False
    review.setdefault("gap_actions", {})["blocked_sign_off_reasons"] = []
    review["updated_at"] = now
    review["last_rebuilt_at"] = now
    review["last_rebuilt_by"] = actor_id
    review["last_rebuild_reason"] = "employment_review_signoff"

    await db.employment_reviews.update_one(
        {"employee_id": employee_id, "current": True},
        {"$set": review, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return review
