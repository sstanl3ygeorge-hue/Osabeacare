"""
Email Automation Architecture - Phase 2
========================================
Extends the email base architecture into a safe automation layer for 
recruitment and compliance requests.

Principles:
- Portal remains source of truth
- Email is delivery + routing + communication evidence only
- No duplicate business logic or storage
- Every click/submission maps cleanly into existing system flows

Usage:
    from email_automation import EmailRequestService, RequestType, RequestStatus
    
    # Create a request (checks for duplicates, creates token, sends email)
    result = await EmailRequestService.create_request(
        person_id="emp-123",
        person_type="employee",
        requirement_id="proof_of_address",
        request_type=RequestType.UPLOAD_DOCUMENT,
        due_days=14
    )
    
    # Track events
    await EmailRequestService.track_event(request_id, EventType.CLICKED)
    
    # Process scheduled reminders
    await EmailRequestService.process_reminders()
"""

import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

PORTAL_URL = os.environ.get('PORTAL_URL', 'https://app.osabeacares.co.uk')

# Reminder schedule (days after initial send)
REMINDER_SCHEDULE = {
    "first_reminder": 3,
    "second_reminder": 7,
    "escalation": 14,
}

# Expiry reminder schedule (days before expiry)
EXPIRY_REMINDER_SCHEDULE = [60, 30, 14, 7, 0]  # 0 = on expiry day

# Default request expiry (days)
DEFAULT_REQUEST_EXPIRY_DAYS = 30


# =============================================================================
# 1. REQUEST LIFECYCLE MODEL
# =============================================================================

class RequestStatus(str, Enum):
    """Request lifecycle states"""
    PENDING_SEND = "pending_send"      # Created, not yet sent
    SENT = "sent"                       # Email delivered
    OPENED = "opened"                   # Email opened (via tracking pixel if implemented)
    CLICKED = "clicked"                 # CTA link clicked
    ACTION_STARTED = "action_started"   # User began the action
    SUBMITTED = "submitted"             # User submitted the form/upload
    COMPLETED = "completed"             # Admin verified/approved (if required)
    EXPIRED = "expired"                 # Token/request expired
    CANCELLED = "cancelled"             # Manually cancelled
    FAILED = "failed"                   # Send failed permanently
    SUPERSEDED = "superseded"           # Replaced by newer request


class RequestType(str, Enum):
    """Types of actionable email requests"""
    UPLOAD_DOCUMENT = "upload_document"
    COMPLETE_FORM = "complete_form"
    EXPLAIN_GAP = "explain_gap"
    REVIEW_REFERENCE = "review_reference"
    VERIFY_REFERENCE = "verify_reference"
    UPLOAD_TRAINING = "upload_training"
    CONFIRM_DETAILS = "confirm_details"


class EventType(str, Enum):
    """Event types for request tracking"""
    CREATED = "created"
    SENT = "sent"
    SEND_FAILED = "send_failed"
    OPENED = "opened"
    CLICKED = "clicked"
    ACTION_STARTED = "action_started"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REMINDER_SENT = "reminder_sent"
    ESCALATION_SENT = "escalation_sent"
    SUPERSEDED = "superseded"
    TOKEN_USED = "token_used"
    TOKEN_EXPIRED = "token_expired"
    DUPLICATE_BLOCKED = "duplicate_blocked"


@dataclass
class EmailRequest:
    """
    Structured request for actionable emails.
    
    This model tracks the lifecycle of email-driven requests WITHOUT 
    duplicating the underlying requirement data.
    """
    id: str
    person_id: str                      # employee_id or applicant_id
    person_type: str                    # "employee" or "applicant"
    requirement_id: Optional[str]       # Links to existing requirement (not duplicated)
    request_type: RequestType
    template_key: str                   # Email template used
    token_id: str                       # JWT token ID (jti claim)
    
    # Status tracking
    status: RequestStatus = RequestStatus.PENDING_SEND
    
    # Timestamps
    created_at: Optional[str] = None
    sent_at: Optional[str] = None
    due_at: Optional[str] = None        # When action is due
    expires_at: Optional[str] = None    # When token expires
    resolved_at: Optional[str] = None   # When completed/cancelled/expired
    
    # Reminder tracking
    reminder_count: int = 0
    last_reminder_at: Optional[str] = None
    next_reminder_at: Optional[str] = None
    
    # Linkage (for audit trail only - actual data lives in portal)
    email_log_id: Optional[str] = None
    submission_id: Optional[str] = None  # Links to where submission landed
    submission_type: Optional[str] = None  # "compliance_status", "form_submission", etc.
    
    # Related entity (for gap/reference requests)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    
    # Metadata
    recipient_email: Optional[str] = None
    admin_notes: Optional[str] = None
    failure_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "person_type": self.person_type,
            "requirement_id": self.requirement_id,
            "request_type": self.request_type.value if isinstance(self.request_type, RequestType) else self.request_type,
            "template_key": self.template_key,
            "token_id": self.token_id,
            "status": self.status.value if isinstance(self.status, RequestStatus) else self.status,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "due_at": self.due_at,
            "expires_at": self.expires_at,
            "resolved_at": self.resolved_at,
            "reminder_count": self.reminder_count,
            "last_reminder_at": self.last_reminder_at,
            "next_reminder_at": self.next_reminder_at,
            "email_log_id": self.email_log_id,
            "submission_id": self.submission_id,
            "submission_type": self.submission_type,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "recipient_email": self.recipient_email,
            "admin_notes": self.admin_notes,
            "failure_reason": self.failure_reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailRequest":
        """Create from MongoDB document"""
        return cls(
            id=data["id"],
            person_id=data["person_id"],
            person_type=data["person_type"],
            requirement_id=data.get("requirement_id"),
            request_type=RequestType(data["request_type"]) if data.get("request_type") else RequestType.UPLOAD_DOCUMENT,
            template_key=data["template_key"],
            token_id=data["token_id"],
            status=RequestStatus(data["status"]) if data.get("status") else RequestStatus.PENDING_SEND,
            created_at=data.get("created_at"),
            sent_at=data.get("sent_at"),
            due_at=data.get("due_at"),
            expires_at=data.get("expires_at"),
            resolved_at=data.get("resolved_at"),
            reminder_count=data.get("reminder_count", 0),
            last_reminder_at=data.get("last_reminder_at"),
            next_reminder_at=data.get("next_reminder_at"),
            email_log_id=data.get("email_log_id"),
            submission_id=data.get("submission_id"),
            submission_type=data.get("submission_type"),
            related_entity_type=data.get("related_entity_type"),
            related_entity_id=data.get("related_entity_id"),
            recipient_email=data.get("recipient_email"),
            admin_notes=data.get("admin_notes"),
            failure_reason=data.get("failure_reason"),
        )


