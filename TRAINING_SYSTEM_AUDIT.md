# Training System — Strict Code-Level Audit

**Date:** 2026-04-16  
**Scope:** Every write path, read path, data model, and broken behavior in training state management  
**Method:** Verified against actual code at file/line level

---

## 1. Training Write-Path Audit

42 distinct write paths found. Categorized by risk.

### CRITICAL — Auto-completes training without controlled review

| # | Endpoint / Function | File | Line | Writes To | What Happens | Risk |
|---|---|---|---|---|---|---|
| W8 | `POST /{eid}/training/bulk-upload` | server.py | L11576 | `training_records` | **AI extracts trainings → inserts records directly with `status="completed"`, `verified=False`.** No admin preview step. Every extracted item becomes a completed training record immediately. | **CRITICAL** — one cert can create 40+ uncontrolled training outcomes |
| W13 | Unified evidence upload (training branch) | server.py | L15150 | `training_records` | Sets `completion_date=now` on evidence upload. Runtime derives "completed". | **HIGH** — uploading evidence auto-completes |
| W25 | `POST /training-records/{id}/upload-certificate` | server.py | L22131 | `training_records` | Sets `completion_date=now` → runtime derives "completed" | **HIGH** — certificate upload auto-completes |
| W26 | `POST /{eid}/training/{req}/upload-certificate` | server.py | L22252 | `training_records` | Creates or updates record with `completion_date=now` | **HIGH** — same auto-complete on upload |
| W27 | `POST /{eid}/complete-training` | server.py | L22406 | `training_records` | Sets `completion_date` directly | **MEDIUM** — admin action, but no verification gate |
| W32 | `POST /{eid}/training/manual` | server.py | L40046 | `training_records` | `status="completed"`, `verified=False` | **MEDIUM** — admin manual entry |
| W41 | `POST /admin/sync-verification-status/{eid}` | routes/verification_sync.py | L160 | `training_records` | **Auto-sets `verified=True`** based on source document status | **HIGH** — auto-verification without manual check |

### MEDIUM — Admin-gated but writes directly

| # | Endpoint / Function | File | Line | Writes To | What Happens | Risk |
|---|---|---|---|---|---|---|
| W4 | `POST /{eid}/training/record` | server.py | L10945 | `training_records` | `status="completed"`, `verified=False` | MEDIUM |
| W5 | `POST /{eid}/training/{id}/verify` | server.py | L11035 | `training_records` | `verified=True` + auto-completes induction item | MEDIUM (intended flow) |
| W11 | `POST /{eid}/training/bulk-save` | server.py | L12008 | `training_records` | Post-extraction admin confirm. `verified=False` | MEDIUM (gated) |
| W24 | `PATCH /{eid}/training/{req}` | server.py | L21981 | `training_records` | Can directly set `verified=True` | MEDIUM |
| W28 | `POST /training-records/{id}/correct` | server.py | L22661 | `training_records` | Updates dates/status. Audit trail required. | LOW |
| W29 | Extraction review: approve | server.py | L27280 | `training_records` | `verification_status="awaiting_review"` | MEDIUM (gated) |
| W30 | `TrainingIntakeService.review_proposed_items()` | server.py | L39430 | `training_records` | `status="completed"`, `verified=False` from approved proposals | MEDIUM (gated) |

### LOW — Controlled operations

