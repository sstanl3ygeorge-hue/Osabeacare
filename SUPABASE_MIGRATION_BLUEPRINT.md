# Supabase Migration Blueprint

**Version:** 1.0  
**Created:** April 2, 2026  
**Status:** PLANNING - NO IMPLEMENTATION YET

---

## Table of Contents

1. [Proposed Postgres Schema](#1-proposed-postgres-schema)
2. [Field Mapping Tables](#2-field-mapping-tables)
3. [Reference Extraction Plan](#3-reference-extraction-plan)
4. [Employment Gap Normalization](#4-employment-gap-normalization)
5. [Dual-Row Compliance Model Design](#5-dual-row-compliance-model-design)
6. [File Storage Migration Plan](#6-file-storage-migration-plan)
7. [User & Auth Migration Plan](#7-user--auth-migration-plan)
8. [Data Review Flags](#8-data-review-flags)
9. [Migration Phases](#9-migration-phases)
10. [Pre-Migration Data Cleanup](#10-pre-migration-data-cleanup)

---

## 1. PROPOSED POSTGRES SCHEMA

### 1.1 Core Tables

```sql
-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE user_role AS ENUM (
  'super_admin', 'admin', 'branch_manager', 'employee', 'auditor'
);

CREATE TYPE person_status AS ENUM (
  'new', 'screening', 'interview', 'compliance_review',  -- Applicant statuses
  'onboarding', 'active', 'inactive', 'archived'          -- Employee statuses
);

CREATE TYPE verification_outcome AS ENUM (
  'awaiting_review', 'verified', 'failed', 'follow_up_required', 'rejected'
);

CREATE TYPE document_status AS ENUM (
  'uploaded', 'awaiting_review', 'verified', 'rejected', 'expired', 'superseded'
);

CREATE TYPE reference_status AS ENUM (
  'not_declared', 'declared', 'request_sent', 'request_viewed',
  'response_received', 'verified', 'rejected'
);

CREATE TYPE gap_status AS ENUM (
  'detected', 'explained', 'verified', 'rejected', 'more_info_needed'
);

CREATE TYPE form_status AS ENUM (
  'not_started', 'draft', 'submitted', 'awaiting_review', 'verified', 'rejected'
);

CREATE TYPE agreement_status AS ENUM (
  'not_started', 'pending', 'submitted', 'verified', 'rejected'
);

CREATE TYPE check_method AS ENUM (
  'share_code_online_check', 'manual_passport_check', 'manual_document_review',
  'update_service_check', 'manual_certificate_review', 'in_person', 'video_call'
);

-- ============================================================
-- PROFILES (extends Supabase auth.users)
-- ============================================================

CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role user_role NOT NULL DEFAULT 'employee',
  branch TEXT,
  picture_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- EMPLOYEES (Primary Entity)
-- ============================================================

CREATE TABLE employees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Identity
  employee_code TEXT UNIQUE,  -- e.g., OCS-0001
  first_name TEXT NOT NULL,
  middle_name TEXT,
  last_name TEXT NOT NULL,
  preferred_name TEXT,
  date_of_birth DATE,
  ni_number TEXT,
  
  -- Contact
  email TEXT NOT NULL,
  phone TEXT,
  phone_secondary TEXT,
  
  -- Address
  address_line_1 TEXT,
  address_line_2 TEXT,
  city TEXT,
  county TEXT,
  postcode TEXT,
  country TEXT DEFAULT 'United Kingdom',
  
  -- Employment
  role TEXT,  -- job role (healthcare_assistant, nurse, etc.)
  status person_status NOT NULL DEFAULT 'new',
  start_date DATE,
  manager_id UUID REFERENCES profiles(id),
  manager_name TEXT,  -- denormalized for display
  branch TEXT,
  
  -- Profile
  profile_photo_url TEXT,
  driver_status TEXT,
  has_driving_licence BOOLEAN DEFAULT FALSE,
  has_own_vehicle BOOLEAN DEFAULT FALSE,
  
  -- Declarations
  criminal_offence_declared BOOLEAN,
  dbs_update_service_consent BOOLEAN,
  health_issue_declared BOOLEAN,
  professional_misconduct_declared BOOLEAN,
  working_time_opt_out BOOLEAN,
  
  -- Next of Kin
  next_of_kin_name TEXT,
  next_of_kin_relationship TEXT,
  next_of_kin_phone TEXT,
  next_of_kin_address TEXT,
  next_of_kin_city TEXT,
  next_of_kin_postcode TEXT,
  
  -- Recruitment
  recruitment_approved BOOLEAN DEFAULT FALSE,
  recruitment_approved_at TIMESTAMPTZ,
  recruitment_approved_by UUID REFERENCES profiles(id),
  
  -- CV Analysis
  cv_document_id UUID,  -- FK to documents, added after documents table
  cv_extracted_roles JSONB,  -- Array of extracted job roles
  
  -- Name Verification
  name_mismatch_status TEXT,
  name_mismatch_review JSONB,
  
  -- Computed (updated by triggers)
  completion_percentage INTEGER DEFAULT 0,
  compliance_score INTEGER DEFAULT 0,
  
  -- Notes
  notes TEXT,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- Migration tracking
  mongo_id TEXT,  -- Original MongoDB id for reference
  migration_reviewed BOOLEAN DEFAULT FALSE,
  migration_notes TEXT
);

-- ============================================================
-- REFERENCES (Extracted from employees)
-- ============================================================

CREATE TABLE employee_references (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  reference_number INTEGER NOT NULL CHECK (reference_number IN (1, 2, 3)),
  
  -- Referee Details
  referee_name TEXT NOT NULL,
  referee_company TEXT,
  referee_email TEXT,
  referee_phone TEXT,
  referee_job_title TEXT,
  
  -- Employment Period (at referee's company)
  employment_start_date DATE,
  employment_end_date DATE,
  
  -- CV Matching
  from_cv BOOLEAN DEFAULT FALSE,
  cv_matched BOOLEAN,
  mismatch_detected BOOLEAN DEFAULT FALSE,
  mismatch_notes TEXT,
  override_reason TEXT,
  override_at TIMESTAMPTZ,
  override_by UUID REFERENCES profiles(id),
  
  -- Request Tracking
  status reference_status NOT NULL DEFAULT 'not_declared',
  request_sent_at TIMESTAMPTZ,
  request_token TEXT UNIQUE,
  request_viewed_at TIMESTAMPTZ,
  last_reminder_at TIMESTAMPTZ,
  resend_count INTEGER DEFAULT 0,
  
  -- Response
  response_received_at TIMESTAMPTZ,
  response_source TEXT,  -- email, phone, portal
  response_data JSONB,
  
  -- Verification
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES profiles(id),
  verified_by_name TEXT,
  
  -- Rejection
  rejected BOOLEAN DEFAULT FALSE,
  rejected_at TIMESTAMPTZ,
  rejected_by UUID REFERENCES profiles(id),
  rejection_reason TEXT,
  
  -- Replacement
  replacement_requested BOOLEAN DEFAULT FALSE,
  replacement_requested_at TIMESTAMPTZ,
  replacement_requested_by UUID REFERENCES profiles(id),
  replacement_reason TEXT,
  
  -- Change History
  change_history JSONB,  -- Array of {from, to, reason, at, by}
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  UNIQUE(employee_id, reference_number)
);

-- ============================================================
-- EMPLOYMENT HISTORY (Normalized)
-- ============================================================

CREATE TABLE employment_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  
  -- Job Details
  company_name TEXT NOT NULL,
  job_title TEXT,
  start_date DATE NOT NULL,
  end_date DATE,  -- NULL = current job
  is_current BOOLEAN DEFAULT FALSE,
  
  -- Source
  source TEXT,  -- 'cv_extraction', 'application', 'manual'
  extraction_confidence NUMERIC(3,2),  -- 0.00 to 1.00
  
  -- Verification
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES profiles(id),
  
  -- Order for display
  sort_order INTEGER,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- EMPLOYMENT GAPS (Normalized)
-- ============================================================

CREATE TABLE employment_gaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  
  -- Gap Period
  gap_start_date DATE NOT NULL,
  gap_end_date DATE NOT NULL,
  gap_months NUMERIC(4,1),  -- Calculated duration
  
  -- Detection
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  preceding_job_id UUID REFERENCES employment_history(id),
  following_job_id UUID REFERENCES employment_history(id),
  
  -- Explanation
  status gap_status NOT NULL DEFAULT 'detected',
  explanation TEXT,
  explanation_submitted_at TIMESTAMPTZ,
  explanation_submitted_by UUID REFERENCES profiles(id),
  
  -- Evidence
  evidence_document_id UUID,  -- FK to documents, added later
  
  -- Verification
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES profiles(id),
  verification_notes TEXT,
  
  -- Rejection
  rejected BOOLEAN DEFAULT FALSE,
  rejected_at TIMESTAMPTZ,
  rejected_by UUID REFERENCES profiles(id),
  rejection_reason TEXT,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- DOCUMENTS (Evidence Files)
-- ============================================================

CREATE TYPE document_category AS ENUM (
  'right_to_work', 'dbs', 'identity', 'proof_of_address', 
  'training', 'cv', 'reference', 'agreement', 'verification_proof',
  'form_attachment', 'other'
);

CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  
  -- Classification
  category document_category NOT NULL,
  document_type_id UUID,  -- FK to document_types reference table
  document_type_name TEXT,
  requirement_id TEXT,  -- e.g., 'right_to_work', 'dbs_certificate'
  requirement_name TEXT,
  document_label TEXT,  -- Custom label
  
  -- File Storage
  storage_path TEXT NOT NULL,  -- Supabase Storage path
  file_url TEXT,  -- Public/signed URL
  original_filename TEXT NOT NULL,
  file_size INTEGER,
  mime_type TEXT,
  
  -- Document Metadata
  document_number TEXT,  -- Passport number, DBS number, etc.
  issue_date DATE,
  expiry_date DATE,
  permission_end_date DATE,  -- For RTW with limited permission
  
  -- Status
  status document_status NOT NULL DEFAULT 'uploaded',
  
  -- Verification
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES profiles(id),
  verified_by_name TEXT,
  verification_notes TEXT,
  
  -- AI Extraction
  extraction_data JSONB,
  extraction_reviewed BOOLEAN DEFAULT FALSE,
  extraction_reviewed_at TIMESTAMPTZ,
  extraction_reviewed_by UUID REFERENCES profiles(id),
  
  -- Upload Info
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  uploaded_by UUID REFERENCES profiles(id),
  source_type TEXT,  -- 'upload', 'extraction', 'application'
  
  -- Supersession (for document history)
  superseded_by UUID REFERENCES documents(id),
  superseded_at TIMESTAMPTZ,
  is_current BOOLEAN DEFAULT TRUE,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- Migration
  mongo_id TEXT,
  old_file_url TEXT  -- Original Emergent storage URL
);

-- ============================================================
-- VERIFICATION CHECKS (Dual-Row Model - Check Records)
-- ============================================================

-- Right to Work Checks
CREATE TABLE rtw_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  
  -- Check Details
  method check_method NOT NULL,
  checked_at TIMESTAMPTZ NOT NULL,
  checked_by UUID REFERENCES profiles(id),
  checked_by_name TEXT,
  
  -- Outcome
  outcome verification_outcome NOT NULL DEFAULT 'awaiting_review',
  source_status_type TEXT,  -- 'digital_status', 'passport_endorsement', etc.
  follow_up_due_at DATE,
  
  -- Evidence Link (Proof of Check)
  proof_document_id UUID REFERENCES documents(id),  -- The PROOF of doing the check
  
  -- Notes
  notes TEXT,
  
  -- Version Control
  is_current BOOLEAN DEFAULT TRUE,
  superseded_at TIMESTAMPTZ,
  superseded_by UUID REFERENCES rtw_checks(id),
  record_version INTEGER DEFAULT 1,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES profiles(id),
  
  -- Migration
  mongo_id TEXT
);

-- DBS Checks
CREATE TABLE dbs_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  
  -- Check Details
  method check_method NOT NULL,
  checked_at TIMESTAMPTZ NOT NULL,
  checked_by UUID REFERENCES profiles(id),
  checked_by_name TEXT,
  
  -- Outcome
  outcome verification_outcome NOT NULL DEFAULT 'awaiting_review',
  certificate_number TEXT,
  review_due_at DATE,  -- Internal policy date, NOT expiry
  
  -- Evidence Link (Proof of Check)
  proof_document_id UUID REFERENCES documents(id),
  
  -- Notes
  notes TEXT,
  
  -- Version Control
  is_current BOOLEAN DEFAULT TRUE,
  superseded_at TIMESTAMPTZ,
  superseded_by UUID REFERENCES dbs_checks(id),
  record_version INTEGER DEFAULT 1,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES profiles(id),
  
  -- Migration
  mongo_id TEXT
);

-- Identity Checks
CREATE TABLE identity_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  
  -- Check Details
  method check_method NOT NULL,
  checked_at TIMESTAMPTZ NOT NULL,
  checked_by UUID REFERENCES profiles(id),
  checked_by_name TEXT,
  
  -- Outcome
  outcome verification_outcome NOT NULL DEFAULT 'awaiting_review',
  
  -- Evidence Link (Proof of Check)
  proof_document_id UUID REFERENCES documents(id),
  
  -- Notes
  notes TEXT,
  
  -- Version Control
  is_current BOOLEAN DEFAULT TRUE,
  superseded_at TIMESTAMPTZ,
  superseded_by UUID REFERENCES identity_checks(id),
  record_version INTEGER DEFAULT 1,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES profiles(id),
  
  -- Migration
  mongo_id TEXT
);

-- Identity Check Documents Junction (multiple docs can be verified)
CREATE TABLE identity_check_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  identity_check_id UUID NOT NULL REFERENCES identity_checks(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  UNIQUE(identity_check_id, document_id)
);

-- Address Verification Checks
CREATE TABLE address_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  
  -- Check Details
  verified_at TIMESTAMPTZ NOT NULL,
  verified_by UUID REFERENCES profiles(id),
  verified_by_name TEXT,
  
  -- Requirements
  verified_count INTEGER NOT NULL DEFAULT 0,
  minimum_required INTEGER NOT NULL DEFAULT 2,
  meets_requirement BOOLEAN DEFAULT FALSE,
  recency_policy_passed BOOLEAN,  -- Within 12 months
  
  -- Notes
  notes TEXT,
  
  -- Version Control
  is_current BOOLEAN DEFAULT TRUE,
  superseded_at TIMESTAMPTZ,
  superseded_by UUID REFERENCES address_checks(id),
  record_version INTEGER DEFAULT 1,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES profiles(id),
  
  -- Migration
  mongo_id TEXT
);

-- Address Check Documents Junction
CREATE TABLE address_check_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  address_check_id UUID NOT NULL REFERENCES address_checks(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  document_date DATE,  -- Date on document for freshness check
  is_valid BOOLEAN,  -- Within 12 month policy
  UNIQUE(address_check_id, document_id)
);

-- ============================================================
-- TRAINING
-- ============================================================

CREATE TABLE training_catalogue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,  -- e.g., 'safeguarding', 'manual_handling'
  name TEXT NOT NULL,
  description TEXT,
  category TEXT,
  is_mandatory BOOLEAN DEFAULT FALSE,
  is_blocker BOOLEAN DEFAULT FALSE,  -- Blocks work readiness
  evidence_required BOOLEAN DEFAULT TRUE,
  validity_months INTEGER,  -- NULL = never expires
  applicable_roles TEXT[],  -- ['healthcare_assistant', 'nurse']
  sort_order INTEGER,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE training_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  training_id UUID NOT NULL REFERENCES training_catalogue(id),
  
  -- Completion
  completion_date DATE,
  expiry_date DATE,
  completion_method TEXT,
  
  -- Evidence
  certificate_document_id UUID REFERENCES documents(id),
  
  -- Status
  status TEXT NOT NULL DEFAULT 'missing',  -- 'missing', 'current', 'expiring', 'expired'
  
  -- Verification
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES profiles(id),
  verified_by_name TEXT,
  
  -- Version Control
  is_current BOOLEAN DEFAULT TRUE,
  superseded_at TIMESTAMPTZ,
  superseded_by UUID REFERENCES training_records(id),
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- Migration
  mongo_id TEXT
);

-- ============================================================
-- FORMS
-- ============================================================

CREATE TABLE form_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  form_type TEXT UNIQUE NOT NULL,  -- 'interview_record', 'staff_health_questionnaire', 'induction'
  name TEXT NOT NULL,
  description TEXT,
  schema JSONB NOT NULL,  -- JSON Schema for form fields
  version INTEGER DEFAULT 1,
  is_blocker BOOLEAN DEFAULT FALSE,
  applicable_to TEXT,  -- 'applicant', 'employee', 'both'
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE form_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  form_template_id UUID NOT NULL REFERENCES form_templates(id),
  form_type TEXT NOT NULL,  -- Denormalized for quick queries
  
  -- Submission
  data JSONB NOT NULL,  -- Form field values
  status form_status NOT NULL DEFAULT 'draft',
  submitted_at TIMESTAMPTZ,
  submitted_by UUID REFERENCES profiles(id),
  submitted_by_name TEXT,
  
  -- Verification
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES profiles(id),
  verified_by_name TEXT,
  verification_notes TEXT,
  
  -- Rejection
  rejected BOOLEAN DEFAULT FALSE,
  rejected_at TIMESTAMPTZ,
  rejected_by UUID REFERENCES profiles(id),
  rejection_reason TEXT,
  
  -- Version Control
  version INTEGER DEFAULT 1,
  is_current BOOLEAN DEFAULT TRUE,
  superseded_at TIMESTAMPTZ,
  superseded_by UUID REFERENCES form_submissions(id),
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- Migration
  mongo_id TEXT
);

-- ============================================================
-- AGREEMENTS
-- ============================================================

CREATE TABLE agreement_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agreement_type TEXT UNIQUE NOT NULL,  -- 'contract_acceptance', 'handbook_acknowledgement'
  name TEXT NOT NULL,
  description TEXT,
  document_url TEXT,  -- Link to agreement document
  version TEXT NOT NULL DEFAULT '1.0',
  is_blocker BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE agreement_acknowledgements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  agreement_template_id UUID NOT NULL REFERENCES agreement_templates(id),
  agreement_type TEXT NOT NULL,  -- Denormalized
  
  -- Completion
  completion_mode TEXT,  -- 'self_service', 'phone_assisted'
  completed_at TIMESTAMPTZ,
  completed_by UUID REFERENCES profiles(id),
  assisted_by UUID REFERENCES profiles(id),
  version_acknowledged TEXT,
  call_note TEXT,
  
  -- Signed Document
  signed_document_id UUID REFERENCES documents(id),
  
  -- Verification
  status agreement_status NOT NULL DEFAULT 'not_started',
  verified BOOLEAN DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  verified_by UUID REFERENCES profiles(id),
  verification_notes TEXT,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- Migration
  mongo_id TEXT
);

-- ============================================================
-- ORGANIZATION
-- ============================================================

CREATE TABLE org_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  category TEXT,
  version TEXT,
  status TEXT DEFAULT 'active',
  storage_path TEXT,
  file_url TEXT,
  original_filename TEXT,
  review_date DATE,
  last_reviewed_at TIMESTAMPTZ,
  reviewed_by UUID REFERENCES profiles(id),
  notes TEXT,
  cqc_required BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES profiles(id),
  mongo_id TEXT
);

CREATE TABLE org_certificates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  certificate_type TEXT,
  storage_path TEXT,
  file_url TEXT,
  original_filename TEXT,
  issue_date DATE,
  expiry_date DATE,
  status TEXT DEFAULT 'active',
  cqc_required BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES profiles(id),
  mongo_id TEXT
);

CREATE TABLE policy_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  policy_id UUID NOT NULL REFERENCES org_policies(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  assigned_by UUID REFERENCES profiles(id),
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(employee_id, policy_id)
);

-- ============================================================
-- RECURRING ITEMS
-- ============================================================

CREATE TABLE recurring_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  item_type TEXT NOT NULL,  -- 'supervision', 'appraisal', 'spot_check'
  title TEXT NOT NULL,
  frequency_months INTEGER NOT NULL,
  last_completed_at TIMESTAMPTZ,
  next_due_at DATE NOT NULL,
  status TEXT DEFAULT 'upcoming',  -- 'overdue', 'due_now', 'upcoming', 'completed'
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE recurring_completions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recurring_item_id UUID NOT NULL REFERENCES recurring_items(id) ON DELETE CASCADE,
  completed_at TIMESTAMPTZ NOT NULL,
  completed_by UUID REFERENCES profiles(id),
  notes TEXT,
  evidence_document_id UUID REFERENCES documents(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- AUDIT LOG
-- ============================================================

CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Entity
  entity_type TEXT NOT NULL,  -- 'employee', 'document', 'rtw_check', etc.
  entity_id UUID,
  
  -- Action
  action TEXT NOT NULL,
  
  -- Actor
  performed_by UUID REFERENCES profiles(id),
  performed_by_name TEXT,
  
  -- Details
  details JSONB,
  previous_state JSONB,
  new_state JSONB,
  
  -- Context
  ip_address INET,
  user_agent TEXT,
  
  -- Timestamp
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- SCHEDULED REQUESTS
-- ============================================================

CREATE TABLE scheduled_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  request_type TEXT NOT NULL,  -- 'training_reminder', 'document_request'
  target_roles TEXT[],
  schedule_cron TEXT,  -- Cron expression
  days_before_expiry INTEGER[],  -- e.g., [60, 30, 7]
  email_template TEXT,
  active BOOLEAN DEFAULT TRUE,
  last_run_at TIMESTAMPTZ,
  next_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES profiles(id)
);

CREATE TABLE request_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheduled_request_id UUID REFERENCES scheduled_requests(id),
  employee_id UUID REFERENCES employees(id),
  request_type TEXT NOT NULL,
  status TEXT DEFAULT 'sent',
  sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  error_message TEXT
);

-- ============================================================
-- DOCUMENT TYPES (Reference Table)
-- ============================================================

CREATE TABLE document_types (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  category document_category NOT NULL,
  description TEXT,
  is_expiring BOOLEAN DEFAULT FALSE,
  validity_months INTEGER,
  cqc_required BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT TRUE,
  sort_order INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_employees_status ON employees(status);
CREATE INDEX idx_employees_role ON employees(role);
CREATE INDEX idx_employees_email ON employees(email);
CREATE INDEX idx_employees_recruitment_approved ON employees(recruitment_approved);

CREATE INDEX idx_documents_employee_id ON documents(employee_id);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_is_current ON documents(is_current);

CREATE INDEX idx_rtw_checks_employee_id ON rtw_checks(employee_id);
CREATE INDEX idx_rtw_checks_is_current ON rtw_checks(is_current);

CREATE INDEX idx_dbs_checks_employee_id ON dbs_checks(employee_id);
CREATE INDEX idx_dbs_checks_is_current ON dbs_checks(is_current);

CREATE INDEX idx_identity_checks_employee_id ON identity_checks(employee_id);
CREATE INDEX idx_address_checks_employee_id ON address_checks(employee_id);

CREATE INDEX idx_training_records_employee_id ON training_records(employee_id);
CREATE INDEX idx_training_records_status ON training_records(status);

CREATE INDEX idx_form_submissions_employee_id ON form_submissions(employee_id);
CREATE INDEX idx_form_submissions_form_type ON form_submissions(form_type);

CREATE INDEX idx_references_employee_id ON employee_references(employee_id);
CREATE INDEX idx_employment_history_employee_id ON employment_history(employee_id);
CREATE INDEX idx_employment_gaps_employee_id ON employment_gaps(employee_id);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
```

---

## 2. FIELD MAPPING TABLES

### 2.1 employees Collection

| MongoDB Field | Postgres Column | Action | Notes |
|---------------|-----------------|--------|-------|
| `id` | `id` | KEEP | Convert string UUID to UUID type |
| `employee_code` | `employee_code` | KEEP | |
| `first_name` | `first_name` | KEEP | |
| `last_name` | `last_name` | KEEP | |
| `email` | `email` | KEEP | |
| `phone` | `phone` | KEEP | |
| `phone_secondary` | `phone_secondary` | KEEP | |
| `role` | `role` | KEEP | |
| `status` | `status` | TRANSFORM | String → person_status ENUM |
| `onboarding_status` | DROP | DROP | Redundant with status |
| `start_date` | `start_date` | TRANSFORM | String → DATE |
| `manager_name` | `manager_name` | KEEP | |
| `driver_status` | `driver_status` | KEEP | |
| `notes` | `notes` | KEEP | |
| `completion_percentage` | `completion_percentage` | KEEP | Will be computed |
| `compliance_score` | `compliance_score` | KEEP | Will be computed |
| `profile_photo_url` | `profile_photo_url` | TRANSFORM | Migrate file |
| `address_line_1` | `address_line_1` | KEEP | |
| `address_line_2` | `address_line_2` | KEEP | |
| `city` | `city` | KEEP | |
| `county` | `county` | KEEP | |
| `postcode` | `postcode` | KEEP | |
| `country` | `country` | KEEP | |
| `next_of_kin_*` | `next_of_kin_*` | KEEP | All NOK fields |
| `ni_number` | `ni_number` | KEEP | |
| `criminal_offence_declared` | `criminal_offence_declared` | KEEP | |
| `dbs_update_service_consent` | `dbs_update_service_consent` | KEEP | |
| `has_driving_licence` | `has_driving_licence` | KEEP | |
| `has_own_vehicle` | `has_own_vehicle` | KEEP | |
| `health_issue_declared` | `health_issue_declared` | KEEP | |
| `professional_misconduct_declared` | `professional_misconduct_declared` | KEEP | |
| `working_time_opt_out` | `working_time_opt_out` | KEEP | |
| `reference_1_*` | → `employee_references` | EXTRACT | Move to separate table |
| `reference_2_*` | → `employee_references` | EXTRACT | Move to separate table |
| `employment_history` | → `employment_history` | EXTRACT | Move to separate table |
| `employment_gaps` | → `employment_gaps` | EXTRACT | Move to separate table |
| `cv_extracted_roles` | `cv_extracted_roles` | KEEP | JSONB |
| `cv_gaps_detected` | DROP | DROP | Computed from gaps table |
| `cv_gaps_all_explained` | DROP | DROP | Computed from gaps table |
| `name_mismatch_status` | `name_mismatch_status` | KEEP | |
| `name_mismatch_review` | `name_mismatch_review` | KEEP | JSONB |
| `recruitment_approved` | `recruitment_approved` | KEEP | |
| `recruitment_approved_at` | `recruitment_approved_at` | TRANSFORM | String → TIMESTAMPTZ |
| `recruitment_approved_by` | `recruitment_approved_by` | TRANSFORM | String → UUID FK |
| `created_at` | `created_at` | TRANSFORM | String → TIMESTAMPTZ |
| `updated_at` | `updated_at` | TRANSFORM | String → TIMESTAMPTZ |
| `onboarding_status_updated_at` | DROP | DROP | Use audit_log |

### 2.2 employee_documents Collection

| MongoDB Field | Postgres Column | Action | Notes |
|---------------|-----------------|--------|-------|
| `id` | `id` | KEEP | String → UUID |
| `employee_id` | `employee_id` | TRANSFORM | String → UUID FK |
| `document_type_id` | `document_type_id` | TRANSFORM | String → UUID FK |
| `document_type_name` | `document_type_name` | KEEP | Denormalized |
| `category` | `category` | TRANSFORM | String → ENUM |
| `requirement_id` | `requirement_id` | KEEP | |
| `requirement_name` | `requirement_name` | KEEP | |
| `document_label` | `document_label` | KEEP | |
| `file_url` | `old_file_url` | TRANSFORM | Keep original, migrate file |
| `file_url` | `storage_path` | CREATE | New Supabase path |
| `original_filename` | `original_filename` | KEEP | |
| `status` | `status` | TRANSFORM | String → ENUM |
| `verified` | `verified` | KEEP | |
| `verified_at` | `verified_at` | TRANSFORM | String → TIMESTAMPTZ |
| `verified_by` | `verified_by` | TRANSFORM | String → UUID FK |
| `verified_by_name` | `verified_by_name` | KEEP | |
| `expiry_date` | `expiry_date` | TRANSFORM | String → DATE |
| `issue_date` | `issue_date` | TRANSFORM | String → DATE |
| `document_number` | `document_number` | KEEP | |
| `permission_end_date` | `permission_end_date` | TRANSFORM | String → DATE |
| `evidence_files` | DROP | DROP | Normalize to separate rows |
| `source_type` | `source_type` | KEEP | |
| `extraction_reviewed` | `extraction_reviewed` | KEEP | |
| `extraction_reviewed_at` | `extraction_reviewed_at` | TRANSFORM | |
| `extraction_reviewed_by` | `extraction_reviewed_by` | TRANSFORM | |
| `uploaded_at` | `uploaded_at` | TRANSFORM | String → TIMESTAMPTZ |
| `uploaded_by` | `uploaded_by` | TRANSFORM | String → UUID FK |
| `created_at` | `created_at` | TRANSFORM | |
| `updated_at` | `updated_at` | TRANSFORM | |

### 2.3 rtw_checks Collection

| MongoDB Field | Postgres Column | Action | Notes |
|---------------|-----------------|--------|-------|
| `id` | `id` | TRANSFORM | String → UUID |
| `employee_id` | `employee_id` | TRANSFORM | String → UUID FK |
| `check_type` | DROP | DROP | Always 'right_to_work' |
| `method` | `method` | TRANSFORM | String → ENUM |
| `checked_at` | `checked_at` | TRANSFORM | String → TIMESTAMPTZ |
| `checked_by` | `checked_by` | TRANSFORM | String → UUID FK |
| `outcome` | `outcome` | TRANSFORM | String → ENUM |
| `source_status_type` | `source_status_type` | KEEP | |
| `follow_up_due_at` | `follow_up_due_at` | TRANSFORM | String → DATE |
| `evidence_document_id` | `proof_document_id` | TRANSFORM | RENAME + UUID FK |
| `notes` | `notes` | KEEP | |
| `is_current` | `is_current` | KEEP | |
| `created_at` | `created_at` | TRANSFORM | String → TIMESTAMPTZ |
| `created_by` | `created_by` | TRANSFORM | String → UUID FK |
| `record_version` | `record_version` | KEEP | |
| `superseded_at` | `superseded_at` | TRANSFORM | |
| `superseded_by` | `superseded_by` | TRANSFORM | String → UUID FK |

### 2.4 dbs_checks, identity_verifications, address_verifications

*Similar mapping pattern as rtw_checks - see schema above*

### 2.5 users Collection

| MongoDB Field | Postgres Column | Action | Notes |
|---------------|-----------------|--------|-------|
| `user_id` | `id` | TRANSFORM | Move to auth.users |
| `email` | `email` | KEEP | Move to auth.users + profiles |
| `password` | `encrypted_password` | TRANSFORM | Move to auth.users |
| `name` | `name` | KEEP | profiles table |
| `role` | `role` | TRANSFORM | String → ENUM, profiles |
| `branch` | `branch` | KEEP | profiles table |
| `picture` | `picture_url` | KEEP | profiles table |
| `created_at` | `created_at` | TRANSFORM | |

### 2.6 training_records Collection

| MongoDB Field | Postgres Column | Action | Notes |
|---------------|-----------------|--------|-------|
| `id` | `id` | TRANSFORM | String → UUID |
| `employee_id` | `employee_id` | TRANSFORM | String → UUID FK |
| `training_name` | DROP | DROP | Get from training_catalogue |
| `mandatory` | DROP | DROP | Get from training_catalogue |
| `requirement_id` | `training_id` | TRANSFORM | Map to training_catalogue.id |
| `status` | `status` | KEEP | |
| `completion_date` | `completion_date` | TRANSFORM | String → DATE |
| `expiry_date` | `expiry_date` | TRANSFORM | String → DATE |
| `certificate_url` | → `documents` | TRANSFORM | Create document record |
| `original_filename` | → `documents` | TRANSFORM | Part of document |
| `completion_method` | `completion_method` | KEEP | |
| `verified` | `verified` | KEEP | |
| `verified_by` | `verified_by` | TRANSFORM | String → UUID FK |
| `verified_at` | `verified_at` | TRANSFORM | |
| `evidence_files` | DROP | DROP | Normalize to documents |
| `created_at` | `created_at` | TRANSFORM | |
| `updated_at` | `updated_at` | TRANSFORM | |

### 2.7 form_submissions Collection

| MongoDB Field | Postgres Column | Action | Notes |
|---------------|-----------------|--------|-------|
| `id` | `id` | TRANSFORM | String → UUID |
| `employee_id` | `employee_id` | TRANSFORM | String → UUID FK |
| `requirement_id` | DROP | DROP | Use form_type |
| `form_type` | `form_type` | KEEP | |
| `form_type` | `form_template_id` | CREATE | FK to form_templates |
| `data` | `data` | KEEP | JSONB |
| `status` | `status` | TRANSFORM | String → ENUM |
| `submitted_at` | `submitted_at` | TRANSFORM | |
| `submitted_by` | `submitted_by` | TRANSFORM | String → UUID FK |
| `submitted_by_name` | `submitted_by_name` | KEEP | |
| `verified` | `verified` | KEEP | |
| `verified_by` | `verified_by` | TRANSFORM | |
| `verified_by_name` | `verified_by_name` | KEEP | |
| `verified_at` | `verified_at` | TRANSFORM | |
| `notes` | `verification_notes` | RENAME | |
| `version` | `version` | KEEP | |
| `superseded_at` | `superseded_at` | TRANSFORM | |

---

## 3. REFERENCE EXTRACTION PLAN

### 3.1 Current State (MongoDB)

References are **embedded** in the `employees` collection:
```javascript
{
  id: "emp_123",
  reference_1_name: "John Smith",
  reference_1_company: "NHS Trust",
  reference_1_email: "john@nhs.uk",
  reference_1_phone: "07123456789",
  reference_1_start_date: "2020-01-01",
  reference_1_end_date: "2023-06-30",
  reference_1_from_cv: true,
  reference_1_verified: true,
  reference_1_verified_at: "2024-01-15T10:30:00Z",
  reference_1_verified_by: "user_admin",
  reference_1_request_status: "verified",
  reference_1_request_sent_at: "2024-01-10T09:00:00Z",
  reference_1_request_token: "tok_abc123",
  reference_1_response_data: {...},
  reference_1_mismatch_detected: false,
  reference_1_rejected: false,
  // ... 30+ more reference_1_* fields
  // ... same for reference_2_*
}
```

### 3.2 Target State (Postgres)

References in **separate normalized table**:
```sql
employee_references (
  id UUID,
  employee_id UUID FK → employees,
  reference_number INTEGER (1, 2, 3),
  referee_name TEXT,
  referee_company TEXT,
  ...
)
```

### 3.3 Extraction Algorithm

```python
# Pseudocode for migration script
def extract_references(mongo_employee: dict) -> list:
    references = []
    
    for num in [1, 2]:
        prefix = f"reference_{num}_"
        
        # Check if reference exists
        if not mongo_employee.get(f"{prefix}name"):
            continue
        
        ref = {
            "id": generate_uuid(),
            "employee_id": mongo_employee["id"],
            "reference_number": num,
            
            # Referee details
            "referee_name": mongo_employee.get(f"{prefix}name"),
            "referee_company": mongo_employee.get(f"{prefix}company"),
            "referee_email": mongo_employee.get(f"{prefix}email"),
            "referee_phone": mongo_employee.get(f"{prefix}phone"),
            "employment_start_date": parse_date(mongo_employee.get(f"{prefix}start_date")),
            "employment_end_date": parse_date(mongo_employee.get(f"{prefix}end_date")),
            
            # CV matching
            "from_cv": mongo_employee.get(f"{prefix}from_cv", False),
            "mismatch_detected": mongo_employee.get(f"{prefix}mismatch_detected", False),
            "mismatch_notes": mongo_employee.get(f"{prefix}mismatch_notes"),
            "override_reason": mongo_employee.get(f"{prefix}override_reason"),
            "override_at": parse_timestamp(mongo_employee.get(f"{prefix}override_at")),
            "override_by": map_user_id(mongo_employee.get(f"{prefix}override_by")),
            
            # Request tracking
            "status": map_reference_status(mongo_employee, num),
            "request_sent_at": parse_timestamp(mongo_employee.get(f"{prefix}request_sent_at")),
            "request_token": mongo_employee.get(f"{prefix}request_token"),
            "request_viewed_at": parse_timestamp(mongo_employee.get(f"{prefix}request_viewed_at")),
            "last_reminder_at": parse_timestamp(mongo_employee.get(f"{prefix}last_reminder_at")),
            "resend_count": mongo_employee.get(f"{prefix}resend_count", 0),
            
            # Response
            "response_received_at": parse_timestamp(mongo_employee.get(f"{prefix}response_received_at")),
            "response_source": mongo_employee.get(f"{prefix}response_source"),
            "response_data": mongo_employee.get(f"{prefix}response_data"),
            
            # Verification
            "verified": mongo_employee.get(f"{prefix}verified", False),
            "verified_at": parse_timestamp(mongo_employee.get(f"{prefix}verified_at")),
            "verified_by": map_user_id(mongo_employee.get(f"{prefix}verified_by")),
            
            # Rejection
            "rejected": mongo_employee.get(f"{prefix}rejected", False),
            "rejected_at": parse_timestamp(mongo_employee.get(f"{prefix}rejected_at")),
            "rejected_by": map_user_id(mongo_employee.get(f"{prefix}rejected_by")),
            "rejection_reason": mongo_employee.get(f"{prefix}rejection_reason") or mongo_employee.get(f"{prefix}rejected_reason"),
            
            # History
            "change_history": mongo_employee.get(f"{prefix}referee_change_history"),
        }
        
        references.append(ref)
    
    return references

def map_reference_status(employee: dict, num: int) -> str:
    """Derive reference_status ENUM from multiple fields"""
    prefix = f"reference_{num}_"
    
    if employee.get(f"{prefix}verified"):
        return "verified"
    if employee.get(f"{prefix}rejected"):
        return "rejected"
    if employee.get(f"{prefix}response_received_at"):
        return "response_received"
    if employee.get(f"{prefix}request_viewed_at"):
        return "request_viewed"
    if employee.get(f"{prefix}request_sent_at"):
        return "request_sent"
    if employee.get(f"{prefix}name"):
        return "declared"
    return "not_declared"
```

### 3.4 Data Validation

Before extraction, validate:
- [ ] All reference_1_name values are non-empty strings
- [ ] All dates can be parsed (ISO format)
- [ ] User IDs in verified_by can be mapped to profiles.id
- [ ] No orphaned request_tokens

### 3.5 Rollback Plan

Keep original fields in `employees.migration_notes` as JSON backup:
```sql
UPDATE employees SET migration_notes = jsonb_build_object(
  'original_reference_1', row_to_json(reference_1_fields),
  'original_reference_2', row_to_json(reference_2_fields)
);
```

---

## 4. EMPLOYMENT GAP NORMALIZATION

### 4.1 Current State (MongoDB)

Gaps exist in **two places**:
1. Embedded array in `employees.employment_gaps`
2. Separate `employment_gaps` collection

```javascript
// In employees collection
{
  id: "emp_123",
  employment_gaps: [
    {
      start_date: "2022-10-31",
      end_date: "2023-01-15",
      duration_months: 2.5,
      status: "more_info_needed",
      explanation: null,
      evidence_document_id: null
    }
  ],
  has_employment_gaps: true,
  cv_gaps_detected: true,
  cv_gaps_all_explained: false
}

// In employment_gaps collection
{
  id: "gap_123",
  employee_id: "emp_123",
  start_date: "2022-10-31",
  end_date: "2023-01-15",
  ...
}
```

### 4.2 Target State (Postgres)

Single normalized table with proper FKs:
```sql
employment_gaps (
  id UUID PRIMARY KEY,
  employee_id UUID FK → employees,
  gap_start_date DATE,
  gap_end_date DATE,
  gap_months NUMERIC,
  status gap_status,
  explanation TEXT,
  evidence_document_id UUID FK → documents,
  preceding_job_id UUID FK → employment_history,
  following_job_id UUID FK → employment_history,
  verified BOOLEAN,
  ...
)
```

### 4.3 Normalization Algorithm

```python
def normalize_employment_gaps(mongo_employee: dict, mongo_gaps_collection: list) -> list:
    """
    Consolidate gaps from both sources into normalized table.
    Priority: employment_gaps collection > embedded array
    """
    employee_id = mongo_employee["id"]
    normalized_gaps = []
    seen_gaps = set()  # (start_date, end_date) tuples
    
    # First: Process separate collection (authoritative)
    collection_gaps = [g for g in mongo_gaps_collection if g["employee_id"] == employee_id]
    for gap in collection_gaps:
        key = (gap["start_date"], gap["end_date"])
        if key in seen_gaps:
            continue
        seen_gaps.add(key)
        
        normalized_gaps.append({
            "id": gap.get("id") or generate_uuid(),
            "employee_id": employee_id,
            "gap_start_date": parse_date(gap["start_date"]),
            "gap_end_date": parse_date(gap["end_date"]),
            "gap_months": gap.get("duration_months") or calculate_months(gap["start_date"], gap["end_date"]),
            "status": map_gap_status(gap),
            "explanation": gap.get("explanation"),
            "evidence_document_id": map_document_id(gap.get("evidence_document_id")),
            "verified": gap.get("verified", False),
            "verified_at": parse_timestamp(gap.get("verified_at")),
            "verified_by": map_user_id(gap.get("verified_by")),
            "verification_notes": gap.get("verification_notes"),
            "rejected": gap.get("rejected", False),
            "rejected_at": parse_timestamp(gap.get("rejected_at")),
            "rejected_by": map_user_id(gap.get("rejected_by")),
            "rejection_reason": gap.get("rejection_reason"),
            "detected_at": parse_timestamp(gap.get("created_at")) or now(),
        })
    
    # Second: Process embedded array (fill in any missing)
    embedded_gaps = mongo_employee.get("employment_gaps", [])
    for gap in embedded_gaps:
        key = (gap.get("start_date"), gap.get("end_date"))
        if key in seen_gaps:
            continue  # Already processed from collection
        seen_gaps.add(key)
        
        normalized_gaps.append({
            "id": generate_uuid(),
            "employee_id": employee_id,
            "gap_start_date": parse_date(gap["start_date"]),
            "gap_end_date": parse_date(gap["end_date"]),
            "gap_months": gap.get("duration_months") or calculate_months(gap["start_date"], gap["end_date"]),
            "status": map_gap_status(gap),
            "explanation": gap.get("explanation"),
            "evidence_document_id": map_document_id(gap.get("evidence_document_id")),
            "verified": gap.get("verified", False),
            "detected_at": now(),
            "migration_reviewed": True,  # Flag for manual review
            "migration_notes": "Migrated from embedded array"
        })
    
    return normalized_gaps

def map_gap_status(gap: dict) -> str:
    """Map various status representations to gap_status ENUM"""
    status = gap.get("status", "").lower()
    
    status_map = {
        "detected": "detected",
        "more_info_needed": "more_info_needed",
        "explained": "explained",
        "verified": "verified",
        "rejected": "rejected",
        "pending": "detected",
        "awaiting_review": "explained",
    }
    
    # Handle verified/rejected flags
    if gap.get("verified"):
        return "verified"
    if gap.get("rejected"):
        return "rejected"
    
    return status_map.get(status, "detected")
```

### 4.4 Employment History Migration

```python
def migrate_employment_history(mongo_employee: dict) -> list:
    """Extract employment_history array to separate table"""
    employee_id = mongo_employee["id"]
    history = mongo_employee.get("employment_history", [])
    
    records = []
    for idx, job in enumerate(history):
        records.append({
            "id": generate_uuid(),
            "employee_id": employee_id,
            "company_name": job.get("company") or job.get("company_name"),
            "job_title": job.get("job_title") or job.get("title") or job.get("role"),
            "start_date": parse_date(job.get("start_date")),
            "end_date": parse_date(job.get("end_date")),
            "is_current": job.get("is_current", False),
            "source": job.get("source", "cv_extraction"),
            "extraction_confidence": job.get("confidence"),
            "sort_order": idx,
        })
    
    return records
```

### 4.5 Linking Gaps to Jobs

After migrating both tables:
```sql
-- Update gaps with preceding/following job references
UPDATE employment_gaps g SET
  preceding_job_id = (
    SELECT id FROM employment_history h 
    WHERE h.employee_id = g.employee_id 
    AND h.end_date <= g.gap_start_date
    ORDER BY h.end_date DESC LIMIT 1
  ),
  following_job_id = (
    SELECT id FROM employment_history h 
    WHERE h.employee_id = g.employee_id 
    AND h.start_date >= g.gap_end_date
    ORDER BY h.start_date ASC LIMIT 1
  );
```

---

## 5. DUAL-ROW COMPLIANCE MODEL DESIGN

### 5.1 Architecture Overview

The dual-row model separates:
1. **Evidence** - Documents uploaded by employee/admin
2. **Check Record** - Employer verification of the evidence
3. **Proof of Check** - Document proving the check was done

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPLIANCE REQUIREMENT                       │
│                    (e.g., Right to Work)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                    ┌─────────────────┐     │
│  │  EVIDENCE ROW   │                    │   CHECK ROW     │     │
│  │                 │                    │                 │     │
│  │  documents      │                    │  rtw_checks     │     │
│  │  (category:     │──── supports ────▶ │                 │     │
│  │   right_to_work)│                    │  proof_document │     │
│  │                 │                    │  ────────┐      │     │
│  └─────────────────┘                    └──────────│──────┘     │
│                                                    │             │
│                                                    ▼             │
│                                         ┌─────────────────┐     │
│                                         │  PROOF DOCUMENT │     │
│                                         │                 │     │
│                                         │  documents      │     │
│                                         │  (category:     │     │
│                                         │   verification_ │     │
│                                         │   proof)        │     │
│                                         └─────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Document Categories (ENUM)

```sql
CREATE TYPE document_category AS ENUM (
  -- Evidence categories
  'right_to_work',      -- Passport, BRP, visa
  'dbs',                -- DBS certificate
  'identity',           -- Driving licence, ID cards
  'proof_of_address',   -- Utility bills, bank statements
  'training',           -- Training certificates
  'cv',                 -- CV/resume
  'reference',          -- Reference letters
  'agreement',          -- Signed contracts/handbooks
  
  -- Proof of check (NEW - distinct from evidence)
  'verification_proof', -- Screenshots, printed checks
  
  -- Other
  'form_attachment',    -- Attachments to forms
  'other'               -- Miscellaneous
);
```

### 5.3 Table Structure

#### Evidence (documents table)
```sql
-- Example: Passport uploaded as RTW evidence
INSERT INTO documents (
  employee_id,
  category,                -- 'right_to_work'
  document_type_name,      -- 'Passport'
  requirement_id,          -- 'right_to_work'
  storage_path,            -- 'employees/{id}/rtw/passport.pdf'
  status,                  -- 'verified'
  verified,                -- true
  ...
);
```

#### Check Record (rtw_checks table)
```sql
-- Example: Online share code check performed
INSERT INTO rtw_checks (
  employee_id,
  method,                  -- 'share_code_online_check'
  checked_at,              -- '2024-01-15 10:30:00'
  checked_by,              -- UUID of admin
  outcome,                 -- 'verified'
  proof_document_id,       -- UUID of screenshot document
  notes,                   -- 'Share code XYZ123 verified online'
  ...
);
```

#### Proof of Check (documents table)
```sql
-- Example: Screenshot of online check
INSERT INTO documents (
  employee_id,
  category,                -- 'verification_proof'
  document_type_name,      -- 'RTW Check Screenshot'
  requirement_id,          -- 'rtw_check_proof'
  storage_path,            -- 'employees/{id}/checks/rtw_screenshot.png'
  status,                  -- 'uploaded'
  ...
);
```

### 5.4 Query Pattern for Compliance File

```sql
-- Get full compliance data for an employee
WITH evidence AS (
  SELECT 
    d.*,
    'evidence' as row_type
  FROM documents d
  WHERE d.employee_id = $1
    AND d.is_current = true
    AND d.category IN ('right_to_work', 'dbs', 'identity', 'proof_of_address')
),
rtw_check AS (
  SELECT 
    c.*,
    'check' as row_type,
    p.storage_path as proof_storage_path,
    p.original_filename as proof_filename
  FROM rtw_checks c
  LEFT JOIN documents p ON c.proof_document_id = p.id
  WHERE c.employee_id = $1
    AND c.is_current = true
)
SELECT 
  'right_to_work' as section,
  e.row_type,
  e.id as document_id,
  e.category,
  e.status as evidence_status,
  e.verified as evidence_verified,
  NULL as check_id,
  NULL as check_outcome
FROM evidence e
WHERE e.category = 'right_to_work'

UNION ALL

SELECT
  'right_to_work' as section,
  c.row_type,
  NULL as document_id,
  NULL as category,
  NULL as evidence_status,
  NULL as evidence_verified,
  c.id as check_id,
  c.outcome as check_outcome
FROM rtw_check c;
```

### 5.5 Frontend Serialization (API Response)

```json
{
  "sections": {
    "right_to_work": {
      "title": "Right to Work",
      "is_blocker": true,
      "rows": [
        {
          "row_type": "evidence",
          "key": "right_to_work_evidence",
          "documents": [...],
          "status": "verified",
          "is_verified": true
        },
        {
          "row_type": "check",
          "key": "right_to_work_check",
          "check_data": {
            "id": "uuid",
            "method": "share_code_online_check",
            "outcome": "verified",
            "checked_at": "2024-01-15T10:30:00Z"
          },
          "proof_document": {
            "id": "uuid",
            "filename": "rtw_screenshot.png",
            "file_url": "https://..."
          },
          "status": "verified",
          "is_verified": true
        }
      ]
    }
  }
}
```

### 5.6 Migration Rules

| MongoDB Source | Postgres Target | Notes |
|----------------|-----------------|-------|
| `employee_documents` with `category: 'right_to_work'` | `documents` with `category = 'right_to_work'` | Direct migration |
| `employee_documents` with `type: 'verification_proof'` | `documents` with `category = 'verification_proof'` | Keep separate |
| `rtw_checks.evidence_document_id` | `rtw_checks.proof_document_id` | Rename to clarify purpose |
| `dbs_checks.evidence_document_id` | `dbs_checks.proof_document_id` | Rename to clarify purpose |
| `identity_verifications.evidence_document_ids[]` | `identity_check_documents` junction | Normalize array |
| `address_verifications.verified_document_ids[]` | `address_check_documents` junction | Normalize array |

### 5.7 Critical Invariants

1. **Evidence and Proof are SEPARATE** - Never collapse them
2. **Check requires Proof** - `proof_document_id` must be populated for verified checks
3. **Evidence supports Check** - Documents in evidence categories linked by `employee_id`
4. **One current check per type** - Only one `is_current = true` per employee per check type

---

## 6. FILE STORAGE MIGRATION PLAN

### 6.1 Current State

| Attribute | Current Value |
|-----------|---------------|
| **Storage Provider** | Emergent Object Storage |
| **Base URL** | `https://integrations.emergentagent.com/objstore/api/v1/storage` |
| **Authentication** | EMERGENT_LLM_KEY → storage_key exchange |
| **File Access** | Via backend proxy (`/api/employee-documents/{id}/file`) |
| **File Path Pattern** | `osabea-care/{employee_id}/{document_type}/{filename}` |
| **URLs in DB** | Full Emergent URLs |

### 6.2 Target State (Supabase Storage)

| Attribute | Target Value |
|-----------|---------------|
| **Storage Provider** | Supabase Storage |
| **Bucket Name** | `documents` (private) |
| **Authentication** | Supabase RLS + signed URLs |
| **File Access** | Direct signed URLs or `/storage/v1/object/` |
| **File Path Pattern** | `{employee_id}/{category}/{filename}` |
| **URLs in DB** | Storage paths (not full URLs) |

### 6.3 Migration Strategy

```
Phase 1: Dual-Write
├── Continue using Emergent for new uploads
├── Begin migrating existing files in batches
└── Store both old_file_url and new storage_path

Phase 2: Cutover
├── Switch new uploads to Supabase
├── Update backend to read from Supabase
└── Keep old_file_url as fallback

Phase 3: Cleanup
├── Verify all files accessible via Supabase
├── Delete files from Emergent
└── Remove old_file_url column
```

### 6.4 Migration Script (Pseudocode)

```python
async def migrate_files():
    """Migrate files from Emergent to Supabase Storage"""
    
    # Initialize clients
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all documents with file_url
    documents = await mongo_db.employee_documents.find(
        {"file_url": {"$exists": True, "$ne": None}}
    ).to_list(None)
    
    total = len(documents)
    success = 0
    failed = []
    
    for doc in documents:
        try:
            # 1. Download from Emergent
            old_url = doc["file_url"]
            file_content = await download_from_emergent(old_url)
            
            # 2. Generate new path
            employee_id = doc["employee_id"]
            category = doc.get("category", "other")
            filename = doc.get("original_filename", f"{doc['id']}.bin")
            new_path = f"{employee_id}/{category}/{filename}"
            
            # 3. Upload to Supabase
            result = supabase.storage.from_("documents").upload(
                path=new_path,
                file=file_content,
                file_options={"content-type": detect_mime_type(filename)}
            )
            
            # 4. Update document record
            await mongo_db.employee_documents.update_one(
                {"id": doc["id"]},
                {"$set": {
                    "storage_path": new_path,
                    "old_file_url": old_url,
                    "migration_status": "completed",
                    "migrated_at": datetime.utcnow().isoformat()
                }}
            )
            
            success += 1
            log(f"Migrated {success}/{total}: {doc['id']}")
            
        except Exception as e:
            failed.append({"id": doc["id"], "error": str(e)})
            log(f"Failed: {doc['id']} - {e}")
    
    return {
        "total": total,
        "success": success,
        "failed": len(failed),
        "failed_docs": failed
    }

async def download_from_emergent(url: str) -> bytes:
    """Download file from Emergent storage"""
    storage_key = await init_emergent_storage()
    response = requests.get(
        url,
        headers={"X-Storage-Key": storage_key},
        timeout=120
    )
    response.raise_for_status()
    return response.content
```

### 6.5 Supabase Storage Structure

```
documents/                          # Bucket (private)
├── {employee_uuid_1}/
│   ├── right_to_work/
│   │   ├── passport_2024.pdf
│   │   └── brp_card.jpg
│   ├── dbs/
│   │   └── dbs_certificate.pdf
│   ├── identity/
│   │   └── driving_licence.pdf
│   ├── proof_of_address/
│   │   ├── utility_bill_jan.pdf
│   │   └── bank_statement_feb.pdf
│   ├── training/
│   │   └── safeguarding_cert.pdf
│   ├── verification_proof/           # Check proofs
│   │   ├── rtw_check_screenshot.png
│   │   └── dbs_update_service.pdf
│   └── cv/
│       └── cv_2024.pdf
├── {employee_uuid_2}/
│   └── ...
└── org/                             # Organization documents
    ├── policies/
    └── certificates/
```

### 6.6 RLS Policies for Storage

```sql
-- Allow authenticated users to read their own documents
CREATE POLICY "Users can read own documents"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'documents' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow admins to read all documents
CREATE POLICY "Admins can read all documents"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'documents' AND
  EXISTS (
    SELECT 1 FROM profiles 
    WHERE id = auth.uid() 
    AND role IN ('super_admin', 'admin')
  )
);

-- Allow authenticated users to upload to their folder
CREATE POLICY "Users can upload own documents"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'documents' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow admins to upload anywhere
CREATE POLICY "Admins can upload anywhere"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'documents' AND
  EXISTS (
    SELECT 1 FROM profiles 
    WHERE id = auth.uid() 
    AND role IN ('super_admin', 'admin')
  )
);
```

---

## 7. USER & AUTH MIGRATION PLAN

### 7.1 Current State (MongoDB)

```javascript
// users collection
{
  user_id: "user_d91e02377f78",
  email: "admin@osabea.care",
  password: "$2b$12$...",  // bcrypt hash
  name: "System Admin",
  role: "super_admin",
  branch: null,
  picture: null,
  created_at: "2024-01-01T00:00:00Z"
}
```

### 7.2 Target State (Supabase)

```sql
-- auth.users (Supabase managed)
{
  id: UUID,
  email: "admin@osabea.care",
  encrypted_password: "$2b$12$...",
  created_at: TIMESTAMPTZ,
  ...
}

-- profiles (custom table)
{
  id: UUID REFERENCES auth.users,
  email: "admin@osabea.care",
  name: "System Admin",
  role: "super_admin",
  branch: null,
  picture_url: null,
  created_at: TIMESTAMPTZ
}
```

### 7.3 Migration Strategy

```
Option A: Preserve Passwords (Recommended)
├── Use Supabase's password import feature
├── Users can login with existing passwords
└── No password reset required

Option B: Force Password Reset
├── Create users with random passwords
├── Send password reset emails
└── Simpler but worse UX
```

### 7.4 Migration Script (Option A)

```python
async def migrate_users_to_supabase():
    """Migrate users while preserving password hashes"""
    
    # Get all MongoDB users
    mongo_users = await mongo_db.users.find({}).to_list(None)
    
    results = {
        "total": len(mongo_users),
        "success": 0,
        "failed": []
    }
    
    for user in mongo_users:
        try:
            # 1. Create Supabase auth user with password hash
            # Note: Requires admin API key
            auth_user = await supabase.auth.admin.create_user({
                "email": user["email"],
                "password_hash": user["password"],  # bcrypt hash
                "email_confirm": True  # Skip email verification
            })
            
            new_user_id = auth_user.user.id
            
            # 2. Create profile record
            await supabase.table("profiles").insert({
                "id": new_user_id,
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "branch": user.get("branch"),
                "picture_url": user.get("picture"),
                "created_at": user.get("created_at") or datetime.utcnow().isoformat()
            })
            
            # 3. Store mapping for FK updates
            user_id_map[user["user_id"]] = new_user_id
            
            results["success"] += 1
            
        except Exception as e:
            results["failed"].append({
                "email": user["email"],
                "error": str(e)
            })
    
    return results

# Global mapping for updating foreign keys
user_id_map = {}

def map_user_id(old_id: str) -> Optional[UUID]:
    """Map old MongoDB user_id to new Supabase UUID"""
    if not old_id:
        return None
    return user_id_map.get(old_id)
```

### 7.5 Role Mapping

| MongoDB Role | Supabase Profile Role | RLS Access |
|--------------|----------------------|------------|
| `super_admin` | `super_admin` | Full access |
| `admin` | `admin` | Full access (except system) |
| `branch_manager` | `branch_manager` | Branch-filtered |
| `employee` | `employee` | Self only |
| `auditor` | `auditor` | Read-only |

### 7.6 RLS Policies for Profiles

```sql
-- Users can read their own profile
CREATE POLICY "Users can read own profile"
ON profiles FOR SELECT
USING (id = auth.uid());

-- Admins can read all profiles
CREATE POLICY "Admins can read all profiles"
ON profiles FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM profiles 
    WHERE id = auth.uid() 
    AND role IN ('super_admin', 'admin')
  )
);

-- Users can update their own profile (limited fields)
CREATE POLICY "Users can update own profile"
ON profiles FOR UPDATE
USING (id = auth.uid())
WITH CHECK (
  -- Cannot change role
  role = (SELECT role FROM profiles WHERE id = auth.uid())
);

-- Only super_admin can create profiles
CREATE POLICY "Super admin can create profiles"
ON profiles FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM profiles 
    WHERE id = auth.uid() 
    AND role = 'super_admin'
  )
);
```

### 7.7 Employee-User Linkage

Some employees may also be users (for self-service):

```sql
-- Add user_id to employees table for self-service portal
ALTER TABLE employees ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Link existing employees to users by email
UPDATE employees e
SET user_id = p.id
FROM profiles p
WHERE e.email = p.email;
```

---

## 8. DATA REVIEW FLAGS

### 8.1 Records Requiring Manual Review

| Table | Condition | Flag Field | Reason |
|-------|-----------|------------|--------|
| `employees` | `status` unclear mapping | `migration_reviewed` | Status normalization |
| `employees` | `role` not in standard list | `migration_reviewed` | Role standardization |
| `documents` | `category` cannot be determined | `migration_reviewed` | Category assignment |
| `documents` | `expiry_date` in past | `migration_reviewed` | Expired document handling |
| `documents` | `evidence_files` array has multiple items | `migration_reviewed` | Array normalization |
| `employee_references` | `status` derived from multiple fields | `migration_reviewed` | Status verification |
| `employment_gaps` | From embedded array (not collection) | `migration_reviewed` | Data quality |
| `training_records` | `status` = 'expired' | `migration_reviewed` | Renewal needed |
| `form_submissions` | `data` schema doesn't match template | `migration_reviewed` | Form compatibility |

### 8.2 Migration Review Columns

Add to all migrated tables:
```sql
-- Standard migration tracking columns
mongo_id TEXT,                    -- Original MongoDB _id or id
migration_reviewed BOOLEAN DEFAULT FALSE,
migration_notes TEXT,
migrated_at TIMESTAMPTZ DEFAULT now()
```

### 8.3 Review Dashboard Query

```sql
-- Migration review dashboard
SELECT 
  'employees' as table_name,
  COUNT(*) FILTER (WHERE NOT migration_reviewed) as pending_review,
  COUNT(*) as total
FROM employees
WHERE mongo_id IS NOT NULL

UNION ALL

SELECT 
  'documents' as table_name,
  COUNT(*) FILTER (WHERE NOT migration_reviewed) as pending_review,
  COUNT(*) as total
FROM documents
WHERE mongo_id IS NOT NULL

UNION ALL

SELECT 
  'employee_references' as table_name,
  COUNT(*) FILTER (WHERE NOT migration_reviewed) as pending_review,
  COUNT(*) as total
FROM employee_references

-- ... repeat for other tables
ORDER BY pending_review DESC;
```

---

## 9. MIGRATION PHASES

### Phase 0: Pre-Migration Preparation

**Duration:** 1-2 days

| Step | Task | Validation |
|------|------|------------|
| 0.1 | Create Supabase project | Project accessible |
| 0.2 | Run schema creation SQL | All tables created |
| 0.3 | Set up Supabase Storage bucket | Bucket accessible |
| 0.4 | Configure RLS policies | Policies applied |
| 0.5 | Data cleanup (see Section 10) | Clean data export |
| 0.6 | Create ID mapping tables | Mapping tables ready |
| 0.7 | Backup MongoDB | Backup verified |

### Phase 1: Core Entities

**Duration:** 1 day  
**Order:** Must complete before other phases

| Step | Source | Target | Dependencies |
|------|--------|--------|--------------|
| 1.1 | `users` | `auth.users` + `profiles` | None |
| 1.2 | `document_types` | `document_types` | None |
| 1.3 | `training_catalogue` | `training_catalogue` | None |
| 1.4 | `employees` (base fields) | `employees` | 1.1 (for FKs) |

**Validation:**
- [ ] All users can login with existing passwords
- [ ] Employee count matches
- [ ] All employee IDs mapped

### Phase 2: References & Employment History

**Duration:** 1 day  
**Order:** After Phase 1

| Step | Source | Target | Dependencies |
|------|--------|--------|--------------|
| 2.1 | `employees.reference_1_*` | `employee_references` | 1.4 |
| 2.2 | `employees.reference_2_*` | `employee_references` | 1.4 |
| 2.3 | `employees.employment_history` | `employment_history` | 1.4 |
| 2.4 | `employees.employment_gaps` + `employment_gaps` | `employment_gaps` | 2.3 |

**Validation:**
- [ ] 2 references per employee (where declared)
- [ ] Employment history preserves order
- [ ] Gaps linked to preceding/following jobs

### Phase 3: Documents & Files

**Duration:** 2-3 days (file transfer is slow)  
**Order:** After Phase 1

| Step | Source | Target | Dependencies |
|------|--------|--------|--------------|
| 3.1 | `employee_documents` (metadata) | `documents` | 1.4 |
| 3.2 | Files from Emergent | Supabase Storage | 3.1 |
| 3.3 | Update `documents.storage_path` | - | 3.2 |
| 3.4 | Normalize `evidence_files[]` arrays | Additional `documents` rows | 3.1 |

**Validation:**
- [ ] All files accessible via Supabase
- [ ] Document count matches
- [ ] File sizes match (checksum if possible)

### Phase 4: Verification Checks

**Duration:** 1 day  
**Order:** After Phase 3 (needs document IDs)

| Step | Source | Target | Dependencies |
|------|--------|--------|--------------|
| 4.1 | `rtw_checks` | `rtw_checks` | 3.1 (proof_document_id) |
| 4.2 | `dbs_checks` | `dbs_checks` | 3.1 |
| 4.3 | `identity_verifications` | `identity_checks` + junction | 3.1 |
| 4.4 | `address_verifications` | `address_checks` + junction | 3.1 |

**Validation:**
- [ ] Check counts match
- [ ] `is_current` flags correct
- [ ] Proof documents linked

### Phase 5: Training & Forms

**Duration:** 1 day  
**Order:** After Phase 3

| Step | Source | Target | Dependencies |
|------|--------|--------|--------------|
| 5.1 | `training_records` | `training_records` | 1.3, 1.4, 3.1 |
| 5.2 | `form_submissions` | `form_submissions` + `form_templates` | 1.4 |
| 5.3 | `agreement_acknowledgements` | `agreement_acknowledgements` | 1.4, 3.1 |

**Validation:**
- [ ] Training record counts match
- [ ] Form data JSONB valid
- [ ] Agreement statuses correct

### Phase 6: Organization Data

**Duration:** 0.5 day  
**Order:** Can run parallel to Phase 3-5

| Step | Source | Target | Dependencies |
|------|--------|--------|--------------|
| 6.1 | `org_policies` | `org_policies` | 1.1 |
| 6.2 | Policy files | Supabase Storage | 6.1 |
| 6.3 | `insurance_docs` → | `org_certificates` | 1.1 |
| 6.4 | `policy_assignments` | `policy_assignments` | 6.1, 1.4 |

### Phase 7: Supporting Data

**Duration:** 0.5 day  
**Order:** After Phase 5

| Step | Source | Target | Dependencies |
|------|--------|--------|--------------|
| 7.1 | `recurring_compliance` | `recurring_items` | 1.4 |
| 7.2 | `scheduled_bulk_requests` | `scheduled_requests` | 1.1 |
| 7.3 | `audit_logs` + `audit_log` | `audit_log` | All |

### Phase 8: Validation & Cutover

**Duration:** 1-2 days

| Step | Task | Success Criteria |
|------|------|------------------|
| 8.1 | Run full validation queries | All counts match |
| 8.2 | Test compliance file API | Same response structure |
| 8.3 | Test all frontend pages | No errors, data displays |
| 8.4 | Run dual-write for 24 hours | Data consistency |
| 8.5 | Switch traffic to Supabase | Production traffic |
| 8.6 | Monitor for 48 hours | No errors |
| 8.7 | Decommission MongoDB | Backup retained |

---

## 10. PRE-MIGRATION DATA CLEANUP

### 10.1 Required Cleanup Tasks

| # | Task | Query/Action | Priority |
|---|------|--------------|----------|
| 1 | **Remove duplicate employees** | Find by email, keep most recent | HIGH |
| 2 | **Normalize status values** | Map variants to ENUM values | HIGH |
| 3 | **Fix invalid dates** | Parse and correct date strings | HIGH |
| 4 | **Remove orphaned documents** | Delete docs without valid employee_id | MEDIUM |
| 5 | **Consolidate duplicate documents** | Merge evidence_files arrays | MEDIUM |
| 6 | **Standardize role names** | Map to standard values | MEDIUM |
| 7 | **Clean empty reference fields** | Remove references with no referee name | LOW |
| 8 | **Fix superseded chains** | Ensure superseded_by links are valid | LOW |

### 10.2 Duplicate Employees

```javascript
// Find duplicate emails
db.employees.aggregate([
  { $group: { _id: "$email", count: { $sum: 1 }, docs: { $push: "$id" } } },
  { $match: { count: { $gt: 1 } } }
])

// Resolution: Keep the one with latest updated_at, merge data if needed
```

### 10.3 Status Normalization

```javascript
// Find non-standard statuses
db.employees.distinct("status")

// Expected: new, screening, interview, compliance_review, onboarding, active, inactive, archived
// Map any variants:
// "Onboarding" → "onboarding"
// "In Progress" → "screening"
// null → "new"
```

### 10.4 Date Validation

```python
def validate_and_fix_dates(collection_name: str, date_fields: list):
    """Validate and fix date fields"""
    invalid_dates = []
    
    for doc in db[collection_name].find():
        for field in date_fields:
            value = doc.get(field)
            if value:
                try:
                    # Try parsing
                    if isinstance(value, str):
                        datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    invalid_dates.append({
                        "id": doc["id"],
                        "field": field,
                        "value": value
                    })
    
    return invalid_dates

# Run for each collection
validate_and_fix_dates("employees", ["start_date", "created_at", "updated_at"])
validate_and_fix_dates("employee_documents", ["expiry_date", "issue_date", "uploaded_at"])
```

### 10.5 Orphaned Documents

```javascript
// Find documents without valid employee
const validEmployeeIds = db.employees.distinct("id");

db.employee_documents.find({
  employee_id: { $nin: validEmployeeIds }
}).count()

// Action: Delete or flag for review
```

### 10.6 Role Standardization

```javascript
// Find all unique roles
db.employees.distinct("role")

// Standard roles: healthcare_assistant, nurse, senior_carer, support_worker
// Map variants:
const roleMap = {
  "HCA": "healthcare_assistant",
  "Healthcare Assistant": "healthcare_assistant",
  "Carer": "healthcare_assistant",
  "RN": "nurse",
  "Registered Nurse": "nurse",
  "Senior Carer": "senior_carer",
  "Support Worker": "support_worker"
};
```

### 10.7 Cleanup Validation Report

Generate before migration:
```python
def generate_cleanup_report():
    return {
        "employees": {
            "total": db.employees.count_documents({}),
            "duplicates": count_duplicate_emails(),
            "invalid_status": count_invalid_status(),
            "missing_email": db.employees.count_documents({"email": None})
        },
        "documents": {
            "total": db.employee_documents.count_documents({}),
            "orphaned": count_orphaned_documents(),
            "no_file_url": db.employee_documents.count_documents({"file_url": None}),
            "invalid_dates": count_invalid_dates()
        },
        "checks": {
            "rtw_total": db.rtw_checks.count_documents({}),
            "dbs_total": db.dbs_checks.count_documents({}),
            "orphaned_rtw": count_orphaned_checks("rtw_checks"),
            "orphaned_dbs": count_orphaned_checks("dbs_checks")
        }
    }
```

---

## APPENDIX A: ID MAPPING TABLES

During migration, maintain mapping tables:

```sql
-- Temporary mapping tables for migration
CREATE TABLE migration_user_map (
  old_id TEXT PRIMARY KEY,
  new_id UUID NOT NULL
);

CREATE TABLE migration_employee_map (
  old_id TEXT PRIMARY KEY,
  new_id UUID NOT NULL
);

CREATE TABLE migration_document_map (
  old_id TEXT PRIMARY KEY,
  new_id UUID NOT NULL
);

-- Use in migration scripts
INSERT INTO employees (id, ...)
SELECT 
  gen_random_uuid(),
  ...
FROM mongo_export;

-- Then populate mapping
INSERT INTO migration_employee_map (old_id, new_id)
SELECT mongo_id, id FROM employees WHERE mongo_id IS NOT NULL;
```

---

## APPENDIX B: MIGRATION SCRIPT TEMPLATE

```python
"""
Supabase Migration Script Template
DO NOT RUN UNTIL APPROVED
"""

import asyncio
from supabase import create_client
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
from uuid import uuid4

# Configuration
MONGO_URL = os.environ.get("MONGO_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # Service key for admin operations

# Initialize clients
mongo_client = AsyncIOMotorClient(MONGO_URL)
mongo_db = mongo_client["test_database"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Mapping dictionaries
user_id_map = {}
employee_id_map = {}
document_id_map = {}

async def main():
    print("Starting migration...")
    print("=" * 50)
    
    # Phase 1
    print("\nPhase 1: Core Entities")
    await migrate_users()
    await migrate_employees()
    
    # Phase 2
    print("\nPhase 2: References & Employment")
    await extract_references()
    await extract_employment_history()
    await normalize_employment_gaps()
    
    # Phase 3
    print("\nPhase 3: Documents")
    await migrate_documents()
    await migrate_files()
    
    # Phase 4
    print("\nPhase 4: Verification Checks")
    await migrate_rtw_checks()
    await migrate_dbs_checks()
    await migrate_identity_checks()
    await migrate_address_checks()
    
    # ... continue for other phases
    
    print("\n" + "=" * 50)
    print("Migration complete!")
    
    # Generate report
    await generate_migration_report()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## SUMMARY

This blueprint provides a complete migration plan from MongoDB to Supabase:

1. **44 MongoDB collections** → **~25 Postgres tables**
2. **Embedded references** → **Normalized `employee_references` table**
3. **Embedded employment gaps** → **Normalized `employment_gaps` table**
4. **Dual-row model preserved** with explicit `documents` vs `*_checks` separation
5. **Files migrate** from Emergent to Supabase Storage
6. **Users migrate** to Supabase Auth with password preservation
7. **9 migration phases** with clear dependencies
8. **Data cleanup** required before migration

**DO NOT IMPLEMENT UNTIL:**
- [ ] Blueprint reviewed and approved
- [ ] All cleanup tasks completed
- [ ] Test migration run on data copy
- [ ] Rollback plan confirmed
