"""
Utility functions for data transformation during migration.
"""

from datetime import datetime, timezone, date
from typing import Optional, Any, Dict
from uuid import uuid4
import re
import json


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


def parse_date(value: Any) -> Optional[date]:
    """Parse various date formats to Python date."""
    if not value:
        return None
    
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
            
        # Remove timezone info for date-only parsing
        value = value.split("T")[0]
        
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %B %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    
    return None


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse various timestamp formats to Python datetime with UTC."""
    if not value:
        return None
    
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
            
        # Handle ISO format with Z
        value = value.replace("Z", "+00:00")
        
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
        
        # Try without timezone
        try:
            base = value.split("+")[0].split("-")[0] if "+" in value or value.count("-") > 2 else value
            dt = datetime.fromisoformat(base.rstrip("Z"))
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    
    return None


def sanitize_string(value: Any, max_length: int = None) -> Optional[str]:
    """Sanitize string for database insertion."""
    if value is None:
        return None
    
    result = str(value).strip()
    
    # Remove null bytes and other problematic characters
    result = result.replace("\x00", "")
    result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', result)
    
    if max_length and len(result) > max_length:
        result = result[:max_length]
    
    return result if result else None


def safe_json(value: Any) -> Any:
    """Convert value to JSON-safe format."""
    if value is None:
        return None
    
    if isinstance(value, (str, int, float, bool)):
        return value
    
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    
    return str(value)


def safe_jsonb(value: Any) -> Optional[str]:
    """Convert value to JSONB string for Postgres."""
    if value is None:
        return None
    
    try:
        return json.dumps(safe_json(value))
    except (TypeError, ValueError):
        return None


def calculate_gap_months(start_date: date, end_date: date) -> float:
    """Calculate months between two dates."""
    if not start_date or not end_date:
        return 0.0
    
    days = (end_date - start_date).days
    return round(days / 30.44, 1)


def extract_mongo_id(doc: Dict) -> Optional[str]:
    """Extract the MongoDB document ID."""
    if "id" in doc:
        return str(doc["id"])
    if "_id" in doc:
        return str(doc["_id"])
    return None


def derive_reference_status(employee: dict, ref_num: int) -> str:
    """Derive reference status from multiple boolean fields."""
    prefix = f"reference_{ref_num}_"
    
    if employee.get(f"{prefix}verified"):
        return "verified"
    if employee.get(f"{prefix}rejected"):
        return "rejected"
    if employee.get(f"{prefix}response_received_at"):
        return "response_received"
    if employee.get(f"{prefix}request_viewed_at"):
        return "request_viewed"
    if employee.get(f"{prefix}request_sent_at"):
        return "request_sent"
    if employee.get(f"{prefix}name"):
        return "declared"
    return "not_declared"


def derive_gap_status(gap: dict) -> str:
    """Derive gap status from multiple fields."""
    if gap.get("verified"):
        return "verified"
    if gap.get("rejected"):
        return "rejected"
    
    status = gap.get("status", "").lower()
    status_map = {
        "detected": "detected",
        "more_info_needed": "more_info_needed",
        "explained": "explained",
        "verified": "verified",
        "rejected": "rejected",
        "pending": "detected",
        "awaiting_explanation": "detected",
    }
    return status_map.get(status, "detected")