| # | Endpoint / Function | File | Writes To | Risk |
|---|---|---|---|---|
| W1 | `get_or_create_training_record()` | server.py L7120 | `training_records` | LOW — creates blank record |
| W2 | `supersede_training_record()` | server.py L7173 | `training_records` | LOW — marks old record superseded |
| W3 | `POST /{eid}/training/assign` | server.py L10891 | `employee_training_assignments` (NOT training_records) | LOW |
| W6 | `POST /{eid}/training/{id}/reject` | server.py L11142 | `training_records` | LOW — intended flow |
| W7 | `POST /{eid}/training/{id}/unverify` | server.py L11208 | `training_records` | LOW — admin action with reason |
| W12 | `POST /{eid}/training/deduplicate` | server.py L12133 | `training_records` | LOW — supersedes duplicates |
| W14–18 | Evidence file delete/supersede/edit | server.py L15570–16510 | `training_records` | LOW |
| W19 | Unified verify requirement | server.py L17730 | `training_records` | LOW — admin verification |
| W20 | Unified unverify | server.py L17900 | `training_records` | LOW |
| W36–40 | `routes/training.py` CRUD | routes/training.py | `training_records` | LOW — standard CRUD |

### SAFE — Preview/proposal only (no direct writes)

| # | Endpoint / Function | File | Writes To | Notes |
|---|---|---|---|---|
| W9 | `POST /{eid}/training/extract-certificate` | server.py L11748 | **Nothing** | Preview only — returns extracted data |
| W10 | `POST /{eid}/training/re-extract` | server.py L11866 | **Nothing** | Preview only |
| W31 | `POST /{eid}/training/intake/from-upload` | server.py L39944 | `employee_documents` | Creates proposed items, NOT training_records |
| W34 | `POST /training/respond/{token}/upload` | server.py L39824 | `employee_documents` | Public token upload → proposed items only |
| W35 | Worker dashboard upload | routes/worker_dashboard.py L1837 | `training_records` | Updates evidence only, not completion |

---

## 2. Training Read-Path Audit

### Canonical evaluator (the one that SHOULD be used everywhere)

| Function | File | Line | Reads From | Used By |
|---|---|---|---|---|
| `compute_training_record_status()` | server.py | L6628 | Single `training_records` doc | Per-record status computation |
| `evaluate_employee_training_status()` | server.py | L6862 | `training_records` only | `GET /{eid}/training`, `GET /{eid}/training/matrix`, `GET /dashboard/training-summary`, audit exports |

### Independent evaluators (DO NOT call the canonical one)

| # | Evaluator | File | Line | Reads From | Problem |
|---|---|---|---|---|---|
| E3 | `UCE is_training_valid()` | unified_compliance_engine.py | L483 | `training_records` | Checks `verified` OR `status=="verified"` OR `computed_status=="verified"`. Does NOT call `compute_training_record_status()`. Checks expiry independently. |
| E4 | Worker dashboard inline | routes/worker_dashboard.py | L688 | `training_records` | Own expiry/status logic. Does NOT call canonical evaluator. |
| E5 | Work readiness engine | work_readiness_engine.py | L310 | `training_records` | Own `verified` check + expiry check. Does NOT call canonical evaluator. |
| E6 | Legacy compliance engine | compliance_engine/status.py | L489 | `training_records` + `training_types` | **Completely different ID system.** Queries `training_types` collection. Also no `record_status` filter — includes superseded/deleted records. |

**Disagreement scenarios:**

| Scenario | Canonical evaluator says | UCE says | Worker dashboard says | Work readiness says |
|---|---|---|---|---|
| Record has `completion_date`, not expired, `verified=False` | `completed` | **INVALID** (requires verified) | `complete` (ignores verification) | **INVALID** (requires verified) |
| Record has `status: "completed"` stored (legacy), no `completion_date` | `not_started` | **VALID** (reads stored `status`) | depends on stored `status` | **VALID** (reads stored `status`) |
| Record has `completion_date`, expired, `verified=True` | `expired` | **INVALID** (expiry checked) | `expired` | **INVALID** (expiry checked) |

### Frontend components and their data sources

