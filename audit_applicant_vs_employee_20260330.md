# APPLICANT VS EMPLOYEE MODEL AUDIT
## Date: 2026-03-30
## Purpose: Determine if current model supports future scale

---

# CURRENT MODEL SUMMARY

## Single Collection Architecture
All recruitment cases and activated staff live in **ONE collection**: `db.employees`

### Collection Structure:
```
employees (95 operations in codebase)
├── id: UUID
├── employee_code: "OSB-001"
├── first_name, last_name, email
├── status: [new, screening, interview, compliance_review, onboarding, active, inactive, archived]
├── onboarding_status: [New, Documents Pending, Under Review, Ready for Placement, Active, Archived]
├── role: [Healthcare Assistant, Nurse, Support Worker, etc.]
├── start_date: (employment start)
├── created_at: (record creation)
├── reference_1_*, reference_2_*: (recruitment data)
├── employment_history: (CV gap analysis)
├── bank_*, ni_number: (activated staff data)
└── [all compliance/training via FK to employee_id]
```

### Current Status Flow:
```
NEW → SCREENING → INTERVIEW → COMPLIANCE_REVIEW → ONBOARDING → ACTIVE → (INACTIVE) → ARCHIVED
 |       |            |              |                |           |
 ├───────┴────────────┴──────────────┘                │           │
 │         "APPLICANT STAGE"                          │           │
 │         (pre-approval)                             │           │
 └────────────────────────────────────────────────────┴───────────┘
                    "EMPLOYEE STAGE"
                    (post-approval)
```

### Status-Based Separation (Already Exists):
| Status | Stage | Dashboard Count Field |
|--------|-------|----------------------|
| new | Applicant | `total_applicants` |
| screening | Applicant | `total_applicants` |
| interview | Applicant | `total_applicants` |
| compliance_review | Applicant | `total_applicants` |
| onboarding | Employee | `total_employees` |
| active | Employee | `total_employees` |

---

# WHERE UNAPPROVED RECRUITS ARE TREATED AS EMPLOYEES

## 1. Collection Name
**Issue**: All records in `employees` collection, regardless of stage
**Code**: 95+ operations on `db.employees`
**Risk**: Conceptual confusion - "employees" who haven't been approved

## 2. Employee Code Generation
**Issue**: Every new record gets `OSB-XXX` employee code immediately
**Code**: `server.py:4897` - `employee_code = await generate_employee_code()`
**Risk**: Codes assigned before approval - could leak sequence numbers

## 3. Profile Page
**Issue**: Same `EmployeeProfilePage.js` for applicants and employees
**Code**: `/portal/employees/{id}` route serves both
**Risk**: UI doesn't distinguish - managers may assume pre-hire = hired

## 4. Compliance Calculation
**Issue**: Same `calculate_employee_compliance()` for all statuses
**Code**: `server.py:1684` - runs for NEW through ACTIVE
**Risk**: Compliance % shown for people not yet approved

## 5. Document Storage
**Issue**: Documents stored with `employee_id` regardless of stage
**Collections**: `employee_documents`, `compliance_status`, `generated_forms`
**Risk**: If applicant rejected, their documents remain employee-linked

## 6. Training Assignment
**Issue**: Training can be assigned to any "employee" record
**Code**: `employee_training_assignments` collection
**Risk**: Training assigned before hire decision

---

# PAGES/COUNTS INCLUDING PRE-APPROVAL PEOPLE

## Dashboard (`/api/dashboard/stats`)
| Count | Includes Pre-Approval | Code |
|-------|----------------------|------|
| `total_employees` | No (ACTIVE + ONBOARDING only) | `server.py:13141` |
| `total_applicants` | Yes (NEW + SCREENING + INTERVIEW + COMPLIANCE_REVIEW) | `server.py:13142` |
| `onboarding_in_progress` | Partial (ONBOARDING only) | `server.py:13143` |
| `fully_verified_employees` | No (ACTIVE + ONBOARDING only) | `server.py:13147` |

**✅ GOOD**: Dashboard correctly separates applicants vs employees

## Employees List (`/api/employees`)
| Filter | Includes Pre-Approval | Notes |
|--------|----------------------|-------|
| No filter | Yes | Returns all non-archived |
| `status=active` | No | Only active |
| `status=new` | Yes | Only applicants at NEW stage |
| Default view | Yes | Shows all stages mixed |

**⚠️ CONCERN**: Default list mixes applicants and employees

