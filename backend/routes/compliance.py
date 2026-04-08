"""
Compliance Management Routes Module

This module handles CQC compliance-related endpoints including:
- Organization policies management (CRUD, upload, review tracking)
- Insurance/certificates management (CRUD, upload, expiry tracking)
- Incident logs management (CRUD, audit trail)
- Compliance dashboard and reports
- CQC evidence mapping

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, ConfigDict

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Compliance Management"])


# ==================== MODELS ====================

class OrgPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    category: str
    version: str
    status: str  # missing, active, expired, under_review, due_soon
    required: Optional[bool] = True
    conditional: Optional[bool] = False
    review_period_months: Optional[int] = 12
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    review_date: Optional[str] = None  # Next review due date
    last_reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_status: Optional[str] = None  # current, due_soon, overdue
    assigned_staff_count: Optional[int] = 0
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class InsuranceDocCreate(BaseModel):
    name: str
    insurance_type: str  # public_liability, employers_liability
    expiry_date: str
    policy_number: Optional[str] = None
    provider: Optional[str] = None
    notes: Optional[str] = None


class InsuranceDocResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    insurance_type: str
    category: Optional[str] = "insurance"
    required: Optional[bool] = True
    conditional: Optional[bool] = False
    renewal_period_months: Optional[int] = 12
    requires_expiry_date: Optional[bool] = True
    valid_until_replaced: Optional[bool] = False
    status: str  # valid, expiring_soon, expired, missing
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    policy_number: Optional[str] = None
    provider: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class IncidentLogCreate(BaseModel):
    incident_type: str  # incident, outbreak, near_miss, complaint
    title: str
    description: str
    date_occurred: str
    location: Optional[str] = None
    persons_involved: Optional[str] = None
    immediate_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None


class IncidentLogUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None


class InsuranceDocUpdate(BaseModel):
    """Update model for insurance/certificates with audit trail"""
    name: Optional[str] = None
    expiry_date: Optional[str] = None
    policy_number: Optional[str] = None
    provider: Optional[str] = None
    issue_date: Optional[str] = None
    notes: Optional[str] = None
    reason: str  # Required for audit trail


class OrgPolicyAmend(BaseModel):
    """Amendment model for policies with audit trail"""
    name: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    review_date: Optional[str] = None
    notes: Optional[str] = None
    reason: str  # Required for audit trail


class IncidentLogAmend(BaseModel):
    """Amendment model for incidents with audit trail"""
    title: Optional[str] = None
    description: Optional[str] = None
    incident_type: Optional[str] = None
    date_occurred: Optional[str] = None
    location: Optional[str] = None
    persons_involved: Optional[str] = None
    immediate_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    reason: str  # Required for audit trail


class IncidentLogResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    incident_type: str
    reference_number: str
    title: str
    description: str
    date_occurred: str
    location: Optional[str] = None
    persons_involved: Optional[str] = None
    immediate_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    status: str  # open, investigating, resolved, closed
    reported_by: str
    reported_at: str
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    created_at: str
    updated_at: str


# ==================== CONSTANTS ====================

CORE_POLICIES = [
    # Core Policies - Essential Safeguarding & Safety (ALL REQUIRED by CQC)
    {"name": "Safeguarding Adults Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Safeguarding Children Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Mental Capacity Act & DoLS Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Health & Safety Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Fire Safety Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "First Aid Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Equality, Diversity & Inclusion Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Whistleblowing Policy", "category": "Core", "required": True, "review_period_months": 12},
    
    # Clinical Policies - Care & Medical (REQUIRED for domiciliary care)
    {"name": "Medication Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Infection Prevention & Control Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Manual Handling Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "COSHH Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Care Planning Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "End of Life Care Policy", "category": "Clinical", "required": False, "conditional": True, "review_period_months": 24},
    {"name": "Nutrition & Hydration Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Pressure Ulcer Prevention Policy", "category": "Clinical", "required": False, "conditional": True, "review_period_months": 24},
    
    # Operational Policies - Day-to-Day Operations (REQUIRED)
    {"name": "Lone Working Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Risk Assessment Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Record Keeping Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Confidentiality Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Complaints Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Incident Reporting Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Business Continuity Policy", "category": "Operational", "required": True, "review_period_months": 24},
    {"name": "Service User Feedback Policy", "category": "Operational", "required": True, "review_period_months": 12},
    
    # Governance Policies - HR & Regulatory (REQUIRED)
    {"name": "Recruitment & Selection Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "DBS & Vetting Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Induction & Probation Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Training & Development Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Supervision & Appraisal Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Disciplinary & Grievance Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Data Protection & GDPR Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Code of Conduct", "category": "Governance", "required": True, "review_period_months": 12},
]


# ==================== POLICY ROUTES ====================

@router.post("/compliance/seed-policies")
async def seed_org_policies(user: dict = Depends(require_admin)):
    """Seed core organisation policies as placeholders with review tracking"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    
    for policy in CORE_POLICIES:
        existing = await db.org_policies.find_one({"name": policy["name"]})
        if not existing:
            policy_doc = {
                "id": str(uuid.uuid4()),
                "name": policy["name"],
                "category": policy["category"],
                "version": "v1.0",
                "status": "missing",
                "required": policy.get("required", True),
                "conditional": policy.get("conditional", False),
                "review_period_months": policy.get("review_period_months", 12),
                "file_url": None,
                "original_filename": None,
                "review_date": None,
                "last_reviewed_at": None,
                "reviewed_by": None,
                "assigned_staff_count": 0,
                "notes": None,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id']
            }
            await db.org_policies.insert_one(policy_doc)
            created += 1
    
    return {"message": f"Created {created} policy placeholders", "total": len(CORE_POLICIES)}


