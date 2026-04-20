"""
backfill_requirement_keys.py
============================
Safe backfill utility: resolves `requirement_key` on existing employee_documents
that only carry `requirement_id` (legacy / worker-portal uploads).

Usage:
    python backfill_requirement_keys.py [--dry-run]

Flags:
    --dry-run    Print what would be changed without writing to MongoDB.

The script:
  1. Finds all employee_documents where requirement_key is absent/None.
  2. Tries to resolve requirement_key from requirement_id via the alias table.
  3. Updates matching docs with the resolved requirement_key.
  4. Reports: total docs, resolved, unresolved, skipped (already had key).
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from requirement_definitions import resolve_requirement_key

# ── Mongo connection ─────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.environ.get("MONGODB_DB", os.environ.get("MONGO_DB", "osabeacare"))

DRY_RUN = "--dry-run" in sys.argv


async def run():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["employee_documents"]

    now = datetime.now(timezone.utc).isoformat()

    total        = 0
    skipped      = 0   # already had requirement_key
    resolved     = 0   # successfully backfilled
    unresolved   = 0   # could not map requirement_id → requirement_key
    errors       = 0

    cursor = col.find(
        {
            "$or": [
                {"requirement_key": {"$exists": False}},
                {"requirement_key": None},
                {"requirement_key": ""},
            ]
        },
        {"_id": 1, "id": 1, "employee_id": 1, "requirement_id": 1, "requirement_key": 1}
    )

    unresolved_samples = []

    async for doc in cursor:
        total += 1
        existing_key = doc.get("requirement_key", "")
        if existing_key and existing_key.strip():
            skipped += 1
            continue

        raw_id  = doc.get("requirement_id", "")
        new_key = resolve_requirement_key(raw_id)

        if not new_key:
            unresolved += 1
            if len(unresolved_samples) < 10:
                unresolved_samples.append({
                    "doc_id":      doc.get("id") or str(doc.get("_id")),
                    "employee_id": doc.get("employee_id"),
                    "requirement_id": raw_id,
                })
            continue

        print(f"  {'[DRY-RUN] ' if DRY_RUN else ''}doc_id={doc.get('id') or doc.get('_id')} "
              f"requirement_id={raw_id!r} → requirement_key={new_key!r}")

        if not DRY_RUN:
            try:
                await col.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "requirement_key": new_key,
                        "backfilled_at":   now,
                        "backfill_source": "backfill_requirement_keys.py",
                    }}
                )
                resolved += 1
            except Exception as exc:
                print(f"  ERROR updating doc {doc.get('id')}: {exc}")
                errors += 1
        else:
            resolved += 1   # count as would-be resolved in dry-run

    print()
    print("=" * 60)
    print(f"Backfill {'(DRY-RUN) ' if DRY_RUN else ''}complete")
    print(f"  Total docs without requirement_key : {total}")
    print(f"  Already had key (skipped)          : {skipped}")
    print(f"  Resolved (backfilled)              : {resolved}")
    print(f"  Unresolved (no alias match)        : {unresolved}")
    if errors:
        print(f"  Errors                             : {errors}")
    print("=" * 60)

    if unresolved_samples:
        print("\nSample unresolved docs (first 10):")
        for s in unresolved_samples:
            print(f"  {s}")
        print("\nFor each unresolved doc, manually inspect requirement_id and add to")
        print("REQUIREMENT_ID_ALIASES in requirement_definitions.py, then re-run.")

    client.close()


if __name__ == "__main__":
    asyncio.run(run())
