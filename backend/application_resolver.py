"""
application_resolver.py — Canonical Application Completeness Resolver

Single source of truth for determining application completeness across all
creation paths: online_structured, online_legacy, offline_pdf_import,
admin_simple, internal.

Usage:
    from application_resolver import resolve_application, backfill_dry_run, backfill_execute

    # Resolve single employee
    result = await resolve_application(db, employee_id)

    # Dry-run backfill for all non-online employees missing application_form
    report = await backfill_dry_run(db)

    # Execute backfill (only after reviewing dry-run)
    result = await backfill_execute(db, user_id, user_name)
"""

from datetime import datetime, timezone
from stage_identity import get_stage_identity, normalize_lifecycle_status

# =============================================================================
# APPLICATION SECTION DEFINITIONS
# =============================================================================
# These mirror the 13 sections of StructuredApplicationForm in server.py.
# Each section defines: which employee-doc fields populate it, whether it's
# required for Employment Review, and the minimum fields that make a section
# "present" vs "empty".

APPLICATION_SECTIONS = {
    "personal_details": {
        "label": "Personal Details",
        "required_for_review": True,
        "employee_fields": {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "date_of_birth": {"required": True},
            "national_insurance": {"required": False},
            "title": {"required": False},
            "middle_name": {"required": False},
            "preferred_name": {"required": False},
        },
    },
    "contact_details": {
        "label": "Contact Details",
        "required_for_review": True,
        "employee_fields": {
            "email": {"required": True},
            "phone": {"required": True},
            "phone_secondary": {"required": False},
        },
    },
    "address": {
        "label": "Address",
        "required_for_review": True,
        "employee_fields": {
            "address_line_1": {"required": True},
            "city": {"required": True},
            "postcode": {"required": True},
            "address_line_2": {"required": False},
            "county": {"required": False},
        },
    },
    "role_availability": {
        "label": "Role & Availability",
        "required_for_review": True,
        "employee_fields": {
            "role_applied_raw": {"required": False, "aliases": ["role"]},
            "role": {"required": True},
            "availability": {"required": False},
            "earliest_start_date": {"required": False},
            "driver_status": {"required": False, "aliases": ["has_driving_licence"]},
            "has_own_transport": {"required": False},
        },
    },
    "employment_history": {
        "label": "Employment History",
        "required_for_review": True,
        "employee_fields": {
            "employment_history": {"required": True, "is_array": True},
            "has_employment_gaps": {"required": False},
            "employment_gap_explanation": {"required": False},
        },
    },
    "references": {
        "label": "References",
        "required_for_review": True,
        "employee_fields": {
            "reference_1_name": {"required": True},
            "reference_1_email": {"required": True},
            "reference_2_name": {"required": True},
            "reference_2_email": {"required": True},
            "reference_1_phone": {"required": False},
            "reference_1_company": {"required": False},
            "reference_1_relationship": {"required": False},
            "reference_2_phone": {"required": False},
            "reference_2_company": {"required": False},
            "reference_2_relationship": {"required": False},
        },
    },
    "qualifications": {
        "label": "Qualifications & Training",
        "required_for_review": False,
        "employee_fields": {
            "highest_qualification": {"required": False},
            "relevant_qualifications": {"required": False, "is_array": True},
            "care_certificate_completed": {"required": False},
        },
    },
    "health_declaration": {
        "label": "Health Declaration",
        "required_for_review": False,
        "employee_fields": {},
        "nested_path": "declarations",
        "nested_fields": {
            "has_health_conditions": {"required": False},
            "health_conditions_details": {"required": False},
        },
    },
    "criminal_declaration": {
        "label": "Criminal Record Declaration",
        "required_for_review": False,
        "employee_fields": {
            "has_criminal_convictions_declared": {"required": False},
        },
        "nested_path": "declarations",
        "nested_fields": {
            "has_criminal_convictions": {"required": False},
            "dbs_consent_given": {"required": False},
        },
    },
    "right_to_work": {
        "label": "Right to Work",
        "required_for_review": True,
        "employee_fields": {
            "right_to_work_declared": {"required": False},
            "citizenship_status_declared": {"required": False},
        },
    },
    "declarations": {
        "label": "Declarations & Consent",
        "required_for_review": False,
        "employee_fields": {},
        "nested_path": "declarations",
        "nested_fields": {
            "information_accurate_declared": {"required": False},
            "consents_to_reference_checks": {"required": False},
            "consents_to_background_checks": {"required": False},
            "consents_to_data_processing": {"required": False},
        },
    },
    "emergency_contact": {
        "label": "Emergency Contact / Next of Kin",
        "required_for_review": False,
        "employee_fields": {
            "emergency_contact_name": {"required": False, "aliases": ["next_of_kin_name"]},
            "emergency_contact_phone": {"required": False, "aliases": ["next_of_kin_phone"]},
            "emergency_contact_relationship": {"required": False, "aliases": ["next_of_kin_relationship"]},
        },
    },
    "additional_info": {
        "label": "Additional Information",
        "required_for_review": False,
        "employee_fields": {
            "how_heard": {"required": False},
        },
    },
}

