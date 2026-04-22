"""Unit tests for governance.training_dedup."""
from __future__ import annotations

import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from governance.training_dedup import (  # noqa: E402
    canonical_training_key,
    dedupe_records_by_canonical_key,
    pick_best_training_record,
    reconcile_active_training_records,
)


# ---------------------------------------------------------------------------
# canonical_training_key
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "record,expected",
    [
        # Canonical id pass-through
        ({"requirement_id": "infection_control", "training_name": "Infection Control"}, "infection_control"),
        # Full CSTF phrasing
        (
            {"requirement_id": "legacy_ipc", "training_name": "Infection Prevention and Control"},
            "infection_control",
        ),
        # Alias id
        ({"requirement_id": "ipc", "training_name": ""}, "infection_control"),
        # CSTF levels phrasing
        (
            {"requirement_id": "random_slug",
             "training_name": "CSTF Infection Prevention and Control Levels 1 and 2"},
            "infection_control",
        ),
        # Ampersand variant
        (
            {"requirement_id": "",
             "training_name": "CSTF Infection Prevention & Control"},
            "infection_control",
        ),
        # Safeguarding adults aliases to safeguarding canonical
        (
            {"requirement_id": "safeguarding_adults", "training_name": "Safeguarding Adults"},
            "safeguarding_adults",
        ),
        # Bare string input
        ("Infection Prevention and Control", "infection_control"),
    ],
)
def test_canonical_training_key_ipc_variants(record, expected):
    assert canonical_training_key(record) == expected


def test_canonical_training_key_unknown_falls_back_to_normalised_name():
    key = canonical_training_key({"training_name": "Bespoke Dementia Awareness (Level 3)"})
    # Non-mandatory training — falls back to normalised form rather than None
    assert key and "_" in key or key.isalnum() or " " not in key


# ---------------------------------------------------------------------------
# pick_best_training_record
# ---------------------------------------------------------------------------

def _rec(**kw):
    defaults = {"id": "r", "record_status": "active", "employee_id": "e1"}
    defaults.update(kw)
    return defaults


def test_pick_best_prefers_verified_over_pending():
    pending = _rec(id="pending", verified=False, completion_date="2026-03-01")
    verified = _rec(id="verified", verified=True, completion_date="2025-12-01")
    best = pick_best_training_record([pending, verified])
    assert best["id"] == "verified"


def test_pick_best_picks_latest_completion_when_both_pending():
    older = _rec(id="older", verified=False, completion_date="2025-01-01")
    newer = _rec(id="newer", verified=False, completion_date="2026-04-01")
    best = pick_best_training_record([older, newer])
    assert best["id"] == "newer"


def test_pick_best_skips_superseded_and_deleted():
    killed = _rec(id="killed", verified=True, completion_date="2026-04-01", record_status="superseded")
    alive = _rec(id="alive", verified=False, completion_date="2025-01-01")
    best = pick_best_training_record([killed, alive])
    assert best["id"] == "alive"


def test_pick_best_rejected_loses_to_pending():
    rejected = _rec(id="rejected", verification_status="rejected", completion_date="2026-04-01")
    pending = _rec(id="pending", verified=False, completion_date="2025-01-01")
    best = pick_best_training_record([rejected, pending])
    assert best["id"] == "pending"


def test_pick_best_returns_none_for_empty():
    assert pick_best_training_record([]) is None


# ---------------------------------------------------------------------------
# dedupe_records_by_canonical_key
# ---------------------------------------------------------------------------

def test_dedupe_collapses_ipc_variants_to_one_row():
    legacy_pending = _rec(
        id="legacy",
        requirement_id="ipc",
        training_name="IPC",
        verified=False,
        completion_date="2025-10-01",
    )
    canonical_verified = _rec(
        id="canonical",
        requirement_id="infection_control",
        training_name="Infection Prevention and Control",
        verified=True,
        completion_date="2026-01-15",
    )
    unrelated = _rec(
        id="fire",
        requirement_id="fire_safety",
        training_name="Fire Safety",
        verified=True,
        completion_date="2026-02-01",
    )
    out = dedupe_records_by_canonical_key([legacy_pending, canonical_verified, unrelated])
    ids = {r["id"] for r in out}
    assert ids == {"canonical", "fire"}


def test_dedupe_no_duplicates_returns_all():
    records = [
        _rec(id="a", requirement_id="fire_safety", verified=True),
        _rec(id="b", requirement_id="basic_life_support", verified=True),
    ]
    out = dedupe_records_by_canonical_key(records)
    assert {r["id"] for r in out} == {"a", "b"}


# ---------------------------------------------------------------------------
# reconcile_active_training_records (async, in-memory fake db)
# ---------------------------------------------------------------------------

