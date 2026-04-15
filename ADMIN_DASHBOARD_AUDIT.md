# Admin Dashboard Audit Report
**Scope:** Admin dashboard truth vs actual system state — data sources, task queue logic, classification, OCS records  
**Date:** 2025-01  
**Method:** Full source read — no assumptions

---

## FILES INSPECTED

| File | Purpose |
|---|---|
| `frontend/src/pages/portal/DashboardPage.js` | Main dashboard component — all metrics |
| `frontend/src/components/admin/ActionableTaskQueue.js` | Task queue widget A |
| `frontend/src/components/admin/AdminTaskQueue.js` | Task queue widget B |
| `backend/routes/task_queue.py` | `/api/admin/task-queue` endpoint |
| `backend/server.py:23057` | `get_dashboard_stats()` |
| `backend/server.py:9646` | `get_employees_unified_progress_summary()` |
| `backend/routes/recruitment.py` | `/staff/employees`, `/recruitment/applicants` |

---

## SECTION 1 — DASHBOARD DATA SOURCES

### All metrics and their origins

| Dashboard Card | Source Endpoint | Computation |
|---|---|---|
| Workers Ready to Work | `/api/employees/unified-progress-summary` | `e.canonical_readiness?.is_work_ready === true` |
| Supervised Start | same | `can_promote === true && is_work_ready !== true` |
| Not Ready | same | `is_work_ready !== true && can_promote !== true` |
| Onboarding In Progress | `/api/dashboard/stats` + `/api/recruitment/applicants` | `stats.onboarding_in_progress + applicants.length` |
| Pending Verifications | `/api/dashboard/stats` | `stats.pending_verifications` |
| Total Employees | `/api/staff/employees` | `employees.length` |
| Expiry Alerts | `/api/dashboard/expiry-alerts` | backend computed |
| Training Summary | `/api/dashboard/training-summary` | backend computed |
| Task Queue (all items) | `/api/admin/task-queue` | **ALWAYS ZERO — see Bug #1** |

---

## SECTION 2 — "ALL TASKS COMPLETE" / "ALL CAUGHT UP" ROOT CAUSE (CONFIRMED)

### The bug

Both `ActionableTaskQueue.js` and `AdminTaskQueue.js` call `GET /api/admin/task-queue`. The backend returns:

```json
{
  "total_tasks": N,
  "tasks": [...],
  "summary": {
    "pending_verifications": N,
    "expiring_documents": N,
    "pending_references": N,
    "scheduled_tasks": N,
    "overdue_followups": N
  },
  "generated_at": "..."
}
```

### What ActionableTaskQueue.js reads (ALL UNDEFINED)

```js
tasks?.pending_verifications   // expects ARRAY  — backend has summary.pending_verifications (a number, not a top-level array)
tasks?.references_to_send      // expects ARRAY  — KEY DOES NOT EXIST IN BACKEND RESPONSE
tasks?.references_to_review    // expects ARRAY  — KEY DOES NOT EXIST IN BACKEND RESPONSE
tasks?.expiring_soon           // expects ARRAY  — KEY DOES NOT EXIST IN BACKEND RESPONSE
tasks?.stuck_workers           // expects ARRAY  — KEY DOES NOT EXIST IN BACKEND RESPONSE
tasks?.induction_incomplete    // number         — KEY DOES NOT EXIST IN BACKEND RESPONSE
tasks?.interviews_pending      // number         — KEY DOES NOT EXIST IN BACKEND RESPONSE
tasks?.spot_checks_due_this_week   // number     — KEY DOES NOT EXIST IN BACKEND RESPONSE
tasks?.supervision_due_this_week   // number     — KEY DOES NOT EXIST IN BACKEND RESPONSE
```

**Result:** `categoryCounts.all = 0 + 0 + 0 = 0` → triggers `"All Tasks Complete"` branch unconditionally.

### What AdminTaskQueue.js reads (ALL UNDEFINED → 0)

```js
tasks?.documents_pending_verification  // KEY DOES NOT EXIST
tasks?.references_pending_response     // KEY DOES NOT EXIST
tasks?.dbs_expiring_30_days            // KEY DOES NOT EXIST
tasks?.rtw_expiring_30_days            // KEY DOES NOT EXIST
tasks?.spot_checks_due_this_week       // KEY DOES NOT EXIST
tasks?.supervision_due_this_week       // KEY DOES NOT EXIST
tasks?.induction_incomplete            // KEY DOES NOT EXIST
tasks?.interviews_pending              // KEY DOES NOT EXIST
```

