"""
Canonical employment review builder.

This module is intentionally side-effect free. It builds the proposed
Employment Review object from the current employee record, existing canonical
gap records, and applicant-submitted explanations, but it does not write to the
database or make the review authoritative yet.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from employment_gap_engine import (
    GapStatus,
    _normalise_employment_history_entries,
    compute_coverage_summary,
    detect_employment_gaps_with_coverage,
    evaluate_gaps_compliance,
    match_gap_explanations_to_canonical_gaps,
    parse_employment_date,
)


REVIEW_STATUS_NOT_STARTED = "not_started"
REVIEW_STATUS_IN_PROGRESS = "in_progress"
REVIEW_STATUS_AWAITING_ADMIN_REVIEW = "awaiting_admin_review"
REVIEW_STATUS_FULLY_ACCOUNTED = "fully_accounted"
REVIEW_STATUS_CANNOT_ASSESS = "cannot_assess"

GAP_STATUS_MISSING = "missing"
GAP_STATUS_EXPLAINED = "explained"
GAP_STATUS_VERIFIED = "verified"
GAP_STATUS_REJECTED = "rejected"


def _as_utc_datetime(value: Optional[date]) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _date_only(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() == "present":
        return "present"
    parsed = parse_employment_date(value)
    if parsed:
        return parsed.strftime("%Y-%m-%d")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _gap_match_key(gap: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    return (
        _date_only(gap.get("gap_start") or gap.get("start_date")),
        _date_only(gap.get("gap_end") or gap.get("end_date")),
    )


def _normalise_gap_status(raw_status: Optional[str]) -> str:
    if raw_status == GapStatus.VERIFIED.value:
        return GAP_STATUS_VERIFIED
    if raw_status == GapStatus.EXPLAINED.value:
        return GAP_STATUS_EXPLAINED
    if raw_status in {GapStatus.REJECTED.value, GapStatus.NEEDS_MORE_INFO.value}:
        return GAP_STATUS_REJECTED
    return GAP_STATUS_MISSING


def _overlay_existing_gap_decisions(
    detected_gaps: List[Dict[str, Any]],
    existing_gap_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Preserve existing explanation/review state on freshly detected gaps."""
    existing_by_range = {}
    existing_by_legacy_id = {}

    for record in existing_gap_records or []:
        if not isinstance(record, dict):
            continue
        key = _gap_match_key(record)
        if key[0] and key[1]:
            existing_by_range[key] = record
        legacy_id = record.get("gap_id") or record.get("id")
        if legacy_id:
            existing_by_legacy_id[str(legacy_id)] = record

    merged = []
    preserve_fields = {
        "id",
        "status",
        "explanation",
        "reason_type",
        "explanation_provided_at",
        "explained_by",
        "explanation_source",
        "evidence_document_id",
        "verified_by",
        "verified_by_name",
        "verified_at",
        "rejection_reason",
        "notes",
        "admin_notes",
        "reviewed_by",
        "reviewed_by_name",
        "reviewed_at",
        "applicant_explanation",
        "applicant_explanation_match",
        "matched_by",
        "source_gap_id",
    }

    for gap in detected_gaps or []:
        gap_copy = dict(gap)
        existing = existing_by_range.get(_gap_match_key(gap_copy))
        if existing is None:
            existing = existing_by_legacy_id.get(str(gap_copy.get("gap_id")))
        if existing:
            for field in preserve_fields:
                if field in existing and existing.get(field) is not None:
                    gap_copy[field] = existing.get(field)
            gap_copy["preserved_from_existing_gap"] = True
        merged.append(gap_copy)

    return merged


def _employment_segment_from_job(job: Dict[str, Any], index: int) -> Dict[str, Any]:
    start_date = _date_only(job.get("start_date") or job.get("from_date"))
    end_date = _date_only(job.get("end_date") or job.get("to_date")) or "present"
    employer = job.get("company") or job.get("employer_name") or job.get("employer") or "Unknown"
    role = job.get("role") or job.get("job_title") or job.get("position") or ""

    return {
        "id": job.get("id") or job.get("record_id") or f"employment_{index + 1}",
        "type": "employment",
        "order": 0,
        "start_date": start_date,
        "end_date": end_date,
        "title": role,
        "organisation": employer,
        "role": role,
        "employer": employer,
        "source": job.get("source") or "employment_history",
        "source_label": job.get("source_label") or "Employment history",
        "source_record_id": job.get("id") or job.get("record_id"),
        "parse_status": "valid",
        "diagnostics": [],
        "raw_record": {k: v for k, v in job.items() if not str(k).startswith("_parsed_")},
    }


