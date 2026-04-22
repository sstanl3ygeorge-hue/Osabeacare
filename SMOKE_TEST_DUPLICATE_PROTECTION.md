# Smoke Test: Training Approve-and-Verify Duplicate Protection

## Test Purpose
Manually verify in browser that fast approval (one-step approve + verify) does NOT create duplicate canonical training records.

---

## Prerequisites
- ✅ Backend approve-and-verify endpoint deployed (`POST /employees/{id}/training/proposed-items/approve-and-verify`)
- ✅ Frontend approve-and-verify handlers implemented
- ✅ Local or staging database seeded with test data

---

## Test Scenario: Same Item Approved Twice

### Step 1: Create Test Employee & Proposed Item
```
Employee: John Smith (ID: emp_test_001)
Role: Care Worker
Proposed training item:
  - ID: prop_test_abc
  - Status: "proposed"
  - Training: Safeguarding Adults
  - Mapped code: "safeguarding"
  - Completion date: 2026-02-15
  - Source: Certificate PDF uploaded
  - Status: "proposed"
```

**Expected State Before Test:**
- `proposed_training_items[prop_test_abc].status = "proposed"`
- `training_records` count with requirement_id="safeguarding" = 0

---

### Step 2: First Approve-and-Verify (Happy Path)

**UI Action:**
1. Navigate to: `/employees/emp_test_001/training`
2. Go to "Extracted Training Awaiting Review" section
3. Find item: "Safeguarding Adults"
4. Click green button: "Approve & Verify"
5. Wait for success toast

**Expected Result:**
```json
{
  "approved_and_verified_count": 1,
  "approved_and_verified": [{
    "item_id": "prop_test_abc",
    "record_id": "tr_xyz123",
    "verified_by": "Admin Name",
    "verified_at": "2026-04-22T14:30:00Z"
  }]
}
```

**Database State After Step 2:**
```
✅ proposed_training_items[prop_test_abc].status = "APPROVED"
✅ proposed_training_items[prop_test_abc].created_training_record_id = "tr_xyz123"
✅ training_records[tr_xyz123].verified = True
✅ training_records[tr_xyz123].verified_by = "Admin Name"
✅ training_records[tr_xyz123].verified_at = "2026-04-22T14:30:00Z"
✅ training_records[tr_xyz123].source_document_id != NULL
```

**UI State After Step 2:**
✅ Item disappears from "Extracted Training" section (status no longer "proposed")
✅ Item appears in "Approved/Current Training" section (now verified)
✅ Readiness/percentage increases if this was a blocking item

---

### Step 3: Verify No Duplicate (Retry Idempotency)

**Database Check:**
```javascript
// Run in MongoDB console
db.training_records.count({
  employee_id: "emp_test_001",
  requirement_id: "safeguarding",
  verified: true
})
// Expected: 1 (not 2)
```

**Confirm Record Stays Approved:**
```javascript
db.proposed_training_items.findOne({
  id: "prop_test_abc"
})
// Expected: status = "APPROVED", created_training_record_id = "tr_xyz123"
```

---

### Step 4: Simulate Network Retry (Call Approve-and-Verify Again)

**UI Action (If Re-test Button Exists):**
- Manually call approve-and-verify again with same item_id
- OR refresh page and click button again (if not hidden after approval)

**API Call (Postman/cURL):**
```bash
POST /api/employees/emp_test_001/training/proposed-items/approve-and-verify
Authorization: Bearer {token}
Content-Type: application/json

{
  "items": [{
    "item_id": "prop_test_abc",
    "mapped_training_code": "safeguarding",
    "completed_at": "2026-02-15",
    "force": false
  }]
}
```

**Expected Response (Idempotent):**
```json
{
  "approved_and_verified_count": 1,
  "approved_and_verified": [{
    "item_id": "prop_test_abc",
    "record_id": "tr_xyz123",       ← SAME as before
    "verified_by": "Admin Name",
    "verified_at": "2026-04-22T14:30:00Z",
    "idempotent_retry": true        ← Indicates retry
  }],
  "needs_review_count": 0
}
```

**Database After Step 4 (No Changes):**
```
✅ training_records count with safeguarding = STILL 1 (NOT 2)
✅ record_id = tr_xyz123 (SAME)
✅ No new training_record created
```

---

### Step 5: Conflict Detection (Different Dates)

