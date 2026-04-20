# CQC / Safer-Recruitment Audit Report
## Candidate: Olumide OBEMBE
**Profile ID:** `9355cb2a-99f3-4d61-b021-40ee7fcd911b`  
**Date:** 2025-02-03  
**Auditor:** GitHub Copilot (code-path analysis)  
**Method:** Static analysis of live codebase + MongoDB schema + stage-gate logic. Live profile requires authentication; data-level findings are marked **[VERIFY IN DB]** where a Mongo query is needed to confirm.

---

> **Important caveat:** The UI "100% complete" badge CANNOT be used as evidence of compliance. See Finding SG-1 below — the badge is driven by a different compliance engine than the stage gate that governs actual approval.

---

## Section A — Right to Work

| Check | Status | Evidence |
|---|---|---|
| RTW document uploaded | **[VERIFY IN DB]** | `db.employee_documents` where `requirement_id` matches `right_to_work` |
| RTW document verified by admin | **[VERIFY IN DB]** | `slot.verified == True` on slot with `requirement_key: "right_to_work"` |
| RTW expiry tracked | Code supports it (`expiry_tracked: True` in definition) | Extraction must have populated `expiry_date` field |
| RTW extraction result (AI) | Code-path: OpenAI primary → Gemini fallback | Empty AI result now blocked with severity `blocker`; check `issues` array on the document |
| UK share code / document type | **[VERIFY IN DB]** | Field `document_number`, `country_of_issue`, `valid_until` on RTW record |

**CQC risk:** If RTW slot (`requirement_key: "right_to_work"`) has `verified: False`, the stage gate will block approval regardless of what the worker uploaded. See SG-1 below for the schema split issue.

---

## Section B — Identity Documents

| Check | Status | Evidence |
|---|---|---|
| Passport or photo ID uploaded | **[VERIFY IN DB]** | `requirement_id` pattern `identity` |
| Identity slot verified | **[VERIFY IN DB]** | `slot.verified` on `requirement_key: "identity"` |
| Proof of Address — 2 documents | **[VERIFY IN DB]** | `can_approve_recruitment` requires `poa_min_files=2` verified PoA docs |
| PoA policy min_files | **Confirmed in code** | `role_policies.get("poa_min_files", 2)` — default 2 for care assistant |
| PoA within 12-month validity | Code tracks `validity_months: 12` | Must check `expiry_date` or issue date on each PoA document |

**CQC risk:** If only 1 PoA document is verified, the stage gate explicitly blocks even if the "compliance score" shows 100%.

---

## Section C — DBS Check

| Check | Status | Evidence |
|---|---|---|
| DBS record exists | **[VERIFY IN DB]** | `db.dbs_checks` where `employee_id = "9355cb2a..."` |
| DBS type (Enhanced / Standard) | **[VERIFY IN DB]** | Field `check_type` on DBS record |
| DBS number recorded | **[VERIFY IN DB]** | Field `certificate_number` |
| DBS slot verified | **[VERIFY IN DB]** | `requirement_key: "dbs"` slot has `verified: True` |
| DBS required before first placement | Code enforces this (`dbs_required_before_approval: True` default) | Confirmed via `role_policies` in `stageGates.py` |
| DBS on Update Service | **[VERIFY IN DB]** | No field in schema currently tracks Update Service subscription — **gap** |

**CQC risk:** No explicit field tracking DBS Update Service subscription. An enhanced check with no Update Service subscription must mean re-certificate on expiry. System does not currently enforce this distinction.

---

## Section D — References