@dataclass
class RequestEvent:
    """
    Event tracking for request lifecycle.
    
    Extends email_logs - events are stored as a sub-array in email_requests
    rather than creating parallel logging.
    """
    id: str
    request_id: str
    event_type: EventType
    timestamp: str
    actor_id: Optional[str] = None      # user_id if human-triggered
    actor_type: Optional[str] = None    # "system", "admin", "employee"
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "details": self.details,
        }


# =============================================================================
# 2. REQUEST TYPE TO TEMPLATE MAPPING
# =============================================================================

REQUEST_TYPE_TEMPLATES = {
    RequestType.UPLOAD_DOCUMENT: {
        "default": "documents.missing_mandatory",
        "proof_of_address": "recruitment.missing_proof_of_address",
        "expiry_60": "documents.expiring_60_days",
        "expiry_30": "documents.expiring_30_days",
    },
    RequestType.EXPLAIN_GAP: {
        "default": "recruitment.cv_gap_explanation_required",
    },
    RequestType.REVIEW_REFERENCE: {
        "default": "recruitment.reference_verification_required",
    },
    RequestType.VERIFY_REFERENCE: {
        "default": "recruitment.reference_verification_required",
    },
    RequestType.UPLOAD_TRAINING: {
        "default": "training.expired",
    },
}

REQUEST_TYPE_ACTIONS = {
    RequestType.UPLOAD_DOCUMENT: "upload_document",
    RequestType.EXPLAIN_GAP: "explain_cv_gap",
    RequestType.REVIEW_REFERENCE: "update_reference",
    RequestType.VERIFY_REFERENCE: "update_reference",
    RequestType.UPLOAD_TRAINING: "upload_training_certificate",
    RequestType.COMPLETE_FORM: "complete_form",
    RequestType.CONFIRM_DETAILS: "confirm_details",
}


# =============================================================================
# 3. SUBMISSION ROUTING
# =============================================================================

# Maps request types to where submissions should land in existing structures
SUBMISSION_ROUTING = {
    RequestType.UPLOAD_DOCUMENT: {
        "collection": "compliance_status",
        "field": "evidence_files",
        "submission_type": "compliance_status",
    },
    RequestType.EXPLAIN_GAP: {
        "collection": "employees",
        "field": "employment_history.$.gap_after.explanation",
        "submission_type": "gap_explanation",
    },
    RequestType.REVIEW_REFERENCE: {
        "collection": "employees",
        "field": "reference_{n}_verified",
        "submission_type": "reference_update",
    },
    RequestType.VERIFY_REFERENCE: {
        "collection": "employees",
        "field": "reference_{n}_verified",
        "submission_type": "reference_verification",
    },
    RequestType.UPLOAD_TRAINING: {
        "collection": "training_records",
        "field": "certificate_url",
        "submission_type": "training_record",
    },
    RequestType.COMPLETE_FORM: {
        "collection": "form_submissions",
        "field": None,
        "submission_type": "form_submission",
    },
}


# =============================================================================
# 4. EMAIL REQUEST SERVICE
# =============================================================================

