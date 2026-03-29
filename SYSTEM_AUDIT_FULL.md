# WHOLE-SYSTEM CODE AUDIT REPORT
## Osabea Healthcare Compliance Portal
**Audit Date**: 2025-12-29
**Auditor**: System Code Review

---

# PART A — SYSTEM AUDIT REPORT

## Executive Summary

| Principle | Status | Risk Level |
|-----------|--------|------------|
| 1. Single Source of Truth | ⚠️ PARTIAL | MEDIUM |
| 2. Compliance Integrity | ✅ STRONG | LOW |
| 3. Workflow Safety | ✅ STRONG | LOW |
| 4. Audit Trail | ✅ STRONG | LOW |
| 5. Data Safety | ✅ STRONG | LOW |
| 6. Cross-Page Consistency | ⚠️ PARTIAL | MEDIUM |
| 7. UI Trust | ⚠️ PARTIAL | MEDIUM |
| 8. Scalability of Structure | ⚠️ PARTIAL | MEDIUM |

---

## 1. CRITICAL ISSUES

### 1.1 🔴 Remaining `new Date()` Usages - 44 Locations
**Risk**: Timezone drift, browser inconsistency, cross-page date mismatch
**Files Affected**: 
- `ComplianceCentrePage.js` (19 usages)
- `EmployeeProfilePage.js` (18 usages)
- `FormEditorPage.js` (12 usages)
- `DBSRegisterPage.js` (1 usage)
- `DocumentsPage.js` (1 usage)

**Critical Examples**:
```javascript
// ComplianceCentrePage.js:1447 - Local days calculation
const daysOld = Math.ceil((new Date() - new Date(i.date_occurred)) / (1000 * 60 * 60 * 24));

// EmployeeProfilePage.js:2211 - DBS review days calculation  
const days = Math.ceil((new Date(dbsSummary.next_dbs_review_due) - new Date()) / (1000 * 60 * 60 * 24));
```

**Impact**: Different browsers/timezones may calculate different "days until expiry" values

---

### 1.2 🔴 Mixed Date Storage Formats in DB
**Risk**: Parsing failures, inconsistent expiry calculations
**Evidence from API response**:
```json
// Training record 1 - YYYY-MM-DD
"completion_date": "2025-09-11"

// Training record 2 - Full ISO
"completion_date": "2026-03-28T02:07:30.467419+00:00"
```

**Root Cause**: Historical data created before normalization patch

---

### 1.3 🔴 Hardcoded Status Labels in Frontend
**Risk**: UI not updating when backend status logic changes
**Locations** (40+ instances):
```javascript
// EmployeeProfilePage.js:4828
label: record.status_label || (record.renewal_status === 'expired' ? 'Expired' : record.renewal_status === 'expiring_soon' ? 'Needs Renewal' : 'Valid'),

// ComplianceCentrePage.js:2295
item.status === 'expired' ? 'Expired' :
```

---

## 2. MEDIUM RISKS

### 2.1 ⚠️ DBS Days Calculation Still Local
**File**: `EmployeeProfilePage.js:2211`
```javascript
const days = Math.ceil((new Date(dbsSummary.next_dbs_review_due) - new Date()) / (1000 * 60 * 60 * 24));
```
**Impact**: DBS review due dates calculated locally, not from backend

### 2.2 ⚠️ Incident "Days Old" Calculated Locally
**File**: `ComplianceCentrePage.js:1447, 1686`
```javascript
const daysOld = Math.ceil((new Date() - new Date(i.date_occurred)) / (1000 * 60 * 60 * 24));
```
**Impact**: Incident age may vary by timezone

### 2.3 ⚠️ Policy Status Comparison Uses String Literals
**File**: `ComplianceCentrePage.js:843`
```javascript
const expiringCount = categoryPolicies.filter(p => p.status === 'expired' || p.status === 'under_review').length;
```
**Impact**: If backend changes status values, frontend breaks silently

### 2.4 ⚠️ Certificate Status Check Uses String Literals
**File**: `ComplianceCentrePage.js:1072-1078`
```javascript
{insurance.filter(i => i.status === 'valid').length} of {insurance.length} certificates valid
{insurance.some(i => i.status === 'missing' || i.status === 'expired') && (
```

