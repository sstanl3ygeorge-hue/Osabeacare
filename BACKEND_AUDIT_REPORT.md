# Backend Audit Report for Supabase Migration

**Generated:** April 2, 2026  
**Purpose:** Complete inventory of current system before Supabase migration

---

## 1. DATA STORAGE AUDIT

### 1.1 Current Database
| Attribute | Value |
|-----------|-------|
| **Database Type** | MongoDB (NoSQL) |
| **Client Library** | Motor (async MongoDB driver for Python) |
| **Connection** | `mongodb://localhost:27017` |
| **Database Name** | `test_database` |
| **Total Collections** | 44 |

### 1.2 All Collections Inventory

| Collection | Document Count | Purpose |
|------------|---------------|---------|
| `employees` | 12 | **Primary entity** - applicants & employees combined |
| `employee_documents` | 76 | Evidence files uploaded for employees |
| `rtw_checks` | 11 | Right to Work verification check records |
| `dbs_checks` | 5 | DBS verification check records |
| `identity_verifications` | 4 | Identity document verification records |
| `address_verifications` | 3 | Proof of Address verification records |
| `training_records` | 43 | Training certificates and records |
| `training_catalogue` | 7 | Master list of available trainings |
| `form_submissions` | 53 | Completed forms (health, interview, induction) |
| `agreement_acknowledgements` | 8 | Contract/handbook completions |
| `agreement_requests` | 2 | Pending agreement requests |
| `agreement_submissions` | 1 | Agreement submission records |
| `users` | 5 | Admin/staff login accounts |
| `user_sessions` | 1 | Active sessions |
| `org_policies` | 32 | Organization policy documents |
| `org_settings` | 1 | Organization configuration |
| `policy_assignments` | 4 | Policy assignments to employees |
| `recurring_compliance` | 3 | Recurring items (supervision, appraisals) |
| `scheduled_bulk_requests` | 5 | Scheduled document requests |
| `schedule_run_history` | 15 | Execution history of schedules |
| `email_logs` | 51 | Sent email records |
| `email_requests` | 46 | Email request records |
| `notification_logs` | 12 | Notification history |
| `audit_logs` | 1218 | Activity audit trail |
| `audit_log` | 18 | Additional audit entries |
| `document_types` | 41 | Document type definitions |
| `templates` | 13 | Form/document templates |
| `insurance_docs` | 13 | Organization insurance documents |
| `extraction_logs` | 46 | AI extraction history |
| `profile_extractions` | 42 | CV/profile extraction results |
| `document_extractions` | 3 | Document extraction results |
| `evidence_edit_logs` | 23 | Evidence modification history |
| `request_events` | 189 | Document request events |
| `requirement_acknowledgements` | 3 | Requirement acknowledgements |
| `employment_gaps` | 2 | Detected employment gaps |
| `form_pdf_exports` | 6 | Exported PDF forms |
| `service_users` | 1 | Care service users |
| `service_user_documents` | 0 | Service user documents |
| `incident_logs` | 0 | Incident records |
| `contact_submissions` | 0 | Contact form submissions |

---

## 2. DETAILED SCHEMA DEFINITIONS

### 2.1 `employees` Collection (PRIMARY ENTITY)

