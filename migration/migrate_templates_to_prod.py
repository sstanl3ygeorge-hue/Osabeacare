#!/usr/bin/env python3
"""Migrate exported local draft templates into production MongoDB.

This script is intentionally conservative:
- dry-run and apply modes are explicit
- inserts only; no updates and no overwrites
- forces status='draft' and import_status='pending_review'
- adds migration_tag and migrated_at
- detects conflicts before writing
- writes a conflicts file for review
- blocks local Windows file paths from reaching production

Expected input is an exported bundle of the local template records and linked
version records, typically created from the cleaned local review set.

Example dry-run:
    python migration/migrate_templates_to_prod.py \
        --dry-run \
        --templates .\migration\bundle\templates_94.json \
        --versions .\migration\bundle\versions_94.json \
        --prod-uri %PROD_MONGO_URL% \
        --prod-db %PROD_DB%

Example apply:
    python migration/migrate_templates_to_prod.py \
        --apply \
        --templates .\migration\bundle\templates_94.json \
        --versions .\migration\bundle\versions_94.json \
        --prod-uri %PROD_MONGO_URL% \
        --prod-db %PROD_DB%
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import BulkWriteError, DuplicateKeyError, PyMongoError


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFLICTS_FILE = SCRIPT_DIR / "template_migration_conflicts.json"

WINDOWS_PATH_RE = re.compile(r"(?i)(?:^[A-Z]:\\|[A-Z]:/|\\\\|/Users/|/home/|/mnt/)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate local draft templates to production MongoDB")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate and report only; do not write to production")
    mode.add_argument("--apply", action="store_true", help="Write migrated templates and versions to production")
    parser.add_argument("--templates", required=True, help="Path to exported templates JSON bundle")
    parser.add_argument("--versions", required=True, help="Path to exported versions JSON bundle")
    parser.add_argument("--prod-uri", default=os.environ.get("PROD_MONGO_URL"), help="Production MongoDB URI")
    parser.add_argument("--prod-db", default=os.environ.get("PROD_DB"), help="Production database name")
    parser.add_argument("--migration-tag", default=None, help="Optional migration tag; defaults to a timestamped tag")
    parser.add_argument("--conflicts-file", default=str(DEFAULT_CONFLICTS_FILE), help="Output JSON file for conflicts and blockers")
    return parser.parse_args()


def load_json_bundle(path_text: str) -> List[Dict[str, Any]]:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"Bundle file not found: {path}")

    raw_text = path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return []

    try:
        parsed = json_util.loads(raw_text)
    except Exception:
        parsed = [json_util.loads(line) for line in raw_text.splitlines() if line.strip()]

    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def looks_like_local_windows_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value.strip():
        return False
    return bool(WINDOWS_PATH_RE.search(value.strip()))


def collect_local_path_hits(value: Any, path: str = "") -> List[Dict[str, str]]:
    hits: List[Dict[str, str]] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}" if path else str(key)
            hits.extend(collect_local_path_hits(nested, nested_path))
        return hits
    if isinstance(value, list):
        for index, nested in enumerate(value):
            nested_path = f"{path}[{index}]" if path else f"[{index}]"
            hits.extend(collect_local_path_hits(nested, nested_path))
        return hits
    if looks_like_local_windows_path(value):
        hits.append({"field": path or "<root>", "value": str(value)})
    return hits


def build_source_index(templates: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by_id: Dict[str, Dict[str, Any]] = {}
    by_doc_code: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_title_filename: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    by_original_filename: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for doc in templates:
        doc_id = normalize_text(doc.get("id"))
        if doc_id:
            by_id[doc_id] = doc
        doc_code = normalize_text(doc.get("doc_code"))
        if doc_code:
            by_doc_code[doc_code].append(doc)
        title_key = normalize_text(doc.get("title"))
        filename_key = normalize_text(doc.get("original_filename"))
        if title_key or filename_key:
            by_title_filename[(title_key, filename_key)].append(doc)
        if filename_key:
            by_original_filename[filename_key].append(doc)

    return {
        "by_id": by_id,
        "by_doc_code": by_doc_code,
        "by_title_filename": by_title_filename,
        "by_original_filename": by_original_filename,
    }


def load_production_index(prod_db) -> Dict[str, Any]:
    template_fields = {
        "_id": 1,
        "id": 1,
        "title": 1,
        "original_filename": 1,
        "doc_code": 1,
        "source_provider": 1,
    }
    version_fields = {
        "_id": 1,
        "id": 1,
        "template_id": 1,
        "original_filename": 1,
    }

    existing_template_ids = set()
    existing_doc_codes: Dict[str, Dict[str, Any]] = {}
    existing_title_filename: Dict[Tuple[str, str], Dict[str, Any]] = {}
    existing_original_filenames: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for doc in prod_db.document_templates.find({}, template_fields):
        existing_template_ids.add(normalize_text(doc.get("id")))
        doc_code = normalize_text(doc.get("doc_code"))
        if doc_code and doc_code not in existing_doc_codes:
            existing_doc_codes[doc_code] = doc
        title_key = normalize_text(doc.get("title"))
        filename_key = normalize_text(doc.get("original_filename"))
        if title_key or filename_key:
            existing_title_filename[(title_key, filename_key)] = doc
        if filename_key:
            existing_original_filenames[filename_key].append(doc)

    existing_version_ids = set()
    existing_version_template_ids = set()
    for doc in prod_db.document_template_versions.find({}, version_fields):
        version_id = normalize_text(doc.get("id"))
        template_id = normalize_text(doc.get("template_id"))
        if version_id:
            existing_version_ids.add(version_id)
        if template_id:
            existing_version_template_ids.add(template_id)

    return {
        "existing_template_ids": existing_template_ids,
        "existing_doc_codes": existing_doc_codes,
        "existing_title_filename": existing_title_filename,
        "existing_original_filenames": existing_original_filenames,
        "existing_version_ids": existing_version_ids,
        "existing_version_template_ids": existing_version_template_ids,
    }


def resolve_prod_target(args: argparse.Namespace) -> Tuple[str, str]:
    if not args.prod_uri or not args.prod_db:
        raise SystemExit(
            "Production MongoDB settings are required. Set PROD_MONGO_URL and PROD_DB, or pass --prod-uri and --prod-db."
        )
    return args.prod_uri, args.prod_db


def make_conflict_entry(
    conflict_type: str,
    template_doc: Dict[str, Any],
    version_doc: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry = {
        "conflict_type": conflict_type,
        "template_id": template_doc.get("id"),
        "version_id": (version_doc or {}).get("id"),
        "title": template_doc.get("title"),
        "original_filename": template_doc.get("original_filename"),
        "doc_code": template_doc.get("doc_code"),
    }
    if details:
        entry["details"] = details
    return entry


def classify_template_conflicts(
    template_doc: Dict[str, Any],
    prod_index: Dict[str, Any],
) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    template_id = normalize_text(template_doc.get("id"))
    doc_code = normalize_text(template_doc.get("doc_code"))
    title_key = normalize_text(template_doc.get("title"))
    filename_key = normalize_text(template_doc.get("original_filename"))

    if template_id and template_id in prod_index["existing_template_ids"]:
        conflicts.append(make_conflict_entry("template_id_exists", template_doc))

    if doc_code and doc_code in prod_index["existing_doc_codes"]:
        conflicts.append(
            make_conflict_entry(
                "doc_code_exists",
                template_doc,
                details={"existing_template_id": prod_index["existing_doc_codes"][doc_code].get("id")},
            )
        )

    if title_key or filename_key:
        matched = prod_index["existing_title_filename"].get((title_key, filename_key))
        if matched:
            conflicts.append(
                make_conflict_entry(
                    "title_original_filename_exists",
                    template_doc,
                    details={"existing_template_id": matched.get("id")},
                )
            )

    if filename_key and filename_key in prod_index["existing_original_filenames"]:
        conflicts.append(
            make_conflict_entry(
                "original_filename_exists",
                template_doc,
                details={
                    "existing_template_ids": [doc.get("id") for doc in prod_index["existing_original_filenames"][filename_key]],
                },
            )
        )

    return conflicts


def classify_version_conflicts(
    template_doc: Dict[str, Any],
    version_doc: Dict[str, Any],
    prod_index: Dict[str, Any],
) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    version_id = normalize_text(version_doc.get("id"))
    template_id = normalize_text(version_doc.get("template_id"))

    if version_id and version_id in prod_index["existing_version_ids"]:
        conflicts.append(make_conflict_entry("version_id_exists", template_doc, version_doc))

    if template_id and template_id in prod_index["existing_version_template_ids"]:
        conflicts.append(make_conflict_entry("version_template_id_exists", template_doc, version_doc))

    return conflicts


def sanitize_for_production(doc: Dict[str, Any], *, migration_tag: str, now_iso: str, collection: str) -> Dict[str, Any]:
    cleaned = copy.deepcopy(doc)
    cleaned.pop("_id", None)
    cleaned["migration_tag"] = migration_tag
    cleaned["migrated_at"] = now_iso

    if collection == "template":
        cleaned["status"] = "draft"
        cleaned["import_status"] = "pending_review"
        cleaned.setdefault("published_at", None)
        cleaned.setdefault("published_by", None)
    elif collection == "version":
        cleaned["status"] = "draft"
        cleaned.setdefault("published_at", None)
        cleaned.setdefault("published_by", None)

    return cleaned


def build_migration_plan(
    templates: Sequence[Dict[str, Any]],
    versions: Sequence[Dict[str, Any]],
    prod_index: Dict[str, Any],
    migration_tag: str,
    now_iso: str,
) -> Dict[str, Any]:
    versions_by_template_id: Dict[str, Dict[str, Any]] = {}
    for version_doc in versions:
        template_id = normalize_text(version_doc.get("template_id"))
        if template_id:
            versions_by_template_id[template_id] = version_doc

    report_rows: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    template_conflict_counts: Counter[str] = Counter()
    local_path_blockers = 0
    stripped_local_path_count = 0
    safe_records: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

    for template_doc in templates:
        template_id = normalize_text(template_doc.get("id"))
        version_doc = versions_by_template_id.get(template_id)
        row = {
            "template_id": template_doc.get("id"),
            "version_id": (version_doc or {}).get("id"),
            "title": template_doc.get("title"),
            "original_filename": template_doc.get("original_filename"),
            "doc_code": template_doc.get("doc_code"),
            "status": template_doc.get("status"),
            "import_status": template_doc.get("import_status"),
            "conflicts": [],
            "local_path_issues": [],
        }

        if not version_doc:
            conflict = make_conflict_entry("missing_version", template_doc, None, details={"reason": "No linked version record in export bundle"})
            row["conflicts"].append(conflict)
            conflicts.append(conflict)
            template_conflict_counts[template_doc.get("id") or "<missing>"] += 1
            report_rows.append(row)
            continue

        template_conflicts = classify_template_conflicts(template_doc, prod_index)
        version_conflicts = classify_version_conflicts(template_doc, version_doc, prod_index)
        all_conflicts = template_conflicts + version_conflicts

        local_path_hits = []
        for collection_name, source_doc in (("template", template_doc), ("version", version_doc)):
            hits = collect_local_path_hits(source_doc)
            for hit in hits:
                field_name = hit["field"]
                if field_name.endswith("local_path") or field_name == "local_path":
                    stripped_local_path_count += 1
                    row["local_path_issues"].append(
                        {
                            "type": "local_path_stripped",
                            "collection": collection_name,
                            "field": field_name,
                            "value": hit["value"],
                        }
                    )
                else:
                    local_path_hits.append(
                        {
                            "type": "local_windows_path_blocker",
                            "collection": collection_name,
                            "field": field_name,
                            "value": hit["value"],
                        }
                    )

        if local_path_hits:
            local_path_blockers += 1
            blocker_conflict = make_conflict_entry(
                "local_windows_path_blocker",
                template_doc,
                version_doc,
                details={"hits": local_path_hits},
            )
            all_conflicts.append(blocker_conflict)

        if all_conflicts:
            for conflict in all_conflicts:
                conflicts.append(conflict)
                row["conflicts"].append(conflict)
            template_conflict_counts[template_doc.get("id") or "<missing>"] += 1
        else:
            safe_template = sanitize_for_production(template_doc, migration_tag=migration_tag, now_iso=now_iso, collection="template")
            safe_version = sanitize_for_production(version_doc, migration_tag=migration_tag, now_iso=now_iso, collection="version")
            if "local_path" in safe_template and looks_like_local_windows_path(safe_template.get("local_path")):
                safe_template["local_path"] = None
                stripped_local_path_count += 1
            if "local_path" in safe_version and looks_like_local_windows_path(safe_version.get("local_path")):
                safe_version["local_path"] = None
                stripped_local_path_count += 1
            safe_records.append((safe_template, safe_version))

        report_rows.append(row)

    summary = {
        "total_templates": len(templates),
        "total_versions": len(versions),
        "safe_records": len(safe_records),
        "conflict_count": len(conflicts),
        "template_conflict_count": sum(1 for count in template_conflict_counts.values() if count > 0),
        "local_path_blockers": local_path_blockers,
        "local_path_values_stripped": stripped_local_path_count,
    }

    return {
        "summary": summary,
        "conflicts": conflicts,
        "report_rows": report_rows,
        "safe_records": safe_records,
    }


def write_conflicts_file(path_text: str, payload: Dict[str, Any]) -> Path:
    path = Path(path_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    prod_uri, prod_db_name = resolve_prod_target(args)

    if not args.dry_run and not args.apply:
        raise SystemExit("Choose either --dry-run or --apply")

    templates = load_json_bundle(args.templates)
    versions = load_json_bundle(args.versions)

    if args.dry_run and (not prod_uri or not prod_db_name):
        raise SystemExit("Dry-run requires production env vars or --prod-uri and --prod-db")
    if args.apply and (not prod_uri or not prod_db_name):
        raise SystemExit("Apply requires production env vars or --prod-uri and --prod-db")

    migration_tag = args.migration_tag or f"template_migration_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    now_iso = datetime.now(timezone.utc).isoformat()

    prod_client = MongoClient(prod_uri, serverSelectionTimeoutMS=4000)
    try:
        prod_client.admin.command("ping")
    except PyMongoError as exc:
        prod_client.close()
        raise SystemExit(f"Production MongoDB connection failed: {exc}")

    prod_db = prod_client[prod_db_name]
    prod_index = load_production_index(prod_db)
    plan = build_migration_plan(templates, versions, prod_index, migration_tag, now_iso)

    conflict_payload = {
        "migration_tag": migration_tag,
        "generated_at": now_iso,
        "mode": "dry-run" if args.dry_run else "apply",
        "summary": plan["summary"],
        "conflicts": plan["conflicts"],
        "report_rows": plan["report_rows"],
    }
    conflicts_path = write_conflicts_file(args.conflicts_file, conflict_payload)

    print(f"mode={'dry-run' if args.dry_run else 'apply'}")
    print(f"production_db={prod_db_name}")
    print(f"migration_tag={migration_tag}")
    print(f"templates_input={len(templates)}")
    print(f"versions_input={len(versions)}")
    print(f"safe_records={plan['summary']['safe_records']}")
    print(f"conflicts={plan['summary']['conflict_count']}")
    print(f"local_path_blockers={plan['summary']['local_path_blockers']}")
    print(f"local_path_values_stripped={plan['summary']['local_path_values_stripped']}")
    print(f"conflicts_file={conflicts_path}")

    if args.dry_run:
        prod_client.close()
        return 0

    inserted_templates = 0
    inserted_versions = 0
    skipped_apply_conflicts = 0
    write_errors: List[Dict[str, Any]] = []

    try:
        for template_doc, version_doc in plan["safe_records"]:
            try:
                prod_db.document_templates.insert_one(template_doc)
                inserted_templates += 1
            except (DuplicateKeyError, BulkWriteError, PyMongoError) as exc:
                skipped_apply_conflicts += 1
                write_errors.append(
                    make_conflict_entry(
                        "template_insert_failed",
                        template_doc,
                        version_doc,
                        details={"error": str(exc)},
                    )
                )
                continue

            try:
                prod_db.document_template_versions.insert_one(version_doc)
                inserted_versions += 1
            except (DuplicateKeyError, BulkWriteError, PyMongoError) as exc:
                skipped_apply_conflicts += 1
                write_errors.append(
                    make_conflict_entry(
                        "version_insert_failed",
                        template_doc,
                        version_doc,
                        details={"error": str(exc)},
                    )
                )
                # Roll back the template insert for this pair to keep the database consistent.
                prod_db.document_templates.delete_one({"id": template_doc.get("id")})
                inserted_templates -= 1

        final_counts = {
            "batch_templates": prod_db.document_templates.count_documents({"migration_tag": migration_tag}),
            "batch_versions": prod_db.document_template_versions.count_documents({"migration_tag": migration_tag}),
            "batch_pending_review": prod_db.document_templates.count_documents({"migration_tag": migration_tag, "import_status": "pending_review"}),
            "batch_published": prod_db.document_templates.count_documents({"migration_tag": migration_tag, "status": "published"}),
        }

        conflict_payload["apply_summary"] = {
            "inserted_templates": inserted_templates,
            "inserted_versions": inserted_versions,
            "skipped_apply_conflicts": skipped_apply_conflicts,
            "write_errors": write_errors,
            "final_counts": final_counts,
        }
        write_conflicts_file(args.conflicts_file, conflict_payload)

        print(f"inserted_templates={inserted_templates}")
        print(f"inserted_versions={inserted_versions}")
        print(f"skipped_apply_conflicts={skipped_apply_conflicts}")
        print(f"batch_templates={final_counts['batch_templates']}")
        print(f"batch_versions={final_counts['batch_versions']}")
        print(f"batch_pending_review={final_counts['batch_pending_review']}")
        print(f"batch_published={final_counts['batch_published']}")
    finally:
        prod_client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
