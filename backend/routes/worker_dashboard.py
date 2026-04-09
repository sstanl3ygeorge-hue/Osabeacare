"""
Worker Dashboard routes for worker self-service portal.

Handles:
- Worker compliance dashboard
- Worker document uploads
- Worker reminder emails (admin action)
- Worker forms (list, get, save, submit)
"""

import os
import uuid
import logging
import asyncio
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Header
from pydantic import BaseModel

from .dependencies import (
    get_db,
    get_current_worker,
    require_manager_or_admin,
    log_audit_action,
    JWT_SECRET,
    SENDER_EMAIL
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["Worker Dashboard"])


# ==================== PYDANTIC MODELS ====================
class SendReminderRequest(BaseModel):
    custom_message: Optional[str] = None


class FormSaveRequest(BaseModel):
    form_data: dict


class FormSubmitRequest(BaseModel):
    form_data: dict


# ==================== LAZY IMPORTS ====================
# Avoid circular imports by importing heavy dependencies lazily

def get_worker_form_definitions():
    """Lazy import of WORKER_FORM_DEFINITIONS from server.py"""
    from server import WORKER_FORM_DEFINITIONS
    return WORKER_FORM_DEFINITIONS


def get_form_based_requirements():
    """Lazy import of FORM_BASED_REQUIREMENTS from server.py"""
    from server import FORM_BASED_REQUIREMENTS
    return FORM_BASED_REQUIREMENTS


def get_mandatory_items():
    """Lazy import of MANDATORY_ITEMS from server.py"""
    from server import MANDATORY_ITEMS
    return MANDATORY_ITEMS


def get_unified_employee_status_func():
    """Lazy import of get_unified_employee_status from unified_compliance_engine"""
    from unified_compliance_engine import get_unified_employee_status
    return get_unified_employee_status


def get_unified_progress_func():
    """Lazy import of get_unified_progress from server.py"""
    from server import get_unified_progress
    return get_unified_progress


def get_validate_file_content_func():
    """Lazy import of validate_file_content from server.py"""
    from server import validate_file_content
    return validate_file_content


def get_sanitize_filename_func():
    """Lazy import of sanitize_filename from server.py"""
    from server import sanitize_filename
    return sanitize_filename


def get_put_object_func():
    """Lazy import of put_object from server.py"""
    from server import put_object
    return put_object


def get_extract_training_from_certificate_func():
    """Lazy import of extract_training_from_certificate from server.py"""
    from server import extract_training_from_certificate
    return extract_training_from_certificate


def get_try_auto_promote_worker_func():
    """Lazy import of try_auto_promote_worker from server.py"""
    from server import try_auto_promote_worker
    return try_auto_promote_worker


def get_resend():
    """Lazy import of resend module"""
    import resend
    return resend


def get_admin_email():
    """Get ADMIN_EMAIL from server.py"""
    from server import ADMIN_EMAIL
    return ADMIN_EMAIL


def get_interview_questions():
    """Lazy import interview question functions"""
    from interview_questions import get_interview_questions_for_role, get_administrative_questions, INTERVIEW_SCORING
    return get_interview_questions_for_role, get_administrative_questions, INTERVIEW_SCORING


def get_pre_interview_questionnaire_data_func():
    """Lazy import of get_pre_interview_questionnaire_data from server.py"""
    from server import get_pre_interview_questionnaire_data
    return get_pre_interview_questionnaire_data


def get_employment_history_form_data_func():
    """Lazy import of get_employment_history_form_data from server.py"""
    from server import get_employment_history_form_data
    return get_employment_history_form_data


# ==================== WORKER DASHBOARD ====================

