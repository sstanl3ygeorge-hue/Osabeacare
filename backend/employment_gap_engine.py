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
    """Parse employment date string to datetime."""
    if not date_str:
        return None
    
    try:
        if isinstance(date_str, str):
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
        return date_str if date_str.tzinfo else date_str.replace(tzinfo=timezone.utc)
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
