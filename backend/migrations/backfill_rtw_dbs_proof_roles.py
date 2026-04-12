"""
Backfill proof_document_id and proof document roles for legacy RTW/DBS current checks.

Why this exists:
- Older check records were created before proof_document_id/document_role split.
- New filtering relies on proof_document_id and document_role=proof.
- Legacy records can therefore leak proof files into evidence/completeness paths.

Safety model:
- Default is DRY-RUN.
- Only touches CURRENT checks (is_current=True).
- Only backfills when proof linkage is explicit/unambiguous from existing fields.
- Uses legacy linkage pattern in order:
  1) check.proof_document_id (already present) -> skip check backfill, ensure doc role only
  2) explicit proof-marked IDs in linked_evidence_ids/document metadata
  3) legacy alias field evidence_document_id (documented historical alias)
- If ambiguous, script skips the check and reports it.

Usage:
  python migrations/backfill_rtw_dbs_proof_roles.py
  python migrations/backfill_rtw_dbs_proof_roles.py --apply
"""

import argparse
import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient

PROOF_ROLE_VALUES = {"proof", "verification_proof", "check_proof"}
PROOF_SOURCE_TYPES = {"verification_proof", "check_proof"}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    return []


async def _fetch_doc_map(db, employee_id: str, doc_ids: list[str]) -> dict[str, dict]:
    if not doc_ids:
        return {}
    docs = await db.employee_documents.find(
        {"employee_id": employee_id, "id": {"$in": doc_ids}},
        {
            "_id": 0,
            "id": 1,
            "employee_id": 1,
            "requirement_id": 1,
            "document_role": 1,
            "source_type": 1,
            "uploaded_by": 1,
            "uploaded_by_worker": 1,
            "status": 1,
            "is_active": 1,
        },
    ).to_list(length=500)
    return {d.get("id"): d for d in docs if d.get("id")}


def _pick_proof_doc_id(check: dict, doc_map: dict[str, dict]) -> tuple[Optional[str], str]:
    """
    Return (proof_doc_id, reason).

    Only returns an ID when linkage is explicit enough to be safe.
    """
    existing_proof = check.get("proof_document_id")
    if isinstance(existing_proof, str) and existing_proof.strip() and existing_proof in doc_map:
        return existing_proof, "already_has_proof_document_id"

    evidence_doc_id = check.get("evidence_document_id")
    linked_ids = [d for d in _as_list(check.get("linked_evidence_ids")) if d in doc_map]

    # 1) Strongest signal: document already tagged or sourced as proof.
    proof_marked_ids = []
    for doc_id in linked_ids:
        doc = doc_map.get(doc_id) or {}
        role = (doc.get("document_role") or "").lower().strip()
        source_type = (doc.get("source_type") or "").lower().strip()
        if role in PROOF_ROLE_VALUES or source_type in PROOF_SOURCE_TYPES:
            proof_marked_ids.append(doc_id)

    if len(proof_marked_ids) == 1:
        return proof_marked_ids[0], "single_proof_marked_linked_document"
    if len(proof_marked_ids) > 1:
        return None, "ambiguous_multiple_proof_marked_documents"

    # 2) Legacy documented storage pattern:
    #    evidence_document_id was historically used for proof-of-check file.
    if isinstance(evidence_doc_id, str) and evidence_doc_id.strip() and evidence_doc_id in doc_map:
        return evidence_doc_id, "legacy_evidence_document_id_alias"

    # 3) If only one linked evidence doc exists and no conflicting signals.
    if len(linked_ids) == 1:
        return linked_ids[0], "single_linked_evidence_document"

    if len(linked_ids) > 1:
        return None, "ambiguous_multiple_linked_evidence_documents"

    return None, "no_linkage_candidate"


