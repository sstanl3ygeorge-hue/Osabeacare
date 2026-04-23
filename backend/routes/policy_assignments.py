"""
Policy Assignments Routes Module

This module handles policy assignment-related endpoints including:
- Listing policy assignments
- Marking policies as viewed
- Employee acknowledgement of policies
- Admin review of acknowledgements
- Unassigning and withdrawing policies

CQC Requirement: Staff must read and acknowledge all relevant policies.

Extracted from server.py for modularity.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .dependencies import (
    get_db,
    get_current_user,
    require_admin,
    require_manager_or_admin,
    log_audit_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Policy Assignments"])


# ==================== MODELS ====================

class PolicyAssignmentResponse(BaseModel):
    """Response model for policy assignment"""
    model_config = ConfigDict(extra="ignore")
    id: str
    policy_id: str
    policy_title: Optional[str] = None
    policy_version: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    assigned_at: str
    assigned_by: Optional[str] = None
    assigned_by_name: Optional[str] = None
    status: str  # assigned -> viewed -> acknowledged -> unassigned -> withdrawn
    viewed_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    acknowledged_by_employee_name: Optional[str] = None
    # Admin review fields
    admin_reviewed: bool = False
    admin_reviewed_at: Optional[str] = None
    admin_reviewed_by: Optional[str] = None
    admin_reviewed_by_name: Optional[str] = None
    # Reversal fields
    unassigned_at: Optional[str] = None
    unassigned_by: Optional[str] = None
    unassigned_by_name: Optional[str] = None
    unassigned_reason: Optional[str] = None
    withdrawn_at: Optional[str] = None
    withdrawn_by: Optional[str] = None
    withdrawn_by_name: Optional[str] = None
    withdrawn_reason: Optional[str] = None


class PolicyReversalRequest(BaseModel):
    """Request model for unassigning or withdrawing a policy"""
    reason: Optional[str] = None


class PolicyAcknowledgeRequest(BaseModel):
    """Request model for policy acknowledgement metadata."""
    signer_name: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.get("/policy-assignments", response_model=List[PolicyAssignmentResponse])
async def get_policy_assignments(
    employee_id: Optional[str] = None,
    policy_id: Optional[str] = None,
    status: Optional[str] = None,
    include_inactive: bool = False,
    user: dict = Depends(get_current_user)
):
    """Get policy assignments with optional filters."""
    db = get_db()
    
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if policy_id:
        query["policy_id"] = policy_id
    if status:
        query["status"] = status
    elif not include_inactive:
        # By default, exclude unassigned and withdrawn
        query["status"] = {"$nin": ["unassigned", "withdrawn"]}
    
    assignments = await db.policy_assignments.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with employee names and policy info if missing
    for a in assignments:
        if not a.get('employee_name'):
            emp = await db.employees.find_one({"id": a['employee_id']}, {"_id": 0})
            if emp:
                a['employee_name'] = f"{emp['first_name']} {emp['last_name']}"
        # Ensure policy_version is present
        if not a.get('policy_version'):
            policy = await db.policies.find_one({"id": a['policy_id']}, {"_id": 0})
            if policy:
                a['policy_version'] = policy.get('version', '1.0')
    
    return [PolicyAssignmentResponse(**a) for a in assignments]


@router.put("/policy-assignments/{assignment_id}/view")
async def mark_policy_viewed(
    assignment_id: str,
    user: dict = Depends(get_current_user)
):
    """Mark a policy assignment as viewed by the employee."""
    db = get_db()
    
    assignment = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Only update viewed_at if not already viewed
    if not assignment.get('viewed_at'):
        update_data = {
            "viewed_at": now,
            "status": "viewed" if assignment.get('status') == 'assigned' else assignment.get('status')
        }
        await db.policy_assignments.update_one({"id": assignment_id}, {"$set": update_data})
        
        await log_audit_action(
            user['user_id'], 
            "policy_viewed", 
            "policy_assignment", 
            assignment_id, 
            {
                "policy_id": assignment['policy_id'],
                "policy_title": assignment.get('policy_title'),
                "employee_id": assignment['employee_id']
            }
        )
    
    updated = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    return PolicyAssignmentResponse(**updated)


@router.put("/policy-assignments/{assignment_id}/acknowledge")
async def acknowledge_policy(
    assignment_id: str,
    request: Optional[PolicyAcknowledgeRequest] = None,
    user: dict = Depends(get_current_user)
):
    """
    Employee acknowledges policy - "I have read and understood this policy"
    Stores: employee_id, policy_id, policy_version, acknowledged_at
    """
    db = get_db()
    
    assignment = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Check if already acknowledged
    if assignment.get('status') == 'acknowledged':
        raise HTTPException(status_code=400, detail="Policy already acknowledged")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get employee name for audit trail
    emp = await db.employees.find_one({"id": assignment['employee_id']}, {"_id": 0})
    emp_name = f"{emp['first_name']} {emp['last_name']}" if emp else "Unknown"
    signer_name = (request.signer_name.strip() if request and request.signer_name else None) or emp_name
    
    update_data = {
        "status": "acknowledged",
        "acknowledged_at": now,
        "acknowledged_by_employee_name": signer_name
    }
    
    # Also mark as viewed if not already
    if not assignment.get('viewed_at'):
        update_data['viewed_at'] = now
    
    await db.policy_assignments.update_one({"id": assignment_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'], 
        "policy_acknowledged", 
        "policy_assignment", 
        assignment_id, 
        {
            "policy_id": assignment['policy_id'],
            "policy_title": assignment.get('policy_title'),
            "policy_version": assignment.get('policy_version'),
            "employee_id": assignment['employee_id'],
            "employee_name": signer_name,
            "acknowledged_at": now
        }
    )
    
    updated = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    return PolicyAssignmentResponse(**updated)


@router.get("/policy-assignments/{assignment_id}/acknowledgement-pdf")
async def export_policy_acknowledgement_pdf(
    assignment_id: str,
    user: dict = Depends(get_current_user)
):
    """Export acknowledgement summary PDF for an acknowledged policy assignment."""
    db = get_db()

    assignment = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.get("status") not in ["acknowledged", "signed", "withdrawn"]:
        raise HTTPException(status_code=400, detail="Policy must be acknowledged before export")

    policy = await db.policies.find_one({"id": assignment.get("policy_id")}, {"_id": 0})
    employee = await db.employees.find_one({"id": assignment.get("employee_id")}, {"_id": 0})

    employee_name = assignment.get("acknowledged_by_employee_name") or assignment.get("employee_name")
    if not employee_name and employee:
        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()

    policy_title = assignment.get("policy_title") or (policy.get("title") if policy else "Policy")
    policy_version = assignment.get("policy_version") or (policy.get("version") if policy else "1.0")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 60
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Policy Acknowledgement Record")

    y -= 30
    pdf.setFont("Helvetica", 11)
    rows = [
        ("Policy Title", policy_title or "-"),
        ("Policy Version", str(policy_version or "-")),
        ("Employee", employee_name or "-"),
        ("Employee ID", assignment.get("employee_id") or "-"),
        ("Acknowledged At", assignment.get("acknowledged_at") or "-"),
        ("Assignment Status", assignment.get("status") or "-"),
        ("Admin Reviewed", "Yes" if assignment.get("admin_reviewed") else "No"),
        ("Admin Reviewed At", assignment.get("admin_reviewed_at") or "-"),
    ]

    for label, value in rows:
        if y < 90:
            pdf.showPage()
            y = height - 60
            pdf.setFont("Helvetica", 11)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y, f"{label}:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(190, y, str(value))
        y -= 22

    y -= 10
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(50, y, "Generated by Osabea Compliance Portal")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = f"policy_ack_{assignment_id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/policy-assignments/{assignment_id}/admin-review")
async def admin_review_policy(
    assignment_id: str,
    user: dict = Depends(require_admin)
):
    """
    Admin reviews and approves the policy acknowledgement.
    Stores: admin_id, reviewed_at, admin_name
    """
    db = get_db()
    
    assignment = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Policy must be acknowledged before admin review
    if assignment.get('status') != 'acknowledged':
        raise HTTPException(status_code=400, detail="Policy must be acknowledged by employee first")
    
    now = datetime.now(timezone.utc).isoformat()
    admin_name = user.get('name', user.get('email', 'Admin'))
    
    update_data = {
        "admin_reviewed": True,
        "admin_reviewed_at": now,
        "admin_reviewed_by": user['user_id'],
        "admin_reviewed_by_name": admin_name
    }
    
    await db.policy_assignments.update_one({"id": assignment_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'], 
        "policy_admin_reviewed", 
        "policy_assignment", 
        assignment_id, 
        {
            "policy_id": assignment['policy_id'],
            "policy_title": assignment.get('policy_title'),
            "employee_id": assignment['employee_id'],
            "employee_name": assignment.get('employee_name'),
            "admin_name": admin_name,
            "reviewed_at": now
        }
    )
    
    updated = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    return PolicyAssignmentResponse(**updated)


@router.put("/policy-assignments/{assignment_id}/unassign")
async def unassign_policy(
    assignment_id: str, 
    request: PolicyReversalRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Unassign a policy BEFORE it has been acknowledged.
    For policies not yet acknowledged, simply marks as unassigned.
    """
    db = get_db()
    
    assignment = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Can only unassign if not yet acknowledged
    if assignment.get('status') in ['acknowledged', 'signed']:
        raise HTTPException(
            status_code=400, 
            detail="Cannot unassign acknowledged policy. Use 'Withdraw' action instead."
        )
    
    if assignment.get('status') == 'unassigned':
        raise HTTPException(status_code=400, detail="Policy is already unassigned")
    
    now = datetime.now(timezone.utc).isoformat()
    user_doc = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Admin')) if user_doc else user.get('email', 'Admin')
    
    previous_status = assignment.get('status')
    
    update_data = {
        "status": "unassigned",
        "unassigned_at": now,
        "unassigned_by": user['user_id'],
        "unassigned_by_name": user_name,
        "unassigned_reason": request.reason.strip() if request.reason else None
    }
    
    await db.policy_assignments.update_one({"id": assignment_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'], 
        "policy_unassigned", 
        "policy_assignment", 
        assignment_id, 
        {
            "policy_id": assignment['policy_id'],
            "policy_title": assignment.get('policy_title'),
            "policy_version": assignment.get('policy_version'),
            "employee_id": assignment['employee_id'],
            "employee_name": assignment.get('employee_name'),
            "previous_status": previous_status,
            "new_status": "unassigned",
            "unassigned_by_name": user_name,
            "reason": request.reason.strip() if request.reason else None
        }
    )
    
    updated = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    return PolicyAssignmentResponse(**updated)


@router.put("/policy-assignments/{assignment_id}/withdraw")
async def withdraw_policy(
    assignment_id: str, 
    request: PolicyReversalRequest,
    user: dict = Depends(require_admin)
):
    """
    Withdraw a policy AFTER it has been acknowledged.
    Preserves the acknowledgement history but marks as withdrawn.
    Only admins can withdraw acknowledged policies.
    """
    db = get_db()
    
    assignment = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Can only withdraw if acknowledged
    if assignment.get('status') not in ['acknowledged', 'signed']:
        raise HTTPException(
            status_code=400, 
            detail="Can only withdraw acknowledged policies. Use 'Unassign' for pending policies."
        )
    
    if assignment.get('status') == 'withdrawn':
        raise HTTPException(status_code=400, detail="Policy is already withdrawn")
    
    now = datetime.now(timezone.utc).isoformat()
    user_doc = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Admin')) if user_doc else user.get('email', 'Admin')
    
    previous_status = assignment.get('status')
    
    update_data = {
        "status": "withdrawn",
        "withdrawn_at": now,
        "withdrawn_by": user['user_id'],
        "withdrawn_by_name": user_name,
        "withdrawn_reason": request.reason.strip() if request.reason else None
    }
    
    await db.policy_assignments.update_one({"id": assignment_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'], 
        "policy_withdrawn", 
        "policy_assignment", 
        assignment_id, 
        {
            "policy_id": assignment['policy_id'],
            "policy_title": assignment.get('policy_title'),
            "policy_version": assignment.get('policy_version'),
            "employee_id": assignment['employee_id'],
            "employee_name": assignment.get('employee_name'),
            "previous_status": previous_status,
            "new_status": "withdrawn",
            "acknowledged_at": assignment.get('acknowledged_at'),
            "acknowledged_by": assignment.get('acknowledged_by_employee_name'),
            "withdrawn_by_name": user_name,
            "reason": request.reason.strip() if request.reason else None
        }
    )
    
    updated = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    return PolicyAssignmentResponse(**updated)
