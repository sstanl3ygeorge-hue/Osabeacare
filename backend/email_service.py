"""
Email Service Architecture for Care Recruitment Portal
======================================================
Provides a scalable, reuse-first email foundation with:
- Purpose-based sender configuration
- Template registry with metadata
- Comprehensive audit logging
- Secure action links with JWT tokens
- Provider abstraction (Resend underneath)

Usage:
    from email_service import EmailService
    
    # Send using template
    await EmailService.send_template(
        template_key="recruitment.missing_proof_of_address",
        recipient_email="employee@example.com",
        recipient_type="employee",
        context={"employee_name": "John", ...},
        employee_id="emp-123",
        requirement_id="proof_of_address"
    )
"""

import os
import uuid
import asyncio
import logging
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import resend

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

PORTAL_URL = os.environ.get('PORTAL_URL', 'https://caretrust-portal.preview.emergentagent.com')
JWT_SECRET = os.environ.get('JWT_SECRET', 'osabea-care-jwt-secret-key-2024-secure')
ACTION_LINK_EXPIRY_HOURS = 72  # Default expiry for secure action links


# =============================================================================
# 1. SENDER CONFIGURATION
# =============================================================================

@dataclass
class SenderConfig:
    """Configuration for an email sender identity"""
    sender_key: str
    from_address: str
    from_name: str
    reply_to: str
    
    @property
    def from_header(self) -> str:
        """Returns formatted 'From' header: 'Name <email>'"""
        return f"{self.from_name} <{self.from_address}>"


# Sender Registry - Add new senders here as needed
SENDER_REGISTRY: Dict[str, SenderConfig] = {
    "recruitment": SenderConfig(
        sender_key="recruitment",
        from_address="recruitment@osabeacares.co.uk",
        from_name="Osabea Recruitment Team",
        reply_to="info@osabeacaresolutions.co.uk"
    ),
    # Future senders (inactive until configured):
    # "documents": SenderConfig(
    #     sender_key="documents",
    #     from_address="documents@osabeacares.co.uk",
    #     from_name="Osabea Documents Team",
    #     reply_to="info@osabeacaresolutions.co.uk"
    # ),
    # "training": SenderConfig(
    #     sender_key="training",
    #     from_address="training@osabeacares.co.uk",
    #     from_name="Osabea Training Team",
    #     reply_to="info@osabeacaresolutions.co.uk"
    # ),
    # "shifts": SenderConfig(
    #     sender_key="shifts",
    #     from_address="shifts@osabeacares.co.uk",
    #     from_name="Osabea Shifts Team",
    #     reply_to="info@osabeacaresolutions.co.uk"
    # ),
}

def get_sender(sender_key: str) -> SenderConfig:
    """Get sender configuration by key, falls back to recruitment"""
    return SENDER_REGISTRY.get(sender_key, SENDER_REGISTRY["recruitment"])


# =============================================================================
# 2. EMAIL CATEGORIES
# =============================================================================

class EmailCategory(str, Enum):
    """Email categories for organization and reporting"""
    RECRUITMENT = "recruitment"
    DOCUMENTS = "documents"
    TRAINING = "training"
    COMPLIANCE = "compliance"
    SHIFTS = "shifts"
    SYSTEM = "system"


# =============================================================================
# 3. TEMPLATE REGISTRY
# =============================================================================

@dataclass
class EmailTemplate:
    """Email template definition with metadata"""
    template_key: str
    category: EmailCategory
    sender_key: str
    subject_template: str
    employee_body_template: Optional[str] = None
    admin_body_template: Optional[str] = None
    requires_secure_link: bool = False
    secure_link_action: Optional[str] = None  # Action type for secure links
    description: str = ""
    
    def build_subject(self, context: Dict[str, Any]) -> str:
        """Build subject line from template and context"""
        try:
            return self.subject_template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing subject context key: {e}")
            return self.subject_template
    
    def build_body(self, recipient_type: str, context: Dict[str, Any]) -> str:
        """Build body from template and context"""
        template = self.employee_body_template if recipient_type == "employee" else self.admin_body_template
        if not template:
            template = self.admin_body_template or self.employee_body_template
        if not template:
            raise ValueError(f"No body template for {self.template_key} / {recipient_type}")
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing body context key: {e}")
            return template


