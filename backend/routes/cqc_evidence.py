"""
CQC Evidence Mapping Routes - Read-only mapping layer for CQC inspection readiness.

This module handles:
- Mapping existing system evidence to CQC 5 Key Questions
- Does NOT change any compliance calculations or employee readiness
- Visibility layer only for CQC inspection preparation
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends

from .dependencies import get_db, get_current_user

router = APIRouter(tags=["CQC Evidence"])


# CQC Evidence Mapping - maps system data to CQC 5 Key Questions
CQC_EVIDENCE_MAPPING = {
    "safe": {
        "title": "Safe",
        "description": "People are protected from abuse and avoidable harm",
        "items": [
            # Policies
            {"name": "Safeguarding Adults Policy", "source_type": "policy", "source_id": "Safeguarding Adults Policy"},
            {"name": "Safeguarding Children Policy", "source_type": "policy", "source_id": "Safeguarding Children Policy"},
            {"name": "Health & Safety Policy", "source_type": "policy", "source_id": "Health & Safety Policy"},
            {"name": "Fire Safety Policy", "source_type": "policy", "source_id": "Fire Safety Policy"},
            {"name": "Infection Prevention & Control Policy", "source_type": "policy", "source_id": "Infection Prevention & Control Policy"},
            {"name": "Medication Policy", "source_type": "policy", "source_id": "Medication Policy"},
            {"name": "Lone Working Policy", "source_type": "policy", "source_id": "Lone Working Policy"},
            {"name": "Risk Assessment Policy", "source_type": "policy", "source_id": "Risk Assessment Policy"},
            {"name": "Manual Handling Policy", "source_type": "policy", "source_id": "Manual Handling Policy"},
            {"name": "COSHH Policy", "source_type": "policy", "source_id": "COSHH Policy"},
            {"name": "First Aid Policy", "source_type": "policy", "source_id": "First Aid Policy"},
            # Registers & Summaries
            {"name": "DBS Register", "source_type": "register", "source_id": "dbs_register"},
            {"name": "Right to Work Summary", "source_type": "register", "source_id": "rtw_register"},
            # Certificates
            {"name": "Fire Safety Certificate", "source_type": "certificate", "source_id": "fire_safety"},
            {"name": "Gas Safety Certificate", "source_type": "certificate", "source_id": "gas_safety"},
            {"name": "PAT Testing Certificate", "source_type": "certificate", "source_id": "pat_testing"},
            {"name": "Electrical Inspection (EICR)", "source_type": "certificate", "source_id": "electrical_inspection"},
            # Forms
            {"name": "Health Screening Forms", "source_type": "form", "source_id": "health_screening"},
            # Reports/Logs
            {"name": "Incident Logs", "source_type": "report", "source_id": "incidents"},
        ]
    },
    "effective": {
        "title": "Effective",
        "description": "Care, treatment and support achieves good outcomes",
        "items": [
            # Policies
            {"name": "Training & Development Policy", "source_type": "policy", "source_id": "Training & Development Policy"},
            {"name": "Supervision Policy", "source_type": "policy", "source_id": "Supervision Policy"},
            {"name": "Recruitment & Selection Policy", "source_type": "policy", "source_id": "Recruitment & Selection Policy"},
            {"name": "Induction Policy", "source_type": "policy", "source_id": "Induction Policy"},
            # Registers
            {"name": "Training Matrix", "source_type": "register", "source_id": "training_matrix"},
            # Forms
            {"name": "Induction Checklists", "source_type": "form", "source_id": "induction"},
            {"name": "Interview Records", "source_type": "form", "source_id": "interview_record"},
        ]
    },
    "caring": {
        "title": "Caring",
        "description": "Staff treat people with compassion, kindness, dignity and respect",
        "items": [
            # Policies
            {"name": "Dignity & Respect Policy", "source_type": "policy", "source_id": "Dignity & Respect Policy"},
            {"name": "Equality & Diversity Policy", "source_type": "policy", "source_id": "Equality & Diversity Policy"},
            {"name": "Confidentiality Policy", "source_type": "policy", "source_id": "Confidentiality Policy"},
            # Forms
            {"name": "Equal Opportunities Forms", "source_type": "form", "source_id": "equal_opportunities"},
            # Service User Feedback
            {"name": "Service User Feedback", "source_type": "report", "source_id": "service_user_feedback"},
        ]
    },
    "responsive": {
        "title": "Responsive",
        "description": "Services meet people's needs",
        "items": [
            # Policies
            {"name": "Complaints Policy", "source_type": "policy", "source_id": "Complaints Policy"},
            {"name": "Whistleblowing Policy", "source_type": "policy", "source_id": "Whistleblowing Policy"},
            # Registers
            {"name": "Complaints Register", "source_type": "report", "source_id": "complaints"},
            # Reports
            {"name": "Service User Feedback Trends", "source_type": "report", "source_id": "feedback_trends"},
        ]
    },
    "well_led": {
        "title": "Well-led",
        "description": "Leadership, management and governance assure high-quality care",
        "items": [
            # Policies
            {"name": "Governance Policy", "source_type": "policy", "source_id": "Governance Policy"},
            {"name": "Quality Assurance Policy", "source_type": "policy", "source_id": "Quality Assurance Policy"},
            {"name": "Business Continuity Policy", "source_type": "policy", "source_id": "Business Continuity Policy"},
            {"name": "Data Protection (GDPR) Policy", "source_type": "policy", "source_id": "Data Protection Policy"},
            # Certificates
            {"name": "Public Liability Insurance", "source_type": "certificate", "source_id": "public_liability_insurance"},
            {"name": "Employers Liability Insurance", "source_type": "certificate", "source_id": "employers_liability_insurance"},
            {"name": "Professional Indemnity Insurance", "source_type": "certificate", "source_id": "professional_indemnity_insurance", "conditional": True},
            # Reports
            {"name": "Audit Logs", "source_type": "report", "source_id": "audit_logs"},
        ]
    }
}


@router.get("/compliance/cqc-evidence-map")
async def get_cqc_evidence_map(user: dict = Depends(get_current_user)):
    """
    CQC Evidence Mapping - Read-only view of existing evidence mapped to CQC 5 Key Questions.
    
    This is a VISIBILITY LAYER ONLY:
    - Does NOT change employee compliance calculations
    - Does NOT change progress %
    - Does NOT change Ready to Work status
    - Does NOT create a second compliance engine
    
    Maps existing system data (policies, certificates, forms, registers, reports) to:
    - Safe
    - Effective
    - Caring
    - Responsive
    - Well-led
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    
    # Fetch all source data
    policies = await db.org_policies.find({}, {"_id": 0}).to_list(200)
    policies_map = {p["name"]: p for p in policies}
    
    certificates = await db.insurance_docs.find({}, {"_id": 0}).to_list(100)
    certs_map = {c["insurance_type"]: c for c in certificates}
    
    # Get form submission counts
    form_counts = {}
    for form_type in ["health_screening", "induction", "recruitment_checklist", "interview_record", "equal_opportunities"]:
        count = await db.form_submissions.count_documents({"form_type": form_type})
        form_counts[form_type] = count
    
    # Get report/log counts
    report_counts = {
        "incidents": await db.incident_logs.count_documents({}) if await db.list_collection_names() and "incident_logs" in await db.list_collection_names() else 0,
        "complaints": await db.complaints.count_documents({}),
        "service_user_feedback": await db.service_user_feedback.count_documents({}),
        "audit_logs": await db.audit_logs.count_documents({})
    }
    
    # Get staff statistics for registers
    total_staff = await db.employees.count_documents({"status": {"$in": ["active", "onboarding"]}})
    
    # DBS register stats
    dbs_valid = await db.dbs_checks.count_documents({
        "is_current": True,
        "outcome": {"$in": ["clear", "verified", "information_reviewed"]}
    })
    dbs_missing = total_staff - dbs_valid
    
    # RTW stats
    rtw_approved = await db.employee_documents.count_documents({
        "requirement_id": "right_to_work",
        "verified": True,
        "status": {"$nin": ["superseded", "expired"]}
    })
    
    # Training count
    training_count = await db.training_records.count_documents({
        "verified": True,
        "record_status": {"$nin": ["superseded", "deleted"]}
    })
    
    def get_item_status(item):
        """Determine status and details for each evidence item"""
        source_type = item["source_type"]
        source_id = item["source_id"]
        name = item["name"]
        
        status = "missing"
        details = None
        link = None
        expiry_date = None
        
        if source_type == "policy":
            policy = policies_map.get(source_id)
            if policy:
                if policy.get("status") == "active":
                    # Check review date
                    review_date_str = policy.get("review_date")
                    if review_date_str:
                        try:
                            if 'T' in str(review_date_str):
                                review_date = datetime.fromisoformat(review_date_str.replace('Z', '+00:00'))
                            else:
                                review_date = datetime.fromisoformat(f"{review_date_str}T00:00:00+00:00")
                            
                            if review_date < now:
                                status = "overdue"
                                details = f"Review overdue since {review_date.strftime('%d %b %Y')}"
                            elif review_date < now + thirty_days:
                                status = "due_review"
                                details = f"Review due {review_date.strftime('%d %b %Y')}"
                            else:
                                status = "present"
                                details = f"Last reviewed {policy.get('effective_date', 'N/A')}"
                        except (ValueError, TypeError):
                            status = "present"
                    else:
                        status = "present"
                else:
                    status = "missing"
                link = f"/portal/compliance-centre?tab=policies&policy={policy.get('id')}"
            else:
                status = "missing"
        
        elif source_type == "certificate":
            cert = certs_map.get(source_id)
            if cert:
                if cert.get("file_url"):
                    if cert.get("expiry_date"):
                        try:
                            exp_str = cert["expiry_date"]
                            if 'T' in str(exp_str):
                                exp_date = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                            else:
                                exp_date = datetime.fromisoformat(f"{exp_str}T00:00:00+00:00")
                            expiry_date = cert["expiry_date"]
                            if exp_date < now:
                                status = "expired"
                            elif exp_date < now + thirty_days:
                                status = "expiring"
                            else:
                                status = "present"
                        except (ValueError, TypeError):
                            status = "present"
                    else:
                        status = "present"
                    details = cert.get("provider")
                else:
                    status = "missing"
                link = f"/portal/compliance-centre?tab=certificates&cert={cert.get('id')}"
            elif item.get("conditional"):
                status = "n/a"
                details = "Conditional - may not apply"
            else:
                status = "missing"
        
        elif source_type == "form":
            count = form_counts.get(source_id, 0)
            if count > 0:
                status = "present"
                details = f"{count} submissions"
            else:
                status = "missing"
            link = "/portal/employees"
        
        elif source_type == "register":
            if source_id == "dbs_register":
                if dbs_valid > 0:
                    status = "present"
                    details = f"{dbs_valid}/{total_staff} staff with valid DBS"
                    if dbs_missing > 0:
                        status = "partial"
                else:
                    status = "missing"
                link = "/portal/compliance-centre?tab=staff"
            elif source_id == "rtw_register":
                if rtw_approved > 0:
                    status = "present"
                    details = f"{rtw_approved}/{total_staff} staff with RTW verified"
                else:
                    status = "missing"
                link = "/portal/employees"
            elif source_id == "training_matrix":
                if training_count > 0:
                    status = "present"
                    details = f"{training_count} training records"
                else:
                    status = "missing"
                link = "/portal/employees"
        
        elif source_type == "report":
            count = report_counts.get(source_id, 0)
            if count > 0:
                status = "present"
                details = f"{count} records"
            else:
                status = "n/a"
                details = "No records yet"
            link = f"/portal/compliance-centre?tab={source_id}"
        
        return {
            "name": name,
            "source_type": source_type,
            "source_id": source_id,
            "status": status,
            "details": details,
            "expiry_date": expiry_date,
            "link": link
        }
    
    # Build result
    result = {}
    summary = {
        "total_items": 0,
        "present": 0,
        "missing": 0,
        "due_review": 0,
        "expired": 0,
        "partial": 0,
        "n_a": 0
    }
    
    for key, category in CQC_EVIDENCE_MAPPING.items():
        items = []
        category_summary = {"present": 0, "missing": 0, "due_review": 0, "expired": 0, "partial": 0, "n_a": 0}
        
        for item in category["items"]:
            item_status = get_item_status(item)
            items.append(item_status)
            
            # Update counts
            status = item_status["status"]
            if status in category_summary:
                category_summary[status] += 1
            elif status == "expiring":
                category_summary["due_review"] += 1
            elif status == "overdue":
                category_summary["expired"] += 1
            
            summary["total_items"] += 1
            if status == "present":
                summary["present"] += 1
            elif status == "missing":
                summary["missing"] += 1
            elif status in ["due_review", "expiring"]:
                summary["due_review"] += 1
            elif status in ["expired", "overdue"]:
                summary["expired"] += 1
            elif status == "partial":
                summary["partial"] += 1
            elif status == "n/a":
                summary["n_a"] += 1
        
        result[key] = {
            "title": category["title"],
            "description": category["description"],
            "items": items,
            "summary": category_summary
        }
    
    return {
        "cqc_mapping": result,
        "summary": summary,
        "generated_at": now.isoformat(),
        "note": "This is a read-only evidence mapping view. It does NOT affect employee compliance calculations, progress %, or Ready to Work status."
    }