| Component | File | API Endpoint(s) | Source | Problem |
|---|---|---|---|---|
| `AuditReadyTrainingMatrix` — Mandatory tab | AuditReadyTrainingMatrix.js | `GET /{eid}/training/matrix` | `training_records` via canonical evaluator | OK |
| `AuditReadyTrainingMatrix` — **Certificates tab** | AuditReadyTrainingMatrix.js L152 | `GET /employee-documents?employee_id={eid}` | **`employee_documents`** filtered by `document_type='training_certificate'` | **BROKEN** — bulk-upload writes certs to `training_records.certificate_url`, NOT `employee_documents`. Certificates tab shows nothing for bulk-uploaded certs. |
| `EnhancedTrainingTab` | EnhancedTrainingTab.js | `GET /{eid}/training-records` | `training_records` raw | **LOCAL date calculation** via `isExpired()` / `getDaysUntilExpiry()` in frontend JS. Contradicts canonical backend computation. |
| `TrainingDetailDrawer` — cert view | TrainingDetailDrawer.js L122 | `GET /training-records/{id}/certificate/file` | Calls `get_object()` (Supabase storage) | **BROKEN** — bulk-upload saves to local disk `/app/uploads/training/`, but `get_object()` queries Supabase. File not found. |
| `TrainingMatrix` | TrainingMatrix.js | `GET /{eid}/training/matrix` with fallback to `/training` | `training_records` via evaluator | OK |
| `WorkerDashboard` — training section | WorkerDashboard.js | `GET /worker/dashboard` | Worker dashboard inline evaluator | Independent logic, may disagree with admin views |
| `ComplianceCentrePage` | ComplianceCentrePage.js | `GET /compliance/reports/training` | training_records only | OK |
| `EmployeeProfilePage` | EmployeeProfilePage.js | Mixed: `/training-records`, `/training`, `/compliance-requirements`, `/unified-progress` | **MIXED** — training_records + employee_documents + compliance requirements | May show conflicting counts |

### Backend read paths with mixed sources

| Surface | File | Line | Sources Mixed | Risk |
|---|---|---|---|---|
| `get_compliance_requirements_for_employee()` | server.py | L795 | training_records + employee_documents + generated_forms | HIGH — cross-collection |
| `calculate_expiry_alerts_quick()` | server.py | L2679 | training_records + employee_documents | MEDIUM — double-counting |
| `induction_definitions._build_verified_training_set()` | induction_definitions.py | L290 | training_records + employee_documents (regex on requirement_id) | HIGH — training appears verified from doc upload OR from training record |
| `derive_onboarding_status()` | server.py | L5046 | training_records + employee_documents + generated_forms | MEDIUM |
| `compliance_engine/status.py _get_training_status()` | compliance_engine/status.py | L489 | training_records + training_types | HIGH — includes superseded records, uses different ID system |
| `routes/verification_sync.py` | verification_sync.py | L160 | training_records + employee_documents (source_document_id) | HIGH — auto-verifies |

---

## 3. Canonical Data Model Audit

### `training_records` document — no enforced schema

There is **no Pydantic model** enforcing the document shape at insert time. Records are written as raw dicts. The field set varies by creation point.

**Field inconsistencies across creation points:**

| Field | `get_or_create` | `bulk-upload` (AI) | `bulk-save` | `manual` | `upload-certificate` | `intake review` |
|---|---|---|---|---|---|---|
| `status` | not set | `"completed"` | not set | `"completed"` | not set | `"completed"` |
| `mandatory` | `True` | varies | not set | not set | not set | `True` |
| `is_mandatory` | not set | varies | varies | not set | not set | not set |
| `requirement_id` | set | not set | set | set | set | set |
| `training_id` | not set | set | set | not set | not set | not set |
| `training_code` | not set | not set | set | not set | not set | not set |
| `provider` | not set | set | set | not set | not set | set |
| `provider_name` | not set | not set | not set | set (alias!) | not set | not set |
| `evidence_files` | `[]` | not set | not set | not set | not set | set |
| `verification_status` | not set | not set | `"pending"` | not set | not set | `"awaiting_review"` |
| `completion_method` | not set | not set | not set | `"manual"` | `"certificate"` | `"certificate"` |

### Training requirement definitions — **4 CONFLICTING LISTS**