# Base HTML wrapper for consistent styling
EMAIL_BASE_WRAPPER = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    {content}
    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0 20px;">
    <p style="font-size: 12px; color: #666;">
        This email was sent by Osabea Healthcare Solutions.<br>
        If you have questions, reply to this email or contact us at info@osabeacaresolutions.co.uk
    </p>
</div>
"""

# Template Registry - All email templates defined here
TEMPLATE_REGISTRY: Dict[str, EmailTemplate] = {
    # =========================================================================
    # RECRUITMENT TEMPLATES
    # =========================================================================
    "recruitment.missing_proof_of_address": EmailTemplate(
        template_key="recruitment.missing_proof_of_address",
        category=EmailCategory.RECRUITMENT,
        sender_key="recruitment",
        subject_template="Proof of Address Required - {employee_name}",
        requires_secure_link=True,
        secure_link_action="upload_proof_of_address",
        description="Request for proof of address documents (2 required)",
        employee_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">Proof of Address Required</h2>
        <p>Dear {employee_name},</p>
        <p>To complete your file, we require <strong>2 separate proof of address documents</strong> (NHS Standard).</p>
        <div style="background: #e8f4f8; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
            <strong>Current Status:</strong> {current_count}/2 documents uploaded<br>
            <strong>Accepted Documents:</strong><br>
            • Utility bill (gas, electric, water)<br>
            • Bank statement<br>
            • Council tax bill<br>
            • Tenancy agreement
        </div>
        <p>Please upload the required documents:</p>
        <p><a href="{action_link}" style="background: #0d6c6c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Upload Documents</a></p>
        <p style="margin-top: 20px;">Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        """,
        admin_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">Missing Proof of Address: {employee_name}</h2>
        <p><strong>{employee_name}</strong> has insufficient proof of address documents:</p>
        <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
            <strong>Required:</strong> 2 documents<br>
            <strong>Uploaded:</strong> {current_count}<br>
            <strong>Verified:</strong> {verified_count}
        </div>
        <p>The employee has been notified to upload additional documents.</p>
        <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee Profile</a></p>
        """
    ),
    
    "recruitment.reference_verification_required": EmailTemplate(
        template_key="recruitment.reference_verification_required",
        category=EmailCategory.RECRUITMENT,
        sender_key="recruitment",
        subject_template="Reference Verification Required - {employee_name}",
        requires_secure_link=True,
        secure_link_action="update_reference",
        description="Request to verify or update reference details",
        employee_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">Reference Verification Required</h2>
        <p>Dear {employee_name},</p>
        <p>Your reference from <strong>{reference_name}</strong> at <strong>{reference_company}</strong> requires verification.</p>
        <p>Please ensure your reference contact details are correct and that your referee is available to respond.</p>
        <div style="background: #e8f4f8; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
            <strong>Reference:</strong> {reference_name}<br>
            <strong>Company:</strong> {reference_company}
        </div>
        <p>If your referee has changed, please update your details:</p>
        <p><a href="{action_link}" style="background: #0d6c6c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Update Reference</a></p>
        <p style="margin-top: 20px;">Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        """,
        admin_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">Reference Pending: {employee_name}</h2>
        <p>Reference {reference_num} for <strong>{employee_name}</strong> requires verification:</p>
        <div style="background: #f8f9fa; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
            <strong>Referee:</strong> {reference_name}<br>
            <strong>Company:</strong> {reference_company}
        </div>
        <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Reference</a></p>
        """
    ),
    
    "recruitment.cv_gap_explanation_required": EmailTemplate(
        template_key="recruitment.cv_gap_explanation_required",
        category=EmailCategory.RECRUITMENT,
        sender_key="recruitment",
        subject_template="Employment Gap Requires Explanation - {employee_name}",
        requires_secure_link=True,
        secure_link_action="explain_cv_gap",
        description="Request explanation for employment history gap",
        employee_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">Employment Gap Detected</h2>
        <p>Dear {employee_name},</p>
        <p>We have identified a gap in your employment history that requires explanation:</p>
        <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
            <strong>Gap Period:</strong> {gap_start} to {gap_end}<br>
            <strong>Duration:</strong> {gap_days} days<br>
            <strong>Between:</strong> {previous_job} → {next_job}
        </div>
        <p>Please provide an explanation for this gap:</p>
        <p><a href="{action_link}" style="background: #0d6c6c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Explain Gap</a></p>
        <p>If you have questions, please contact your recruitment manager.</p>
        <p style="margin-top: 20px;">Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        """,
        admin_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">CV Gap Alert: {employee_name}</h2>
        <p>An employment gap has been detected for <strong>{employee_name}</strong>:</p>
        <div style="background: #f8f9fa; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
            <strong>Gap Period:</strong> {gap_start} to {gap_end}<br>
            <strong>Duration:</strong> {gap_days} days<br>
            <strong>Between:</strong> {previous_job} → {next_job}
        </div>
        <p>The employee has been notified to provide an explanation.</p>
        <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee Profile</a></p>
        """
    ),
    
    # =========================================================================
    # DOCUMENTS TEMPLATES (for future use)
    # =========================================================================
    "documents.expiring_60_days": EmailTemplate(
        template_key="documents.expiring_60_days",
        category=EmailCategory.DOCUMENTS,
        sender_key="recruitment",  # Using recruitment sender until documents sender activated
        subject_template="Document Expiring in 60 Days - {document_name}",
        requires_secure_link=True,
        secure_link_action="upload_document",
        description="60-day expiry warning for documents",
        employee_body_template="""
        <h2 style="color: #ffc107; margin-bottom: 20px;">Document Expiring Soon</h2>
        <p>Dear {employee_name},</p>
        <p>The following document will expire in <strong>60 days</strong>:</p>
        <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
            <strong>Document:</strong> {document_name}<br>
            <strong>Expiry Date:</strong> {expiry_date}
        </div>
        <p>Please renew this document and upload the new version before it expires.</p>
        <p><a href="{action_link}" style="background: #ffc107; color: #000; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Upload Renewal</a></p>
        <p style="margin-top: 20px;">Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        """,
        admin_body_template="""
        <h2 style="color: #ffc107; margin-bottom: 20px;">Expiry Alert (60 Days): {employee_name}</h2>
        <p>Document expiring for <strong>{employee_name}</strong>:</p>
        <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
            <strong>Document:</strong> {document_name}<br>
            <strong>Expiry Date:</strong> {expiry_date}
        </div>
        <p>The employee has been notified.</p>
        """
    ),
    
    "documents.expiring_30_days": EmailTemplate(
        template_key="documents.expiring_30_days",
        category=EmailCategory.DOCUMENTS,
        sender_key="recruitment",
        subject_template="URGENT: Document Expiring in 30 Days - {document_name}",
        requires_secure_link=True,
        secure_link_action="upload_document",
        description="30-day urgent expiry warning for documents",
        employee_body_template="""
        <h2 style="color: #dc3545; margin-bottom: 20px;">Urgent: Document Expiring Soon</h2>
        <p>Dear {employee_name},</p>
        <p>The following document will expire in <strong>30 days</strong>:</p>
        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
            <strong>Document:</strong> {document_name}<br>
            <strong>Expiry Date:</strong> {expiry_date}
        </div>
        <p><strong>Action Required:</strong> Please renew this document immediately to remain work-ready.</p>
        <p><a href="{action_link}" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Upload Renewal Now</a></p>
        <p style="margin-top: 20px;">Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        """,
        admin_body_template="""
        <h2 style="color: #dc3545; margin-bottom: 20px;">URGENT Expiry Alert (30 Days): {employee_name}</h2>
        <p>Document expiring soon for <strong>{employee_name}</strong>:</p>
        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
            <strong>Document:</strong> {document_name}<br>
            <strong>Expiry Date:</strong> {expiry_date}
        </div>
        <p>The employee has been notified urgently.</p>
        """
    ),
    
    "documents.missing_mandatory": EmailTemplate(
        template_key="documents.missing_mandatory",
        category=EmailCategory.DOCUMENTS,
        sender_key="recruitment",
        subject_template="Missing Required Document - {document_name}",
        requires_secure_link=True,
        secure_link_action="upload_document",
        description="Notification for missing mandatory document",
        employee_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">Missing Required Document</h2>
        <p>Dear {employee_name},</p>
        <p>We are missing the following mandatory document from your file:</p>
        <div style="background: #e8f4f8; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
            <strong>Document:</strong> {document_name}<br>
            <strong>Category:</strong> {category}
        </div>
        <p>Please upload this document to complete your requirements.</p>
        <p><a href="{action_link}" style="background: #0d6c6c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Upload Document</a></p>
        <p style="margin-top: 20px;">Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        """,
        admin_body_template="""
        <h2 style="color: #0d6c6c; margin-bottom: 20px;">Missing Document: {employee_name}</h2>
        <p><strong>{employee_name}</strong> is missing a mandatory document:</p>
        <div style="background: #f8f9fa; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
            <strong>Document:</strong> {document_name}<br>
            <strong>Category:</strong> {category}
        </div>
        <p>The employee has been notified.</p>
        """
    ),
    
    # =========================================================================
    # TRAINING TEMPLATES (for future use)
    # =========================================================================
    "training.expired": EmailTemplate(
        template_key="training.expired",
        category=EmailCategory.TRAINING,
        sender_key="recruitment",
        subject_template="Training Expired - Action Required - {training_name}",
        requires_secure_link=True,
        secure_link_action="upload_training_certificate",
        description="Notification for expired training certification",
        employee_body_template="""
        <h2 style="color: #dc3545; margin-bottom: 20px;">Training Expired</h2>
        <p>Dear {employee_name},</p>
        <p>Your training certification has <strong>expired</strong>:</p>
        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
            <strong>Training:</strong> {training_name}<br>
            <strong>Expired On:</strong> {expiry_date}
        </div>
        <p><strong>You cannot work until this training is renewed.</strong> Please complete the refresher training and upload your new certificate.</p>
        <p><a href="{action_link}" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Upload Certificate</a></p>
        <p style="margin-top: 20px;">Kind regards,<br><strong>Osabea Recruitment Team</strong></p>
        """,
        admin_body_template="""
        <h2 style="color: #dc3545; margin-bottom: 20px;">Training Expired: {employee_name}</h2>
        <p><strong>{employee_name}</strong> has expired training:</p>
        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
            <strong>Training:</strong> {training_name}<br>
            <strong>Expired On:</strong> {expiry_date}<br>
            <strong>Work Status:</strong> Employee should not be allocated shifts
        </div>
        <p><a href="{admin_link}" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Training Records</a></p>
        """
    ),
    
    # =========================================================================
    # COMPLIANCE/ADMIN TEMPLATES
    # =========================================================================
    "compliance.unverified_submission": EmailTemplate(
        template_key="compliance.unverified_submission",
        category=EmailCategory.COMPLIANCE,
        sender_key="recruitment",
        subject_template="Document Awaiting Verification - {document_name}",
        requires_secure_link=False,
        description="Admin notification for unverified document submission",
        admin_body_template="""
        <h2 style="color: #17a2b8; margin-bottom: 20px;">Document Awaiting Verification</h2>
        <p>A document has been uploaded and requires verification:</p>
        <div style="background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin: 15px 0;">
            <strong>Employee:</strong> {employee_name}<br>
            <strong>Document:</strong> {document_name}<br>
            <strong>Uploaded:</strong> {uploaded_at}
        </div>
        <p><a href="{admin_link}" style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Review & Verify</a></p>
        """
    ),
}