## Compliance Reports
| Report | Includes Pre-Approval | Code |
|--------|----------------------|------|
| Training Matrix | Yes (status filter available) | `server.py:16913` |
| Audit Readiness | No (ACTIVE + ONBOARDING) | `server.py:13141` |
| Expiry Dashboard | Yes (all non-archived) | `server.py:13997` |
| CQC Evidence Map | Yes (all) | `server.py:14128` |

**⚠️ CONCERN**: Some compliance views include unapproved people

---

# DATA ALREADY BEHAVING LIKE APPLICANT-STAGE DATA

## Fields That Are Recruitment-Specific:
```python
# These fields are only relevant before activation:
reference_1_name, reference_1_company, reference_1_verified  # Pre-hire check
reference_2_name, reference_2_company, reference_2_verified  # Pre-hire check
reference_1_from_cv, reference_1_override_reason             # CV integrity
reference_2_from_cv, reference_2_override_reason             # CV integrity
employment_history                                            # CV gap analysis
cv_gaps_detected, cv_gaps_all_explained                      # Gap explanations
criminal_offence_declared                                     # Application declaration
professional_misconduct_declared                              # Application declaration
health_issue_declared                                         # Application declaration
```

## Forms That Are Recruitment-Specific:
```python
MANDATORY_ITEMS["4_Recruitment_Record"] = [
    "interview_record",      # Pre-hire interview
    "reference_1",           # Pre-hire reference
    "reference_2",           # Pre-hire reference  
    "recruitment_checklist", # Pre-hire checklist
    "application_form",      # Application
    "cv"                     # Pre-hire CV
]
```

## Compliance Items by Stage Relevance:
| Item | Stage | Notes |
|------|-------|-------|
| application_form | Applicant | Pre-hire only |
| cv | Applicant | Pre-hire only |
| interview_record | Applicant | Pre-hire only |
| recruitment_checklist | Applicant | Pre-hire only |
| reference_1, reference_2 | Applicant | Pre-hire check |
| right_to_work_* | Both | Required before + during |
| dbs_certificate | Both | Required before + renewed during |
| identity_documents | Both | Verified pre-hire, kept during |
| training_* | Employee | Post-hire primarily |
| staff_personal_info | Employee | Post-activation |
| bank details | Employee | Post-activation only |

---

# RISKS OF KEEPING ONE SHARED MODEL

## Risk 1: Data Pollution
**Severity**: Medium
- Rejected applicants remain in `employees` collection with `archived` status
- Their data (references, CV, documents) stays mixed with real employees
- Over time, collection grows with non-employee data

## Risk 2: Reporting Confusion
**Severity**: High
- Compliance reports may inadvertently include pre-approved people
- Manager could assign shifts to someone not yet cleared
- CQC inspection could surface unapproved person as "Ready for Placement"

## Risk 3: Privacy/GDPR
**Severity**: Medium
- Applicant data subject to different retention rules than employee data
- Rejected applicants should be purged after X months
- Current model makes selective purge difficult

## Risk 4: Employee Code Exhaustion
**Severity**: Low
- Every applicant gets an employee code
- If 10 applicants rejected for every 1 hired, 90% of codes wasted
- Not critical with UUID-style codes, but confusing for sequential

## Risk 5: Audit Trail Ambiguity
**Severity**: Medium
- Audit logs show "create_employee" for applicant creation
- No clear distinction between "applied" vs "hired" events
- Harder to prove recruitment compliance to CQC

## Risk 6: Future Feature Conflicts
**Severity**: High
- Shifts scheduling should only see ACTIVE employees
- Payroll integration should only see activated staff
- Self-service portal needs different permissions for applicants vs employees

---

# WHAT CAN STAY SHARED

## ✅ Keep Shared - Same Data Structure:
1. **Basic identity fields**: first_name, last_name, email, phone
2. **Address fields**: address_line_1, city, postcode (needed both stages)
3. **Emergency contact**: next_of_kin_* (safety requirement all stages)
4. **Core verification fields**: verified, verified_by, verified_at pattern
5. **Document storage model**: file_url, evidence_files structure
6. **Status tracking pattern**: status + onboarding_status fields

## ✅ Keep Shared - Business Logic:
1. **Compliance calculation**: Same algorithm, different requirement sets
2. **Document upload flow**: Same process regardless of stage
3. **Verification flow**: Same approve/reject regardless of stage
4. **Audit logging**: Same pattern for all actions

---

# WHAT SHOULD BE SEPARATED LATER

## Phase 1: Logical Separation (No Schema Change)
Add explicit fields to distinguish:
```python
# New fields on employee record:
recruitment_stage: str = "applicant"  # "applicant" | "cleared" | "employed"
recruitment_approved_at: Optional[str] = None
recruitment_approved_by: Optional[str] = None
activation_date: Optional[str] = None  # When they became ACTIVE
```

