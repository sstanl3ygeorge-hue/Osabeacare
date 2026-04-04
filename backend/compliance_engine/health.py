# Occupational Health Models and Service
# CQC requirement for fitness to work declarations

import uuid
from datetime import datetime, timezone, date
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health declaration status."""
    FIT = "fit"                    # Cleared to work
    REQUIRES_REVIEW = "requires_review"  # Needs OH review
    NOT_FIT = "not_fit"            # Cannot work
    CONDITIONAL = "conditional"    # Fit with adjustments


class HealthDeclarationInput(BaseModel):
    """Input model for health declaration submission."""
    declaration_date: date
    declared_fit_to_work: bool
    conditions_disclosed: bool = False
    conditions_details: Optional[str] = None
    
    # Specific questions
    back_problems: bool = False
    skin_conditions: bool = False
    respiratory_conditions: bool = False
    infectious_diseases: bool = False
    mental_health: bool = False
    physical_limitations: bool = False
    medication: bool = False
    medication_details: Optional[str] = None
    
    # Immunizations
    hepatitis_b_vaccinated: Optional[bool] = None
    flu_vaccinated: Optional[bool] = None
    covid_vaccinated: Optional[bool] = None
    
    # Consent
    consent_to_oh_contact: bool = True
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    notes: Optional[str] = None


class HealthDeclaration(BaseModel):
    """Health declaration record."""
    id: str = Field(default_factory=lambda: f"health_{uuid.uuid4().hex[:12]}")
    employee_id: str
    
    # Declaration details
    declaration_date: date
    declared_fit_to_work: bool
    
    # Conditions
    conditions_disclosed: bool = False
    conditions_details: Optional[str] = None
    
    # Specific health questions
    health_questions: Dict[str, Any] = Field(default_factory=dict)
    
    # Immunizations
    immunizations: Dict[str, Any] = Field(default_factory=dict)
    
    # Emergency contact
    emergency_contact: Optional[Dict[str, str]] = None
    
    # Review
    status: HealthStatus = HealthStatus.REQUIRES_REVIEW
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Adjustments (if conditional)
    adjustments_required: Optional[str] = None
    
    # Linked document (if uploaded)
    document_id: Optional[str] = None
    
    # Timestamps
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True


class HealthDeclarationService:
    """Service for managing occupational health declarations."""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.health_declarations
    
    async def submit_declaration(
        self,
        employee_id: str,
        declaration: HealthDeclarationInput,
        submitted_by: Optional[str] = None
    ) -> HealthDeclaration:
        """Submit a new health declaration."""
        
        # Build health questions dict
        health_questions = {
            "back_problems": declaration.back_problems,
            "skin_conditions": declaration.skin_conditions,
            "respiratory_conditions": declaration.respiratory_conditions,
            "infectious_diseases": declaration.infectious_diseases,
            "mental_health": declaration.mental_health,
            "physical_limitations": declaration.physical_limitations,
            "medication": declaration.medication,
            "medication_details": declaration.medication_details
        }
        
        # Build immunizations dict
        immunizations = {
            "hepatitis_b": declaration.hepatitis_b_vaccinated,
            "flu": declaration.flu_vaccinated,
            "covid": declaration.covid_vaccinated
        }
        
        # Emergency contact
        emergency_contact = None
        if declaration.emergency_contact_name:
            emergency_contact = {
                "name": declaration.emergency_contact_name,
                "phone": declaration.emergency_contact_phone
            }
        
        # Determine initial status
        if declaration.declared_fit_to_work and not declaration.conditions_disclosed:
            status = HealthStatus.FIT
        else:
            status = HealthStatus.REQUIRES_REVIEW
        
        record = HealthDeclaration(
            employee_id=employee_id,
            declaration_date=declaration.declaration_date,
            declared_fit_to_work=declaration.declared_fit_to_work,
            conditions_disclosed=declaration.conditions_disclosed,
            conditions_details=declaration.conditions_details,
            health_questions=health_questions,
            immunizations=immunizations,
            emergency_contact=emergency_contact,
            status=status
        )
        
        await self.collection.insert_one(record.dict())
        
        return record
    
    async def review_declaration(
        self,
        declaration_id: str,
        status: HealthStatus,
        reviewed_by: str,
        review_notes: Optional[str] = None,
        adjustments_required: Optional[str] = None
    ) -> Optional[Dict]:
        """Review a health declaration."""
        result = await self.collection.find_one_and_update(
            {"id": declaration_id},
            {
                "$set": {
                    "status": status.value,
                    "reviewed_by": reviewed_by,
                    "reviewed_at": datetime.now(timezone.utc),
                    "review_notes": review_notes,
                    "adjustments_required": adjustments_required,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            return_document=True
        )
        
        if result:
            result.pop("_id", None)
        
        return result
    
    async def get_current_declaration(self, employee_id: str) -> Optional[Dict]:
        """Get the most recent health declaration for an employee."""
        result = await self.collection.find_one(
            {"employee_id": employee_id},
            sort=[("declaration_date", -1)],
            projection={"_id": 0}
        )
        return result
    
    async def get_declaration_history(
        self, 
        employee_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Get declaration history for an employee."""
        cursor = self.collection.find(
            {"employee_id": employee_id},
            {"_id": 0}
        ).sort("declaration_date", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_declarations_requiring_review(self, limit: int = 50) -> List[Dict]:
        """Get all declarations that need review."""
        cursor = self.collection.find(
            {"status": HealthStatus.REQUIRES_REVIEW.value},
            {"_id": 0}
        ).sort("submitted_at", 1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_employees_not_fit(self) -> List[Dict]:
        """Get employees marked as not fit to work."""
        pipeline = [
            {"$match": {"status": HealthStatus.NOT_FIT.value}},
            {"$sort": {"declaration_date": -1}},
            {"$group": {
                "_id": "$employee_id",
                "latest": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$latest"}},
            {"$project": {"_id": 0}}
        ]
        
        return await self.collection.aggregate(pipeline).to_list(100)


# Service instance
health_service: Optional[HealthDeclarationService] = None


def init_health_service(db) -> HealthDeclarationService:
    """Initialize the health declaration service."""
    global health_service
    health_service = HealthDeclarationService(db)
    return health_service


def get_health_service() -> HealthDeclarationService:
    """Get the health declaration service instance."""
    global health_service
    if health_service is None:
        raise RuntimeError("Health service not initialized")
    return health_service
