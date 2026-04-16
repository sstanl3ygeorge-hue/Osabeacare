# One-Way Online Application — Strict Rollout Plan

**Date:** 2026-04-16  
**Scope:** Retire all legacy applicant intake paths. Enforce `POST /applications/structured` as the only canonical applicant journey.  
**Method:** Code-verified against actual file/line references. Every recommendation traceable to a specific read/write path.

---

## 1. Rollout Plan by Phase

---

### Phase 0 — Pre-existing Bug Fix (BLOCKING)

**Objective:** Fix a broken reference status check in the compliance engine that will produce wrong results regardless of this rollout.

**Finding:** `compliance_engine/status.py` line 459 — `_get_references_status()` calls `db.references.find({"employee_id": employee_id})` and then reads `r.get("status")`. But the `references` collection stores **one document per employee** with nested `ref1`/`ref2` sub-documents. There is no top-level `status` field. This function always returns `MISSING` for references.

**File:** `backend/compliance_engine/status.py` L458–480  
**Fix:** Rewrite to read `ref1.verification_status` and `ref2.verification_status` from a `find_one()` result.  
**Impact:** None — this code already returns wrong results.  
**Rollback:** Revert function.

---

### Phase 1 — Kill Dead Endpoints (zero risk)

**Objective:** Disable the 3 applicant creation endpoints that have zero live frontend callers.

| Endpoint | File | Source | Frontend Callers | Action |
|---|---|---|---|---|
| `POST /apply` | `server.py` L24881 | `online_legacy` | **None** | Replace body with `410 Gone` |
| `POST /employees/simple` | `routes/employees.py` L235 | `admin_simple` | **None** | Replace body with `410 Gone` |
| `GET /admin/employees/import-template` | `server.py` L12765 | *(helper for bulk import)* | **None** | Replace body with `410 Gone` |

**Expected impact:** Zero. No frontend code calls these endpoints.  
**Rollout risk:** None.  
**Rollback:** Restore function bodies.

---

### Phase 2 — Retire Bulk Import (coordinated backend + frontend deploy)

**Objective:** Disable the bulk import / PDF extraction pipeline and remove all its UI entry points.

#### Backend changes

| Endpoint | File | Line | Action |
|---|---|---|---|
| `POST /admin/employees/bulk-import` | `server.py` L12590 | Replace body with `410 Gone` |
| `POST /admin/employees/extract-from-pdf` | `server.py` L12800 | Replace body with `410 Gone` |

Keep the `BulkEmployeeImportRow` / `BulkEmployeeImportRequest` models in place — they are harmless and removing them risks breaking imports elsewhere. The 410 response is the gate.

#### Frontend changes

| File | Change |
|---|---|
| `src/App.js` L41 | Remove `import BulkImportPage` |
| `src/App.js` L116 | Remove `<Route path="bulk-import" …>` |
| `src/components/portal/PortalLayout.js` L27 | Remove `{ name: 'Bulk Import', href: '/portal/bulk-import', icon: Upload }` |
| `src/components/portal/PortalLayout.js` L21 | Remove `Upload` from lucide-react import (if unused elsewhere) |
| `src/pages/portal/BulkImportPage.js` | Delete file |
| `src/components/admin/BulkImportPanel.js` | Delete file |

**Expected impact:** Admins lose the PDF import + bulk creation capability. This is the desired outcome.  
**Rollout risk:** Low — coordinated deploy means backend 410 + frontend removal happen together.  
**Rollback:** Restore endpoint bodies + restore frontend files.  
**Pre-check:** Confirm with admin team that no bulk imports are pending or expected.

---

### Phase 3 — Reference Collection Unification (integrity fix)

**Objective:** Eliminate the dual `references` / `employee_references` collection problem. Make `references` the sole canonical store.

See §4 below for the full reference integrity plan.

**Expected impact:** Worker wizard and profile-completion flows switch to writing `references` directly. Bulk-imported employees get a `references` doc created from their `employee_references` data. Compliance/readiness engines see correct reference data for all employees.  
**Rollout risk:** Medium — data migration required. Test thoroughly.  
**Rollback:** Keep old code paths behind feature flag or revert. `employee_references` data is not deleted during migration.