def _gap_segment_from_gap(gap: Dict[str, Any], index: int) -> Dict[str, Any]:
    raw_status = gap.get("status") or GapStatus.PENDING.value
    status = _normalise_gap_status(raw_status)
    gap_id = gap.get("gap_id") or gap.get("id") or f"gap_{index + 1}"
    explanation = gap.get("applicant_explanation") or {}
    explanation_text = gap.get("explanation") or explanation.get("explanation")

    if explanation_text:
        explanation = {
            **explanation,
            "text": explanation_text,
            "reason_type": gap.get("reason_type") or explanation.get("reason_type"),
            "submitted_by": gap.get("explained_by") or explanation.get("explained_by") or "applicant",
            "submitted_at": gap.get("explanation_provided_at") or explanation.get("explanation_provided_at"),
            "matched_by": gap.get("matched_by") or explanation.get("matched_by"),
            "source_gap_id": gap.get("source_gap_id") or explanation.get("source_gap_id"),
        }
    else:
        explanation = None

    return {
        "id": str(gap.get("id") or gap_id),
        "gap_id": gap_id,
        "type": "gap",
        "order": 0,
        "start_date": _date_only(gap.get("gap_start") or gap.get("start_date")),
        "end_date": _date_only(gap.get("gap_end") or gap.get("end_date")),
        "duration_days": gap.get("duration_days"),
        "duration_months": gap.get("duration_months"),
        "gap_type": gap.get("gap_type") or "inter_employment",
        "status": status,
        "raw_status": raw_status,
        "status_label": {
            GAP_STATUS_MISSING: "Missing explanation",
            GAP_STATUS_EXPLAINED: "Explained, awaiting admin review",
            GAP_STATUS_VERIFIED: "Verified",
            GAP_STATUS_REJECTED: "Rejected / action required",
        }.get(status, "Missing explanation"),
        "readiness_impact": "none" if status == GAP_STATUS_VERIFIED else "blocking_until_verified",
        "previous_employment": gap.get("previous_employment"),
        "next_employment": gap.get("next_employment"),
        "explanation": explanation,
        "evidence": {
            "document_ids": [gap.get("evidence_document_id")] if gap.get("evidence_document_id") else [],
            "has_evidence": bool(gap.get("evidence_document_id")),
        },
        "admin_review": {
            "decision": status if status in {GAP_STATUS_VERIFIED, GAP_STATUS_REJECTED} else None,
            "reviewed_by": gap.get("verified_by") or gap.get("reviewed_by"),
            "reviewed_by_name": gap.get("verified_by_name") or gap.get("reviewed_by_name"),
            "reviewed_at": gap.get("verified_at") or gap.get("reviewed_at"),
            "notes": gap.get("admin_notes") or gap.get("notes"),
            "rejection_reason": gap.get("rejection_reason"),
        },
        "allowed_actions": (
            ["reopen_gap"]
            if status == GAP_STATUS_VERIFIED
            else ["verify_gap", "reject_gap", "request_more_info"]
        ),
        "preserved_from_existing_gap": bool(gap.get("preserved_from_existing_gap")),
    }


def _segment_sort_key(segment: Dict[str, Any]) -> Tuple[datetime, int]:
    parsed_start = parse_employment_date(segment.get("start_date"))
    if not parsed_start:
        parsed_start = datetime.max.replace(tzinfo=timezone.utc)
    return parsed_start, 0 if segment.get("type") == "employment" else 1


