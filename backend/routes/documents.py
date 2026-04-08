"""
Document Management Routes Module

This module handles document-related endpoints including:
- Document types CRUD
- Employee document CRUD
- Document verification and stamping
- Document download and file operations

NOTE: Some complex endpoints that depend heavily on helper functions in server.py
are still there and will be migrated in a future phase.

Extracted from server.py for modularity.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Document Management"])


# ==================== DOCUMENT MODELS ====================

class DocumentTypeCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    requires_expiry: bool = False
    validity_period_months: Optional[int] = None


class DocumentTypeResponse(BaseModel):
    id: str
    name: str
    category: str
    description: Optional[str] = None
    requires_expiry: bool = False
    validity_period_months: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        extra = "ignore"


# ==================== DOCUMENT TYPES CRUD ====================

@router.post("/document-types", response_model=DocumentTypeResponse)
async def create_document_type(
    doc_type: DocumentTypeCreate,
    user: dict = Depends(require_admin)
):
    """Create a new document type."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    doc_type_id = str(uuid.uuid4())
    doc_type_data = {
        "id": doc_type_id,
        **doc_type.model_dump(),
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("user_id")
    }
    
    await db.document_types.insert_one(doc_type_data)
    
    await log_audit_action(
        user.get("user_id"),
        "create_document_type",
        "document_type",
        doc_type_id,
        {"name": doc_type.name, "category": doc_type.category}
    )
    
    return DocumentTypeResponse(**doc_type_data)