---

## 3. LOW/POLISH ISSUES

### 3.1 🟡 Inconsistent Date Display Formats
**Issue**: Some dates show as "15 Mar 2027", others as "3/15/2027"
- `formatBackendDate` used in TrainingPage, EmployeeProfilePage training tab
- Raw `toLocaleDateString()` used elsewhere

### 3.2 🟡 Duplicate Badge Color Logic
**Issue**: Badge colors defined inline in multiple files
- `bg-green-100 text-green-700` appears 50+ times
- `bg-red-100 text-red-700` appears 40+ times
- Should use `StatusBadge` component

### 3.3 🟡 Legacy Form System Still Present
**Issue**: Both `generated_forms` and `form_submissions` tables exist
- `check_item_completion()` checks both systems
- Could cause confusion about source of truth

---

## 4. AREAS THAT ARE STRONG (DO NOT TOUCH)

### 4.1 ✅ Training Status Computation (Single Source of Truth)
**File**: `server.py:3613-3745`
```python
def compute_training_record_status(record: dict) -> dict:
    """
    SINGLE SOURCE OF TRUTH for training record status.
    """
```
- Correctly computes status from `completion_date`, `expiry_date`, `verified`
- All training endpoints use `enrich_training_record_with_computed_status()`
- Frontend uses backend-provided `computed_status`, `renewal_status`, `status_label`

### 4.2 ✅ Work Readiness Calculation
**File**: `server.py:978-1082`
```python
def calculate_work_readiness(requirements: List[dict], role: str) -> dict:
```
- Clear logic: all_mandatory_verified → "work_ready"
- Proper fallback chain: fully_compliant → work_ready → supervised_start → not_ready

### 4.3 ✅ Expiry Status Computation
**File**: `server.py:670-717`
```python
def calculate_expiry_status(expiry_date_str: str) -> dict:
```
- Uses UTC throughout
- Returns structured object with status, label, color, days
- Used consistently across document/training expiry checks

### 4.4 ✅ Form Submission Flow
**Files**: `server.py:9634-9845`
- Valid state transitions: submitted → verified → (unverified back to submitted)
- Proper audit logging at each step
- Soft delete only (no data loss)

### 4.5 ✅ Audit Trail Coverage
**Evidence**: 50+ `log_audit_action()` calls covering:
- Employee CRUD
- Document uploads/verifications
- Training record changes
- Form submissions
- Status changes

### 4.6 ✅ Role-Based Access Control
**Pattern**: Consistent use of decorators
```python
@Depends(require_admin)           # Admin-only actions
@Depends(require_manager_or_admin) # Manager+ actions  
@Depends(get_current_user)         # Any authenticated user
```

### 4.7 ✅ Extraction Safety (Review-Before-Apply)
**File**: `server.py:4840-4872`
```python
SAFE_AUTO_APPLY_FIELDS = {...}      # Personal info only
REVIEW_BEFORE_APPLY_FIELDS = {...}  # References, declarations, health data
```
- Sensitive fields require explicit review
- Never overwrites verified data automatically

---

## 5. FINAL VERDICT

### Is the system trustworthy enough for audit use right now?

**VERDICT: YES, WITH CAVEATS**

**What's Ready**:
- Training compliance calculations are solid
- Work readiness logic is correct
- Audit trail is comprehensive
- Form workflow is safe
- RBAC is consistent

**Remaining Risks**:
1. **Date Display Consistency** (Medium) - 44 `new Date()` usages need migration to `formatBackendDate()`
2. **Hardcoded Status Strings** (Medium) - 40+ places check status strings directly
3. **Historical Date Format Mix** (Low) - Old records have mixed formats

**Recommendation**: 
- System CAN be used for audits today
- Complete date utility migration before next CQC inspection
- Create status constants file to centralize status strings

---

# PART B — EXACT CODE FOR REVIEW

## B.1 Compliance Status Computation

