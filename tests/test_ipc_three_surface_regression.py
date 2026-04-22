"""Regression test: the IPC stale-pending vs canonical-verified contradiction.

Before the canonical dedup patch, a single employee could end up with two
active ``training_records`` for the same real training (e.g. a legacy row with
``requirement_id='ipc'`` marked pending, plus a canonical row with
``requirement_id='infection_control'`` marked verified). That caused the three
user-facing surfaces to disagree:

  A. Training Library  (GET /training-records)           → "Submitted, not reviewed"
  B. Mandatory table   (training evaluator lookup)       → "Awaiting admin review"
  C. Review modal      (POST /verify-training)           → "Training already verified"

This test simulates all three surfaces against the same in-memory dataset and
asserts they agree both **before reconciliation** (only surface C needed to
already behave idempotently) and **after reconciliation** (all three agree on
the single verified canonical row).
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from governance.training_dedup import (  # noqa: E402
    dedupe_records_by_canonical_key,
    reconcile_active_training_records,
)
from services.training_evaluator import (  # noqa: E402
    build_training_records_lookup,
    resolve_training_record,
)


# ---------------------------------------------------------------------------
# Minimal async mongo fake (same shape as tests/test_training_dedup.py).
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


# ---------------------------------------------------------------------------
# Fixture builder: the exact bad state the bug produced in production.
# ---------------------------------------------------------------------------

def _seed_contradiction():
    """Two active rows for one employee — legacy pending + canonical verified."""
    legacy_pending = {
        "id": "rec-legacy",
        "employee_id": "EMP-1001",
        "requirement_id": "ipc",                      # legacy alias
        "training_name": "Infection Prevention and Control",
        "verified": False,
        "verification_status": "pending",
        "completion_date": "2025-10-01",
        "record_status": "active",
    }
    canonical_verified = {
        "id": "rec-canonical",
        "employee_id": "EMP-1001",
        "requirement_id": "infection_control",        # canonical id
        "training_name": "Infection Prevention and Control",
        "verified": True,
        "verification_status": "verified",
        "completion_date": "2026-01-15",
        "verified_at": "2026-01-16T09:00:00Z",
        "verified_by": "admin-user",
        "record_status": "active",
    }
    # Distractor row so we know dedup isn't collapsing unrelated training.
    fire = {
        "id": "rec-fire",
        "employee_id": "EMP-1001",
        "requirement_id": "fire_safety",
        "training_name": "Fire Safety",
        "verified": True,
        "verification_status": "verified",
        "completion_date": "2026-02-01",
        "record_status": "active",
    }
    return legacy_pending, canonical_verified, fire


# ---------------------------------------------------------------------------
# Surface simulators — each mirrors what production code does post-patch.
# ---------------------------------------------------------------------------

def _surface_a_training_library(all_records):
    """GET /training-records for an employee with include_superseded=False.

    Production code filters to record_status='active' then runs the same
    canonical dedup call used below.
    """
    active = [r for r in all_records if r.get("record_status", "active") == "active"]
    return dedupe_records_by_canonical_key(active)


def _surface_b_mandatory_evaluator(deduped_records):
    """Mandatory-table status for IPC: mirror the evaluator's resolve path."""
    lookup = build_training_records_lookup(deduped_records)
    return resolve_training_record(
        lookup,
        req_id="infection_control",
        training_name="Infection Prevention and Control",
    )