@router.get("/document-types", response_model=List[DocumentTypeResponse])
async def get_document_types(
    category: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all document types, optionally filtered by category."""
    db = get_db()
    
    query = {}
    if category:
        query["category"] = category
    
    doc_types = await db.document_types.find(query, {"_id": 0}).to_list(100)
    
    return [DocumentTypeResponse(**dt) for dt in doc_types]


@router.get("/document-types/{doc_type_id}", response_model=DocumentTypeResponse)
async def get_document_type(
    doc_type_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific document type."""
    db = get_db()
    
    doc_type = await db.document_types.find_one({"id": doc_type_id}, {"_id": 0})
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    return DocumentTypeResponse(**doc_type)


@router.put("/document-types/{doc_type_id}", response_model=DocumentTypeResponse)
async def update_document_type(
    doc_type_id: str,
    doc_type: DocumentTypeCreate,
    user: dict = Depends(require_admin)
):
    """Update a document type."""
    db = get_db()
    
    existing = await db.document_types.find_one({"id": doc_type_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        **doc_type.model_dump(),
        "updated_at": now,
        "updated_by": user.get("user_id")
    }
    
    await db.document_types.update_one({"id": doc_type_id}, {"$set": update_data})
    
    updated = await db.document_types.find_one({"id": doc_type_id}, {"_id": 0})
    
    await log_audit_action(
        user.get("user_id"),
        "update_document_type",
        "document_type",
        doc_type_id,
        update_data
    )
    
    return DocumentTypeResponse(**updated)


@router.delete("/document-types/{doc_type_id}")
async def delete_document_type(
    doc_type_id: str,
    user: dict = Depends(require_admin)
):
    """Delete a document type."""
    db = get_db()
    
    existing = await db.document_types.find_one({"id": doc_type_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    # Check if any documents use this type
    doc_count = await db.employee_documents.count_documents({"document_type_id": doc_type_id})
    if doc_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete: {doc_count} documents use this type"
        )
    
    await db.document_types.delete_one({"id": doc_type_id})
    
    await log_audit_action(
        user.get("user_id"),
        "delete_document_type",
        "document_type",
        doc_type_id,
        {"name": existing.get("name")}
    )
    
    return {"success": True, "message": "Document type deleted"}


# ==================== DOCUMENT CATEGORIES ====================

@router.get("/document-categories")
async def get_document_categories(user: dict = Depends(get_current_user)):
    """Get all unique document categories."""
    db = get_db()
    
    # Get distinct categories from document_types
    categories = await db.document_types.distinct("category")
    
    # Also include predefined categories
    predefined = [
        "identity",
        "right_to_work",
        "qualifications",
        "dbs",
        "references",
        "health",
        "training",
        "contracts",
        "other"
    ]
    
    all_categories = list(set(categories + predefined))
    all_categories.sort()
    
    return {"categories": all_categories}


# ==================== DOCUMENT STATISTICS ====================

@router.get("/admin/document-statistics")
async def get_document_statistics(user: dict = Depends(get_current_user)):
    """Get document statistics for admin dashboard."""
    db = get_db()
    
    total = await db.employee_documents.count_documents({})
    verified = await db.employee_documents.count_documents({"verified": True})
    pending = await db.employee_documents.count_documents({
        "status": {"$in": ["pending", "uploaded", "pending_review"]}
    })
    rejected = await db.employee_documents.count_documents({"status": "rejected"})
    
    # By category
    by_category = {}
    categories = await db.employee_documents.distinct("category")
    for cat in categories:
        if cat:
            by_category[cat] = await db.employee_documents.count_documents({"category": cat})
    
    return {
        "total": total,
        "verified": verified,
        "pending_review": pending,
        "rejected": rejected,
        "by_category": by_category,
        "verification_rate": round((verified / total * 100) if total > 0 else 0, 1)
    }


# ==================== DOCUMENT SEARCH ====================

@router.get("/documents/search")
async def search_documents(
    query: str = Query(..., min_length=2),
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Search documents by name, employee, or type."""
    db = get_db()
    
    search_query = {
        "$or": [
            {"original_filename": {"$regex": query, "$options": "i"}},
            {"document_type_name": {"$regex": query, "$options": "i"}},
            {"requirement_name": {"$regex": query, "$options": "i"}},
            {"notes": {"$regex": query, "$options": "i"}}
        ]
    }
    
    if category:
        search_query["category"] = category
    if status:
        search_query["status"] = status
    
    docs = await db.employee_documents.find(
        search_query,
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    # Enrich with employee names
    for doc in docs:
        emp = await db.employees.find_one(
            {"id": doc.get("employee_id")},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if emp:
            doc["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
    
    return {
        "results": docs,
        "count": len(docs),
        "query": query
    }


# ==================== BULK DOCUMENT OPERATIONS ====================

@router.post("/admin/documents/bulk-verify")
async def bulk_verify_documents(
    document_ids: List[str],
    user: dict = Depends(require_manager_or_admin)
):
    """Verify multiple documents at once."""
    db = get_db()
    
    now = datetime.now(timezone.utc).isoformat()
    verified_count = 0
    errors = []
    
    for doc_id in document_ids:
        try:
            doc = await db.employee_documents.find_one({"id": doc_id})
            if not doc:
                errors.append(f"{doc_id}: Not found")
                continue
            
            if doc.get("verified"):
                errors.append(f"{doc_id}: Already verified")
                continue
            
            await db.employee_documents.update_one(
                {"id": doc_id},
                {
                    "$set": {
                        "verified": True,
                        "verified_by": user.get("user_id"),
                        "verified_at": now,
                        "status": "verified",
                        "updated_at": now
                    }
                }
            )
            verified_count += 1
            
        except Exception as e:
            errors.append(f"{doc_id}: {str(e)}")
    
    await log_audit_action(
        user.get("user_id"),
        "bulk_verify_documents",
        "employee_documents",
        "bulk",
        {"verified_count": verified_count, "requested": len(document_ids)}
    )
    
    return {
        "success": True,
        "verified_count": verified_count,
        "errors": errors
    }


@router.get("/admin/documents/pending-review")
async def get_documents_pending_review(
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """Get all documents pending review."""
    db = get_db()
    
    docs = await db.employee_documents.find(
        {
            "status": {"$in": ["pending", "uploaded", "pending_review"]},
            "verified": {"$ne": True}
        },
        {"_id": 0}
    ).sort("uploaded_at", -1).limit(limit).to_list(limit)
    
    # Enrich with employee names
    for doc in docs:
        emp = await db.employees.find_one(
            {"id": doc.get("employee_id")},
            {"_id": 0, "first_name": 1, "last_name": 1, "email": 1}
        )
        if emp:
            doc["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            doc["employee_email"] = emp.get("email")
    
    return {
        "documents": docs,
        "count": len(docs)
    }