def get_template(template_key: str) -> Optional[EmailTemplate]:
    """Get template by key"""
    return TEMPLATE_REGISTRY.get(template_key)

def list_templates(category: Optional[EmailCategory] = None) -> List[EmailTemplate]:
    """List all templates, optionally filtered by category"""
    templates = list(TEMPLATE_REGISTRY.values())
    if category:
        templates = [t for t in templates if t.category == category]
    return templates


# =============================================================================
# 4. SECURE ACTION LINKS
# =============================================================================

@dataclass
class SecureActionToken:
    """Token payload for secure email action links"""
    person_id: str  # employee_id or applicant_id
    person_type: str  # "employee" or "applicant"
    action_type: str  # e.g., "upload_proof_of_address", "explain_cv_gap"
    requirement_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    expires_at: Optional[datetime] = None


def generate_secure_action_token(
    person_id: str,
    person_type: str,
    action_type: str,
    requirement_id: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    expiry_hours: int = ACTION_LINK_EXPIRY_HOURS
) -> str:
    """Generate a JWT token for secure email action links"""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    
    payload = {
        "person_id": person_id,
        "person_type": person_type,
        "action_type": action_type,
        "requirement_id": requirement_id,
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
        "exp": expires_at.timestamp(),
        "iat": datetime.now(timezone.utc).timestamp(),
        "jti": str(uuid.uuid4())  # Unique token ID
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_secure_action_token(token: str) -> Optional[SecureActionToken]:
    """Verify and decode a secure action token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return SecureActionToken(
            person_id=payload["person_id"],
            person_type=payload["person_type"],
            action_type=payload["action_type"],
            requirement_id=payload.get("requirement_id"),
            related_entity_type=payload.get("related_entity_type"),
            related_entity_id=payload.get("related_entity_id"),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Secure action token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid secure action token: {e}")
        return None


def build_secure_action_link(
    action_type: str,
    person_id: str,
    person_type: str = "employee",
    requirement_id: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    expiry_hours: int = ACTION_LINK_EXPIRY_HOURS
) -> str:
    """Build a complete secure action URL for email CTAs"""
    token = generate_secure_action_token(
        person_id=person_id,
        person_type=person_type,
        action_type=action_type,
        requirement_id=requirement_id,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        expiry_hours=expiry_hours
    )
    
    # Route based on action type
    if action_type in ["upload_proof_of_address", "upload_document", "upload_training_certificate"]:
        path = f"/portal/employees/{person_id}?tab=checklist&action={action_type}&token={token}"
    elif action_type == "explain_cv_gap":
        path = f"/portal/employees/{person_id}?tab=recruitment&action={action_type}&token={token}"
    elif action_type == "update_reference":
        path = f"/portal/employees/{person_id}?tab=recruitment&action={action_type}&token={token}"
    else:
        path = f"/portal/employees/{person_id}?action={action_type}&token={token}"
    
    return f"{PORTAL_URL}{path}"


# =============================================================================
# 5. EMAIL LOG MODEL
# =============================================================================

@dataclass
class EmailLogEntry:
    """Complete email log entry for audit trail"""
    id: str
    template_key: str
    email_type: str  # Alias for template_key for backwards compatibility
    category: str
    from_address: str
    from_name: str
    reply_to: str
    to_address: str
    subject: str
    
    # Person linkage
    employee_id: Optional[str] = None
    applicant_id: Optional[str] = None
    
    # Entity linkage
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    requirement_id: Optional[str] = None
    
    # Provider info
    provider: str = "resend"
    provider_message_id: Optional[str] = None
    
    # Status
    status: str = "pending"  # pending, sent, failed, bounced, delivered
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: Optional[str] = None
    sent_at: Optional[str] = None
    
    # Context (non-sensitive parts)
    context_summary: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "id": self.id,
            "template_key": self.template_key,
            "email_type": self.email_type,
            "category": self.category,
            "from_address": self.from_address,
            "from_name": self.from_name,
            "reply_to": self.reply_to,
            "to_address": self.to_address,
            "subject": self.subject,
            "employee_id": self.employee_id,
            "applicant_id": self.applicant_id,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "requirement_id": self.requirement_id,
            "provider": self.provider,
            "provider_message_id": self.provider_message_id,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "context_summary": self.context_summary
        }


# =============================================================================
# 6. EMAIL SERVICE (Provider Abstraction)
# =============================================================================

class EmailService:
    """
    Central email service that abstracts the email provider (Resend).
    All business logic should call this service, not Resend directly.
    """
    
    _db = None  # Set by server.py on startup
    
    @classmethod
    def set_db(cls, db):
        """Set the database reference (called from server.py)"""
        cls._db = db
    
    @classmethod
    async def send_template(
        cls,
        template_key: str,
        recipient_email: str,
        recipient_type: str,  # "employee" or "admin"
        context: Dict[str, Any],
        employee_id: Optional[str] = None,
        applicant_id: Optional[str] = None,
        requirement_id: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email using a registered template.
        
        Args:
            template_key: Key from TEMPLATE_REGISTRY
            recipient_email: Email address to send to
            recipient_type: "employee" or "admin"
            context: Template variables (employee_name, etc.)
            employee_id: Link to employee record
            applicant_id: Link to applicant record
            requirement_id: Link to compliance requirement
            related_entity_type: Type of related entity
            related_entity_id: ID of related entity
            
        Returns:
            Dict with status, email_id, log_id
        """
        # Validate provider is configured
        if not resend.api_key:
            logger.warning("Email service not configured (no API key)")
            return {"status": "skipped", "reason": "Email service not configured"}
        
        # Get template
        template = get_template(template_key)
        if not template:
            logger.error(f"Unknown template: {template_key}")
            return {"status": "error", "reason": f"Unknown template: {template_key}"}
        
        # Get sender config
        sender = get_sender(template.sender_key)
        
        # Build secure action link if required
        if template.requires_secure_link and template.secure_link_action:
            person_id = employee_id or applicant_id
            if person_id:
                context["action_link"] = build_secure_action_link(
                    action_type=template.secure_link_action,
                    person_id=person_id,
                    person_type="employee" if employee_id else "applicant",
                    requirement_id=requirement_id,
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id
                )
        
        # Build admin link (non-secure, just portal navigation)
        if employee_id:
            context["admin_link"] = f"{PORTAL_URL}/portal/employees/{employee_id}?tab=recruitment"
            context["portal_link"] = context.get("action_link") or context["admin_link"]
        
        # Build subject and body
        try:
            subject = template.build_subject(context)
            body = template.build_body(recipient_type, context)
            # Wrap in base template
            body = EMAIL_BASE_WRAPPER.format(content=body)
        except Exception as e:
            logger.error(f"Failed to build email content: {e}")
            return {"status": "error", "reason": f"Template error: {e}"}
        
        # Create log entry
        now = datetime.now(timezone.utc)
        log_entry = EmailLogEntry(
            id=str(uuid.uuid4()),
            template_key=template_key,
            email_type=template_key,
            category=template.category.value,
            from_address=sender.from_address,
            from_name=sender.from_name,
            reply_to=sender.reply_to,
            to_address=recipient_email,
            subject=subject,
            employee_id=employee_id,
            applicant_id=applicant_id,
            requirement_id=requirement_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            created_at=now.isoformat(),
            context_summary={k: v for k, v in context.items() if not k.endswith('_link') and k != 'action_link'}
        )
        
        # Send via Resend
        try:
            email_result = await asyncio.to_thread(resend.Emails.send, {
                "from": sender.from_header,
                "to": [recipient_email],
                "reply_to": sender.reply_to,
                "subject": subject,
                "html": body
            })
            
            # Update log with success
            log_entry.status = "sent"
            log_entry.sent_at = datetime.now(timezone.utc).isoformat()
            log_entry.provider_message_id = email_result.get("id")
            
            # Save to database
            if cls._db is not None:
                await cls._db.email_logs.insert_one(log_entry.to_dict())
            
            logger.info(f"Email sent: {template_key} to {recipient_email} (employee: {employee_id})")
            
            return {
                "status": "sent",
                "email_id": email_result.get("id"),
                "log_id": log_entry.id
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
            # Update log with failure
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            log_entry.sent_at = datetime.now(timezone.utc).isoformat()
            
            # Save failed attempt to database
            if cls._db is not None:
                await cls._db.email_logs.insert_one(log_entry.to_dict())
            
            return {
                "status": "failed",
                "error": str(e),
                "log_id": log_entry.id
            }
    
    @classmethod
    async def send_raw(
        cls,
        sender_key: str,
        recipient_email: str,
        subject: str,
        html_body: str,
        employee_id: Optional[str] = None,
        email_type: str = "custom"
    ) -> Dict[str, Any]:
        """
        Send a raw email without using a template.
        Use sparingly - prefer templates for consistency.
        """
        if not resend.api_key:
            return {"status": "skipped", "reason": "Email service not configured"}
        
        sender = get_sender(sender_key)
        now = datetime.now(timezone.utc)
        
        log_entry = EmailLogEntry(
            id=str(uuid.uuid4()),
            template_key="raw",
            email_type=email_type,
            category="system",
            from_address=sender.from_address,
            from_name=sender.from_name,
            reply_to=sender.reply_to,
            to_address=recipient_email,
            subject=subject,
            employee_id=employee_id,
            created_at=now.isoformat()
        )
        
        try:
            email_result = await asyncio.to_thread(resend.Emails.send, {
                "from": sender.from_header,
                "to": [recipient_email],
                "reply_to": sender.reply_to,
                "subject": subject,
                "html": html_body
            })
            
            log_entry.status = "sent"
            log_entry.sent_at = datetime.now(timezone.utc).isoformat()
            log_entry.provider_message_id = email_result.get("id")
            
            if cls._db is not None:
                await cls._db.email_logs.insert_one(log_entry.to_dict())
            
            return {"status": "sent", "email_id": email_result.get("id"), "log_id": log_entry.id}
            
        except Exception as e:
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            log_entry.sent_at = datetime.now(timezone.utc).isoformat()
            
            if cls._db is not None:
                await cls._db.email_logs.insert_one(log_entry.to_dict())
            
            return {"status": "failed", "error": str(e), "log_id": log_entry.id}
    
    @classmethod
    async def get_logs(
        cls,
        employee_id: Optional[str] = None,
        template_key: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Query email logs with filters"""
        if cls._db is None:
            return []
        
        query = {}
        if employee_id:
            query["employee_id"] = employee_id
        if template_key:
            query["template_key"] = template_key
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        
        logs = await cls._db.email_logs.find(query, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)
        return logs


# =============================================================================
# 7. MIGRATION HELPERS - Map old notification types to new templates
# =============================================================================

# Mapping from old NotificationType to new template_key
LEGACY_TYPE_TO_TEMPLATE = {
    "cv_gap_detected": "recruitment.cv_gap_explanation_required",
    "reference_not_verified": "recruitment.reference_verification_required",
    "reference_mismatch": "recruitment.reference_verification_required",  # Same template, different context
    "missing_proof_of_address": "recruitment.missing_proof_of_address",
    "document_expiring_60_days": "documents.expiring_60_days",
    "document_expiring_30_days": "documents.expiring_30_days",
    "training_expired": "training.expired",
    "missing_mandatory_item": "documents.missing_mandatory",
    "unverified_submission": "compliance.unverified_submission",
}

def get_template_for_legacy_type(legacy_type: str) -> Optional[str]:
    """Get new template key for legacy notification type"""
    return LEGACY_TYPE_TO_TEMPLATE.get(legacy_type)
