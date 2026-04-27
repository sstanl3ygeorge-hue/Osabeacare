import argparse
import asyncio
import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient


ACTIVE_GENERATED_STATUSES = {
    "pending_signature",
    "awaiting_worker_signature",
    "signed",
    "awaiting_company_countersignature",
    "fully_executed",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _run(dry_run: bool) -> None:
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGO_DB_NAME", "osabea")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI or MONGODB_URI is required")

    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    now_iso = _iso_now()

    cursor = db.agreement_acknowledgements.find(
        {
            "agreement_type": "contract_acceptance",
            "$or": [
                {"verification_status": "rejected"},
                {"status": "rejected"},
                {"contract_state": {"$in": ["rejected_reopen_required", "action_required"]}},
            ],
            "status": {"$ne": "superseded"},
        },
        {"_id": 0},
    )
    rows = await cursor.to_list(length=100000)
    print(f"found_candidate_rows={len(rows)}")

    updated = 0
    for ack in rows:
        employee_id = ack.get("employee_id")
        if not employee_id:
            continue
        generated = await db.generated_contracts.find(
            {
                "employee_id": employee_id,
                "status": {"$in": list(ACTIVE_GENERATED_STATUSES)},
                "$or": [
                    {"superseded_by_contract_id": {"$exists": False}},
                    {"superseded_by_contract_id": None},
                    {"superseded_by_contract_id": ""},
                ],
            },
            {"_id": 0},
        ).sort([("generated_at", -1), ("created_at", -1), ("id", -1)]).limit(1).to_list(length=1)
        if not generated:
            continue
        latest = generated[0]
        active_contract_id = latest.get("id")
        if not active_contract_id:
            continue
        if ack.get("active_contract_id") == active_contract_id:
            continue

        print(
            f"employee_id={employee_id} ack_id={ack.get('id')} stale_active_contract_id={ack.get('active_contract_id')} "
            f"new_active_contract_id={active_contract_id} latest_status={latest.get('status')}"
        )
        if dry_run:
            continue

        result = await db.agreement_acknowledgements.update_one(
            {"id": ack.get("id"), "employee_id": employee_id},
            {
                "$set": {
                    "status": "superseded",
                    "superseded": True,
                    "superseded_at": now_iso,
                    "supersede_reason": "stale_rejected_ack_superseded_by_newer_generated_contract",
                    "superseded_by_contract_id": active_contract_id,
                    "is_historical": True,
                    "updated_at": now_iso,
                }
            },
        )
        if result.modified_count:
            updated += 1

    print(f"updated_rows={updated}")
    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mark stale rejected contract agreement rows historical when newer active generated contract exists.")
    parser.add_argument("--dry-run", action="store_true", help="Print candidates only, do not mutate")
    args = parser.parse_args()
    asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

