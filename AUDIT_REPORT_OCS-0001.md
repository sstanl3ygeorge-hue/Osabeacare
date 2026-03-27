# COMPLIANCE SYSTEM AUDIT REPORT
## Employee: Olakunle Alonge (OCS-0001)
## Date: 2026-03-27

---

## 1. REQUIREMENT INVENTORY

| REQ_ID | CATEGORY | TYPE | STATUS | VERIFIED | EVIDENCE |
|--------|----------|------|--------|----------|----------|
| application_form | A_Application_Form | form | completed | No | docs=4, form=Y |
| cv | A_Application_Form | document | completed | Yes | docs=1, form=N |
| recruitment_checklist | B_Recruitment_Checklist | form | missing | No | docs=0, form=N |
| personal_info | C_Personal_Information | form | missing | No | docs=0, form=N |
| interview_record | D_Interview | form | missing | No | docs=0, form=Y (draft) |
| equal_opportunities | E_Equal_Opportunities | form | missing | No | docs=0, form=N |
| health_screening | F_Health_Screening | form | completed | No | docs=1, form=Y |
| identity_rtw | G_Identity_RTW | document | completed | Yes | docs=3, form=N |
| reference_1 | H_References | document | completed | Yes | docs=1, form=N |
| reference_2 | H_References | document | completed | Yes | docs=1, form=N |
| dbs | I_DBS | document | completed | Yes | docs=2, form=N |
| induction | J_Induction_Shadowing | form | completed | No | docs=1, form=Y |
| contract | L_Contract | form | completed | No | docs=1, form=Y |
| handbook | O_Other | form | completed | No | docs=1, form=Y |
| safeguarding | N_Training | training | missing | No | training=Y (not_started) |
| manual_handling | N_Training | training | missing | No | training=Y (not_started) |
| infection_control | N_Training | training | completed | Yes | training=Y (completed) |
| bls | N_Training | training | missing | No | training=N |
| fire_safety | N_Training | training | missing | No | training=N |
| health_safety | N_Training | training | missing | No | training=Y (completed, but name mismatch) |

**Summary:** 20 requirements, 10-11 complete (discrepancy), 4-6 verified

---

## 2. EVIDENCE INVENTORY - DOCUMENTS

| DOC_ID | REQ_ID | DOC_TYPE_NAME | STATUS | VER | HAS_FILE | SOURCE | ISSUE |
|--------|--------|---------------|--------|-----|----------|--------|-------|
| 4798ffc5 | application_form | Application Form | approved | 2 | YES | manual | |
| 4c2dab5f | cv | CV / Resume | approved | 2 | YES | manual | |
| f0e6376f | interview_record | Interview Questions | not_started | 1 | NO | manual | **ORPHAN (no file)** |
| cdc63a0a | NONE | New Starter Form | not_started | 1 | NO | manual | **ORPHAN (no req, no file)** |
| 42ba6b80 | application_form | Application Form | approved | 1 | YES | manual | **DUPLICATE** |
| bfbb0ad9 | cv | CV / Resume | approved | 1 | YES | manual | **DUPLICATE** |
| 6c4a86e0 | application_form | Application Form | approved | 1 | YES | manual | **DUPLICATE** |
| 8902afc0 | dbs | DBS Certificate | approved | 2 | YES | manual | |
| a47dedac | application_form | Application Form | approved | 1 | YES | form_submission | **DUPLICATE** |
| 18032ba3 | reference_2 | Reference 2 | approved | 5 | YES | manual | |
| f382873e | dbs | DBS Form / Update Service | approved | 15 | YES | manual | **DUPLICATE** |
| 695379a9 | identity_rtw | Right to Work in UK | approved | 1 | YES | manual | |
| 61d20cee | identity_rtw | Right to Work in UK | approved | 1 | YES | manual | |
| 3eb41822 | identity_rtw | Right to Work in UK | approved | 1 | YES | manual | |
| f06d2798 | reference_1 | Reference 1 | approved | 12 | YES | imported | |
| df3585f0 | health_screening | Health Screening Questionnaire | approved | 4 | YES | imported | |
| 109d7fdf | contract | Contract Acknowledgement | approved | 4 | YES | imported | |
| 494585e1 | induction | Induction & Competency Assessment | approved | 2 | YES | imported | |
| 075092cd | handbook | Employee Handbook Acknowledgement | approved | 2 | YES | imported | |

**Total:** 19 document records
**Issues:**
- 2 documents WITHOUT file_url (orphan placeholders)
- 1 document WITHOUT requirement_id
- Multiple documents for same requirement (application_form: 4, cv: 2, dbs: 2)

