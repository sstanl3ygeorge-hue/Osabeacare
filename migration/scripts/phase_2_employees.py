"""
Phase 2: Migrate employees from MongoDB to Postgres.

Handles both applicants and employees (same collection, different status).
Extracts references and employment data to separate tables in Phase 3.

Idempotent: Checks mongo_id before inserting.
Resumable: Tracks last_processed_id in migration_state.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_date, parse_timestamp, sanitize_string, 
    extract_mongo_id, safe_jsonb
)
from config.mappings import PERSON_STATUS_MAP, get_mapped_value


class Phase2EmployeeMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_2_employees", dry_run)
    
    async def migrate(self):
        # Count total employees
        cursor = self.mongo_db.employees.find({})
        employees = await cursor.to_list(length=None)
        self.result.total_records = len(employees)
        
        self.logger.info(f"Found {len(employees)} employees to migrate")
        
        # Sort for consistent ordering
        employees.sort(key=lambda x: x.get("id", "") or str(x.get("_id", "")))
        
        for emp in employees:
            mongo_id = emp.get("id") or str(emp.get("_id"))
            
            # Resume support
            if self.result.last_processed_id:
                if mongo_id <= self.result.last_processed_id:
                    self.record_skip(mongo_id, "already processed")
                    continue
            
            try:
                await self._migrate_employee(emp)
                self.result.migrated_records += 1
                self.result.last_processed_id = mongo_id
                
                if self.result.migrated_records % 10 == 0:
                    await self._save_state()
                    
            except Exception as e:
                self.record_error(mongo_id, str(e))
    
    async def _migrate_employee(self, emp: dict):
        """Migrate a single employee."""
        mongo_id = emp.get("id") or str(emp.get("_id"))
        
        # Idempotent check
        if await self.is_already_migrated("employees", mongo_id):
            self.record_skip(mongo_id, "already exists")
            return
        
        if mongo_id in self.employee_id_map:
            self.record_skip(mongo_id, "already in mapping")
            return
        
        new_id = generate_uuid()
        
        # Map status
        status = get_mapped_value(
            emp.get("status", "new"),
            PERSON_STATUS_MAP,
            "new"
        )
        
        # Map user IDs for FKs
        manager_id = self.map_user_id(emp.get("manager_id"))
        approved_by = self.map_user_id(emp.get("recruitment_approved_by"))
        
        name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        self.logger.debug(f"Migrating employee: {name} ({mongo_id})")
        
        if not self.dry_run and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO employees (
                        id, employee_code, first_name, middle_name, last_name,
                        preferred_name, date_of_birth, ni_number,
                        email, phone, phone_secondary,
                        address_line_1, address_line_2, city, county, postcode, country,
                        role, status, start_date, manager_id, manager_name, branch,
                        profile_photo_url, driver_status, has_driving_licence, has_own_vehicle,
                        criminal_offence_declared, dbs_update_service_consent,
                        health_issue_declared, professional_misconduct_declared, working_time_opt_out,
                        next_of_kin_name, next_of_kin_relationship, next_of_kin_phone,
                        next_of_kin_address, next_of_kin_city, next_of_kin_postcode,
                        recruitment_approved, recruitment_approved_at, recruitment_approved_by,
                        cv_extracted_roles, name_mismatch_status, name_mismatch_review,
                        completion_percentage, compliance_score, notes,
                        created_at, updated_at, mongo_id, migration_reviewed
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19::person_status, $20,
                        $21, $22, $23, $24, $25, $26, $27, $28, $29, $30,
                        $31, $32, $33, $34, $35, $36, $37, $38, $39, $40,
                        $41, $42, $43, $44, $45, $46, $47, $48, $49, $50
                    )
                    ON CONFLICT (mongo_id) DO NOTHING
                """,
                    new_id,
                    sanitize_string(emp.get("employee_code")),
                    sanitize_string(emp.get("first_name", "Unknown")),
                    sanitize_string(emp.get("middle_name")),
                    sanitize_string(emp.get("last_name", "Unknown")),
                    sanitize_string(emp.get("preferred_name")),
                    parse_date(emp.get("date_of_birth")),
                    sanitize_string(emp.get("ni_number")),
                    sanitize_string(emp.get("email", f"unknown_{mongo_id}@migration.local")),
                    sanitize_string(emp.get("phone")),
                    sanitize_string(emp.get("phone_secondary")),
                    sanitize_string(emp.get("address_line_1")),
                    sanitize_string(emp.get("address_line_2")),
                    sanitize_string(emp.get("city")),
                    sanitize_string(emp.get("county")),
                    sanitize_string(emp.get("postcode")),
                    sanitize_string(emp.get("country", "United Kingdom")),
                    sanitize_string(emp.get("role")),
                    status,
                    parse_date(emp.get("start_date")),
                    manager_id,
                    sanitize_string(emp.get("manager_name")),
                    sanitize_string(emp.get("branch")),
                    emp.get("profile_photo_url"),
                    sanitize_string(emp.get("driver_status")),
                    emp.get("has_driving_licence", False),
                    emp.get("has_own_vehicle", False),
                    emp.get("criminal_offence_declared"),
                    emp.get("dbs_update_service_consent"),
                    emp.get("health_issue_declared"),
                    emp.get("professional_misconduct_declared"),
                    emp.get("working_time_opt_out"),
                    sanitize_string(emp.get("next_of_kin_name")),
                    sanitize_string(emp.get("next_of_kin_relationship")),
                    sanitize_string(emp.get("next_of_kin_phone")),
                    sanitize_string(emp.get("next_of_kin_address")),
                    sanitize_string(emp.get("next_of_kin_city")),
                    sanitize_string(emp.get("next_of_kin_postcode")),
                    emp.get("recruitment_approved", False),
                    parse_timestamp(emp.get("recruitment_approved_at")),
                    approved_by,
                    safe_jsonb(emp.get("cv_extracted_roles")),
                    sanitize_string(emp.get("name_mismatch_status")),
                    safe_jsonb(emp.get("name_mismatch_review")),
                    emp.get("completion_percentage", 0),
                    emp.get("compliance_score", 0),
                    sanitize_string(emp.get("notes")),
                    parse_timestamp(emp.get("created_at")),
                    parse_timestamp(emp.get("updated_at")),
                    mongo_id,
                    False
                )
        
        await self.save_employee_mapping(mongo_id, new_id)
        self.logger.info(f"Migrated employee: {name}")


async def run(dry_run: bool = False):
    """Entry point for phase 2."""
    migration = Phase2EmployeeMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    asyncio.run(run(dry_run=args.dry_run))
