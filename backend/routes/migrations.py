"""
Migration routes for admin data migration operations.

Handles:
- Dual-row migration (converting legacy compliance data to new model)
- Stamp migration (applying visual stamps to historical verified documents)

These are administrative endpoints used for one-time or batch data migrations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request

from .dependencies import (
    get_db,
    require_admin,
    log_audit_action
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(prefix="/admin", tags=["Admin Migration"])


# ==================== LAZY IMPORTS ====================

def get_dual_row_migration_service():
    """Lazy import of DualRowMigrationService from server.py"""
    from server import DualRowMigrationService
    return DualRowMigrationService


# ==================== DUAL-ROW MIGRATION ENDPOINTS ====================

@router.post("/dual-row-migration/employee/{employee_id}")
async def migrate_employee_to_dual_row(
    employee_id: str,
    dry_run: bool = Query(True, description="If true, only preview what would be migrated"),
    user: dict = Depends(require_admin)
):
    """
    Migrate a single employee's compliance data to dual-row model.
    
    Migration policy (conservative):
    - Keeps existing evidence files as they are
    - Creates derived check records ONLY where data is strong enough
    - Does NOT silently manufacture verified checks from just uploaded evidence
    
    Set dry_run=false to actually perform the migration.
    """
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    DualRowMigrationService = get_dual_row_migration_service()
    result = await DualRowMigrationService.migrate_employee_checks(
        employee_id=employee_id,
        migrated_by=user['user_id'],
        dry_run=dry_run
    )
    
    return result


@router.post("/dual-row-migration/batch")
async def run_batch_dual_row_migration(
    employee_ids: Optional[List[str]] = Body(None, description="Specific employee IDs to migrate, or null for auto-detect"),
    dry_run: bool = Query(True, description="If true, only preview what would be migrated"),
    limit: int = Query(100, description="Maximum employees to process"),
    user: dict = Depends(require_admin)
):
    """
    Run batch migration for multiple employees.
    
    If employee_ids is null, migrates employees without existing check records.
    Always use dry_run=true first to preview changes.
    """
    DualRowMigrationService = get_dual_row_migration_service()
    result = await DualRowMigrationService.run_batch_migration(
        employee_ids=employee_ids,
        migrated_by=user['user_id'],
        dry_run=dry_run,
        limit=limit
    )
    
    return result


# ==================== STAMP MIGRATION ENDPOINT ====================

@router.post("/run-stamp-migration")
async def run_stamp_migration(
    request: Request,
    user: dict = Depends(require_admin)
):
    """
    Migration endpoint to stamp historical verified documents.
    Only accessible by admin users.
    
    Finds all verified documents without stamped_file_url and applies visual stamps.
    """
    from services.pdf_service import stamp_evidence_document
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    import httpx
    
    db = get_db()
    
    results = {
        "total_found": 0,
        "stamped_successfully": 0,
        "skipped_no_url": 0,
        "failed": 0,
        "errors": [],
        "processed": []
    }
    
    # Check Supabase configuration
    if not is_supabase_storage_configured():
        raise HTTPException(status_code=500, detail="Supabase storage not configured")
    
    # Find documents that need stamping
    query = {
        "$and": [
            {"verification_stamp": {"$nin": [None, "", "not_verified"]}},
            {"$or": [
                {"stamped_file_url": {"$exists": False}},
                {"stamped_file_url": None},
                {"stamped_file_url": ""}
            ]},
            {"file_url": {"$regex": "^https?://"}}
        ]
    }
    
    docs = await db.employee_documents.find(query, {"_id": 0}).to_list(length=500)
    results["total_found"] = len(docs)
    
    if len(docs) == 0:
        return {
            "success": True,
            "message": "No documents need stamping",
            "results": results
        }
    
    # Process each document
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        for doc in docs:
            doc_id = doc.get("id")
            employee_id = doc.get("employee_id")
            requirement_id = doc.get("requirement_id", "unknown")
            file_url = doc.get("file_url")
            
            try:
                # Get verification info
                verification_stamp = doc.get("verification_stamp", {})
                if isinstance(verification_stamp, str):
                    admin_name = "System Admin"
                    verified_at = doc.get("verified_at", doc.get("updated_at", datetime.now(timezone.utc).isoformat()))
                    verification_id = doc_id[:12] if doc_id else "migration"
                else:
                    admin_name = verification_stamp.get("verified_by_name", "System Admin")
                    verified_at = verification_stamp.get("verified_at", doc.get("updated_at"))
                    verification_id = verification_stamp.get("verification_id", doc_id[:12] if doc_id else "migration")
                
                # Download original file
                response = await client.get(file_url)
                if response.status_code != 200:
                    results["errors"].append(f"{requirement_id}: Download failed ({response.status_code})")
                    results["failed"] += 1
                    continue
                
                file_bytes = response.content
                
                # Determine if it's an image or PDF
                is_image = any(file_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
                
                # Apply stamp
                stamped_bytes = stamp_evidence_document(
                    document_bytes=file_bytes,
                    admin_name=admin_name,
                    verified_at=verified_at,
                    verification_id=verification_id,
                    is_image=is_image
                )
                
                # Upload to Supabase
                original_filename = file_url.split("/")[-1].split("?")[0]
                if not original_filename.lower().endswith('.pdf'):
                    original_filename = original_filename.rsplit('.', 1)[0] + '_stamped.pdf'
                else:
                    original_filename = original_filename.rsplit('.', 1)[0] + '_stamped.pdf'
                
                upload_result = await upload_to_supabase(
                    file_content=stamped_bytes,
                    filename=original_filename,
                    folder=f"stamped/{employee_id}"
                )
                stamped_url = upload_result.get("url")
                
                # Update database record
                await db.employee_documents.update_one(
                    {"id": doc_id},
                    {
                        "$set": {
                            "stamped_file_url": stamped_url,
                            "stamp_applied_at": datetime.now(timezone.utc).isoformat(),
                            "stamp_migration": True
                        }
                    }
                )
                
                results["stamped_successfully"] += 1
                results["processed"].append({
                    "doc_id": doc_id,
                    "requirement": requirement_id,
                    "stamped_url": stamped_url[:60] + "..."
                })
                
            except Exception as e:
                results["errors"].append(f"{requirement_id} ({doc_id}): {str(e)}")
                results["failed"] += 1
    

# ==================== APPLICATION UNIFICATION (Phase 1) ====================

from application_resolver import resolve_application, backfill_dry_run, backfill_execute


@router.get("/application-resolver/{employee_id}")
async def resolve_employee_application(
    employee_id: str,
    user: dict = Depends(require_admin),
):
    """
    Resolve application completeness for a single employee.

    Returns section-by-section breakdown, provenance, and whether
    the record is safe for Employment Review.
    """
    db = get_db()
    result = await resolve_application(db, employee_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/application-backfill/dry-run")
async def application_backfill_dry_run(
    user: dict = Depends(require_admin),
):
    """
    Dry-run: report which employees would get a backfilled
    application_form form_submission, without writing anything.

    Returns a full report: candidates, skipped, section completeness.
    """
    db = get_db()
    report = await backfill_dry_run(db)
    return report


@router.post("/application-backfill/execute")
async def application_backfill_run(
    user: dict = Depends(require_admin),
):
    """
    Execute backfill: create application_form form_submissions for
    non-online employees that don't have one yet.

    Safety:
    - Never overwrites existing form_submissions
    - Never touches online_structured records
    - Provenance stamped on every record
    """
    db = get_db()
    user_id = user.get("user_id", user.get("id", "system"))
    user_name = user.get("name", user.get("email", "Admin"))

    result = await backfill_execute(db, user_id, user_name)

    await log_audit_action(
        user_id,
        "application_backfill_execute",
        "migration",
        "all",
        {"backfilled": result["backfilled"], "skipped": result["skipped"]},
    )

    return result
    # Log audit
    await log_audit_action(
        user["user_id"],
        "run_stamp_migration",
        "system",
        "migration",
        {
            "total_found": results["total_found"],
            "stamped": results["stamped_successfully"],
            "failed": results["failed"]
        }
    )
    
    return {
        "success": True,
        "message": f"Migration complete: {results['stamped_successfully']}/{results['total_found']} documents stamped",
        "results": results
    }
