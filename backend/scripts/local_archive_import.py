#!/usr/bin/env python3
"""Local-only archive importer for Template Library draft preload.

Default mode is dry-run. The script reads the Phase 1 + 2 manifest, loads files
from a local Windows folder, extracts metadata and placeholders, copies files
through the same Template Library storage path, and creates draft templates only
when `--apply` is explicitly provided.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(BACKEND_ROOT / ".env", override=False)

from routes.document_templates import (  # noqa: E402
    ArchiveImportManifestItem,
    _check_duplicate_template,
    _create_archive_preload_draft,
    _ensure_template_indexes,
    _extract_docx_template_data,
    _extract_pdf_template_data,
    _hash_bytes_sha256,
    _is_temp_office_file,
    _load_import_manifest,
    _manifest_templates_for_phase,
    _normalize_archive_filename,
    _normalize_archive_title,
    _resolve_archive_source_file,
)


DEFAULT_SOURCE_ROOT = Path(r"C:\Users\sstan\Downloads\Osabea Healthcare Solutions Ltd (2)")
SAFE_DB_NAME_TOKENS = ("local", "dev", "test", "staging")
SAFE_HOSTS = {"localhost", "127.0.0.1"}


def _is_supported_template_file(filename: str) -> bool:
    lower_name = (filename or "").lower()
    return lower_name.endswith(".docx") or lower_name.endswith(".pdf")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local-only archive import for Template Library drafts")
    parser.add_argument(
        "--source-root",
        default=str(DEFAULT_SOURCE_ROOT),
        help="Local archive folder root on this Windows machine",
    )
    parser.add_argument(
        "--phase",
        default="phase_1_critical+phase_2_high",
        help="Manifest phase selection (default: phase_1_critical+phase_2_high)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write templates into the configured local/dev database (default: dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Accepted for explicit dry-run invocation; dry-run is already the default mode.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit for testing a smaller subset",
    )
    return parser.parse_args()


def _resolve_mongo_target() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    mongo_url = (
        os.environ.get("MONGO_URL")
        or os.environ.get("MONGODB_URI")
        or os.environ.get("MONGO_URI")
        or os.environ.get("DATABASE_URL")
    )
    db_name = os.environ.get("DB_NAME") or os.environ.get("MONGODB_DB") or os.environ.get("MONGO_DB")
    parsed = urlparse(mongo_url) if mongo_url else None
    host = parsed.hostname if parsed else None
    return mongo_url, db_name, host


def _is_safe_target(db_name: Optional[str], host: Optional[str]) -> bool:
    db_lower = (db_name or "").lower()
    host_lower = (host or "").lower()
    return host_lower in SAFE_HOSTS or any(token in db_lower for token in SAFE_DB_NAME_TOKENS)


async def _connect_db(require_connection: bool):
    mongo_url, db_name, host = _resolve_mongo_target()
    if not mongo_url or not db_name:
        if require_connection:
            raise SystemExit("Missing MongoDB configuration. Set MONGO_URL and DB_NAME for local/dev use.")
        return None, None, {"available": False, "reason": "missing MongoDB configuration"}

    if not _is_safe_target(db_name, host):
        raise SystemExit(
            f"Refusing archive import against non-local/non-dev target host={host or '?'} db={db_name or '?'}"
        )

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2500)
    db = client[db_name]
    try:
        await client.admin.command("ping")
        return client, db, {"available": True, "host": host, "db_name": db_name}
    except PyMongoError as exc:
        client.close()
        if require_connection:
            raise SystemExit(f"Local/dev MongoDB connection failed: {exc}")
        return None, None, {"available": False, "reason": str(exc), "host": host, "db_name": db_name}


async def _probe_manifest_item(source_root: Path, manifest_item: ArchiveImportManifestItem) -> Dict[str, Any]:
    source_path = _resolve_archive_source_file(source_root, manifest_item.folder_path, manifest_item.filename)
    if not source_path:
        raise FileNotFoundError(f"Missing source file: {manifest_item.folder_path} / {manifest_item.filename}")

    file_bytes = source_path.read_bytes()
    if not file_bytes:
        raise ValueError(f"Source file is empty: {manifest_item.filename}")

    actual_hash = _hash_bytes_sha256(file_bytes)
    if manifest_item.file_hash and manifest_item.file_hash != actual_hash:
        raise ValueError(f"Hash mismatch: {manifest_item.filename}")

    lower_name = manifest_item.filename.lower()
    if lower_name.endswith(".docx"):
        extracted_text, extracted_metadata, detected_placeholders = _extract_docx_template_data(file_bytes)
    elif lower_name.endswith(".pdf"):
        extracted_text, extracted_metadata, detected_placeholders = _extract_pdf_template_data(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {manifest_item.filename}")

    return {
        "source_path": str(source_path),
        "clean_title": _normalize_archive_title(manifest_item.filename),
        "normalized_filename": _normalize_archive_filename(manifest_item.filename),
        "placeholder_count": len(detected_placeholders),
        "metadata": extracted_metadata,
        "text_sample": (extracted_text or "")[:240],
    }


async def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root).expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise SystemExit(f"Source root not found: {source_root}")

    manifest = _load_import_manifest()
    templates = _manifest_templates_for_phase(manifest, args.phase)
    if args.limit and args.limit > 0:
        templates = templates[:args.limit]

    client, db, db_status = await _connect_db(require_connection=args.apply)
    duplicate_check_enabled = bool(db is not None)
    if db is not None:
        await _ensure_template_indexes(db)

    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Source root: {source_root}")
    print(f"Phase: {args.phase}")
    print(f"Templates selected: {len(templates)}")
    if db_status:
        if db_status.get("available"):
            print(f"Mongo target: host={db_status.get('host')} db={db_status.get('db_name')}")
        else:
            print(f"Mongo target unavailable for dry-run duplicate checks: {db_status.get('reason')}")

    summary = {
        "imported": 0,
        "skipped": 0,
        "duplicates": 0,
        "errors": 0,
        "temp_files": 0,
    }

    created_ids = []
    user = {"user_id": "local_archive_import"}
    now_iso = datetime.now(timezone.utc).isoformat()

    for raw_item in templates:
        filename = raw_item.get("filename", "")
        if _is_temp_office_file(filename):
            summary["skipped"] += 1
            summary["temp_files"] += 1
            continue
        if not _is_supported_template_file(filename):
            summary["skipped"] += 1
            print(f"[SKIP] {filename}: unsupported non-DOCX/PDF archive file")
            continue

        try:
            manifest_item = ArchiveImportManifestItem(**raw_item)
            duplicate_info = None
            if db is not None:
                duplicate_info = await _check_duplicate_template(
                    db,
                    manifest_item.filename,
                    manifest_item.folder_path,
                    manifest_item.file_hash,
                )
            if duplicate_info:
                summary["skipped"] += 1
                summary["duplicates"] += 1
                continue

            probe = await _probe_manifest_item(source_root, manifest_item)
            if args.apply:
                created = await _create_archive_preload_draft(
                    db,
                    manifest_item=manifest_item,
                    archive_root=source_root,
                    user=user,
                    now_iso=now_iso,
                )
                created_ids.append(created["template_id"])
            summary["imported"] += 1

            print(
                f"[OK] {manifest_item.folder_path} / {manifest_item.filename} -> "
                f"{probe['clean_title']} | {probe['normalized_filename']} | placeholders={probe['placeholder_count']}"
            )
        except Exception as exc:
            summary["errors"] += 1
            print(f"[ERROR] {filename or '<unknown>'}: {exc}")

    if client is not None:
        client.close()

    print("\nSummary")
    print(f"  imported: {summary['imported']}")
    print(f"  skipped: {summary['skipped']}")
    print(f"  duplicates: {summary['duplicates']}")
    print(f"  errors: {summary['errors']}")
    if summary["temp_files"]:
        print(f"  temp_files_skipped: {summary['temp_files']}")
    if not duplicate_check_enabled:
        print("  duplicate_checks: unavailable (local/dev MongoDB not reachable in dry-run)")
    if args.apply:
        print(f"  created_ids: {len(created_ids)}")

    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))