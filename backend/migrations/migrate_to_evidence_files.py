"""
Phase 2 Migration: Convert legacy data to evidence_files array format

This migration ensures all employee_documents and training_records use the
evidence_files array structure for consistent multi-file support.

Run with: python migrations/migrate_to_evidence_files.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
import uuid

async def migrate_to_evidence_files():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    now = datetime.now(timezone.utc).isoformat()
    migration_log = []
    
    print("=" * 60)
    print("Phase 2 Migration: Evidence Files Array Structure")
    print("=" * 60)
    print(f"Database: {db_name}")
    print(f"Timestamp: {now}")
    print()
    
    # ========== Migrate Training Records ==========
    print("--- Training Records Migration ---")
    
    training_records = await db.training_records.find({
        "certificate_url": {"$exists": True, "$ne": None, "$ne": ""},
        "$or": [
            {"evidence_files": {"$exists": False}},
            {"evidence_files": {"$eq": []}},
            {"evidence_files": {"$eq": None}}
        ]
    }).to_list(500)
    
    training_migrated = 0
    for record in training_records:
        record_id = record.get('id')
        cert_url = record.get('certificate_url')
        original_filename = record.get('original_filename', 'Training Certificate')
        training_name = record.get('training_name', 'Training')
        
        # Create evidence_files array from certificate_url
        evidence_file = {
            "file_id": str(uuid.uuid4()),
            "file_url": cert_url,
            "original_filename": original_filename,
            "file_label": f"{training_name} Certificate",
            "uploaded_at": record.get('uploaded_at') or record.get('completion_date') or now,
            "source_type": "certificate",
            "status": "active"
        }
        
        # Update the record
        result = await db.training_records.update_one(
            {"id": record_id},
            {
                "$set": {
                    "evidence_files": [evidence_file],
                    "migrated_at": now,
                    "migration_version": "2.0_evidence_files"
                }
            }
        )
        
        if result.modified_count > 0:
            training_migrated += 1
            migration_log.append({
                "type": "training_record",
                "id": record_id,
                "training_name": training_name,
                "action": "converted certificate_url to evidence_files"
            })
            print(f"  ✓ Migrated: {training_name} ({record_id[:12]}...)")
    
    print(f"\nTraining records migrated: {training_migrated}")
    
    # ========== Migrate Employee Documents ==========
    print("\n--- Employee Documents Migration ---")
    
    employee_docs = await db.employee_documents.find({
        "file_url": {"$exists": True, "$ne": None, "$ne": ""},
        "$or": [
            {"evidence_files": {"$exists": False}},
            {"evidence_files": {"$eq": []}},
            {"evidence_files": {"$eq": None}}
        ]
    }).to_list(500)
    
    docs_migrated = 0
    for doc in employee_docs:
        doc_id = doc.get('id')
        file_url = doc.get('file_url')
        original_filename = doc.get('original_filename', 'Document')
        document_label = doc.get('document_label', 'Document')
        
        # Create evidence_files array from file_url
        evidence_file = {
            "file_id": str(uuid.uuid4()),
            "file_url": file_url,
            "original_filename": original_filename,
            "file_label": document_label,
            "uploaded_at": doc.get('uploaded_at') or now,
            "uploaded_by": doc.get('uploaded_by'),
            "uploaded_by_name": doc.get('uploaded_by_name'),
            "source_type": doc.get('source_type', 'manual_upload'),
            "status": "active"
        }
        
        # Update the record
        result = await db.employee_documents.update_one(
            {"id": doc_id},
            {
                "$set": {
                    "evidence_files": [evidence_file],
                    "migrated_at": now,
                    "migration_version": "2.0_evidence_files"
                }
            }
        )
        
        if result.modified_count > 0:
            docs_migrated += 1
            migration_log.append({
                "type": "employee_document",
                "id": doc_id,
                "document_label": document_label,
                "action": "converted file_url to evidence_files"
            })
            print(f"  ✓ Migrated: {document_label} ({doc_id[:12]}...)")
    
    print(f"\nEmployee documents migrated: {docs_migrated}")
    
    # ========== Log Migration ==========
    print("\n--- Saving Migration Log ---")
    
    await db.audit_logs.insert_one({
        "id": f"migration_{str(uuid.uuid4())[:8]}",
        "action": "phase2_evidence_files_migration",
        "performed_at": now,
        "summary": {
            "training_records_migrated": training_migrated,
            "employee_documents_migrated": docs_migrated,
            "total_migrated": training_migrated + docs_migrated
        },
        "details": migration_log,
        "migration_version": "2.0_evidence_files"
    })
    
    print(f"Migration log saved to audit_logs collection")
    
    # ========== Summary ==========
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"  Training records migrated: {training_migrated}")
    print(f"  Employee documents migrated: {docs_migrated}")
    print(f"  Total records updated: {training_migrated + docs_migrated}")
    print()
    
    # Verify migration
    print("--- Verification ---")
    
    remaining_training = await db.training_records.count_documents({
        "certificate_url": {"$exists": True, "$ne": None, "$ne": ""},
        "$or": [
            {"evidence_files": {"$exists": False}},
            {"evidence_files": {"$eq": []}},
            {"evidence_files": {"$eq": None}}
        ]
    })
    
    remaining_docs = await db.employee_documents.count_documents({
        "file_url": {"$exists": True, "$ne": None, "$ne": ""},
        "$or": [
            {"evidence_files": {"$exists": False}},
            {"evidence_files": {"$eq": []}},
            {"evidence_files": {"$eq": None}}
        ]
    })
    
    print(f"  Training records still needing migration: {remaining_training}")
    print(f"  Employee documents still needing migration: {remaining_docs}")
    
    if remaining_training == 0 and remaining_docs == 0:
        print("\n✅ All records successfully migrated to evidence_files format!")
    else:
        print("\n⚠️  Some records may still need manual review")
    
    client.close()
    return {
        "training_migrated": training_migrated,
        "docs_migrated": docs_migrated,
        "remaining_training": remaining_training,
        "remaining_docs": remaining_docs
    }

if __name__ == "__main__":
    result = asyncio.run(migrate_to_evidence_files())
    print(f"\nMigration result: {result}")
