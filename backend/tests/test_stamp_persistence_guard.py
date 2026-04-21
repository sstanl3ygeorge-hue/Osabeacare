from backend.stamp_persistence import (
    assert_verified_document_stamp_persisted,
    build_missing_stamp_backfill_query,
)


def test_verified_document_requires_stamp_fields_and_url():
    update_data = {
        "verified": True,
        "status": "approved",
        "review_status": "approved",
        "verification_stamp": "copy_verified",
        "verification_stamp_by_name": "Admin User",
        "verification_stamp_at": "2026-04-21T10:00:00+00:00",
    }

    assert_verified_document_stamp_persisted(
        update_data,
        "https://example.com/stamped.pdf",
        context="test",
    )


def test_verified_document_missing_stamp_url_raises():
    update_data = {
        "verified": True,
        "status": "approved",
        "review_status": "approved",
        "verification_stamp": "copy_verified",
        "verification_stamp_by_name": "Admin User",
        "verification_stamp_at": "2026-04-21T10:00:00+00:00",
    }

    try:
        assert_verified_document_stamp_persisted(update_data, None, context="test")
        assert False, "Expected ValueError for missing stamped_file_url"
    except ValueError as exc:
        assert "missing stamped_file_url" in str(exc)


def test_backfill_query_targets_missing_url_or_missing_stamp():
    query = build_missing_stamp_backfill_query()
    clauses = query["$and"]

    verified_clause = clauses[0]["$or"]
    assert {"verified": True} in verified_clause
    assert {"status": {"$in": ["approved", "verified"]}} in verified_clause or {"status": {"$in": ["verified", "approved"]}} in verified_clause

    missing_clause = clauses[1]["$or"]
    assert {"stamped_file_url": {"$in": [None, ""]}} in missing_clause
    assert {"verification_stamp": {"$in": [None, ""]}} in missing_clause
