-- ============================================================
-- SUPABASE MIGRATION SCHEMA
-- Phase 0: Create all types, tables, indexes
-- Idempotent: Uses IF NOT EXISTS / CREATE OR REPLACE
-- ============================================================

-- ============================================================
-- ENUM TYPES
-- ============================================================

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM (
        'super_admin', 'admin', 'branch_manager', 'employee', 'auditor'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE person_status AS ENUM (
        'new', 'screening', 'interview', 'compliance_review',
        'onboarding', 'active', 'inactive', 'archived'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE document_category AS ENUM (
        'right_to_work', 'dbs', 'identity', 'proof_of_address',
        'training', 'cv', 'reference', 'agreement', 'verification_proof',
        'form_attachment', 'other'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE document_status AS ENUM (
        'uploaded', 'awaiting_review', 'verified', 'rejected', 'expired', 'superseded'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE verification_outcome AS ENUM (
        'awaiting_review', 'verified', 'failed', 'follow_up_required', 'rejected'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE check_method AS ENUM (
        'share_code_online_check', 'manual_passport_check', 'manual_document_review',
        'update_service_check', 'manual_certificate_review', 'in_person', 'video_call'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE reference_status AS ENUM (
        'not_declared', 'declared', 'request_sent', 'request_viewed',
        'response_received', 'verified', 'rejected'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE gap_status AS ENUM (
        'detected', 'explained', 'verified', 'rejected', 'more_info_needed'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE form_status AS ENUM (
        'not_started', 'draft', 'submitted', 'awaiting_review', 'verified', 'rejected'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE agreement_status AS ENUM (
        'not_started', 'pending', 'submitted', 'verified', 'rejected'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- MIGRATION TRACKING TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS migration_user_map (
    old_id TEXT PRIMARY KEY,
    new_id UUID NOT NULL,
    migrated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS migration_employee_map (
    old_id TEXT PRIMARY KEY,
    new_id UUID NOT NULL,
    migrated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS migration_document_map (
    old_id TEXT PRIMARY KEY,
    new_id UUID NOT NULL,
    migrated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS migration_state (
    phase TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_records INTEGER DEFAULT 0,
    migrated_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    last_processed_id TEXT,
    error_log JSONB DEFAULT '[]'::jsonb
);

-- ============================================================
-- PROFILES TABLE (extends Supabase auth.users)
-- ============================================================

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role user_role NOT NULL DEFAULT 'employee',
    branch TEXT,
    picture_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT,
    migration_reviewed BOOLEAN DEFAULT FALSE
);

-- ============================================================
-- EMPLOYEES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_code TEXT UNIQUE,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    last_name TEXT NOT NULL,
    preferred_name TEXT,
    date_of_birth DATE,
    ni_number TEXT,
    email TEXT NOT NULL,
    phone TEXT,
    phone_secondary TEXT,
    address_line_1 TEXT,
    address_line_2 TEXT,
    city TEXT,
    county TEXT,
    postcode TEXT,
    country TEXT DEFAULT 'United Kingdom',
    role TEXT,
    status person_status NOT NULL DEFAULT 'new',
    start_date DATE,
    manager_id UUID REFERENCES profiles(id),
    manager_name TEXT,
    branch TEXT,
    profile_photo_url TEXT,
    driver_status TEXT,
    has_driving_licence BOOLEAN DEFAULT FALSE,
    has_own_vehicle BOOLEAN DEFAULT FALSE,
    criminal_offence_declared BOOLEAN,
    dbs_update_service_consent BOOLEAN,
    health_issue_declared BOOLEAN,
    professional_misconduct_declared BOOLEAN,
    working_time_opt_out BOOLEAN,
    next_of_kin_name TEXT,
    next_of_kin_relationship TEXT,
    next_of_kin_phone TEXT,
    next_of_kin_address TEXT,
    next_of_kin_city TEXT,
    next_of_kin_postcode TEXT,
    recruitment_approved BOOLEAN DEFAULT FALSE,
    recruitment_approved_at TIMESTAMPTZ,
    recruitment_approved_by UUID REFERENCES profiles(id),
    cv_document_id UUID,
    cv_extracted_roles JSONB,
    name_mismatch_status TEXT,
    name_mismatch_review JSONB,
    completion_percentage INTEGER DEFAULT 0,
    compliance_score INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT UNIQUE,
    migration_reviewed BOOLEAN DEFAULT FALSE,
    migration_notes TEXT
);

-- ============================================================
-- EMPLOYEE REFERENCES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS employee_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    reference_number INTEGER NOT NULL CHECK (reference_number IN (1, 2, 3)),
    referee_name TEXT NOT NULL,
    referee_company TEXT,
    referee_email TEXT,
    referee_phone TEXT,
    referee_job_title TEXT,
    employment_start_date DATE,
    employment_end_date DATE,
    from_cv BOOLEAN DEFAULT FALSE,
    cv_matched BOOLEAN,
    mismatch_detected BOOLEAN DEFAULT FALSE,
    mismatch_notes TEXT,
    override_reason TEXT,
    override_at TIMESTAMPTZ,
    override_by UUID REFERENCES profiles(id),
    status reference_status NOT NULL DEFAULT 'not_declared',
    request_sent_at TIMESTAMPTZ,
    request_token TEXT UNIQUE,
    request_viewed_at TIMESTAMPTZ,
    last_reminder_at TIMESTAMPTZ,
    resend_count INTEGER DEFAULT 0,
    response_received_at TIMESTAMPTZ,
    response_source TEXT,
    response_data JSONB,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    verified_by_name TEXT,
    rejected BOOLEAN DEFAULT FALSE,
    rejected_at TIMESTAMPTZ,
    rejected_by UUID REFERENCES profiles(id),
    rejection_reason TEXT,
    replacement_requested BOOLEAN DEFAULT FALSE,
    replacement_requested_at TIMESTAMPTZ,
    replacement_requested_by UUID REFERENCES profiles(id),
    replacement_reason TEXT,
    change_history JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(employee_id, reference_number)
);

-- ============================================================
-- EMPLOYMENT HISTORY TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS employment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    job_title TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    source TEXT,
    extraction_confidence NUMERIC(3,2),
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    sort_order INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- EMPLOYMENT GAPS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS employment_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    gap_start_date DATE NOT NULL,
    gap_end_date DATE NOT NULL,
    gap_months NUMERIC(4,1),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    preceding_job_id UUID REFERENCES employment_history(id),
    following_job_id UUID REFERENCES employment_history(id),
    status gap_status NOT NULL DEFAULT 'detected',
    explanation TEXT,
    explanation_submitted_at TIMESTAMPTZ,
    explanation_submitted_by UUID REFERENCES profiles(id),
    evidence_document_id UUID,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    verification_notes TEXT,
    rejected BOOLEAN DEFAULT FALSE,
    rejected_at TIMESTAMPTZ,
    rejected_by UUID REFERENCES profiles(id),
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT
);

-- ============================================================
-- DOCUMENTS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    category document_category NOT NULL,
    document_type_id UUID,
    document_type_name TEXT,
    requirement_id TEXT,
    requirement_name TEXT,
    document_label TEXT,
    storage_path TEXT,
    file_url TEXT,
    old_file_url TEXT,
    original_filename TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    document_number TEXT,
    issue_date DATE,
    expiry_date DATE,
    permission_end_date DATE,
    status document_status NOT NULL DEFAULT 'uploaded',
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    verified_by_name TEXT,
    verification_notes TEXT,
    extraction_data JSONB,
    extraction_reviewed BOOLEAN DEFAULT FALSE,
    extraction_reviewed_at TIMESTAMPTZ,
    extraction_reviewed_by UUID REFERENCES profiles(id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    uploaded_by UUID REFERENCES profiles(id),
    source_type TEXT,
    superseded_by UUID REFERENCES documents(id),
    superseded_at TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT UNIQUE,
    migration_reviewed BOOLEAN DEFAULT FALSE,
    file_migration_status TEXT DEFAULT 'pending',
    file_migration_error TEXT
);

-- ============================================================
-- VERIFICATION CHECK TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS rtw_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    method check_method NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    checked_by UUID REFERENCES profiles(id),
    checked_by_name TEXT,
    outcome verification_outcome NOT NULL DEFAULT 'awaiting_review',
    source_status_type TEXT,
    follow_up_due_at DATE,
    proof_document_id UUID REFERENCES documents(id),
    notes TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    superseded_at TIMESTAMPTZ,
    superseded_by UUID REFERENCES rtw_checks(id),
    record_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES profiles(id),
    mongo_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS dbs_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    method check_method NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    checked_by UUID REFERENCES profiles(id),
    checked_by_name TEXT,
    outcome verification_outcome NOT NULL DEFAULT 'awaiting_review',
    certificate_number TEXT,
    review_due_at DATE,
    proof_document_id UUID REFERENCES documents(id),
    notes TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    superseded_at TIMESTAMPTZ,
    superseded_by UUID REFERENCES dbs_checks(id),
    record_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES profiles(id),
    mongo_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS identity_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    method check_method NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    checked_by UUID REFERENCES profiles(id),
    checked_by_name TEXT,
    outcome verification_outcome NOT NULL DEFAULT 'awaiting_review',
    proof_document_id UUID REFERENCES documents(id),
    notes TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    superseded_at TIMESTAMPTZ,
    superseded_by UUID REFERENCES identity_checks(id),
    record_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES profiles(id),
    mongo_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS identity_check_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_check_id UUID NOT NULL REFERENCES identity_checks(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(identity_check_id, document_id)
);

CREATE TABLE IF NOT EXISTS address_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    verified_at TIMESTAMPTZ NOT NULL,
    verified_by UUID REFERENCES profiles(id),
    verified_by_name TEXT,
    verified_count INTEGER NOT NULL DEFAULT 0,
    minimum_required INTEGER NOT NULL DEFAULT 2,
    meets_requirement BOOLEAN DEFAULT FALSE,
    recency_policy_passed BOOLEAN,
    notes TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    superseded_at TIMESTAMPTZ,
    superseded_by UUID REFERENCES address_checks(id),
    record_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES profiles(id),
    mongo_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS address_check_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address_check_id UUID NOT NULL REFERENCES address_checks(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_date DATE,
    is_valid BOOLEAN,
    UNIQUE(address_check_id, document_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role);
CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email);
CREATE INDEX IF NOT EXISTS idx_employees_mongo_id ON employees(mongo_id);
CREATE INDEX IF NOT EXISTS idx_employees_recruitment ON employees(recruitment_approved);

CREATE INDEX IF NOT EXISTS idx_documents_employee_id ON documents(employee_id);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_is_current ON documents(is_current);
CREATE INDEX IF NOT EXISTS idx_documents_mongo_id ON documents(mongo_id);

CREATE INDEX IF NOT EXISTS idx_rtw_checks_employee ON rtw_checks(employee_id);
CREATE INDEX IF NOT EXISTS idx_rtw_checks_current ON rtw_checks(is_current);
CREATE INDEX IF NOT EXISTS idx_dbs_checks_employee ON dbs_checks(employee_id);
CREATE INDEX IF NOT EXISTS idx_dbs_checks_current ON dbs_checks(is_current);
CREATE INDEX IF NOT EXISTS idx_identity_checks_employee ON identity_checks(employee_id);
CREATE INDEX IF NOT EXISTS idx_address_checks_employee ON address_checks(employee_id);

CREATE INDEX IF NOT EXISTS idx_references_employee ON employee_references(employee_id);
CREATE INDEX IF NOT EXISTS idx_employment_history_employee ON employment_history(employee_id);
CREATE INDEX IF NOT EXISTS idx_employment_gaps_employee ON employment_gaps(employee_id);

-- ============================================================
-- TRAINING TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS training_catalogue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    is_mandatory BOOLEAN DEFAULT FALSE,
    is_blocker BOOLEAN DEFAULT FALSE,
    evidence_required BOOLEAN DEFAULT TRUE,
    validity_months INTEGER,
    applicable_roles TEXT[],
    sort_order INTEGER,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS training_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    training_id UUID REFERENCES training_catalogue(id),
    completion_date DATE,
    expiry_date DATE,
    completion_method TEXT,
    certificate_document_id UUID REFERENCES documents(id),
    status TEXT NOT NULL DEFAULT 'missing' CHECK (status IN ('missing', 'current', 'expiring', 'expired')),
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    verified_by_name TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    superseded_at TIMESTAMPTZ,
    superseded_by UUID REFERENCES training_records(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT UNIQUE
);

-- ============================================================
-- FORMS TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS form_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_type TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    schema JSONB DEFAULT '{}',
    is_blocker BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    form_template_id UUID REFERENCES form_templates(id),
    form_type TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    status form_status NOT NULL DEFAULT 'not_started',
    submitted_at TIMESTAMPTZ,
    submitted_by UUID REFERENCES profiles(id),
    submitted_by_name TEXT,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    verified_by_name TEXT,
    verification_notes TEXT,
    rejected BOOLEAN DEFAULT FALSE,
    rejected_at TIMESTAMPTZ,
    rejected_by UUID REFERENCES profiles(id),
    rejection_reason TEXT,
    version INTEGER DEFAULT 1,
    is_current BOOLEAN DEFAULT TRUE,
    superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT UNIQUE
);

-- ============================================================
-- AGREEMENTS TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS agreement_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agreement_type TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_blocker BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agreement_acknowledgements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    agreement_template_id UUID REFERENCES agreement_templates(id),
    agreement_type TEXT NOT NULL,
    completion_mode TEXT,
    completed_at TIMESTAMPTZ,
    completed_by UUID REFERENCES profiles(id),
    assisted_by UUID REFERENCES profiles(id),
    version_acknowledged TEXT,
    call_note TEXT,
    signed_document_id UUID REFERENCES documents(id),
    status agreement_status NOT NULL DEFAULT 'not_started',
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    verification_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT UNIQUE
);

-- ============================================================
-- ORGANIZATION TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS org_policies (
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
    mongo_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS org_certificates (
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
    mongo_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS policy_assignments (
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
-- AUDIT LOGS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    employee_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    user_email TEXT,
    user_name TEXT,
    details JSONB,
    old_values JSONB,
    new_values JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mongo_id TEXT UNIQUE
);

-- ============================================================
-- ADDITIONAL INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_training_records_employee ON training_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_training_records_training ON training_records(training_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_employee ON form_submissions(employee_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_type ON form_submissions(form_type);
CREATE INDEX IF NOT EXISTS idx_agreement_acks_employee ON agreement_acknowledgements(employee_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_employee ON audit_logs(employee_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);

-- ============================================================
-- INSERT INITIAL MIGRATION STATE
-- ============================================================

INSERT INTO migration_state (phase, status) VALUES
    ('phase_0_schema', 'pending'),
    ('phase_1_users', 'pending'),
    ('phase_2_employees', 'pending'),
    ('phase_3_references', 'pending'),
    ('phase_4_documents', 'pending'),
    ('phase_5_files', 'pending'),
    ('phase_6_checks', 'pending'),
    ('phase_7_training', 'pending'),
    ('phase_8_forms', 'pending'),
    ('phase_9_org', 'pending'),
    ('phase_10_audit_logs', 'pending')
ON CONFLICT (phase) DO NOTHING;