**Result:** `activeItems = []`, `totalTasks = 0` → triggers `"All caught up!"` branch unconditionally.

### What the backend actually has

`task_queue.py` collects real data into a **flat typed array**:
- `db.employee_documents.find({verification_stamp: None|""|"not_verified"})` → type: `"pending_verification"`
- `db.employee_documents.find({expiry_date: <= 30 days})` → type: `"expiring_document"`
- `db.employees.find({reference_1/2_request_status: "submitted"})` → type: `"reference_to_review"`
- `db.spot_checks.find({status: "scheduled", scheduled_date: <= 7 days})` → type: `"spot_check_due"`
- `db.competency_records.find({...})` → type: `"supervision_due"`
- `db.spot_checks.find({follow_up_required: True, ...})` → type: `"overdue_followup"`

This data is **never seen** by either frontend component. Both always show their "nothing to do" state regardless of actual system state.

---

## SECTION 3 — APPLICANT VS EMPLOYEE CLASSIFICATION

### Canonical classification (routes/recruitment.py)

```python
APPLICANT_STATUSES = ['new', 'screening', 'interview', 'compliance_review']
EMPLOYEE_STATUSES  = ['onboarding', 'active', 'inactive']
```

**`GET /api/recruitment/applicants`** → `{"status": {"$in": APPLICANT_STATUSES}}`  
**`GET /api/staff/employees`** → `{"status": {"$in": ["onboarding", "active"]}}` (inactive excluded unless flag set)

Classification is **purely by status field**. Employee code prefix (`OCS-` vs `APPLICANT-`) has **zero effect** on which endpoint a record appears in.

### `person_stage` derivation

Hardcoded at query time:
- `/recruitment/applicants` → `person_stage = "applicant"` on all records
- `/staff/employees` → `person_stage = "employee"` on all records

---

## SECTION 4 — OCS LEGACY RECORD HANDLING

### Code generation

All admin-added staff get `OCS-XXXX` codes (`server.py:9215`):
```python
return f"OCS-{str(num).zfill(4)}"
```

Online applicants get `APPLICANT-{uuid}` codes (from `POST /applications/structured`).

### Where OCS records appear

