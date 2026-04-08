"""
Service Users (CQC Care Records) Routes Module

This module handles service user (client/patient) management endpoints including:
- Service user CRUD operations
- Document management organized by CQC-compliant sections
- Document verification

Service User File structure aligned with CQC expectations:
- Sections 1-10 based on standard care file requirements

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Service Users (CQC Care Records)"])


# ==================== CONSTANTS ====================

SERVICE_USER_SECTIONS = {
    "1_personal_referral": {
        "section_number": 1,
        "name": "Personal Info & Referral",
        "description": "Basic personal information, referral details, and initial contact",
        "document_types": ["referral_form", "initial_assessment", "personal_details"],
    },
    "2_consent_contracts": {
        "section_number": 2,
        "name": "Consent & Contracts",
        "description": "Service agreements, consent forms, and contractual documents",
        "document_types": ["service_agreement", "consent_form", "terms_conditions", "confidentiality"],
    },
    "3_assessments": {
        "section_number": 3,
        "name": "Assessments",
        "description": "Initial and ongoing needs assessments",
        "document_types": ["needs_assessment", "capacity_assessment", "mental_health_assessment"],
    },
    "4_care_plans": {
        "section_number": 4,
        "name": "Care Plans",
        "description": "Individual care plans and support plans",
        "document_types": ["care_plan", "support_plan", "daily_routine"],
    },
    "5_risk_assessments": {
        "section_number": 5,
        "name": "Risk Assessments",
        "description": "Risk assessments and management plans",
        "document_types": ["risk_assessment", "moving_handling_risk", "falls_risk", "medication_risk"],
    },
    "6_monitoring": {
        "section_number": 6,
        "name": "Monitoring",
        "description": "Daily logs, charts, and monitoring records",
        "document_types": ["daily_log", "fluid_chart", "food_chart", "repositioning_chart"],
    },
    "7_medication": {
        "section_number": 7,
        "name": "Medication",
        "description": "Medication records, MAR charts, and prescriptions",
        "document_types": ["mar_chart", "prescription", "medication_list", "prn_protocol"],
    },
    "8_health_visits": {
        "section_number": 8,
        "name": "Health Visits",
        "description": "GP visits, hospital appointments, and professional visits",
        "document_types": ["gp_visit", "hospital_letter", "district_nurse_visit", "specialist_report"],
    },
    "9_reviews": {
        "section_number": 9,
        "name": "Reviews",
        "description": "Care reviews, quality checks, and feedback",
        "document_types": ["care_review", "quality_check", "family_feedback", "annual_review"],
    },
    "10_correspondence": {
        "section_number": 10,
        "name": "Letters & Correspondence",
        "description": "General correspondence, letters, and other documents",
        "document_types": ["letter", "email_correspondence", "other"],
    },
}


# ==================== MODELS ====================

class ServiceUserCreate(BaseModel):
    """Create a new service user"""
    full_name: str
    date_of_birth: Optional[str] = None
    nhs_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postcode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    gp_name: Optional[str] = None
    gp_surgery: Optional[str] = None
    gp_phone: Optional[str] = None
    notes: Optional[str] = None


class ServiceUserUpdate(BaseModel):
    """Update service user details"""
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nhs_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postcode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    gp_name: Optional[str] = None
    gp_surgery: Optional[str] = None
    gp_phone: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ServiceUserDocumentCreate(BaseModel):
    """Upload a document to a service user's file"""
    section_id: str  # e.g., "3_assessments"
    document_type: Optional[str] = None
    title: str
    notes: Optional[str] = None
    file_url: str
    file_name: str
    expiry_date: Optional[str] = None


# ==================== SERVICE USER ROUTES ====================

