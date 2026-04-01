"""
Phase 4: Migrate documents from MongoDB to Postgres.

Handles employee_documents collection.
Stores old_file_url for later file migration.
Normalizes evidence_files arrays to individual rows.

Idempotent: Checks mongo_id before inserting.
Resumable: Tracks last_processed_id.
"""

import sys
sys.path.insert(0, '/app/migration')

from scripts.base import BaseMigration
from scripts.utils import (
    generate_uuid, parse_date, parse_timestamp, sanitize_string,
    extract_mongo_id, safe_jsonb
)
from config.mappings import (
    DOCUMENT_CATEGORY_MAP, DOCUMENT_STATUS_MAP, get_mapped_value
)


class Phase4DocumentsMigration(BaseMigration):
    
    def __init__(self, dry_run: bool = False):
        super().__init__("phase_4_documents", dry_run)
    
    async def migrate(self):
        cursor = self.mongo_db.employee_documents.find({})
        documents = await cursor.to_list(length=None)
        self.result.total_records = len(documents)
        
        self.logger.info(f"Found {len(documents)} documents to migrate")
        
        documents.sort(key=lambda x: x.get("id", "") or str(x.get("_id", "")))
        
        for doc in documents:
            mongo_id = doc.get("id") or str(doc.get("_id"))
            
            if self.result.last_processed_id:
                if mongo_id <= self.result.last_processed_id:
                    self.record_skip(mongo_id, "already processed")
                    continue
            
            try:
                await self._migrate_document(doc)
                self.result.migrated_records += 1
                self.result.last_processed_id = mongo_id
                
                if self.result.migrated_records % 20 == 0:
                    await self._save_state()
                    
            except Exception as e:
                self.record_error(mongo_id, str(e))
    
    async def _migrate_document(self, doc: dict):
        """Migrate a single document."""
        mongo_id = doc.get("id") or str(doc.get("_id"))
        
        # Idempotent check
        if await self.is_already_migrated("documents", mongo_id):
            self.record_skip(mongo_id, "already exists")
            return
        
        if mongo_id in self.document_id_map:
            self.record_skip(mongo_id, "already in mapping")
            return
        
        # Get postgres employee ID
        mongo_employee_id = doc.get("employee_id")
        employee_id = self.map_employee_id(mongo_employee_id)
        
        if not employee_id:
            self.record_warning(f"No employee mapping for {mongo_employee_id}")
            return
        
        new_id = generate_uuid()
        
        # Map category
        category = get_mapped_value(
            doc.get("category") or doc.get("type", "other"),
            DOCUMENT_CATEGORY_MAP,
            "other"
        )
        
        # Map status
        status = get_mapped_value(
            doc.get("status", "uploaded"),
            DOCUMENT_STATUS_MAP,
            "uploaded"
        )
        
        filename = doc.get("original_filename") or doc.get("filename") or f"document_{mongo_id}"
        
        self.logger.debug(f"Migrating document: {filename} ({mongo_id})")
        
        if not self.dry_run and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO documents (
                        id, employee_id, category, document_type_id, document_type_name,
                        requirement_id, requirement_name, document_label,
                        storage_path, file_url, old_file_url, original_filename,
                        file_size, mime_type, document_number, issue_date, expiry_date, permission_end_date,
                        status, verified, verified_at, verified_by, verified_by_name, verification_notes,
                        extraction_data, extraction_reviewed, extraction_reviewed_at, extraction_reviewed_by,
                        uploaded_at, uploaded_by, source_type, is_current,
                        created_at, updated_at, mongo_id, migration_reviewed, file_migration_status
                    )
                    VALUES (
                        $1, $2, $3::document_category, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19::document_status,
                        $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37
                    )
                    ON CONFLICT (mongo_id) DO NOTHING
                """,
                    new_id,
                    employee_id,
                    category,
                    doc.get("document_type_id"),
                    sanitize_string(doc.get("document_type_name")),
                    sanitize_string(doc.get("requirement_id")),
                    sanitize_string(doc.get("requirement_name")),
                    sanitize_string(doc.get("document_label")),
                    None,  # storage_path - set during file migration
                    None,  # file_url - generated from storage_path
                    doc.get("file_url"),  # old_file_url - original Emergent URL
                    sanitize_string(filename),
                    doc.get("file_size"),
                    doc.get("mime_type"),
                    sanitize_string(doc.get("document_number")),
                    parse_date(doc.get("issue_date")),
                    parse_date(doc.get("expiry_date")),
                    parse_date(doc.get("permission_end_date")),
                    status,
                    doc.get("verified", False),
                    parse_timestamp(doc.get("verified_at")),
                    self.map_user_id(doc.get("verified_by")),
                    sanitize_string(doc.get("verified_by_name")),
                    sanitize_string(doc.get("verification_notes")),
                    safe_jsonb(doc.get("extraction_data")),
                    doc.get("extraction_reviewed", False),
                    parse_timestamp(doc.get("extraction_reviewed_at")),
                    self.map_user_id(doc.get("extraction_reviewed_by")),
                    parse_timestamp(doc.get("uploaded_at") or doc.get("created_at")),
                    self.map_user_id(doc.get("uploaded_by")),
                    sanitize_string(doc.get("source_type")),
                    doc.get("is_current", True),
                    parse_timestamp(doc.get("created_at")),
                    parse_timestamp(doc.get("updated_at")),
                    mongo_id,
                    False,
                    "pending" if doc.get("file_url") else "no_file"
                )
        
        await self.save_document_mapping(mongo_id, new_id)
        
        # Handle evidence_files array (multiple files for same evidence)
        evidence_files = doc.get("evidence_files", [])
        if evidence_files and len(evidence_files) > 1:
            await self._migrate_evidence_files(evidence_files[1:], employee_id, category, doc)
        
        self.logger.info(f"Migrated document: {filename}")
    
    async def _migrate_evidence_files(self, files: list, employee_id: str, category: str, parent_doc: dict):
        """Migrate additional files from evidence_files array as separate document rows."""
        for file_entry in files:
            if not file_entry.get("file_url"):
                continue
            
            file_id = file_entry.get("id") or generate_uuid()
            
            # Check if already migrated
            if file_id in self.document_id_map:
                continue
            
            new_id = generate_uuid()
            
            if not self.dry_run and self.pg_pool:
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO documents (
                            id, employee_id, category, document_type_name,
                            requirement_id, requirement_name,
                            old_file_url, original_filename,
                            status, uploaded_at, uploaded_by, source_type, is_current,
                            created_at, updated_at, mongo_id, file_migration_status
                        )
                        VALUES ($1, $2, $3::document_category, $4, $5, $6, $7, $8, $9::document_status, $10, $11, $12, $13, $14, $15, $16, $17)
                        ON CONFLICT (mongo_id) DO NOTHING
                    """,
                        new_id,
                        employee_id,
                        category,
                        sanitize_string(parent_doc.get("document_type_name")),
                        sanitize_string(parent_doc.get("requirement_id")),
                        sanitize_string(parent_doc.get("requirement_name")),
                        file_entry.get("file_url"),
                        sanitize_string(file_entry.get("original_filename", f"file_{file_id}")),
                        file_entry.get("status", "uploaded"),
                        parse_timestamp(file_entry.get("uploaded_at")),
                        self.map_user_id(file_entry.get("uploaded_by")),
                        "evidence_file_array",
                        file_entry.get("status") != "superseded",
                        parse_timestamp(file_entry.get("uploaded_at")),
                        parse_timestamp(file_entry.get("uploaded_at")),
                        file_id,
                        "pending"
                    )
            
            await self.save_document_mapping(file_id, new_id)


async def run(dry_run: bool = False):
    """Entry point for phase 4."""
    migration = Phase4DocumentsMigration(dry_run=dry_run)
    return await migration.run()


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    asyncio.run(run(dry_run=args.dry_run))
