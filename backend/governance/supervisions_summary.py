"""
Supervisions summary helper — pure, DB-free.

Produces the summary dict consumed by
``governance.readiness.compute_worker_governance_readiness(supervisions=...)``.

The route layer fetches the relevant ``supervisions`` rows and their linked
``recurring_compliance`` cadence row, then calls this helper.  Keeping the
helper pure lets every branch be covered by unit tests without Mongo.

Verified-only rule: the caller must pre-filter by
``verification_status == "verified"`` when counting evidence toward readiness.
This helper trusts its input; the gate is enforced at the route layer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

# Window for the "due soon" alert — lines up with the existing cadence engine
# reminder schedule ([14, 7, 0]) so alerts fire on the first reminder.
DUE_SOON_WINDOW_DAYS = 14


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _now(now: Optional[datetime] = None) -> datetime:
    return now if now else datetime.now(timezone.utc)


def compute_supervision_summary(
    supervisions: Iterable[Dict[str, Any]],
    *,
    cadence_next_due_at: Any = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Summarise supervision state for one employee.

    Args:
        supervisions: iterable of supervision docs (already fetched).  Each
            doc should carry at minimum ``status``, ``completed_at``,
            ``next_due_at``.
        cadence_next_due_at: the authoritative next-due date from the linked
            ``recurring_compliance`` row, if any.  When absent, the most
            recent ``next_due_at`` on the supervisions is used as a fallback.
        now: injectable clock for tests.

    Returns dict with:
        due_soon_count          : int
        overdue_count           : int
        completed_count         : int
        cancelled_count         : int
        last_completed_at       : ISO str or None
        next_due_at             : ISO str or None  (cadence-owned when present)
        overdue                 : bool   — ready-to-feed readiness helper
        due_within_14d          : bool   — ready-to-feed readiness helper
        open_worker_actions_overdue : int (always 0 at this step; actions-
            tracking lands with the actions-module; kept for shape stability)
    """
    clock = _now(now)

    completed_count = 0
    cancelled_count = 0
    due_soon_count = 0
    overdue_count = 0
    last_completed_at_dt: Optional[datetime] = None
    fallback_next_due_dt: Optional[datetime] = None

    for row in supervisions:
        status = (row.get("status") or "").strip().lower()
        completed = _parse_iso(row.get("completed_at"))
        next_due = _parse_iso(row.get("next_due_at"))
        scheduled = _parse_iso(row.get("scheduled_at"))

        if status == "completed":
            completed_count += 1
            if completed and (
                last_completed_at_dt is None or completed > last_completed_at_dt
            ):
                last_completed_at_dt = completed
            if next_due and (
                fallback_next_due_dt is None or next_due > fallback_next_due_dt
            ):
                fallback_next_due_dt = next_due
        elif status == "cancelled":
            cancelled_count += 1
        elif status == "scheduled":
            target = scheduled or next_due
            if target:
                delta_days = (target.date() - clock.date()).days
                if delta_days < 0:
                    overdue_count += 1
                elif delta_days <= DUE_SOON_WINDOW_DAYS:
                    due_soon_count += 1
        elif status == "overdue":
            overdue_count += 1

    # Cadence row is the authoritative next_due — fall back only if missing.
    cadence_dt = _parse_iso(cadence_next_due_at) or fallback_next_due_dt
    cadence_overdue = False
    cadence_due_soon = False
    if cadence_dt:
        delta_days = (cadence_dt.date() - clock.date()).days
        if delta_days < 0:
            cadence_overdue = True
        elif delta_days <= DUE_SOON_WINDOW_DAYS:
            cadence_due_soon = True

    overdue = overdue_count > 0 or cadence_overdue
    due_within_14d = (due_soon_count > 0 or cadence_due_soon) and not overdue

    return {
        "due_soon_count": due_soon_count,
        "overdue_count": overdue_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
        "last_completed_at": (
            last_completed_at_dt.isoformat() if last_completed_at_dt else None
        ),
        "next_due_at": cadence_dt.isoformat() if cadence_dt else None,
        "overdue": overdue,
        "due_within_14d": due_within_14d,
        "open_worker_actions_overdue": 0,
    }
