# TRAINING SUBTAB AUDIT — Admin vs Worker Dashboard

**Date:** 2026-03-30  
**Scope:** Exact code-level audit of three admin training subtabs (Mandatory / All Qualifications / Certificates) and comparison with worker dashboard training section.  
**Status:** Audit-only. No changes implemented.

---

## Section 1 — Exact Subtab Audit

### 1.1 Mandatory Tab (`value="mandatory"`)

| Property | Value |
|----------|-------|
| **Component** | `AuditReadyTrainingMatrix.js` L483–665 |
| **Data source** | `mandatoryTraining` state → from `GET /api/employees/{eid}/training/matrix` → `response.items` |
| **Backend handler** | `server.py` L10708 `get_employee_training_matrix()` |
| **Evaluator called** | `evaluate_employee_training_status()` (canonical, L6862) → calls `compute_training_record_status()` (L6628) |
| **Required training list** | `get_required_training_for_employee()` (L1523) → `MANDATORY_ITEMS["training"]` |
| **Badge count** | `summary.totalRequired` (= `summary.total` = `len(matrix_items)`) |
| **Status displayed** | `item.status` from backend (`missing` / `expired` / `expiring_soon` / `due_soon` / `awaiting_review` / `completed` / `verified`) via `renderStatusBadge()` |
| **Collections read** | `training_records` (via evaluator) |
| **Fields shown** | title, status badge, certificate link, completed_at, expires_at, verified badge, actions |

**Status logic:** Backend-computed via canonical evaluator. Status flows through `compute_training_record_status()` → `evaluate_employee_training_status()` → matrix endpoint. Frontend does **not** re-derive status.

**Training item count:** `MANDATORY_ITEMS["training"]` contains **14 items** (safeguarding, safeguarding_l2, safeguarding_l3, manual_handling, infection_control, bls, fire_safety, health_safety, information_governance, prevent, induction_training, medication, food_hygiene, mca_dols, dementia, autism) — but `get_required_training_for_employee()` returns all 14+2 (nurse-specific if applicable). The matrix endpoint then builds items for each of those, so the "8 mandatory training items" label on the card is **hardcoded text (L495)** and **does not reflect the actual number of training items returned by the API**.

**Certificate link logic (3-tier fallback):**
1. `item.source_document_id` → `onViewCertificate(id)` (views from `employee_documents`)
2. `item.certificate_url` → direct `<a>` link (from `training_records.certificate_url`)
3. `item.evidence?.length > 0` → shows count
4. None → shows "None"

**FINDING M-1:** The card description says "These 8 mandatory training items" but the actual `MANDATORY_ITEMS["training"]` list has 14+ items. The badge shows `summary.totalRequired` which is the actual count, so badge and label will disagree.

**FINDING M-2:** Certificate viewing has 3 fallback tiers. `source_document_id` points to `employee_documents` (populated when certificate is uploaded via the new intake flow). `certificate_url` is a raw URL stored on `training_records` (populated by bulk-upload legacy flow). These two paths are never reconciled — a training record could have `certificate_url` but no `source_document_id`, or vice versa.

---

### 1.2 All Qualifications Tab (`value="library"`)

| Property | Value |
|----------|-------|
| **Component** | `AuditReadyTrainingMatrix.js` L666–923 |
| **Data source** | `[...mandatoryTraining, ...additionalTraining]` combined |
| **mandatoryTraining** | From `GET /training/matrix` → `response.items` (same as Mandatory tab) |
| **additionalTraining** | From `GET /training/matrix` → `response.additional_items` |
| **Plus proposed items** | From `GET /employees/{eid}/training/proposed-items` → `proposedItems` (shown in "Awaiting Review" section) |
| **Badge count** | `summary.additionalQualifications + summary.totalRequired` |
| **Collections read** | `training_records` (mandatory via evaluator + non-mandatory additional), `proposed_training_items` (proposed items) |
| **Status displayed** | `item.status` from backend for both mandatory and additional items |

**Additional items status logic (L10850–10870 in server.py):**  
For non-mandatory training records, the matrix endpoint computes status **inline** with a simple expiry check:
- No expiry → `current`
- Expired → `expired`
- Within 30 days → `expiring_soon`

