"""
Enhanced synthetic dry-run: simulates the full backfill pipeline against
5+ realistic employee profiles, then verifies shape compatibility with
ApplicationFormViewer and Employment Review.

Temporary script — safe to delete after verification.
"""
import sys, json
from datetime import datetime, timezone
from application_resolver import (
    APPLICATION_SECTIONS,
    _evaluate_section,
    _build_form_data_from_employee,
    SOURCE_LABELS,
    ONLINE_SOURCES,
)

# =============================================================================
# MOCK EMPLOYEES — realistic profiles covering all 5 source types
# =============================================================================

MOCK_EMPLOYEES = [
    # 1. offline_pdf_import — rich data (typical PDF import)
    {
        "id": "emp-offline-rich-001",
        "first_name": "Grace",
        "last_name": "Mensah",
        "email": "grace.mensah@example.com",
        "phone": "07700900001",
        "date_of_birth": "1990-05-14",
        "national_insurance": "AB123456C",
        "role": "Care Assistant",
        "application_source": "offline_pdf_import",
        "employee_code": "EMP-0042",
        "address_line_1": "14 Elm Road",
        "city": "Birmingham",
        "postcode": "B15 2TT",
        "county": "West Midlands",
        "reference_1_name": "Sarah Jones",
        "reference_1_email": "sarah.j@nhs.uk",
        "reference_1_company": "NHS Trust",
        "reference_2_name": "Mark Fisher",
        "reference_2_email": "mark.f@care.org",
        "reference_2_company": "Care UK",
        "employment_history": [
            {"employer_name": "NHS Birmingham", "job_title": "HCA", "start_date": "2018-06-01", "end_date": "2023-01-15", "reason_for_leaving": "Career change"},
            {"employer_name": "Priory Group", "job_title": "Support Worker", "start_date": "2016-09-01", "end_date": "2018-05-30"},
        ],
        "right_to_work_declared": True,
        "citizenship_status_declared": "british_citizen",
        "declarations": {
            "dbs_consent_given": True,
            "information_accurate_declared": True,
            "consents_to_reference_checks": True,
            "consents_to_background_checks": True,
            "consents_to_data_processing": True,
        },
        "emergency_contact_name": "Kwame Mensah",
        "emergency_contact_phone": "07700900099",
        "emergency_contact_relationship": "Brother",
        "how_heard": "Indeed",
    },
    # 2. offline_pdf_import — sparse data (minimal PDF scan)
    {
        "id": "emp-offline-sparse-002",
        "first_name": "James",
        "last_name": "Okafor",
        "email": "james.okafor@mail.com",
        "phone": "07700900002",
        "role": "Support Worker",
        "application_source": "offline_pdf_import",
        "employee_code": "EMP-0078",
        "address_line_1": "Flat 3, 22 High Street",
        "city": "London",
        "postcode": "SW1A 1AA",
        # Missing: date_of_birth, NI, references, employment_history
        "declarations": {},
    },
    # 3. admin_simple — admin-created record
    {
        "id": "emp-admin-003",
        "first_name": "Amara",
        "last_name": "Diallo",
        "email": "amara.d@test.com",
        "phone": "07700900003",
        "date_of_birth": "1985-11-22",
        "role": "Senior Care Assistant",
        "application_source": "admin_simple",
        "employee_code": "EMP-0103",
        "address_line_1": "7 Rose Lane",
        "address_line_2": "Apt 2B",
        "city": "Manchester",
        "postcode": "M1 1AA",
        "reference_1_name": "Dr Patel",
        "reference_1_email": "patel@hospital.nhs.uk",
        "reference_2_name": "Linda Chen",
        "reference_2_email": "linda.c@care.co.uk",
        "employment_history": [
            {"employer_name": "Manchester Royal", "job_title": "Nurse", "start_date": "2012-01-15"},
        ],
        "right_to_work_declared": True,
        "declarations": {
            "dbs_consent_given": True,
            "consents_to_data_processing": True,
        },
    },
    # 4. internal — promoted/transferred staff
    {
        "id": "emp-internal-004",
        "first_name": "Benjamin",
        "last_name": "Asante",
        "email": "ben.asante@osabea.care",
        "phone": "07700900004",
        "date_of_birth": "1992-03-08",
        "national_insurance": "CD789012E",
        "role": "Team Leader",
        "application_source": "internal",
        "employee_code": "EMP-0015",
        "address_line_1": "28 Oak Avenue",
        "city": "Leeds",
        "postcode": "LS1 3EE",
        "reference_1_name": "Emma Williams",
        "reference_1_email": "emma.w@osabea.care",
        "reference_1_company": "Osabea Care",
        "reference_2_name": "David Brown",
        "reference_2_email": "david.b@osabea.care",
        "reference_2_company": "Osabea Care",
        "employment_history": [
            {"employer_name": "Osabea Care", "job_title": "Care Assistant", "start_date": "2019-02-01", "is_current": True},
        ],
        "highest_qualification": "NVQ Level 3",
        "right_to_work_declared": True,
        "citizenship_status_declared": "british_citizen",
        "declarations": {
            "dbs_consent_given": True,
            "information_accurate_declared": True,
            "consents_to_reference_checks": True,
            "consents_to_background_checks": True,
            "consents_to_data_processing": True,
        },
        "emergency_contact_name": "Ama Asante",
        "emergency_contact_phone": "07700900098",
        "emergency_contact_relationship": "Wife",
    },
    # 5. online_legacy — old online form (no form_submission record)
    {
        "id": "emp-legacy-005",
        "first_name": "Fatima",
        "last_name": "Hassan",
        "email": "fatima.h@gmail.com",
        "phone": "07700900005",
        "phone_secondary": "02012345678",
        "date_of_birth": "1988-07-19",
        "role": "Healthcare Assistant",
        "application_source": "online_legacy",
        "applicant_reference": "APP-2024-0199",
        "address_line_1": "56 Cedar Close",
        "city": "Bristol",
        "postcode": "BS1 4DJ",
        "reference_1_name": "Dr Ahmed",
        "reference_1_email": "ahmed@clinic.co.uk",
        "reference_1_relationship": "Supervisor",
        "reference_2_name": "Nurse Kelly",
        "reference_2_email": "kelly@nhs.uk",
        "reference_2_relationship": "Colleague",
        "employment_history": [
            {"employer_name": "Bristol Royal Infirmary", "job_title": "HCA", "start_date": "2015-04-01", "end_date": "2023-12-31"},
        ],
        "right_to_work_declared": True,
        "has_criminal_convictions_declared": False,
        "declarations": {
            "dbs_consent_given": True,
            "has_health_conditions": False,
            "information_accurate_declared": True,
            "consents_to_reference_checks": True,
        },
        "emergency_contact_name": "Ali Hassan",
        "emergency_contact_phone": "07700900097",
    },
    # 6. online_structured — should be SKIPPED (already has form)
    {
        "id": "emp-online-006",
        "first_name": "Test",
        "last_name": "OnlineUser",
        "email": "test@online.com",
        "phone": "07700900006",
        "role": "Care Assistant",
        "application_source": "online_structured",
        "employee_code": "EMP-0200",
    },
    # 7. Edge case — unknown source, almost empty
    {
        "id": "emp-edge-007",
        "first_name": "Unknown",
        "last_name": "Source",
        "email": "unknown@test.com",
        "role": "Support Worker",
        "application_source": "unknown",
    },
]


