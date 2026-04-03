# Unified Compliance Labels
# All human-readable labels for compliance UI display

from typing import Optional


# =============================================================================
# EVIDENCE STATUS LABELS
# =============================================================================

EVIDENCE_STATUS_LABELS = {
    "received": "Received",
    "pending_review": "Pending Review",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "uploaded_in_error": "Uploaded in Error",
    "superseded": "Superseded",
    "historical": "Historical",
    # Legacy statuses for backwards compatibility
    "active": "Active",
    "uploaded": "Uploaded",
    "approved": "Approved",
    "under_review": "Under Review",
    "verified": "Verified"
}


# =============================================================================
# STAMP TYPE LABELS
# =============================================================================

STAMP_TYPE_LABELS = {
    "original_verified": "Original Verified",
    "copy_verified": "Copy Verified",
    "online_verified": "Online Verified",
    "not_verified": "Not Verified",
    # Legacy stamps
    "original_seen": "Original Seen",
    "online_check": "Online Check"
}


# =============================================================================
# VERIFICATION STATUS LABELS
# =============================================================================

VERIFICATION_STATUS_LABELS = {
    "not_started": "Not Started",
    "completed": "Completed",
    "updated": "Updated",
    "failed": "Failed",
    "expired": "Expired",
    "follow_up_due": "Follow-up Due",
    "incomplete": "Incomplete"
}


# =============================================================================
# VERIFICATION OUTCOME LABELS
# =============================================================================

OUTCOME_LABELS = {
    "verified": "Verified",
    "failed": "Failed",
    "needs_more_info": "Needs More Information",
    "rejected": "Rejected",
    "follow_up_required": "Follow-up Required",
    "awaiting_review": "Awaiting Review"
}


# =============================================================================
# COMPUTED STATE LABELS
# =============================================================================

COMPUTED_STATE_LABELS = {
    "missing": "Missing",
    "awaiting_upload": "Awaiting Upload",
    "awaiting_review": "Awaiting Review",
    "reviewed": "Reviewed",
    "verification_pending": "Verification Pending",
    "verified": "Verified",
    "warning": "Warning",
    "expired": "Expired",
    "incomplete": "Incomplete"
}


# =============================================================================
# METHOD LABELS - By Requirement Type
# =============================================================================

# Right to Work Methods
RTW_METHOD_LABELS = {
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

# DBS Methods
DBS_METHOD_LABELS = {
    "update_service_check": "DBS Update Service Check",
    "manual_certificate_review": "Manual Certificate Review",
    "dbs_certificate_review": "DBS Certificate Review",
    "dbs_update_service_check": "DBS Update Service Check"
}

# Identity Methods
IDENTITY_METHOD_LABELS = {
    "original_document_seen": "Original Document Seen",
    "copy_verified": "Copy Verified",
    "digital_id_verification": "Digital ID Verification",
    "other_documented_verification": "Other Documented Verification",
    "manual_passport_check": "Manual Passport Check",
    "manual_id_verification": "Manual ID Verification",
    "digital_id_check": "Digital ID Check"
}

# Proof of Address Methods
ADDRESS_METHOD_LABELS = {
    "original_document_seen": "Original Document Seen",
    "uploaded_copy_reviewed": "Uploaded Copy Reviewed",
    "copy_verified": "Copy Verified",
    "other_documented_verification": "Other Documented Verification",
    "manual_document_check": "Manual Document Check"
}

# Combined method labels lookup
METHOD_LABELS = {
    **RTW_METHOD_LABELS,
    **DBS_METHOD_LABELS,
    **IDENTITY_METHOD_LABELS,
    **ADDRESS_METHOD_LABELS
}


# =============================================================================
# STATUS COLOR MAPPING
# =============================================================================

STATUS_COLORS = {
    # Computed states
    "missing": "gray",
    "awaiting_upload": "gray",
    "awaiting_review": "amber",
    "reviewed": "blue",
    "verification_pending": "amber",
    "verified": "green",
    "warning": "amber",
    "expired": "red",
    "incomplete": "red",
    # Verification outcomes
    "failed": "red",
    "needs_more_info": "amber",
    "rejected": "red",
    "follow_up_required": "amber",
    # RTW-specific
    "continuous": "green",
    "time_limited_valid": "green",
    "follow_up_due_soon": "amber",
    "urgent_follow_up": "red",
    "incomplete_result": "amber",
    "not_verified": "gray",
    # DBS-specific
    "clear": "green",
    "information_present": "amber",
    "pending_review": "amber",
    "recheck_due_soon": "amber",
    "recheck_overdue": "red"
}


# =============================================================================
# REQUIREMENT TYPE LABELS
# =============================================================================

REQUIREMENT_TYPE_LABELS = {
    "right_to_work": "Right to Work",
    "dbs": "DBS Check",
    "identity": "Identity Verification",
    "proof_of_address": "Proof of Address",
    "references": "References",
    "health_questionnaire": "Health Questionnaire",
    "interview_notes": "Interview Notes",
    "training": "Training",
    "agreements": "Agreements"
}


# =============================================================================
# BLOCKER MESSAGES
# =============================================================================

BLOCKER_MESSAGES = {
    "right_to_work": "Right to Work check not verified",
    "dbs": "DBS check not verified",
    "identity": "Identity verification not completed",
    "proof_of_address": "Proof of Address verification not completed",
    "references": "References not verified",
    "health_questionnaire": "Health questionnaire not completed"
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_label(label_type: str, key: str, default: Optional[str] = None) -> str:
    """
    Get a human-readable label for a given key.
    
    Args:
        label_type: Type of label ('evidence_status', 'stamp_type', 'method', etc.)
        key: The key to look up
        default: Default value if not found (if None, formats the key)
    
    Returns:
        Human-readable label string
    """
    label_maps = {
        "evidence_status": EVIDENCE_STATUS_LABELS,
        "stamp_type": STAMP_TYPE_LABELS,
        "verification_status": VERIFICATION_STATUS_LABELS,
        "outcome": OUTCOME_LABELS,
        "computed_state": COMPUTED_STATE_LABELS,
        "method": METHOD_LABELS,
        "rtw_method": RTW_METHOD_LABELS,
        "dbs_method": DBS_METHOD_LABELS,
        "identity_method": IDENTITY_METHOD_LABELS,
        "address_method": ADDRESS_METHOD_LABELS,
        "status_color": STATUS_COLORS,
        "requirement_type": REQUIREMENT_TYPE_LABELS,
        "blocker": BLOCKER_MESSAGES
    }
    
    label_map = label_maps.get(label_type, {})
    
    if key in label_map:
        return label_map[key]
    
    if default is not None:
        return default
    
    # Format the key as a fallback
    return key.replace("_", " ").title() if key else "Unknown"


def get_status_color(status: str) -> str:
    """Get the color for a given status."""
    return STATUS_COLORS.get(status, "gray")