@router.get("/compliance/policies", response_model=List[OrgPolicyResponse])
async def get_org_policies(
    category: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all organisation policies with review status tracking"""
    db = get_db()
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    policies = await db.org_policies.find(query, {"_id": 0}).sort("category", 1).to_list(100)
    
    # Compute review status based on review date and last reviewed
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    
    # Get assignment counts per policy
    assignments_pipeline = [
        {"$match": {"status": {"$ne": "removed"}}},
        {"$group": {"_id": "$policy_id", "count": {"$sum": 1}}}
    ]
    assignment_counts = {}
    try:
        assignments = await db.policy_assignments.aggregate(assignments_pipeline).to_list(1000)
        for a in assignments:
            assignment_counts[a["_id"]] = a["count"]
    except Exception:
        pass
    
    for policy in policies:
        # Update assigned staff count
        policy["assigned_staff_count"] = assignment_counts.get(policy["id"], 0)
        
        # Determine review status
        if policy.get("review_date"):
            try:
                review_str = policy["review_date"]
                if isinstance(review_str, datetime):
                    review_date = review_str if review_str.tzinfo else review_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(review_str):
                    review_date = datetime.fromisoformat(review_str.replace('Z', '+00:00'))
                else:
                    review_date = datetime.fromisoformat(f"{review_str}T00:00:00+00:00")
                
                if review_date < now:
                    policy["review_status"] = "overdue"
                    if policy["status"] == "active":
                        policy["status"] = "expired"
                elif review_date < now + thirty_days:
                    policy["review_status"] = "due_soon"
                else:
                    policy["review_status"] = "current"
            except Exception:
                policy["review_status"] = None
        else:
            policy["review_status"] = None if policy["status"] == "missing" else "current"
    
    return policies


@router.get("/compliance/policies/{policy_id}", response_model=OrgPolicyResponse)
async def get_org_policy(policy_id: str, user: dict = Depends(get_current_user)):
    """Get a specific organisation policy"""
    db = get_db()
    policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/compliance/policies/{policy_id}/upload")
async def upload_org_policy_document(
    policy_id: str,
    file: UploadFile = File(...),
    review_months: int = Query(12, description="Months until next review"),
    user: dict = Depends(require_admin)
):
    """Upload a policy document file"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc)
    review_date = (now + timedelta(days=review_months * 30)).isoformat()
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="policies")
        file_url = result.get("url")
    
    update = {
        "file_url": file_url,
        "original_filename": file.filename,
        "status": "active",
        "review_date": review_date,
        "last_reviewed_at": now.isoformat(),
        "reviewed_by": user['user_id'],
        "updated_at": now.isoformat()
    }
    
    await db.org_policies.update_one({"id": policy_id}, {"$set": update})
    
    await log_audit_action(
        user['user_id'],
        "upload_policy",
        "org_policy",
        policy_id,
        {"filename": file.filename, "review_months": review_months}
    )
    
    return {"message": "Policy uploaded", "file_url": file_url, "review_date": review_date}