# Sources that already have a real online application form submission
ONLINE_SOURCES = {"online_structured"}

# Human-readable provenance labels
SOURCE_LABELS = {
    "online_structured": "Online structured application",
    "online_legacy": "Online legacy application",
    "offline_pdf_import": "Offline PDF import",
    "admin_simple": "Admin-created record",
    "internal": "Internal / promoted staff",
}


# =============================================================================
# SECTION EVALUATION
# =============================================================================

def _get_field_value(employee: dict, field_name: str, field_config: dict):
    """Get a field value from the employee doc, checking aliases."""
    val = employee.get(field_name)
    if val is not None and val != "" and val != []:
        return val
    for alias in field_config.get("aliases", []):
        val = employee.get(alias)
        if val is not None and val != "" and val != []:
            return val
    return None


def _evaluate_section(section_key: str, section_def: dict, employee: dict) -> dict:
    """
    Evaluate a single section's completeness from employee data.

    Returns:
        {
            "key": str,
            "label": str,
            "present": bool,          # at least one field has data
            "complete": bool,          # all required fields have data
            "required_for_review": bool,
            "fields_present": [str],   # fields that have data
            "fields_missing": [str],   # required fields that are empty
            "field_count": int,
            "filled_count": int,
        }
    """
    fields_present = []
    fields_missing = []

    # Top-level employee fields
    for field_name, field_config in section_def.get("employee_fields", {}).items():
        val = _get_field_value(employee, field_name, field_config)
        is_array = field_config.get("is_array", False)

        if is_array:
            has_data = isinstance(val, list) and len(val) > 0
        else:
            has_data = val is not None and val != ""

        if has_data:
            fields_present.append(field_name)
        elif field_config.get("required"):
            fields_missing.append(field_name)

    # Nested fields (e.g., inside employee.declarations)
    nested_path = section_def.get("nested_path")
    if nested_path:
        nested_obj = employee.get(nested_path) or {}
        for field_name, field_config in section_def.get("nested_fields", {}).items():
            val = nested_obj.get(field_name)
            if val is not None and val != "":
                fields_present.append(f"{nested_path}.{field_name}")
            elif field_config.get("required"):
                fields_missing.append(f"{nested_path}.{field_name}")

    total_fields = (
        len(section_def.get("employee_fields", {}))
        + len(section_def.get("nested_fields", {}))
    )
    present = len(fields_present) > 0
    complete = len(fields_missing) == 0

    return {
        "key": section_key,
        "label": section_def["label"],
        "present": present,
        "complete": complete,
        "required_for_review": section_def["required_for_review"],
        "fields_present": fields_present,
        "fields_missing": fields_missing,
        "field_count": total_fields,
        "filled_count": len(fields_present),
    }


# =============================================================================
# CANONICAL RESOLVER
# =============================================================================

