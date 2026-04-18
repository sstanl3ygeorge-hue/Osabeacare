"""
Employment Gap Detection and Verification Engine

Automatically detects employment gaps from employment history,
creates structured gap records, and gates recruitment approval
until all gaps are explained and verified.

Gap Record Structure:
{
    "gap_id": "gap_1",
    "employee_id": "...",
    "gap_start": "YYYY-MM-DD",
    "gap_end": "YYYY-MM-DD",
    "duration_days": 45,
    "duration_months": 1.5,
    "previous_employment": { "company", "role", "end_date" },
    "next_employment": { "company", "role", "start_date" },
    "explanation": "Travelling abroad...",
    "explanation_provided_at": "...",
    "evidence_document_id": null,
    "status": "pending | explained | needs_more_info | verified | rejected | reopened",
    "verified_by": null,
    "verified_at": null,
    "rejection_reason": null,
    "notes": []
}
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone
from enum import Enum

# =============================================================================
# CONSTANTS
# =============================================================================

# Minimum gap in days to be flagged (30 days = ~1 month)
MIN_GAP_DAYS = 30

# Gap status values
class GapStatus(str, Enum):
    PENDING = "pending"              # Gap detected, no explanation yet
    EXPLAINED = "explained"          # Explanation provided, awaiting verification
    REOPENED = "reopened"            # Previously verified gap reopened by admin
    VERIFIED = "verified"            # Verified by admin
    REJECTED = "rejected"            # Explanation rejected, needs revision
    NEEDS_MORE_INFO = "needs_more_info"  # Admin requested more details


# =============================================================================
# GAP DETECTION
# =============================================================================

def parse_employment_date(date_str) -> Optional[datetime]:
    """Parse employment date string to datetime.

    Handles ISO (YYYY-MM-DD), DD/MM/YYYY, DD-MM-YYYY and 2-digit year
    variants (DD/MM/YY, DD-MM-YY).
    """
    if not date_str:
        return None

    if not isinstance(date_str, str):
        return date_str if date_str.tzinfo else date_str.replace(tzinfo=timezone.utc)

    date_str = date_str.strip()

    # ISO with time component
    if 'T' in date_str:
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            pass

    # DD/MM/YYYY or DD-MM-YYYY (4-digit year)
    import re
    m = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', date_str)
    if m:
        try:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return datetime(year, month, day, tzinfo=timezone.utc)
        except Exception:
            pass

    # DD/MM/YY or DD-MM-YY (2-digit year)
    m = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})$', date_str)
    if m:
        try:
            day, month, short_year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            year = 2000 + short_year if short_year < 80 else 1900 + short_year
            return datetime(year, month, day, tzinfo=timezone.utc)
        except Exception:
            pass

    # Plain ISO YYYY-MM-DD
    try:
        return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
    except Exception:
        return None


def detect_employment_gaps(employment_history: List[Dict]) -> List[Dict]:
    """
    Detect gaps in employment history.
    
    Args:
        employment_history: List of employment records with start_date and end_date
        
    Returns:
        List of detected gaps with structure:
        {
            "gap_id": "gap_1",
            "gap_start": "YYYY-MM-DD",
            "gap_end": "YYYY-MM-DD",
            "duration_days": int,
            "duration_months": float,
            "previous_employment": { "company", "role", "end_date" },
            "next_employment": { "company", "role", "start_date" },
            "status": "pending"
        }
    """
    if not employment_history or len(employment_history) < 1:
        return []
    
    # Filter jobs with valid start dates
    valid_jobs = [j for j in employment_history if j.get("start_date")]
    
    if len(valid_jobs) < 1:
        return []
    
    # Sort by start date ascending (oldest first)
    sorted_jobs = sorted(
        valid_jobs,
        key=lambda x: parse_employment_date(x.get("start_date")) or datetime.min.replace(tzinfo=timezone.utc)
    )
    
    gaps = []
    gap_counter = 0
    
    for i in range(len(sorted_jobs) - 1):
        current_job = sorted_jobs[i]
        next_job = sorted_jobs[i + 1]
        
        # Current job's end date
        current_end = parse_employment_date(current_job.get("end_date"))
        if not current_end:
            # If no end date, assume it's ongoing - skip gap check for this pair
            continue
        
        # Next job's start date
        next_start = parse_employment_date(next_job.get("start_date"))
        if not next_start:
            continue
        
        # Calculate gap
        gap_days = (next_start - current_end).days
        
        if gap_days >= MIN_GAP_DAYS:
            gap_counter += 1
            gap_months = round(gap_days / 30, 1)
            
            gaps.append({
                "gap_id": f"gap_{gap_counter}",
                "gap_start": current_job.get("end_date"),
                "gap_end": next_job.get("start_date"),
                "duration_days": gap_days,
                "duration_months": gap_months,
                "previous_employment": {
                    "company": current_job.get("company") or current_job.get("employer_name", "Unknown"),
                    "role": current_job.get("role") or current_job.get("job_title", ""),
                    "end_date": current_job.get("end_date")
                },
                "next_employment": {
                    "company": next_job.get("company") or next_job.get("employer_name", "Unknown"),
                    "role": next_job.get("role") or next_job.get("job_title", ""),
                    "start_date": next_job.get("start_date")
                },
                "explanation": None,
                "explanation_provided_at": None,
                "evidence_document_id": None,
                "status": GapStatus.PENDING.value,
                "verified_by": None,
                "verified_at": None,
                "rejection_reason": None,
                "notes": []
            })
    
    # Also check for gap from last job to present
    if sorted_jobs:
        most_recent = sorted_jobs[-1]
        recent_end = parse_employment_date(most_recent.get("end_date"))
        
        # If most recent job has an end date (not currently employed)
        if recent_end:
            now = datetime.now(timezone.utc)
            gap_days = (now - recent_end).days
            
            if gap_days >= MIN_GAP_DAYS:
                gap_counter += 1
                gap_months = round(gap_days / 30, 1)
                
                gaps.append({
                    "gap_id": f"gap_{gap_counter}",
                    "gap_start": most_recent.get("end_date"),
                    "gap_end": "present",
                    "duration_days": gap_days,
                    "duration_months": gap_months,
                    "previous_employment": {
                        "company": most_recent.get("company") or most_recent.get("employer_name", "Unknown"),
                        "role": most_recent.get("role") or most_recent.get("job_title", ""),
                        "end_date": most_recent.get("end_date")
                    },
                    "next_employment": {
                        "company": "Present",
                        "role": "Current application",
                        "start_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    },
                    "explanation": None,
                    "explanation_provided_at": None,
                    "evidence_document_id": None,
                    "status": GapStatus.PENDING.value,
                    "verified_by": None,
                    "verified_at": None,
                    "rejection_reason": None,
                    "notes": []
                })
    
    return gaps


# =============================================================================
# GAP VERIFICATION
# =============================================================================

def evaluate_gaps_compliance(gaps: List[Dict]) -> Dict:
    """
    Evaluate if employment gap verification requirement is met.
    
    Returns:
        {
            "has_gaps": bool,
            "total_gaps": int,
            "verified_count": int,
            "pending_count": int,
            "rejected_count": int,
            "needs_info_count": int,
            "all_verified": bool,
            "is_complete": bool,
            "blockers": []
        }
    """
    result = {
        "has_gaps": len(gaps) > 0,
        "total_gaps": len(gaps),
        "verified_count": 0,
        "explained_count": 0,
        "pending_count": 0,
        "rejected_count": 0,
        "needs_info_count": 0,
        "reopened_count": 0,
        "all_verified": True,
        "is_complete": True,
        "blockers": [],
        "gaps": []
    }
    
    if not gaps:
        return result
    
    for gap in gaps:
        status = gap.get("status", GapStatus.PENDING.value)
        gap_info = {
            "gap_id": gap.get("gap_id"),
            "duration_months": gap.get("duration_months"),
            "status": status,
            "has_explanation": bool(gap.get("explanation")),
            "period": f"{gap.get('gap_start')} to {gap.get('gap_end')}"
        }
        result["gaps"].append(gap_info)
        
        if status == GapStatus.VERIFIED.value:
            result["verified_count"] += 1
        elif status == GapStatus.EXPLAINED.value:
            result["explained_count"] += 1
            result["all_verified"] = False
            result["blockers"].append({
                "gap_id": gap.get("gap_id"),
                "reason": f"Gap explanation awaiting verification ({gap.get('duration_months')} months)"
            })
        elif status == GapStatus.PENDING.value:
            result["pending_count"] += 1
            result["all_verified"] = False
            result["blockers"].append({
                "gap_id": gap.get("gap_id"),
                "reason": f"Employment gap requires explanation ({gap.get('duration_months')} months)"
            })
        elif status == GapStatus.REOPENED.value:
            result["reopened_count"] += 1
            result["pending_count"] += 1
            result["all_verified"] = False
            result["blockers"].append({
                "gap_id": gap.get("gap_id"),
                "reason": f"Previously verified gap reopened and requires fresh review ({gap.get('duration_months')} months)"
            })
        elif status == GapStatus.REJECTED.value:
            result["rejected_count"] += 1
            result["all_verified"] = False
            result["blockers"].append({
                "gap_id": gap.get("gap_id"),
                "reason": f"Gap explanation rejected - revision needed ({gap.get('duration_months')} months)"
            })
        elif status == GapStatus.NEEDS_MORE_INFO.value:
            result["needs_info_count"] += 1
            result["all_verified"] = False
            result["blockers"].append({
                "gap_id": gap.get("gap_id"),
                "reason": f"More information requested for gap ({gap.get('duration_months')} months)"
            })
    
    result["is_complete"] = result["all_verified"]
    
    return result


def get_gap_blocker_for_approval(gap_evaluation: Dict) -> Optional[Dict]:
    """
    Get employment gap blocker info for recruitment approval engine.
    
    Returns None if all gaps verified, otherwise returns blocker dict.
    """
    if not gap_evaluation.get("has_gaps"):
        return None
    
    if gap_evaluation.get("is_complete"):
        return None
    
    pending = gap_evaluation.get("pending_count", 0)
    rejected = gap_evaluation.get("rejected_count", 0)
    needs_info = gap_evaluation.get("needs_info_count", 0)
    explained = gap_evaluation.get("explained_count", 0)
    total = gap_evaluation.get("total_gaps", 0)
    verified = gap_evaluation.get("verified_count", 0)
    
    if pending > 0:
        return {
            "requirement_key": "employment_history_verification",
            "label": "Employment History Verification",
            "reason": f"{pending} employment gap(s) require explanation",
            "category": "employment_gap",
            "status": "pending"
        }
    
    if rejected > 0:
        return {
            "requirement_key": "employment_history_verification",
            "label": "Employment History Verification",
            "reason": f"{rejected} gap explanation(s) rejected - revision needed",
            "category": "employment_gap",
            "status": "rejected"
        }
    
    if needs_info > 0:
        return {
            "requirement_key": "employment_history_verification",
            "label": "Employment History Verification",
            "reason": f"More information requested for {needs_info} gap(s)",
            "category": "employment_gap",
            "status": "needs_info"
        }
    
    if explained > 0:
        return {
            "requirement_key": "employment_history_verification",
            "label": "Employment History Verification",
            "reason": f"{explained} gap explanation(s) awaiting admin verification",
            "category": "employment_gap",
            "status": "awaiting_verification"
        }
    
    return {
        "requirement_key": "employment_history_verification",
        "label": "Employment History Verification",
        "reason": f"Employment gaps not fully verified ({verified}/{total})",
        "category": "employment_gap"
    }


# =============================================================================
# GAP RECORD HELPERS
# =============================================================================

def create_gap_record(
    employee_id: str,
    gap_data: Dict,
    created_by: str = "system"
) -> Dict:
    """
    Create a full gap record for database storage.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    return {
        "id": f"{employee_id}_{gap_data['gap_id']}",
        "employee_id": employee_id,
        "gap_id": gap_data["gap_id"],
        "gap_type": gap_data.get("gap_type", "inter_entry"),
        "gap_start": gap_data["gap_start"],
        "gap_end": gap_data["gap_end"],
        "duration_days": gap_data["duration_days"],
        "duration_months": gap_data["duration_months"],
        "previous_employment": gap_data["previous_employment"],
        "next_employment": gap_data["next_employment"],
        "explanation": gap_data.get("explanation"),
        "explanation_provided_at": gap_data.get("explanation_provided_at"),
        "evidence_document_id": gap_data.get("evidence_document_id"),
        "status": gap_data.get("status", GapStatus.PENDING.value),
        "verified_by": gap_data.get("verified_by"),
        "verified_at": gap_data.get("verified_at"),
        "rejection_reason": gap_data.get("rejection_reason"),
        "notes": gap_data.get("notes", []),
        "created_at": now,
        "created_by": created_by,
        "updated_at": now
    }


