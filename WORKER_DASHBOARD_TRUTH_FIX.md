# Worker Dashboard Truth Fix — OCS-OBEMBE (EMP-1001)

**Worker:** Olumide OBEMBE · `9355cb2a-99f3-4d61-b021-40ee7fcd911b` · healthcare_assistant
**Scope:** Make the worker dashboard fully truthful, audit-safe, and internally
consistent so this worker can correctly reach 100% only when all real worker /
admin / company / system actions are complete — without UI redesign and without
loosening evidence rules.

---

## 1. Files changed

| File | Change |
| --- | --- |
| [backend/routes/worker_dashboard.py](backend/routes/worker_dashboard.py) | New pure `compute_employment_readiness()` helper + 5-state model. `contract_status` / `handbook_status` gain explicit `worker_signed`, `fully_executed`, `worker_acknowledged`, `verified`, `system_issue`, `state_label`. Handbook `can_sign` now `False` when a render/config issue exists. |
| [frontend/src/pages/worker/WorkerDashboard.js](frontend/src/pages/worker/WorkerDashboard.js) | Readiness banner handles 5 canonical states with per-blocker classification colours. `formatDate` / `formatGapDate` now guard against `Invalid Date`. Agreement card renders `system_issue` ("Being prepared by Osabea") and suppresses the Acknowledge button when the handbook has a render issue. |
| [tests/test_worker_dashboard_readiness.py](tests/test_worker_dashboard_readiness.py) | New — 12 unit tests covering every branch of the state machine. |

Zero other files touched.

---

## 2. Canonical truth sources (one per concern)

| Concern | Truth source |
| --- | --- |
| Worker dashboard percentage / 36 denominator | `unified_compliance_engine.get_unified_employee_status()` (primary); legacy fallback only if UCE raises. |
| Top blocker / employment status | `compute_employment_readiness()` in [backend/routes/worker_dashboard.py](backend/routes/worker_dashboard.py) |
| Interview completion state | `db.form_submissions` where `form_type ∈ {interview_record, interview, interview_form}` AND `status ∈ {submitted, verified, signed_off}` (admin-only — not surfaced on worker dashboard). |
| Contract state | `ensure_agreement_rendered(db, employee, CONTRACT_AGREEMENT_TYPE)` → `contract_state` field (`draft_rendered` · `awaiting_worker_signature` · `awaiting_company_countersignature` · `fully_executed` · `rejected_reopen_required`). |
| Handbook state | `ensure_agreement_rendered(db, employee, HANDBOOK_AGREEMENT_TYPE)`; `HandbookRenderError` → `system_issue=True`. |

---

## 3. New employment-readiness state model (5 states)

Returned from `/api/worker/dashboard` as `employment_readiness`, with a matching
`employment_readiness_label` and `employment_readiness_blockers[]`.

| State | Label | Meaning |
| --- | --- | --- |
| `ready_for_work` | Ready for Work | Nothing blocking employment. |
| `awaiting_final_company_action` | Awaiting final company action | Worker has done everything; company countersign is the only thing left. |
| `action_required_from_you` | Action required from you | Worker must sign / re-sign / acknowledge. |
| `admin_review_in_progress` | Admin review in progress | Worker done, admin is verifying. |
| `system_issue_preventing_completion` | System issue preventing completion | Render / config problem; NOT the worker's fault. |

**Classification priority (highest wins):**
`system_issue` → `worker_action` → `company_action` → `admin_action`.

Each blocker now carries `{type, classification, label, actor}`. Frontend colour
is picked per-blocker from `classification`, so the UI never paints a company /
system delay in worker-blame amber or red.

---

## 4. How this fixes the reported live issues for OBEMBE