@router.put("/compliance/policies/{policy_id}", response_model=OrgPolicyResponse)
async def update_org_policy(
    policy_id: str,
    updates: OrgPolicyAmend,
    user: dict = Depends(require_admin)
):
    """Update policy metadata with audit trail"""
    db = get_db()
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Store amendment history
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "org_policy",
        "entity_id": policy_id,
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": updates.reason,
        "changes": {},
        "previous_values": {}
    }
    
    update_dict = {"updated_at": now}
    for field, value in updates.model_dump(exclude_none=True, exclude={'reason'}).items():
        if field in policy and policy[field] != value:
            amendment["changes"][field] = value
            amendment["previous_values"][field] = policy[field]
            update_dict[field] = value
    
    if amendment["changes"]:
        await db.amendments.insert_one(amendment)
        await db.org_policies.update_one({"id": policy_id}, {"$set": update_dict})
    
    updated = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    return updated


@router.get("/compliance/policies/{policy_id}/file")
async def get_policy_file_url(policy_id: str, user: dict = Depends(get_current_user)):
    """Get the file URL for a policy"""
    db = get_db()
    policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0, "file_url": 1, "original_filename": 1})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {
        "file_url": policy.get("file_url"),
        "filename": policy.get("original_filename")
    }


@router.get("/compliance/policies/{policy_id}/download")
async def download_policy_file(policy_id: str, user: dict = Depends(get_current_user)):
    """Get download URL for a policy file"""
    db = get_db()
    policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if not policy.get("file_url"):
        raise HTTPException(status_code=404, detail="No file uploaded for this policy")
    return {
        "download_url": policy.get("file_url"),
        "filename": policy.get("original_filename")
    }


@router.post("/compliance/policies/{policy_id}/replace")
async def replace_policy_document(
    policy_id: str,
    file: UploadFile = File(...),
    review_months: int = Query(12),
    reason: str = Query(..., description="Reason for replacement"),
    user: dict = Depends(require_admin)
):
    """Replace a policy document with audit trail"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc)
    
    # Store replacement in amendments
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "org_policy",
        "entity_id": policy_id,
        "amendment_type": "file_replacement",
        "amended_by": user['user_id'],
        "amended_at": now.isoformat(),
        "reason": reason,
        "previous_values": {
            "file_url": policy.get("file_url"),
            "original_filename": policy.get("original_filename")
        }
    }
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="policies")
        file_url = result.get("url")
    
    review_date = (now + timedelta(days=review_months * 30)).isoformat()
    
    amendment["new_values"] = {
        "file_url": file_url,
        "original_filename": file.filename
    }
    
    await db.amendments.insert_one(amendment)
    
    await db.org_policies.update_one(
        {"id": policy_id},
        {"$set": {
            "file_url": file_url,
            "original_filename": file.filename,
            "version": f"v{int(policy.get('version', 'v1.0').replace('v', '').split('.')[0]) + 1}.0",
            "review_date": review_date,
            "last_reviewed_at": now.isoformat(),
            "reviewed_by": user['user_id'],
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Policy replaced", "file_url": file_url}


@router.delete("/compliance/policies/{policy_id}/file")
async def delete_policy_file(
    policy_id: str,
    reason: str = Query(..., description="Reason for deletion"),
    user: dict = Depends(require_admin)
):
    """Delete a policy file with audit trail"""
    db = get_db()
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "org_policy",
        "entity_id": policy_id,
        "amendment_type": "file_deletion",
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": reason,
        "previous_values": {
            "file_url": policy.get("file_url"),
            "original_filename": policy.get("original_filename")
        }
    }
    
    await db.amendments.insert_one(amendment)
    
    await db.org_policies.update_one(
        {"id": policy_id},
        {"$set": {
            "file_url": None,
            "original_filename": None,
            "status": "missing",
            "updated_at": now
        }}
    )
    
    return {"message": "Policy file deleted"}


@router.put("/compliance/policies/{policy_id}/amend")
async def amend_policy(
    policy_id: str,
    amendment: OrgPolicyAmend,
    user: dict = Depends(require_admin)
):
    """Amend policy metadata with audit trail"""
    db = get_db()
    
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return await update_org_policy(policy_id, amendment, user)


@router.get("/compliance/policies/{policy_id}/history")
async def get_policy_history(policy_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for a policy"""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "org_policy", "entity_id": policy_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


# ==================== INSURANCE ROUTES ====================