This is **NOT** the canonical evaluator — it's a simplified inline calculation that does **not** check `verified`, `verification_status`, or call `compute_training_record_status()`.

**Proposed items section:**
- Shows items from `proposed_training_items` collection where `status === 'proposed'`
- Displays: `raw_course_title`, `mapped_training_title`, `completed_at`, `expires_at`
- Admin can Approve/Reject/Edit

**FINDING Q-1:** Additional (non-mandatory) training status is computed with a simple date comparison inside the matrix endpoint, **not** through the canonical evaluator. A non-mandatory training that is `completed` but `not verified` will show as `current` (no awaiting_review status). This is an intentional simplification but means the Library tab shows a different status vocabulary for additional vs mandatory items.

**FINDING Q-2:** The Library tab shows ALL `proposedItems` from the `proposed_training_items` collection. The Certificates tab also shows items linked to certificates. If a proposed item is displayed in both places, the review action (Approve/Reject) on the Library tab will change the status, but the Certificates tab will just re-render the same item via its `source_document_id` link. No duplication bug, but potential user confusion.

---

### 1.3 Certificates Tab (`value="certificates"`)

| Property | Value |
|----------|-------|
| **Component** | `AuditReadyTrainingMatrix.js` L924–1095 |
| **Data source** | `certificates` state → from `GET /api/employee-documents?employee_id={eid}` |
| **Filter applied** | `doc.document_type === 'training_certificate' \|\| doc.requirement_id?.includes('training') \|\| doc.category === 'training'` |
| **Badge count** | `summary.certificatesUploaded` (= count of filtered employee_documents) |
| **Linked items** | `proposedItems.filter(p => p.source_document_id === cert.id)` (cross-references back to proposed_training_items) |
| **Collections read** | `employee_documents` (certificates), `proposed_training_items` (linked items) |

**What each certificate card shows:**
- `original_filename`, `uploaded_at`, `uploaded_by`
- Badge: count of linked proposed items extracted from this certificate
- Badge: count of pending proposed items
- Buttons: View, Download, Re-extract (admin)
- Expanded: list of linked proposed items with status/confidence/mapped code

**FINDING C-1 (CRITICAL):** The Certificates tab reads `employee_documents`, NOT `training_records`. Certificates that were uploaded via the **bulk-upload** flow (`server.py` L11576) write to `training_records.certificate_url` and do NOT create `employee_documents` entries. These certificates are **invisible** in the Certificates tab.

**FINDING C-2:** The Certificates tab relies on `proposedItems.filter(p => p.source_document_id === cert.id)` to show linked training items. This only works for certificates processed through the TrainingIntakeService (which creates `proposed_training_items` with `source_document_id`). Certificates uploaded via legacy bulk-upload have no `proposed_training_items` and will show "0 items extracted" even though training records were auto-completed.

**FINDING C-3:** The `summary.certificatesUploaded` badge on the tab counts `employee_documents` matching the training filter. The Mandatory tab also shows certificate links via `source_document_id`. If a certificate is in `employee_documents` but the linked `proposed_training_item` hasn't been approved yet, the Mandatory tab will show "None" for that training's certificate, while the Certificates tab will show the document with "1 pending review". The two tabs tell different stories about the same certificate.

---

## Section 2 — Admin vs Worker Dashboard Comparison

### 2.1 Side-by-Side Training Data

| Aspect | Admin (AuditReadyTrainingMatrix) | Worker (WorkerDashboard) |
|--------|----------------------------------|--------------------------|
| **Component** | `AuditReadyTrainingMatrix.js` | `WorkerDashboard.js` L1890–2170 |
| **Endpoint** | `GET /employees/{eid}/training/matrix` | `GET /worker/dashboard` |
| **Backend handler** | `server.py` L10708 | `worker_dashboard.py` L202 (training at L688–830) |
| **Evaluator** | `evaluate_employee_training_status()` (canonical) | **INLINE** expiry check + fuzzy name match |
| **Status values** | `missing`, `expired`, `expiring_soon`, `due_soon`, `awaiting_review`, `completed`, `verified` | `missing`, `expired`, `complete`, `rejected` |
| **Mandatory list** | `MANDATORY_ITEMS["training"]` (14+ items) | Hardcoded 8-item dict (L688–697) |
| **Recommended list** | (included in mandatory via MANDATORY_ITEMS) | Separate 6-item dict (L699–706) |
| **Certificate evidence** | 3-tier fallback (source_document_id → certificate_url → evidence count) | Not displayed |
| **Verified state** | Shows green/amber verified badge | Shows shield icon if `verified=true` |
| **Subtabs** | 3 tabs: Mandatory / All Qualifications / Certificates | No subtabs — single card with 3 sections |
| **Proposed items** | Visible in Library and Certificates tabs | Not visible |
| **Badge counts** | Per-tab: totalRequired, qualifications, certificatesUploaded | None |

