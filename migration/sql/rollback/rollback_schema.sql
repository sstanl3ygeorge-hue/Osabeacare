-- ============================================================
-- ROLLBACK SCHEMA
-- Drops all migration tables in correct order
-- ============================================================

-- Drop check junction tables first
DROP TABLE IF EXISTS identity_check_documents CASCADE;
DROP TABLE IF EXISTS address_check_documents CASCADE;

-- Drop check tables
DROP TABLE IF EXISTS rtw_checks CASCADE;
DROP TABLE IF EXISTS dbs_checks CASCADE;
DROP TABLE IF EXISTS identity_checks CASCADE;
DROP TABLE IF EXISTS address_checks CASCADE;

-- Drop documents
DROP TABLE IF EXISTS documents CASCADE;

-- Drop employee extensions
DROP TABLE IF EXISTS employment_gaps CASCADE;
DROP TABLE IF EXISTS employment_history CASCADE;
DROP TABLE IF EXISTS employee_references CASCADE;

-- Drop employees
DROP TABLE IF EXISTS employees CASCADE;

-- Drop profiles
DROP TABLE IF EXISTS profiles CASCADE;

-- Drop migration tracking
DROP TABLE IF EXISTS migration_state CASCADE;
DROP TABLE IF EXISTS migration_document_map CASCADE;
DROP TABLE IF EXISTS migration_employee_map CASCADE;
DROP TABLE IF EXISTS migration_user_map CASCADE;

-- Drop ENUMs (optional - uncomment if needed)
-- DROP TYPE IF EXISTS agreement_status CASCADE;
-- DROP TYPE IF EXISTS form_status CASCADE;
-- DROP TYPE IF EXISTS gap_status CASCADE;
-- DROP TYPE IF EXISTS reference_status CASCADE;
-- DROP TYPE IF EXISTS check_method CASCADE;
-- DROP TYPE IF EXISTS verification_outcome CASCADE;
-- DROP TYPE IF EXISTS document_status CASCADE;
-- DROP TYPE IF EXISTS document_category CASCADE;
-- DROP TYPE IF EXISTS person_status CASCADE;
-- DROP TYPE IF EXISTS user_role CASCADE;
