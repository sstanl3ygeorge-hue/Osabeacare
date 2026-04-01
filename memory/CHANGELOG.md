# Changelog

## 2026-04-01

### Supabase Migration Scripts Complete
- Implemented Phase 7-10 migration scripts:
  - `phase_7_training.py`: Training catalogue & records migration
  - `phase_8_forms.py`: Forms templates, submissions, agreements migration
  - `phase_9_org.py`: Org policies, certificates, policy assignments migration
  - `phase_10_audit_logs.py`: Audit logs migration (both collections)
- Updated SQL schema (`001_create_schema.sql`) with new tables
- Created `BACKEND_SWITCH_PLAN.md` with practical code patterns
- Updated `run_migration.py` to orchestrate all 10 phases
- Dry-run tested all phases successfully

### Backend Audit & Documentation
- Created `BACKEND_AUDIT_REPORT.md` - Full analysis of server.py
- Created `SUPABASE_MIGRATION_BLUEPRINT.md` - Migration architecture
- Created `MIGRATION_RUNBOOK.md` - Operational procedures
- Created migration scripts for phases 1-6 (users, employees, references, documents, files, checks)

## 2026-04-02

### Compliance Verification Proof Enforcement
- Enforced mandatory proof file upload for all verification checks (RTW, DBS, Identity, Address)
- Fixed RecordCheckDialog upload endpoint bug
- Added proof file display in CheckRow expanded view
- Test report: iteration_114.json

### System Audit & Stabilization
- Fixed document view/download 404 errors
- Fixed "No active files" filter bug
- Removed 1029 lines of legacy checklist code

### UI Consolidation
- Removed ~993 lines of duplicate/dead UI code
- Established single-source-of-truth per tab
