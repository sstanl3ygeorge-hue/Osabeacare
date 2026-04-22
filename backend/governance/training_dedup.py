"""
Canonical training-record dedup + reconciliation.

Purpose
-------
Enforce ONE active canonical training record per (employee_id, canonical
requirement_id). This eliminates the three-surface contradiction that could
appear for the same training (e.g. "Infection Prevention and Control"):

    Training Library     : "Submitted, not reviewed"   (seeing an unverified
                                                         legacy row via
                                                         /training-records)
    Mandatory table      : "Awaiting admin review"     (evaluator using the
                                                         same legacy row)
    Review modal verify  : "Training already verified" (verify_training's
                                                         find_one picked a
                                                         different, verified
                                                         canonical row)

Root cause: more than one row in `training_records` exists with
`record_status == "active"` for the same employee and same underlying
qualification — typically because the legacy row uses a non-canonical
`requirement_id` (e.g. "ipc", "cstf_infection_prevention_and_control") while
the newly-approved row uses the canonical id (e.g. "infection_control").

This module provides:
    * canonical_training_key(record_or_name) — single source of truth for the
      canonical id used in dedup/grouping (alias-aware).
    * pick_best_training_record(records)    — deterministic "which record
      should survive" (verified > rejected; later completion wins; ties
      broken by updated_at/created_at).
    * async find_active_canonical_records(db, employee_id, canonical_code)
      — returns all active records whose canonical key matches.
    * async reconcile_active_training_records(db, employee_id, canonical_code,
                                              keep_record_id, actor_id, reason)
      — supersedes every other active record with that canonical key; writes
      an audit trail entry on each superseded row.

Design principles
-----------------
* Pure helpers are synchronous and importable from tests without a DB.
* Reconciliation is **idempotent** — running it twice with the same keep id
  is a no-op.
* Never auto-verify and never alter the kept record beyond stamping it with
  the canonical `requirement_id` when legacy.
* No side-effects outside `training_records` + audit log.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from services.training_evaluator import (
    TRAINING_ALIASES,
    normalize_training_key,
    normalize_training_text,
    resolve_mandatory_training_code,
)


# ---------------------------------------------------------------------------
# Canonical key resolution
# ---------------------------------------------------------------------------

def _norm_req_id(req_id: Optional[str]) -> str:
    """Normalise a raw requirement_id for alias lookup (underscore form)."""
    if not req_id:
        return ""
    return normalize_training_key(req_id)


def canonical_training_key(record_or_name: Any) -> str:
    """Return the canonical training id for a record OR a bare name string.

    Resolution order (most to least authoritative):
        1. Mandatory-training keyword/alias match on training_name.
        2. Mandatory-training keyword/alias match on requirement_id.
        3. TRAINING_ALIASES lookup on requirement_id.
        4. TRAINING_ALIASES lookup on normalised training_name.
        5. Fallback to the raw normalised requirement_id.
        6. Fallback to the normalised training_name.

    The return value is always a lower-snake string safe to use as an index
    key for grouping. Empty string when nothing identifies the record.
    """
    if isinstance(record_or_name, str):
        name = record_or_name
        req_id = ""
    else:
        record = record_or_name or {}
        name = (
            record.get("training_name")
            or record.get("mapped_training_title")
            or ""
        )
        req_id = (
            record.get("requirement_id")
            or record.get("mapped_training_code")
            or record.get("code")
            or ""
        )

    # 1 & 2 — mandatory keyword map (catches e.g. "Infection Prevention
    # and Control", "IPC", "cstf_infection_prevention_and_control").
    for candidate in (name, req_id):
        if candidate:
            canon = resolve_mandatory_training_code(candidate)
            if canon:
                return canon

    # 3 — direct alias of requirement_id
    normalised_req = _norm_req_id(req_id)
    if normalised_req:
        canon = TRAINING_ALIASES.get(normalised_req)
        if canon:
            return canon

    # 4 — alias of training_name
    normalised_name = _norm_req_id(name)
    if normalised_name:
        canon = TRAINING_ALIASES.get(normalised_name)
        if canon:
            return canon

    # 5/6 — fall through to the most specific normalised form available.
    return normalised_req or normalised_name


# ---------------------------------------------------------------------------
# "Best record wins" — deterministic selection
# ---------------------------------------------------------------------------

def _verification_rank(record: Dict[str, Any]) -> int:
    """Lower is better. Verified beats unverified; rejected is last."""
    if record.get("verification_status") == "rejected":
        return 3
    if record.get("verified") or record.get("verification_status") == "verified":
        return 0
    if record.get("completion_date") or record.get("completed_at"):
        return 1  # completed but awaiting review
    return 2      # no completion data


def _iso_sort_value(value: Optional[str]) -> str:
    """Return a sortable iso string; missing sorts earlier ("")."""
    return value or ""


def pick_best_training_record(
    records: Iterable[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Deterministically pick the record that should survive dedup.

    Precedence:
        1. Verification rank (verified → completed → no-data → rejected).
        2. Latest completion_date (or completed_at).
        3. Latest updated_at.
        4. Latest created_at.
        5. Stable fallback: record id.

    Returns None when the input iterable is empty.
    """
    active = [r for r in records if r.get("record_status") not in ("deleted", "superseded")]
    if not active:
        return None

    def _key(record: Dict[str, Any]) -> Tuple[int, str, str, str, str]:
        return (
            _verification_rank(record),
            # Latest completion first → invert by negating via reversed string
            # order; easiest is to sort descending on these via reverse=True
            # below and keep ascending on the rank. Build key so that a SINGLE
            # sort call works: we sort by rank asc, then flip the remaining
            # timestamps by returning them negated via chr(0x10FFFF) − char.
            _iso_sort_value(record.get("completion_date") or record.get("completed_at")),
            _iso_sort_value(record.get("updated_at")),
            _iso_sort_value(record.get("created_at")),
            record.get("id") or "",
        )

    # Primary sort on verification rank ascending; timestamps descending.
    ranked = sorted(active, key=lambda r: _verification_rank(r))
    best_rank = _verification_rank(ranked[0])
    tied = [r for r in ranked if _verification_rank(r) == best_rank]
    tied.sort(
        key=lambda r: (
            _iso_sort_value(r.get("completion_date") or r.get("completed_at")),
            _iso_sort_value(r.get("updated_at")),
            _iso_sort_value(r.get("created_at")),
            r.get("id") or "",
        ),
        reverse=True,
    )
    return tied[0]