### 2.2 Mandatory Training Definition Disagreement

**Admin** uses `MANDATORY_ITEMS["training"]` with 14+ items:
```
safeguarding, safeguarding_l2, safeguarding_l3, manual_handling, infection_control,
bls, fire_safety, health_safety, information_governance, prevent,
induction_training, medication, food_hygiene, mca_dols, dementia, autism
```

**Worker** uses a hardcoded 8-item dict:
```
safeguarding, manual_handling, health_safety, bls, fire_safety,
infection_control, information_governance, prevent
```

**Worker recommended** (separate section, 6 items):
```
induction, medication, food_hygiene, mca_dols, dementia, autism
```

**FINDING AW-1 (CRITICAL):** The admin considers all 14+ items as "training requirements" served through the canonical evaluator with work-blocker flags. The worker dashboard splits them into 8 "mandatory" + 6 "recommended". But the admin matrix endpoint returns ALL of them in `items` (mandatory) and treats `induction_training`, `medication`, `food_hygiene`, `mca_dols`, `dementia`, `autism` as mandatory training items with specific `priority_order` and `status_group` values. The admin and worker disagree on what is mandatory.

**FINDING AW-2 (CRITICAL):** The worker dashboard does NOT call the canonical evaluator. It has its own inline status derivation (L781–810) that:
- Does not distinguish `expiring_soon` (no 30-day warning)
- Does not have `awaiting_review` status
- Does not check `verified` for status determination (only exposes it as a field)
- Uses fuzzy substring matching instead of `requirement_id` lookup

This means an employee can see `complete` on the worker dashboard but `awaiting_review` on the admin dashboard for the same training.

**FINDING AW-3:** The worker's fuzzy matching (`if pattern in t_name`) can match the wrong record. Example: a training record named "Safeguarding Adults Level 2" would match the worker's `safeguarding` pattern first (since "safeguard" is in the search patterns), causing the worker to show Level 2 as the match for base safeguarding, while the admin's canonical evaluator uses `requirement_id` matching and would correctly distinguish them.

---

## Section 3 — Upload Path Comparison Table

| Upload Path | Trigger | Endpoint | Writes To | Creates `employee_documents`? | Creates `proposed_training_items`? | Creates `training_records`? | Visible in Certificates Tab? | Visible in Mandatory Tab? |
|-------------|---------|----------|-----------|-------------------------------|------------------------------------|-----------------------------|------------------------------|---------------------------|
| **Admin: Upload Certificate button (Mandatory tab)** | `onUploadCertificate` prop | Opens TrainingCertificateExtractor → `POST /employees/{eid}/training/intake/from-upload` | Supabase storage | **YES** | **YES** | **NO** (only after proposed item approved) | **YES** | Only after approval (via `source_document_id`) |
| **Admin: Bulk Upload** | `setExtractorOpen(true)` | Same as above via TrainingCertificateExtractor | Supabase storage | **YES** | **YES** | **NO** (only after approval) | **YES** | Only after approval |
| **Admin: Legacy Bulk Upload** | Legacy code path | `POST /employees/{eid}/training/bulk-upload` (L11576) | **Local disk** | **NO** | **NO** | **YES** (auto-completed) | **NO** ❌ | **YES** (via `certificate_url`) |
| **Worker: Single training upload** | Upload button per training | `POST /worker/upload-document/training_{id}` | Supabase storage | **YES** | **YES** (if AI extraction succeeds) | **NO** (only after admin approval) | **YES** | Only after admin approval |
| **Worker: Bulk upload** | "Bulk Upload" button | `POST /worker/upload-document/training_bulk` | Supabase storage | **YES** | **YES** (if AI extraction succeeds) | **NO** | **YES** | Only after admin approval |
| **Admin: Manual record via edit dialog** | Edit training dialog | `PATCH /employees/{eid}/training/{code}` | N/A | **NO** | **NO** | **YES** (updates existing) | **NO** | **YES** (from `training_records` fields) |
| **Admin: Approve proposed item** | Approve button in Library tab | `POST /employees/{eid}/training/proposed-items/review` | N/A | **NO** | Updates status to `approved` | **YES** (creates canonical record) | Still linked via `source_document_id` | **YES** (new training record) |