@router.get("/service-users")
async def list_service_users(
    status: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """List all service users with optional filtering"""
    db = get_db()
    query = {}
    
    if status:
        query["status"] = status
    
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"nhs_number": {"$regex": search, "$options": "i"}},
            {"postcode": {"$regex": search, "$options": "i"}},
        ]
    
    service_users = await db.service_users.find(query, {"_id": 0}).sort("full_name", 1).to_list(500)
    
    # Add document counts per section
    for su in service_users:
        doc_counts = await db.service_user_documents.aggregate([
            {"$match": {"service_user_id": su["id"]}},
            {"$group": {"_id": "$section_id", "count": {"$sum": 1}}}
        ]).to_list(20)
        su["document_counts"] = {d["_id"]: d["count"] for d in doc_counts}
        su["total_documents"] = sum(d["count"] for d in doc_counts)
    
    return service_users


@router.post("/service-users")
async def create_service_user(
    data: ServiceUserCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new service user"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate unique ID and code
    su_id = str(uuid.uuid4())
    
    # Generate service user code (SU-XXXX format)
    count = await db.service_users.count_documents({})
    su_code = f"SU-{count + 1:04d}"
    
    service_user = {
        "id": su_id,
        "service_user_code": su_code,
        "full_name": data.full_name,
        "date_of_birth": data.date_of_birth,
        "nhs_number": data.nhs_number,
        "address_line_1": data.address_line_1,
        "address_line_2": data.address_line_2,
        "city": data.city,
        "county": data.county,
        "postcode": data.postcode,
        "phone": data.phone,
        "email": data.email,
        "emergency_contact_name": data.emergency_contact_name,
        "emergency_contact_phone": data.emergency_contact_phone,
        "emergency_contact_relationship": data.emergency_contact_relationship,
        "gp_name": data.gp_name,
        "gp_surgery": data.gp_surgery,
        "gp_phone": data.gp_phone,
        "notes": data.notes,
        "status": "active",
        "created_at": now,
        "created_by": user.get("user_id"),
        "updated_at": now,
    }
    
    await db.service_users.insert_one(service_user)
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user",
        "entity_id": su_id,
        "action": "created",
        "performed_by": user.get("user_id"),
        "details": {"full_name": data.full_name, "service_user_code": su_code},
        "timestamp": now
    })
    
    return {"id": su_id, "service_user_code": su_code, "message": "Service user created successfully"}


@router.get("/service-users/sections")
async def get_service_user_sections(user: dict = Depends(get_current_user)):
    """Get all available service user file sections with their document types"""
    return {
        "sections": [
            {
                "id": section_id,
                **section_info
            }
            for section_id, section_info in SERVICE_USER_SECTIONS.items()
        ]
    }


@router.get("/service-users/{service_user_id}")
async def get_service_user(
    service_user_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Get service user details with all sections"""
    db = get_db()
    service_user = await db.service_users.find_one({"id": service_user_id}, {"_id": 0})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    # Get documents grouped by section
    documents = await db.service_user_documents.find(
        {"service_user_id": service_user_id},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(500)
    
    # Organize documents by section
    sections = {}
    for section_id, section_info in SERVICE_USER_SECTIONS.items():
        section_docs = [d for d in documents if d.get("section_id") == section_id]
        sections[section_id] = {
            "section_number": section_info["section_number"],
            "name": section_info["name"],
            "description": section_info["description"],
            "document_types": section_info["document_types"],
            "documents": section_docs,
            "document_count": len(section_docs),
        }
    
    service_user["sections"] = sections
    service_user["total_documents"] = len(documents)
    
    return service_user


@router.put("/service-users/{service_user_id}")
async def update_service_user(
    service_user_id: str,
    data: ServiceUserUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update service user details"""
    db = get_db()
    service_user = await db.service_users.find_one({"id": service_user_id}, {"_id": 0})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.service_users.update_one(
        {"id": service_user_id},
        {"$set": update_data}
    )
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user",
        "entity_id": service_user_id,
        "action": "updated",
        "performed_by": user.get("user_id"),
        "details": {"fields_updated": list(update_data.keys())},
        "timestamp": update_data["updated_at"]
    })
    
    return {"message": "Service user updated successfully"}