**This is the SINGLE source of truth for both applicants and employees.**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID - primary identifier |
| `employee_code` | string | Human-readable code (e.g., OCS-0001) |
| `first_name` | string | First name |
| `last_name` | string | Last name |
| `email` | string | Email address |
| `phone` | string | Primary phone |
| `phone_secondary` | string | Secondary phone |
| `role` | string | Job role (healthcare_assistant, nurse, etc.) |
| `status` | string | **CRITICAL** - determines applicant vs employee |
| `onboarding_status` | string | Onboarding progress status |
| `start_date` | string | Employment start date |
| `manager_name` | string | Line manager name |
| `driver_status` | string | Driver availability |
| `notes` | string | Admin notes |
| `completion_percentage` | number | Profile completion % |
| `profile_photo_url` | string | Profile photo URL |
| `compliance_score` | number | Compliance percentage |
| **Address Fields** | | |
| `address_line_1` | string | Address line 1 |
| `address_line_2` | string | Address line 2 |
| `city` | string | City |
| `county` | string | County |
| `postcode` | string | Postcode |
| `country` | string | Country |
| **Next of Kin** | | |
| `next_of_kin_name` | string | NOK name |
| `next_of_kin_phone` | string | NOK phone |
| `next_of_kin_relationship` | string | NOK relationship |
| `next_of_kin_address` | string | NOK address |
| **Declarations** | | |
| `ni_number` | string | National Insurance number |
| `criminal_offence_declared` | boolean | Criminal offence declaration |
| `dbs_update_service_consent` | boolean | DBS consent |
| `has_driving_licence` | boolean | Driving licence |
| `has_own_vehicle` | boolean | Vehicle ownership |
| `health_issue_declared` | boolean | Health declaration |
| `professional_misconduct_declared` | boolean | Misconduct declaration |
| `working_time_opt_out` | boolean | Working time directive opt-out |
| **Reference 1** | | |
| `reference_1_name` | string | Referee name |
| `reference_1_company` | string | Referee company |
| `reference_1_email` | string | Referee email |
| `reference_1_phone` | string | Referee phone |
| `reference_1_start_date` | string | Employment start |
| `reference_1_end_date` | string | Employment end |
| `reference_1_from_cv` | boolean | Matched from CV |
| `reference_1_override_reason` | string | Why referee differs from CV |
| `reference_1_verified` | boolean | Verified status |
| `reference_1_verified_at` | string | Verification timestamp |
| `reference_1_verified_by` | string | Verifier ID |
| `reference_1_request_status` | string | Request status |
| `reference_1_request_sent_at` | string | Request sent timestamp |
| `reference_1_request_token` | string | Request token |
| `reference_1_response_data` | object | Response data |
| `reference_1_response_received_at` | string | Response timestamp |
| `reference_1_mismatch_detected` | boolean | CV mismatch flag |
| `reference_1_mismatch_notes` | string | Mismatch notes |
| `reference_1_rejected` | boolean | Rejected flag |
| `reference_1_rejection_reason` | string | Rejection reason |
| **Reference 2** | | Same structure as Reference 1 |
| **Employment History** | | |
| `employment_history` | array | Employment history entries |
| `cv_extracted_roles` | array | Roles extracted from CV |
| `has_employment_gaps` | boolean | Gaps detected |
| `employment_gaps` | array | Gap details |
| `cv_gaps_detected` | boolean | Gaps in CV |
| `cv_gaps_all_explained` | boolean | All gaps explained |
| **Name Verification** | | |
| `name_mismatch_status` | string | Name mismatch status |
| `name_mismatch_review` | object | Review details |
| **Timestamps** | | |
| `created_at` | string | Creation timestamp |
| `updated_at` | string | Last update timestamp |
| `onboarding_status_updated_at` | string | Status change timestamp |

**Status Values (CRITICAL for applicant/employee separation):**
- Applicant statuses: `new`, `screening`, `interview`, `compliance_review`
- Employee statuses: `onboarding`, `active`, `inactive`, `archived`

---

### 2.2 `employee_documents` Collection (EVIDENCE FILES)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `employee_id` | string | **FK** → employees.id |
| `document_type_id` | string | **FK** → document_types.id |
| `document_type_name` | string | Denormalized type name |
| `category` | string | right_to_work, dbs, identity, etc. |
| `requirement_id` | string | Linked requirement key |
| `requirement_name` | string | Requirement display name |
| `document_label` | string | Custom label |
| `file_url` | string | **Cloud storage URL** |
| `original_filename` | string | Original file name |
| `status` | string | uploaded, verified, rejected |
| `verified` | boolean | Verification status |
| `verified_at` | string | Verification timestamp |
| `verified_by` | string | Verifier user ID |
| `verified_by_name` | string | Verifier name |
| `source_type` | string | upload, extraction, application |
| `expiry_date` | string | Document expiry |
| `issue_date` | string | Document issue date |
| `document_number` | string | Document number (passport, etc.) |
| `permission_end_date` | string | RTW permission end date |
| `evidence_files` | array | Multiple files for same evidence |
| `extraction_reviewed` | boolean | AI extraction reviewed |
| `extraction_reviewed_at` | string | Review timestamp |
| `extraction_reviewed_by` | string | Reviewer ID |
| `created_at` | string | Creation timestamp |
| `updated_at` | string | Update timestamp |
| `uploaded_by` | string | Uploader user ID |
| `uploaded_at` | string | Upload timestamp |