| OCS record status | Appears in | Dashboard impact |
|---|---|---|
| `new`, `screening`, `interview`, `compliance_review` | `/recruitment/applicants` | Added to `applicants.length` in onboarding count |
| `onboarding` | `/staff/employees` AND `stats.onboarding_in_progress` | Double-counted in onboarding metric (Bug #3) |
| `active` | `/staff/employees`, workforce readiness | Correct |
| `inactive` | `/staff/employees` (if flag set) | Correct |

No code-prefix filtering exists anywhere. An OCS-XXXX record with `new` status is identical to an APPLICANT-XXXX record with `new` status in every query.

---

## SECTION 5 — WORKFORCE READINESS (CANONICAL — MOST ACCURATE METRIC)

Workforce Readiness IS built on the canonical UCE:

1. `DashboardPage.js` fetches `/api/staff/employees` → filters client-side to `['onboarding','active','inactive']`
2. Calls `/api/employees/unified-progress-summary?employee_ids=...`
3. Backend calls `get_unified_employee_status(employee_id, db, user_role="admin", include_details=False)` per employee
4. Returns `{is_work_ready, can_promote, overall_percentage, blockers, blocker_count}`
5. On UCE error: defaults to `{is_work_ready: false, can_promote: false}` → employee counts as "Not Ready"

**This metric is correct.** An employee with `is_work_ready = false` genuinely cannot work. The Workforce Readiness card accurately reflects canonical compliance state.

---

## SECTION 6 — ALL BUGS FOUND

### BUG #1 — Task Queue Response Shape Mismatch [CRITICAL — ROOT CAUSE]

**Severity:** P0  
**Effect:** Both task queue components permanently show "All Tasks Complete" / "All caught up!" regardless of true state  
**Root cause:** Backend `task_queue.py` returns `{tasks: [...], summary: {...}}` — frontend reads named top-level keys that don't exist  
**Fix options (pick one):**  
- Option A (recommended): Update `task_queue.py` to also return named top-level arrays matching what the frontend reads
- Option B: Update both frontend components to read `tasks[]` with `.filter(t => t.type === "...")` instead of named keys

---

### BUG #2 — Pending Verifications count is real, but task queue (which should list them) is always empty

**Severity:** P1  
**Effect:** Dashboard "Needs Attention" card shows a nonzero pending verifications count. Task queue shows 0. Logically inconsistent — admin sees a problem count but no actionable list.  
**Root cause:** These come from two different sources:
- Count: `dashboard/stats` iterates `employee_documents` collection → CAN be nonzero
- Task queue: `task_queue.py` returns real items in `tasks[]` but frontend never reads them (Bug #1)

Both would be resolved by fixing Bug #1.

---

### BUG #3 — Onboarding Count Inflation

**Severity:** P1  
**Effect:** "In Progress" count on dashboard is misleadingly large  
**Location:** `DashboardPage.js`  
```js
const onboarding = (stats?.onboarding_in_progress || 0) + applicants.length;
```
- `stats.onboarding_in_progress` = `db.employees.count_documents({status: "onboarding"})` — employee-stage people
- `applicants.length` = everyone in `new/screening/interview/compliance_review` — pre-employee-stage people  

These are mutually exclusive by status. Adding them produces a "total pipeline" number labeled as "In Progress."  
**Fix:** Rename or split this metric to clarify it's "total pipeline" not just "in onboarding."

---

### BUG #4 — `dashboard/stats` Pending Verifications Uses Over-Broad Scope

**Severity:** P2  
**Location:** `server.py:23057` `get_dashboard_stats()`  
**Issue:** Iterates employees with status:
```python
["new", "screening", "interview", "compliance_review", "onboarding", "applicant"]
```
Problems:
- `"applicant"` is a non-standard status string, not a defined `EmployeeStatus` enum value — no record should have this status, making it a dead query condition that adds noise
- Scope mixing: `onboarding` is employee-stage; `new/screening/interview/compliance_review` are applicant-stage. Counting unverified docs across both is defensible but should be documented

---

### BUG #5 — References Query in task_queue.py Uses Old Flat Schema

**Severity:** P2  
**Location:** `backend/routes/task_queue.py`  
```python
db.employees.find({
    "$or": [
        {"reference_1_request_status": "submitted"},
        {"reference_2_request_status": "submitted"}
    ]
})
```
**Issue:** Uses deprecated flat employee fields. The canonical references system uses `db.references` collection with nested `ref1/ref2` documents. References sent through the modern system will NOT appear in this query. The task queue will miss most pending references.

---

### BUG #6 — `fully_verified_count` in dashboard/stats Uses Legacy Evidence Schema

**Severity:** P2  
**Location:** `server.py:23057`  
Queries `db.employee_documents.find_one({"requirement_type": "evidence_store"})` — this is a legacy document schema structure not used by the current UCE, which queries `employee_documents` by `requirement_id`. The `fully_verified_count` on the dashboard card derives from an orphaned query pattern and may return 0 or stale data for all employees.

---

## SECTION 7 — WHAT CAUSES FALSE DASHBOARD CLEANLINESS

The dashboard can simultaneously show:
- "Pending Verifications: 12" (real, from `dashboard/stats`)
- "Employees Not Ready: 5" (real, from workforce readiness)
- "All Tasks Complete" (always fake — Bug #1)
- "All caught up!" (always fake — Bug #1)

The task queue components are the dashboard's primary action surface. They are **permanently broken**. An admin opening the dashboard will see numeric indicators of problems but no actionable task list, creating the false impression that all problems are already being handled.

---

## SECTION 8 — FIX PRIORITY ORDER

| Priority | Bug | Fix |
|---|---|---|
| P0 | Task queue response shape mismatch | Reshape `task_queue.py` to include named top-level arrays: `pending_verifications[]`, `references_to_send[]`, `references_to_review[]`, `expiring_soon[]`, `stuck_workers[]`, etc. **OR** update both frontend components to filter `tasks[]` by `.type` |
| P1 | Onboarding count inflation | Rename the metric or split into "applicants in pipeline" and "workers in onboarding" |
| P2 | References query uses flat schema | Update `task_queue.py` references query to use `db.references` collection |
| P2 | `dashboard/stats` scope includes `"applicant"` string | Remove non-enum status string from query |
| P2 | `fully_verified_count` uses legacy schema | Rewrite to use `employee_documents` with `requirement_id` query pattern |

---

## VERDICT

**The admin dashboard does not accurately represent system state.**

- Workforce Readiness is correct (canonical UCE).
- Pending Verifications count is correct (real DB query).
- The task queue — the primary action surface — is **permanently broken** and always shows "all clear" regardless of reality.
- Onboarding In Progress count is inflated by design.
- OCS legacy records are classified correctly by status; no code-prefix filtering exists or is needed.

The most urgent fix is Bug #1. Until the task queue response shape is aligned between backend and frontend, the dashboard provides false assurance to administrators.
