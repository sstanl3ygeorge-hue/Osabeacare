"""
Admin Task Queue Routes.

This module handles:
- Centralized admin task dashboard
- Pending verifications tracking
- Expiring documents alerts
- References awaiting review
- Scheduled assessments
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends

from .dependencies import get_db, get_current_user

router = APIRouter(tags=["Task Queue"])


@router.get("/admin/task-queue")
async def get_admin_task_queue(
    user: dict = Depends(get_current_user)
):
    """
    Get all pending admin tasks across all employees.
    Used for dashboard task summary and actionable task list.
    """
    db = get_db()
    
    now = datetime.now(timezone.utc)
    thirty_days_later = now + timedelta(days=30)
    seven_days_later = now + timedelta(days=7)
    
    # 1. Documents awaiting verification (no valid stamp)
    docs_pending = await db.employee_documents.find({
        "$or": [
            {"verification_stamp": {"$in": [None, "", "not_verified"]}},
            {"verification_stamp": {"$exists": False}}
        ],
        "status": {"$in": ["active", "uploaded", "approved", "accepted"]}
    }, {"_id": 0, "id": 1, "employee_id": 1, "document_type": 1, "uploaded_at": 1, "requirement_id": 1}).to_list(100)
    
    # Enrich with employee names
    pending_verifications = []
    for doc in docs_pending[:10]:
        emp = await db.employees.find_one({"id": doc.get("employee_id")}, {"_id": 0, "first_name": 1, "last_name": 1})
        if emp:
            pending_verifications.append({
                "type": "verification",
                "id": doc.get("id"),
                "employee_id": doc.get("employee_id"),
                "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                "document_type": doc.get("document_type") or doc.get("requirement_id"),
                "uploaded_at": doc.get("uploaded_at"),
                "priority": "high"
            })
    
    # 2. Expiring documents (next 30 days) - use global constant for sync
    from server import EXCLUDED_DOC_STATUSES
    expiring_docs = await db.employee_documents.find({
        "expiry_date": {"$lte": thirty_days_later.isoformat(), "$gte": now.isoformat()},
        "status": {"$nin": EXCLUDED_DOC_STATUSES}
    }, {"_id": 0, "id": 1, "employee_id": 1, "requirement_id": 1, "expiry_date": 1}).to_list(50)
    
    expiring_items = []
    for doc in expiring_docs[:10]:
        emp = await db.employees.find_one({"id": doc.get("employee_id")}, {"_id": 0, "first_name": 1, "last_name": 1})
        if emp:
            try:
                exp_date = datetime.fromisoformat(doc.get("expiry_date", "").replace('Z', '+00:00'))
                days_until = (exp_date - now).days
            except (ValueError, TypeError):
                days_until = 30
            
            expiring_items.append({
                "type": "expiring",
                "id": doc.get("id"),
                "employee_id": doc.get("employee_id"),
                "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                "document_type": doc.get("requirement_id"),
                "expiry_date": doc.get("expiry_date"),
                "days_until": days_until,
                "priority": "critical" if days_until <= 7 else "high" if days_until <= 14 else "medium"
            })
    
    # 3. References awaiting review — query canonical db.references collection
    refs_docs = await db.references.find({
        "$or": [
            {"ref1.verification.status": {"$nin": ["verified", "rejected"]}},
            {"ref2.verification.status": {"$nin": ["verified", "rejected"]}}
        ]
    }, {"_id": 0, "employee_id": 1, "ref1": 1, "ref2": 1}).to_list(50)

    pending_references = []
    for ref_doc in refs_docs:
        emp = await db.employees.find_one(
            {"id": ref_doc.get("employee_id")},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if not emp:
            continue
        emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        for ref_num, ref_key in [(1, "ref1"), (2, "ref2")]:
            ref_data = ref_doc.get(ref_key) or {}
            verif_status = ref_data.get("verification", {}).get("status")
            if ref_data and verif_status not in ("verified", "rejected"):
                pending_references.append({
                    "type": "reference",
                    "id": f"{ref_doc.get('employee_id')}_ref{ref_num}",
                    "employee_id": ref_doc.get("employee_id"),
                    "employee_name": emp_name,
                    "reference_num": ref_num,
                    "priority": "high"
                })
    
    # 4. Scheduled spot checks due this week
    upcoming_spot_checks = await db.spot_checks.find({
        "status": "scheduled",
        "scheduled_date": {"$lte": seven_days_later.strftime('%Y-%m-%d')}
    }, {"_id": 0}).to_list(20)
    
    scheduled_tasks = []
    for check in upcoming_spot_checks:
        scheduled_tasks.append({
            "type": "spot_check",
            "id": check.get("id"),
            "employee_id": check.get("employee_id"),
            "employee_name": check.get("employee_name"),
            "scheduled_date": check.get("scheduled_date"),
            "check_type": check.get("type"),
            "area": check.get("area"),
            "priority": "medium"
        })
    
    # 5. Scheduled competency assessments due this week
    upcoming_competencies = await db.competency_records.find({
        "status": "scheduled",
        "scheduled_date": {"$lte": seven_days_later.strftime('%Y-%m-%d')}
    }, {"_id": 0}).to_list(20)
    
    for comp in upcoming_competencies:
        emp = await db.employees.find_one({"id": comp.get("employee_id")}, {"_id": 0, "first_name": 1, "last_name": 1})
        emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() if emp else "Unknown"
        scheduled_tasks.append({
            "type": "competency_assessment",
            "id": comp.get("id"),
            "employee_id": comp.get("employee_id"),
            "employee_name": emp_name,
            "scheduled_date": comp.get("scheduled_date"),
            "competency_type": comp.get("competency_type"),
            "priority": "medium"
        })
    
    # 6. Follow-ups due (spot checks with follow_up_required and date passed)
    overdue_followups = await db.spot_checks.find({
        "follow_up_required": True,
        "follow_up_completed": {"$ne": True},
        "follow_up_date": {"$lte": now.strftime('%Y-%m-%d')}
    }, {"_id": 0}).to_list(20)
    
    followup_tasks = []
    for fu in overdue_followups:
        followup_tasks.append({
            "type": "followup",
            "id": fu.get("id"),
            "employee_id": fu.get("employee_id"),
            "employee_name": fu.get("employee_name"),
            "follow_up_date": fu.get("follow_up_date"),
            "original_check_type": fu.get("type"),
            "original_outcome": fu.get("outcome"),
            "priority": "high"
        })
    
    # Combine and sort all tasks
    all_tasks = (
        pending_verifications + 
        expiring_items + 
        pending_references + 
        scheduled_tasks + 
        followup_tasks
    )
    
    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_tasks.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
    
    return {
        "total_tasks": len(all_tasks),
        "tasks": all_tasks,
        "summary": {
            "pending_verifications": len(pending_verifications),
            "expiring_documents": len(expiring_items),
            "pending_references": len(pending_references),
            "scheduled_tasks": len(scheduled_tasks),
            "overdue_followups": len(followup_tasks)
        },
        "generated_at": now.isoformat()
    }


@router.get("/employees/{employee_id}/recent-uploads")
async def get_recent_uploads(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get recent uploads for an employee (documents, training, forms).
    Used for "What's New" sidebar in employee view.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Last 30 days
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    # Documents - use global constant for sync
    from server import EXCLUDED_DOC_STATUSES, EXCLUDED_TRAINING_STATUSES
    docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "uploaded_at": {"$gte": thirty_days_ago},
        "status": {"$nin": EXCLUDED_DOC_STATUSES}
    }, {"_id": 0, "id": 1, "requirement_id": 1, "document_type": 1, "uploaded_at": 1, "original_filename": 1}).sort("uploaded_at", -1).to_list(20)
    
    # Training records
    trainings = await db.training_records.find({
        "employee_id": employee_id,
        "created_at": {"$gte": thirty_days_ago},
        "record_status": {"$nin": EXCLUDED_TRAINING_STATUSES}
    }, {"_id": 0, "id": 1, "training_name": 1, "created_at": 1, "status": 1}).sort("created_at", -1).to_list(20)
    
    # Form submissions
    forms = await db.form_submissions.find({
        "employee_id": employee_id,
        "submitted_at": {"$gte": thirty_days_ago}
    }, {"_id": 0, "id": 1, "form_type": 1, "submitted_at": 1}).sort("submitted_at", -1).to_list(20)
    
    # Combine and format
    items = []
    
    for doc in docs:
        items.append({
            "type": "document",
            "id": doc.get("id"),
            "name": doc.get("original_filename") or doc.get("requirement_id") or doc.get("document_type") or "Document",
            "uploaded_at": doc.get("uploaded_at"),
            "tab": "documents"
        })
    
    for tr in trainings:
        items.append({
            "type": "training",
            "id": tr.get("id"),
            "name": tr.get("training_name") or "Training",
            "uploaded_at": tr.get("created_at"),
            "status": tr.get("status"),
            "tab": "training"
        })
    
    for form in forms:
        items.append({
            "type": "form",
            "id": form.get("id"),
            "name": form.get("form_type", "").replace("_", " ").title() or "Form",
            "uploaded_at": form.get("submitted_at"),
            "tab": "forms"
        })
    
    # Sort by upload date (most recent first)
    items.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
    
    return {
        "employee_id": employee_id,
        "total": len(items),
        "items": items
    }