@router.post("/compliance/seed-insurance")
async def seed_insurance_docs(user: dict = Depends(require_admin)):
    """Seed required insurance/certificate types"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    required_certs = [
        {"name": "Public Liability Insurance", "insurance_type": "public_liability", "category": "insurance", "required": True, "renewal_period_months": 12},
        {"name": "Employers Liability Insurance", "insurance_type": "employers_liability", "category": "insurance", "required": True, "renewal_period_months": 12},
        {"name": "Professional Indemnity Insurance", "insurance_type": "professional_indemnity", "category": "insurance", "required": False, "conditional": True, "renewal_period_months": 12},
        {"name": "CQC Registration Certificate", "insurance_type": "cqc_registration", "category": "regulatory", "required": True, "renewal_period_months": 0, "valid_until_replaced": True},
        {"name": "ICO Registration", "insurance_type": "ico_registration", "category": "regulatory", "required": True, "renewal_period_months": 12},
        {"name": "PAT Testing Certificate", "insurance_type": "pat_testing", "category": "safety", "required": True, "renewal_period_months": 12},
        {"name": "Fire Risk Assessment", "insurance_type": "fire_risk", "category": "safety", "required": True, "renewal_period_months": 12},
        {"name": "Gas Safety Certificate", "insurance_type": "gas_safety", "category": "safety", "required": False, "conditional": True, "renewal_period_months": 12},
        {"name": "Electrical Installation Certificate", "insurance_type": "electrical", "category": "safety", "required": False, "conditional": True, "renewal_period_months": 60},
    ]
    
    created = 0
    for cert in required_certs:
        existing = await db.insurance_docs.find_one({"insurance_type": cert["insurance_type"]})
        if not existing:
            doc = {
                "id": str(uuid.uuid4()),
                "name": cert["name"],
                "insurance_type": cert["insurance_type"],
                "category": cert.get("category", "insurance"),
                "required": cert.get("required", True),
                "conditional": cert.get("conditional", False),
                "renewal_period_months": cert.get("renewal_period_months", 12),
                "requires_expiry_date": not cert.get("valid_until_replaced", False),
                "valid_until_replaced": cert.get("valid_until_replaced", False),
                "status": "missing",
                "file_url": None,
                "original_filename": None,
                "expiry_date": None,
                "issue_date": None,
                "policy_number": None,
                "provider": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id']
            }
            await db.insurance_docs.insert_one(doc)
            created += 1
    
    return {"message": f"Created {created} certificate placeholders", "total": len(required_certs)}


@router.get("/compliance/insurance", response_model=List[InsuranceDocResponse])
async def get_insurance_docs(
    category: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all insurance/certificate documents with expiry tracking"""
    db = get_db()
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    docs = await db.insurance_docs.find(query, {"_id": 0}).sort("category", 1).to_list(100)
    
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    
    for doc in docs:
        # Calculate status based on expiry
        if doc.get("valid_until_replaced") and doc.get("file_url"):
            doc["status"] = "valid"
        elif doc.get("expiry_date"):
            try:
                expiry_str = doc["expiry_date"]
                if isinstance(expiry_str, datetime):
                    expiry_date = expiry_str if expiry_str.tzinfo else expiry_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(expiry_str):
                    expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    expiry_date = datetime.fromisoformat(f"{expiry_str}T00:00:00+00:00")
                
                if expiry_date < now:
                    doc["status"] = "expired"
                elif expiry_date < now + thirty_days:
                    doc["status"] = "expiring_soon"
                else:
                    doc["status"] = "valid"
            except Exception:
                doc["status"] = "missing" if not doc.get("file_url") else "valid"
        else:
            doc["status"] = "missing" if not doc.get("file_url") else "valid"
    
    return docs


@router.post("/compliance/insurance/{insurance_id}/upload")
async def upload_insurance_doc(
    insurance_id: str,
    file: UploadFile = File(...),
    expiry_date: Optional[str] = None,
    policy_number: Optional[str] = None,
    provider: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Upload an insurance/certificate document"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="insurance")
        file_url = result.get("url")
    
    update = {
        "file_url": file_url,
        "original_filename": file.filename,
        "status": "valid",
        "issue_date": now,
        "updated_at": now
    }
    
    if expiry_date:
        update["expiry_date"] = expiry_date
    if policy_number:
        update["policy_number"] = policy_number
    if provider:
        update["provider"] = provider
    
    await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update})
    
    await log_audit_action(
        user['user_id'],
        "upload_insurance",
        "insurance_doc",
        insurance_id,
        {"filename": file.filename}
    )
    
    return {"message": "Document uploaded", "file_url": file_url}