def dedupe_records_by_canonical_key(
    records: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Group active records by canonical key and return the best of each group.

    Deleted/superseded records are dropped. Records with an empty canonical
    key pass through untouched (grouped only on their own id).
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        if record.get("record_status") in ("deleted", "superseded"):
            continue
        key = canonical_training_key(record) or (record.get("id") or "")
        grouped.setdefault(key, []).append(record)

    out: List[Dict[str, Any]] = []
    for group in grouped.values():
        best = pick_best_training_record(group)
        if best is not None:
            out.append(best)
    return out


# ---------------------------------------------------------------------------
# Async reconciliation against MongoDB
# ---------------------------------------------------------------------------

async def find_active_canonical_records(
    db: Any,
    employee_id: str,
    canonical_code: str,
) -> List[Dict[str, Any]]:
    """Return all active training_records that canonicalise to *canonical_code*.

    Matching is done in Python after a broad mongo fetch because the stored
    `requirement_id` may be a legacy/alias form that the mongo query cannot
    cover without replicating the full alias table.
    """
    if not canonical_code:
        return []
    raw = await db.training_records.find(
        {
            "employee_id": employee_id,
            "record_status": {"$nin": ["deleted", "superseded"]},
        },
        {"_id": 0},
    ).to_list(200)
    return [r for r in raw if canonical_training_key(r) == canonical_code]


async def reconcile_active_training_records(
    db: Any,
    employee_id: str,
    canonical_code: str,
    keep_record_id: Optional[str],
    actor_id: Optional[str],
    reason: str = "canonical_dedup",
) -> Dict[str, Any]:
    """Enforce one-active-record per (employee_id, canonical_code).

    Behaviour:
        * Stamp the kept record with canonical `requirement_id` +
          `mapped_training_code` + `mapped_training_title` (when missing or
          non-canonical).
        * Mark every other active record with the same canonical key as
          `record_status == "superseded"`, recording `superseded_by`,
          `superseded_at`, `superseded_reason`, and `superseded_by_record_id`.

    Returns a summary dict `{"kept_id", "superseded_ids", "canonical_code"}`.
    Idempotent: calling it when no duplicates exist is a no-op.
    """
    if not canonical_code:
        return {"kept_id": keep_record_id, "superseded_ids": [], "canonical_code": ""}

    matching = await find_active_canonical_records(db, employee_id, canonical_code)
    if not matching:
        return {"kept_id": keep_record_id, "superseded_ids": [], "canonical_code": canonical_code}

    if keep_record_id is None:
        best = pick_best_training_record(matching)
        keep_record_id = best.get("id") if best else None

    now = datetime.now(timezone.utc).isoformat()
    superseded_ids: List[str] = []

    for record in matching:
        rid = record.get("id")
        if not rid:
            continue
        if rid == keep_record_id:
            # Stamp canonical requirement_id on the kept row if needed.
            updates: Dict[str, Any] = {}
            if record.get("requirement_id") != canonical_code:
                updates["requirement_id"] = canonical_code
                updates["requirement_id_before_canonicalisation"] = record.get("requirement_id")
            if not record.get("mapped_training_code"):
                updates["mapped_training_code"] = canonical_code
            if updates:
                updates["canonicalised_at"] = now
                updates["canonicalised_by"] = actor_id
                updates["updated_at"] = now
                await db.training_records.update_one({"id": rid}, {"$set": updates})
            continue

        superseded_ids.append(rid)
        await db.training_records.update_one(
            {"id": rid},
            {
                "$set": {
                    "record_status": "superseded",
                    "superseded_at": now,
                    "superseded_by": actor_id,
                    "superseded_by_record_id": keep_record_id,
                    "superseded_reason": reason,
                    "updated_at": now,
                }
            },
        )

    return {
        "kept_id": keep_record_id,
        "superseded_ids": superseded_ids,
        "canonical_code": canonical_code,
    }
