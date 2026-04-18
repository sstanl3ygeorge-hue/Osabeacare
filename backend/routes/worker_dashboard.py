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
from induction_definitions import get_employee_induction_status

logger = logging.getLogger(__name__)

# Live evidence statuses only (everything else is historical/non-counting)
_LIVE_EXCLUDED_STATUSES = frozenset({
    "deleted", "superseded", "rejected", "amendment_requested",
    "invalidated", "uploaded_in_error", "removed", "archived",
    "misfiled", "moved", "replaced",
})


def _is_live_document(doc: dict) -> bool:
    status = (doc.get("status") or "").lower().strip()
    review_status = (doc.get("review_status") or "").lower().strip()
    is_active = doc.get("is_active")
    if status in _LIVE_EXCLUDED_STATUSES:
        return False
    if review_status in {"rejected", "amendment_requested", "invalidated"}:
        return False
    if is_active is False:
        return False
    return True


def _is_proof_role_document(doc: dict, current_proof_doc_ids: Optional[set] = None) -> bool:
    role = (doc.get("document_role") or "").lower().strip()
    source_type = (doc.get("source_type") or "").lower().strip()
    doc_id = doc.get("id")
    if role in {"proof", "verification_proof", "check_proof"}:
        return True
    if source_type in {"verification_proof", "check_proof"}:
        return True
    if current_proof_doc_ids and doc_id and doc_id in current_proof_doc_ids:
        return True
    return False


def _matches_canonical_requirement(
    requirement_id: str,
    canonical_target: str,
    aliases: dict,
    exclusions: frozenset,
) -> bool:
    if not requirement_id:
        return False
    req_lower = requirement_id.lower().strip()
    if req_lower in exclusions:
        return False
    canonical = aliases.get(req_lower, req_lower)
    if canonical == canonical_target:
        return True
    raw_canonical = aliases.get(req_lower)
    # Identity must match explicit canonical alias mapping only.
    # Do not allow loose substring fallback for identity.
    if canonical_target == "identity" and raw_canonical is None:
        return False
    # Never treat verification/check buckets as upload evidence via substring fallback.
    if "verification" in req_lower or "check" in req_lower:
        return False
    if raw_canonical is None and canonical_target in req_lower:
        return True
    return False

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


def get_evaluate_employee_training_status_func():
    """Lazy import of evaluate_employee_training_status from training evaluator service."""
    from services.training_evaluator import evaluate_employee_training_status
    return evaluate_employee_training_status