@router.post("/compliance/insurance/{insurance_id}/replace")
async def replace_insurance_doc(
    insurance_id: str,
    file: UploadFile = File(...),
    expiry_date: Optional[str] = None,
    reason: str = Query(...),
    user: dict = Depends(require_admin)
):
    """Replace an insurance document with audit trail"""
    db = get_db()
    from supabase_storage import upload_to_supabase, is_supabase_storage_configured
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "insurance_doc",
        "entity_id": insurance_id,
        "amendment_type": "file_replacement",
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": reason,
        "previous_values": {
            "file_url": doc.get("file_url"),
            "original_filename": doc.get("original_filename"),
            "expiry_date": doc.get("expiry_date")
        }
    }
    
    file_content = await file.read()
    file_url = None
    
    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_content, file.filename, folder="insurance")
        file_url = result.get("url")
    
    amendment["new_values"] = {
        "file_url": file_url,
        "original_filename": file.filename,
        "expiry_date": expiry_date
    }
    
    await db.amendments.insert_one(amendment)
    
    update = {
        "file_url": file_url,
        "original_filename": file.filename,
        "status": "valid",
        "issue_date": now,
        "updated_at": now
    }
    if expiry_date:
        update["expiry_date"] = expiry_date
    
    await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update})
    
    return {"message": "Document replaced", "file_url": file_url}


@router.delete("/compliance/insurance/{insurance_id}/file")
async def delete_insurance_file(
    insurance_id: str,
    reason: str = Query(...),
    user: dict = Depends(require_admin)
):
    """Delete an insurance file with audit trail"""
    db = get_db()
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amendment = {
        "id": str(uuid.uuid4()),
        "entity_type": "insurance_doc",
        "entity_id": insurance_id,
        "amendment_type": "file_deletion",
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": reason,
        "previous_values": {
            "file_url": doc.get("file_url"),
            "original_filename": doc.get("original_filename")
        }
    }
    
    await db.amendments.insert_one(amendment)
    
    await db.insurance_docs.update_one(
        {"id": insurance_id},
        {"$set": {
            "file_url": None,
            "original_filename": None,
            "status": "missing",
            "updated_at": now
        }}
    )
    
    return {"message": "Insurance file deleted"}


@router.put("/compliance/insurance/{insurance_id}/amend")
async def amend_insurance(
    insurance_id: str,
    amendment: InsuranceDocUpdate,
    user: dict = Depends(require_admin)
):
    """Amend insurance metadata with audit trail"""
    db = get_db()
    
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amend_record = {
        "id": str(uuid.uuid4()),
        "entity_type": "insurance_doc",
        "entity_id": insurance_id,
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": amendment.reason,
        "changes": {},
        "previous_values": {}
    }
    
    update_dict = {"updated_at": now}
    for field, value in amendment.model_dump(exclude_none=True, exclude={'reason'}).items():
        if field in doc and doc[field] != value:
            amend_record["changes"][field] = value
            amend_record["previous_values"][field] = doc[field]
            update_dict[field] = value
    
    if amend_record["changes"]:
        await db.amendments.insert_one(amend_record)
        await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update_dict})
    
    updated = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0})
    return updated