| Check | Status | Evidence |
|---|---|---|
| Reference 1 — referee contact recorded | **[VERIFY IN DB]** | `metadata` field on `requirement_key: "reference_1"` slot |
| Reference 1 — verified | **[VERIFY IN DB]** | `slot.verified` on `reference_1` slot |
| Reference 2 — verified | **[VERIFY IN DB]** | `slot.verified` on `reference_2` slot |
| Reference decision propagated to worker | **CODE BUG (BUG-W9)** | Admin decision stored as `bool` (`accepted: True`), but worker dashboard checks for string `'accepted'` — **type mismatch means decision never reaches worker side** |
| 10-year employment history coverage | **[VERIFY IN DB]** | References must cover full 10-year history; system does not enforce this gap check |
| Employment gap engine run | **[VERIFY IN DB]** | `employment_gap_engine.py` must have run and raised no unresolved gaps |
| Gaps explained and documented | **[VERIFY IN DB]** | `form_submissions` for `employment_history_10yr` |

**CQC risk (HIGH):** BUG-W9 means references may appear "accepted" in the admin view but that decision never propagates. If references were accepted purely through the admin toggle (and worker was never re-sent a confirmation), the audit trail for reference acceptance is broken.

---

## Section E — Training Records

| Check | Status | Evidence |
|---|---|---|
| Mandatory training list matches role | Code-driven per `role_pack` | `get_role_pack("care_assistant")` determines mandatory list |
| Training records exist | **[VERIFY IN DB]** | `db.training_records` where `employee_id = ...` and `status: "verified"` |
| All mandatory training verified | **[VERIFY IN DB]** | Only `verified: True` records count toward compliance — `awaiting_review` does NOT pass |
| Training expiry dates | **[VERIFY IN DB]** | Fields `expires_at` on each training record |
| Training certificates on file | Code requires file attachment | `file_id` field on training record |
| Shadow Shift Completed sign-off | **[VERIFY IN DB]** | No confirmed admin creation UI for shadow shift sign-off record (BUG-W11 from previous audit) |
| Induction checklist completed | **[VERIFY IN DB]** | `db.induction_checklists` where `employee_id = ...` and `status: "completed"` |

**CQC risk:** Training count displayed on the admin dashboard card may be hardcoded/stale. The actual compliance evaluation uses `training_evaluator.py` which only counts `verified: True` records. Any certificate uploaded but not yet reviewed (`awaiting_review`) will block compliance.

---

## Section F — Professional Registration (if applicable)

| Check | Status | Evidence |
|---|---|---|
| Role stored in correct field | **[VERIFY IN DB]** | If `employee.role` vs `employee.job_role` mismatch, NMC check silently skipped (prior audit finding) |
| NMC / HCPC check required? | Code-path: only for `nurse` normalized role | If Obembe is a care assistant, NMC check is NOT required — correct |
| Care Certificate obtained | **[VERIFY IN DB]** | `care_certificate_config.py` defines completion criteria |

---

## Section G — Fit and Proper Person / Declaration

| Check | Status | Evidence |
|---|---|---|
| `fit_proper_persons` form completed | **[VERIFY IN DB]** | `form_submissions` where `form_type: "fit_proper_persons"` |
| Declaration valid for this role | **CODE BUG (BUG-W4)** | `fit_proper_persons` form is shown to ALL workers — Reg 5 declaration is only valid for registered managers. If Obembe is a care assistant, this declaration has no regulatory weight and its presence is misleading |
| Conflict of interest form | **[VERIFY IN DB]** | `form_submissions` where `form_type: "conflict_of_interest"` — but BUG-W7: admin cannot review this as a structured form |

---

## Section H — Contract and Pre-Employment Checks

| Check | Status | Evidence |
|---|---|---|
| Contract signed | **[VERIFY IN DB]** | `db.form_submissions` or `db.contract_templates` |
| Contract visible to worker | **CODE BUG (BUG-W2)** | Contract is signed but not surfaced in the worker portal — worker has no downloadable copy |
| Interview record exists | **[VERIFY IN DB]** | `db.interviews` or `form_submissions` for interview |
| Interview score recorded | **[VERIFY IN DB]** | `interview_questions.py` drives interview structure |

---

## Section I — System Structural Findings (Stage Gate Analysis)