| Location | File | Items | Missing From Others |
|---|---|---|---|
| `MANDATORY_TRAINING_HCA` | unified_compliance_engine.py L52 | 8 (safeguarding_adults, manual_handling, fire_safety, health_safety, basic_life_support, infection_control, information_governance, prevent) | Uses `safeguarding_adults` while everyone else uses `safeguarding` |
| `MANDATORY_ITEMS["training"]` | server.py L1230 | 8+ items with full metadata | Has role-specific L2/L3 safeguarding |
| `mandatory_trainings` | routes/worker_dashboard.py L688 | 8 items | Standalone dict, not shared |
| `MANDATORY_TRAININGS` | server.py L11297 | **6 items** | **MISSING: information_governance, prevent** |
| `MANDATORY_TRAINING_BY_ROLE` | services/multi_training_extraction.py L26 | 8 per role | Per-role, uses different IDs |

### ID inconsistency

The same training appears under different IDs depending on which subsystem you ask:

| Training | UCE ID | MANDATORY_ITEMS ID | Worker Dashboard ID | Extraction ID |
|---|---|---|---|---|
| Safeguarding | `safeguarding_adults` | `safeguarding` | `safeguarding` | `safeguarding` |
| Manual Handling | `manual_handling` | `manual_handling` | `manual_handling` | `manual_handling` |
| BLS | `basic_life_support` | `bls` | `bls` | `basic_life_support` |

The canonical evaluator uses fuzzy matching (`training_name` normalization + `training_id` + `requirement_id`) to paper over these inconsistencies, but downstream consumers that do direct queries may miss records.

### Dual mandatory flag

Records can have `mandatory: true` and/or `is_mandatory: true`. Different creation paths set one or the other. Some set both. Some set neither but the training is actually mandatory.

### Stored `status` vs computed `status`

- Old creation paths write `status: "completed"` directly on the record
- Newer hardened paths do NOT write `status` — they rely on `compute_training_record_status()` to derive it from `completion_date`/`expiry_date`
- UCE and work readiness engine read `status` from the record AND check `computed_status` — so old records with stale `status: "completed"` but expired `expiry_date` may still pass as valid in some evaluators

### Employee-level training fields (orphaned)

| Field | Where | Connection to training_records |
|---|---|---|
| `employee.care_certificate_completed` | Set on structured application | **None** — never synced |
| `employee.mandatory_training_completed` | Set on structured application (list of strings) | **None** — never synced |

---

## 4. Broken Behavior Audit

### Bug 1: One certificate extracted many wrong qualifications

**Root cause:** `POST /{eid}/training/bulk-upload` (server.py L11576) calls AI extraction (`extract_training_from_certificate()` + `extract_multiple_trainings_from_certificate()`) and **immediately inserts every extracted item as a completed training record** without any admin review step.

The AI extraction service (`services/multi_training_extraction.py`) is designed to handle multi-training certificates (e.g. a certificate listing 40 CSTF modules). When the AI misidentifies content, every wrong item becomes a `status: "completed"` record.

**Code path:**
1. Upload hits `bulk_upload_training_certificates()` at L11576
2. AI extracts → returns list of trainings (L11651)
3. `extract_multiple_trainings_from_certificate()` categorizes (L11662)
4. **For loop at L11671** iterates every extracted training
5. **L11705** `db.training_records.insert_one(training_record)` — no review, no approval
6. Each record has `status: "completed"`, `verified: False`

**Contrast with the safe path:** `POST /{eid}/training/intake/from-upload` (L39944) creates `proposed_training_items` that require admin approval via `TrainingIntakeService.review_proposed_items()`. This path EXISTS but the bulk-upload endpoint bypasses it entirely.

**Affected files:** `server.py` L11576–11745, `services/multi_training_extraction.py`  
**Fix location:** Backend — `bulk-upload` must route through the intake/proposal flow, not direct insert

