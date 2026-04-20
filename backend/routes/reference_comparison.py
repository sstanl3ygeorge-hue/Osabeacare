"""
Reference-Employment Comparison Routes.

This module handles:
- Comparing declared references against employment history
- Detecting mismatches for CQC / NHS-compliant recruitment checks.

Compliance model (aligned with NHS reference guidance):
  - ok      : reference matched to most recent employer
  - warning : reference matched to an earlier (not most recent) employer —
              must be investigated but is NOT an automatic failure
  - alert   : reference does not match any declared employer —
              must be investigated before approval
"""

import re
from fastapi import APIRouter, HTTPException, Depends

from .dependencies import get_db, get_current_user
from reference_matching import (
    normalize_employer as _normalize_employer,
    strip_employer_suffix as _strip_suffix,
    match_employers as _match_employers,
    identify_most_recent_employer as _identify_most_recent_employer,
    compliance_status_for_match,
    EMPLOYER_SUFFIXES as _EMPLOYER_SUFFIXES,
)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/employees/{employee_id}/reference-employment-comparison")
async def get_reference_employment_comparison(
    employee_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Compare declared references against employment history.

    Addresses Medway QA finding:
    "references neither appear to match references given in application form"

    Response contract (always present — frontend must never crash):
    {
      "employee_id": str,
      "employee_name": str,
      "employment_history": [...],
      "references": [
        {
          "reference_num": int,
          "name": str,
          "company": str,
          "organisation": str,
          "matches_employment_history": bool,
          "matching_employer": dict | null,
          "match_reason": "exact"|"substring"|"normalized"|"none",
          "is_most_recent_employer": bool,
          "compliance_status": "ok"|"warning"|"alert",
          ...
        }
      ],
      "comparison_summary": {
        "employment_history_count": int,
        "total_references_declared": int,
        "matched_references": int,
        "unmatched_references": int,
        "warning_references": int,
        "has_discrepancy": bool,
        "highest_severity": "ok"|"warning"|"alert"
      },
      "alert": { "show": bool, "level": str, "message": str }
    }
    """
    db = get_db()

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # ------------------------------------------------------------------
    # Collect employment history — three sources, most authoritative first
    # ------------------------------------------------------------------
    employment_history: list[dict] = []

    def _add_emp(employer_name, position, start_date, end_date, is_current, source):
        if not employer_name:
            return
        norm = _normalize_employer(employer_name)
        if not norm:
            return
        # Deduplicate on normalised name
        if any(_normalize_employer(e["employer_name"]) == norm for e in employment_history):
            return
        employment_history.append({
            "employer_name": employer_name,
            "position": position or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
            "is_current": bool(is_current),
            "source": source,
        })

    # Source 1 — direct employee.employment_history (richest / most recent save)
    for emp in (employee.get("employment_history") or []):
        if isinstance(emp, dict):
            _add_emp(
                emp.get("employer_name") or emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                emp.get("position") or emp.get("job_title") or emp.get("role") or "",
                emp.get("start_date") or emp.get("from") or "",
                emp.get("end_date") or emp.get("to") or "",
                emp.get("is_current") or emp.get("current") or False,
                "profile",
            )

    # Source 2 — application form_submission
    application = await db.form_submissions.find_one(
        {
            "employee_id": employee_id,
            "form_type": {"$in": ["application_form", "application", "public_application"]},
        },
        {"_id": 0, "data": 1, "form_data": 1},
    )
    if application:
        app_data = application.get("data") or application.get("form_data") or {}
        for emp in (app_data.get("employment_history") or app_data.get("employmentHistory") or []):
            if isinstance(emp, dict):
                _add_emp(
                    emp.get("employer_name") or emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                    emp.get("position") or emp.get("job_title") or emp.get("role") or "",
                    emp.get("start_date") or emp.get("from") or "",
                    emp.get("end_date") or emp.get("to") or "",
                    emp.get("is_current") or emp.get("current") or False,
                    "application",
                )

    # Source 3 — CV extraction
    cv_data = employee.get("cv_extraction") or employee.get("extracted_cv_data") or {}
    for emp in (cv_data.get("employment_history") or cv_data.get("work_experience") or []):
        if isinstance(emp, dict):
            _add_emp(
                emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                emp.get("position") or emp.get("title") or emp.get("role") or "",
                emp.get("start_date") or "",
                emp.get("end_date") or "",
                emp.get("is_current") or False,
                "cv",
            )

    # ------------------------------------------------------------------
    # Identify the most-recent employer (used for NHS compliance grading)
    # ------------------------------------------------------------------
    most_recent_norm = _identify_most_recent_employer(employment_history)

    # ------------------------------------------------------------------
    # Build reference comparison entries
    # ------------------------------------------------------------------
    references: list[dict] = []

    for ref_num in [1, 2]:
        ref_prefix = f"reference_{ref_num}"
        ref_company = employee.get(f"{ref_prefix}_company") or ""

        declared: dict = {
            "reference_num": ref_num,
            "name": employee.get(f"{ref_prefix}_name") or "",
            "company": ref_company,
            "organisation": ref_company,          # alias — frontend reads this field
            "email": employee.get(f"{ref_prefix}_email") or "",
            "phone": employee.get(f"{ref_prefix}_phone") or "",
            "relationship": employee.get(f"{ref_prefix}_relationship") or "",
            "from_cv": bool(employee.get(f"{ref_prefix}_from_cv")),
            "override_reason": employee.get(f"{ref_prefix}_override_reason") or None,
        }

        # Skip entirely-blank slots (no name AND no company)
        if not declared["name"] and not declared["company"]:
            continue

        matched, matching_employer, match_reason = _match_employers(ref_company, employment_history)

        # Is this the most-recent employer?
        is_most_recent = False
        if matched and matching_employer and most_recent_norm:
            emp_norm = _normalize_employer(matching_employer.get("employer_name") or "")
            is_most_recent = (emp_norm == most_recent_norm)

        # CQC compliance grade — shared logic (same as stageGates.py)
        compliance_status = compliance_status_for_match(
            matched=matched,
            matching_employer=matching_employer,
            is_most_recent=is_most_recent,
            override_reason=declared["override_reason"],
        )

        declared.update({
            "matches_employment_history": matched,
            "matching_employer": matching_employer,
            "match_reason": match_reason,
            "is_most_recent_employer": is_most_recent,
            "compliance_status": compliance_status,
        })

        references.append(declared)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    matched_count = sum(1 for r in references if r["matches_employment_history"])
    unmatched_count = len(references) - matched_count
    warning_count = sum(1 for r in references if r["compliance_status"] == "warning")
    alert_count = sum(1 for r in references if r["compliance_status"] == "alert")

    if alert_count > 0:
        highest_severity = "alert"
        has_discrepancy = True
    elif warning_count > 0:
        highest_severity = "warning"
        has_discrepancy = True
    else:
        highest_severity = "ok"
        has_discrepancy = False

    # Alert banner message
    if alert_count > 0:
        alert_level = "alert"
        alert_msg = (
            f"{alert_count} reference(s) could not be matched to any declared employer — "
            "investigation required before approval"
        )
    elif warning_count > 0:
        alert_level = "warning"
        alert_msg = (
            f"{warning_count} reference(s) match an earlier employer (not the most recent) — "
            "verify and record explanation per NHS guidance"
        )
    else:
        alert_level = "ok"
        alert_msg = ""

    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employment_history": employment_history,
        "references": references,
        "comparison_summary": {
            "employment_history_count": len(employment_history),
            "total_references_declared": len(references),
            "matched_references": matched_count,
            "unmatched_references": unmatched_count,
            "warning_references": warning_count,
            "has_discrepancy": has_discrepancy,
            "highest_severity": highest_severity,
        },
        "alert": {
            "show": has_discrepancy,
            "level": alert_level,
            "message": alert_msg,
        },
    }
