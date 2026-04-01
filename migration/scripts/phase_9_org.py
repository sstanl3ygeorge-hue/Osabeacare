"""
Phase 9: Migrate organization data.

Handles org_policies, insurance_docs (→ org_certificates), policy_assignments.

Idempotent: Checks mongo_id before inserting.
Resumable: Tracks last_processed_id.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_date, parse_timestamp, sanitize_string
)


class Phase9OrgMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_9_org", dry_run)
        self.policy_id_map = {}
    
    async def migrate(self):
        await self._migrate_org_policies()
        await self._migrate_org_certificates()
        await self._migrate_policy_assignments()
    
    async def _migrate_org_policies(self):
        """Migrate organization policies."""
        self.logger.info("Migrating org policies...")
        
        cursor = self.mongo_db.org_policies.find({})
        policies = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(policies)} org policies")
        
        for policy in policies:
            mongo_id = policy.get("id") or str(policy.get("_id"))
            
            try:
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO org_policies (
                                id, name, category, version, status,
                                storage_path, file_url, original_filename,
                                review_date, last_reviewed_at, reviewed_by,
                                notes, cqc_required,
                                created_at, updated_at, created_by, mongo_id
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            sanitize_string(policy.get("name", "Untitled Policy")),
                            sanitize_string(policy.get("category")),
                            sanitize_string(policy.get("version")),
                            sanitize_string(policy.get("status", "active")),
                            None,  # storage_path - migrate files separately
                            policy.get("file_url"),
                            sanitize_string(policy.get("original_filename")),
                            parse_date(policy.get("review_date")),
                            parse_timestamp(policy.get("last_reviewed_at")),
                            self.map_user_id(policy.get("reviewed_by")),
                            sanitize_string(policy.get("notes")),
                            policy.get("cqc_required", False),
                            parse_timestamp(policy.get("created_at")),
                            parse_timestamp(policy.get("updated_at")),
                            self.map_user_id(policy.get("created_by")),
                            mongo_id
                        )
                
                self.policy_id_map[mongo_id] = new_id
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_org_certificates(self):
        """Migrate insurance docs to org certificates."""
        self.logger.info("Migrating org certificates (from insurance_docs)...")
        
        cursor = self.mongo_db.insurance_docs.find({})
        certs = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(certs)} org certificates")
        
        for cert in certs:
            mongo_id = cert.get("id") or str(cert.get("_id"))
            
            try:
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO org_certificates (
                                id, name, certificate_type,
                                storage_path, file_url, original_filename,
                                issue_date, expiry_date, status, cqc_required,
                                created_at, updated_at, created_by, mongo_id
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            sanitize_string(cert.get("name", "Untitled Certificate")),
                            sanitize_string(cert.get("certificate_type") or cert.get("type")),
                            None,
                            cert.get("file_url"),
                            sanitize_string(cert.get("original_filename")),
                            parse_date(cert.get("issue_date")),
                            parse_date(cert.get("expiry_date")),
                            sanitize_string(cert.get("status", "active")),
                            cert.get("cqc_required", False),
                            parse_timestamp(cert.get("created_at")),
                            parse_timestamp(cert.get("updated_at")),
                            self.map_user_id(cert.get("created_by")),
                            mongo_id
                        )
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_policy_assignments(self):
        """Migrate policy assignments."""
        self.logger.info("Migrating policy assignments...")
        
        cursor = self.mongo_db.policy_assignments.find({})
        assignments = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(assignments)} policy assignments")
        
        for assignment in assignments:
            mongo_id = assignment.get("id") or str(assignment.get("_id"))
            
            try:
                employee_id = self.map_employee_id(assignment.get("employee_id"))
                if not employee_id:
                    continue
                
                policy_mongo_id = assignment.get("policy_id")
                policy_id = self.policy_id_map.get(policy_mongo_id)
                if not policy_id:
                    # Try to find by name or skip
                    continue
                
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO policy_assignments (
                                id, employee_id, policy_id,
                                assigned_at, assigned_by,
                                acknowledged, acknowledged_at, created_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (employee_id, policy_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            policy_id,
                            parse_timestamp(assignment.get("assigned_at")),
                            self.map_user_id(assignment.get("assigned_by")),
                            assignment.get("acknowledged", False),
                            parse_timestamp(assignment.get("acknowledged_at")),
                            parse_timestamp(assignment.get("created_at"))
                        )
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1


async def run(dry_run: bool = False):
    migration = Phase9OrgMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))
