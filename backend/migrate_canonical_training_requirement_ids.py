"""
Canonical training requirement_id back-fill migration.

Usage
-----
    python backend/migrate_canonical_training_requirement_ids.py [--dry-run] [--employee <id>]

What it does
------------
For every employee (or a single employee when `--employee` is supplied):

    1. Groups their active `training_records` by canonical training key
       (alias-aware — see governance.training_dedup.canonical_training_key).
    2. For each group with >1 active record, keeps the best record
       (verified > completed > awaiting > rejected; latest completion wins
       ties) and marks the rest as `record_status == "superseded"` with an
       audit-trail entry.
    3. Stamps the kept record's `requirement_id` with the canonical code
       when it currently stores a legacy alias. The prior value is kept in
       `requirement_id_before_canonicalisation` for rollback.

Safety
------
    * Idempotent — re-running it after it has converged is a no-op.
    * Never deletes rows; only flips `record_status`.
    * Never changes verification state or completion dates.
    * `--dry-run` prints the plan without writing.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load backend/.env the same way server.py does so the migration picks up
# MONGO_URL / DB_NAME without requiring them to be exported in the shell.
try:
    from dotenv import load_dotenv
    _here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_here, ".env"))
except Exception:
    pass

from governance.training_dedup import (  # noqa: E402
    canonical_training_key,
    pick_best_training_record,
    reconcile_active_training_records,
)

logger = logging.getLogger("migrate_canonical_training_requirement_ids")


def _connect():
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get("MONGO_URI")
    db_name = os.environ.get("DB_NAME") or os.environ.get("MONGO_DB") or "osabea"
    if not mongo_url:
        raise SystemExit("MONGO_URL environment variable is required")
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


async def _group_active_by_canonical(
    db: Any, employee_id: str
) -> Dict[str, List[Dict[str, Any]]]:
    raw = await db.training_records.find(
        {
            "employee_id": employee_id,
            "record_status": {"$nin": ["deleted", "superseded"]},
        },
        {"_id": 0},
    ).to_list(500)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for rec in raw:
        key = canonical_training_key(rec)
        if not key:
            continue
        grouped.setdefault(key, []).append(rec)
    return grouped


async def migrate(employee_id: str = None, dry_run: bool = False) -> Dict[str, Any]:
    db = _connect()
    summary = {
        "employees_scanned": 0,
        "groups_converged": 0,
        "rows_superseded": 0,
        "rows_canonicalised": 0,
        "dry_run": dry_run,
        "details": [],
    }

    if employee_id:
        employee_ids = [employee_id]
    else:
        employee_ids = [
            e["id"]
            async for e in db.employees.find({}, {"_id": 0, "id": 1})
            if e.get("id")
        ]

    for emp_id in employee_ids:
        summary["employees_scanned"] += 1
        grouped = await _group_active_by_canonical(db, emp_id)

        for canonical_code, records in grouped.items():
            if len(records) <= 1:
                rec = records[0]
                if rec.get("requirement_id") != canonical_code and canonical_code:
                    summary["rows_canonicalised"] += 1
                    summary["details"].append({
                        "employee_id": emp_id,
                        "canonical_code": canonical_code,
                        "action": "canonicalise_only",
                        "record_id": rec.get("id"),
                        "previous_requirement_id": rec.get("requirement_id"),
                    })
                    if not dry_run:
                        await reconcile_active_training_records(
                            db,
                            emp_id,
                            canonical_code,
                            keep_record_id=rec.get("id"),
                            actor_id="migration_canonicalise",
                            reason="migration_canonical_requirement_id",
                        )
                continue

            best = pick_best_training_record(records)
            keep_id = best.get("id") if best else None
            superseded_ids = [r.get("id") for r in records if r.get("id") != keep_id]
            summary["groups_converged"] += 1
            summary["rows_superseded"] += len(superseded_ids)
            summary["details"].append({
                "employee_id": emp_id,
                "canonical_code": canonical_code,
                "action": "supersede_duplicates",
                "kept_record_id": keep_id,
                "superseded_record_ids": superseded_ids,
            })
            if not dry_run:
                await reconcile_active_training_records(
                    db,
                    emp_id,
                    canonical_code,
                    keep_record_id=keep_id,
                    actor_id="migration_canonicalise",
                    reason="migration_canonical_requirement_id",
                )

    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no writes")
    parser.add_argument("--employee", help="Scope to a single employee id")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    summary = asyncio.run(migrate(employee_id=args.employee, dry_run=args.dry_run))

    print("=" * 70)
    print(f"Employees scanned       : {summary['employees_scanned']}")
    print(f"Duplicate groups        : {summary['groups_converged']}")
    print(f"Rows superseded         : {summary['rows_superseded']}")
    print(f"Rows canonicalised only : {summary['rows_canonicalised']}")
    print(f"Mode                    : {'DRY-RUN' if summary['dry_run'] else 'APPLIED'}")
    print("=" * 70)
    for detail in summary["details"]:
        print(detail)


if __name__ == "__main__":
    main()
