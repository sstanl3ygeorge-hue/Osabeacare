"""
Shared guardrails for verified document stamp persistence.

These helpers are intentionally small and pure so they can be reused by
legacy verification routes, newer verify-and-stamp flows, and the stamp
backfill migration without pulling in FastAPI or database dependencies.
"""

from __future__ import annotations

from typing import Any


VERIFIED_STATUSES = frozenset({"approved", "verified"})


def document_requires_stamp_persistence(document: dict[str, Any]) -> bool:
    """Return True when a document state implies it must carry stamp data."""
    return bool(
        document.get("verified") is True
        or document.get("status") in VERIFIED_STATUSES
        or document.get("review_status") in VERIFIED_STATUSES
    )


def has_persisted_stamp_metadata(document: dict[str, Any]) -> bool:
    """Return True when the document has the flat metadata needed for audit/UI."""
    stamp = document.get("verification_stamp")
    if stamp in (None, "", False):
        return False
    return bool(
        document.get("verification_stamp_at")
        and document.get("verification_stamp_by_name")
    )


def assert_stamp_integrity(
    document: dict[str, Any],
    stamped_file_url: str | None,
    *,
    context: str,
) -> None:
    """
    Raise ValueError when a verified/approved document is missing stamp state.

    Routes should call this before writing a verified/approved update so we
    fail closed instead of silently persisting an audit-unsafe document state.
    """
    if not document_requires_stamp_persistence(document):
        return

    if not has_persisted_stamp_metadata(document):
        raise ValueError(
            f"{context}: verified document is missing verification stamp metadata"
        )

    if not stamped_file_url:
        raise ValueError(
            f"{context}: verified document is missing stamped_file_url"
        )


def assert_verified_document_stamp_persisted(
    document: dict[str, Any],
    stamped_file_url: str | None,
    *,
    context: str,
) -> None:
    """Backward-compatible alias for existing callers."""
    assert_stamp_integrity(document, stamped_file_url, context=context)


# Requirement-id values that are pure status/check rows and have no file to stamp.
_NON_FILE_REQUIREMENT_IDS = frozenset({
    "dbs_status_check",
    "dbs_update_service_check",
})


def _missing_field_clause(field: str) -> dict[str, Any]:
    """Return an $or clause that matches null/empty/missing for *field*.

    MongoDB does not allow nesting query operators (e.g. {$exists: false})
    inside $in / $nin, so we always use explicit $or branches.
    """
    return {
        "$or": [
            {field: {"$exists": False}},
            {field: None},
            {field: ""},
        ]
    }


def build_missing_stamp_backfill_query() -> dict[str, Any]:
    """Mongo query for verified/approved docs that still need stamp backfill.

    Excludes:
    - documents with no file_url (nothing to stamp)
    - status/check rows that are never file documents
    """
    return {
        "$and": [
            # Must be in a verified/approved state
            {
                "$or": [
                    {"verified": True},
                    {"status": {"$in": list(VERIFIED_STATUSES)}},
                    {"review_status": {"$in": list(VERIFIED_STATUSES)}},
                ]
            },
            # Must have a non-empty file_url (resolver handles http URLs, Supabase
            # storage paths like documents/<id>/file.pdf, and legacy paths)
            {"file_url": {"$exists": True}},
            {"file_url": {"$nin": [None, ""]}},
            # Exclude non-file requirement rows
            {"requirement_id": {"$nin": list(_NON_FILE_REQUIREMENT_IDS)}},
            # Missing stamped_file_url OR missing verification_stamp
            {
                "$or": [
                    # stamped_file_url absent/null/empty
                    {"stamped_file_url": {"$exists": False}},
                    {"stamped_file_url": None},
                    {"stamped_file_url": ""},
                    # verification_stamp absent/null/empty
                    {"verification_stamp": {"$exists": False}},
                    {"verification_stamp": None},
                    {"verification_stamp": ""},
                    # flat metadata fields missing
                    {"verification_stamp_at": {"$exists": False}},
                    {"verification_stamp_at": None},
                    {"verification_stamp_by_name": {"$exists": False}},
                    {"verification_stamp_by_name": None},
                    {"verification_stamp_by_name": ""},
                ]
            },
        ]
    }