**Scenario:** Create second proposed item for same training with different completion date

**Setup:**
```
New proposed item:
  - ID: prop_test_def
  - Status: "proposed"
  - Training: Safeguarding Adults
  - Mapped code: "safeguarding"
  - Completion date: 2026-03-20 (DIFFERENT from 2026-02-15)
  - Source: Another certificate
```

**UI Action or API Call:**
```bash
POST /api/employees/emp_test_001/training/proposed-items/approve-and-verify
{
  "items": [{
    "item_id": "prop_test_def",
    "mapped_training_code": "safeguarding",
    "completed_at": "2026-03-20",
    "force": false
  }]
}
```

**Expected Response (Conflict Detected):**
```json
{
  "approved_and_verified_count": 0,
  "needs_review_count": 1,
  "needs_review": [{
    "item_id": "prop_test_def",
    "skip_reason": "duplicate_conflict",
    "conflict_detail": "Existing verified record has 2026-02-15 but this item has 2026-03-20"
  }]
}
```

**Database After Step 5 (Protected):**
```
✅ training_records count with safeguarding = STILL only 1
✅ Existing record [tr_xyz123] with date 2026-02-15 UNCHANGED
✅ No new record created (conflict prevented)
✅ proposed_training_items[prop_test_def].status = "proposed" (not approved)
```

**UI State:**
✅ Item "prop_test_def" stays in "Needs Review" or shows error badge
✅ Must be manually reviewed/resolved

---

## Test Checklist

| # | Test | Command/Action | Expected Result | Pass? |
|---|------|-----------------|-----------------|-------|
| 1 | Single approve-verify | Click "Approve & Verify" | Item approved, verified=True, record_id generated | ☐ |
| 2 | Item disappears from extracted | View extracted section | Item no longer visible (status changed) | ☐ |
| 3 | Item appears as verified | View approved/current section | Item shown with ✓ verified | ☐ |
| 4 | No duplicate created | `db.training_records.count (requirement="safeguarding", verified=true)` | Result = 1 | ☐ |
| 5 | Retry returns same record | Call approve-and-verify again | Same record_id returned, `idempotent_retry=true` | ☐ |
| 6 | Conflict detected | Call approve-verify with different date | Skipped with `skip_reason="duplicate_conflict"` | ☐ |
| 7 | Existing record protected | Check DB after conflict | Existing record unchanged, no new record | ☐ |
| 8 | Readiness increases | Check employee % | Percentage increases if blocking training | ☐ |

---

## Failure Modes to Watch For

### ❌ Failure 1: Duplicate Record Created
**Symptom:** `db.training_records.count()` = 2 after step 2
**Root Cause:** Idempotency check not working or creating new record on retry
**Fix:** Verify proposed item status is set to "APPROVED" AND `created_training_record_id` is saved

### ❌ Failure 2: Item Stays in Extracted Section
**Symptom:** After approval, item still shows as "proposed"
**Root Cause:** UI not filtering by status, or refresh not happening
**Fix:** Verify fetchTrainingData() called after success, filter on `status="proposed"`

### ❌ Failure 3: Conflict NOT Detected
**Symptom:** Different date item still gets approved (creates 2nd record)
**Root Cause:** Conflict detection logic not checking existing verified record
**Fix:** Check duplicate protection layer 2 in endpoint

### ❌ Failure 4: Readiness NOT Updated
**Symptom:** Percentage stays same after approval
**Root Cause:** Training evaluator still filtering unverified, or percentage calc not including training
**Fix:** Verify `verified=True` records are counted by training_evaluator

---

## Success Criteria (All Must Pass)

- ✅ [1] Single approve-and-verify: PASS
- ✅ [2] Item disappears from extracted: PASS
- ✅ [3] Item appears as verified: PASS
- ✅ [4] No duplicate created (count=1): PASS
- ✅ [5] Idempotent retry (same record_id, idempotent_retry=true): PASS
- ✅ [6] Conflict detection (skip with reason): PASS
- ✅ [7] Existing record protected (unchanged): PASS
- ✅ [8] Readiness increases: PASS

---

## Sign-Off
- **Test Date:** April 22, 2026
- **Tester:** [Name]
- **Result:** ☐ PASS / ☐ FAIL
- **Issues Found:** (describe if any)
- **Sign-Off:** Approved by [Manager]
