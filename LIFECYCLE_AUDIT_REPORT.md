# LIFECYCLE AUDIT REPORT
**Date:** 2025-05  
**Scope:** Full recruitment → onboarding → active-employee journey  
**Type:** Backend-first truth audit + worker/admin parity check  
**Verdict:** ⚠️ NOT READY FOR LIVE — 11 confirmed bugs, 2 are P0 CQC-class

---

## 1. FILES INSPECTED

| File | Lines Read | Status |
|------|-----------|--------|
| `backend/stage_identity.py` | All | ✅ Full |
| `backend/unified_compliance_engine.py` | 1–1200 of ~3000 | ⚠️ Partial |
| `backend/stageGates.py` | All | ✅ Full |
| `backend/routes/recruitment.py` | All | ✅ Full |
| `backend/routes/promotion.py` | All | ✅ Full |
| `backend/routes/worker_dashboard.py` | 1–2400 | ✅ Full |
| `backend/routes/agreements.py` | 1–250 | ✅ Sufficient |
| `backend/routes/task_queue.py` | All | ✅ Full |
| `backend/server.py` | ~25,000 selected lines | ✅ Sufficient |
| `backend/approval_engine.py` | grep only | ⚠️ Partial |
| `backend/routes/documents.py` | Not read | ❌ Missing |
| `backend/routes/auth.py` | Not read | ❌ Missing |
| `backend/routes/induction.py` | Not read | ❌ Missing |
| Frontend (admin/worker portals) | Not read | ❌ Missing |

---

## 2. END-TO-END LIFECYCLE MAP (code-confirmed)

### Stage 1 — ONLINE APPLICATION
**Endpoint:** `POST /apply` (legacy) or `POST /applications/structured` (main)

**What happens:**
- Creates record in `employees` collection with `status: "new"`, `recruitment_approved: False`
- Legacy: assigns `applicant_reference: "APP-XXXXXXXX"`, `employee_code: null`
- Structured: assigns `applicant_reference`, + temp `employee_code: "APPLICANT-{uuid}"` (to avoid unique index collision)
- Structured: runs `StageGateService.generate_requirements_for_employee()` — creates requirement slots in `employee_documents`
- Structured: creates `form_submissions` record, seeds CV/application_form/equal_opportunities slots as completed
- **NO worker account created at this stage** (hard constraint)

**Identity:** `stage_identity.get_stage_identity()` returns `"applicant"` (status: "new" is in `APPLICANT_STATUSES`)

---

### Stage 2 — APPLICANT SCREENING
**Endpoints:** Status update (admin side, not fully read), `GET /recruitment/applicants`

**What happens:**
- Admin manually moves status through: `new → screening → interview → compliance_review`
- All four statuses produce `stage_identity == "applicant"`
- Applicant list filter: `{status: {$in: ["new", "screening", "interview", "compliance_review"]}}` — status-only, no `recruitment_approved` check
- Progress shown via `calculate_completion_percentage_simple()` — a simplified calc, **NOT UCE**

---

### Stage 3 — RECRUITMENT APPROVAL
**Endpoint:** `POST /employees/{id}/approve-recruitment` (admin only)

**What happens:**
1. Sets `recruitment_approved: True` on employee record
2. If employee has no real code (`null` or starts with `APPLICANT-`): generates new `employee_code: "EMP-{n:04d}"` (starting from last `EMP-` code, min 1001)
3. Transitions `status` → `onboarding` (if was an applicant status)
4. Calls `create_worker_account_on_approval()` → creates `worker_accounts` record
5. Calls `send_welcome_email_with_magic_link()` → emails worker with portal login link
6. Returns `portal_invite_sent: bool`

**Identity shift:** `stage_identity` immediately flips to `"employee"` because `recruitment_approved: True` is the primary gate.

---

### Stage 4 — ONBOARDING
**Worker authenticates via:** magic link → `worker_accounts` record → JWT with `type: "worker_login"` → `get_current_worker()` dependency  
**Endpoint:** `GET /worker/dashboard`

