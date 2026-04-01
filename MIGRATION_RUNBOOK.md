# Supabase Migration Runbook

**Version:** 1.0  
**Created:** April 2, 2026  
**Status:** OPERATIONAL RUNBOOK - NO IMPLEMENTATION YET  
**Prerequisite:** Complete `/app/SUPABASE_MIGRATION_BLUEPRINT.md`

---

## Table of Contents

1. [Preflight Checklist](#1-preflight-checklist)
2. [Migration Order](#2-migration-order)
3. [Scripts & Modules Needed](#3-scripts--modules-needed)
4. [Phase Execution with Validation](#4-phase-execution-with-validation)
5. [Rollback Procedures](#5-rollback-procedures)
6. [File Migration Safety Plan](#6-file-migration-safety-plan)
7. [Cutover Sequence](#7-cutover-sequence)
8. [Post-Cutover Smoke Tests](#8-post-cutover-smoke-tests)
9. [Fields to Recompute vs Migrate](#9-fields-to-recompute-vs-migrate)

---

## 1. PREFLIGHT CHECKLIST

### 1.1 Infrastructure Ready

| # | Item | Owner | Verified |
|---|------|-------|----------|
| 1.1.1 | Supabase project created | DevOps | ☐ |
| 1.1.2 | Supabase project region matches user base (EU/UK) | DevOps | ☐ |
| 1.1.3 | Supabase plan supports required connections (Pro+) | DevOps | ☐ |
| 1.1.4 | Database connection pooling configured | DevOps | ☐ |
| 1.1.5 | Supabase Storage bucket `documents` created | DevOps | ☐ |
| 1.1.6 | Storage bucket set to private | DevOps | ☐ |
| 1.1.7 | Supabase Edge Functions enabled (if needed) | DevOps | ☐ |
| 1.1.8 | Staging/test Supabase project available | DevOps | ☐ |

### 1.2 Access & Credentials

| # | Item | Location | Verified |
|---|------|----------|----------|
| 1.2.1 | Supabase project URL | Env vars | ☐ |
| 1.2.2 | Supabase anon key | Env vars | ☐ |
| 1.2.3 | Supabase service role key (admin) | Secure vault | ☐ |
| 1.2.4 | Supabase database direct connection string | Secure vault | ☐ |
| 1.2.5 | MongoDB connection string | Env vars | ☐ |
| 1.2.6 | Emergent storage key (for file download) | Env vars | ☐ |
| 1.2.7 | Migration operator Supabase account | Created | ☐ |

### 1.3 Schema Deployed

| # | Item | Verified |
|---|------|----------|
| 1.3.1 | All ENUM types created | ☐ |
| 1.3.2 | All tables created (no data) | ☐ |
| 1.3.3 | All indexes created | ☐ |
| 1.3.4 | All foreign key constraints created | ☐ |
| 1.3.5 | Migration tracking columns added (`mongo_id`, `migration_reviewed`, etc.) | ☐ |
| 1.3.6 | Temporary mapping tables created | ☐ |
| 1.3.7 | RLS policies created but DISABLED | ☐ |
| 1.3.8 | Schema deployed to staging first | ☐ |

### 1.4 Data Cleanup Complete

| # | Item | Count Before | Count After | Verified |
|---|------|--------------|-------------|----------|
| 1.4.1 | Duplicate employees removed | ___ | 0 | ☐ |
| 1.4.2 | Status values normalized | ___ variants | 8 standard | ☐ |
| 1.4.3 | Invalid dates fixed | ___ | 0 | ☐ |
| 1.4.4 | Orphaned documents removed | ___ | 0 | ☐ |
| 1.4.5 | Role names standardized | ___ variants | 4 standard | ☐ |
| 1.4.6 | Empty references cleaned | ___ | 0 | ☐ |
| 1.4.7 | Broken superseded chains fixed | ___ | 0 | ☐ |

### 1.5 Backups & Safety

| # | Item | Location | Verified |
|---|------|----------|----------|
| 1.5.1 | MongoDB full backup taken | S3/GCS bucket | ☐ |
| 1.5.2 | MongoDB backup restore tested | Staging | ☐ |
| 1.5.3 | Emergent file list exported | CSV file | ☐ |
| 1.5.4 | Maintenance window scheduled | Calendar | ☐ |
| 1.5.5 | Stakeholders notified | Email sent | ☐ |
| 1.5.6 | Rollback time budget agreed (max 4 hours) | Documented | ☐ |

### 1.6 Scripts Ready

| # | Item | Path | Tested on Staging | Verified |
|---|------|------|-------------------|----------|
| 1.6.1 | Schema creation SQL | `/migration/sql/001_schema.sql` | ☐ | ☐ |
| 1.6.2 | User migration script | `/migration/scripts/migrate_users.py` | ☐ | ☐ |
| 1.6.3 | Employee migration script | `/migration/scripts/migrate_employees.py` | ☐ | ☐ |
| 1.6.4 | Reference extraction script | `/migration/scripts/extract_references.py` | ☐ | ☐ |
| 1.6.5 | Document migration script | `/migration/scripts/migrate_documents.py` | ☐ | ☐ |
| 1.6.6 | File transfer script | `/migration/scripts/transfer_files.py` | ☐ | ☐ |
| 1.6.7 | Check migration script | `/migration/scripts/migrate_checks.py` | ☐ | ☐ |
| 1.6.8 | Validation queries | `/migration/sql/validation/` | ☐ | ☐ |
| 1.6.9 | Rollback scripts | `/migration/sql/rollback/` | ☐ | ☐ |

### 1.7 Monitoring Ready

| # | Item | Verified |
|---|------|----------|
| 1.7.1 | Migration progress dashboard created | ☐ |
| 1.7.2 | Error alerting configured | ☐ |
| 1.7.3 | Supabase dashboard accessible | ☐ |
| 1.7.4 | Log aggregation configured | ☐ |

### 1.8 Final Go/No-Go

| # | Criteria | Status |
|---|----------|--------|
| 1.8.1 | All preflight items checked | ☐ |
| 1.8.2 | Staging migration successful | ☐ |
| 1.8.3 | Staging validation 100% passed | ☐ |
| 1.8.4 | Team available for migration window | ☐ |
| 1.8.5 | Rollback tested on staging | ☐ |
| 1.8.6 | **GO / NO-GO decision** | _______ |

---

## 2. MIGRATION ORDER

### 2.1 Execution Sequence Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MIGRATION SEQUENCE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 0: PREPARATION                                                        │
│  ├── 0.1 Deploy schema (ENUMs, tables, indexes)                             │
│  ├── 0.2 Create mapping tables                                              │
│  └── 0.3 Disable RLS policies                                               │
│                                                                              │
│  PHASE 1: FOUNDATION (No dependencies)                                       │
│  ├── 1.1 users → auth.users + profiles                                      │
│  ├── 1.2 document_types → document_types                                    │
│  ├── 1.3 training_catalogue → training_catalogue                            │
│  ├── 1.4 form templates → form_templates                                    │
│  └── 1.5 agreement templates → agreement_templates                          │
│       │                                                                      │
│       ▼ (user IDs now available)                                            │
│                                                                              │
│  PHASE 2: EMPLOYEES                                                          │
│  └── 2.1 employees (base fields only) → employees                           │
│       │                                                                      │
│       ▼ (employee IDs now available)                                        │
│                                                                              │
│  PHASE 3: EMPLOYEE EXTENSIONS (parallel-safe)                                │
│  ├── 3.1 Extract references → employee_references                           │
│  ├── 3.2 Extract employment_history → employment_history                    │
│  └── 3.3 Normalize employment_gaps → employment_gaps                        │
│       │                                                                      │
│       ▼ (all employee data migrated)                                        │
│                                                                              │
│  PHASE 4: DOCUMENTS                                                          │
│  ├── 4.1 employee_documents (metadata) → documents                          │
│  ├── 4.2 Normalize evidence_files arrays → additional documents rows        │
│  └── 4.3 Link CV documents to employees.cv_document_id                      │
│       │                                                                      │
│       ▼ (document IDs now available)                                        │
│                                                                              │
│  PHASE 5: FILES (can run parallel, long-running)                             │
│  ├── 5.1 Download files from Emergent                                       │
│  ├── 5.2 Upload files to Supabase Storage                                   │
│  └── 5.3 Update documents.storage_path                                      │
│       │                                                                      │
│       ▼ (files accessible)                                                  │
│                                                                              │
│  PHASE 6: VERIFICATION CHECKS                                                │
│  ├── 6.1 rtw_checks → rtw_checks                                            │
│  ├── 6.2 dbs_checks → dbs_checks                                            │
│  ├── 6.3 identity_verifications → identity_checks + junction                │
│  └── 6.4 address_verifications → address_checks + junction                  │
│       │                                                                      │
│       ▼ (checks linked to documents)                                        │
│                                                                              │
│  PHASE 7: TRAINING & FORMS                                                   │
│  ├── 7.1 training_records → training_records                                │
│  ├── 7.2 form_submissions → form_submissions                                │
│  └── 7.3 agreement_acknowledgements → agreement_acknowledgements            │
│       │                                                                      │
│       ▼                                                                      │
│                                                                              │
│  PHASE 8: ORGANIZATION                                                       │
│  ├── 8.1 org_policies → org_policies                                        │
│  ├── 8.2 insurance_docs → org_certificates                                  │
│  ├── 8.3 policy_assignments → policy_assignments                            │
│  └── 8.4 Org files → Supabase Storage                                       │
│       │                                                                      │
│       ▼                                                                      │
│                                                                              │
│  PHASE 9: SUPPORTING DATA                                                    │
│  ├── 9.1 recurring_compliance → recurring_items                             │
│  ├── 9.2 scheduled_bulk_requests → scheduled_requests                       │
│  └── 9.3 audit_logs → audit_log                                             │
│       │                                                                      │
│       ▼                                                                      │
│                                                                              │
│  PHASE 10: FINALIZATION                                                      │
│  ├── 10.1 Recompute calculated fields                                       │
│  ├── 10.2 Update gap FK links (preceding_job_id, following_job_id)          │
│  ├── 10.3 Enable RLS policies                                               │
│  ├── 10.4 Run full validation suite                                         │
│  └── 10.5 Generate migration report                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Dependency Matrix

| Phase | Depends On | Blocks |
|-------|------------|--------|
| 0 | Nothing | All |
| 1 | 0 | 2, 7, 8, 9 |
| 2 | 1 | 3, 4, 6, 7 |
| 3 | 2 | 10 |
| 4 | 2 | 5, 6 |
| 5 | 4 | 10 |
| 6 | 4 | 10 |
| 7 | 1, 2, 4 | 10 |
| 8 | 1 | 10 |
| 9 | All | 10 |
| 10 | All | Cutover |

### 2.3 Estimated Timing

| Phase | Duration | Cumulative | Notes |
|-------|----------|------------|-------|
| 0 | 15 min | 0:15 | Schema deployment |
| 1 | 30 min | 0:45 | ~5 users, ref tables |
| 2 | 30 min | 1:15 | ~12 employees |
| 3 | 30 min | 1:45 | Extract embedded data |
| 4 | 45 min | 2:30 | ~76 documents |
| 5 | 2-4 hours | 6:30 | File transfer (bottleneck) |
| 6 | 30 min | 7:00 | ~23 check records |
| 7 | 30 min | 7:30 | ~104 records |
| 8 | 30 min | 8:00 | Org data |
| 9 | 30 min | 8:30 | Audit logs |
| 10 | 30 min | 9:00 | Finalization |

**Total estimated: 8-10 hours** (dominated by file transfer)

---

## 3. SCRIPTS & MODULES NEEDED

### 3.1 Directory Structure

```
/app/migration/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Environment variables, connection strings
│   └── mappings.py              # Status mappings, role mappings
│
├── sql/
│   ├── 001_enums.sql            # Create all ENUM types
│   ├── 002_tables.sql           # Create all tables
│   ├── 003_indexes.sql          # Create indexes
│   ├── 004_constraints.sql      # Add foreign keys
│   ├── 005_mapping_tables.sql   # Temporary migration mapping tables
│   ├── 006_rls_policies.sql     # RLS policies (applied later)
│   │
│   ├── validation/
│   │   ├── phase_1_users.sql
│   │   ├── phase_2_employees.sql
│   │   ├── phase_3_extensions.sql
│   │   ├── phase_4_documents.sql
│   │   ├── phase_5_files.sql
│   │   ├── phase_6_checks.sql
│   │   ├── phase_7_training.sql
│   │   ├── phase_8_org.sql
│   │   ├── phase_9_supporting.sql
│   │   └── full_validation.sql
│   │
│   └── rollback/
│       ├── rollback_phase_1.sql
│       ├── rollback_phase_2.sql
│       ├── rollback_phase_3.sql
│       ├── rollback_phase_4.sql
│       ├── rollback_phase_5.sql
│       ├── rollback_phase_6.sql
│       ├── rollback_phase_7.sql
│       ├── rollback_phase_8.sql
│       └── rollback_phase_9.sql
│
├── scripts/
│   ├── __init__.py
│   ├── base.py                  # Base migration class, logging, error handling
│   ├── utils.py                 # Date parsing, UUID generation, mapping helpers
│   │
│   ├── phase_0_prepare.py       # Schema deployment
│   ├── phase_1_users.py         # User migration
│   ├── phase_2_employees.py     # Employee migration
│   ├── phase_3_extensions.py    # References, employment history, gaps
│   ├── phase_4_documents.py     # Document metadata migration
│   ├── phase_5_files.py         # File transfer (Emergent → Supabase)
│   ├── phase_6_checks.py        # Verification checks migration
│   ├── phase_7_training.py      # Training and forms migration
│   ├── phase_8_org.py           # Organization data migration
│   ├── phase_9_supporting.py    # Audit logs, schedules
│   ├── phase_10_finalize.py     # Recompute fields, enable RLS
│   │
│   ├── validate.py              # Run validation queries
│   └── rollback.py              # Execute rollback for specific phase
│
├── run_migration.py             # Main orchestrator script
├── run_validation.py            # Validation runner
├── run_rollback.py              # Rollback runner
│
└── reports/
    └── (generated during migration)
```

### 3.2 Core Module: `base.py`

```python
# /app/migration/scripts/base.py

"""
Base migration infrastructure.
Provides logging, error handling, progress tracking, and database connections.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import json

from motor.motor_asyncio import AsyncIOMotorClient
from supabase import create_client, Client
import asyncpg

from config.settings import (
    MONGO_URL, MONGO_DB_NAME,
    SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_DB_URL
)


class MigrationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationResult:
    phase: str
    status: MigrationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_records: int = 0
    migrated_records: int = 0
    failed_records: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_records": self.total_records,
            "migrated_records": self.migrated_records,
            "failed_records": self.failed_records,
            "success_rate": f"{(self.migrated_records / self.total_records * 100):.1f}%" if self.total_records > 0 else "N/A",
            "errors": self.errors[:10],  # First 10 errors
            "error_count": len(self.errors),
            "warnings": self.warnings[:10],
            "warning_count": len(self.warnings)
        }


class BaseMigration:
    """Base class for all migration phases."""
    
    def __init__(self, phase_name: str, dry_run: bool = False):
        self.phase_name = phase_name
        self.dry_run = dry_run
        self.logger = logging.getLogger(f"migration.{phase_name}")
        
        # Connections (initialized in setup)
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.mongo_db = None
        self.supabase: Optional[Client] = None
        self.pg_pool: Optional[asyncpg.Pool] = None
        
        # ID mappings (loaded from mapping tables)
        self.user_id_map: Dict[str, str] = {}
        self.employee_id_map: Dict[str, str] = {}
        self.document_id_map: Dict[str, str] = {}
        
        # Result tracking
        self.result = MigrationResult(
            phase=phase_name,
            status=MigrationStatus.PENDING,
            started_at=datetime.now(timezone.utc)
        )
    
    async def setup(self):
        """Initialize database connections."""
        self.logger.info(f"Setting up {self.phase_name}...")
        
        # MongoDB
        self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        self.mongo_db = self.mongo_client[MONGO_DB_NAME]
        
        # Supabase client (for Storage, Auth)
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # Direct Postgres connection (for bulk inserts)
        self.pg_pool = await asyncpg.create_pool(SUPABASE_DB_URL, min_size=2, max_size=10)
        
        # Load ID mappings
        await self._load_mappings()
    
    async def teardown(self):
        """Close database connections."""
        if self.mongo_client:
            self.mongo_client.close()
        if self.pg_pool:
            await self.pg_pool.close()
    
    async def _load_mappings(self):
        """Load ID mappings from mapping tables."""
        async with self.pg_pool.acquire() as conn:
            # User mappings
            rows = await conn.fetch("SELECT old_id, new_id FROM migration_user_map")
            self.user_id_map = {r["old_id"]: str(r["new_id"]) for r in rows}
            
            # Employee mappings
            rows = await conn.fetch("SELECT old_id, new_id FROM migration_employee_map")
            self.employee_id_map = {r["old_id"]: str(r["new_id"]) for r in rows}
            
            # Document mappings
            rows = await conn.fetch("SELECT old_id, new_id FROM migration_document_map")
            self.document_id_map = {r["old_id"]: str(r["new_id"]) for r in rows}
    
    async def _save_mapping(self, table: str, old_id: str, new_id: str):
        """Save ID mapping to mapping table."""
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                f"INSERT INTO {table} (old_id, new_id) VALUES ($1, $2) ON CONFLICT (old_id) DO NOTHING",
                old_id, new_id
            )
    
    def map_user_id(self, old_id: Optional[str]) -> Optional[str]:
        """Map MongoDB user ID to Supabase UUID."""
        if not old_id:
            return None
        return self.user_id_map.get(old_id)
    
    def map_employee_id(self, old_id: Optional[str]) -> Optional[str]:
        """Map MongoDB employee ID to Supabase UUID."""
        if not old_id:
            return None
        return self.employee_id_map.get(old_id)
    
    def map_document_id(self, old_id: Optional[str]) -> Optional[str]:
        """Map MongoDB document ID to Supabase UUID."""
        if not old_id:
            return None
        return self.document_id_map.get(old_id)
    
    async def run(self) -> MigrationResult:
        """Execute the migration phase."""
        try:
            await self.setup()
            self.result.status = MigrationStatus.IN_PROGRESS
            self.logger.info(f"Starting {self.phase_name}...")
            
            if self.dry_run:
                self.logger.info("DRY RUN MODE - No data will be written")
            
            # Execute migration (implemented by subclass)
            await self.migrate()
            
            self.result.status = MigrationStatus.COMPLETED
            self.result.completed_at = datetime.now(timezone.utc)
            self.logger.info(f"Completed {self.phase_name}: {self.result.migrated_records}/{self.result.total_records} records")
            
        except Exception as e:
            self.result.status = MigrationStatus.FAILED
            self.result.completed_at = datetime.now(timezone.utc)
            self.result.errors.append({"type": "fatal", "message": str(e)})
            self.logger.error(f"Migration failed: {e}", exc_info=True)
            raise
            
        finally:
            await self.teardown()
            await self._save_result()
        
        return self.result
    
    async def migrate(self):
        """Override in subclass to implement migration logic."""
        raise NotImplementedError
    
    async def _save_result(self):
        """Save migration result to file."""
        report_path = f"/app/migration/reports/{self.phase_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(self.result.to_dict(), f, indent=2)
        self.logger.info(f"Report saved: {report_path}")
    
    def record_error(self, record_id: str, error: str, data: dict = None):
        """Record a migration error."""
        self.result.failed_records += 1
        self.result.errors.append({
            "record_id": record_id,
            "error": error,
            "data": data
        })
        self.logger.warning(f"Error migrating {record_id}: {error}")
    
    def record_warning(self, message: str):
        """Record a migration warning."""
        self.result.warnings.append(message)
        self.logger.warning(message)
```

### 3.3 Core Module: `utils.py`

```python
# /app/migration/scripts/utils.py

"""
Utility functions for data transformation during migration.
"""

from datetime import datetime, timezone, date
from typing import Optional, Any
from uuid import uuid4
import re


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


def parse_date(value: Any) -> Optional[date]:
    """Parse various date formats to Python date."""
    if not value:
        return None
    
    if isinstance(value, date):
        return value
    
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, str):
        # Remove timezone info for date-only parsing
        value = value.split("T")[0]
        
        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    
    return None


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse various timestamp formats to Python datetime."""
    if not value:
        return None
    
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    
    if isinstance(value, str):
        # ISO format with various timezone representations
        value = value.replace("Z", "+00:00")
        
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
        
        # Try without timezone
        try:
            dt = datetime.fromisoformat(value.split("+")[0].split("-")[0])
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    
    return None


def normalize_status(value: str, status_map: dict, default: str) -> str:
    """Normalize status string to ENUM value."""
    if not value:
        return default
    
    normalized = value.lower().strip()
    return status_map.get(normalized, default)


def calculate_gap_months(start_date: date, end_date: date) -> float:
    """Calculate months between two dates."""
    if not start_date or not end_date:
        return 0.0
    
    days = (end_date - start_date).days
    return round(days / 30.44, 1)  # Average days per month


def sanitize_string(value: Any, max_length: int = None) -> Optional[str]:
    """Sanitize string for database insertion."""
    if not value:
        return None
    
    result = str(value).strip()
    
    # Remove null bytes
    result = result.replace("\x00", "")
    
    # Truncate if needed
    if max_length and len(result) > max_length:
        result = result[:max_length]
    
    return result if result else None


def safe_json(value: Any) -> Any:
    """Convert value to JSON-safe format."""
    if value is None:
        return None
    
    if isinstance(value, (str, int, float, bool)):
        return value
    
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    
    if isinstance(value, list):
        return [safe_json(v) for v in value]
    
    return str(value)


# Status mapping dictionaries
PERSON_STATUS_MAP = {
    "new": "new",
    "screening": "screening",
    "interview": "interview",
    "compliance_review": "compliance_review",
    "onboarding": "onboarding",
    "active": "active",
    "inactive": "inactive",
    "archived": "archived",
    # Variants
    "in progress": "screening",
    "pending": "new",
    "hired": "onboarding",
}

DOCUMENT_STATUS_MAP = {
    "uploaded": "uploaded",
    "awaiting_review": "awaiting_review",
    "verified": "verified",
    "rejected": "rejected",
    "expired": "expired",
    "superseded": "superseded",
    # Variants
    "pending": "awaiting_review",
    "approved": "verified",
}

VERIFICATION_OUTCOME_MAP = {
    "awaiting_review": "awaiting_review",
    "verified": "verified",
    "failed": "failed",
    "follow_up_required": "follow_up_required",
    "rejected": "rejected",
    # Variants
    "pending": "awaiting_review",
    "passed": "verified",
}

REFERENCE_STATUS_MAP = {
    "not_declared": "not_declared",
    "declared": "declared",
    "request_sent": "request_sent",
    "request_viewed": "request_viewed",
    "response_received": "response_received",
    "verified": "verified",
    "rejected": "rejected",
    # Variants
    "sent": "request_sent",
    "viewed": "request_viewed",
    "received": "response_received",
}

GAP_STATUS_MAP = {
    "detected": "detected",
    "explained": "explained",
    "verified": "verified",
    "rejected": "rejected",
    "more_info_needed": "more_info_needed",
    # Variants
    "pending": "detected",
    "awaiting_explanation": "detected",
}

DOCUMENT_CATEGORY_MAP = {
    "right_to_work": "right_to_work",
    "dbs": "dbs",
    "identity": "identity",
    "proof_of_address": "proof_of_address",
    "training": "training",
    "cv": "cv",
    "reference": "reference",
    "agreement": "agreement",
    "verification_proof": "verification_proof",
    "form_attachment": "form_attachment",
    "other": "other",
    # Variants
    "rtw": "right_to_work",
    "poa": "proof_of_address",
    "address": "proof_of_address",
}
```

### 3.4 Example Phase Script: `phase_1_users.py`

```python
# /app/migration/scripts/phase_1_users.py

"""
Phase 1: Migrate users from MongoDB to Supabase Auth + profiles.
"""

from .base import BaseMigration, MigrationStatus
from .utils import parse_timestamp, generate_uuid, sanitize_string
from config.mappings import ROLE_MAP


class Phase1UserMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_1_users", dry_run)
    
    async def migrate(self):
        # Get all MongoDB users
        cursor = self.mongo_db.users.find({})
        users = await cursor.to_list(length=None)
        self.result.total_records = len(users)
        
        self.logger.info(f"Found {len(users)} users to migrate")
        
        for user in users:
            try:
                await self._migrate_user(user)
                self.result.migrated_records += 1
            except Exception as e:
                self.record_error(user.get("user_id", "unknown"), str(e), user)
    
    async def _migrate_user(self, mongo_user: dict):
        """Migrate a single user."""
        old_id = mongo_user.get("user_id")
        email = mongo_user.get("email")
        
        if not email:
            raise ValueError("User has no email")
        
        self.logger.debug(f"Migrating user: {email}")
        
        # Generate new UUID
        new_id = generate_uuid()
        
        if not self.dry_run:
            # 1. Create Supabase auth user with existing password hash
            # Note: This requires the service role key and admin API
            auth_response = self.supabase.auth.admin.create_user({
                "email": email,
                "password": mongo_user.get("password"),  # bcrypt hash
                "email_confirm": True,
                "user_metadata": {
                    "migrated_from_mongo": True,
                    "mongo_user_id": old_id
                }
            })
            
            # Use the Supabase-generated ID
            new_id = auth_response.user.id
            
            # 2. Create profile record
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO profiles (id, email, name, role, branch, picture_url, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    new_id,
                    email,
                    sanitize_string(mongo_user.get("name")),
                    ROLE_MAP.get(mongo_user.get("role", "employee"), "employee"),
                    sanitize_string(mongo_user.get("branch")),
                    mongo_user.get("picture"),
                    parse_timestamp(mongo_user.get("created_at")) or datetime.now(timezone.utc),
                    datetime.now(timezone.utc)
                )
            
            # 3. Save mapping
            await self._save_mapping("migration_user_map", old_id, new_id)
        
        # Update local map
        self.user_id_map[old_id] = new_id
        self.logger.info(f"Migrated user {email}: {old_id} → {new_id}")


async def run(dry_run: bool = False):
    """Entry point for phase 1."""
    migration = Phase1UserMigration(dry_run=dry_run)
    return await migration.run()
```

### 3.5 Main Orchestrator: `run_migration.py`

```python
# /app/migration/run_migration.py

"""
Main migration orchestrator.
Executes phases in order with validation between each.
"""

import asyncio
import argparse
import logging
from datetime import datetime
import json

from scripts import (
    phase_0_prepare,
    phase_1_users,
    phase_2_employees,
    phase_3_extensions,
    phase_4_documents,
    phase_5_files,
    phase_6_checks,
    phase_7_training,
    phase_8_org,
    phase_9_supporting,
    phase_10_finalize,
)
from scripts.validate import run_phase_validation


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(f"/app/migration/reports/migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("migration.orchestrator")


PHASES = [
    ("phase_0", phase_0_prepare, False),   # (name, module, requires_validation)
    ("phase_1", phase_1_users, True),
    ("phase_2", phase_2_employees, True),
    ("phase_3", phase_3_extensions, True),
    ("phase_4", phase_4_documents, True),
    ("phase_5", phase_5_files, True),
    ("phase_6", phase_6_checks, True),
    ("phase_7", phase_7_training, True),
    ("phase_8", phase_8_org, True),
    ("phase_9", phase_9_supporting, True),
    ("phase_10", phase_10_finalize, True),
]


async def run_migration(
    start_phase: int = 0,
    end_phase: int = 10,
    dry_run: bool = False,
    skip_validation: bool = False,
    stop_on_error: bool = True
):
    """Run migration phases."""
    
    results = []
    
    logger.info("=" * 60)
    logger.info(f"MIGRATION STARTED")
    logger.info(f"Phases: {start_phase} to {end_phase}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 60)
    
    for phase_num, (phase_name, phase_module, requires_validation) in enumerate(PHASES):
        if phase_num < start_phase or phase_num > end_phase:
            continue
        
        logger.info(f"\n{'=' * 40}")
        logger.info(f"STARTING {phase_name.upper()}")
        logger.info(f"{'=' * 40}")
        
        try:
            # Run phase
            result = await phase_module.run(dry_run=dry_run)
            results.append(result)
            
            if result.status.value != "completed":
                logger.error(f"{phase_name} failed with status: {result.status.value}")
                if stop_on_error:
                    logger.error("Stopping migration due to error")
                    break
            
            # Run validation
            if requires_validation and not skip_validation and not dry_run:
                logger.info(f"Running validation for {phase_name}...")
                validation_passed = await run_phase_validation(phase_name)
                
                if not validation_passed:
                    logger.error(f"Validation failed for {phase_name}")
                    if stop_on_error:
                        logger.error("Stopping migration due to validation failure")
                        break
                else:
                    logger.info(f"Validation passed for {phase_name}")
            
            logger.info(f"COMPLETED {phase_name.upper()}")
            
        except Exception as e:
            logger.error(f"Exception in {phase_name}: {e}", exc_info=True)
            if stop_on_error:
                break
    
    # Generate final report
    report = {
        "started_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "phases": [r.to_dict() for r in results]
    }
    
    report_path = f"/app/migration/reports/final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"\nFinal report: {report_path}")
    logger.info("MIGRATION COMPLETE")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Run Supabase migration")
    parser.add_argument("--start", type=int, default=0, help="Start phase (0-10)")
    parser.add_argument("--end", type=int, default=10, help="End phase (0-10)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no writes)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue on error")
    
    args = parser.parse_args()
    
    asyncio.run(run_migration(
        start_phase=args.start,
        end_phase=args.end,
        dry_run=args.dry_run,
        skip_validation=args.skip_validation,
        stop_on_error=not args.continue_on_error
    ))


if __name__ == "__main__":
    main()
```

---

## 4. PHASE EXECUTION WITH VALIDATION

### 4.1 Phase 0: Preparation

**Execution:**
```bash
python run_migration.py --start 0 --end 0
```

**Validation SQL:** `/migration/sql/validation/phase_0_schema.sql`
```sql
-- Verify all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Expected: 25+ tables
-- Must include: profiles, employees, documents, rtw_checks, dbs_checks, etc.

-- Verify all ENUMs exist
SELECT typname 
FROM pg_type 
WHERE typcategory = 'E'
ORDER BY typname;

-- Expected: user_role, person_status, document_category, etc.

-- Verify mapping tables exist and are empty
SELECT 
    'migration_user_map' as table_name, COUNT(*) as count FROM migration_user_map
UNION ALL
SELECT 'migration_employee_map', COUNT(*) FROM migration_employee_map
UNION ALL
SELECT 'migration_document_map', COUNT(*) FROM migration_document_map;

-- Expected: All counts = 0
```

**Success Criteria:**
- [ ] 25+ tables created
- [ ] All ENUM types created
- [ ] Mapping tables empty
- [ ] No SQL errors

---

### 4.2 Phase 1: Users

**Execution:**
```bash
python run_migration.py --start 1 --end 1
```

**Validation SQL:** `/migration/sql/validation/phase_1_users.sql`
```sql
-- Count comparison
WITH mongo_count AS (
    SELECT 5 as expected  -- Replace with actual MongoDB count
),
pg_count AS (
    SELECT COUNT(*) as actual FROM profiles
)
SELECT 
    m.expected as mongo_users,
    p.actual as postgres_profiles,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Verify auth.users created
SELECT COUNT(*) as auth_users FROM auth.users;

-- Verify all roles are valid ENUMs
SELECT role, COUNT(*) 
FROM profiles 
GROUP BY role;

-- Verify mapping table populated
SELECT COUNT(*) as mapped_users FROM migration_user_map;

-- Check for orphaned profiles (no auth.users entry)
SELECT p.id, p.email 
FROM profiles p
LEFT JOIN auth.users a ON p.id = a.id
WHERE a.id IS NULL;

-- Expected: 0 rows (no orphans)
```

**Success Criteria:**
- [ ] Profile count = MongoDB user count
- [ ] Auth.users count = profile count
- [ ] All roles are valid ENUMs
- [ ] Mapping table populated
- [ ] No orphaned profiles

---

### 4.3 Phase 2: Employees

**Execution:**
```bash
python run_migration.py --start 2 --end 2
```

**Validation SQL:** `/migration/sql/validation/phase_2_employees.sql`
```sql
-- Count comparison
WITH mongo_count AS (
    SELECT 12 as expected  -- Replace with actual
),
pg_count AS (
    SELECT COUNT(*) as actual FROM employees
)
SELECT 
    m.expected as mongo_employees,
    p.actual as postgres_employees,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Verify all statuses are valid ENUMs
SELECT status, COUNT(*) 
FROM employees 
GROUP BY status
ORDER BY COUNT(*) DESC;

-- Verify all have mongo_id (migration tracking)
SELECT COUNT(*) as without_mongo_id 
FROM employees 
WHERE mongo_id IS NULL;

-- Expected: 0

-- Verify mapping table populated
SELECT COUNT(*) as mapped_employees FROM migration_employee_map;

-- Check for duplicate emails
SELECT email, COUNT(*) 
FROM employees 
GROUP BY email 
HAVING COUNT(*) > 1;

-- Expected: 0 rows

-- Verify FK references (manager_id, recruitment_approved_by)
SELECT COUNT(*) as invalid_manager_refs
FROM employees e
LEFT JOIN profiles p ON e.manager_id = p.id
WHERE e.manager_id IS NOT NULL AND p.id IS NULL;

-- Expected: 0
```

**Success Criteria:**
- [ ] Employee count matches
- [ ] All statuses valid
- [ ] All have mongo_id
- [ ] No duplicate emails
- [ ] FK references valid

---

### 4.4 Phase 3: Extensions (References, History, Gaps)

**Execution:**
```bash
python run_migration.py --start 3 --end 3
```

**Validation SQL:** `/migration/sql/validation/phase_3_extensions.sql`
```sql
-- Reference count (should be ~2 per employee with declared refs)
SELECT 
    (SELECT COUNT(*) FROM employees WHERE mongo_id IS NOT NULL) as employees,
    (SELECT COUNT(*) FROM employee_references) as references,
    (SELECT COUNT(DISTINCT employee_id) FROM employee_references) as employees_with_refs;

-- Verify reference numbers are 1 or 2
SELECT reference_number, COUNT(*) 
FROM employee_references 
GROUP BY reference_number;

-- Expected: Only 1 and 2

-- Verify unique constraint (employee_id, reference_number)
SELECT employee_id, reference_number, COUNT(*)
FROM employee_references
GROUP BY employee_id, reference_number
HAVING COUNT(*) > 1;

-- Expected: 0 rows

-- Employment history count
SELECT 
    (SELECT COUNT(*) FROM employment_history) as history_records,
    (SELECT COUNT(DISTINCT employee_id) FROM employment_history) as employees_with_history;

-- Employment gaps count
SELECT 
    (SELECT COUNT(*) FROM employment_gaps) as gaps,
    (SELECT COUNT(DISTINCT employee_id) FROM employment_gaps) as employees_with_gaps;

-- Verify gap dates are valid (start < end)
SELECT id, gap_start_date, gap_end_date
FROM employment_gaps
WHERE gap_start_date >= gap_end_date;

-- Expected: 0 rows

-- Verify gap_months calculated correctly (spot check)
SELECT 
    id,
    gap_start_date,
    gap_end_date,
    gap_months,
    ROUND(EXTRACT(EPOCH FROM (gap_end_date - gap_start_date)) / (30.44 * 86400), 1) as calculated_months
FROM employment_gaps
LIMIT 5;
```

**Success Criteria:**
- [ ] References extracted (count reasonable)
- [ ] Only reference_number 1 or 2
- [ ] No duplicate references
- [ ] Employment history populated
- [ ] Gap dates valid (start < end)
- [ ] Gap months calculated correctly

---

### 4.5 Phase 4: Documents

**Execution:**
```bash
python run_migration.py --start 4 --end 4
```

**Validation SQL:** `/migration/sql/validation/phase_4_documents.sql`
```sql
-- Count comparison
WITH mongo_count AS (
    SELECT 76 as expected  -- Replace with actual
),
pg_count AS (
    SELECT COUNT(*) as actual FROM documents
)
SELECT 
    m.expected,
    p.actual,
    CASE WHEN m.expected <= p.actual THEN 'PASS' ELSE 'FAIL' END as status;

-- Note: Postgres may have MORE due to evidence_files array normalization

-- Category distribution
SELECT category, COUNT(*) 
FROM documents 
GROUP BY category 
ORDER BY COUNT(*) DESC;

-- Verify all have valid employee FK
SELECT COUNT(*) as orphaned_documents
FROM documents d
LEFT JOIN employees e ON d.employee_id = e.id
WHERE e.id IS NULL;

-- Expected: 0

-- Verify mapping table populated
SELECT COUNT(*) as mapped_documents FROM migration_document_map;

-- Check for documents without old_file_url (migration tracking)
SELECT COUNT(*) as without_old_url
FROM documents
WHERE old_file_url IS NULL AND mongo_id IS NOT NULL;

-- Documents needing file migration
SELECT COUNT(*) as needs_file_migration
FROM documents
WHERE storage_path IS NULL AND old_file_url IS NOT NULL;
```

**Success Criteria:**
- [ ] Document count >= MongoDB count
- [ ] All categories valid
- [ ] No orphaned documents
- [ ] Mapping table populated
- [ ] old_file_url preserved

---

### 4.6 Phase 5: Files

**Execution:**
```bash
python run_migration.py --start 5 --end 5
```

**Validation SQL:** `/migration/sql/validation/phase_5_files.sql`
```sql
-- File migration progress
SELECT 
    COUNT(*) as total_documents,
    COUNT(storage_path) as migrated_files,
    COUNT(*) - COUNT(storage_path) as pending_files,
    ROUND(COUNT(storage_path)::numeric / COUNT(*) * 100, 1) as percent_complete
FROM documents
WHERE old_file_url IS NOT NULL;

-- Files by status
SELECT 
    CASE 
        WHEN storage_path IS NOT NULL THEN 'migrated'
        WHEN old_file_url IS NOT NULL THEN 'pending'
        ELSE 'no_file'
    END as status,
    COUNT(*)
FROM documents
GROUP BY 1;

-- Check for failed migrations (have old_file_url but no storage_path and flagged)
SELECT id, old_file_url, migration_notes
FROM documents
WHERE old_file_url IS NOT NULL 
AND storage_path IS NULL
AND migration_notes LIKE '%error%';

-- Verify storage paths follow convention
SELECT 
    id,
    storage_path,
    CASE 
        WHEN storage_path ~ '^[a-f0-9-]+/[a-z_]+/.+$' THEN 'valid'
        ELSE 'invalid'
    END as path_format
FROM documents
WHERE storage_path IS NOT NULL
LIMIT 10;
```

**Success Criteria:**
- [ ] 100% files migrated (or known failures documented)
- [ ] All storage_path values follow convention
- [ ] Failed files flagged with notes
- [ ] Files accessible in Supabase Storage

---

### 4.7 Phase 6: Verification Checks

**Execution:**
```bash
python run_migration.py --start 6 --end 6
```

**Validation SQL:** `/migration/sql/validation/phase_6_checks.sql`
```sql
-- RTW checks count
WITH mongo_count AS (SELECT 11 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM rtw_checks)
SELECT m.expected, p.actual, 
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- DBS checks count
WITH mongo_count AS (SELECT 5 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM dbs_checks)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Identity checks count
WITH mongo_count AS (SELECT 4 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM identity_checks)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Address checks count
WITH mongo_count AS (SELECT 3 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM address_checks)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Verify is_current flag (only one per employee)
SELECT employee_id, COUNT(*) as current_count
FROM rtw_checks
WHERE is_current = true
GROUP BY employee_id
HAVING COUNT(*) > 1;

-- Expected: 0 rows

-- Verify proof_document_id references valid documents
SELECT c.id as check_id, c.proof_document_id
FROM rtw_checks c
LEFT JOIN documents d ON c.proof_document_id = d.id
WHERE c.proof_document_id IS NOT NULL AND d.id IS NULL;

-- Expected: 0 rows

-- Identity check junction table
SELECT 
    (SELECT COUNT(*) FROM identity_checks) as checks,
    (SELECT COUNT(*) FROM identity_check_documents) as junction_rows;

-- Address check junction table
SELECT 
    (SELECT COUNT(*) FROM address_checks) as checks,
    (SELECT COUNT(*) FROM address_check_documents) as junction_rows;
```

**Success Criteria:**
- [ ] All check counts match
- [ ] Only one is_current=true per employee per check type
- [ ] proof_document_id references valid
- [ ] Junction tables populated

---

### 4.8 Phase 7: Training & Forms

**Execution:**
```bash
python run_migration.py --start 7 --end 7
```

**Validation SQL:** `/migration/sql/validation/phase_7_training.sql`
```sql
-- Training records count
WITH mongo_count AS (SELECT 43 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM training_records)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Training records with valid training_id FK
SELECT COUNT(*) as invalid_training_id
FROM training_records t
LEFT JOIN training_catalogue c ON t.training_id = c.id
WHERE c.id IS NULL;

-- Expected: 0

-- Form submissions count
WITH mongo_count AS (SELECT 53 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM form_submissions)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Form types distribution
SELECT form_type, COUNT(*) 
FROM form_submissions 
GROUP BY form_type 
ORDER BY COUNT(*) DESC;

-- Agreement acknowledgements count
WITH mongo_count AS (SELECT 8 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM agreement_acknowledgements)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Verify JSONB data is valid (form_submissions.data)
SELECT id, form_type
FROM form_submissions
WHERE data IS NULL OR data = '{}'::jsonb;

-- Expected: 0 or documented reasons
```

**Success Criteria:**
- [ ] Training records count matches
- [ ] All training_id FKs valid
- [ ] Form submissions count matches
- [ ] Agreement acknowledgements count matches
- [ ] JSONB data preserved

---

### 4.9 Phase 8: Organization

**Execution:**
```bash
python run_migration.py --start 8 --end 8
```

**Validation SQL:** `/migration/sql/validation/phase_8_org.sql`
```sql
-- Org policies count
WITH mongo_count AS (SELECT 32 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM org_policies)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Org certificates count (from insurance_docs)
WITH mongo_count AS (SELECT 13 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM org_certificates)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Policy assignments count
WITH mongo_count AS (SELECT 4 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM policy_assignments)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Verify policy assignment FKs
SELECT COUNT(*) as invalid_assignments
FROM policy_assignments pa
LEFT JOIN employees e ON pa.employee_id = e.id
LEFT JOIN org_policies p ON pa.policy_id = p.id
WHERE e.id IS NULL OR p.id IS NULL;

-- Expected: 0
```

**Success Criteria:**
- [ ] Org policies count matches
- [ ] Org certificates count matches
- [ ] Policy assignments count matches
- [ ] All FKs valid

---

### 4.10 Phase 9: Supporting Data

**Execution:**
```bash
python run_migration.py --start 9 --end 9
```

**Validation SQL:** `/migration/sql/validation/phase_9_supporting.sql`
```sql
-- Recurring items count
WITH mongo_count AS (SELECT 3 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM recurring_items)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Scheduled requests count
WITH mongo_count AS (SELECT 5 as expected),
pg_count AS (SELECT COUNT(*) as actual FROM scheduled_requests)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Audit log count (combined from audit_logs + audit_log)
WITH mongo_count AS (SELECT 1236 as expected),  -- 1218 + 18
pg_count AS (SELECT COUNT(*) as actual FROM audit_log)
SELECT m.expected, p.actual,
    CASE WHEN m.expected = p.actual THEN 'PASS' ELSE 'FAIL' END as status
FROM mongo_count m, pg_count p;

-- Audit log entity types
SELECT entity_type, COUNT(*) 
FROM audit_log 
GROUP BY entity_type 
ORDER BY COUNT(*) DESC;
```

**Success Criteria:**
- [ ] Recurring items count matches
- [ ] Scheduled requests count matches
- [ ] Audit log count matches (combined)

---

### 4.11 Phase 10: Finalization

**Execution:**
```bash
python run_migration.py --start 10 --end 10
```

**Validation SQL:** `/migration/sql/validation/phase_10_finalize.sql`
```sql
-- Verify gap FKs updated
SELECT COUNT(*) as gaps_without_job_links
FROM employment_gaps
WHERE preceding_job_id IS NULL AND following_job_id IS NULL;

-- Note: Some gaps may legitimately have no links (first/last job)

-- Verify computed fields updated
SELECT 
    id,
    completion_percentage,
    compliance_score
FROM employees
WHERE completion_percentage IS NULL OR compliance_score IS NULL
LIMIT 10;

-- Verify RLS policies enabled
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;

-- Full record counts summary
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
UNION ALL SELECT 'training_records', COUNT(*) FROM training_records
UNION ALL SELECT 'form_submissions', COUNT(*) FROM form_submissions
UNION ALL SELECT 'agreement_acknowledgements', COUNT(*) FROM agreement_acknowledgements
UNION ALL SELECT 'org_policies', COUNT(*) FROM org_policies
UNION ALL SELECT 'recurring_items', COUNT(*) FROM recurring_items
UNION ALL SELECT 'audit_log', COUNT(*) FROM audit_log
ORDER BY table_name;
```

**Success Criteria:**
- [ ] Gap job links populated where applicable
- [ ] Computed fields populated
- [ ] RLS policies enabled
- [ ] All table counts verified

---

## 5. ROLLBACK PROCEDURES

### 5.1 General Rollback Principles

1. **Rollback in reverse phase order**
2. **Each phase rollback is independent**
3. **Mapping tables preserved during rollback** (for retry)
4. **MongoDB remains source of truth until cutover**
5. **Maximum rollback window: 4 hours from start**

### 5.2 Phase-Specific Rollback

#### Phase 1 Rollback (Users)
```sql
-- /migration/sql/rollback/rollback_phase_1.sql

-- Delete profiles (cascade will handle most)
DELETE FROM profiles WHERE id IN (SELECT new_id FROM migration_user_map);

-- Delete auth.users via admin API (script required)
-- See rollback script: scripts/rollback_phase_1.py

-- Clear mapping (optional, keep for retry)
-- TRUNCATE migration_user_map;

-- Verify
SELECT COUNT(*) FROM profiles;  -- Should be 0
```

#### Phase 2 Rollback (Employees)
```sql
-- /migration/sql/rollback/rollback_phase_2.sql

-- Delete employees (will cascade to dependent tables)
DELETE FROM employees WHERE mongo_id IS NOT NULL;

-- Clear mapping (optional)
-- TRUNCATE migration_employee_map;

-- Verify
SELECT COUNT(*) FROM employees;  -- Should be 0
```

#### Phase 3 Rollback (Extensions)
```sql
-- /migration/sql/rollback/rollback_phase_3.sql

-- These are dependent on employees, so delete explicitly
DELETE FROM employee_references;
DELETE FROM employment_history;
DELETE FROM employment_gaps;

-- Verify
SELECT COUNT(*) FROM employee_references;  -- Should be 0
SELECT COUNT(*) FROM employment_history;   -- Should be 0
SELECT COUNT(*) FROM employment_gaps;      -- Should be 0
```

#### Phase 4 Rollback (Documents)
```sql
-- /migration/sql/rollback/rollback_phase_4.sql

-- Delete junction tables first
DELETE FROM identity_check_documents;
DELETE FROM address_check_documents;

-- Delete documents
DELETE FROM documents WHERE mongo_id IS NOT NULL;

-- Clear mapping (optional)
-- TRUNCATE migration_document_map;

-- Verify
SELECT COUNT(*) FROM documents;  -- Should be 0
```

#### Phase 5 Rollback (Files)
```sql
-- /migration/sql/rollback/rollback_phase_5.sql

-- Clear storage_path (files remain in Supabase Storage for manual cleanup)
UPDATE documents SET storage_path = NULL WHERE mongo_id IS NOT NULL;

-- Note: Supabase Storage files should be cleaned manually:
-- 1. List all files in bucket
-- 2. Delete files not in documents.storage_path
-- OR delete entire bucket contents and re-run migration
```

#### Phase 6 Rollback (Checks)
```sql
-- /migration/sql/rollback/rollback_phase_6.sql

-- Delete junction tables first
DELETE FROM identity_check_documents;
DELETE FROM address_check_documents;

-- Delete check tables
DELETE FROM rtw_checks WHERE mongo_id IS NOT NULL;
DELETE FROM dbs_checks WHERE mongo_id IS NOT NULL;
DELETE FROM identity_checks WHERE mongo_id IS NOT NULL;
DELETE FROM address_checks WHERE mongo_id IS NOT NULL;
```

#### Phase 7 Rollback (Training & Forms)
```sql
-- /migration/sql/rollback/rollback_phase_7.sql

DELETE FROM training_records WHERE mongo_id IS NOT NULL;
DELETE FROM form_submissions WHERE mongo_id IS NOT NULL;
DELETE FROM agreement_acknowledgements WHERE mongo_id IS NOT NULL;
```

#### Phase 8 Rollback (Organization)
```sql
-- /migration/sql/rollback/rollback_phase_8.sql

DELETE FROM policy_assignments;
DELETE FROM org_policies WHERE mongo_id IS NOT NULL;
DELETE FROM org_certificates WHERE mongo_id IS NOT NULL;
```

#### Phase 9 Rollback (Supporting)
```sql
-- /migration/sql/rollback/rollback_phase_9.sql

DELETE FROM recurring_completions;
DELETE FROM recurring_items;
DELETE FROM scheduled_requests;
DELETE FROM request_log;
DELETE FROM audit_log WHERE mongo_id IS NOT NULL;
```

### 5.3 Full Rollback Command

```bash
# Rollback all phases (reverse order)
python run_rollback.py --from-phase 9 --to-phase 1

# Rollback specific phase only
python run_rollback.py --phase 5

# Rollback with preserved mappings (for retry)
python run_rollback.py --from-phase 9 --to-phase 1 --keep-mappings
```

### 5.4 Rollback Decision Tree

```
Is the error in Phase 5 (Files)?
├── YES → Can we fix and continue?
│         ├── YES → Fix, resume from phase 5
│         └── NO → Rollback phase 5 only, retry
│
└── NO → Is error data-related?
         ├── YES → Is it single record?
         │         ├── YES → Skip record, flag for review
         │         └── NO → Rollback current phase, fix data, retry
         │
         └── NO → Is it infrastructure?
                  ├── YES → Fix infra, resume
                  └── NO → Full rollback, investigate
```

---

## 6. FILE MIGRATION SAFETY PLAN

### 6.1 Pre-Migration File Inventory

```python
# Generate file inventory before migration
async def generate_file_inventory():
    """Create inventory of all files to migrate."""
    
    documents = await mongo_db.employee_documents.find(
        {"file_url": {"$exists": True, "$ne": None}}
    ).to_list(None)
    
    inventory = []
    for doc in documents:
        inventory.append({
            "document_id": doc["id"],
            "employee_id": doc["employee_id"],
            "old_url": doc["file_url"],
            "filename": doc.get("original_filename"),
            "category": doc.get("category"),
            "file_size": None,  # Will be populated during migration
            "checksum": None,   # Will be populated during migration
            "status": "pending"
        })
    
    # Save inventory
    with open("/app/migration/reports/file_inventory.json", "w") as f:
        json.dump(inventory, f, indent=2)
    
    return len(inventory)
```

### 6.2 File Migration Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    FILE MIGRATION PROCESS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. DOWNLOAD FROM EMERGENT                                       │
│     ├── Authenticate with EMERGENT_LLM_KEY                      │
│     ├── Download file to memory                                  │
│     ├── Calculate MD5 checksum                                   │
│     └── Record file size                                         │
│                                                                  │
│  2. VALIDATE FILE                                                │
│     ├── Check file is not empty                                  │
│     ├── Check file is not corrupted                              │
│     ├── Verify MIME type matches extension                       │
│     └── If invalid → flag for manual review                      │
│                                                                  │
│  3. UPLOAD TO SUPABASE STORAGE                                   │
│     ├── Generate storage path: {employee_id}/{category}/{file}  │
│     ├── Upload with correct content-type                         │
│     ├── Verify upload successful                                 │
│     └── Calculate new checksum (optional double-check)           │
│                                                                  │
│  4. UPDATE DATABASE                                              │
│     ├── Set documents.storage_path                               │
│     ├── Preserve documents.old_file_url                          │
│     ├── Record file_size                                         │
│     └── Update inventory status                                  │
│                                                                  │
│  5. VERIFY ACCESS                                                │
│     ├── Generate signed URL                                      │
│     ├── Test download via signed URL                             │
│     └── If failed → flag for investigation                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Batch Processing

```python
# Process files in batches to avoid memory issues
BATCH_SIZE = 10  # Files per batch
MAX_CONCURRENT = 5  # Concurrent downloads

async def migrate_files_batch(document_ids: List[str]):
    """Migrate a batch of files."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def migrate_single(doc_id):
        async with semaphore:
            return await migrate_file(doc_id)
    
    tasks = [migrate_single(doc_id) for doc_id in document_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success = sum(1 for r in results if not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))
    
    return {"success": success, "failed": failed}
```

### 6.4 Failure Recovery

| Failure Type | Recovery Action |
|--------------|-----------------|
| Emergent download timeout | Retry 3 times with backoff |
| Emergent 404 | Flag as missing, continue |
| Supabase upload failed | Retry 3 times, then flag |
| Checksum mismatch | Re-download and re-upload |
| Invalid file | Flag for manual review |

### 6.5 File Migration Validation

```sql
-- After file migration, verify all files accessible
WITH file_status AS (
    SELECT 
        id,
        storage_path,
        old_file_url,
        CASE 
            WHEN storage_path IS NOT NULL THEN 'migrated'
            WHEN old_file_url IS NOT NULL THEN 'pending'
            ELSE 'no_file'
        END as status
    FROM documents
)
SELECT 
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM file_status
GROUP BY status;

-- Expected: 100% migrated or documented exceptions
```

### 6.6 Supabase Storage Verification Script

```python
async def verify_supabase_files():
    """Verify all migrated files are accessible."""
    
    results = {
        "total": 0,
        "accessible": 0,
        "inaccessible": []
    }
    
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, storage_path, employee_id
            FROM documents
            WHERE storage_path IS NOT NULL
        """)
    
    results["total"] = len(rows)
    
    for row in rows:
        try:
            # Try to get signed URL
            url = supabase.storage.from_("documents").create_signed_url(
                row["storage_path"], 60
            )
            
            # Optionally verify URL works
            response = requests.head(url["signedUrl"], timeout=10)
            if response.status_code == 200:
                results["accessible"] += 1
            else:
                results["inaccessible"].append({
                    "id": str(row["id"]),
                    "path": row["storage_path"],
                    "error": f"HTTP {response.status_code}"
                })
        except Exception as e:
            results["inaccessible"].append({
                "id": str(row["id"]),
                "path": row["storage_path"],
                "error": str(e)
            })
    
    return results
```

---

## 7. CUTOVER SEQUENCE

### 7.1 Pre-Cutover Checklist

| # | Item | Verified |
|---|------|----------|
| 7.1.1 | All migration phases complete | ☐ |
| 7.1.2 | All validation queries pass | ☐ |
| 7.1.3 | All files migrated and accessible | ☐ |
| 7.1.4 | Computed fields populated | ☐ |
| 7.1.5 | RLS policies enabled and tested | ☐ |
| 7.1.6 | Backend code updated for Supabase | ☐ |
| 7.1.7 | Frontend code updated for Supabase | ☐ |
| 7.1.8 | New backend tested against Supabase | ☐ |
| 7.1.9 | Staging environment validated | ☐ |
| 7.1.10 | Rollback plan reviewed | ☐ |
| 7.1.11 | Team on standby | ☐ |
| 7.1.12 | Maintenance window active | ☐ |

### 7.2 Cutover Steps

```
TIME 00:00 - MAINTENANCE MODE
├── 1. Enable maintenance page
├── 2. Block new MongoDB writes
├── 3. Notify users of maintenance
└── 4. Confirm no active sessions

TIME 00:10 - FINAL SYNC
├── 5. Run delta migration (changes since migration start)
├── 6. Verify counts match exactly
├── 7. Run full validation suite
└── 8. Generate final comparison report

TIME 00:30 - CODE DEPLOYMENT
├── 9. Deploy Supabase-enabled backend
├── 10. Deploy Supabase-enabled frontend
├── 11. Update environment variables
└── 12. Clear CDN/edge caches

TIME 00:45 - VERIFICATION
├── 13. Run smoke tests (see Section 8)
├── 14. Verify admin login works
├── 15. Verify employee data displays
├── 16. Verify file access works
└── 17. Verify compliance file loads

TIME 01:00 - GO/NO-GO DECISION
├── IF ALL PASS → Proceed to live
├── IF FAILURES → Assess severity
│   ├── Minor issues → Note and proceed
│   └── Major issues → Execute rollback
└── 18. Document decision

TIME 01:15 - GO LIVE
├── 19. Disable maintenance page
├── 20. Monitor error rates
├── 21. Monitor performance metrics
└── 22. Stay on standby for 4 hours

TIME 05:15 - STABILIZATION
├── 23. Review error logs
├── 24. Address any issues found
├── 25. Confirm normal operation
└── 26. Stand down team

TIME +24 HOURS
├── 27. Second review of logs
├── 28. User feedback assessment
└── 29. Plan any fixes

TIME +7 DAYS
├── 30. MongoDB read-only backup
├── 31. Disable MongoDB connection
└── 32. Archive MongoDB data
```

### 7.3 Cutover Rollback Trigger Criteria

**Immediate rollback if:**
- [ ] Admin cannot login
- [ ] Compliance file API returns 500
- [ ] >10% of file accesses fail
- [ ] Data corruption detected
- [ ] >50% of smoke tests fail

**Consider rollback if:**
- [ ] Performance degraded >200%
- [ ] Multiple users report issues
- [ ] 20-50% of smoke tests fail
- [ ] RLS blocking legitimate access

### 7.4 Rollback During Cutover

```bash
# If rollback needed during cutover
# TIME: Must decide within 30 minutes of go-live

# 1. Re-enable maintenance page
# 2. Revert backend deployment
git checkout main
git revert HEAD  # Revert Supabase changes
./deploy.sh

# 3. Revert frontend deployment
cd frontend
git checkout main
git revert HEAD
./deploy.sh

# 4. Restore MongoDB connection
# Update .env: MONGO_URL to original

# 5. Clear caches
# 6. Disable maintenance page
# 7. Verify MongoDB app works
# 8. Post-mortem scheduled
```

---

## 8. POST-CUTOVER SMOKE TESTS

### 8.1 Critical Path Tests

| # | Test | Endpoint/Action | Expected | Verified |
|---|------|-----------------|----------|----------|
| 8.1.1 | Admin login | POST /api/auth/login | Token returned | ☐ |
| 8.1.2 | Get current user | GET /api/auth/me | User object | ☐ |
| 8.1.3 | List employees | GET /api/employees | Array of employees | ☐ |
| 8.1.4 | Get employee detail | GET /api/employees/{id} | Employee object | ☐ |
| 8.1.5 | Get compliance file | GET /api/employees/{id}/compliance-file | Sections object | ☐ |
| 8.1.6 | View document | GET /api/employee-documents/{id}/file | File content | ☐ |
| 8.1.7 | Download document | GET /api/employee-documents/{id}/download | File download | ☐ |
| 8.1.8 | List training | GET /api/employees/{id}/training | Training array | ☐ |
| 8.1.9 | Dashboard stats | GET /api/dashboard/stats | Stats object | ☐ |
| 8.1.10 | Recruitment list | GET /api/recruitment/applicants | Applicants array | ☐ |

### 8.2 Data Integrity Tests

| # | Test | Validation | Verified |
|---|------|------------|----------|
| 8.2.1 | Employee count | API count = DB count | ☐ |
| 8.2.2 | Document count | API count = DB count | ☐ |
| 8.2.3 | Training count | API count = DB count | ☐ |
| 8.2.4 | References present | 2 refs per employee with declared refs | ☐ |
| 8.2.5 | Employment gaps | Gaps visible in compliance file | ☐ |
| 8.2.6 | Check records | RTW/DBS checks visible | ☐ |
| 8.2.7 | Proof documents | Proof linked to checks | ☐ |

### 8.3 Functional Tests

| # | Test | Steps | Expected | Verified |
|---|------|-------|----------|----------|
| 8.3.1 | Upload document | Upload PDF | Document saved | ☐ |
| 8.3.2 | Record RTW check | Fill form, upload proof | Check created | ☐ |
| 8.3.3 | Verify document | Click verify | Status updated | ☐ |
| 8.3.4 | Submit form | Complete health questionnaire | Form saved | ☐ |
| 8.3.5 | Send reference request | Click send | Email sent | ☐ |
| 8.3.6 | Approve recruitment | Click approve | Status changed | ☐ |

### 8.4 Performance Tests

| # | Test | Threshold | Actual | Pass |
|---|------|-----------|--------|------|
| 8.4.1 | Login response | <500ms | ___ms | ☐ |
| 8.4.2 | Employee list (12) | <1s | ___ms | ☐ |
| 8.4.3 | Compliance file | <2s | ___ms | ☐ |
| 8.4.4 | File preview | <3s | ___ms | ☐ |
| 8.4.5 | Dashboard | <1s | ___ms | ☐ |

### 8.5 Automated Smoke Test Script

```python
# /app/migration/scripts/smoke_test.py

"""Post-cutover smoke test suite."""

import asyncio
import aiohttp
import time
from dataclasses import dataclass

API_URL = "https://caretrust-portal.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    error: str = None


async def run_smoke_tests():
    results = []
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Login
        start = time.time()
        try:
            async with session.post(
                f"{API_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
            ) as resp:
                data = await resp.json()
                token = data.get("token")
                passed = resp.status == 200 and token
                results.append(TestResult(
                    "Admin Login",
                    passed,
                    (time.time() - start) * 1000,
                    None if passed else str(data)
                ))
        except Exception as e:
            results.append(TestResult("Admin Login", False, 0, str(e)))
            return results  # Can't continue without token
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 2: Get current user
        start = time.time()
        try:
            async with session.get(f"{API_URL}/auth/me", headers=headers) as resp:
                passed = resp.status == 200
                results.append(TestResult(
                    "Get Current User",
                    passed,
                    (time.time() - start) * 1000
                ))
        except Exception as e:
            results.append(TestResult("Get Current User", False, 0, str(e)))
        
        # Test 3: List employees
        start = time.time()
        try:
            async with session.get(f"{API_URL}/employees", headers=headers) as resp:
                data = await resp.json()
                passed = resp.status == 200 and len(data.get("employees", [])) > 0
                results.append(TestResult(
                    "List Employees",
                    passed,
                    (time.time() - start) * 1000,
                    None if passed else f"Count: {len(data.get('employees', []))}"
                ))
                
                if passed:
                    employee_id = data["employees"][0]["id"]
        except Exception as e:
            results.append(TestResult("List Employees", False, 0, str(e)))
            return results
        
        # Test 4: Get employee detail
        start = time.time()
        try:
            async with session.get(f"{API_URL}/employees/{employee_id}", headers=headers) as resp:
                passed = resp.status == 200
                results.append(TestResult(
                    "Get Employee Detail",
                    passed,
                    (time.time() - start) * 1000
                ))
        except Exception as e:
            results.append(TestResult("Get Employee Detail", False, 0, str(e)))
        
        # Test 5: Get compliance file
        start = time.time()
        try:
            async with session.get(f"{API_URL}/employees/{employee_id}/compliance-file", headers=headers) as resp:
                data = await resp.json()
                passed = resp.status == 200 and "sections" in data
                results.append(TestResult(
                    "Get Compliance File",
                    passed,
                    (time.time() - start) * 1000
                ))
        except Exception as e:
            results.append(TestResult("Get Compliance File", False, 0, str(e)))
        
        # Test 6: Dashboard stats
        start = time.time()
        try:
            async with session.get(f"{API_URL}/dashboard/stats", headers=headers) as resp:
                passed = resp.status == 200
                results.append(TestResult(
                    "Dashboard Stats",
                    passed,
                    (time.time() - start) * 1000
                ))
        except Exception as e:
            results.append(TestResult("Dashboard Stats", False, 0, str(e)))
    
    return results


def print_results(results):
    print("\n" + "=" * 60)
    print("SMOKE TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{status} | {r.name} | {r.duration_ms:.0f}ms")
        if r.error:
            print(f"       Error: {r.error}")
    
    print("=" * 60)
    print(f"TOTAL: {passed}/{total} passed ({passed/total*100:.0f}%)")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    results = asyncio.run(run_smoke_tests())
    success = print_results(results)
    exit(0 if success else 1)
```

---

## 9. FIELDS TO RECOMPUTE VS MIGRATE

### 9.1 Fields to RECOMPUTE (Do Not Migrate Directly)

| Table | Field | Recomputation Logic | Trigger |
|-------|-------|---------------------|---------|
| `employees` | `completion_percentage` | Count completed requirements / total required | On compliance change |
| `employees` | `compliance_score` | Weighted score of verified items | On compliance change |
| `employment_gaps` | `gap_months` | `(gap_end_date - gap_start_date) / 30.44` | On insert |
| `employment_gaps` | `preceding_job_id` | Query `employment_history` for closest job before gap | Post-migration |
| `employment_gaps` | `following_job_id` | Query `employment_history` for closest job after gap | Post-migration |
| `training_records` | `status` | Based on `completion_date`, `expiry_date`, `verified` | On update |
| `recurring_items` | `status` | Based on `next_due_at` vs current date | Daily cron |
| `documents` | `file_url` | Generate signed URL from `storage_path` | On request |

### 9.2 Fields to MIGRATE (Source of Truth in MongoDB)

| Table | Field | Notes |
|-------|-------|-------|
| `employees` | All personal info | First name, last name, email, etc. |
| `employees` | `status` | Normalize to ENUM |
| `employees` | `recruitment_approved` | Boolean flag |
| `employees` | `recruitment_approved_at` | Timestamp |
| `employee_references` | All fields | Extracted from embedded |
| `documents` | `old_file_url` | Preserve original URL |
| `documents` | `expiry_date` | User-entered data |
| `documents` | `verified` | Verification status |
| `*_checks` | `outcome` | Verification result |
| `*_checks` | `notes` | User-entered notes |
| `form_submissions` | `data` | Form field values (JSONB) |
| `audit_log` | All fields | Historical record |

### 9.3 Fields to DERIVE (Computed at Query Time)

| Field | Derivation | Do Not Store |
|-------|------------|--------------|
| `person_stage` | `status` in APPLICANT_STATUSES → 'applicant' else 'employee' | ✓ |
| `work_readiness_3tier` | Call `evaluate_work_readiness()` | ✓ |
| `can_approve_recruitment` | Call `evaluate_recruitment_approval()` | ✓ |
| `document_expired` | `expiry_date < CURRENT_DATE` | ✓ |
| `training_expiring_soon` | `expiry_date BETWEEN NOW() AND NOW() + 30 days` | ✓ |

### 9.4 Recomputation SQL (Phase 10)

```sql
-- Recompute completion_percentage
-- (Simplified example - actual logic is more complex)
UPDATE employees e SET
  completion_percentage = (
    SELECT ROUND(
      COUNT(*) FILTER (WHERE status = 'verified') * 100.0 / 
      NULLIF(COUNT(*), 0)
    )
    FROM documents d
    WHERE d.employee_id = e.id
    AND d.is_current = true
  );

-- Recompute gap_months
UPDATE employment_gaps SET
  gap_months = ROUND(
    EXTRACT(EPOCH FROM (gap_end_date - gap_start_date)) / (30.44 * 86400), 
    1
  );

-- Link gaps to jobs
UPDATE employment_gaps g SET
  preceding_job_id = (
    SELECT id FROM employment_history h 
    WHERE h.employee_id = g.employee_id 
    AND h.end_date <= g.gap_start_date
    ORDER BY h.end_date DESC 
    LIMIT 1
  ),
  following_job_id = (
    SELECT id FROM employment_history h 
    WHERE h.employee_id = g.employee_id 
    AND h.start_date >= g.gap_end_date
    ORDER BY h.start_date ASC 
    LIMIT 1
  );

-- Recompute training_records status
UPDATE training_records SET
  status = CASE
    WHEN completion_date IS NULL THEN 'missing'
    WHEN expiry_date IS NULL THEN 'current'
    WHEN expiry_date < CURRENT_DATE THEN 'expired'
    WHEN expiry_date < CURRENT_DATE + INTERVAL '30 days' THEN 'expiring'
    ELSE 'current'
  END;

-- Recompute recurring_items status
UPDATE recurring_items SET
  status = CASE
    WHEN next_due_at < CURRENT_DATE THEN 'overdue'
    WHEN next_due_at <= CURRENT_DATE + INTERVAL '7 days' THEN 'due_now'
    ELSE 'upcoming'
  END;
```

### 9.5 Recomputation Triggers (Post-Migration)

```sql
-- Trigger to recompute training status on update
CREATE OR REPLACE FUNCTION recompute_training_status()
RETURNS TRIGGER AS $$
BEGIN
  NEW.status = CASE
    WHEN NEW.completion_date IS NULL THEN 'missing'
    WHEN NEW.expiry_date IS NULL THEN 'current'
    WHEN NEW.expiry_date < CURRENT_DATE THEN 'expired'
    WHEN NEW.expiry_date < CURRENT_DATE + INTERVAL '30 days' THEN 'expiring'
    ELSE 'current'
  END;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER training_status_trigger
BEFORE INSERT OR UPDATE ON training_records
FOR EACH ROW
EXECUTE FUNCTION recompute_training_status();

-- Daily cron job for recurring items (via Supabase Edge Function or external)
-- Schedule: 0 1 * * * (1am daily)
-- Action: Call UPDATE recurring_items SET status = ... query
```

---

## SUMMARY CHECKLIST

### Before Migration
- [ ] All preflight items complete
- [ ] Schema deployed and validated
- [ ] Data cleanup complete
- [ ] Staging migration successful
- [ ] Team ready

### During Migration
- [ ] Each phase completes
- [ ] Each validation passes
- [ ] Files transfer complete
- [ ] No blocking errors

### Cutover
- [ ] Final sync complete
- [ ] New code deployed
- [ ] Smoke tests pass
- [ ] Go-live decision made

### Post-Cutover
- [ ] Monitor 4 hours
- [ ] Address issues
- [ ] Second review at 24 hours
- [ ] MongoDB archived at 7 days

---

**Document Status:** Ready for review  
**Next Action:** Approve runbook, then create migration scripts
