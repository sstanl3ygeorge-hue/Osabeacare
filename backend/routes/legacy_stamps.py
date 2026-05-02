"""
Legacy stamp identification + bulk re-stamp endpoints.

Branded stamps applied by the current pipeline are tagged with
`stamped_renderer = "branded_evidence_stamp_v1"` (see
migrate_stamp_documents.py). Documents stamped before that renderer was
introduced (and any stamped via the older plain EvidenceStamper path)
lack that marker and therefore look "old" to the admin (e.g. Lawrence's
documents — no logo, no coloured border).

These endpoints let an admin:
  1. LIST all documents that carry an old-style stamp.
  2. RE-STAMP them in small batches with the branded Osabea stamp.

The re-stamp logic reuses the exact helper (`_apply_branded_stamp`) that
the CLI migration script uses, so output is identical.
"""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Body, Query
from pydantic import BaseModel

from .dependencies import (
    get_db,
    require_admin,
    log_audit_action,
)


router = APIRouter()


BRANDED_RENDERER = "branded_evidence_stamp_v1"

_NON_FILE_REQUIREMENT_IDS = frozenset({
    "dbs_status_check",
    "dbs_update_service_check",
})


def _build_legacy_stamp_query() -> dict:
    """Documents that ARE stamped (have stamped_file_url) but were NOT produced
    by the current branded renderer."""
    return {
        "$and": [
            {"stamped_file_url": {"$exists": True, "$nin": [None, ""]}},
            {"file_url": {"$exists": True, "$nin": [None, ""]}},
            {"requirement_id": {"$nin": list(_NON_FILE_REQUIREMENT_IDS)}},
            {
                "$or": [
                    {"stamped_renderer": {"$exists": False}},
                    {"stamped_renderer": None},
                    {"stamped_renderer": ""},
                    {"stamped_renderer": {"$ne": BRANDED_RENDERER}},
                ]
            },
        ]
    }


@router.get("/admin/documents/legacy-stamps")
async def list_legacy_stamped_documents(
    employee_id: Optional[str] = Query(None),
    limit: int = Query(500),
    user: dict = Depends(require_admin),
):
    """List employee_documents stamped by an older renderer.

    Read-only. Use this first to see how many documents will be re-stamped
    and which employees are affected.
    """
    db = get_db()

    query = _build_legacy_stamp_query()
    if employee_id:
        query["$and"].append({"employee_id": employee_id})

    docs = await db.employee_documents.find(query, {"_id": 0}).to_list(length=limit)

    # Hydrate employee names so the admin can read the list at a glance.
    employee_ids = list({d.get("employee_id") for d in docs if d.get("employee_id")})
    employees = {}
    if employee_ids:
        emp_docs = await db.employees.find(
            {"id": {"$in": employee_ids}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "status": 1},
        ).to_list(length=10000)
        employees = {e["id"]: e for e in emp_docs}

    per_employee: dict = {}
    results: list = []
    for d in docs:
        emp = employees.get(d.get("employee_id")) or {}
        emp_name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip() or "(unknown)"
        results.append({
            "document_id": d.get("id"),
            "employee_id": d.get("employee_id"),
            "employee_name": emp_name,
            "employee_status": emp.get("status"),
            "requirement_id": d.get("requirement_id"),
            "stamped_renderer": d.get("stamped_renderer"),
            "stamped_file_url": d.get("stamped_file_url"),
            "verified_at": d.get("verification_stamp_at") or d.get("verified_at"),
            "verified_by": d.get("verification_stamp_by_name"),
        })
        per_employee.setdefault(emp_name, 0)
        per_employee[emp_name] += 1

    return {
        "success": True,
        "count": len(docs),
        "employees_affected": len(per_employee),
        "per_employee_counts": per_employee,
        "results": results,
    }


class RestampInput(BaseModel):
    document_ids: Optional[List[str]] = None  # None → all matching legacy docs
    employee_id: Optional[str] = None
    apply: bool = False
    limit: int = 20  # Cap per call to keep request under proxy timeout


