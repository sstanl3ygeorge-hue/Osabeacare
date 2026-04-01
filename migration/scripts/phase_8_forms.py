"""
Phase 8: Migrate forms and agreements.

Handles form_submissions and agreement_acknowledgements.
Creates form_templates and agreement_templates reference tables.

Idempotent: Checks mongo_id before inserting.
Resumable: Tracks last_processed_id.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_timestamp, sanitize_string, safe_jsonb
)


class Phase8FormsMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_8_forms", dry_run)
        self.form_template_map = {}
        self.agreement_template_map = {}
    
    async def migrate(self):
        await self._create_form_templates()
        await self._create_agreement_templates()
        await self._migrate_form_submissions()
        await self._migrate_agreement_acknowledgements()
    
    async def _create_form_templates(self):
        """Create form templates from distinct form_types."""
        self.logger.info("Creating form templates...")
        
        # Get distinct form types
        form_types = await self.mongo_db.form_submissions.distinct("form_type")
        
        templates = {
            "interview_record": {"name": "Interview Record", "is_blocker": True},
            "staff_health_questionnaire": {"name": "Staff Health Questionnaire", "is_blocker": True},
            "induction": {"name": "Induction & Competency Assessment", "is_blocker": True},
            "supervision": {"name": "Supervision Record", "is_blocker": False},
            "appraisal": {"name": "Annual Appraisal", "is_blocker": False},
        }
        
        for form_type in form_types:
            if not form_type:
                continue
            
            template_data = templates.get(form_type, {"name": form_type.replace("_", " ").title(), "is_blocker": False})
            new_id = generate_uuid()
            
            if not self.dry_run and self.pg_pool:
                async with self.pg_pool.acquire() as conn:
                    existing = await conn.fetchval(
                        "SELECT id FROM form_templates WHERE form_type = $1", form_type
                    )
                    if existing:
                        self.form_template_map[form_type] = str(existing)
                        continue
                    
                    await conn.execute("""
                        INSERT INTO form_templates (id, form_type, name, description, schema, is_blocker, active)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (form_type) DO NOTHING
                    """,
                        new_id, form_type, template_data["name"], None,
                        '{}', template_data["is_blocker"], True
                    )
            
            self.form_template_map[form_type] = new_id
    
    async def _create_agreement_templates(self):
        """Create agreement templates."""
        self.logger.info("Creating agreement templates...")
        
        templates = [
            ("contract_acceptance", "Zero Hour Contract", True),
            ("handbook_acknowledgement", "Employee Handbook Acknowledgement", True),
        ]
        
        for agreement_type, name, is_blocker in templates:
            new_id = generate_uuid()
            
            if not self.dry_run and self.pg_pool:
                async with self.pg_pool.acquire() as conn:
                    existing = await conn.fetchval(
                        "SELECT id FROM agreement_templates WHERE agreement_type = $1", agreement_type
                    )
                    if existing:
                        self.agreement_template_map[agreement_type] = str(existing)
                        continue
                    
                    await conn.execute("""
                        INSERT INTO agreement_templates (id, agreement_type, name, is_blocker, active)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (agreement_type) DO NOTHING
                    """,
                        new_id, agreement_type, name, is_blocker, True
                    )
            
            self.agreement_template_map[agreement_type] = new_id
    
    async def _migrate_form_submissions(self):
        """Migrate form submissions."""
        self.logger.info("Migrating form submissions...")
        
        cursor = self.mongo_db.form_submissions.find({})
        submissions = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(submissions)} form submissions")
        
        for sub in submissions:
            mongo_id = sub.get("id") or str(sub.get("_id"))
            
            try:
                employee_id = self.map_employee_id(sub.get("employee_id"))
                if not employee_id:
                    self.record_warning(f"No employee mapping for form {mongo_id}")
                    continue
                
                form_type = sub.get("form_type")
                template_id = self.form_template_map.get(form_type)
                
                # Map status
                status = sub.get("status", "draft")
                if status not in ("not_started", "draft", "submitted", "awaiting_review", "verified", "rejected"):
                    status = "submitted" if sub.get("submitted_at") else "draft"
                
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO form_submissions (
                                id, employee_id, form_template_id, form_type,
                                data, status, submitted_at, submitted_by, submitted_by_name,
                                verified, verified_at, verified_by, verified_by_name, verification_notes,
                                rejected, rejected_at, rejected_by, rejection_reason,
                                version, is_current, superseded_at,
                                created_at, updated_at, mongo_id
                            )
                            VALUES ($1, $2, $3, $4, $5, $6::form_status, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            template_id,
                            form_type,
                            safe_jsonb(sub.get("data", {})),
                            status,
                            parse_timestamp(sub.get("submitted_at")),
                            self.map_user_id(sub.get("submitted_by")),
                            sanitize_string(sub.get("submitted_by_name")),
                            sub.get("verified", False),
                            parse_timestamp(sub.get("verified_at")),
                            self.map_user_id(sub.get("verified_by")),
                            sanitize_string(sub.get("verified_by_name")),
                            sanitize_string(sub.get("verification_notes") or sub.get("notes")),
                            sub.get("rejected", False),
                            parse_timestamp(sub.get("rejected_at")),
                            self.map_user_id(sub.get("rejected_by")),
                            sanitize_string(sub.get("rejection_reason")),
                            sub.get("version", 1),
                            True,
                            parse_timestamp(sub.get("superseded_at")),
                            parse_timestamp(sub.get("created_at")),
                            parse_timestamp(sub.get("updated_at")),
                            mongo_id
                        )
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1
    
    async def _migrate_agreement_acknowledgements(self):
        """Migrate agreement acknowledgements."""
        self.logger.info("Migrating agreement acknowledgements...")
        
        cursor = self.mongo_db.agreement_acknowledgements.find({})
        acks = await cursor.to_list(length=None)
        
        self.logger.info(f"Found {len(acks)} agreement acknowledgements")
        
        for ack in acks:
            mongo_id = ack.get("id") or str(ack.get("_id"))
            
            try:
                employee_id = self.map_employee_id(ack.get("employee_id"))
                if not employee_id:
                    self.record_warning(f"No employee mapping for agreement {mongo_id}")
                    continue
                
                agreement_type = ack.get("agreement_type")
                template_id = self.agreement_template_map.get(agreement_type)
                
                # Map signed document
                signed_doc_id = self.map_document_id(ack.get("signed_document_id"))
                
                # Map status
                status = ack.get("verification_status", "pending")
                if status not in ("not_started", "pending", "submitted", "verified", "rejected"):
                    if ack.get("verified_at"):
                        status = "verified"
                    elif ack.get("completed_at"):
                        status = "submitted"
                    else:
                        status = "pending"
                
                new_id = generate_uuid()
                
                if not self.dry_run and self.pg_pool:
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO agreement_acknowledgements (
                                id, employee_id, agreement_template_id, agreement_type,
                                completion_mode, completed_at, completed_by, assisted_by,
                                version_acknowledged, call_note, signed_document_id,
                                status, verified, verified_at, verified_by, verification_notes,
                                created_at, updated_at, mongo_id
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::agreement_status, $13, $14, $15, $16, $17, $18, $19)
                            ON CONFLICT (mongo_id) DO NOTHING
                        """,
                            new_id,
                            employee_id,
                            template_id,
                            agreement_type,
                            sanitize_string(ack.get("completion_mode")),
                            parse_timestamp(ack.get("completed_at")),
                            self.map_user_id(ack.get("completed_by")),
                            self.map_user_id(ack.get("assisted_by")),
                            sanitize_string(ack.get("version_acknowledged")),
                            sanitize_string(ack.get("call_note")),
                            signed_doc_id,
                            status,
                            ack.get("verified", False) or status == "verified",
                            parse_timestamp(ack.get("verified_at")),
                            self.map_user_id(ack.get("verified_by")),
                            sanitize_string(ack.get("verification_notes")),
                            parse_timestamp(ack.get("created_at")),
                            parse_timestamp(ack.get("updated_at")),
                            mongo_id
                        )
                
                self.result.migrated_records += 1
                self.result.total_records += 1
                
            except Exception as e:
                self.record_error(mongo_id, str(e))
                self.result.total_records += 1


async def run(dry_run: bool = False):
    migration = Phase8FormsMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))
