# Adjacent-Risk Verification Pass: Evidence Lifecycle
**Date:** 2025-12-30

## SCOPE CHECKED

### Endpoints Verified
1. `/api/employees/{id}/compliance-requirements` — Main requirement row builder
2. `/api/employees/{id}/requirements/{req_id}/evidence` — Evidence drawer
3. `/api/training-records` — Training list
4. `/api/employees/{id}` — Employee profile (work readiness)

### Collection Queries Verified
- `training_records` — Now filtered by `record_status: {"$nin": ["superseded", "deleted"]}`
- `employee_documents` — Now filtered by `status: {"$nin": ["superseded", "archived", "deleted"]}`

---

## ADDITIONAL BUGS FOUND AND FIXED

### Bug 1: Training records query not filtering superseded/deleted
**Location:** `server.py:8535`
**Fix:** Added `"record_status": {"$nin": ["superseded", "deleted"]}` to query

### Bug 2: Evidence endpoint training query missing filter
**Location:** `server.py:7016`
**Fix:** Added `"record_status": {"$nin": ["superseded", "deleted"]}` to query

### Bug 3: Evidence endpoint document query missing filter  
**Location:** `server.py:7056`
**Fix:** Added `"status": {"$nin": ["superseded", "archived", "deleted"]}` to query

### Bug 4: Quick work readiness training query missing filter
**Location:** `server.py:4375`
**Fix:** Added `"record_status": {"$nin": ["superseded", "deleted"]}` to query

### Bug 5: Missing `status: "active"` on evidence file objects
Multiple paths were returning evidence files without explicit status:
- Form submission evidence (line 8820)
- Legacy certificate evidence (line 8885)
- Legacy document evidence (line 8727)
- Form PDF evidence (line 8780)

**Fix:** Added `"status": "active"` to all evidence file objects

---

## VERIFICATION RESULTS

| Scenario | Status | Notes |
|----------|--------|-------|
| Upload -> Remove -> Reload | ✅ PASS | Removed files not in evidence_files |
| Upload -> Replace -> Reload | ✅ PASS | Only new file shows, old file superseded |
| Multiple files -> Remove one -> Count | ✅ PASS | evidence_count matches active files |
| Remove last file -> Status recompute | ✅ PASS | completion_date reset, status="not_started" |
| Verified -> Evidence changed | ✅ PASS | Compliance state reflects current evidence |

---

## FILES CHECKED

- `/app/backend/server.py` — All evidence-related functions
- Training-backed rows: ✅
- Document-backed rows: ✅  
- Form-backed rows: ✅

---

## CURRENT STATE

All evidence files now return with explicit `status: "active"` field.
All removed/superseded files are filtered out at the database query level.
The frontend receives only active evidence and can trust the counts.

**Evidence UI is now consistent everywhere.**
