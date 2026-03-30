# Completion Percentage Consistency Fix Report

**Date**: 2026-03-30
**Issue**: Progress/completion percentage inconsistent across pages (e.g., 83% on list vs 86% on profile)

---

## ROOT CAUSE

### Issue 1: Archived Items Not Excluded

The `calculate_employee_compliance()` function (used by employees list) did NOT exclude items with `archived: True` from the total count. However, the `compliance-requirements` endpoint (used by profile view) DID exclude them.

**Example**: `health_screening` is marked `archived: True` but was being counted in list view, adding 1 to the denominator.

**Result**: 
- List view: 20/24 = 83%
- Profile view: 20/23 = 86%

### Issue 2: Evidence Files With Superseded Status Counted

The `check_item_completion()` function checked for document existence using `file_url` but did NOT verify that the `evidence_files` array had active (non-superseded) files.

**Example**: `reference_1` had a `file_url` but its only evidence file had `status: "superseded"`. List view incorrectly counted it as complete.

**Result**: Inconsistent completed counts between views.

---

## FIX APPLIED

### File: `/app/backend/server.py`

**1. Added archived item exclusion** (line ~1480):
```python
# Skip archived items from compliance calculation (hidden from UI, historical only)
if item.get("archived", False):
    archived_count += 1
    continue

# Total excludes optional and archived items
total_items = len(mandatory_items) - optional_count - archived_count
```

**2. Fixed evidence_files status check** (line ~1370):
```python
# Check evidence_files array for active files
evidence_files = doc.get('evidence_files', [])
if evidence_files:
    for ef in evidence_files:
        ef_status = ef.get('status', 'active')
        if ef_status in ['active', None] and ef.get('file_url'):
            has_active_evidence = True
            break
# Fallback: check file_url (legacy format) only if no evidence_files with any status
elif doc.get('file_url'):
    has_active_evidence = True
```

---

## CANONICAL FORMULA

**Completion Percentage** = `(completed_items / total_items) * 100`

Where:
- **completed_items**: Items with status "complete" or "completed" AND active evidence
- **total_items**: All mandatory items EXCLUDING:
  - Items marked `optional: true`
  - Items marked `archived: true`
  
An item is considered "complete" if:
- **Training**: Has `training_record` with `record_status` not deleted/superseded AND has `certificate_url` or active `evidence_files`
- **Document**: Has `employee_document` with active status AND (`file_url` OR at least one active evidence file)
- **Form**: Has `form_submission` with status not deleted/superseded

---

## VERIFICATION

| Employee | List % (Before) | Profile % (Before) | List % (After) | Profile % (After) | Match |
|----------|-----------------|--------------------|--------------  |-------------------|-------|
| Olakunle Alonge | 83% | 86% | 86% | 86% | ✅ |
| Lawrence Egbeni | 66% | 65% | 65% | 65% | ✅ |
| Henrietta Omo-Igene | 47% | 43% | 43% | 43% | ✅ |
| OLUMIDE OBEMBE | 52% | 52% | 52% | 52% | ✅ |
| Ayomi Lori | 53% | 53% | 53% | 53% | ✅ |
| Ramon Akinsanya | 56% | 56% | 56% | 56% | ✅ |
| Olufisayo Ojo | 42% | 42% | 42% | 42% | ✅ |

**All employees now show consistent percentages across all views.**

---

## PAGES/VIEWS AFFECTED

| View | Source | Status |
|------|--------|--------|
| Dashboard | `calculate_employee_compliance()` | ✅ Fixed |
| Employees List | `calculate_completion_percentage()` → `calculate_employee_compliance()` | ✅ Fixed |
| Employee Profile | `compliance-requirements` endpoint | Reference (already correct) |
| Audit View | Uses compliance data | ✅ Fixed |

---

## FILES CHANGED

| File | Line | Change |
|------|------|--------|
| `/app/backend/server.py` | ~1480 | Added `archived_count` tracking and filtering |
| `/app/backend/server.py` | ~1520 | Updated total calculation to exclude archived |
| `/app/backend/server.py` | ~1370 | Fixed evidence_files status check for documents |

---

## REMAINING CONSIDERATIONS

1. **Stored percentages**: No compliance percentages are stored in DB - all calculated at runtime (correct SSOT behavior)
2. **Dashboard widgets**: All use the same `calculate_employee_compliance()` function now
3. **Audit trail**: No changes to audit logging - this fix corrects calculation logic only