def _get_mandatory_training_ids():
    """Lazy import of canonical mandatory training IDs from training evaluator service."""
    from services.training_evaluator import get_canonical_mandatory_training_ids
    return get_canonical_mandatory_training_ids()


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

    ref_doc = await db.references.find_one(
        {"employee_id": employee_id},
        {"_id": 0}
    ) or {}

    rtw_check = await db.rtw_checks.find_one({"employee_id": employee_id, "is_current": True}, {"_id": 0, "proof_document_id": 1})
    dbs_check = await db.dbs_checks.find_one({"employee_id": employee_id, "is_current": True}, {"_id": 0, "proof_document_id": 1})
    current_proof_doc_ids = {
        doc_id for doc_id in [
            (rtw_check or {}).get("proof_document_id"),
            (dbs_check or {}).get("proof_document_id"),
        ] if doc_id
    }
    
    # Determine if active employee or still onboarding
    employee_status = employee.get("status", "onboarding")
    is_active_employee = employee_status == "active"
    
    # Get documents - Import the global constant from server.py for single source of truth.
    # Also exclude amendment_requested and invalidated: those docs are not live evidence.
    # Filter review_status to exclude docs an admin has rejected via review workflow.
    from server import EXCLUDED_DOC_STATUSES
    _worker_excluded = list(EXCLUDED_DOC_STATUSES) + ["amendment_requested", "invalidated"]
    documents = await db.employee_documents.find({
        "employee_id": employee_id,
        "status": {"$nin": _worker_excluded},
        "review_status": {"$nin": ["rejected", "amendment_requested", "invalidated"]},
        "$or": [
            {"is_active": True},
            {"is_active": {"$exists": False}}
        ]
    }).to_list(length=200)
    documents = [d for d in documents if _is_live_document(d)]
    documents = [d for d in documents if not _is_proof_role_document(d, current_proof_doc_ids)]
    
    rejected_documents = await db.employee_documents.find({
        "employee_id": employee_id,
        "$and": [
            {
                "$or": [
                    {"status": {"$in": ["rejected", "amendment_requested", "invalidated"]}},
                    {"review_status": {"$in": ["rejected", "amendment_requested", "invalidated"]}},
                ]
            },
            {
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}}
                ]
            }
        ]
    }).to_list(length=200)
    rejected_documents = [d for d in rejected_documents if (d.get("is_active") is not False)]
    rejected_documents = [d for d in rejected_documents if not _is_proof_role_document(d, current_proof_doc_ids)]

    def get_rejection_details(doc: dict) -> dict:
        return {
            "rejection_reason": doc.get("amendment_reason") or doc.get("rejection_reason") or doc.get("uploaded_in_error_reason") or "Please re-upload this document.",
            "previous_file_name": doc.get("file_name") or doc.get("original_filename"),
            "rejected_by_name": doc.get("amendment_requested_by_name") or doc.get("rejected_by_name") or doc.get("verification_stamp_by_name")
        }
    
    # Required document types with their acceptable requirement_id patterns.
    # Patterns and exclusions are derived directly from the unified engine constants
    # so worker dashboard and unified engine always agree on which docs count.
    from unified_compliance_engine import DOC_REQUIREMENT_ALIASES, DOC_REQUIREMENT_EXCLUSIONS
    required_docs = {
        "right_to_work": {
            "name": "Right to Work",
            "patterns": ["right_to_work"] + [
                k for k, v in DOC_REQUIREMENT_ALIASES.items() if v == "right_to_work"
            ],
            "exclude_patterns": ["right_to_work_check"]
        },
        "dbs": {
            "name": "DBS Certificate",
            "patterns": ["dbs"] + [
                k for k, v in DOC_REQUIREMENT_ALIASES.items() if v == "dbs"
            ],
            "exclude_patterns": ["dbs_check", "dbs_status_check", "dbs_update"]
        },
        "identity": {
            "name": "Identity (Passport/ID)",
            "patterns": ["identity"] + [
                k for k, v in DOC_REQUIREMENT_ALIASES.items() if v == "identity"
            ],
            "exclude_patterns": ["identity_check", "identity_verification"]
        },
        "proof_of_address": {
            "name": "Proof of Address",
            "patterns": ["proof_of_address"] + [
                k for k, v in DOC_REQUIREMENT_ALIASES.items() if v == "proof_of_address"
            ],
            "exclude_patterns": ["address_check", "address_verification"]
        }
    }
    
    def matches_requirement(requirement_id: str, doc_config: dict) -> bool:
        """Check if a requirement_id matches a document type's patterns.

        Uses the same alias + exclusion logic as unified_compliance_engine so that
        worker and admin always agree on which documents count for each requirement.
        """
        if not requirement_id:
            return False
        req_lower = requirement_id.lower().strip()

        # Hard-reject any known exclusion (check/verification record IDs that share
        # a prefix with real evidence requirement IDs).
        if req_lower in DOC_REQUIREMENT_EXCLUSIONS:
            return False

        # Never classify verification/check/review buckets as upload evidence.
        # This prevents stale identity verification IDs from showing as live
        # "Awaiting Review" identity documents on the worker dashboard.
        if "verification" in req_lower or "check" in req_lower or "review" in req_lower:
            return False

        # Resolve alias: if req_lower maps to a canonical, compare to canonical patterns
        canonical = DOC_REQUIREMENT_ALIASES.get(req_lower, req_lower)
        raw_canonical = DOC_REQUIREMENT_ALIASES.get(req_lower)
        is_identity_doc_type = "identity" in doc_config.get("patterns", [])

        for pattern in doc_config.get("patterns", []):
            # Exact match on the resolved canonical name (primary path)
            if canonical == pattern:
                return True
            # Substring fallback for un-mapped legacy IDs
            # (e.g. "identity_evidence_2" not in alias map)
            if is_identity_doc_type and raw_canonical is None and pattern == "identity":
                continue
            if pattern in req_lower:
                return True
        return False
    
    missing_docs = []
    completed_docs = []
    # Initialised to None here; populated after the documents loop by the
    # unified-status fetch.  The post-loop second pass below applies the
    # canonical overrides once both are available.
    rtw_canonical_item = None
    dbs_canonical_item = None
    identity_canonical_item = None

    for doc_type, doc_config in required_docs.items():
        doc_name = doc_config["name"]
        # All documents here are already filtered to active statuses only (query level)
        matching = [d for d in documents 
                   if matches_requirement(d.get("requirement_id", ""), doc_config)]
        rejected_matching = [d for d in rejected_documents 
                             if matches_requirement(d.get("requirement_id", ""), doc_config)]
        amendment_requested_docs = [d for d in matching if d.get("status") == "amendment_requested"]
        
        # Active docs are the ones we can work with
        active_docs = [d for d in matching if d.get("status") != "amendment_requested"]
        
        if active_docs:
            def canonical_status(doc):
                return doc.get("review_status") or doc.get("status")

            def is_verified_doc(doc):
                status = canonical_status(doc)
                return status in ["verified", "approved"] or doc.get("verification_stamp") not in [None, "", "not_verified"] or doc.get("verified") == True

            verified_docs = [d for d in active_docs if is_verified_doc(d)]
            if verified_docs:
                verified_docs.sort(key=lambda x: x.get("reviewed_at") or x.get("verified_at") or x.get("verification_stamp_at") or x.get("uploaded_at") or "", reverse=True)
                doc = verified_docs[0]
            else:
                active_docs.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
                doc = active_docs[0]
            
            is_verified = is_verified_doc(doc)
            file_url = None
            if is_verified and doc.get("stamped_file_url"):
                file_url = doc.get("stamped_file_url")
            elif doc.get("file_url"):
                file_url = doc.get("file_url")
            
            canonical_status_value = doc.get("review_status") or doc.get("status")
            if doc_type == "right_to_work" and rtw_canonical_item:
                # Canonical item is the sole source for all status/verification fields.
                # Document row is used only for file display metadata.
                rtw_is_verified = bool(rtw_canonical_item.get("completed"))
                rtw_display_status = (
                    rtw_canonical_item.get("verification_status")
                    or ("verified" if rtw_is_verified else "check_required")
                )
                rtw_entry = {
                    "id": doc.get("id"),
                    "type": doc_type,
                    "name": doc_name,
                    "verified": rtw_is_verified,
                    "uploaded_at": doc.get("uploaded_at"),
                    "file_name": doc.get("file_name") or doc.get("original_filename"),
                    "file_url": doc.get("stamped_file_url") or doc.get("file_url"),
                    "document_id": doc.get("id"),
                    "verification_stamp": doc.get("verification_stamp"),
                    "verification_stamp_label": doc.get("verification_stamp_label"),
                    "verified_by": None,
                    "verified_by_name": None,
                    "verified_at": rtw_canonical_item.get("verified_at"),
                    "status": rtw_display_status,
                    "raw_status": doc.get("status"),
                    "review_status": None,
                    "review_reason": None,
                    "reviewed_at": None,
                    "reviewed_by": None,
                    "reviewed_by_name": None,
                }
                if rtw_canonical_item.get("next_action"):
                    rtw_entry["next_action"] = rtw_canonical_item["next_action"]
                if rtw_canonical_item.get("expiry_date"):
                    rtw_entry["expiry_date"] = rtw_canonical_item["expiry_date"]
                if rtw_canonical_item.get("follow_up_due_at"):
                    rtw_entry["follow_up_due_at"] = rtw_canonical_item["follow_up_due_at"]
                completed_docs.append(rtw_entry)
            elif doc_type == "dbs" and dbs_canonical_item:
                # Canonical item is the sole source for DBS status/verification fields.
                # Document row is used only for file display metadata.
                dbs_is_verified = bool(dbs_canonical_item.get("completed"))
                dbs_display_status = (
                    dbs_canonical_item.get("verification_status")
                    or ("verified" if dbs_is_verified else "check_required")
                )
                dbs_entry = {
                    "id": doc.get("id"),
                    "type": doc_type,
                    "name": doc_name,
                    "verified": dbs_is_verified,
                    "uploaded_at": doc.get("uploaded_at"),
                    "file_name": doc.get("file_name") or doc.get("original_filename"),
                    "file_url": doc.get("stamped_file_url") or doc.get("file_url"),
                    "document_id": doc.get("id"),
                    "verification_stamp": doc.get("verification_stamp"),
                    "verification_stamp_label": doc.get("verification_stamp_label"),
                    "verified_by": None,
                    "verified_by_name": None,
                    "verified_at": dbs_canonical_item.get("verified_at"),
                    "status": dbs_display_status,
                    "raw_status": doc.get("status"),
                    "review_status": None,
                    "review_reason": None,
                    "reviewed_at": None,
                    "reviewed_by": None,
                    "reviewed_by_name": None,
                }
                if dbs_canonical_item.get("next_action"):
                    dbs_entry["next_action"] = dbs_canonical_item["next_action"]
                if dbs_canonical_item.get("recheck_date"):
                    dbs_entry["recheck_date"] = dbs_canonical_item["recheck_date"]
                completed_docs.append(dbs_entry)
            else:
                if is_verified:
                    display_status = "verified"
                elif canonical_status_value in ["pending", "submitted", "uploaded", "pending_review", "pending_approval"]:
                    display_status = "awaiting_review"
                else:
                    display_status = canonical_status_value or doc.get("status", "uploaded")

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
                    "raw_status": doc.get("status"),
                    "review_status": doc.get("review_status"),
                    "review_reason": doc.get("review_reason"),
                    "reviewed_at": doc.get("reviewed_at"),
                    "reviewed_by": doc.get("reviewed_by"),
                    "reviewed_by_name": doc.get("reviewed_by_name")
                })
        elif doc_type == "right_to_work" and rtw_canonical_item:
            # No active document row: build entry from canonical item only.
            # File metadata from first document in canonical list if present.
            rtw_is_verified = bool(rtw_canonical_item.get("completed"))
            rtw_display_status = (
                rtw_canonical_item.get("verification_status")
                or ("verified" if rtw_is_verified else "check_required")
            )
            rtw_file_doc = (rtw_canonical_item.get("documents") or [{}])[0]
            canonical_entry = {
                "id": rtw_file_doc.get("id") or rtw_canonical_item.get("id") or "rtw_canonical",
                "type": doc_type,
                "name": doc_name,
                "verified": rtw_is_verified,
                "uploaded_at": rtw_file_doc.get("uploaded_at") or rtw_canonical_item.get("updated_at"),
                "file_name": rtw_file_doc.get("file_name") or rtw_file_doc.get("original_filename") or "Right to Work document",
                "file_url": rtw_file_doc.get("file_url"),
                "document_id": rtw_file_doc.get("id"),
                "verification_stamp": None,
                "verification_stamp_label": None,
                "verified_by": None,
                "verified_by_name": None,
                "verified_at": rtw_canonical_item.get("verified_at"),
                "status": rtw_display_status,
                "raw_status": None,
                "review_status": None,
                "review_reason": None,
                "reviewed_at": None,
                "reviewed_by": None,
                "reviewed_by_name": None,
            }
            if rtw_canonical_item.get("next_action"):
                canonical_entry["next_action"] = rtw_canonical_item["next_action"]
            if rtw_canonical_item.get("expiry_date"):
                canonical_entry["expiry_date"] = rtw_canonical_item["expiry_date"]
            if rtw_canonical_item.get("follow_up_due_at"):
                canonical_entry["follow_up_due_at"] = rtw_canonical_item["follow_up_due_at"]
            completed_docs.append(canonical_entry)
        elif doc_type == "dbs" and dbs_canonical_item:
            # No active DBS document row: build entry purely from canonical item.
            dbs_is_verified = bool(dbs_canonical_item.get("completed"))
            dbs_display_status = (
                dbs_canonical_item.get("verification_status")
                or ("verified" if dbs_is_verified else "check_required")
            )
            dbs_file_doc = (dbs_canonical_item.get("documents") or [{}])[0]
            dbs_canonical_entry = {
                "id": dbs_file_doc.get("id") or dbs_canonical_item.get("id") or "dbs_canonical",
                "type": doc_type,
                "name": doc_name,
                "verified": dbs_is_verified,
                "uploaded_at": dbs_file_doc.get("uploaded_at") or dbs_canonical_item.get("updated_at"),
                "file_name": dbs_file_doc.get("file_name") or dbs_file_doc.get("original_filename") or "DBS Certificate",
                "file_url": dbs_file_doc.get("file_url"),
                "document_id": dbs_file_doc.get("id"),
                "verification_stamp": None,
                "verification_stamp_label": None,
                "verified_by": None,
                "verified_by_name": None,
                "verified_at": dbs_canonical_item.get("verified_at"),
                "status": dbs_display_status,
                "raw_status": None,
                "review_status": None,
                "review_reason": None,
                "reviewed_at": None,
                "reviewed_by": None,
                "reviewed_by_name": None,
            }
            if dbs_canonical_item.get("next_action"):
                dbs_canonical_entry["next_action"] = dbs_canonical_item["next_action"]
            if dbs_canonical_item.get("recheck_date"):
                dbs_canonical_entry["recheck_date"] = dbs_canonical_item["recheck_date"]
            completed_docs.append(dbs_canonical_entry)
        elif amendment_requested_docs:
            amendment_requested_docs.sort(key=lambda x: x.get("updated_at") or x.get("uploaded_at") or "", reverse=True)
            rejected_doc = amendment_requested_docs[0]
            missing_docs.append({
                "type": doc_type,
                "name": doc_name,
                "action": "upload",
                "rejection": get_rejection_details(rejected_doc)
            })
        elif rejected_matching:
            rejected_matching.sort(key=lambda x: x.get("updated_at") or x.get("uploaded_at") or "", reverse=True)
            rejected_doc = rejected_matching[0]
            missing_docs.append({
                "type": doc_type,
                "name": doc_name,
                "action": "upload",
                "rejection": get_rejection_details(rejected_doc)
            })
        else:
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
    rejected_poa_docs = [d for d in rejected_documents 
                        if matches_requirement(d.get("requirement_id", ""), poa_config)]
    
    # Remove the generic POA entry added by the loop above - we'll handle POA specially
    completed_docs = [d for d in completed_docs if d["type"] != "proof_of_address"]
    
    if len(poa_docs) == 0:
        if rejected_poa_docs:
            rejected_poa_docs.sort(key=lambda x: x.get("updated_at") or x.get("uploaded_at") or "", reverse=True)
            rejected_poa_doc = rejected_poa_docs[0]
            missing_docs.append({
                "type": "proof_of_address",
                "name": "Proof of Address (need 2)",
                "action": "upload",
                "rejection": get_rejection_details(rejected_poa_doc)
            })
        else:
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
            "status": "verified" if is_verified else "awaiting_review",
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
                "status": "verified" if is_verified else "awaiting_review",
                "verified_by_name": poa_doc.get("verification_stamp_by_name") or poa_doc.get("verified_by_name"),
                "verified_at": poa_doc.get("verification_stamp_at") or poa_doc.get("verified_at"),
            })
    
    # -------- TRAINING: canonical evaluator (Phase 2 Step 5) --------
    now = datetime.now(timezone.utc)

    evaluate_training = get_evaluate_employee_training_status_func()
    role = employee.get("role", "") or employee.get("job_title", "")
    training_eval = await evaluate_training(employee_id, role)

    # IDs that are compliance-mandatory – derived from canonical MANDATORY_ITEMS.
    _MANDATORY_TRAINING_IDS = _get_mandatory_training_ids()

    all_mandatory_trainings = []
    all_recommended_trainings = []
    missing_trainings = []
    completed_trainings = []
    expired_trainings = []

    for item in training_eval.get("items", []):
        entry = {
            "id": item["code"],
            "name": item["title"],
            "status": item["status"],               # canonical — no mapping
            "completion_date": item.get("completion_date"),
            "expiry_date": item.get("expires_at"),
            "verified": item.get("verified", False),
            "record_id": item.get("record_id"),
            "days_until_expiry": item.get("days_until_expiry"),
            "detail": item.get("detail"),
            "blocker": item.get("blocker", False),
            "rejection_reason": item.get("rejection_reason"),
        }

        if item["code"] in _MANDATORY_TRAINING_IDS:
            all_mandatory_trainings.append(entry)
        else:
            all_recommended_trainings.append(entry)

        # Bucket into convenience lists (top-level response keys)
        if item["status"] in ("missing", "rejected"):
            missing_trainings.append({
                "id": item["code"],
                "name": item["title"],
                "action": "upload_certificate",
            })
        elif item["status"] == "expired":
            expired_trainings.append({
                "id": item["code"],
                "name": item["title"],
                "expiry_date": item.get("expires_at"),
                "action": "upload_certificate",
            })
        elif item["status"] in ("completed", "verified", "due_soon", "awaiting_review"):
            completed_trainings.append({
                "id": item["code"],
                "name": item["title"],
                "completion_date": item.get("completion_date"),
                "expiry_date": item.get("expires_at"),
                "verified": item.get("verified", False),
            })
    
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
        "signed": bool(contract_ack and (
            contract_ack.get("acknowledged")
            or contract_ack.get("status") in ("signed", "submitted", "verified")
        )),
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
    try:
        unified_status = await get_unified_employee_status(employee_id, db, user_role="worker", include_details=True)
        progress_percentage = unified_status["progress"]["percentage"]
        total_required = unified_status["progress"]["total"]
        total_completed = unified_status["progress"]["completed"]
        unified_blockers = unified_status.get("blockers", [])
        has_blockers = len(unified_blockers) > 0 or not contract_signed
        
        rtw_canonical_item = next(
            (
                item for item in unified_status.get("categories", {}).get("documents", {}).get("items", [])
                if item.get("id") == "right_to_work"
            ),
            None
        )
        dbs_canonical_item = next(
            (
                item for item in unified_status.get("categories", {}).get("documents", {}).get("items", [])
                if item.get("id") in ("dbs", "dbs_certificate")
            ),
            None
        )
        identity_canonical_item = next(
            (
                item for item in unified_status.get("categories", {}).get("documents", {}).get("items", [])
                if item.get("id") == "identity"
            ),
            None
        )
    except Exception as e:
        logger.error(f"Unified progress failed for {employee_id}: {e}")
        total_required = len(required_docs) + 1 + len(all_mandatory_trainings)
        total_completed = len([d for d in completed_docs if not d.get("partial")]) + len(completed_trainings)
        if len(poa_docs) >= 2:
            total_completed += 1
        progress_percentage = round((total_completed / total_required) * 100) if total_required > 0 else 0
        has_blockers = len(missing_docs) > 0 or len(missing_trainings) > 0 or len(expired_trainings) > 0 or not contract_signed
        unified_blockers = []
        dbs_canonical_item = None
        identity_canonical_item = None

    # Second pass: apply canonical UCE state to completed_docs entries that were
    # built from raw document rows before the unified-status fetch.
    # If the canonical item says no live evidence exists, remove the entry from
    # completed_docs and add it to missing_docs so the worker is prompted to upload.
    # This prevents phantom "Pending Verification" entries when admin sees no evidence
    # (e.g. a doc stored with a non-canonical requirement_id that the worker's substring
    # matcher catches but the admin's exact-key lookup misses).
    if rtw_canonical_item or dbs_canonical_item or identity_canonical_item:
        entries_to_remove = []
        for entry in completed_docs:
            if entry.get("type") == "identity" and identity_canonical_item:
                if not identity_canonical_item.get("has_upload"):
                    # UCE says no live identity evidence — move to missing so worker can upload
                    entries_to_remove.append(entry)
                    missing_docs.append({"type": "identity", "name": "Identity (Passport/ID)", "action": "upload"})
                    continue
                identity_is_verified = bool(identity_canonical_item.get("completed"))
                entry["verified"] = identity_is_verified
                entry["status"] = (
                    identity_canonical_item.get("verification_status")
                    or ("verified" if identity_is_verified else "awaiting_review")
                )
                if entry["status"] in ("missing", "reupload_required", "check_required", "check_in_progress", "proof_required"):
                    entry["verified"] = False
            elif entry.get("type") == "right_to_work" and rtw_canonical_item:
                if not rtw_canonical_item.get("has_upload"):
                    # Canonical says no live evidence — move to missing
                    entries_to_remove.append(entry)
                    missing_docs.append({"type": "right_to_work", "name": "Right to Work", "action": "upload"})
                    continue
                rtw_is_verified = bool(rtw_canonical_item.get("completed"))
                entry["verified"] = rtw_is_verified
                entry["status"] = (
                    rtw_canonical_item.get("verification_status")
                    or ("verified" if rtw_is_verified else "check_required")
                )
                # Safeguard: proof required but missing → not verified
                if entry["status"] in ("proof_required", "check_required", "check_in_progress", "missing", "reupload_required"):
                    entry["verified"] = False
                entry["verified_at"] = rtw_canonical_item.get("verified_at")
                if rtw_canonical_item.get("next_action"):
                    entry["next_action"] = rtw_canonical_item["next_action"]
                if rtw_canonical_item.get("expiry_date"):
                    entry["expiry_date"] = rtw_canonical_item["expiry_date"]
                if rtw_canonical_item.get("follow_up_due_at"):
                    entry["follow_up_due_at"] = rtw_canonical_item["follow_up_due_at"]
            elif entry.get("type") == "dbs" and dbs_canonical_item:
                if not dbs_canonical_item.get("has_upload"):
                    # Canonical says no live evidence — move to missing
                    entries_to_remove.append(entry)
                    missing_docs.append({"type": "dbs", "name": "DBS Certificate", "action": "upload"})
                    continue
                dbs_is_verified = bool(dbs_canonical_item.get("completed"))
                entry["verified"] = dbs_is_verified
                entry["status"] = (
                    dbs_canonical_item.get("verification_status")
                    or ("verified" if dbs_is_verified else "check_required")
                )
                # Safeguard: proof required but missing → not verified
                if entry["status"] in ("proof_required", "check_required", "check_in_progress", "missing", "reupload_required"):
                    entry["verified"] = False
                entry["verified_at"] = dbs_canonical_item.get("verified_at")
                if dbs_canonical_item.get("next_action"):
                    entry["next_action"] = dbs_canonical_item["next_action"]
                if dbs_canonical_item.get("recheck_date"):
                    entry["recheck_date"] = dbs_canonical_item["recheck_date"]
        for entry in entries_to_remove:
            completed_docs.remove(entry)

    # HARD RULE: no live canonical identity file => no identity awaiting/completed entry.
    # Identity state for workers must be driven only by live active identity documents,
    # never by stale verification/check history.
    live_identity_docs = [
        d for d in documents
        if _matches_canonical_requirement(
            d.get("requirement_id", ""),
            "identity",
            DOC_REQUIREMENT_ALIASES,
            DOC_REQUIREMENT_EXCLUSIONS,
        )
    ]
    if len(live_identity_docs) == 0:
        completed_docs = [d for d in completed_docs if d.get("type") != "identity"]
        has_identity_missing_entry = any(d.get("type") == "identity" for d in missing_docs)
        if not has_identity_missing_entry:
            missing_docs.append({
                "type": "identity",
                "name": "Identity (Passport/ID)",
                "action": "upload"
            })

    status = "READY" if is_active_employee else ("NOT_READY" if has_blockers else "READY")
    
    # Get form status for onboarding employees
    forms_status = []
    if not is_active_employee:
        _emp_role_for_forms = (employee.get("job_role") or employee.get("role") or "").lower()
        for form_id, form_def in WORKER_FORM_DEFINITIONS.items():
            # Skip role-aware forms if this worker's role is not in the required list
            if form_def.get("role_aware") and form_def.get("roles_required"):
                if not any(r in _emp_role_for_forms for r in form_def["roles_required"]):
                    continue
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
    job_role = (employee.get("job_role") or employee.get("role") or "").lower()
    
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
    has_canonical_references = bool(ref_doc)
    for ref_num in [1, 2]:
        prefix = f"reference_{ref_num}_"

        if has_canonical_references:
            ref_data = ref_doc.get(f"ref{ref_num}") or {}
            declared_data = ref_data.get("declared") or {}
            request_data = ref_data.get("request") or {}
            response_data = ref_data.get("response") or {}
            verification_data = ref_data.get("verification") or {}
            mismatch_data = ref_data.get("mismatch") or {}

            referee_name = declared_data.get("name", "")
            referee_email = declared_data.get("email", "")
            is_declared = bool(referee_name and referee_email)

            request_sent_at = request_data.get("sent_at")
            request_status = request_data.get("status")
            request_token = request_data.get("token")
            request_sent = bool(request_sent_at) or request_status in ["awaiting_response", "requested", "sent"] or bool(request_token)

            response_received_at = response_data.get("received_at")
            response_received = (
                bool(response_data)
                or bool(response_received_at)
                or request_status in ["submitted", "awaiting_review", "verified", "rejected"]
            )

            is_verified = verification_data.get("status") == "verified"
            verified_at = verification_data.get("verified_at")
            verified_by = verification_data.get("verified_by")

            is_rejected = verification_data.get("status") == "rejected" or request_status == "rejected"
            rejection_reason = verification_data.get("rejection_reason", "")

            data_cleared = is_rejected and not referee_name
            mismatch_explanation = mismatch_data.get("reason") or mismatch_data.get("notes")
            mismatch_explanation_status = "documented" if mismatch_data.get("documented") else "not_submitted"
            # Admin writes decision to employee flat fields only; db.references.mismatch.detected is a bool flag.
            mismatch_admin_decision = employee.get(f"{prefix}mismatch_admin_decision")
            referee_company = declared_data.get("organisation") or declared_data.get("company", "")
        else:
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
            mismatch_explanation = employee.get(f"{prefix}mismatch_explanation")
            mismatch_explanation_status = employee.get(f"{prefix}mismatch_explanation_status", "not_submitted")
            mismatch_admin_decision = employee.get(f"{prefix}mismatch_admin_decision")
            referee_company = employee.get(f"{prefix}company", "")
        
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
        
        references_status.append({
            "reference_number": ref_num,
            "referee_name": referee_name if is_declared else None,
            "referee_company": referee_company if is_declared else None,
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
    
    # Induction checklist status — canonical function
    induction_canonical = await get_employee_induction_status(db, employee_id)
    induction_status = {
        "total": induction_canonical["total"],
        "completed": induction_canonical["completed"],
        "items": [
            {
                "id": item["id"],
                "name": item["name"],
                "mandatory": item["mandatory"],
                "completed": item["completed"],
                "completed_at": item["completed_at"],
                "completed_by_name": item["completed_by_name"],
                "synced_from_training": item["synced_from_training"],
            }
            for item in induction_canonical["items"]
        ],
        "overall_status": induction_canonical["overall_status"],
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
            "job_role": employee.get("job_role", ""),
            "person_stage": "employee" if employee_status in ("onboarding", "active", "inactive", "archived") else "applicant",
            "recruitment_approved": employee.get("recruitment_approved", False),
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
        "recommended_trainings": all_recommended_trainings,
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

    # Server-side guardrail: enforce max ACTIVE LIVE evidence files per requirement.
    # This prevents worker/admin desync when frontend limits are bypassed.
    is_training_cert = requirement_id.startswith("training") or "training" in requirement_id.lower()
    if not is_training_cert:
        from unified_compliance_engine import DOC_REQUIREMENT_ALIASES, DOC_REQUIREMENT_EXCLUSIONS

        _raw_req = requirement_id.lower().strip()
        _canonical_req = DOC_REQUIREMENT_ALIASES.get(_raw_req, _raw_req)
        if _canonical_req not in {"right_to_work", "dbs", "identity", "proof_of_address"}:
            if "right_to_work" in _raw_req:
                _canonical_req = "right_to_work"
            elif "dbs" in _raw_req:
                _canonical_req = "dbs"
            elif "identity" in _raw_req or "passport" in _raw_req or "id_document" in _raw_req:
                _canonical_req = "identity"
            elif "proof_of_address" in _raw_req or _raw_req.startswith("poa"):
                _canonical_req = "proof_of_address"
        _max_active_limits = {
            "right_to_work": 2,
            "dbs": 1,
            "identity": 2,
            "proof_of_address": 3,
        }
        _max_allowed = _max_active_limits.get(_canonical_req)

        if _max_allowed is not None:
            live_docs = await db.employee_documents.find({
                "employee_id": employee_id,
                "status": {"$nin": list(_LIVE_EXCLUDED_STATUSES)},
                "review_status": {"$nin": ["rejected", "amendment_requested", "invalidated"]},
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}},
                ],
            }, {"_id": 0, "id": 1, "requirement_id": 1, "status": 1, "review_status": 1, "is_active": 1, "source_type": 1, "file_name": 1, "original_filename": 1, "uploaded_by": 1}).to_list(length=300)

            live_docs = [d for d in live_docs if _is_live_document(d)]
            live_docs = [d for d in live_docs if not _is_proof_role_document(d)]
            _matching_live_count = sum(
                1 for d in live_docs
                if _matches_canonical_requirement(
                    d.get("requirement_id", ""),
                    _canonical_req,
                    DOC_REQUIREMENT_ALIASES,
                    DOC_REQUIREMENT_EXCLUSIONS,
                )
            )

            if _matching_live_count >= _max_allowed:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Upload limit reached for {_canonical_req.replace('_', ' ')}: "
                        f"{_matching_live_count}/{_max_allowed} active files. "
                        "Please remove/reject/supersede old files before uploading a new one."
                    )
                )
    
    contents = await file.read()
    
    is_valid, detected_type, error_msg = validate_file_content(contents, file.content_type)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    if requirement_id in ["cv", "resume", "curriculum_vitae"] or "cv" in requirement_id.lower():
        if detected_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF CV files are supported. Please upload your CV as a PDF. Word documents (.doc, .docx) are not accepted."
            )
    
    safe_filename = sanitize_filename(file.filename)
    safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    
    storage_path = f"documents/{employee_id}/{safe_filename}"
    
    content_type = detected_type or file.content_type or "application/octet-stream"
    put_object(storage_path, contents, content_type)
    
    file_url = storage_path
    now = datetime.now(timezone.utc).isoformat()
    
    doc_id = str(uuid.uuid4())
    
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
        "source_type": "worker_portal_upload",
        "document_role": "evidence"
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
            employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1, "employee_code": 1, "applicant_reference": 1})
            emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() if employee else "Unknown"
            emp_code = (employee.get("employee_code") or employee.get("applicant_reference") or "N/A") if employee else "N/A"
            
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
            await db.employee_documents.update_one(
                {"id": doc_id},
                {"$set": {
                    "extraction_status": "extraction_pending",
                    "extraction_error": None,
                    "updated_at": now
                }}
            )
            extracted_trainings = await extract_training_from_certificate(contents, file.filename)
            
            if extracted_trainings:
                logger.info(f"AI extracted {len(extracted_trainings)} training(s) from worker upload")
                
                await db.employee_documents.update_one(
                    {"id": doc_id},
                    {"$set": {
                        "extraction_count": len(extracted_trainings),
                        "extracted_item_count": len(extracted_trainings),
                        "extraction_status": "extracted_with_matches",
                        "extraction_error": None,
                        "extraction_date": now,
                        "updated_at": now
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
                    existing_names.add(normalize_name(prop.get("raw_course_title")))
                    existing_names.add(normalize_name(prop.get("mapped_training_title")))
                
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
                            "raw_course_title": training_name,
                            "mapped_training_title": training_name,
                            "provider": training.get("provider"),
                            "completion_date": training.get("completion_date"),
                            "completed_at": training.get("completion_date"),
                            "expiry_date": training.get("expiry_date"),
                            "expires_at": training.get("expiry_date"),
                            "mapped_training_code": matched_code,
                            "is_mandatory": matched_code is not None,
                            "ai_extracted": True,
                            "extraction_confidence": training.get("confidence", "medium"),
                            "confidence": training.get("confidence", "medium"),
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

                    # Create preliminary training_records for mandatory items so the
                    # evaluator returns "awaiting_review" instead of "missing".
                    # The admin review flow (review_proposed_items) already handles
                    # updating existing records, so no duplicate issue.
                    preliminary_records = []
                    for p_item in proposed_items:
                        if p_item.get("mapped_training_code"):
                            preliminary_records.append({
                                "id": str(uuid.uuid4()),
                                "employee_id": employee_id,
                                "training_name": p_item["training_name"],
                                "requirement_id": p_item["mapped_training_code"],
                                "mandatory": True,
                                "completion_date": p_item.get("completion_date"),
                                "expiry_date": p_item.get("expiry_date"),
                                "status": "completed",
                                "certificate_url": file_url,
                                "original_filename": file.filename,
                                "verified": False,
                                "completion_method": "certificate",
                                "record_status": "active",
                                "source_document_id": doc_id,
                                "intake_item_id": p_item["id"],
                                "ai_extracted": True,
                                "uploaded_by_worker": True,
                                "created_at": now,
                                "updated_at": now,
                            })
                    if preliminary_records:
                        await db.training_records.insert_many(preliminary_records)
                        logger.info(f"Created {len(preliminary_records)} preliminary training_records for mandatory items (awaiting verification)")
                
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
            else:
                await db.employee_documents.update_one(
                    {"id": doc_id},
                    {"$set": {
                        "extraction_count": 0,
                        "extracted_item_count": 0,
                        "extraction_status": "extracted_no_match",
                        "extraction_error": None,
                        "extraction_date": now,
                        "updated_at": now
                    }}
                )
        except Exception as e:
            logger.warning(f"AI training extraction failed for worker upload: {e}")
            await db.employee_documents.update_one(
                {"id": doc_id},
                {"$set": {
                    "extraction_count": 0,
                    "extracted_item_count": 0,
                    "extraction_status": "extraction_failed",
                    "extraction_error": str(e),
                    "updated_at": now
                }}
            )
    
    # CV uploads
    if requirement_id in ["cv", "resume", "curriculum_vitae"] or "cv" in requirement_id.lower():
        await db.employee_documents.update_many(
            {
                "employee_id": employee_id,
                "id": {"$ne": doc_id},
                "requirement_id": {"$in": ["cv", "resume", "curriculum_vitae"]},
                "status": {"$nin": ["superseded", "archived", "deleted"]}
            },
            {"$set": {
                "status": "superseded",
                "is_active": False,
                "superseded_at": now,
                "updated_at": now
            }}
        )
        await db.employee_documents.update_one(
            {"id": doc_id},
            {"$set": {
                "extraction_status": "pending_admin_review",
                "document_subtype": "cv",
                "requires_admin_extraction": True
            }}
        )
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "cv_document_id": doc_id,
                "cv_status": "uploaded",
                "updated_at": now
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
    
    frontend_url = os.environ.get("FRONTEND_URL", "https://app.osabeacares.co.uk")
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
    
    # Look up employee role for role-aware form filtering
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "role": 1, "job_title": 1})
    if not employee:
        employee = await db.applications.find_one({"id": employee_id}, {"_id": 0, "role": 1, "job_title": 1})
    employee_role = (employee.get("role") or employee.get("job_title") or "").lower() if employee else ""
    
    forms = []
    for form_id, form_def in WORKER_FORM_DEFINITIONS.items():
        # Skip forms restricted to specific roles if worker doesn't match
        roles_required = form_def.get("roles_required")
        if roles_required:
            if not any(r.lower() in employee_role for r in roles_required):
                continue
        
        progress = await db.form_progress.find_one({
            "employee_id": employee_id,
            "form_id": form_id
        }, {"_id": 0})
        
        submission = await db.form_submissions.find_one({
            "employee_id": employee_id,
            "form_type": form_id,
            "status": {"$in": ["submitted", "verified", "rejected", "amendment_requested"]}
        }, {"_id": 0})
        
        status = "not_started"
        saved_at = None
        submitted_at = None
        progress_percentage = 0
        
        if submission:
            status = submission.get("status", "submitted")
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
    
    employee_id = worker.get("employee_id")
    
    if form_id not in WORKER_FORM_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Block access to role-restricted forms if worker doesn't match
    form_def_meta = WORKER_FORM_DEFINITIONS[form_id]
    roles_required = form_def_meta.get("roles_required")
    if roles_required:
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "role": 1, "job_title": 1})
        if not employee:
            employee = await db.applications.find_one({"id": employee_id}, {"_id": 0, "role": 1, "job_title": 1})
        employee_role = (employee.get("role") or employee.get("job_title") or "").lower() if employee else ""
        if not any(r.lower() in employee_role for r in roles_required):
            raise HTTPException(status_code=403, detail="This form is not required for your role")
    
    # Special handling for pre-interview questionnaire
    if form_id == "pre_interview_questionnaire":
        return await get_pre_interview_questionnaire_data(employee_id, worker)
    
    # Resolve form definition early so it's available for all return paths
    form_def_with_sections = FORM_BASED_REQUIREMENTS.get(form_id)
    form_definition = form_def_with_sections or WORKER_FORM_DEFINITIONS[form_id]
    
    submission = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "form_type": form_id
    }, {"_id": 0})
    
    if submission and submission.get("status") in ["submitted", "verified"]:
        return {
            "form_id": form_id,
            "form_definition": form_definition,
            "status": submission.get("status"),
            "data": submission.get("form_data", {}),
            "submitted_at": submission.get("submitted_at"),
            "can_edit": False
        }

    if submission and submission.get("status") in ["rejected", "amendment_requested"]:
        return {
            "form_id": form_id,
            "form_definition": form_definition,
            "status": submission.get("status"),
            "data": submission.get("form_data", {}),
            "submitted_at": submission.get("submitted_at"),
            "can_edit": True
        }
    
    progress = await db.form_progress.find_one({
        "employee_id": employee_id,
        "form_id": form_id
    }, {"_id": 0})
    
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
            # Health data from application form (safe auto-fill fields)
            "flu_vaccination_date": employee.get("flu_vaccination_date"),
            "influenza_vaccine_status": employee.get("influenza_vaccine_status"),
            # health_issues_disability from application → maps to medical_problems_affecting_work in staff_health_questionnaire
            "health_issues_disability": employee.get("health_issues_disability"),
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
    
    # Block submission of role-restricted forms if worker doesn't match
    form_def_meta = WORKER_FORM_DEFINITIONS[form_id]
    roles_required = form_def_meta.get("roles_required")
    if roles_required:
        emp = await db.employees.find_one({"id": employee_id}, {"_id": 0, "role": 1, "job_title": 1})
        if not emp:
            emp = await db.applications.find_one({"id": employee_id}, {"_id": 0, "role": 1, "job_title": 1})
        emp_role = (emp.get("role") or emp.get("job_title") or "").lower() if emp else ""
        if not any(r.lower() in emp_role for r in roles_required):
            raise HTTPException(status_code=403, detail="This form is not required for your role")
    
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
            employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1, "employee_code": 1, "applicant_reference": 1})
            emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() if employee else employee_name
            emp_code = (employee.get("employee_code") or employee.get("applicant_reference") or "N/A") if employee else "N/A"
            
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
                        <a href="{os.environ.get('FRONTEND_URL', 'https://app.osabeacares.co.uk')}/portal/employees/{employee_id}?tab=compliance" style="background: #2563EB; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
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


    # ==================== WORKER REPLACEMENT REFEREE ====================
    class ProvideNewRefereeRequest(BaseModel):
        name: str
        email: str
        phone: Optional[str] = None
        organisation: Optional[str] = None
        position: Optional[str] = None
        relationship: Optional[str] = None


    @router.post("/worker/references/{ref_num}/provide-new")
    async def worker_provide_new_referee(
        ref_num: int,
        request: ProvideNewRefereeRequest,
        worker: dict = Depends(get_current_worker)
    ):
        """
        Worker submits replacement referee details after their reference was rejected
        or they are providing their first declaration.

        Only allowed when:
        - reference_N_request_status == 'rejected' (data was cleared, can_provide_new=True)
        - reference_N_name is None (never declared, not_declared)
        """
        db = get_db()
        if ref_num not in [1, 2]:
            raise HTTPException(status_code=400, detail="ref_num must be 1 or 2")

        emp = await db.employees.find_one({"id": worker["employee_id"]}, {"_id": 0})
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")

        prefix = f"reference_{ref_num}_"
        current_status = emp.get(f"{prefix}request_status")
        current_name = emp.get(f"{prefix}name")

        # Gate: only allowed when worker can provide new details
        data_cleared = (current_status == "rejected" and not current_name)
        not_declared = (current_name is None and current_status not in ["verified", "requested", "awaiting_response", "submitted", "awaiting_review"])
        if not (data_cleared or not_declared):
            raise HTTPException(
                status_code=400,
                detail=f"Reference {ref_num} does not require new referee details at this time."
            )

        now = datetime.now(timezone.utc).isoformat()
        employee_id = worker["employee_id"]

        # 1. Write to db.employees flat fields and reset status
        emp_update = {
            f"{prefix}name": request.name,
            f"{prefix}email": request.email,
            f"{prefix}phone": request.phone,
            f"{prefix}company": request.organisation,
            f"{prefix}job_title": request.position,
            f"{prefix}relationship": request.relationship,
            f"{prefix}declared": True,
            f"{prefix}request_status": None,   # cleared — admin must re-send request
            f"{prefix}request_token": None,
            f"{prefix}request_sent_at": None,
            f"{prefix}request_viewed_at": None,
            f"{prefix}resend_count": 0,
            f"{prefix}last_reminder_at": None,
            f"{prefix}response_data": None,
            f"{prefix}response_received_at": None,
            f"{prefix}mismatch_detected": False,
            f"{prefix}mismatch_notes": None,
            f"{prefix}reviewed": False,
            f"{prefix}reviewed_by": None,
            f"{prefix}reviewed_at": None,
            f"{prefix}verified": False,
            f"{prefix}verified_by": None,
            f"{prefix}verified_at": None,
            f"{prefix}rejected": False,
            f"{prefix}rejected_by": None,
            f"{prefix}rejected_at": None,
            f"{prefix}rejection_reason": None,
            f"{prefix}replacement_requested_at": None,
            f"{prefix}replacement_requested_by": None,
            f"{prefix}replacement_reason": None,
            "updated_at": now,
        }
        await db.employees.update_one({"id": employee_id}, {"$set": emp_update})

        # 2. Write to db.references nested doc (upsert)
        ref_nested = {
            f"ref{ref_num}.declared.name": request.name,
            f"ref{ref_num}.declared.email": request.email,
            f"ref{ref_num}.declared.phone": request.phone,
            f"ref{ref_num}.declared.organisation": request.organisation,
            f"ref{ref_num}.declared.position": request.position,
            f"ref{ref_num}.declared.relationship": request.relationship,
            f"ref{ref_num}.verification_status": "declared",
            "updated_at": now,
        }
        await db.references.update_one(
            {"employee_id": employee_id},
            {"$set": ref_nested},
            upsert=True
        )

        # 3. Write to db.employee_references (upsert by employee_id + reference_number)
        existing_ref_doc = await db.employee_references.find_one(
            {"employee_id": employee_id, "reference_number": ref_num}
        )
        ref_collection_update = {
            "employee_id": employee_id,
            "reference_number": ref_num,
            "referee_name": request.name,
            "referee_email": request.email,
            "referee_phone": request.phone,
            "referee_organisation": request.organisation,
            "referee_position": request.position,
            "referee_relationship": request.relationship,
            "status": "declared",
            "request_status": None,
            "updated_at": now,
            "source": "worker_provided",
        }
        if existing_ref_doc:
            await db.employee_references.update_one(
                {"employee_id": employee_id, "reference_number": ref_num},
                {"$set": ref_collection_update}
            )
        else:
            ref_collection_update["id"] = str(uuid.uuid4())
            ref_collection_update["created_at"] = now
            await db.employee_references.insert_one(ref_collection_update)

        await log_audit_action(
            worker["employee_id"],
            "worker_provided_new_referee",
            "employee",
            employee_id,
            {
                "reference_number": ref_num,
                "referee_name": request.name,
                "referee_email": request.email,
            }
        )

        return {
            "success": True,
            "message": f"Reference {ref_num} details submitted. Your manager will send the reference request shortly.",
            "reference_number": ref_num,
        }