---

### Phase 4 — Runtime Guards

**Objective:** Prevent legacy records from polluting live operational surfaces. Add guards keyed on canonical `form_submissions` existence, not optimistic source labels.

See §3 below for the full runtime protection plan.

**Expected impact:** Admins see clear indicators for legacy records. Work readiness engine handles missing forms gracefully. Compliance file shows provenance banner.  
**Rollout risk:** Low — additive changes only (banners, indicators, optional filters).  
**Rollback:** Remove guard code.

---

### Phase 5 — ProfileCompletionWizard Cleanup

**Objective:** Remove the ProfileCompletionWizard and its `profile_completion_needed` trigger, which exist solely for the bulk-import flow.

**Pre-check (BLOCKING):** Query production DB:
```js
db.employees.countDocuments({
  profile_completion_needed: true,
  status: { $nin: ["archived", "withdrawn", "superseded"] }
})
```
If count > 0, those workers must complete their profiles first or be manually resolved before this phase.

#### Frontend changes

| File | Change |
|---|---|
| `src/components/worker/ProfileCompletionWizard.js` | Delete file |
| `src/pages/worker/WorkerDashboard.js` L21 | Remove `ProfileCompletionWizard` import |
| `src/pages/worker/WorkerDashboard.js` L456 | Remove `profileCompletionStatus` state |
| `src/pages/worker/WorkerDashboard.js` L534 | Remove `checkProfileCompletion()` call |
| `src/pages/worker/WorkerDashboard.js` L1270 | Remove "Complete Your Profile" banner |
| `src/pages/worker/WorkerDashboard.js` L3334 | Remove `<ProfileCompletionWizard>` render |

#### Backend changes

| File | Change |
|---|---|
| `routes/workers.py` L252–402 | Remove/simplify `GET /worker/profile-completion-status` endpoint — or keep it but remove `needs_wizard` logic |
| `routes/workers.py` L527 | Remove `profile_completion_needed` clearing logic |

**Expected impact:** Workers who were never given `profile_completion_needed: true` see no change. The wizard was only triggered for PDF imports.  
**Rollout risk:** Low — after pre-check confirms zero active wizard users.  
**Rollback:** Restore files.

---

### Phase 6 — Legacy Data Migration (one-time)

**Objective:** Backfill `form_submissions` and `employee_documents` requirement slots for legacy employees who need them, then archive records that don't.

See §5 below for decision rules.

**Expected impact:** Compliance views become accurate for retained legacy employees. Unnecessary legacy records get archived.  
**Rollout risk:** Low — data enrichment only, stamped as `"backfilled"`.  
**Rollback:** Delete backfilled `form_submissions` where `provenance` starts with `"backfilled_from_"`.

---

### Phase 7 — Dead Code Cleanup

**Objective:** Remove code that only served retired paths.

| File | Change |
|---|---|
| `server.py` | Delete `POST /apply` function body entirely (was 410 stub from Phase 1) |
| `server.py` | Delete `POST /admin/employees/bulk-import` function body entirely |
| `server.py` | Delete `POST /admin/employees/extract-from-pdf` function body entirely |
| `server.py` | Delete `GET /admin/employees/import-template` function body entirely |
| `server.py` | Delete `BulkEmployeeImportRow`, `BulkEmployeeImportRequest` models |
| `server.py` | Delete `ApplicationForm` model (legacy simple form) |
| `routes/employees.py` | Delete `POST /employees/simple` function body entirely |
| `application_resolver.py` | Remove `SOURCE_LABELS` entries for retired sources. Archive `backfill_dry_run()` / `backfill_execute()` after Phase 6 completes. |

**Expected impact:** None — all paths already disabled.  
**Rollout risk:** None.  
**Rollback:** Restore code from git.

---

## 2. Exact Code Changes for Phase 1

### 2a. Disable `POST /apply`

**File:** `backend/server.py`  
**Location:** Line 24881