@router.get("/worker/dashboard")
async def worker_dashboard(worker: dict = Depends(get_current_worker)):
    """
    Get worker's compliance dashboard data.
    Shows different views for onboarding vs active employees:
    - Onboarding: Forms to complete, documents to upload
    - Active: Expiry alerts, renewal documents
    """
    db = get_db()
    get_unified_employee_status = get_unified_employee_status_func()
    WORKER_FORM_DEFINITIONS = get_worker_form_definitions()
    
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to account")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Determine if active employee or still onboarding
    employee_status = employee.get("status", "onboarding")
    is_active_employee = employee_status == "active_employee"
    
    # Get documents - IMPORTANT: Exclude ALL non-active statuses at query level for data sync
    # This must match the filtering in server.py HISTORICAL_STATUSES for consistency
    EXCLUDED_STATUSES = ["deleted", "superseded", "uploaded_in_error", "rejected", "moved", "archived", "misfiled"]
    documents = await db.employee_documents.find({
        "employee_id": employee_id,
        "status": {"$nin": EXCLUDED_STATUSES}
    }).to_list(length=200)
    
    # Required document types with their acceptable requirement_id patterns
    required_docs = {
        "right_to_work": {
            "name": "Right to Work",
            "patterns": ["right_to_work", "right_to_work_documents", "right_to_work_evidence", "rtw"],
            "exclude_patterns": ["right_to_work_check"]
        },
        "dbs": {
            "name": "DBS Certificate",
            "patterns": ["dbs", "dbs_certificate", "dbs_evidence"],
            "exclude_patterns": ["dbs_check", "dbs_status_check", "dbs_update"]
        },
        "identity": {
            "name": "Identity (Passport/ID)",
            "patterns": ["identity", "identity_documents", "identity_evidence", "passport", "id_document"],
            "exclude_patterns": ["identity_check", "identity_verification"]
        },
        "proof_of_address": {
            "name": "Proof of Address",
            "patterns": ["proof_of_address", "poa", "address_evidence"],
            "exclude_patterns": ["address_check", "address_verification"]
        }
    }
    
    def matches_requirement(requirement_id: str, doc_config: dict) -> bool:
        """Check if a requirement_id matches a document type's patterns."""
        if not requirement_id:
            return False
        req_lower = requirement_id.lower()
        
        for exclude in doc_config.get("exclude_patterns", []):
            if exclude in req_lower:
                return False
        
        for pattern in doc_config.get("patterns", []):
            if pattern in req_lower:
                return True
        return False
    
    missing_docs = []
    completed_docs = []
    
    for doc_type, doc_config in required_docs.items():
        doc_name = doc_config["name"]
        # All documents here are already filtered to active statuses only (query level)
        matching = [d for d in documents 
                   if matches_requirement(d.get("requirement_id", ""), doc_config)]
        
        # Active docs are the ones we can work with
        active_docs = matching  # All are active since we filtered at query level
        
        if active_docs:
            verified_docs = [d for d in matching if (
                d.get("verification_stamp") not in [None, "", "not_verified"] or
                d.get("verified") == True or
                d.get("status") == "verified"
            )]
            if verified_docs:
                verified_docs.sort(key=lambda x: x.get("verified_at") or x.get("verification_stamp_at") or x.get("uploaded_at") or "", reverse=True)
                doc = verified_docs[0]
            else:
                matching.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
                doc = matching[0]
            
            is_verified = (
                doc.get("verification_stamp") not in [None, "", "not_verified"] or
                doc.get("verified") == True or
                doc.get("status") == "verified"
            )
            file_url = None
            if is_verified and doc.get("stamped_file_url"):
                file_url = doc.get("stamped_file_url")
            elif doc.get("file_url"):
                file_url = doc.get("file_url")
            
            if is_verified:
                display_status = "verified"
            elif doc.get("status") == "pending" or doc.get("status") == "uploaded":
                display_status = "pending_verification"
            else:
                display_status = doc.get("status", "uploaded")
            
            completed_docs.append({
                "id": doc.get("id"),
                "type": doc_type,
                "name": doc_name,
                "verified": is_verified,
                "uploaded_at": doc.get("uploaded_at"),
                "file_name": doc.get("file_name") or doc.get("original_filename"),
                "file_url": file_url,
                "document_id": doc.get("id"),
                "verification_stamp": doc.get("verification_stamp"),
                "verification_stamp_label": doc.get("verification_stamp_label"),
                "verified_by": doc.get("verification_stamp_by") or doc.get("verified_by"),
                "verified_by_name": doc.get("verification_stamp_by_name") or doc.get("verified_by_name"),
                "verified_at": doc.get("verification_stamp_at") or doc.get("verified_at"),
                "status": display_status,
                "raw_status": doc.get("status")
            })
        else:
            # No active documents - check if there was a rejection to show helpful message
            # Note: rejected docs are already excluded at query level, but we can check historical
            missing_docs.append({
                "type": doc_type,
                "name": doc_name,
                "action": "upload"
            })
    
    # Check POA needs 2 documents - handle all cases for data sync with admin
    poa_config = required_docs["proof_of_address"]
    # All docs are already filtered to active statuses at query level
    poa_docs = [d for d in documents 
               if matches_requirement(d.get("requirement_id", ""), poa_config)]
    
    # Remove the generic POA entry added by the loop above - we'll handle POA specially
    completed_docs = [d for d in completed_docs if d["type"] != "proof_of_address"]
    
    if len(poa_docs) == 0:
        # No POA docs - add to missing
        missing_docs.append({
            "type": "proof_of_address",
            "name": "Proof of Address (need 2)",
            "action": "upload"
        })
    elif len(poa_docs) == 1:
        # Only 1 POA doc - show it with partial status
        poa_doc = poa_docs[0]
        is_verified = (
            poa_doc.get("verification_stamp") not in [None, "", "not_verified"] or
            poa_doc.get("verified") == True or
            poa_doc.get("status") == "verified"
        )
        file_url = poa_doc.get("stamped_file_url") if is_verified else poa_doc.get("file_url")
        completed_docs.append({
            "id": poa_doc.get("id"),
            "type": "proof_of_address",
            "name": "Proof of Address (1 of 2)",
            "verified": is_verified,
            "uploaded_at": poa_doc.get("uploaded_at"),
            "file_url": file_url,
            "file_name": poa_doc.get("file_name") or poa_doc.get("original_filename"),
            "document_id": poa_doc.get("id"),
            "partial": True,
            "status": "verified" if is_verified else "pending_verification",
            "verified_by_name": poa_doc.get("verification_stamp_by_name") or poa_doc.get("verified_by_name"),
            "verified_at": poa_doc.get("verification_stamp_at") or poa_doc.get("verified_at"),
        })
        missing_docs.append({
            "type": "proof_of_address_2",
            "name": "Second Proof of Address (need 1 more)",
            "action": "upload"
        })
    else:
        # 2+ POA docs - show ALL of them (sync with admin view)
        poa_docs.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
        for idx, poa_doc in enumerate(poa_docs[:5]):  # Cap at 5 to match admin max
            is_verified = (
                poa_doc.get("verification_stamp") not in [None, "", "not_verified"] or
                poa_doc.get("verified") == True or
                poa_doc.get("status") == "verified"
            )
            file_url = poa_doc.get("stamped_file_url") if is_verified else poa_doc.get("file_url")
            completed_docs.append({
                "id": poa_doc.get("id"),
                "type": f"proof_of_address_{idx+1}" if idx > 0 else "proof_of_address",
                "name": f"Proof of Address {idx + 1}",
                "verified": is_verified,
                "uploaded_at": poa_doc.get("uploaded_at"),
                "file_url": file_url,
                "file_name": poa_doc.get("file_name") or poa_doc.get("original_filename"),
                "document_id": poa_doc.get("id"),
                "partial": False,
                "status": "verified" if is_verified else "pending_verification",
                "verified_by_name": poa_doc.get("verification_stamp_by_name") or poa_doc.get("verified_by_name"),
                "verified_at": poa_doc.get("verification_stamp_at") or poa_doc.get("verified_at"),
            })
    
    # Get training
    trainings = await db.training_records.find({
        "employee_id": employee_id,
        "record_status": {"$ne": "superseded"}
    }).to_list(length=100)
    
    mandatory_trainings = {
        # CQC Standard Trainings (in order of priority)
        "induction": "Induction",
        "safeguarding": "Safeguarding",
        "manual_handling": "Moving & Handling", 
        "medication": "Medication",
        "health_safety": "Health & Safety",
        "food_hygiene": "Food Hygiene",
        "bls": "First Aid / Basic Life Support",
        "mca_dols": "MCA and DoLs",
        "dementia": "Dementia Awareness",
        "fire_safety": "Fire Safety",
        "autism": "Autism Awareness",
        "infection_control": "Infection Control",
        "information_governance": "Information Governance",
        "prevent": "Prevent"
    }
    
    missing_trainings = []
    completed_trainings = []
    expired_trainings = []
    all_mandatory_trainings = []
    now = datetime.now(timezone.utc)
    
    for training_id, training_name in mandatory_trainings.items():
        record = None
        search_patterns = [
            training_id.replace("_", " "),
            training_id.replace("_", ""),
            training_name.lower(),
            f"cstf {training_name.lower()}",
            f"cstf {training_id.replace('_', ' ')}",
        ]
        
        # Add alternative search patterns for each training type
        if training_id == "induction":
            search_patterns.extend(["company induction", "orientation", "welcome training"])
        elif training_id == "safeguarding":
            search_patterns.extend(["safeguarding adults", "safeguarding children", "safeguard"])
        elif training_id == "manual_handling":
            search_patterns.extend(["moving & handling", "moving and handling", "patient handling"])
        elif training_id == "medication":
            search_patterns.extend(["medication administration", "medicines management", "safe handling of medicines"])
        elif training_id == "bls":
            search_patterns.extend(["basic life support", "resuscitation", "cpr", "first aid"])
        elif training_id == "health_safety":
            search_patterns.extend(["health, safety and welfare", "health and safety", "h&s"])
        elif training_id == "food_hygiene":
            search_patterns.extend(["food safety", "food handling", "level 2 food"])
        elif training_id == "mca_dols":
            search_patterns.extend(["mental capacity", "deprivation of liberty", "mca", "dols", "best interests"])
        elif training_id == "dementia":
            search_patterns.extend(["dementia awareness", "dementia care", "alzheimer"])
        elif training_id == "autism":
            search_patterns.extend(["autism awareness", "autism spectrum", "asd"])
        elif training_id == "fire_safety":
            search_patterns.extend(["fire awareness", "fire prevention", "fire evacuation"])
        elif training_id == "infection_control":
            search_patterns.extend(["infection prevention", "ipc"])
        elif training_id == "information_governance":
            search_patterns.extend(["gdpr", "data protection", "ig training"])
        elif training_id == "prevent":
            search_patterns.extend(["counter terrorism", "radicalisation", "prevent duty"])
        
        for t in trainings:
            t_name = (t.get("training_name") or "").lower()
            for pattern in search_patterns:
                if pattern in t_name:
                    record = t
                    break
            if record:
                break
        
        training_entry = {
            "id": training_id,
            "name": training_name,
            "status": "missing",
            "completion_date": None,
            "expiry_date": None,
            "verified": False,
            "record_id": None
        }
        
        if record:
            expiry_str = record.get("expiry_date")
            is_expired = False
            
            if expiry_str:
                try:
                    if isinstance(expiry_str, str):
                        if 'T' in expiry_str or '+' in expiry_str or 'Z' in expiry_str:
                            expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                        else:
                            expiry = datetime.strptime(expiry_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    else:
                        expiry = expiry_str
                        if expiry.tzinfo is None:
                            expiry = expiry.replace(tzinfo=timezone.utc)
                    is_expired = expiry < now
                except Exception as e:
                    logger.warning(f"Error parsing training expiry date '{expiry_str}': {e}")
            
            training_entry.update({
                "status": "expired" if is_expired else "complete",
                "completion_date": record.get("completion_date"),
                "expiry_date": expiry_str,
                "verified": record.get("verified", False),
                "record_id": record.get("id")
            })
            
            if is_expired:
                expired_trainings.append({
                    "id": training_id,
                    "name": training_name,
                    "expiry_date": expiry_str,
                    "action": "upload_certificate"
                })
            else:
                completed_trainings.append({
                    "id": training_id,
                    "name": training_name,
                    "completion_date": record.get("completion_date"),
                    "expiry_date": expiry_str,
                    "verified": record.get("verified", False)
                })
        else:
            missing_trainings.append({
                "id": training_id,
                "name": training_name,
                "action": "upload_certificate"
            })
        
        all_mandatory_trainings.append(training_entry)
    
    # Get expiry alerts
    alerts = []
    
    dbs_check = await db.dbs_checks.find_one({"employee_id": employee_id}, {"_id": 0})
    if dbs_check and dbs_check.get("next_check_due"):
        due_str = dbs_check["next_check_due"]
        try:
            if isinstance(due_str, str):
                due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            else:
                due_date = due_str
            days_left = (due_date - now).days
            if days_left < 90:
                alerts.append({
                    "type": "dbs",
                    "title": "DBS Update Service Check Due",
                    "date": due_str,
                    "days_left": max(0, days_left),
                    "urgent": days_left < 30
                })
        except:
            pass
    
    rtw_check = await db.rtw_checks.find_one({"employee_id": employee_id}, {"_id": 0})
    if rtw_check and rtw_check.get("expiry_date"):
        exp_str = rtw_check["expiry_date"]
        try:
            if isinstance(exp_str, str):
                exp_date = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
            else:
                exp_date = exp_str
            days_left = (exp_date - now).days
            if days_left < 90:
                alerts.append({
                    "type": "rtw",
                    "title": "Right to Work Expiring",
                    "date": exp_str,
                    "days_left": max(0, days_left),
                    "urgent": days_left < 30
                })
        except:
            pass
    
    # Training expiry alerts
    for t in completed_trainings + expired_trainings:
        if t.get("expiry_date"):
            try:
                exp_str = t["expiry_date"]
                if isinstance(exp_str, str):
                    if 'T' in exp_str or '+' in exp_str or 'Z' in exp_str:
                        exp_date = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                    else:
                        exp_date = datetime.strptime(exp_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                else:
                    exp_date = exp_str
                    if exp_date.tzinfo is None:
                        exp_date = exp_date.replace(tzinfo=timezone.utc)
                days_left = (exp_date - now).days
                
                if days_left < 60:
                    alerts.append({
                        "type": "training",
                        "name": t['name'],
                        "title": f"{t['name']} Training {'EXPIRED' if days_left < 0 else 'Expiring'}",
                        "date": exp_str,
                        "days_left": days_left,
                        "urgent": days_left < 30,
                        "is_expired": days_left < 0,
                        "training_id": t.get("id")
                    })
            except Exception as e:
                logger.warning(f"Error parsing training expiry for alert: {e}")
    
    # Agreements status
    agreements_status = []
    
    contract_ack = await db.agreement_acknowledgements.find_one({
        "employee_id": employee_id,
        "agreement_type": "contract_acceptance"
    }, {"_id": 0})
    
    contract_status = {
        "id": "contract_acceptance",
        "name": "Contract Acceptance",
        "type": "contract_acceptance",
        "signed": bool(contract_ack and contract_ack.get("acknowledged")),
        "signed_at": contract_ack.get("acknowledged_at") if contract_ack else None,
        "verified": bool(contract_ack and contract_ack.get("verification_status") == "verified"),
        "verified_at": contract_ack.get("verified_at") if contract_ack else None,
        "verified_by_name": contract_ack.get("verified_by_name") if contract_ack else None,
        "can_sign": not bool(contract_ack and contract_ack.get("acknowledged")),
        "status": "verified" if (contract_ack and contract_ack.get("verification_status") == "verified") else (
            "signed" if (contract_ack and contract_ack.get("acknowledged")) else "pending"
        )
    }
    agreements_status.append(contract_status)
    contract_signed = contract_status["signed"]
    
    handbook_ack = await db.agreement_acknowledgements.find_one({
        "employee_id": employee_id,
        "agreement_type": "handbook_acknowledgement"
    }, {"_id": 0})
    
    handbook_status = {
        "id": "handbook_acknowledgement",
        "name": "Employee Handbook Acknowledgement",
        "type": "handbook_acknowledgement",
        "signed": bool(handbook_ack and handbook_ack.get("acknowledged")),
        "signed_at": handbook_ack.get("acknowledged_at") if handbook_ack else None,
        "verified": bool(handbook_ack and handbook_ack.get("verification_status") == "verified"),
        "verified_at": handbook_ack.get("verified_at") if handbook_ack else None,
        "verified_by_name": handbook_ack.get("verified_by_name") if handbook_ack else None,
        "can_sign": not bool(handbook_ack and handbook_ack.get("acknowledged")),
        "status": "verified" if (handbook_ack and handbook_ack.get("verification_status") == "verified") else (
            "signed" if (handbook_ack and handbook_ack.get("acknowledged")) else "pending"
        )
    }
    agreements_status.append(handbook_status)
    
    # Unified progress
    unified_training_items = []
    try:
        unified_status = await get_unified_employee_status(employee_id, db, user_role="worker", include_details=True)
        progress_percentage = unified_status["progress"]["percentage"]
        total_required = unified_status["progress"]["total"]
        total_completed = unified_status["progress"]["completed"]
        unified_blockers = unified_status.get("blockers", [])
        has_blockers = len(unified_blockers) > 0 or not contract_signed
        
        unified_training_items = unified_status.get("category_details", {}).get("training", {}).get("items", [])
    except Exception as e:
        logger.error(f"Unified progress failed for {employee_id}: {e}")
        total_required = len(required_docs) + 1 + len(mandatory_trainings)
        total_completed = len([d for d in completed_docs if not d.get("partial")]) + len(completed_trainings)
        if len(poa_docs) >= 2:
            total_completed += 1
        progress_percentage = round((total_completed / total_required) * 100) if total_required > 0 else 0
        has_blockers = len(missing_docs) > 0 or len(missing_trainings) > 0 or len(expired_trainings) > 0 or not contract_signed
        unified_blockers = []
    
    if unified_training_items:
        all_mandatory_trainings = []
        for item in unified_training_items:
            all_mandatory_trainings.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "status": "complete" if item.get("completed") else ("expired" if "expired" in (item.get("invalid_reason") or "").lower() else "missing"),
                "completion_date": None,
                "expiry_date": item.get("expiry_date"),
                "verified": item.get("verified", False),
                "record_id": None
            })
    
    status = "READY" if is_active_employee else ("NOT_READY" if has_blockers else "READY")
    
    # Get form status for onboarding employees
    forms_status = []
    if not is_active_employee:
        for form_id, form_def in WORKER_FORM_DEFINITIONS.items():
            progress = await db.form_progress.find_one({
                "employee_id": employee_id,
                "form_id": form_id
            }, {"_id": 0})
            
            submission = await db.form_submissions.find_one({
                "employee_id": employee_id,
                "form_type": form_id,
                "status": {"$in": ["submitted", "verified"]}
            }, {"_id": 0})
            
            form_status = "not_started"
            saved_at = None
            submitted_at = None
            form_progress_pct = 0
            
            if submission:
                form_status = "submitted" if submission.get("status") == "submitted" else "verified"
                submitted_at = submission.get("submitted_at")
            elif progress:
                form_status = "in_progress"
                saved_at = progress.get("last_saved")
                form_data = progress.get("data", {})
                if form_data:
                    filled_fields = sum(1 for v in form_data.values() if v)
                    total_fields = len(form_data) or 1
                    form_progress_pct = int((filled_fields / total_fields) * 100)
            
            forms_status.append({
                "id": form_id,
                "name": form_def["name"],
                "description": form_def.get("description", ""),
                "required": form_def.get("required", True),
                "status": form_status,
                "saved_at": saved_at,
                "submitted_at": submitted_at,
                "progress_percentage": form_progress_pct
            })
    
    # Professional registration
    professional_registrations = employee.get("professional_registrations", [])
    job_role = employee.get("job_role", "").lower()
    
    requires_prof_reg = False
    registration_type = None
    if "nurse" in job_role or "midwife" in job_role:
        requires_prof_reg = True
        registration_type = "NMC"
    elif "doctor" in job_role or "physician" in job_role or "consultant" in job_role:
        requires_prof_reg = True
        registration_type = "GMC"
    elif "physio" in job_role or "occupational" in job_role or "paramedic" in job_role:
        requires_prof_reg = True
        registration_type = "HCPC"
    elif "social worker" in job_role:
        requires_prof_reg = True
        registration_type = "SWE"
    
    prof_reg_status = None
    if requires_prof_reg:
        matching_reg = None
        for reg in professional_registrations:
            if reg.get("registration_type") == registration_type:
                matching_reg = reg
                break
        
        if matching_reg:
            prof_reg_status = {
                "type": registration_type,
                "number": matching_reg.get("registration_number"),
                "verified": matching_reg.get("verified", False),
                "expiry_date": matching_reg.get("expiry_date"),
                "status": "verified" if matching_reg.get("verified") else "pending_verification"
            }
        else:
            prof_reg_status = {
                "type": registration_type,
                "number": None,
                "verified": False,
                "status": "not_submitted",
                "required": True
            }
    
    # References status
    references_status = []
    for ref_num in [1, 2]:
        prefix = f"reference_{ref_num}_"
        
        referee_name = employee.get(f"{prefix}name", "")
        referee_email = employee.get(f"{prefix}email", "")
        is_declared = bool(referee_name and referee_email)
        
        request_sent_at = employee.get(f"{prefix}request_sent_at")
        request_status = employee.get(f"{prefix}request_status")
        request_token = employee.get(f"{prefix}request_token")
        request_sent = bool(request_sent_at) or request_status in ["awaiting_response", "requested", "sent"] or bool(request_token)
        
        response_data = employee.get(f"{prefix}response_data")
        response_received_at = employee.get(f"{prefix}response_received_at")
        response_status = employee.get(f"{prefix}response_status")
        response_received = bool(response_data) or bool(response_received_at) or response_status in ["received", "submitted"] or request_status == "response_received"
        
        is_verified = (
            employee.get(f"{prefix}verified", False) == True or
            employee.get(f"{prefix}status") == "verified" or
            request_status == "verified"
        )
        verified_at = employee.get(f"{prefix}verified_at")
        verified_by = employee.get(f"{prefix}verified_by")
        
        is_rejected = employee.get(f"{prefix}rejected", False) or request_status == "rejected"
        rejection_reason = employee.get(f"{prefix}rejection_reason", "")
        
        data_cleared = is_rejected and not referee_name
        
        if is_verified:
            ref_status = "verified"
            status_label = "Verified"
        elif data_cleared:
            ref_status = "needs_new_input"
            status_label = "Please provide new referee details"
        elif is_rejected:
            ref_status = "rejected"
            status_label = "Rejected - Please provide new referee"
        elif response_received:
            ref_status = "response_received"
            status_label = "Response received - pending admin review"
        elif request_sent:
            ref_status = "sent"
            status_label = "Request sent - awaiting referee response"
        elif is_declared:
            ref_status = "declared"
            status_label = "Referee declared - admin will send request"
        else:
            ref_status = "not_declared"
            status_label = "Not declared"
        
        verified_by_name = None
        if verified_by:
            admin_user = await db.users.find_one({"id": verified_by}, {"_id": 0, "first_name": 1, "last_name": 1})
            if admin_user:
                verified_by_name = f"{admin_user.get('first_name', '')} {admin_user.get('last_name', '')}".strip()
        
        mismatch_explanation = employee.get(f"{prefix}mismatch_explanation")
        mismatch_explanation_status = employee.get(f"{prefix}mismatch_explanation_status", "not_submitted")
        mismatch_admin_decision = employee.get(f"{prefix}mismatch_admin_decision")
        
        references_status.append({
            "reference_number": ref_num,
            "referee_name": referee_name if is_declared else None,
            "referee_company": employee.get(f"{prefix}company", "") if is_declared else None,
            "status": ref_status,
            "status_label": status_label,
            "rejection_reason": rejection_reason if (is_rejected or data_cleared) else None,
            "can_provide_new": data_cleared or ref_status == "not_declared",
            "verified_at": verified_at,
            "verified_by_name": verified_by_name,
            "response_received_at": response_received_at,
            "has_mismatch_explanation": mismatch_explanation is not None,
            "mismatch_explanation_status": mismatch_explanation_status,
            "mismatch_admin_decision": mismatch_admin_decision
        })
    
    # Induction checklist status
    induction_record = await db.induction_checklists.find_one({
        "employee_id": employee_id
    }, {"_id": 0})
    
    training_records = await db.training_records.find({
        "employee_id": employee_id,
        "verified": True
    }, {"_id": 0}).to_list(50)
    
    training_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$regex": "training|safeguard|fire|manual|infection|health|bls|basic_life"},
        "verification_stamp": {"$nin": [None, "", "not_verified"]}
    }, {"_id": 0}).to_list(50)
    
    verified_training_names = set()
    for tr in training_records:
        name = (tr.get("training_name") or "").lower()
        verified_training_names.add(name)
    for doc in training_docs:
        req_id = (doc.get("requirement_id") or "").lower()
        verified_training_names.add(req_id)
        if "safeguard" in req_id:
            verified_training_names.add("safeguarding adults")
            verified_training_names.add("safeguarding")
        if "fire" in req_id:
            verified_training_names.add("fire safety")
        if "manual" in req_id or "moving" in req_id:
            verified_training_names.add("moving & handling")
            verified_training_names.add("manual handling")
        if "infection" in req_id:
            verified_training_names.add("infection prevention & control")
            verified_training_names.add("infection control")
        if "health" in req_id and "safety" in req_id:
            verified_training_names.add("health & safety")
        if "bls" in req_id or "basic_life" in req_id:
            verified_training_names.add("basic life support")
    
    INDUCTION_TRAINING_MAP = {
        "safeguarding adults": ["safeguarding", "safeguard", "safeguard_adults"],
        "health and safety": ["health_safety", "health safety", "health & safety", "cstf_health"],
        "infection prevention and control": ["infection", "infection control", "infection_control", "cstf_infection"],
        "basic life support": ["bls", "basic life", "basic_life", "resuscitation"],
        "equality and diversity": ["equality", "diversity", "edi", "equality_diversity", "cstf_equality"],
        "fluids and nutrition": ["food_hygiene", "food safety", "nutrition"],
        "handling information": ["data_protection", "gdpr", "information governance"],
        "communication": ["communication"],
        "mental health, dementia and learning disabilities": ["dementia", "mental health", "learning disabilities"],
    }
    
    def is_training_verified(item_name):
        item_lower = item_name.lower()
        if item_lower in verified_training_names:
            return True
        for induction_name, training_patterns in INDUCTION_TRAINING_MAP.items():
            if induction_name in item_lower or item_lower in induction_name:
                for pattern in training_patterns:
                    if any(pattern in vtn for vtn in verified_training_names):
                        return True
        return False
    
    induction_items = []
    completed_count = 0
    total_items = 0
    
    if induction_record and induction_record.get("items"):
        admin_items = induction_record.get("items", [])
        for item in admin_items:
            item_name = item.get("name", "Unknown")
            
            is_complete_in_checklist = item.get("status") == "completed"
            is_training_complete = is_training_verified(item_name)
            
            is_complete = is_complete_in_checklist or is_training_complete
            completed_at = item.get("completed_at")
            
            if is_complete:
                completed_count += 1
            total_items += 1
            
            induction_items.append({
                "id": item_name.lower().replace(" ", "_").replace("&", "and"),
                "name": item_name,
                "mandatory": item.get("mandatory", True),
                "completed": is_complete,
                "completed_at": completed_at,
                "completed_by_name": item.get("completed_by_name"),
                "synced_from_training": is_training_complete and not is_complete_in_checklist
            })
    else:
        care_certificate_standards = [
            {"name": "Understand Your Role", "mandatory": True},
            {"name": "Your Personal Development", "mandatory": True},
            {"name": "Duty of Care", "mandatory": True},
            {"name": "Equality and Diversity", "mandatory": True},
            {"name": "Work in a Person-Centred Way", "mandatory": True},
            {"name": "Communication", "mandatory": True},
            {"name": "Privacy and Dignity", "mandatory": True},
            {"name": "Fluids and Nutrition", "mandatory": True},
            {"name": "Awareness of Mental Health, Dementia and Learning Disabilities", "mandatory": True},
            {"name": "Safeguarding Adults", "mandatory": True},
            {"name": "Basic Life Support", "mandatory": True},
            {"name": "Health and Safety", "mandatory": True},
            {"name": "Handling Information", "mandatory": True},
            {"name": "Infection Prevention and Control", "mandatory": True},
            {"name": "Shadow Shift Completed", "mandatory": True},
        ]
        for std in care_certificate_standards:
            std_name = std["name"]
            is_training_complete = is_training_verified(std_name)
            if is_training_complete:
                completed_count += 1
            total_items += 1
            induction_items.append({
                "id": std_name.lower().replace(" ", "_").replace(",", "").replace("&", "and"),
                "name": std_name,
                "mandatory": std["mandatory"],
                "completed": is_training_complete,
                "completed_at": None,
                "completed_by_name": None,
                "synced_from_training": is_training_complete
            })
    
    induction_status = {
        "total": total_items,
        "completed": completed_count,
        "items": induction_items,
        "overall_status": induction_record.get("overall_status") if induction_record else "not_started"
    }
    
    # Competency assessments
    competency_records = await db.competency_assessments.find({
        "employee_id": employee_id
    }, {"_id": 0}).sort("scheduled_date", -1).to_list(20)
    
    competency_status = []
    for comp in competency_records:
        competency_status.append({
            "id": comp.get("id"),
            "competency_name": comp.get("competency_name") or comp.get("assessment_type", "Assessment"),
            "area": comp.get("area") or comp.get("competency_area"),
            "status": comp.get("status", "pending"),
            "scheduled_date": comp.get("scheduled_date") or comp.get("due_date"),
            "completed_date": comp.get("completed_date") or comp.get("assessment_date"),
            "outcome": comp.get("outcome"),
            "assessed_by_name": comp.get("assessed_by_name") or comp.get("assessor_name"),
            "notes": comp.get("notes"),
            "follow_up_required": comp.get("follow_up_required", False),
            "follow_up_date": comp.get("follow_up_date")
        })
    
    # Spot checks
    spot_check_records = await db.spot_checks.find({
        "employee_id": employee_id
    }, {"_id": 0}).sort("date", -1).to_list(20)
    
    spot_check_status = []
    for spot in spot_check_records:
        spot_check_status.append({
            "id": spot.get("id"),
            "type": spot.get("type", "observation"),
            "area": spot.get("area"),
            "date": spot.get("date") or spot.get("scheduled_date"),
            "outcome": spot.get("outcome"),
            "notes": spot.get("notes"),
            "assessed_by_name": spot.get("assessed_by_name"),
            "follow_up_required": spot.get("follow_up_required", False),
            "follow_up_date": spot.get("follow_up_date")
        })
    
    return {
        "employee": {
            "id": employee_id,
            "name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            "code": employee.get("employee_code"),
            "email": employee.get("email"),
            "status": status,
            "employee_status": employee_status,
            "is_active_employee": is_active_employee,
            "job_role": employee.get("job_role", "")
        },
        "progress": {
            "percentage": progress_percentage,
            "completed": total_completed,
            "required": total_required
        },
        "unified_blockers": unified_blockers,
        "forms": forms_status,
        "missing_documents": missing_docs,
        "completed_documents": completed_docs,
        "missing_trainings": missing_trainings,
        "completed_trainings": completed_trainings,
        "expired_trainings": expired_trainings,
        "all_mandatory_trainings": all_mandatory_trainings,
        "alerts": sorted(alerts, key=lambda x: x.get("days_left", 999)),
        "contract_signed": contract_signed,
        "professional_registration": prof_reg_status,
        "references": references_status,
        "induction": induction_status,
        "competency_assessments": competency_status,
        "spot_checks": spot_check_status,
        "agreements": agreements_status
    }


