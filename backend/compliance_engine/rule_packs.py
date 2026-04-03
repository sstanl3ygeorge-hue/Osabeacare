# Unified Compliance Rule Packs
# Requirement-specific rules for RTW, DBS, Identity, and Proof of Address

from typing import Dict, List, Optional, Any
from datetime import datetime, date

from .models import (
    RequirementType, 
    ComputedState
)
from .labels import get_label, get_status_color


# =============================================================================
# BASE RULE PACK
# =============================================================================

class BaseRulePack:
    """
    Base class for requirement-specific rule packs.
    
    Each rule pack defines:
    - Required fields for the structured result
    - Method choices
    - Validation rules
    - Status computation logic
    """
    
    requirement_type: RequirementType = None
    
    # Required fields for a complete result
    required_fields: List[str] = []
    
    # Optional fields that enhance the result
    optional_fields: List[str] = []
    
    # Available verification methods
    methods: Dict[str, str] = {}
    
    # Minimum evidence files required
    min_evidence_files: int = 0
    
    # Whether this requirement blocks work readiness
    blocks_readiness: bool = True
    
    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get the list of required fields for this requirement type."""
        return cls.required_fields
    
    @classmethod
    def get_method_label(cls, method: str) -> str:
        """Get the human-readable label for a method."""
        return cls.methods.get(method, get_label("method", method))
    
    @classmethod
    def validate_result(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a structured result.
        
        Returns:
            Dict with 'is_valid', 'missing_fields', 'warnings'
        """
        missing = []
        warnings = []
        
        for field in cls.required_fields:
            if field not in data or data.get(field) is None:
                missing.append(field)
        
        return {
            "is_valid": len(missing) == 0,
            "missing_fields": missing,
            "warnings": warnings
        }
    
    @classmethod
    def compute_status(
        cls,
        verification_outcome: Optional[str],
        result_data: Dict[str, Any],
        evidence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Compute the overall status for this requirement.
        
        Returns:
            Dict with 'status', 'status_label', 'status_color', 'alerts', 'is_blocking'
        """
        # Default implementation
        if verification_outcome == "verified":
            return {
                "status": ComputedState.VERIFIED.value,
                "status_label": "Verified",
                "status_color": "green",
                "alerts": [],
                "is_blocking": False
            }
        elif verification_outcome:
            return {
                "status": ComputedState.INCOMPLETE.value,
                "status_label": get_label("outcome", verification_outcome),
                "status_color": get_status_color(verification_outcome),
                "alerts": [],
                "is_blocking": cls.blocks_readiness
            }
        elif evidence_count > 0:
            return {
                "status": ComputedState.AWAITING_REVIEW.value,
                "status_label": "Awaiting Review",
                "status_color": "amber",
                "alerts": [],
                "is_blocking": cls.blocks_readiness
            }
        else:
            return {
                "status": ComputedState.MISSING.value,
                "status_label": "Missing",
                "status_color": "gray",
                "alerts": [],
                "is_blocking": cls.blocks_readiness
            }


# =============================================================================
# RIGHT TO WORK RULE PACK
# =============================================================================

class RTWRulePack(BaseRulePack):
    """
    Right to Work specific rules.
    
    Key features:
    - Expiry date tracking with thresholds
    - Follow-up date tracking
    - Restriction tracking
    - Share code / reference number storage
    """
    
    requirement_type = RequirementType.RIGHT_TO_WORK
    
    required_fields = [
        "method",
        "checked_at",
        "outcome"
    ]
    
    optional_fields = [
        "permission_type",
        "permission_start_date",
        "permission_end_date",
        "is_indefinite",
        "share_code",
        "reference_number",
        "restrictions",
        "hours_limit",
        "follow_up_required",
        "follow_up_due_at",
        "route",
        "document_type"
    ]
    
    methods = {
        "home_office_online_check": "Home Office Online Check",
        "manual_passport_uk_irish": "Manual Check - UK/Irish Passport",
        "manual_list_a_document": "Manual Check - List A Document",
        "manual_list_a_check": "Manual List A Check",
        "manual_list_b_group_1": "Manual Check - List B Group 1",
        "manual_list_b_group_1_check": "Manual List B Group 1 Check",
        "manual_list_b_group_2_ecs": "Manual Check - List B Group 2 / ECS",
        "manual_list_b_group_2_check": "Manual List B Group 2 Check",
        "idsp_check": "Digital Verification Service (IDSP)",
        "digital_verification_service_check": "Digital Verification Service",
        "ecs_pvn_check": "Employer Checking Service (PVN)",
        "ecs_check": "Employer Checking Service",
        "share_code_online_check": "Share Code Online Check"
    }
    
    min_evidence_files = 0
    blocks_readiness = True
    
    # Expiry thresholds (days)
    EXPIRY_THRESHOLDS = {
        "green": 180,      # > 180 days: all good
        "amber": 90,       # 90-180 days: approaching
        "amber_warning": 30,  # 30-90 days: warning
        "red": 30,         # < 30 days: urgent
        "expired": 0       # expired
    }
    
    @classmethod
    def compute_status(
        cls,
        verification_outcome: Optional[str],
        result_data: Dict[str, Any],
        evidence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Compute RTW status with expiry and follow-up awareness.
        """
        alerts = []
        
        # Not verified yet
        if verification_outcome != "verified":
            return super().compute_status(verification_outcome, result_data, evidence_count)
        
        # Check for indefinite permission
        is_indefinite = result_data.get("is_indefinite", False)
        permission_end_date = result_data.get("permission_end_date")
        follow_up_due_at = result_data.get("follow_up_due_at")
        
        # Calculate days until expiry
        days_until_expiry = None
        if permission_end_date and not is_indefinite:
            try:
                if isinstance(permission_end_date, str):
                    end_date = datetime.fromisoformat(permission_end_date.replace("Z", "+00:00")).date()
                else:
                    end_date = permission_end_date
                
                days_until_expiry = (end_date - date.today()).days
            except (ValueError, TypeError):
                pass
        
        # Calculate days until follow-up
        days_until_followup = None
        if follow_up_due_at:
            try:
                if isinstance(follow_up_due_at, str):
                    followup_date = datetime.fromisoformat(follow_up_due_at.replace("Z", "+00:00")).date()
                else:
                    followup_date = follow_up_due_at
                
                days_until_followup = (followup_date - date.today()).days
            except (ValueError, TypeError):
                pass
        
        # Determine status
        if is_indefinite:
            status = "continuous"
            status_label = "Continuous Permission"
            status_color = "green"
        elif days_until_expiry is not None:
            if days_until_expiry < 0:
                status = "expired"
                status_label = "Permission Expired"
                status_color = "red"
                alerts.append({
                    "level": "error",
                    "message": f"Permission expired {abs(days_until_expiry)} days ago"
                })
            elif days_until_expiry <= cls.EXPIRY_THRESHOLDS["red"]:
                status = "urgent_follow_up"
                status_label = "Urgent - Expiring Soon"
                status_color = "red"
                alerts.append({
                    "level": "urgent",
                    "message": f"Permission expires in {days_until_expiry} days"
                })
            elif days_until_expiry <= cls.EXPIRY_THRESHOLDS["amber"]:
                status = "follow_up_due_soon"
                status_label = "Follow-up Due Soon"
                status_color = "amber"
                alerts.append({
                    "level": "warning",
                    "message": f"Permission expires in {days_until_expiry} days"
                })
            else:
                status = "time_limited_valid"
                status_label = "Time-Limited Permission - Valid"
                status_color = "green"
        else:
            status = "verified"
            status_label = "Verified"
            status_color = "green"
        
        # Check follow-up separately
        if days_until_followup is not None and days_until_followup < 0:
            alerts.append({
                "level": "error",
                "message": f"Follow-up overdue by {abs(days_until_followup)} days"
            })
            if status_color != "red":
                status_color = "red"
                status = "urgent_follow_up"
                status_label = "Follow-up Overdue"
        elif days_until_followup is not None and days_until_followup <= 30:
            alerts.append({
                "level": "warning",
                "message": f"Follow-up due in {days_until_followup} days"
            })
        
        # Check for restrictions
        if result_data.get("restrictions"):
            alerts.append({
                "level": "info",
                "message": "Work restrictions apply"
            })
        
        return {
            "status": status,
            "status_label": status_label,
            "status_color": status_color,
            "days_until_expiry": days_until_expiry,
            "days_until_followup": days_until_followup,
            "is_indefinite": is_indefinite,
            "alerts": alerts,
            "is_blocking": status == "expired"
        }


# =============================================================================
# DBS RULE PACK
# =============================================================================

class DBSRulePack(BaseRulePack):
    """
    DBS Check specific rules.
    
    Key features:
    - Certificate number and level tracking
    - Update Service integration
    - No statutory expiry - policy-based recheck
    - Information present tracking
    """
    
    requirement_type = RequirementType.DBS
    
    required_fields = [
        "method",
        "checked_at",
        "outcome"
    ]
    
    optional_fields = [
        "dbs_level",
        "certificate_number",
        "certificate_issue_date",
        "name_on_certificate",
        "workforce",
        "update_service_registered",
        "update_service_status",
        "last_status_check_date",
        "update_service_check_result",
        "result_status",
        "information_present",
        "result_summary",
        "recheck_required",
        "next_recheck_date"
    ]
    
    methods = {
        "update_service_check": "DBS Update Service Check",
        "manual_certificate_review": "Manual Certificate Review",
        "dbs_certificate_review": "DBS Certificate Review",
        "dbs_update_service_check": "DBS Update Service Check"
    }
    
    min_evidence_files = 0
    blocks_readiness = True
    
    # Default recheck period (3 years in days)
    DEFAULT_RECHECK_DAYS = 1095
    
    # Recheck thresholds (days)
    RECHECK_THRESHOLDS = {
        "green": 180,      # > 180 days: all good
        "amber": 90,       # 90-180 days: approaching
        "red": 30,         # < 30 days: urgent
        "overdue": 0       # overdue
    }
    
    @classmethod
    def compute_status(
        cls,
        verification_outcome: Optional[str],
        result_data: Dict[str, Any],
        evidence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Compute DBS status with recheck and information-present awareness.
        """
        alerts = []
        
        # Not verified yet
        if verification_outcome != "verified":
            return super().compute_status(verification_outcome, result_data, evidence_count)
        
        next_recheck_date = result_data.get("next_recheck_date")
        information_present = result_data.get("information_present", False)
        result_status = result_data.get("result_status", "clear")
        update_service_status = result_data.get("update_service_status")
        
        # Calculate days until recheck
        days_until_recheck = None
        if next_recheck_date:
            try:
                if isinstance(next_recheck_date, str):
                    recheck_date = datetime.fromisoformat(next_recheck_date.replace("Z", "+00:00")).date()
                else:
                    recheck_date = next_recheck_date
                
                days_until_recheck = (recheck_date - date.today()).days
            except (ValueError, TypeError):
                pass
        
        # Base status from result
        if information_present or result_status == "information_present":
            status = "information_present"
            status_label = "Information Present - Review Required"
            status_color = "amber"
            alerts.append({
                "level": "warning",
                "message": "DBS contains disclosed information"
            })
        else:
            status = "clear"
            status_label = "Clear"
            status_color = "green"
        
        # Check recheck dates (policy-based, not statutory)
        if days_until_recheck is not None:
            if days_until_recheck < 0:
                status = "recheck_overdue"
                status_label = "Recheck Overdue"
                status_color = "red"
                alerts.append({
                    "level": "error",
                    "message": f"DBS recheck overdue by {abs(days_until_recheck)} days"
                })
            elif days_until_recheck <= cls.RECHECK_THRESHOLDS["red"]:
                alerts.append({
                    "level": "urgent",
                    "message": f"DBS recheck due in {days_until_recheck} days"
                })
                if status_color == "green":
                    status_color = "amber"
                    status = "recheck_due_soon"
                    status_label = "Recheck Due Soon"
            elif days_until_recheck <= cls.RECHECK_THRESHOLDS["amber"]:
                alerts.append({
                    "level": "warning",
                    "message": f"DBS recheck due in {days_until_recheck} days"
                })
        
        # Update Service status
        if update_service_status == "active":
            alerts.append({
                "level": "info",
                "message": "Registered on DBS Update Service"
            })
        
        return {
            "status": status,
            "status_label": status_label,
            "status_color": status_color,
            "days_until_recheck": days_until_recheck,
            "information_present": information_present,
            "alerts": alerts,
            "is_blocking": status == "recheck_overdue"
        }


# =============================================================================
# IDENTITY RULE PACK
# =============================================================================

class IdentityRulePack(BaseRulePack):
    """
    Identity Verification specific rules.
    
    Key features:
    - Document type tracking (passport, driving licence, ID card)
    - Name/DOB/Photo match verification
    - Document expiry tracking
    """
    
    requirement_type = RequirementType.IDENTITY
    
    required_fields = [
        "method",
        "checked_at",
        "outcome"
    ]
    
    optional_fields = [
        "document_type",
        "full_name_on_document",
        "date_of_birth",
        "document_number",
        "issue_date",
        "expiry_date",
        "nationality",
        "name_matches_application",
        "dob_matches_application",
        "photo_match_confirmed"
    ]
    
    methods = {
        "original_document_seen": "Original Document Seen",
        "copy_verified": "Copy Verified",
        "digital_id_verification": "Digital ID Verification",
        "other_documented_verification": "Other Documented Verification",
        "manual_passport_check": "Manual Passport Check",
        "manual_id_verification": "Manual ID Verification",
        "digital_id_check": "Digital ID Check"
    }
    
    min_evidence_files = 1
    blocks_readiness = True
    
    @classmethod
    def compute_status(
        cls,
        verification_outcome: Optional[str],
        result_data: Dict[str, Any],
        evidence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Compute Identity status with document expiry and match awareness.
        """
        alerts = []
        
        # Not verified yet
        if verification_outcome != "verified":
            return super().compute_status(verification_outcome, result_data, evidence_count)
        
        expiry_date = result_data.get("expiry_date")
        name_matches = result_data.get("name_matches_application", False)
        dob_matches = result_data.get("dob_matches_application", False)
        photo_match = result_data.get("photo_match_confirmed", False)
        
        # Calculate days until expiry
        days_until_expiry = None
        if expiry_date:
            try:
                if isinstance(expiry_date, str):
                    exp_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00")).date()
                else:
                    exp_date = expiry_date
                
                days_until_expiry = (exp_date - date.today()).days
            except (ValueError, TypeError):
                pass
        
        # Base status
        status = "verified"
        status_label = "Verified"
        status_color = "green"
        
        # Check for mismatches
        if not name_matches:
            alerts.append({
                "level": "warning",
                "message": "Name does not match application"
            })
        if not dob_matches:
            alerts.append({
                "level": "warning",
                "message": "Date of birth does not match application"
            })
        if not photo_match:
            alerts.append({
                "level": "warning",
                "message": "Photo match not confirmed"
            })
        
        # Check document expiry
        if days_until_expiry is not None:
            if days_until_expiry < 0:
                status = "expired"
                status_label = "Document Expired"
                status_color = "red"
                alerts.append({
                    "level": "error",
                    "message": f"Identity document expired {abs(days_until_expiry)} days ago"
                })
            elif days_until_expiry <= 30:
                alerts.append({
                    "level": "warning",
                    "message": f"Identity document expires in {days_until_expiry} days"
                })
                if status_color == "green":
                    status_color = "amber"
        
        return {
            "status": status,
            "status_label": status_label,
            "status_color": status_color,
            "days_until_expiry": days_until_expiry,
            "alerts": alerts,
            "is_blocking": status == "expired"
        }


# =============================================================================
# PROOF OF ADDRESS RULE PACK
# =============================================================================

class POARulePack(BaseRulePack):
    """
    Proof of Address specific rules.
    
    Key features:
    - Document count requirement (default: 2)
    - Document type-specific recency limits
    - Address matching
    """
    
    requirement_type = RequirementType.PROOF_OF_ADDRESS
    
    required_fields = [
        "method",
        "checked_at",
        "outcome"
    ]
    
    optional_fields = [
        "documents_received_count",
        "documents_required_count",
        "verified_documents",
        "extracted_address_line1",
        "extracted_address_line2",
        "extracted_city",
        "extracted_postcode",
        "address_matches_application",
        "all_documents_sufficiently_recent"
    ]
    
    methods = {
        "original_document_seen": "Original Document Seen",
        "uploaded_copy_reviewed": "Uploaded Copy Reviewed",
        "copy_verified": "Copy Verified",
        "other_documented_verification": "Other Documented Verification",
        "manual_document_check": "Manual Document Check"
    }
    
    min_evidence_files = 2  # PoA requires 2 documents
    blocks_readiness = True
    
    # Document type recency limits (months)
    DOCUMENT_RECENCY = {
        "utility_bill": 3,
        "bank_statement": 3,
        "council_tax": 6,
        "hmrc_letter": 6,
        "government_letter": 6,
        "tenancy_agreement": None,  # Valid if current
        "mortgage_statement": 6,
        "other": 3
    }
    
    @classmethod
    def get_recency_limit(cls, document_type: str) -> Optional[int]:
        """Get the recency limit in months for a document type."""
        return cls.DOCUMENT_RECENCY.get(document_type, 3)
    
    @classmethod
    def compute_status(
        cls,
        verification_outcome: Optional[str],
        result_data: Dict[str, Any],
        evidence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Compute PoA status with document count and recency awareness.
        """
        alerts = []
        
        # Not verified yet
        if verification_outcome != "verified":
            return super().compute_status(verification_outcome, result_data, evidence_count)
        
        documents_received = result_data.get("documents_received_count", 0)
        documents_required = result_data.get("documents_required_count", 2)
        all_recent = result_data.get("all_documents_sufficiently_recent", False)
        address_matches = result_data.get("address_matches_application", False)
        
        # Base status
        if documents_received >= documents_required and all_recent:
            status = "verified"
            status_label = f"{documents_received}/{documents_required} Valid Documents"
            status_color = "green"
        elif documents_received >= documents_required and not all_recent:
            status = "outdated_docs"
            status_label = "Contains Outdated Documents"
            status_color = "amber"
            alerts.append({
                "level": "warning",
                "message": "Some documents are outside recency limits"
            })
        elif documents_received > 0:
            status = "partial"
            status_label = f"{documents_received}/{documents_required} Documents"
            status_color = "amber"
            alerts.append({
                "level": "warning",
                "message": f"Need {documents_required - documents_received} more document(s)"
            })
        else:
            status = "missing"
            status_label = "No Documents"
            status_color = "gray"
        
        # Check address match
        if not address_matches and verification_outcome == "verified":
            alerts.append({
                "level": "warning",
                "message": "Address does not match application"
            })
        
        return {
            "status": status,
            "status_label": status_label,
            "status_color": status_color,
            "documents_received": documents_received,
            "documents_required": documents_required,
            "all_documents_recent": all_recent,
            "alerts": alerts,
            "is_blocking": documents_received < documents_required
        }


# =============================================================================
# RULE PACK REGISTRY
# =============================================================================

RULE_PACKS = {
    RequirementType.RIGHT_TO_WORK: RTWRulePack,
    RequirementType.DBS: DBSRulePack,
    RequirementType.IDENTITY: IdentityRulePack,
    RequirementType.PROOF_OF_ADDRESS: POARulePack
}


def get_rule_pack(requirement_type: RequirementType) -> type:
    """Get the rule pack class for a requirement type."""
    return RULE_PACKS.get(requirement_type, BaseRulePack)