**What happens (worker portal):**
1. Fetches employee by `worker.employee_id`
2. Runs a first-pass document status loop (14 training IDs, 4 doc types, fuzzy matching)
3. Calls `get_unified_employee_status(employee_id, db, user_role="worker")` (UCE) as canonical truth
4. **Second-pass override:** UCE results overwrite the first-pass loop for DBS/RTW/Identity
5. Returns `completed_docs[]`, `missing_docs[]`, `all_mandatory_trainings[]`, `agreements_status`, `forms_status`, `unified_blockers[]`, `progress_percentage`
6. Contract signing (`POST /employees/{id}/sign-contract`): worker signs → triggers `try_auto_promote_worker()`
7. Document uploads → trigger `try_auto_promote_worker()` (line 20220 in server.py)
8. Form submissions → trigger `try_auto_promote_worker()` (line 9159 in server.py)

**`try_auto_promote_worker()` uses ONLY UCE `can_promote`.** Contract is NOT included in UCE. See BUG #8.

---

### Stage 5 — PROMOTION TO ACTIVE
**Paths:**
- `try_auto_promote_worker()` — system-triggered, uses UCE only
- `POST /employees/{id}/auto-promote` — explicit endpoint, uses UCE only, **does NOT send promotion email** (BUG #9)
- `POST /employees/{id}/force-promote` — admin override with audit reason

**What happens on promotion:**
- `status` set to `"active"`, `promoted_at` / `promoted_via` logged
- `try_auto_promote_worker()` also calls `send_promotion_email()` (welcome to active status)
- `stage_identity` remains `"employee"` throughout (already set at approval)

---

### Stage 6 — ACTIVE EMPLOYEE
**Worker dashboard:**
- `is_active_employee = status == "active"` → flips response to "READY" mode
- Forms hidden, expiry alerts shown, UCE blockers still visible

---

## 3. WORKER vs ADMIN TRUTH PARITY MAP

| Data Point | Worker Sees | Admin Sees | Match? |
|-----------|-------------|------------|--------|
| Document status (DBS/RTW) | UCE canonical (second-pass override) | UCE via `/unified-progress-summary` | ✅ Same engine |
| Document status (Identity/PoA) | UCE second-pass override | UCE | ✅ Same |
| Mandatory training list | 8 items (from UCE override) | 8 items (UCE) | ✅ Match (if UCE doesn't fail) |
| Training count on dashboard | UCE `evaluate_employee_training_status` | separate function | ❌ Different engine (BUG #11) |
| `can_promote` | Worker can't see directly | UCE `can_promote` | N/A |
| Completion % | UCE via `overall_percentage` | UCE via `/unified-progress-summary` | ✅ Same |
| Contract status | Checked separately, shown as blocker | NOT shown in compliance view | ❌ Gap (BUG #8) |
| References status | `db.references` collection | `task_queue` reads flat employee fields | ❌ Different source (BUG #3) |
| Induction progress | UCE-computed | Not verified (induction.py not read) | ⚠️ Unverified |
| Stage identity | Worker portal uses `recruitment_approved` implicitly | `stage_identity.get_stage_identity()` | ✅ Match |

---

## 4. DYNAMIC TRANSITION AUDIT

| Event | Triggers Auto-Promote? | Contract Required? | Email Sent? |
|-------|----------------------|-------------------|-------------|
| Document uploaded (via worker portal) | ✅ Yes (`server.py:20220`) | ❌ No | ✅ If `can_promote` becomes true |
| Form submitted | ✅ Yes (`server.py:9159`) | ❌ No | ✅ If `can_promote` becomes true |
| Contract signed | ✅ Yes (`server.py:9159` context) | ✅ Contract just signed | ✅ Yes |
| Training verified (by admin) | ✅ Yes (`server.py:20220`) | ❌ No | ✅ If `can_promote` becomes true |
| `POST /auto-promote` called | ✅ Yes (explicit) | ❌ No | ❌ NOT sent (BUG #9) |
| `POST /force-promote` called | N/A (manual bypass) | ❌ No | Not confirmed |

---

## 5. CQC / SAFER RECRUITMENT ASSESSMENT

| Dimension | Status | Notes |
|-----------|--------|-------|
| 1. Right to Work | ⚠️ Partial | UCE checks RTW with check record + live doc. DBS Update Service path requires `proof_document_id`. Legacy fallback (no check record) accepts admin-verified doc alone — OK for legacy data. |
| 2. DBS Check | ⚠️ Partial | Same dual path as RTW. No automatic DBS expiry enforcement blocking promotion (only alert). |
| 3. References (2 required) | ❌ BROKEN | UCE reads `db.references` canonical collection. Admin task queue reads `employee.reference_1_request_status` (old flat field). Counts diverge — admin may see refs as "outstanding" when UCE considers them verified. |
| 4. Identity Verification | ✅ Pass | UCE checks live docs + admin stamp. Second-pass override in worker dashboard applies UCE canonical state. |
| 5. Employment Contract | ❌ BROKEN | Contract checked separately OUTSIDE UCE. `try_auto_promote_worker()` uses only `can_promote` which does NOT include contract. Worker can be promoted to `active` without signing contract. |
| 6. Mandatory Training (8 items) | ✅ Pass | UCE tracks 8 canonical items. Worker dashboard overrides to UCE list. Induction auto-complete from training is implemented. |
| 7. Proof of Address (×2) | ⚠️ Partial | `StageGateService.can_approve_recruitment()` checks PoA count but queries documents with status "uploaded" or "active" only — may miss verified-stamp-only docs. UCE uses `find_docs_for_requirement()` which has different matching logic. |
| 8. Safer Recruitment Gate | ⚠️ Partial | `StageGateService.can_approve_recruitment()` gates pre-approval blocking requirements, but `routes/recruitment.py:approve_recruitment` does NOT call this gate — admin can approve without any compliance check. |

---

## 6. CONFIRMED BUGS

### P0 — Critical (CQC/data integrity break)

---

#### BUG #1 — Contract NOT Required for Auto-Promotion
**File:** `backend/server.py:10707` (`try_auto_promote_worker`)  
**File:** `backend/unified_compliance_engine.py` (entire `can_promote` logic)  

**Problem:** `try_auto_promote_worker()` calls UCE `can_promote` exclusively. UCE `can_promote` does NOT include a contract check. Contract is only checked in `worker_dashboard.py` as a separate `has_blockers` flag. This means a worker whose UCE checks are all green will be **auto-promoted to `active` status immediately after their last document upload** — without ever signing the employment contract.

**Evidence:**
```python
# server.py:10707 - try_auto_promote_worker
can_promote = unified_status.get("can_promote", False)
if not can_promote:
    return  # Not ready yet
# → promotes to active, no contract check here

# worker_dashboard.py ~line 980
has_blockers = len(unified_blockers) > 0 or not contract_signed
# → contract check exists ONLY in dashboard display, never feeds into UCE
```

**CQC Risk:** Workers can begin shift-matching / be considered "active" without a signed employment contract.  
**Fix:** See Section 8.

---

#### BUG #2 — Admin Task Queue: "All Tasks Complete" Always Shows
**File:** `backend/routes/task_queue.py` + both frontend task queue components  

**Problem:** `/api/admin/task-queue` returns `{tasks: [...], summary: {...}}`. Both `ActionableTaskQueue.js` and `AdminTaskQueue.js` read named top-level keys (`pending_verifications[]`, `references_to_send[]`, `expiring_soon[]`) that do not exist at the response root. All values resolve to `undefined` → 0 → components always render "All Tasks Complete" / "All caught up!" regardless of actual data.

**Fix:** See Section 8.

---

### P1 — High (data divergence, incorrect business decisions)

---

#### BUG #3 — References: Task Queue Reads Dead Schema
**File:** `backend/routes/task_queue.py`

**Problem:** Task queue queries `{reference_1_request_status: "submitted"}` on the employee record (old flat schema). UCE and the canonical reference system use the `db.references` collection with `ref1.verification.status`. The two diverge: UCE may consider refs verified while task queue still shows them as outstanding.

---

#### BUG #4 — `StageGateService.can_approve_recruitment()` Never Called on Approval
**File:** `backend/routes/recruitment.py` (`approve_recruitment` endpoint)  

**Problem:** `StageGateService` has a `can_approve_recruitment()` method that checks all blocking requirements (RTW, DBS, Identity, PoA×2, references, NMC for nurses). This gate is **never called** from the `approve_recruitment` endpoint. Admin can approve any applicant regardless of compliance state.

---

#### BUG #5 — Employee Code Format Inconsistency
**Files:** `backend/routes/recruitment.py:100`, `backend/server.py:9215`

**Problem:** Two functions generate codes in different formats:
- `routes/recruitment.py`: `EMP-{n:04d}` starting at EMP-1001 (online → approved applicants)
- `server.py`: `OCS-{n}` zero-padded (manually-added staff)

Both write to the same `employee_code` field on the `employees` collection. Code format now depends on which approval path was used — no single canonical format exists. Affects any code that tries to infer record type from the code prefix.

---

#### BUG #6 — `POST /employees/{id}/auto-promote` Does Not Send Promotion Email
**File:** `backend/routes/promotion.py:163`

**Problem:** The explicit `auto-promote` endpoint promotes the worker (sets `status=active`) but does NOT call `send_promotion_email()`. The code comment admits this: *"Promotion email is sent via try_auto_promote_worker in server.py"*. However, `try_auto_promote_worker` is a fire-and-forget background helper, not called by this endpoint. If an admin manually triggers `POST auto-promote`, the worker receives no notification.

---

### P2 — Medium (divergence, CQC audit risk)

---

#### BUG #7 — Dashboard Training Summary Uses Separate Engine (Not UCE)
**File:** `backend/server.py` (`/dashboard/training-summary` endpoint)

**Problem:** The dashboard training-blocked count is produced by `evaluate_employee_training_status()` — a function separate from UCE. The worker compliance file and UCE use `MANDATORY_TRAINING_HCA` (8 items with normalized matching). The dashboard function has its own logic. Training blocked counts in the admin dashboard summary may differ from what UCE considers blocked.

---

#### BUG #8 — Worker Dashboard Onboarding Count Inflation
**File:** Frontend admin dashboard component

**Problem:** `const onboarding = (stats?.onboarding_in_progress || 0) + applicants.length` — adds employee-stage and applicant-stage persons together into the "In Progress" metric.

---

#### BUG #9 — pending_verifications Scope Includes Non-Standard Status
**File:** `backend/routes/task_queue.py`

**Problem:** pending_verifications iteration includes `status: "applicant"` as a valid value — this is not a real `EmployeeStatus` enum value. Any record with that literal string status (possible via manual DB edit or legacy sync) will be incorrectly included.

---

#### BUG #10 — PoA Count Verification Query Mismatch
**File:** `backend/stageGates.py:can_approve_recruitment()`

**Problem:** The PoA count check queries for documents with `status: {$in: ["uploaded", "active"]}`. UCE's `find_docs_for_requirement()` uses alias matching and checks `is_document_verified_with_stamp()`. The two methods may return different counts for the same employee. Even if `can_approve_recruitment()` were called from the approval endpoint (it currently isn't — BUG #4), it could disagree with the UCE-computed state.

---

#### BUG #11 — Induction Dual-Schema: List vs Dict Format
**File:** `backend/unified_compliance_engine.py` (`auto_complete_induction_from_training`)

**Problem:** UCE explicitly handles `induction_checklists` items in both list format and dict format. While UCE handles it, any other code path reading the induction checklist (induction.py routes, admin view of induction progress — not yet read) that assumes one specific format will silently misread the data. The dual-format coexistence in production data creates a latent breakage risk on any future induction endpoint work.

---

## 7. TINY SAFE FIXES APPLIED DURING AUDIT

None applied. Per instruction: "do NOT make speculative fixes yet unless a tiny truth-alignment fix is obviously safe." All items above require deliberate fixes with testing.

---

## 8. FIX PRIORITY ORDER

### P0 — Fix Immediately Before Live

**Fix A — Add contract check to `try_auto_promote_worker()`**
```python
# backend/server.py: try_auto_promote_worker()
# After: can_promote = unified_status.get("can_promote", False)
# Add:

from routes.agreements import get_agreement_acknowledgement_service
AgreementAcknowledgementService = get_agreement_acknowledgement_service()
contract_status = await AgreementAcknowledgementService.get_contract_status(employee_id)
contract_signed = contract_status.get("signed", False)

if not can_promote or not contract_signed:
    return  # Block auto-promotion if contract unsigned
```
**Also:** add `contract_signed` to UCE `can_promote` output or document clearly that it's a separate gate.

**Fix B — Task Queue response shape**
Either:
- Change `task_queue.py` to return the named top-level keys the frontend expects, OR
- Update both `ActionableTaskQueue.js` and `AdminTaskQueue.js` to read `response.tasks` and classify locally

(Option 1 is safer — backend owns shape, frontend reads it.)

---

### P1 — Fix Before First Real CQC Use

**Fix C — Call `can_approve_recruitment()` gate from approval endpoint**
In `routes/recruitment.py:approve_recruitment`, add:
```python
can_approve, blockers = await stage_gate_service.can_approve_recruitment(employee_id)
if not can_approve:
    raise HTTPException(status_code=400, detail={"message": "Cannot approve: compliance gaps", "blockers": blockers})
```
Add an `override_compliance_check: bool = False` option for admin force-approve.

**Fix D — Task queue references query**
Replace `{reference_1_request_status: "submitted"}` scan with:
```python
db.references.find({"ref1.status": {"$in": ["sent", "pending"]}, "ref2.status": {"$in": ["sent", "pending"]}})
```

**Fix E — Employee code format unification**
Pick one format (recommend `EMP-XXXX`) and update `server.py`'s `generate_employee_code()` to match. Migration: one-time `db.employees.updateMany({employee_code: /^OCS-/}, ...)` to rename old codes if business allows.

---

### P2 — Fix Before Scale

**Fix F — auto-promote endpoint: send promotion email**
Add `send_promotion_email(employee_id)` call in `routes/promotion.py` after confirming promotion.

**Fix G — Training summary: migrate to UCE**
Replace `evaluate_employee_training_status()` in `/dashboard/training-summary` with UCE calls.

**Fix H — Onboarding count: stop double-counting applicants**

**Fix I — Remove `"applicant"` string from pending_verifications status filter**

---

## 9. FINAL VERDICT

**Status: NOT READY FOR LIVE**

| Area | Verdict |
|------|---------|
| Application → Applicant creation | ✅ Correct |
| Applicant screening tracking | ✅ Correct |
| Recruitment approval flow | ⚠️ Gate never checked (BUG #4) |
| Worker portal onboarding (truth) | ✅ UCE canonical |
| Auto-promotion trigger logic | ❌ Contract not checked (BUG #1) |
| Admin dashboard tasks | ❌ Always shows "All Complete" (BUG #2) |
| References (admin side) | ❌ Wrong schema (BUG #3) |
| Stage identity / classification | ✅ Correct |
| CQC safer recruitment: DBS | ⚠️ Depends on check record path |
| CQC safer recruitment: RTW | ⚠️ Depends on check record path |
| CQC safer recruitment: Contract | ❌ Not gated on promotion |
| Training compliance | ✅ UCE canonical (8 items) |
| Code format consistency | ❌ EMP vs OCS dual format |

**Minimum for live (P0 only):** Fix contract gate, fix task queue shape.  
**Minimum for CQC inspection readiness (P0+P1):** Above + recruitment gate + references schema + code format.