@router.delete("/service-users/{service_user_id}")
async def delete_service_user(
    service_user_id: str,
    user: dict = Depends(require_admin)
):
    """Delete a service user (admin only - for test data cleanup)"""
    db = get_db()
    service_user = await db.service_users.find_one({"id": service_user_id})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    # Delete associated documents first
    await db.service_user_documents.delete_many({"service_user_id": service_user_id})
    
    # Delete the service user
    await db.service_users.delete_one({"id": service_user_id})
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user",
        "entity_id": service_user_id,
        "action": "deleted",
        "performed_by": user.get("user_id"),
        "details": {"name": service_user.get("full_name"), "reason": "Test data cleanup"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Service user deleted successfully", "id": service_user_id}


# ==================== SERVICE USER DOCUMENT ROUTES ====================

@router.post("/service-users/{service_user_id}/documents")
async def upload_service_user_document(
    service_user_id: str,
    data: ServiceUserDocumentCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Upload a document to a service user's file"""
    db = get_db()
    service_user = await db.service_users.find_one({"id": service_user_id}, {"_id": 0})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    if data.section_id not in SERVICE_USER_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section: {data.section_id}")
    
    now = datetime.now(timezone.utc).isoformat()
    doc_id = str(uuid.uuid4())
    
    document = {
        "id": doc_id,
        "service_user_id": service_user_id,
        "section_id": data.section_id,
        "section_name": SERVICE_USER_SECTIONS[data.section_id]["name"],
        "document_type": data.document_type,
        "title": data.title,
        "notes": data.notes,
        "file_url": data.file_url,
        "file_name": data.file_name,
        "expiry_date": data.expiry_date,
        "uploaded_at": now,
        "uploaded_by": user.get("user_id"),
        "verified": False,
        "verified_at": None,
        "verified_by": None,
    }
    
    await db.service_user_documents.insert_one(document)
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user_document",
        "entity_id": doc_id,
        "action": "uploaded",
        "performed_by": user.get("user_id"),
        "details": {
            "service_user_id": service_user_id,
            "section": data.section_id,
            "title": data.title
        },
        "timestamp": now
    })
    
    return {"id": doc_id, "message": "Document uploaded successfully"}


@router.get("/service-users/{service_user_id}/documents")
async def get_service_user_documents(
    service_user_id: str,
    section_id: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """Get all documents for a service user, optionally filtered by section"""
    db = get_db()
    query = {"service_user_id": service_user_id}
    
    if section_id:
        query["section_id"] = section_id
    
    documents = await db.service_user_documents.find(query, {"_id": 0}).sort("uploaded_at", -1).to_list(500)
    
    return documents


@router.put("/service-users/{service_user_id}/documents/{document_id}/verify")
async def verify_service_user_document(
    service_user_id: str,
    document_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Mark a service user document as verified"""
    db = get_db()
    document = await db.service_user_documents.find_one({
        "id": document_id,
        "service_user_id": service_user_id
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.service_user_documents.update_one(
        {"id": document_id},
        {"$set": {
            "verified": True,
            "verified_at": now,
            "verified_by": user.get("user_id")
        }}
    )
    
    return {"message": "Document verified successfully"}


@router.delete("/service-users/{service_user_id}/documents/{document_id}")
async def delete_service_user_document(
    service_user_id: str,
    document_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Delete a service user document"""
    db = get_db()
    document = await db.service_user_documents.find_one({
        "id": document_id,
        "service_user_id": service_user_id
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.service_user_documents.delete_one({"id": document_id})
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user_document",
        "entity_id": document_id,
        "action": "deleted",
        "performed_by": user.get("user_id"),
        "details": {
            "service_user_id": service_user_id,
            "title": document.get("title")
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Document deleted successfully", "id": document_id}
