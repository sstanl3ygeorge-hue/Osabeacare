# Unified Compliance Models
# Shared object model for all requirement types

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# ENUMERATIONS - Shared across all requirement types
# =============================================================================

class RequirementType(str, Enum):
    """Supported requirement types"""
    RIGHT_TO_WORK = "right_to_work"
    DBS = "dbs"
    IDENTITY = "identity"
    PROOF_OF_ADDRESS = "proof_of_address"
    REFERENCES = "references"
    HEALTH_QUESTIONNAIRE = "health_questionnaire"
    INTERVIEW_NOTES = "interview_notes"
    TRAINING = "training"
    AGREEMENTS = "agreements"


class EvidenceStatus(str, Enum):
    """Shared evidence review statuses"""
    RECEIVED = "received"
    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UPLOADED_IN_ERROR = "uploaded_in_error"
    SUPERSEDED = "superseded"
    HISTORICAL = "historical"


class StampType(str, Enum):
    """Shared stamp types - per evidence, not per requirement"""
    ORIGINAL_VERIFIED = "original_verified"
    COPY_VERIFIED = "copy_verified"
    ONLINE_VERIFIED = "online_verified"
    NOT_VERIFIED = "not_verified"


class VerificationStatus(str, Enum):
    """Shared verification statuses"""
    NOT_STARTED = "not_started"
    COMPLETED = "completed"
    UPDATED = "updated"
    FAILED = "failed"
    EXPIRED = "expired"
    FOLLOW_UP_DUE = "follow_up_due"
    INCOMPLETE = "incomplete"


class VerificationOutcome(str, Enum):
    """Shared verification outcomes"""
    VERIFIED = "verified"
    FAILED = "failed"
    NEEDS_MORE_INFO = "needs_more_info"
    REJECTED = "rejected"


class ComputedState(str, Enum):
    """Shared computed states for all requirements"""
    MISSING = "missing"
    AWAITING_UPLOAD = "awaiting_upload"
    AWAITING_REVIEW = "awaiting_review"
    REVIEWED = "reviewed"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    WARNING = "warning"
    EXPIRED = "expired"
    INCOMPLETE = "incomplete"


class VisibilityBucket(str, Enum):
    """Evidence visibility for UI display"""
    ACTIVE = "active"
    HISTORICAL = "historical"
    HIDDEN = "hidden"


# =============================================================================
# SHARED OBJECT MODELS
# =============================================================================

class Evidence(BaseModel):
    """
    Shared evidence model for all requirement types.
    
    Evidence is per-file, not per-requirement.
    Stamp is per-evidence.
    """
    evidence_id: str
    requirement_type: RequirementType
    employee_id: str
    file_name: str
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    
    # Upload info
    uploaded_by: str
    uploaded_at: datetime
    source: str = "applicant_upload"  # applicant_upload, admin_upload, extraction
    
    # Review state
    review_status: EvidenceStatus = EvidenceStatus.RECEIVED
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    # Stamp state - per evidence, not per requirement
    stamp_type: Optional[StampType] = None
    stamped_by: Optional[str] = None
    stamped_at: Optional[datetime] = None
    
    # Visibility
    visibility_bucket: VisibilityBucket = VisibilityBucket.ACTIVE
    
    # Notes
    notes: Optional[str] = None
    
    # Labels for frontend
    review_status_label: Optional[str] = None
    stamp_type_label: Optional[str] = None
    uploaded_by_name: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    stamped_by_name: Optional[str] = None
    
    class Config:
        use_enum_values = True


class Verification(BaseModel):
    """
    Shared verification record for all requirement types.
    
    Verification is requirement-level, not evidence-level.
    """
    verification_id: str
    requirement_type: RequirementType
    employee_id: str
    
    # Verification details
    method: str  # Requirement-specific method
    outcome: VerificationOutcome
    checked_at: str  # YYYY-MM-DD
    checked_by: str
    
    # Proof of check
    proof_document_id: Optional[str] = None
    proof_required: bool = False
    
    # Status
    status: VerificationStatus = VerificationStatus.COMPLETED
    
    # Notes
    notes: Optional[str] = None
    
    # Labels for frontend
    method_label: Optional[str] = None
    outcome_label: Optional[str] = None
    checked_by_name: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class StructuredResult(BaseModel):
    """
    Shared structured result container.
    
    The 'data' field contains requirement-specific fields.
    Computed state and badges are standard.
    """
    result_id: str
    verification_id: str
    requirement_type: RequirementType
    
    # Requirement-specific result data
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Computed state from rule pack
    computed_state: ComputedState = ComputedState.INCOMPLETE
    computed_state_label: Optional[str] = None
    
    # Computed badges for display
    computed_badges: List[str] = Field(default_factory=list)
    
    # Minimum required fields check
    is_complete: bool = False
    missing_fields: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class RequirementSummary(BaseModel):
    """
    Master summary object for each requirement.
    
    This is what the UI reads to display status.
    """
    requirement_type: RequirementType
    requirement_key: str  # e.g., "right_to_work", "dbs"
    
    # Overall status
    status: ComputedState = ComputedState.MISSING
    status_label: str = "Missing"
    status_color: str = "gray"  # green, amber, red, gray
    
    # Blocker info
    blocking: bool = True
    blocker_text: Optional[str] = None
    
    # Evidence counts
    evidence_count: int = 0
    active_evidence_count: int = 0
    accepted_evidence_count: int = 0
    pending_review_count: int = 0
    historical_evidence_count: int = 0
    
    # Verification reference
    current_verification_id: Optional[str] = None
    has_verification: bool = False
    verification_outcome: Optional[str] = None
    
    # Result state
    current_result_id: Optional[str] = None
    current_result_state: Optional[str] = None
    
    # Display
    summary_label: str = "Not started"
    summary_badges: List[str] = Field(default_factory=list)
    
    # Contribution to page totals
    contributes_blocker: bool = True
    contributes_warning: bool = False
    contributes_pending_review: int = 0
    
    class Config:
        use_enum_values = True


# =============================================================================
# PAGE-LEVEL SUMMARY
# =============================================================================

class ComplianceSummary(BaseModel):
    """
    Page-level compliance summary.
    
    One source of truth for all counts.
    """
    employee_id: str
    
    # Counts
    total_requirements: int = 0
    completed_count: int = 0
    blocking_count: int = 0
    warning_count: int = 0
    pending_review_count: int = 0
    missing_count: int = 0
    
    # Computed
    completion_percentage: float = 0.0
    is_ready_to_work: bool = False
    can_approve: bool = False
    
    # Blocker list for display
    blockers: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    pending_items: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Requirement summaries
    requirements: Dict[str, RequirementSummary] = Field(default_factory=dict)


# =============================================================================
# REQUEST MODELS
# =============================================================================

class DocumentRequestItem(BaseModel):
    """Single item in a consolidated request"""
    requirement_type: RequirementType
    requirement_key: str
    requirement_name: str
    instructions: Optional[str] = None
    selected: bool = True


class ConsolidatedRequest(BaseModel):
    """
    Consolidated request model.
    
    One email, multiple requirements, no spam.
    """
    employee_id: str
    employee_name: str
    employee_email: str
    
    # Selected requirements
    items: List[DocumentRequestItem]
    
    # Request details
    requested_by: str
    requested_at: datetime
    custom_message: Optional[str] = None
    
    # Tracking
    request_id: str
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