**Evidence Files Array Structure:**
```javascript
evidence_files: [{
  id: string,
  file_url: string,
  original_filename: string,
  uploaded_at: string,
  uploaded_by: string,
  status: "active" | "superseded" | "deleted"
}]
```

---

### 2.3 `rtw_checks` Collection (RIGHT TO WORK VERIFICATION)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID (rtw_chk_xxx) |
| `employee_id` | string | **FK** → employees.id |
| `check_type` | string | Always "right_to_work" |
| `method` | string | share_code_online_check, manual_passport_check |
| `checked_at` | string | When check was performed |
| `checked_by` | string | Checker user ID |
| `outcome` | string | verified, failed, follow_up_required |
| `source_status_type` | string | digital_status, passport_endorsement |
| `follow_up_due_at` | string | Follow-up date if needed |
| `evidence_document_id` | string | **FK** → employee_documents.id |
| `notes` | string | Check notes |
| `is_current` | boolean | Current active check |
| `created_at` | string | Creation timestamp |
| `created_by` | string | Creator user ID |
| `record_version` | number | Version number |
| `superseded_at` | string | When superseded |
| `superseded_by` | string | Superseding check ID |

---

### 2.4 `dbs_checks` Collection (DBS VERIFICATION)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID (dbs_chk_xxx) |
| `employee_id` | string | **FK** → employees.id |
| `check_type` | string | Always "dbs_status" |
| `method` | string | update_service_check, manual_certificate_review |
| `checked_at` | string | When check was performed |
| `checked_by` | string | Checker user ID |
| `outcome` | string | verified, failed, follow_up_required |
| `review_due_at` | string | Internal policy review date |
| `certificate_number` | string | DBS certificate number |
| `evidence_document_id` | string | **FK** → employee_documents.id |
| `notes` | string | Check notes |
| `is_current` | boolean | Current active check |
| `created_at` | string | Creation timestamp |
| `created_by` | string | Creator user ID |
| `record_version` | number | Version number |
| `superseded_at` | string | When superseded |
| `superseded_by` | string | Superseding check ID |

---

### 2.5 `identity_verifications` Collection

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID (id_ver_xxx) |
| `employee_id` | string | **FK** → employees.id |
| `check_type` | string | Always "identity" |
| `method` | string | in_person, video_call |
| `checked_at` | string | When check was performed |
| `checked_by` | string | Checker user ID |
| `outcome` | string | verified, failed |
| `evidence_document_ids` | array | **FK[]** → employee_documents.id |
| `notes` | string | Check notes |
| `is_current` | boolean | Current active check |
| `created_at` | string | Creation timestamp |
| `created_by` | string | Creator user ID |
| `record_version` | number | Version number |

---

### 2.6 `address_verifications` Collection

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `employee_id` | string | **FK** → employees.id |
| `check_type` | string | Always "address_verification" |
| `verified_document_ids` | array | **FK[]** → employee_documents.id |
| `verified_count` | number | Count of verified documents |
| `minimum_required` | number | Required count (usually 2) |
| `meets_requirement` | boolean | Requirement met |
| `verified_at` | string | Verification timestamp |
| `verified_by` | string | Verifier user ID |
| `recency_policy_passed` | boolean | 12-month recency check |
| `notes` | string | Check notes |
| `is_current` | boolean | Current active check |
| `created_at` | string | Creation timestamp |
| `created_by` | string | Creator user ID |
| `record_version` | number | Version number |

---

### 2.7 `training_records` Collection

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `employee_id` | string | **FK** → employees.id |
| `requirement_id` | string | **FK** → training_catalogue.id |
| `training_name` | string | Training name |
| `mandatory` | boolean | Is mandatory |
| `status` | string | current, expired, missing |
| `completion_date` | string | Completion date |
| `expiry_date` | string | Expiry date |
| `certificate_url` | string | Certificate file URL |
| `original_filename` | string | Original file name |
| `completion_method` | string | How training was completed |
| `verified` | boolean | Verified status |
| `verified_by` | string | Verifier user ID |
| `verified_at` | string | Verification timestamp |
| `evidence_files` | array | Multiple certificate files |
| `record_status` | string | active, superseded, deleted |
| `created_at` | string | Creation timestamp |
| `updated_at` | string | Update timestamp |
| `uploaded_at` | string | Upload timestamp |

---