Replace the entire function body (keep the decorator and signature for route registration):

```python
@api_router.post("/apply")
async def submit_application(form: ApplicationForm):
    """
    RETIRED — Legacy application endpoint disabled.
    All applications must use POST /applications/structured via the online form.
    """
    raise HTTPException(
        status_code=410,
        detail="This application endpoint has been retired. Please use the online application form at /apply"
    )
```

**Audit log:** Not needed — endpoint was never called by any live frontend. No data is lost.

### 2b. Disable `POST /employees/simple`

**File:** `backend/routes/employees.py`  
**Location:** Line 235

Replace the entire function body:

```python
@router.post("/employees/simple", response_model=None)
async def create_employee_simple(
    employee: EmployeeCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """
    RETIRED — Simplified employee creation disabled.
    Use POST /employees for admin creation or direct applicants to the online application form.
    """
    raise HTTPException(
        status_code=410,
        detail="This endpoint has been retired. Use POST /employees for admin creation, or direct applicants to the online application form."
    )
```

**Note:** Change `response_model=EmployeeResponse` to `response_model=None` since the function now always raises.

### 2c. Disable `GET /admin/employees/import-template`

**File:** `backend/server.py`  
**Location:** Line 12765

Replace the function body:

```python
@api_router.get("/admin/employees/import-template")
async def get_import_template(
    user: dict = Depends(require_manager_or_admin)
):
    """RETIRED — Bulk import has been disabled."""
    raise HTTPException(
        status_code=410,
        detail="Bulk import has been retired. All applicants must apply via the online application form."
    )
```

### 2d. Disable `POST /admin/employees/bulk-import`

**File:** `backend/server.py`  
**Location:** Line 12590

Replace the function body:

```python
@api_router.post("/admin/employees/bulk-import")
async def bulk_import_employees(
    request: BulkEmployeeImportRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """RETIRED — Bulk import has been disabled. All applicants must apply online."""
    raise HTTPException(
        status_code=410,
        detail="Bulk import has been retired. All applicants must apply via the online application form."
    )
```

### 2e. Disable `POST /admin/employees/extract-from-pdf`

**File:** `backend/server.py`  
**Location:** Line 12800

Replace the function body:

```python
@api_router.post("/admin/employees/extract-from-pdf")
async def extract_employee_from_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(require_manager_or_admin)
):
    """RETIRED — PDF extraction has been disabled alongside bulk import."""
    raise HTTPException(
        status_code=410,
        detail="PDF extraction has been retired. All applicants must apply via the online application form."
    )
```

### Phase 1 validation

After applying these 5 changes, run:
```bash
python -c "from server import app; print('OK')"
python -m pytest tests/ -x --tb=short -q
```

The import check verifies no syntax errors. Existing tests should pass since no live test calls these endpoints directly (test_reference_slot_hardening tests the reference system, not application creation).

---

## 3. Runtime Protection Plan

### Guard Philosophy

**Key off canonical `form_submissions` existence, not `application_source`.**

Rationale:
- `application_source` is write-only metadata — easy to fake, not validated
- The actual operational difference is whether a `form_submissions` record with `requirement_id: "application_form"` exists
- A record with a real `form_submission` went through the structured intake and has attestation-quality data
- A record without one was created via a shortcut path and may have incomplete/unattested data

Define the guard check as:

```python
has_canonical_application = await db.form_submissions.find_one({
    "employee_id": employee_id,
    "requirement_id": "application_form",
    "status": {"$in": ["submitted", "verified", "approved", "signed_off"]}
}) is not None
```

### Surface-by-Surface Plan

#### 3.1 Employment Review Sign-off

**File:** `routes/recruitment.py` L597–610  
**Current risk:** None — already guarded.  
**Existing guard:** Checks `form_submissions.find_one({"employee_id": ..., "requirement_id": "application_form"})` and rejects with HTTP 400 if missing.  
**Action:** **None.** This is the gold standard.

#### 3.2 Compliance File View

