#!/usr/bin/env python3
"""
Migration Script: Fix Worker Form Submissions
==============================================
This script updates form submissions that used old form IDs
to use the new IDs that match the admin compliance system.

Run this on your production database:
    python3 migrate_worker_forms.py

Old IDs -> New IDs:
- health_questionnaire -> staff_health_questionnaire
- personal_info -> staff_personal_info
- hmrc_starter -> hmrc_starter_checklist
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Mapping of old form IDs to new form IDs
FORM_ID_MIGRATION = {
    "health_questionnaire": "staff_health_questionnaire",
    "personal_info": "staff_personal_info",
    "hmrc_starter": "hmrc_starter_checklist",
}

async def migrate():
    # Connect to database
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    print(f"Connecting to: {mongo_url}")
    print(f"Database: {db_name}")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("\n" + "="*50)
    print("FORM SUBMISSIONS MIGRATION")
    print("="*50 + "\n")
    
    total_updated = 0
    
    # Migrate form_submissions collection
    for old_id, new_id in FORM_ID_MIGRATION.items():
        # Find submissions with old form_type
        submissions = await db.form_submissions.find(
            {"form_type": old_id},
            {"_id": 0, "id": 1, "employee_id": 1, "form_type": 1, "status": 1}
        ).to_list(length=100)
        
        if submissions:
            print(f"Found {len(submissions)} submissions with form_type '{old_id}':")
            for s in submissions[:5]:  # Show first 5
                print(f"  - ID: {s.get('id')}, Employee: {s.get('employee_id')}, Status: {s.get('status')}")
            if len(submissions) > 5:
                print(f"  ... and {len(submissions) - 5} more")
            
            # Update form_type and add requirement_id
            result = await db.form_submissions.update_many(
                {"form_type": old_id},
                {
                    "$set": {
                        "form_type": new_id,
                        "requirement_id": new_id
                    }
                }
            )
            print(f"  ✅ Updated {result.modified_count} submissions to '{new_id}'\n")
            total_updated += result.modified_count
        else:
            print(f"No submissions found with form_type '{old_id}'")
    
    print("\n" + "="*50)
    print("FORM PROGRESS (SAVED DRAFTS) MIGRATION")
    print("="*50 + "\n")
    
    # Migrate form_progress collection (saved drafts)
    for old_id, new_id in FORM_ID_MIGRATION.items():
        progress_docs = await db.form_progress.find(
            {"form_id": old_id},
            {"_id": 0, "employee_id": 1, "form_id": 1, "status": 1}
        ).to_list(length=100)
        
        if progress_docs:
            print(f"Found {len(progress_docs)} saved drafts with form_id '{old_id}'")
            
            result = await db.form_progress.update_many(
                {"form_id": old_id},
                {"$set": {"form_id": new_id}}
            )
            print(f"  ✅ Updated {result.modified_count} drafts to '{new_id}'\n")
            total_updated += result.modified_count
        else:
            print(f"No saved drafts found with form_id '{old_id}'")
    
    # Ensure all worker form submissions have requirement_id
    print("\n" + "="*50)
    print("ADDING MISSING requirement_id FIELDS")
    print("="*50 + "\n")
    
    worker_forms = [
        "staff_health_questionnaire", 
        "staff_personal_info", 
        "hmrc_starter_checklist", 
        "equal_opportunities", 
        "emergency_contacts"
    ]
    
    for form_type in worker_forms:
        count = await db.form_submissions.count_documents({
            "form_type": form_type,
            "requirement_id": {"$exists": False}
        })
        if count > 0:
            result = await db.form_submissions.update_many(
                {"form_type": form_type, "requirement_id": {"$exists": False}},
                {"$set": {"requirement_id": form_type}}
            )
            print(f"✅ Added requirement_id to {result.modified_count} '{form_type}' submissions")
            total_updated += result.modified_count
    
    print("\n" + "="*50)
    print("MIGRATION SUMMARY")
    print("="*50)
    print(f"\nTotal records updated: {total_updated}")
    
    # Show current state
    print("\n" + "="*50)
    print("CURRENT FORM SUBMISSIONS BY TYPE")
    print("="*50 + "\n")
    
    pipeline = [
        {"$match": {"status": {"$in": ["submitted", "verified"]}}},
        {"$group": {"_id": "$form_type", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    async for doc in db.form_submissions.aggregate(pipeline):
        print(f"  {doc['_id']}: {doc['count']} submissions")
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