# ==================== WORKER DOCUMENT UPLOAD ====================

@router.post("/worker/upload-document/{requirement_id}")
async def worker_upload_document(
    requirement_id: str,
    file: UploadFile = File(...),
    worker: dict = Depends(get_current_worker)
):
    """
    Upload a document from the worker portal.
    Worker can only upload their own documents.
    """
    db = get_db()
    validate_file_content = get_validate_file_content_func()
    sanitize_filename = get_sanitize_filename_func()
    put_object = get_put_object_func()
    extract_training_from_certificate = get_extract_training_from_certificate_func()
    MANDATORY_ITEMS = get_mandatory_items()
    resend = get_resend()
    ADMIN_EMAIL = get_admin_email()
    
    employee_id = worker.get("employee_id")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    contents = await file.read()
    
    is_valid, detected_type, error_msg = validate_file_content(contents, file.content_type)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    safe_filename = sanitize_filename(file.filename)
    safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    
    storage_path = f"documents/{employee_id}/{safe_filename}"
    
    content_type = detected_type or file.content_type or "application/octet-stream"
    put_object(storage_path, contents, content_type)
    
    file_url = storage_path
    now = datetime.now(timezone.utc).isoformat()
    
    doc_id = str(uuid.uuid4())
    
    is_training_cert = requirement_id.startswith("training") or "training" in requirement_id.lower()
    
    # Normalize requirement_id for identity documents to ensure admin can find them
    # The admin dashboard searches for identity_evidence which maps to these values
    normalized_requirement_id = requirement_id
    if requirement_id == "identity":
        normalized_requirement_id = "identity"  # Keep as-is, backend mapping handles it
    
    # Get employee name for audit trail
    emp_info = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    emp_name = f"{emp_info.get('first_name', '')} {emp_info.get('last_name', '')}".strip() if emp_info else "Worker"
    
    doc_record = {
        "id": doc_id,
        "employee_id": employee_id,
        "requirement_id": normalized_requirement_id,
        "document_type_id": normalized_requirement_id,
        "document_type": "training_certificate" if is_training_cert else normalized_requirement_id,
        "category": "training" if is_training_cert else "document",
        "file_name": file.filename,
        "original_filename": file.filename,
        "file_url": file_url,
        "file_type": detected_type,
        "uploaded_at": now,
        "uploaded_by": f"worker_{employee_id}",
        "uploaded_by_name": emp_name,
        "uploaded_by_worker": True,
        "status": "uploaded",
        "verified": False,
        "verification_stamp": None,  # Changed from "not_verified" to None for cleaner display
        "is_active": True,
        "created_at": now,
        "source_type": "worker_portal_upload"
    }
    
    await db.employee_documents.insert_one(doc_record)
    
    await log_audit_action(f"worker_{employee_id}", "worker_document_upload", "employee", employee_id, {
        "requirement_id": requirement_id,
        "document_id": doc_id,
        "file_name": file.filename,
        "employee_id": employee_id
    })
    
    # Send admin notification
    try:
        if resend.api_key:
            employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1, "employee_code": 1})
            emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() if employee else "Unknown"
            emp_code = employee.get("employee_code", "N/A") if employee else "N/A"
            
            req_name = requirement_id.replace("_", " ").title()
            for item in MANDATORY_ITEMS:
                if item.get("id") == requirement_id:
                    req_name = item.get("name", req_name)
                    break
            
            admin_email_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #0F172A; padding: 16px; text-align: center;">
                    <h2 style="color: white; margin: 0;">Document Uploaded</h2>
                </div>
                <div style="padding: 24px; background: #f8fafc;">
                    <h3 style="color: #1e293b; margin-top: 0;">New Document Requires Verification</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Employee:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: bold;">{emp_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Employee Code:</td>
                            <td style="padding: 8px 0; color: #1e293b;">{emp_code}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Document Type:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: bold;">{req_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">File Name:</td>
                            <td style="padding: 8px 0; color: #1e293b;">{file.filename}</td>
                        </tr>
                    </table>
                    <div style="margin-top: 24px; text-align: center;">
                        <a href="{os.environ.get('FRONTEND_URL', 'https://app.osabeacares.co.uk')}/portal/employees/{employee_id}?tab=evidence" style="background: #2563EB; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                            Review Document
                        </a>
                    </div>
                </div>
            </div>
            """
            
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [ADMIN_EMAIL],
                "subject": f"Document Upload: {req_name} - {emp_name}",
                "html": admin_email_html
            })
            logger.info(f"Admin notification sent for document upload: {requirement_id} by {employee_id}")
    except Exception as e:
        logger.warning(f"Failed to send admin notification for document upload: {e}")
    
    # Training certificate AI extraction
    if requirement_id.startswith("training") or "training" in requirement_id.lower():
        try:
            extracted_trainings = await extract_training_from_certificate(contents, file.filename)
            
            if extracted_trainings:
                logger.info(f"AI extracted {len(extracted_trainings)} training(s) from worker upload")
                
                await db.employee_documents.update_one(
                    {"id": doc_id},
                    {"$set": {
                        "extraction_count": len(extracted_trainings),
                        "extraction_status": "completed",
                        "extraction_date": now
                    }}
                )
                
                mandatory_codes = {
                    "safeguarding": ["safeguarding", "safeguard", "protection of adults"],
                    "manual_handling": ["manual handling", "moving and handling", "people handling"],
                    "fire_safety": ["fire safety", "fire awareness", "fire marshal", "fire warden"],
                    "health_safety": ["health and safety", "health & safety", "h&s awareness"],
                    "basic_life_support": ["basic life support", "bls", "first aid", "resuscitation", "cpr"],
                    "infection_control": ["infection control", "infection prevention", "ipc"],
                    "information_governance": ["information governance", "data protection", "gdpr", "confidentiality"],
                    "prevent": ["prevent", "counter terrorism", "radicalisation", "prevent duty"]
                }
                
                existing_training_records = await db.training_records.find(
                    {"employee_id": employee_id, "record_status": {"$ne": "superseded"}}
                ).to_list(200)
                existing_proposed = await db.proposed_training_items.find(
                    {"employee_id": employee_id}
                ).to_list(200)
                
                def normalize_name(name):
                    return (name or "").lower().strip().replace("-", " ").replace("_", " ")
                
                existing_names = set()
                for rec in existing_training_records:
                    existing_names.add(normalize_name(rec.get("training_name")))
                    existing_names.add(normalize_name(rec.get("course_name")))
                for prop in existing_proposed:
                    existing_names.add(normalize_name(prop.get("training_name")))
                    existing_names.add(normalize_name(prop.get("course_name")))
                
                proposed_items = []
                updated_items = []
                new_items = []
                
                for training in extracted_trainings:
                    training_name = training.get("training_name", "Unknown Training")
                    training_name_normalized = normalize_name(training_name)
                    
                    matched_code = None
                    training_lower = training_name.lower()
                    for code, keywords in mandatory_codes.items():
                        if any(kw in training_lower for kw in keywords):
                            matched_code = code
                            break
                    
                    is_duplicate = training_name_normalized in existing_names
                    
                    if matched_code and not is_duplicate:
                        for rec in existing_training_records:
                            rec_name = normalize_name(rec.get("training_name"))
                            for kw in mandatory_codes.get(matched_code, []):
                                if kw in rec_name:
                                    is_duplicate = True
                                    break
                            if is_duplicate:
                                break
                    
                    if is_duplicate:
                        logger.info(f"Training '{training_name}' already exists - will update with new certificate")
                        
                        update_query = {"employee_id": employee_id, "record_status": {"$ne": "superseded"}}
                        if matched_code:
                            update_query["$or"] = [
                                {"training_name": {"$regex": training_name, "$options": "i"}},
                                {"mapped_training_code": matched_code}
                            ]
                        else:
                            update_query["training_name"] = {"$regex": training_name, "$options": "i"}
                        
                        existing_record = await db.training_records.find_one(update_query, {"_id": 0})
                        
                        if existing_record:
                            certificates = existing_record.get("certificate_urls", [])
                            if existing_record.get("certificate_url"):
                                certificates.append(existing_record["certificate_url"])
                            certificates.append(file_url)
                            certificates = list(set(certificates))
                            
                            update_fields = {
                                "certificate_urls": certificates,
                                "updated_at": now,
                                "additional_documents": existing_record.get("additional_documents", []) + [{
                                    "document_id": doc_id,
                                    "file_url": file_url,
                                    "file_name": file.filename,
                                    "uploaded_at": now,
                                    "uploaded_by_worker": True
                                }]
                            }
                            
                            new_expiry = training.get("expiry_date")
                            if new_expiry:
                                old_expiry = existing_record.get("expiry_date")
                                if not old_expiry or new_expiry > old_expiry:
                                    update_fields["expiry_date"] = new_expiry
                            
                            await db.training_records.update_one(
                                {"id": existing_record["id"]},
                                {"$set": update_fields}
                            )
                            updated_items.append(training_name)
                        else:
                            existing_proposed_item = await db.proposed_training_items.find_one({
                                "employee_id": employee_id,
                                "training_name": {"$regex": training_name, "$options": "i"}
                            })
                            if existing_proposed_item:
                                await db.proposed_training_items.update_one(
                                    {"id": existing_proposed_item["id"]},
                                    {"$set": {
                                        "additional_certificates": existing_proposed_item.get("additional_certificates", []) + [{
                                            "document_id": doc_id,
                                            "file_url": file_url,
                                            "file_name": file.filename
                                        }],
                                        "updated_at": now
                                    }}
                                )
                                updated_items.append(training_name)
                    else:
                        proposed_item = {
                            "id": str(uuid.uuid4()),
                            "employee_id": employee_id,
                            "source_document_id": doc_id,
                            "source_document_url": file_url,
                            "source_document_name": file.filename,
                            "training_name": training_name,
                            "course_name": training.get("course_name", training_name),
                            "provider": training.get("provider"),
                            "completion_date": training.get("completion_date"),
                            "expiry_date": training.get("expiry_date"),
                            "mapped_training_code": matched_code,
                            "is_mandatory": matched_code is not None,
                            "ai_extracted": True,
                            "extraction_confidence": training.get("confidence", "medium"),
                            "status": "proposed",
                            "uploaded_by_worker": True,
                            "created_at": now
                        }
                        proposed_items.append(proposed_item)
                        new_items.append(training_name)
                        existing_names.add(training_name_normalized)
                
                if proposed_items:
                    await db.proposed_training_items.insert_many(proposed_items)
                    logger.info(f"Created {len(proposed_items)} NEW proposed training items for admin review")
                
                if updated_items:
                    logger.info(f"Updated {len(updated_items)} existing training records with new certificate")
                
                return {
                    "success": True,
                    "document_id": doc_id,
                    "requirement_id": requirement_id,
                    "file_name": file.filename,
                    "ai_extraction": {
                        "extracted": True,
                        "trainings_found": len(extracted_trainings),
                        "new_trainings": new_items,
                        "updated_trainings": updated_items,
                        "mandatory_matched": sum(1 for p in proposed_items if p.get("is_mandatory"))
                    },
                    "message": f"Certificate uploaded. AI extracted {len(extracted_trainings)} training(s): {len(new_items)} new, {len(updated_items)} updated."
                }
        except Exception as e:
            logger.warning(f"AI training extraction failed for worker upload: {e}")
    
    # CV uploads
    if requirement_id in ["cv", "resume", "curriculum_vitae"] or "cv" in requirement_id.lower():
        await db.employee_documents.update_one(
            {"id": doc_id},
            {"$set": {
                "extraction_status": "pending_admin_review",
                "document_subtype": "cv",
                "requires_admin_extraction": True
            }}
        )
        
        logger.info(f"CV uploaded by worker {employee_id} - pending admin review for AI extraction")
        
        return {
            "success": True,
            "document_id": doc_id,
            "requirement_id": requirement_id,
            "file_name": file.filename,
            "message": "CV uploaded successfully! Our team will review it and extract your employment history."
        }
    
    return {
        "success": True,
        "document_id": doc_id,
        "requirement_id": requirement_id,
        "file_name": file.filename,
        "message": "Document uploaded successfully. Awaiting admin verification."
    }


# ==================== SEND WORKER REMINDER (ADMIN ACTION) ====================

@router.post("/workers/{employee_id}/send-reminder")
async def send_worker_reminder(
    employee_id: str,
    request: SendReminderRequest = SendReminderRequest(),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Send a reminder email to a worker with their magic link.
    """
    db = get_db()
    get_unified_progress = get_unified_progress_func()
    resend = get_resend()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    email = employee.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Employee has no email address")
    
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    token_payload = {
        "employee_id": employee_id,
        "email": email,
        "type": "worker_login",
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    magic_token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
    
    await db.magic_tokens.update_one(
        {"employee_id": employee_id, "email": email},
        {"$set": {
            "token": magic_token,
            "employee_id": employee_id,
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "used": False
        }},
        upsert=True
    )
    
    unified_progress = await get_unified_progress(employee_id, user)
    blockers = unified_progress.get("blockers", [])
    overall_pct = unified_progress.get("overall_percentage", 0)
    
    frontend_url = os.environ.get("FRONTEND_URL", "https://caretrust-portal.preview.emergentagent.com")
    portal_link = f"{frontend_url}/worker/verify?token={magic_token}"
    
    blockers_html = ""
    if blockers:
        blockers_html = "<ul style='margin: 16px 0; padding-left: 20px;'>"
        for blocker in blockers[:10]:
            blockers_html += f"<li style='margin: 4px 0; color: #dc2626;'>{blocker}</li>"
        blockers_html += "</ul>"
    else:
        blockers_html = "<p style='color: #16a34a;'>All items are complete! Please review your dashboard.</p>"
    
    custom_msg_html = ""
    if request.custom_message:
        custom_msg_html = f"""
        <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin: 16px 0;">
            <p style="margin: 0; color: #92400e;"><strong>Message from Admin:</strong></p>
            <p style="margin: 8px 0 0 0; color: #92400e;">{request.custom_message}</p>
        </div>
        """
    
    email_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 32px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Compliance Reminder</h1>
        </div>
        
        <div style="background: white; padding: 32px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 16px 16px;">
            <p style="font-size: 18px; margin-bottom: 8px;">Hello {emp_name},</p>
            
            {custom_msg_html}
            
            <p>This is a reminder to complete your outstanding compliance items. Your current progress is <strong>{overall_pct}%</strong>.</p>
            
            <p><strong>Outstanding items:</strong></p>
            {blockers_html}
            
            <div style="text-align: center; margin: 32px 0;">
                <a href="{portal_link}" style="display: inline-block; background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; padding: 16px 32px; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 16px;">
                    Go to My Portal
                </a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">This link will expire in 7 days. If you have any questions, please contact your manager.</p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
            
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                Osabea Healthcare Solutions - Compliance Portal<br>
                This is an automated reminder from your employer.
            </p>
        </div>
    </body>
    </html>
    """
    
    email_sent = False
    try:
        if resend.api_key:
            resend.Emails.send({
                "from": SENDER_EMAIL,
                "to": [email],
                "subject": f"Compliance Reminder - {overall_pct}% Complete",
                "html": email_html
            })
            email_sent = True
        else:
            logger.warning("Resend API key not configured - reminder email not sent")
    except Exception as e:
        logger.error(f"Failed to send reminder email: {e}")
    
    await log_audit_action(user.get("id", "admin"), "send_worker_reminder", "employee", employee_id, {
        "email": email,
        "custom_message": request.custom_message,
        "blockers_count": len(blockers),
        "progress_percentage": overall_pct,
        "email_sent": email_sent
    })
    
    return {
        "success": True,
        "message": f"Reminder {'sent to' if email_sent else 'prepared for'} {email}",
        "employee_id": employee_id,
        "blockers_sent": len(blockers),
        "email_sent": email_sent,
        "portal_link": portal_link
    }


# ==================== WORKER FORMS ====================

@router.get("/worker/forms")
async def get_worker_forms(worker: dict = Depends(get_current_worker)):
    """Get all forms and their status for the worker"""
    db = get_db()
    WORKER_FORM_DEFINITIONS = get_worker_form_definitions()
    
    employee_id = worker.get("employee_id")
    
    forms = []
    for form_id, form_def in WORKER_FORM_DEFINITIONS.items():
        progress = await db.form_progress.find_one({
            "employee_id": employee_id,
            "form_id": form_id
        }, {"_id": 0})
        
        submission = await db.form_submissions.find_one({
            "employee_id": employee_id,
            "form_type": form_id,
            "status": {"$in": ["submitted", "verified"]}
        }, {"_id": 0})
        
        status = "not_started"
        saved_at = None
        submitted_at = None
        progress_percentage = 0
        
        if submission:
            status = "submitted" if submission.get("status") == "submitted" else "verified"
            submitted_at = submission.get("submitted_at")
        elif progress:
            status = "in_progress"
            saved_at = progress.get("last_saved")
            form_data = progress.get("data", {})
            if form_data:
                filled_fields = sum(1 for v in form_data.values() if v)
                total_fields = len(form_data) or 1
                progress_percentage = int((filled_fields / total_fields) * 100)
        
        forms.append({
            "id": form_id,
            "name": form_def["name"],
            "description": form_def["description"],
            "required": form_def["required"],
            "status": status,
            "saved_at": saved_at,
            "submitted_at": submitted_at,
            "progress_percentage": progress_percentage
        })
    
    return {"forms": forms}


@router.get("/worker/forms/{form_id}")
async def get_worker_form_data(form_id: str, worker: dict = Depends(get_current_worker)):
    """Get saved form data for resuming, with auto-fill from employee profile"""
    db = get_db()
    WORKER_FORM_DEFINITIONS = get_worker_form_definitions()
    FORM_BASED_REQUIREMENTS = get_form_based_requirements()
    get_pre_interview_questionnaire_data = get_pre_interview_questionnaire_data_func()
    get_employment_history_form_data = get_employment_history_form_data_func()
    
    employee_id = worker.get("employee_id")
    
    if form_id not in WORKER_FORM_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Special handling for pre-interview questionnaire
    if form_id == "pre_interview_questionnaire":
        return await get_pre_interview_questionnaire_data(employee_id, worker)
    
    # Special handling for 10-year employment history
    if form_id == "employment_history_10yr":
        return await get_employment_history_form_data(employee_id, worker)
    
    submission = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "form_type": form_id
    }, {"_id": 0})
    
    if submission and submission.get("status") in ["submitted", "verified"]:
        return {
            "form_id": form_id,
            "status": "submitted",
            "data": submission.get("form_data", {}),
            "submitted_at": submission.get("submitted_at"),
            "can_edit": False
        }
    
    progress = await db.form_progress.find_one({
        "employee_id": employee_id,
        "form_id": form_id
    }, {"_id": 0})
    
    form_def_with_sections = FORM_BASED_REQUIREMENTS.get(form_id)
    
    auto_fill_data = {}
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    if employee and form_def_with_sections:
        def build_full_address():
            parts = [
                employee.get("address_line_1"),
                employee.get("address_line_2"),
                employee.get("city"),
                employee.get("county"),
                employee.get("postcode"),
                employee.get("country")
            ]
            return ", ".join(filter(None, parts))
        
        def build_full_name():
            parts = [
                employee.get("first_name"),
                employee.get("middle_name"),
                employee.get("last_name")
            ]
            return " ".join(filter(None, parts))
        
        def build_nok_address():
            parts = [
                employee.get("next_of_kin_address_line_1") or employee.get("next_of_kin_address"),
                employee.get("next_of_kin_city"),
                employee.get("next_of_kin_postcode")
            ]
            return ", ".join(filter(None, parts))
        
        field_value_map = {
            "full_name": build_full_name(),
            "first_name": employee.get("first_name"),
            "middle_name": employee.get("middle_name"),
            "last_name": employee.get("last_name"),
            "title": employee.get("title"),
            "date_of_birth": employee.get("date_of_birth"),
            "job_title": employee.get("role"),
            "role": employee.get("role"),
            "full_address": build_full_address(),
            "address": build_full_address(),
            "address_line_1": employee.get("address_line_1"),
            "address_line_2": employee.get("address_line_2"),
            "city": employee.get("city"),
            "county": employee.get("county"),
            "postcode": employee.get("postcode"),
            "country": employee.get("country"),
            "phone": employee.get("phone"),
            "contact_number": employee.get("phone"),
            "phone_primary": employee.get("phone"),
            "email": employee.get("email"),
            "ni_number": employee.get("ni_number"),
            "start_date": employee.get("start_date"),
            "next_of_kin_name": employee.get("next_of_kin_name") or employee.get("emergency_contact_name"),
            "emergency_name": employee.get("next_of_kin_name") or employee.get("emergency_contact_name"),
            "next_of_kin_relationship": employee.get("next_of_kin_relationship") or employee.get("emergency_contact_relationship"),
            "emergency_relationship": employee.get("next_of_kin_relationship") or employee.get("emergency_contact_relationship"),
            "next_of_kin_phone": employee.get("next_of_kin_phone") or employee.get("emergency_contact_phone"),
            "emergency_phone": employee.get("next_of_kin_phone") or employee.get("emergency_contact_phone"),
            "next_of_kin_address": build_nok_address(),
            "emergency_address": build_nok_address(),
            "emergency_contact_name": employee.get("emergency_contact_name") or employee.get("next_of_kin_name"),
            "emergency_contact_phone": employee.get("emergency_contact_phone") or employee.get("next_of_kin_phone"),
            "emergency_contact_relationship": employee.get("emergency_contact_relationship") or employee.get("next_of_kin_relationship"),
            "has_driving_licence": "Yes" if employee.get("has_driving_licence") else ("No" if employee.get("has_driving_licence") == False else None),
            "driving_licence_number": employee.get("driving_licence_number"),
            "has_own_vehicle": "Yes" if employee.get("has_own_vehicle") else ("No" if employee.get("has_own_vehicle") == False else None),
            "vehicle_registration": employee.get("vehicle_registration"),
            "today": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        }
        
        for section in form_def_with_sections.get("sections", []):
            for field in section.get("fields", []):
                field_id = field.get("id")
                auto_fill_key = field.get("auto_fill")
                
                if auto_fill_key and auto_fill_key in field_value_map:
                    value = field_value_map[auto_fill_key]
                    if value is not None and value != "":
                        auto_fill_data[field_id] = value
    
    merged_data = {**auto_fill_data, **(progress.get("data", {}) if progress else {})}
    
    return {
        "form_id": form_id,
        "form_definition": form_def_with_sections or WORKER_FORM_DEFINITIONS[form_id],
        "status": "in_progress" if progress else "not_started",
        "data": merged_data,
        "auto_fill_data": auto_fill_data,
        "last_saved": progress.get("last_saved") if progress else None,
        "can_edit": True
    }


@router.post("/worker/forms/{form_id}/save")
async def save_form_progress(
    form_id: str,
    request: FormSaveRequest,
    worker: dict = Depends(get_current_worker)
):
    """Auto-save form progress without submitting"""
    db = get_db()
    WORKER_FORM_DEFINITIONS = get_worker_form_definitions()
    
    employee_id = worker.get("employee_id")
    
    if form_id not in WORKER_FORM_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Form not found")
    
    submission = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "form_type": form_id,
        "status": {"$in": ["submitted", "verified"]}
    })
    
    if submission:
        raise HTTPException(status_code=400, detail="Form already submitted")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.form_progress.update_one(
        {
            "employee_id": employee_id,
            "form_id": form_id
        },
        {
            "$set": {
                "data": request.form_data,
                "last_saved": now,
                "status": "in_progress"
            },
            "$setOnInsert": {
                "created_at": now
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "saved_at": now,
        "message": "Progress saved. You can return and continue later."
    }


@router.post("/worker/forms/{form_id}/submit")
async def submit_worker_form(
    form_id: str,
    request: FormSubmitRequest,
    worker: dict = Depends(get_current_worker)
):
    """Final submit - form becomes read-only"""
    db = get_db()
    WORKER_FORM_DEFINITIONS = get_worker_form_definitions()
    resend = get_resend()
    ADMIN_EMAIL = get_admin_email()
    try_auto_promote_worker = get_try_auto_promote_worker_func()
    
    employee_id = worker.get("employee_id")
    employee_name = worker.get("name", "Unknown")
    
    if form_id not in WORKER_FORM_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Form not found")
    
    existing = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "form_type": form_id,
        "status": {"$in": ["submitted", "verified"]}
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Form already submitted")
    
    now = datetime.now(timezone.utc).isoformat()
    
    form_def = WORKER_FORM_DEFINITIONS[form_id]
    requirement_id = form_def.get("admin_requirement_id", form_id)
    
    submission = {
        "id": f"form_{uuid.uuid4().hex[:12]}",
        "employee_id": employee_id,
        "form_type": form_id,
        "requirement_id": requirement_id,
        "form_data": request.form_data,
        "data": request.form_data,
        "submitted_at": now,
        "submitted_by": f"worker_{employee_id}",
        "submitted_by_name": employee_name,
        "status": "submitted",
        "awaiting_admin_review": True,
        "verified": False,
        "version": 1,
        "created_at": now
    }
    
    await db.form_submissions.insert_one(submission)
    
    await db.form_progress.delete_one({
        "employee_id": employee_id,
        "form_id": form_id
    })
    
    await log_audit_action(
        employee_id,
        "worker_form_submitted",
        "form_submission",
        submission["id"],
        {
            "form_id": form_id,
            "form_name": WORKER_FORM_DEFINITIONS[form_id]["name"]
        }
    )
    
    # Send admin notification
    try:
        if resend.api_key:
            employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1, "employee_code": 1})
            emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() if employee else employee_name
            emp_code = employee.get("employee_code", "N/A") if employee else "N/A"
            
            admin_email_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #0F172A; padding: 16px; text-align: center;">
                    <h2 style="color: white; margin: 0;">Form Submission</h2>
                </div>
                <div style="padding: 24px; background: #f8fafc;">
                    <h3 style="color: #1e293b; margin-top: 0;">New Form Requires Review</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Employee:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: bold;">{emp_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Employee Code:</td>
                            <td style="padding: 8px 0; color: #1e293b;">{emp_code}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Form:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: bold;">{WORKER_FORM_DEFINITIONS[form_id]['name']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Submitted:</td>
                            <td style="padding: 8px 0; color: #1e293b;">{now[:16].replace('T', ' ')}</td>
                        </tr>
                    </table>
                    <div style="margin-top: 24px; text-align: center;">
                        <a href="{os.environ.get('FRONTEND_URL', 'https://caretrust-portal.preview.emergentagent.com')}/portal/employees/{employee_id}?tab=compliance" style="background: #2563EB; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                            Review Submission
                        </a>
                    </div>
                </div>
            </div>
            """
            
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [ADMIN_EMAIL],
                "subject": f"Form Submission: {WORKER_FORM_DEFINITIONS[form_id]['name']} - {emp_name}",
                "html": admin_email_html
            })
            logger.info(f"Admin notification sent for form submission: {form_id} by {employee_id}")
    except Exception as e:
        logger.warning(f"Failed to send admin notification for form: {e}")
    
    # Try auto-promotion after form submission
    await try_auto_promote_worker(employee_id)
    
    return {
        "success": True,
        "submission_id": submission["id"],
        "submitted_at": now,
        "message": f"{WORKER_FORM_DEFINITIONS[form_id]['name']} submitted successfully. Awaiting admin review."
    }