# ==================== WORKER EMPLOYMENT GAP CLARIFICATION ====================

GAP_REASON_TYPES = [
    "education",
    "caring_responsibilities",
    "illness",
    "travel",
    "career_break",
    "redundancy",
    "unemployment",
    "maternity_paternity",
    "voluntary_work",
    "other",
]


class WorkerGapExplanation(BaseModel):
    explanation: str
    reason_type: Optional[str] = None


@router.get("/worker/employment-gaps")
async def get_worker_employment_gaps(worker: dict = Depends(get_current_worker)):
    """Get the current worker's employment gaps and 10-year coverage for self-service clarification."""
    db = get_db()
    employee_id = worker.get("employee_id")

    gap_records = await db.employment_gaps.find(
        {"employee_id": employee_id}
    ).sort("gap_start", 1).to_list(50)

    for gap in gap_records:
        gap.pop("_id", None)

    # Fallback to inline employee.employment_gaps if no collection records
    if not gap_records:
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "employment_gaps": 1, "employment_history": 1, "employment_coverage": 1})
        gap_records = employee.get("employment_gaps", []) if employee else []
    else:
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "employment_history": 1, "employment_coverage": 1})

    from employment_gap_engine import evaluate_gaps_compliance, compute_coverage_summary
    evaluation = evaluate_gaps_compliance(gap_records)

    # Compute 10-year coverage summary
    employment_history = (employee or {}).get("employment_history", [])
    # Use stored coverage if available, otherwise compute fresh
    coverage = (employee or {}).get("employment_coverage")
    if not coverage:
        coverage = compute_coverage_summary(employment_history)

    # Lazily assign stable IDs to any legacy entries without one
    if _ensure_entry_ids(employment_history):
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {"employment_history": employment_history}},
        )

    # Sort consistently: current first, then newest-to-oldest
    sorted_entries = _sort_employment_entries(employment_history)

    # Build employment entries for the worker — worker-editable fields only
    # Excludes admin-only fields: verification_status, verified_by, verified_at, reference_id
    entries_summary = []
    for entry in sorted_entries:
        entries_summary.append({
            "id": entry.get("id"),
            "employer_name": entry.get("employer_name", "Unknown"),
            "job_title": entry.get("job_title", entry.get("position", "")),
            "start_date": entry.get("start_date"),
            "end_date": entry.get("end_date"),
            "is_current": not bool(entry.get("end_date")),
            "duties": entry.get("duties", ""),
            "reason_for_leaving": entry.get("reason_for_leaving", ""),
            "employer_address": entry.get("employer_address", ""),
            "employer_phone": entry.get("employer_phone", ""),
            "can_contact": entry.get("can_contact", True),
        })

    return {
        "gaps": gap_records,
        "has_gaps": evaluation.get("has_gaps", False),
        "total_gaps": evaluation.get("total_gaps", 0),
        "all_explained": evaluation.get("is_complete", False),
        "reason_types": GAP_REASON_TYPES,
        "coverage": coverage,
        "employment_entries": entries_summary,
    }


