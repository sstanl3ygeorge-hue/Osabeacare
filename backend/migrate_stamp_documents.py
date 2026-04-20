"""
Migration Script: Burn Visual Stamps onto Historical Documents

This script finds all verified documents that don't have a stamped_file_url
and retroactively applies the CQC visual stamp.

Usage:
    python migrate_stamp_documents.py

Requirements:
    - MONGO_URL environment variable set
    - SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables set
    - Run from the backend directory
"""

import os
import sys
import asyncio
import httpx
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import stamp functionality
from services.pdf_service import stamp_evidence_document
from supabase_storage import upload_to_supabase, is_supabase_storage_configured

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# Track results
results = {
    "total_found": 0,
    "stamped_successfully": 0,
    "skipped_no_url": 0,
    "skipped_already_stamped": 0,
    "failed": 0,
    "errors": []
}


async def download_file(url: str) -> bytes:
    """Download file from URL."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Download failed: {response.status_code}")


async def process_document(db, doc: dict) -> bool:
    """Process a single document - download, stamp, upload, update."""
    doc_id = doc.get("id")
    employee_id = doc.get("employee_id")
    requirement_id = doc.get("requirement_id", "unknown")
    file_url = doc.get("file_url")
    
    print(f"\n  Processing: {requirement_id} for employee {employee_id[:8]}...")
    
    # Skip if no file URL
    if not file_url:
        print(f"    ⚠ Skipped: No file_url")
        results["skipped_no_url"] += 1
        return False
    
    # Skip if already has stamped URL
    if doc.get("stamped_file_url"):
        print(f"    ⚠ Skipped: Already has stamped_file_url")
        results["skipped_already_stamped"] += 1
        return False
    
    try:
        # Get verification info
        verification_stamp = doc.get("verification_stamp", {})
        if isinstance(verification_stamp, str):
            # Old format - just a status string
            admin_name = "System Admin"
            verified_at = doc.get("verified_at", doc.get("updated_at", datetime.now(timezone.utc).isoformat()))
            verification_id = doc_id[:12]
        else:
            admin_name = verification_stamp.get("verified_by_name", "System Admin")
            verified_at = verification_stamp.get("verified_at", doc.get("updated_at"))
            verification_id = verification_stamp.get("verification_id", doc_id[:12])
        
        # Download original file
        print(f"    ↓ Downloading from: {file_url[:60]}...")
        file_bytes = await download_file(file_url)
        print(f"    ✓ Downloaded: {len(file_bytes)} bytes")
        
        # Determine if it's an image or PDF
        is_image = any(file_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
        
        # Apply stamp
        print(f"    🔨 Burning stamp...")
        stamped_bytes = stamp_evidence_document(
            document_bytes=file_bytes,
            admin_name=admin_name,
            verified_at=verified_at,
            verification_id=verification_id,
            is_image=is_image
        )
        print(f"    ✓ Stamped: {len(stamped_bytes)} bytes")
        
        # Upload to Supabase
        original_filename = file_url.split("/")[-1].split("?")[0]
        if not original_filename.lower().endswith('.pdf'):
            original_filename = original_filename.rsplit('.', 1)[0] + '_stamped.pdf'
        else:
            original_filename = original_filename.rsplit('.', 1)[0] + '_stamped.pdf'
        
        print(f"    ↑ Uploading to Supabase as: {original_filename}")
        upload_result = await upload_to_supabase(
            file_content=stamped_bytes,
            filename=original_filename,
            folder=f"stamped/{employee_id}"
        )
        stamped_url = upload_result.get("url")
        print(f"    ✓ Uploaded: {stamped_url[:60]}...")
        
        # Update database record
        await db.employee_documents.update_one(
            {"id": doc_id},
            {
                "$set": {
                    "stamped_file_url": stamped_url,
                    "verification_stamp_by_name": admin_name,
                    "verification_stamp_at": verified_at,
                    "verification_stamp_label": "Verified copy",
                    "stamp_applied_at": datetime.now(timezone.utc).isoformat(),
                    "stamp_migration": True
                }
            }
        )
        print(f"    ✓ Database updated")
        
        results["stamped_successfully"] += 1
        return True
        
    except Exception as e:
        error_msg = f"{requirement_id} ({doc_id}): {str(e)}"
        print(f"    ✗ Error: {e}")
        results["errors"].append(error_msg)
        results["failed"] += 1
        return False


async def run_migration():
    """Main migration function."""
    print("=" * 60)
    print("STAMP MIGRATION SCRIPT")
    print("Burns visual CQC stamps onto historical verified documents")
    print("=" * 60)
    
    # Check Supabase configuration
    if not is_supabase_storage_configured():
        print("\n❌ ERROR: Supabase storage not configured!")
        print("   Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        return
    
    print("\n✓ Supabase storage configured")
    
    # Connect to MongoDB
    if not MONGO_URL:
        print("\n❌ ERROR: MONGO_URL not set!")
        return
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    print(f"✓ Connected to MongoDB: {DB_NAME}")
    
    # Find documents that need stamping
    # Criteria: Has verification_stamp that's not "not_verified" AND no stamped_file_url AND has valid HTTP URL
    query = {
        "$and": [
            {"verification_stamp": {"$nin": [None, "", "not_verified"]}},
            {"$or": [
                {"stamped_file_url": {"$exists": False}},
                {"stamped_file_url": None},
                {"stamped_file_url": ""}
            ]},
            {"file_url": {"$regex": "^https?://"}}  # Only documents with valid HTTP/HTTPS URLs
        ]
    }
    
    docs = await db.employee_documents.find(query, {"_id": 0}).to_list(length=500)
    results["total_found"] = len(docs)
    
    print(f"\n📋 Found {len(docs)} documents to stamp")
    
    if len(docs) == 0:
        print("\n✓ No documents need stamping!")
        
        # Also check for verified docs without file_url (info only)
        no_url_query = {
            "$and": [
                {"verification_stamp": {"$nin": [None, "", "not_verified"]}},
                {"$or": [
                    {"file_url": {"$exists": False}},
                    {"file_url": None},
                    {"file_url": ""}
                ]}
            ]
        }
        no_url_count = await db.employee_documents.count_documents(no_url_query)
        if no_url_count > 0:
            print(f"\n⚠ Note: {no_url_count} verified documents have no file_url (cannot be stamped)")
        
        return
    
    # Process each document
    print("\n" + "-" * 60)
    print("PROCESSING DOCUMENTS")
    print("-" * 60)
    
    for i, doc in enumerate(docs, 1):
        print(f"\n[{i}/{len(docs)}]", end="")
        await process_document(db, doc)

    # -------------------------------------------------------
    # PASS 2: Backfill flat stamp fields for docs that already
    # have stamped_file_url but are missing verification_stamp_by_name
    # -------------------------------------------------------
    print("\n" + "-" * 60)
    print("PASS 2: BACKFILL FLAT STAMP FIELDS")
    print("-" * 60)

    backfill_query = {
        "$and": [
            {"stamped_file_url": {"$nin": [None, "", {"$exists": False}]}},
            {"$or": [
                {"verification_stamp_by_name": {"$exists": False}},
                {"verification_stamp_by_name": None},
                {"verification_stamp_by_name": ""}
            ]},
            {"verification_stamp": {"$nin": [None, "", "not_verified"]}}
        ]
    }
    backfill_docs = await db.employee_documents.find(backfill_query, {"_id": 0}).to_list(length=2000)
    print(f"Found {len(backfill_docs)} documents needing flat-field backfill")

    backfill_count = 0
    for doc in backfill_docs:
        doc_id = doc.get("id")
        verification_stamp = doc.get("verification_stamp", {})
        if isinstance(verification_stamp, str):
            admin_name = "System Admin"
            verified_at = doc.get("verified_at", doc.get("updated_at", datetime.now(timezone.utc).isoformat()))
        else:
            admin_name = verification_stamp.get("verified_by_name", "System Admin")
            verified_at = verification_stamp.get("verified_at", doc.get("verified_at", doc.get("updated_at")))
        await db.employee_documents.update_one(
            {"id": doc_id},
            {"$set": {
                "verification_stamp_by_name": admin_name,
                "verification_stamp_at": verified_at,
                "verification_stamp_label": "Verified copy"
            }}
        )
        backfill_count += 1

    print(f"✓ Backfilled flat stamp fields on {backfill_count} documents")

    # -----------------------------------------------------------------------
    # PASS 3: Backfill requirement-slot verified=True for all employees
    # that have verified documents but whose slot still has verified=False.
    # This fixes the gate vs compliance-file mismatch for historical records.
    # -----------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("PASS 3: Backfill requirement slot verified flags")
    print("-" * 60)

    SLOT_KEY_ALIASES = {
        "identity": [
            "identity", "id_document", "passport", "driving_licence",
            "driving_license", "identity_documents", "identity_evidence",
            "identity_rtw", "proof_of_identity", "identity_document",
            "identity_evidence_2", "identity_evidence_3", "identity_upload",
        ],
        "right_to_work": [
            "right_to_work", "rtw", "right-to-work", "right_to_work_documents",
            "right_to_work_evidence",
        ],
        "proof_of_address": [
            "proof_of_address", "poa", "proof_of_address_1", "proof_of_address_2",
            "address_document",
        ],
        "dbs": [
            "dbs", "dbs_certificate", "dbs_check",
        ],
    }

    slot_backfill_count = 0
    for req_key, aliases in SLOT_KEY_ALIASES.items():
        _dead = frozenset((
            "rejected", "amendment_requested", "invalidated",
            "deleted", "superseded", "uploaded_in_error",
        ))
        # Find all verified documents (by any alias) not already feeding a verified slot
        verified_docs = await db.employee_documents.find(
            {
                "$and": [
                    {"requirement_id": {"$in": aliases}},
                    {"status": {"$nin": list(_dead)}},
                    {
                        "$or": [
                            {"verified": True},
                            {"status": {"$in": ["verified", "approved"]}},
                            {"review_status": {"$in": ["verified", "approved"]}},
                            {"verification_stamp": {"$nin": [None, "", "not_verified"]}},
                        ]
                    },
                ]
            },
            {"_id": 0, "employee_id": 1, "verified_at": 1, "verified_by_name": 1,
             "verification_stamp": 1},
        ).to_list(5000)

        # Group by employee_id
        from collections import defaultdict
        by_employee: dict = defaultdict(list)
        for d in verified_docs:
            by_employee[d["employee_id"]].append(d)

        for employee_id, emp_docs in by_employee.items():
            # Pick verified_at / verified_by_name from the best doc
            best = sorted(
                emp_docs,
                key=lambda x: x.get("verified_at") or x.get("verification_stamp", {}).get("verified_at") or "",
                reverse=True,
            )[0]
            stamp = best.get("verification_stamp") or {}
            va = best.get("verified_at") or (stamp.get("verified_at") if isinstance(stamp, dict) else None)
            vn = best.get("verified_by_name") or (stamp.get("verified_by_name") if isinstance(stamp, dict) else "System Admin")

            result = await db.employee_documents.update_one(
                {
                    "employee_id": employee_id,
                    "requirement_key": req_key,
                    "$or": [{"verified": {"$ne": True}}, {"verified": {"$exists": False}}],
                },
                {"$set": {"verified": True, "verified_at": va, "verified_by_name": vn,
                          "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            if result.modified_count:
                slot_backfill_count += 1

    print(f"✓ Backfilled verified=True on {slot_backfill_count} requirement slots")

    # Print summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"\n📊 Results:")
    print(f"   Total found:           {results['total_found']}")
    print(f"   ✓ Stamped successfully: {results['stamped_successfully']}")
    print(f"   ⚠ Skipped (no URL):     {results['skipped_no_url']}")
    print(f"   ⚠ Already stamped:      {results['skipped_already_stamped']}")
    print(f"   ✗ Failed:               {results['failed']}")
    
    if results["errors"]:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for err in results["errors"][:10]:
            print(f"   - {err}")
        if len(results["errors"]) > 10:
            print(f"   ... and {len(results['errors']) - 10} more")
    
    print("\n")


if __name__ == "__main__":
    asyncio.run(run_migration())