### 2.8 `users` Collection (AUTHENTICATION)

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | UUID |
| `email` | string | **UNIQUE** - login email |
| `password` | string | **bcrypt hashed** |
| `name` | string | Display name |
| `role` | string | super_admin, admin, branch_manager, employee, auditor |
| `branch` | string | Branch assignment |
| `picture` | string | Profile picture URL |
| `created_at` | string | Creation timestamp |

---

### 2.9 `form_submissions` Collection

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `employee_id` | string | **FK** → employees.id |
| `requirement_id` | string | Requirement key |
| `form_type` | string | interview_record, staff_health_questionnaire, induction |
| `data` | object | Form field values (structure varies by type) |
| `status` | string | draft, submitted, verified, rejected |
| `submitted_at` | string | Submission timestamp |
| `submitted_by` | string | Submitter user ID |
| `submitted_by_name` | string | Submitter name |
| `verified` | boolean | Verification status |
| `verified_by` | string | Verifier user ID |
| `verified_by_name` | string | Verifier name |
| `verified_at` | string | Verification timestamp |
| `notes` | string | Admin notes |
| `version` | number | Form version |
| `superseded_at` | string | When superseded |

---

### 2.10 `agreement_acknowledgements` Collection

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `employee_id` | string | **FK** → employees.id |
| `agreement_type` | string | contract_acceptance, handbook_acknowledgement |
| `completion_mode` | string | self_service, phone_assisted |
| `completed_at` | string | Completion timestamp |
| `completed_by` | string | Completer user ID |
| `assisted_by` | string | Assistant user ID (if phone) |
| `version_acknowledged` | string | Document version |
| `call_note` | string | Phone call notes |
| `signed_document_id` | string | **FK** → employee_documents.id |
| `verification_status` | string | pending, verified, rejected |
| `verification_notes` | string | Verification notes |
| `verified_at` | string | Verification timestamp |
| `verified_by` | string | Verifier user ID |
| `created_at` | string | Creation timestamp |
| `created_by` | string | Creator user ID |

---

## 3. DOCUMENT/FILE STORAGE AUDIT

### 3.1 Storage Mechanism

| Attribute | Value |
|-----------|-------|
| **Storage Type** | Emergent Cloud Object Storage |
| **Storage URL** | `https://integrations.emergentagent.com/objstore/api/v1/storage` |
| **Authentication** | EMERGENT_LLM_KEY → storage_key exchange |
| **File Access** | Via backend proxy endpoints |

### 3.2 File Upload Flow

```
1. Frontend sends file to backend
2. Backend authenticates with Emergent storage (init_storage)
3. Backend uploads via PUT /objects/{path}
4. Returns public file_url stored in MongoDB document
5. Files served via /api/employee-documents/{id}/file endpoint
```

### 3.3 File URL Structure

Files are stored with paths like:
```
osabea-care/{employee_id}/{document_type}/{filename}
```

### 3.4 Document Metadata Storage

| Collection | File Fields |
|------------|-------------|
| `employee_documents` | `file_url`, `original_filename`, `evidence_files[]` |
| `training_records` | `certificate_url`, `original_filename`, `evidence_files[]` |
| `org_policies` | `file_url`, `original_filename` |
| `insurance_docs` | `file_url`, `original_filename` |

### 3.5 File Linking Pattern

| Check Collection | Links To |
|-----------------|----------|
| `rtw_checks.evidence_document_id` | `employee_documents.id` |
| `dbs_checks.evidence_document_id` | `employee_documents.id` |
| `identity_verifications.evidence_document_ids[]` | `employee_documents.id` |
| `address_verifications.verified_document_ids[]` | `employee_documents.id` |
| `agreement_acknowledgements.signed_document_id` | `employee_documents.id` |

---

## 4. AUTH SYSTEM AUDIT

### 4.1 Authentication Method

| Attribute | Value |
|-----------|-------|
| **Type** | JWT (JSON Web Token) |
| **Algorithm** | HS256 |
| **Expiration** | 7 days |
| **Secret** | `JWT_SECRET` env var (default fallback exists) |
| **Password Hashing** | bcrypt |

### 4.2 User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `super_admin` | System administrator | Full access |
| `admin` | Organization admin | Full access (except system) |
| `branch_manager` | Branch level manager | Filtered to branch |
| `employee` | Staff member | Self-service only |
| `auditor` | Read-only access | Inspection mode |

