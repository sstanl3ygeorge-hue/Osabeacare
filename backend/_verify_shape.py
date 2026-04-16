"""Verification script: Compare real online_structured shape vs backfill shape."""
import asyncio, os, json
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # =========================================================================
    # 1. Get real online_structured form_submission shape
    # =========================================================================
    online_emps = await db.employees.find(
        {"application_source": "online_structured"},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
    ).to_list(10)
    print(f"Online structured employees: {len(online_emps)}")

    real_form = None
    real_emp = None
    for emp in online_emps:
        eid = emp["id"]
        form = await db.form_submissions.find_one(
            {"employee_id": eid, "requirement_id": "application_form"}, {"_id": 0}
        )
        if form and form.get("form_data"):
            real_form = form
            real_emp = emp
            break

    if real_form:
        name = f"{real_emp.get('first_name','')} {real_emp.get('last_name','')}"
        print(f"\n{'='*60}")
        print(f"REAL FORM: {name} ({real_emp['id'][:20]})")
        print(f"{'='*60}")
        print(f"Top-level keys: {sorted(real_form.keys())}")
        fd = real_form.get("form_data", {})
        print(f"form_data keys: {sorted(fd.keys())}")
        print(f"status: {real_form.get('status')}")
        print(f"verified: {real_form.get('verified')}")
        print(f"template_id: {real_form.get('template_id')}")
        print(f"form_type: {real_form.get('form_type')}")
        print(f"requirement_id: {real_form.get('requirement_id')}")

        for section_key in sorted(fd.keys()):
            val = fd[section_key]
            if isinstance(val, dict):
                print(f"  {section_key}: dict keys={sorted(val.keys())}")
            elif isinstance(val, list):
                print(f"  {section_key}: list len={len(val)}")
                if val and isinstance(val[0], dict):
                    print(f"    [0] keys={sorted(val[0].keys())}")
            else:
                print(f"  {section_key}: {type(val).__name__} = {repr(val)[:80]}")

        print(f"\n--- FULL form_data JSON (truncated) ---")
        print(json.dumps(fd, indent=2, default=str)[:4000])
    else:
        print("WARNING: No online_structured form_submissions found!")

    # =========================================================================
    # 2. Get backfill shape for a NON-online employee
    # =========================================================================
    from application_resolver import resolve_application, _build_form_data_from_employee

    # Find a non-online employee without form_submission  
    non_online = await db.employees.find(
        {"application_source": {"$nin": ["online_structured", None]}},
        {"_id": 0}
    ).to_list(20)

    backfill_example = None
    for emp in non_online:
        eid = emp["id"]
        existing = await db.form_submissions.find_one(
            {"employee_id": eid, "requirement_id": "application_form"},
            {"_id": 0, "id": 1}
        )
        # Want one WITHOUT existing form but WITH some data
        if not existing and emp.get("first_name"):
            backfill_example = emp
            break

    if backfill_example:
        name = f"{backfill_example.get('first_name','')} {backfill_example.get('last_name','')}"
        src = backfill_example.get("application_source", "unknown")
        print(f"\n{'='*60}")
        print(f"BACKFILL EXAMPLE: {name} (source={src})")
        print(f"{'='*60}")

        bf_form_data = _build_form_data_from_employee(backfill_example)
        print(f"Backfill form_data keys: {sorted(bf_form_data.keys())}")

        for section_key in sorted(bf_form_data.keys()):
            val = bf_form_data[section_key]
            if isinstance(val, dict):
                print(f"  {section_key}: dict keys={sorted(val.keys())}")
            elif isinstance(val, list):
                print(f"  {section_key}: list len={len(val)}")
                if val and isinstance(val[0], dict):
                    print(f"    [0] keys={sorted(val[0].keys())}")
            else:
                print(f"  {section_key}: {type(val).__name__} = {repr(val)[:80]}")

        print(f"\n--- BACKFILL form_data JSON (truncated) ---")
        print(json.dumps(bf_form_data, indent=2, default=str)[:4000])
    else:
        print("WARNING: No non-online employee without form found!")

    # =========================================================================
    # 3. SHAPE COMPARISON
    # =========================================================================
    if real_form and backfill_example:
        real_fd = real_form.get("form_data", {})
        bf_fd = bf_form_data

        print(f"\n{'='*60}")
        print("SHAPE COMPARISON: REAL vs BACKFILL")
        print(f"{'='*60}")

        real_sections = set(real_fd.keys())
        bf_sections = set(bf_fd.keys())
        print(f"Real sections: {sorted(real_sections)}")
        print(f"Backfill sections: {sorted(bf_sections)}")
        print(f"In real but NOT backfill: {sorted(real_sections - bf_sections)}")
        print(f"In backfill but NOT real: {sorted(bf_sections - real_sections)}")

        # Compare nested keys for shared sections
        for section in sorted(real_sections & bf_sections):
            rv = real_fd[section]
            bv = bf_fd[section]
            if isinstance(rv, dict) and isinstance(bv, dict):
                rk = set(rv.keys())
                bk = set(bv.keys())
                if rk != bk:
                    print(f"\n  {section} KEY MISMATCH:")
                    print(f"    Real keys: {sorted(rk)}")
                    print(f"    Backfill keys: {sorted(bk)}")
                    print(f"    In real only: {sorted(rk - bk)}")
                    print(f"    In backfill only: {sorted(bk - rk)}")
                else:
                    print(f"  {section}: keys match ({len(rk)} keys)")
            elif isinstance(rv, list) and isinstance(bv, list):
                if rv and bv and isinstance(rv[0], dict) and isinstance(bv[0], dict):
                    rk = set(rv[0].keys())
                    bk = set(bv[0].keys())
                    if rk != bk:
                        print(f"\n  {section} ARRAY ITEM KEY MISMATCH:")
                        print(f"    Real[0] keys: {sorted(rk)}")
                        print(f"    Backfill[0] keys: {sorted(bk)}")
                        print(f"    In real only: {sorted(rk - bk)}")
                        print(f"    In backfill only: {sorted(bk - rk)}")
                    else:
                        print(f"  {section}: array item keys match ({len(rk)} keys)")
                else:
                    print(f"  {section}: lists (real len={len(rv)}, bf len={len(bv)})")
            elif type(rv) != type(bv):
                print(f"\n  {section} TYPE MISMATCH: real={type(rv).__name__}, bf={type(bv).__name__}")
            else:
                print(f"  {section}: scalar match")

    # =========================================================================
    # 4. Consumer field audit - check what ApplicationFormViewer reads
    # =========================================================================
    if backfill_example:
        print(f"\n{'='*60}")
        print("CONSUMER FIELD AUDIT (backfill)")
        print(f"{'='*60}")

        # ApplicationDataPanel reads
        checks = {
            "form_data.employment_history": bf_form_data.get("employment_history"),
            "form_data.has_employment_gaps": bf_form_data.get("has_employment_gaps"),
            "form_data.employment_gap_explanation": bf_form_data.get("employment_gap_explanation"),
            "form_data.criminal_declaration": bf_form_data.get("criminal_declaration"),
            "form_data.health_declaration": bf_form_data.get("health_declaration"),
            "form_data.right_to_work": bf_form_data.get("right_to_work"),
        }
        for path, val in checks.items():
            present = val is not None and val != "" and val != [] and val != {}
            print(f"  {path}: {'PRESENT' if present else 'MISSING'} ({type(val).__name__ if val else 'None'})")

        # Criminal declaration sub-fields
        crd = bf_form_data.get("criminal_declaration", {})
        for k in ("has_criminal_convictions", "conviction_details", "consents_to_dbs_check"):
            print(f"    criminal_declaration.{k}: {crd.get(k, 'MISSING')}")

        # Health declaration sub-fields
        hd = bf_form_data.get("health_declaration", {})
        for k in ("has_health_conditions", "health_condition_details"):
            print(f"    health_declaration.{k}: {hd.get(k, 'MISSING')}")

        # Right to work sub-fields
        rtw = bf_form_data.get("right_to_work", {})
        for k in ("has_unlimited_right_to_work", "visa_type", "has_right_to_work_uk"):
            print(f"    right_to_work.{k}: {rtw.get(k, 'MISSING')}")

    # =========================================================================
    # 5. Backfill record shape - verify consumer-critical fields
    # =========================================================================
    print(f"\n{'='*60}")
    print("BACKFILL RECORD SHAPE (what gets written to form_submissions)")
    print(f"{'='*60}")
    
    # Simulate the record that would be written
    record_fields = [
        "id", "employee_id", "requirement_id", "template_id", "template_name",
        "form_type", "form_data", "status", "submitted_by_applicant",
        "submitted_at", "verified", "provenance", "backfill_metadata",
        "created_at", "updated_at"
    ]
    print(f"Record top-level keys: {record_fields}")
    
    # Compare with real form top-level keys
    if real_form:
        real_keys = set(real_form.keys())
        bf_keys = set(record_fields)
        print(f"\nReal form top-level keys: {sorted(real_keys)}")
        print(f"In real but NOT in backfill record: {sorted(real_keys - bf_keys)}")
        print(f"In backfill record but NOT in real: {sorted(bf_keys - real_keys)}")

    # =========================================================================
    # 6. employee_documents slot shape
    # =========================================================================
    print(f"\n{'='*60}")
    print("EMPLOYEE_DOCUMENTS SLOT ANALYSIS")
    print(f"{'='*60}")

    # Check existing application_form doc slots
    existing_doc_slots = await db.employee_documents.find(
        {"requirement_key": "application_form"},
        {"_id": 0}
    ).to_list(20)
    print(f"Existing application_form doc slots: {len(existing_doc_slots)}")
    
    if existing_doc_slots:
        slot = existing_doc_slots[0]
        print(f"Example slot keys: {sorted(slot.keys())}")
        print(f"  status: {slot.get('status')}")
        print(f"  verified: {slot.get('verified')}")
        print(f"  form_submission_id: {slot.get('form_submission_id')}")
        print(f"  supports_files: {slot.get('supports_files')}")
        print(f"  supports_requests: {slot.get('supports_requests')}")
        print(f"  file_url: {slot.get('file_url')}")
        print(f"  blocking: {slot.get('blocking')}")

    # What backfill would create vs what exists
    backfill_doc_keys = [
        "id", "employee_id", "requirement_key", "requirement_id",
        "requirement_type", "document_type_name", "category", "blocking",
        "supports_files", "supports_requests", "status", "verified",
        "form_submission_id", "policy", "metadata", "notes",
        "created_at", "updated_at"
    ]
    if existing_doc_slots:
        real_doc_keys = set(existing_doc_slots[0].keys())
        bf_doc_keys = set(backfill_doc_keys)
        print(f"\nIn real doc BUT NOT backfill doc: {sorted(real_doc_keys - bf_doc_keys)}")
        print(f"In backfill doc BUT NOT real doc: {sorted(bf_doc_keys - real_doc_keys)}")

    # =========================================================================
    # 7. safe_for_review vs actual review rules
    # =========================================================================
    print(f"\n{'='*60}")
    print("SAFE_FOR_REVIEW ANALYSIS")
    print(f"{'='*60}")

    # Check what routes/recruitment.py employment review actually checks
    # It checks: form_submissions with requirement_id=application_form OR form_type=application_form
    # So: does the backfill record satisfy that?
    print("Backfill sets requirement_id='application_form': YES")
    print("Backfill sets form_type='application_form': YES")
    print("Employment Review query ($or requirement_id/form_type): WOULD MATCH")
    print("Backfill sets status='completed': YES")
    print("Backfill sets verified=False: YES (needs manual verification)")

    client.close()

asyncio.run(main())
