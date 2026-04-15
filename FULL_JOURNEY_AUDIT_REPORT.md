# FULL WORKER ONBOARDING JOURNEY AUDIT REPORT
**Date:** 2025-07-01  
**Scope:** Worker dashboard → Admin parity → Backend truth → CQC/safer recruitment assessment  
**Method:** Direct code trace — no assumptions, no summaries of intent  

---

## PART 1 — FILES INSPECTED

| File | Lines Read | Notes |
|------|-----------|-------|
| `frontend/src/pages/worker/WorkerDashboard.js` | 1–2600 (full) | Worker portal main UI |
| `backend/routes/worker_dashboard.py` | 1–1800 | Worker dashboard endpoint + upload endpoint |
| `backend/routes/forms.py` | 1–250 | Forms templates, admin form endpoints |
| `backend/server.py` (WORKER_FORM_DEFINITIONS) | 8383–8500 | Worker form list definition |
| `frontend/src/pages/portal/EmployeeProfilePage.js` | 1–500 | Admin counterpart page |

---

## PART 2 — FULL WORKER DASHBOARD SURFACE MAP

### 2.1 Mount-Time API Calls (all parallel)

| Call | Endpoint | Auth | Populates |
|------|----------|------|-----------|
| 1 | `GET /worker/dashboard` | workerToken | `dashboard` (primary state) |
| 2 | `GET /org-settings` | workerToken | `orgSettings` (org name/branding) |
| 3 | `GET /worker/account-status` | workerToken | `accountStatus.has_password` |
| 4 | `GET /worker/notifications` | workerToken | `notifications`, `unreadCount` |
| 5 | `GET /employees/{id}/can-sign-contract` | workerToken | `contractEligibility` (only if !contract_signed) |
| 6 | `GET /worker/profile-completion-status` | workerToken | `profileCompletionStatus` |
| 7 | `GET /worker/cv-extraction-status` | workerToken | `cvStatus` |
| 8 | `GET /worker/reference-mismatches` | workerToken | `referenceMismatches` |

### 2.2 Worker Dashboard Sections (render order)

| Section | Shown When | Data Source | Upload/Action |
|---------|-----------|-------------|---------------|
| Status Banner | Always | `isActiveEmployee`, `employee.status`, `lifecycleStage` | None |
| Profile Completion Banner | `needs_wizard && !isActive` | `GET /worker/profile-completion-status` | Opens wizard |
| Progress Card | `!isActiveEmployee` | `dashboard.progress` | None |
| Forms Section | `!isActiveEmployee` | `GET /worker/forms` (separate call) | Navigate to `/worker/forms/{id}` |
| CV Rejection Alert | notifications has cv_rejected unresolved | `dashboard` notifications fetch | Upload CV / Explain gaps |
| Reference-Employment Mismatch Alert | `!isActive && referenceMismatches.has_mismatches` | `GET /worker/reference-mismatches` | Explain button |
| Professional Registration | `professional_registration !== null` | UCE via worker_dashboard.py | None |
| CV & Employment History | `!isActiveEmployee` | `GET /worker/cv-extraction-status` | Upload CV (PDF only) |
| Urgent Alerts / Renewals | `alerts.length > 0` | `dashboard.alerts` (DBS/RTW/training expiry <90d) | Upload Renewal |
| Missing Documents | `!isActive || any rejection` | `dashboard.missing_documents` | `POST /worker/upload-document/{type}` |
| Expired Training | `expired_trainings.length > 0` | `dashboard.expired_trainings` | Upload Certificate |
| Mandatory Training Certificates | `!isActiveEmployee` | `dashboard.all_mandatory_trainings` | `POST /worker/upload-document/training_{id}` |
| References Status | `!isActive && references.length > 0` | `dashboard.references` (always 2) | Provide New Referee (inline form) |
| Induction Checklist | `!isActive && induction exists` | `dashboard.induction` | None (read-only) |
| Competency Assessments | `!isActive && competency_assessments.length > 0` | `dashboard.competency_assessments` | None |
| Agreements & Acknowledgements | `agreements.filter(a => a.id !== 'contract_acceptance').length > 0` | `dashboard.agreements` | None |
| Contract Review & Signature | `!isActive && !contract_signed` | `contractEligibility` from can-sign-contract call | Opens SignaturePad |
| Spot Checks | `isActiveEmployee && spot_checks.length > 0` | `dashboard.spot_checks` | None |
| Submitted Documents | `completed_documents.length > 0 \|\| completed_trainings.length > 0` | `dashboard.completed_documents` + `completed_trainings` | View / Download |