def _timeline_fingerprint(segments: List[Dict[str, Any]]) -> str:
    fingerprint_payload = []
    for segment in segments:
        item = {
            "type": segment.get("type"),
            "start_date": segment.get("start_date"),
            "end_date": segment.get("end_date"),
        }
        if segment.get("type") == "employment":
            item["organisation"] = segment.get("organisation")
            item["title"] = segment.get("title")
        else:
            item["gap_type"] = segment.get("gap_type")
        fingerprint_payload.append(item)
    encoded = json.dumps(fingerprint_payload, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _build_sign_off(employee: Dict[str, Any], version: int, timeline_fingerprint: str, status_without_signoff: str) -> Dict[str, Any]:
    signed = bool(employee.get("employment_review_signed_off"))
    signed_fingerprint = (
        employee.get("employment_review_signed_timeline_fingerprint")
        or employee.get("employment_review_timeline_fingerprint")
    )
    version_signed = employee.get("employment_review_version_signed") or employee.get("employment_review_signed_version")

    valid_for_current_timeline = (
        signed
        and status_without_signoff == REVIEW_STATUS_AWAITING_ADMIN_REVIEW
        and signed_fingerprint
        and signed_fingerprint == timeline_fingerprint
        and (version_signed is None or int(version_signed) == int(version))
    )

    invalidated = signed and not valid_for_current_timeline
    invalidated_reason = None
    if invalidated:
        if not signed_fingerprint:
            invalidated_reason = "Existing employee-level sign-off is legacy metadata and is not tied to this review timeline."
        elif signed_fingerprint != timeline_fingerprint:
            invalidated_reason = "Employment review timeline has changed since sign-off."
        elif status_without_signoff != REVIEW_STATUS_AWAITING_ADMIN_REVIEW:
            invalidated_reason = "Current review is not eligible for sign-off."
        else:
            invalidated_reason = "Employment review version no longer matches signed version."

    return {
        "signed_off": valid_for_current_timeline,
        "previous_signed_off": signed,
        "version_signed": version_signed if valid_for_current_timeline else None,
        "signed_off_by": employee.get("employment_review_signed_off_by"),
        "signed_off_by_name": employee.get("employment_review_signed_off_by_name"),
        "signed_off_at": employee.get("employment_review_signed_off_at"),
        "decision": "signed_off" if valid_for_current_timeline else None,
        "notes": employee.get("employment_review_signoff_notes"),
        "timeline_fingerprint": timeline_fingerprint if valid_for_current_timeline else None,
        "invalidated": invalidated,
        "invalidated_reason": invalidated_reason,
    }


def _derive_review_status(
    employment_history: List[Dict[str, Any]],
    invalid_entries: List[Dict[str, Any]],
    gap_segments: List[Dict[str, Any]],
) -> Tuple[str, str]:
    if not employment_history:
        return REVIEW_STATUS_NOT_STARTED, "No employment history has been submitted."
    if invalid_entries:
        return REVIEW_STATUS_CANNOT_ASSESS, "One or more employment rows have missing or invalid dates."

    if any(gap.get("status") in {GAP_STATUS_MISSING, GAP_STATUS_REJECTED} for gap in gap_segments):
        return REVIEW_STATUS_IN_PROGRESS, "One or more employment gaps are missing, rejected, or require action."

    if any(gap.get("status") == GAP_STATUS_EXPLAINED for gap in gap_segments):
        return REVIEW_STATUS_AWAITING_ADMIN_REVIEW, "All detected gaps have explanations, but admin verification is still required."

    return REVIEW_STATUS_AWAITING_ADMIN_REVIEW, "The 10-year timeline is ready for final admin sign-off."


def build_employment_review_from_employee(
    employee: dict,
    existing_gap_records: list[dict],
    applicant_explanations: list[dict],
    as_of_date: date | None = None,
) -> dict:
    """
    Build the canonical Employment Review object without database writes.

    The returned object is a preview/foundation payload. It does not make
    ``employment_reviews`` authoritative and does not migrate old fields.
    """
    employee = employee or {}
    employee_id = employee.get("id") or employee.get("employee_id")
    employment_history = employee.get("employment_history") or []
    version = int(employee.get("employment_review_version") or 1)
    as_of_dt = _as_utc_datetime(as_of_date)
    coverage_start = as_of_dt - timedelta(days=365 * 10)

    valid_jobs, invalid_entries = _normalise_employment_history_entries(employment_history)
    detected_gaps = detect_employment_gaps_with_coverage(employment_history, as_of_date=as_of_dt)
    decision_aware_gaps = _overlay_existing_gap_decisions(detected_gaps, existing_gap_records or [])
    explanation_match = match_gap_explanations_to_canonical_gaps(
        decision_aware_gaps,
        applicant_explanations or [],
        explanation_source="application_form",
        apply_to_gaps=True,
    )
    canonical_gaps = explanation_match.get("gaps", [])
    coverage = compute_coverage_summary(employment_history, gap_records=canonical_gaps, as_of_date=as_of_dt)
    gap_evaluation = evaluate_gaps_compliance(canonical_gaps)

    employment_segments = [
        _employment_segment_from_job(job, index)
        for index, job in enumerate(valid_jobs)
    ]
    gap_segments = [
        _gap_segment_from_gap(gap, index)
        for index, gap in enumerate(canonical_gaps)
    ]
    segments = sorted([*employment_segments, *gap_segments], key=_segment_sort_key)
    for order, segment in enumerate(segments, start=1):
        segment["order"] = order

    timeline_fingerprint = _timeline_fingerprint(segments)
    status_without_signoff, status_reason = _derive_review_status(
        employment_history,
        invalid_entries,
        gap_segments,
    )
    sign_off = _build_sign_off(employee, version, timeline_fingerprint, status_without_signoff)
    status_reason_without_signoff = status_reason
    status = REVIEW_STATUS_FULLY_ACCOUNTED if sign_off.get("signed_off") else status_without_signoff
    if status == REVIEW_STATUS_FULLY_ACCOUNTED:
        status_reason = "Employment review was signed off for this review version and timeline."

    top_summary = {
        "employment_segments": len(employment_segments),
        "gap_segments": len(gap_segments),
        "missing_gaps": sum(1 for gap in gap_segments if gap.get("status") == GAP_STATUS_MISSING),
        "explained_gaps": sum(1 for gap in gap_segments if gap.get("status") == GAP_STATUS_EXPLAINED),
        "verified_gaps": sum(1 for gap in gap_segments if gap.get("status") == GAP_STATUS_VERIFIED),
        "rejected_gaps": sum(1 for gap in gap_segments if gap.get("status") == GAP_STATUS_REJECTED),
        "invalid_entries": len(invalid_entries),
        "unmatched_notes": len(explanation_match.get("unmatched_applicant_explanations", [])),
        "coverage_percent": coverage.get("coverage_percent"),
        "coverage_is_informational": True,
    }
    blocked_sign_off_reasons = []
    if status_without_signoff == REVIEW_STATUS_NOT_STARTED:
        blocked_sign_off_reasons.append("No employment history has been submitted")
    if status_without_signoff == REVIEW_STATUS_CANNOT_ASSESS:
        blocked_sign_off_reasons.append("Employment history cannot be assessed from current data")
    if top_summary["missing_gaps"]:
        blocked_sign_off_reasons.append(f"{top_summary['missing_gaps']} gap(s) need explanation")
    if top_summary["explained_gaps"]:
        blocked_sign_off_reasons.append(f"{top_summary['explained_gaps']} gap explanation(s) require admin verification")
    if top_summary["rejected_gaps"]:
        blocked_sign_off_reasons.append(f"{top_summary['rejected_gaps']} gap explanation(s) rejected or need action")

    if sign_off.get("signed_off") and blocked_sign_off_reasons:
        sign_off = {
            **sign_off,
            "signed_off": False,
            "previous_signed_off": True,
            "version_signed": None,
            "decision": None,
            "invalidated": True,
            "invalidated_reason": "Current review still has blockers and cannot remain signed off.",
        }
        status = status_without_signoff
        status_reason = status_reason_without_signoff

    can_sign_off = (
        status_without_signoff == REVIEW_STATUS_AWAITING_ADMIN_REVIEW
        and not sign_off.get("signed_off")
        and not blocked_sign_off_reasons
    )

    return {
        "id": f"employment_review_{employee_id}" if employee_id else None,
        "employee_id": employee_id,
        "application_submission_id": employee.get("application_submission_id"),
        "version": version,
        "status": status,
        "status_label": {
            REVIEW_STATUS_NOT_STARTED: "Not started",
            REVIEW_STATUS_IN_PROGRESS: "In progress",
            REVIEW_STATUS_AWAITING_ADMIN_REVIEW: "Awaiting admin review",
            REVIEW_STATUS_FULLY_ACCOUNTED: "Fully accounted",
            REVIEW_STATUS_CANNOT_ASSESS: "Cannot assess",
        }.get(status, "Cannot assess"),
        "status_reason": status_reason,
        "can_sign_off": can_sign_off,
        "cannot_assess": status_without_signoff == REVIEW_STATUS_CANNOT_ASSESS,
        "review_window": {
            "start_date": coverage_start.strftime("%Y-%m-%d"),
            "end_date": as_of_dt.strftime("%Y-%m-%d"),
            "years": 10,
        },
        "top_summary": top_summary,
        "coverage": {
            **coverage,
            "percent": coverage.get("coverage_percent"),
            "accounted_days": coverage.get("total_days_covered"),
            "required_days": coverage.get("total_days_required"),
            "unaccounted_days": max(
                (coverage.get("total_days_required") or 0) - (coverage.get("total_days_covered") or 0),
                0,
            ),
            "informational_only": True,
            "message": "Coverage percentage is informational. Final compliance depends on each gap being reviewed and verified.",
        },
        "segments": segments,
        "gap_actions": {
            "can_rerun_analysis": bool(employment_history),
            "can_edit_history": True,
            "can_sign_off": can_sign_off,
            "blocked_sign_off_reasons": blocked_sign_off_reasons,
        },
        "sign_off": sign_off,
        "unmatched_applicant_notes": explanation_match.get("unmatched_applicant_explanations", []),
        "invalid_entries": invalid_entries,
        "diagnostics": {
            "analysis_status": "cannot_assess" if invalid_entries else "completed",
            "analysis_error": "One or more employment rows have missing or invalid dates." if invalid_entries else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "timeline_fingerprint": timeline_fingerprint,
            "gap_evaluation": gap_evaluation,
            "explanation_match_summary": explanation_match.get("explanation_match_summary", {}),
        },
    }
