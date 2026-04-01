"""
Proof of Address Freshness Engine

Implements NHS-level PoA policy enforcement:
- Minimum 2 valid documents
- Each document must be dated within 12 months
- Documents without clear dates require manual review

Freshness States:
- VALID: Document dated within 12 months
- EXPIRED: Document dated older than 12 months
- DATE_UNCLEAR: Document date could not be extracted - requires manual review
- MANUAL_OVERRIDE: Admin manually approved despite unclear/expired date
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from enum import Enum

# =============================================================================
# CONSTANTS
# =============================================================================

POA_FRESHNESS_MONTHS = 12  # Documents must be within 12 months
POA_FRESHNESS_DAYS = 365   # 12 months in days
POA_MINIMUM_DOCUMENTS = 2  # NHS standard: 2 separate documents required


class PoAFreshnessStatus(str, Enum):
    """Freshness status for a single PoA document."""
    VALID = "valid"              # Within 12 months
    EXPIRED = "expired"          # Older than 12 months  
    DATE_UNCLEAR = "date_unclear"  # Could not extract date
    MANUAL_OVERRIDE = "manual_override"  # Admin approved despite issues


class PoAOverallStatus(str, Enum):
    """Overall PoA compliance status."""
    COMPLETE = "complete"        # 2+ valid documents
    PARTIAL = "partial"          # Some valid but less than 2
    REVIEW_NEEDED = "review_needed"  # Has documents needing manual review
    INCOMPLETE = "incomplete"    # No valid documents


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_document_freshness(document_date: Optional[str], manual_override: bool = False) -> Dict:
    """
    Calculate freshness status for a single PoA document.
    
    Args:
        document_date: ISO date string (YYYY-MM-DD or full ISO)
        manual_override: Whether admin manually approved this document
        
    Returns:
        {
            "status": PoAFreshnessStatus value,
            "document_date": original date or None,
            "days_old": number of days since document date,
            "months_old": approximate months since document date,
            "is_valid": whether document counts toward PoA requirement,
            "reason": human-readable reason
        }
    """
    result = {
        "status": PoAFreshnessStatus.DATE_UNCLEAR.value,
        "document_date": None,
        "days_old": None,
        "months_old": None,
        "is_valid": False,
        "reason": "Document date not available"
    }
    
    # Manual override takes precedence
    if manual_override:
        result["status"] = PoAFreshnessStatus.MANUAL_OVERRIDE.value
        result["is_valid"] = True
        result["reason"] = "Manually approved by administrator"
        return result
    
    if not document_date:
        result["status"] = PoAFreshnessStatus.DATE_UNCLEAR.value
        result["is_valid"] = False
        result["reason"] = "Document date could not be extracted - manual review required"
        return result
    
    try:
        # Parse the date
        if 'T' in str(document_date):
            doc_date = datetime.fromisoformat(str(document_date).replace('Z', '+00:00'))
        else:
            doc_date = datetime.fromisoformat(str(document_date) + "T00:00:00+00:00")
        
        # Calculate age
        now = datetime.now(timezone.utc)
        days_old = (now - doc_date).days
        months_old = days_old // 30  # Approximate
        
        result["document_date"] = document_date
        result["days_old"] = days_old
        result["months_old"] = months_old
        
        if days_old <= POA_FRESHNESS_DAYS:
            result["status"] = PoAFreshnessStatus.VALID.value
            result["is_valid"] = True
            result["reason"] = f"Document is {months_old} months old (within {POA_FRESHNESS_MONTHS} months)"
        else:
            result["status"] = PoAFreshnessStatus.EXPIRED.value
            result["is_valid"] = False
            result["reason"] = f"Document is {months_old} months old (exceeds {POA_FRESHNESS_MONTHS} month limit)"
            
    except Exception as e:
        result["status"] = PoAFreshnessStatus.DATE_UNCLEAR.value
        result["is_valid"] = False
        result["reason"] = f"Could not parse document date: {str(e)}"
    
    return result


def evaluate_poa_compliance(documents: List[Dict]) -> Dict:
    """
    Evaluate overall PoA compliance based on document list.
    
    Args:
        documents: List of PoA document records, each should have:
            - document_date or extracted_fields.document_date
            - freshness_override (optional)
            - verified (optional)
            
    Returns:
        {
            "overall_status": PoAOverallStatus value,
            "valid_count": number of valid documents,
            "expired_count": number of expired documents,
            "unclear_count": number needing manual review,
            "override_count": number manually approved,
            "total_count": total documents,
            "required_count": 2 (NHS standard),
            "is_complete": whether PoA requirement is met,
            "blockers": list of blocker reasons,
            "documents": list with freshness details for each
        }
    """
    result = {
        "overall_status": PoAOverallStatus.INCOMPLETE.value,
        "valid_count": 0,
        "expired_count": 0,
        "unclear_count": 0,
        "override_count": 0,
        "total_count": len(documents),
        "required_count": POA_MINIMUM_DOCUMENTS,
        "is_complete": False,
        "blockers": [],
        "documents": []
    }
    
    for doc in documents:
        # Get document date from various possible locations
        doc_date = (
            doc.get("document_date") or 
            doc.get("extracted_date") or
            (doc.get("extracted_fields") or {}).get("document_date") or
            (doc.get("extraction_result") or {}).get("fields", {}).get("document_date")
        )
        
        # Check for manual override
        manual_override = (
            doc.get("freshness_override") or
            doc.get("freshness_status") == PoAFreshnessStatus.MANUAL_OVERRIDE.value
        )
        
        # Calculate freshness
        freshness = calculate_document_freshness(doc_date, manual_override)
        
        # Add document info
        doc_info = {
            "file_id": doc.get("file_id") or doc.get("id"),
            "original_filename": doc.get("original_filename"),
            "uploaded_at": doc.get("uploaded_at"),
            "verified": doc.get("verified", False),
            **freshness
        }
        result["documents"].append(doc_info)
        
        # Count by status
        if freshness["status"] == PoAFreshnessStatus.VALID.value:
            result["valid_count"] += 1
        elif freshness["status"] == PoAFreshnessStatus.EXPIRED.value:
            result["expired_count"] += 1
        elif freshness["status"] == PoAFreshnessStatus.DATE_UNCLEAR.value:
            result["unclear_count"] += 1
        elif freshness["status"] == PoAFreshnessStatus.MANUAL_OVERRIDE.value:
            result["override_count"] += 1
            result["valid_count"] += 1  # Overrides count as valid
    
    # Determine overall status
    effective_valid = result["valid_count"]  # Includes overrides
    
    if effective_valid >= POA_MINIMUM_DOCUMENTS:
        result["overall_status"] = PoAOverallStatus.COMPLETE.value
        result["is_complete"] = True
    elif result["unclear_count"] > 0:
        result["overall_status"] = PoAOverallStatus.REVIEW_NEEDED.value
        result["blockers"].append(f"{result['unclear_count']} document(s) need date verification")
    elif effective_valid > 0:
        result["overall_status"] = PoAOverallStatus.PARTIAL.value
        result["blockers"].append(f"Only {effective_valid}/{POA_MINIMUM_DOCUMENTS} valid documents")
    else:
        result["overall_status"] = PoAOverallStatus.INCOMPLETE.value
        if result["expired_count"] > 0:
            result["blockers"].append(f"{result['expired_count']} document(s) expired (older than 12 months)")
        else:
            result["blockers"].append("No valid proof of address documents")
    
    # Add expired document blocker
    if result["expired_count"] > 0 and not result["is_complete"]:
        result["blockers"].append(f"{result['expired_count']} expired document(s) need replacement")
    
    return result


def get_poa_blocker_for_approval(poa_evaluation: Dict) -> Optional[Dict]:
    """
    Get PoA blocker info for recruitment approval engine.
    
    Returns None if PoA requirement is met, otherwise returns blocker dict.
    """
    if poa_evaluation.get("is_complete"):
        return None
    
    status = poa_evaluation.get("overall_status")
    valid_count = poa_evaluation.get("valid_count", 0)
    required = poa_evaluation.get("required_count", POA_MINIMUM_DOCUMENTS)
    
    if status == PoAOverallStatus.REVIEW_NEEDED.value:
        return {
            "requirement_key": "proof_of_address",
            "label": "Proof of Address",
            "reason": f"Document dates unclear - manual review required ({valid_count}/{required} valid)",
            "category": "document",
            "needs_review": True
        }
    elif status == PoAOverallStatus.PARTIAL.value:
        return {
            "requirement_key": "proof_of_address",
            "label": "Proof of Address",
            "reason": f"Insufficient valid documents ({valid_count}/{required} within 12 months)",
            "category": "document"
        }
    else:
        expired_count = poa_evaluation.get("expired_count", 0)
        if expired_count > 0:
            return {
                "requirement_key": "proof_of_address",
                "label": "Proof of Address",
                "reason": f"No valid documents ({expired_count} expired, need 2 within 12 months)",
                "category": "expired_document"
            }
        return {
            "requirement_key": "proof_of_address",
            "label": "Proof of Address",
            "reason": f"Missing proof of address (need {required} documents within 12 months)",
            "category": "document"
        }