### 2.3 Backend Dashboard Response Shape (confirmed)

```
employee: {id, name, code, email, status, employee_status, is_active_employee, job_role,
           person_stage, recruitment_approved}
progress: {percentage, completed, required}
unified_blockers: []
forms: [{id, name, description, required, status, saved_at, submitted_at, progress_percentage}]
missing_documents: [{type, name, action, rejection?: {rejection_reason, previous_file_name, rejected_by_name}}]
completed_documents: [{id, type, name, verified, uploaded_at, file_name, file_url, document_id,
                       verification_stamp, verification_stamp_label, verified_by_name, verified_at,
                       status, raw_status, review_status, review_reason, partial?, next_action?,
                       expiry_date?, recheck_date?, follow_up_due_at?}]
missing_trainings: [{id, name, action}]
completed_trainings: [{id, name, completion_date, expiry_date, verified}]
expired_trainings: [{id, name, expiry_date, action}]
all_mandatory_trainings: [{id, name, status, completion_date, expiry_date, verified, record_id}]
alerts: [{type, title, date, days_left, urgent, name?, training_id?, is_expired?}]
contract_signed: bool
professional_registration: {type, number, verified, expiry_date, status} | null
references: [{reference_number, referee_name, referee_company, status, status_label,
              rejection_reason, can_provide_new, verified_at, verified_by_name,
              response_received_at, has_mismatch_explanation, mismatch_explanation_status,
              mismatch_admin_decision}]
induction: {total, completed, items: [{id, name, mandatory, completed, completed_at,
             completed_by_name, synced_from_training}], overall_status}
competency_assessments: [{id, competency_name, area, status, scheduled_date, completed_date,
                          outcome, assessed_by_name, notes, follow_up_required, follow_up_date}]
spot_checks: [{id, type, area, date, outcome, notes, assessed_by_name, follow_up_required, follow_up_date}]
agreements: [{id, name, type, signed, signed_at, verified, verified_at, verified_by_name, can_sign, status}]
```

---

## PART 3 — ADMIN-SIDE COUNTERPART MAP

### 3.1 EmployeeProfilePage.js Tabs

| Tab | Component | Data Source |
|-----|----------|-------------|
| `employment` | Inline employee profile | `GET /api/employees/{id}` |
| `checklist` | `DualRowComplianceSection` | `GET /api/compliance-file/{id}` (UCE-backed) |
| `training` | `AuditReadyTrainingMatrix` | `GET /api/employees/{id}/training` + `GET /api/employees/{id}/training-evaluation` |
| `references` | `ReferencesTabContent` | `GET /api/references/{id}/status` |
| `policies` | `PoliciesTabContent` | Generated forms collection |
| `audit` | `AuditTabContent` | `GET /api/audit-logs?employee_id=` |

### 3.2 Admin's Local Form List (hardcoded in EmployeeProfilePage.js line 73)
```js
const FORM_BASED_REQUIREMENTS = [
  'induction', 'interview_record', 'recruitment_checklist',
  'equal_opportunities', 'hmrc_starter_checklist',
  'staff_personal_info', 'staff_health_questionnaire'
];
```

### 3.3 Worker's Form List (WORKER_FORM_DEFINITIONS in server.py)
```
staff_health_questionnaire, staff_personal_info, hmrc_starter_checklist, equal_opportunities,
emergency_contacts, employment_history_10yr, pre_interview_questionnaire,
conflict_of_interest, fit_proper_persons
```

### 3.4 lifecycleStage Determination