### Bug 2: No skip-extraction path

**Root cause:** The `bulk-upload` endpoint always runs AI extraction. There is no parameter or alternative endpoint to upload a certificate and manually assign it to a specific training without AI processing.

The closest alternatives are:
- `POST /training-records/{id}/upload-certificate` (L22131) — requires an EXISTING record ID
- `POST /{eid}/training/{req}/upload-certificate` (L22252) — requires knowing the requirement_id upfront
- Neither appears well-surfaced in the UI's primary upload flow

The `TrainingCertificateExtractor` component always triggers extraction. `AuditReadyTrainingMatrix` surfaces the extraction wizard as the primary upload UX.

**Affected files:** Frontend `TrainingCertificateExtractor.js`, `AuditReadyTrainingMatrix.js`; Backend `server.py` L11576  
**Fix location:** Both — need a "skip extraction, manually assign" UI path + backend support

### Bug 3: Uploaded certificate viewing is broken

**Root cause:** Storage path mismatch between write and read.

**Write path** (`bulk-upload` at L11623–11633):
```python
upload_dir = Path("/app/uploads/training") / employee_id  # LOCAL filesystem
file_url = f"/uploads/training/{employee_id}/{safe_filename}"  # Stored on record
```

**Read path** (`GET /training-records/{id}/certificate/file` at L22198):
```python
file_bytes, stored_content_type = get_object(record['certificate_url'])
```

**`get_object()` at L664:**
```python
resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key})
```

The `bulk-upload` saves files to **local disk** (`/app/uploads/training/`). The certificate view endpoint calls `get_object()` which queries **Supabase storage** with the path. The file doesn't exist in Supabase → 404/500.

**Contrast:** The single-cert upload endpoints (`upload_training_certificate` at L22131, `upload_training_certificate_for_requirement` at L22252) correctly use `put_object()` to upload to Supabase storage, storing the returned `result["path"]` as `certificate_url`.

**Affected files:** `server.py` L11623–11633 (write), L22198 (read), L664 (`get_object`)  
**Fix location:** Backend — `bulk-upload` must use `put_object()` instead of local file write

### Bug 4: Same training appears with different statuses in different tabs

**Root cause:** 6 independent status evaluators that don't share code.

| Evaluator | Example result for "completed but unverified, not expired" |
|---|---|
| Canonical `compute_training_record_status()` | `"completed"` |
| UCE `is_training_valid()` | **`False`** (requires `verified=True`) |
| Worker dashboard | `"complete"` (ignores verification) |
| Work readiness | **`False`** (requires `verified=True`) |
| `EnhancedTrainingTab` (frontend) | Own `isExpired()` calc — may disagree on edge-case dates |
| `compliance_engine/status.py` | Undefined — queries `training_types` collection with different IDs |

A training can show as "Completed" in the mandatory tab (canonical evaluator), "Missing/Incomplete" in compliance centre (UCE requires verification), and "Complete" on the worker dashboard (no verification check).

**Affected files:** All 6 evaluator locations above  
**Fix location:** Backend — all evaluators must delegate to `compute_training_record_status()` + `evaluate_employee_training_status()`

### Bug 5: Upload may auto-complete training without controlled review

**Root cause:** 4 certificate upload endpoints set `completion_date = now` automatically:
- `bulk-upload` (L11705): `status="completed"` + `completion_date`
- Evidence upload training branch (L15176): `completion_date=now`  
- `upload_training_certificate` (L22176): `completion_date=now`
- `upload_training_certificate_for_requirement` (L22323/22362): `completion_date=now`

In all cases, uploading a certificate file immediately makes the training "completed" at the record level. The only gate is `verified=False` — but not all read paths check verification. The worker dashboard, the canonical evaluator's `computed_status`, and `EnhancedTrainingTab` all treat an unverified-but-completed record as complete.

**Affected files:** `server.py` at all 4 upload paths  
**Fix location:** Backend — certificate upload should add evidence only, not set `completion_date`