@router.post("/worker/employment-gaps/{gap_id}/explain")
async def worker_explain_gap(
    gap_id: str,
    request: WorkerGapExplanation,
    worker: dict = Depends(get_current_worker),
):
    """Worker provides an explanation for a specific employment gap.
    Writes directly to the canonical db.employment_gaps collection."""
    db = get_db()
    employee_id = worker.get("employee_id")

    gap = await db.employment_gaps.find_one(
        {"employee_id": employee_id, "$or": [{"id": gap_id}, {"gap_id": gap_id}]},
    )
    if not gap:
        raise HTTPException(status_code=404, detail="Gap not found")

    gap.pop("_id", None)
    record_id = gap.get("id") or gap.get("gap_id")

    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "explanation": request.explanation.strip(),
        "reason_type": request.reason_type,
        "status": "explained",
        "verification_status": "explained",
        "verified": False,
        "requires_further_info": False,
        "explained_at": now,
        "explained_by": f"worker_{employee_id}",
        "explanation_submitted_by_role": "worker",
        "explanation_submitted_by_name": worker.get("name", ""),
        "explanation_source": "worker_gap_clarification",
        "status_updated_at": now,
        "updated_at": now,
    }

    await db.employment_gaps.update_one(
        {"employee_id": employee_id, "id": record_id},
        {"$set": update_data},
    )

    # Invalidate employment review sign-off if it was already done
    await db.employees.update_one(
        {"id": employee_id, "employment_review_signed_off": True},
        {"$unset": {
            "employment_review_signed_off": "",
            "employment_review_signed_off_by": "",
            "employment_review_signed_off_at": "",
        }},
    )

    await log_audit_action(
        f"worker_{employee_id}",
        "employment_gap_explained",
        "employment_gap",
        record_id,
        {"reason_type": request.reason_type, "source": "worker_dashboard"},
    )

    return {"success": True, "message": "Gap explanation submitted"}