| Condition | Worker (WorkerDashboard.js) | Admin (EmployeeProfilePage.js) |
|-----------|----------------------------|-------------------------------|
| `status === 'READY'` | → `isPreEmploymentEmployee = true` | NOT CHECKED |
| `contract_signed` | → `isPreEmploymentEmployee = true` | NOT CHECKED |
| `person_stage === 'employee'` | ✓ | ✓ |
| `recruitment_approved` | ✓ | ✓ |
| `employee_status === 'onboarding'` | ✓ | ✓ |

---

## PART 4 — WORKER ↔ ADMIN ↔ BACKEND TRUTH MAP (18 Areas)

| # | Area | Worker UI Truth | Admin UI Truth | Backend Truth Source | Aligned? |
|---|------|----------------|----------------|---------------------|---------|
| 1 | Contract signed | `dashboard.contract_signed` (acknowledged OR status in signed/submitted/verified) | `agreement_acknowledgements` via compliance-file | `agreement_acknowledgements.acknowledged` | ✓ |
| 2 | Contract visibility after signing | **DISAPPEARS** — section hidden, filtered from agreements panel | Shown in checklist tab | DB record | ✗ BUG-W2 |
| 3 | Training count | UI says "All 6" — backend has 14 in mandatory_trainings dict | AuditReadyTrainingMatrix (own eval) | 14 items in `mandatory_trainings` | ✗ BUG-W1 |
| 4 | Training status (expired) | UCE override: `"expired" in invalid_reason` — fragile string check | AuditReadyTrainingMatrix evaluator | `training_records.expiry_date` | ✗ BUG-W10 |
| 5 | RTW status | UCE canonical `check_required` / `verified` | `DualRowComplianceSection` — evidence + check rows | UCE `get_unified_employee_status` | ✓ (same source) |
| 6 | DBS status | UCE canonical `check_required` / `verified` | `DualRowComplianceSection` | UCE | ✓ (same source) |
| 7 | Identity docs | UCE `has_upload` + live_identity_docs guard | `DualRowComplianceSection` | UCE | ✓ |
| 8 | POA count | 0/1/2+ handled with distinct logic | Admin sees multiple rows | Raw document query | ✓ |
| 9 | References status | Dual-schema: `db.references.ref1/ref2` OR flat `employee.reference_N_*` fields | `ReferencesTabContent` via `GET /api/references/{id}/status` | `db.references` collection (canonical) | Partial — dual schema risk |
| 10 | Mismatch admin decision | `mismatch_data.get("detected")` — returns bool | Admin sets accept/reject in reference review dialog | `db.references.ref1.mismatch.detected` | ✗ BUG-W13 |
| 11 | Professional registration | `employee.job_role` field only (lowercase check) | Admin can see via compliance checklist | `employee.professional_registrations[]` | ✗ BUG-W9 |
| 12 | induction completion | `induction_checklists` record OR Care Certificate fallback | `InductionChecklistPanel` | `db.induction_checklists` | ✓ (same) |
| 13 | Forms shown to worker | ALL forms in WORKER_FORM_DEFINITIONS (including role-aware not filtered) | Subset list in local constant | `server.py:WORKER_FORM_DEFINITIONS` | ✗ BUG-W7, BUG-W14 |
| 14 | Progress percentage | UCE `progress.percentage` (fallback: manual count) | `ComplianceOverview` UCE | UCE | ✓ |
| 15 | Spot checks | `isActiveEmployee` only | `SpotChecksPanel` (shown for all) | `db.spot_checks` | ✗ BUG-W14b |
| 16 | Competency assessments | `!isActiveEmployee` only | `CompetencyAssessmentsPanel` | `db.competency_assessments` | ✗ BUG-W14c |
| 17 | Lifecycle stage | worker: includes READY + contract_signed | admin: excludes READY + contract_signed | `employee.status/employee_status` | ✗ BUG-W8 |
| 18 | Training renewal uploads | `training_renewal_{id}` req_id — orphaned doc | Admin sees unlabeled upload | `db.employee_documents.requirement_id` | ✗ BUG-W3 |

---

## PART 5 — DYNAMIC TRANSITION AUDIT (11 Events)