def detect_employment_gaps_with_coverage(
    employment_history: List[Dict],
    coverage_years: int = 10
) -> List[Dict]:
    """
    Coverage-aware gap detection.  Wraps detect_employment_gaps() and adds
    a pre-history gap when the earliest entry does not reach back to the
    required coverage window start.

    Every returned gap carries a ``gap_type`` field:
      * ``"inter_entry"``  – gap between two consecutive entries
      * ``"trailing"``     – gap from the most recent entry to today
      * ``"pre_history"``  – gap from the coverage window start to the
                             earliest entry
    """
    from datetime import timedelta

    # Baseline inter-entry + trailing gaps
    gaps = detect_employment_gaps(employment_history)

    # Tag existing gaps
    for gap in gaps:
        if gap.get("gap_end") == "present":
            gap["gap_type"] = "trailing"
        else:
            gap["gap_type"] = "inter_entry"

    # --- pre-history coverage gap ---
    now = datetime.now(timezone.utc)
    coverage_start = now - timedelta(days=365 * coverage_years)

    valid_jobs = [j for j in (employment_history or []) if j.get("start_date")]
    if valid_jobs:
        parsed_starts = [d for d in (parse_employment_date(j["start_date"]) for j in valid_jobs) if d is not None]
        earliest_start = min(parsed_starts) if parsed_starts else None
        if earliest_start and (earliest_start - coverage_start).days >= MIN_GAP_DAYS:
            gap_days = (earliest_start - coverage_start).days
            gap_months = round(gap_days / 30, 1)
            # Determine the next gap_id number
            existing_ids = [g.get("gap_id", "") for g in gaps]
            max_num = 0
            for gid in existing_ids:
                try:
                    max_num = max(max_num, int(gid.split("_")[1]))
                except (IndexError, ValueError):
                    pass
            gap_counter = max_num + 1

            earliest_job = min(
                valid_jobs,
                key=lambda j: parse_employment_date(j["start_date"]) or datetime.max.replace(tzinfo=timezone.utc),
            )

            gaps.append({
                "gap_id": f"gap_{gap_counter}",
                "gap_type": "pre_history",
                "gap_start": coverage_start.strftime("%Y-%m-%d"),
                "gap_end": earliest_job.get("start_date"),
                "duration_days": gap_days,
                "duration_months": gap_months,
                "previous_employment": None,
                "next_employment": {
                    "company": earliest_job.get("company") or earliest_job.get("employer_name", "Unknown"),
                    "role": earliest_job.get("role") or earliest_job.get("job_title", ""),
                    "start_date": earliest_job.get("start_date"),
                },
                "explanation": None,
                "explanation_provided_at": None,
                "evidence_document_id": None,
                "status": GapStatus.PENDING.value,
                "verified_by": None,
                "verified_at": None,
                "rejection_reason": None,
                "notes": [],
            })

    return gaps


