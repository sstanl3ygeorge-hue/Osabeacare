"""
Read-only triage: list RTW and DBS documents whose extraction is missing,
empty or low-confidence. Output is a worklist for admin re-review via the
existing UI (Profile → document → "Review Extracted Data" → Retry / Edit).

Safe: only reads from `db.employee_documents`, `db.document_extractions`
and `db.employees`. Makes NO writes.

Usage (from repo root, with the venv activated):
    python backend/_list_garbage_extractions.py
    python backend/_list_garbage_extractions.py --doc-types rtw
    python backend/_list_garbage_extractions.py --doc-types dbs --json
    python backend/_list_garbage_extractions.py --include-approved
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Make the backend package importable when running from repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

MONGO_URL = os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME") or os.environ.get("MONGO_DB") or "test_database"

if not MONGO_URL:
    print("ERROR: MONGO_URL not set. Run from a shell with the backend env loaded.", file=sys.stderr)
    sys.exit(1)


# ── classification (mirror of DocumentExtractionService._classify_document_type) ──

RTW_KEYWORDS = ("rtw", "right_to_work", "right to work", "visa", "brp",
                "residence", "permit", "share_code", "share code")
DBS_KEYWORDS = ("dbs", "disclosure", "barring")
TRAINING_KEYWORDS = ("training", "certificate", "course", "accreditation")


def classify(document: Dict[str, Any]) -> str:
    parts = [
        document.get("document_type_id") or "",
        document.get("document_type_name") or "",
        document.get("file_name") or "",
        document.get("original_filename") or "",
        document.get("category") or "",
        document.get("requirement_id") or "",
    ]
    text = " ".join(p.lower() for p in parts)
    if any(kw in text for kw in TRAINING_KEYWORDS) and "dbs" not in text:
        return "training_certificate"
    if any(kw in text for kw in DBS_KEYWORDS):
        return "dbs"
    if any(kw in text for kw in RTW_KEYWORDS):
        return "rtw"
    return "other"


# Fields we expect populated for each document class. If they are missing or
# null, the extraction is considered to have produced "empty / garbage".
EXPECTED_FIELDS = {
    "rtw": [
        "holder_name",
        "document_type",
        "document_number",
        # one of these must exist:
        ("expiry_date", "permission_end", "indefinite_right_to_work"),
    ],
    "dbs": [
        "name_on_certificate",
        "certificate_number",
        "issue_date",
        # dbs_level OR disclosure_type acceptable
        ("dbs_level", "disclosure_type"),
    ],
}

LOW_CONFIDENCE_THRESHOLD = 0.5


def field_problems(extraction: Dict[str, Any], doc_class: str) -> List[str]:
    """Return a list of field-level issues for this extraction."""
    if doc_class not in EXPECTED_FIELDS:
        return []
    fields = extraction.get("extracted_fields") or {}
    metadata = extraction.get("field_metadata") or {}
    problems: List[str] = []

    for spec in EXPECTED_FIELDS[doc_class]:
        if isinstance(spec, tuple):
            satisfied = any(
                fields.get(name) not in (None, "", [], {})
                for name in spec
            )
            if not satisfied:
                problems.append(f"missing all of: {'/'.join(spec)}")
        else:
            value = fields.get(spec)
            if value in (None, "", [], {}):
                problems.append(f"missing: {spec}")
                continue
            meta = metadata.get(spec) or {}
            conf = meta.get("confidence")
            src = meta.get("source_type")
            if src == "not_found":
                problems.append(f"low confidence ({spec}: source_type=not_found)")
            elif isinstance(conf, (int, float)) and conf < LOW_CONFIDENCE_THRESHOLD:
                problems.append(f"low confidence ({spec}: {conf})")
    return problems


async def main(doc_types: List[str], include_approved: bool, as_json: bool) -> int:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Pull all employee_documents that look like RTW or DBS by requirement_id
    # OR by classification. We post-filter on `classify()` to match production.
    query: Dict[str, Any] = {
        "$or": [
            {"requirement_id": {"$regex": "right_to_work|rtw|dbs|disclosure|barring", "$options": "i"}},
            {"document_type_id": {"$regex": "right_to_work|rtw|dbs|disclosure|barring", "$options": "i"}},
            {"document_type_name": {"$regex": "right to work|rtw|dbs|disclosure|barring", "$options": "i"}},
            {"category": {"$regex": "right_to_work|rtw|dbs", "$options": "i"}},
        ],
        "status": {"$nin": ["deleted", "superseded"]},
    }
    docs = await db.employee_documents.find(query, {"_id": 0}).to_list(length=10000)

    findings: List[Dict[str, Any]] = []

    for doc in docs:
        doc_class = classify(doc)
        if doc_class not in doc_types:
            continue

        doc_id = doc.get("id")
        if not doc_id:
            continue

        extraction = await db.document_extractions.find_one(
            {"document_id": doc_id}, {"_id": 0}
        )

        # Decide whether this entry needs admin attention.
        reasons: List[str] = []
        status = (extraction or {}).get("extraction_status") or "no_extraction_record"

        if not extraction:
            reasons.append("no extraction record exists")
        else:
            if status in ("failed", "error"):
                reasons.append(f"extraction_status={status}")
            issues = extraction.get("issues") or []
            blockers = [i for i in issues if (i.get("severity") or "").lower() == "blocker"]
            if blockers:
                reasons.append(f"{len(blockers)} blocker issue(s)")
            field_issues = field_problems(extraction, doc_class)
            reasons.extend(field_issues)

        # If the admin already approved this extraction, skip unless requested.
        review_status = (extraction or {}).get("review_status")
        if review_status == "approved" and not include_approved:
            continue

        if not reasons:
            continue

        emp_id = doc.get("employee_id")
        emp = await db.employees.find_one(
            {"id": emp_id},
            {"_id": 0, "first_name": 1, "last_name": 1, "employee_code": 1},
        ) if emp_id else None

        findings.append({
            "doc_class": doc_class,
            "document_id": doc_id,
            "employee_id": emp_id,
            "employee_name": (
                f"{(emp or {}).get('first_name', '')} {(emp or {}).get('last_name', '')}".strip()
                if emp else None
            ),
            "employee_code": (emp or {}).get("employee_code") if emp else None,
            "requirement_id": doc.get("requirement_id"),
            "file_name": doc.get("file_name") or doc.get("original_filename"),
            "uploaded_at": doc.get("created_at") or doc.get("uploaded_at"),
            "extraction_status": status,
            "extraction_review_status": review_status,
            "reasons": reasons,
        })

    findings.sort(key=lambda f: (f["doc_class"], f.get("employee_name") or ""))

    if as_json:
        print(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "db": DB_NAME,
            "doc_types": doc_types,
            "include_approved": include_approved,
            "count": len(findings),
            "items": findings,
        }, indent=2, default=str))
        return 0

    # Human-readable report
    print("=" * 88)
    print(f"RTW/DBS extraction triage — db={DB_NAME}")
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print(f"Filtered to: {', '.join(doc_types)}"
          + (" (including admin-approved)" if include_approved else ""))
    print(f"Total flagged: {len(findings)}")
    print("=" * 88)

    if not findings:
        print("No flagged documents. All scanned RTW/DBS extractions look populated.")
        return 0

    by_class: Dict[str, List[Dict[str, Any]]] = {}
    for f in findings:
        by_class.setdefault(f["doc_class"], []).append(f)

    for cls, items in by_class.items():
        print()
        print(f"── {cls.upper()}  ({len(items)} flagged) ──")
        for f in items:
            name = f.get("employee_name") or "<unknown>"
            code = f.get("employee_code") or ""
            print(f"  • {name} {('('+code+')') if code else ''}")
            print(f"      employee_id     : {f.get('employee_id')}")
            print(f"      document_id     : {f.get('document_id')}")
            print(f"      requirement_id  : {f.get('requirement_id')}")
            print(f"      file_name       : {f.get('file_name')}")
            print(f"      extraction      : status={f.get('extraction_status')}"
                  f" review={f.get('extraction_review_status')}")
            for r in f["reasons"]:
                print(f"        - {r}")
    print()
    print("Resolve each via: Employee Profile → open document → "
          "'Review Extracted Data' → 'Retry Extraction' or edit fields and "
          "'Save Edited Values'.")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--doc-types",
        nargs="+",
        choices=["rtw", "dbs"],
        default=["rtw", "dbs"],
        help="Which document classes to scan (default: both).",
    )
    p.add_argument(
        "--include-approved",
        action="store_true",
        help="Also list documents whose extraction was already admin-approved "
             "but still has empty/low-confidence fields.",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON instead of a report.")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(main(args.doc_types, args.include_approved, args.json)))