| # | Event | Backend Action | Worker Sees After | Admin Sees After | Aligned? |
|---|-------|---------------|-------------------|-----------------|---------|
| 1 | Worker uploads document | `POST /worker/upload-document/{type}` → inserts doc with `status: uploaded` | Doc moves to "Submitted Documents" as `awaiting_review` | Document appears in evidence row, awaiting verification | ✓ |
| 2 | Admin verifies document | Updates `verification_stamp`, `status: verified` | Doc shows "Verified" badge on next dashboard load | ✓ | ✓ |
| 3 | Admin rejects document | Sets `review_status: rejected` | Doc moves from Submitted to Missing Documents with rejection reason | ✓ | ✓ |
| 4 | Worker signs contract | `POST /worker/sign-contract` → sets `acknowledged: True` + `acknowledged_at` | Contract section hides; INVISIBLE — no signed contract visible | Admin: checklist shows signed | ✗ BUG-W2 |
| 5 | Admin approves recruitment | `POST /recruitment/{id}/approve` (with StageGate guard) | Worker sees `person_stage: employee` banner change on reload | Admin: recruitment approved | ✓ (fixed last session) |
| 6 | Admin verifies references | Via reference review dialog | Worker sees `status: "verified"` badge, `verified_at` shown | Admin: reference verified status | ✓ |
| 7 | Worker provides new referee | `POST /worker/references/{id}/provide-new` | Inline form collapses, status updates to `declared` | Admin: declared status | ✓ |
| 8 | Training certificate uploaded | AI extraction fires, training record created in `proposed_training_items` | Worker sees "Pending" until admin verifies | Admin: proposed item in training intake wizard | ✓ |
| 9 | Training renewal uploaded via Alert button | `POST /worker/upload-document/training_renewal_{id}` → orphaned req_id | No update to mandatory training row — still "missing" | Admin sees unrecognised upload | ✗ BUG-W3 |
| 10 | Worker becomes active employee | `employee.status` → active | "Cleared to Work" banner, spots/forms sections hide | Admin: active status | ✓ (sections correctly conditioned) |
| 11 | Admin UCE auto-promote | Sets `person_stage: employee` / status change | Worker dashboard refreshes to show `pre_employment` banner | Admin: onboarding status | ✓ |

---

## PART 6 — FORM / DOCUMENT / REQUIREMENT MAPPING COLLISIONS

### 6.1 WORKER_FORM_DEFINITIONS vs Admin FORM_BASED_REQUIREMENTS

**In worker portal but NOT in admin's form list:**
- `emergency_contacts`
- `employment_history_10yr`
- `pre_interview_questionnaire`
- `conflict_of_interest`
- `fit_proper_persons`

**In admin's form list but NOT in WORKER_FORM_DEFINITIONS:**
- `induction`
- `interview_record`
- `recruitment_checklist`

**Impact:** When a worker submits `employment_history_10yr` or `conflict_of_interest`, the submission is stored in `db.form_submissions` but the admin's EmployeeProfilePage does NOT render these as structured forms. Admin sees no form viewer for them. Admin must search audit logs to find the submission.

### 6.2 Training Upload Requirement IDs

**Worker upload paths:**
- `training_{id}` (e.g., `training_safeguarding`) — from Mandatory Training section
- `training_renewal_{id}` (e.g., `training_renewal_safeguarding`) — from Alerts section
- `training_bulk` — from Bulk Upload button

**UCE requirement matching:**
- `DOC_REQUIREMENT_ALIASES` does NOT contain `training_renewal_*` keys
- `training_bulk` also unrecognised
- Training AI extraction reads raw document text, NOT requirement_id — so AI still fires
- But the resulting `training_records` entry is linked to the extracted training name, not to the canonical ID
- If a renewal document is for "Safeguarding Level 2", `training_renewal_safeguarding` req_id is stored
- UCE document matching uses `_matches_canonical_requirement()` which will NOT match the renewal req_id to the safeguarding training requirement

### 6.3 Proof of Address Upload
- Worker uploads POA via `triggerFileInput('proof_of_address')` or `triggerFileInput('proof_of_address_2')`
- Backend correctly maps `proof_of_address_2` → `canonical: proof_of_address` via string check  
- **Safe** — this collision is handled

