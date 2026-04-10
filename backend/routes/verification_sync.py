"""
Verification Sync Routes - Document verification status synchronization.

This module handles:
- Syncing verification status across documents for an employee
- Bulk verification sync across all employees
- Fixing verification mismatches (stamp vs verified flag vs status)
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from .dependencies import (
    get_db, require_admin, log_audit_action
)

router = APIRouter(tags=["Verification Sync"])


@router.post("/employees/{employee_id}/sync-verification-status")
async def sync_employee_verification_status(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """
    P0 FIX: Sync verification status across all documents for an employee.
    
    Ensures consistency between:
    - Document verification_stamp
    - Document verified boolean
    - Document status field
    - DBS checks
    - Training records
    
    Call this endpoint to fix any verification mismatches.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    synced_documents = []
    
    # 1. Sync DBS checks with evidence documents
    dbs_check = await db.dbs_checks.find_one({
        "employee_id": employee_id,
        "is_current": True
    }, {"_id": 0})
    
    if dbs_check and dbs_check.get("outcome") in ["clear", "verified", "information_reviewed"]:
        # Find DBS documents and sync verification
        dbs_docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": {"$regex": "dbs", "$options": "i"},
            "status": {"$ne": "superseded"}
        }).to_list(10)
        
        for doc in dbs_docs:
            # Check if verification is not synced
            stamp = doc.get("verification_stamp")
            verified = doc.get("verified")
            
            if stamp in [None, "", "not_verified"] or not verified:
                # Sync verification from DBS check
                method = dbs_check.get("method", "")
                if "update_service" in method:
                    stamp_type = "online_check"
                    stamp_label = "DBS Update Service Verified"
                else:
                    stamp_type = "original_seen"
                    stamp_label = "DBS Certificate Verified"
                
                await db.employee_documents.update_one(
                    {"id": doc.get("id")},
                    {"$set": {
                        "verification_stamp": stamp_type,
                        "verification_stamp_label": stamp_label,
                        "verification_stamp_at": now,
                        "verification_stamp_by": user['user_id'],
                        "verified": True,
                        "verified_at": now,
                        "status": "verified",
                        "review_status": "verified",
                        "review_reason": None,
                        "reviewed_at": now,
                        "reviewed_by": user['user_id'],
                        "reviewed_by_name": user.get('name')
                    }}
                )
                synced_documents.append({"id": doc.get("id"), "type": "dbs", "action": "synced_from_dbs_check"})
    
    # 2. Sync all documents - ensure verified flag matches verification_stamp
    all_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "status": {"$ne": "superseded"}
    }).to_list(200)
    
    for doc in all_docs:
        stamp = doc.get("verification_stamp")
        verified = doc.get("verified")
        status = doc.get("status")
        
        # If verification_stamp is set but verified is not
        if stamp and stamp not in ["not_verified", ""] and not verified:
            await db.employee_documents.update_one(
                {"id": doc.get("id")},
                {"$set": {
                    "verified": True,
                    "verified_at": doc.get("verification_stamp_at") or now,
                    "status": "verified",
                    "review_status": "verified",
                    "review_reason": None,
                    "reviewed_at": doc.get("verification_stamp_at") or now,
                    "reviewed_by": doc.get("verification_stamp_by") or user['user_id'],
                    "reviewed_by_name": doc.get("verification_stamp_by_name") or user.get('name')
                }}
            )
            synced_documents.append({"id": doc.get("id"), "type": doc.get("requirement_id"), "action": "set_verified_from_stamp"})
        
        # If verified is True but verification_stamp is missing
        elif verified and (not stamp or stamp in ["not_verified", ""]):
            await db.employee_documents.update_one(
                {"id": doc.get("id")},
                {"$set": {
                    "verification_stamp": "original_seen",
                    "verification_stamp_label": "Original Seen",
                    "verification_stamp_at": doc.get("verified_at") or now,
                    "status": "verified",
                    "review_status": "verified",
                    "review_reason": None,
                    "reviewed_at": doc.get("verified_at") or now,
                    "reviewed_by": doc.get("verified_by") or user['user_id'],
                    "reviewed_by_name": doc.get("verified_by_name") or user.get('name')
                }}
            )
            synced_documents.append({"id": doc.get("id"), "type": doc.get("requirement_id"), "action": "set_stamp_from_verified"})
        
        # If status is verified but other flags are not set
        elif status == "verified" and (not stamp or stamp in ["not_verified", ""] or not verified):
            await db.employee_documents.update_one(
                {"id": doc.get("id")},
                {"$set": {
                    "verification_stamp": "original_seen" if not stamp or stamp in ["not_verified", ""] else stamp,
                    "verification_stamp_label": doc.get("verification_stamp_label") or "Original Seen",
                    "verified": True,
                    "verified_at": doc.get("verified_at") or now,
                    "review_status": "verified",
                    "review_reason": None,
                    "reviewed_at": doc.get("verified_at") or now,
                    "reviewed_by": doc.get("verified_by") or user['user_id'],
                    "reviewed_by_name": doc.get("verified_by_name") or user.get('name')
                }}
            )
            synced_documents.append({"id": doc.get("id"), "type": doc.get("requirement_id"), "action": "synced_from_status"})
    
    # 3. Sync training records
    training_records = await db.training_records.find({
        "employee_id": employee_id,
        "record_status": {"$ne": "superseded"}
    }).to_list(100)
    
    synced_trainings = []
    for tr in training_records:
        verified = tr.get("verified")
        status = tr.get("status")
        
        if status in ["completed", "current"] and not verified:
            # Check if there's an associated document that's verified
            source_doc_id = tr.get("source_document_id")
            if source_doc_id:
                source_doc = await db.employee_documents.find_one({"id": source_doc_id})
                if source_doc and source_doc.get("verified"):
                    await db.training_records.update_one(
                        {"id": tr.get("id")},
                        {"$set": {"verified": True, "verified_at": now}}
                    )
                    synced_trainings.append({"id": tr.get("id"), "name": tr.get("training_name"), "action": "synced_from_document"})
    
    await log_audit_action(user['user_id'], "sync_verification_status", "employee", employee_id, {
        "documents_synced": len(synced_documents),
        "trainings_synced": len(synced_trainings)
    })
    
    return {
        "success": True,
        "employee_id": employee_id,
        "documents_synced": len(synced_documents),
        "trainings_synced": len(synced_trainings),
        "document_details": synced_documents[:20],
        "training_details": synced_trainings[:20],
        "message": f"Synced {len(synced_documents)} documents and {len(synced_trainings)} training records"
    }


