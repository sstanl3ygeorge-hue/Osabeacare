"""
Reference-Employment Comparison Routes.

This module handles:
- Comparing declared references against employment history
- Detecting mismatches for CQC compliance (Medway QA finding)
"""

from fastapi import APIRouter, HTTPException, Depends

from .dependencies import get_db, get_current_user

router = APIRouter(tags=["Reference Comparison"])


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
    
    # Get employment history from application or CV extraction
    employment_history = []
    
    # Try to get from form_submissions (application form)
    application = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "form_type": {"$in": ["application_form", "application", "public_application"]}
    }, {"_id": 0, "data": 1, "form_data": 1})
    
    if application:
        app_data = application.get("data") or application.get("form_data") or {}
        
        # Extract employment history - try various structures
        emp_hist = app_data.get("employment_history") or app_data.get("employmentHistory") or []
        if isinstance(emp_hist, list):
            for emp in emp_hist:
                if isinstance(emp, dict):
                    employment_history.append({
                        "employer_name": emp.get("employer_name") or emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                        "position": emp.get("position") or emp.get("job_title") or emp.get("role") or "",
                        "start_date": emp.get("start_date") or emp.get("from") or "",
                        "end_date": emp.get("end_date") or emp.get("to") or "",
                        "is_current": emp.get("is_current") or emp.get("current") or False
                    })
    
    # Also check CV extraction data
    cv_data = employee.get("cv_extraction") or employee.get("extracted_cv_data") or {}
    cv_employment = cv_data.get("employment_history") or cv_data.get("work_experience") or []
    if isinstance(cv_employment, list):
        for emp in cv_employment:
            if isinstance(emp, dict):
                # Avoid duplicates
                employer = emp.get("employer") or emp.get("company") or emp.get("organisation") or ""
                if employer and not any(e["employer_name"].lower() == employer.lower() for e in employment_history):
                    employment_history.append({
                        "employer_name": employer,
                        "position": emp.get("position") or emp.get("title") or emp.get("role") or "",
                        "start_date": emp.get("start_date") or "",
                        "end_date": emp.get("end_date") or "",
                        "is_current": emp.get("is_current") or False
                    })
    
    # Get declared references
    references = []
    for ref_num in [1, 2]:
        ref_prefix = f"reference_{ref_num}"
        declared = {
            "reference_num": ref_num,
            "name": employee.get(f"{ref_prefix}_name") or "",
            "company": employee.get(f"{ref_prefix}_company") or "",
            "email": employee.get(f"{ref_prefix}_email") or "",
            "phone": employee.get(f"{ref_prefix}_phone") or "",
            "relationship": employee.get(f"{ref_prefix}_relationship") or "",
            "from_cv": employee.get(f"{ref_prefix}_from_cv") or False,
            "override_reason": employee.get(f"{ref_prefix}_override_reason") or None
        }
        
        # Check if reference company appears in employment history
        ref_company = (declared["company"] or "").lower().strip()
        matches_employment = False
        matching_employer = None
        
        if ref_company:
            for emp in employment_history:
                emp_name = (emp["employer_name"] or "").lower().strip()
                # Fuzzy match - check if one contains the other
                if emp_name and (ref_company in emp_name or emp_name in ref_company):
                    matches_employment = True
                    matching_employer = emp
                    break
        
        declared["matches_employment_history"] = matches_employment
        declared["matching_employer"] = matching_employer
        
        if declared["name"] or declared["company"]:
            references.append(declared)
    
    # Calculate summary
    unmatched_count = sum(1 for r in references if not r["matches_employment_history"] and not r.get("override_reason"))
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employment_history": employment_history,
        "references": references,
        "summary": {
            "employment_history_count": len(employment_history),
            "references_declared": len(references),
            "references_matching_employment": sum(1 for r in references if r["matches_employment_history"]),
            "unmatched_references": unmatched_count,
            "has_discrepancy": unmatched_count > 0
        },
        "alert": {
            "show": unmatched_count > 0,
            "level": "warning",
            "message": f"{unmatched_count} reference(s) do not match declared employment history - verify before approving"
        }
    }
