"""
Data transformation mappings for migration.
"""

# Person status mapping (MongoDB string -> Postgres ENUM)
PERSON_STATUS_MAP = {
    "new": "new",
    "screening": "screening",
    "interview": "interview",
    "compliance_review": "compliance_review",
    "onboarding": "onboarding",
    "active": "active",
    "inactive": "inactive",
    "archived": "archived",
    # Variants
    "in progress": "screening",
    "pending": "new",
    "hired": "onboarding",
    "in_progress": "screening",
}

# User role mapping
ROLE_MAP = {
    "super_admin": "super_admin",
    "admin": "admin",
    "branch_manager": "branch_manager",
    "employee": "employee",
    "auditor": "auditor",
    # Variants
    "superadmin": "super_admin",
    "manager": "branch_manager",
}

# Document status mapping
DOCUMENT_STATUS_MAP = {
    "uploaded": "uploaded",
    "awaiting_review": "awaiting_review",
    "verified": "verified",
    "rejected": "rejected",
    "expired": "expired",
    "superseded": "superseded",
    # Variants
    "pending": "awaiting_review",
    "approved": "verified",
    "active": "verified",
}

# Document category mapping
DOCUMENT_CATEGORY_MAP = {
    "right_to_work": "right_to_work",
    "dbs": "dbs",
    "identity": "identity",
    "proof_of_address": "proof_of_address",
    "training": "training",
    "cv": "cv",
    "reference": "reference",
    "agreement": "agreement",
    "verification_proof": "verification_proof",
    "form_attachment": "form_attachment",
    "other": "other",
    # Variants
    "rtw": "right_to_work",
    "poa": "proof_of_address",
    "address": "proof_of_address",
    "id": "identity",
}

# Verification outcome mapping
VERIFICATION_OUTCOME_MAP = {
    "awaiting_review": "awaiting_review",
    "verified": "verified",
    "failed": "failed",
    "follow_up_required": "follow_up_required",
    "rejected": "rejected",
    # Variants
    "pending": "awaiting_review",
    "passed": "verified",
    "approved": "verified",
}

# Check method mapping
CHECK_METHOD_MAP = {
    "share_code_online_check": "share_code_online_check",
    "manual_passport_check": "manual_passport_check",
    "manual_document_review": "manual_document_review",
    "update_service_check": "update_service_check",
    "manual_certificate_review": "manual_certificate_review",
    "in_person": "in_person",
    "video_call": "video_call",
    # Variants
    "online": "share_code_online_check",
    "manual": "manual_document_review",
}

# Reference status mapping
REFERENCE_STATUS_MAP = {
    "not_declared": "not_declared",
    "declared": "declared",
    "request_sent": "request_sent",
    "request_viewed": "request_viewed",
    "response_received": "response_received",
    "verified": "verified",
    "rejected": "rejected",
    # Variants
    "sent": "request_sent",
    "viewed": "request_viewed",
    "received": "response_received",
}

def get_mapped_value(value, mapping, default=None):
    """Get mapped value with case-insensitive lookup."""
    if not value:
        return default
    normalized = str(value).lower().strip()
    return mapping.get(normalized, default or normalized)