async def _surface_c_verify_modal(db, *, keep_record_id):
    """POST /verify-training behaviour: reconcile to one active canonical row."""
    return await reconcile_active_training_records(
        db,
        employee_id="EMP-1001",
        canonical_code="infection_control",
        keep_record_id=keep_record_id,
        actor_id="admin-user",
        reason="verify_training_regression",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_pre_reconciliation_library_and_evaluator_already_agree():
    """Even with two active DB rows, the dedup helper collapses them to one.

    This is the protection for surfaces A and B: they ran against the raw
    two-row state in the old bug; now they both go through
    ``dedupe_records_by_canonical_key`` so they can't disagree.
    """
    legacy, canonical, fire = _seed_contradiction()
    all_records = [legacy, canonical, fire]

    # Surface A (Training Library)
    a_rows = _surface_a_training_library(all_records)
    a_ipc = [r for r in a_rows if r["id"] in {"rec-legacy", "rec-canonical"}]
    assert len(a_ipc) == 1, "Library surface must collapse IPC variants to one row"
    assert a_ipc[0]["id"] == "rec-canonical", "Verified row must win over pending"
    assert a_ipc[0]["verified"] is True

    # Surface B (Mandatory evaluator)
    b_row = _surface_b_mandatory_evaluator(a_rows)
    assert b_row is not None, "Evaluator must resolve IPC via canonical lookup"
    assert b_row["id"] == "rec-canonical"
    assert b_row["verified"] is True

    # Distractor untouched
    assert any(r["id"] == "rec-fire" for r in a_rows)


def test_verify_modal_reconciles_and_all_three_surfaces_agree():
    asyncio.run(_verify_modal_reconciles_and_all_three_surfaces_agree())


async def _verify_modal_reconciles_and_all_three_surfaces_agree():
    legacy, canonical, fire = _seed_contradiction()
    all_records = [legacy, canonical, fire]
    db = _FakeDB(all_records)

    # Surface C: verify-training endpoint reconciles duplicates.
    summary = await _surface_c_verify_modal(db, keep_record_id="rec-canonical")
    assert summary["kept_id"] == "rec-canonical"
    assert summary["superseded_ids"] == ["rec-legacy"]

    # DB state: legacy is now superseded, canonical still active.
    assert legacy["record_status"] == "superseded"
    assert legacy["superseded_by_record_id"] == "rec-canonical"
    assert canonical["record_status"] == "active"
    assert canonical["verified"] is True

    # Surface A after reconciliation: only one IPC row remains.
    a_rows = _surface_a_training_library(all_records)
    ipc_rows = [
        r for r in a_rows
        if r.get("requirement_id") == "infection_control"
        or r.get("id") in {"rec-legacy", "rec-canonical"}
    ]
    assert len(ipc_rows) == 1
    assert ipc_rows[0]["id"] == "rec-canonical"
    assert ipc_rows[0]["verified"] is True

    # Surface B after reconciliation: evaluator finds the same verified row.
    b_row = _surface_b_mandatory_evaluator(a_rows)
    assert b_row is not None
    assert b_row["id"] == "rec-canonical"
    assert b_row["verified"] is True

    # Surface C idempotency: calling verify again must not re-supersede.
    second = await _surface_c_verify_modal(db, keep_record_id="rec-canonical")
    assert second["superseded_ids"] == []
    assert legacy["record_status"] == "superseded"  # unchanged


def test_verify_modal_auto_picks_verified_when_no_keep_supplied():
    asyncio.run(_verify_modal_auto_picks_verified_when_no_keep_supplied())


async def _verify_modal_auto_picks_verified_when_no_keep_supplied():
    """If the verify endpoint is invoked without an explicit keep id (e.g. the
    already-verified idempotent branch), the reconciler must still pick the
    verified canonical row and supersede the stale legacy pending row."""
    legacy, canonical, _fire = _seed_contradiction()
    db = _FakeDB([legacy, canonical])

    summary = await reconcile_active_training_records(
        db,
        employee_id="EMP-1001",
        canonical_code="infection_control",
        keep_record_id=None,
        actor_id="admin-user",
        reason="idempotent_already_verified",
    )

    assert summary["kept_id"] == "rec-canonical"
    assert summary["superseded_ids"] == ["rec-legacy"]
    assert legacy["record_status"] == "superseded"
    assert canonical["verified"] is True


def test_legacy_only_state_is_canonicalised_without_data_loss():
    """If only the legacy row exists (no canonical duplicate yet), the
    migration path keeps that row active but stamps it with the canonical
    ``requirement_id`` so all three surfaces can find it going forward."""
    asyncio.run(_legacy_only_state_is_canonicalised_without_data_loss())


async def _legacy_only_state_is_canonicalised_without_data_loss():
    legacy_only = {
        "id": "rec-legacy-only",
        "employee_id": "EMP-1001",
        "requirement_id": "ipc",
        "training_name": "Infection Prevention and Control",
        "verified": True,
        "verification_status": "verified",
        "completion_date": "2026-01-15",
        "record_status": "active",
    }
    db = _FakeDB([legacy_only])

    summary = await reconcile_active_training_records(
        db,
        employee_id="EMP-1001",
        canonical_code="infection_control",
        keep_record_id="rec-legacy-only",
        actor_id="migration",
        reason="three_surface_regression",
    )
    assert summary["superseded_ids"] == []
    assert legacy_only["requirement_id"] == "infection_control"
    assert legacy_only["requirement_id_before_canonicalisation"] == "ipc"

    # Evaluator can now resolve via canonical id.
    a_rows = _surface_a_training_library([legacy_only])
    b_row = _surface_b_mandatory_evaluator(a_rows)
    assert b_row is not None
    assert b_row["id"] == "rec-legacy-only"
    assert b_row["verified"] is True
