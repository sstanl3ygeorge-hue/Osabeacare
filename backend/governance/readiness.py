"""
Worker-governance readiness — pure, testable helper.

Sibling of ``compute_employment_readiness`` in ``routes/worker_dashboard.py``.

Design rules (from PHASE_1_GOVERNANCE_PLAN.md §0):
    - This helper NEVER touches the database.  The route layer fetches the
      per-domain summaries and passes them in.
    - The result NEVER merges into employment_readiness.  It is delivered as a
      separate ``governance_readiness`` block on the worker dashboard payload.
    - Blockers flip the state.  Alerts do not.
    - Provider-profile completeness is deliberately absent — see the explicit
      test ``test_provider_profile_is_excluded_from_worker_governance``.
    - Only *verified* evidence should be summarised by the caller; this helper
      is oblivious to that rule so the verified-only gate stays in the route
      layer where it already exists.

State priority (highest wins):
    high_risk_open_issue  >  overdue_actions  >  attention_required  >  on_track
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Canonical state model — parallel to EMPLOYMENT_READINESS_STATES but
# governance-specific.  Do not rename; tests lock these identifiers.
GOVERNANCE_READINESS_STATES: Tuple[str, ...] = (
    "on_track",
    "attention_required",
    "overdue_actions",
    "high_risk_open_issue",
)

_GOVERNANCE_READINESS_LABELS: Dict[str, str] = {
    "on_track": "On track",
    "attention_required": "Attention required",
    "overdue_actions": "Overdue actions",
    "high_risk_open_issue": "High-risk open issue",
}

# Classification → which state it escalates to.
_BLOCKER_STATE_BY_CLASSIFICATION = {
    "high_risk": "high_risk_open_issue",
    "overdue": "overdue_actions",
}

# Severity order used to pick the dominant state when mixed blockers exist.
_STATE_PRIORITY = {
    "on_track": 0,
    "attention_required": 1,
    "overdue_actions": 2,
    "high_risk_open_issue": 3,
}


def _blocker(
    domain: str,
    blocker_type: str,
    label: str,
    classification: str,
    actor: str,
) -> Dict[str, Any]:
    return {
        "domain": domain,
        "type": blocker_type,
        "label": label,
        "classification": classification,  # "high_risk" | "overdue"
        "actor": actor,                    # "worker" | "admin" | "manager" | "system"
    }


def _alert(
    domain: str,
    alert_type: str,
    label: str,
    actor: str,
) -> Dict[str, Any]:
    return {
        "domain": domain,
        "type": alert_type,
        "label": label,
        "classification": "attention",
        "actor": actor,
    }


def _coerce_summary(raw: Any) -> Dict[str, Any]:
    """Defensive: treat None / missing summaries as empty dicts."""
    return dict(raw) if isinstance(raw, dict) else {}


def compute_worker_governance_readiness(
    *,
    supervisions: Dict[str, Any] | None = None,
    competencies: Dict[str, Any] | None = None,
    spot_checks: Dict[str, Any] | None = None,
    incidents: Dict[str, Any] | None = None,
    care_plan_reviews: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Classify worker governance readiness into one of four canonical states.

    All inputs are small, already-computed per-domain summaries.  This keeps
    the helper pure (no DB, no FastAPI) so every branch can be exercised by a
    unit test.

    Expected summary shapes (all keys optional; unknown keys ignored):

        supervisions = {
            "overdue": bool,               # past escalation threshold
            "due_within_14d": bool,
            "open_worker_actions_overdue": int,
        }
        competencies = {
            "critical_missing": int,       # required-by-role, no record at all
            "critical_expired": int,       # last status competent, review_due_date < now
            "critical_training_required": int,  # last status not_competent
            "noncritical_due_within_30d": int,
        }
        spot_checks = {
            "fail_unclosed_overdue": bool, # outcome=fail past escalation threshold
            "critical_finding_open": bool,
            "followup_overdue": bool,
            "next_periodic_due_within_30d": bool,
            "followup_due_within_7d": bool,
        }
        incidents = {
            "critical_open_past_7d": int,
            "safeguarding_missing_ref_over_24h": int,
            "open_high_severity_involving_worker": int,
        }
        care_plan_reviews = {
            "assigned_overdue": int,
            "assigned_due_within_7d": int,
        }

    Returns:
        {
          "governance_readiness":       <state>,
          "governance_readiness_label": <human label>,
          "governance_blockers":        [ {domain,type,label,classification,actor}, ... ],
          "governance_alerts":          [ {domain,type,label,classification,actor}, ... ],
          "governance_summary":         { counts_per_domain... },
        }
    """
    sup = _coerce_summary(supervisions)
    comp = _coerce_summary(competencies)
    spot = _coerce_summary(spot_checks)
    inc = _coerce_summary(incidents)
    cpr = _coerce_summary(care_plan_reviews)

    blockers: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []

    # ── A. Supervisions ──────────────────────────────────────────────────
    if sup.get("overdue"):
        blockers.append(_blocker(
            "supervisions",
            "supervision_overdue",
            "Supervision is overdue",
            "overdue",
            "manager",
        ))
    if int(sup.get("open_worker_actions_overdue") or 0) > 0:
        blockers.append(_blocker(
            "supervisions",
            "supervision_actions_overdue",
            "Supervision action(s) assigned to you are overdue",
            "overdue",
            "worker",
        ))
    if sup.get("due_within_14d") and not sup.get("overdue"):
        alerts.append(_alert(
            "supervisions",
            "supervision_due_soon",
            "Supervision due in the next 14 days",
            "manager",
        ))

    # ── B. Competencies ──────────────────────────────────────────────────
    if int(comp.get("critical_missing") or 0) > 0:
        blockers.append(_blocker(
            "competencies",
            "critical_competency_missing",
            "Required critical competency has never been recorded",
            "overdue",
            "admin",
        ))
    if int(comp.get("critical_expired") or 0) > 0:
        blockers.append(_blocker(
            "competencies",
            "critical_competency_expired",
            "Critical competency has expired and needs reassessment",
            "overdue",
            "admin",
        ))
    if int(comp.get("critical_training_required") or 0) > 0:
        blockers.append(_blocker(
            "competencies",
            "critical_competency_training_required",
            "Critical competency assessed as not competent — training required",
            "overdue",
            "manager",
        ))
    if int(comp.get("noncritical_due_within_30d") or 0) > 0:
        alerts.append(_alert(
            "competencies",
            "competency_due_soon",
            "Competency reassessment due in the next 30 days",
            "admin",
        ))

    # ── C. Spot checks ───────────────────────────────────────────────────
    if spot.get("fail_unclosed_overdue"):
        blockers.append(_blocker(
            "spot_checks",
            "spot_check_fail_unclosed",
            "Failed spot check is unresolved beyond the escalation window",
            "overdue",
            "manager",
        ))
    if spot.get("critical_finding_open"):
        blockers.append(_blocker(
            "spot_checks",
            "spot_check_critical_finding_open",
            "Critical finding from a spot check is still open",
            "high_risk",
            "manager",
        ))
    if spot.get("followup_overdue"):
        blockers.append(_blocker(
            "spot_checks",
            "spot_check_followup_overdue",
            "Spot-check follow-up is overdue",
            "overdue",
            "manager",
        ))
    if spot.get("next_periodic_due_within_30d"):
        alerts.append(_alert(
            "spot_checks",
            "spot_check_due_soon",
            "Next periodic spot check due in the next 30 days",
            "manager",
        ))
    if spot.get("followup_due_within_7d") and not spot.get("followup_overdue"):
        alerts.append(_alert(
            "spot_checks",
            "spot_check_followup_due_soon",
            "Spot-check follow-up due in the next 7 days",
            "manager",
        ))

    # ── D. Incidents + safeguarding ──────────────────────────────────────
    if int(inc.get("critical_open_past_7d") or 0) > 0:
        blockers.append(_blocker(
            "incidents",
            "critical_incident_open",
            "Critical incident open beyond 7 days",
            "high_risk",
            "admin",
        ))
    if int(inc.get("safeguarding_missing_ref_over_24h") or 0) > 0:
        blockers.append(_blocker(
            "incidents",
            "safeguarding_ref_missing",
            "Safeguarding concern without a local-authority reference > 24h",
            "high_risk",
            "admin",
        ))
    if int(inc.get("open_high_severity_involving_worker") or 0) > 0:
        alerts.append(_alert(
            "incidents",
            "open_high_severity_incident",
            "High-severity incident involving you is open",
            "admin",
        ))

    # ── E. Care-plan reviews ─────────────────────────────────────────────
    if int(cpr.get("assigned_overdue") or 0) > 0:
        blockers.append(_blocker(
            "care_plan_reviews",
            "care_plan_review_overdue",
            "Care-plan review assigned to you is overdue",
            "overdue",
            "worker",
        ))
    if int(cpr.get("assigned_due_within_7d") or 0) > 0:
        alerts.append(_alert(
            "care_plan_reviews",
            "care_plan_review_due_soon",
            "Care-plan review assigned to you is due in the next 7 days",
            "worker",
        ))

    # Resolve state.
    state = "on_track"
    if blockers:
        state = "attention_required"  # placeholder to be escalated below
        for b in blockers:
            escalated = _BLOCKER_STATE_BY_CLASSIFICATION.get(b["classification"])
            if escalated and _STATE_PRIORITY[escalated] > _STATE_PRIORITY[state]:
                state = escalated
    elif alerts:
        state = "attention_required"

    summary = {
        "supervisions": {
            "overdue": bool(sup.get("overdue")),
            "due_within_14d": bool(sup.get("due_within_14d")),
            "open_worker_actions_overdue": int(sup.get("open_worker_actions_overdue") or 0),
        },
        "competencies": {
            "critical_missing": int(comp.get("critical_missing") or 0),
            "critical_expired": int(comp.get("critical_expired") or 0),
            "critical_training_required": int(comp.get("critical_training_required") or 0),
            "noncritical_due_within_30d": int(comp.get("noncritical_due_within_30d") or 0),
        },
        "spot_checks": {
            "fail_unclosed_overdue": bool(spot.get("fail_unclosed_overdue")),
            "critical_finding_open": bool(spot.get("critical_finding_open")),
            "followup_overdue": bool(spot.get("followup_overdue")),
            "next_periodic_due_within_30d": bool(spot.get("next_periodic_due_within_30d")),
            "followup_due_within_7d": bool(spot.get("followup_due_within_7d")),
        },
        "incidents": {
            "critical_open_past_7d": int(inc.get("critical_open_past_7d") or 0),
            "safeguarding_missing_ref_over_24h": int(inc.get("safeguarding_missing_ref_over_24h") or 0),
            "open_high_severity_involving_worker": int(inc.get("open_high_severity_involving_worker") or 0),
        },
        "care_plan_reviews": {
            "assigned_overdue": int(cpr.get("assigned_overdue") or 0),
            "assigned_due_within_7d": int(cpr.get("assigned_due_within_7d") or 0),
        },
    }

    return {
        "governance_readiness": state,
        "governance_readiness_label": _GOVERNANCE_READINESS_LABELS[state],
        "governance_blockers": blockers,
        "governance_alerts": alerts,
        "governance_summary": summary,
    }