---

## 5. Source-of-Truth Verdict

### What MUST be the single source of truth

**`training_records`** — one collection, one evaluator.

- `compute_training_record_status()` and `evaluate_employee_training_status()` already exist as the designated canonical functions
- They read from `training_records` only
- They derive status from `completion_date` + `expiry_date` + `verified`
- They are already used by the primary admin views (`/training/matrix`, `/training`)

### What MUST become evidence only

| Item | Current Role | Target Role |
|---|---|---|
| Uploaded certificate files | Auto-complete training on upload | **Evidence only** — certificate goes into `evidence_files[]` or `certificate_url`. Does NOT set `completion_date`. |
| `employee_documents` with `training_certificate` type | Read by Certificates tab | **Should not exist for training.** Training evidence lives on `training_records.evidence_files[]`. The Certificates tab should read from `training_records` records that have evidence files. |

### What MUST become suggestion only

| Item | Current Role | Target Role |
|---|---|---|
| AI extraction results from `bulk-upload` | **Direct insert** into `training_records` as completed | **Proposed items only** — extraction creates `proposed_training_items` (like the intake flow at L39944). Admin reviews and approves before any training_record is created. |
| `extract_multiple_trainings_from_certificate()` output | Consumed directly by bulk-upload insert loop | **Suggestion payload** — returned for preview, never written until explicit approval. |

### What MUST stop mutating training status automatically

| Write Path | What It Does Wrong | Required Change |
|---|---|---|
| `bulk-upload` (W8) | Inserts completed records directly from AI extraction | Route through proposal/approval flow |
| Evidence upload training branch (W13) | Sets `completion_date=now` | Evidence only — don't set completion_date |
| `upload_training_certificate` (W25) | Sets `completion_date=now` | Evidence only |
| `upload_training_certificate_for_requirement` (W26) | Sets `completion_date=now` | Evidence only |
| `sync-verification-status` (W41) | Auto-sets `verified=True` | Remove auto-verify or require admin confirmation |

---

## 6. Safe Rollout Order

### Phase 0 — STOP: Fix uncontrolled writes (highest priority)

**Objective:** Stop the bulk-upload endpoint from creating uncontrolled training outcomes.

1. **Redirect `bulk-upload` through proposal flow.** Change `POST /{eid}/training/bulk-upload` to create `proposed_training_items` (like the intake flow) instead of direct `training_records` inserts. The endpoint already has a safe parallel: `POST /{eid}/training/intake/from-upload`.
2. **Fix certificate storage.** Change `bulk-upload` to use `put_object()` (Supabase) instead of local disk write. This fixes certificate viewing immediately.
3. **Remove auto-verification sync.** Disable or gate `POST /admin/sync-verification-status/{eid}` auto-verify behavior.

### Phase 1 — GATE: Certificate upload stops setting completion

**Objective:** Uploading a certificate adds evidence but does NOT auto-complete.