class EmailRequestService:
    """
    Central service for email-driven request automation.
    
    This service:
    - Creates and tracks actionable email requests
    - Prevents duplicate active requests
    - Manages reminder schedules
    - Links submissions back to requests
    - Does NOT duplicate business logic or requirement data
    """
    
    _db = None
    _email_service = None
    
    @classmethod
    def initialize(cls, db, email_service):
        """Initialize with database and email service references"""
        cls._db = db
        cls._email_service = email_service
    
    # -------------------------------------------------------------------------
    # REQUEST CREATION
    # -------------------------------------------------------------------------
    
    @classmethod
    async def create_request(
        cls,
        person_id: str,
        person_type: str,
        request_type: RequestType,
        requirement_id: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        template_variant: str = "default",
        due_days: int = 14,
        expiry_days: int = DEFAULT_REQUEST_EXPIRY_DAYS,
        context: Optional[Dict[str, Any]] = None,
        send_immediately: bool = True,
        admin_id: Optional[str] = None,
        force_resend: bool = False
    ) -> Dict[str, Any]:
        """
        Create an email request with duplicate checking.
        
        Args:
            force_resend: If True, supersede any existing active request and send new email
        
        Returns:
            Dict with status (sent, resent, duplicate_blocked, error, etc.), request_id, or error details
        """
        if cls._db is None:
            return {"status": "error", "reason": "Service not initialized"}
        
        # Check for duplicate active request
        duplicate_check = await cls._check_duplicate(
            person_id, person_type, requirement_id, request_type, related_entity_type, related_entity_id
        )
        
        superseded_request_id = None
        is_resend = False
        
        if duplicate_check["has_duplicate"]:
            if force_resend:
                # Supersede the existing request
                superseded_request_id = duplicate_check["existing_request_id"]
                await cls._supersede_request(superseded_request_id, admin_id)
                is_resend = True
            else:
                # Block the duplicate
                await cls._track_event(
                    duplicate_check["existing_request_id"],
                    EventType.DUPLICATE_BLOCKED,
                    actor_id=admin_id,
                    actor_type="admin" if admin_id else "system",
                    details={"new_request_attempted": True}
                )
                return {
                    "status": "duplicate_blocked",
                    "reason": "Active request already exists. Use 'Resend' to send a new email.",
                    "existing_request_id": duplicate_check["existing_request_id"]
                }
        
        # Check if requirement is already satisfied
        if requirement_id:
            is_satisfied = await cls._check_requirement_satisfied(
                person_id, person_type, requirement_id, request_type
            )
            if is_satisfied:
                return {
                    "status": "already_satisfied",
                    "reason": "Requirement already met"
                }
        
        # Get recipient email
        recipient = await cls._get_recipient(person_id, person_type)
        if not recipient or not recipient.get("email"):
            return {"status": "error", "reason": "No email address for recipient"}
        
        # Determine template
        template_key = cls._get_template_key(request_type, requirement_id, template_variant)
        
        # Generate token
        from email_service import generate_secure_action_token
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expiry_days)
        due_at = now + timedelta(days=due_days)
        
        token = generate_secure_action_token(
            person_id=person_id,
            person_type=person_type,
            action_type=REQUEST_TYPE_ACTIONS.get(request_type, "upload_document"),
            requirement_id=requirement_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            expiry_hours=expiry_days * 24
        )
        
        # Extract token ID (jti) from token
        import jwt
        from email_service import JWT_SECRET
        token_payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        token_id = token_payload["jti"]
        
        # Create request record
        request = EmailRequest(
            id=str(uuid.uuid4()),
            person_id=person_id,
            person_type=person_type,
            requirement_id=requirement_id,
            request_type=request_type,
            template_key=template_key,
            token_id=token_id,
            status=RequestStatus.PENDING_SEND,
            created_at=now.isoformat(),
            due_at=due_at.isoformat(),
            expires_at=expires_at.isoformat(),
            next_reminder_at=(now + timedelta(days=REMINDER_SCHEDULE["first_reminder"])).isoformat(),
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            recipient_email=recipient["email"],
        )
        
        # Add reference to superseded request if this is a resend
        request_dict = request.to_dict()
        if superseded_request_id:
            request_dict["supersedes_request_id"] = superseded_request_id
            request_dict["is_resend"] = True
        
        # Store request
        await cls._db.email_requests.insert_one(request_dict)
        
        # Track creation event
        event_details = {}
        if is_resend:
            event_details["is_resend"] = True
            event_details["superseded_request_id"] = superseded_request_id
        
        await cls._track_event(
            request.id,
            EventType.CREATED,
            actor_id=admin_id,
            actor_type="admin" if admin_id else "system",
            details=event_details if event_details else None
        )
        
        # Send email if requested
        if send_immediately:
            send_result = await cls._send_request_email(request, recipient, context, token)
            if send_result["status"] == "sent":
                request.status = RequestStatus.SENT
                request.sent_at = datetime.now(timezone.utc).isoformat()
                request.email_log_id = send_result.get("log_id")
                await cls._update_request(request.id, {
                    "status": RequestStatus.SENT.value,
                    "sent_at": request.sent_at,
                    "email_log_id": request.email_log_id
                })
                await cls._track_event(request.id, EventType.SENT)
                
                # Return 'resent' status if this was a resend operation
                final_status = "resent" if is_resend else "sent"
                return {
                    "status": final_status, 
                    "request_id": request.id, 
                    "due_date": request.due_at,
                    "superseded_request_id": superseded_request_id
                }
            else:
                request.status = RequestStatus.FAILED
                request.failure_reason = send_result.get("error", "Unknown send error")
                await cls._update_request(request.id, {
                    "status": RequestStatus.FAILED.value,
                    "failure_reason": request.failure_reason
                })
                await cls._track_event(
                    request.id, 
                    EventType.SEND_FAILED,
                    details={"error": request.failure_reason}
                )
                return {"status": "send_failed", "request_id": request.id, "error": request.failure_reason}
        
        return {"status": "created", "request_id": request.id}
    
    @classmethod
    async def _check_duplicate(
        cls,
        person_id: str,
        person_type: str,
        requirement_id: Optional[str],
        request_type: RequestType,
        related_entity_type: Optional[str],
        related_entity_id: Optional[str]
    ) -> Dict[str, Any]:
        """Check for existing active request for same person + requirement + type"""
        active_statuses = [
            RequestStatus.PENDING_SEND.value,
            RequestStatus.SENT.value,
            RequestStatus.OPENED.value,
            RequestStatus.CLICKED.value,
            RequestStatus.ACTION_STARTED.value,
        ]
        
        query = {
            "person_id": person_id,
            "person_type": person_type,
            "request_type": request_type.value,
            "status": {"$in": active_statuses}
        }
        
        if requirement_id:
            query["requirement_id"] = requirement_id
        if related_entity_type:
            query["related_entity_type"] = related_entity_type
        if related_entity_id:
            query["related_entity_id"] = related_entity_id
        
        existing = await cls._db.email_requests.find_one(query, {"_id": 0})
        
        return {
            "has_duplicate": existing is not None,
            "existing_request_id": existing["id"] if existing else None
        }
    
    @classmethod
    async def _supersede_request(
        cls,
        request_id: str,
        admin_id: Optional[str] = None
    ) -> bool:
        """
        Supersede an existing request when a resend is triggered.
        Marks the old request as superseded and tracks the event.
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Update the old request status to superseded
        result = await cls._db.email_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": RequestStatus.SUPERSEDED.value,
                "resolved_at": now,
                "superseded_at": now,
                "superseded_by_admin": admin_id
            }}
        )
        
        # Track the superseded event
        await cls._track_event(
            request_id,
            EventType.SUPERSEDED,
            actor_id=admin_id,
            actor_type="admin" if admin_id else "system",
            details={"reason": "Replaced by resend operation"}
        )
        
        logger.info(f"Request {request_id} superseded by admin {admin_id}")
        return result.modified_count > 0
    
    @classmethod
    async def _check_requirement_satisfied(
        cls,
        person_id: str,
        person_type: str,
        requirement_id: str,
        request_type: RequestType
    ) -> bool:
        """Check if the underlying requirement is already satisfied"""
        if request_type == RequestType.UPLOAD_DOCUMENT:
            # Check compliance_status for uploaded + verified
            status = await cls._db.compliance_status.find_one({
                "employee_id": person_id,
                "requirement_id": requirement_id,
                "verified": True
            })
            return status is not None
        
        elif request_type == RequestType.EXPLAIN_GAP:
            # Check if gap has explanation
            employee = await cls._db.employees.find_one({"id": person_id}, {"_id": 0})
            if employee:
                for job in employee.get("employment_history", []):
                    gap = job.get("gap_after", {})
                    if gap.get("gap_id") == requirement_id and gap.get("explanation"):
                        return True
            return False
        
        elif request_type in [RequestType.REVIEW_REFERENCE, RequestType.VERIFY_REFERENCE]:
            # Check if reference is verified
            employee = await cls._db.employees.find_one({"id": person_id}, {"_id": 0})
            if employee:
                # requirement_id might be "reference_1" or "reference_2"
                ref_num = requirement_id.split("_")[-1] if requirement_id else "1"
                return employee.get(f"reference_{ref_num}_verified", False)
            return False
        
        return False
    
    @classmethod
    async def _get_recipient(cls, person_id: str, person_type: str) -> Optional[Dict[str, Any]]:
        """Get recipient details from existing data"""
        if person_type == "employee":
            employee = await cls._db.employees.find_one({"id": person_id}, {"_id": 0})
            if employee:
                return {
                    "email": employee.get("email"),
                    "name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
                    "first_name": employee.get("first_name"),
                    "last_name": employee.get("last_name")
                }
        # Future: handle applicants
        return None
    
    @classmethod
    def _get_template_key(
        cls,
        request_type: RequestType,
        requirement_id: Optional[str],
        variant: str
    ) -> str:
        """Get the appropriate template key for the request type"""
        templates = REQUEST_TYPE_TEMPLATES.get(request_type, {})
        
        # Check for requirement-specific template
        if requirement_id and requirement_id in templates:
            return templates[requirement_id]
        
        # Check for variant
        if variant in templates:
            return templates[variant]
        
        # Fall back to default
        return templates.get("default", "documents.missing_mandatory")
    
    @classmethod
    async def _send_request_email(
        cls,
        request: EmailRequest,
        recipient: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        token: str
    ) -> Dict[str, Any]:
        """Send the email via EmailService"""
        from email_service import EmailService, PORTAL_URL
        
        # Core compliance requirement names (readable mapping)
        CORE_REQUIREMENT_NAMES = {
            "right_to_work": "Right to Work",
            "identity": "Identity Documents",
            "dbs": "DBS Certificate",
            "dbs_certificate": "DBS Certificate",
            "proof_of_address": "Proof of Address",
            "cv": "CV / Resume",
            "application_form": "Application Form",
            "references": "Employment References",
            "health_questionnaire": "Health Questionnaire",
            "training": "Training Records",
        }
        
        CORE_REQUIREMENT_CATEGORIES = {
            "right_to_work": "Right to Work",
            "identity": "Identity Verification",
            "dbs": "DBS Checks",
            "dbs_certificate": "DBS Checks",
            "proof_of_address": "Address Verification",
            "cv": "Recruitment Record",
            "application_form": "Recruitment Record",
            "references": "References",
            "health_questionnaire": "Health & Safety",
            "training": "Training",
        }
        
        # Build base context
        email_context = context or {}
        email_context["employee_name"] = recipient.get("name", "")
        email_context["first_name"] = recipient.get("first_name", "")
        
        # CRITICAL: Get document/requirement details for template variables
        requirement_id = request.requirement_id
        if requirement_id:
            # First check core requirement names
            if requirement_id in CORE_REQUIREMENT_NAMES:
                email_context["document_name"] = CORE_REQUIREMENT_NAMES[requirement_id]
                email_context["category"] = CORE_REQUIREMENT_CATEGORIES.get(requirement_id, "Compliance Documents")
            else:
                # Try to get document type info from database
                doc_type = await cls._db.document_types.find_one(
                    {"id": requirement_id}, 
                    {"_id": 0, "name": 1, "category": 1}
                )
                if doc_type:
                    email_context["document_name"] = doc_type.get("name", requirement_id)
                    email_context["category"] = doc_type.get("category", "Compliance Documents")
                else:
                    # Fallback: Format requirement_id as readable name
                    formatted_name = requirement_id.replace("_", " ").title()
                    email_context["document_name"] = formatted_name
                    email_context["category"] = "Compliance Documents"
        else:
            email_context["document_name"] = "Required Document"
            email_context["category"] = "Compliance Documents"
        
        # Build action link with token
        action_type = REQUEST_TYPE_ACTIONS.get(request.request_type, "upload_document")
        
        # Use correct path based on person type
        if request.person_type == "applicant":
            # For applicants, use public upload page
            path = f"/upload-document?token={token}&request_id={request.id}"
        else:
            # For employees, also use public upload page (no login required)
            # This allows employees to upload documents directly from email links
            path = f"/upload-document?token={token}&request_id={request.id}"
        
        email_context["action_link"] = f"{PORTAL_URL}{path}"
        email_context["admin_link"] = f"{PORTAL_URL}/portal/employees/{request.person_id}"
        
        result = await EmailService.send_template(
            template_key=request.template_key,
            recipient_email=request.recipient_email,
            recipient_type="employee",
            context=email_context,
            employee_id=request.person_id if request.person_type == "employee" else None,
            requirement_id=request.requirement_id,
            related_entity_type=request.related_entity_type,
            related_entity_id=request.related_entity_id
        )
        
        return result
    
    # -------------------------------------------------------------------------
    # EVENT TRACKING
    # -------------------------------------------------------------------------
    
    @classmethod
    async def track_event(
        cls,
        request_id: str,
        event_type: EventType,
        actor_id: Optional[str] = None,
        actor_type: str = "system",
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track an event on a request.
        
        Updates request status based on event type.
        """
        request = await cls.get_request(request_id)
        if not request:
            return {"status": "error", "reason": "Request not found"}
        
        # Track the event
        await cls._track_event(request_id, event_type, actor_id, actor_type, details)
        
        # Update request status based on event
        status_updates = {
            EventType.OPENED: RequestStatus.OPENED,
            EventType.CLICKED: RequestStatus.CLICKED,
            EventType.ACTION_STARTED: RequestStatus.ACTION_STARTED,
            EventType.SUBMITTED: RequestStatus.SUBMITTED,
            EventType.COMPLETED: RequestStatus.COMPLETED,
            EventType.EXPIRED: RequestStatus.EXPIRED,
            EventType.CANCELLED: RequestStatus.CANCELLED,
        }
        
        new_status = status_updates.get(event_type)
        if new_status:
            updates = {"status": new_status.value}
            
            # Set resolved_at for terminal statuses
            if new_status in [RequestStatus.COMPLETED, RequestStatus.EXPIRED, RequestStatus.CANCELLED]:
                updates["resolved_at"] = datetime.now(timezone.utc).isoformat()
            
            await cls._update_request(request_id, updates)
        
        return {"status": "tracked", "event_type": event_type.value}
    
    @classmethod
    async def _track_event(
        cls,
        request_id: str,
        event_type: EventType,
        actor_id: Optional[str] = None,
        actor_type: str = "system",
        details: Optional[Dict[str, Any]] = None
    ):
        """Internal event tracking - stores in request_events collection"""
        event = RequestEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor_id=actor_id,
            actor_type=actor_type,
            details=details
        )
        
        await cls._db.request_events.insert_one(event.to_dict())
    
    # -------------------------------------------------------------------------
    # TOKEN HANDLING
    # -------------------------------------------------------------------------
    
    @classmethod
    async def validate_and_use_token(
        cls,
        token: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a token and mark it as used.
        
        Returns request details if valid, error otherwise.
        """
        from email_service import verify_secure_action_token
        
        # Verify JWT
        token_data = verify_secure_action_token(token)
        if not token_data:
            return {"status": "error", "reason": "Invalid or expired token"}
        
        # Find the request by token_id (jti)
        import jwt
        from email_service import JWT_SECRET
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            token_id = payload.get("jti")
        except:
            return {"status": "error", "reason": "Invalid token format"}
        
        # Find request
        request = await cls._db.email_requests.find_one({"token_id": token_id}, {"_id": 0})
        if not request:
            # Token is valid JWT but no matching request - allow action but log
            logger.warning(f"Valid token with no matching request: {token_id}")
            return {
                "status": "valid_no_request",
                "token_data": {
                    "person_id": token_data.person_id,
                    "person_type": token_data.person_type,
                    "action_type": token_data.action_type,
                    "requirement_id": token_data.requirement_id,
                }
            }
        
        # Check request status
        terminal_statuses = [
            RequestStatus.COMPLETED.value,
            RequestStatus.EXPIRED.value,
            RequestStatus.CANCELLED.value,
            RequestStatus.SUPERSEDED.value,
        ]
        
        if request["status"] in terminal_statuses:
            await cls._track_event(
                request["id"],
                EventType.TOKEN_EXPIRED,
                details={"reason": f"Request already {request['status']}"}
            )
            return {
                "status": "error",
                "reason": f"Request already {request['status']}",
                "request_status": request["status"]
            }
        
        # Track token use
        await cls._track_event(request["id"], EventType.TOKEN_USED)
        
        # Update status to clicked if just sent
        if request["status"] == RequestStatus.SENT.value:
            await cls._update_request(request["id"], {"status": RequestStatus.CLICKED.value})
        
        return {
            "status": "valid",
            "request_id": request["id"],
            "request": EmailRequest.from_dict(request),
            "token_data": {
                "person_id": token_data.person_id,
                "person_type": token_data.person_type,
                "action_type": token_data.action_type,
                "requirement_id": token_data.requirement_id,
                "related_entity_type": token_data.related_entity_type,
                "related_entity_id": token_data.related_entity_id,
            }
        }
    
    # -------------------------------------------------------------------------
    # SUBMISSION LINKING
    # -------------------------------------------------------------------------
    
    @classmethod
    async def link_submission(
        cls,
        request_id: str,
        submission_id: str,
        submission_type: str,
        actor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Link a submission to a request.
        
        This marks the request as submitted but does NOT mark the requirement
        as complete - that requires admin verification.
        """
        request = await cls.get_request(request_id)
        if not request:
            return {"status": "error", "reason": "Request not found"}
        
        # Update request with submission link
        await cls._update_request(request_id, {
            "submission_id": submission_id,
            "submission_type": submission_type,
            "status": RequestStatus.SUBMITTED.value
        })
        
        # Track submission event
        await cls._track_event(
            request_id,
            EventType.SUBMITTED,
            actor_id=actor_id,
            actor_type="employee",
            details={"submission_id": submission_id, "submission_type": submission_type}
        )
        
        return {"status": "linked", "request_id": request_id}
    
    @classmethod
    async def mark_completed(
        cls,
        request_id: str,
        admin_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a request as completed (admin action after verification).
        
        This is separate from the underlying requirement verification which
        happens through the portal's normal flows.
        """
        request = await cls.get_request(request_id)
        if not request:
            return {"status": "error", "reason": "Request not found"}
        
        await cls._update_request(request_id, {
            "status": RequestStatus.COMPLETED.value,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": notes
        })
        
        await cls._track_event(
            request_id,
            EventType.COMPLETED,
            actor_id=admin_id,
            actor_type="admin",
            details={"notes": notes}
        )
        
        return {"status": "completed", "request_id": request_id}
    
    # -------------------------------------------------------------------------
    # REMINDER PROCESSING
    # -------------------------------------------------------------------------
    
    @classmethod
    async def process_reminders(cls) -> Dict[str, Any]:
        """
        Process scheduled reminders for all active requests.
        
        Respects:
        - Do not send if request already resolved
        - Do not send if requirement already satisfied
        - Follow reminder schedule (3, 7, 14 days)
        """
        now = datetime.now(timezone.utc)
        
        # Find requests due for reminder
        due_requests = await cls._db.email_requests.find({
            "status": {"$in": [
                RequestStatus.SENT.value,
                RequestStatus.OPENED.value,
                RequestStatus.CLICKED.value,
                RequestStatus.ACTION_STARTED.value
            ]},
            "next_reminder_at": {"$lte": now.isoformat()}
        }, {"_id": 0}).to_list(100)
        
        results = {"sent": 0, "skipped_satisfied": 0, "skipped_expired": 0, "failed": 0}
        
        for req_data in due_requests:
            request = EmailRequest.from_dict(req_data)
            
            # Check if expired
            if request.expires_at:
                expires = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
                if expires < now:
                    await cls._update_request(request.id, {
                        "status": RequestStatus.EXPIRED.value,
                        "resolved_at": now.isoformat()
                    })
                    await cls._track_event(request.id, EventType.EXPIRED)
                    results["skipped_expired"] += 1
                    continue
            
            # Check if requirement already satisfied
            if request.requirement_id:
                is_satisfied = await cls._check_requirement_satisfied(
                    request.person_id,
                    request.person_type,
                    request.requirement_id,
                    RequestType(request.request_type)
                )
                if is_satisfied:
                    await cls._update_request(request.id, {
                        "status": RequestStatus.COMPLETED.value,
                        "resolved_at": now.isoformat()
                    })
                    await cls._track_event(
                        request.id,
                        EventType.COMPLETED,
                        actor_type="system",
                        details={"reason": "Requirement satisfied externally"}
                    )
                    results["skipped_satisfied"] += 1
                    continue
            
            # Determine reminder type
            reminder_count = request.reminder_count
            if reminder_count == 0:
                reminder_type = "first_reminder"
                next_days = REMINDER_SCHEDULE["second_reminder"]
            elif reminder_count == 1:
                reminder_type = "second_reminder"
                next_days = REMINDER_SCHEDULE["escalation"]
            else:
                reminder_type = "escalation"
                next_days = 7  # Weekly escalations after that
            
            # Get recipient
            recipient = await cls._get_recipient(request.person_id, request.person_type)
            if not recipient:
                results["failed"] += 1
                continue
            
            # Send reminder
            from email_service import generate_secure_action_token
            
            token = generate_secure_action_token(
                person_id=request.person_id,
                person_type=request.person_type,
                action_type=REQUEST_TYPE_ACTIONS.get(RequestType(request.request_type), "upload_document"),
                requirement_id=request.requirement_id,
                related_entity_type=request.related_entity_type,
                related_entity_id=request.related_entity_id,
                expiry_hours=next_days * 24
            )
            
            context = {"reminder_number": reminder_count + 1, "reminder_type": reminder_type}
            send_result = await cls._send_request_email(request, recipient, context, token)
            
            if send_result["status"] == "sent":
                await cls._update_request(request.id, {
                    "reminder_count": reminder_count + 1,
                    "last_reminder_at": now.isoformat(),
                    "next_reminder_at": (now + timedelta(days=next_days)).isoformat()
                })
                
                event_type = EventType.ESCALATION_SENT if reminder_type == "escalation" else EventType.REMINDER_SENT
                await cls._track_event(
                    request.id,
                    event_type,
                    details={"reminder_type": reminder_type, "reminder_count": reminder_count + 1}
                )
                results["sent"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    # -------------------------------------------------------------------------
    # REQUEST MANAGEMENT
    # -------------------------------------------------------------------------
    
    @classmethod
    async def get_request(cls, request_id: str) -> Optional[EmailRequest]:
        """Get a request by ID"""
        data = await cls._db.email_requests.find_one({"id": request_id}, {"_id": 0})
        return EmailRequest.from_dict(data) if data else None
    
    @classmethod
    async def get_requests_for_person(
        cls,
        person_id: str,
        person_type: str = "employee",
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all requests for a person"""
        query = {"person_id": person_id, "person_type": person_type}
        if status:
            query["status"] = status
        
        requests = await cls._db.email_requests.find(
            query, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return requests
    
    @classmethod
    async def get_pending_requests(cls, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all pending/active requests for admin view"""
        active_statuses = [
            RequestStatus.PENDING_SEND.value,
            RequestStatus.SENT.value,
            RequestStatus.OPENED.value,
            RequestStatus.CLICKED.value,
            RequestStatus.ACTION_STARTED.value,
            RequestStatus.SUBMITTED.value,
        ]
        
        requests = await cls._db.email_requests.find(
            {"status": {"$in": active_statuses}},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return requests
    
    @classmethod
    async def cancel_request(
        cls,
        request_id: str,
        admin_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a request"""
        request = await cls.get_request(request_id)
        if not request:
            return {"status": "error", "reason": "Request not found"}
        
        # Can't cancel already resolved requests
        terminal_statuses = [RequestStatus.COMPLETED, RequestStatus.EXPIRED, RequestStatus.CANCELLED]
        if request.status in terminal_statuses:
            return {"status": "error", "reason": f"Cannot cancel {request.status.value} request"}
        
        await cls._update_request(request_id, {
            "status": RequestStatus.CANCELLED.value,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": reason
        })
        
        await cls._track_event(
            request_id,
            EventType.CANCELLED,
            actor_id=admin_id,
            actor_type="admin",
            details={"reason": reason}
        )
        
        return {"status": "cancelled", "request_id": request_id}
    
    @classmethod
    async def resend_request(
        cls,
        request_id: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """Resend email for an existing request"""
        request = await cls.get_request(request_id)
        if not request:
            return {"status": "error", "reason": "Request not found"}
        
        # Only resend for active requests
        active_statuses = [
            RequestStatus.SENT,
            RequestStatus.OPENED,
            RequestStatus.CLICKED,
            RequestStatus.ACTION_STARTED,
        ]
        if request.status not in active_statuses:
            return {"status": "error", "reason": f"Cannot resend {request.status.value} request"}
        
        # Get recipient
        recipient = await cls._get_recipient(request.person_id, request.person_type)
        if not recipient:
            return {"status": "error", "reason": "Recipient not found"}
        
        # Generate new token
        from email_service import generate_secure_action_token
        token = generate_secure_action_token(
            person_id=request.person_id,
            person_type=request.person_type,
            action_type=REQUEST_TYPE_ACTIONS.get(request.request_type, "upload_document"),
            requirement_id=request.requirement_id,
            related_entity_type=request.related_entity_type,
            related_entity_id=request.related_entity_id,
            expiry_hours=DEFAULT_REQUEST_EXPIRY_DAYS * 24
        )
        
        # Send
        send_result = await cls._send_request_email(request, recipient, {"resend": True}, token)
        
        if send_result["status"] == "sent":
            await cls._track_event(
                request_id,
                EventType.SENT,
                actor_id=admin_id,
                actor_type="admin",
                details={"resend": True}
            )
            return {"status": "sent", "request_id": request_id}
        else:
            return {"status": "failed", "error": send_result.get("error")}
    
    @classmethod
    async def supersede_request(
        cls,
        old_request_id: str,
        new_request_id: str,
        admin_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark an old request as superseded by a new one"""
        await cls._update_request(old_request_id, {
            "status": RequestStatus.SUPERSEDED.value,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "admin_notes": f"Superseded by request {new_request_id}"
        })
        
        await cls._track_event(
            old_request_id,
            EventType.SUPERSEDED,
            actor_id=admin_id,
            actor_type="admin" if admin_id else "system",
            details={"new_request_id": new_request_id}
        )
        
        return {"status": "superseded", "old_request_id": old_request_id}
    
    @classmethod
    async def get_request_events(cls, request_id: str) -> List[Dict[str, Any]]:
        """Get all events for a request"""
        events = await cls._db.request_events.find(
            {"request_id": request_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(100)
        
        return events
    
    @classmethod
    async def _update_request(cls, request_id: str, updates: Dict[str, Any]):
        """Update a request document"""
        await cls._db.email_requests.update_one(
            {"id": request_id},
            {"$set": updates}
        )
    
    # -------------------------------------------------------------------------
    # EXPIRY PROCESSING
    # -------------------------------------------------------------------------
    
    @classmethod
    async def process_expired_requests(cls) -> Dict[str, Any]:
        """Mark expired requests and clean up"""
        now = datetime.now(timezone.utc)
        
        # Find expired but not yet marked
        expired = await cls._db.email_requests.find({
            "status": {"$nin": [
                RequestStatus.COMPLETED.value,
                RequestStatus.EXPIRED.value,
                RequestStatus.CANCELLED.value,
                RequestStatus.SUPERSEDED.value,
            ]},
            "expires_at": {"$lt": now.isoformat()}
        }, {"_id": 0}).to_list(100)
        
        count = 0
        for req_data in expired:
            await cls._update_request(req_data["id"], {
                "status": RequestStatus.EXPIRED.value,
                "resolved_at": now.isoformat()
            })
            await cls._track_event(req_data["id"], EventType.EXPIRED)
            count += 1
        
        return {"expired_count": count}


# =============================================================================
# 5. FAILURE HANDLING
# =============================================================================

class RequestFailureHandler:
    """
    Handles various failure scenarios with explicit logging.
    No silent failures allowed.
    """
    
    @staticmethod
    async def handle_send_failure(
        request_id: str,
        error: str,
        db
    ):
        """Handle email send failure"""
        await db.email_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": RequestStatus.FAILED.value,
                "failure_reason": error
            }}
        )
        
        event = RequestEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=EventType.SEND_FAILED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor_type="system",
            details={"error": error}
        )
        await db.request_events.insert_one(event.to_dict())
        
        logger.error(f"Email request {request_id} send failed: {error}")
    
    @staticmethod
    async def handle_expired_token(
        request_id: str,
        token_id: str,
        db
    ):
        """Handle expired token access attempt"""
        event = RequestEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=EventType.TOKEN_EXPIRED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor_type="system",
            details={"token_id": token_id}
        )
        await db.request_events.insert_one(event.to_dict())
        
        logger.warning(f"Expired token access attempt for request {request_id}")
    
    @staticmethod
    async def handle_duplicate_submission(
        request_id: str,
        existing_submission_id: str,
        db
    ):
        """Handle duplicate submission attempt"""
        event = RequestEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=EventType.DUPLICATE_BLOCKED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor_type="system",
            details={
                "type": "duplicate_submission",
                "existing_submission_id": existing_submission_id
            }
        )
        await db.request_events.insert_one(event.to_dict())
        
        logger.warning(f"Duplicate submission blocked for request {request_id}")
    
    @staticmethod
    async def handle_missing_linkage(
        request_id: str,
        missing_field: str,
        db
    ):
        """Handle submission with missing linkage"""
        event = RequestEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=EventType.SEND_FAILED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor_type="system",
            details={
                "type": "missing_linkage",
                "missing_field": missing_field
            }
        )
        await db.request_events.insert_one(event.to_dict())
        
        logger.error(f"Missing linkage for request {request_id}: {missing_field}")