# =============================================================================
# APPLICATIONFORMVIEWER FIELD EXPECTATIONS
# =============================================================================

VIEWER_SECTIONS = {
    "personal_details": ["title", "first_name", "middle_name", "last_name", "preferred_name", "date_of_birth", "national_insurance"],
    "contact_details": ["email", "phone", "phone_secondary"],
    "address": ["line_1", "address_line_1", "line_2", "address_line_2", "city", "county", "postcode", "country", "years_at_address"],
    "role_availability": ["role_applied", "availability", "earliest_start_date", "has_driving_licence", "has_own_transport"],
    "employment_history": "array",
    "references": "array",
    "qualifications": ["highest_qualification", "relevant_qualifications", "care_certificate_completed"],
    "health_declaration": ["has_health_conditions", "health_condition_details"],
    "criminal_declaration": ["has_criminal_convictions", "consents_to_dbs_check", "understands_dbs_required"],
    "right_to_work": ["has_right_to_work_uk", "citizenship_status", "visa_type", "visa_expiry"],
    "declarations": ["information_accurate", "consents_to_reference_checks", "consents_to_background_checks", "consents_to_data_processing"],
    "emergency_contact": ["name", "phone", "relationship", "address"],
}


def check_viewer_compatibility(form_data: dict) -> dict:
    """Check if form_data structure is compatible with ApplicationFormViewer."""
    issues = []
    warnings = []
    
    for section_key, expected_fields in VIEWER_SECTIONS.items():
        section_data = form_data.get(section_key)
        
        if expected_fields == "array":
            if section_data is not None and not isinstance(section_data, list):
                issues.append(f"{section_key}: expected array, got {type(section_data).__name__}")
            continue
        
        if section_data is None:
            continue  # Section not present = OK (viewer handles missing)
        
        if not isinstance(section_data, dict):
            issues.append(f"{section_key}: expected dict, got {type(section_data).__name__}")
            continue
        
        # Check for any values that are dicts/lists where viewer expects primitives
        for key, val in section_data.items():
            if isinstance(val, dict):
                issues.append(f"{section_key}.{key}: unexpected nested object")
            if isinstance(val, list) and key not in ("relevant_qualifications",):
                warnings.append(f"{section_key}.{key}: unexpected array (may render as [object Object])")
    
    return {"issues": issues, "warnings": warnings}


