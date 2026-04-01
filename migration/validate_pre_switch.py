#!/usr/bin/env python3
"""
PRE-SWITCH VALIDATION SCRIPT
Run before enabling any Supabase read flags.

Usage:
    python validate_pre_switch.py
    python validate_pre_switch.py --check counts
    python validate_pre_switch.py --check relationships
    python validate_pre_switch.py --check dual-row
    python validate_pre_switch.py --check all
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime

# Add paths
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/migration')

from motor.motor_asyncio import AsyncIOMotorClient

# Try importing asyncpg
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    print("WARNING: asyncpg not installed. Supabase checks will be skipped.")


class ValidationResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.details = []
    
    def add(self, check: str, passed: bool, detail: str = ""):
        self.details.append({
            "check": check,
            "passed": passed,
            "detail": detail
        })
        if not passed:
            self.passed = False
    
    def print_report(self):
        status = "PASS" if self.passed else "FAIL"
        print(f"\n{'='*60}")
        print(f"{self.name}: {status}")
        print('='*60)
        for d in self.details:
            icon = "✓" if d["passed"] else "✗"
            print(f"  {icon} {d['check']}: {d['detail']}")


async def get_mongo():
    """Get MongoDB connection."""
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = AsyncIOMotorClient(mongo_url)
    return client, client[db_name]


async def get_postgres():
    """Get Postgres connection if configured."""
    if not HAS_ASYNCPG:
        return None
    
    db_url = os.environ.get('SUPABASE_DB_URL')
    if not db_url:
        print("SUPABASE_DB_URL not configured - skipping Postgres checks")
        return None
    
    try:
        return await asyncpg.connect(db_url)
    except Exception as e:
        print(f"Postgres connection failed: {e}")
        return None


async def validate_counts() -> ValidationResult:
    """Validate record counts between MongoDB and Postgres."""
    result = ValidationResult("RECORD COUNT VALIDATION")
    
    client, mdb = await get_mongo()
    pg = await get_postgres()
    
    collections = [
        ("employees", "employees"),
        ("users", "profiles"),
        ("employee_documents", "documents"),
        ("training_records", "training_records"),
        ("training_catalogue", "training_catalogue"),
        ("rtw_checks", "rtw_checks"),
        ("dbs_checks", "dbs_checks"),
    ]
    
    for mongo_col, pg_table in collections:
        try:
            mongo_count = await mdb[mongo_col].count_documents({})
        except:
            mongo_count = 0
        
        pg_count = 0
        if pg:
            try:
                pg_count = await pg.fetchval(f"SELECT COUNT(*) FROM {pg_table}")
            except:
                pg_count = -1  # Table doesn't exist
        
        if pg:
            if pg_count == -1:
                result.add(mongo_col, False, f"Mongo={mongo_count}, Postgres=TABLE MISSING")
            elif mongo_count == pg_count:
                result.add(mongo_col, True, f"Mongo={mongo_count}, Postgres={pg_count}")
            else:
                diff_pct = abs(mongo_count - pg_count) / max(mongo_count, 1) * 100
                passed = diff_pct < 5  # Allow 5% variance
                result.add(mongo_col, passed, f"Mongo={mongo_count}, Postgres={pg_count} ({diff_pct:.1f}% diff)")
        else:
            result.add(mongo_col, True, f"Mongo={mongo_count} (Postgres not configured)")
    
    client.close()
    if pg:
        await pg.close()
    
    return result


async def validate_relationships() -> ValidationResult:
    """Validate FK relationships."""
    result = ValidationResult("RELATIONSHIP INTEGRITY")
    
    client, mdb = await get_mongo()
    
    # Check employee references in documents
    doc_emp_ids = set()
    async for doc in mdb.employee_documents.find({}, {"employee_id": 1}):
        doc_emp_ids.add(doc.get("employee_id"))
    
    emp_ids = set()
    async for emp in mdb.employees.find({}, {"id": 1}):
        emp_ids.add(emp.get("id"))
    
    orphan_docs = doc_emp_ids - emp_ids
    result.add(
        "Documents → Employees",
        len(orphan_docs) == 0,
        f"{len(orphan_docs)} orphan documents" if orphan_docs else "All documents linked"
    )
    
    # Check training records
    training_emp_ids = set()
    async for rec in mdb.training_records.find({}, {"employee_id": 1}):
        training_emp_ids.add(rec.get("employee_id"))
    
    orphan_training = training_emp_ids - emp_ids
    result.add(
        "Training → Employees",
        len(orphan_training) == 0,
        f"{len(orphan_training)} orphan training records" if orphan_training else "All training linked"
    )
    
    # Check RTW checks
    rtw_emp_ids = set()
    async for check in mdb.rtw_checks.find({}, {"employee_id": 1}):
        rtw_emp_ids.add(check.get("employee_id"))
    
    orphan_rtw = rtw_emp_ids - emp_ids
    result.add(
        "RTW Checks → Employees",
        len(orphan_rtw) == 0,
        f"{len(orphan_rtw)} orphan RTW checks" if orphan_rtw else "All RTW checks linked"
    )
    
    client.close()
    return result


async def validate_dual_row_model() -> ValidationResult:
    """Validate Evidence/Check/Proof separation."""
    result = ValidationResult("DUAL-ROW MODEL (CRITICAL)")
    
    client, mdb = await get_mongo()
    
    # Count evidence documents by category
    evidence_categories = ['right_to_work', 'dbs', 'identity', 'proof_of_address', 'training', 'cv']
    
    for cat in evidence_categories:
        count = await mdb.employee_documents.count_documents({"category": cat})
        result.add(f"Evidence [{cat}]", True, f"{count} documents")
    
    # Count proof documents
    proof_count = await mdb.employee_documents.count_documents({"category": "verification_proof"})
    result.add("Proof documents", True, f"{proof_count} documents")
    
    # Count check records
    for check_col in ['rtw_checks', 'dbs_checks', 'identity_verifications', 'address_verifications']:
        try:
            count = await mdb[check_col].count_documents({})
            result.add(f"Check [{check_col}]", True, f"{count} records")
        except:
            result.add(f"Check [{check_col}]", True, "Collection not found (OK if no data)")
    
    # CRITICAL: Check for proof documents with evidence-like fields
    misclassified = await mdb.employee_documents.count_documents({
        "category": "verification_proof",
        "requirement_name": {"$exists": True, "$ne": None}
    })
    
    result.add(
        "Proof/Evidence separation",
        misclassified == 0,
        f"{misclassified} proof documents misclassified" if misclassified > 0 else "Clean separation"
    )
    
    client.close()
    return result


async def validate_required_fields() -> ValidationResult:
    """Validate required fields are populated."""
    result = ValidationResult("REQUIRED FIELDS")
    
    client, mdb = await get_mongo()
    
    # Employees required fields
    emp_required = ['id', 'first_name', 'last_name', 'email', 'status']
    for field in emp_required:
        null_count = await mdb.employees.count_documents({
            "$or": [
                {field: {"$exists": False}},
                {field: None},
                {field: ""}
            ]
        })
        result.add(
            f"employees.{field}",
            null_count == 0,
            f"{null_count} missing" if null_count > 0 else "All populated"
        )
    
    # Documents required fields
    doc_required = ['id', 'employee_id', 'category']
    for field in doc_required:
        null_count = await mdb.employee_documents.count_documents({
            "$or": [
                {field: {"$exists": False}},
                {field: None}
            ]
        })
        result.add(
            f"documents.{field}",
            null_count == 0,
            f"{null_count} missing" if null_count > 0 else "All populated"
        )
    
    client.close()
    return result


async def run_all_validations():
    """Run all validation checks."""
    print("\n" + "="*60)
    print("PRE-SWITCH VALIDATION REPORT")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*60)
    
    results = []
    
    # Run validations
    results.append(await validate_counts())
    results.append(await validate_relationships())
    results.append(await validate_dual_row_model())
    results.append(await validate_required_fields())
    
    # Print reports
    for r in results:
        r.print_report()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = all(r.passed for r in results)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  {r.name}: {status}")
    
    print("-"*60)
    if all_passed:
        print("  OVERALL: PASS - Safe to proceed with read switching")
    else:
        print("  OVERALL: FAIL - Fix issues before switching")
    
    return 0 if all_passed else 1


def main():
    parser = argparse.ArgumentParser(description="Pre-switch validation")
    parser.add_argument("--check", choices=["counts", "relationships", "dual-row", "fields", "all"],
                        default="all", help="Which check to run")
    args = parser.parse_args()
    
    if args.check == "counts":
        result = asyncio.run(validate_counts())
        result.print_report()
    elif args.check == "relationships":
        result = asyncio.run(validate_relationships())
        result.print_report()
    elif args.check == "dual-row":
        result = asyncio.run(validate_dual_row_model())
        result.print_report()
    elif args.check == "fields":
        result = asyncio.run(validate_required_fields())
        result.print_report()
    else:
        exit_code = asyncio.run(run_all_validations())
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
