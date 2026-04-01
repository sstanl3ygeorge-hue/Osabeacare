-- ============================================================
-- VALIDATION QUERIES FOR ALL PHASES
-- Run after each phase to verify migration success
-- ============================================================

-- ============================================================
-- PHASE 1: Users / Profiles
-- ============================================================

-- Count comparison
SELECT 'phase_1_users' as phase,
    (SELECT COUNT(*) FROM profiles) as postgres_count,
    (SELECT COUNT(*) FROM migration_user_map) as mapped_count;

-- Check all roles are valid
SELECT role, COUNT(*) as count
FROM profiles
GROUP BY role
ORDER BY count DESC;

-- Check for profiles without mappings (should be 0 after migration)
SELECT COUNT(*) as unmapped_profiles
FROM profiles p
LEFT JOIN migration_user_map m ON p.id::text = m.new_id::text
WHERE m.old_id IS NULL AND p.mongo_id IS NOT NULL;

-- ============================================================
-- PHASE 2: Employees
-- ============================================================

-- Count comparison
SELECT 'phase_2_employees' as phase,
    (SELECT COUNT(*) FROM employees) as postgres_count,
    (SELECT COUNT(*) FROM migration_employee_map) as mapped_count;

-- Status distribution
SELECT status, COUNT(*) as count
FROM employees
GROUP BY status
ORDER BY count DESC;

-- Check for duplicate emails
SELECT email, COUNT(*) as count
FROM employees
GROUP BY email
HAVING COUNT(*) > 1;

-- Check for employees without mappings
SELECT COUNT(*) as unmapped_employees
FROM employees e
LEFT JOIN migration_employee_map m ON e.id::text = m.new_id::text
WHERE m.old_id IS NULL AND e.mongo_id IS NOT NULL;

-- Verify FK references
SELECT 'manager_id FK' as check_name,
    COUNT(*) as invalid_count
FROM employees e
LEFT JOIN profiles p ON e.manager_id = p.id
WHERE e.manager_id IS NOT NULL AND p.id IS NULL;

-- ============================================================
-- PHASE 3: References & Employment
-- ============================================================

-- Reference counts
SELECT 'phase_3_references' as phase,
    (SELECT COUNT(*) FROM employee_references) as references_count,
    (SELECT COUNT(DISTINCT employee_id) FROM employee_references) as employees_with_refs;

-- Reference number distribution (should only be 1, 2, or 3)
SELECT reference_number, COUNT(*) as count
FROM employee_references
GROUP BY reference_number
ORDER BY reference_number;

-- Check for duplicate references
SELECT employee_id, reference_number, COUNT(*) as count
FROM employee_references
GROUP BY employee_id, reference_number
HAVING COUNT(*) > 1;

-- Employment history counts
SELECT 'employment_history' as table_name,
    COUNT(*) as total,
    COUNT(DISTINCT employee_id) as employees;

-- Employment gaps counts
SELECT 'employment_gaps' as table_name,
    COUNT(*) as total,
    COUNT(DISTINCT employee_id) as employees;

-- Gap date validation (start < end)
SELECT id, gap_start_date, gap_end_date
FROM employment_gaps
WHERE gap_start_date >= gap_end_date;

-- ============================================================
-- PHASE 4: Documents
-- ============================================================

-- Count comparison
SELECT 'phase_4_documents' as phase,
    (SELECT COUNT(*) FROM documents) as postgres_count,
    (SELECT COUNT(*) FROM migration_document_map) as mapped_count;

-- Category distribution
SELECT category, COUNT(*) as count
FROM documents
GROUP BY category
ORDER BY count DESC;

-- Status distribution
SELECT status, COUNT(*) as count
FROM documents
GROUP BY status
ORDER BY count DESC;

-- Check for orphaned documents (no valid employee)
SELECT COUNT(*) as orphaned_documents
FROM documents d
LEFT JOIN employees e ON d.employee_id = e.id
WHERE e.id IS NULL;

-- Check for documents with old_file_url (need file migration)
SELECT COUNT(*) as needs_file_migration
FROM documents
WHERE old_file_url IS NOT NULL AND storage_path IS NULL;

-- ============================================================
-- PHASE 5: Files
-- ============================================================

-- File migration status
SELECT file_migration_status, COUNT(*) as count
FROM documents
GROUP BY file_migration_status
ORDER BY count DESC;

-- Calculate completion percentage
SELECT 
    COUNT(*) as total,
    COUNT(storage_path) as migrated,
    ROUND(COUNT(storage_path)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as percent_complete
FROM documents
WHERE old_file_url IS NOT NULL;

-- Files with errors
SELECT id, original_filename, file_migration_error
FROM documents
WHERE file_migration_status = 'error'
LIMIT 20;

-- ============================================================
-- PHASE 6: Verification Checks
-- ============================================================

-- RTW checks
SELECT 'rtw_checks' as table_name,
    COUNT(*) as total,
    COUNT(DISTINCT employee_id) as employees,
    SUM(CASE WHEN is_current THEN 1 ELSE 0 END) as current_checks;

-- DBS checks
SELECT 'dbs_checks' as table_name,
    COUNT(*) as total,
    COUNT(DISTINCT employee_id) as employees,
    SUM(CASE WHEN is_current THEN 1 ELSE 0 END) as current_checks;

-- Identity checks
SELECT 'identity_checks' as table_name,
    COUNT(*) as total,
    COUNT(DISTINCT employee_id) as employees,
    SUM(CASE WHEN is_current THEN 1 ELSE 0 END) as current_checks;

-- Address checks
SELECT 'address_checks' as table_name,
    COUNT(*) as total,
    COUNT(DISTINCT employee_id) as employees,
    SUM(CASE WHEN is_current THEN 1 ELSE 0 END) as current_checks;

-- Junction table counts
SELECT 
    'identity_check_documents' as table_name,
    COUNT(*) as rows
FROM identity_check_documents
UNION ALL
SELECT 
    'address_check_documents',
    COUNT(*)
FROM address_check_documents;

-- Check is_current uniqueness (only one current per employee per check type)
SELECT employee_id, COUNT(*) as current_count
FROM rtw_checks
WHERE is_current = true
GROUP BY employee_id
HAVING COUNT(*) > 1;

-- Verify proof_document_id references
SELECT 'rtw_checks invalid proof' as check_name,
    COUNT(*) as invalid_count
FROM rtw_checks c
LEFT JOIN documents d ON c.proof_document_id = d.id
WHERE c.proof_document_id IS NOT NULL AND d.id IS NULL;

-- ============================================================
-- FULL SUMMARY
-- ============================================================

SELECT 'profiles' as table_name, COUNT(*) as count FROM profiles
UNION ALL SELECT 'employees', COUNT(*) FROM employees
UNION ALL SELECT 'employee_references', COUNT(*) FROM employee_references
UNION ALL SELECT 'employment_history', COUNT(*) FROM employment_history
UNION ALL SELECT 'employment_gaps', COUNT(*) FROM employment_gaps
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'rtw_checks', COUNT(*) FROM rtw_checks
UNION ALL SELECT 'dbs_checks', COUNT(*) FROM dbs_checks
UNION ALL SELECT 'identity_checks', COUNT(*) FROM identity_checks
UNION ALL SELECT 'address_checks', COUNT(*) FROM address_checks
ORDER BY table_name;

-- Migration state
SELECT phase, status, migrated_records, failed_records, completed_at
FROM migration_state
ORDER BY phase;