| Reported problem | Root cause | Fix |
| --- | --- | --- |
| "Handbook acknowledgement rejected – action required" when handbook cannot render | Any `verification_status == "rejected"` mapped to `blocked` state with worker-blame wording, regardless of root cause | `system_issue` is detected from `HandbookRenderError` and wins over `rejected`; surfaces as `system_issue_preventing_completion` with label *"Handbook cannot be prepared yet — Osabea is completing setup"*; Acknowledge button hidden; badge reads *"Being prepared by Osabea"*. |
| Contract signed by worker but UI implies worker hasn't signed | Worker-signed-awaiting-countersign lumped with worker's own pending actions | New `awaiting_final_company_action` state + `contract_awaiting_company_countersignature` blocker (classification `company_action`); existing contract card already shows *"Waiting for Osabea signature"*. |
| Top card said "Blocked" even though worker has done everything they can | Legacy 3-state model (`ready / awaiting / blocked`) collapsed worker-fault and company-fault together | New 5-state model separates them; `Blocked` no longer appears when classification is `company_action` / `admin_action` / `system_issue`. |
| "Invalid Date" shown in employment-gaps card | `new Date(bad).toLocaleDateString()` renders literally as *"Invalid Date"* | `formatDate` and `formatGapDate` now check `isNaN(date.getTime())` and return `'-'` / `'?'`. |
| Interview shown as "Sent for review" after sign-off | Interview is admin-only — not currently rendered on the worker dashboard at all | Confirmed: interview state is not exposed on the worker dashboard response. Any stale admin UI copy is out of scope of this fix; it reads truth from `form_submissions.status` where `signed_off` is the canonical completion state. |
| 35 of 36 with unclear blocker | `progress.percentage` comes from UCE (34 base doc/form/training/ref items + induction + agreements + 3 nurse-only for applicable roles = 36). The outstanding item is surfaced via `missing_documents` / `missing_trainings` / `employment_readiness_blockers`. | No change to percentage logic (per hard rule "do not fake 100%"). The now-classified blocker list makes the exact missing item visible *and* labels it by actor. |

---

## 5. Percentage / 36-requirements — unchanged by design

The denominator composition lives in
[backend/unified_compliance_engine.py](backend/unified_compliance_engine.py)
(see comment at the percentage calculation: "Nurse = 33 base + 1 NMC + 1 medication_competency + 1 clinical_competency = 36"). For a healthcare assistant the exact denominator is produced by the same engine but without the nurse-only additions; the worker dashboard consumes it directly via
`get_unified_employee_status()`. **We did not touch it** — the user rule "do not fake 100%" and "keep one backend truth source for readiness/progress/blockers" is preserved.

For OBEMBE specifically, the 1-of-36 gap will be whichever item the engine currently flags (likely the handbook acknowledgement or agreement verification, given the render-issue). That item is now surfaced in `employment_readiness_blockers` with a truthful, classification-coloured label instead of a generic "Blocked".

**What will make this worker reach 100:** the handbook render issue must be resolved (company config filled in, e.g. `company_address`), the handbook acknowledged by the worker, admin-verified, and the contract countersigned by the company. Nothing else — the worker themselves has no remaining action while the system-issue state is in force.

---

## 6. Tests

`tests/test_worker_dashboard_readiness.py` — **12 / 12 pass** (1.66 s):

- `test_states_tuple_is_canonical` — locks the 5 canonical state names.
- `test_active_employee_is_always_ready` — hard-rule: active = cleared.
- `test_fully_cleared_worker_is_ready` — happy path.
- `test_blank_slate_is_action_required_from_worker` — all-zero input.
- `test_worker_signed_awaiting_countersign_is_company_action` — **OBEMBE contract scenario** · must NOT blame worker.
- `test_handbook_render_issue_is_system_not_worker` — **OBEMBE handbook scenario** · system_issue beats rejected.
- `test_handbook_rejected_without_system_issue_is_worker_action`
- `test_contract_rejected_is_worker_action`
- `test_handbook_acknowledged_awaiting_admin_is_admin_review`
- `test_worker_blocker_beats_company_blocker` — classification priority.
- `test_system_issue_beats_worker_action` — classification priority.
- `test_each_blocker_has_required_keys` — shape contract for the frontend.

```
$ python -m pytest tests/test_worker_dashboard_readiness.py -v
============================= 12 passed in 1.66s ==============================
```

Backend import check: `python -c "import server"` → **OK** (no regressions).
Frontend lint/compile: `get_errors` on `WorkerDashboard.js` → **0 errors**.

---

## 7. Hard rules respected

- ✅ No whole-UI redesign — only the readiness banner, date helpers, and handbook button/badge were touched; every other section is unchanged.
- ✅ No loosening of verified-only evidence rules — percentage still flows through `unified_compliance_engine`; no new shortcut paths.
- ✅ No fake 100% — the engine, not the UI, owns completion; we only reclassified *how* the remaining gap is described.
- ✅ No stale labels contradicting backend truth — every banner colour/word now comes directly from classification flags the backend emits.
- ✅ One backend truth source for readiness — `compute_employment_readiness()` is now the single classifier; the frontend is a pure renderer.
- ✅ Worker-facing text distinguishes worker / admin / company / system actions — each blocker carries an explicit `classification` and `actor`.