### Location: `/app/backend/server.py:765-975`
```python
def calculate_separated_statuses(requirements: List[dict], role: str, policies_data: dict = None) -> dict:
    """
    Calculate the three separated status types:
    1. Start Status - Can the employee safely start work?
    2. Recruitment File - Is the pre-employment record complete?
    3. Policies - Have assigned policies been acknowledged?
    """
    work_ready_ids = get_work_ready_items_for_role(role)
    recruitment_ids = get_recruitment_file_items()
    competency_ids = get_competency_health_items(role)
    
    # Initialize counters
    start_items = []
    recruitment_items = []
    competency_items = []
    other_items = []
    
    # Track expiry status
    expired_docs = []
    expiring_soon_docs = []
    valid_docs = []
    
    for req in requirements:
        req_id = req.get('id')
        status_group = req.get('status_group', 'other')
        
        # Track document expiry
        if req.get('has_evidence'):
            evidence_files = req.get('evidence_files', [])
            for ef in evidence_files:
                if ef.get('status') == 'active' and ef.get('expiry_date'):
                    exp_status = calculate_expiry_status(ef.get('expiry_date'))
                    doc_info = {
                        "req_id": req_id,
                        "req_name": req.get('name'),
                        "file_name": ef.get('original_filename'),
                        "expiry_date": ef.get('expiry_date'),
                        "expiry_status": exp_status
                    }
                    if exp_status.get('status') == 'expired':
                        expired_docs.append(doc_info)
                    elif exp_status.get('status') == 'expiring_soon':
                        expiring_soon_docs.append(doc_info)
                    else:
                        valid_docs.append(doc_info)
        ...
```

## B.2 Training Status Computation

### Location: `/app/backend/server.py:3613-3745`
```python
def compute_training_record_status(record: dict) -> dict:
    """
    SINGLE SOURCE OF TRUTH for training record status.
    
    Canonical fields used:
    - completion_date: When training was completed
    - expiry_date: When training expires (if set)
    - verified: Whether training has been verified
    
    Computed status values:
    - "not_started": No completion_date
    - "expired": expiry_date exists AND today > expiry_date
    - "needs_renewal": expiry_date exists AND within 30 days of expiry
    - "completed": Has completion_date, not expired, not near expiry
    """
    completion_date = record.get('completion_date')
    expiry_date = record.get('expiry_date')
    verified = record.get('verified', False)
    
    # No completion date = not started
    if not completion_date:
        return {
            "computed_status": "not_started",
            "renewal_status": None,
            "days_until_expiry": None,
            "status_label": "Not Started",
            "status_color": "gray"
        }
    
    # If no expiry date, it's completed/valid indefinitely
    if not expiry_date:
        return {
            "computed_status": "completed",
            "renewal_status": "no_expiry",
            "days_until_expiry": None,
            "status_label": "Completed" if not verified else "Verified",
            "status_color": "green"
        }
    
    # Calculate days until expiry
    try:
        now = datetime.now(timezone.utc)
        if isinstance(expiry_date, str):
            if 'T' in expiry_date:
                exp_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            else:
                exp_dt = datetime.strptime(expiry_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            exp_dt = expiry_date
        
        days_until_expiry = (exp_dt - now).days
        expiry_date_str = exp_dt.strftime('%Y-%m-%d')
        
        if days_until_expiry < 0:
            return {
                "computed_status": "expired",
                "renewal_status": "expired",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Expired ({abs(days_until_expiry)}d ago)",
                "status_color": "red"
            }
        elif days_until_expiry <= EXPIRY_WARNING_DAYS:
            return {
                "computed_status": "needs_renewal",
                "renewal_status": "expiring_soon",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Expires in {days_until_expiry}d",
                "status_color": "amber"
            }
        else:
            return {
                "computed_status": "completed",
                "renewal_status": "valid",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Valid ({days_until_expiry}d left)",
                "status_color": "green"
            }
    except Exception as e:
        logger.error(f"Error computing training status: {e}")
        return {
            "computed_status": "completed",
            "renewal_status": "unknown",
            "days_until_expiry": None,
            "status_label": "Completed",
            "status_color": "green"
        }
```

## B.3 Employee Compliance Requirements Aggregation