@router.post("/admin/documents/restamp-legacy")
async def restamp_legacy_documents(
    data: RestampInput = Body(...),
    user: dict = Depends(require_admin),
):
    """Re-apply the branded Osabea stamp to documents that currently carry an
    older stamp.

    Safety:
    - `apply=false` (default) returns a plan; downloads and re-stamps nothing.
    - `limit` caps how many documents are processed per call (default 20)
      to stay under the Railway proxy request timeout. Call repeatedly until
      `count == 0`.
    - The previous `stamped_file_url` is recorded in `previous_stamped_file_url`
      so a manual rollback is possible if needed.
    - Audit-logged.

    Reuses `_apply_branded_stamp` from migrate_stamp_documents.py so the
    output is byte-identical to the CLI migration.
    """
    db = get_db()

    query = _build_legacy_stamp_query()
    if data.employee_id:
        query["$and"].append({"employee_id": data.employee_id})
    if data.document_ids:
        query["$and"].append({"id": {"$in": data.document_ids}})

    docs = await db.employee_documents.find(query, {"_id": 0}).to_list(length=data.limit)
    counts = {"matched": len(docs), "restamped": 0, "failed": 0, "skipped_no_url": 0}
    results: list = []

    if not data.apply:
        for d in docs:
            results.append({
                "document_id": d.get("id"),
                "employee_id": d.get("employee_id"),
                "requirement_id": d.get("requirement_id"),
                "current_renderer": d.get("stamped_renderer"),
                "action": "would_restamp",
            })
        return {
            "success": True,
            "dry_run": True,
            "counts": counts,
            "results": results,
            "note": "Run again with apply=true to actually re-stamp these documents.",
        }

    # ---- Real run: import heavy deps lazily so dry-run stays fast ----
    from migrate_stamp_documents import _apply_branded_stamp
    from server import retrieve_file_bytes
    from supabase_storage import upload_file_to_storage, is_supabase_storage_configured

    if not is_supabase_storage_configured():
        return {
            "success": False,
            "dry_run": False,
            "error": "supabase_not_configured",
            "message": "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set on the backend.",
            "counts": counts,
            "results": [],
        }

    now_iso = datetime.now(timezone.utc).isoformat()

    for d in docs:
        doc_id = d.get("id")
        employee_id = d.get("employee_id")
        file_url = d.get("file_url") or d.get("file_path")
        if not file_url:
            counts["skipped_no_url"] += 1
            results.append({"document_id": doc_id, "action": "skipped_no_url"})
            continue
        try:
            existing_stamp = d.get("verification_stamp") if isinstance(d.get("verification_stamp"), dict) else {}
            admin_name = (
                existing_stamp.get("verified_by_name")
                or d.get("verification_stamp_by_name")
                or d.get("verified_by_name")
                or "System Admin"
            )
            verified_at = (
                existing_stamp.get("verified_at")
                or d.get("verification_stamp_at")
                or d.get("verified_at")
                or d.get("updated_at")
                or now_iso
            )
            verification_id = existing_stamp.get("verification_id") or (doc_id[:12] if doc_id else "unknown")
            stamp_type = existing_stamp.get("stamp_type", "copy_verified")
            stamp_data = {
                "stamp_type": stamp_type,
                "verified_by_name": admin_name,
                "verified_at": verified_at,
                "employee_name": d.get("employee_name", ""),
                "document_type": d.get("requirement_id", ""),
                "verification_id": verification_id,
            }

            file_bytes, content_type = await retrieve_file_bytes(file_url)
            normalized_ct = (content_type or "").lower()
            is_image = (
                any(file_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'])
                or normalized_ct.startswith("image/")
            )

            stamped_bytes = _apply_branded_stamp(file_bytes, stamp_data, is_image)

            original_filename = file_url.split("/")[-1].split("?")[0]
            if not original_filename.lower().endswith('.pdf'):
                original_filename = original_filename.rsplit('.', 1)[0] + '_stamped.pdf'
            else:
                original_filename = original_filename.rsplit('.', 1)[0] + '_stamped.pdf'

            stamped_url = await upload_file_to_storage(
                file_content=stamped_bytes,
                filename=original_filename,
                folder=f"stamped/{employee_id}",
            )
            if not stamped_url:
                raise RuntimeError("upload_file_to_storage returned no URL")

            stamp_data["migrated_backfill"] = True
            stamp_data["stamped_renderer"] = BRANDED_RENDERER
            await db.employee_documents.update_one(
                {"id": doc_id},
                {"$set": {
                    "stamped_file_url": stamped_url,
                    "verification_stamp": stamp_data,
                    "verification_stamp_by_name": admin_name,
                    "verification_stamp_at": verified_at,
                    "verification_stamp_label": "Verified copy",
                    "stamp_applied_at": now_iso,
                    "stamp_migration": True,
                    "stamped_renderer": BRANDED_RENDERER,
                    "restamped_at": now_iso,
                    "previous_stamped_file_url": d.get("stamped_file_url"),
                    "previous_verification_stamp": d.get("verification_stamp"),
                    "restamped_by": user["user_id"],
                }},
            )
            counts["restamped"] += 1
            results.append({
                "document_id": doc_id,
                "employee_id": employee_id,
                "action": "restamped",
                "new_stamped_url": stamped_url,
            })
        except Exception as exc:
            counts["failed"] += 1
            results.append({
                "document_id": doc_id,
                "employee_id": employee_id,
                "action": "failed",
                "error": str(exc),
            })

    await log_audit_action(
        user["user_id"],
        "admin_restamp_legacy_documents",
        "employee_documents",
        "batch_operation",
        {"counts": counts, "limit": data.limit},
    )

    return {
        "success": True,
        "dry_run": False,
        "counts": counts,
        "results": results,
        "more_remaining": len(docs) >= data.limit,
        "note": (
            "If more_remaining is true, call this endpoint again to process "
            "the next batch."
        ),
    }