async def _process_collection(db, collection_name: str, apply_changes: bool) -> dict[str, int]:
    now = datetime.now(timezone.utc).isoformat()
    checks = await db[collection_name].find(
        {"is_current": True},
        {
            "_id": 0,
            "id": 1,
            "employee_id": 1,
            "proof_document_id": 1,
            "evidence_document_id": 1,
            "linked_evidence_ids": 1,
            "check_type": 1,
            "method": 1,
            "checked_at": 1,
        },
    ).to_list(length=5000)

    stats = {
        "checked": 0,
        "backfilled_check": 0,
        "updated_doc": 0,
        "already_ok": 0,
        "skipped_ambiguous": 0,
        "skipped_missing_doc": 0,
    }

    print(f"\n[{collection_name}] current checks: {len(checks)}")

    for check in checks:
        stats["checked"] += 1
        check_id = check.get("id")
        employee_id = check.get("employee_id")
        if not check_id or not employee_id:
            stats["skipped_missing_doc"] += 1
            print(f"- skip check missing id/employee_id: {check}")
            continue

        candidate_ids = []
        if isinstance(check.get("proof_document_id"), str):
            candidate_ids.append(check.get("proof_document_id"))
        if isinstance(check.get("evidence_document_id"), str):
            candidate_ids.append(check.get("evidence_document_id"))
        candidate_ids.extend(_as_list(check.get("linked_evidence_ids")))
        candidate_ids = [c for c in dict.fromkeys(candidate_ids) if c]

        doc_map = await _fetch_doc_map(db, employee_id, candidate_ids)
        proof_doc_id, reason = _pick_proof_doc_id(check, doc_map)

        if not proof_doc_id:
            stats["skipped_ambiguous"] += 1
            print(f"- skip {collection_name}:{check_id} reason={reason}")
            continue

        doc = doc_map.get(proof_doc_id)
        if not doc:
            stats["skipped_missing_doc"] += 1
            print(f"- skip {collection_name}:{check_id} missing doc {proof_doc_id}")
            continue

        needs_check_update = not (check.get("proof_document_id") == proof_doc_id)
        role = (doc.get("document_role") or "").lower().strip()
        needs_doc_update = role not in PROOF_ROLE_VALUES or doc.get("proof_role_current") is not True

        if not needs_check_update and not needs_doc_update:
            stats["already_ok"] += 1
            print(f"- ok   {collection_name}:{check_id} proof_doc={proof_doc_id}")
            continue

        print(
            f"- {'apply' if apply_changes else 'dry'} {collection_name}:{check_id} "
            f"proof_doc={proof_doc_id} reason={reason} "
            f"check_update={needs_check_update} doc_update={needs_doc_update}"
        )

        if not apply_changes:
            continue

        if needs_check_update:
            await db[collection_name].update_one(
                {"id": check_id},
                {
                    "$set": {
                        "proof_document_id": proof_doc_id,
                        "proof_backfilled_at": now,
                        "proof_backfill_reason": reason,
                        "proof_backfill_source": "backfill_rtw_dbs_proof_roles",
                    }
                },
            )
            stats["backfilled_check"] += 1

        if needs_doc_update:
            await db.employee_documents.update_one(
                {"id": proof_doc_id, "employee_id": employee_id},
                {
                    "$set": {
                        "document_role": "proof",
                        "proof_role_current": True,
                        "proof_role_check_id": check_id,
                        "proof_role_backfilled_at": now,
                        "proof_role_backfill_source": "backfill_rtw_dbs_proof_roles",
                        "updated_at": now,
                    }
                },
            )
            stats["updated_doc"] += 1

    return stats


async def run_backfill(apply_changes: bool) -> None:
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    try:
        rtw_stats = await _process_collection(db, "rtw_checks", apply_changes)
        dbs_stats = await _process_collection(db, "dbs_checks", apply_changes)

        print("\n=== SUMMARY ===")
        print(f"Mode: {'APPLY' if apply_changes else 'DRY-RUN'}")
        print(f"rtw_checks: {rtw_stats}")
        print(f"dbs_checks: {dbs_stats}")
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill proof_document_id/document_role for legacy RTW/DBS current checks"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply writes (default is dry-run)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_backfill(args.apply))