**FINDING U-1 (CRITICAL):** There are **two completely separate document lifecycle paths**:
1. **New path** (IntakeService): Upload → `employee_documents` + `proposed_training_items` → Admin review → `training_records`
2. **Legacy path** (bulk-upload): Upload → `training_records` directly (auto-completed, local disk)

Records created via the legacy path are invisible in the Certificates tab. Records created via the new path are invisible in the Mandatory tab until approved.

**FINDING U-2:** Worker uploads always go through the new path (creates `employee_documents` + `proposed_training_items`), but the worker dashboard reads `training_records` for status display. Until admin approves the proposed item (which creates a `training_records` entry), the worker will still see the training as `missing` even though they uploaded a certificate. The only feedback is the toast message "Awaiting admin verification."

**FINDING U-3:** The worker upload endpoint (`worker_dashboard.py` L1516) has its own inline mandatory code matching dict (L1649–1658) that is separate from both the `MANDATORY_ITEMS["training"]` list and the worker dashboard's `mandatory_trainings` dict. Three different definitions in three different places.

---

## Section 4 — Canonical Source-of-Truth Verdict

### Per-Subtab Data Source Chain

| Subtab | Canonical Source | Evaluator | Collection(s) | Verdict |
|--------|-----------------|-----------|---------------|---------|
| **Mandatory** | `training_records` via `evaluate_employee_training_status()` | Canonical ✅ | `training_records` | **CORRECT** — Uses canonical evaluator, backend-computed status. Only weakness is the hardcoded "8 mandatory" label and certificate_url fallback to legacy data. |
| **All Qualifications** | Mandatory items via canonical evaluator + additional items via inline date check | **MIXED** ⚠️ | `training_records` + `proposed_training_items` | **PARTIALLY CORRECT** — Mandatory items use canonical evaluator. Additional items use simplified inline status. Proposed items are a third source. Three different status models in one tab. |
| **Certificates** | `employee_documents` filtered by training type | No evaluator (display only) | `employee_documents` + `proposed_training_items` (linked) | **WRONG COLLECTION** ❌ — Shows documents, not training status. Documents uploaded via legacy bulk-upload are invisible. Badge count has no relation to actual training completion. |

### Overall Verdict

**The system has no single source of truth for training certificates.**

- `training_records.certificate_url` — populated by legacy bulk-upload and some manual operations
- `employee_documents` (filtered by `document_type='training_certificate'`) — populated by new IntakeService and worker uploads
- `proposed_training_items.source_document_id` → links back to `employee_documents`

The Mandatory tab can see evidence from `training_records.certificate_url` (legacy path). The Certificates tab can only see evidence from `employee_documents` (new path). Neither tab shows the complete picture.

---

## Section 5 — Hidden Integrity Risks

### Risk 1: Ghost Completions (Severity: HIGH)
If the legacy bulk-upload path is still accessible, it creates `training_records` with `status: completed` and `certificate_url` pointing to local disk storage. These records:
- Pass the canonical evaluator (which only checks `completion_date` and `expiry_date`)
- Show as "completed" on the admin Mandatory tab
- Show as "complete" on the worker dashboard
- Have a `certificate_url` that returns 404 (local disk, not Supabase)
- Are invisible in the Certificates tab

**Impact:** Training appears complete with a broken certificate link. CQC inspector clicking "View" gets a 404.