@router.get("/compliance/insurance/{insurance_id}/history")
async def get_insurance_history(insurance_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for an insurance document"""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "insurance_doc", "entity_id": insurance_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


@router.get("/compliance/insurance/{insurance_id}/file")
async def get_insurance_file_url(insurance_id: str, user: dict = Depends(get_current_user)):
    """Get the file URL for an insurance document"""
    db = get_db()
    doc = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0, "file_url": 1, "original_filename": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    return {
        "file_url": doc.get("file_url"),
        "filename": doc.get("original_filename")
    }


@router.get("/compliance/insurance/{insurance_id}/download")
async def download_insurance_file(insurance_id: str, user: dict = Depends(get_current_user)):
    """Get download URL for an insurance file"""
    db = get_db()
    doc = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    if not doc.get("file_url"):
        raise HTTPException(status_code=404, detail="No file uploaded")
    return {
        "download_url": doc.get("file_url"),
        "filename": doc.get("original_filename")
    }


# ==================== INCIDENT ROUTES ====================

@router.get("/compliance/incidents", response_model=List[IncidentLogResponse])
async def get_incidents(
    incident_type: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all incident logs"""
    db = get_db()
    query = {}
    if incident_type:
        query["incident_type"] = incident_type
    if status:
        query["status"] = status
    
    incidents = await db.incident_logs.find(query, {"_id": 0}).sort("date_occurred", -1).to_list(1000)
    return incidents


@router.post("/compliance/incidents", response_model=IncidentLogResponse)
async def create_incident(incident: IncidentLogCreate, user: dict = Depends(require_admin)):
    """Create a new incident log"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate reference number
    count = await db.incident_logs.count_documents({})
    ref_number = f"INC-{datetime.now().year}-{str(count + 1).zfill(4)}"
    
    doc = {
        "id": str(uuid.uuid4()),
        "reference_number": ref_number,
        **incident.model_dump(),
        "status": "open",
        "reported_by": user['user_id'],
        "reported_at": now,
        "closed_at": None,
        "closed_by": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.incident_logs.insert_one(doc)
    
    await log_audit_action(
        user['user_id'],
        "create_incident",
        "incident_log",
        doc["id"],
        {"reference": ref_number, "type": incident.incident_type}
    )
    
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/compliance/incidents/{incident_id}", response_model=IncidentLogResponse)
async def update_incident(
    incident_id: str,
    updates: IncidentLogUpdate,
    user: dict = Depends(require_admin)
):
    """Update an incident log"""
    db = get_db()
    
    incident = await db.incident_logs.find_one({"id": incident_id})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_dict = {"updated_at": now}
    
    for field, value in updates.model_dump(exclude_none=True).items():
        update_dict[field] = value
    
    if updates.status == "closed":
        update_dict["closed_at"] = now
        update_dict["closed_by"] = user['user_id']
    
    await db.incident_logs.update_one({"id": incident_id}, {"$set": update_dict})
    
    updated = await db.incident_logs.find_one({"id": incident_id}, {"_id": 0})
    return updated


@router.put("/compliance/incidents/{incident_id}/amend")
async def amend_incident(
    incident_id: str,
    amendment: IncidentLogAmend,
    user: dict = Depends(require_admin)
):
    """Amend incident with audit trail"""
    db = get_db()
    
    incident = await db.incident_logs.find_one({"id": incident_id})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    amend_record = {
        "id": str(uuid.uuid4()),
        "entity_type": "incident_log",
        "entity_id": incident_id,
        "amended_by": user['user_id'],
        "amended_at": now,
        "reason": amendment.reason,
        "changes": {},
        "previous_values": {}
    }
    
    update_dict = {"updated_at": now}
    for field, value in amendment.model_dump(exclude_none=True, exclude={'reason'}).items():
        if field in incident and incident[field] != value:
            amend_record["changes"][field] = value
            amend_record["previous_values"][field] = incident[field]
            update_dict[field] = value
    
    if amend_record["changes"]:
        await db.amendments.insert_one(amend_record)
        await db.incident_logs.update_one({"id": incident_id}, {"$set": update_dict})
    
    updated = await db.incident_logs.find_one({"id": incident_id}, {"_id": 0})
    return updated


@router.get("/compliance/incidents/{incident_id}/history")
async def get_incident_history(incident_id: str, user: dict = Depends(require_admin)):
    """Get amendment history for an incident"""
    db = get_db()
    history = await db.amendments.find(
        {"entity_type": "incident_log", "entity_id": incident_id},
        {"_id": 0}
    ).sort("amended_at", -1).to_list(100)
    return {"history": history}


# ==================== COMPLIANCE REPORTS ====================

@router.get("/compliance/reports/staff-dbs")
async def get_staff_dbs_report(user: dict = Depends(require_admin)):
    """Get DBS compliance report for all staff"""
    db = get_db()
    
    employees = await db.employees.find(
        {"status": {"$in": ["onboarding", "active"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "dbs_status": 1, 
         "dbs_certificate_number": 1, "dbs_issue_date": 1, "dbs_update_service_registered": 1}
    ).to_list(1000)
    
    return {"employees": employees, "total": len(employees)}


@router.get("/compliance/reports/training")
async def get_training_compliance_report(user: dict = Depends(require_admin)):
    """Get training compliance report"""
    db = get_db()
    
    # Get all employees
    employees = await db.employees.find(
        {"status": {"$in": ["onboarding", "active"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1}
    ).to_list(1000)
    
    # Get training records
    training = await db.training_records.find(
        {"employee_id": {"$in": [e["id"] for e in employees]}},
        {"_id": 0}
    ).to_list(10000)
    
    # Group by employee
    training_by_emp = {}
    for t in training:
        emp_id = t.get("employee_id")
        if emp_id not in training_by_emp:
            training_by_emp[emp_id] = []
        training_by_emp[emp_id].append(t)
    
    for emp in employees:
        emp["training_records"] = training_by_emp.get(emp["id"], [])
        emp["training_count"] = len(emp["training_records"])
    
    return {"employees": employees, "total": len(employees)}