# =============================================================================
# WORKER EMPLOYMENT HISTORY AMENDMENT
# =============================================================================


def _ensure_entry_ids(employment_history: list) -> bool:
    """Ensure every entry has a stable `id`. Returns True if any were assigned."""
    changed = False
    for entry in employment_history:
        if not entry.get("id"):
            entry["id"] = str(uuid.uuid4())
            changed = True
    return changed


def _sort_employment_entries(employment_history: list) -> list:
    """Sort: current role first, then newest-to-oldest by start_date."""
    def sort_key(e):
        is_current = 0 if (not e.get("end_date") or e.get("is_current")) else 1
        start = e.get("start_date") or "0000-00"
        end = e.get("end_date") or "9999-99"
        return (is_current, start, end)  # ascending → reversed below
    # Current first (is_current=0 < 1); among non-current, newest first
    return sorted(employment_history, key=sort_key, reverse=True)


class WorkerEmploymentEntry(BaseModel):
    employer_name: str
    job_title: str
    start_date: str  # YYYY-MM or YYYY-MM-DD
    end_date: Optional[str] = None
    is_current: bool = False
    duties: Optional[str] = None
    reason_for_leaving: Optional[str] = None
    employer_address: Optional[str] = None
    employer_phone: Optional[str] = None
    can_contact: bool = True


