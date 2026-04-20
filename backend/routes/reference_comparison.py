"""
Reference-Employment Comparison Routes.

This module handles:
- Comparing declared references against employment history
- Detecting mismatches for CQC compliance (Medway QA finding)
"""

import re
from fastapi import APIRouter, HTTPException, Depends

from .dependencies import get_db, get_current_user

router = APIRouter(tags=["Reference Comparison"])

# Common suffixes (order matters — strip longest first)
_EMPLOYER_SUFFIXES = [
    "nhs foundation trust", "foundation trust", "nhs trust", "community health",
    "healthcare services", "health care services", "healthcare", "health care",
    "support services", "care home", "limited liability partnership", "limited liability",
    "llp", "ltd", "limited", "plc", "inc", "llc", "group", "trust", "foundation",
]

def _normalize_employer(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, remove common suffixes."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    for suffix in _EMPLOYER_SUFFIXES:
        if name.endswith(f" {suffix}"):
            name = name[: -(len(suffix) + 1)].strip()
            break
    return name


def _match_employers(ref_company: str, employment_history: list) -> tuple[bool, object | None, str]:
    """
    Returns (matched, matching_employer_dict, match_reason).
    Tries three strategies in order:
      1. Exact normalized match
      2. Substring containment  on normalized names
      3. Suffix-stripped substring match
    """
    ref_norm = _normalize_employer(ref_company)
    if not ref_norm:
        return False, None, ""

    for emp in employment_history:
        emp_name = emp.get("employer_name") or ""
        emp_norm = _normalize_employer(emp_name)
        if not emp_norm:
            continue

        if ref_norm == emp_norm:
            return True, emp, "exact"

        if ref_norm in emp_norm or emp_norm in ref_norm:
            return True, emp, "substring"

    # Suffix-stripped pass
    ref_stripped = ref_norm
    for suffix in _EMPLOYER_SUFFIXES:
        if ref_stripped.endswith(f" {suffix}"):
            ref_stripped = ref_stripped[: -(len(suffix) + 1)].strip()
            break

    if ref_stripped and ref_stripped != ref_norm:
        for emp in employment_history:
            emp_stripped = _normalize_employer(emp.get("employer_name") or "")
            for suffix in _EMPLOYER_SUFFIXES:
                if emp_stripped.endswith(f" {suffix}"):
                    emp_stripped = emp_stripped[: -(len(suffix) + 1)].strip()
                    break
            if emp_stripped and (ref_stripped in emp_stripped or emp_stripped in ref_stripped):
                return True, emp, "suffix_stripped"

    return False, None, ""


@router.get("/employees/{employee_id}/reference-employment-comparison")
async def get_reference_employment_comparison(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Compare declared references against employment history.
    Addresses Medway QA finding: "references neither appear to match references given in application form"
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Collect employment history from three sources (most authoritative first)
    employment_history = []

    def _add_emp(employer_name, position, start_date, end_date, is_current, source):
        if not employer_name:
            return
        norm = _normalize_employer(employer_name)
        if not norm:
            return
        if any(_normalize_employer(e["employer_name"]) == norm for e in employment_history):
            return  # dedup
        employment_history.append({
            "employer_name": employer_name,
            "position": position or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
            "is_current": bool(is_current),
            "source": source,
        })

    # Source 1: direct employee.employment_history field (most complete)
    direct_hist = employee.get("employment_history") or []
    if isinstance(direct_hist, list):
        for emp in direct_hist:
            if isinstance(emp, dict):
                _add_emp(
                    emp.get("employer_name") or emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                    emp.get("position") or emp.get("job_title") or emp.get("role") or "",
                    emp.get("start_date") or emp.get("from") or "",
                    emp.get("end_date") or emp.get("to") or "",
                    emp.get("is_current") or emp.get("current") or False,
                    "profile",
                )

    # Source 2: form_submissions (application form)
    application = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "form_type": {"$in": ["application_form", "application", "public_application"]}
    }, {"_id": 0, "data": 1, "form_data": 1})
    
    if application:
        app_data = application.get("data") or application.get("form_data") or {}
        emp_hist = app_data.get("employment_history") or app_data.get("employmentHistory") or []
        if isinstance(emp_hist, list):
            for emp in emp_hist:
                if isinstance(emp, dict):
                    _add_emp(
                        emp.get("employer_name") or emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                        emp.get("position") or emp.get("job_title") or emp.get("role") or "",
                        emp.get("start_date") or emp.get("from") or "",
                        emp.get("end_date") or emp.get("to") or "",
                        emp.get("is_current") or emp.get("current") or False,
                        "application",
                    )

    # Source 3: CV extraction
    cv_data = employee.get("cv_extraction") or employee.get("extracted_cv_data") or {}
    cv_employment = cv_data.get("employment_history") or cv_data.get("work_experience") or []
    if isinstance(cv_employment, list):
        for emp in cv_employment:
            if isinstance(emp, dict):
                _add_emp(
                    emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                    emp.get("position") or emp.get("title") or emp.get("role") or "",
                    emp.get("start_date") or "",
                    emp.get("end_date") or "",
                    emp.get("is_current") or False,
                    "cv",
                )

    # Get declared references
    references = []
    for ref_num in [1, 2]:
        ref_prefix = f"reference_{ref_num}"
        declared = {
            "reference_num": ref_num,
            "name": employee.get(f"{ref_prefix}_name") or "",
            "company": employee.get(f"{ref_prefix}_company") or "",
            "organisation": employee.get(f"{ref_prefix}_company") or "",  # alias for frontend
            "email": employee.get(f"{ref_prefix}_email") or "",
            "phone": employee.get(f"{ref_prefix}_phone") or "",
            "relationship": employee.get(f"{ref_prefix}_relationship") or "",
            "from_cv": employee.get(f"{ref_prefix}_from_cv") or False,
            "override_reason": employee.get(f"{ref_prefix}_override_reason") or None,
        }

        ref_company = declared["company"]
        matches_employment, matching_employer, match_reason = _match_employers(ref_company, employment_history)

        declared["matches_employment_history"] = matches_employment
        declared["matching_employer"] = matching_employer
        declared["match_reason"] = match_reason

        if declared["name"] or declared["company"]:
            references.append(declared)
    
    # Calculate summary
    unmatched_count = sum(1 for r in references if not r["matches_employment_history"] and not r.get("override_reason"))
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employment_history": employment_history,
        "references": references,
        "comparison_summary": {
            "employment_history_count": len(employment_history),
            "total_references_declared": len(references),
            "references_matching_employment": sum(1 for r in references if r["matches_employment_history"]),
            "unmatched_references": unmatched_count,
            "has_discrepancy": unmatched_count > 0,
        },
        "alert": {
            "show": unmatched_count > 0,
            "level": "warning",
            "message": f"{unmatched_count} reference(s) do not match declared employment history - verify before approving"
        },
    }