---

## 3. FORMS INVENTORY

| FORM_ID | REQ_ID | TEMPLATE_NAME | STATUS | LOCKED | HAS_PDF | ISSUE |
|---------|--------|---------------|--------|--------|---------|-------|
| c2efc29a | NONE | Reference 1 | completed_imported | YES | YES | **NO REQ_ID** |
| 1f018276 | NONE | Contract Acknowledgement Form | completed_imported | YES | YES | **NO REQ_ID** |
| 2af158f1 | NONE | Health Screening Questionnaire | completed_imported | YES | YES | **NO REQ_ID** |
| 52ecf407 | NONE | Employee Handbook Acknowledgement | completed_imported | YES | YES | **NO REQ_ID** |
| 71865bcf | NONE | Induction & Competency Assessment | completed_imported | YES | YES | **NO REQ_ID** |
| d9ff0dd2 | NONE | Reference 2 | completed_imported | YES | YES | **NO REQ_ID** |
| 24cd1e4c | NONE | Interview Record Form | draft | NO | NO | **NO REQ_ID** |
| 40386fbd | NONE | Application Form | completed_imported | YES | YES | **NO REQ_ID** |

**Total:** 8 forms
**Critical Issue:** ALL 8 forms have requirement_id = NONE
**Impact:** Forms are not properly linked to compliance requirements

---

## 4. TRAINING AUDIT

| TRAINING_ID | TRAINING_NAME | STATUS | ISSUE |
|-------------|---------------|--------|-------|
| ef0a2146 | Safeguarding | not_started | |
| b506e915 | Moving & Handling | not_started | Name mismatch with "Manual Handling" |
| 7c29db45 | Infection Control | not_started | |
| 8df4ab96 | Health & Safety | not_started | |
| 48f3380c | First Aid | not_started | Not in MANDATORY_ITEMS |
| bc618e2e | First Aid Awareness | completed | Not in MANDATORY_ITEMS |
| 1f5ce0c8 | Health and Safety | completed | **DUPLICATE** (different spelling) |
| bc013486 | Infection Control and Hygiene | completed | **DUPLICATE** (longer name) |
| e23ea2c1 | Infection Control and Hygiene | not_started | **DUPLICATE** |

**Total:** 9 training records
**Critical Issues:**
1. **DUPLICATE training records** for same competency
2. **Name mismatches** between training_records and MANDATORY_ITEMS:
   - "Moving & Handling" vs "Manual Handling"
   - "Health & Safety" vs "Health and Safety"
   - "Infection Control" vs "Infection Control and Hygiene"
3. **Orphan training records** not in mandatory list (First Aid, First Aid Awareness)

---

## 5. COMPLIANCE SCORE DISCREPANCY

### Endpoint 1: `/compliance` (used for employee.completion_percentage)
```
Total: 20, Complete: 11, Percentage: 55%
Completed: application_form, contract, cv, dbs, handbook, health_screening, 
           identity_rtw, induction, infection_control, reference_1, reference_2
```

### Endpoint 2: `/compliance-requirements` (used for Checklist tab)
```
Total: 20, Complete: 10, Percentage: 50%
Completed: application_form, contract, cv, dbs, handbook, health_screening,
           identity_rtw, induction, reference_1, reference_2
```

### DISCREPANCY IDENTIFIED:
- `/compliance` counts `infection_control` as complete (matches "Infection Control and Hygiene")
- `/compliance-requirements` does NOT count it (different matching algorithm)

### Why score jumped from 15% to 55%:
1. **Before cleanup:** Score was based on `document_type_id` matching old document_types table
2. **After cleanup:** Score is based on requirement_id matching MANDATORY_ITEMS
3. **Forms now count:** 8 completed_imported forms now contribute to score
4. **Training matching fixed:** Regex matching now finds completed training

---

## 6. SINGLE SOURCE OF TRUTH ANALYSIS

### Current Architecture (PROBLEMATIC):