class WorkerEmploymentAmendment(BaseModel):
    """Payload for adding or updating a single employment entry."""
    entry: WorkerEmploymentEntry
    entry_id: Optional[str] = None  # None = add new, str = update existing by stable id


async def _reconcile_employment_after_amendment(employee_id: str, employment_history: list, actor_id: str):
    """
    After employment_history changes:
    1. Re-detect gaps with coverage awareness
    2. Re-compute coverage summary
    3. Reconcile db.employment_gaps — preserve explained/verified where dates still match
    4. Invalidate employment review sign-off
    5. Update employee record
    """
    db = get_db()
    from employment_gap_engine import (
        detect_employment_gaps_with_coverage,
        compute_coverage_summary,
        create_gap_record,
    )

    now = datetime.now(timezone.utc).isoformat()

    # 1-2. Detect new gaps and compute coverage
    new_gaps = detect_employment_gaps_with_coverage(employment_history)
    coverage = compute_coverage_summary(employment_history)

    # 3. Reconcile: load existing gap records, match by date range, preserve status
    existing_gap_records = await db.employment_gaps.find(
        {"employee_id": employee_id}
    ).to_list(100)
    existing_by_range = {}
    for eg in existing_gap_records:
        eg.pop("_id", None)
        key = (eg.get("gap_start"), eg.get("gap_end"))
        existing_by_range[key] = eg

    # Build set of new gap date-range keys
    new_gap_keys = set()
    for ng in new_gaps:
        key = (ng.get("gap_start"), ng.get("gap_end"))
        new_gap_keys.add(key)

    # Upsert new/matched gaps
    for ng in new_gaps:
        key = (ng.get("gap_start"), ng.get("gap_end"))
        existing = existing_by_range.get(key)
        if existing:
            # Gap still exists — preserve worker-provided data
            preserved_fields = {
                "explanation", "reason_type", "explanation_provided_at",
                "explained_at", "explained_by", "explanation_submitted_by_role",
                "explanation_submitted_by_name", "explanation_source",
                "evidence_document_id",
            }
            # Preserve status only if explained or verified (not stale pending)
            existing_status = (existing.get("status") or "pending").lower()
            if existing_status in ("explained", "verified", "needs_more_info"):
                preserved_fields.add("status")
                preserved_fields.add("verification_status")
                preserved_fields.add("verified")
                preserved_fields.add("verified_by")
                preserved_fields.add("verified_at")
                preserved_fields.add("admin_notes")
                preserved_fields.add("verification_notes")

            gap_record = create_gap_record(employee_id, ng, created_by=f"worker_{employee_id}")
            for field in preserved_fields:
                if existing.get(field) is not None:
                    gap_record[field] = existing[field]
            gap_record["updated_at"] = now

            await db.employment_gaps.update_one(
                {"id": gap_record["id"]},
                {"$set": gap_record},
                upsert=True,
            )
        else:
            # Brand new gap
            gap_record = create_gap_record(employee_id, ng, created_by=f"worker_{employee_id}")
            await db.employment_gaps.update_one(
                {"id": gap_record["id"]},
                {"$set": gap_record},
                upsert=True,
            )

    # Remove gap records that no longer exist
    for key, eg in existing_by_range.items():
        if key not in new_gap_keys:
            await db.employment_gaps.delete_one({"id": eg["id"]})

    # Ensure all entries have stable IDs before saving
    _ensure_entry_ids(employment_history)

    # Sort consistently before persisting
    employment_history[:] = _sort_employment_entries(employment_history)

    # 4-5. Update employee record + invalidate sign-off
    update_set = {
        "employment_history": employment_history,
        "employment_coverage": coverage,
        "employment_gaps": new_gaps,
        "employment_gaps_detected_at": now,
        "has_employment_gaps": len(new_gaps) > 0,
        "employment_history_amended_at": now,
        "employment_history_amended_by": actor_id,
    }
    update_unset = {
        "employment_review_signed_off": "",
        "employment_review_signed_off_by": "",
        "employment_review_signed_off_by_name": "",
        "employment_review_signed_off_at": "",
        "employment_review_notes": "",
    }
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": update_set, "$unset": update_unset},
    )

    return new_gaps, coverage


