#!/usr/bin/env python3
"""
P5 Duplicate Reconciliation Script (Dry-run by default)

- Detects and proposes deduplication for:
  * generated_contracts
  * agreement_acknowledgements
  * employee_documents
  * rtw_checks, dbs_checks, identity_verifications, address_verifications
  * lifecycle mixed applicant/employee records (audit only)
- Outputs JSON and CSV reports to backend/reports/p5/
- Never hard deletes; preserves history
- Dry-run by default; --apply requires --confirm-run-id <run_id>
- Supports --employee-id filter for safe testing
"""

import argparse
import os
import sys
import json
import csv
import uuid
from datetime import datetime
from collections import defaultdict

# --- Load .env files and configure environment ---
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    print("[ERROR] python-dotenv is required. Install with: pip install python-dotenv")
    sys.exit(1)

# Load both backend/.env and project root .env if present
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.resolve()
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(SCRIPT_DIR.parent / ".env", override=False)

# --- MongoDB Setup (prioritized env vars) ---
from pymongo import MongoClient

MONGO_ENV_VARS = ["MONGO_URL", "MONGODB_URI", "MONGO_URI", "DATABASE_URL"]
mongo_url = None
mongo_env_var = None
for var in MONGO_ENV_VARS:
    val = os.environ.get(var)
    if val:
        mongo_url = val
        mongo_env_var = var
        break
if not mongo_url:
    print(f"[ERROR] No MongoDB URI found. Set one of: {', '.join(MONGO_ENV_VARS)} in .env or backend/.env.")
    sys.exit(1)

# DB name: prefer DB_NAME env, else parse from URI
db_name = os.environ.get("DB_NAME")
if not db_name:
    # Try to parse db name from URI
    import re
    m = re.match(r"mongodb(?:\+srv)?://[^/]+/([^?]+)", mongo_url)
    if m:
        db_name = m.group(1)
if not db_name:
    print("[ERROR] No DB_NAME found in env or URI. Set DB_NAME in .env or backend/.env, or use a URI with a database name.")
    sys.exit(1)

# Print safe connection info
from urllib.parse import urlparse
parsed = urlparse(mongo_url)
host = parsed.hostname or "?"
print(f"[INFO] Connecting to MongoDB:")
print(f"  Env var: {mongo_env_var}")
print(f"  Database: {db_name}")
print(f"  Host: {host}")

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "p5")
os.makedirs(REPORT_DIR, exist_ok=True)

COLLECTIONS = [
    "generated_contracts",
    "agreement_acknowledgements",
    "employee_documents",
    "rtw_checks",
    "dbs_checks",
    "identity_verifications",
    "address_verifications",
]

CHECK_COLLECTIONS = [
    "rtw_checks",
    "dbs_checks",
    "identity_verifications",
    "address_verifications",
]

# --- Utility Functions ---
def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def write_json_report(name, data):
    path = os.path.join(REPORT_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"[report] {path}")

def write_csv_report(name, rows, fieldnames):
    path = os.path.join(REPORT_DIR, f"{name}.csv")
    with open(path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"[report] {path}")

def parse_args():
    parser = argparse.ArgumentParser(description="P5 Duplicate Reconciliation Script")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--confirm-run-id", type=str, help="Required with --apply for safety")
    parser.add_argument("--employee-id", type=str, help="Limit to one employee for testing")
    return parser.parse_args()

def get_run_id():
    return str(uuid.uuid4())[:8]