### 4.3 Authentication Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/auth/register` | Admin creates user |
| `POST /api/auth/login` | Email/password login |
| `GET /api/auth/me` | Get current user |
| `POST /api/auth/google` | Google OAuth (Emergent) |

### 4.4 Auth Flow

```python
# Login
1. User sends email/password
2. Backend verifies with bcrypt
3. Creates JWT with {user_id, email, role, exp}
4. Frontend stores token, sends in Authorization header

# Protected routes
1. require_user() extracts and validates JWT
2. require_admin() checks role is admin/super_admin
3. require_branch_manager() checks branch access
```

---

## 5. EVIDENCE VS CHECK HANDLING (CRITICAL)

### 5.1 Dual-Row Model Architecture

The system uses a **Dual-Row Model** separating:

| Row Type | Purpose | Collection |
|----------|---------|------------|
| **Evidence Row** | Employee-uploaded documents | `employee_documents` |
| **Check Row** | Employer verification outcome | `rtw_checks`, `dbs_checks`, etc. |

### 5.2 How They Link

```
Evidence Row (employee_documents)
    ↓ (id)
Check Row (rtw_checks.evidence_document_id)
    ↓ links back to
Proof Document (employee_documents with type='verification_proof')
```

### 5.3 Frontend Serialization

```javascript
// Backend compliance-file endpoint returns:
{
  sections: {
    right_to_work: {
      rows: [
        { row_type: "evidence", key: "right_to_work_evidence", ... },
        { row_type: "check", key: "right_to_work_check", check_data: {...}, evidence_document: {...} }
      ]
    }
  }
}

// Frontend maps:
const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
const checkRow = section.rows.find(r => r.row_type === 'check');
```

### 5.4 Why Check Proof Appears in Evidence Row

**This was a BUG that was fixed.** The issue occurred because:

1. Originally, check proof files were stored in `employee_documents` with `type: 'verification_proof'`
2. These were being queried alongside regular evidence documents
3. The frontend wasn't distinguishing `type` field when rendering

**Fix Applied:** Check records now explicitly store `evidence_document_id` linking to the proof, and the compliance-file endpoint returns `evidence_document` inside `check_data`.

### 5.5 Relevant Backend Code

```python
# server.py line ~29541-29555
check_data = {
    "evidence_document_id": check_data.get("evidence_document_id") if has_check else None,
    "evidence_document": next(
        (d for d in documents if d.get("id") == check_data.get("evidence_document_id")),
        None
    ) if has_check and check_data.get("evidence_document_id") else None
}
```

---

## 6. READINESS LOGIC AUDIT

### 6.1 Two-Gate System

| Gate | Name | Question | Module |
|------|------|----------|--------|
| **Gate 1** | Recruitment Approval | Can we hire this person? | `approval_engine.py` |
| **Gate 2** | Work Readiness | Can this person work? | `work_readiness_engine.py` |

### 6.2 Gate 1: Recruitment Approval

**Location:** `/app/backend/approval_engine.py`

**Role-Specific Requirements:**
```python
ROLE_APPROVAL_REQUIREMENTS = {
    "healthcare_assistant": [
        "right_to_work", "identity", "proof_of_address", "dbs",
        "reference_1", "reference_2", "interview_record",
        "recruitment_checklist", "staff_health_questionnaire",
        "staff_personal_info", "employment_history_verification"
    ]
}
```

**Logic Location:** Backend only - `evaluate_recruitment_approval()` function

**Result:** Stored as `recruitment_approved: true` on `employees` document

### 6.3 Gate 2: Work Readiness

**Location:** `/app/backend/work_readiness_engine.py`

**Role-Specific Requirements:**
```python
ROLE_WORK_REQUIREMENTS = {
    "healthcare_assistant": {
        "agreements": ["contract_acceptance", "handbook_acknowledgement"],
        "forms": ["induction", "staff_health_questionnaire"],
        "competencies": ["care_certificate"],
        "critical_documents": ["right_to_work", "dbs", "identity"],
        "training_blockers": True
    }
}
```

**3-Tier Status:**
- `READY_TO_WORK` - 0 blockers
- `READY_WITH_CONDITIONS` - 1-3 blockers
- `NOT_READY` - 4+ blockers

**Logic Location:** Backend only - `evaluate_work_readiness()` function

**Result:** Calculated on-the-fly, not stored (derived from compliance state)

### 6.4 Dashboard Counts

**Calculated in:** Backend API endpoints