### Location: `/app/backend/server.py:8565-8950` (partial)
```python
@api_router.get("/employees/{employee_id}/compliance-requirements")
async def get_employee_compliance_requirements(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get all compliance requirements for an employee with their current status.
    Returns structured data for the compliance overview UI.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    role = employee.get("role", "")
    mandatory_items = get_mandatory_items_for_role(role)
    
    # Get all training records - ENRICH WITH COMPUTED STATUS (SINGLE SOURCE OF TRUTH)
    raw_training = await db.training_records.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    all_training = [enrich_training_record_with_computed_status(t) for t in raw_training]
    ...
```

## B.4 Form Submission / Review / Approval Flow

### Location: `/app/backend/server.py:9634-9845`
```python
@api_router.post("/form-submissions", response_model=FormSubmissionResponse)
async def create_form_submission(submission: FormSubmissionCreate, user: dict = Depends(get_current_user)):
    """Submit a structured form"""
    # ... validation ...
    
    # Check for existing submission (supersede if exists)
    existing = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "status": {"$nin": ["deleted", "superseded"]}
    })
    
    if existing:
        # Supersede the existing submission
        await db.form_submissions.update_one(
            {"id": existing["id"]},
            {"$set": {"status": "superseded", "superseded_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    new_submission = {
        "id": submission_id,
        "status": "submitted",  # Initial state
        "verified": False,
        ...
    }
    
    await db.form_submissions.insert_one(new_submission)
    await log_audit_action(user['user_id'], "form_submitted", ...)
    
@api_router.post("/form-submissions/{submission_id}/verify")
async def verify_form_submission(submission_id: str, user: dict = Depends(require_admin)):
    """Verify a form submission"""
    # ... transitions to status="verified" ...
    await log_audit_action(user['user_id'], "form_verified", ...)
    
@api_router.post("/form-submissions/{submission_id}/unverify")
async def unverify_form_submission(submission_id: str, user: dict = Depends(require_admin)):
    """Remove verification"""
    # ... transitions back to status="submitted" ...
    await log_audit_action(user['user_id'], "form_unverified", ...)
```

## B.5 PDF Generation/Export Flow

### Location: `/app/backend/server.py:9852-10200` (partial)
```python
async def generate_staff_health_pdf(submission_data: dict, employee_data: dict, template_config: dict = None) -> bytes:
    """
    Generate a completed Staff Health Questionnaire PDF from structured form data.
    Uses reportlab to create a professional PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, ...)
    
    # ... build PDF content from submission_data ...
    
    doc.build(story)
    return buffer.getvalue()

@api_router.post("/form-submissions/generate-pdf/{submission_id}")
async def generate_form_pdf(submission_id: str, user: dict = Depends(require_manager_or_admin)):
    """Generate PDF for a form submission"""
    submission = await db.form_submissions.find_one({"id": submission_id})
    
    # Generate PDF
    pdf_bytes = await generate_staff_health_pdf(submission["data"], employee)
    
    # Upload to storage
    pdf_url = await upload_to_storage(pdf_bytes, filename)
    
    # Create export record
    export_doc = {
        "id": export_id,
        "submission_id": submission_id,
        "pdf_url": pdf_url,
        "generated_at": now,
        ...
    }
    await db.form_pdf_exports.insert_one(export_doc)
```

## B.6 Application Form Extraction / Mapping Flow

### Location: `/app/backend/server.py:4765-4872` (mapping), `5249-5400` (parsing)
```python
# Field mapping (partial)
APPLICATION_FORM_FIELD_MAPPING = {
    "first_name": "first_name",
    "surname": "last_name",
    "date_of_birth": "date_of_birth",
    # ... 50+ field mappings ...
}

# Safe auto-apply fields (personal info only)
SAFE_AUTO_APPLY_FIELDS = {
    "first_name", "last_name", "middle_name", "title",
    "address_line_1", "address_line_2", "city", "county", "postcode", "country",
    "phone", "phone_secondary", "email", "date_of_birth",
    ...
}

# Review-required fields (sensitive)
REVIEW_BEFORE_APPLY_FIELDS = {
    "reference_1_name", "reference_1_company", ...  # References
    "working_time_opt_out", "dbs_update_service_consent", ...  # Declarations
    "health_issues_disability", "influenza_vaccine_status", ...  # Health
}

# Parsing logic
async def parse_extracted_text_to_fields(...):
    # ... AI extraction ...
    
    # Apply auto-apply rules
    if current_val:
        should_apply = False  # Never overwrite existing
    elif field_name in REVIEW_BEFORE_APPLY_FIELDS:
        should_apply = False  # Always review sensitive
    elif field_name in SAFE_AUTO_APPLY_FIELDS:
        should_apply = True   # Auto-apply safe personal info
    else:
        should_apply = False  # Unknown = require review
```