### SG-1 — CRITICAL: Dual Document Schema (requirement_key vs requirement_id)

**Severity: HIGH**

The stage gate `can_approve_recruitment()` in `stageGates.py` queries `db.employee_documents` using the field `requirement_key`:
```python
slot = await self.db.employee_documents.find_one({
    "employee_id": employee_id,
    "requirement_key": req_key  # e.g. "right_to_work"
})
```

Worker portal uploads (`POST /worker/upload-document/{requirement_id}`) store documents using `requirement_id`, not `requirement_key`. These are statically different fields on different document records.

**Two possible outcomes:**
1. ✅ If `stageGates.generate_requirements_for_employee()` was called at application time → slots exist with `requirement_key`. Admin verifies the slot record itself → gate passes.
2. ❌ If slots were never generated (e.g. the applicant was manually created, bypassing the application form route) → `find_one(requirement_key=...)` returns `None` and all requirements show as "slot not found" → gate permanently blocks regardless of what the worker uploaded.

**Audit action:** Run the following query for this candidate:
```javascript
db.employee_documents.find(
  { employee_id: "9355cb2a-99f3-4d61-b021-40ee7fcd911b" },
  { requirement_key: 1, requirement_id: 1, verified: 1, status: 1 }
)
```
If no documents have `requirement_key` set, the entire stage gate is non-functional for this profile.

---

### SG-2 — is_verified_doc Threshold

`is_verified_doc` accepts a document as verified if `verification_stamp not in [None, "", "not_verified"]`. This means any non-null stamp value (including e.g. `"pending"`) passes the check. This is not an explicit admin sign-off.

---

### SG-3 — Compliance Score ≠ Stage Gate

The UCE (Unified Compliance Engine) and the `stageGates.can_approve_recruitment()` function are independent. A worker can show "100% compliant" in the dashboard while `can_approve_recruitment` still returns blockers — e.g. if PoA has only 1 verified file, or if slots don't have `verified: True`.

---

## Overall CQC Risk Assessment

| Domain | Risk Level | Blocker? |
|---|---|---|
| Right to Work | Cannot confirm without DB access | Yes if slot unverified |
| Identity | Cannot confirm | Yes if slot unverified |
| Proof of Address (2 docs) | Cannot confirm | Yes — 2 required |
| DBS | Cannot confirm; no Update Service tracking | Yes if slot unverified |
| References | **BUG-W9 data corruption risk** | Yes |
| Training | Cannot confirm `verified: True` for all mandatory | Yes |
| Shadow Shift | No admin UI confirmed | Depends on config |
| Contract | BUG-W2 — worker has no copy | Compliance concern |
| Fit & Proper | BUG-W4 — invalid if care assistant | Documentation concern |
| Stage Gate slots | **SG-1 — may not exist for this profile** | Yes |

---

## Recommended Actions Before Any CQC Inspection

1. **Query MongoDB directly** for all `employee_documents` where `employee_id = "9355cb2a..."` — confirm slots with `requirement_key` exist and have `verified: True`.
2. **Check BUG-W9 fix status** — confirm reference acceptance is stored as `string "accepted"` not `bool True`, otherwise re-verify references.
3. **Confirm 2× PoA documents** are both verified (not just uploaded).
4. **Confirm DBS is Enhanced** with a valid certificate number and confirm workforce's position on the Update Service.
5. **Check all mandatory training records** have `status: "verified"` (not `awaiting_review`).
6. **Confirm shadow shift sign-off record exists** for this employee.
7. **Do not rely on UI "100% complete" badge** — run `can_approve_recruitment("9355cb2a...")` directly against the live DB and inspect the returned `blockers` list.
8. **Apply BUG-W9 fix** before any inspection — reference decision type mismatch must be resolved.

---

*End of audit report. This report is based on static code analysis and cannot substitute for a live database-level compliance check. No live profile data was accessible to the auditor.*