## Phase 2: Query Separation
Create wrapper functions:
```python
async def get_applicants(filters):
    return db.employees.find({"status": {"$in": APPLICANT_STATUSES}})

async def get_active_employees(filters):
    return db.employees.find({"status": {"$in": EMPLOYEE_STATUSES}})
```

## Phase 3: UI Separation
- Separate "Recruitment Pipeline" view from "Staff Directory"
- Different profile pages for applicants vs employees
- Hide bank/payroll fields until activated

## Phase 4: Collection Separation (Future - Major Migration)
IF scale requires:
```
applicants (new collection)
├── application_id
├── applicant_data
├── recruitment_status: [applied, screening, interviewing, offered, rejected, converted]
├── converted_to_employee_id  # Links to employees on conversion
└── retention_expires_at  # GDPR auto-purge date

employees (existing - trimmed)
├── id
├── employee_code  # Assigned only on activation
├── hired_from_applicant_id  # Links back to application
└── [employment-only fields]
```

---

# SMALLEST SAFE TRANSITION PLAN

## Step 1: Add Recruitment Approval Gate (1 day)
**No schema change required**
```python
# Add to employee record when approved:
await db.employees.update_one(
    {"id": employee_id},
    {"$set": {
        "recruitment_approved": True,
        "recruitment_approved_by": admin_id,
        "recruitment_approved_at": now
    }}
)

# Gate ACTIVE status:
if new_status == "active" and not employee.get("recruitment_approved"):
    raise HTTPException(400, "Cannot activate without recruitment approval")
```

## Step 2: Add Query Helpers (1 day)
```python
APPLICANT_STATUSES = ["new", "screening", "interview", "compliance_review"]
EMPLOYEE_STATUSES = ["onboarding", "active", "inactive"]

async def get_applicants_only(**filters):
    filters["status"] = {"$in": APPLICANT_STATUSES}
    return await db.employees.find(filters, {"_id": 0}).to_list(1000)

async def get_employees_only(**filters):
    filters["status"] = {"$in": EMPLOYEE_STATUSES}
    return await db.employees.find(filters, {"_id": 0}).to_list(1000)
```

## Step 3: Create Separate API Endpoints (1 day)
```python
@api_router.get("/recruitment/applicants")
async def list_applicants(...):
    return await get_applicants_only(...)

@api_router.get("/recruitment/pipeline")
async def get_recruitment_pipeline(...):
    # Returns applicants grouped by stage

@api_router.get("/staff/employees")  
async def list_staff(...):
    return await get_employees_only(...)
```

## Step 4: Update Frontend Views (2 days)
- Add "Recruitment" section in sidebar (NEW)
- Move NEW/SCREENING/INTERVIEW/COMPLIANCE_REVIEW to Recruitment Pipeline
- Keep "Employees" showing only ONBOARDING/ACTIVE/INACTIVE

## Step 5: Defer Employee Code Assignment (1 day)
```python
# On create: No employee code
employee_doc = {
    "id": employee_id,
    "employee_code": None,  # Assigned later
    ...
}

# On activation:
if not employee.get("employee_code"):
    employee_code = await generate_employee_code()
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"employee_code": employee_code}}
    )
```

---

# SUMMARY

| Aspect | Current State | Risk Level | Action |
|--------|---------------|------------|--------|
| Collection structure | Single `employees` | Medium | Keep for now |
| Status separation | Exists (status field) | Low | Already good |
| Dashboard counts | Separated | Low | Already good |
| List views | Mixed | Medium | Separate endpoints |
| Profile pages | Shared | Medium | UI hints needed |
| Employee codes | Pre-assigned | Low | Defer to activation |
| Recruitment approval | Missing | High | Add gate |
| Query patterns | Mixed | Medium | Add helpers |

## Recommended Immediate Actions:
1. ✅ Add `recruitment_approved` field and gate
2. ✅ Create query helpers for applicants vs employees
3. ✅ Add separate API endpoints
4. ⏳ Update frontend to use new endpoints

## DO NOT Do Yet:
- ❌ Create separate `applicants` collection
- ❌ Migrate existing data
- ❌ Change document FK patterns
- ❌ Build applicant self-service portal

The current single-collection model is **adequate for current scale** with the addition of proper gating and query separation. Collection split should only happen when:
- Applicant volume > 10x employee volume
- GDPR retention requirements force separation
- Performance degrades on mixed queries

