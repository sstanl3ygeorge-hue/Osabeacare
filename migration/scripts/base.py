"""
Base migration infrastructure.
Provides database connections, state tracking, logging, and error handling.
All migrations inherit from BaseMigration for consistent behavior.
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg

import sys
sys.path.insert(0, '/app/migration')

from config.settings import (
    MONGO_URL, MONGO_DB_NAME, SUPABASE_DB_URL, REPORTS_DIR
)


class MigrationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class PhaseResult:
    """Result of a migration phase."""
    phase: str
    status: MigrationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_records: int = 0
    migrated_records: int = 0
    skipped_records: int = 0
    failed_records: int = 0
    last_processed_id: Optional[str] = None
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
            "skipped_records": self.skipped_records,
            "failed_records": self.failed_records,
            "last_processed_id": self.last_processed_id,
            "success_rate": f"{(self.migrated_records / max(self.total_records, 1) * 100):.1f}%",
            "error_count": len(self.errors),
            "errors": self.errors[:20],
            "warning_count": len(self.warnings),
            "warnings": self.warnings[:20],
        }


class BaseMigration(ABC):
    """
    Base class for all migration phases.
    Provides:
    - Database connections (MongoDB source, Postgres target)
    - ID mapping lookup/storage
    - State persistence (resumable)
    - Logging
    - Error tracking
    """
    
    def __init__(self, phase_name: str, dry_run: bool = False):
        self.phase_name = phase_name
        self.dry_run = dry_run
        
        # Set up logging
        self.logger = logging.getLogger(f"migration.{phase_name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Database connections
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.mongo_db = None
        self.pg_pool: Optional[asyncpg.Pool] = None
        
        # ID mappings (loaded from DB)
        self.user_id_map: Dict[str, str] = {}
        self.employee_id_map: Dict[str, str] = {}
        self.document_id_map: Dict[str, str] = {}
        
        # Result tracking
        self.result = PhaseResult(
            phase=phase_name,
            status=MigrationStatus.PENDING,
            started_at=datetime.now(timezone.utc)
        )
    
    async def setup(self):
        """Initialize database connections and load mappings."""
        self.logger.info(f"Setting up {self.phase_name}...")
        
        # MongoDB connection
        self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        self.mongo_db = self.mongo_client[MONGO_DB_NAME]
        
        # Test MongoDB connection
        try:
            await self.mongo_db.command("ping")
            self.logger.info("MongoDB connected")
        except Exception as e:
            raise ConnectionError(f"MongoDB connection failed: {e}")
        
        # Postgres connection pool
        if SUPABASE_DB_URL:
            self.pg_pool = await asyncpg.create_pool(
                SUPABASE_DB_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            self.logger.info("Postgres connected")
        else:
            self.logger.warning("No SUPABASE_DB_URL - running in MongoDB-only mode")
        
        # Load existing mappings
        await self._load_mappings()
        
        # Load last state for resumption
        await self._load_state()
    
    async def teardown(self):
        """Close database connections."""
        if self.mongo_client:
            self.mongo_client.close()
        if self.pg_pool:
            await self.pg_pool.close()
    
    async def _load_mappings(self):
        """Load ID mappings from mapping tables."""
        if not self.pg_pool:
            return
            
        async with self.pg_pool.acquire() as conn:
            # User mappings
            rows = await conn.fetch("SELECT old_id, new_id::text FROM migration_user_map")
            self.user_id_map = {r["old_id"]: r["new_id"] for r in rows}
            self.logger.info(f"Loaded {len(self.user_id_map)} user mappings")
            
            # Employee mappings
            rows = await conn.fetch("SELECT old_id, new_id::text FROM migration_employee_map")
            self.employee_id_map = {r["old_id"]: r["new_id"] for r in rows}
            self.logger.info(f"Loaded {len(self.employee_id_map)} employee mappings")
            
            # Document mappings
            rows = await conn.fetch("SELECT old_id, new_id::text FROM migration_document_map")
            self.document_id_map = {r["old_id"]: r["new_id"] for r in rows}
            self.logger.info(f"Loaded {len(self.document_id_map)} document mappings")
    
    async def _load_state(self):
        """Load previous state for resumption."""
        if not self.pg_pool:
            return
            
        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM migration_state WHERE phase = $1",
                self.phase_name
            )
            if row and row["status"] == "in_progress":
                self.result.last_processed_id = row["last_processed_id"]
                self.result.migrated_records = row["migrated_records"] or 0
                self.result.failed_records = row["failed_records"] or 0
                self.logger.info(f"Resuming from {self.result.last_processed_id}")
    
    async def _save_state(self):
        """Persist current state for resumption."""
        if not self.pg_pool or self.dry_run:
            return
            
        async with self.pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO migration_state 
                    (phase, status, started_at, completed_at, total_records, 
                     migrated_records, failed_records, last_processed_id, error_log)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (phase) DO UPDATE SET
                    status = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at,
                    total_records = EXCLUDED.total_records,
                    migrated_records = EXCLUDED.migrated_records,
                    failed_records = EXCLUDED.failed_records,
                    last_processed_id = EXCLUDED.last_processed_id,
                    error_log = EXCLUDED.error_log
            """,
                self.phase_name,
                self.result.status.value,
                self.result.started_at,
                self.result.completed_at,
                self.result.total_records,
                self.result.migrated_records,
                self.result.failed_records,
                self.result.last_processed_id,
                json.dumps(self.result.errors[:100])
            )
    
    async def save_user_mapping(self, old_id: str, new_id: str):
        """Save user ID mapping."""
        if self.dry_run or not self.pg_pool:
            self.user_id_map[old_id] = new_id
            return
            
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO migration_user_map (old_id, new_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                old_id, new_id
            )
        self.user_id_map[old_id] = new_id
    
    async def save_employee_mapping(self, old_id: str, new_id: str):
        """Save employee ID mapping."""
        if self.dry_run or not self.pg_pool:
            self.employee_id_map[old_id] = new_id
            return
            
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO migration_employee_map (old_id, new_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                old_id, new_id
            )
        self.employee_id_map[old_id] = new_id
    
    async def save_document_mapping(self, old_id: str, new_id: str):
        """Save document ID mapping."""
        if self.dry_run or not self.pg_pool:
            self.document_id_map[old_id] = new_id
            return
            
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO migration_document_map (old_id, new_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                old_id, new_id
            )
        self.document_id_map[old_id] = new_id
    
    def map_user_id(self, old_id: Optional[str]) -> Optional[str]:
        """Map MongoDB user ID to Postgres UUID."""
        if not old_id:
            return None
        return self.user_id_map.get(old_id)
    
    def map_employee_id(self, old_id: Optional[str]) -> Optional[str]:
        """Map MongoDB employee ID to Postgres UUID."""
        if not old_id:
            return None
        return self.employee_id_map.get(old_id)
    
    def map_document_id(self, old_id: Optional[str]) -> Optional[str]:
        """Map MongoDB document ID to Postgres UUID."""
        if not old_id:
            return None
        return self.document_id_map.get(old_id)
    
    def record_error(self, record_id: str, error: str, data: dict = None):
        """Record a migration error for a specific record."""
        self.result.failed_records += 1
        self.result.errors.append({
            "record_id": record_id,
            "error": str(error)[:500],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.logger.warning(f"Error migrating {record_id}: {error}")
    
    def record_skip(self, record_id: str, reason: str):
        """Record a skipped record (already migrated)."""
        self.result.skipped_records += 1
        self.logger.debug(f"Skipped {record_id}: {reason}")
    
    def record_warning(self, message: str):
        """Record a migration warning."""
        self.result.warnings.append(message)
        self.logger.warning(message)
    
    async def run(self) -> PhaseResult:
        """Execute the migration phase."""
        try:
            await self.setup()
            
            self.result.status = MigrationStatus.IN_PROGRESS
            await self._save_state()
            
            self.logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Starting {self.phase_name}...")
            
            # Execute migration (implemented by subclass)
            await self.migrate()
            
            self.result.status = MigrationStatus.COMPLETED
            self.result.completed_at = datetime.now(timezone.utc)
            
            self.logger.info(
                f"Completed {self.phase_name}: "
                f"{self.result.migrated_records}/{self.result.total_records} migrated, "
                f"{self.result.skipped_records} skipped, "
                f"{self.result.failed_records} failed"
            )
            
        except Exception as e:
            self.result.status = MigrationStatus.FAILED
            self.result.completed_at = datetime.now(timezone.utc)
            self.result.errors.append({
                "type": "fatal",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.logger.error(f"Migration failed: {e}", exc_info=True)
            raise
            
        finally:
            await self._save_state()
            await self._save_report()
            await self.teardown()
        
        return self.result
    
    async def _save_report(self):
        """Save migration report to file."""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = f"{REPORTS_DIR}/{self.phase_name}_{timestamp}.json"
        
        with open(report_path, "w") as f:
            json.dump(self.result.to_dict(), f, indent=2)
        
        self.logger.info(f"Report saved: {report_path}")
    
    @abstractmethod
    async def migrate(self):
        """Override in subclass to implement migration logic."""
        pass
    
    async def is_already_migrated(self, table: str, mongo_id: str) -> bool:
        """Check if a record is already migrated (idempotent check)."""
        if not self.pg_pool:
            return False
            
        async with self.pg_pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT 1 FROM {table} WHERE mongo_id = $1",
                mongo_id
            )
            return result is not None