def compute_coverage_summary(
    employment_history: List[Dict],
    coverage_years: int = 10,
    gap_records: List[Dict] = None,
) -> Dict:
    """
    Pure helper – returns a coverage summary dict without side effects.

    ``meets_10_year_requirement`` is **True** only when there are no
    active unresolved coverage gaps in the required window (NOT a
    percentage threshold).

    If *gap_records* is provided (actual DB records with real statuses),
    those are used for the unresolved-gap check instead of freshly-
    detected gaps which always have status ``pending``.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    coverage_start = now - timedelta(days=365 * coverage_years)
    coverage_end = now
    total_days_required = (coverage_end - coverage_start).days

    valid_jobs = [j for j in (employment_history or []) if j.get("start_date")]

    if not valid_jobs:
        return {
            "coverage_start": coverage_start.strftime("%Y-%m-%d"),
            "coverage_end": coverage_end.strftime("%Y-%m-%d"),
            "total_days_required": total_days_required,
            "total_days_covered": 0,
            "coverage_percent": 0.0,
            "earliest_entry_date": None,
            "latest_entry_date": None,
            "has_current_employment": False,
            "meets_10_year_requirement": False,
        }

    # Sort ascending
    sorted_jobs = sorted(
        valid_jobs,
        key=lambda j: parse_employment_date(j["start_date"]) or datetime.min.replace(tzinfo=timezone.utc),
    )

    earliest_date = parse_employment_date(sorted_jobs[0]["start_date"])
    latest_end = None
    has_current = False

    # Merge overlapping intervals to compute total covered days within window
    intervals = []
    for j in sorted_jobs:
        s = parse_employment_date(j["start_date"])
        if not s:
            continue
        e = parse_employment_date(j.get("end_date"))
        if not e:
            e = now
            has_current = True
        # Clamp to coverage window
        s = max(s, coverage_start)
        e = min(e, coverage_end)
        if s < e:
            intervals.append((s, e))
        # Track latest end for display
        raw_end = parse_employment_date(j.get("end_date")) or now
        if latest_end is None or raw_end > latest_end:
            latest_end = raw_end

    # Merge intervals
    intervals.sort()
    merged = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    total_covered = sum((e - s).days for s, e in merged)
    coverage_pct = round((total_covered / total_days_required) * 100, 1) if total_days_required > 0 else 0.0

    # Determine if requirement is met: check for any unresolved gaps.
    # Use DB gap_records (with real statuses) when provided; otherwise
    # fall back to freshly-detected gaps (which all default to "pending").
    if gap_records is not None:
        all_gaps = gap_records
    else:
        all_gaps = detect_employment_gaps_with_coverage(employment_history, coverage_years)
    unresolved_statuses = {
        GapStatus.PENDING.value,
        GapStatus.EXPLAINED.value,
        GapStatus.REOPENED.value,
        GapStatus.REJECTED.value,
        GapStatus.NEEDS_MORE_INFO.value,
    }
    has_unresolved = any(g.get("status") in unresolved_statuses for g in all_gaps)

    # Cannot meet the requirement if no days were actually covered
    # (e.g. all dates failed to parse, or all entries fall outside the window).
    requirement_met = (not has_unresolved) and (total_covered > 0)

    return {
        "coverage_start": coverage_start.strftime("%Y-%m-%d"),
        "coverage_end": coverage_end.strftime("%Y-%m-%d"),
        "total_days_required": total_days_required,
        "total_days_covered": total_covered,
        "coverage_percent": coverage_pct,
        "earliest_entry_date": earliest_date.strftime("%Y-%m-%d") if earliest_date else None,
        "latest_entry_date": latest_end.strftime("%Y-%m-%d") if latest_end else None,
        "has_current_employment": has_current,
        "meets_10_year_requirement": requirement_met,
    }


def format_gap_summary(gaps: List[Dict]) -> str:
    """Format gaps into a human-readable summary."""
    if not gaps:
        return "No employment gaps detected"
    
    parts = []
    for gap in gaps:
        months = gap.get("duration_months", 0)
        start = gap.get("gap_start", "?")
        end = gap.get("gap_end", "?")
        status = gap.get("status", "pending")
        
        status_emoji = {
            "verified": "✓",
            "explained": "○",
            "pending": "!",
            "reopened": "!",
            "rejected": "✗",
            "needs_more_info": "?"
        }.get(status, "?")
        
        parts.append(f"{status_emoji} {months}mo ({start} - {end})")
    
    return " | ".join(parts)
