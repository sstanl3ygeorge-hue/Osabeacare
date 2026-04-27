"""
One-off agreement reset repair for employee 9355cb2a-99f3-4d61-b021-40ee7fcd911b.

Purpose:
- Reset ONLY agreements (contract + handbook) to first-issue worker-actionable state.
- Preserve audit/history by superseding old rows instead of deleting.
- Be idempotent: never leave duplicate active agreement rows.

Usage:
    python backend/scripts/reset_employee_9355_agreements.py \
      --admin-user-id <ADMIN_USER_ID> \
      --admin-role admin
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from motor.motor_asyncio import AsyncIOMotorClient

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from agreement_document_service import (  # noqa: E402
    CONTRACT_AGREEMENT_TYPE,
    HANDBOOK_AGREEMENT_TYPE,
    ensure_agreement_rendered,
)

TARGET_EMPLOYEE_ID = "9355cb2a-99f3-4d61-b021-40ee7fcd911b"
ALLOWED_ROLES = {"admin", "superadmin"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mongo_config() -> tuple[str, str]:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGODB_DB") or os.environ.get("MONGO_DB", "osabeacare")
    return uri, db_name


async def _assert_admin_actor(db, admin_user_id: str, admin_role: str) -> None:
    if admin_role not in ALLOWED_ROLES:
        raise RuntimeError(f"--admin-role must be one of {sorted(ALLOWED_ROLES)}")

    users_doc = await db.users.find_one({"id": admin_user_id}, {"_id": 0, "id": 1, "role": 1})
    admins_doc = await db.admin_users.find_one({"id": admin_user_id}, {"_id": 0, "id": 1, "role": 1})
    actor_doc = users_doc or admins_doc
    if not actor_doc:
        raise RuntimeError(f"Admin actor '{admin_user_id}' not found in users/admin_users")
    actor_role = str(actor_doc.get("role") or "").lower()
    if actor_role and actor_role not in ALLOWED_ROLES:
        raise RuntimeError(f"Admin actor role '{actor_role}' is not allowed")


async def _archive_agreement_rows(
    db,
    employee_id: str,
    agreement_type: str,
    admin_user_id: str,
    reason: str,
    now_iso: str,
) -> None:
    rows = await db.agreement_acknowledgements.find(
        {"employee_id": employee_id, "agreement_type": agreement_type},
        {"_id": 0},
    ).to_list(200)
    for row in rows:
        await db.agreement_acknowledgements.update_one(
            {"id": row.get("id"), "employee_id": employee_id},
            {
                "$set": {
                    "status": "superseded",
                    "verification_status": "superseded",
                    "superseded_at": now_iso,
                    "superseded_by": admin_user_id,
                    "supersede_reason": reason,
                    "updated_at": now_iso,
                    "repair_reset_batch": now_iso,
                }
            },
        )


async def _archive_generated_contracts(
    db,
    employee_id: str,
    admin_user_id: str,
    reason: str,
    now_iso: str,
) -> None:
    await db.generated_contracts.update_many(
        {
            "employee_id": employee_id,
            "$and": [
                {
                    "$or": [
                        {"status": {"$exists": False}},
                        {"status": {"$ne": "superseded"}},
                    ]
                },
                {
                    "$or": [
                        {"superseded_by_contract_id": {"$exists": False}},
                        {"superseded_by_contract_id": None},
                        {"superseded_by_contract_id": ""},
                    ]
                },
            ],
        },
        {
            "$set": {
                "status": "superseded",
                "superseded_at": now_iso,
                "superseded_by": admin_user_id,
                "supersede_reason": reason,
                "updated_at": now_iso,
                "repair_reset_batch": now_iso,
            }
        },
    )


def _empty_signature_fields() -> Dict[str, Any]:
    return {
        "signed_at": None,
        "signed_by": None,
        "completed_at": None,
        "completed_by": None,
        "worker_signed": False,
        "company_signed": False,
        "countersigned_at": None,
        "worker_signed_at": None,
        "worker_signer_name": None,
        "company_signed_at": None,
        "company_signer_name": None,
        "signed_document_url": None,
        "worker_signed_contract_pdf_url": None,
        "executed_contract_pdf_url": None,
        "acknowledged": False,
        "acknowledged_at": None,
        "verified_at": None,
        "verified_by": None,
        "verified_by_name": None,
        "verification_status": "pending",
    }


async def _reset_contract_agreement(db, employee: Dict[str, Any], admin_user_id: str, now_iso: str) -> Dict[str, Any]:
    employee_id = employee["id"]
    reason = "One-off manual repair reset for corrupted agreement state"
    await _archive_generated_contracts(db, employee_id, admin_user_id, reason, now_iso)
    await _archive_agreement_rows(db, employee_id, CONTRACT_AGREEMENT_TYPE, admin_user_id, reason, now_iso)

    # Force a fresh canonical rendered artifact by clearing canonical row first.
    await db.agreement_acknowledgements.update_one(
        {"employee_id": employee_id, "agreement_type": CONTRACT_AGREEMENT_TYPE},
        {
            "$set": {
                "id": f"agr_{CONTRACT_AGREEMENT_TYPE}_{employee_id}",
                "employee_id": employee_id,
                "agreement_type": CONTRACT_AGREEMENT_TYPE,
                "status": "pending_signature",
                "contract_state": "awaiting_worker_signature",
                "updated_at": now_iso,
                "created_at": now_iso,
            },
            "$unset": {
                "template_version": "",
                "rendered_file_url": "",
                "rendered_contract_pdf_url": "",
                "rejection_reason": "",
                "rejected_at": "",
                "rejected_by": "",
                "rejected_by_name": "",
                "superseded_by_contract_id": "",
                "recover_reason": "",
                "recovered_at": "",
            },
        },
        upsert=True,
    )

    await ensure_agreement_rendered(db, employee, CONTRACT_AGREEMENT_TYPE)

    active_contract = await db.generated_contracts.find_one(
        {
            "employee_id": employee_id,
            "$or": [
                {"status": "awaiting_worker_signature"},
                {"status": "pending_signature"},
            ],
            "$or": [
                {"superseded_by_contract_id": {"$exists": False}},
                {"superseded_by_contract_id": None},
                {"superseded_by_contract_id": ""},
            ],
        },
        sort=[("generated_at", -1), ("created_at", -1), ("id", -1)],
    )
    if not active_contract:
        # Defensive upsert fallback if renderer did not create generated_contract row.
        contract_id = f"contract_{employee_id}_{uuid.uuid4().hex[:12]}"
        await db.generated_contracts.update_one(
            {"id": contract_id},
            {
                "$set": {
                    "id": contract_id,
                    "employee_id": employee_id,
                    "status": "pending_signature",
                    "contract_state": "awaiting_worker_signature",
                    "generated_at": now_iso,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
            },
            upsert=True,
        )
        active_contract = await db.generated_contracts.find_one({"id": contract_id})

    active_contract_id = active_contract.get("id")
    agreement_row = await db.agreement_acknowledgements.find_one(
        {"employee_id": employee_id, "agreement_type": CONTRACT_AGREEMENT_TYPE},
        {"_id": 0},
    ) or {}

    await db.generated_contracts.update_one(
        {"id": active_contract_id, "employee_id": employee_id},
        {
            "$set": {
                **_empty_signature_fields(),
                "status": "pending_signature",
                "contract_state": "awaiting_worker_signature",
                "updated_at": now_iso,
            },
            "$unset": {
                "rejection_reason": "",
                "rejected_at": "",
                "rejected_by": "",
                "rejected_by_name": "",
                "superseded_by_contract_id": "",
            },
        },
    )

    await db.agreement_acknowledgements.update_one(
        {"employee_id": employee_id, "agreement_type": CONTRACT_AGREEMENT_TYPE},
        {
            "$set": {
                **_empty_signature_fields(),
                "status": "pending_signature",
                "contract_state": "awaiting_worker_signature",
                "active_contract_id": active_contract_id,
                "rendered_file_url": agreement_row.get("rendered_file_url"),
                "rendered_contract_pdf_url": agreement_row.get("rendered_contract_pdf_url") or agreement_row.get("rendered_file_url"),
                "updated_at": now_iso,
            },
            "$unset": {
                "rejection_reason": "",
                "rejected_at": "",
                "rejected_by": "",
                "rejected_by_name": "",
                "superseded_by_contract_id": "",
            },
        },
    )

    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "pending_contract_id": active_contract_id,
                "pending_contract_generated_at": now_iso,
                "contract_signed": False,
                "contract_signed_at": None,
                "contract_id": None,
                "updated_at": now_iso,
            }
        },
    )

    return {"active_contract_id": active_contract_id}


async def _reset_handbook_agreement(db, employee: Dict[str, Any], admin_user_id: str, now_iso: str) -> Dict[str, Any]:
    employee_id = employee["id"]
    reason = "One-off manual repair reset for corrupted agreement state"
    await _archive_agreement_rows(db, employee_id, HANDBOOK_AGREEMENT_TYPE, admin_user_id, reason, now_iso)

    await db.agreement_acknowledgements.update_one(
        {"employee_id": employee_id, "agreement_type": HANDBOOK_AGREEMENT_TYPE},
        {
            "$set": {
                "id": f"agr_{HANDBOOK_AGREEMENT_TYPE}_{employee_id}",
                "employee_id": employee_id,
                "agreement_type": HANDBOOK_AGREEMENT_TYPE,
                "status": "pending",
                "verification_status": "pending",
                "updated_at": now_iso,
                "created_at": now_iso,
            },
            "$unset": {
                "template_version": "",
                "rendered_file_url": "",
                "rejection_reason": "",
                "rejected_at": "",
                "rejected_by": "",
                "rejected_by_name": "",
                "system_issue": "",
                "superseded_by_acknowledgement_id": "",
                "recover_reason": "",
                "recovered_at": "",
            },
        },
        upsert=True,
    )

    await ensure_agreement_rendered(db, employee, HANDBOOK_AGREEMENT_TYPE)
    fresh = await db.agreement_acknowledgements.find_one(
        {"employee_id": employee_id, "agreement_type": HANDBOOK_AGREEMENT_TYPE},
        {"_id": 0},
    ) or {}
    await db.agreement_acknowledgements.update_one(
        {"employee_id": employee_id, "agreement_type": HANDBOOK_AGREEMENT_TYPE},
        {
            "$set": {
                **_empty_signature_fields(),
                "status": "pending",
                "verification_status": "pending",
                "rendered_file_url": fresh.get("rendered_file_url"),
                "updated_at": now_iso,
            },
            "$unset": {
                "rejection_reason": "",
                "rejected_at": "",
                "rejected_by": "",
                "rejected_by_name": "",
                "system_issue": "",
            },
        },
    )
    return {"handbook_ack_id": fresh.get("id")}


async def _log_repair_audit(
    db,
    employee_id: str,
    admin_user_id: str,
    admin_role: str,
    details: Dict[str, Any],
    now_iso: str,
) -> None:
    await db.audit_logs.insert_one(
        {
            "id": f"audit_agreement_reset_{employee_id}_{uuid.uuid4().hex[:8]}",
            "actor_id": admin_user_id,
            "actor_role": admin_role,
            "action": "manual_repair_reset_agreements",
            "entity_type": "employee",
            "entity_id": employee_id,
            "timestamp": now_iso,
            "metadata": {
                "scope": "agreements_only",
                "agreement_types": [CONTRACT_AGREEMENT_TYPE, HANDBOOK_AGREEMENT_TYPE],
                **details,
            },
        }
    )


async def run(admin_user_id: str, admin_role: str, employee_id: str) -> Dict[str, Any]:
    if employee_id != TARGET_EMPLOYEE_ID:
        raise RuntimeError(
            f"This one-off script is locked to employee {TARGET_EMPLOYEE_ID}. Received: {employee_id}"
        )

    mongo_uri, db_name = _mongo_config()
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    try:
        await _assert_admin_actor(db, admin_user_id, admin_role)
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            raise RuntimeError(f"Employee not found: {employee_id}")

        now_iso = _now_iso()
        contract_result = await _reset_contract_agreement(db, employee, admin_user_id, now_iso)
        handbook_result = await _reset_handbook_agreement(db, employee, admin_user_id, now_iso)

        summary = {
            "employee_id": employee_id,
            "contract": contract_result,
            "handbook": handbook_result,
            "reset_at": now_iso,
            "script": os.path.basename(__file__),
        }
        await _log_repair_audit(db, employee_id, admin_user_id, admin_role, summary, now_iso)
        return summary
    finally:
        client.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-off agreements reset for employee 9355... only.")
    parser.add_argument("--employee-id", default=TARGET_EMPLOYEE_ID)
    parser.add_argument("--admin-user-id", required=True)
    parser.add_argument("--admin-role", required=True, help="admin or superadmin")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = asyncio.run(
        run(
            admin_user_id=args.admin_user_id.strip(),
            admin_role=args.admin_role.strip().lower(),
            employee_id=args.employee_id.strip(),
        )
    )
    print("Agreement reset completed:")
    print(result)
