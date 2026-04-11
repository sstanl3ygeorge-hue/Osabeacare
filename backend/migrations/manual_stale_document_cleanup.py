"""
Manual stale document cleanup helper (admin-safe, explicit IDs only).

Purpose:
- Deactivate stale/seeded legacy documents without runtime heuristics.
- Preserve audit trail by writing clear cleanup metadata.

Usage examples:
  python manual_stale_document_cleanup.py --employee-id <emp_id> --doc-id <doc1> --doc-id <doc2> --reason "Legacy seed cleanup" --apply
  python manual_stale_document_cleanup.py --employee-id <emp_id> --doc-id <doc1> --reason "Legacy seed cleanup"

Default mode is DRY-RUN (no writes). Add --apply to execute updates.
"""

import argparse
import asyncio
import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient


async def run_cleanup(employee_id: str, doc_ids: list[str], reason: str, apply_changes: bool) -> None:
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    docs = await db.employee_documents.find(
        {"employee_id": employee_id, "id": {"$in": doc_ids}},
        {"_id": 0, "id": 1, "employee_id": 1, "requirement_id": 1, "status": 1, "review_status": 1, "is_active": 1},
    ).to_list(length=500)

    found_ids = {d.get("id") for d in docs}
    missing = [doc_id for doc_id in doc_ids if doc_id not in found_ids]

    print(f"Found {len(docs)} matching documents for employee {employee_id}.")
    if missing:
        print(f"Missing IDs ({len(missing)}): {missing}")

    if not docs:
        client.close()
        return

    now = datetime.now(timezone.utc).isoformat()
    update_payload = {
        "$set": {
            "is_active": False,
            "status": "superseded",
            "review_status": "invalidated",
            "cleanup_reason": reason,
            "cleanup_at": now,
            "cleanup_source": "manual_stale_document_cleanup",
            "updated_at": now,
        }
    }

    if not apply_changes:
        print("DRY-RUN ONLY. The following docs would be updated:")
        for doc in docs:
            print(
                f"- id={doc.get('id')} req={doc.get('requirement_id')} "
                f"status={doc.get('status')} review_status={doc.get('review_status')} is_active={doc.get('is_active')}"
            )
        client.close()
        return

    result = await db.employee_documents.update_many(
        {"employee_id": employee_id, "id": {"$in": [d.get("id") for d in docs]}},
        update_payload,
    )
    print(f"Updated {result.modified_count} documents.")
    client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manually deactivate stale employee documents by explicit IDs")
    parser.add_argument("--employee-id", required=True, help="Employee ID")
    parser.add_argument("--doc-id", action="append", dest="doc_ids", required=True, help="Document ID (repeat for multiple)")
    parser.add_argument("--reason", required=True, help="Audit reason for cleanup")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_cleanup(args.employee_id, args.doc_ids, args.reason, args.apply))