# --- Main Logic ---
def main():
    args = parse_args()
    dry_run = not args.apply
    run_id = get_run_id() if dry_run else args.confirm_run_id
    if args.apply and not args.confirm_run_id:
        print("[ERROR] --apply requires --confirm-run-id <run_id>")
        sys.exit(1)
    print(f"[INFO] Mode: {'DRY-RUN' if dry_run else 'APPLY'} | Run ID: {run_id}")

    client = MongoClient(mongo_url)
    db = client[db_name]

    summary = {}
    all_mutations = []

    # --- 1. generated_contracts ---
    contracts = list(db.generated_contracts.find({}))
    contracts_by_emp = defaultdict(list)
    for row in contracts:
        if args.employee_id and row.get("employee_id") != args.employee_id:
            continue
        contracts_by_emp[row.get("employee_id")].append(row)
    contract_mutations = []
    for emp_id, rows in contracts_by_emp.items():
        actives = [r for r in rows if r.get("latest_active", True) and r.get("status") != "superseded"]
        if len(actives) <= 1:
            continue
        # Sort by created/updated
        actives.sort(key=lambda r: r.get("updated_at") or r.get("created_at") or r.get("_id"), reverse=True)
        keep = actives[0]
        for stale in actives[1:]:
            mutation = {
                "_id": stale["_id"],
                "employee_id": emp_id,
                "action": "supersede_contract",
                "set": {
                    "latest_active": False,
                    "status": "superseded",
                    "superseded_by_id": keep["_id"],
                    "superseded_at": now_iso(),
                    "superseded_reason": "p5_duplicate_reconciliation",
                    "p5_reconciled_at": now_iso(),
                    "p5_reconciliation_run_id": run_id,
                },
            }
            contract_mutations.append(mutation)
    summary["generated_contracts"] = len(contract_mutations)
    all_mutations.extend(contract_mutations)
    write_json_report("generated_contracts_mutations", contract_mutations)

    # --- 2. agreement_acknowledgements ---
    agreements = list(db.agreement_acknowledgements.find({}))
    agreements_by_emp_type = defaultdict(list)
    for row in agreements:
        if args.employee_id and row.get("employee_id") != args.employee_id:
            continue
        key = (row.get("employee_id"), row.get("agreement_type"))
        agreements_by_emp_type[key].append(row)
    agreement_mutations = []
    for (emp_id, agreement_type), rows in agreements_by_emp_type.items():
        actives = [r for r in rows if r.get("latest_active", True) and r.get("status") != "superseded"]
        if len(actives) <= 1:
            continue
        actives.sort(key=lambda r: r.get("updated_at") or r.get("created_at") or r.get("_id"), reverse=True)
        keep = actives[0]
        for stale in actives[1:]:
            mutation = {
                "_id": stale["_id"],
                "employee_id": emp_id,
                "agreement_type": agreement_type,
                "action": "supersede_agreement",
                "set": {
                    "latest_active": False,
                    "status": "superseded",
                    "superseded_by_id": keep["_id"],
                    "superseded_at": now_iso(),
                    "superseded_reason": "p5_duplicate_reconciliation",
                    "p5_reconciled_at": now_iso(),
                    "p5_reconciliation_run_id": run_id,
                },
            }
            agreement_mutations.append(mutation)
    summary["agreement_acknowledgements"] = len(agreement_mutations)
    all_mutations.extend(agreement_mutations)
    write_json_report("agreement_acknowledgements_mutations", agreement_mutations)

    # --- 3. employee_documents ---
    docs = list(db.employee_documents.find({}))
    docs_by_emp_req = defaultdict(list)
    for row in docs:
        if args.employee_id and row.get("employee_id") != args.employee_id:
            continue
        docs_by_emp_req[(row.get("employee_id"), row.get("requirement_id"))].append(row)
    doc_mutations = []
    for (emp_id, req_id), rows in docs_by_emp_req.items():
        actives = [r for r in rows if r.get("status") not in ["superseded", "expired", "deleted"]]
        if len(actives) <= 1:
            continue
        actives.sort(key=lambda r: r.get("updated_at") or r.get("created_at") or r.get("_id"), reverse=True)
        keep = actives[0]
        for stale in actives[1:]:
            mutation = {
                "_id": stale["_id"],
                "employee_id": emp_id,
                "requirement_id": req_id,
                "action": "supersede_document",
                "set": {
                    "status": "superseded",
                    "superseded_by_id": keep["_id"],
                    "superseded_at": now_iso(),
                    "superseded_reason": "p5_duplicate_reconciliation",
                    "p5_reconciled_at": now_iso(),
                    "p5_reconciliation_run_id": run_id,
                },
            }
            doc_mutations.append(mutation)
    summary["employee_documents"] = len(doc_mutations)
    all_mutations.extend(doc_mutations)
    write_json_report("employee_documents_mutations", doc_mutations)

    # --- 4. Check collections ---
    check_mutations = []
    for coll in CHECK_COLLECTIONS:
        checks = list(db[coll].find({}))
        checks_by_emp = defaultdict(list)
        for row in checks:
            if args.employee_id and row.get("employee_id") != args.employee_id:
                continue
            checks_by_emp[row.get("employee_id")].append(row)
        for emp_id, rows in checks_by_emp.items():
            currents = [r for r in rows if r.get("is_current", True)]
            if len(currents) <= 1:
                continue
            currents.sort(key=lambda r: r.get("verified_at") or r.get("updated_at") or r.get("created_at") or r.get("_id"), reverse=True)
            keep = currents[0]
            for stale in currents[1:]:
                mutation = {
                    "_id": stale["_id"],
                    "employee_id": emp_id,
                    "collection": coll,
                    "action": "unset_current",
                    "set": {
                        "is_current": False,
                        "superseded_by_id": keep["_id"],
                        "superseded_at": now_iso(),
                        "superseded_reason": "p5_duplicate_reconciliation",
                        "p5_reconciled_at": now_iso(),
                        "p5_reconciliation_run_id": run_id,
                    },
                }
                check_mutations.append(mutation)
    summary["checks"] = len(check_mutations)
    all_mutations.extend(check_mutations)
    write_json_report("checks_mutations", check_mutations)

    # --- 5. Lifecycle mixed records (audit only) ---
    employees = list(db.employees.find({}))
    mixed_profiles = []
    for emp in employees:
        status = emp.get("status")
        legacy_flags = {k: emp.get(k) for k in ["is_applicant", "is_employee", "applicant_status"] if k in emp}
        if status in ["active", "onboarding", "inactive"] and legacy_flags.get("is_applicant"):
            mixed_profiles.append({"employee_id": emp.get("id"), "status": status, **legacy_flags})
        elif status in ["new", "screening"] and legacy_flags.get("is_employee"):
            mixed_profiles.append({"employee_id": emp.get("id"), "status": status, **legacy_flags})
    summary["lifecycle_mixed_profiles"] = len(mixed_profiles)
    write_json_report("lifecycle_mixed_profiles", mixed_profiles)

    # --- CSV Reports ---
    for name, mutations in [
        ("generated_contracts_mutations", contract_mutations),
        ("agreement_acknowledgements_mutations", agreement_mutations),
        ("employee_documents_mutations", doc_mutations),
        ("checks_mutations", check_mutations),
    ]:
        if mutations:
            fieldnames = sorted(set().union(*(m.keys() | m.get("set", {}).keys() for m in mutations)))
            rows = []
            for m in mutations:
                row = {**m, **m.get("set", {})}
                row.pop("set", None)
                rows.append(row)
            write_csv_report(name, rows, fieldnames)

    # --- Print Summary ---
    print("\n=== P5 Duplicate Reconciliation Summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"Total proposed mutations: {len(all_mutations)}")
    if dry_run:
        print("[DRY-RUN] No database writes performed.")
    else:
        print("[APPLY] Applying mutations...")
        for m in all_mutations:
            coll = None
            if m["action"] == "supersede_contract":
                coll = db.generated_contracts
            elif m["action"] == "supersede_agreement":
                coll = db.agreement_acknowledgements
            elif m["action"] == "supersede_document":
                coll = db.employee_documents
            elif m["action"] == "unset_current":
                coll = db[m["collection"]]
            if coll:
                coll.update_one({"_id": m["_id"]}, {"$set": m["set"]})
        print("[APPLY] All mutations applied.")

if __name__ == "__main__":
    main()