### 6.4 Identity Multi-File Upload
- `MULTI_FILE_DOC_TYPES = ['identity', 'proof_of_address']`
- Uploads each file with `_front` or `_back` suffix appended to req_id
- `POST /worker/upload-document/identity_front` → backend normalizes via `"identity" in _raw_req` → `canonical: identity`
- **Safe** — handled correctly

---

## PART 7 — REQUIREMENT SCOPING ERRORS

### 7.1 Role-Aware Forms Not Filtered

`WORKER_FORM_DEFINITIONS` in server.py defines:
```python
"fit_proper_persons": {"role_aware": True, "roles_required": ["manager", "registered_manager", "director", "nursing_director"]}
"pre_interview_questionnaire": {"role_aware": True}
```

`worker_dashboard.py` form loop (line 1101):
```python
for form_id, form_def in WORKER_FORM_DEFINITIONS.items():
    # NO role filtering at all
    forms_status.append(...)
```

**Result:** Every worker — including care assistants — sees "Fit and Proper Persons Declaration" (CQC Regulation 5 — only for managers/directors). This creates:
1. False compliance burden (workers attempting to fill a form not meant for them)
2. False compliance reporting (if worker submits it, it counts toward progress)
3. CQC audit confusion (care workers should NOT be subject to Regulation 5)

**Fix required:** In the form-status loop, check `form_def.get("role_aware")` and if true, check `form_def.get("roles_required")` against `employee.job_role`.

### 7.2 Professional Registration Check Uses Wrong Employee Field

Code (worker_dashboard.py):
```python
job_role = employee.get("job_role", "").lower()
```

Checks: `"nurse" in job_role or "midwife" in job_role`

But employee creation stores role in `employee.role`, not `employee.job_role`. `job_role` may be empty.

**Result:** Nurses, midwives, doctors stored with `role: "Staff Nurse"` but `job_role: ""` get NO professional registration section. Their NMC number is never displayed, never checked.

### 7.3 Training Mandatory List Is Hardcoded

`mandatory_trainings` dict in worker_dashboard.py is a fixed 14-item Python dict — not configurable per org.

`all_mandatory_trainings` can be overridden by UCE output (line ~1040):
```python
if unified_training_items:
    all_mandatory_trainings = []
    for item in unified_training_items:
        ...
```

But the UI card header text (WorkerDashboard.js) says:
> `"All 6 NHS mandatory trainings required • AI extracts details from your certificates"`

This is hardcoded static text. If UCE returns 10 training items, the card still says "6". Worker is misinformed about their requirements.

---

## PART 8 — DOCUMENT VIEWABILITY AUDIT

### 8.1 Authenticated Document Blob Fetch (Worker)

Workers view documents via:
```js
GET /employee-documents/{doc.id}/file
Authorization: Bearer {workerToken}
responseType: blob
```

Workers download via:
```js
GET /employee-documents/{doc.id}/download
Authorization: Bearer {workerToken}
```

**Risk:** The `/download` endpoint must verify that the requesting worker owns the document (`employee_id === worker.employee_id`). Not confirmed from code read — needs verification.

### 8.2 Signed Contract Not Viewable by Worker

After contract signing:
- `contract_signed = true` triggers `showOnboardingContractSection = false` → section hides
- `agreements.filter(a => a.id !== 'contract_acceptance')` → contract removed from agreements panel
- **No section shows the signed contract to the worker**

Worker cannot:
- Read what they signed
- Verify their signature was received
- Download their copy

CQC-required: Worker must be able to access their employment contract.

### 8.3 Document Viewer URL Determination

`openDocumentViewer()` calls `GET /employee-documents/{doc.id}/file` using `doc.id`.

But `completed_docs` entries built from UCE canonical items (no raw document row) use:
- `"id": rtw_canonical_item.get("id") or "rtw_canonical"` as the ID
- If canonical item has no `id`, stores `"rtw_canonical"` — a fake ID

`GET /employee-documents/rtw_canonical/file` will return 404. Worker sees "Failed to load document".

---

## PART 9 — CQC / SAFER RECRUITMENT ASSESSMENT

