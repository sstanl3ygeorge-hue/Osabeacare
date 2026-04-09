"""
Seed Data and Admin Cleanup Routes.

This module handles:
- Seeding initial document types
- Admin duplicate cleanup
- Employee data cleanup
- Training catalogue seeding
- System role fixes
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import (
    get_db, require_admin, log_audit_action
)

router = APIRouter(tags=["Seed Data & Cleanup"])


@router.post("/seed-data")
async def seed_data():
    """Seed initial document types based on care compliance checklist"""
    db = get_db()
    
    document_categories = [
        # Application Form
        {"name": "Application Form", "category": "Application", "required_before_active": True, "sort_order": 1},
        
        # Recruitment Checklist
        {"name": "New Starter Form", "category": "Recruitment", "required_before_active": True, "sort_order": 10},
        {"name": "Employment History", "category": "Recruitment", "required_before_active": True, "sort_order": 11},
        {"name": "Availability Form", "category": "Recruitment", "required_before_active": True, "sort_order": 12},
        {"name": "Interview Questions", "category": "Recruitment", "required_before_active": False, "sort_order": 13},
        
        # Personal Information
        {"name": "Proof of NI Number", "category": "Personal Information", "required_before_active": True, "sort_order": 20},
        {"name": "Proof of Address 1", "category": "Personal Information", "required_before_active": True, "sort_order": 21},
        {"name": "Proof of Address 2", "category": "Personal Information", "required_before_active": True, "sort_order": 22},
        {"name": "Proof of Bank Details", "category": "Personal Information", "required_before_active": True, "sort_order": 23},
        {"name": "Photo Proof of ID", "category": "Personal Information", "required_before_active": True, "sort_order": 24},
        {"name": "Passport Photo", "category": "Personal Information", "required_before_active": True, "sort_order": 25},
        
        # Identity & Right to Work
        {"name": "Right to Work in UK", "category": "Identity & Right to Work", "required_before_active": True, "has_expiry": True, "sort_order": 30},
        
        # References
        {"name": "Reference 1", "category": "References", "required_before_active": True, "sort_order": 40},
        {"name": "Reference 2", "category": "References", "required_before_active": True, "sort_order": 41},
        
        # Professional Documentation
        {"name": "CV", "category": "Professional", "required_before_active": False, "sort_order": 50},
        {"name": "Qualification Certificates", "category": "Professional", "required_before_active": False, "sort_order": 51},
        
        # DBS
        {"name": "DBS Certificate", "category": "DBS", "required_before_active": True, "has_expiry": True, "sort_order": 60},
        {"name": "DBS Update Service", "category": "DBS", "required_before_active": False, "has_expiry": True, "sort_order": 61},
        
        # Mandatory Training
        {"name": "Moving & Handling", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 70},
        {"name": "Basic Life Support", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 71},
        {"name": "Safeguarding Adults", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 72},
        {"name": "Safeguarding Children", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 73},
        {"name": "Infection Control", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 74},
        {"name": "Fire Safety", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 75},
        {"name": "Food Hygiene", "category": "Mandatory Training", "required_before_active": False, "has_expiry": True, "sort_order": 76},
        {"name": "Health & Safety", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 77},
        {"name": "GDPR/Data Protection", "category": "Mandatory Training", "required_before_active": True, "has_expiry": True, "sort_order": 78},
        
        # HR Forms
        {"name": "HMRC Starter Checklist", "category": "HR Forms", "required_before_active": True, "sort_order": 80},
        {"name": "Staff Health Questionnaire", "category": "HR Forms", "required_before_active": True, "sort_order": 81},
        {"name": "Staff Personal Information Form", "category": "HR Forms", "required_before_active": True, "sort_order": 82},
        {"name": "Equal Opportunities Form", "category": "HR Forms", "required_before_active": False, "sort_order": 83},
        
        # Contract
        {"name": "Employment Contract", "category": "Contract", "required_before_active": True, "sort_order": 90},
    ]
    
    inserted = 0
    for doc_type in document_categories:
        doc_id = doc_type["name"].lower().replace(" ", "_").replace("&", "and").replace("/", "_")
        existing = await db.document_types.find_one({"id": doc_id})
        if not existing:
            await db.document_types.insert_one({
                "id": doc_id,
                **doc_type,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            inserted += 1
    
    return {"message": f"Seeded {inserted} document types", "total_types": len(document_categories)}


@router.post("/admin/cleanup-duplicates")
async def cleanup_duplicate_documents(user: dict = Depends(require_admin)):
    """
    Find and resolve duplicate document records.
    Keeps the most recent verified version, supersedes others.
    """
    db = get_db()
    
    # Use global constant for consistency
    from server import EXCLUDED_DOC_STATUSES
    
    # Aggregation to find duplicates
    pipeline = [
        {"$match": {"status": {"$nin": EXCLUDED_DOC_STATUSES}}},
        {"$group": {
            "_id": {"employee_id": "$employee_id", "requirement_id": "$requirement_id"},
            "count": {"$sum": 1},
            "docs": {"$push": {"id": "$id", "uploaded_at": "$uploaded_at", "verified": "$verified"}}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicates = await db.employee_documents.aggregate(pipeline).to_list(500)
    
    fixed_count = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for dup in duplicates:
        docs = dup["docs"]
        
        # Sort: verified first, then by upload date (newest first)
        docs.sort(key=lambda x: (not x.get("verified", False), x.get("uploaded_at", "") or ""), reverse=True)
        
        # Keep the first one, supersede the rest
        keep_id = docs[0]["id"]
        for doc in docs[1:]:
            await db.employee_documents.update_one(
                {"id": doc["id"]},
                {"$set": {
                    "status": "superseded",
                    "superseded_at": now,
                    "superseded_by": keep_id,
                    "supersede_reason": "duplicate_cleanup"
                }}
            )
            fixed_count += 1
    
    await log_audit_action(user['user_id'], "cleanup_duplicates", "system", "all", {
        "duplicates_found": len(duplicates),
        "documents_superseded": fixed_count
    })
    
    return {
        "message": "Cleanup complete",
        "duplicates_found": len(duplicates),
        "documents_superseded": fixed_count
    }


@router.post("/admin/cleanup-employee/{employee_id}")
async def cleanup_employee_documents(
    employee_id: str,
    user: dict = Depends(require_admin)
):
    """
    Clean up an employee's documents:
    - Remove orphaned documents (no file_url)
    - Fix status inconsistencies
    - Resolve duplicates within this employee
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    changes = {"orphans_removed": 0, "status_fixed": 0, "duplicates_resolved": 0}
    
    # 1. Find orphaned documents (uploaded but no file)
    orphans = await db.employee_documents.find({
        "employee_id": employee_id,
        "$or": [
            {"file_url": None},
            {"file_url": ""},
            {"file_url": {"$exists": False}}
        ],
        "status": {"$nin": ["superseded", "deleted", "requested"]}
    }).to_list(100)
    
    for orphan in orphans:
        # Check if it's a form submission reference
        if orphan.get("form_submission_id") or orphan.get("source") == "form_submission":
            continue  # Keep form-based records
        
        await db.employee_documents.update_one(
            {"id": orphan["id"]},
            {"$set": {"status": "deleted", "deleted_at": now, "delete_reason": "orphan_cleanup"}}
        )
        changes["orphans_removed"] += 1
    
    # 2. Fix status inconsistencies
    inconsistent = await db.employee_documents.find({
        "employee_id": employee_id,
        "verified": True,
        "status": {"$nin": ["verified", "superseded"]}
    }).to_list(100)
    
    for doc in inconsistent:
        await db.employee_documents.update_one(
            {"id": doc["id"]},
            {"$set": {"status": "verified"}}
        )
        changes["status_fixed"] += 1
    
    # 3. Resolve duplicates
    pipeline = [
        {"$match": {"employee_id": employee_id, "status": {"$nin": ["superseded", "deleted"]}}},
        {"$group": {
            "_id": "$requirement_id",
            "count": {"$sum": 1},
            "docs": {"$push": {"id": "$id", "uploaded_at": "$uploaded_at", "verified": "$verified", "verification_stamp": "$verification_stamp"}}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicates = await db.employee_documents.aggregate(pipeline).to_list(100)
    
    for dup in duplicates:
        docs = dup["docs"]
        docs.sort(key=lambda x: (
            not x.get("verified", False),
            not bool(x.get("verification_stamp")),
            x.get("uploaded_at", "") or ""
        ), reverse=True)
        
        keep_id = docs[0]["id"]
        for doc in docs[1:]:
            await db.employee_documents.update_one(
                {"id": doc["id"]},
                {"$set": {
                    "status": "superseded",
                    "superseded_at": now,
                    "superseded_by": keep_id,
                    "supersede_reason": "employee_cleanup"
                }}
            )
            changes["duplicates_resolved"] += 1
    
    await log_audit_action(user['user_id'], "cleanup_employee", "employee", employee_id, changes)
    
    return {"success": True, "employee_id": employee_id, "changes": changes}


@router.post("/admin/training-catalogue/seed")
async def seed_training_catalogue(user: dict = Depends(require_admin)):
    """
    Seed the training catalogue with standard NHS/CQC training items.
    Creates training types that can be selected when adding training records.
    """
    db = get_db()
    
    training_items = [
        # Mandatory Training (CSTF)
        {"code": "manual_handling", "name": "Moving & Handling", "category": "Mandatory", "validity_months": 12, "is_mandatory": True},
        {"code": "bls", "name": "Basic Life Support (BLS)", "category": "Mandatory", "validity_months": 12, "is_mandatory": True},
        {"code": "safeguarding_adults", "name": "Safeguarding Adults", "category": "Mandatory", "validity_months": 36, "is_mandatory": True},
        {"code": "safeguarding_children", "name": "Safeguarding Children", "category": "Mandatory", "validity_months": 36, "is_mandatory": True},
        {"code": "infection_control", "name": "Infection Prevention & Control", "category": "Mandatory", "validity_months": 12, "is_mandatory": True},
        {"code": "fire_safety", "name": "Fire Safety", "category": "Mandatory", "validity_months": 12, "is_mandatory": True},
        {"code": "health_safety", "name": "Health & Safety", "category": "Mandatory", "validity_months": 12, "is_mandatory": True},
        {"code": "data_protection", "name": "GDPR/Data Protection", "category": "Mandatory", "validity_months": 12, "is_mandatory": True},
        {"code": "equality_diversity", "name": "Equality & Diversity", "category": "Mandatory", "validity_months": 36, "is_mandatory": True},
        {"code": "food_hygiene", "name": "Food Hygiene", "category": "Mandatory", "validity_months": 36, "is_mandatory": False},
        
        # Clinical/Specialist
        {"code": "medication", "name": "Medication Administration", "category": "Clinical", "validity_months": 12, "is_mandatory": False},
        {"code": "dementia", "name": "Dementia Awareness", "category": "Specialist", "validity_months": 36, "is_mandatory": False},
        {"code": "mental_health", "name": "Mental Health Awareness", "category": "Specialist", "validity_months": 36, "is_mandatory": False},
        {"code": "learning_disabilities", "name": "Learning Disabilities Awareness", "category": "Specialist", "validity_months": 36, "is_mandatory": False},
        {"code": "end_of_life", "name": "End of Life Care", "category": "Specialist", "validity_months": 36, "is_mandatory": False},
        {"code": "catheter_care", "name": "Catheter Care", "category": "Clinical", "validity_months": 24, "is_mandatory": False},
        {"code": "stoma_care", "name": "Stoma Care", "category": "Clinical", "validity_months": 24, "is_mandatory": False},
        {"code": "peg_feeding", "name": "PEG Feeding", "category": "Clinical", "validity_months": 24, "is_mandatory": False},
        {"code": "wound_care", "name": "Wound Care", "category": "Clinical", "validity_months": 24, "is_mandatory": False},
        {"code": "diabetes", "name": "Diabetes Management", "category": "Clinical", "validity_months": 24, "is_mandatory": False},
        {"code": "epilepsy", "name": "Epilepsy Management", "category": "Clinical", "validity_months": 24, "is_mandatory": False},
        
        # NHS Framework Compliance
        {"code": "hep_b", "name": "Hepatitis B Vaccination", "category": "NHS Compliance", "validity_months": 60, "is_mandatory": False},
        {"code": "oh_clearance", "name": "Occupational Health Clearance", "category": "NHS Compliance", "validity_months": 24, "is_mandatory": False},
        {"code": "fit_proper_persons", "name": "Fit & Proper Persons Declaration", "category": "NHS Compliance", "validity_months": 12, "is_mandatory": False},
        {"code": "care_certificate", "name": "Care Certificate", "category": "NHS Compliance", "validity_months": None, "is_mandatory": True},
        {"code": "whistleblowing", "name": "Whistleblowing Training", "category": "NHS Compliance", "validity_months": 36, "is_mandatory": False},
        {"code": "conflict_of_interest", "name": "Conflict of Interest Declaration", "category": "NHS Compliance", "validity_months": 12, "is_mandatory": False},
    ]
    
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for item in training_items:
        existing = await db.training_catalogue.find_one({"code": item["code"]})
        if not existing:
            await db.training_catalogue.insert_one({
                "id": str(uuid.uuid4()),
                **item,
                "created_at": now,
                "created_by": user['user_id']
            })
            inserted += 1
    
    return {"message": f"Seeded {inserted} training types", "total_types": len(training_items)}


@router.post("/admin/fix-system-roles")
async def fix_system_roles(user: dict = Depends(require_admin)):
    """
    Fix system_role field for all employees based on their declared role.
    Ensures consistent role categorization for work readiness calculations.
    """
    db = get_db()
    
    employees = await db.employees.find({}, {"_id": 0, "id": 1, "role": 1, "system_role": 1}).to_list(1000)
    
    fixed_count = 0
    
    for emp in employees:
        role = (emp.get("role") or "").lower()
        old_system_role = emp.get("system_role")
        
        # Determine correct system_role
        if "nurse" in role or "rgn" in role or "rmn" in role:
            system_role = "NURSE"
        else:
            system_role = "HCA"
        
        if old_system_role != system_role:
            await db.employees.update_one(
                {"id": emp["id"]},
                {"$set": {"system_role": system_role}}
            )
            fixed_count += 1
    
    await log_audit_action(user['user_id'], "fix_system_roles", "system", "all", {
        "employees_checked": len(employees),
        "roles_fixed": fixed_count
    })
    
    return {
        "message": f"Fixed {fixed_count} system roles",
        "employees_checked": len(employees),
        "roles_fixed": fixed_count
    }
