"""
Phase 10: Migrate audit logs.

Handles audit_logs and audit_log collections (both variants exist in the codebase).
Maps employee and user IDs to new UUIDs.

Idempotent: Checks mongo_id before inserting.
Resumable: Tracks last_processed_id.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_timestamp, sanitize_string, safe_jsonb
)


class Phase10AuditLogsMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_10_audit_logs", dry_run)
    
    async def migrate(self):
        # Migrate from both collection names (audit_logs and audit_log)
        await self._migrate_audit_collection("audit_logs")
        await self._migrate_audit_collection("audit_log")
    
    async def _migrate_audit_collection(self, collection_name: str):
        """Migrate audit logs from a specific collection."""
        self.logger.info(f"Migrating {collection_name}...")
        
        # Check if collection exists
        collections = await self.mongo_db.list_collection_names()
        if collection_name not in collections:
            self.logger.info(f"Collection {collection_name} not found, skipping")
            return
        
        cursor = self.mongo_db[collection_name].find({})
        logs = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(logs)} audit logs in {collection_name}")
        
        # Sort for consistent ordering
        logs.sort(key=lambda x: str(x.get("created_at", "") or x.get("_id", "")))
        
        for log in logs:
            mongo_id = log.get("id") or str(log.get("_id"))
            
            # Resume support
            if self.result.last_processed_id:
                if mongo_id <= self.result.last_processed_id:
                    continue
            
            try:
                await self._migrate_audit_log(log, mongo_id)
                self.result.migrated_records += 1
                self.result.total_records += 1
                self.result.last_processed_id = mongo_id
                
                # Periodic state save
                if self.result.migrated_records % 100 == 0:
                    await self._save_state()
                    self.logger.info(f"Migrated {self.result.migrated_records} audit logs...")
                    
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_audit_log(self, log: dict, mongo_id: str):
        """Migrate a single audit log entry."""
        
        # Idempotent check
        if await self.is_already_migrated("audit_logs", mongo_id):
            return
        
        new_id = generate_uuid()
        
        # Map employee ID if present
        employee_id = None
        emp_mongo_id = log.get("employee_id")
        if emp_mongo_id:
            employee_id = self.map_employee_id(emp_mongo_id)
        
        # Map user ID if present
        user_id = None
        user_mongo_id = log.get("user_id") or log.get("performed_by")
        if user_mongo_id:
            user_id = self.map_user_id(user_mongo_id)
        
        # Extract action and entity info
        action = log.get("action") or log.get("type") or "unknown"
        entity_type = log.get("entity_type") or log.get("target_type")
        entity_id = log.get("entity_id") or log.get("target_id")
        
        # Handle details - could be nested or flat
        details = log.get("details") or log.get("data") or {}
        if isinstance(details, str):
            details = {"message": details}
        
        old_values = log.get("old_values") or log.get("before")
        new_values = log.get("new_values") or log.get("after")
        
        if not self.dry_run and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO audit_logs (
                        id, action, entity_type, entity_id,
                        employee_id, user_id, user_email, user_name,
                        details, old_values, new_values,
                        ip_address, user_agent,
                        created_at, mongo_id
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (mongo_id) DO NOTHING
                """,
                    new_id,
                    sanitize_string(action, 255),
                    sanitize_string(entity_type, 100),
                    sanitize_string(entity_id, 255),
                    employee_id,
                    user_id,
                    sanitize_string(log.get("user_email") or log.get("email")),
                    sanitize_string(log.get("user_name") or log.get("name") or log.get("performed_by_name")),
                    safe_jsonb(details),
                    safe_jsonb(old_values),
                    safe_jsonb(new_values),
                    sanitize_string(log.get("ip_address") or log.get("ip")),
                    sanitize_string(log.get("user_agent")),
                    parse_timestamp(log.get("created_at") or log.get("timestamp")),
                    mongo_id
                )


async def run(dry_run: bool = False):
    migration = Phase10AuditLogsMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))