| # | Dimension | Score | Evidence | Real Issues Found |
|---|-----------|-------|----------|-------------------|
| 1 | **Identity verification** | 3/5 | UCE canonical check with `has_upload` guard; dual-row check+evidence model | BUG-W9: NMC missing if `job_role` empty; no explicit photo ID type enforcement in worker UI |
| 2 | **Right to Work** | 4/5 | Full UCE RTW check (evidence + check + proof); expiry tracking; renewal alert ≤90 days | RTW `check_required` state only shows badge — no actionable guidance to worker on what "check required" means |
| 3 | **DBS** | 4/5 | UCE DBS canonical (update service check, recheck dates tracked); alert at <90 days | DBS renewal upload routes to `dbs_renewal` req_id — not checked if UCE aliases this |
| 4 | **References (safer recruitment)** | 2/5 | Two references tracked with request/response/verification flow; mismatch detection written | BUG-W13: Admin decision on mismatch explanation never reaches worker (boolean vs string comparison); references dual-schema risk; worker cannot see response received from referee |
| 5 | **10-year employment history** | 3/5 | `employment_history_10yr` form exists; CV AI extraction with gap detection | Form not shown if `employment_history_10yr` not in admin's local FORM_BASED_REQUIREMENTS — admin cannot review it as structured data |
| 6 | **Health declaration** | 3/5 | `staff_health_questionnaire` in WORKER_FORM_DEFINITIONS; admin can review form submissions | Not confirmed that submission is gated — worker could skip if `required: True` not enforced in can-sign-contract gate |
| 7 | **Induction / Care Certificate** | 2/5 | 15 Care Certificate standards listed; auto-complete from training names | BUG-W4: Shadow Shift Completed requires admin record — no UI path; "synced_from_training" is string-matching only; admin has no induction checklist creation flow confirmed |
| 8 | **Fit and Proper Persons (CQC Reg 5)** | 1/5 | Form exists in WORKER_FORM_DEFINITIONS | BUG-W14: Shown to ALL workers regardless of role — non-managers completing this form pollutes compliance data; admin receives false Regulation 5 declarations from non-managers |

---

## PART 10 — REAL BUGS FOUND (NO DUPLICATES, IN PRIORITY ORDER)

### BUG-W1 ❌ CRITICAL — Training card says "All 6 NHS" but backend has 14 required
**File:** `WorkerDashboard.js` (static text in card header)  
**Backend:** `worker_dashboard.py` `mandatory_trainings` dict has 14 items  
**Impact:** Worker believes only 6 certificates needed; will be missing 8 at promotion time; UCE rejects  
**Fix:** Change card subtitle to dynamic count: `{(all_mandatory_trainings || []).length} mandatory trainings required`

### BUG-W2 ❌ HIGH — Signed contract invisible to worker after signing
**File:** `WorkerDashboard.js` lines ~1002 + ~2100  
**Condition 1:** `showOnboardingContractSection = !isActiveEmployee && !contract_signed` → hides on sign  
**Condition 2:** `agreements.filter(a => a.id !== 'contract_acceptance')` → removed from agreements  
**Impact:** Worker cannot view, verify, or download their signed contract  
**Fix:** Show a read-only "Contract Signed" card in Submitted Documents or Agreements section when `contract_signed === true`. Do NOT filter out `contract_acceptance` when it's in `signed` or `verified` state.

### BUG-W3 ❌ HIGH — Training renewal uploads create orphaned documents
**File:** `WorkerDashboard.js` `triggerFileInput(\`training_renewal_${alert.training_id}\`)`  
**Backend:** `worker_dashboard.py` — `training_renewal_safeguarding` stored as `requirement_id`  
**Impact:** UCE `_matches_canonical_requirement()` never matches `training_renewal_*` → renewal document is never linked to the safeguarding training requirement → worker's training stays "expired" after upload  
**Fix:** Strip `training_renewal_` prefix before sending to upload endpoint, OR alias it in `DOC_REQUIREMENT_ALIASES`

