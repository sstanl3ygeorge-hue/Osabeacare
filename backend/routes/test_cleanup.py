"""
Test Data Cleanup Routes.

This module handles:
- Cleaning up test data from employee records
- Bulk test data cleanup across all employees
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .dependencies import (
    get_db, require_admin, log_audit_action
)

router = APIRouter(tags=["Test Data Cleanup"])


class TestDataCleanupRequest(BaseModel):
    """Request model for test data cleanup"""
    remove_employment_history: Optional[List[str]] = None  # List of employer names to remove
    reset_contract: bool = False
    remove_test_forms: bool = False
    clear_all_test_data: bool = False  # Nuclear option - removes all test-like data


@router.post("/employees/{employee_id}/cleanup-test-data")
async def cleanup_employee_test_data(
    employee_id: str,
    payload: TestDataCleanupRequest,
    user: dict = Depends(require_admin)
):
    """
    Clean up test data from an employee's record.
    Use this to remove dummy/test data created during development.
    
    Options:
    - remove_employment_history: List of employer names to remove (e.g., ["Care Home A", "Care Home B"])
    - reset_contract: Remove contract_signed status (re-enables contract gating)
    - remove_test_forms: Remove test form submissions
    - clear_all_test_data: Auto-detect and remove common test patterns
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    changes_made = []
    
    # 1. Remove specified employment history entries
    if payload.remove_employment_history:
        current_history = employee.get("employment_history", [])
        names_to_remove = [n.lower() for n in payload.remove_employment_history]
        
        new_history = [
            h for h in current_history 
            if h.get("employer_name", "").lower() not in names_to_remove
        ]
        
        removed_count = len(current_history) - len(new_history)
        if removed_count > 0:
            await db.employees.update_one(
                {"id": employee_id},
                {"$set": {"employment_history": new_history}}
            )
            changes_made.append(f"Removed {removed_count} employment history entries")
    
    # 2. Reset contract status
    if payload.reset_contract:
        await db.employees.update_one(
            {"id": employee_id},
            {"$unset": {
                "contract_signed": "",
                "contract_signed_at": "",
                "contract_signed_by": "",
                "contract_pdf_url": "",
                "contract_version": ""
            }}
        )
        
        # Also delete contract documents
        await db.employee_documents.delete_many({
            "employee_id": employee_id,
            "requirement_id": {"$regex": "contract", "$options": "i"}
        })
        
        changes_made.append("Reset contract status")
    
    # 3. Remove test form submissions
    if payload.remove_test_forms:
        test_patterns = ["test", "dummy", "sample", "example"]
        
        deleted = await db.form_submissions.delete_many({
            "employee_id": employee_id,
            "$or": [
                {"data.test_submission": True},
                {"submitted_by_name": {"$regex": "|".join(test_patterns), "$options": "i"}}
            ]
        })
        
        if deleted.deleted_count > 0:
            changes_made.append(f"Removed {deleted.deleted_count} test form submissions")
    
    # 4. Clear all test-like data (nuclear option)
    if payload.clear_all_test_data:
        test_patterns = ["test", "dummy", "sample", "example", "demo", "fake"]
        
        # Clear test employment history
        current_history = employee.get("employment_history", [])
        new_history = [
            h for h in current_history 
            if not any(p in (h.get("employer_name", "") or "").lower() for p in test_patterns)
        ]
        
        if len(new_history) != len(current_history):
            await db.employees.update_one(
                {"id": employee_id},
                {"$set": {"employment_history": new_history}}
            )
            changes_made.append(f"Removed {len(current_history) - len(new_history)} test employment entries")
        
        # Clear test documents
        deleted_docs = await db.employee_documents.delete_many({
            "employee_id": employee_id,
            "$or": [
                {"original_filename": {"$regex": "|".join(test_patterns), "$options": "i"}},
                {"notes": {"$regex": "|".join(test_patterns), "$options": "i"}}
            ]
        })
        
        if deleted_docs.deleted_count > 0:
            changes_made.append(f"Removed {deleted_docs.deleted_count} test documents")
    
    await log_audit_action(user['user_id'], "cleanup_test_data", "employee", employee_id, {
        "changes": changes_made
    })
    
    return {
        "success": True,
        "employee_id": employee_id,
        "changes_made": changes_made,
        "message": f"Cleanup complete: {len(changes_made)} changes made"
    }


@router.post("/admin/bulk-cleanup-test-data")
async def bulk_cleanup_test_data(user: dict = Depends(require_admin)):
    """
    Clean up common test data patterns across ALL employees.
    
    This removes:
    - Employment history entries with common test employer names
    - Contract status for test employees
    - Test form submissions
    
    Use with caution - this affects all employees.
    """
    db = get_db()
    
    test_employer_patterns = [
        "care home a", "care home b", "test care", "demo care",
        "sample employer", "fake company", "example org"
    ]
    
    updated_count = 0
    
    # Find employees with test employment history
    employees = await db.employees.find(
        {"employment_history": {"$exists": True, "$ne": []}},
        {"_id": 0, "id": 1, "employment_history": 1}
    ).to_list(1000)
    
    for emp in employees:
        current_history = emp.get("employment_history", [])
        new_history = [
            h for h in current_history 
            if not any(p in (h.get("employer_name", "") or "").lower() for p in test_employer_patterns)
        ]
        
        if len(new_history) != len(current_history):
            await db.employees.update_one(
                {"id": emp["id"]},
                {"$set": {"employment_history": new_history}}
            )
            updated_count += 1
    
    # Reset contracts for test employees (those with "test" in email)
    test_contracts = await db.employees.update_many(
        {"email": {"$regex": "test", "$options": "i"}},
        {"$unset": {
            "contract_signed": "",
            "contract_signed_at": "",
            "contract_pdf_url": ""
        }}
    )
    
    await log_audit_action(user['user_id'], "bulk_cleanup_test_data", "system", "all", {
        "employees_cleaned": updated_count,
        "contracts_reset": test_contracts.modified_count
    })
    
    return {
        "success": True,
        "employees_cleaned": updated_count,
        "contracts_reset": test_contracts.modified_count,
        "message": f"Cleaned {updated_count} employee records, reset {test_contracts.modified_count} test contracts"
    }