| Count | Calculation Location |
|-------|---------------------|
| Expired | `server.py` - counts documents with `expiry_date < now` |
| Needs Renewal | `server.py` - counts documents expiring within 30 days |
| Not Ready | `server.py` - calls `calculate_work_readiness_3tier_quick()` |
| Ready to Work | `server.py` - filters by readiness status |

**Storage:** Not stored - recalculated on each request

---

## 7. API / BACKEND STRUCTURE

### 7.1 Backend Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI |
| **Server** | Uvicorn (via Supervisor) |
| **Database Driver** | Motor (async MongoDB) |
| **Authentication** | PyJWT + bcrypt |
| **Email** | Resend API |
| **AI** | OpenAI GPT-5.2 (via Emergent) |
| **Storage** | Emergent Object Storage |

### 7.2 File Structure

```
/app/backend/
├── server.py              # MAIN FILE (37,790 lines!)
├── approval_engine.py     # Recruitment approval logic
├── work_readiness_engine.py # Work readiness logic
├── agreement_templates.py # Agreement template definitions
├── training_evaluator.py  # Training matrix evaluation
├── training_config.py     # Training configuration
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables
```

### 7.3 Key API Endpoints

**Authentication:**
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `POST /api/auth/google`

**Employees:**
- `GET /api/employees`
- `GET /api/employees/{id}`
- `PUT /api/employees/{id}`
- `GET /api/employees/{id}/compliance-file`
- `GET /api/employees/{id}/documents`
- `POST /api/employees/{id}/upload-document`

**Verification Checks:**
- `POST /api/employees/{id}/right-to-work/check`
- `POST /api/employees/{id}/dbs/check`
- `POST /api/employees/{id}/identity/check`
- `POST /api/employees/{id}/requirements/{req}/verify`

**Training:**
- `GET /api/employees/{id}/training`
- `POST /api/employees/{id}/training`
- `GET /api/training/catalogue`

**Recruitment:**
- `GET /api/recruitment/applicants`
- `POST /api/recruitment/{id}/approve`
- `POST /api/recruitment/{id}/advance-stage`

**References:**
- `POST /api/employees/{id}/references/{num}/send-request`
- `POST /api/employees/{id}/references/{num}/verify`
- `POST /api/references/respond/{token}`

**Dashboard:**
- `GET /api/dashboard/stats`
- `GET /api/dashboard/expiring-documents`

**Organization:**
- `GET /api/org/policies`
- `GET /api/org/certificates`
- `GET /api/compliance-centre/summary`

### 7.4 Technical Debt: server.py Size

**Problem:** `server.py` is 37,790 lines - extremely difficult to maintain.

**Recommendation for migration:** Split into modular routers:
- `routes/auth.py`
- `routes/employees.py`
- `routes/compliance.py`
- `routes/training.py`
- `routes/recruitment.py`
- `routes/references.py`
- `routes/documents.py`
- `routes/organization.py`

---

## 8. DATA INTEGRITY RISKS

### 8.1 Identified Issues

| Risk | Severity | Description |
|------|----------|-------------|
| **Duplicate Functions** | HIGH | F811 linting errors - duplicate function definitions in server.py |
| **Denormalized Data** | MEDIUM | Names, emails duplicated across collections |
| **No Foreign Keys** | HIGH | MongoDB has no referential integrity |
| **Orphaned Documents** | MEDIUM | `employee_documents` may exist without valid `employee_id` |
| **Inconsistent Status** | LOW | Some documents may have contradictory status fields |
| **Mixed Date Formats** | MEDIUM | Some dates as strings, some as ISO |

### 8.2 Data That Could Be Lost

| Data Type | Risk |
|-----------|------|
| **Check History** | `superseded_at`/`superseded_by` chain could break |
| **Reference Audit Trail** | Embedded in `employees` document, could become inconsistent |
| **Employment Gaps** | Partially in `employees`, partially in `employment_gaps` collection |
| **Verification Proofs** | Link from check to proof document is single ID reference |

### 8.3 Relationship Integrity Issues

```
employees.id → employee_documents.employee_id  (NO FK CONSTRAINT)
employees.id → rtw_checks.employee_id          (NO FK CONSTRAINT)
employees.id → training_records.employee_id   (NO FK CONSTRAINT)
rtw_checks.evidence_document_id → employee_documents.id (NO FK CONSTRAINT)
```

---