@router.post("/worker/employment-history/amend")
async def worker_amend_employment_history(
    request: WorkerEmploymentAmendment,
    worker: dict = Depends(get_current_worker),
):
    """
    Worker adds or updates a single employment history entry.
    After save: re-detects gaps, recomputes coverage, reconciles gap records,
    and invalidates any existing employment review sign-off.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to account")

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employment_history = list(employee.get("employment_history", []))

    # Ensure all existing entries have stable IDs (lazy migration)
    _ensure_entry_ids(employment_history)

    entry_data = request.entry.model_dump()
    now = datetime.now(timezone.utc).isoformat()

    # Validate: employer_name and start_date are required
    if not entry_data.get("employer_name", "").strip():
        raise HTTPException(status_code=422, detail="Employer name is required")
    if not entry_data.get("start_date", "").strip():
        raise HTTPException(status_code=422, detail="Start date is required")

    # Validate: end_date required unless is_current
    if not entry_data.get("is_current") and not entry_data.get("end_date"):
        raise HTTPException(status_code=422, detail="End date is required unless this is your current role")

    # Validate: start_date < end_date
    if entry_data.get("end_date"):
        if entry_data["start_date"] > entry_data["end_date"]:
            raise HTTPException(status_code=422, detail="Start date must be before end date")

    # If is_current, clear end_date
    if entry_data.get("is_current"):
        entry_data["end_date"] = None

    # Amendment metadata
    entry_data["amended_at"] = now
    entry_data["amended_by"] = f"worker_{employee_id}"
    entry_data["amendment_source"] = "worker_dashboard"

    if request.entry_id is not None:
        # Update existing entry by stable ID
        idx = next((i for i, e in enumerate(employment_history) if e.get("id") == request.entry_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Employment entry not found")
        # Preserve any admin-only fields from the original entry
        original = employment_history[idx]
        for admin_field in ("verification_status", "verified_by", "verified_at", "reference_id", "id"):
            if admin_field in original:
                entry_data[admin_field] = original[admin_field]
        employment_history[idx] = entry_data
        action = "employment_entry_updated"
    else:
        # Add new entry with a fresh stable ID
        entry_data["id"] = str(uuid.uuid4())
        employment_history.append(entry_data)
        action = "employment_entry_added"

    actor_id = f"worker_{employee_id}"

    # Reconcile gaps, coverage, sign-off
    new_gaps, coverage = await _reconcile_employment_after_amendment(
        employee_id, employment_history, actor_id
    )

    # Audit log
    await log_audit_action(
        actor_id,
        action,
        "employee",
        employee_id,
        {
            "entry_id": entry_data.get("id"),
            "employer_name": entry_data["employer_name"],
            "start_date": entry_data["start_date"],
            "end_date": entry_data.get("end_date"),
            "source": "worker_dashboard_amendment",
            "gaps_after": len(new_gaps),
            "coverage_percent": coverage.get("coverage_percent", 0),
        },
    )

    # Admin awareness: create notification so admin knows re-review is needed
    try:
        employee_rec = await db.employees.find_one(
            {"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1}
        )
        emp_name = f"{employee_rec.get('first_name', '')} {employee_rec.get('last_name', '')}".strip() if employee_rec else employee_id
        await db.worker_notifications.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "type": "employment_history_amended",
            "title": "Employment History Amended",
            "message": f"{emp_name} amended employment history ({action.replace('_', ' ')}); coverage/gaps re-detected. Employment review requires re-review.",
            "data": {
                "entry_id": entry_data.get("id"),
                "action": action,
                "employer_name": entry_data["employer_name"],
                "gaps_after": len(new_gaps),
                "coverage_percent": coverage.get("coverage_percent", 0),
            },
            "created_at": now,
            "read": False,
            "target_audience": "admin",
        })
    except Exception as e:
        logger.warning(f"Failed to create admin notification for employment amendment: {e}")

    return {
        "success": True,
        "message": "Employment entry saved. Gaps and coverage have been recalculated.",
        "entry_id": entry_data.get("id"),
        "gaps_count": len(new_gaps),
        "coverage": coverage,
    }


@router.delete("/worker/employment-history/{entry_id}")
async def worker_delete_employment_entry(
    entry_id: str,
    worker: dict = Depends(get_current_worker),
):
    """
    Worker removes an employment history entry by stable ID.
    Re-detects gaps, recomputes coverage, and invalidates sign-off.
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to account")

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employment_history = list(employee.get("employment_history", []))

    # Ensure stable IDs on legacy entries
    _ensure_entry_ids(employment_history)

    idx = next((i for i, e in enumerate(employment_history) if e.get("id") == entry_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Employment entry not found")

    removed_entry = employment_history.pop(idx)
    actor_id = f"worker_{employee_id}"

    new_gaps, coverage = await _reconcile_employment_after_amendment(
        employee_id, employment_history, actor_id
    )

    await log_audit_action(
        actor_id,
        "employment_entry_removed",
        "employee",
        employee_id,
        {
            "entry_id": entry_id,
            "employer_name": removed_entry.get("employer_name"),
            "source": "worker_dashboard_amendment",
            "gaps_after": len(new_gaps),
        },
    )

    # Admin awareness
    try:
        employee_rec = await db.employees.find_one(
            {"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1}
        )
        emp_name = f"{employee_rec.get('first_name', '')} {employee_rec.get('last_name', '')}".strip() if employee_rec else employee_id
        now = datetime.now(timezone.utc).isoformat()
        await db.worker_notifications.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "type": "employment_history_amended",
            "title": "Employment Entry Removed",
            "message": f"{emp_name} removed an employment entry ({removed_entry.get('employer_name', 'Unknown')}); coverage/gaps re-detected. Employment review requires re-review.",
            "data": {
                "entry_id": entry_id,
                "action": "employment_entry_removed",
                "employer_name": removed_entry.get("employer_name"),
                "gaps_after": len(new_gaps),
                "coverage_percent": coverage.get("coverage_percent", 0),
            },
            "created_at": now,
            "read": False,
            "target_audience": "admin",
        })
    except Exception as e:
        logger.warning(f"Failed to create admin notification for employment deletion: {e}")

    return {
        "success": True,
        "message": "Employment entry removed. Gaps and coverage recalculated.",
        "gaps_count": len(new_gaps),
        "coverage": coverage,
    }
