# Evidence File Lifecycle Bug Fix Report
**Date:** 2025-12-30  
**Issue:** Wrong certificate file cannot be removed/replaced cleanly - still visible in UI

---

## ROOT CAUSE

The backend endpoints that build the `evidence_files` array for compliance requirements were including ALL files from the database WITHOUT filtering by status. This meant:

1. When a file was soft-removed (marked as `status: 'removed'`), it was still included in the `evidence_files` array
2. The `evidence_count` field was counting ALL files, not just active ones
3. The frontend had filtering logic BUT the backend was sending incorrect counts

**Affected Code Locations:**
- `server.py:8843` — Training evidence collection
- `server.py:8691` — Document evidence collection
- `server.py:7459` — Soft-remove training (missing completion_date reset)

---

## FILES CHANGED

**`/app/backend/server.py`**

### Fix 1: Filter training evidence files (Line ~8843)
Added filter to skip removed/superseded files when building evidence array:
```python
for ef in linked_training['evidence_files']:
    # HARDENING: Skip removed/superseded files - only include active files
    file_status = ef.get('status', 'active')
    if file_status not in ['active', None]:
        continue  # Skip removed/superseded/archived files
```

### Fix 2: Filter document evidence files (Line ~8691)
Added same filter for document evidence:
```python
for ef in doc['evidence_files']:
    # HARDENING: Skip removed/superseded files - only include active files
    file_status = ef.get('status', 'active')
    if file_status not in ['active', None]:
        continue  # Skip removed/superseded/archived files
```

### Fix 3: Reset completion_date on soft-remove (Line ~7459)
When all active files are removed, reset the training record properly:
```python
if not active_files:
    update_data["verified"] = False
    update_data["completion_method"] = "manual"
    update_data["completion_date"] = None  # Reset so status derives to "not_started"
    update_data["certificate_url"] = None
```

---

## EVIDENCE FILE LIFECYCLE

### Upload
- File stored with `status: 'active'` in `evidence_files` array

### Replace
- Old file marked as `status: 'superseded'`
- New file added with `status: 'active'`

### Soft-Remove (Recommended)
- File marked as `status: 'removed'`
- Kept in array for audit history
- Not counted in `evidence_count`
- Not shown as active evidence

### Hard-Delete (Permanent)
- File removed from `evidence_files` array entirely
- Storage file deleted
- Audit log entry created

### Active vs Inactive Visibility
| Status | Shown in Current Evidence? | Counted? | Audit History? |
|--------|---------------------------|----------|----------------|
| active | YES | YES | YES |
| superseded | NO | NO | YES |
| removed | NO | NO | YES |

---

## VERIFICATION

After fix, the API correctly returns:
- Only active files in evidence arrays
- Correct `evidence_count` for compliance calculations
- Removed/superseded files preserved for audit history but not shown as current

Example API response:
```json
{
  "training_name": "Safeguarding",
  "evidence_count": 1,
  "evidence_files": [
    {
      "original_filename": "Certificate.pdf",
      "status": "active"
    }
  ]
}
```

---

## PROOF

After remove/reload:
1. ✅ Removed file no longer shows as current evidence
2. ✅ `evidence_count` correctly reflects only active files
3. ✅ Badges and readiness state refresh correctly
4. ✅ Removed file remains in audit history (soft-delete)
5. ✅ No silent failure on delete/remove

---

## CONSTRAINTS RESPECTED

- ✅ Did NOT migrate storage/database
- ✅ Did NOT move to Supabase
- ✅ Did NOT refactor broadly
- ✅ Patched current system safely
- ✅ Minimal surgical changes only