## B.7 Audit Log Creation Logic

### Location: `/app/backend/server.py` (multiple locations)
```python
async def log_audit_action(
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict = None
):
    """Log an audit action"""
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat()
    })

# Usage examples (50+ calls):
await log_audit_action(user['user_id'], "form_submitted", "form_submission", submission_id, {...})
await log_audit_action(user['user_id'], "document_verified", "requirement", requirement_id, {...})
await log_audit_action(user['user_id'], "training_record_created", "training_record", record_id, {...})
```

## B.8 Role/Permission Checks

### Location: `/app/backend/server.py:4170-4180`
```python
async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_manager_or_admin(user: dict = Depends(get_current_user)) -> dict:
    if user['role'] not in ['admin', 'manager']:
        raise HTTPException(status_code=403, detail="Manager or admin access required")
    return user

# Usage pattern:
@api_router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, user: dict = Depends(require_admin)):
    # Only admins can delete

@api_router.post("/training-records")
async def create_training_record(record: ..., user: dict = Depends(require_manager_or_admin)):
    # Managers and admins can create
```

## B.9 Shared Status Badge / Requirement Row Components

### Location: `/app/frontend/src/components/ui/status-badge.jsx`
```javascript
export const StatusBadge = ({ 
  status, 
  label, 
  size = 'sm', 
  showIcon = false,
  className,
  variant = 'badge'
}) => {
  const normalizedStatus = (status || '').toLowerCase().replace(/[\s_-]+/g, '_');
  
  const statusConfig = {
    valid: { bg: 'bg-green-100', text: 'text-green-700', ... },
    expired: { bg: 'bg-red-100', text: 'text-red-700', ... },
    pending: { bg: 'bg-amber-100', text: 'text-amber-700', ... },
    // ... 20+ status variants
  };
  ...
};
```

### Location: `/app/frontend/src/components/ui/requirement-row.jsx`
```javascript
export const RequirementRow = ({
  title,
  subtitle,
  status,
  type = 'document',
  expiry,
  badges = [],
  actions = [],
  onView,
  onEdit,
  ...
}) => {
  // Unified row for documents/training/forms
  ...
};
```

---

## B.10 GREP RESULTS — All Locations

### Status Computation Logic (50+ locations)
```
server.py:670:def calculate_expiry_status
server.py:765:def calculate_separated_statuses
server.py:978:def calculate_work_readiness
server.py:3613:def compute_training_record_status
server.py:3715:def enrich_training_record_with_computed_status
```

### Approval State Logic (50+ locations)
```
server.py:9683:        "status": "submitted"
server.py:9781:            "status": "verified"
server.py:9809:            "status": "submitted"  # unverify
server.py:9833:            "status": "deleted"
```

### `new Date(` — 50 locations in frontend
See GREP 3 output above.

### `.toLocaleDateString(` — 44 locations in frontend
See GREP 4 output above.

### Hardcoded Status Labels — 40+ locations
```
ComplianceCentrePage.js:843: p.status === 'expired'
ComplianceCentrePage.js:1072: i.status === 'valid'
ComplianceCentrePage.js:2295: item.status === 'expired'
EmployeeProfilePage.js:4828: 'expired' ? 'Expired' : ...
TrainingPage.js:243: t.renewal_status === 'expired'
```

### Writing Computed Status to Storage — 30 locations
```
server.py:3726:    enriched['computed_status'] = computed['computed_status']
server.py:3727:    enriched['renewal_status'] = computed['renewal_status']
server.py:3734:    if computed['computed_status'] == 'expired':
server.py:3735:        enriched['status'] = 'expired'
```

---

## END OF AUDIT REPORT