### Risk 2: Status Divergence Between Admin and Worker (Severity: HIGH)
- Admin uses canonical evaluator → can return `awaiting_review` if evidence_required but unverified
- Worker uses inline expiry check → has no `awaiting_review` state
- A training that the admin sees as `awaiting_review` (blocked) will appear as `complete` to the worker
- This means the worker thinks they're clear to work, but the admin dashboard shows a blocker

### Risk 3: Fuzzy Match Collisions (Severity: MEDIUM)
The worker dashboard uses substring matching: `if pattern in t_name`. Examples:
- "Fire Safety Awareness Day" matches `fire_safety` pattern "fire safety" ✓
- "Safeguarding Adults Level 2" matches `safeguarding` pattern "safeguard" before reaching `safeguarding_l2` because L2 is not in the worker's mandatory list at all
- "Health and Safety At Work" matches `health_safety` ✓
- "Mental Health First Aid" could match `bls` pattern "first aid" ✗ (wrong training)

**Impact:** Worker dashboard could show wrong training record for a category. Admin (canonical evaluator using `requirement_id` match) and worker (fuzzy substring) resolve different records for the same training.

### Risk 4: Triple-Definition Drift (Severity: MEDIUM)
Three separate mandatory training definitions exist:
1. `MANDATORY_ITEMS["training"]` in `server.py` L1220–1400 — **14+ items**
2. `mandatory_trainings` dict in `worker_dashboard.py` L688–697 — **8 items**
3. `mandatory_codes` in `worker_dashboard.py` L1649–1658 (upload matching) — **8 items** (different format: dict of lists)

Any update to the training requirements must be applied to all three locations. If someone adds a new mandatory training to `MANDATORY_ITEMS["training"]`, the worker dashboard will not show it, and worker uploads for it won't be recognized as mandatory.

### Risk 5: Orphaned Proposed Items After Re-Extract (Severity: LOW)
The Certificates tab has a "Re-extract" button (`handleReExtract(cert.id)`) that re-runs AI extraction on an existing certificate. This creates new `proposed_training_items` but does NOT clean up previously approved items. If a certificate was already processed and training records created, re-extracting could create duplicate proposed items for the same training.

### Risk 6: Badge Count Misrepresentation (Severity: LOW)
- All Qualifications badge = `summary.additionalQualifications + summary.totalRequired`
- If an additional training record exists with a `requirement_id` that fuzzy-matches a mandatory code, it gets classified as mandatory in the matrix endpoint (L10752–10761) and excluded from `additional_items`. The badge count shifts without any data change.

---

## Summary of All Findings

| ID | Severity | Finding |
|----|----------|---------|
| M-1 | LOW | Mandatory tab label says "8 mandatory" but actual count varies (14+ items returned by API) |
| M-2 | MEDIUM | Certificate viewing has 3-tier fallback mixing `employee_documents` and `training_records.certificate_url` without reconciliation |
| Q-1 | MEDIUM | Additional training uses simplified inline status, not canonical evaluator |
| Q-2 | LOW | Proposed items displayed in both Library and Certificates tabs (potential confusion) |
| C-1 | **CRITICAL** | Certificates tab reads `employee_documents` — legacy bulk-upload certificates are invisible |
| C-2 | HIGH | Certificates tab shows "0 items extracted" for legacy-uploaded certificates |
| C-3 | MEDIUM | Mandatory and Certificates tabs tell different stories about the same certificate's state |
| AW-1 | **CRITICAL** | Admin treats 14+ trainings as requirements; worker splits into 8 mandatory + 6 recommended |
| AW-2 | **CRITICAL** | Worker dashboard does NOT use canonical evaluator; 4 missing status values |
| AW-3 | HIGH | Fuzzy substring matching on worker side can match wrong training record |
| U-1 | **CRITICAL** | Two separate document lifecycle paths with no reconciliation |
| U-2 | HIGH | Worker upload → proposed_training_items, but worker dashboard reads training_records (invisible until approved) |
| U-3 | MEDIUM | Three different mandatory training definitions in three different files |

### Critical Issues Requiring Immediate Attention (4):
1. **C-1:** Certificates tab blind spot (legacy uploads invisible)
2. **AW-1:** Mandatory list disagreement (14+ admin vs 8 worker)
3. **AW-2:** Worker bypasses canonical evaluator entirely
4. **U-1:** Dual document lifecycle with no reconciliation