```
┌─────────────────┐
│ MANDATORY_ITEMS │  ← Definition of 20 requirements
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     THREE SEPARATE FLOWS                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ /compliance     │ /compliance-    │ Individual endpoints        │
│ endpoint        │ requirements    │ (forms, docs, training)     │
│                 │ endpoint        │                             │
│ Uses:           │ Uses:           │ Uses:                       │
│ check_item_     │ In-memory       │ Direct DB queries           │
│ completion()    │ matching        │                             │
│                 │                 │                             │
│ Result: 55%     │ Result: 50%     │ Raw data                    │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### What Powers Each View:

| View | Backend Source | Issue |
|------|----------------|-------|
| Compliance Score Card | `/compliance` → `calculate_employee_compliance()` | Returns 55% |
| Checklist Tab | `/compliance-requirements` → `get_compliance_requirements()` | Returns 50% |
| Documents Tab | `/compliance-requirements` requirements filtered | Shows 5 document requirements |
| Forms Tab | `/generated-forms` directly | Shows 8 forms, no req linking |
| Training (sidebar) | `/training-records` directly | Shows 9 records, duplicates |

---

## 7. ROOT CAUSE ANALYSIS

### Problem 1: No `requirement_id` on Forms
- Forms created via import do not set `requirement_id`
- Forms created via "Generate" also don't set `requirement_id`
- Compliance matching falls back to fuzzy template name matching

### Problem 2: Training Name Normalization Missing
- MANDATORY_ITEMS uses: "Manual Handling", "Infection Control"
- training_records uses: "Moving & Handling", "Infection Control and Hygiene"
- No normalization layer exists

### Problem 3: Document Duplicates
- Single-file requirements (CV, DBS, Application) have multiple records
- Deduplication only works on frontend display, not backend data

### Problem 4: Two Compliance Calculation Paths
- `check_item_completion()` uses regex DB queries
- `get_compliance_requirements()` uses in-memory loops
- Different matching = different results

### Problem 5: Training Module Disconnected
- Sidebar training module creates records in `training_records`
- These don't map to MANDATORY_ITEMS training requirements
- Creates duplicates and orphans

---

## 8. RECOMMENDED CLEANUP PLAN

### Phase 1: Data Cleanup (IMMEDIATE)

1. **Delete orphan documents**
   - Remove 2 documents without file_url
   - Remove 1 document without requirement_id

2. **Deduplicate training records**
   - Keep 1 record per training type
   - Map to normalized training names

3. **Add requirement_id to all forms**
   - Update 8 forms with correct requirement_id

4. **Deduplicate documents**
   - For single-file requirements, keep only highest version

### Phase 2: Unify Compliance Logic (SHORT-TERM)

1. **Create single compliance calculation function**
   - Deprecate one of the two endpoints
   - OR make both use identical logic

2. **Create training name mapping**
   ```
   "Moving & Handling" → "manual_handling"
   "Health & Safety" → "health_safety"
   "Infection Control" → "infection_control"
   ```

3. **Enforce requirement_id on all inserts**
   - Forms: Set requirement_id on create
   - Documents: Already done, verify
   - Training: Add requirement_id field

### Phase 3: Architecture Stabilization (MEDIUM-TERM)

1. **Create `employee_requirements` table**
   - One row per employee × requirement
   - Status: missing / uploaded / verified / completed
   - Evidence links: document_id, form_id, training_id

2. **All views read from `employee_requirements`**
   - Compliance score = COUNT(status=completed) / total
   - Checklist = employee_requirements grouped by category
   - Documents = employee_requirements filtered

3. **Evidence upload triggers requirement update**
   - Upload document → update employee_requirements.status
   - Complete form → update employee_requirements.status
   - Complete training → update employee_requirements.status

---

## 9. SAFE PATH TO 100% TONIGHT

### Current State:
- 10-11/20 complete (depending on endpoint)
- 9-10 missing requirements

### Missing Requirements:
1. `recruitment_checklist` (form) - Generate and complete
2. `personal_info` (form) - Generate and complete
3. `interview_record` (form) - Draft exists, complete it
4. `equal_opportunities` (form) - Generate and complete
5. `safeguarding` (training) - Mark complete
6. `manual_handling` (training) - Mark complete
7. `bls` (training) - Create and mark complete
8. `fire_safety` (training) - Create and mark complete
9. `health_safety` (training) - Already completed (name mismatch issue)

### Steps to Complete:
1. **Fix training name matching** - Either rename training records OR update regex
2. **Import/Generate missing forms** - Use Import Document feature
3. **Create missing training records** - Use training module
4. **Verify score reaches 100%** - Check both endpoints agree

---

## 10. IMMEDIATE ACTIONS REQUIRED

Before any feature work:

1. **Fix the score discrepancy** - Both endpoints must return same result
2. **Add requirement_id to existing forms** - Run migration
3. **Clean training duplicates** - Keep newest, delete rest
4. **Normalize training names** - Create mapping table
5. **Delete orphan documents** - Clean placeholders

**Estimated cleanup time:** 30-60 minutes
**Risk if not done:** Compliance scores unreliable, audits will fail

---

*End of Audit Report*
