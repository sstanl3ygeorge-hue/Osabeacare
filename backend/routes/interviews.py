"""
Interview Management Routes Module

This module handles interview-related endpoints including:
- Interview configuration by role
- Interview records CRUD
- Pre-interview questionnaires
- Interview scoring and decisions
- PDF download for interview records

Extracted from server.py for modularity.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_user,
    require_manager_or_admin,
    log_audit_action,
)

# Import interview configuration from separate module
from interview_questions import get_role_interview_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interviews"])


# ==================== MODELS ====================

class InterviewRecordRequest(BaseModel):
    """Request model for creating/updating interview records"""
    interview_date: str
    interview_method: str  # phone, video, in_person
    interviewer_name: Optional[str] = None
    communication_score: int = 3  # 1-5 (V1 format)
    experience_score: int = 3  # 1-5 (V1 format)
    values_score: int = 3  # 1-5 (V1 format)
    availability: Optional[str] = None
    strengths: Optional[str] = None
    areas_for_development: Optional[str] = None
    decision: Optional[str] = None  # Approve, Reject, On Hold
    notes: Optional[str] = None
    is_draft: bool = False


class PreInterviewReviewRequest(BaseModel):
    """Request model for reviewing pre-interview questionnaire"""
    review_decision: str  # approved, concerns_noted, needs_discussion
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None


# ==================== INTERVIEW CONFIG ROUTES ====================

@router.get("/interview-config/{role}")
async def get_interview_config(
    role: str,
    user: dict = Depends(get_current_user)
):
    """
    Get interview configuration for a role.
    Returns questions, scoring criteria, and administrative questions.
    """
    config = get_role_interview_config(role)
    
    return {
        "role": role,
        "questions": config.get("questions", []),
        "administrative_questions": config.get("administrative_questions", []),
        "pre_employment_checks": config.get("pre_employment_checks", []),
        "scoring": config.get("scoring", {}),
        "question_count": config.get("question_count", 8),
        "max_possible_score": config.get("max_possible_score", 24),
        "pass_threshold_score": config.get("pass_threshold_score", 11),
        "scale_description": config.get("scale_description", "0-3 scale"),
    }


@router.get("/roles/{role}/interview-questions")
async def get_role_interview_questions(
    role: str,
    user: dict = Depends(get_current_user)
):
    """Get interview questions for a specific role."""
    config = get_role_interview_config(role)
    return {
        "role": role,
        "questions": config.get("questions", []),
        "administrative_questions": config.get("administrative_questions", []),
        "scoring": config.get("scoring", {})
    }


# ==================== INTERVIEW RECORDS ROUTES ====================

@router.get("/employees/{employee_id}/interview-records")
async def get_interview_records(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all interview records for an employee"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    records = await db.form_submissions.find({
        "employee_id": employee_id,
        "requirement_id": "interview_record"
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return {
        "stage": "admin_final_assessment",
        "stage_label": "Interview Assessment Record (Admin Only)",
        "depends_on": "worker_pre_screen",
        "records": records,
    }


@router.post("/employees/{employee_id}/interview-records")
async def create_interview_record(
    employee_id: str,
    request: Request,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new interview record - supports both V1 and V2 format"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    now = datetime.now(timezone.utc).isoformat()
    record_id = f"interview_{uuid.uuid4().hex[:12]}"
    
    # Detect format based on presence of question_scores (V2) or communication_score (V1)
    is_v2_format = "question_scores" in payload
    
    if is_v2_format:
        # V2 Format: Osabea 0-3 scoring with individual question scores
        question_scores = payload.get("question_scores", {})
        question_notes = payload.get("question_notes", {})
        
        # Calculate total score
        total_score = sum(int(s) for s in question_scores.values() if s is not None)
        max_score = len(question_scores) * 3 if question_scores else 24
        pass_score = 11
        percentage = round((total_score / max_score) * 100) if max_score > 0 else 0
        passed = total_score >= pass_score
        
        form_data = {
            "interview_date": payload.get("interview_date"),
            "interview_method": payload.get("interview_method", "in_person"),
            "interviewer_name": payload.get("interviewer_name") or user.get('name', 'System Admin'),
            "candidate_name": payload.get("candidate_name") or f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            "vacancy_job_title": payload.get("vacancy_job_title", "Care Worker"),
            "panel_members": payload.get("panel_members"),
            "question_scores": question_scores,
            "question_notes": question_notes,
            # Part 2 - Admin questions
            "requires_work_permit": payload.get("requires_work_permit"),
            "rtw_proof_taken": payload.get("rtw_proof_taken"),
            "hours_wanted": payload.get("hours_wanted"),
            "flexible_working": payload.get("flexible_working"),
            "has_driving_licence": payload.get("has_driving_licence"),
            "annual_leave_booked": payload.get("annual_leave_booked"),
            "notice_period": payload.get("notice_period"),
            "start_date": payload.get("start_date"),
            # Decision
            "decision": payload.get("decision"),
            "overall_impression": payload.get("overall_impression"),
            "candidate_questions": payload.get("candidate_questions"),
            "notes": payload.get("notes"),
            # Calculated
            "total_score": total_score,
            "max_score": max_score,
            "pass_score": pass_score,
            "passed": passed,
            "percentage": percentage,
            "format_version": "v2_osabea"
        }
    else:
        # V1 Format: Legacy 1-5 star scoring
        form_data = {
            "interview_date": payload.get("interview_date"),
            "interview_method": payload.get("interview_method"),
            "interviewer_name": payload.get("interviewer_name") or user.get('name', 'System Admin'),
            "communication_score": payload.get("communication_score", 3),
            "experience_score": payload.get("experience_score", 3),
            "values_score": payload.get("values_score", 3),
            "availability": payload.get("availability"),
            "strengths": payload.get("strengths"),
            "areas_for_development": payload.get("areas_for_development"),
            "decision": payload.get("decision"),
            "notes": payload.get("notes"),
            "is_draft": payload.get("is_draft", False),
            "format_version": "v1_legacy"
        }
    
    # Create the submission record
    is_draft = payload.get("is_draft", False)
    submission = {
        "id": record_id,
        "employee_id": employee_id,
        "requirement_id": "interview_record",
        "form_type": "interview_record",
        "form_data": form_data,
        "data": form_data,
        # Admin-authored form: signing off on create removes the compliance-file blocker.
        # Drafts stay as "draft"; anything else is treated as completed by the interviewer.
        "status": "draft" if is_draft else "signed_off",
        "verified": not is_draft,
        "verified_by": user.get("user_id") if not is_draft else None,
        "verified_at": now if not is_draft else None,
        "submitted_at": now,
        "submitted_by": user.get("user_id"),
        "created_at": now,
        "updated_at": now,
        "version": 1
    }
    
    await db.form_submissions.insert_one(submission)
    
    # If decision is Approve, update employee status
    if form_data.get("decision") == "Approve" and not payload.get("is_draft"):
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "interview_passed": True,
                "interview_passed_at": now,
                "interview_passed_by": user.get("user_id"),
                "updated_at": now
            }}
        )
    
    await log_audit_action(
        user['user_id'],
        "create_interview_record",
        "interview_record",
        record_id,
        {"employee_id": employee_id, "decision": form_data.get("decision")}
    )
    
    return {
        "id": record_id,
        "message": "Interview assessment record created",
        "stage": "admin_final_assessment",
        "status": submission["status"],
        "decision": form_data.get("decision")
    }


# ==================== PRE-INTERVIEW QUESTIONNAIRE ====================

@router.get("/employees/{employee_id}/pre-interview-questionnaire")
async def get_pre_interview_questionnaire(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """Get pre-interview questionnaire responses for an employee"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check for form submission
    questionnaire = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "requirement_id": "pre_interview_questionnaire"
    }, {"_id": 0})
    
    if not questionnaire:
        # Return empty questionnaire structure
        return {
            "employee_id": employee_id,
            "stage": "worker_pre_screen",
            "stage_label": "Pre-Interview Questionnaire (Worker)",
            "status": "not_submitted",
            "form_data": None
        }
    
    return {
        "employee_id": employee_id,
        "stage": "worker_pre_screen",
        "stage_label": "Pre-Interview Questionnaire (Worker)",
        "next_stage": "admin_final_assessment",
        "status": questionnaire.get("status", "submitted"),
        "form_data": questionnaire.get("form_data") or questionnaire.get("data"),
        "submitted_at": questionnaire.get("submitted_at"),
        "review_status": questionnaire.get("review_status"),
        "reviewed_at": questionnaire.get("reviewed_at"),
        "reviewed_by": questionnaire.get("reviewed_by"),
        "reviewer_notes": questionnaire.get("reviewer_notes")
    }


@router.post("/employees/{employee_id}/pre-interview-questionnaire/review")
async def review_pre_interview_questionnaire(
    employee_id: str,
    review: PreInterviewReviewRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """Review pre-interview questionnaire submission"""
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    questionnaire = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "requirement_id": "pre_interview_questionnaire"
    })
    
    if not questionnaire:
        raise HTTPException(status_code=404, detail="Pre-interview questionnaire not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.form_submissions.update_one(
        {"id": questionnaire["id"]},
        {"$set": {
            "review_status": review.review_decision,
            "reviewed_at": now,
            "reviewed_by": review.reviewed_by or user.get("user_id"),
            "reviewer_notes": review.reviewer_notes,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "review_pre_interview_questionnaire",
        "form_submission",
        questionnaire["id"],
        {"employee_id": employee_id, "decision": review.review_decision}
    )
    
    return {
        "message": "Pre-interview questionnaire reviewed",
        "stage": "worker_pre_screen",
        "next_stage": "admin_final_assessment",
        "review_status": review.review_decision
    }
