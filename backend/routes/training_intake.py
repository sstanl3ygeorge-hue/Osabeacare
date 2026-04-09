"""
Training Intake Routes - Multi-Training Certificate Processing.

This module handles:
- Proposed training items from certificate extraction
- Training intake trigger for multi-certificate documents
- Email requests for training certificate uploads

Note: These routes MUST be registered BEFORE parameterized training routes
to avoid being shadowed by /training/{requirement_id}
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body

from .dependencies import (
    get_db, get_current_user, require_manager_or_admin
)

router = APIRouter(tags=["Training Intake"])


@router.get("/employees/{employee_id}/training/proposed-items")
async def get_proposed_training_items(
    employee_id: str,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get proposed training items awaiting review for an employee.
    Must be defined BEFORE parameterized training routes.
    """
    db = get_db()
    
    # Query directly since TrainingIntakeService is defined in server.py
    query = {"employee_id": employee_id}
    if status:
        query["status"] = status
    
    items = await db.proposed_training_items.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    # Enrich with source document info
    for item in items:
        doc_id = item.get("source_document_id")
        if doc_id:
            doc = await db.employee_documents.find_one(
                {"id": doc_id},
                {"_id": 0, "original_filename": 1, "file_url": 1, "uploaded_at": 1}
            )
            if doc:
                item["source_document"] = {
                    "filename": doc.get("original_filename"),
                    "url": doc.get("file_url"),
                    "uploaded_at": doc.get("uploaded_at")
                }
    
    return {"proposed_items": items, "total": len(items)}


@router.post("/employees/{employee_id}/training/request-certificates")
async def request_training_certificates(
    employee_id: str,
    due_days: int = Body(14, embed=True),
    message: Optional[str] = Body(None, embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Send email request to employee for training certificate upload.
    Must be defined BEFORE parameterized training routes.
    """
    db = get_db()
    
    # Import services from server (lazy import to avoid circular)
    from server import EmailRequestService, RequestType
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    context = {
        "employee_name": employee_name,
        "message": message
    }
    
    result = await EmailRequestService.create_request(
        person_id=employee_id,
        person_type="employee",
        request_type=RequestType.UPLOAD_TRAINING,
        requirement_id="training_certificates",
        template_variant="training_intake",
        due_days=due_days,
        context=context,
        admin_id=user.get("user_id")
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("reason"))
    
    return result


@router.post("/employees/{employee_id}/training/intake")
async def trigger_training_intake(
    employee_id: str,
    document_id: str = Body(..., embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Trigger multi-training extraction for a specific document.
    Must be defined BEFORE parameterized training routes.
    
    This endpoint calls TrainingIntakeService.extract_multi_training which:
    - Detects single/multi training certificates
    - Maps raw titles to internal training codes
    - Compares certificate holder name with employee name
    - Creates proposed_training_items for review
    """
    db = get_db()
    
    # Import TrainingIntakeService from server (lazy import to avoid circular)
    from server import TrainingIntakeService
    
    # First validate the document exists
    document = await db.employee_documents.find_one({"id": document_id}, {"_id": 0})
    if not document:
        # Try file_id fallback
        document = await db.employee_documents.find_one(
            {"evidence_files.file_id": document_id}, {"_id": 0}
        )
    
    if not document:
        # Check training_records
        training_doc = await db.training_records.find_one(
            {"$or": [{"id": document_id}, {"evidence_files.file_id": document_id}]},
            {"_id": 0}
        )
        if not training_doc:
            raise HTTPException(status_code=404, detail="Document not found")
    
    # Call TrainingIntakeService
    try:
        result = await TrainingIntakeService.extract_multi_training(document_id, employee_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except NameError:
        # TrainingIntakeService not yet defined (shouldn't happen at runtime)
        raise HTTPException(status_code=500, detail="TrainingIntakeService not available")
