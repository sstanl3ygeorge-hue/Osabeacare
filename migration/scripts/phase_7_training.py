"""
Phase 7: Migrate training records and catalogue.

Handles training_catalogue and training_records collections.
Links certificate_document_id to documents table.

Idempotent: Checks mongo_id before inserting.
Resumable: Tracks last_processed_id.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_date, parse_timestamp, sanitize_string, safe_jsonb
)


class Phase7TrainingMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_7_training", dry_run)
        self.training_id_map = {}  # catalogue mongo_id -> pg_id
    
    async def migrate(self):
        await self._migrate_training_catalogue()
        await self._migrate_training_records()
    
    async def _migrate_training_catalogue(self):
        """Migrate training catalogue (reference table)."""
        self.logger.info("Migrating training catalogue...")
        
        cursor = self.mongo_db.training_catalogue.find({})
        items = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(items)} training catalogue items")
        
        for item in items:
            mongo_id = item.get("id") or item.get("code") or str(item.get("_id"))
            
            try:
                new_id = generate_uuid()
                code = item.get("code") or item.get("id") or mongo_id
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        # Check if exists by code
                        existing = await conn.fetchval(
                            "SELECT id FROM training_catalogue WHERE code = $1", code
                        )
                        if existing:
                            self.training_id_map[mongo_id] = str(existing)
                            continue
                        
                        await conn.execute("""
                            INSERT INTO training_catalogue (
                                id, code, name, description, category,
                                is_mandatory, is_blocker, evidence_required,
                                validity_months, applicable_roles, sort_order, active,
                                created_at, updated_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                            ON CONFLICT (code) DO NOTHING
                        """,
                            new_id,
                            code,
                            sanitize_string(item.get("name", code)),
                            sanitize_string(item.get("description")),
                            sanitize_string(item.get("category")),
                            item.get("is_mandatory", item.get("mandatory", False)),
                            item.get("is_blocker", False),
                            item.get("evidence_required", True),
                            item.get("validity_months"),
                            item.get("applicable_roles"),
                            item.get("sort_order"),
                            item.get("active", True),
                            parse_timestamp(item.get("created_at")),
                            parse_timestamp(item.get("updated_at"))
                        )
                
                self.training_id_map[mongo_id] = new_id
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_training_records(self):
        """Migrate training records."""
        self.logger.info("Migrating training records...")
        
        cursor = self.mongo_db.training_records.find({})
        records = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(records)} training records")
        
        for record in records:
            mongo_id = record.get("id") or str(record.get("_id"))
            
            try:
                employee_id = self.map_employee_id(record.get("employee_id"))
                if not employee_id:
                    self.record_warning(f"No employee mapping for training {mongo_id}")
                    continue
                
                # Map training catalogue ID
                req_id = record.get("requirement_id") or record.get("training_id")
                training_id = self.training_id_map.get(req_id)
                
                # Map certificate document
                cert_doc_id = self.map_document_id(record.get("certificate_document_id"))
                
                new_id = generate_uuid()
                
                # Determine status
                status = record.get("status", "missing")
                if status not in ("missing", "current", "expiring", "expired"):
                    status = "missing"
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO training_records (
                                id, employee_id, training_id,
                                completion_date, expiry_date, completion_method,
                                certificate_document_id, status,
                                verified, verified_at, verified_by, verified_by_name,
                                is_current, superseded_at, superseded_by,
                                created_at, updated_at, mongo_id
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            training_id,
                            parse_date(record.get("completion_date")),
                            parse_date(record.get("expiry_date")),
                            sanitize_string(record.get("completion_method")),
                            cert_doc_id,
                            status,
                            record.get("verified", False),
                            parse_timestamp(record.get("verified_at")),
                            self.map_user_id(record.get("verified_by")),
                            sanitize_string(record.get("verified_by_name")),
                            record.get("is_current", True),
                            parse_timestamp(record.get("superseded_at")),
                            None,
                            parse_timestamp(record.get("created_at")),
                            parse_timestamp(record.get("updated_at")),
                            mongo_id
                        )
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1


async def run(dry_run: bool = False):
    migration = Phase7TrainingMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))