1. Remove `completion_date = now` from all 4 upload paths (W13, W25, W26, and W8's replacement).
2. Certificate upload writes to `evidence_files[]` or `certificate_url` only.
3. Admin must explicitly call `POST /{eid}/complete-training` or `POST /{eid}/training/record` to set completion.
4. Add a "skip extraction, manually assign" UI path for certificates that don't need AI.

### Phase 2 — UNIFY: Single status evaluator

**Objective:** All runtime surfaces call the canonical evaluator. No independent status computation.

1. UCE `is_training_valid()` must delegate to `compute_training_record_status()`.
2. Worker dashboard must call `evaluate_employee_training_status()` instead of inline logic.
3. Work readiness engine must call canonical evaluator.
4. `compliance_engine/status.py _get_training_status()` must be rewritten to use canonical evaluator (also fix the broken `find()` + `status` field read).
5. `EnhancedTrainingTab.js` frontend — remove local `isExpired()`/`getDaysUntilExpiry()`. Use backend-computed values only.
6. `induction_definitions._build_verified_training_set()` must read from `training_records` only, not `employee_documents`.

### Phase 3 — UNIFY: Single training requirements definition

**Objective:** One list of mandatory trainings, one set of IDs.

1. Create `backend/training_definitions.py` as the single definition file.
2. Define canonical IDs, display names, blocker flags, role-specific requirements.
3. Import from this file in: UCE, worker dashboard, server.py evaluator, extraction service.
4. Fix `MANDATORY_TRAININGS` (server.py L11297) — missing IG and Prevent.
5. Normalize ID inconsistency (`safeguarding_adults` → `safeguarding`, `basic_life_support` → `bls`, etc.).

### Phase 4 — CLEAN: Schema enforcement

**Objective:** Every `training_records` insert uses a validated Pydantic model.

1. Create a `TrainingRecordInsert` Pydantic model with the canonical field set.
2. Remove the stored `status` field — always derive via `compute_training_record_status()`.
3. Normalize: `mandatory` only (remove `is_mandatory`), `provider` only (remove `provider_name`), `requirement_id` only (remove `training_code`).
4. Ensure all write paths go through the model.

### Phase 5 — CLEAN: Certificates tab data source

**Objective:** Certificates tab reads from `training_records` (not `employee_documents`).

1. Change `AuditReadyTrainingMatrix` certificates tab to query `GET /{eid}/training-records` filtered by records with `certificate_url` or `evidence_files`.
2. Remove the `GET /employee-documents?employee_id` query for training certificates.
3. Clean up any legacy training-related `employee_documents` data.

### Phase 6 — REMOVE: Dead/duplicate paths

**Objective:** Remove code that is no longer needed.

1. Remove `MANDATORY_TRAININGS` 6-item list from server.py (replaced by unified definitions).
2. Remove `training_types` collection dependency from `compliance_engine/status.py`.
3. Remove `employee.care_certificate_completed` and `employee.mandatory_training_completed` orphaned fields.
4. Remove mixed-source reads from `calculate_expiry_alerts_quick()`.
5. Archive `routes/training.py` duplicate CRUD if covered by server.py endpoints.

---

## Summary of Critical Findings

| Finding | Severity | Location |
|---|---|---|
| `bulk-upload` creates completed records directly from AI extraction — no review | **CRITICAL** | server.py L11576 |
| Certificate files saved to local disk, read from Supabase — viewing always fails | **CRITICAL** | server.py L11623 (write) vs L22198+L664 (read) |
| 6 independent status evaluators produce conflicting results | **HIGH** | 6 files listed in §2 |
| 4 certificate upload paths auto-set `completion_date` | **HIGH** | server.py L15176, L22176, L22323, L11705 |
| Certificates tab reads `employee_documents` but certs are on `training_records` | **HIGH** | AuditReadyTrainingMatrix.js L152 |
| 4+ conflicting mandatory training requirement lists | **HIGH** | UCE, server.py, worker_dashboard, extraction service |
| Training IDs inconsistent across subsystems | **HIGH** | safeguarding vs safeguarding_adults, bls vs basic_life_support |
| `MANDATORY_TRAININGS` list missing 2 items (IG, Prevent) | **MEDIUM** | server.py L11297 |
| `compliance_engine/status.py` includes superseded/deleted records in queries | **MEDIUM** | compliance_engine/status.py L489 |
| `sync-verification-status` auto-verifies without manual check | **MEDIUM** | routes/verification_sync.py L160 |
| `EnhancedTrainingTab` computes expiry locally in frontend JS | **MEDIUM** | EnhancedTrainingTab.js |
| Schema varies wildly across 6+ creation points — no Pydantic model | **MEDIUM** | All write paths |
| `mandatory` vs `is_mandatory` dual flag | **LOW** | Multiple creation paths |
| `provider` vs `provider_name` dual field | **LOW** | Multiple creation paths |
