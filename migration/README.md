# Supabase Migration Scripts

Staging migration scripts for migrating from MongoDB to Supabase/Postgres.

## Structure

```
/app/migration/
├── config/
│   ├── settings.py          # Environment variables
│   └── mappings.py           # Data transformation mappings
├── sql/
│   ├── schema/
│   │   └── 001_create_schema.sql   # Full schema creation (idempotent)
│   ├── validation/
│   │   └── all_phases.sql          # Validation queries
│   └── rollback/
│       └── rollback_schema.sql     # Full schema rollback
├── scripts/
│   ├── base.py                  # Base migration class
│   ├── utils.py                 # Utility functions
│   ├── phase_1_users.py         # User/profile migration
│   ├── phase_2_employees.py     # Employee migration
│   ├── phase_3_references.py    # Reference extraction
│   ├── phase_4_documents.py     # Document migration
│   ├── phase_5_files.py         # File transfer
│   ├── phase_6_checks.py        # Verification checks
│   ├── phase_7_training.py      # Training catalogue & records
│   ├── phase_8_forms.py         # Forms & agreements
│   ├── phase_9_org.py           # Org policies & certificates
│   └── phase_10_audit_logs.py   # Audit logs
├── run_migration.py          # Main orchestrator
├── run_validation.py         # Validation runner
├── run_rollback.py           # Rollback runner
└── reports/                  # Generated reports
```

## Prerequisites

1. Install dependencies:
```bash
pip install asyncpg aiohttp
```

2. Set environment variables:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-key"
export SUPABASE_DB_URL="postgresql://postgres:password@db.your-project.supabase.co:5432/postgres"
```

3. Deploy schema to Supabase:
```bash
# Run SQL from sql/schema/001_create_schema.sql in Supabase SQL Editor
```

## Usage

### Dry Run (No Changes)
```bash
# Test against MongoDB without writing to Postgres
python run_migration.py --dry-run
```

### Run All Phases
```bash
python run_migration.py
```

### Run Specific Phase
```bash
python run_migration.py --phase 2
```

### Run Phase Range
```bash
python run_migration.py --start 3 --end 5
```

### Continue After Error
```bash
python run_migration.py --continue-on-error
```

### Run Validation
```bash
python run_validation.py
```

### Rollback
```bash
# Dry run rollback (shows what would happen)
python run_rollback.py --phase 6

# Actually execute rollback
python run_rollback.py --phase 6 --confirm

# Rollback multiple phases
python run_rollback.py --from 6 --to 3 --confirm

# Rollback everything
python run_rollback.py --all --confirm
```

## Migration Phases

| Phase | Name | Source Collection | Target Table(s) |
|-------|------|-------------------|-----------------|
| 1 | Users | `users` | `profiles` |
| 2 | Employees | `employees` | `employees` |
| 3 | References | `employees` (embedded) | `employee_references`, `employment_history`, `employment_gaps` |
| 4 | Documents | `employee_documents` | `documents` |
| 5 | Files | Emergent Storage | Supabase Storage |
| 6 | Checks | `rtw_checks`, `dbs_checks`, etc. | Check tables + junctions |
| 7 | Training | `training_catalogue`, `training_records` | `training_catalogue`, `training_records` |
| 8 | Forms | `form_submissions`, `agreement_acknowledgements` | `form_templates`, `form_submissions`, `agreement_templates`, `agreement_acknowledgements` |
| 9 | Org Data | `org_policies`, `insurance_docs`, `policy_assignments` | `org_policies`, `org_certificates`, `policy_assignments` |
| 10 | Audit Logs | `audit_logs`, `audit_log` | `audit_logs` |

## Key Features

### Idempotent
- All scripts check `mongo_id` before inserting
- Re-running won't create duplicates

### Resumable
- Progress tracked in `migration_state` table
- `last_processed_id` allows continuing after interruption

### Validated
- Validation queries after each phase
- Count comparisons, FK checks, orphan detection

### Rollback Support
- Per-phase rollback SQL
- Preserves mapping tables for retry

## Data Flow

```
MongoDB                         Postgres
────────                        ────────
users           ──────────►     profiles
employees       ──────────►     employees
 ├─ reference_1_*  ──────►      employee_references
 ├─ reference_2_*  ──────►      employee_references
 ├─ employment_history ──►      employment_history
 └─ employment_gaps  ────►      employment_gaps
employee_documents ───────►     documents
Emergent Storage  ────────►     Supabase Storage (storage_path)
rtw_checks        ────────►     rtw_checks
dbs_checks        ────────►     dbs_checks
identity_verifications ───►     identity_checks + junction
address_verifications ────►     address_checks + junction
training_catalogue   ─────►     training_catalogue
training_records     ─────►     training_records
form_submissions     ─────►     form_templates + form_submissions
agreement_acknowledgements ►    agreement_templates + agreement_acknowledgements
org_policies         ─────►     org_policies
insurance_docs       ─────►     org_certificates
policy_assignments   ─────►     policy_assignments
audit_logs + audit_log ───►     audit_logs
```

## ID Mapping

Mapping tables track old->new IDs:
- `migration_user_map`: MongoDB user_id -> Postgres UUID
- `migration_employee_map`: MongoDB id -> Postgres UUID
- `migration_document_map`: MongoDB id -> Postgres UUID

## Reports

Each phase generates a JSON report in `/app/migration/reports/`:
```json
{
  "phase": "phase_2_employees",
  "status": "completed",
  "total_records": 12,
  "migrated_records": 12,
  "skipped_records": 0,
  "failed_records": 0,
  "errors": []
}
```

## Troubleshooting

### "No SUPABASE_DB_URL" Warning
- Set the environment variable with your Supabase database connection string
- Without it, scripts run in MongoDB-only mode (dry run)

### Phase Fails Mid-Way
- Check the report in `/app/migration/reports/`
- Fix the issue
- Re-run the same phase (it will resume from `last_processed_id`)

### Need to Start Over
```bash
python run_rollback.py --all --confirm
```

### Check Migration State
```sql
SELECT * FROM migration_state ORDER BY phase;
```