class _FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query, projection=None):
        parent = self

        class _Cursor:
            def __init__(self):
                self._filtered = list(parent._matches(query))

            async def to_list(self, limit):
                return list(self._filtered[:limit])

        return _Cursor()

    def _matches(self, query):
        for d in self._docs:
            ok = True
            for k, v in query.items():
                if isinstance(v, dict) and "$nin" in v:
                    if d.get(k) in v["$nin"]:
                        ok = False
                        break
                elif d.get(k) != v:
                    ok = False
                    break
            if ok:
                yield d

    async def update_one(self, filt, update):
        for d in self._docs:
            if all(d.get(k) == v for k, v in filt.items()):
                for k, v in update.get("$set", {}).items():
                    d[k] = v
                return


class _FakeDB:
    def __init__(self, training_records):
        self.training_records = _FakeCollection(training_records)


def test_reconcile_supersedes_legacy_ipc_row():
    asyncio.run(_reconcile_supersedes_legacy_ipc_row())


async def _reconcile_supersedes_legacy_ipc_row():
    legacy = _rec(
        id="legacy",
        requirement_id="ipc",
        training_name="IPC",
        verified=False,
        completion_date="2025-10-01",
    )
    canonical = _rec(
        id="canonical",
        requirement_id="infection_control",
        training_name="Infection Prevention and Control",
        verified=True,
        completion_date="2026-01-15",
    )
    db = _FakeDB([legacy, canonical])

    summary = await reconcile_active_training_records(
        db,
        employee_id="e1",
        canonical_code="infection_control",
        keep_record_id="canonical",
        actor_id="admin-user",
        reason="unit_test",
    )

    assert summary["kept_id"] == "canonical"
    assert summary["superseded_ids"] == ["legacy"]
    assert legacy["record_status"] == "superseded"
    assert legacy["superseded_by_record_id"] == "canonical"
    assert legacy["superseded_reason"] == "unit_test"
    # Kept record untouched on the verification side
    assert canonical["verified"] is True
    assert canonical["record_status"] == "active"


def test_reconcile_is_idempotent():
    asyncio.run(_reconcile_is_idempotent())


async def _reconcile_is_idempotent():
    canonical = _rec(
        id="canonical",
        requirement_id="infection_control",
        training_name="Infection Prevention and Control",
        verified=True,
    )
    db = _FakeDB([canonical])
    first = await reconcile_active_training_records(
        db, "e1", "infection_control", "canonical", "admin", "unit_test"
    )
    second = await reconcile_active_training_records(
        db, "e1", "infection_control", "canonical", "admin", "unit_test"
    )
    assert first["superseded_ids"] == []
    assert second["superseded_ids"] == []
    assert canonical["record_status"] == "active"


def test_reconcile_stamps_canonical_requirement_id_on_legacy_kept_row():
    asyncio.run(_reconcile_stamps_canonical_requirement_id_on_legacy_kept_row())


async def _reconcile_stamps_canonical_requirement_id_on_legacy_kept_row():
    legacy = _rec(
        id="legacy",
        requirement_id="ipc",
        training_name="Infection Prevention and Control",
        verified=True,
        completion_date="2026-01-15",
    )
    db = _FakeDB([legacy])

    summary = await reconcile_active_training_records(
        db,
        "e1",
        canonical_code="infection_control",
        keep_record_id="legacy",
        actor_id="migration",
        reason="migration_test",
    )

    assert summary["kept_id"] == "legacy"
    assert summary["superseded_ids"] == []
    # Legacy requirement_id was back-filled to canonical
    assert legacy["requirement_id"] == "infection_control"
    assert legacy["requirement_id_before_canonicalisation"] == "ipc"
    assert "canonicalised_at" in legacy


def test_reconcile_auto_picks_best_when_no_keep_supplied():
    asyncio.run(_reconcile_auto_picks_best_when_no_keep_supplied())


async def _reconcile_auto_picks_best_when_no_keep_supplied():
    pending = _rec(
        id="pending",
        requirement_id="ipc",
        training_name="IPC",
        verified=False,
        completion_date="2025-10-01",
    )
    verified = _rec(
        id="verified",
        requirement_id="infection_control",
        training_name="Infection Prevention and Control",
        verified=True,
        completion_date="2026-01-15",
    )
    db = _FakeDB([pending, verified])

    summary = await reconcile_active_training_records(
        db,
        "e1",
        "infection_control",
        keep_record_id=None,
        actor_id="auto",
        reason="auto_pick",
    )

    assert summary["kept_id"] == "verified"
    assert summary["superseded_ids"] == ["pending"]