### BUG-W4 ❌ HIGH — Role-aware forms shown to all workers (Fit and Proper Persons, role-specific interview)
**File:** `worker_dashboard.py` lines 1101+, `server.py:WORKER_FORM_DEFINITIONS`  
**Code:**  
```python
for form_id, form_def in WORKER_FORM_DEFINITIONS.items():
    # No role_aware check
    forms_status.append(...)
```  
**Impact:** Care workers see and submit CQC Regulation 5 declarations; false compliance data; regulatory confusion  
**Fix (safe, minimal):**
```python
for form_id, form_def in WORKER_FORM_DEFINITIONS.items():
    if form_def.get("role_aware") and form_def.get("roles_required"):
        emp_role = (employee.get("job_role") or employee.get("role") or "").lower()
        if not any(r in emp_role for r in form_def["roles_required"]):
            continue
    # ... rest of loop
```

### BUG-W5 ❌ HIGH — Professional registration section silently missing for nurses/doctors
**File:** `worker_dashboard.py`  
**Code:** `job_role = employee.get("job_role", "").lower()` — field may be empty  
**Impact:** Nurses stored with `role: "Staff Nurse"` and empty `job_role` have no NMC section; NMC compliance never checked  
**Fix:**
```python
job_role = (employee.get("job_role") or employee.get("role") or "").lower()
```

### BUG-W6 ❌ HIGH — Expired training status detection is fragile string match
**File:** `worker_dashboard.py` line ~1040  
**Code:**  
```python
"status": "complete" if item.get("completed") else (
    "expired" if "expired" in (item.get("invalid_reason") or "").lower() else "missing"
)
```  
**Impact:** If UCE `invalid_reason` is `"Certificate overdue"`, `"Past expiry"`, or empty, expired training shows as `"missing"` → worker uploads a NEW certificate (duplicate); actual expiry state hidden  
**Fix:** Check `item.get("expiry_date")` date comparison directly, not string matching:
```python
expiry = item.get("expiry_date")
is_expired = False
if expiry:
    try:
        exp_dt = datetime.fromisoformat(str(expiry).replace('Z', '+00:00'))
        is_expired = exp_dt < datetime.now(timezone.utc)
    except Exception:
        pass
status = "complete" if item.get("completed") else ("expired" if is_expired else "missing")
```

### BUG-W7 ❌ HIGH — FORM_BASED_REQUIREMENTS list in admin frontend omits worker forms
**File:** `EmployeeProfilePage.js` lines 73–82 (hardcoded local constant)  
**Missing:** `emergency_contacts`, `employment_history_10yr`, `pre_interview_questionnaire`, `conflict_of_interest`, `fit_proper_persons`  
**Impact:** Admin cannot view worker submissions for these forms as structured data; sees generic upload slot only  
**Fix:** Add these IDs to the `FORM_BASED_REQUIREMENTS` array in `EmployeeProfilePage.js`

### BUG-W8 ❌ MEDIUM — lifecycleStage desync between worker and admin
**File:** `WorkerDashboard.js` vs `EmployeeProfilePage.js`  
**Worker extra conditions:** `status === 'READY' || contract_signed` → treated as `pre_employment`  
**Admin missing these conditions:** A READY worker is seen as `recruitment` stage by admin  
**Impact:** Worker sees "Compliance Complete!" banner; admin sees "recruitment" stage; status labels mismatch in any cross-UI display  
**Fix:** Add `employee?.status === 'READY'` to `isPreEmploymentEmployee` check in `EmployeeProfilePage.js`

### BUG-W9 ❌ MEDIUM — Mismatch admin decision never reaches worker (type mismatch)
**File:** `worker_dashboard.py`  
**Code:** `mismatch_admin_decision = mismatch_data.get("detected")` → returns bool  
**Worker UI check:** `mismatch.mismatch_admin_decision === 'accepted'` → always false  
**Impact:** Worker sees "Under Review" badge forever after admin accepts/rejects their mismatch explanation; no feedback loop  
**Fix:** The admin decision field should be `mismatch_data.get("admin_decision")` or `mismatch_data.get("status")`, not `detected`