**File:** `server.py` L34266  
**Current risk:** HIGH — shows empty rows for legacy employees with no form_submissions, no references, no requirement slots. Admin sees a seemingly empty record with zero progress, may waste time investigating.  
**Guard needed:** Yes.  
**Action:** Add a top-level field `has_canonical_application` to the compliance-file response, computed by the guard check above. The frontend can use this to display a banner: *"This record was not created via the online application form. Compliance data may be incomplete."*

```python
# In the compliance-file endpoint, after loading employee:
app_submission = await db.form_submissions.find_one({
    "employee_id": employee_id,
    "requirement_id": "application_form",
    "status": {"$in": ["submitted", "verified", "approved", "signed_off"]}
})
# Add to response:
"has_canonical_application": app_submission is not None,
"application_source": employee.get("application_source", "unknown"),
```

**Why `form_submissions` and not just `application_source`:** A backfilled record will have `application_source: "internal"` but ALSO have a form_submission with `provenance: "backfilled_from_internal"`. The guard catches both states correctly — present with any provenance = show compliance normally; absent = show warning.

#### 3.3 Admin Employee List

**File:** `server.py` L9307–9420  
**Current risk:** HIGH — no way to identify legacy/imported records. Admins see records with 0% completion and no context for why.  
**Guard needed:** Yes.  
**Action:**
1. Add `application_source` to the `EmployeeResponse` serialisation (currently omitted).
2. Add an optional query parameter `source` to `GET /employees` for filtering.
3. Frontend can use this to show a badge or filter legacy records from default views.

#### 3.4 Application Viewer (frontend)

**File:** Frontend `ApplicationFormViewer.js`  
**Current risk:** MEDIUM — shows blank panel when no `form_submission` exists.  
**Guard needed:** Yes, frontend-side.  
**Action:** When the `GET /form-submissions?employee_id={id}&requirement_id=application_form` call returns `[]`, display: *"No application form on file. This record may have been created via admin import."* Do not render the empty form viewer.

#### 3.5 Recruitment Pipeline

**File:** `routes/recruitment.py` L153–197  
**Current risk:** LOW — status filter (`new`, `screening`, `interview`, `compliance_review`) naturally excludes most legacy records. Legacy records created via admin or bulk import that happen to have applicant-stage statuses would appear.  
**Guard needed:** Optional — low priority.  
**Action (if applied):** Add `application_source` to the applicant list response so the recruitment UI can show provenance. Do NOT filter by source — admins may need to see and manually resolve these records.

#### 3.6 Worker Dashboard

**File:** `routes/worker_dashboard.py` L200  
**Current risk:** LOW-MEDIUM — degrades gracefully. Shows wall of "action required" for workers with no data, but doesn't crash.  
**Guard needed:** Optional.  
**Action (if applied):** Add `application_source` and `has_canonical_application` to the dashboard payload. Frontend can display context banner for non-canonical workers.

#### 3.7 Task Queue

**File:** `routes/task_queue.py` L20  
**Current risk:** LOW — document-driven. Legacy employees without documents or references don't appear at all.  
**Guard needed:** No.  
**Action:** None.

### Guard Implementation Priority

| Priority | Surface | Reason |
|---|---|---|
| P0 (Phase 4) | Compliance file | Admins will see confusing empty compliance screens for legacy records |
| P0 (Phase 4) | Admin employee list | No way to identify legacy records currently |
| P1 (Phase 4) | Application viewer | Blank panel is confusing |
| P2 (optional) | Recruitment pipeline | Low traffic from legacy, but provenance indicator is cheap |
| P3 (optional) | Worker dashboard | Graceful degradation already works |
| Skip | Task queue | Already safe |
| Skip | Employment review | Already guarded |

---

## 4. Reference Integrity Plan

### Current State (verified)

**Two collections exist:**

