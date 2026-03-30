# Upload-to-Display Regression Fix

## Issue
After the evidence lifecycle hardening pass, newly uploaded training certificates were showing "success" toast but not appearing in the requirement row. Status remained "Still Needed" despite successful upload.

## Root Cause
The training upload endpoint `/employees/{id}/training/{req_id}/upload-certificate` was finding ANY existing training record (including deleted ones) and updating it. However, the compliance-requirements API filters out records with `record_status: "deleted"`.

This caused a "silent success" scenario where:
1. Upload succeeds and updates the deleted record
2. The deleted record remains `record_status: "deleted"` 
3. Compliance query filters it out
4. UI shows no evidence

## Fix Applied (server.py)

### 1. Training Upload Endpoint (line ~11643)
Added `record_status` filter to only find active records:
```python
# BEFORE
existing_record = await db.training_records.find_one({
    "employee_id": employee_id,
    "$or": [
        {"training_name": {"$regex": training_name, "$options": "i"}},
        {"requirement_id": requirement_id}
    ]
})

# AFTER
existing_record = await db.training_records.find_one({
    "employee_id": employee_id,
    "record_status": {"$nin": ["superseded", "deleted"]},  # BUGFIX
    "$or": [
        {"training_name": {"$regex": training_name, "$options": "i"}},
        {"requirement_id": requirement_id}
    ]
})
```

### 2. Ensure `record_status: "active"` on Update
Added explicit `record_status: "active"` to update operations to ensure records don't drift.

### 3. New Record Creation
Added explicit `record_status: "active"` to new record creation for consistency.

### 4. Document Upload Endpoint
Applied same fix to employee document uploads:
```python
existing = await db.employee_documents.find_one({
    "employee_id": employee_id,
    "requirement_id": requirement_id,
    "status": {"$nin": ["superseded", "archived", "deleted"]}  # BUGFIX
})
```

## Verification
1. Uploaded certificate to `infection_control` requirement with existing deleted record
2. Fix correctly created NEW active record instead of updating deleted one
3. Compliance API returns the new evidence
4. UI displays the file with "Ready for Review" status

## Date
2026-03-30
