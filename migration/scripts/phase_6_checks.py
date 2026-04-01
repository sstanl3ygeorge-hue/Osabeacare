"""
Phase 6: Migrate verification checks from MongoDB to Postgres.

Handles rtw_checks, dbs_checks, identity_verifications, address_verifications.
Links proof_document_id to documents table using mapping.

Idempotent: Checks mongo_id before inserting.
Resumable: Processes each collection separately with tracking.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_date, parse_timestamp, sanitize_string
)
from config.mappings import (
    VERIFICATION_OUTCOME_MAP, CHECK_METHOD_MAP, get_mapped_value
)


class Phase6ChecksMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_6_checks", dry_run)
    
    async def migrate(self):
        # Migrate each check collection
        await self._migrate_rtw_checks()
        await self._migrate_dbs_checks()
        await self._migrate_identity_checks()
        await self._migrate_address_checks()
    
    async def _migrate_rtw_checks(self):
        """Migrate Right to Work checks."""
        self.logger.info("Migrating RTW checks...")
        
        cursor = self.mongo_db.rtw_checks.find({})
        checks = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(checks)} RTW checks")
        
        for check in checks:
            mongo_id = check.get("id") or str(check.get("_id"))
            
            try:
                if await self.is_already_migrated("rtw_checks", mongo_id):
                    self.record_skip(mongo_id, "already exists")
                    continue
                
                employee_id = self.map_employee_id(check.get("employee_id"))
                if not employee_id:
                    self.record_warning(f"No employee mapping for RTW check {mongo_id}")
                    continue
                
                # Map proof document
                proof_doc_id = self.map_document_id(check.get("evidence_document_id"))
                
                method = get_mapped_value(
                    check.get("method", "manual_document_review"),
                    CHECK_METHOD_MAP,
                    "manual_document_review"
                )
                
                outcome = get_mapped_value(
                    check.get("outcome", "awaiting_review"),
                    VERIFICATION_OUTCOME_MAP,
                    "awaiting_review"
                )
                
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO rtw_checks (
                                id, employee_id, method, checked_at, checked_by, checked_by_name,
                                outcome, source_status_type, follow_up_due_at, proof_document_id,
                                notes, is_current, superseded_at, record_version,
                                created_at, created_by, mongo_id
                            )
                            VALUES ($1, $2, $3::check_method, $4, $5, $6, $7::verification_outcome, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            method,
                            parse_timestamp(check.get("checked_at")) or parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("checked_by")),
                            sanitize_string(check.get("checked_by_name")),
                            outcome,
                            sanitize_string(check.get("source_status_type")),
                            parse_date(check.get("follow_up_due_at")),
                            proof_doc_id,
                            sanitize_string(check.get("notes")),
                            check.get("is_current", True),
                            parse_timestamp(check.get("superseded_at")),
                            check.get("record_version", 1),
                            parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("created_by")),
                            mongo_id
                        )
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_dbs_checks(self):
        """Migrate DBS checks."""
        self.logger.info("Migrating DBS checks...")
        
        cursor = self.mongo_db.dbs_checks.find({})
        checks = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(checks)} DBS checks")
        
        for check in checks:
            mongo_id = check.get("id") or str(check.get("_id"))
            
            try:
                if await self.is_already_migrated("dbs_checks", mongo_id):
                    self.record_skip(mongo_id, "already exists")
                    continue
                
                employee_id = self.map_employee_id(check.get("employee_id"))
                if not employee_id:
                    self.record_warning(f"No employee mapping for DBS check {mongo_id}")
                    continue
                
                proof_doc_id = self.map_document_id(check.get("evidence_document_id"))
                
                method = get_mapped_value(
                    check.get("method", "manual_certificate_review"),
                    CHECK_METHOD_MAP,
                    "manual_certificate_review"
                )
                
                outcome = get_mapped_value(
                    check.get("outcome", "awaiting_review"),
                    VERIFICATION_OUTCOME_MAP,
                    "awaiting_review"
                )
                
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO dbs_checks (
                                id, employee_id, method, checked_at, checked_by, checked_by_name,
                                outcome, certificate_number, review_due_at, proof_document_id,
                                notes, is_current, superseded_at, record_version,
                                created_at, created_by, mongo_id
                            )
                            VALUES ($1, $2, $3::check_method, $4, $5, $6, $7::verification_outcome, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            method,
                            parse_timestamp(check.get("checked_at")) or parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("checked_by")),
                            sanitize_string(check.get("checked_by_name")),
                            outcome,
                            sanitize_string(check.get("certificate_number")),
                            parse_date(check.get("review_due_at")),
                            proof_doc_id,
                            sanitize_string(check.get("notes")),
                            check.get("is_current", True),
                            parse_timestamp(check.get("superseded_at")),
                            check.get("record_version", 1),
                            parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("created_by")),
                            mongo_id
                        )
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_identity_checks(self):
        """Migrate identity verifications with junction table."""
        self.logger.info("Migrating identity checks...")
        
        cursor = self.mongo_db.identity_verifications.find({})
        checks = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(checks)} identity checks")
        
        for check in checks:
            mongo_id = check.get("id") or str(check.get("_id"))
            
            try:
                if await self.is_already_migrated("identity_checks", mongo_id):
                    self.record_skip(mongo_id, "already exists")
                    continue
                
                employee_id = self.map_employee_id(check.get("employee_id"))
                if not employee_id:
                    self.record_warning(f"No employee mapping for identity check {mongo_id}")
                    continue
                
                proof_doc_id = self.map_document_id(check.get("evidence_document_id"))
                
                method = get_mapped_value(
                    check.get("method", "in_person"),
                    CHECK_METHOD_MAP,
                    "in_person"
                )
                
                outcome = get_mapped_value(
                    check.get("outcome", "awaiting_review"),
                    VERIFICATION_OUTCOME_MAP,
                    "awaiting_review"
                )
                
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO identity_checks (
                                id, employee_id, method, checked_at, checked_by, checked_by_name,
                                outcome, proof_document_id, notes, is_current,
                                superseded_at, record_version, created_at, created_by, mongo_id
                            )
                            VALUES ($1, $2, $3::check_method, $4, $5, $6, $7::verification_outcome, $8, $9, $10, $11, $12, $13, $14, $15)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            method,
                            parse_timestamp(check.get("checked_at")) or parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("checked_by")),
                            sanitize_string(check.get("checked_by_name")),
                            outcome,
                            proof_doc_id,
                            sanitize_string(check.get("notes")),
                            check.get("is_current", True),
                            parse_timestamp(check.get("superseded_at")),
                            check.get("record_version", 1),
                            parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("created_by")),
                            mongo_id
                        )
                        
                        # Insert junction table entries for verified document IDs
                        doc_ids = check.get("evidence_document_ids", [])
                        for doc_mongo_id in doc_ids:
                            doc_pg_id = self.map_document_id(doc_mongo_id)
                            if doc_pg_id:
                                await conn.execute("""
                                    INSERT INTO identity_check_documents (id, identity_check_id, document_id)
                                    VALUES ($1, $2, $3)
                                    ON CONFLICT DO NOTHING
                                """, generate_uuid(), new_id, doc_pg_id)
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_address_checks(self):
        """Migrate address verifications with junction table."""
        self.logger.info("Migrating address checks...")
        
        cursor = self.mongo_db.address_verifications.find({})
        checks = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(checks)} address checks")
        
        for check in checks:
            mongo_id = check.get("id") or str(check.get("_id"))
            
            try:
                if await self.is_already_migrated("address_checks", mongo_id):
                    self.record_skip(mongo_id, "already exists")
                    continue
                
                employee_id = self.map_employee_id(check.get("employee_id"))
                if not employee_id:
                    self.record_warning(f"No employee mapping for address check {mongo_id}")
                    continue
                
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO address_checks (
                                id, employee_id, verified_at, verified_by, verified_by_name,
                                verified_count, minimum_required, meets_requirement, recency_policy_passed,
                                notes, is_current, superseded_at, record_version,
                                created_at, created_by, mongo_id
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            parse_timestamp(check.get("verified_at")) or parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("verified_by")),
                            sanitize_string(check.get("verified_by_name")),
                            check.get("verified_count", 0),
                            check.get("minimum_required", 2),
                            check.get("meets_requirement", False),
                            check.get("recency_policy_passed"),
                            sanitize_string(check.get("notes")),
                            check.get("is_current", True),
                            parse_timestamp(check.get("superseded_at")),
                            check.get("record_version", 1),
                            parse_timestamp(check.get("created_at")),
                            self.map_user_id(check.get("created_by")),
                            mongo_id
                        )
                        
                        # Insert junction table entries
                        doc_ids = check.get("verified_document_ids", [])
                        for doc_mongo_id in doc_ids:
                            doc_pg_id = self.map_document_id(doc_mongo_id)
                            if doc_pg_id:
                                await conn.execute("""
                                    INSERT INTO address_check_documents (id, address_check_id, document_id)
                                    VALUES ($1, $2, $3)
                                    ON CONFLICT DO NOTHING
                                """, generate_uuid(), new_id, doc_pg_id)
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1


async def run(dry_run: bool = False):
    """Entry point for phase 6."""
    migration = Phase6ChecksMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    asyncio.run(run(dry_run=args.dry_run))