| Collection | Schema | Documents Per Employee | Writers | Readers |
|---|---|---|---|---|
| `db.references` | 1 doc with nested `ref1`/`ref2` sub-objects, each containing `declared`, `request`, `response`, `verification`, `mismatch` | 1 | Structured app submission, admin edit, referee outreach, worker dashboard | Compliance engine (×3), work readiness, referee outreach, task queue, compliance file, worker dashboard, profile-completion-status |
| `db.employee_references` | 1 doc per ref slot, flat structure with `referee_name`, `referee_email`, `status` | Up to 2 | Bulk import, worker profile wizard, worker dashboard (declares new referee) | Profile-completion-status (fallback), drift report, aggregated reference view, worker profile data |

### Which Collection is Canonical

**`db.references`** is canonical. Non-negotiable.

Reasons:
- All compliance checks read from `references` (unified_compliance_engine L655, work_readiness_engine L715/L1142, compliance_engine/status.py L459)
- All verification lifecycle (request → submit → review → verify/reject) operates on `references`
- Referee outreach (send email, token, public form submission) operates on `references`
- The compliance-file builder reads `references`
- The task queue reads `references` for pending reviews

`employee_references` is a legacy parallel store that:
- Was created for bulk-import (which is being retired)
- Is read as a **fallback** only when `references` is empty
- Has no verification lifecycle, no request/response model, no outreach integration
- Goes stale the moment the referee outreach lifecycle begins (outreach writes only to `references`)

### Reads That Must Change

| File | Line | Current Read | Change |
|---|---|---|---|
| `compliance_engine/status.py` | L459 | `db.references.find()` then `r.get("status")` | **BUG FIX:** Rewrite to `find_one()`, read `ref1.verification_status` and `ref2.verification_status`. This is broken today regardless of this rollout. |
| `routes/workers.py` | L211 | `db.employee_references.find()` — worker profile data fill | Change to read from `db.references` `ref{N}.declared` fields. Fall back to employee flat fields if `references` doc doesn't exist. Remove `employee_references` read. |
| `routes/workers.py` | L338–374 | `db.references.find_one()` primary → `db.employee_references.find()` fallback → employee flat fields fallback | Remove the `employee_references` fallback. Keep: `db.references.find_one()` → employee flat fields. |

### Writes That Must Change

| File | Line | Current Write | Change |
|---|---|---|---|
| `routes/workers.py` | L474 | Worker wizard saves referee to `db.employee_references` only | Change to upsert into `db.references` `ref{N}.declared` sub-document. Format: `{"$set": {"ref{N}.declared.name": ..., "ref{N}.declared.email": ..., ...}}` |
| `routes/worker_dashboard.py` | L2617 | Worker declares referee → writes to `db.references` `ref{N}.declared` | Already correct. Keep. |
| `routes/worker_dashboard.py` | L2642–2649 | Worker declares referee → ALSO writes to `db.employee_references` | **Remove the `employee_references` write.** This is a triple-write (employees + references + employee_references). Reduce to dual-write (employees + references). |
| `server.py` | L12712 | Bulk import → `db.employee_references.insert_one()` | Endpoint is being retired in Phase 2. No change needed — dead code after Phase 1. |

### Migration Required

**Yes.** For any employee that has `employee_references` docs but NO `references` doc:

```python
# Pseudocode for one-time migration
for emp_ref in db.employee_references.find({}):
    employee_id = emp_ref["employee_id"]
    ref_num = emp_ref["reference_number"]  # 1 or 2
    slot = f"ref{ref_num}"
    
    # Only create if no references doc exists for this employee
    existing = await db.references.find_one({"employee_id": employee_id})
    if not existing:
        await db.references.insert_one({
            "employee_id": employee_id,
            "ref1": None,
            "ref2": None,
            "created_at": now,
            "migrated_from": "employee_references"
        })
    
    # Upsert declared data into the correct slot
    await db.references.update_one(
        {"employee_id": employee_id},
        {"$set": {
            f"{slot}.declared.name": emp_ref.get("referee_name"),
            f"{slot}.declared.email": emp_ref.get("referee_email"),
            f"{slot}.declared.phone": emp_ref.get("referee_phone"),
            f"{slot}.declared.organisation": emp_ref.get("referee_organisation"),
            f"{slot}.declared.relationship": emp_ref.get("referee_relationship"),
            f"{slot}.verification_status": emp_ref.get("status", "pending"),
            f"{slot}.declared.migrated_from": "employee_references",
            f"{slot}.declared.migrated_at": now
        }}
    )
```