## 9. MIGRATION READINESS ASSESSMENT

### 9.1 Clean Migration Path

| Collection | Supabase Mapping | Notes |
|------------|------------------|-------|
| `employees` | `employees` table | Primary entity - straightforward |
| `users` | `auth.users` + profile | Use Supabase Auth |
| `employee_documents` | `documents` table | Add FK to employees |
| `rtw_checks` | `rtw_checks` table | Add FK to employees + documents |
| `dbs_checks` | `dbs_checks` table | Add FK to employees + documents |
| `identity_verifications` | `identity_verifications` table | Add FK to employees |
| `address_verifications` | `address_verifications` table | Add FK to employees |
| `training_records` | `training_records` table | Add FK to employees + catalogue |
| `training_catalogue` | `training_catalogue` table | Reference table |
| `form_submissions` | `form_submissions` table | Add FK to employees |
| `agreement_acknowledgements` | `agreement_acknowledgements` table | Add FK to employees |
| `org_policies` | `org_policies` table | Organization-level |
| `audit_logs` | `audit_log` table | Consolidate both collections |

### 9.2 Requires Transformation

| Data | Transformation Needed |
|------|----------------------|
| **References** | Extract from `employees` to separate `references` table |
| **Employment Gaps** | Consolidate embedded + separate collection |
| **Evidence Files** | Normalize `evidence_files[]` array to junction table |
| **Document Types** | Clean up and normalize |
| **User Roles** | Map to Supabase RLS policies |
| **Check History** | Flatten `superseded_by` chain to proper history |

### 9.3 Currently Unreliable

| Data | Issue |
|------|-------|
| `completion_percentage` | Calculated inconsistently |
| `compliance_score` | Sometimes stale |
| Some status fields | May not reflect actual state |
| Denormalized names | May be out of sync |

### 9.4 Must Rebuild From Scratch

| Component | Reason |
|-----------|--------|
| **RLS Policies** | MongoDB has no row-level security |
| **Foreign Keys** | MongoDB has no constraints |
| **Unique Constraints** | Need to add (email, employee_code) |
| **Computed Fields** | Use Supabase functions/triggers |
| **File Storage** | Migrate to Supabase Storage |
| **Auth System** | Use Supabase Auth |

---

## 10. SUMMARY TABLES

### 10.1 Collection Relationships Diagram

```
                         ┌──────────────┐
                         │   users      │
                         │  (auth)      │
                         └──────────────┘
                                │ created_by/verified_by
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                          employees                                │
│  (PRIMARY ENTITY - applicants & employees)                       │
│  - reference_1_*, reference_2_* (embedded)                       │
│  - employment_history[], employment_gaps[] (embedded)            │
└──────────────────────────────────────────────────────────────────┘
        │              │              │              │
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│employee_    │ │training_    │ │form_        │ │agreement_       │
│documents    │ │records      │ │submissions  │ │acknowledgements │
│(evidence)   │ │             │ │             │ │                 │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘
        │              ▲
        │              │ requirement_id
        ▼              │
┌─────────────┐ ┌─────────────┐
│rtw_checks   │ │training_    │
│dbs_checks   │ │catalogue    │
│identity_ver │ │             │
│address_ver  │ │             │
│(verifications)│             │
└─────────────┘ └─────────────┘
```

### 10.2 Supabase Migration Priority

| Priority | What | Why |
|----------|------|-----|
| P0 | `auth.users` | Foundation for everything |
| P0 | `employees` | Primary entity |
| P1 | `employee_documents` | Core compliance |
| P1 | `*_checks/*_verifications` | Core compliance |
| P1 | `training_records` + `training_catalogue` | Compliance |
| P2 | `form_submissions` | Compliance |
| P2 | `agreement_acknowledgements` | Compliance |
| P2 | `org_policies` | Organization |
| P3 | `audit_log` | History |
| P3 | `scheduled_*` | Automation |

---

## NEXT STEPS (DO NOT IMPLEMENT YET)

1. **Design Supabase Schema** - Create proper relational schema with FKs
2. **Plan Migration Scripts** - Write data transformation scripts
3. **Set Up RLS Policies** - Role-based access control
4. **Migrate File Storage** - Move to Supabase Storage
5. **Implement Auth** - Switch to Supabase Auth
6. **Data Validation** - Clean inconsistent data before migration
7. **Test Migration** - Run on copy of data first