@router.post("/admin/bulk-sync-verification-status")
async def bulk_sync_verification_status(
    user: dict = Depends(require_admin)
):
    """
    P0 FIX: Bulk sync verification status across ALL employees.
    
    Ensures consistency for all documents in the system.
    Use after database migrations or to fix systemic verification mismatches.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Find all documents with verification mismatches
    mismatched_docs = await db.employee_documents.find({
        "$or": [
            # Has stamp but not verified
            {
                "verification_stamp": {"$nin": [None, "", "not_verified"]},
                "verified": {"$ne": True}
            },
            # Is verified but no stamp
            {
                "verified": True,
                "verification_stamp": {"$in": [None, "", "not_verified"]}
            },
            # Status is verified but flags don't match
            {
                "status": "verified",
                "$or": [
                    {"verified": {"$ne": True}},
                    {"verification_stamp": {"$in": [None, "", "not_verified"]}}
                ]
            }
        ]
    }).to_list(1000)
    
    fixed_count = 0
    for doc in mismatched_docs:
        stamp = doc.get("verification_stamp")
        verified = doc.get("verified")
        status = doc.get("status")
        
        updates = {}
        
        if stamp and stamp not in ["not_verified", ""] and not verified:
            updates["verified"] = True
            updates["verified_at"] = doc.get("verification_stamp_at") or now
            updates["status"] = "verified"
        elif verified and (not stamp or stamp in ["not_verified", ""]):
            updates["verification_stamp"] = "original_seen"
            updates["verification_stamp_label"] = "Original Seen"
            updates["verification_stamp_at"] = doc.get("verified_at") or now
            updates["status"] = "verified"
        elif status == "verified":
            if not stamp or stamp in ["not_verified", ""]:
                updates["verification_stamp"] = "original_seen"
                updates["verification_stamp_label"] = "Original Seen"
            if not verified:
                updates["verified"] = True
                updates["verified_at"] = now
        
        if updates:
            await db.employee_documents.update_one(
                {"_id": doc.get("_id")},
                {"$set": updates}
            )
            fixed_count += 1
    
    await log_audit_action(user['user_id'], "bulk_sync_verification_status", "system", "all", {
        "documents_fixed": fixed_count
    })
    
    return {
        "success": True,
        "documents_scanned": len(mismatched_docs),
        "documents_fixed": fixed_count,
        "message": f"Fixed verification sync on {fixed_count} documents"
    }
