"""
Templates Management Routes Module

This module handles document/form template-related endpoints including:
- Template CRUD operations
- Template retrieval with filtering

Templates are used for:
- Interview record forms
- Contract templates
- Induction documents
- Training sign-off sheets

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Templates"])


# ==================== MODELS ====================

class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str  # e.g., "Identity", "References", "Training", "Contract"
    linked_document_type_id: Optional[str] = None  # Links to document_types
    form_fields: List[Dict[str, Any]] = []  # JSON schema for form fields
    requires_employee_signature: bool = True
    requires_admin_signature: bool = True
    content_html: str = ""  # HTML template content
    visibility: str = "normal"  # normal, restricted, confidential
    role_specific: Optional[str] = None  # None = all roles, "Nurse", "Healthcare Assistant"
    section: Optional[str] = None  # Recruitment, Interview, Compliance, etc.


class TemplateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = None
    category: str
    linked_document_type_id: Optional[str] = None
    form_fields: List[Dict[str, Any]] = []
    requires_employee_signature: bool = True
    requires_admin_signature: bool = True
    content_html: str = ""
    active: bool = True
    version: int = 1
    visibility: str = "normal"
    role_specific: Optional[str] = None
    section: Optional[str] = None
    created_at: str
    updated_at: str


# ==================== TEMPLATE ROUTES ====================

@router.post("/templates", response_model=TemplateResponse)
async def create_template(template: TemplateCreate, user: dict = Depends(require_admin)):
    """Create a new template."""
    db = get_db()
    template_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    template_doc = {
        "id": template_id,
        **template.model_dump(),
        "active": True,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "created_by": user['user_id']
    }
    await db.templates.insert_one(template_doc)
    
    await log_audit_action(user['user_id'], "create_template", "template", template_id, {"name": template.name})
    
    return TemplateResponse(**template_doc)


@router.get("/templates", response_model=List[TemplateResponse])
async def get_templates(
    category: Optional[str] = None,
    active: bool = True,
    user: dict = Depends(get_current_user)
):
    """Get all templates with optional filtering."""
    db = get_db()
    query = {"active": active}
    if category:
        query["category"] = category
    
    templates = await db.templates.find(query, {"_id": 0}).to_list(100)
    return [TemplateResponse(**t) for t in templates]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    """Get a specific template by ID."""
    db = get_db()
    template = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse(**template)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, update: TemplateCreate, user: dict = Depends(require_admin)):
    """Update an existing template."""
    db = get_db()
    template = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = update.model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["version"] = template.get("version", 1) + 1
    
    await db.templates.update_one({"id": template_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "update_template", "template", template_id, {"name": update.name})
    
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return TemplateResponse(**updated)


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(require_admin)):
    """Soft delete a template (mark as inactive)."""
    db = get_db()
    result = await db.templates.update_one({"id": template_id}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await log_audit_action(user['user_id'], "delete_template", "template", template_id, {})
    return {"message": "Template archived"}