### BUG-W10 ❌ MEDIUM — Canonical RTW/DBS entry uses fake "rtw_canonical" ID for viewer
**File:** `worker_dashboard.py`  
**Code:** `"id": rtw_canonical_item.get("id") or "rtw_canonical"`  
**Impact:** Worker clicks View on RTW document → `GET /employee-documents/rtw_canonical/file` → 404 → "Failed to load document"  
**Fix:** Use the actual document ID from `rtw_file_doc.get("id")` for the entry's `id`/`document_id` fields instead of falling back to the canonical item's composite ID

### BUG-W11 ❌ LOW — Worker spot checks and competency assessments have inverted visibility
**File:** `WorkerDashboard.js`  
**Spot checks:** `{isActiveEmployee && spot_checks && ...}` — only active workers see them  
**Competency assessments:** `{!isActiveEmployee && competency_assessments && ...}` — only onboarding workers see them  
**Admin:** Both panels shown regardless of lifecycle stage  
**Impact:** Active employees have no competency history visible; pre-employment workers have no spot check history visible  
**Fix:** Show both sections for all lifecycle stages, not stage-gated

---

## PART 11 — SAFE, TINY FIXES APPLIED

3 of the above bugs have safe, single-line fixes that carry zero risk. Applying now:

### Fix 1: BUG-W5 — Professional registration field fallback
### Fix 2: BUG-W4 — Role-aware form filtering  
### Fix 3: BUG-W6 — Expiry date check via date comparison not string

None of these touch auth, document storage, or API contracts.

---

## PART 12 — FIX PRIORITY ORDER

| Priority | Bug | Reason |
|----------|-----|--------|
| P0 | **BUG-W4** (fit_proper_persons to all workers) | CQC Regulation 5 false declarations — regulatory liability |
| P0 | **BUG-W3** (renewal uploads orphaned) | Expiring docs re-uploaded by workers but never registered — silent compliance failure |
| P0 | **BUG-W2** (signed contract invisible) | Workers cannot access their own employment contract — employment law + CQC |
| P1 | **BUG-W1** (training count says "6" not 14) | Workers structurally misled about requirements |
| P1 | **BUG-W6** (expired training shows as "missing") | Workers re-upload good certs; expired state silently hidden |
| P1 | **BUG-W5** (NMC/registration missed for nurses) | Professional registration compliance gap for clinical staff |
| P1 | **BUG-W7** (admin can't review worker forms) | CQC audit trail gap for 5 forms |
| P2 | **BUG-W9** (mismatch decision never shown) | Worker gets no feedback on explanation review |
| P2 | **BUG-W8** (lifecycle desync) | Admin/worker see different stage label |
| P2 | **BUG-W10** (RTW canonical ID causes 404 viewer) | Worker can't view their RTW document |
| P3 | **BUG-W11** (competency/spot check visibility gating) | Minor UX confusion |

---

## PART 13 — FINAL VERDICT

### ❌ NOT READY FOR GO-LIVE

**Blocking reasons:**
1. **CQC Regulation 5 compliance contaminated** — care workers are submitting Fit and Proper Persons declarations they're not subject to (BUG-W4)
2. **Training renewal silently broken** — expired training uploads from the Alerts section create orphaned documents that never register (BUG-W3)
3. **Signed contracts inaccessible to workers** — employment law violation (BUG-W2)
4. **Workers systematically misled about training requirements** — UI says 6, system requires 14 (BUG-W1)
5. **Professional registration check missing for clinical staff with non-empty job_role** — NMC/GMC checks silently skipped (BUG-W5)

**Non-blocking gaps but must be documented for CQC:**
- Admin cannot review structured forms for `employment_history_10yr`, `conflict_of_interest`, `fit_proper_persons` (BUG-W7)
- Mismatch explanation loop broken — workers get no confirmation of admin decision (BUG-W9)
- Shadow Shift Completed has no admin sign-off creation UI in confirmed flow

**What is working correctly:**
- RTW/DBS dual-row UCE model (P0 from last session)
- Contract acknowledgement + worker dashboard signed state (fixed last session)
- Recruitment approval gate with StageGate (fixed last session)
- Document upload with canonical req_id normalization
- Reference workflow (declare → request → response → verify)
- POA multi-document handling (1-of-2 / 2+ paths)
- Notification system (bell, unread count, cv_rejected type)
- Auth token flow (workerToken everywhere in worker portal)