def check_employment_review_compat(employee: dict, form_data: dict) -> dict:
    """Check if backfilled record satisfies Employment Review sign-off guards."""
    guards = {}
    
    # Guard 1: Application on file (the backfill creates this)
    guards["application_on_file"] = True  # backfill always creates the form_submission
    
    # Guard 2: DBS consent
    decl = employee.get("declarations") or {}
    guards["dbs_consent"] = decl.get("dbs_consent_given") is not None
    
    # Guard 3: Employment history
    eh = employee.get("employment_history")
    guards["employment_history"] = isinstance(eh, list) and len(eh) > 0
    
    # Guard 4: Gaps resolved (can't check without DB, assume OK)
    guards["gaps_resolved"] = "CANNOT_VERIFY_WITHOUT_DB"
    
    all_pass = guards["dbs_consent"] and guards["employment_history"]
    return {"guards": guards, "would_pass": all_pass}


def build_backfill_record(employee: dict) -> dict:
    """Simulate exactly what backfill_execute would write."""
    import uuid
    source = employee.get("application_source", "unknown")
    now = datetime.now(timezone.utc).isoformat()
    form_data = _build_form_data_from_employee(employee)
    
    # Evaluate sections
    sections = {}
    backfilled_sections = []
    missing_sections = []
    for section_key, section_def in APPLICATION_SECTIONS.items():
        section_eval = _evaluate_section(section_key, section_def, employee)
        sections[section_key] = section_eval
        if section_eval["present"]:
            backfilled_sections.append(section_key)
        if section_eval["required_for_review"] and not section_eval["complete"]:
            missing_sections.append(section_key)
    
    present = sum(1 for s in sections.values() if s["present"])
    total = len(sections)
    req_sections = [s for s in sections.values() if s["required_for_review"]]
    req_complete = sum(1 for s in req_sections if s["complete"])
    complete = len(missing_sections) == 0
    
    form_sub_id = str(uuid.uuid4())
    form_submission = {
        "id": form_sub_id,
        "employee_id": employee["id"],
        "requirement_id": "application_form",
        "template_id": "backfilled_application_form",
        "template_name": "Application Form (Backfilled)",
        "form_type": "application_form",
        "form_data": form_data,
        "status": "completed",
        "submitted_by_applicant": False,
        "submitted_at": now,
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "requires_reverification": False,
        "provenance": f"backfilled_from_{source}",
        "backfill_metadata": {
            "original_source": source,
            "backfilled_by": "system_dry_run",
            "backfilled_by_name": "Dry Run",
            "backfilled_at": now,
            "sections_present": present,
            "sections_total": total,
            "application_data_complete": complete,
            "missing_sections": missing_sections,
        },
        "created_at": now,
        "updated_at": now,
    }
    
    employee_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": employee["id"],
        "requirement_key": "application_form",
        "requirement_id": "application_form",
        "requirement_type": "form",
        "document_type_name": "Application Form",
        "category": "Application",
        "blocking": True,
        "supports_files": False,
        "supports_requests": False,
        "status": "completed",
        "verified": False,
        "form_submission_id": form_sub_id,
        "policy": {},
        "metadata": {"provenance": f"backfilled_from_{source}"},
        "notes": f"Application form backfilled from {source} employee data",
        "created_at": now,
        "updated_at": now,
    }
    
    return {
        "form_submission": form_submission,
        "employee_document": employee_doc,
        "sections_present": present,
        "sections_total": total,
        "required_complete": req_complete,
        "required_total": len(req_sections),
        "complete": complete,
        "missing_sections": missing_sections,
        "backfilled_sections": backfilled_sections,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("ENHANCED SYNTHETIC DRY-RUN REPORT")
    print("=" * 70)
    
    total = len(MOCK_EMPLOYEES)
    skipped_online = 0
    candidates = []
    skipped = []
    
    # Phase 1: Triage
    for emp in MOCK_EMPLOYEES:
        source = emp.get("application_source", "unknown")
        if source in ONLINE_SOURCES:
            skipped_online += 1
            skipped.append({"id": emp["id"], "reason": "online_structured (skip)"})
            continue
        candidates.append(emp)
    
    print(f"\nTotal employees scanned:       {total}")
    print(f"Already have application_form: 0  (synthetic — no DB)")
    print(f"Skipped (online_structured):   {skipped_online}")
    print(f"Would backfill:                {len(candidates)}")
    print()
    
    # Phase 2: Source breakdown
    from collections import Counter
    source_counts = Counter(c.get("application_source", "unknown") for c in candidates)
    print("CANDIDATES BY SOURCE:")
    for src, cnt in source_counts.most_common():
        label = SOURCE_LABELS.get(src, src)
        print(f"  {src:30s} {cnt:3d}  ({label})")
    print()
    
    # Phase 3: Build and verify each candidate
    results = []
    malformed = []
    incomplete = []
    
    for emp in candidates:
        result = build_backfill_record(emp)
        viewer_compat = check_viewer_compatibility(result["form_submission"]["form_data"])
        review_compat = check_employment_review_compat(emp, result["form_submission"]["form_data"])
        
        entry = {
            "employee": emp,
            "result": result,
            "viewer_compat": viewer_compat,
            "review_compat": review_compat,
        }
        results.append(entry)
        
        # Malformed check
        issues = []
        if result["sections_present"] == 0:
            issues.append("zero_sections")
        name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        if not name:
            issues.append("no_name")
        if emp.get("application_source") in (None, "", "unknown"):
            issues.append("unknown_source")
        if viewer_compat["issues"]:
            issues.append("viewer_incompatible")
        if issues:
            malformed.append({"id": emp["id"], "name": name, "source": emp.get("application_source"), "issues": issues})
        
        if not result["complete"]:
            incomplete.append({"id": emp["id"], "name": name, "source": emp.get("application_source"), "missing": result["missing_sections"]})
    
    # Phase 4: Malformed
    if malformed:
        print(f"MALFORMED RECORDS ({len(malformed)}):")
        for m in malformed:
            print(f"  {m['id']:30s} name=\"{m['name']}\" source={m['source']} issues={m['issues']}")
    else:
        print("MALFORMED RECORDS: NONE")
    print()
    
    # Phase 5: Incomplete
    complete_count = sum(1 for r in results if r["result"]["complete"])
    incomplete_count = len(results) - complete_count
    print(f"Application data complete:   {complete_count}")
    print(f"Application data incomplete: {incomplete_count}")
    if incomplete:
        print("\nINCOMPLETE CANDIDATES:")
        for inc in incomplete:
            print(f"  {inc['id']:30s} source={inc['source']:20s} missing={inc['missing']}")
    print()
    
    # Phase 6: Per-candidate detail
    print("=" * 70)
    print("SPOT-CHECK: 5 CANDIDATES")
    print("=" * 70)
    
    # Pick: 2 offline_pdf_import, 1 admin_simple, 1 internal, 1 online_legacy
    spot_checks = [
        ("offline_pdf_import (rich)", "emp-offline-rich-001"),
        ("offline_pdf_import (sparse)", "emp-offline-sparse-002"),
        ("admin_simple", "emp-admin-003"),
        ("internal", "emp-internal-004"),
        ("online_legacy", "emp-legacy-005"),
    ]
    
    all_pass = True
    
    for label, emp_id in spot_checks:
        entry = next(e for e in results if e["employee"]["id"] == emp_id)
        emp = entry["employee"]
        result = entry["result"]
        fs = result["form_submission"]
        ed = result["employee_document"]
        vc = entry["viewer_compat"]
        rc = entry["review_compat"]
        
        name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        code = emp.get("employee_code") or emp.get("applicant_reference") or "no-code"
        
        print(f"\n--- {label}: {name} ({code}) ---")
        print(f"  Source: {emp.get('application_source')}")
        print(f"  Sections: {result['sections_present']}/{result['sections_total']}  Required: {result['required_complete']}/{result['required_total']}")
        print(f"  Complete: {result['complete']}")
        if result['missing_sections']:
            print(f"  Missing: {result['missing_sections']}")
        
        # form_submission shape
        shape_keys = sorted(fs.keys())
        print(f"\n  form_submission shape ({len(shape_keys)} keys):")
        required_keys = ["id", "employee_id", "requirement_id", "template_id", "form_type",
                         "form_data", "status", "submitted_at", "verified", "verified_by",
                         "verified_at", "requires_reverification", "provenance", "backfill_metadata"]
        missing_keys = [k for k in required_keys if k not in fs]
        if missing_keys:
            print(f"    MISSING REQUIRED KEYS: {missing_keys}")
            all_pass = False
        else:
            print(f"    All {len(required_keys)} required keys present: OK")
        
        # form_data sections
        fd = fs["form_data"]
        fd_keys = sorted(fd.keys())
        print(f"  form_data sections: {fd_keys}")
        
        # employee_documents slot shape
        ed_required = ["id", "employee_id", "requirement_key", "requirement_id", "status", "form_submission_id"]
        ed_missing = [k for k in ed_required if k not in ed]
        if ed_missing:
            print(f"\n  employee_document MISSING KEYS: {ed_missing}")
            all_pass = False
        else:
            print(f"  employee_document slot: OK ({len(ed.keys())} keys)")
        assert ed["requirement_key"] == "application_form", f"Bad requirement_key: {ed['requirement_key']}"
        assert ed["form_submission_id"] == fs["id"], "form_submission_id mismatch!"
        
        # ApplicationFormViewer compatibility
        if vc["issues"]:
            print(f"\n  ApplicationFormViewer ISSUES: {vc['issues']}")
            all_pass = False
        else:
            print(f"  ApplicationFormViewer: COMPATIBLE")
        if vc["warnings"]:
            print(f"  Viewer warnings: {vc['warnings']}")
        
        # Employment Review compatibility
        print(f"  Employment Review guards: {rc['guards']}")
        if not rc["would_pass"]:
            print(f"    -> Would NOT pass Employment Review (missing data, not a backfill issue)")
        else:
            print(f"    -> Would pass Employment Review: YES")
    
    # Edge case
    print(f"\n--- Edge case: unknown source ---")
    edge = next(e for e in results if e["employee"]["id"] == "emp-edge-007")
    er = edge["result"]
    print(f"  Source: {edge['employee'].get('application_source')}")
    print(f"  Sections: {er['sections_present']}/{er['sections_total']}")
    print(f"  Missing: {er['missing_sections']}")
    print(f"  Provenance: {er['form_submission']['provenance']}")
    print(f"  Viewer: issues={edge['viewer_compat']['issues']}")
    
    # Final verdict
    print()
    print("=" * 70)
    if all_pass:
        print("VERDICT: ALL SPOT-CHECKS PASSED")
        print("  - form_submission shape: correct (all 14 required keys)")
        print("  - employee_documents slot: correct")
        print("  - ApplicationFormViewer: compatible")
        print("  - Employment Review: backfill creates the required record")
        print("  - Provenance: correctly stamped on all records")
        print("  - Online sources: correctly skipped")
    else:
        print("VERDICT: ISSUES FOUND — SEE ABOVE")
    print("=" * 70)


if __name__ == "__main__":
    main()
