"""
Policies Routes

Organization policy CRUD operations:
- Create, read, list policies
- Upload policy documents
- Assign policies to employees

Extracted from server.py - Phase 38
"""

import uuid
import io
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action
)

router = APIRouter(tags=["Policies"])


# Pydantic Models
class PolicyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "General"
    version: str = "1.0"
    review_due_at: Optional[str] = None
    mandatory: bool = True


class PolicyResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    version: str
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    active: bool = True
    published_at: Optional[str] = None
    review_due_at: Optional[str] = None
    mandatory: bool = True
    assigned_count: int = 0
    signed_count: int = 0
    
    class Config:
        from_attributes = True


class PolicyAssignmentCreate(BaseModel):
    policy_id: str
    employee_ids: List[str]


# Lazy import for storage functions
def get_storage_functions():
    from server import put_object, get_object, APP_NAME
    return put_object, get_object, APP_NAME


@router.post("/policies", response_model=PolicyResponse)
async def create_policy(policy: PolicyCreate, user: dict = Depends(require_admin)):
    """Create a new organization policy"""
    db = get_db()
    
    policy_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    policy_doc = {
        "id": policy_id,
        **policy.model_dump(),
        "file_url": None,
        "active": True,
        "published_at": now,
        "assigned_count": 0,
        "signed_count": 0
    }
    await db.policies.insert_one(policy_doc)
    return PolicyResponse(**policy_doc)


@router.get("/policies", response_model=List[PolicyResponse])
async def get_policies(active: Optional[bool] = None, user: dict = Depends(get_current_user)):
    """Get all organization policies"""
    db = get_db()
    
    query = {}
    if active is not None:
        query["active"] = active
    policies = await db.policies.find(query, {"_id": 0}).to_list(100)
    
    # Get counts
    for policy in policies:
        assigned_count = await db.policy_assignments.count_documents({"policy_id": policy['id']})
        acknowledged_count = await db.policy_assignments.count_documents({
            "policy_id": policy['id'], 
            "status": {"$in": ["acknowledged", "signed"]}
        })
        policy['assigned_count'] = assigned_count
        policy['signed_count'] = acknowledged_count
    
    return [PolicyResponse(**p) for p in policies]


@router.post("/policies/{policy_id}/upload")
async def upload_policy_file(policy_id: str, file: UploadFile = File(...), user: dict = Depends(require_admin)):
    """Upload a document file for a policy"""
    db = get_db()
    put_object, _, APP_NAME = get_storage_functions()
    
    policy = await db.policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    path = f"{APP_NAME}/policies/{uuid.uuid4()}.{ext}"
    
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/pdf")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.policies.update_one({"id": policy_id}, {"$set": {
        "file_url": result["path"],
        "original_filename": file.filename,
        "uploaded_at": now
    }})
    
    await log_audit_action(
        user['user_id'],
        "policy_uploaded",
        "policy",
        policy_id,
        {
            "policy_title": policy['title'],
            "filename": file.filename,
            "version": policy.get('version', '1.0')
        }
    )
    
    updated_policy = await db.policies.find_one({"id": policy_id}, {"_id": 0})
    return PolicyResponse(**updated_policy)


@router.get("/policies/{policy_id}/file")
async def get_policy_file(policy_id: str, user: dict = Depends(get_current_user)):
    """Get policy file for viewing"""
    db = get_db()
    _, get_object, _ = get_storage_functions()
    
    policy = await db.policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if not policy.get('file_url'):
        raise HTTPException(status_code=404, detail="No file uploaded for this policy")
    
    try:
        data, content_type = get_object(policy['file_url'])
        filename = policy.get('original_filename', f"policy_{policy_id}.pdf")
        return StreamingResponse(
            io.BytesIO(data),
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename=\"{filename}\""}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve policy file")


@router.post("/policies/assign")
async def assign_policies(assignment: PolicyAssignmentCreate, user: dict = Depends(require_admin)):
    """Assign a policy to multiple employees"""
    db = get_db()
    
    # Check both policies and org_policies collections
    policy = await db.policies.find_one({"id": assignment.policy_id}, {"_id": 0})
    if not policy:
        policy = await db.org_policies.find_one({"id": assignment.policy_id}, {"_id": 0})
        if policy:
            policy = {
                "id": policy.get("id"),
                "title": policy.get("name"),
                "version": policy.get("version", "1.0"),
                "file_url": policy.get("file_url")
            }
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    assignments = []
    
    for emp_id in assignment.employee_ids:
        # Check if already assigned
        existing = await db.policy_assignments.find_one({
            "policy_id": assignment.policy_id, 
            "employee_id": emp_id,
            "status": {"$nin": ["unassigned", "withdrawn"]}
        })
        if existing:
            continue
        
        emp = await db.employees.find_one({"id": emp_id}, {"_id": 0})
        emp_name = f"{emp['first_name']} {emp['last_name']}" if emp else "Unknown"
        
        assignment_doc = {
            "id": str(uuid.uuid4()),
            "policy_id": assignment.policy_id,
            "policy_title": policy['title'],
            "policy_version": policy.get('version', '1.0'),
            "employee_id": emp_id,
            "employee_name": emp_name,
            "assigned_at": now,
            "assigned_by": user['user_id'],
            "assigned_by_name": user.get('name', user.get('email', 'Admin')),
            "status": "assigned",
            "viewed_at": None,
            "acknowledged_at": None,
            "acknowledged_by_employee_name": None,
            "admin_reviewed": False,
            "admin_reviewed_at": None,
            "admin_reviewed_by": None,
            "admin_reviewed_by_name": None
        }
        await db.policy_assignments.insert_one(assignment_doc)
        assignments.append(assignment_doc)
        
        await log_audit_action(
            user['user_id'], 
            "policy_assigned", 
            "policy_assignment", 
            assignment_doc['id'], 
            {
                "policy_id": assignment.policy_id, 
                "policy_title": policy['title'],
                "policy_version": policy.get('version', '1.0'),
                "employee_id": emp_id,
                "employee_name": emp_name,
                "assigned_by_name": user.get('name', user.get('email', 'Admin'))
            }
        )
    
    return {"assigned": len(assignments), "message": f"Policy assigned to {len(assignments)} employees"}
