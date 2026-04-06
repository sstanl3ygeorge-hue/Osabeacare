# Audit Trail Service
# CQC-compliant audit logging for all compliance actions

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Audit action types for CQC compliance."""
    # Document actions
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    DOCUMENT_REVIEWED = "DOCUMENT_REVIEWED"
    DOCUMENT_APPROVED = "DOCUMENT_APPROVED"
    DOCUMENT_REJECTED = "DOCUMENT_REJECTED"
    
    # Verification actions
    CHECK_RECORDED = "CHECK_RECORDED"
    CHECK_VERIFIED = "CHECK_VERIFIED"
    CHECK_FAILED = "CHECK_FAILED"
    CHECK_UPDATED = "CHECK_UPDATED"
    CHECK_SUPERSEDED = "CHECK_SUPERSEDED"
    
    # Status changes
    STATUS_CHANGED = "STATUS_CHANGED"
    WORK_READINESS_CHANGED = "WORK_READINESS_CHANGED"
    COMPLIANCE_STATUS_CHANGED = "COMPLIANCE_STATUS_CHANGED"
    
    # Employee actions
    EMPLOYEE_CREATED = "EMPLOYEE_CREATED"
    EMPLOYEE_UPDATED = "EMPLOYEE_UPDATED"
    EMPLOYEE_STATUS_CHANGED = "EMPLOYEE_STATUS_CHANGED"
    
    # Reference actions
    REFERENCE_ADDED = "REFERENCE_ADDED"
    REFERENCE_REQUEST_SENT = "REFERENCE_REQUEST_SENT"
    REFERENCE_RECEIVED = "REFERENCE_RECEIVED"
    REFERENCE_VERIFIED = "REFERENCE_VERIFIED"
    
    # Training actions
    TRAINING_RECORDED = "TRAINING_RECORDED"
    TRAINING_EXPIRED = "TRAINING_EXPIRED"
    TRAINING_RENEWED = "TRAINING_RENEWED"
    
    # Health actions
    HEALTH_DECLARATION_SUBMITTED = "HEALTH_DECLARATION_SUBMITTED"
    HEALTH_DECLARATION_REVIEWED = "HEALTH_DECLARATION_REVIEWED"
    
    # System actions
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    BULK_ACTION_PERFORMED = "BULK_ACTION_PERFORMED"


class EntityType(str, Enum):
    """Entity types for audit logging."""
    EMPLOYEE = "employee"
    DOCUMENT = "document"
    RTW_CHECK = "rtw_check"
    DBS_CHECK = "dbs_check"
    IDENTITY_CHECK = "identity_check"
    ADDRESS_CHECK = "address_check"
    REFERENCE = "reference"
    TRAINING = "training"
    HEALTH_DECLARATION = "health_declaration"
    USER = "user"
    SYSTEM = "system"


class AuditLogEntry(BaseModel):
    """Audit log entry model."""
    id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}")
    
    # Who performed the action
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    
    # What action was performed
    action: AuditAction
    
    # What entity was affected
    entity_type: EntityType
    entity_id: str
    
    # Related employee (for easy querying)
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    
    # When
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Change details
    metadata: Dict[str, Any] = Field(default_factory=dict)
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    
    # Additional context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AuditTrailService:
    """
    Service for logging all compliance-related actions.
    
    CQC Requirements:
    - All document uploads must be logged
    - All verification decisions must be logged
    - All status changes must be logged
    - Logs must be immutable and timestamped
    - Logs must identify the user who performed the action
    """
    
    def __init__(self, db):
        self.db = db
        self.collection = db.audit_logs
    
    async def log(
        self,
        action: AuditAction,
        entity_type: EntityType,
        entity_id: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        employee_id: Optional[str] = None,
        employee_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Log an audit event.
        
        Returns:
            The audit log entry ID
        """
        entry = AuditLogEntry(
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            employee_id=employee_id,
            employee_name=employee_name,
            metadata=metadata or {},
            previous_state=previous_state,
            new_state=new_state,
            ip_address=ip_address,
            notes=notes
        )
        
        # Insert into MongoDB
        await self.collection.insert_one(entry.dict())
        
        return entry.id
    
    async def log_document_upload(
        self,
        document_id: str,
        employee_id: str,
        employee_name: str,
        requirement_type: str,
        filename: str,
        user_id: str,
        user_email: str,
        user_name: str,
        ip_address: Optional[str] = None
    ) -> str:
        """Log a document upload event."""
        return await self.log(
            action=AuditAction.DOCUMENT_UPLOADED,
            entity_type=EntityType.DOCUMENT,
            entity_id=document_id,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            employee_id=employee_id,
            employee_name=employee_name,
            metadata={
                "requirement_type": requirement_type,
                "filename": filename
            },
            ip_address=ip_address
        )
    
    async def log_verification_check(
        self,
        check_type: str,  # rtw, dbs, identity, address
        check_id: str,
        employee_id: str,
        employee_name: str,
        method: str,
        outcome: str,
        user_id: str,
        user_email: str,
        user_name: str,
        check_details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log a verification check event."""
        entity_type_map = {
            "rtw": EntityType.RTW_CHECK,
            "dbs": EntityType.DBS_CHECK,
            "identity": EntityType.IDENTITY_CHECK,
            "address": EntityType.ADDRESS_CHECK
        }
        
        return await self.log(
            action=AuditAction.CHECK_VERIFIED if outcome == "verified" else AuditAction.CHECK_RECORDED,
            entity_type=entity_type_map.get(check_type, EntityType.DOCUMENT),
            entity_id=check_id,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            employee_id=employee_id,
            employee_name=employee_name,
            metadata={
                "check_type": check_type,
                "method": method,
                "outcome": outcome,
                **(check_details or {})
            },
            ip_address=ip_address
        )
    
    async def log_status_change(
        self,
        employee_id: str,
        employee_name: str,
        status_type: str,  # work_readiness, compliance_status
        previous_status: str,
        new_status: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> str:
        """Log a status change event."""
        return await self.log(
            action=AuditAction.WORK_READINESS_CHANGED if status_type == "work_readiness" else AuditAction.COMPLIANCE_STATUS_CHANGED,
            entity_type=EntityType.EMPLOYEE,
            entity_id=employee_id,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name or "System",
            employee_id=employee_id,
            employee_name=employee_name,
            previous_state={status_type: previous_status},
            new_state={status_type: new_status},
            notes=reason
        )
    
    async def log_reference_action(
        self,
        action: AuditAction,
        reference_id: str,
        employee_id: str,
        employee_name: str,
        referee_name: str,
        user_id: str,
        user_email: str,
        user_name: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a reference-related action."""
        return await self.log(
            action=action,
            entity_type=EntityType.REFERENCE,
            entity_id=reference_id,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            employee_id=employee_id,
            employee_name=employee_name,
            metadata={
                "referee_name": referee_name,
                **(details or {})
            }
        )
    
    async def get_employee_audit_trail(
        self,
        employee_id: str,
        limit: int = 100,
        skip: int = 0,
        action_filter: Optional[List[AuditAction]] = None
    ) -> List[Dict]:
        """Get audit trail for a specific employee.
        
        Searches both:
        - employee_id field (new format)
        - metadata.employee_id (legacy format for backwards compatibility)
        - entity_id when entity_type is employee
        """
        # Build query to search multiple locations for employee_id
        query = {
            "$or": [
                {"employee_id": employee_id},
                {"metadata.employee_id": employee_id},
                {"entity_id": employee_id, "entity_type": {"$in": ["employee", "EMPLOYEE"]}}
            ]
        }
        
        if action_filter:
            query["action"] = {"$in": [a.value for a in action_filter]}
        
        cursor = self.collection.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_audit_trail_by_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get audit trail for a specific entity."""
        cursor = self.collection.find(
            {"entity_type": entity_type.value, "entity_id": entity_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_recent_actions(
        self,
        limit: int = 50,
        action_filter: Optional[List[AuditAction]] = None
    ) -> List[Dict]:
        """Get recent audit actions across all entities."""
        query = {}
        if action_filter:
            query["action"] = {"$in": [a.value for a in action_filter]}
        
        cursor = self.collection.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def search_audit_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[EntityType] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict]:
        """Search audit logs with filters."""
        query = {}
        
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date
        
        if user_id:
            query["user_id"] = user_id
        if employee_id:
            query["employee_id"] = employee_id
        if action:
            query["action"] = action.value
        if entity_type:
            query["entity_type"] = entity_type.value
        
        cursor = self.collection.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)


# Singleton instance (will be initialized with db in server.py)
audit_service: Optional[AuditTrailService] = None


def get_audit_service() -> AuditTrailService:
    """Get the audit service instance."""
    global audit_service
    if audit_service is None:
        raise RuntimeError("Audit service not initialized")
    return audit_service


def init_audit_service(db) -> AuditTrailService:
    """Initialize the audit service with database connection."""
    global audit_service
    audit_service = AuditTrailService(db)
    return audit_service