After migration, do NOT delete `employee_references` docs — keep them as historical audit trail. But all reads/writes switch to `references` only.

### What Breaks If This Is Not Fixed Before Broader Rollout

1. **Any employee created via bulk import has zero reference status in compliance/readiness.** Their `employee_references` data is invisible to the compliance engine, work readiness engine, reference verification UI, and task queue. These employees appear to have no references at all. 

2. **Worker wizard creates orphaned reference data.** When a worker completes the profile wizard and enters referee details, those go into `employee_references` (L474) but NOT into the `references` collection that compliance reads. The worker thinks they've provided referees; admin sees no references in the compliance file.

3. **The `compliance_engine/status.py` L459 bug** means reference status is already broken for ALL employees, regardless of collection. This must be fixed first.

---

## 5. Legacy Migration Decision Rules

### Rule 1: Archive Immediately

**Criteria:** Employee record where ALL of the following are true:
- `application_source` NOT `"online_structured"`
- `status` in `["new", "screening", "withdrawn", "superseded"]`
- NO `worker_accounts` record exists
- NO verified `employee_documents` exist
- NO verified references exist (in either collection)
- `created_at` older than 90 days

**Action:** Set `status: "archived"`, add `archived_at`, `archived_reason: "legacy_intake_retired"`.

**Rationale:** These records entered via a retired path, never progressed, have no linked data worth preserving, and will never be promoted to canonical status. Archiving removes them from default list views and pipeline counts.

### Rule 2: Admin-visible but flagged (temporary)

**Criteria:** Employee record where:
- `application_source` NOT `"online_structured"`
- `status` in `["interview", "compliance_review", "onboarding"]` — actively progressing
- Some linked data exists (documents uploaded, references declared, etc.)

**Action:** Do NOT archive. Add field `legacy_intake: true` and `legacy_intake_notice: "Record created before online-only enforcement. May lack canonical application form."` Display this notice in the compliance file and employee profile.

**Rationale:** These records are mid-pipeline. Archiving would disrupt active workflows. The admin needs to decide per-record: push through to completion manually, or ask the applicant to reapply online.

### Rule 3: One-time backfill candidates

**Criteria:** Employee record where:
- `application_source` NOT `"online_structured"`
- `status` in `["active", "onboarding"]` — already working or about to start
- Has `recruitment_approved: true`
- Has verified documents in `employee_documents`

**Action:** Run `backfill_execute()` from `application_resolver.py` to create a synthetic `form_submission` with `requirement_id: "application_form"` and `provenance: "backfilled_from_{source}"`.

Also run `StageGateService.generate_requirements_for_employee()` if requirement slots are missing.

**Rationale:** These employees are already approved and may be actively working. Backfilling makes their compliance file accurate and removes the "Application Form: Not completed" row that would otherwise persist permanently. The backfilled record is clearly stamped as non-canonical.

### Rule 4: Never promote to canonical

Records that should **never** be treated as having canonical application data, even after backfill:

- Any record where `form_submission.provenance` starts with `"backfilled_from_"`
- Any record with `application_source` in `["online_legacy", "admin_simple", "offline_pdf_import", "internal"]` AND no real (non-backfilled) `form_submission`

**Why:** Backfilled form_submissions contain admin-entered or system-extracted data, not worker-attested declarations. They satisfy the compliance file display requirement but do NOT carry the same attestation weight as an online structured application where the worker personally entered and submitted their data.

**Operational consequence:** Employment review sign-off (which checks for `form_submission` existence) will pass for backfilled records. This is acceptable because:
1. The record already has `recruitment_approved: true`
2. The backfill provenance is on record
3. The admin made a conscious decision to approve before the policy change

### Field-level backfill rules