async def resolve_application(db, employee_id: str) -> dict:
    """
    Canonical resolver: determine application completeness for any employee.

    Returns:
        {
            "employee_id": str,
            "employee_name": str,
            "application_source": str,
            "source_label": str,
            "has_application_form": bool,        # form_submission with requirement_id=application_form exists
            "has_application_document": bool,     # employee_documents slot exists
            "form_submission_id": str | None,
            "provenance": str,                    # online_structured | backfilled_from_* | none
            "sections": {key: section_eval},
            "backfilled_sections": [str],         # sections that could be backfilled from employee data
            "missing_sections": [str],            # required sections still empty after backfill
            "application_data_complete": bool,    # all required_for_review sections have data
            "completion_summary": {
                "total_sections": int,
                "present_sections": int,
                "complete_sections": int,
                "required_complete": int,
                "required_total": int,
            },
        }
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return {"error": "employee_not_found", "employee_id": employee_id}

    source = employee.get("application_source", "unknown")
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()

    # Check for existing form_submission
    form_sub = await db.form_submissions.find_one(
        {"employee_id": employee_id, "requirement_id": "application_form"},
        {"_id": 0, "id": 1, "status": 1, "submitted_at": 1, "verified": 1},
    )

    # Check for existing employee_documents slot
    app_doc = await db.employee_documents.find_one(
        {"employee_id": employee_id, "requirement_key": "application_form"},
        {"_id": 0, "id": 1, "status": 1},
    )

    has_form = form_sub is not None
    has_doc_slot = app_doc is not None

    # Determine provenance
    if has_form:
        if source in ONLINE_SOURCES:
            provenance = "online_structured"
        else:
            # Existing form_submission from a non-online source = previously backfilled
            provenance = f"backfilled_from_{source}" if source != "unknown" else "backfilled"
    else:
        provenance = "none"

    # Evaluate each section from employee data
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

    total_sections = len(sections)
    present_sections = sum(1 for s in sections.values() if s["present"])
    complete_sections = sum(1 for s in sections.values() if s["complete"])
    required_sections = [s for s in sections.values() if s["required_for_review"]]
    required_complete = sum(1 for s in required_sections if s["complete"])

    application_data_complete = len(missing_sections) == 0
    normalized_status = normalize_lifecycle_status(employee.get("status"))
    stage_identity = get_stage_identity({"status": normalized_status})

    return {
        "employee_id": employee_id,
        "employee_name": emp_name,
        "employee_code": employee.get("employee_code"),
        "applicant_reference": employee.get("applicant_reference"),
        "application_source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "has_application_form": has_form,
        "has_application_document": has_doc_slot,
        "form_submission_id": form_sub.get("id") if form_sub else None,
        "provenance": provenance,
        "sections": sections,
        "backfilled_sections": backfilled_sections,
        "missing_sections": missing_sections,
        "application_data_complete": application_data_complete,
        "lifecycle": {
            "status": normalized_status,
            "person_stage": "employee" if stage_identity == "employee" else "applicant",
            "is_applicant": stage_identity == "applicant",
            "is_employee": stage_identity == "employee",
        },
        "completion_summary": {
            "total_sections": total_sections,
            "present_sections": present_sections,
            "complete_sections": complete_sections,
            "required_complete": required_complete,
            "required_total": len(required_sections),
        },
    }


# =============================================================================
# BACKFILL: Build form_submission from employee data
# =============================================================================

def _build_form_data_from_employee(employee: dict) -> dict:
    """
    Build the form_data dict (matching the online_structured layout)
    from flat employee fields. Only includes fields with actual data.
    """
    def _v(key, *aliases):
        val = employee.get(key)
        if val is not None and val != "":
            return val
        for a in aliases:
            val = employee.get(a)
            if val is not None and val != "":
                return val
        return None

    decl = employee.get("declarations") or {}

    form_data = {}

    # personal_details
    pd = {}
    for k in ("title", "first_name", "middle_name", "last_name", "preferred_name",
              "date_of_birth", "national_insurance"):
        v = _v(k, "ni_number" if k == "national_insurance" else None)
        if v is not None:
            pd[k] = v
    if pd:
        form_data["personal_details"] = pd

    # contact_details
    cd = {}
    for k in ("email", "phone", "phone_secondary"):
        v = _v(k)
        if v is not None:
            cd[k] = v
    if cd:
        form_data["contact_details"] = cd

    # address
    addr = {}
    for k in ("address_line_1", "address_line_2", "city", "county", "postcode"):
        v = _v(k)
        if v is not None:
            addr[k] = v
    if addr:
        form_data["address"] = addr

    # role_availability
    ra = {}
    role_raw = _v("role_applied_raw", "role")
    if role_raw:
        ra["role_applied"] = role_raw
    for k in ("availability", "earliest_start_date"):
        v = _v(k)
        if v is not None:
            ra[k] = v
    drive = _v("driver_status", "has_driving_licence")
    if drive is not None:
        ra["has_driving_licence"] = bool(drive)
    transport = _v("has_own_transport")
    if transport is not None:
        ra["has_own_transport"] = bool(transport)
    if ra:
        form_data["role_availability"] = ra

    # employment_history
    eh = employee.get("employment_history")
    if isinstance(eh, list) and len(eh) > 0:
        form_data["employment_history"] = eh
    gaps = _v("has_employment_gaps")
    if gaps is not None:
        form_data["has_employment_gaps"] = gaps
    gap_exp = _v("employment_gap_explanation")
    if gap_exp:
        form_data["employment_gap_explanation"] = gap_exp

    # references
    refs = []
    for i in (1, 2):
        ref = {}
        for suffix in ("name", "email", "phone", "company", "job_title",
                        "relationship", "years_known", "is_professional",
                        "can_contact_before_offer"):
            v = _v(f"reference_{i}_{suffix}")
            if v is not None:
                # Map flat keys to structured keys
                mapped_key = {
                    "name": "referee_name",
                    "email": "referee_email",
                    "phone": "referee_phone",
                    "company": "referee_organisation",
                    "job_title": "referee_job_title",
                }.get(suffix, suffix)
                ref[mapped_key] = v
        if ref:
            refs.append(ref)
    if refs:
        form_data["references"] = refs

    # qualifications
    quals = {}
    for k in ("highest_qualification", "care_certificate_completed"):
        v = _v(k)
        if v is not None:
            quals[k] = v
    rq = employee.get("relevant_qualifications")
    if isinstance(rq, list) and rq:
        quals["relevant_qualifications"] = rq
    if quals:
        form_data["qualifications"] = quals

    # health_declaration
    hd = {}
    if decl.get("has_health_conditions") is not None:
        hd["has_health_conditions"] = decl["has_health_conditions"]
    if decl.get("health_conditions_details"):
        hd["health_condition_details"] = decl["health_conditions_details"]
    if hd:
        form_data["health_declaration"] = hd

    # criminal_declaration
    crd = {}
    if decl.get("has_criminal_convictions") is not None:
        crd["has_criminal_convictions"] = decl["has_criminal_convictions"]
    if decl.get("dbs_consent_given") is not None:
        crd["consents_to_dbs_check"] = decl["dbs_consent_given"]
    if decl.get("understands_dbs_required") is not None:
        crd["understands_dbs_required"] = decl["understands_dbs_required"]
    conv_declared = _v("has_criminal_convictions_declared")
    if conv_declared is not None and "has_criminal_convictions" not in crd:
        crd["has_criminal_convictions"] = conv_declared
    if crd:
        form_data["criminal_declaration"] = crd

    # right_to_work
    rtw = {}
    rtw_dec = _v("right_to_work_declared")
    if rtw_dec is not None:
        rtw["has_right_to_work_uk"] = rtw_dec
    cit = _v("citizenship_status_declared")
    if cit:
        rtw["citizenship_status"] = cit
    if decl.get("has_rtw_restrictions") is not None:
        rtw["has_unlimited_right_to_work"] = not decl["has_rtw_restrictions"]
    if decl.get("rtw_restrictions_details"):
        rtw["visa_type"] = decl["rtw_restrictions_details"]
    if decl.get("rtw_expiry_date"):
        rtw["visa_expiry"] = decl["rtw_expiry_date"]
    if rtw:
        form_data["right_to_work"] = rtw

    # declarations
    dec_out = {}
    for k in ("information_accurate_declared", "consents_to_reference_checks",
              "consents_to_background_checks", "consents_to_data_processing"):
        v = decl.get(k)
        if v is not None:
            # Map to canonical key names
            mapped = k.replace("_declared", "")
            dec_out[mapped] = v
    if dec_out:
        form_data["declarations"] = dec_out

    # emergency_contact
    ec = {}
    for suffix in ("name", "phone", "relationship", "address"):
        v = _v(f"emergency_contact_{suffix}", f"next_of_kin_{suffix}")
        if v is not None:
            ec[suffix] = v
    if ec:
        form_data["emergency_contact"] = ec

    # additional
    hw = _v("how_heard")
    if hw:
        form_data["how_heard"] = hw

    return form_data


# =============================================================================
# DRY-RUN MIGRATION
# =============================================================================

async def backfill_dry_run(db, employee_ids: list = None) -> dict:
    """
    Dry-run: evaluate all employees (or a subset) and report which ones
    need a backfilled application_form form_submission.

    Never touches the database.

    Args:
        db: database instance
        employee_ids: optional list of specific IDs to evaluate (None = all)

    Returns:
        {
            "total_employees": int,
            "already_have_form": int,
            "would_backfill": int,
            "skipped_online": int,
            "candidates": [
                {
                    "employee_id": str,
                    "employee_name": str,
                    "application_source": str,
                    "sections_present": int,
                    "sections_total": int,
                    "required_complete": int,
                    "required_total": int,
                    "application_data_complete": bool,
                    "missing_sections": [str],
                    "backfilled_sections": [str],
                },
            ],
            "skipped": [
                {"employee_id": str, "reason": str},
            ],
        }
    """
    query = {}
    if employee_ids:
        query["id"] = {"$in": employee_ids}

    employees = await db.employees.find(query, {"_id": 0, "id": 1}).to_list(5000)
    emp_ids = [e["id"] for e in employees]

    # Batch-fetch existing form_submissions for application_form
    existing_forms = await db.form_submissions.find(
        {"employee_id": {"$in": emp_ids}, "requirement_id": "application_form"},
        {"_id": 0, "employee_id": 1},
    ).to_list(5000)
    has_form_set = {f["employee_id"] for f in existing_forms}

    candidates = []
    skipped = []
    already_have = 0
    skipped_online = 0

    for emp_stub in employees:
        eid = emp_stub["id"]

        if eid in has_form_set:
            already_have += 1
            skipped.append({"employee_id": eid, "reason": "already_has_form_submission"})
            continue

        # Resolve full application status
        resolution = await resolve_application(db, eid)
        if resolution.get("error"):
            skipped.append({"employee_id": eid, "reason": resolution["error"]})
            continue

        source = resolution["application_source"]

        # Never overwrite real online_structured applications
        if source in ONLINE_SOURCES:
            skipped_online += 1
            skipped.append({"employee_id": eid, "reason": "online_source_without_form (data issue)"})
            continue

        candidates.append({
            "employee_id": eid,
            "employee_name": resolution["employee_name"],
            "employee_code": resolution.get("employee_code"),
            "applicant_reference": resolution.get("applicant_reference"),
            "application_source": source,
            "source_label": resolution["source_label"],
            "sections_present": resolution["completion_summary"]["present_sections"],
            "sections_total": resolution["completion_summary"]["total_sections"],
            "required_complete": resolution["completion_summary"]["required_complete"],
            "required_total": resolution["completion_summary"]["required_total"],
            "application_data_complete": resolution["application_data_complete"],
            "missing_sections": resolution["missing_sections"],
            "backfilled_sections": resolution["backfilled_sections"],
        })

    return {
        "total_employees": len(emp_ids),
        "already_have_form": already_have,
        "would_backfill": len(candidates),
        "skipped_online": skipped_online,
        "candidates": candidates,
        "skipped": skipped,
    }


# =============================================================================
# EXECUTE BACKFILL
# =============================================================================

async def backfill_execute(
    db,
    user_id: str,
    user_name: str,
    employee_ids: list = None,
) -> dict:
    """
    Execute backfill: create form_submission records for employees that
    don't have one, using data already on their employee document.

    Safety:
        - NEVER overwrites existing form_submissions with requirement_id=application_form
        - NEVER touches online_structured records
        - Provenance is clearly stamped on every backfilled record
        - Also creates/updates the employee_documents slot if missing

    Args:
        db: database instance
        user_id: admin user performing the backfill
        user_name: admin user name for audit
        employee_ids: optional subset (None = all eligible)

    Returns:
        {"backfilled": int, "skipped": int, "errors": [...]}
    """
    import uuid

    dry = await backfill_dry_run(db, employee_ids)
    candidates = dry["candidates"]

    backfilled = 0
    errors = []

    for cand in candidates:
        eid = cand["employee_id"]
        try:
            # Double-check: no existing form_submission
            existing = await db.form_submissions.find_one(
                {"employee_id": eid, "requirement_id": "application_form"},
                {"_id": 0, "id": 1},
            )
            if existing:
                continue

            employee = await db.employees.find_one({"id": eid}, {"_id": 0})
            if not employee:
                continue

            source = employee.get("application_source", "unknown")
            now = datetime.now(timezone.utc).isoformat()
            form_data = _build_form_data_from_employee(employee)

            form_sub_id = str(uuid.uuid4())
            form_submission = {
                "id": form_sub_id,
                "employee_id": eid,
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
                    "backfilled_by": user_id,
                    "backfilled_by_name": user_name,
                    "backfilled_at": now,
                    "sections_present": cand["sections_present"],
                    "sections_total": cand["sections_total"],
                    "application_data_complete": cand["application_data_complete"],
                    "missing_sections": cand["missing_sections"],
                },
                "created_at": now,
                "updated_at": now,
            }

            await db.form_submissions.insert_one(form_submission)

            # Ensure employee_documents slot exists
            existing_doc = await db.employee_documents.find_one(
                {"employee_id": eid, "requirement_key": "application_form"},
                {"_id": 0, "id": 1},
            )
            if not existing_doc:
                await db.employee_documents.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": eid,
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
                })

            backfilled += 1

        except Exception as e:
            errors.append({"employee_id": eid, "error": str(e)})

    return {
        "backfilled": backfilled,
        "skipped": dry["already_have_form"] + dry["skipped_online"],
        "errors": errors[:20],
    }
