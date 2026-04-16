# System Impact Assessment — Enforcing Online Structured Application as Sole Entry Path

**Date:** 2026-03-30  
**Scope:** What breaks, changes, or needs migration if we retire `POST /apply`, `POST /employees/simple`, `POST /admin/employees/bulk-import`, and optionally restrict `POST /employees`  
**Method:** Full code-path verification across backend and frontend  

---

## 1. Endpoint Impact

### Endpoints to RETIRE (disable or delete)

| # | Endpoint | Source Value | File | Line | Frontend Caller | Safe Action |
|---|----------|-------------|------|------|-----------------|-------------|
| 1 | `POST /apply` | `online_legacy` | server.py | L24878 | **None** (dead code) | **Delete** — no caller in frontend or backend. No linked records created (no form_submissions, no references, no requirement slots). Orphan endpoint. |
| 2 | `POST /employees/simple` | `admin_simple` | routes/employees.py | L235 | **None** (dead code) | **Delete** — near-duplicate of `POST /employees`, never called from frontend. |
| 3 | `POST /admin/employees/bulk-import` | `offline_pdf_import` | server.py | L12586 | BulkImportPanel.js | **Disable with 410 Gone** — has active frontend caller. Requires coordinated frontend removal. |
| 4 | `POST /admin/employees/extract-from-pdf` | *(helper for #3)* | server.py | *(nearby)* | BulkImportPanel.js | **Disable with 410 Gone** — orphaned without bulk-import. |

### Endpoints to RESTRICT (keep but narrow scope)

| # | Endpoint | Source Value | File | Line | Frontend Caller | Decision Required |
|---|----------|-------------|------|------|-----------------|-------------------|
| 5 | `POST /employees` | `internal` | server.py | L9261 | EmployeesPage.js "Add Employee" dialog | **DECISION POINT:** This is the admin "Add Employee" button. Options: (A) Retire entirely — force all applicants through public ApplyPage, (B) Keep as "create stub + invite to fill online form" — requires new "complete existing application" worker flow, (C) Keep unchanged — admin can still create minimal records. See §7 for recommendation. |

### Endpoints UNAFFECTED (the canonical path)

| # | Endpoint | Source Value | File | Line | Frontend Caller | Status |
|---|----------|-------------|------|------|-----------------|--------|
| 6 | `POST /applications/structured` | `online_structured` | server.py | L24961 | ApplyPage.js | **No change** — this IS the canonical path. |

### Downstream Endpoints That Reference Retired Sources (read-only)

| Endpoint / Module | What it does with `application_source` | Impact |
|---|---|---|
| `application_resolver.py` `resolve_application()` | Reads `application_source`, branches on `ONLINE_SOURCES` to set provenance | **Low** — continues to work for existing records. `ONLINE_SOURCES` set already only contains `"online_structured"`. Backfill functions become legacy-data-only tools. |
| `application_resolver.py` `backfill_dry_run()` / `backfill_execute()` | Skips `online_structured`, processes everything else | **Low** — useful for migrating existing legacy records, then can be retired. |

### Endpoints with ZERO `application_source` dependency

Every other endpoint in the system — recruitment pipeline, compliance, references, worker dashboard, approval, stage gates, task queues, all CRUD operations — has **zero** runtime dependency on `application_source`. Verified across all files.

---

## 2. Frontend Impact

### Files to DELETE

| File | Reason |
|------|--------|
| `src/components/admin/BulkImportPanel.js` | Entire component serves retired bulk-import endpoint |
| `src/pages/portal/BulkImportPage.js` | Thin wrapper around BulkImportPanel |

### Files to EDIT

| File | Change | Risk |
|------|--------|------|
| `src/App.js` | Remove BulkImportPage import (L41) + route (L116) | Low — route removal only |
| `src/components/portal/PortalLayout.js` | Remove "Bulk Import" nav entry (L26), remove unused `Upload` icon import | Low — nav cleanup only |
| `src/pages/portal/EmployeesPage.js` | **DECISION POINT:** The "Add Employee" dialog (L460–560) posts to `POST /employees`. If that endpoint is retired → remove dialog. If kept → no change. | Medium — see §7 |
| `src/components/worker/ProfileCompletionWizard.js` | Remove `isFromPdfImport` state (L30), `offline_pdf_import` check (L115), PDF-specific info banner (L696). If no remaining trigger source → delete entire component. | Low — dead code removal |
| `src/pages/worker/WorkerDashboard.js` | If ProfileCompletionWizard is deleted: remove import (L21), `profileCompletionStatus` state (L456), `checkProfileCompletion()` (L534), wizard banner (L1270), `<ProfileCompletionWizard>` render (L3334) | Medium — multiple touchpoints but all clearly scoped |

### Files UNAFFECTED

| File | Why |
|------|-----|
| `src/pages/public/ApplyPage.js` | Already uses ONLY `POST /applications/structured` |
| `src/components/compliance/ApplicationFormViewer.js` | No source branching |
| `src/components/employee/ApplicationDataPanel.js` | No source branching |
| `src/pages/public/AboutPage.js`, `RecruitmentPage.js`, `Footer.js` | Their `/apply` links point to the **public route** for ApplyPage (the canonical path) — these are correct and unchanged |

### Search term inventory (exhaustive frontend grep)

| Term | Files Found | Action |
|------|-------------|--------|
| `application_source` | 0 files | No frontend code reads this field |
| `online_legacy` | 0 files | — |
| `offline_pdf_import` | 1 file (ProfileCompletionWizard.js L115) | Remove |
| `admin_simple` | 0 files | — |
| `bulk-import` / `bulk_import` | 4 files (App.js, BulkImportPanel, BulkImportPage, PortalLayout) | Delete/edit |
| `/employees/simple` | 0 files | — |
| `ProfileCompletionWizard` | 2 files (WorkerDashboard import + self) | Delete if wizard has no remaining purpose |
| `profile_completion_needed` | 0 files | Backend-only field |
| `import_source` | 1 file (ProfileCompletionWizard.js L115) | Remove |

---

## 3. Data / Model Impact

### Collections with source-dependent behavior

| Collection | `online_structured` creates? | Other sources create? | Impact if enforced |
|---|---|---|---|
| `employees` | Yes (full record) | Yes (varying completeness) | Existing non-online records stay. New records all go through structured path. **No schema change needed.** |
| `form_submissions` | **Yes** (application_form, equal_opportunities) | **No** — only structured apps create these | **CRITICAL:** Existing `internal`/`admin_simple`/`offline_pdf_import` employees have NO `form_submissions`. Compliance shows Application Form as perpetually incomplete. Work readiness reports those forms as not done. |
| `references` | **Yes** (single doc with ref1/ref2 slots) | **No** | Existing non-online employees have NO `references` doc. Their reference data (if any) lives in `employee_references` instead. |
| `employee_references` | **No** | **Yes** (bulk import + worker wizard) | **DUAL COLLECTION PROBLEM:** Two reference collections exist. `references` (structured apps) vs `employee_references` (bulk imports + worker wizard updates). Profile-completion-status checks `references` first, falls back to `employee_references`. |
| `employee_documents` | **Yes** (requirement slots via StageGateService) | **No** (requirement slots NOT generated) | Existing non-online employees may have NO requirement slots. They'd need manual slot generation or backfill before compliance can track their documents. |
| `employment_gaps` | Yes (auto-detected) | Bulk import: yes (different function). Others: no. | Minor inconsistency — different gap detection functions used (`detect_employment_gaps()` vs `detect_cv_gaps()`). |
| `magic_tokens` | Yes (7-day application welcome) | Bulk import: optionally. Others: no. | No impact — tokens are ephemeral. |
| `worker_accounts` | No (created on approval) | Bulk import: optionally (at import time — **violates "no account at application stage" constraint**) | Existing bulk-imported accounts that got early worker_accounts: no remediation needed, accounts already exist. |
| `audit_log` | Yes (direct insert) | Yes (mixed: direct insert vs `log_audit_action()` helper) | Historical audit entries have different shapes. Legacy entries store `"application_source": "online_legacy"` etc. No runtime impact — audit log is append-only. |

### Fields set ONLY by structured applications (missing from other sources)

| Field | Set by `online_structured` | Missing from `internal`/`admin_simple` | Missing from `offline_pdf_import` |
|---|---|---|---|
| `date_of_birth` | Yes | Yes | Sometimes present |
| `national_insurance` / `ni_number` | Yes | Yes | Sometimes present |
| `declarations` (nested object) | Yes | Yes | Sometimes present |
| `next_of_kin_*` / `emergency_contact_*` | Yes | Yes | Sometimes present |
| `employment_history` | Yes | Yes | Sometimes present |
| `reference_1_*` / `reference_2_*` (9 fields each) | Yes | Yes | No (uses `employee_references` instead) |
| `role_applied_raw` + normalized `role` + `system_role` | Yes | Raw role only, no normalization | Raw role only |
| `onboarding_status` | Yes | Yes | **Missing entirely** |
| `assignment` | Yes ("Unassigned") | Varies | **Missing entirely** |
| `completion_percentage` | Yes (0) | Yes (0) | **Missing entirely** |

---

## 4. Runtime Impact

### Runtime surfaces verified — NONE branch on `application_source`

| Runtime Surface | Checks `application_source`? | Checks `form_submissions`? | Impact |
|---|---|---|---|
| Recruitment pipeline (`GET /recruitment/applicants`, `/pipeline`) | **No** | **No** | **None** — all applicants appear regardless of source. Legacy applicants remain visible. |
| Unified compliance engine | **No** | **Yes** (queries for form compliance) | **Medium** — employees without `form_submissions` show Application Form as incomplete forever. Functionally correct but visually noisy for legacy records. |
| Work readiness engine | **No** | **Yes** (checks form completion for readiness) | **High** — employees without `form_submissions` can **never reach work-ready** for form-dependent requirements (application_form, health_questionnaire, equal_opportunities). |
| Worker dashboard | **No** | **No** (indirectly via compliance) | **Low** — renders fine. Shows form sections as "to-do" for legacy employees. |
| Approval engine | **No** | **No** | **None** — `application_form` is in `NON_BLOCKING_REQUIREMENTS`. Missing form does NOT block recruitment approval. Generates warning only. |
| Stage gate validation | **No** | **No** | **None** — purely document-slot based (RTW, DBS, identity, references). |
| Task queue / background | **No** | **No** | **None** |
| Email automation | **No** | **No** | **None** |
| Application resolver | **Yes** (core logic) | **Yes** (writes form_submissions) | **Low** — continues to work. Backfill functions remain useful for legacy data migration, then become inert for new records. |

### Key finding: `application_source` is WRITE-ONLY everywhere except `application_resolver.py`

No recruitment, compliance, dashboard, approval, stage gate, or task queue code EVER reads `application_source`. It is metadata set once at creation, never consulted in live business logic. The real runtime impact comes from **presence/absence of `form_submissions`**, not from the source value itself.

---

## 5. Migration Impact

### Category A — Records that can be archived immediately (zero dependencies)

| Source | Criteria | Safe Action |
|---|---|---|
| `online_legacy` | Status = `new`, `withdrawn`, `superseded`, `archived` | Archive directly. No form_submissions, no references, no requirement slots were ever created. Zero linked data. |
| `admin_simple` | Status = `new`, `archived` AND no linked `employee_documents` or `references` | Archive if no downstream data. Check first. |

### Category B — Records that need form_submission backfill before they can reach compliance

| Source | Issue | Remediation |
|---|---|---|
| `internal` (admin create) | No `form_submissions`, no `references` doc, no `employee_documents` requirement slots | Run `application_resolver.backfill_execute()` to create synthetic `form_submission`. Then run `StageGateService.generate_requirements_for_employee()` to create requirement slots. Then create `references` doc from employee flat fields or `employee_references` entries. |
| `offline_pdf_import` (bulk import) | No `form_submissions`, references in wrong collection (`employee_references` not `references`), requirement slots may be missing | Same as above PLUS: migrate `employee_references` → `references` collection for affected employees. |

### Category C — Active employees past compliance (handle carefully)

| Source | Issue | Remediation |
|---|---|---|
| Any non-online source with status `ACTIVE` | Already approved and working. May have complete compliance file via manual document uploads. Missing `form_submissions` is cosmetic. | **Option 1:** Backfill `form_submissions` from employee doc fields (stamps as `"backfilled"`). **Option 2:** Leave as-is — they're already compliant. The missing Application Form row is non-blocking. |

### Dual reference collection migration

| Current State | Target State | Migration |
|---|---|---|
| `references` collection: used by structured apps, compliance engine, verification flows | Keep as canonical | No change |
| `employee_references` collection: used by bulk imports, worker wizard | **Migrate data into `references`** format, then deprecate | For each employee with `employee_references` but no `references` doc: create a `references` doc from `employee_references` data. Map `reference_number: 1` → `ref1`, `reference_number: 2` → `ref2`. |

### `profile_completion_needed` flag

| Current State | Action |
|---|---|
| Set to `True` only by bulk import endpoint | Flag becomes inert once bulk import is retired. No new records will ever have it set. Existing records with `profile_completion_needed: True` can be cleaned up: if profile is actually complete, set to `False`; if not, those workers need to complete via portal. |

---

## 6. Rollout Risk Matrix

| # | Change | Impact | Severity | Rollback Difficulty | Sequence |
|---|--------|--------|----------|--------------------|----|
| 1 | Delete `POST /apply` endpoint | None — no callers | **None** | Trivial (re-add code) | **Phase 1** |
| 2 | Delete `POST /employees/simple` endpoint | None — no callers | **None** | Trivial | **Phase 1** |
| 3 | Disable `POST /admin/employees/bulk-import` + extract-from-pdf | Breaks BulkImportPanel. Admins lose PDF import capability. | **Medium** — operational change for admins | Easy (re-enable endpoint) | **Phase 2** (after frontend cleanup) |
| 4 | Delete BulkImportPanel.js, BulkImportPage.js, nav entry, route | UI cleanup. No one can navigate to dead page. | **Low** | Easy (restore files) | **Phase 2** (same deploy as #3) |
| 5 | Remove ProfileCompletionWizard + related WorkerDashboard code | Workers imported via bulk (if any remain with `needs_wizard`) lose the wizard flow. | **Medium** — check if any workers still have `profile_completion_needed: True` first | Medium (restore files + imports) | **Phase 3** (after confirming no active wizard users) |
| 6 | Decide on `POST /employees` (admin "Add Employee") | If retired: admins must tell applicants to apply online. If kept: no code change needed. | **High** (operational workflow change) | Easy (re-enable) | **Phase 4** (requires admin communication) |
| 7 | Backfill `form_submissions` for existing non-online employees | Makes compliance view accurate for legacy records. No runtime logic change. | **Low** — data enrichment only | Medium (cannot un-create form_submissions easily, but they're stamped as "backfilled") | **Phase 5** (use existing `backfill_execute()`) |
| 8 | Migrate `employee_references` → `references` | Unifies reference data into single collection. Required for legacy employees to appear correctly in reference verification flows. | **Medium** — data migration, potential for mismatch | Medium (need rollback script) | **Phase 5** (after backfill) |
| 9 | Generate missing `employee_documents` requirement slots for legacy employees | Enables compliance tracking for legacy employees who were never given requirement slots. | **Low** — creates missing records only | Easy (slots are additive) | **Phase 5** (after backfill) |
| 10 | Clean up `application_resolver.py` backfill functions | Remove code that only served legacy data migration. | **None** (dead code removal) | Trivial | **Phase 6** (after all migration complete) |

---

## 7. Final Recommendation

### Safest Rollout Order

**Phase 1 — Zero-risk deletions (deploy immediately)**
- Delete `POST /apply` — zero callers, zero linked data, zero risk.
- Delete `POST /employees/simple` — zero callers, duplicate of `POST /employees`.
- No frontend changes needed. No migration needed.

**Phase 2 — Bulk import retirement (single coordinated deploy)**
- Disable `POST /admin/employees/bulk-import` with 410 Gone.
- Disable `POST /admin/employees/extract-from-pdf` with 410 Gone.
- Delete `BulkImportPanel.js` and `BulkImportPage.js`.
- Remove nav entry from `PortalLayout.js`, route from `App.js`.
- **Pre-check:** Confirm with admin team that no bulk imports are pending or expected.

**Phase 3 — ProfileCompletionWizard cleanup**
- **Pre-check:** Query DB for `{profile_completion_needed: true, status: {$nin: ["archived", "withdrawn", "superseded"]}}`. If count > 0, those workers need to complete profiles first OR be manually resolved.
- Remove `isFromPdfImport` logic from ProfileCompletionWizard.
- If no remaining trigger path exists, delete the wizard entirely + WorkerDashboard references.

**Phase 4 — Admin "Add Employee" decision**
- **Recommended: KEEP `POST /employees` but document it as "admin stub creation only."** Retiring it forces all applicant entry through the public form, which is operationally rigid. Admin may need to create records for phone applicants, walk-ins, or agency referrals. The endpoint creates a minimal record with `application_source: "internal"` — this is metadata only, with zero runtime branching.
- If kept: no code change. Admins understand these records won't have structured application data.
- If retired: remove Add Employee dialog from EmployeesPage.js. Communicate to admins.

**Phase 5 — Legacy data reconciliation (background migration)**
- Run `backfill_dry_run()` to identify all non-online employees needing form_submissions.
- Run `backfill_execute()` to create synthetic form_submissions (stamped as `"backfilled_from_{source}"`).
- Migrate `employee_references` → `references` for affected employees.
- Run `StageGateService.generate_requirements_for_employee()` for employees missing requirement slots.
- **This phase is non-blocking.** The system works without it. It only makes compliance views accurate for legacy records.

**Phase 6 — Code cleanup**
- Remove `SOURCE_LABELS` entries for retired sources from `application_resolver.py`.
- Optionally archive `backfill_dry_run()` / `backfill_execute()` functions.
- Remove `profile_completion_needed` field handling from `routes/workers.py`.

### Biggest Risks

1. **Dual reference collection (`references` vs `employee_references`)** — This is the single most dangerous data inconsistency. The compliance engine reads `references`. The worker wizard writes `employee_references`. If bulk-imported employees have references verified through the `employee_references` path, those won't appear in compliance checks via the `references` collection. Migration in Phase 5 is important for data integrity.

2. **Work readiness engine blocks on missing form_submissions** — Existing non-online employees without `form_submissions` will be reported as not work-ready for form-dependent requirements. If any are currently `ACTIVE` and working, this is a cosmetic problem (they're already approved). But for any in `COMPLIANCE_REVIEW` or `ONBOARDING`, it could stall their pipeline until backfilled.

3. **Admin operational workflow change** — If `POST /employees` is retired, admins lose the ability to quickly add a record. This is the highest-risk operational change because it affects daily workflows, not just code.

### Places Most Likely to Break

| Location | Why | Severity |
|----------|-----|----------|
| Compliance file view for legacy employees | Application Form row shows "incomplete" forever until backfilled | **Cosmetic** — non-blocking for approval |
| Work readiness calculation for legacy employees in pipeline | Reports not-ready for form requirements | **Functional** — may confuse admins reviewing pipeline |
| ProfileCompletionWizard for in-flight bulk-imported workers | If wizard is deleted before they complete, they lose the guided flow | **Functional** — check DB count first |
| Reference verification for bulk-imported employees | Data in `employee_references` not visible to compliance engine reading `references` | **Data integrity** — migrate in Phase 5 |

### Bottom Line

The architecture is **surprisingly clean for this change.** `application_source` is write-only metadata with zero runtime branching outside the admin-only `application_resolver.py`. The real work is:
1. Disabling 3 dead/legacy endpoints (zero risk)
2. Removing bulk import UI (low risk, one coordinated deploy)  
3. Deciding on admin "Add Employee" (operational, not technical)
4. Migrating legacy data for compliance accuracy (important but non-blocking)
5. Unifying the dual reference collection (the one genuinely dangerous migration)