| Field | Can Backfill From | Cannot Backfill — Requires Worker Attestation |
|---|---|---|
| `first_name`, `last_name`, `email`, `phone` | Admin-entered data on employee doc | — |
| `date_of_birth`, `ni_number` | Employee doc (if present) | If missing: requires worker to enter |
| `address` fields | Employee doc (if present) | If missing: requires worker to update profile |
| `employment_history` | Employee doc (if present, e.g. from PDF extraction) | If missing: cannot backfill — worker must declare |
| `declarations` (criminal convictions, DBS consent, right-to-work, health) | **Cannot backfill under any circumstance** | Always requires worker attestation |
| `references` (referee contact details) | Employee doc flat fields OR `employee_references` docs | — |
| `equal_opportunities` | **Cannot backfill** | Optional — worker may decline |
| `next_of_kin` / `emergency_contact` | Employee doc (if present) | If missing: requires worker to enter |

---

## 6. Final Target Architecture

### End State (strict)

1. **One-way online application only.** `POST /applications/structured` is the sole applicant creation path. No alternatives exist in the API.

2. **`POST /employees` (admin create) remains** for operational flexibility — creating stub records for phone/walk-in applicants who will be directed to complete the online form. These records receive `application_source: "internal"` and have no `form_submission`. They are visually flagged in the UI and cannot pass employment review sign-off until a canonical application form is on file.

3. **No bulk / manual / PDF applicant intake.** Endpoints disabled (Phase 1–2). Frontend entry points removed (Phase 2). Models retained temporarily for import compatibility, deleted in Phase 7.

4. **No ProfileCompletionWizard.** The wizard existed solely for bulk-imported workers. It is deleted (Phase 5) after confirming zero active users. Workers who need to update their profiles use standard profile edit endpoints.

5. **Single reference collection.** `db.references` is the sole canonical reference store. `db.employee_references` is a retired historical collection — no live code reads from or writes to it after Phase 3. Existing data preserved for audit trail.

6. **Canonical application consumers operate on `form_submissions` existence.** Runtime guards key off `form_submissions` with `requirement_id: "application_form"`, not `application_source` labels. This is the single source of truth for "did this person go through a real application process."

7. **Legacy records either migrated or retired.**
   - Inactive/stale legacy records: archived with `legacy_intake_retired` reason
   - Active legacy employees: backfilled with clearly stamped `provenance: "backfilled_from_{source}"`
   - Mid-pipeline legacy applicants: flagged for admin resolution, not auto-promoted

8. **No hidden assumptions.** Every runtime surface that displays employee/applicant data either:
   - Already handles missing `form_submissions` gracefully (dashboard, task queue), OR
   - Has an explicit guard rejecting the operation (employment review sign-off), OR
   - Displays a clear provenance indicator (compliance file, employee list)

### Collections post-rollout

| Collection | Status | Contents |
|---|---|---|
| `employees` | Active | All employee/applicant records. `application_source` field retained as metadata. |
| `form_submissions` | Active | Only records from online structured apps + backfilled records with `provenance` stamp. |
| `references` | Active (sole canonical) | One doc per employee with nested `ref1`/`ref2`. All verification lifecycle lives here. |
| `employee_references` | Retired (read-only archive) | Historical data from bulk imports and wizard submissions pre-Phase 3. No live reads or writes. |
| `employee_documents` | Active | Requirement slots. Legacy employees may need slots generated via StageGateService backfill. |
| `worker_accounts` | Active | Unchanged — created on recruitment approval regardless of source. |
| `magic_tokens` | Active | Unchanged — ephemeral auth tokens. |

### API surface post-rollout

| Endpoint | Status |
|---|---|
| `POST /applications/structured` | Active — sole applicant entry |
| `POST /employees` | Active — admin stub creation only |
| `POST /apply` | 410 Gone |
| `POST /employees/simple` | 410 Gone |
| `POST /admin/employees/bulk-import` | 410 Gone |
| `POST /admin/employees/extract-from-pdf` | 410 Gone |
| `GET /admin/employees/import-template` | 410 Gone |
| All other endpoints | Unchanged |
