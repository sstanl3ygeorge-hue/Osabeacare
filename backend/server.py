from fastapi import FastAPI, APIRouter, HTTPException, Depends, File, UploadFile, Query, Header, Response, Form
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import asyncio
import io
import zipfile
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import requests
import resend
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from templates_data import COMPLIANCE_TEMPLATES, EMAIL_TEMPLATES

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'care-recruitment-jwt-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

# Object Storage Config
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY')
APP_NAME = "osabea-care"
storage_key = None

# Resend Config
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# Initialize storage
def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    if not EMERGENT_KEY:
        logger.warning("EMERGENT_LLM_KEY not set, storage disabled")
        return None
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str) -> tuple:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

app = FastAPI(title="Osabea Healthcare Solutions API")
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    BRANCH_MANAGER = "branch_manager"  # Legacy - now manages assignments
    EMPLOYEE = "employee"
    AUDITOR = "auditor"

class EmployeeStatus:
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW = "interview"
    COMPLIANCE_REVIEW = "compliance_review"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class DocumentStatus:
    NOT_STARTED = "not_started"
    REQUESTED = "requested"
    UPLOADED = "uploaded"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    NOT_APPLICABLE = "not_applicable"

# Onboarding Status values
class OnboardingStatus:
    NEW = "New"
    DOCUMENTS_PENDING = "Documents Pending"
    UNDER_REVIEW = "Under Review"
    READY_FOR_PLACEMENT = "Ready for Placement"
    ACTIVE = "Active"
    ARCHIVED = "Archived"

# Mandatory Compliance Items by Role
# EVIDENCE-BASED COMPLIANCE MODEL (2026-03-27 Redesign)
# 
# Types:
#   - "document": Employee-submitted or internal evidence file(s)
#   - "form-generated": Internal form that becomes evidence document on completion
#   - "training": Training certificate evidence
#
# Source:
#   - "employee": Evidence submitted by employee (passport, DBS cert, references)
#   - "internal": Internal verification evidence (RTW check, DBS check)
#   - "form": Auto-generated from completed internal form
#
# Rules:
#   - allow_multiple_files: True = supports multiple evidence files
#   - min_files: Minimum files required for completion (default 1)
#   - Only evidence-backed completions count toward compliance score
#   - Verification requires at least one viewable file
#
# ============================================================================
# WORK READINESS REQUIREMENTS - CQC Standards
# ============================================================================
# Priority Levels:
#   - "mandatory": Required to start work (BLOCKS work readiness)
#   - "required_soon": Required within first weeks (does NOT block work)
#   - "secondary": For full compliance (does NOT block work)
# ============================================================================

# Items that BLOCK work readiness if not completed & verified
WORK_READY_REQUIREMENTS = {
    # LEGAL (MANDATORY) - Cannot start without these
    "right_to_work_documents",
    "right_to_work_check", 
    "identity_documents",
    
    # SAFETY (MANDATORY) - Cannot start without these
    "dbs_certificate",
    "dbs_check",
    
    # CORE TRAINING (MANDATORY) - Cannot start without these
    "safeguarding",
    "manual_handling",
    "infection_control",
    
    # NOTE: nmc_registration is added dynamically for Nurses via get_work_ready_items_for_role()
}

# Items required soon after starting (within first weeks)
REQUIRED_SOON = {
    "bls",
    "fire_safety",
    "health_safety",
    "reference_1",
    "reference_2",
    "health_screening",
}

MANDATORY_ITEMS = {
    "base": [  # Common to all roles - ordered by work readiness priority
        
        # ======== MANDATORY: LEGAL (Required to Start Work) ========
        {"id": "right_to_work_documents", "name": "Right to Work Documents", 
         "category": "1_Legal_Safety", "type": "document", "source": "employee",
         "document_types": ["visa", "brp", "share_code", "settled_status"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "mandatory", "priority_order": 1,
         "description": "Visa, BRP, share code evidence, settled status proof",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "right_to_work_check", "name": "Right to Work Verification", 
         "category": "1_Legal_Safety", "type": "document", "source": "internal",
         "document_types": ["rtw_check", "share_code_check"],
         "allow_multiple_files": True,
         "priority": "mandatory", "priority_order": 2,
         "description": "Internal RTW verification - share code check result",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "identity_documents", "name": "Identity Documents", 
         "category": "1_Legal_Safety", "type": "document", "source": "employee",
         "document_types": ["passport", "driving_licence", "national_id"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "mandatory", "priority_order": 3,
         "description": "Passport, driving licence, or other photo ID",
         "work_ready_hint": "Required before employee can start work"},
        
        # ======== MANDATORY: SAFETY (Required to Start Work) ========
        {"id": "dbs_certificate", "name": "DBS Certificate", "category": "1_Legal_Safety",
         "type": "document", "source": "employee",
         "document_types": ["dbs", "dbs_certificate"],
         "allow_multiple_files": True,
         "priority": "mandatory", "priority_order": 4,
         "description": "DBS certificate from employee",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "dbs_check", "name": "DBS Update Service Check", "category": "1_Legal_Safety",
         "type": "document", "source": "internal",
         "document_types": ["dbs_check", "dbs_update_service"],
         "allow_multiple_files": True,
         "priority": "mandatory", "priority_order": 5,
         "description": "Internal DBS verification - update service check result",
         "work_ready_hint": "Required before employee can start work"},
        
        # ======== REQUIRED SOON: Additional Training ========
        # (Core training defined in "training" section below)
        
        # ======== REQUIRED SOON: Role Readiness ========
        {"id": "health_screening", "name": "Health Screening Questionnaire", 
         "category": "3_Role_Readiness", "type": "form-generated",
         "template_name": "Health Screening Questionnaire",
         "allow_multiple_files": True, "source": "form",
         "priority": "required_soon", "priority_order": 20,
         "description": "Health questionnaire and medical attachments",
         "work_ready_hint": "Complete within first 2 weeks"},
        
        {"id": "induction", "name": "Induction & Competency Assessment", 
         "category": "3_Role_Readiness", "type": "form-generated",
         "template_name": "Induction & Competency Assessment",
         "allow_multiple_files": True, "source": "internal",
         "priority": "secondary", "priority_order": 30,
         "description": "Induction checklist, shadowing records, competency sign-offs",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "interview_record", "name": "Interview Record", 
         "category": "3_Role_Readiness", "type": "form-generated",
         "template_name": "Interview Record Form",
         "allow_multiple_files": True, "source": "internal",
         "priority": "secondary", "priority_order": 31,
         "description": "Interview notes, assessment, and supporting documents",
         "work_ready_hint": "Complete after employee starts"},
        
        # ======== REQUIRED SOON: References ========
        {"id": "reference_1", "name": "Reference 1", "category": "4_Employment",
         "type": "document", "source": "employee",
         "document_types": ["reference"],
         "allow_multiple_files": True,
         "priority": "required_soon", "priority_order": 21,
         "description": "First reference letter and attachments",
         "work_ready_hint": "Complete within first 2 weeks"},
        
        {"id": "reference_2", "name": "Reference 2", "category": "4_Employment",
         "type": "document", "source": "employee",
         "document_types": ["reference"],
         "allow_multiple_files": True,
         "priority": "required_soon", "priority_order": 22,
         "description": "Second reference letter and attachments",
         "work_ready_hint": "Complete within first 2 weeks"},
        
        # ======== SECONDARY: Employment Records ========
        {"id": "recruitment_checklist", "name": "Recruitment Compliance Checklist", 
         "category": "4_Employment", "type": "form-generated", 
         "template_name": "Recruitment Compliance Checklist",
         "allow_multiple_files": True, "source": "internal",
         "priority": "secondary", "priority_order": 32,
         "description": "Internal recruitment tracking checklist",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "application_form", "name": "Application Form", "category": "4_Employment", 
         "type": "form-generated", "template_name": "Application Form", 
         "allow_multiple_files": False, "source": "form",
         "priority": "secondary", "priority_order": 33,
         "description": "Completed application form",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "cv", "name": "CV / Resume", "category": "4_Employment", 
         "type": "document", "source": "employee",
         "document_types": ["cv", "resume"], 
         "allow_multiple_files": True,
         "priority": "secondary", "priority_order": 34,
         "description": "CV and supporting documents",
         "work_ready_hint": "Complete after employee starts"},
        
        # ======== SECONDARY: Agreements ========
        {"id": "contract", "name": "Contract Acknowledgement", 
         "category": "5_Agreements", "type": "form-generated",
         "template_name": "Contract Acknowledgement Form",
         "allow_multiple_files": True, "source": "form",
         "priority": "secondary", "priority_order": 35,
         "description": "Signed contract/offer letter and appendices",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "handbook", "name": "Employee Handbook Acknowledgement", 
         "category": "5_Agreements", "type": "form-generated",
         "template_name": "Employee Handbook Acknowledgement",
         "allow_multiple_files": False, "source": "form",
         "priority": "secondary", "priority_order": 36,
         "description": "Signed handbook acknowledgement",
         "work_ready_hint": "Complete after employee starts"},
        
        # ======== SECONDARY: Admin / Other ========
        {"id": "personal_info", "name": "Personal Information Form", 
         "category": "6_Admin", "type": "form-generated", 
         "template_name": "Personal Information Form",
         "allow_multiple_files": True, "source": "form",
         "priority": "secondary", "priority_order": 37,
         "description": "Personal details form with supporting docs",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "equal_opportunities", "name": "Equal Opportunities Monitoring", 
         "category": "6_Admin", "type": "form-generated",
         "template_name": "Equal Opportunities Monitoring Form",
         "allow_multiple_files": False, "source": "form",
         "priority": "secondary", "priority_order": 38,
         "description": "Diversity monitoring form",
         "work_ready_hint": "Complete after employee starts"},
    ],
    
    "training": [  # Training items with priority
        # ======== MANDATORY: Core Training (Required to Start Work) ========
        {"id": "safeguarding", "name": "Safeguarding Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Safeguarding",
         "allow_multiple_files": True,
         "priority": "mandatory", "priority_order": 6,
         "description": "Safeguarding certificate and transcript",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "manual_handling", "name": "Manual Handling Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Manual Handling",
         "allow_multiple_files": True,
         "priority": "mandatory", "priority_order": 7,
         "description": "Manual handling certificate",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "infection_control", "name": "Infection Control Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Infection Control",
         "allow_multiple_files": True,
         "priority": "mandatory", "priority_order": 8,
         "description": "Infection control certificate",
         "work_ready_hint": "Required before employee can start work"},
        
        # ======== REQUIRED SOON: Additional Training ========
        {"id": "bls", "name": "Basic Life Support (BLS)", "category": "2_Core_Training",
         "type": "training", "training_name": "Basic Life Support",
         "allow_multiple_files": True,
         "priority": "required_soon", "priority_order": 23,
         "description": "BLS certificate, renewal card",
         "work_ready_hint": "Complete within first 2 weeks"},
        
        {"id": "fire_safety", "name": "Fire Safety Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Fire Safety",
         "allow_multiple_files": True,
         "priority": "required_soon", "priority_order": 24,
         "description": "Fire safety certificate",
         "work_ready_hint": "Complete within first 2 weeks"},
        
        {"id": "health_safety", "name": "Health & Safety Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Health & Safety",
         "allow_multiple_files": True,
         "priority": "required_soon", "priority_order": 25,
         "description": "Health & Safety certificate",
         "work_ready_hint": "Complete within first 2 weeks"},
    ],
    
    "nurse_specific": [  # Additional items for Nurses only
        # ======== MANDATORY for Nurses ========
        {"id": "nmc_registration", "name": "NMC Registration", "category": "1_Legal_Safety",
         "type": "document", "source": "employee",
         "document_types": ["nmc_registration", "professional_registration"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "mandatory", "priority_order": 9,
         "description": "NMC PIN card, registration letter",
         "work_ready_hint": "Required before nurse can start work"},
        
        {"id": "clinical_competency", "name": "Clinical Competency Evidence", 
         "category": "2_Core_Training", "type": "document", "source": "employee",
         "document_types": ["clinical_competency", "competency_assessment"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "required_soon", "priority_order": 26,
         "description": "Clinical competency assessments, skill sign-offs",
         "work_ready_hint": "Complete within first 2 weeks"},
        
        {"id": "medication_competency", "name": "Medication Competency", 
         "category": "2_Core_Training", "type": "training", "training_name": "Medication",
         "allow_multiple_files": True,
         "priority": "required_soon", "priority_order": 27,
         "description": "Medication administration competency certificate",
         "work_ready_hint": "Complete within first 2 weeks"},
    ]
}

# Priority display configuration
PRIORITY_CONFIG = {
    "mandatory": {
        "label": "Required to Start Work",
        "color": "red",
        "weight": 0.8,  # 80% of score
        "emoji": "🔴"
    },
    "required_soon": {
        "label": "Required Soon",
        "color": "orange",
        "weight": 0.15,  # 15% of score
        "emoji": "🟠"
    },
    "secondary": {
        "label": "Complete After Start",
        "color": "yellow",
        "weight": 0.05,  # 5% of score
        "emoji": "🟡"
    }
}

# Category display names (care-focused)
CATEGORY_DISPLAY_NAMES = {
    "1_Legal_Safety": "Legal & Safety",
    "2_Core_Training": "Core Training",
    "3_Role_Readiness": "Role Readiness",
    "4_Employment": "Employment",
    "5_Agreements": "Agreements",
    "6_Admin": "Admin / Other"
}

# Legacy ID mapping for data migration
LEGACY_REQUIREMENT_MAPPING = {
    "identity_rtw": ["identity_documents", "right_to_work_documents"],  # Split into two
    "dbs": "dbs_certificate",  # Renamed
}

# ============================================================================
# EXPIRY TRACKING CONFIGURATION
# ============================================================================
# Items that should track expiry dates
EXPIRABLE_REQUIREMENTS = {
    # Documents with expiry
    "dbs_certificate",
    "right_to_work_documents",
    "nmc_registration",
    
    # Training with expiry
    "safeguarding",
    "manual_handling", 
    "infection_control",
    "bls",
    "fire_safety",
    "health_safety",
}

# Expiry thresholds (in days)
EXPIRY_WARNING_DAYS = 30  # Show "Expiring Soon" when within 30 days

def calculate_expiry_status(expiry_date_str: str) -> dict:
    """Calculate expiry status from date string"""
    if not expiry_date_str:
        return None
    
    try:
        from datetime import datetime, timezone
        
        # Parse expiry date
        if isinstance(expiry_date_str, str):
            # Handle ISO format
            if 'T' in expiry_date_str:
                expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            else:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            expiry_date = expiry_date_str
        
        now = datetime.now(timezone.utc)
        days_until_expiry = (expiry_date - now).days
        
        if days_until_expiry < 0:
            return {
                "status": "expired",
                "label": f"Expired on {expiry_date.strftime('%d %b %Y')}",
                "color": "error",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date.strftime('%Y-%m-%d')
            }
        elif days_until_expiry <= EXPIRY_WARNING_DAYS:
            return {
                "status": "expiring_soon",
                "label": f"Expires soon ({expiry_date.strftime('%d %b %Y')})",
                "color": "warning",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date.strftime('%Y-%m-%d')
            }
        else:
            return {
                "status": "valid",
                "label": f"Valid until {expiry_date.strftime('%d %b %Y')}",
                "color": "success",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date.strftime('%Y-%m-%d')
            }
    except Exception as e:
        print(f"Error calculating expiry status: {e}")
        return None

def get_mandatory_items_for_role(role: str) -> List[dict]:
    """Get all mandatory items for a specific role, sorted by priority"""
    items = MANDATORY_ITEMS["base"].copy() + MANDATORY_ITEMS["training"].copy()
    
    # Add nurse-specific items
    if role and "nurse" in role.lower():
        items.extend(MANDATORY_ITEMS["nurse_specific"])
    
    # Sort by priority_order (mandatory items first, then required_soon, then secondary)
    items.sort(key=lambda x: x.get('priority_order', 99))
    
    return items

def get_work_ready_items_for_role(role: str) -> set:
    """Get the set of requirement IDs that are mandatory for work readiness"""
    work_ready = WORK_READY_REQUIREMENTS.copy()
    
    # Add nurse-specific mandatory item
    if role and "nurse" in role.lower():
        work_ready.add("nmc_registration")
    
    return work_ready

def calculate_work_readiness(requirements: List[dict], role: str) -> dict:
    """
    Calculate work readiness status based on mandatory items.
    Returns work_ready_status and detailed breakdown.
    """
    work_ready_ids = get_work_ready_items_for_role(role)
    
    mandatory_items = []
    required_soon_items = []
    secondary_items = []
    
    mandatory_complete = 0
    mandatory_verified = 0
    required_soon_complete = 0
    secondary_complete = 0
    
    missing_mandatory = []
    
    for req in requirements:
        req_id = req.get('id')
        is_complete = req.get('status') == 'completed' and req.get('has_evidence', False)
        is_verified = req.get('verified', False)
        priority = req.get('priority', 'secondary')
        
        if req_id in work_ready_ids or priority == 'mandatory':
            mandatory_items.append(req)
            if is_complete:
                mandatory_complete += 1
                if is_verified:
                    mandatory_verified += 1
            else:
                missing_mandatory.append({
                    "id": req_id,
                    "name": req.get('name'),
                    "status": req.get('status')
                })
        elif priority == 'required_soon':
            required_soon_items.append(req)
            if is_complete:
                required_soon_complete += 1
        else:
            secondary_items.append(req)
            if is_complete:
                secondary_complete += 1
    
    total_mandatory = len(mandatory_items)
    total_required_soon = len(required_soon_items)
    total_secondary = len(secondary_items)
    total_all = total_mandatory + total_required_soon + total_secondary
    
    # Calculate weighted score (80% mandatory, 15% required_soon, 5% secondary)
    mandatory_score = (mandatory_complete / total_mandatory * 80) if total_mandatory > 0 else 0
    required_soon_score = (required_soon_complete / total_required_soon * 15) if total_required_soon > 0 else 0
    secondary_score = (secondary_complete / total_secondary * 5) if total_secondary > 0 else 0
    weighted_score = int(mandatory_score + required_soon_score + secondary_score)
    
    # Determine work ready status
    all_mandatory_complete = mandatory_complete == total_mandatory
    all_mandatory_verified = mandatory_verified == total_mandatory
    all_complete = (mandatory_complete + required_soon_complete + secondary_complete) == total_all
    all_verified = all([req.get('verified', False) for req in requirements if req.get('has_evidence')])
    
    if all_verified and all_complete:
        status = "fully_compliant"
        status_label = "Fully Compliant"
        status_color = "success"
    elif all_mandatory_verified:
        status = "work_ready"
        status_label = "Work Ready"
        status_color = "success"
    elif all_mandatory_complete:
        status = "almost_ready"
        status_label = "Almost Ready"
        status_color = "warning"
    elif mandatory_complete > 0:
        status = "in_progress"
        status_label = "Not Ready"
        status_color = "error"
    else:
        status = "not_started"
        status_label = "Not Ready"
        status_color = "error"
    
    return {
        "status": status,
        "status_label": status_label,
        "status_color": status_color,
        "weighted_score": weighted_score,
        "mandatory": {
            "total": total_mandatory,
            "complete": mandatory_complete,
            "verified": mandatory_verified,
            "missing": missing_mandatory
        },
        "required_soon": {
            "total": total_required_soon,
            "complete": required_soon_complete
        },
        "secondary": {
            "total": total_secondary,
            "complete": secondary_complete
        },
        "is_work_ready": all_mandatory_verified,
        "is_fully_compliant": all_verified and all_complete
    }

async def calculate_expiry_alerts_quick(employee_id: str) -> dict:
    """Quick expiry alerts calculation for list views"""
    expired_count = 0
    expiring_soon_count = 0
    
    # Check documents with expiry dates
    docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "expiry_date": {"$exists": True, "$ne": None}
    }, {"_id": 0, "expiry_date": 1}).to_list(100)
    
    for doc in docs:
        status = calculate_expiry_status(doc.get('expiry_date'))
        if status:
            if status['status'] == 'expired':
                expired_count += 1
            elif status['status'] == 'expiring_soon':
                expiring_soon_count += 1
    
    # Check training records with expiry dates
    training = await db.training_records.find({
        "employee_id": employee_id,
        "expiry_date": {"$exists": True, "$ne": None}
    }, {"_id": 0, "expiry_date": 1}).to_list(100)
    
    for t in training:
        status = calculate_expiry_status(t.get('expiry_date'))
        if status:
            if status['status'] == 'expired':
                expired_count += 1
            elif status['status'] == 'expiring_soon':
                expiring_soon_count += 1
    
    has_alerts = expired_count > 0 or expiring_soon_count > 0
    
    return {
        "expired_count": expired_count,
        "expiring_soon_count": expiring_soon_count,
        "has_alerts": has_alerts,
        "severity": "error" if expired_count > 0 else ("warning" if expiring_soon_count > 0 else None)
    }

# Folder mapping for form types to document folders
FORM_TO_FOLDER_MAP = {
    "Application Form": "A_Application_Form",
    "Recruitment Compliance Checklist": "B_Recruitment_Checklist",
    "Personal Information Form": "C_Personal_Information",
    "Interview Record Form": "D_Interview",
    "Interview Record": "D_Interview",
    "Equal Opportunities Monitoring Form": "E_Equal_Opportunities",
    "Equal Opportunities Monitoring": "E_Equal_Opportunities",
    "Health Screening Questionnaire": "F_Health_Screening",
    "Health Screening": "F_Health_Screening",
    "Identity Verification": "G_Identity_RTW",
    "Right to Work": "G_Identity_RTW",
    "Reference Form": "H_References",
    "Reference 1": "H_References",
    "Reference 2": "H_References",
    "DBS Declaration": "I_DBS",
    "Induction & Competency Assessment": "J_Induction_Shadowing_Observations",
    "Induction Checklist": "J_Induction_Shadowing_Observations",
    "HMRC Starter Checklist": "K_HMRC",
    "Contract Acknowledgement Form": "L_Contract",
    "Contract Acknowledgement": "L_Contract",
    "Supervision Form": "M_Supervision_Appraisals",
    "Training Certificate": "N_Training",
    "Employee Handbook Acknowledgement": "O_Other",
}

def get_folder_for_form(form_name: str) -> str:
    """Get the document folder for a form type"""
    # Direct match
    if form_name in FORM_TO_FOLDER_MAP:
        return FORM_TO_FOLDER_MAP[form_name]
    
    # Partial match
    form_lower = form_name.lower()
    for key, folder in FORM_TO_FOLDER_MAP.items():
        if key.lower() in form_lower or form_lower in key.lower():
            return folder
    
    return "O_Other"  # Default folder

def generate_document_filename(employee_name: str, form_type: str, date_str: str = None) -> str:
    """Generate structured document filename: EmployeeName_FormType_Date.pdf"""
    import re
    # Clean employee name
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', employee_name.replace(' ', ''))
    # Clean form type
    clean_form = re.sub(r'[^a-zA-Z0-9]', '', form_type.replace(' ', ''))
    # Get date
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime('%d-%m-%Y')
    
    return f"{clean_name}_{clean_form}_{date_str}.pdf"

# Requirement ID to document type name mapping for auto-matching
REQUIREMENT_TO_DOCTYPE = {
    "application_form": ["Application Form"],
    "cv": ["CV", "CV / Resume", "Resume", "Curriculum Vitae"],
    "recruitment_checklist": ["Recruitment Checklist", "Recruitment Compliance Checklist", "New Starter Form"],
    "personal_info": ["Personal Information Form", "Personal Information"],
    "interview_record": ["Interview Record", "Interview Questions", "Interview Record Form"],
    "equal_opportunities": ["Equal Opportunities", "Equal Opportunities Monitoring", "Equal Opportunities Monitoring Form"],
    "health_screening": ["Health Screening", "Health Screening Form", "Health Screening Questionnaire"],
    "identity_rtw": ["Right to Work", "Right to Work in UK", "Passport", "Visa", "Identity Verification"],
    "reference_1": ["Reference 1", "Reference"],
    "reference_2": ["Reference 2", "Reference"],
    "references": ["Reference 1", "Reference 2", "Reference"],
    "dbs": ["DBS", "DBS Certificate", "DBS Check"],
    "induction": ["Induction", "Induction Checklist", "Induction & Competency Assessment"],
    "contract": ["Contract", "Contract Acknowledgement", "Contract of Employment", "Contract Acknowledgement Form"],
    "handbook": ["Employee Handbook", "Handbook Acknowledgement", "Employee Handbook Receipt", "Employee Handbook Acknowledgement"],
    "nmc_registration": ["NMC Registration", "NMC", "Professional Registration"],
    "clinical_competency": ["Clinical Competency", "Competency Assessment"],
}

def get_requirement_id_from_doctype(doc_type_name: str) -> Optional[str]:
    """Get the requirement ID that a document type belongs to"""
    doc_lower = doc_type_name.lower()
    
    for req_id, doc_names in REQUIREMENT_TO_DOCTYPE.items():
        for name in doc_names:
            if name.lower() in doc_lower or doc_lower in name.lower():
                return req_id
    
    # Special handling for references
    if 'reference 1' in doc_lower:
        return 'reference_1'
    if 'reference 2' in doc_lower:
        return 'reference_2'
    if 'reference' in doc_lower:
        return 'references'
    
    return None

def get_requirement_name(requirement_id: str) -> Optional[str]:
    """Get the human-readable name for a requirement ID"""
    all_items = MANDATORY_ITEMS['base'] + MANDATORY_ITEMS['training'] + MANDATORY_ITEMS['nurse_specific']
    for item in all_items:
        if item['id'] == requirement_id:
            return item['name']
    
    # Handle special reference cases
    if requirement_id == 'reference_1':
        return 'Reference 1'
    if requirement_id == 'reference_2':
        return 'Reference 2'
    
    return None

async def check_item_completion(employee_id: str, item: dict) -> dict:
    """Check if a specific mandatory item is complete for an employee"""
    result = {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "type": item["type"],
        "status": "missing",
        "verified": False,
        "details": None,
        "expiry_date": None
    }
    
    requirement_id = item["id"]
    
    if item["type"] == "form":
        # Check for completed form - FIRST by requirement_id, then by template_name
        form = await db.generated_forms.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "status": {"$in": ["completed", "completed_imported", "reviewed", "signed_off"]}
        }, {"_id": 0, "id": 1, "status": 1, "completed_at": 1, "signed_off_at": 1})
        
        # Fallback to template name matching
        if not form:
            form = await db.generated_forms.find_one({
                "employee_id": employee_id,
                "template_name": {"$regex": item.get("template_name", ""), "$options": "i"},
                "status": {"$in": ["completed", "completed_imported", "reviewed", "signed_off"]}
            }, {"_id": 0, "id": 1, "status": 1, "completed_at": 1, "signed_off_at": 1})
        
        if form:
            result["status"] = "complete"
            result["verified"] = form.get("status") == "signed_off"
            result["details"] = f"Form ID: {form['id']}"
    
    elif item["type"] == "document":
        # Check for documents - FIRST by requirement_id (exclude superseded/inactive)
        min_count = item.get("min_files", 1)
        
        docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "file_url": {"$exists": True, "$ne": None},
            "status": {"$in": ["uploaded", "approved"]},
            "$or": [
                {"active": {"$exists": False}},
                {"active": True}
            ]
        }, {"_id": 0, "id": 1, "status": 1, "verified": 1, "expiry_date": 1}).to_list(20)
        
        # Fallback to document_type_name matching for legacy documents
        if len(docs) < min_count:
            doc_types = item.get("document_types", [])
            fallback_docs = await db.employee_documents.find({
                "employee_id": employee_id,
                "requirement_id": {"$exists": False},
                "document_type_name": {"$regex": f"({'|'.join(doc_types)})", "$options": "i"},
                "file_url": {"$exists": True, "$ne": None},
                "status": {"$in": ["uploaded", "approved"]},
                "$or": [
                    {"active": {"$exists": False}},
                    {"active": True}
                ]
            }, {"_id": 0, "id": 1, "status": 1, "verified": 1, "expiry_date": 1}).to_list(20)
            docs.extend(fallback_docs)
        
        if len(docs) >= min_count:
            result["status"] = "complete"
            result["verified"] = all(d.get("verified") or d.get("status") == "approved" for d in docs)
            result["details"] = f"{len(docs)} document(s) uploaded"
            # Check for expiring documents
            for doc in docs:
                if doc.get("expiry_date"):
                    try:
                        exp_date = datetime.fromisoformat(doc["expiry_date"].replace('Z', '+00:00'))
                        if exp_date < datetime.now(timezone.utc) + timedelta(days=30):
                            result["status"] = "expiring"
                            result["expiry_date"] = doc["expiry_date"]
                    except:
                        pass
    
    elif item["type"] == "training":
        # Check for completed training
        training = await db.training_records.find_one({
            "employee_id": employee_id,
            "training_name": {"$regex": item.get("training_name", ""), "$options": "i"},
            "status": "completed"
        }, {"_id": 0, "id": 1, "status": 1, "completed_at": 1, "expiry_date": 1})
        
        if training:
            result["status"] = "complete"
            result["verified"] = True
            result["details"] = f"Completed: {training.get('completed_at', 'N/A')}"
            if training.get("expiry_date"):
                try:
                    exp_date = datetime.fromisoformat(training["expiry_date"].replace('Z', '+00:00'))
                    if exp_date < datetime.now(timezone.utc) + timedelta(days=30):
                        result["status"] = "expiring"
                        result["expiry_date"] = training["expiry_date"]
                except:
                    pass
    
    return result

async def calculate_employee_compliance(employee_id: str, role: str) -> dict:
    """Calculate full compliance status for an employee"""
    mandatory_items = get_mandatory_items_for_role(role)
    
    results = []
    complete_count = 0
    verified_count = 0
    expiring_count = 0
    missing_count = 0
    
    for item in mandatory_items:
        check = await check_item_completion(employee_id, item)
        results.append(check)
        
        if check["status"] == "complete":
            complete_count += 1
            if check["verified"]:
                verified_count += 1
        elif check["status"] == "expiring":
            complete_count += 1
            expiring_count += 1
        else:
            missing_count += 1
    
    total_items = len(mandatory_items)
    completion_percentage = int((complete_count / total_items) * 100) if total_items > 0 else 0
    verification_percentage = int((verified_count / total_items) * 100) if total_items > 0 else 0
    
    return {
        "items": results,
        "total_items": total_items,
        "complete_count": complete_count,
        "verified_count": verified_count,
        "expiring_count": expiring_count,
        "missing_count": missing_count,
        "completion_percentage": completion_percentage,
        "verification_percentage": verification_percentage
    }

async def derive_onboarding_status(employee_id: str, role: str, current_status: str = None) -> str:
    """Auto-derive onboarding status based on compliance progress"""
    # Don't change archived status
    if current_status == OnboardingStatus.ARCHIVED:
        return OnboardingStatus.ARCHIVED
    
    compliance = await calculate_employee_compliance(employee_id, role)
    
    # Check for any activity
    forms_count = await db.generated_forms.count_documents({"employee_id": employee_id})
    docs_count = await db.employee_documents.count_documents({"employee_id": employee_id})
    training_count = await db.training_records.count_documents({"employee_id": employee_id})
    
    total_activity = forms_count + docs_count + training_count
    
    if total_activity == 0:
        return OnboardingStatus.NEW
    
    # All mandatory items complete and verified
    if compliance["complete_count"] == compliance["total_items"]:
        if compliance["verified_count"] == compliance["total_items"]:
            # Check if they are actively working (has current assignment or marked active)
            if current_status == OnboardingStatus.ACTIVE:
                return OnboardingStatus.ACTIVE
            return OnboardingStatus.READY_FOR_PLACEMENT
        else:
            return OnboardingStatus.UNDER_REVIEW
    
    # Has activity but items still missing
    return OnboardingStatus.DOCUMENTS_PENDING

# User Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = UserRole.EMPLOYEE

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    role: str
    picture: Optional[str] = None
    created_at: str

# Employee Models
class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    onboarding_status: str = OnboardingStatus.NEW
    status: str = EmployeeStatus.NEW
    start_date: Optional[str] = None
    manager_name: Optional[str] = None
    driver_status: bool = False
    notes: Optional[str] = None
    profile_photo_url: Optional[str] = None

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    onboarding_status: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    manager_name: Optional[str] = None
    driver_status: Optional[bool] = None
    notes: Optional[str] = None
    profile_photo_url: Optional[str] = None

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    role: str
    onboarding_status: str = OnboardingStatus.NEW
    status: str
    start_date: Optional[str] = None
    manager_name: Optional[str] = None
    driver_status: bool = False
    notes: Optional[str] = None
    completion_percentage: int = 0
    profile_photo_url: Optional[str] = None
    work_readiness: Optional[dict] = None  # Work readiness status for list view
    expiry_alerts: Optional[dict] = None  # Expiry alerts count for list view
    created_at: str
    updated_at: str

# Document Type Models
class DocumentTypeCreate(BaseModel):
    name: str
    category: str
    required_for_role: List[str] = []
    has_expiry: bool = False
    required_before_active: bool = False
    sort_order: int = 0

class DocumentTypeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    category: str
    required_for_role: List[str] = []
    has_expiry: bool = False
    required_before_active: bool = False
    sort_order: int = 0

# Employee Document Models
class EmployeeDocumentCreate(BaseModel):
    employee_id: str
    document_type_id: str
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    requirement_id: Optional[str] = None  # Links to MANDATORY_ITEMS id
    document_label: Optional[str] = None  # e.g., "Passport Front", "Visa", for multi-file requirements

class EmployeeDocumentUpdate(BaseModel):
    status: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    verified: Optional[bool] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    requirement_id: Optional[str] = None
    document_label: Optional[str] = None

class EmployeeDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_id: str
    document_type_id: str
    document_type_name: Optional[str] = None
    category: Optional[str] = None
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    status: str
    uploaded_by: Optional[str] = None
    uploaded_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    version_number: int = 1
    # Verification fields
    verified: bool = False
    verified_by: Optional[str] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[str] = None
    source_type: Optional[str] = None  # "manual", "imported", "form_submission"
    source_form_id: Optional[str] = None  # Link to generated form if applicable
    # Requirement linking
    requirement_id: Optional[str] = None  # Links to MANDATORY_ITEMS id
    requirement_name: Optional[str] = None
    document_label: Optional[str] = None  # e.g., "Passport Front", "Visa"

# Policy Models
class PolicyCreate(BaseModel):
    title: str
    version: str
    description: Optional[str] = None
    category: Optional[str] = None
    effective_date: Optional[str] = None

class PolicyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    version: str
    description: Optional[str] = None
    category: Optional[str] = None
    file_url: Optional[str] = None
    active: bool = True
    effective_date: Optional[str] = None
    published_at: str
    assigned_count: int = 0
    signed_count: int = 0

# Policy Assignment Models
class PolicyAssignmentCreate(BaseModel):
    policy_id: str
    employee_ids: List[str]
    message: Optional[str] = None

class PolicyAssignmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    policy_id: str
    policy_title: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    assigned_at: str
    status: str
    viewed_at: Optional[str] = None
    signed_at: Optional[str] = None

# Training Record Models
class TrainingRecordCreate(BaseModel):
    employee_id: str
    training_name: str
    mandatory: bool = True
    completion_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str = "not_started"

class TrainingRecordResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_id: str
    training_name: str
    mandatory: bool = True
    completion_date: Optional[str] = None
    expiry_date: Optional[str] = None
    certificate_url: Optional[str] = None
    original_filename: Optional[str] = None
    uploaded_at: Optional[str] = None
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    completion_method: Optional[str] = None  # "certificate" or "manual" 
    requirement_id: Optional[str] = None
    status: str
    created_at: str

# Contact/Application Form Models
class ContactForm(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    organisation: Optional[str] = None
    subject: str
    message: str

class ApplicationForm(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None
    postcode: Optional[str] = None
    role_applied: str
    availability: Optional[str] = None
    right_to_work: bool = False
    has_dbs: bool = False
    experience_summary: Optional[str] = None
    how_heard: Optional[str] = None

# Dashboard Stats Model
class DashboardStats(BaseModel):
    total_employees: int = 0
    total_applicants: int = 0
    fully_verified_employees: int = 0
    onboarding_in_progress: int = 0
    missing_urgent_documents: int = 0
    unsigned_policies: int = 0
    dbs_pending: int = 0
    rtw_missing: int = 0
    references_outstanding: int = 0
    expiring_30_days: int = 0
    expiring_60_days: int = 0
    expiring_90_days: int = 0

# Email Request Model
class EmailRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    html_content: str

# ==================== TEMPLATE LIBRARY MODELS ====================

class FormStatus:
    DRAFT = "draft"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    SIGNED_OFF = "signed_off"
    ARCHIVED = "archived"

class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str  # e.g., "Identity", "References", "Training", "Contract"
    linked_document_type_id: Optional[str] = None  # Links to document_types
    form_fields: List[Dict[str, Any]] = []  # JSON schema for form fields
    requires_employee_signature: bool = True
    requires_admin_signature: bool = True
    content_html: str = ""  # HTML template content
    visibility: str = "normal"  # normal, restricted, confidential
    role_specific: Optional[str] = None  # None = all roles, "Nurse", "Healthcare Assistant"
    section: Optional[str] = None  # Recruitment, Interview, Compliance, etc.

class TemplateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = None
    category: str
    linked_document_type_id: Optional[str] = None
    form_fields: List[Dict[str, Any]] = []
    requires_employee_signature: bool = True
    requires_admin_signature: bool = True
    content_html: str = ""
    active: bool = True
    version: int = 1
    visibility: str = "normal"
    role_specific: Optional[str] = None
    section: Optional[str] = None
    created_at: str
    updated_at: str

class GeneratedFormCreate(BaseModel):
    template_id: str
    employee_id: str
    form_data: Dict[str, Any] = {}

class GeneratedFormUpdate(BaseModel):
    form_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    employee_signature: Optional[str] = None
    employee_signed_at: Optional[str] = None
    admin_signature: Optional[str] = None
    admin_signed_at: Optional[str] = None
    notes: Optional[str] = None

class GeneratedFormResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    template_id: str
    template_name: Optional[str] = None
    template_category: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    form_data: Dict[str, Any] = {}
    status: str
    employee_signature: Optional[str] = None
    employee_signed_at: Optional[str] = None
    admin_signature: Optional[str] = None
    admin_signed_at: Optional[str] = None
    admin_signoff_by: Optional[str] = None
    pdf_url: Optional[str] = None
    locked: bool = False
    notes: Optional[str] = None
    version: int = 1
    access_token: Optional[str] = None
    created_at: str
    updated_at: str
    sent_at: Optional[str] = None
    viewed_at: Optional[str] = None
    completed_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    signed_off_at: Optional[str] = None
    requirement_id: Optional[str] = None  # Link to compliance requirement
    imported: bool = False
    original_filename: Optional[str] = None

class BulkUploadResult(BaseModel):
    employee_id: str
    employee_name: str
    successful: int = 0
    failed: int = 0
    errors: List[str] = []

# ==================== COMPLIANCE CENTRE MODELS ====================

class OrgPolicyStatus(str):
    MISSING = "missing"
    ACTIVE = "active"
    EXPIRED = "expired"
    UNDER_REVIEW = "under_review"

class OrgPolicyCreate(BaseModel):
    name: str
    category: str
    version: str = "v1.0"
    review_date: Optional[str] = None
    notes: Optional[str] = None

class OrgPolicyUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    review_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class OrgPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    category: str
    version: str
    status: str  # missing, active, expired, under_review
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    review_date: Optional[str] = None
    last_reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
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
    status: str  # valid, expiring_soon, expired, missing
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    expiry_date: Optional[str] = None
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
    attachments: List[str] = []

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        user = await db.users.find_one({"user_id": payload['user_id']}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user['role'] not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_manager_or_admin(user: dict = Depends(get_current_user)) -> dict:
    if user['role'] not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.BRANCH_MANAGER]:
        raise HTTPException(status_code=403, detail="Manager or admin access required")
    return user

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register")
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id,
        "email": user.email,
        "password": hash_password(user.password),
        "name": user.name,
        "role": user.role,
        "assignment": user.assignment if hasattr(user, 'assignment') else "Unassigned",
        "picture": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, user.email, user.role)
    user_response = {k: v for k, v in user_doc.items() if k != 'password'}
    return {"token": token, "user": user_response}

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user['user_id'], user['email'], user['role'])
    user_response = {k: v for k, v in user.items() if k != 'password'}
    return {"token": token, "user": user_response}

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {k: v for k, v in user.items() if k != 'password'}

# Emergent Google OAuth session exchange
@api_router.post("/auth/session")
async def exchange_session(session_id: str = Header(None, alias="X-Session-ID")):
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    try:
        resp = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=30
        )
        resp.raise_for_status()
        session_data = resp.json()
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": session_data['email']}, {"_id": 0})
        
        if existing_user:
            user_id = existing_user['user_id']
            # Update user info if needed
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"name": session_data.get('name', existing_user['name']), "picture": session_data.get('picture')}}
            )
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        else:
            # Create new user
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            user = {
                "user_id": user_id,
                "email": session_data['email'],
                "name": session_data.get('name', ''),
                "picture": session_data.get('picture'),
                "role": UserRole.EMPLOYEE,
                "password": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
        
        # Store session
        await db.user_sessions.insert_one({
            "user_id": user_id,
            "session_token": session_data['session_token'],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        token = create_token(user_id, user['email'], user['role'])
        user_response = {k: v for k, v in user.items() if k not in ['password', '_id']}
        return {"token": token, "user": user_response}
    except requests.RequestException as e:
        logger.error(f"OAuth session exchange failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to exchange session")

# ==================== EMPLOYEE ROUTES ====================

async def generate_employee_code():
    last_employee = await db.employees.find_one(sort=[("employee_code", -1)])
    if last_employee and last_employee.get('employee_code'):
        try:
            num = int(last_employee['employee_code'].split('-')[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f"OCS-{str(num).zfill(4)}"

async def calculate_completion_percentage(employee_id: str) -> int:
    """Calculate completion percentage based on REQUIREMENT completion, not document count"""
    # Get employee role
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "role": 1})
    if not employee:
        return 0
    
    role = employee.get('role', '')
    
    # Use the requirement-based compliance calculation
    compliance = await calculate_employee_compliance(employee_id, role)
    
    return compliance.get('completion_percentage', 0)

async def calculate_work_readiness_quick(employee_id: str, role: str) -> dict:
    """Quick work readiness calculation for list views"""
    work_ready_ids = get_work_ready_items_for_role(role)
    
    # Get documents for mandatory items
    docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$in": list(work_ready_ids)},
        "verified": True
    }, {"_id": 0, "requirement_id": 1}).to_list(100)
    
    # Get verified training for mandatory items
    training_ids = {r for r in work_ready_ids if r in ["safeguarding", "manual_handling", "infection_control"]}
    training = await db.training_records.find({
        "employee_id": employee_id,
        "requirement_id": {"$in": list(training_ids)},
        "verified": True
    }, {"_id": 0, "requirement_id": 1}).to_list(100)
    
    verified_ids = {d['requirement_id'] for d in docs}
    verified_ids.update({t['requirement_id'] for t in training})
    
    mandatory_complete = len(verified_ids.intersection(work_ready_ids))
    total_mandatory = len(work_ready_ids)
    
    if mandatory_complete == total_mandatory:
        return {"status": "work_ready", "label": "Work Ready", "color": "success"}
    elif mandatory_complete >= total_mandatory - 2:
        return {"status": "almost_ready", "label": "Almost Ready", "color": "warning"}
    elif mandatory_complete > 0:
        return {"status": "in_progress", "label": "Not Ready", "color": "error"}
    else:
        return {"status": "not_started", "label": "Not Ready", "color": "error"}

@api_router.post("/employees", response_model=EmployeeResponse)
async def create_employee(employee: EmployeeCreate, user: dict = Depends(require_manager_or_admin)):
    employee_id = str(uuid.uuid4())
    employee_code = await generate_employee_code()
    now = datetime.now(timezone.utc).isoformat()
    
    employee_doc = {
        "id": employee_id,
        "employee_code": employee_code,
        **employee.model_dump(),
        "completion_percentage": 0,
        "created_at": now,
        "updated_at": now
    }
    await db.employees.insert_one(employee_doc)
    
    # Log action
    await log_audit_action(user['user_id'], "create_employee", "employee", employee_id, {"employee_code": employee_code})
    
    return EmployeeResponse(**employee_doc)

@api_router.get("/employees", response_model=List[EmployeeResponse])
async def get_employees(
    onboarding_status: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = False,
    missing_dbs: bool = False,
    missing_rtw: bool = False,
    missing_references: bool = False,
    unsigned_policies: bool = False,
    expiring_soon: bool = False,
    user: dict = Depends(get_current_user)
):
    query = {}
    
    # Onboarding status filter
    if onboarding_status:
        query["onboarding_status"] = onboarding_status
    
    if status:
        query["status"] = status
    elif not include_archived:
        # By default, exclude archived employees unless specifically requested
        query["status"] = {"$ne": EmployeeStatus.ARCHIVED}
    
    if role:
        query["role"] = role
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"employee_code": {"$regex": search, "$options": "i"}}
        ]
    
    employees = await db.employees.find(query, {"_id": 0}).to_list(1000)
    
    # Calculate completion percentages, work readiness, and expiry alerts
    for emp in employees:
        emp['completion_percentage'] = await calculate_completion_percentage(emp['id'])
        emp['work_readiness'] = await calculate_work_readiness_quick(emp['id'], emp.get('role', ''))
        emp['expiry_alerts'] = await calculate_expiry_alerts_quick(emp['id'])
    
    return [EmployeeResponse(**emp) for emp in employees]

@api_router.get("/onboarding-statuses")
async def get_onboarding_statuses(user: dict = Depends(get_current_user)):
    """Get list of available onboarding status options"""
    return [
        OnboardingStatus.NEW,
        OnboardingStatus.DOCUMENTS_PENDING,
        OnboardingStatus.UNDER_REVIEW,
        OnboardingStatus.READY_FOR_PLACEMENT,
        OnboardingStatus.ACTIVE,
        OnboardingStatus.ARCHIVED
    ]

@api_router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str, user: dict = Depends(get_current_user)):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee['completion_percentage'] = await calculate_completion_percentage(employee_id)
    return EmployeeResponse(**employee)

@api_router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(employee_id: str, update: EmployeeUpdate, user: dict = Depends(require_manager_or_admin)):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await log_audit_action(user['user_id'], "update_employee", "employee", employee_id, update_data)
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    employee['completion_percentage'] = await calculate_completion_percentage(employee_id)
    return EmployeeResponse(**employee)

@api_router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, user: dict = Depends(require_admin)):
    result = await db.employees.delete_one({"id": employee_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await log_audit_action(user['user_id'], "delete_employee", "employee", employee_id, {})
    return {"message": "Employee deleted"}

@api_router.post("/employees/{employee_id}/archive")
async def archive_employee(employee_id: str, user: dict = Depends(require_manager_or_admin)):
    """Archive an employee - soft delete that retains all data"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.get("status") == EmployeeStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Employee is already archived")
    
    previous_status = employee.get("status")
    update_data = {
        "status": EmployeeStatus.ARCHIVED,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "archived_by": user['user_id'],
        "previous_status": previous_status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'], 
        "archive_employee", 
        "employee", 
        employee_id, 
        {
            "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
            "employee_code": employee.get('employee_code'),
            "previous_status": previous_status,
            "reason": "Employee archived"
        }
    )
    
    return {"message": "Employee archived successfully", "employee_id": employee_id}

@api_router.post("/employees/{employee_id}/restore")
async def restore_employee(employee_id: str, user: dict = Depends(require_manager_or_admin)):
    """Restore an archived employee to their previous status"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.get("status") != EmployeeStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Employee is not archived")
    
    restore_status = employee.get("previous_status", EmployeeStatus.INACTIVE)
    update_data = {
        "status": restore_status,
        "archived_at": None,
        "archived_by": None,
        "previous_status": None,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'], 
        "restore_employee", 
        "employee", 
        employee_id, 
        {
            "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
            "restored_to_status": restore_status
        }
    )
    
    return {"message": "Employee restored successfully", "employee_id": employee_id, "status": restore_status}

@api_router.delete("/employees/{employee_id}/permanent")
async def permanent_delete_employee(employee_id: str, user: dict = Depends(require_admin)):
    """Permanently delete an employee and all related data. Super Admin only.
    Use only for: duplicate records, test/demo records, incorrect entries."""
    
    # Only super_admin can permanently delete
    if user.get('role') != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only Super Admin can permanently delete employees")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_info = {
        "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
        "employee_code": employee.get('employee_code'),
        "email": employee.get('email'),
        "status_at_deletion": employee.get('status')
    }
    
    # Delete employee record
    await db.employees.delete_one({"id": employee_id})
    
    # Delete related records
    deleted_docs = await db.employee_documents.delete_many({"employee_id": employee_id})
    deleted_forms = await db.generated_forms.delete_many({"employee_id": employee_id})
    deleted_policies = await db.policy_assignments.delete_many({"employee_id": employee_id})
    deleted_training = await db.training_records.delete_many({"employee_id": employee_id})
    
    await log_audit_action(
        user['user_id'], 
        "permanent_delete_employee", 
        "employee", 
        employee_id, 
        {
            **employee_info,
            "deleted_documents": deleted_docs.deleted_count,
            "deleted_forms": deleted_forms.deleted_count,
            "deleted_policies": deleted_policies.deleted_count,
            "deleted_training": deleted_training.deleted_count,
            "action": "PERMANENT DELETION - All employee data removed"
        }
    )
    
    return {
        "message": "Employee permanently deleted",
        "employee_id": employee_id,
        "deleted_records": {
            "documents": deleted_docs.deleted_count,
            "forms": deleted_forms.deleted_count,
            "policies": deleted_policies.deleted_count,
            "training": deleted_training.deleted_count
        }
    }

# ==================== EMPLOYEE COMPLIANCE ROUTES ====================

@api_router.post("/employees/{employee_id}/profile-photo")
async def upload_profile_photo(
    employee_id: str, 
    file: UploadFile = File(...),
    user: dict = Depends(require_manager_or_admin)
):
    """Upload profile photo for an employee"""
    # Validate employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, and WEBP images are allowed")
    
    # Check file size (5MB max)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be less than 5MB")
    
    # Upload to storage
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    storage_path = f"{APP_NAME}/profile-photos/{employee_id}/photo.{file_ext}"
    
    try:
        result = put_object(storage_path, content, file.content_type)
        file_url = result.get("url", storage_path)
        
        # Update employee record
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "profile_photo_url": file_url,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await log_audit_action(
            user['user_id'],
            "upload_profile_photo",
            "employee",
            employee_id,
            {"photo_url": file_url[:50] + "..." if len(file_url) > 50 else file_url}
        )
        
        return {"message": "Profile photo uploaded", "photo_url": file_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

@api_router.delete("/employees/{employee_id}/profile-photo")
async def remove_profile_photo(employee_id: str, user: dict = Depends(require_manager_or_admin)):
    """Remove profile photo for an employee"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "profile_photo_url": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "remove_profile_photo",
        "employee",
        employee_id,
        {}
    )
    
    return {"message": "Profile photo removed"}

@api_router.get("/employees/{employee_id}/profile-photo/view")
async def view_profile_photo(employee_id: str, user: dict = Depends(get_current_user)):
    """View/stream profile photo for an employee"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "profile_photo_url": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    photo_url = employee.get("profile_photo_url")
    if not photo_url:
        raise HTTPException(status_code=404, detail="No profile photo")
    
    try:
        file_bytes, stored_content_type = get_object(photo_url)
        # Determine content type from extension if not provided
        ext = photo_url.split('.')[-1].lower() if '.' in photo_url else 'jpg'
        content_types = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'webp': 'image/webp'
        }
        content_type = stored_content_type or content_types.get(ext, 'image/jpeg')
        return Response(content=file_bytes, media_type=content_type)
    except Exception as e:
        logger.error(f"Failed to retrieve profile photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve photo")

@api_router.get("/employees/{employee_id}/compliance")
async def get_employee_compliance(employee_id: str, user: dict = Depends(get_current_user)):
    """Get full compliance status for an employee including all mandatory items"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    compliance = await calculate_employee_compliance(employee_id, employee.get("role", ""))
    derived_status = await derive_onboarding_status(employee_id, employee.get("role", ""), employee.get("onboarding_status"))
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
        "role": employee.get("role"),
        "current_onboarding_status": employee.get("onboarding_status", "New"),
        "derived_onboarding_status": derived_status,
        "compliance": compliance
    }

@api_router.post("/employees/{employee_id}/refresh-status")
async def refresh_employee_onboarding_status(employee_id: str, user: dict = Depends(require_manager_or_admin)):
    """Refresh and auto-update employee's onboarding status based on compliance"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    current_status = employee.get("onboarding_status", "New")
    derived_status = await derive_onboarding_status(employee_id, employee.get("role", ""), current_status)
    
    if derived_status != current_status:
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "onboarding_status": derived_status,
                "onboarding_status_updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await log_audit_action(
            user['user_id'],
            "auto_update_onboarding_status",
            "employee",
            employee_id,
            {
                "previous_status": current_status,
                "new_status": derived_status,
                "reason": "Auto-derived from compliance progress"
            }
        )
    
    # Calculate new completion percentage
    compliance = await calculate_employee_compliance(employee_id, employee.get("role", ""))
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"completion_percentage": compliance["completion_percentage"]}}
    )
    
    return {
        "employee_id": employee_id,
        "previous_status": current_status,
        "new_status": derived_status,
        "completion_percentage": compliance["completion_percentage"],
        "status_changed": derived_status != current_status
    }

@api_router.post("/employees/{employee_id}/override-status")
async def override_employee_status(
    employee_id: str, 
    new_status: str = Query(..., description="New onboarding status"),
    reason: str = Query(None, description="Reason for override"),
    user: dict = Depends(require_admin)
):
    """Manually override onboarding status (Super Admin only)"""
    if user.get('role') != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only Super Admin can override onboarding status")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    valid_statuses = [OnboardingStatus.NEW, OnboardingStatus.DOCUMENTS_PENDING, 
                     OnboardingStatus.UNDER_REVIEW, OnboardingStatus.READY_FOR_PLACEMENT,
                     OnboardingStatus.ACTIVE, OnboardingStatus.ARCHIVED]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    previous_status = employee.get("onboarding_status", "New")
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "onboarding_status": new_status,
            "onboarding_status_override": True,
            "onboarding_status_override_by": user['user_id'],
            "onboarding_status_override_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "manual_override_onboarding_status",
        "employee",
        employee_id,
        {
            "previous_status": previous_status,
            "new_status": new_status,
            "reason": reason or "Manual override by Super Admin"
        }
    )
    
    return {
        "employee_id": employee_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "override": True
    }

# ==================== EMPLOYEE EXPORT ROUTES ====================

@api_router.get("/employees/{employee_id}/export-file")
async def export_employee_file(employee_id: str, user: dict = Depends(get_current_user)):
    """Export employee file as ZIP with organized folder structure"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    # Define folder structure
    folders = [
        "A_Application_Form",
        "B_Recruitment_Checklist", 
        "C_Personal_Information",
        "D_Interview",
        "E_Equal_Opportunities",
        "F_Health_Screening",
        "G_Identity_RTW",
        "H_References",
        "I_DBS",
        "J_Induction_Shadowing_Observations",
        "K_HMRC",
        "L_Contract",
        "M_Supervision_Appraisals",
        "N_Training",
        "O_Other"
    ]
    
    # Map form templates to folders
    form_folder_map = {
        "Application Form": "A_Application_Form",
        "Recruitment Compliance Checklist": "B_Recruitment_Checklist",
        "Personal Information Form": "C_Personal_Information",
        "Interview Record Form": "D_Interview",
        "Equal Opportunities Monitoring Form": "E_Equal_Opportunities",
        "Health Screening Questionnaire": "F_Health_Screening",
        "Induction & Competency Assessment": "J_Induction_Shadowing_Observations",
        "Contract Acknowledgement Form": "L_Contract",
        "Supervision Record": "M_Supervision_Appraisals",
        "Annual Appraisal Form": "M_Supervision_Appraisals",
        "Reference Request & Verification Form": "H_References",
        "DBS Review & Risk Assessment": "I_DBS",
        "Employee Handbook Acknowledgement": "O_Other"
    }
    
    # Map document types to folders
    doc_folder_map = {
        "passport": "G_Identity_RTW",
        "visa": "G_Identity_RTW",
        "right_to_work": "G_Identity_RTW",
        "driving_licence": "G_Identity_RTW",
        "birth_certificate": "G_Identity_RTW",
        "dbs": "I_DBS",
        "reference": "H_References",
        "contract": "L_Contract",
        "training_certificate": "N_Training",
        "professional_registration": "O_Other",
        "nmc_registration": "O_Other",
        "clinical_competency": "N_Training",
        "competency_assessment": "N_Training",
        "hmrc": "K_HMRC",
        "p45": "K_HMRC",
        "ni_number": "K_HMRC"
    }
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Create empty folders
        for folder in folders:
            zf.writestr(f"{folder}/.gitkeep", "")
        
        # Add generated forms
        forms = await db.generated_forms.find(
            {"employee_id": employee_id, "status": {"$in": ["completed", "reviewed", "signed_off"]}},
            {"_id": 0}
        ).to_list(100)
        
        for form in forms:
            folder = form_folder_map.get(form.get("template_name"), "O_Other")
            filename = f"{form.get('template_name', 'Form')}_{form.get('id', 'unknown')[:8]}.json"
            # Save form data as JSON (in production, this would be a PDF)
            form_content = {
                "template_name": form.get("template_name"),
                "employee_name": form.get("employee_name"),
                "status": form.get("status"),
                "form_data": form.get("form_data"),
                "completed_at": form.get("completed_at"),
                "signed_off_at": form.get("signed_off_at")
            }
            import json
            zf.writestr(f"{folder}/{filename}", json.dumps(form_content, indent=2))
        
        # Add uploaded documents
        documents = await db.employee_documents.find(
            {"employee_id": employee_id},
            {"_id": 0}
        ).to_list(100)
        
        for doc in documents:
            folder = doc_folder_map.get(doc.get("document_type"), "O_Other")
            file_url = doc.get("file_url")
            if file_url:
                try:
                    content, content_type = get_object(file_url)
                    ext = ".pdf" if "pdf" in content_type else ".file"
                    filename = doc.get("original_filename") or f"{doc.get('document_type', 'document')}_{doc.get('id', 'unknown')[:8]}{ext}"
                    zf.writestr(f"{folder}/{filename}", content)
                except Exception as e:
                    logger.error(f"Failed to add document to ZIP: {e}")
        
        # Add training records summary
        training = await db.training_records.find(
            {"employee_id": employee_id},
            {"_id": 0}
        ).to_list(100)
        
        if training:
            import json
            training_summary = []
            for t in training:
                training_summary.append({
                    "training_name": t.get("training_name"),
                    "status": t.get("status"),
                    "completed_at": t.get("completed_at"),
                    "expiry_date": t.get("expiry_date"),
                    "provider": t.get("provider")
                })
            zf.writestr("N_Training/_training_summary.json", json.dumps(training_summary, indent=2))
        
        # Add employee summary file
        summary = {
            "employee_code": employee.get("employee_code"),
            "name": f"{employee.get('first_name')} {employee.get('last_name')}",
            "email": employee.get("email"),
            "role": employee.get("role"),
            "onboarding_status": employee.get("onboarding_status"),
            "status": employee.get("status"),
            "start_date": employee.get("start_date"),
            "export_date": datetime.now(timezone.utc).isoformat(),
            "total_forms": len(forms),
            "total_documents": len(documents),
            "total_training": len(training)
        }
        import json
        zf.writestr("_EMPLOYEE_SUMMARY.json", json.dumps(summary, indent=2))
    
    zip_buffer.seek(0)
    
    # Generate filename
    emp_name = f"{employee.get('first_name')}_{employee.get('last_name')}".replace(" ", "_")
    emp_code = employee.get("employee_code", "unknown")
    filename = f"{emp_code}_{emp_name}_File.zip"
    
    await log_audit_action(user['user_id'], "export_employee_file", "employee", employee_id, {
        "filename": filename
    })
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@api_router.get("/employees/{employee_id}/export-compliance-summary")
async def export_compliance_summary(employee_id: str, user: dict = Depends(get_current_user)):
    """Export compliance summary as JSON (can be converted to PDF by frontend)"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    compliance = await calculate_employee_compliance(employee_id, employee.get("role", ""))
    
    # Get training records
    training = await db.training_records.find(
        {"employee_id": employee_id, "status": "completed"},
        {"_id": 0, "training_name": 1, "completed_at": 1, "expiry_date": 1}
    ).to_list(100)
    
    # Get policy acknowledgements
    policies = await db.policy_assignments.find(
        {"employee_id": employee_id, "status": "acknowledged"},
        {"_id": 0, "policy_name": 1, "acknowledged_at": 1}
    ).to_list(100)
    
    # Get verified documents
    verified_docs = await db.employee_documents.find(
        {"employee_id": employee_id, "status": "approved"},
        {"_id": 0, "document_type_name": 1, "uploaded_at": 1, "verified_at": 1}
    ).to_list(100)
    
    # Build compliance summary
    summary = {
        "employee": {
            "name": f"{employee.get('first_name')} {employee.get('last_name')}",
            "employee_id": employee.get("employee_code"),
            "role": employee.get("role"),
            "email": employee.get("email"),
            "onboarding_status": employee.get("onboarding_status"),
            "start_date": employee.get("start_date")
        },
        "compliance_overview": {
            "completion_percentage": compliance["completion_percentage"],
            "verification_percentage": compliance["verification_percentage"],
            "total_mandatory_items": compliance["total_items"],
            "complete_items": compliance["complete_count"],
            "verified_items": compliance["verified_count"],
            "missing_items": compliance["missing_count"],
            "expiring_items": compliance["expiring_count"]
        },
        "mandatory_items_checklist": [
            {
                "item": item["name"],
                "category": item["category"],
                "status": item["status"],
                "verified": item["verified"],
                "expiry_date": item.get("expiry_date")
            }
            for item in compliance["items"]
        ],
        "missing_items": [
            item["name"] for item in compliance["items"] if item["status"] == "missing"
        ],
        "expiring_items": [
            {"item": item["name"], "expiry_date": item.get("expiry_date")}
            for item in compliance["items"] if item["status"] == "expiring"
        ],
        "training_summary": [
            {
                "training": t.get("training_name"),
                "completed": t.get("completed_at"),
                "expires": t.get("expiry_date")
            }
            for t in training
        ],
        "verified_documents": [
            {
                "document": d.get("document_type_name"),
                "uploaded": d.get("uploaded_at"),
                "verified": d.get("verified_at")
            }
            for d in verified_docs
        ],
        "policy_acknowledgements": [
            {
                "policy": p.get("policy_name"),
                "acknowledged": p.get("acknowledged_at")
            }
            for p in policies
        ],
        "export_date": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.get("name", user.get("email"))
    }
    
    await log_audit_action(user['user_id'], "export_compliance_summary", "employee", employee_id, {})
    
    return summary

@api_router.get("/employees/{employee_id}/export-compliance-pdf")
async def export_compliance_pdf(employee_id: str, user: dict = Depends(get_current_user)):
    """Export compliance summary as professional A4 PDF suitable for audits"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    compliance = await calculate_employee_compliance(employee_id, employee.get("role", ""))
    
    # Get training records
    training = await db.training_records.find(
        {"employee_id": employee_id},
        {"_id": 0, "training_name": 1, "status": 1, "completed_at": 1, "expiry_date": 1}
    ).to_list(100)
    
    # Get last audit/review info
    last_audit = await db.audit_logs.find_one(
        {"entity_type": "employee", "entity_id": employee_id, "action": {"$in": ["approve_document", "sign_off_form"]}},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    # Create PDF buffer
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CompanyHeader',
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor('#0D9488'),
        alignment=TA_CENTER,
        spaceAfter=5*mm
    ))
    styles.add(ParagraphStyle(
        name='DocumentTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#1F2937'),
        alignment=TA_CENTER,
        spaceAfter=10*mm
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor('#1F2937'),
        spaceBefore=8*mm,
        spaceAfter=4*mm
    ))
    styles.add(ParagraphStyle(
        name='ComplianceBodyText',
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        spaceAfter=2*mm
    ))
    styles.add(ParagraphStyle(
        name='SmallText',
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
    ))
    styles.add(ParagraphStyle(
        name='ComplianceScore',
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=colors.HexColor('#0D9488'),
        alignment=TA_CENTER,
    ))
    
    elements = []
    
    # Header
    elements.append(Paragraph("Osabea Healthcare Solutions", styles['CompanyHeader']))
    elements.append(Paragraph("Employee Compliance Summary", styles['DocumentTitle']))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E5E7EB')))
    elements.append(Spacer(1, 5*mm))
    
    # Employee Info Table
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
    emp_code = employee.get('employee_code', 'N/A')
    emp_role = employee.get('role', 'N/A')
    emp_status = employee.get('onboarding_status', 'New')
    
    info_data = [
        ['Employee Name:', emp_name, 'Employee ID:', emp_code],
        ['Role:', emp_role, 'Onboarding Status:', emp_status],
        ['Email:', employee.get('email', 'N/A'), 'Start Date:', employee.get('start_date', 'N/A') or 'Not Set'],
    ]
    
    info_table = Table(info_data, colWidths=[35*mm, 55*mm, 35*mm, 45*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 5*mm))
    
    # Compliance Score Box
    score = compliance['completion_percentage']
    verified = compliance['verification_percentage']
    
    score_color = '#10B981' if score >= 80 else '#F59E0B' if score >= 50 else '#EF4444'
    
    score_data = [
        [Paragraph(f"<font color='{score_color}'>{score}%</font>", styles['ComplianceScore'])],
        [Paragraph("Compliance Score", ParagraphStyle('ScoreLabel', fontName='Helvetica', fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor('#6B7280')))],
    ]
    
    score_table = Table(score_data, colWidths=[50*mm])
    score_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F9FAFB')),
        ('TOPPADDING', (0, 0), (-1, -1), 5*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5*mm),
    ]))
    
    stats_data = [
        ['Total Items:', str(compliance['total_items'])],
        ['Complete:', str(compliance['complete_count'])],
        ['Verified:', str(compliance['verified_count'])],
        ['Missing:', str(compliance['missing_count'])],
        ['Expiring:', str(compliance['expiring_count'])],
    ]
    
    stats_table = Table(stats_data, colWidths=[25*mm, 20*mm])
    stats_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    
    overview_layout = Table([[score_table, stats_table]], colWidths=[60*mm, 50*mm])
    overview_layout.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(overview_layout)
    elements.append(Spacer(1, 8*mm))
    
    # Section 1: Mandatory Items Checklist
    elements.append(Paragraph("1. Mandatory Items Checklist", styles['SectionHeader']))
    
    checklist_data = [['Item', 'Category', 'Status']]
    for item in compliance['items']:
        status_symbol = '✔' if item['status'] == 'complete' and item['verified'] else '⏳' if item['status'] == 'complete' else '✖'
        status_text = 'Complete & Verified' if item['status'] == 'complete' and item['verified'] else 'Pending Verification' if item['status'] == 'complete' else 'Expiring' if item['status'] == 'expiring' else 'Missing'
        status_display = f"{status_symbol} {status_text}"
        
        category_short = item['category'].replace('_', ' ').split(' ', 1)[-1] if '_' in item['category'] else item['category']
        checklist_data.append([item['name'], category_short[:20], status_display])
    
    checklist_table = Table(checklist_data, colWidths=[75*mm, 45*mm, 50*mm])
    checklist_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
    ]))
    elements.append(checklist_table)
    elements.append(Spacer(1, 5*mm))
    
    # Section 2: Training Summary
    elements.append(Paragraph("2. Training Summary", styles['SectionHeader']))
    
    completed_training = [t for t in training if t.get('status') == 'completed']
    pending_training = [t for t in training if t.get('status') != 'completed']
    
    # Get required training items from compliance
    required_training = [item for item in compliance['items'] if item['type'] == 'training']
    missing_training = [item['name'] for item in required_training if item['status'] == 'missing']
    
    if completed_training:
        training_data = [['Training', 'Completed', 'Expires']]
        for t in completed_training:
            completed_date = t.get('completed_at', 'N/A')
            if completed_date and completed_date != 'N/A':
                try:
                    completed_date = datetime.fromisoformat(completed_date.replace('Z', '+00:00')).strftime('%d/%m/%Y')
                except:
                    pass
            expiry_date = t.get('expiry_date', 'N/A')
            if expiry_date and expiry_date != 'N/A':
                try:
                    expiry_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00')).strftime('%d/%m/%Y')
                except:
                    pass
            training_data.append([t.get('training_name', 'Unknown'), completed_date, expiry_date])
        
        training_table = Table(training_data, colWidths=[85*mm, 40*mm, 40*mm])
        training_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        elements.append(training_table)
    else:
        elements.append(Paragraph("No completed training records found.", styles['ComplianceBodyText']))
    
    if missing_training:
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(f"<b>Missing Training:</b> {', '.join(missing_training)}", styles['ComplianceBodyText']))
    
    elements.append(Spacer(1, 5*mm))
    
    # Section 3: Missing Items (Clear Action List)
    missing_items = [item['name'] for item in compliance['items'] if item['status'] == 'missing']
    if missing_items:
        elements.append(Paragraph("3. Missing Items - Action Required", styles['SectionHeader']))
        
        missing_data = [['#', 'Item', 'Category']]
        for idx, item in enumerate([i for i in compliance['items'] if i['status'] == 'missing'], 1):
            category_short = item['category'].replace('_', ' ').split(' ', 1)[-1]
            missing_data.append([str(idx), item['name'], category_short])
        
        missing_table = Table(missing_data, colWidths=[10*mm, 100*mm, 55*mm])
        missing_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEF2F2')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFF7ED')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FECACA')),
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        elements.append(missing_table)
        elements.append(Spacer(1, 5*mm))
    
    # Section 4: Verification
    elements.append(Paragraph("4. Verification", styles['SectionHeader']))
    
    verified_by = user.get('name', user.get('email', 'System'))
    last_review = last_audit.get('created_at', None) if last_audit else None
    if last_review:
        try:
            last_review = datetime.fromisoformat(last_review.replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
        except:
            last_review = 'N/A'
    else:
        last_review = 'N/A'
    
    export_date = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')
    
    verification_data = [
        ['Generated By:', verified_by],
        ['Export Date:', export_date],
        ['Last Review Activity:', last_review],
        ['Verification Rate:', f"{verified}/{compliance['total_items']} items ({compliance['verification_percentage']}%)"],
    ]
    
    verification_table = Table(verification_data, colWidths=[45*mm, 120*mm])
    verification_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(verification_table)
    
    # Footer
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E5E7EB')))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        f"This document was generated by Osabea Healthcare Solutions Compliance Portal on {export_date}. "
        "For audit and compliance purposes only.",
        styles['SmallText']
    ))
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    
    # Generate filename
    emp_name_safe = f"{employee.get('first_name', '')}_{employee.get('last_name', '')}".replace(" ", "_")
    filename = f"{employee.get('employee_code', 'EMP')}_Compliance_Summary_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    await log_audit_action(user['user_id'], "export_compliance_pdf", "employee", employee_id, {
        "filename": filename
    })
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf"
        }
    )

# ==================== DOCUMENT TYPE ROUTES ====================

@api_router.post("/document-types", response_model=DocumentTypeResponse)
async def create_document_type(doc_type: DocumentTypeCreate, user: dict = Depends(require_admin)):
    doc_id = str(uuid.uuid4())
    doc = {"id": doc_id, **doc_type.model_dump()}
    await db.document_types.insert_one(doc)
    return DocumentTypeResponse(**doc)

@api_router.get("/document-types", response_model=List[DocumentTypeResponse])
async def get_document_types(category: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    docs = await db.document_types.find(query, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return [DocumentTypeResponse(**d) for d in docs]

@api_router.put("/document-types/{doc_type_id}", response_model=DocumentTypeResponse)
async def update_document_type(doc_type_id: str, update: DocumentTypeCreate, user: dict = Depends(require_admin)):
    result = await db.document_types.update_one({"id": doc_type_id}, {"$set": update.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document type not found")
    doc = await db.document_types.find_one({"id": doc_type_id}, {"_id": 0})
    return DocumentTypeResponse(**doc)

@api_router.delete("/document-types/{doc_type_id}")
async def delete_document_type(doc_type_id: str, user: dict = Depends(require_admin)):
    result = await db.document_types.delete_one({"id": doc_type_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document type not found")
    return {"message": "Document type deleted"}


# ==================== UNIFIED EVIDENCE MANAGEMENT ====================
# Evidence-based compliance system - all evidence flows through these endpoints

class EvidenceFileResponse(BaseModel):
    """Single evidence file within a requirement"""
    file_id: str
    file_url: str
    original_filename: str
    uploaded_at: str
    uploaded_by: Optional[str] = None
    uploaded_by_name: Optional[str] = None
    file_label: Optional[str] = None
    source_type: str  # "manual_upload", "form_submission", "imported", "replacement"
    content_type: Optional[str] = None
    # Status for soft-delete/replace
    status: Optional[str] = "active"  # active, superseded, removed
    # Metadata
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    # Removal info
    removed_at: Optional[str] = None
    removed_by: Optional[str] = None
    removed_by_name: Optional[str] = None
    removal_reason: Optional[str] = None
    # Supersede info
    superseded_at: Optional[str] = None
    superseded_by: Optional[str] = None
    superseded_by_name: Optional[str] = None
    superseded_by_file_id: Optional[str] = None
    supersede_reason: Optional[str] = None
    replaces_file_id: Optional[str] = None


class RequirementEvidenceResponse(BaseModel):
    """Complete evidence status for a requirement"""
    requirement_id: str
    requirement_name: str
    requirement_type: str  # document, form-generated, training
    category: str
    source: Optional[str] = None  # employee, internal, form
    description: Optional[str] = None
    allow_multiple_files: bool = True
    
    # Evidence files
    evidence_files: List[EvidenceFileResponse] = []
    has_evidence: bool = False
    evidence_count: int = 0
    
    # Status
    status: str  # missing, in_progress, completed, completed_no_evidence
    completed_at: Optional[str] = None
    
    # Verification (only valid when has_evidence=True)
    verified: bool = False
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    can_verify: bool = False  # True only when evidence exists
    
    # Form linkage
    linked_form_id: Optional[str] = None
    linked_form_status: Optional[str] = None
    
    # Training specific
    training_expiry_date: Optional[str] = None
    training_completion_method: Optional[str] = None  # certificate, manual


@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/evidence")
async def upload_requirement_evidence(
    employee_id: str,
    requirement_id: str,
    file: UploadFile = File(...),
    file_label: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Upload evidence file for any requirement type.
    Supports multi-file: adds to existing evidence rather than replacing.
    """
    logger.info(f"Upload started: employee={employee_id}, requirement={requirement_id}, file={file.filename}, size={file.size if hasattr(file, 'size') else 'unknown'}")
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        logger.error(f"Upload failed: Employee not found {employee_id}")
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get requirement definition
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        logger.error(f"Upload failed: Invalid requirement_id {requirement_id}")
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    now = datetime.now(timezone.utc).isoformat()
    req_type = requirement.get('type', 'document')
    
    # Upload file to storage
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    employee_name = f"{employee['first_name']}{employee['last_name']}"
    req_slug = requirement_id.replace('_', '-')
    storage_filename = f"{employee_name}_{req_slug}_{uuid.uuid4().hex[:8]}.{ext}"
    path = f"{APP_NAME}/evidence/{employee_id}/{requirement_id}/{storage_filename}"
    
    try:
        data = await file.read()
        logger.info(f"Uploading to storage: path={path}, size={len(data)} bytes, type={file.content_type}")
        result = put_object(path, data, file.content_type or "application/octet-stream")
        logger.info(f"Storage upload successful: {result}")
    except Exception as e:
        logger.error(f"Storage upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    # Get user name
    user_doc = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    uploaded_by_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    # Create evidence file record
    file_id = str(uuid.uuid4())
    evidence_file = {
        "file_id": file_id,
        "file_url": result["path"],
        "original_filename": file.filename,
        "uploaded_at": now,
        "uploaded_by": user['user_id'],
        "uploaded_by_name": uploaded_by_name,
        "file_label": file_label or requirement['name'],
        "source_type": "manual_upload",
        "content_type": file.content_type,
        "status": "active",  # active, superseded, removed
        "issue_date": None,
        "expiry_date": expiry_date,
        "notes": None
    }
    
    # Handle based on requirement type
    if req_type == 'training':
        # For training, update training_records collection
        training_name = requirement.get('training_name', requirement['name'])
        
        # Find or create training record
        existing = await db.training_records.find_one({
            "employee_id": employee_id,
            "$or": [
                {"requirement_id": requirement_id},
                {"training_name": {"$regex": training_name, "$options": "i"}}
            ]
        }, {"_id": 0})
        
        if existing:
            # Add to existing evidence files
            evidence_files = existing.get('evidence_files', [])
            # Migrate old certificate_url to evidence_files if needed
            if existing.get('certificate_url') and not evidence_files:
                evidence_files.append({
                    "file_id": str(uuid.uuid4()),
                    "file_url": existing['certificate_url'],
                    "original_filename": existing.get('original_filename', 'certificate'),
                    "uploaded_at": existing.get('uploaded_at', existing.get('created_at')),
                    "source_type": "migrated"
                })
            evidence_files.append(evidence_file)
            
            await db.training_records.update_one(
                {"id": existing['id']},
                {"$set": {
                    "evidence_files": evidence_files,
                    "certificate_url": result["path"],  # Keep for backward compat
                    "original_filename": file.filename,
                    "uploaded_at": now,
                    "status": "completed",
                    "completion_date": now,
                    "completion_method": "certificate",
                    "requirement_id": requirement_id,
                    "updated_at": now,
                    "expiry_date": expiry_date
                }}
            )
            record_id = existing['id']
        else:
            # Create new training record
            record_id = str(uuid.uuid4())
            new_record = {
                "id": record_id,
                "employee_id": employee_id,
                "training_name": training_name,
                "mandatory": True,
                "status": "completed",
                "completion_date": now,
                "expiry_date": expiry_date,
                "certificate_url": result["path"],
                "original_filename": file.filename,
                "uploaded_at": now,
                "evidence_files": [evidence_file],
                "verified": False,
                "completion_method": "certificate",
                "requirement_id": requirement_id,
                "created_at": now
            }
            await db.training_records.insert_one(new_record)
        
        await log_audit_action(user['user_id'], "upload_evidence", "training_record", record_id, 
                               {"requirement_id": requirement_id, "filename": file.filename})
    
    else:
        # For documents/form-generated, create/update employee_documents
        # Check for existing document for this requirement
        existing = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id
        }, {"_id": 0})
        
        if existing:
            # Add to existing evidence files
            evidence_files = existing.get('evidence_files', [])
            # Migrate old file_url to evidence_files if needed
            if existing.get('file_url') and not evidence_files:
                evidence_files.append({
                    "file_id": str(uuid.uuid4()),
                    "file_url": existing['file_url'],
                    "original_filename": existing.get('original_filename', 'document'),
                    "uploaded_at": existing.get('uploaded_at', existing.get('created_at')),
                    "source_type": "migrated"
                })
            evidence_files.append(evidence_file)
            
            await db.employee_documents.update_one(
                {"id": existing['id']},
                {"$set": {
                    "evidence_files": evidence_files,
                    "file_url": result["path"],  # Keep latest for backward compat
                    "original_filename": file.filename,
                    "uploaded_at": now,
                    "status": "uploaded",
                    "updated_at": now,
                    "expiry_date": expiry_date
                }}
            )
            doc_id = existing['id']
        else:
            # Create new document
            doc_id = str(uuid.uuid4())
            # Find or create appropriate document type
            doc_type = await db.document_types.find_one({"name": requirement['name']}, {"_id": 0})
            doc_type_id = doc_type['id'] if doc_type else requirement_id
            
            new_doc = {
                "id": doc_id,
                "employee_id": employee_id,
                "document_type_id": doc_type_id,
                "document_type_name": requirement['name'],
                "category": requirement.get('category'),
                "file_url": result["path"],
                "original_filename": file.filename,
                "status": "uploaded",
                "uploaded_by": user['user_id'],
                "uploaded_at": now,
                "expiry_date": expiry_date,
                "verified": False,
                "requirement_id": requirement_id,
                "requirement_name": requirement['name'],
                "document_label": file_label or requirement['name'],
                "evidence_files": [evidence_file],
                "source_type": "manual_upload",
                "created_at": now
            }
            await db.employee_documents.insert_one(new_doc)
        
        await log_audit_action(user['user_id'], "upload_evidence", "employee_document", doc_id,
                               {"requirement_id": requirement_id, "filename": file.filename})
    
    # Update employee compliance
    await update_employee_compliance(employee_id)
    
    logger.info(f"Upload completed successfully: employee={employee_id}, requirement={requirement_id}, file_id={file_id}")
    
    return {
        "success": True,
        "message": f"Evidence uploaded for '{requirement['name']}'",
        "file_id": file_id,
        "requirement_id": requirement_id,
        "file_url": result["path"]
    }


@api_router.get("/employees/{employee_id}/requirements/{requirement_id}/evidence")
async def get_requirement_evidence(
    employee_id: str,
    requirement_id: str,
    user: dict = Depends(get_current_user)
):
    """Get all evidence files for a specific requirement"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    req_type = requirement.get('type', 'document')
    evidence_files = []
    status = "missing"
    verified = False
    verified_by = None
    verified_at = None
    linked_form_id = None
    linked_form_status = None
    training_expiry = None
    training_method = None
    completed_at = None
    
    if req_type == 'training':
        training_name = requirement.get('training_name', requirement['name'])
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "$or": [
                {"requirement_id": requirement_id},
                {"training_name": {"$regex": training_name, "$options": "i"}}
            ]
        }, {"_id": 0})
        
        if record:
            evidence_files = record.get('evidence_files', [])
            # Backward compat: include certificate_url if no evidence_files
            if not evidence_files and record.get('certificate_url'):
                evidence_files = [{
                    "file_id": record['id'],
                    "file_url": record['certificate_url'],
                    "original_filename": record.get('original_filename', 'certificate'),
                    "uploaded_at": record.get('uploaded_at', record.get('created_at')),
                    "source_type": "certificate"
                }]
            
            status = record.get('status', 'completed') if evidence_files else "completed_no_evidence"
            verified = record.get('verified', False)
            verified_by = record.get('verified_by')
            verified_at = record.get('verified_at')
            training_expiry = record.get('expiry_date')
            training_method = record.get('completion_method')
            completed_at = record.get('completion_date')
    else:
        # Check documents
        # Build query with legacy mapping support
        legacy_mapping = {
            "dbs_certificate": ["dbs", "dbs_certificate"],
            "identity_documents": ["identity_rtw", "identity_documents"],
            "right_to_work_documents": ["identity_rtw", "right_to_work_documents"],
        }
        
        req_ids_to_search = legacy_mapping.get(requirement_id, [requirement_id])
        if isinstance(req_ids_to_search, str):
            req_ids_to_search = [req_ids_to_search]
        
        docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": {"$in": req_ids_to_search}
        }, {"_id": 0}).to_list(100)
        
        for doc in docs:
            doc_files = doc.get('evidence_files', [])
            if not doc_files and doc.get('file_url'):
                doc_files = [{
                    "file_id": doc['id'],
                    "file_url": doc['file_url'],
                    "original_filename": doc.get('original_filename', 'document'),
                    "uploaded_at": doc.get('uploaded_at', doc.get('created_at')),
                    "uploaded_by_name": doc.get('uploaded_by_name'),
                    "file_label": doc.get('document_label'),
                    "source_type": doc.get('source_type', 'manual_upload')
                }]
            evidence_files.extend(doc_files)
            
            if doc.get('verified'):
                verified = True
                verified_by = doc.get('verified_by') or doc.get('verified_by_name')
                verified_at = doc.get('verified_at')
            
            completed_at = completed_at or doc.get('uploaded_at')
        
        # Check for linked forms
        if requirement.get('type') == 'form-generated':
            template_name = requirement.get('template_name')
            if template_name:
                form = await db.generated_forms.find_one({
                    "employee_id": employee_id,
                    "template_name": {"$regex": template_name, "$options": "i"}
                }, {"_id": 0})
                
                if form:
                    linked_form_id = form['id']
                    linked_form_status = form.get('status')
                    
                    # If form is completed and has PDF, add to evidence
                    if form.get('status') in ['completed', 'completed_imported'] and form.get('pdf_url'):
                        evidence_files.append({
                            "file_id": form['id'],
                            "file_url": form['pdf_url'],
                            "original_filename": f"{template_name}.pdf",
                            "uploaded_at": form.get('completed_at', form.get('updated_at')),
                            "source_type": "form_submission",
                            "file_label": f"Completed {template_name}"
                        })
        
        if evidence_files:
            status = "completed"
        elif linked_form_id and linked_form_status in ['draft', 'in_progress']:
            status = "in_progress"
    
    # Separate active files from all files (for history)
    all_evidence_files = evidence_files.copy()
    active_evidence_files = [f for f in evidence_files if f.get('status', 'active') == 'active']
    
    # Only active files count for compliance
    has_evidence = len(active_evidence_files) > 0
    
    # If no active evidence, reset status
    if not has_evidence and status == "completed":
        status = "missing"
    
    return RequirementEvidenceResponse(
        requirement_id=requirement_id,
        requirement_name=requirement['name'],
        requirement_type=requirement.get('type', 'document'),
        category=requirement.get('category', ''),
        source=requirement.get('source'),
        description=requirement.get('description'),
        allow_multiple_files=requirement.get('allow_multiple_files', True),
        evidence_files=all_evidence_files,  # Return all files including removed/superseded for history
        has_evidence=has_evidence,  # Only true if active files exist
        evidence_count=len(active_evidence_files),  # Only count active files
        status=status,
        completed_at=completed_at,
        verified=verified and has_evidence,
        verified_at=verified_at if has_evidence else None,
        verified_by=verified_by if has_evidence else None,
        can_verify=has_evidence and not verified,
        linked_form_id=linked_form_id,
        linked_form_status=linked_form_status,
        training_expiry_date=training_expiry,
        training_completion_method=training_method
    )


@api_router.delete("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}")
async def delete_requirement_evidence(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Remove a specific evidence file from a requirement"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    req_type = requirement.get('type', 'document')
    now = datetime.now(timezone.utc).isoformat()
    
    if req_type == 'training':
        # Find and update training record
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "$or": [
                {"requirement_id": requirement_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if record:
            evidence_files = [f for f in record.get('evidence_files', []) if f.get('file_id') != file_id]
            update_data = {"evidence_files": evidence_files, "updated_at": now}
            
            # If no more evidence, update status
            if not evidence_files:
                update_data["certificate_url"] = None
                update_data["completion_method"] = "manual"
                update_data["verified"] = False
            
            await db.training_records.update_one(
                {"id": record['id']},
                {"$set": update_data}
            )
    else:
        # Find and update document
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "$or": [
                {"id": file_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if doc:
            evidence_files = [f for f in doc.get('evidence_files', []) if f.get('file_id') != file_id]
            
            if not evidence_files and doc['id'] == file_id:
                # Delete the entire document record
                await db.employee_documents.delete_one({"id": file_id})
            else:
                # Just remove the file from evidence_files
                update_data = {"evidence_files": evidence_files, "updated_at": now}
                if not evidence_files:
                    update_data["verified"] = False
                await db.employee_documents.update_one(
                    {"id": doc['id']},
                    {"$set": update_data}
                )
    
    await log_audit_action(user['user_id'], "delete_evidence", "requirement", requirement_id,
                           {"file_id": file_id, "employee_id": employee_id})
    
    # Update compliance
    await update_employee_compliance(employee_id)
    
    return {"success": True, "message": "Evidence file removed"}


class RemoveFileRequest(BaseModel):
    reason: str  # Required reason for removing file


class ReplaceFileRequest(BaseModel):
    reason: str  # Required reason for replacing file


@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}/remove")
async def remove_requirement_evidence_soft(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    request: RemoveFileRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Soft-remove an evidence file (mark as 'removed', don't delete).
    Requires a reason for audit trail. File remains in history.
    """
    if not request.reason or len(request.reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 3 characters)")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    req_type = requirement.get('type', 'document')
    now = datetime.now(timezone.utc).isoformat()
    
    # Get user name for audit
    user_doc = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    file_found = False
    original_file = None
    
    if req_type == 'training':
        # Find training record
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "$or": [
                {"requirement_id": requirement_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if record:
            evidence_files = record.get('evidence_files', [])
            for f in evidence_files:
                if f.get('file_id') == file_id:
                    original_file = f.copy()
                    f['status'] = 'removed'
                    f['removed_at'] = now
                    f['removed_by'] = user['user_id']
                    f['removed_by_name'] = user_name
                    f['removal_reason'] = request.reason.strip()
                    file_found = True
                    break
            
            if file_found:
                # Check if any active files remain
                active_files = [f for f in evidence_files if f.get('status', 'active') == 'active']
                update_data = {"evidence_files": evidence_files, "updated_at": now}
                
                if not active_files:
                    update_data["verified"] = False
                    update_data["completion_method"] = "manual"
                
                await db.training_records.update_one(
                    {"id": record['id']},
                    {"$set": update_data}
                )
    else:
        # Find document
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "$or": [
                {"id": file_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if doc:
            evidence_files = doc.get('evidence_files', [])
            for f in evidence_files:
                if f.get('file_id') == file_id:
                    original_file = f.copy()
                    f['status'] = 'removed'
                    f['removed_at'] = now
                    f['removed_by'] = user['user_id']
                    f['removed_by_name'] = user_name
                    f['removal_reason'] = request.reason.strip()
                    file_found = True
                    break
            
            if file_found:
                active_files = [f for f in evidence_files if f.get('status', 'active') == 'active']
                update_data = {"evidence_files": evidence_files, "updated_at": now}
                
                if not active_files:
                    update_data["verified"] = False
                    update_data["status"] = "not_started"
                
                await db.employee_documents.update_one(
                    {"id": doc['id']},
                    {"$set": update_data}
                )
    
    if not file_found:
        raise HTTPException(status_code=404, detail="Evidence file not found")
    
    # Create detailed audit log entry
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action_type": "remove_evidence",
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "file_id": file_id,
        "user_id": user['user_id'],
        "user_name": user_name,
        "reason": request.reason.strip(),
        "original_file": original_file,
        "timestamp": now
    })
    
    # Update compliance
    await update_employee_compliance(employee_id)
    
    return {
        "success": True, 
        "message": "File marked as removed",
        "file_id": file_id,
        "status": "removed"
    }


@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}/replace")
async def replace_requirement_evidence(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    file: UploadFile = File(...),
    reason: str = Form(...),
    file_label: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Replace an evidence file with a new one.
    Old file is marked as 'superseded', new file becomes active.
    Requires a reason for audit trail.
    """
    if not reason or len(reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 3 characters)")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    req_type = requirement.get('type', 'document')
    now = datetime.now(timezone.utc).isoformat()
    
    # Get user name
    user_doc = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    # Upload new file
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    employee_name = f"{employee['first_name']}{employee['last_name']}"
    req_slug = requirement_id.replace('_', '-')
    storage_filename = f"{employee_name}_{req_slug}_{uuid.uuid4().hex[:8]}.{ext}"
    path = f"{APP_NAME}/evidence/{employee_id}/{requirement_id}/{storage_filename}"
    
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    
    # Create new evidence file record
    new_file_id = str(uuid.uuid4())
    new_evidence_file = {
        "file_id": new_file_id,
        "file_url": result["path"],
        "original_filename": file.filename,
        "uploaded_at": now,
        "uploaded_by": user['user_id'],
        "uploaded_by_name": user_name,
        "file_label": file_label or requirement['name'],
        "source_type": "replacement",
        "content_type": file.content_type,
        "status": "active",
        "issue_date": None,
        "expiry_date": expiry_date,
        "notes": None,
        "replaces_file_id": file_id  # Reference to superseded file
    }
    
    file_found = False
    original_file = None
    
    if req_type == 'training':
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "$or": [
                {"requirement_id": requirement_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if record:
            evidence_files = record.get('evidence_files', [])
            for f in evidence_files:
                if f.get('file_id') == file_id:
                    original_file = f.copy()
                    f['status'] = 'superseded'
                    f['superseded_at'] = now
                    f['superseded_by'] = user['user_id']
                    f['superseded_by_name'] = user_name
                    f['superseded_by_file_id'] = new_file_id
                    f['supersede_reason'] = reason.strip()
                    file_found = True
                    break
            
            if file_found:
                evidence_files.append(new_evidence_file)
                await db.training_records.update_one(
                    {"id": record['id']},
                    {"$set": {
                        "evidence_files": evidence_files,
                        "updated_at": now,
                        "certificate_url": result["path"],
                        "original_filename": file.filename
                    }}
                )
    else:
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "$or": [
                {"id": file_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if doc:
            evidence_files = doc.get('evidence_files', [])
            for f in evidence_files:
                if f.get('file_id') == file_id:
                    original_file = f.copy()
                    f['status'] = 'superseded'
                    f['superseded_at'] = now
                    f['superseded_by'] = user['user_id']
                    f['superseded_by_name'] = user_name
                    f['superseded_by_file_id'] = new_file_id
                    f['supersede_reason'] = reason.strip()
                    file_found = True
                    break
            
            if file_found:
                evidence_files.append(new_evidence_file)
                await db.employee_documents.update_one(
                    {"id": doc['id']},
                    {"$set": {
                        "evidence_files": evidence_files,
                        "updated_at": now,
                        "file_url": result["path"],
                        "original_filename": file.filename
                    }}
                )
    
    if not file_found:
        raise HTTPException(status_code=404, detail="Evidence file not found")
    
    # Create detailed audit log entry
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action_type": "replace_evidence",
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "old_file_id": file_id,
        "new_file_id": new_file_id,
        "user_id": user['user_id'],
        "user_name": user_name,
        "reason": reason.strip(),
        "original_file": original_file,
        "new_file": new_evidence_file,
        "timestamp": now
    })
    
    # Update compliance
    await update_employee_compliance(employee_id)
    
    return {
        "success": True,
        "message": "File replaced successfully",
        "old_file_id": file_id,
        "new_file_id": new_file_id,
        "new_file_url": result["path"]
    }


@api_router.get("/employees/{employee_id}/requirements/{requirement_id}/history")
async def get_requirement_history(
    employee_id: str,
    requirement_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get full history of all file operations for a requirement.
    Includes uploads, replacements, removals, edits, and verifications.
    """
    # Get all audit logs for this requirement
    audit_logs = await db.audit_logs.find({
        "employee_id": employee_id,
        "requirement_id": requirement_id
    }, {"_id": 0}).sort("timestamp", -1).to_list(100)
    
    # Also get file history from audit_logs collection for edits
    edit_logs = await db.audit_logs.find({
        "employee_id": employee_id,
        "$or": [
            {"requirement_id": requirement_id},
            {"entity_id": requirement_id}
        ]
    }, {"_id": 0}).sort("timestamp", -1).to_list(100)
    
    # Combine and dedupe
    all_logs = {log.get('id', str(i)): log for i, log in enumerate(audit_logs + edit_logs)}
    combined = sorted(all_logs.values(), key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Format for display
    history = []
    for log in combined:
        entry = {
            "id": log.get('id'),
            "action": log.get('action_type') or log.get('action'),
            "timestamp": log.get('timestamp') or log.get('created_at'),
            "user_id": log.get('user_id'),
            "user_name": log.get('user_name'),
            "reason": log.get('reason'),
            "details": {}
        }
        
        if log.get('action_type') == 'replace_evidence':
            entry['details'] = {
                "old_file_id": log.get('old_file_id'),
                "new_file_id": log.get('new_file_id'),
                "old_filename": log.get('original_file', {}).get('original_filename'),
                "new_filename": log.get('new_file', {}).get('original_filename')
            }
        elif log.get('action_type') == 'remove_evidence':
            entry['details'] = {
                "file_id": log.get('file_id'),
                "filename": log.get('original_file', {}).get('original_filename')
            }
        elif log.get('action_type') == 'edit_evidence':
            entry['details'] = {
                "field": log.get('field_changed'),
                "old_value": log.get('old_value'),
                "new_value": log.get('new_value')
            }
        elif log.get('details'):
            entry['details'] = log.get('details')
        
        history.append(entry)
    
    return {
        "requirement_id": requirement_id,
        "employee_id": employee_id,
        "history": history
    }


@api_router.get("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}/view")
async def view_requirement_evidence(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """View/stream a specific evidence file"""
    # Find the file URL
    file_url = None
    
    # Check training records
    record = await db.training_records.find_one({
        "employee_id": employee_id,
        "$or": [
            {"requirement_id": requirement_id},
            {"id": file_id},
            {"evidence_files.file_id": file_id}
        ]
    }, {"_id": 0})
    
    if record:
        for f in record.get('evidence_files', []):
            if f.get('file_id') == file_id:
                file_url = f.get('file_url')
                break
        if not file_url and record.get('certificate_url'):
            file_url = record['certificate_url']
    
    if not file_url:
        # Check documents
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "$or": [
                {"id": file_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if doc:
            for f in doc.get('evidence_files', []):
                if f.get('file_id') == file_id:
                    file_url = f.get('file_url')
                    break
            if not file_url and doc.get('file_url'):
                file_url = doc['file_url']
    
    if not file_url:
        # Check generated forms
        form = await db.generated_forms.find_one({"id": file_id}, {"_id": 0})
        if form and form.get('pdf_url'):
            file_url = form['pdf_url']
    
    if not file_url:
        raise HTTPException(status_code=404, detail="Evidence file not found")
    
    try:
        file_bytes, stored_content_type = get_object(file_url)
        ext = file_url.split('.')[-1].lower()
        content_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        content_type = stored_content_type or content_types.get(ext, 'application/octet-stream')
        return Response(content=file_bytes, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file: {str(e)}")


@api_router.get("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}/download")
async def download_requirement_evidence(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """Download a specific evidence file"""
    # Find the file
    file_url = None
    original_filename = "evidence"
    
    # Check training records
    record = await db.training_records.find_one({
        "employee_id": employee_id,
        "$or": [
            {"requirement_id": requirement_id},
            {"id": file_id},
            {"evidence_files.file_id": file_id}
        ]
    }, {"_id": 0})
    
    if record:
        for f in record.get('evidence_files', []):
            if f.get('file_id') == file_id:
                file_url = f.get('file_url')
                original_filename = f.get('original_filename', 'evidence')
                break
        if not file_url and record.get('certificate_url'):
            file_url = record['certificate_url']
            original_filename = record.get('original_filename', 'certificate')
    
    if not file_url:
        # Check documents
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "$or": [
                {"id": file_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if doc:
            for f in doc.get('evidence_files', []):
                if f.get('file_id') == file_id:
                    file_url = f.get('file_url')
                    original_filename = f.get('original_filename', 'document')
                    break
            if not file_url and doc.get('file_url'):
                file_url = doc['file_url']
                original_filename = doc.get('original_filename', 'document')
    
    if not file_url:
        raise HTTPException(status_code=404, detail="Evidence file not found")
    
    try:
        file_bytes, _ = get_object(file_url)
        return Response(
            content=file_bytes,
            media_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={original_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


# ==================== EVIDENCE EDITING WITH AUDIT TRAIL ====================

class EvidenceEditRequest(BaseModel):
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    file_label: Optional[str] = None
    reason: str  # Required - reason for change

class EvidenceEditLog(BaseModel):
    id: str
    employee_id: str
    requirement_id: str
    file_id: str
    field_changed: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: str
    changed_by_name: str
    changed_at: str
    reason: str

@api_router.put("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}")
async def edit_evidence_metadata(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    edit_request: EvidenceEditRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Edit metadata for a specific evidence file (issue_date, expiry_date, notes, label).
    Creates an immutable audit log entry for every change.
    Does NOT replace the underlying file.
    """
    if not edit_request.reason or len(edit_request.reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="A reason for the change is required (min 3 characters)")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    user_doc = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    now = datetime.now(timezone.utc).isoformat()
    changes_made = []
    was_verified = False
    
    # Try to find and update in training records
    record = await db.training_records.find_one({
        "employee_id": employee_id,
        "$or": [
            {"requirement_id": requirement_id},
            {"id": file_id},
            {"evidence_files.file_id": file_id}
        ]
    }, {"_id": 0})
    
    if record:
        was_verified = record.get('verified', False)
        evidence_files = record.get('evidence_files', [])
        file_index = next((i for i, f in enumerate(evidence_files) if f.get('file_id') == file_id), None)
        
        if file_index is not None:
            file_data = evidence_files[file_index]
            
            # Track changes and update
            if edit_request.issue_date is not None and edit_request.issue_date != file_data.get('issue_date'):
                changes_made.append({
                    "field": "issue_date",
                    "old": file_data.get('issue_date'),
                    "new": edit_request.issue_date
                })
                evidence_files[file_index]['issue_date'] = edit_request.issue_date
            
            if edit_request.expiry_date is not None and edit_request.expiry_date != file_data.get('expiry_date'):
                changes_made.append({
                    "field": "expiry_date",
                    "old": file_data.get('expiry_date'),
                    "new": edit_request.expiry_date
                })
                evidence_files[file_index]['expiry_date'] = edit_request.expiry_date
            
            if edit_request.notes is not None and edit_request.notes != file_data.get('notes'):
                changes_made.append({
                    "field": "notes",
                    "old": file_data.get('notes'),
                    "new": edit_request.notes
                })
                evidence_files[file_index]['notes'] = edit_request.notes
            
            if edit_request.file_label is not None and edit_request.file_label != file_data.get('file_label'):
                changes_made.append({
                    "field": "file_label",
                    "old": file_data.get('file_label'),
                    "new": edit_request.file_label
                })
                evidence_files[file_index]['file_label'] = edit_request.file_label
            
            evidence_files[file_index]['last_edited_at'] = now
            evidence_files[file_index]['last_edited_by'] = user_name
            
            # Update training record
            update_data = {
                "evidence_files": evidence_files,
                "updated_at": now
            }
            
            # Also update top-level expiry if changed
            if edit_request.expiry_date is not None:
                update_data["expiry_date"] = edit_request.expiry_date
            
            # Flag if edited after verification
            if was_verified and changes_made:
                update_data["edited_after_approval"] = True
                update_data["edited_after_approval_at"] = now
            
            await db.training_records.update_one(
                {"id": record['id']},
                {"$set": update_data}
            )
    else:
        # Try documents
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "$or": [
                {"id": file_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if doc:
            was_verified = doc.get('verified', False) or doc.get('status') == 'approved'
            evidence_files = doc.get('evidence_files', [])
            file_index = next((i for i, f in enumerate(evidence_files) if f.get('file_id') == file_id), None)
            
            if file_index is not None:
                file_data = evidence_files[file_index]
                
                # Track changes and update
                if edit_request.issue_date is not None and edit_request.issue_date != file_data.get('issue_date'):
                    changes_made.append({
                        "field": "issue_date",
                        "old": file_data.get('issue_date'),
                        "new": edit_request.issue_date
                    })
                    evidence_files[file_index]['issue_date'] = edit_request.issue_date
                
                if edit_request.expiry_date is not None and edit_request.expiry_date != file_data.get('expiry_date'):
                    changes_made.append({
                        "field": "expiry_date",
                        "old": file_data.get('expiry_date'),
                        "new": edit_request.expiry_date
                    })
                    evidence_files[file_index]['expiry_date'] = edit_request.expiry_date
                
                if edit_request.notes is not None and edit_request.notes != file_data.get('notes'):
                    changes_made.append({
                        "field": "notes",
                        "old": file_data.get('notes'),
                        "new": edit_request.notes
                    })
                    evidence_files[file_index]['notes'] = edit_request.notes
                
                if edit_request.file_label is not None and edit_request.file_label != file_data.get('file_label'):
                    changes_made.append({
                        "field": "file_label",
                        "old": file_data.get('file_label'),
                        "new": edit_request.file_label
                    })
                    evidence_files[file_index]['file_label'] = edit_request.file_label
                
                evidence_files[file_index]['last_edited_at'] = now
                evidence_files[file_index]['last_edited_by'] = user_name
                
                update_data = {
                    "evidence_files": evidence_files,
                    "updated_at": now
                }
                
                # Also update top-level fields
                if edit_request.expiry_date is not None:
                    update_data["expiry_date"] = edit_request.expiry_date
                if edit_request.issue_date is not None:
                    update_data["issue_date"] = edit_request.issue_date
                
                # Flag if edited after verification
                if was_verified and changes_made:
                    update_data["edited_after_approval"] = True
                    update_data["edited_after_approval_at"] = now
                
                await db.employee_documents.update_one(
                    {"id": doc['id']},
                    {"$set": update_data}
                )
            else:
                # Single file document (no evidence_files array)
                if edit_request.issue_date is not None and edit_request.issue_date != doc.get('issue_date'):
                    changes_made.append({
                        "field": "issue_date",
                        "old": doc.get('issue_date'),
                        "new": edit_request.issue_date
                    })
                
                if edit_request.expiry_date is not None and edit_request.expiry_date != doc.get('expiry_date'):
                    changes_made.append({
                        "field": "expiry_date",
                        "old": doc.get('expiry_date'),
                        "new": edit_request.expiry_date
                    })
                
                if edit_request.notes is not None and edit_request.notes != doc.get('notes'):
                    changes_made.append({
                        "field": "notes",
                        "old": doc.get('notes'),
                        "new": edit_request.notes
                    })
                
                update_data = {"updated_at": now}
                if edit_request.issue_date is not None:
                    update_data["issue_date"] = edit_request.issue_date
                if edit_request.expiry_date is not None:
                    update_data["expiry_date"] = edit_request.expiry_date
                if edit_request.notes is not None:
                    update_data["notes"] = edit_request.notes
                
                # Flag if edited after verification
                if was_verified and changes_made:
                    update_data["edited_after_approval"] = True
                    update_data["edited_after_approval_at"] = now
                
                await db.employee_documents.update_one(
                    {"id": doc['id']},
                    {"$set": update_data}
                )
    
    if not changes_made:
        return {"success": True, "message": "No changes detected", "changes": []}
    
    # Create audit log entries for each change
    for change in changes_made:
        log_entry = {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "file_id": file_id,
            "field_changed": change["field"],
            "old_value": change["old"],
            "new_value": change["new"],
            "changed_by": user['user_id'],
            "changed_by_name": user_name,
            "changed_at": now,
            "reason": edit_request.reason,
            "was_verified_before_edit": was_verified
        }
        await db.evidence_edit_logs.insert_one(log_entry)
    
    # Also add to main audit log
    await log_audit_action(
        user['user_id'],
        "edit_evidence_metadata",
        "evidence",
        file_id,
        {
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "changes": changes_made,
            "reason": edit_request.reason,
            "was_verified": was_verified
        }
    )
    
    return {
        "success": True,
        "message": f"Updated {len(changes_made)} field(s)",
        "changes": changes_made,
        "edited_after_approval": was_verified
    }


@api_router.get("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}/history")
async def get_evidence_edit_history(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """Get edit history for a specific evidence file"""
    logs = await db.evidence_edit_logs.find(
        {
            "employee_id": employee_id,
            "file_id": file_id
        },
        {"_id": 0}
    ).sort("changed_at", -1).to_list(100)
    
    return logs



@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/verify")
async def verify_requirement(
    employee_id: str,
    requirement_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Verify a requirement. REQUIRES evidence to exist.
    Cannot verify empty requirements.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    # Get evidence status
    evidence = await get_requirement_evidence(employee_id, requirement_id, user)
    
    if not evidence.has_evidence:
        raise HTTPException(
            status_code=400, 
            detail="Cannot verify requirement without evidence. Please upload evidence first."
        )
    
    if evidence.verified:
        return {"success": True, "message": "Requirement already verified", "verified": True}
    
    now = datetime.now(timezone.utc).isoformat()
    user_doc = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    verified_by_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    req_type = requirement.get('type', 'document')
    
    if req_type == 'training':
        await db.training_records.update_many(
            {"employee_id": employee_id, "requirement_id": requirement_id},
            {"$set": {
                "verified": True,
                "verified_by": verified_by_name,
                "verified_at": now,
                "updated_at": now
            }}
        )
    else:
        # Build query with legacy mapping support
        legacy_mapping = {
            "dbs_certificate": ["dbs", "dbs_certificate"],
            "identity_documents": ["identity_rtw", "identity_documents"],
            "right_to_work_documents": ["identity_rtw", "right_to_work_documents"],
        }
        req_ids_to_search = legacy_mapping.get(requirement_id, [requirement_id])
        
        await db.employee_documents.update_many(
            {"employee_id": employee_id, "requirement_id": {"$in": req_ids_to_search}},
            {"$set": {
                "verified": True,
                "verified_by": user['user_id'],
                "verified_by_name": verified_by_name,
                "verified_at": now,
                "updated_at": now
            }}
        )
    
    await log_audit_action(user['user_id'], "verify_requirement", "requirement", requirement_id,
                           {"employee_id": employee_id})
    
    await update_employee_compliance(employee_id)
    
    return {"success": True, "message": f"'{requirement['name']}' verified", "verified": True}


@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/unverify")
async def unverify_requirement(
    employee_id: str,
    requirement_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Remove verification from a requirement"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    now = datetime.now(timezone.utc).isoformat()
    req_type = requirement.get('type', 'document')
    
    # Build query with legacy mapping support
    legacy_mapping = {
        "dbs_certificate": ["dbs", "dbs_certificate"],
        "identity_documents": ["identity_rtw", "identity_documents"],
        "right_to_work_documents": ["identity_rtw", "right_to_work_documents"],
    }
    req_ids_to_search = legacy_mapping.get(requirement_id, [requirement_id])
    
    if req_type == 'training':
        await db.training_records.update_many(
            {"employee_id": employee_id, "requirement_id": {"$in": req_ids_to_search}},
            {"$set": {"verified": False, "verified_by": None, "verified_at": None, "updated_at": now}}
        )
    else:
        await db.employee_documents.update_many(
            {"employee_id": employee_id, "requirement_id": {"$in": req_ids_to_search}},
            {"$set": {"verified": False, "verified_by": None, "verified_by_name": None, "verified_at": None, "updated_at": now}}
        )
    
    await log_audit_action(user['user_id'], "unverify_requirement", "requirement", requirement_id,
                           {"employee_id": employee_id})
    
    return {"success": True, "message": f"Verification removed from '{requirement['name']}'"}


# ==================== EMPLOYEE DOCUMENT ROUTES ====================

@api_router.post("/employee-documents", response_model=EmployeeDocumentResponse)
async def create_employee_document(doc: EmployeeDocumentCreate, user: dict = Depends(require_manager_or_admin)):
    now = datetime.now(timezone.utc).isoformat()
    
    doc_type = await db.document_types.find_one({"id": doc.document_type_id}, {"_id": 0})
    doc_type_name = doc_type['name'] if doc_type else None
    
    # Auto-detect requirement_id if not provided
    requirement_id = doc.requirement_id
    if not requirement_id and doc_type_name:
        requirement_id = get_requirement_id_from_doctype(doc_type_name)
    
    # Check for existing document with same requirement_id to prevent duplicates
    if requirement_id:
        existing_doc = await db.employee_documents.find_one({
            "employee_id": doc.employee_id,
            "requirement_id": requirement_id
        }, {"_id": 0})
        
        if existing_doc:
            # Update existing document instead of creating duplicate
            update_data = {
                "document_type_id": doc.document_type_id,
                "document_type_name": doc_type_name,
                "category": doc_type['category'] if doc_type else None,
                "notes": doc.notes or existing_doc.get('notes'),
                "expiry_date": doc.expiry_date,
                "updated_at": now,
                "version_number": existing_doc.get('version_number', 1) + 1
            }
            await db.employee_documents.update_one({"id": existing_doc['id']}, {"$set": update_data})
            updated_doc = await db.employee_documents.find_one({"id": existing_doc['id']}, {"_id": 0})
            updated_doc['requirement_name'] = get_requirement_name(requirement_id)
            return EmployeeDocumentResponse(**updated_doc)
    
    # Create new document
    doc_id = str(uuid.uuid4())
    doc_data = {
        "id": doc_id,
        **doc.model_dump(),
        "requirement_id": requirement_id,
        "requirement_name": get_requirement_name(requirement_id) if requirement_id else None,
        "document_type_name": doc_type_name,
        "category": doc_type['category'] if doc_type else None,
        "file_url": None,
        "original_filename": None,
        "status": DocumentStatus.NOT_STARTED,
        "uploaded_by": None,
        "uploaded_at": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "version_number": 1,
        "verified": False,
        "created_at": now,
        "updated_at": now
    }
    await db.employee_documents.insert_one(doc_data)
    return EmployeeDocumentResponse(**doc_data)

@api_router.get("/employee-documents", response_model=List[EmployeeDocumentResponse])
async def get_employee_documents(
    employee_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    docs = await db.employee_documents.find(query, {"_id": 0}).to_list(1000)
    return [EmployeeDocumentResponse(**d) for d in docs]

@api_router.get("/employee-documents/{doc_id}", response_model=EmployeeDocumentResponse)
async def get_employee_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return EmployeeDocumentResponse(**doc)

@api_router.get("/employees/{employee_id}/compliance-requirements")
async def get_compliance_requirements(employee_id: str, user: dict = Depends(get_current_user)):
    """
    Get all compliance requirements with evidence-based status.
    EVIDENCE-BASED COMPLIANCE: Only requirements with viewable evidence count as complete.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get mandatory items for this employee's role
    role = employee.get('role', '')
    mandatory_items = get_mandatory_items_for_role(role)
    
    # Get all ACTIVE documents for this employee (exclude superseded/inactive)
    all_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "$or": [
            {"active": {"$exists": False}},
            {"active": True}
        ],
        "status": {"$ne": "superseded"}
    }, {"_id": 0}).to_list(500)
    
    # Get all forms for this employee
    all_forms = await db.generated_forms.find({"employee_id": employee_id}, {"_id": 0}).to_list(500)
    
    # Get all training records
    all_training = await db.training_records.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    
    requirements = []
    completed_count = 0
    verified_count = 0
    evidence_backed_count = 0
    
    for item in mandatory_items:
        req_id = item['id']
        req_type = item.get('type', 'document')
        allow_multiple = item.get('allow_multiple_files', True)  # Default to True now
        min_files = item.get('min_files', 1)
        source = item.get('source', 'employee')
        priority = item.get('priority', 'secondary')
        priority_order = item.get('priority_order', 99)
        work_ready_hint = item.get('work_ready_hint', '')
        
        req = {
            "id": req_id,
            "name": item['name'],
            "category": item['category'],
            "type": req_type,
            "source": source,
            "description": item.get('description', ''),
            "allow_multiple_files": allow_multiple,
            "min_files": min_files,
            "status": "missing",
            "documents": [],  # Legacy: Array of document records
            "evidence_files": [],  # NEW: Unified evidence files array
            "document_count": 0,
            "evidence_count": 0,
            "has_evidence": False,  # NEW: Critical for evidence-based compliance
            "form": None,
            "training": None,
            "verified": False,
            "verified_by": None,
            "verified_at": None,
            "all_verified": False,
            "can_verify": False,  # NEW: True only when evidence exists
            "completion_method": None,  # NEW: "evidence" or "manual" or "form"
            # Work Readiness fields
            "priority": priority,
            "priority_order": priority_order,
            "priority_label": PRIORITY_CONFIG.get(priority, {}).get('label', 'Complete After Start'),
            "priority_color": PRIORITY_CONFIG.get(priority, {}).get('color', 'yellow'),
            "work_ready_hint": work_ready_hint,
            "is_mandatory_for_work": req_id in WORK_READY_REQUIREMENTS or priority == 'mandatory'
        }
        
        evidence_files = []
        
        # ======== Handle Documents ========
        if req_type in ['document', 'form-generated']:
            # Find ALL linked documents for this requirement
            linked_docs = []
            for doc in all_docs:
                doc_req_id = doc.get('requirement_id')
                if doc_req_id == req_id:
                    linked_docs.append(doc)
                # Also match by document type name if no explicit requirement_id
                elif not doc_req_id and doc.get('document_type_name'):
                    auto_req_id = get_requirement_id_from_doctype(doc['document_type_name'])
                    if auto_req_id == req_id:
                        linked_docs.append(doc)
                # Legacy support: match identity_rtw to new split requirements
                elif doc_req_id == 'identity_rtw' and req_id in ['identity_documents', 'right_to_work_documents']:
                    # Try to intelligently route based on document type
                    doc_type = doc.get('document_type_name', '').lower()
                    if req_id == 'identity_documents' and any(x in doc_type for x in ['passport', 'licence', 'license', 'id']):
                        linked_docs.append(doc)
                    elif req_id == 'right_to_work_documents' and any(x in doc_type for x in ['visa', 'brp', 'share', 'work']):
                        linked_docs.append(doc)
                # Legacy support: match dbs to dbs_certificate
                elif doc_req_id == 'dbs' and req_id == 'dbs_certificate':
                    linked_docs.append(doc)
            
            # Sort by uploaded_at (newest first)
            linked_docs.sort(key=lambda d: d.get('uploaded_at') or '', reverse=True)
            
            # Extract evidence files from documents
            for doc in linked_docs:
                # Get expiry date from document record
                doc_expiry_date = doc.get('expiry_date')
                
                # Check for evidence_files array (new format)
                if doc.get('evidence_files'):
                    for ef in doc['evidence_files']:
                        file_expiry = ef.get('expiry_date') or doc_expiry_date
                        evidence_files.append({
                            "file_id": ef.get('file_id', doc['id']),
                            "file_url": ef.get('file_url'),
                            "original_filename": ef.get('original_filename', 'document'),
                            "uploaded_at": ef.get('uploaded_at'),
                            "uploaded_by_name": ef.get('uploaded_by_name'),
                            "file_label": ef.get('file_label') or doc.get('document_label'),
                            "source_type": ef.get('source_type', 'manual_upload'),
                            "doc_id": doc['id'],
                            "verified": doc.get('verified', False),
                            "expiry_date": file_expiry,
                            "expiry_status": calculate_expiry_status(file_expiry) if file_expiry else None
                        })
                # Fallback to file_url (legacy format)
                elif doc.get('file_url'):
                    evidence_files.append({
                        "file_id": doc['id'],
                        "file_url": doc['file_url'],
                        "original_filename": doc.get('original_filename', 'document'),
                        "uploaded_at": doc.get('uploaded_at'),
                        "uploaded_by_name": doc.get('uploaded_by_name'),
                        "file_label": doc.get('document_label'),
                        "source_type": doc.get('source_type', 'manual_upload'),
                        "doc_id": doc['id'],
                        "verified": doc.get('verified', False),
                        "expiry_date": doc_expiry_date,
                        "expiry_status": calculate_expiry_status(doc_expiry_date) if doc_expiry_date else None
                    })
            
            req['documents'] = linked_docs
            req['document_count'] = len(linked_docs)
            
            # Check verification
            verified_docs = [d for d in linked_docs if d.get('verified')]
            if verified_docs and evidence_files:
                req['verified'] = len(verified_docs) >= min_files
                req['all_verified'] = len(verified_docs) == len([d for d in linked_docs if d.get('file_url')])
                req['verified_by'] = verified_docs[0].get('verified_by_name') or verified_docs[0].get('verified_by')
                req['verified_at'] = verified_docs[0].get('verified_at')
        
        # ======== Handle Forms ========
        if req_type == 'form-generated':
            # Check for linked form
            linked_form = None
            for form in all_forms:
                if form.get('requirement_id') == req_id:
                    linked_form = form
                    break
            
            if not linked_form:
                template_name = item.get('template_name', item['name'])
                for form in all_forms:
                    if template_name.lower() in form.get('template_name', '').lower():
                        linked_form = form
                        break
            
            if linked_form:
                req['form'] = {
                    "id": linked_form['id'],
                    "status": linked_form['status'],
                    "locked": linked_form.get('locked', False),
                    "completed_at": linked_form.get('completed_at'),
                    "pdf_url": linked_form.get('pdf_url')
                }
                
                # If form is completed with PDF, add to evidence
                if linked_form['status'] in ['completed', 'completed_imported', 'signed_off']:
                    if linked_form.get('pdf_url'):
                        evidence_files.append({
                            "file_id": linked_form['id'],
                            "file_url": linked_form['pdf_url'],
                            "original_filename": f"{linked_form.get('template_name', 'Form')}.pdf",
                            "uploaded_at": linked_form.get('completed_at') or linked_form.get('updated_at'),
                            "source_type": "form_submission",
                            "file_label": f"Completed {linked_form.get('template_name', 'Form')}",
                            "verified": False  # Forms need separate verification
                        })
        
        # ======== Handle Training ========
        if req_type == 'training':
            training_name = item.get('training_name', item['name'])
            linked_training = None
            
            # First try by requirement_id
            for training in all_training:
                if training.get('requirement_id') == req_id:
                    linked_training = training
                    break
            
            # Fallback to name matching
            if not linked_training:
                for training in all_training:
                    train_name = training.get('training_name', '')
                    if training_name.lower() in train_name.lower() or train_name.lower() in training_name.lower():
                        linked_training = training
                        break
            
            if linked_training:
                # Get expiry date from training record
                training_expiry_date = linked_training.get('expiry_date')
                
                # Extract evidence files from training
                if linked_training.get('evidence_files'):
                    for ef in linked_training['evidence_files']:
                        file_expiry = ef.get('expiry_date') or training_expiry_date
                        evidence_files.append({
                            "file_id": ef.get('file_id', linked_training['id']),
                            "file_url": ef.get('file_url'),
                            "original_filename": ef.get('original_filename', 'certificate'),
                            "uploaded_at": ef.get('uploaded_at'),
                            "source_type": ef.get('source_type', 'certificate'),
                            "file_label": ef.get('file_label', 'Training Certificate'),
                            "verified": linked_training.get('verified', False),
                            "expiry_date": file_expiry,
                            "expiry_status": calculate_expiry_status(file_expiry) if file_expiry else None
                        })
                elif linked_training.get('certificate_url'):
                    evidence_files.append({
                        "file_id": linked_training['id'],
                        "file_url": linked_training['certificate_url'],
                        "original_filename": linked_training.get('original_filename', 'certificate'),
                        "uploaded_at": linked_training.get('uploaded_at', linked_training.get('completion_date')),
                        "source_type": "certificate",
                        "file_label": "Training Certificate",
                        "verified": linked_training.get('verified', False),
                        "expiry_date": training_expiry_date,
                        "expiry_status": calculate_expiry_status(training_expiry_date) if training_expiry_date else None
                    })
                
                req['training'] = {
                    "id": linked_training['id'],
                    "status": linked_training['status'],
                    "completed_at": linked_training.get('completed_at') or linked_training.get('completion_date'),
                    "expiry_date": linked_training.get('expiry_date'),
                    "certificate_url": linked_training.get('certificate_url'),
                    "original_filename": linked_training.get('original_filename'),
                    "uploaded_at": linked_training.get('uploaded_at'),
                    "verified": linked_training.get('verified', False),
                    "verified_by": linked_training.get('verified_by'),
                    "verified_at": linked_training.get('verified_at'),
                    "completion_method": linked_training.get('completion_method'),
                    "has_evidence": bool(evidence_files)
                }
                
                if linked_training.get('verified') and evidence_files:
                    req['verified'] = True
                    req['verified_by'] = linked_training.get('verified_by')
                    req['verified_at'] = linked_training.get('verified_at')
        
        # ======== Calculate Status (EVIDENCE-BASED) ========
        req['evidence_files'] = evidence_files
        req['evidence_count'] = len(evidence_files)
        req['has_evidence'] = len(evidence_files) > 0
        req['can_verify'] = req['has_evidence'] and not req['verified']
        
        if evidence_files:
            # Has evidence = complete
            req['status'] = 'completed'
            req['completion_method'] = 'evidence'
            completed_count += 1
            evidence_backed_count += 1
            
            if req['verified']:
                verified_count += 1
        elif req.get('form') and req['form']['status'] in ['completed', 'completed_imported']:
            # Form completed but no PDF/evidence - mark as "completed_no_evidence"
            if not req['form'].get('pdf_url'):
                req['status'] = 'completed_no_evidence'
                req['completion_method'] = 'form_no_pdf'
                # Does NOT count toward compliance score
            else:
                req['status'] = 'completed'
                req['completion_method'] = 'form'
                completed_count += 1
                evidence_backed_count += 1
        elif req.get('training') and req['training']['status'] == 'completed':
            # Training completed but no certificate
            req['status'] = 'completed_no_evidence'
            req['completion_method'] = 'manual'
            # Does NOT count toward compliance score
        elif req.get('form') and req['form']['status'] in ['draft', 'in_progress']:
            req['status'] = 'in_progress'
        elif req.get('training') and req['training']['status'] in ['in_progress', 'scheduled']:
            req['status'] = 'in_progress'
        else:
            req['status'] = 'missing'
        
        # ======== Calculate Expiry Status for Requirement ========
        # Check if this requirement should track expiry
        req['tracks_expiry'] = req_id in EXPIRABLE_REQUIREMENTS
        req['expiry_status'] = None
        req['expiry_date'] = None
        
        if req['tracks_expiry'] and evidence_files:
            # Find the most relevant expiry status from evidence files
            expiry_statuses = [ef.get('expiry_status') for ef in evidence_files if ef.get('expiry_status')]
            if expiry_statuses:
                # Prioritize: expired > expiring_soon > valid
                expired = [s for s in expiry_statuses if s['status'] == 'expired']
                expiring = [s for s in expiry_statuses if s['status'] == 'expiring_soon']
                valid = [s for s in expiry_statuses if s['status'] == 'valid']
                
                if expired:
                    req['expiry_status'] = expired[0]
                elif expiring:
                    req['expiry_status'] = expiring[0]
                elif valid:
                    req['expiry_status'] = valid[0]
                
                if req['expiry_status']:
                    req['expiry_date'] = req['expiry_status'].get('expiry_date')
        
        requirements.append(req)
    
    # ======== Calculate Expiry Alerts ========
    expiring_soon_items = []
    expired_items = []
    
    for req in requirements:
        if req.get('expiry_status'):
            if req['expiry_status']['status'] == 'expired':
                expired_items.append({
                    "id": req['id'],
                    "name": req['name'],
                    "expiry_date": req['expiry_status'].get('expiry_date'),
                    "days_overdue": abs(req['expiry_status'].get('days_until_expiry', 0))
                })
            elif req['expiry_status']['status'] == 'expiring_soon':
                expiring_soon_items.append({
                    "id": req['id'],
                    "name": req['name'],
                    "expiry_date": req['expiry_status'].get('expiry_date'),
                    "days_until_expiry": req['expiry_status'].get('days_until_expiry', 0)
                })
    
    total_count = len(requirements)
    # EVIDENCE-BASED SCORING: Only evidence-backed completions count
    completion_percentage = int((evidence_backed_count / total_count) * 100) if total_count > 0 else 0
    verification_percentage = int((verified_count / evidence_backed_count) * 100) if evidence_backed_count > 0 else 0
    
    # Calculate Work Readiness
    work_readiness = calculate_work_readiness(requirements, role)
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "role": role,
        "requirements": requirements,
        "summary": {
            "total": total_count,
            "completed": evidence_backed_count,  # Only evidence-backed
            "completed_no_evidence": completed_count - evidence_backed_count,  # Flagged items
            "verified": verified_count,
            "missing": total_count - completed_count,
            "completion_percentage": completion_percentage,
            "verification_percentage": verification_percentage,
            "audit_ready": verified_count == evidence_backed_count and evidence_backed_count == total_count
        },
        "work_readiness": work_readiness,
        "expiry_alerts": {
            "expiring_soon": expiring_soon_items,
            "expired": expired_items,
            "expiring_soon_count": len(expiring_soon_items),
            "expired_count": len(expired_items),
            "has_alerts": len(expiring_soon_items) > 0 or len(expired_items) > 0
        }
    }

@api_router.post("/employees/{employee_id}/upload-document")
async def upload_document_for_requirement(
    employee_id: str,
    requirement_id: str = Form(...),
    file: UploadFile = File(...),
    document_label: Optional[str] = Form(None),  # e.g., "Passport Front", "Visa"
    notes: Optional[str] = Form(None),
    user: dict = Depends(require_manager_or_admin)
):
    """Upload a document linked to a requirement. 
    - Single-file requirements: replaces existing document
    - Multi-file requirements: adds new document to the requirement
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get requirement config
    all_items = MANDATORY_ITEMS['base'] + MANDATORY_ITEMS['training'] + MANDATORY_ITEMS['nurse_specific']
    req_config = next((item for item in all_items if item['id'] == requirement_id), None)
    allow_multiple = req_config.get('allow_multiple_files', False) if req_config else False
    
    # Get requirement name
    req_name = get_requirement_name(requirement_id) or requirement_id.replace('_', ' ').title()
    
    # Find matching document type
    doc_types = REQUIREMENT_TO_DOCTYPE.get(requirement_id, [req_name])
    doc_type = None
    for type_name in doc_types:
        doc_type = await db.document_types.find_one(
            {"name": {"$regex": type_name, "$options": "i"}},
            {"_id": 0}
        )
        if doc_type:
            break
    
    # Upload file
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    employee_name = f"{employee['first_name']}{employee['last_name']}"
    timestamp = datetime.now(timezone.utc).strftime('%d-%m-%Y_%H%M%S')
    filename = f"{employee_name}_{requirement_id}_{timestamp}.{ext}"
    path = f"{APP_NAME}/documents/{employee_id}/{requirement_id}/{filename}"
    
    data = await file.read()
    put_object(path, data, file.content_type or "application/octet-stream")
    
    if allow_multiple:
        # Multi-file requirement: always create new document
        doc_id = str(uuid.uuid4())
        doc_data = {
            "id": doc_id,
            "employee_id": employee_id,
            "document_type_id": doc_type['id'] if doc_type else str(uuid.uuid4()),
            "document_type_name": doc_type['name'] if doc_type else req_name,
            "category": req_config.get('category', 'O_Other') if req_config else (doc_type['category'] if doc_type else "O_Other"),
            "requirement_id": requirement_id,
            "requirement_name": req_name,
            "document_label": document_label or file.filename,  # Use provided label or filename
            "file_url": path,
            "original_filename": file.filename,
            "status": DocumentStatus.UPLOADED,
            "uploaded_by": user['user_id'],
            "uploaded_at": now,
            "reviewed_by": None,
            "reviewed_at": None,
            "expiry_date": None,
            "notes": notes,
            "version_number": 1,
            "verified": False,
            "source_type": "manual",
            "created_at": now,
            "updated_at": now
        }
        await db.employee_documents.insert_one(doc_data)
        
        # Count total files for this requirement
        doc_count = await db.employee_documents.count_documents({
            "employee_id": employee_id,
            "requirement_id": requirement_id
        })
        
        await log_audit_action(user['user_id'], "add_document", "employee_document", doc_id, {
            "requirement_id": requirement_id,
            "filename": file.filename,
            "document_label": document_label,
            "total_files": doc_count
        })
    else:
        # Single-file requirement: replace existing
        existing_doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id
        }, {"_id": 0})
        
        if existing_doc:
            # Update existing document
            update_data = {
                "file_url": path,
                "original_filename": file.filename,
                "document_label": document_label,
                "status": DocumentStatus.UPLOADED,
                "uploaded_by": user['user_id'],
                "uploaded_at": now,
                "notes": notes or existing_doc.get('notes'),
                "version_number": existing_doc.get('version_number', 1) + 1,
                "verified": False,  # Reset verification on re-upload
                "verified_by": None,
                "verified_at": None,
                "verified_by_name": None,
                "updated_at": now
            }
            await db.employee_documents.update_one({"id": existing_doc['id']}, {"$set": update_data})
            doc_id = existing_doc['id']
            
            await log_audit_action(user['user_id'], "replace_document", "employee_document", doc_id, {
                "requirement_id": requirement_id,
                "filename": file.filename,
                "version": update_data['version_number']
            })
        else:
            # Create new document
            doc_id = str(uuid.uuid4())
            doc_data = {
                "id": doc_id,
                "employee_id": employee_id,
                "document_type_id": doc_type['id'] if doc_type else str(uuid.uuid4()),
                "document_type_name": doc_type['name'] if doc_type else req_name,
                "category": req_config.get('category', 'O_Other') if req_config else (doc_type['category'] if doc_type else "O_Other"),
                "requirement_id": requirement_id,
                "requirement_name": req_name,
                "document_label": document_label,
                "file_url": path,
                "original_filename": file.filename,
                "status": DocumentStatus.UPLOADED,
                "uploaded_by": user['user_id'],
                "uploaded_at": now,
                "reviewed_by": None,
                "reviewed_at": None,
                "expiry_date": None,
                "notes": notes,
                "version_number": 1,
                "verified": False,
                "source_type": "manual",
                "created_at": now,
                "updated_at": now
            }
            await db.employee_documents.insert_one(doc_data)
            
            await log_audit_action(user['user_id'], "upload_document", "employee_document", doc_id, {
                "requirement_id": requirement_id,
                "filename": file.filename
            })
    
    doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    return EmployeeDocumentResponse(**doc)

@api_router.post("/employee-documents/{doc_id}/upload")
async def upload_employee_document(
    doc_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Generate storage path
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    path = f"{APP_NAME}/documents/{doc['employee_id']}/{uuid.uuid4()}.{ext}"
    
    # Upload to storage
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update document record
    await db.employee_documents.update_one(
        {"id": doc_id},
        {"$set": {
            "file_url": result["path"],
            "original_filename": file.filename,
            "status": DocumentStatus.UPLOADED,
            "uploaded_by": user['user_id'],
            "uploaded_at": now,
            "version_number": doc.get('version_number', 0) + 1
        }}
    )
    
    await log_audit_action(user['user_id'], "upload_document", "employee_document", doc_id, {"filename": file.filename})
    
    updated_doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    return EmployeeDocumentResponse(**updated_doc)

@api_router.put("/employee-documents/{doc_id}", response_model=EmployeeDocumentResponse)
async def update_employee_document(doc_id: str, update: EmployeeDocumentUpdate, user: dict = Depends(require_manager_or_admin)):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if 'status' in update_data and update_data['status'] in [DocumentStatus.APPROVED, DocumentStatus.REJECTED]:
        update_data['reviewed_by'] = user['user_id']
        update_data['reviewed_at'] = datetime.now(timezone.utc).isoformat()
    
    # Handle verification
    if update_data.get('verified'):
        update_data['verified_by'] = user['user_id']
        update_data['verified_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.employee_documents.update_one({"id": doc_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await log_audit_action(user['user_id'], "update_document", "employee_document", doc_id, update_data)
    
    doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    
    # Get verifier name if verified
    if doc.get('verified_by'):
        verifier = await db.users.find_one({"user_id": doc['verified_by']}, {"_id": 0, "name": 1})
        doc['verified_by_name'] = verifier.get('name') if verifier else None
    
    return EmployeeDocumentResponse(**doc)

@api_router.post("/employee-documents/{doc_id}/verify")
async def verify_employee_document(doc_id: str, user: dict = Depends(require_manager_or_admin)):
    """Mark a document as verified"""
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Ensure document is approved before verification
    if doc.get('status') not in ['approved', 'uploaded']:
        raise HTTPException(status_code=400, detail="Document must be approved before verification")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get verifier name
    verifier = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0, "name": 1})
    verifier_name = verifier.get('name') if verifier else None
    
    update_data = {
        "verified": True,
        "verified_by": user['user_id'],
        "verified_by_name": verifier_name,
        "verified_at": now,
        "status": "approved"  # Ensure status is approved
    }
    
    await db.employee_documents.update_one({"id": doc_id}, {"$set": update_data})
    await log_audit_action(user['user_id'], "verify_document", "employee_document", doc_id, {"verified": True})
    
    updated_doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    
    return EmployeeDocumentResponse(**updated_doc)

@api_router.post("/employee-documents/{doc_id}/unverify")
async def unverify_employee_document(doc_id: str, user: dict = Depends(require_manager_or_admin)):
    """Remove verification from a document"""
    result = await db.employee_documents.update_one(
        {"id": doc_id},
        {"$set": {"verified": False, "verified_by": None, "verified_at": None, "verified_by_name": None}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await log_audit_action(user['user_id'], "unverify_document", "employee_document", doc_id, {"verified": False})
    
    doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    return EmployeeDocumentResponse(**doc)

@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/verify-all")
async def verify_all_documents_in_requirement(employee_id: str, requirement_id: str, user: dict = Depends(require_manager_or_admin)):
    """Verify all documents under a requirement"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Get verifier name
    verifier = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0, "name": 1})
    verifier_name = verifier.get('name') if verifier else None
    
    # Find all documents for this requirement
    result = await db.employee_documents.update_many(
        {
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "status": {"$in": ["uploaded", "approved"]}
        },
        {"$set": {
            "verified": True,
            "verified_by": user['user_id'],
            "verified_by_name": verifier_name,
            "verified_at": now,
            "status": "approved"
        }}
    )
    
    await log_audit_action(user['user_id'], "verify_requirement", "requirement", requirement_id, {
        "employee_id": employee_id,
        "documents_verified": result.modified_count
    })
    
    return {"message": f"Verified {result.modified_count} documents", "verified_count": result.modified_count}

@api_router.delete("/employee-documents/{doc_id}")
async def delete_employee_document(doc_id: str, user: dict = Depends(require_manager_or_admin)):
    """Delete a specific document (for multi-file requirements)"""
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if this is a multi-file requirement - if single-file, don't allow delete
    requirement_id = doc.get('requirement_id')
    if requirement_id:
        all_items = MANDATORY_ITEMS['base'] + MANDATORY_ITEMS['training'] + MANDATORY_ITEMS['nurse_specific']
        req_config = next((item for item in all_items if item['id'] == requirement_id), None)
        if req_config and not req_config.get('allow_multiple_files', False):
            raise HTTPException(status_code=400, detail="Cannot delete document from single-file requirement. Use replace instead.")
    
    await db.employee_documents.delete_one({"id": doc_id})
    
    await log_audit_action(user['user_id'], "delete_document", "employee_document", doc_id, {
        "requirement_id": requirement_id,
        "filename": doc.get('original_filename')
    })
    
    return {"message": "Document deleted successfully"}

@api_router.get("/employee-documents/{doc_id}/file")
async def serve_employee_document_file(doc_id: str, user: dict = Depends(get_current_user)):
    """Serve an employee document file"""
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = doc.get("file_url")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file uploaded for this document")
    
    try:
        content, content_type = get_object(file_path)
        filename = doc.get("original_filename", doc.get("file_name", "document.pdf"))
        safe_filename = filename.replace('"', '\\"') if filename else "document.pdf"
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to retrieve employee document file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file")

@api_router.get("/employee-documents/{doc_id}/download")
async def download_employee_document_file(doc_id: str, user: dict = Depends(get_current_user)):
    """Download an employee document file"""
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = doc.get("file_url")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file uploaded for this document")
    
    try:
        content, content_type = get_object(file_path)
        filename = doc.get("original_filename", doc.get("file_name", "document.pdf"))
        safe_filename = filename.replace('"', '\\"') if filename else "document.pdf"
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to download employee document file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file")
async def download_file(path: str, authorization: str = Header(None), auth: str = Query(None)):
    auth_header = authorization or (f"Bearer {auth}" if auth else None)
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        logger.error(f"File download failed: {e}")
        raise HTTPException(status_code=404, detail="File not found")

# ==================== POLICY ROUTES ====================

@api_router.post("/policies", response_model=PolicyResponse)
async def create_policy(policy: PolicyCreate, user: dict = Depends(require_admin)):
    policy_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    policy_doc = {
        "id": policy_id,
        **policy.model_dump(),
        "file_url": None,
        "active": True,
        "published_at": now,
        "assigned_count": 0,
        "signed_count": 0
    }
    await db.policies.insert_one(policy_doc)
    return PolicyResponse(**policy_doc)

@api_router.get("/policies", response_model=List[PolicyResponse])
async def get_policies(active: Optional[bool] = None, user: dict = Depends(get_current_user)):
    query = {}
    if active is not None:
        query["active"] = active
    policies = await db.policies.find(query, {"_id": 0}).to_list(100)
    
    # Get counts
    for policy in policies:
        assigned_count = await db.policy_assignments.count_documents({"policy_id": policy['id']})
        signed_count = await db.policy_assignments.count_documents({"policy_id": policy['id'], "status": "signed"})
        policy['assigned_count'] = assigned_count
        policy['signed_count'] = signed_count
    
    return [PolicyResponse(**p) for p in policies]

@api_router.post("/policies/{policy_id}/upload")
async def upload_policy_file(policy_id: str, file: UploadFile = File(...), user: dict = Depends(require_admin)):
    policy = await db.policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    path = f"{APP_NAME}/policies/{uuid.uuid4()}.{ext}"
    
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/pdf")
    
    await db.policies.update_one({"id": policy_id}, {"$set": {"file_url": result["path"]}})
    
    updated_policy = await db.policies.find_one({"id": policy_id}, {"_id": 0})
    return PolicyResponse(**updated_policy)

@api_router.post("/policies/assign")
async def assign_policies(assignment: PolicyAssignmentCreate, user: dict = Depends(require_admin)):
    policy = await db.policies.find_one({"id": assignment.policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    assignments = []
    
    for emp_id in assignment.employee_ids:
        # Check if already assigned
        existing = await db.policy_assignments.find_one({"policy_id": assignment.policy_id, "employee_id": emp_id})
        if existing:
            continue
        
        assignment_doc = {
            "id": str(uuid.uuid4()),
            "policy_id": assignment.policy_id,
            "policy_title": policy['title'],
            "employee_id": emp_id,
            "assigned_at": now,
            "status": "assigned",
            "viewed_at": None,
            "signed_at": None
        }
        await db.policy_assignments.insert_one(assignment_doc)
        assignments.append(assignment_doc)
        
        await log_audit_action(user['user_id'], "assign_policy", "policy_assignment", assignment_doc['id'], {"policy_id": assignment.policy_id, "employee_id": emp_id})
    
    return {"assigned": len(assignments), "message": f"Policy assigned to {len(assignments)} employees"}

@api_router.get("/policy-assignments", response_model=List[PolicyAssignmentResponse])
async def get_policy_assignments(
    employee_id: Optional[str] = None,
    policy_id: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if policy_id:
        query["policy_id"] = policy_id
    if status:
        query["status"] = status
    
    assignments = await db.policy_assignments.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with employee names
    for a in assignments:
        emp = await db.employees.find_one({"id": a['employee_id']}, {"_id": 0})
        if emp:
            a['employee_name'] = f"{emp['first_name']} {emp['last_name']}"
    
    return [PolicyAssignmentResponse(**a) for a in assignments]

@api_router.put("/policy-assignments/{assignment_id}/acknowledge")
async def acknowledge_policy(assignment_id: str, user: dict = Depends(get_current_user)):
    assignment = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {"status": "signed", "signed_at": now}
    if not assignment.get('viewed_at'):
        update_data['viewed_at'] = now
    
    await db.policy_assignments.update_one({"id": assignment_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "acknowledge_policy", "policy_assignment", assignment_id, {"policy_id": assignment['policy_id']})
    
    updated = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    return PolicyAssignmentResponse(**updated)

# ==================== TRAINING ROUTES ====================

@api_router.post("/training-records", response_model=TrainingRecordResponse)
async def create_training_record(record: TrainingRecordCreate, user: dict = Depends(require_manager_or_admin)):
    record_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    record_doc = {
        "id": record_id,
        **record.model_dump(),
        "certificate_url": None,
        "created_at": now
    }
    await db.training_records.insert_one(record_doc)
    
    await log_audit_action(user['user_id'], "create_training", "training_record", record_id, {"training_name": record.training_name})
    
    return TrainingRecordResponse(**record_doc)

@api_router.get("/training-records", response_model=List[TrainingRecordResponse])
async def get_training_records(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    mandatory: Optional[bool] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if status:
        query["status"] = status
    if mandatory is not None:
        query["mandatory"] = mandatory
    
    records = await db.training_records.find(query, {"_id": 0}).to_list(1000)
    return [TrainingRecordResponse(**r) for r in records]

@api_router.put("/training-records/{record_id}", response_model=TrainingRecordResponse)
async def update_training_record(record_id: str, update: TrainingRecordCreate, user: dict = Depends(require_manager_or_admin)):
    result = await db.training_records.update_one({"id": record_id}, {"$set": update.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    return TrainingRecordResponse(**record)

@api_router.post("/training-records/{record_id}/upload-certificate")
async def upload_training_certificate(
    record_id: str, 
    file: UploadFile = File(...), 
    expiry_date: Optional[str] = Form(None),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Upload a certificate for a training record.
    This is the proper way to complete training with evidence.
    """
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    # Get employee for file path
    employee = await db.employees.find_one({"id": record['employee_id']}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    employee_name = f"{employee['first_name']}{employee['last_name']}"
    training_slug = record['training_name'].replace(' ', '_')
    storage_filename = f"{employee_name}_{training_slug}_certificate_{datetime.now(timezone.utc).strftime('%d-%m-%Y')}.{ext}"
    path = f"{APP_NAME}/certificates/{record['employee_id']}/{storage_filename}"
    
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/pdf")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "certificate_url": result["path"], 
        "original_filename": file.filename,
        "uploaded_at": now,
        "status": "completed",
        "completion_date": now,
        "completion_method": "certificate",
        "updated_at": now
    }
    
    if expiry_date:
        update_data["expiry_date"] = expiry_date
    
    await db.training_records.update_one(
        {"id": record_id},
        {"$set": update_data}
    )
    
    await log_audit_action(
        user['user_id'], 
        "upload_training_certificate", 
        "training_record", 
        record_id, 
        {"training_name": record['training_name'], "filename": file.filename}
    )
    
    # Update employee compliance
    await update_employee_compliance(record['employee_id'])
    
    updated = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    return updated


@api_router.post("/training-records/{record_id}/verify")
async def verify_training_record(record_id: str, user: dict = Depends(require_manager_or_admin)):
    """
    Verify a training record. Requires certificate to be uploaded first.
    """
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    # Check if certificate exists
    if not record.get('certificate_url'):
        raise HTTPException(
            status_code=400, 
            detail="Cannot verify training without uploaded certificate. Please upload a certificate first."
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get user name for verification
    user_doc = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    verified_by_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    await db.training_records.update_one(
        {"id": record_id},
        {"$set": {
            "verified": True,
            "verified_by": verified_by_name,
            "verified_at": now,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'], 
        "verify_training", 
        "training_record", 
        record_id, 
        {"training_name": record['training_name']}
    )
    
    # Update employee compliance
    await update_employee_compliance(record['employee_id'])
    
    updated = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    return {"success": True, "message": "Training verified successfully", "training_record": updated}


@api_router.post("/training-records/{record_id}/unverify")
async def unverify_training_record(record_id: str, user: dict = Depends(require_manager_or_admin)):
    """Remove verification from a training record."""
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.training_records.update_one(
        {"id": record_id},
        {"$set": {
            "verified": False,
            "verified_by": None,
            "verified_at": None,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'], 
        "unverify_training", 
        "training_record", 
        record_id, 
        {"training_name": record['training_name']}
    )
    
    updated = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    return {"success": True, "message": "Training verification removed", "training_record": updated}


@api_router.get("/training-records/{record_id}/certificate/file")
async def get_training_certificate_file(record_id: str, user: dict = Depends(get_current_user)):
    """Get certificate file for viewing."""
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    if not record.get('certificate_url'):
        raise HTTPException(status_code=404, detail="No certificate uploaded for this training")
    
    try:
        file_bytes, stored_content_type = get_object(record['certificate_url'])
        
        # Determine content type from extension or use stored type
        ext = record['certificate_url'].split('.')[-1].lower()
        content_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        content_type = content_types.get(ext, stored_content_type)
        
        return Response(content=file_bytes, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve certificate: {str(e)}")


@api_router.get("/training-records/{record_id}/certificate/download")
async def download_training_certificate(record_id: str, user: dict = Depends(get_current_user)):
    """Download certificate file."""
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    if not record.get('certificate_url'):
        raise HTTPException(status_code=404, detail="No certificate uploaded for this training")
    
    try:
        file_bytes, _ = get_object(record['certificate_url'])
        
        filename = record.get('original_filename', f"{record['training_name']}_certificate.pdf")
        
        return Response(
            content=file_bytes, 
            media_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download certificate: {str(e)}")


@api_router.post("/employees/{employee_id}/training/{requirement_id}/upload-certificate")
async def upload_training_certificate_for_requirement(
    employee_id: str,
    requirement_id: str,
    file: UploadFile = File(...),
    expiry_date: Optional[str] = Form(None),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Upload a certificate for a training requirement.
    Creates training record if not exists, or updates existing one.
    This is the PROPER way to complete training with evidence.
    """
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get the requirement config from MANDATORY_ITEMS
    all_items = MANDATORY_ITEMS['base'] + MANDATORY_ITEMS['training'] + MANDATORY_ITEMS['nurse_specific']
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    if requirement.get('type') != 'training':
        raise HTTPException(status_code=400, detail=f"Requirement {requirement_id} is not a training requirement")
    
    training_name = requirement.get('training_name', requirement['name'])
    now = datetime.now(timezone.utc).isoformat()
    
    # Upload file
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    employee_name = f"{employee['first_name']}{employee['last_name']}"
    training_slug = training_name.replace(' ', '_')
    storage_filename = f"{employee_name}_{training_slug}_certificate_{datetime.now(timezone.utc).strftime('%d-%m-%Y')}.{ext}"
    path = f"{APP_NAME}/certificates/{employee_id}/{storage_filename}"
    
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/pdf")
    
    # Check for existing training record
    existing_record = await db.training_records.find_one({
        "employee_id": employee_id,
        "$or": [
            {"training_name": {"$regex": training_name, "$options": "i"}},
            {"requirement_id": requirement_id}
        ]
    }, {"_id": 0})
    
    if existing_record:
        # Update existing record
        update_data = {
            "certificate_url": result["path"],
            "original_filename": file.filename,
            "uploaded_at": now,
            "status": "completed",
            "completion_date": now,
            "completion_method": "certificate",
            "requirement_id": requirement_id,
            "updated_at": now
        }
        if expiry_date:
            update_data["expiry_date"] = expiry_date
            
        await db.training_records.update_one(
            {"id": existing_record['id']},
            {"$set": update_data}
        )
        
        await log_audit_action(
            user['user_id'], 
            "upload_training_certificate", 
            "training_record", 
            existing_record['id'], 
            {"requirement_id": requirement_id, "training_name": training_name, "filename": file.filename}
        )
        
        updated_record = await db.training_records.find_one({"id": existing_record['id']}, {"_id": 0})
        action = "updated"
    else:
        # Create new training record with certificate
        record_id = str(uuid.uuid4())
        new_record = {
            "id": record_id,
            "employee_id": employee_id,
            "training_name": training_name,
            "mandatory": True,
            "status": "completed",
            "completion_date": now,
            "expiry_date": expiry_date,
            "certificate_url": result["path"],
            "original_filename": file.filename,
            "uploaded_at": now,
            "verified": False,
            "verified_by": None,
            "verified_at": None,
            "completion_method": "certificate",
            "requirement_id": requirement_id,
            "created_at": now
        }
        
        await db.training_records.insert_one(new_record)
        
        await log_audit_action(
            user['user_id'], 
            "upload_training_certificate", 
            "training_record", 
            record_id, 
            {"requirement_id": requirement_id, "training_name": training_name, "filename": file.filename}
        )
        
        updated_record = {k: v for k, v in new_record.items() if k != '_id'}
        action = "created"
    
    # Update employee compliance
    await update_employee_compliance(employee_id)
    
    return {
        "success": True,
        "message": f"Certificate uploaded for '{requirement['name']}'",
        "training_record": updated_record,
        "action": action
    }


async def update_employee_compliance(employee_id: str):
    """Helper function to recalculate and update employee compliance percentage"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if employee:
        compliance = await calculate_employee_compliance(employee_id, employee.get("role", ""))
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {"completion_percentage": compliance["completion_percentage"]}}
        )


class CompleteTrainingRequest(BaseModel):
    """Request to complete a training requirement"""
    requirement_id: str  # The requirement ID from MANDATORY_ITEMS (e.g., 'safeguarding', 'manual_handling')
    completion_date: Optional[str] = None  # ISO date string, defaults to now
    expiry_date: Optional[str] = None  # Optional expiry date
    notes: Optional[str] = None
    link_existing_id: Optional[str] = None  # If linking to existing training record


@api_router.post("/employees/{employee_id}/complete-training")
async def complete_training_requirement(
    employee_id: str, 
    request: CompleteTrainingRequest, 
    user: dict = Depends(require_manager_or_admin)
):
    """
    Complete a training requirement for an employee.
    - If link_existing_id is provided, links that existing training record to this requirement
    - Otherwise, creates a new completed training record
    - PREVENTS DUPLICATES: Checks if requirement already has a training record
    """
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get the requirement config from MANDATORY_ITEMS
    all_items = MANDATORY_ITEMS['base'] + MANDATORY_ITEMS['training'] + MANDATORY_ITEMS['nurse_specific']
    requirement = next((item for item in all_items if item['id'] == request.requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {request.requirement_id}")
    
    if requirement.get('type') != 'training':
        raise HTTPException(status_code=400, detail=f"Requirement {request.requirement_id} is not a training requirement")
    
    training_name = requirement.get('training_name', requirement['name'])
    now = datetime.now(timezone.utc).isoformat()
    completion_date = request.completion_date or now
    
    # Check if there's already a completed training record for this requirement
    # Use the same matching logic as check_item_completion
    existing_training = await db.training_records.find_one({
        "employee_id": employee_id,
        "$or": [
            {"training_name": {"$regex": training_name, "$options": "i"}},
            {"training_name": {"$regex": training_name.replace(" ", ""), "$options": "i"}}
        ],
        "status": "completed"
    }, {"_id": 0})
    
    if existing_training:
        return {
            "success": True,
            "message": f"Training requirement '{requirement['name']}' is already completed",
            "training_record": existing_training,
            "action": "already_completed"
        }
    
    # If linking to existing record
    if request.link_existing_id:
        existing_record = await db.training_records.find_one({"id": request.link_existing_id}, {"_id": 0})
        if not existing_record:
            raise HTTPException(status_code=404, detail="Existing training record not found")
        
        if existing_record['employee_id'] != employee_id:
            raise HTTPException(status_code=400, detail="Training record belongs to a different employee")
        
        # Update the existing record to mark it completed and link to requirement
        await db.training_records.update_one(
            {"id": request.link_existing_id},
            {"$set": {
                "status": "completed",
                "completion_date": completion_date,
                "expiry_date": request.expiry_date,
                "requirement_id": request.requirement_id,
                "updated_at": now
            }}
        )
        
        updated_record = await db.training_records.find_one({"id": request.link_existing_id}, {"_id": 0})
        
        await log_audit_action(
            user['user_id'], 
            "link_training", 
            "training_record", 
            request.link_existing_id, 
            {"requirement_id": request.requirement_id, "training_name": training_name}
        )
        
        # Update employee compliance percentage
        await update_employee_compliance(employee_id)
        
        return {
            "success": True,
            "message": f"Linked existing training to requirement '{requirement['name']}'",
            "training_record": updated_record,
            "action": "linked"
        }
    
    # Create new completed training record
    # First check for any existing record (even incomplete) for this training type
    existing_incomplete = await db.training_records.find_one({
        "employee_id": employee_id,
        "$or": [
            {"training_name": {"$regex": training_name, "$options": "i"}},
            {"training_name": {"$regex": training_name.replace(" ", ""), "$options": "i"}}
        ]
    }, {"_id": 0})
    
    if existing_incomplete:
        # Update the existing record instead of creating a new one
        await db.training_records.update_one(
            {"id": existing_incomplete['id']},
            {"$set": {
                "status": "completed",
                "completion_date": completion_date,
                "expiry_date": request.expiry_date,
                "requirement_id": request.requirement_id,
                "updated_at": now
            }}
        )
        
        updated_record = await db.training_records.find_one({"id": existing_incomplete['id']}, {"_id": 0})
        
        await log_audit_action(
            user['user_id'], 
            "complete_training", 
            "training_record", 
            existing_incomplete['id'], 
            {"requirement_id": request.requirement_id, "training_name": training_name}
        )
        
        # Update employee compliance percentage
        await update_employee_compliance(employee_id)
        
        return {
            "success": True,
            "message": f"Training requirement '{requirement['name']}' marked as complete",
            "training_record": updated_record,
            "action": "updated"
        }
    
    # Create brand new training record
    record_id = str(uuid.uuid4())
    new_record = {
        "id": record_id,
        "employee_id": employee_id,
        "training_name": training_name,
        "mandatory": True,
        "status": "completed",
        "completion_date": completion_date,
        "expiry_date": request.expiry_date,
        "certificate_url": None,
        "requirement_id": request.requirement_id,
        "created_at": now
    }
    
    await db.training_records.insert_one(new_record)
    
    await log_audit_action(
        user['user_id'], 
        "complete_training", 
        "training_record", 
        record_id, 
        {"requirement_id": request.requirement_id, "training_name": training_name}
    )
    
    # Update employee compliance percentage
    await update_employee_compliance(employee_id)
    
    # Return without _id
    if '_id' in new_record:
        del new_record['_id']
    
    return {
        "success": True,
        "message": f"Training requirement '{requirement['name']}' marked as complete",
        "training_record": {k: v for k, v in new_record.items() if k != '_id'},
        "action": "created"
    }


@api_router.get("/employees/{employee_id}/training-requirements")
async def get_employee_training_requirements(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get all training requirements for an employee with their current status.
    Returns the requirement definition along with any linked training records.
    """
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get all training items for the employee's role
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    training_items = [item for item in all_items if item.get('type') == 'training']
    
    # Get all training records for the employee
    training_records = await db.training_records.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).to_list(100)
    
    requirements = []
    for item in training_items:
        training_name = item.get('training_name', item['name'])
        
        # Find matching training record (same logic as check_item_completion)
        linked_record = None
        for record in training_records:
            record_name = record.get('training_name', '')
            if (training_name.lower() in record_name.lower() or 
                record_name.lower() in training_name.lower()):
                linked_record = record
                break
        
        status = 'missing'
        if linked_record:
            if linked_record.get('status') == 'completed':
                status = 'completed'
            elif linked_record.get('status') in ['in_progress', 'scheduled']:
                status = 'in_progress'
            else:
                status = 'pending'
        
        requirements.append({
            "requirement_id": item['id'],
            "name": item['name'],
            "training_name": training_name,
            "category": item.get('category', 'N_Training'),
            "status": status,
            "training_record": linked_record,
            "is_complete": status == 'completed'
        })
    
    completed_count = sum(1 for r in requirements if r['is_complete'])
    
    return {
        "employee_id": employee_id,
        "requirements": requirements,
        "summary": {
            "total": len(requirements),
            "completed": completed_count,
            "missing": len(requirements) - completed_count
        }
    }


# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(user: dict = Depends(require_manager_or_admin)):
    assignment_filter = {}
    if user['role'] == UserRole.BRANCH_MANAGER:
        assignment_filter = {"assignment": user.get('assignment')}
    
    # Get counts
    total_employees = await db.employees.count_documents({**assignment_filter, "status": {"$in": [EmployeeStatus.ACTIVE, EmployeeStatus.ONBOARDING]}})
    total_applicants = await db.employees.count_documents({**assignment_filter, "status": {"$in": [EmployeeStatus.NEW, EmployeeStatus.SCREENING, EmployeeStatus.INTERVIEW, EmployeeStatus.COMPLIANCE_REVIEW]}})
    onboarding = await db.employees.count_documents({**assignment_filter, "status": EmployeeStatus.ONBOARDING})
    
    # Count fully verified employees (all requirements have evidence AND are verified)
    fully_verified_count = 0
    active_employees = await db.employees.find(
        {**assignment_filter, "status": {"$in": [EmployeeStatus.ACTIVE, EmployeeStatus.ONBOARDING]}},
        {"_id": 0, "id": 1}
    ).to_list(500)
    
    for emp in active_employees:
        emp_doc = await db.employee_documents.find_one(
            {"employee_id": emp["id"], "requirement_type": "evidence_store"},
            {"_id": 0}
        )
        if emp_doc:
            evidence_store = emp_doc.get("evidence_store", {})
            if evidence_store:
                all_verified = True
                has_any_evidence = False
                for req_id, evidence in evidence_store.items():
                    files = evidence.get("evidence_files", [])
                    if files:
                        has_any_evidence = True
                        # Check if all files are verified
                        if not all(f.get("verified", False) for f in files):
                            all_verified = False
                            break
                if has_any_evidence and all_verified:
                    fully_verified_count += 1
    
    # Get DBS document type
    dbs_type = await db.document_types.find_one({"name": {"$regex": "DBS", "$options": "i"}}, {"_id": 0})
    rtw_type = await db.document_types.find_one({"name": {"$regex": "Right to Work", "$options": "i"}}, {"_id": 0})
    ref_type = await db.document_types.find_one({"name": {"$regex": "Reference", "$options": "i"}}, {"_id": 0})
    
    # Count missing documents
    missing_urgent = await db.employee_documents.count_documents({"status": {"$in": [DocumentStatus.NOT_STARTED, DocumentStatus.REQUESTED]}})
    dbs_pending = await db.employee_documents.count_documents({"document_type_id": dbs_type['id'] if dbs_type else "", "status": {"$ne": DocumentStatus.APPROVED}}) if dbs_type else 0
    rtw_missing = await db.employee_documents.count_documents({"document_type_id": rtw_type['id'] if rtw_type else "", "status": {"$ne": DocumentStatus.APPROVED}}) if rtw_type else 0
    refs_outstanding = await db.employee_documents.count_documents({"document_type_id": ref_type['id'] if ref_type else "", "status": {"$ne": DocumentStatus.APPROVED}}) if ref_type else 0
    
    # Unsigned policies
    unsigned_policies = await db.policy_assignments.count_documents({"status": {"$ne": "signed"}})
    
    # Expiring documents
    now = datetime.now(timezone.utc)
    exp_30 = (now + timedelta(days=30)).isoformat()
    exp_60 = (now + timedelta(days=60)).isoformat()
    exp_90 = (now + timedelta(days=90)).isoformat()
    
    expiring_30 = await db.employee_documents.count_documents({"expiry_date": {"$lte": exp_30, "$gt": now.isoformat()}})
    expiring_60 = await db.employee_documents.count_documents({"expiry_date": {"$lte": exp_60, "$gt": exp_30}})
    expiring_90 = await db.employee_documents.count_documents({"expiry_date": {"$lte": exp_90, "$gt": exp_60}})
    
    return DashboardStats(
        total_employees=total_employees,
        total_applicants=total_applicants,
        fully_verified_employees=fully_verified_count,
        onboarding_in_progress=onboarding,
        missing_urgent_documents=missing_urgent,
        unsigned_policies=unsigned_policies,
        dbs_pending=dbs_pending,
        rtw_missing=rtw_missing,
        references_outstanding=refs_outstanding,
        expiring_30_days=expiring_30,
        expiring_60_days=expiring_60,
        expiring_90_days=expiring_90
    )

@api_router.get("/dashboard/audit-readiness")
async def get_audit_readiness_dashboard(user: dict = Depends(require_manager_or_admin)):
    """Get audit readiness dashboard with smart compliance metrics"""
    
    # Get all active/onboarding employees
    employees = await db.employees.find(
        {"status": {"$in": [EmployeeStatus.ACTIVE, EmployeeStatus.ONBOARDING, EmployeeStatus.NEW, 
                           EmployeeStatus.SCREENING, EmployeeStatus.INTERVIEW, EmployeeStatus.COMPLIANCE_REVIEW]}},
        {"_id": 0, "id": 1, "role": 1, "onboarding_status": 1, "status": 1}
    ).to_list(500)
    
    # Initialize counters
    ready_for_placement = 0
    under_review = 0
    documents_pending = 0
    new_employees = 0
    active_employees = 0
    
    missing_critical = 0
    employees_with_missing_items = []
    
    # Onboarding status counts
    for emp in employees:
        status = emp.get("onboarding_status", "New")
        if status == OnboardingStatus.READY_FOR_PLACEMENT:
            ready_for_placement += 1
        elif status == OnboardingStatus.UNDER_REVIEW:
            under_review += 1
        elif status == OnboardingStatus.DOCUMENTS_PENDING:
            documents_pending += 1
        elif status == OnboardingStatus.NEW:
            new_employees += 1
        elif status == OnboardingStatus.ACTIVE:
            active_employees += 1
    
    # Check for critical missing items (sample first 50 employees)
    sample_employees = employees[:50]
    for emp in sample_employees:
        compliance = await calculate_employee_compliance(emp["id"], emp.get("role", ""))
        if compliance["missing_count"] > 0:
            critical_missing = [
                item["name"] for item in compliance["items"] 
                if item["status"] == "missing" and item["id"] in ["dbs", "identity_rtw", "references", "safeguarding"]
            ]
            if critical_missing:
                missing_critical += 1
                if len(employees_with_missing_items) < 10:
                    employees_with_missing_items.append({
                        "employee_id": emp["id"],
                        "missing_items": critical_missing
                    })
    
    # Expiring documents
    now = datetime.now(timezone.utc)
    exp_30 = (now + timedelta(days=30)).isoformat()
    
    expiring_dbs = await db.employee_documents.count_documents({
        "document_type": "dbs",
        "expiry_date": {"$lte": exp_30, "$gt": now.isoformat()}
    })
    
    expiring_training = await db.training_records.count_documents({
        "expiry_date": {"$lte": exp_30, "$gt": now.isoformat()}
    })
    
    # Organisation compliance
    policies_missing = await db.org_policies.count_documents({"status": "missing"})
    policies_total = await db.org_policies.count_documents({})
    
    insurance_missing = await db.insurance_docs.count_documents({"status": "missing"})
    insurance_expiring = await db.insurance_docs.count_documents({
        "expiry_date": {"$lte": exp_30, "$gt": now.isoformat()}
    })
    insurance_total = await db.insurance_docs.count_documents({})
    
    return {
        "staff_compliance": {
            "total_staff": len(employees),
            "ready_for_placement": ready_for_placement,
            "under_review": under_review,
            "documents_pending": documents_pending,
            "new_employees": new_employees,
            "active_employees": active_employees
        },
        "critical_alerts": {
            "missing_critical_items": missing_critical,
            "expiring_dbs": expiring_dbs,
            "expiring_training": expiring_training,
            "employees_with_issues": employees_with_missing_items
        },
        "organisation_compliance": {
            "policies_uploaded": policies_total - policies_missing,
            "policies_missing": policies_missing,
            "policies_total": policies_total,
            "insurance_valid": insurance_total - insurance_missing - insurance_expiring,
            "insurance_missing": insurance_missing,
            "insurance_expiring": insurance_expiring,
            "insurance_total": insurance_total
        },
        "audit_readiness_score": calculate_audit_score(
            ready_for_placement, under_review, documents_pending,
            policies_missing, insurance_missing, missing_critical
        )
    }

def calculate_audit_score(ready: int, review: int, pending: int, 
                         policies_missing: int, insurance_missing: int, 
                         critical_missing: int) -> dict:
    """Calculate overall audit readiness score"""
    total_staff = ready + review + pending
    if total_staff == 0:
        staff_score = 100
    else:
        staff_score = int((ready / total_staff) * 100)
    
    # Deduct points for missing items
    penalty = min(50, (policies_missing * 2) + (insurance_missing * 5) + (critical_missing * 3))
    overall = max(0, min(100, staff_score - penalty))
    
    if overall >= 80:
        status = "Audit Ready"
        color = "success"
    elif overall >= 60:
        status = "Needs Attention"
        color = "warning"
    else:
        status = "Critical Issues"
        color = "error"
    
    return {
        "score": overall,
        "status": status,
        "color": color,
        "staff_readiness": staff_score
    }

@api_router.get("/dashboard/expiry-alerts")
async def get_expiry_alerts_dashboard(user: dict = Depends(get_current_user)):
    """
    Get dashboard view of all expiring and expired compliance items across all employees.
    Returns employees grouped by alert severity.
    """
    now = datetime.now(timezone.utc)
    warning_threshold = now + timedelta(days=EXPIRY_WARNING_DAYS)
    
    # Get all non-archived employees
    employees = await db.employees.find(
        {"status": {"$ne": "archived"}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1}
    ).to_list(1000)
    
    employees_with_expired = []
    employees_expiring_soon = []
    
    for emp in employees:
        emp_id = emp['id']
        emp_name = f"{emp['first_name']} {emp['last_name']}"
        role = emp.get('role', '')
        
        expired_items = []
        expiring_items = []
        
        # Check documents
        docs = await db.employee_documents.find({
            "employee_id": emp_id,
            "expiry_date": {"$exists": True, "$ne": None}
        }, {"_id": 0, "requirement_id": 1, "document_label": 1, "expiry_date": 1}).to_list(100)
        
        for doc in docs:
            expiry_status = calculate_expiry_status(doc.get('expiry_date'))
            if expiry_status:
                item_info = {
                    "requirement_id": doc.get('requirement_id'),
                    "name": doc.get('document_label', 'Document'),
                    "expiry_date": expiry_status.get('expiry_date'),
                    "days": expiry_status.get('days_until_expiry')
                }
                if expiry_status['status'] == 'expired':
                    expired_items.append(item_info)
                elif expiry_status['status'] == 'expiring_soon':
                    expiring_items.append(item_info)
        
        # Check training records
        training = await db.training_records.find({
            "employee_id": emp_id,
            "expiry_date": {"$exists": True, "$ne": None}
        }, {"_id": 0, "requirement_id": 1, "training_name": 1, "expiry_date": 1}).to_list(100)
        
        for t in training:
            expiry_status = calculate_expiry_status(t.get('expiry_date'))
            if expiry_status:
                item_info = {
                    "requirement_id": t.get('requirement_id'),
                    "name": t.get('training_name', 'Training'),
                    "expiry_date": expiry_status.get('expiry_date'),
                    "days": expiry_status.get('days_until_expiry')
                }
                if expiry_status['status'] == 'expired':
                    expired_items.append(item_info)
                elif expiry_status['status'] == 'expiring_soon':
                    expiring_items.append(item_info)
        
        if expired_items:
            employees_with_expired.append({
                "employee_id": emp_id,
                "employee_name": emp_name,
                "role": role,
                "expired_items": expired_items,
                "expired_count": len(expired_items)
            })
        
        if expiring_items:
            employees_expiring_soon.append({
                "employee_id": emp_id,
                "employee_name": emp_name,
                "role": role,
                "expiring_items": expiring_items,
                "expiring_count": len(expiring_items)
            })
    
    # Sort by count (most urgent first)
    employees_with_expired.sort(key=lambda x: x['expired_count'], reverse=True)
    employees_expiring_soon.sort(key=lambda x: x['expiring_count'], reverse=True)
    
    return {
        "expired": {
            "employees": employees_with_expired,
            "total_employees": len(employees_with_expired),
            "total_items": sum(e['expired_count'] for e in employees_with_expired)
        },
        "expiring_soon": {
            "employees": employees_expiring_soon,
            "total_employees": len(employees_expiring_soon),
            "total_items": sum(e['expiring_count'] for e in employees_expiring_soon)
        },
        "has_alerts": len(employees_with_expired) > 0 or len(employees_expiring_soon) > 0
    }

# ==================== AUDIT LOG ROUTES ====================

async def log_audit_action(user_id: str, action: str, entity_type: str, entity_id: str, metadata: dict):
    audit_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(audit_doc)

@api_router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_manager_or_admin)
):
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Enrich with user names
    for log in logs:
        user_doc = await db.users.find_one({"user_id": log['user_id']}, {"_id": 0})
        if user_doc:
            log['user_name'] = user_doc.get('name', 'Unknown')
    
    return logs

# ==================== TEMPLATE LIBRARY ROUTES ====================

@api_router.post("/templates", response_model=TemplateResponse)
async def create_template(template: TemplateCreate, user: dict = Depends(require_admin)):
    template_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    template_doc = {
        "id": template_id,
        **template.model_dump(),
        "active": True,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "created_by": user['user_id']
    }
    await db.templates.insert_one(template_doc)
    
    await log_audit_action(user['user_id'], "create_template", "template", template_id, {"name": template.name})
    
    return TemplateResponse(**template_doc)

@api_router.get("/templates", response_model=List[TemplateResponse])
async def get_templates(
    category: Optional[str] = None,
    active: bool = True,
    user: dict = Depends(get_current_user)
):
    query = {"active": active}
    if category:
        query["category"] = category
    
    templates = await db.templates.find(query, {"_id": 0}).to_list(100)
    return [TemplateResponse(**t) for t in templates]

@api_router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    template = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse(**template)

@api_router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, update: TemplateCreate, user: dict = Depends(require_admin)):
    template = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = update.model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["version"] = template.get("version", 1) + 1
    
    await db.templates.update_one({"id": template_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "update_template", "template", template_id, {"name": update.name})
    
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return TemplateResponse(**updated)

@api_router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(require_admin)):
    # Soft delete - just mark as inactive
    result = await db.templates.update_one({"id": template_id}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await log_audit_action(user['user_id'], "delete_template", "template", template_id, {})
    return {"message": "Template archived"}

# ==================== GENERATED FORMS ROUTES ====================

async def auto_fill_employee_data(employee_id: str) -> dict:
    """Get employee data for auto-filling forms"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return {}
    
    return {
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_first_name": employee['first_name'],
        "employee_last_name": employee['last_name'],
        "employee_id": employee['employee_code'],
        "employee_email": employee['email'],
        "employee_phone": employee.get('phone', ''),
        "employee_role": employee['role'],
        "employee_assignment": employee.get('assignment', 'Unassigned'),
        "employee_manager": employee.get('manager_name', ''),
        "employee_start_date": employee.get('start_date', ''),
        "date_generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "date_generated_formatted": datetime.now(timezone.utc).strftime("%d %B %Y")
    }


async def auto_generate_form_pdf(form_id: str, user: dict):
    """
    Auto-generate PDF for a completed form and store as evidence document.
    Called automatically when form status changes to 'completed' or 'signed_off'.
    """
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        return
    
    # Skip if already has PDF
    if form.get('pdf_url'):
        return
    
    # Get employee
    employee = await db.employees.find_one({"id": form['employee_id']}, {"_id": 0})
    if not employee:
        return
    
    # Get template
    template = await db.templates.find_one({"id": form['template_id']}, {"_id": 0})
    template_name = form.get('template_name') or (template['name'] if template else 'Form')
    
    # Determine folder
    folder = get_folder_for_form(template_name)
    
    # Generate filename
    employee_name = f"{employee['first_name']} {employee['last_name']}"
    filename = generate_document_filename(employee_name, template_name)
    
    # Generate PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('FormTitle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=20)
    elements.append(Paragraph(template_name, title_style))
    
    # Employee info
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=10, spaceAfter=5)
    elements.append(Paragraph(f"<b>Employee:</b> {employee_name} ({employee.get('employee_code', 'N/A')})", info_style))
    elements.append(Paragraph(f"<b>Role:</b> {employee.get('role', 'N/A')}", info_style))
    elements.append(Paragraph(f"<b>Date:</b> {datetime.now(timezone.utc).strftime('%d/%m/%Y')}", info_style))
    elements.append(Spacer(1, 20))
    
    # Form data
    form_data = form.get('form_data', {})
    if form_data:
        elements.append(Paragraph("<b>Form Data</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Create table for form data
        table_data = [['Field', 'Value']]
        for key, value in form_data.items():
            if value:
                display_key = key.replace('_', ' ').title()
                display_value = str(value)[:100]
                table_data.append([display_key, display_value])
        
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[200, 300])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004D4D')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFA')]),
            ]))
            elements.append(table)
    
    elements.append(Spacer(1, 30))
    
    # Signatures section
    if form.get('employee_signature') or form.get('admin_signature'):
        elements.append(Paragraph("<b>Signatures</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        if form.get('employee_signature'):
            elements.append(Paragraph(f"Employee Signature: {form['employee_signature']}", info_style))
            if form.get('employee_signed_at'):
                elements.append(Paragraph(f"Signed: {form['employee_signed_at'][:10]}", info_style))
        
        if form.get('admin_signature'):
            elements.append(Paragraph(f"Admin Signature: {form['admin_signature']}", info_style))
            if form.get('admin_signed_at'):
                elements.append(Paragraph(f"Signed: {form['admin_signed_at'][:10]}", info_style))
    
    # Status footer
    elements.append(Spacer(1, 30))
    status_text = f"Status: {form.get('status', 'Unknown').upper()}"
    if form.get('locked'):
        status_text += " (LOCKED)"
    elements.append(Paragraph(f"<i>{status_text}</i>", info_style))
    elements.append(Paragraph(f"<i>Generated: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}</i>", info_style))
    
    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Upload PDF to storage
    now = datetime.now(timezone.utc).isoformat()
    file_path = f"osabea-care/documents/{employee['id']}/{folder}/{filename}"
    put_object(file_path, pdf_content, "application/pdf")
    
    # Determine requirement_id from form template
    req_id = form.get('requirement_id')
    if not req_id:
        # Map template name to requirement_id
        template_to_req = {
            "application form": "application_form",
            "recruitment compliance checklist": "recruitment_checklist",
            "personal information form": "personal_info",
            "interview record": "interview_record",
            "equal opportunities monitoring": "equal_opportunities",
            "health screening questionnaire": "health_screening",
            "induction": "induction",
            "contract acknowledgement": "contract",
            "employee handbook acknowledgement": "handbook",
        }
        for key, value in template_to_req.items():
            if key in template_name.lower():
                req_id = value
                break
    
    # Find or create document type
    doc_type = await db.document_types.find_one(
        {"name": {"$regex": template_name, "$options": "i"}},
        {"_id": 0}
    )
    
    doc_type_id = doc_type['id'] if doc_type else str(uuid.uuid4())
    doc_type_name = doc_type['name'] if doc_type else template_name
    
    # Create employee document record with proper requirement_id
    doc_id = str(uuid.uuid4())
    evidence_file = {
        "file_id": doc_id,
        "file_url": file_path,
        "original_filename": filename,
        "uploaded_at": now,
        "uploaded_by": user['user_id'],
        "source_type": "form_submission",
        "file_label": f"Completed {template_name}"
    }
    
    emp_doc = {
        "id": doc_id,
        "employee_id": employee['id'],
        "document_type_id": doc_type_id,
        "document_type_name": doc_type_name,
        "category": folder,
        "file_url": file_path,
        "original_filename": filename,
        "status": DocumentStatus.APPROVED,
        "uploaded_by": user['user_id'],
        "uploaded_at": now,
        "reviewed_by": user['user_id'],
        "reviewed_at": now,
        "expiry_date": None,
        "notes": f"Auto-generated from form completion. Form ID: {form_id}",
        "version_number": 1,
        "verified": False,
        "source_type": "form_submission",
        "source_form_id": form_id,
        "requirement_id": req_id,
        "requirement_name": template_name,
        "document_label": f"Completed {template_name}",
        "evidence_files": [evidence_file],
        "created_at": now
    }
    
    await db.employee_documents.insert_one(emp_doc)
    
    # Update form with PDF URL and requirement_id
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {
            "pdf_url": file_path, 
            "saved_as_document_id": doc_id,
            "requirement_id": req_id
        }}
    )
    
    # Update employee compliance
    await update_employee_compliance(employee['id'])
    
    logger.info(f"Auto-generated PDF for form {form_id} -> document {doc_id}")


@api_router.post("/generated-forms/{form_id}/regenerate-pdf")
async def regenerate_form_pdf(form_id: str, user: dict = Depends(require_manager_or_admin)):
    """
    Force regenerate PDF for a completed form.
    Use this when a form is completed but has no PDF evidence.
    """
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    if form['status'] not in ['completed', 'completed_imported', 'signed_off', 'reviewed']:
        raise HTTPException(status_code=400, detail="Form must be in completed status to generate PDF")
    
    # Clear existing pdf_url to force regeneration
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$unset": {"pdf_url": ""}}
    )
    
    await auto_generate_form_pdf(form_id, user)
    
    updated_form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    
    return {
        "success": True,
        "message": "PDF regenerated successfully",
        "pdf_url": updated_form.get('pdf_url'),
        "document_id": updated_form.get('saved_as_document_id')
    }


@api_router.post("/generated-forms", response_model=GeneratedFormResponse)
async def create_generated_form(form: GeneratedFormCreate, user: dict = Depends(require_manager_or_admin)):
    form_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get template
    template = await db.templates.find_one({"id": form.template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": form.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Auto-fill employee data
    auto_filled = await auto_fill_employee_data(form.employee_id)
    merged_data = {**auto_filled, **form.form_data}
    
    # Generate access token for employee/external access
    access_token = str(uuid.uuid4())
    
    form_doc = {
        "id": form_id,
        "template_id": form.template_id,
        "template_name": template['name'],
        "template_category": template['category'],
        "employee_id": form.employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee['employee_code'],
        "form_data": merged_data,
        "status": FormStatus.DRAFT,
        "employee_signature": None,
        "employee_signed_at": None,
        "admin_signature": None,
        "admin_signed_at": None,
        "admin_signoff_by": None,
        "pdf_url": None,
        "locked": False,
        "notes": None,
        "version": 1,
        "access_token": access_token,
        "created_at": now,
        "updated_at": now,
        "created_by": user['user_id'],
        "sent_at": None,
        "viewed_at": None,
        "completed_at": None,
        "reviewed_at": None,
        "signed_off_at": None
    }
    await db.generated_forms.insert_one(form_doc)
    
    await log_audit_action(user['user_id'], "create_form", "generated_form", form_id, {
        "template_name": template['name'],
        "employee_id": form.employee_id
    })
    
    return GeneratedFormResponse(**form_doc)

@api_router.get("/generated-forms", response_model=List[GeneratedFormResponse])
async def get_generated_forms(
    employee_id: Optional[str] = None,
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if template_id:
        query["template_id"] = template_id
    if status:
        query["status"] = status
    
    forms = await db.generated_forms.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [GeneratedFormResponse(**f) for f in forms]

@api_router.get("/generated-forms/{form_id}", response_model=GeneratedFormResponse)
async def get_generated_form(form_id: str, user: dict = Depends(get_current_user)):
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return GeneratedFormResponse(**form)

# Public access endpoint for employees to complete forms via access token
@api_router.get("/forms/access/{access_token}")
async def get_form_by_token(access_token: str):
    form = await db.generated_forms.find_one({"access_token": access_token}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or link expired")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is locked and cannot be edited")
    
    # Mark as viewed if not already
    if not form.get('viewed_at'):
        await db.generated_forms.update_one(
            {"id": form['id']},
            {"$set": {"viewed_at": datetime.now(timezone.utc).isoformat()}}
        )
        await log_audit_action("system", "form_viewed", "generated_form", form['id'], {"access_type": "token"})
    
    # Get template for form fields
    template = await db.templates.find_one({"id": form['template_id']}, {"_id": 0})
    
    return {
        "form": GeneratedFormResponse(**form),
        "template": template
    }

@api_router.put("/forms/access/{access_token}/submit")
async def submit_form_by_token(access_token: str, data: dict):
    form = await db.generated_forms.find_one({"access_token": access_token}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or link expired")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is locked and cannot be edited")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "form_data": {**form['form_data'], **data.get('form_data', {})},
        "status": FormStatus.COMPLETED,
        "completed_at": now,
        "updated_at": now
    }
    
    # Handle employee signature
    if data.get('employee_signature'):
        update_data['employee_signature'] = data['employee_signature']
        update_data['employee_signed_at'] = now
    
    await db.generated_forms.update_one({"id": form['id']}, {"$set": update_data})
    
    await log_audit_action("employee", "form_completed", "generated_form", form['id'], {"access_type": "token"})
    
    return {"message": "Form submitted successfully"}

@api_router.put("/generated-forms/{form_id}", response_model=GeneratedFormResponse)
async def update_generated_form(form_id: str, update: GeneratedFormUpdate, user: dict = Depends(require_manager_or_admin)):
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is locked and cannot be edited")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = now
    
    # Track if we're completing the form (need to auto-generate PDF)
    should_generate_pdf = False
    
    # Track status changes
    if update.status:
        if update.status == FormStatus.SENT and not form.get('sent_at'):
            update_data['sent_at'] = now
        elif update.status == FormStatus.COMPLETED and not form.get('completed_at'):
            update_data['completed_at'] = now
            should_generate_pdf = True  # Auto-generate PDF on completion
        elif update.status == FormStatus.REVIEWED and not form.get('reviewed_at'):
            update_data['reviewed_at'] = now
        elif update.status == FormStatus.SIGNED_OFF and not form.get('signed_off_at'):
            update_data['signed_off_at'] = now
            update_data['admin_signoff_by'] = user['user_id']
            should_generate_pdf = True  # Also generate on signoff if not already
    
    await db.generated_forms.update_one({"id": form_id}, {"$set": update_data})
    
    # Auto-generate PDF evidence on completion (if not already exists)
    if should_generate_pdf and not form.get('pdf_url'):
        try:
            await auto_generate_form_pdf(form_id, user)
        except Exception as e:
            logger.error(f"Failed to auto-generate PDF for form {form_id}: {e}")
    
    await log_audit_action(user['user_id'], "update_form", "generated_form", form_id, {"status": update.status})
    
    updated_form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    return GeneratedFormResponse(**updated_form)

@api_router.post("/generated-forms/{form_id}/send")
async def send_form_to_employee(form_id: str, send_email: bool = True, user: dict = Depends(require_manager_or_admin)):
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    employee = await db.employees.find_one({"id": form['employee_id']}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update status
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {"status": FormStatus.SENT, "sent_at": now, "updated_at": now}}
    )
    
    # Generate access link
    access_link = f"{os.environ.get('FRONTEND_URL', '')}/form/{form['access_token']}"
    
    # Send email if configured
    if send_email and resend.api_key:
        try:
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [employee['email']],
                "subject": f"Form to complete: {form['template_name']}",
                "html": f"""
                <h2>Form Request from Osabea Healthcare Solutions</h2>
                <p>Dear {employee['first_name']},</p>
                <p>Please complete the following form:</p>
                <p><strong>{form['template_name']}</strong></p>
                <p><a href="{access_link}" style="display: inline-block; padding: 12px 24px; background-color: #0F5C5E; color: white; text-decoration: none; border-radius: 8px;">Complete Form</a></p>
                <p>Or copy this link: {access_link}</p>
                <p>Thank you,<br>Osabea Healthcare Solutions Team</p>
                """
            })
        except Exception as e:
            logger.error(f"Failed to send form email: {e}")
    
    await log_audit_action(user['user_id'], "send_form", "generated_form", form_id, {"employee_email": employee['email']})
    
    return {"message": "Form sent", "access_link": access_link}

@api_router.post("/generated-forms/{form_id}/signoff")
async def signoff_form(form_id: str, admin_signature: str, notes: Optional[str] = None, user: dict = Depends(require_admin)):
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    if form['locked']:
        raise HTTPException(status_code=403, detail="Form is already signed off and locked")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "status": FormStatus.SIGNED_OFF,
        "admin_signature": admin_signature,
        "admin_signed_at": now,
        "admin_signoff_by": user['user_id'],
        "signed_off_at": now,
        "locked": True,
        "updated_at": now
    }
    if notes:
        update_data['notes'] = notes
    
    await db.generated_forms.update_one({"id": form_id}, {"$set": update_data})
    
    # Link to employee document if template is linked
    template = await db.templates.find_one({"id": form['template_id']}, {"_id": 0})
    if template and template.get('linked_document_type_id'):
        # Update or create employee document record
        existing_doc = await db.employee_documents.find_one({
            "employee_id": form['employee_id'],
            "document_type_id": template['linked_document_type_id']
        })
        
        if existing_doc:
            await db.employee_documents.update_one(
                {"id": existing_doc['id']},
                {"$set": {
                    "status": DocumentStatus.APPROVED,
                    "reviewed_by": user['user_id'],
                    "reviewed_at": now,
                    "notes": f"Signed off via generated form: {form_id}"
                }}
            )
        else:
            doc_id = str(uuid.uuid4())
            doc_type = await db.document_types.find_one({"id": template['linked_document_type_id']}, {"_id": 0})
            await db.employee_documents.insert_one({
                "id": doc_id,
                "employee_id": form['employee_id'],
                "document_type_id": template['linked_document_type_id'],
                "document_type_name": doc_type['name'] if doc_type else template['name'],
                "category": doc_type['category'] if doc_type else template['category'],
                "file_url": None,
                "original_filename": f"{template['name']} - Signed Form",
                "status": DocumentStatus.APPROVED,
                "uploaded_by": user['user_id'],
                "uploaded_at": now,
                "reviewed_by": user['user_id'],
                "reviewed_at": now,
                "expiry_date": None,
                "notes": f"Generated form signed off: {form_id}",
                "version_number": 1,
                "generated_form_id": form_id,
                "created_at": now
            })
    
    await log_audit_action(user['user_id'], "signoff_form", "generated_form", form_id, {"locked": True})
    
    updated_form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    return GeneratedFormResponse(**updated_form)

@api_router.post("/generated-forms/{form_id}/save-as-document")
async def save_form_as_document(form_id: str, user: dict = Depends(require_manager_or_admin)):
    """Convert a completed form to a PDF document and save to employee's folder"""
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": form['employee_id']}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get template
    template = await db.templates.find_one({"id": form['template_id']}, {"_id": 0})
    template_name = form.get('template_name') or (template['name'] if template else 'Form')
    
    # Determine folder
    folder = get_folder_for_form(template_name)
    
    # Generate filename
    employee_name = f"{employee['first_name']} {employee['last_name']}"
    filename = generate_document_filename(employee_name, template_name)
    
    # Generate PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    # TA_CENTER and TA_LEFT already imported at top level
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('FormTitle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=20)
    elements.append(Paragraph(template_name, title_style))
    
    # Employee info
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=10, spaceAfter=5)
    elements.append(Paragraph(f"<b>Employee:</b> {employee_name} ({employee.get('employee_code', 'N/A')})", info_style))
    elements.append(Paragraph(f"<b>Role:</b> {employee.get('role', 'N/A')}", info_style))
    elements.append(Paragraph(f"<b>Date:</b> {datetime.now(timezone.utc).strftime('%d/%m/%Y')}", info_style))
    elements.append(Spacer(1, 20))
    
    # Form data
    form_data = form.get('form_data', {})
    if form_data:
        elements.append(Paragraph("<b>Form Data</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Create table for form data
        table_data = [['Field', 'Value']]
        for key, value in form_data.items():
            if value:  # Only show non-empty values
                display_key = key.replace('_', ' ').title()
                display_value = str(value)[:100]  # Truncate long values
                table_data.append([display_key, display_value])
        
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[200, 300])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004D4D')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFA')]),
            ]))
            elements.append(table)
    
    elements.append(Spacer(1, 30))
    
    # Signatures section
    if form.get('employee_signature') or form.get('admin_signature'):
        elements.append(Paragraph("<b>Signatures</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        if form.get('employee_signature'):
            elements.append(Paragraph(f"Employee Signature: {form['employee_signature']}", info_style))
            if form.get('employee_signed_at'):
                elements.append(Paragraph(f"Signed: {form['employee_signed_at'][:10]}", info_style))
        
        if form.get('admin_signature'):
            elements.append(Paragraph(f"Admin Signature: {form['admin_signature']}", info_style))
            if form.get('admin_signed_at'):
                elements.append(Paragraph(f"Signed: {form['admin_signed_at'][:10]}", info_style))
    
    # Status footer
    elements.append(Spacer(1, 30))
    status_text = f"Status: {form.get('status', 'Unknown').upper()}"
    if form.get('locked'):
        status_text += " (LOCKED)"
    elements.append(Paragraph(f"<i>{status_text}</i>", info_style))
    elements.append(Paragraph(f"<i>Generated: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}</i>", info_style))
    
    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Upload PDF to storage
    now = datetime.now(timezone.utc).isoformat()
    file_path = f"osabea-care/documents/{employee['id']}/{folder}/{filename}"
    put_object(file_path, pdf_content, "application/pdf")
    
    # Find or create document type
    doc_type = await db.document_types.find_one(
        {"name": {"$regex": template_name, "$options": "i"}},
        {"_id": 0}
    )
    
    if not doc_type:
        # Try partial match
        doc_type = await db.document_types.find_one(
            {"category": {"$regex": folder.replace('_', ' '), "$options": "i"}},
            {"_id": 0}
        )
    
    doc_type_id = doc_type['id'] if doc_type else str(uuid.uuid4())
    doc_type_name = doc_type['name'] if doc_type else template_name
    
    # Create employee document record
    doc_id = str(uuid.uuid4())
    emp_doc = {
        "id": doc_id,
        "employee_id": employee['id'],
        "document_type_id": doc_type_id,
        "document_type_name": doc_type_name,
        "category": folder,
        "file_url": file_path,
        "original_filename": filename,
        "status": DocumentStatus.APPROVED,
        "uploaded_by": user['user_id'],
        "uploaded_at": now,
        "reviewed_by": user['user_id'],
        "reviewed_at": now,
        "expiry_date": None,
        "notes": f"Auto-generated from form submission. Form ID: {form_id}",
        "version_number": 1,
        "verified": False,
        "source_type": "form_submission",
        "source_form_id": form_id,
        "created_at": now
    }
    
    await db.employee_documents.insert_one(emp_doc)
    
    # Update form with PDF URL
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {"pdf_url": file_path, "saved_as_document_id": doc_id}}
    )
    
    await log_audit_action(user['user_id'], "save_form_as_document", "generated_form", form_id, {
        "document_id": doc_id,
        "filename": filename,
        "folder": folder
    })
    
    return {
        "success": True,
        "document_id": doc_id,
        "filename": filename,
        "folder": folder,
        "file_url": file_path
    }

@api_router.post("/generated-forms/{form_id}/archive")
async def archive_form(form_id: str, user: dict = Depends(require_admin)):
    form = await db.generated_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.generated_forms.update_one(
        {"id": form_id},
        {"$set": {"status": FormStatus.ARCHIVED, "updated_at": now}}
    )
    
    await log_audit_action(user['user_id'], "archive_form", "generated_form", form_id, {})
    
    return {"message": "Form archived"}

# ==================== BULK UPLOAD ROUTES ====================

@api_router.post("/employees/{employee_id}/bulk-upload")
async def bulk_upload_documents(
    employee_id: str,
    files: List[UploadFile] = File(...),
    document_type_ids: str = Query(..., description="Comma-separated document type IDs"),
    user: dict = Depends(require_manager_or_admin)
):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    type_ids = document_type_ids.split(',')
    
    if len(files) != len(type_ids):
        raise HTTPException(status_code=400, detail="Number of files must match number of document type IDs")
    
    now = datetime.now(timezone.utc).isoformat()
    results = {"successful": 0, "failed": 0, "errors": [], "documents": []}
    
    for file, doc_type_id in zip(files, type_ids):
        try:
            doc_type = await db.document_types.find_one({"id": doc_type_id.strip()}, {"_id": 0})
            if not doc_type:
                results["errors"].append(f"Document type {doc_type_id} not found")
                results["failed"] += 1
                continue
            
            # Check if document already exists
            existing = await db.employee_documents.find_one({
                "employee_id": employee_id,
                "document_type_id": doc_type_id.strip()
            })
            
            # Upload file to storage
            ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
            path = f"{APP_NAME}/documents/{employee_id}/{uuid.uuid4()}.{ext}"
            data = await file.read()
            result = put_object(path, data, file.content_type or "application/octet-stream")
            
            if existing:
                # Update existing document
                await db.employee_documents.update_one(
                    {"id": existing['id']},
                    {"$set": {
                        "file_url": result["path"],
                        "original_filename": file.filename,
                        "status": DocumentStatus.UPLOADED,
                        "uploaded_by": user['user_id'],
                        "uploaded_at": now,
                        "version_number": existing.get('version_number', 0) + 1
                    }}
                )
                doc_id = existing['id']
            else:
                # Create new document
                doc_id = str(uuid.uuid4())
                await db.employee_documents.insert_one({
                    "id": doc_id,
                    "employee_id": employee_id,
                    "document_type_id": doc_type_id.strip(),
                    "document_type_name": doc_type['name'],
                    "category": doc_type['category'],
                    "file_url": result["path"],
                    "original_filename": file.filename,
                    "status": DocumentStatus.UPLOADED,
                    "uploaded_by": user['user_id'],
                    "uploaded_at": now,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "expiry_date": None,
                    "notes": None,
                    "version_number": 1,
                    "created_at": now
                })
            
            results["successful"] += 1
            results["documents"].append({
                "id": doc_id,
                "document_type": doc_type['name'],
                "filename": file.filename
            })
            
            await log_audit_action(user['user_id'], "bulk_upload_document", "employee_document", doc_id, {
                "employee_id": employee_id,
                "document_type": doc_type['name'],
                "filename": file.filename
            })
            
        except Exception as e:
            results["errors"].append(f"Failed to upload {file.filename}: {str(e)}")
            results["failed"] += 1
    
    return results

# ==================== COMPLIANCE SUMMARY EXPORT ====================

@api_router.get("/employees/{employee_id}/compliance-summary")
async def get_compliance_summary(employee_id: str, user: dict = Depends(get_current_user)):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get all document types
    doc_types = await db.document_types.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    
    # Get employee documents
    emp_docs = await db.employee_documents.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    emp_docs_map = {d['document_type_id']: d for d in emp_docs}
    
    # Get policies
    policy_assignments = await db.policy_assignments.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    
    # Get training
    training_records = await db.training_records.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    
    # Get generated forms
    generated_forms = await db.generated_forms.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    
    # Build compliance checklist
    checklist = {}
    for doc_type in doc_types:
        category = doc_type['category']
        if category not in checklist:
            checklist[category] = []
        
        emp_doc = emp_docs_map.get(doc_type['id'])
        checklist[category].append({
            "name": doc_type['name'],
            "required": doc_type.get('required_before_active', False),
            "status": emp_doc['status'] if emp_doc else 'not_started',
            "uploaded_at": emp_doc.get('uploaded_at') if emp_doc else None,
            "reviewed_at": emp_doc.get('reviewed_at') if emp_doc else None,
            "expiry_date": emp_doc.get('expiry_date') if emp_doc else None
        })
    
    # Calculate stats
    total_required = sum(1 for dt in doc_types if dt.get('required_before_active'))
    approved_required = sum(1 for dt in doc_types if dt.get('required_before_active') and emp_docs_map.get(dt['id'], {}).get('status') == 'approved')
    
    return {
        "employee": {
            "id": employee['id'],
            "employee_code": employee['employee_code'],
            "name": f"{employee['first_name']} {employee['last_name']}",
            "role": employee['role'],
            "assignment": employee.get('assignment', 'Unassigned'),
            "status": employee['status'],
            "start_date": employee.get('start_date'),
            "manager": employee.get('manager_name')
        },
        "compliance_score": int((approved_required / total_required) * 100) if total_required > 0 else 0,
        "stats": {
            "total_documents": len(emp_docs),
            "approved_documents": sum(1 for d in emp_docs if d['status'] == 'approved'),
            "pending_documents": sum(1 for d in emp_docs if d['status'] in ['uploaded', 'under_review']),
            "missing_required": total_required - approved_required,
            "policies_assigned": len(policy_assignments),
            "policies_signed": sum(1 for p in policy_assignments if p['status'] == 'signed'),
            "training_records": len(training_records),
            "training_completed": sum(1 for t in training_records if t['status'] == 'completed'),
            "forms_completed": sum(1 for f in generated_forms if f['status'] in ['completed', 'signed_off'])
        },
        "checklist": checklist,
        "policies": policy_assignments,
        "training": training_records,
        "generated_forms": generated_forms,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

# ==================== SEED TEMPLATES ====================

@api_router.post("/seed-templates")
async def seed_templates(user: dict = Depends(require_admin)):
    """Seed comprehensive compliance form templates"""
    now = datetime.now(timezone.utc).isoformat()
    
    created_count = 0
    updated_count = 0
    
    for template_data in COMPLIANCE_TEMPLATES:
        # Check if template already exists
        existing = await db.templates.find_one({"name": template_data['name']})
        
        if existing:
            # Update existing template with new fields
            update_data = {
                "description": template_data.get('description', ''),
                "category": template_data.get('category', ''),
                "section": template_data.get('section', template_data.get('category', '')),
                "visibility": template_data.get('visibility', 'normal'),
                "role_specific": template_data.get('role_specific'),
                "form_fields": template_data.get('form_fields', []),
                "requires_employee_signature": template_data.get('requires_employee_signature', True),
                "requires_admin_signature": template_data.get('requires_admin_signature', True),
                "updated_at": now,
                "version": existing.get('version', 1) + 1
            }
            await db.templates.update_one({"id": existing['id']}, {"$set": update_data})
            updated_count += 1
        else:
            # Create new template
            template_doc = {
                "id": str(uuid.uuid4()),
                "name": template_data['name'],
                "description": template_data.get('description', ''),
                "category": template_data.get('category', ''),
                "section": template_data.get('section', template_data.get('category', '')),
                "visibility": template_data.get('visibility', 'normal'),
                "role_specific": template_data.get('role_specific'),
                "linked_document_type_id": None,
                "form_fields": template_data.get('form_fields', []),
                "requires_employee_signature": template_data.get('requires_employee_signature', True),
                "requires_admin_signature": template_data.get('requires_admin_signature', True),
                "content_html": "",
                "active": True,
                "version": 1,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id']
            }
            await db.templates.insert_one(template_doc)
            created_count += 1
    
    return {
        "message": "Templates seeded successfully",
        "created": created_count,
        "updated": updated_count,
        "total_templates": len(COMPLIANCE_TEMPLATES)
    }

@api_router.post("/generated-forms/bulk")
async def bulk_generate_forms(
    employee_id: str = Query(...),
    template_ids: List[str] = Query(...),
    user: dict = Depends(require_manager_or_admin)
):
    """Generate multiple forms for a single employee"""
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    auto_filled = await auto_fill_employee_data(employee_id)
    
    created_forms = []
    errors = []
    
    for template_id in template_ids:
        try:
            # Get template
            template = await db.templates.find_one({"id": template_id}, {"_id": 0})
            if not template:
                errors.append(f"Template {template_id} not found")
                continue
            
            # Check if form already exists for this employee/template
            existing = await db.generated_forms.find_one({
                "template_id": template_id,
                "employee_id": employee_id,
                "status": {"$nin": ["archived", "signed_off"]}
            })
            
            if existing:
                errors.append(f"Active form already exists for {template['name']}")
                continue
            
            form_id = str(uuid.uuid4())
            access_token = str(uuid.uuid4())
            
            form_doc = {
                "id": form_id,
                "template_id": template_id,
                "template_name": template['name'],
                "template_category": template['category'],
                "employee_id": employee_id,
                "employee_name": f"{employee['first_name']} {employee['last_name']}",
                "employee_code": employee['employee_code'],
                "form_data": auto_filled,
                "status": FormStatus.DRAFT,
                "employee_signature": None,
                "employee_signed_at": None,
                "admin_signature": None,
                "admin_signed_at": None,
                "admin_signoff_by": None,
                "pdf_url": None,
                "locked": False,
                "notes": None,
                "version": 1,
                "access_token": access_token,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id'],
                "sent_at": None,
                "viewed_at": None,
                "completed_at": None,
                "reviewed_at": None,
                "signed_off_at": None
            }
            await db.generated_forms.insert_one(form_doc)
            created_forms.append({
                "id": form_id,
                "template_name": template['name'],
                "status": "created"
            })
            
            await log_audit_action(user['user_id'], "bulk_create_form", "generated_form", form_id, {
                "template_name": template['name'],
                "employee_id": employee_id
            })
            
        except Exception as e:
            errors.append(f"Error creating form for template {template_id}: {str(e)}")
    
    return {
        "created": len(created_forms),
        "forms": created_forms,
        "errors": errors
    }

@api_router.post("/generated-forms/import-application")
async def import_application_form(
    employee_id: str = Form(...),
    application_file: UploadFile = File(...),
    cv_file: Optional[UploadFile] = File(None),
    user: dict = Depends(require_manager_or_admin)
):
    """Import an existing completed application form and optionally a CV"""
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find Application Form template
    application_template = await db.templates.find_one(
        {"name": {"$regex": "Application Form", "$options": "i"}},
        {"_id": 0}
    )
    
    if not application_template:
        raise HTTPException(status_code=404, detail="Application Form template not found")
    
    now = datetime.now(timezone.utc).isoformat()
    form_id = str(uuid.uuid4())
    access_token = str(uuid.uuid4())
    
    # Upload application file to storage
    try:
        app_file_content = await application_file.read()
        app_file_path = f"osabea-care/forms/{employee_id}/{form_id}/{application_file.filename}"
        put_object(app_file_path, app_file_content, application_file.content_type or "application/pdf")
        app_file_url = app_file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload application file: {str(e)}")
    
    # Upload CV if provided
    cv_file_url = None
    cv_doc_id = None
    if cv_file:
        try:
            cv_content = await cv_file.read()
            cv_path = f"osabea-care/documents/{employee_id}/{str(uuid.uuid4())}/{cv_file.filename}"
            put_object(cv_path, cv_content, cv_file.content_type or "application/pdf")
            cv_file_url = cv_path
            
            # Get or create CV document type
            cv_doc_type = await db.document_types.find_one(
                {"name": {"$regex": "CV|Resume", "$options": "i"}},
                {"_id": 0}
            )
            
            if cv_doc_type:
                cv_doc_id = str(uuid.uuid4())
                cv_doc = {
                    "id": cv_doc_id,
                    "employee_id": employee_id,
                    "document_type_id": cv_doc_type['id'],
                    "document_type_name": cv_doc_type['name'],
                    "requirement_id": "cv",
                    "requirement_name": "CV / Resume",
                    "category": "A_Application_Form",
                    "file_url": cv_file_url,
                    "original_filename": cv_file.filename,
                    "status": "uploaded",
                    "source_type": "imported",
                    "notes": "Imported with application form",
                    "uploaded_at": now,
                    "uploaded_by": user['user_id'],
                    "expiry_date": None,
                    "version_number": 1,
                    "verified": False,
                    "created_at": now,
                    "updated_at": now
                }
                # Check if CV already exists for this employee, replace if so
                existing_cv = await db.employee_documents.find_one({
                    "employee_id": employee_id,
                    "requirement_id": "cv"
                })
                if existing_cv:
                    cv_doc["version_number"] = existing_cv.get("version_number", 1) + 1
                    await db.employee_documents.update_one(
                        {"id": existing_cv["id"]},
                        {"$set": {
                            "file_url": cv_file_url,
                            "original_filename": cv_file.filename,
                            "version_number": cv_doc["version_number"],
                            "uploaded_at": now,
                            "updated_at": now
                        }}
                    )
                    cv_doc_id = existing_cv["id"]
                else:
                    await db.employee_documents.insert_one(cv_doc)
        except Exception as e:
            # Log but don't fail the whole import
            print(f"Warning: Failed to upload CV: {str(e)}")
    
    # Auto-fill employee data
    auto_filled = await auto_fill_employee_data(employee_id)
    
    # Create the generated form with imported status
    form_doc = {
        "id": form_id,
        "template_id": application_template['id'],
        "template_name": application_template['name'],
        "template_category": application_template.get('category', 'Application'),
        "employee_id": employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee['employee_code'],
        "form_data": auto_filled,
        "status": "completed_imported",  # Special status for imported forms
        "employee_signature": None,
        "employee_signed_at": None,
        "admin_signature": None,
        "admin_signed_at": None,
        "admin_signoff_by": None,
        "pdf_url": app_file_url,  # Store the uploaded file as the PDF
        "locked": True,  # Lock the form since it's imported
        "notes": f"Imported from existing application. Original file: {application_file.filename}",
        "version": 1,
        "access_token": access_token,
        "created_at": now,
        "updated_at": now,
        "created_by": user['user_id'],
        "sent_at": None,
        "viewed_at": now,
        "completed_at": now,  # Mark as completed immediately
        "reviewed_at": None,
        "signed_off_at": None,
        "imported": True,  # Flag to indicate this is an imported form
        "original_filename": application_file.filename
    }
    
    await db.generated_forms.insert_one(form_doc)
    
    # Also create an employee document record for the Application Form
    app_doc_type = await db.document_types.find_one(
        {"name": {"$regex": "Application Form", "$options": "i"}},
        {"_id": 0}
    )
    
    if app_doc_type:
        app_doc_id = str(uuid.uuid4())
        app_doc = {
            "id": app_doc_id,
            "employee_id": employee_id,
            "document_type_id": app_doc_type['id'],
            "document_type_name": "Application Form",
            "file_url": app_file_url,
            "original_filename": application_file.filename,
            "status": "approved",  # Auto-approve imported applications
            "notes": "Imported - existing completed application",
            "uploaded_at": now,
            "uploaded_by": user['user_id'],
            "expiry_date": None,
            "created_at": now,
            "updated_at": now
        }
        await db.employee_documents.insert_one(app_doc)
    
    await log_audit_action(user['user_id'], "import_application", "generated_form", form_id, {
        "template_name": application_template['name'],
        "employee_id": employee_id,
        "original_file": application_file.filename,
        "cv_included": cv_file is not None
    })
    
    return {
        "success": True,
        "form_id": form_id,
        "form_status": "completed_imported",
        "application_file": application_file.filename,
        "cv_file": cv_file.filename if cv_file else None,
        "cv_document_id": cv_doc_id,
        "message": "Application form imported successfully"
    }

# Form type to requirement mapping for imports
FORM_TYPE_TO_REQUIREMENT = {
    "reference": {"requirement_id": None, "category": "H_References"},  # Multiple references, handled specially
    "reference_1": {"requirement_id": "reference_1", "category": "H_References"},
    "reference_2": {"requirement_id": "reference_2", "category": "H_References"},
    "health_screening": {"requirement_id": "health_screening", "category": "F_Health_Screening"},
    "contract": {"requirement_id": "contract", "category": "L_Contract"},
    "induction": {"requirement_id": "induction", "category": "J_Induction_Shadowing_Observations"},
    "handbook": {"requirement_id": "handbook", "category": "O_Other"},
    "recruitment_checklist": {"requirement_id": "recruitment_checklist", "category": "B_Recruitment_Checklist"},
    "personal_info": {"requirement_id": "personal_info", "category": "C_Personal_Information"},
    "interview_record": {"requirement_id": "interview_record", "category": "D_Interview"},
    "equal_opportunities": {"requirement_id": "equal_opportunities", "category": "E_Equal_Opportunities"},
    "application_form": {"requirement_id": "application_form", "category": "A_Application_Form"},
}

@api_router.post("/generated-forms/import-document")
async def import_form_document(
    employee_id: str = Form(...),
    form_type: str = Form(...),  # reference_1, reference_2, health_screening, contract
    document_file: UploadFile = File(...),
    reference_number: Optional[int] = Form(None),  # For references: 1 or 2
    notes: Optional[str] = Form(None),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Import an existing completed document for various form types.
    ENFORCES ONE FORM PER REQUIREMENT - updates existing rather than creating duplicates.
    """
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate form type
    if form_type not in FORM_TYPE_TO_REQUIREMENT:
        raise HTTPException(status_code=400, detail=f"Invalid form type. Valid types: {list(FORM_TYPE_TO_REQUIREMENT.keys())}")
    
    form_config = FORM_TYPE_TO_REQUIREMENT[form_type]
    requirement_id = form_config['requirement_id']
    category = form_config['category']
    
    # Map form type to template name for display
    display_names = {
        "reference_1": "Reference 1",
        "reference_2": "Reference 2",
        "health_screening": "Health Screening Questionnaire",
        "contract": "Contract Acknowledgement",
        "induction": "Induction & Competency Assessment",
        "handbook": "Employee Handbook Acknowledgement",
    }
    display_name = display_names.get(form_type, form_type.replace("_", " ").title())
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Upload file to storage
    try:
        file_content = await document_file.read()
        file_ext = document_file.filename.split('.')[-1] if '.' in document_file.filename else 'pdf'
        employee_name = f"{employee['first_name']}{employee['last_name']}"
        storage_filename = f"{employee_name}_{form_type}_{datetime.now(timezone.utc).strftime('%d-%m-%Y')}.{file_ext}"
        file_path = f"osabea-care/forms/{employee_id}/{requirement_id}/{storage_filename}"
        put_object(file_path, file_content, document_file.content_type or "application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    # CHECK FOR EXISTING FORM for this requirement - UPDATE instead of creating duplicate
    existing_form = await db.generated_forms.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id
    })
    
    if existing_form:
        # UPDATE existing form instead of creating new one
        update_data = {
            "pdf_url": file_path,
            "status": "completed_imported",
            "locked": True,
            "notes": notes or f"Imported from existing document. Original file: {document_file.filename}",
            "original_filename": document_file.filename,
            "updated_at": now,
            "completed_at": now,
            "version": existing_form.get('version', 1) + 1
        }
        await db.generated_forms.update_one({"id": existing_form['id']}, {"$set": update_data})
        form_id = existing_form['id']
        action = "updated"
    else:
        # Create new form with requirement_id
        form_id = str(uuid.uuid4())
        access_token = str(uuid.uuid4())
        auto_filled = await auto_fill_employee_data(employee_id)
        
        form_doc = {
            "id": form_id,
            "template_id": str(uuid.uuid4()),
            "template_name": display_name,
            "template_category": category,
            "employee_id": employee_id,
            "employee_name": f"{employee['first_name']} {employee['last_name']}",
            "employee_code": employee.get('employee_code', ''),
            "form_data": auto_filled,
            "status": "completed_imported",
            "employee_signature": None,
            "employee_signed_at": None,
            "admin_signature": None,
            "admin_signed_at": None,
            "admin_signoff_by": None,
            "pdf_url": file_path,
            "locked": True,
            "notes": notes or f"Imported from existing document. Original file: {document_file.filename}",
            "version": 1,
            "access_token": access_token,
            "created_at": now,
            "updated_at": now,
            "created_by": user['user_id'],
            "sent_at": None,
            "viewed_at": now,
            "completed_at": now,
            "reviewed_at": None,
            "signed_off_at": None,
            "imported": True,
            "original_filename": document_file.filename,
            "requirement_id": requirement_id  # CRITICAL: Link form to requirement
        }
        await db.generated_forms.insert_one(form_doc)
        action = "created"
    
    # Also update/create employee document record
    existing_doc = await db.employee_documents.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id
    })
    
    if existing_doc:
        # Update existing document
        doc_update = {
            "file_url": file_path,
            "original_filename": document_file.filename,
            "status": "approved",
            "source_type": "imported",
            "source_form_id": form_id,
            "notes": notes or "Imported document (updated)",
            "uploaded_at": now,
            "updated_at": now,
            "version_number": existing_doc.get("version_number", 1) + 1
        }
        await db.employee_documents.update_one({"id": existing_doc["id"]}, {"$set": doc_update})
        doc_id = existing_doc["id"]
    else:
        # Create new document record
        doc_id = str(uuid.uuid4())
        doc_record = {
            "id": doc_id,
            "employee_id": employee_id,
            "document_type_id": str(uuid.uuid4()),
            "document_type_name": display_name,
            "requirement_id": requirement_id,
            "requirement_name": display_name,
            "category": category,
            "file_url": file_path,
            "original_filename": document_file.filename,
            "status": "approved",
            "source_type": "imported",
            "source_form_id": form_id,
            "notes": notes or "Imported document",
            "uploaded_at": now,
            "uploaded_by": user['user_id'],
            "expiry_date": None,
            "version_number": 1,
            "verified": False,
            "created_at": now,
            "updated_at": now
        }
        await db.employee_documents.insert_one(doc_record)
    
    await log_audit_action(user['user_id'], f"import_document_{action}", "generated_form", form_id, {
        "form_type": form_type,
        "requirement_id": requirement_id,
        "employee_id": employee_id,
        "original_file": document_file.filename
    })
    
    return {
        "success": True,
        "form_id": form_id,
        "document_id": doc_id,
        "form_type": form_type,
        "requirement_id": requirement_id,
        "form_status": "completed_imported",
        "action": action,
        "original_filename": document_file.filename,
        "message": f"{display_name} {action} successfully"
    }

# ==================== EMAIL TEMPLATES ====================

@api_router.get("/email-templates")
async def get_email_templates(user: dict = Depends(require_manager_or_admin)):
    """Get all available email templates"""
    return EMAIL_TEMPLATES

@api_router.get("/email-templates/{template_key}")
async def get_email_template(template_key: str, user: dict = Depends(require_manager_or_admin)):
    """Get a specific email template by key"""
    if template_key not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Email template not found")
    return EMAIL_TEMPLATES[template_key]

class SendEmailRequest(BaseModel):
    template_key: str
    employee_id: str
    custom_data: Optional[Dict[str, str]] = None

@api_router.post("/send-email")
async def send_templated_email(request: SendEmailRequest, user: dict = Depends(require_manager_or_admin)):
    """Send an email using a template"""
    if not resend.api_key:
        raise HTTPException(status_code=503, detail="Email service not configured")
    
    if request.template_key not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Get employee
    employee = await db.employees.find_one({"id": request.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    template = EMAIL_TEMPLATES[request.template_key]
    
    # Build template variables
    variables = {
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee['employee_code'],
        "portal_url": os.environ.get('PORTAL_URL', 'https://portal.osabea.care'),
        **(request.custom_data or {})
    }
    
    # Substitute variables in template
    subject = template['subject']
    body = template['body']
    for key, value in variables.items():
        body = body.replace(f"{{{key}}}", str(value))
        subject = subject.replace(f"{{{key}}}", str(value))
    
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [employee['email']],
            "subject": subject,
            "html": f"<div style='font-family: Arial, sans-serif; line-height: 1.6;'>{body.replace(chr(10), '<br>')}</div>"
        })
        
        await log_audit_action(user['user_id'], "send_email", "email", request.template_key, {
            "employee_id": request.employee_id,
            "template": request.template_key
        })
        
        return {"message": "Email sent successfully", "recipient": employee['email']}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# ==================== COMPLIANCE CENTRE - ORG POLICIES ====================

# Core policies that should exist as placeholders
# Comprehensive Organisation Policies organised by category
CORE_POLICIES = [
    # Core Policies - Essential Safeguarding & Safety
    {"name": "Safeguarding Adults Policy", "category": "Core"},
    {"name": "Safeguarding Children Policy", "category": "Core"},
    {"name": "Mental Capacity Act & DoLS Policy", "category": "Core"},
    {"name": "Health & Safety Policy", "category": "Core"},
    {"name": "Fire Safety Policy", "category": "Core"},
    {"name": "First Aid Policy", "category": "Core"},
    {"name": "Equality, Diversity & Inclusion Policy", "category": "Core"},
    {"name": "Whistleblowing Policy", "category": "Core"},
    
    # Clinical Policies - Care & Medical
    {"name": "Medication Policy", "category": "Clinical"},
    {"name": "Infection Prevention & Control Policy", "category": "Clinical"},
    {"name": "Manual Handling Policy", "category": "Clinical"},
    {"name": "COSHH Policy", "category": "Clinical"},
    {"name": "Care Planning Policy", "category": "Clinical"},
    {"name": "End of Life Care Policy", "category": "Clinical"},
    {"name": "Nutrition & Hydration Policy", "category": "Clinical"},
    {"name": "Pressure Ulcer Prevention Policy", "category": "Clinical"},
    
    # Operational Policies - Day-to-Day Operations
    {"name": "Lone Working Policy", "category": "Operational"},
    {"name": "Risk Assessment Policy", "category": "Operational"},
    {"name": "Record Keeping Policy", "category": "Operational"},
    {"name": "Confidentiality Policy", "category": "Operational"},
    {"name": "Complaints Policy", "category": "Operational"},
    {"name": "Incident Reporting Policy", "category": "Operational"},
    {"name": "Business Continuity Policy", "category": "Operational"},
    {"name": "Service User Feedback Policy", "category": "Operational"},
    
    # Governance Policies - HR & Regulatory
    {"name": "Recruitment & Selection Policy", "category": "Governance"},
    {"name": "DBS & Vetting Policy", "category": "Governance"},
    {"name": "Induction & Probation Policy", "category": "Governance"},
    {"name": "Training & Development Policy", "category": "Governance"},
    {"name": "Supervision & Appraisal Policy", "category": "Governance"},
    {"name": "Disciplinary & Grievance Policy", "category": "Governance"},
    {"name": "Data Protection & GDPR Policy", "category": "Governance"},
    {"name": "Code of Conduct", "category": "Governance"},
]

@api_router.post("/compliance/seed-policies")
async def seed_org_policies(user: dict = Depends(require_admin)):
    """Seed core organisation policies as placeholders"""
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
                "file_url": None,
                "original_filename": None,
                "review_date": None,
                "last_reviewed_at": None,
                "reviewed_by": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
                "created_by": user['user_id']
            }
            await db.org_policies.insert_one(policy_doc)
            created += 1
    
    return {"message": f"Created {created} policy placeholders", "total": len(CORE_POLICIES)}

@api_router.get("/compliance/policies", response_model=List[OrgPolicyResponse])
async def get_org_policies(
    category: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all organisation policies"""
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    policies = await db.org_policies.find(query, {"_id": 0}).sort("category", 1).to_list(100)
    
    # Check for expired policies based on review date
    now = datetime.now(timezone.utc)
    for policy in policies:
        if policy.get("review_date"):
            try:
                review_str = policy["review_date"]
                if isinstance(review_str, datetime):
                    review_date = review_str if review_str.tzinfo else review_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(review_str):
                    review_date = datetime.fromisoformat(review_str.replace('Z', '+00:00'))
                else:
                    review_date = datetime.fromisoformat(f"{review_str}T00:00:00+00:00")
                    
                if review_date < now and policy["status"] == "active":
                    policy["status"] = "expired"
            except Exception:
                pass  # Keep current status if date parsing fails
    
    return policies

@api_router.get("/compliance/policies/{policy_id}", response_model=OrgPolicyResponse)
async def get_org_policy(policy_id: str, user: dict = Depends(get_current_user)):
    """Get a specific organisation policy"""
    policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@api_router.post("/compliance/policies/{policy_id}/upload")
async def upload_org_policy_document(
    policy_id: str,
    file: UploadFile = File(...),
    version: Optional[str] = None,
    review_date: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Upload a document for an organisation policy"""
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Upload file
    content = await file.read()
    path = f"{APP_NAME}/policies/{policy_id}/{str(uuid.uuid4())}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"
    result = put_object(path, content, content_type)
    
    update_data = {
        "file_url": result["path"],
        "original_filename": file.filename,
        "status": "active",
        "last_reviewed_at": now,
        "reviewed_by": user['user_id'],
        "updated_at": now
    }
    
    if version:
        update_data["version"] = version
    if review_date:
        update_data["review_date"] = review_date
    
    await db.org_policies.update_one({"id": policy_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "upload_org_policy", "org_policy", policy_id, {
        "filename": file.filename,
        "policy_name": policy["name"]
    })
    
    updated_policy = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    return updated_policy

@api_router.put("/compliance/policies/{policy_id}", response_model=OrgPolicyResponse)
async def update_org_policy(
    policy_id: str,
    update: OrgPolicyUpdate,
    user: dict = Depends(require_admin)
):
    """Update an organisation policy"""
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.org_policies.update_one({"id": policy_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "update_org_policy", "org_policy", policy_id, update_data)
    
    updated = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    return updated

# ==================== COMPLIANCE CENTRE - INSURANCE ====================

# Insurance & Certificates required for care agency compliance
INSURANCE_TYPES = [
    {"name": "Public Liability Insurance", "type": "public_liability"},
    {"name": "Employer's Liability Insurance", "type": "employers_liability"},
    {"name": "Professional Indemnity Insurance", "type": "professional_indemnity"},
    {"name": "CQC Registration Certificate", "type": "cqc_registration"},
    {"name": "ICO Registration Certificate", "type": "ico_registration"},
    {"name": "Company Registration Certificate", "type": "company_registration"},
]

@api_router.post("/compliance/seed-insurance")
async def seed_insurance_docs(user: dict = Depends(require_admin)):
    """Seed insurance document placeholders"""
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    
    for ins in INSURANCE_TYPES:
        existing = await db.insurance_docs.find_one({"insurance_type": ins["type"]})
        if not existing:
            doc = {
                "id": str(uuid.uuid4()),
                "name": ins["name"],
                "insurance_type": ins["type"],
                "status": "missing",
                "file_url": None,
                "original_filename": None,
                "expiry_date": None,
                "policy_number": None,
                "provider": None,
                "notes": None,
                "created_at": now,
                "updated_at": now
            }
            await db.insurance_docs.insert_one(doc)
            created += 1
    
    return {"message": f"Created {created} insurance placeholders", "total": len(INSURANCE_TYPES)}

@api_router.get("/compliance/insurance", response_model=List[InsuranceDocResponse])
async def get_insurance_docs(user: dict = Depends(get_current_user)):
    """Get all insurance documents"""
    docs = await db.insurance_docs.find({}, {"_id": 0}).to_list(20)
    
    # Calculate status based on expiry date
    now = datetime.now(timezone.utc)
    thirty_days = now + timedelta(days=30)
    
    for doc in docs:
        if not doc.get("file_url"):
            doc["status"] = "missing"
        elif doc.get("expiry_date"):
            try:
                expiry_str = doc["expiry_date"]
                # Handle various date formats
                if isinstance(expiry_str, datetime):
                    expiry = expiry_str if expiry_str.tzinfo else expiry_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(expiry_str):
                    expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    # Simple date format YYYY-MM-DD
                    expiry = datetime.fromisoformat(f"{expiry_str}T00:00:00+00:00")
                
                if expiry < now:
                    doc["status"] = "expired"
                elif expiry < thirty_days:
                    doc["status"] = "expiring_soon"
                else:
                    doc["status"] = "valid"
            except Exception:
                doc["status"] = "valid"
        else:
            doc["status"] = "valid"
    
    return docs

@api_router.post("/compliance/insurance/{insurance_id}/upload")
async def upload_insurance_doc(
    insurance_id: str,
    file: UploadFile = File(...),
    expiry_date: str = Query(...),
    policy_number: Optional[str] = None,
    provider: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Upload an insurance document"""
    insurance = await db.insurance_docs.find_one({"id": insurance_id})
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    content = await file.read()
    path = f"{APP_NAME}/insurance/{insurance_id}/{str(uuid.uuid4())}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"
    result = put_object(path, content, content_type)
    
    update_data = {
        "file_url": result["path"],
        "original_filename": file.filename,
        "expiry_date": expiry_date,
        "status": "valid",
        "updated_at": now
    }
    
    if policy_number:
        update_data["policy_number"] = policy_number
    if provider:
        update_data["provider"] = provider
    
    await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "upload_insurance", "insurance", insurance_id, {
        "filename": file.filename,
        "expiry_date": expiry_date
    })
    
    updated = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0})
    return updated

# ==================== FILE SERVING ENDPOINTS ====================

@api_router.get("/compliance/policies/{policy_id}/file")
async def serve_policy_file(policy_id: str, user: dict = Depends(get_current_user)):
    """Serve a policy document file"""
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    file_path = policy.get("file_url")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file uploaded for this policy")
    
    try:
        content, content_type = get_object(file_path)
        filename = policy.get("original_filename", "policy.pdf")
        # Sanitize filename for Content-Disposition header
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to retrieve policy file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file")

@api_router.get("/compliance/policies/{policy_id}/download")
async def download_policy_file(policy_id: str, user: dict = Depends(get_current_user)):
    """Download a policy document file"""
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    file_path = policy.get("file_url")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file uploaded for this policy")
    
    try:
        content, content_type = get_object(file_path)
        filename = policy.get("original_filename", "policy.pdf")
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to download policy file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file")

@api_router.get("/compliance/insurance/{insurance_id}/file")
async def serve_insurance_file(insurance_id: str, user: dict = Depends(get_current_user)):
    """Serve an insurance/certificate document file"""
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    file_path = doc.get("file_url")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file uploaded for this document")
    
    try:
        content, content_type = get_object(file_path)
        filename = doc.get("original_filename", "document.pdf")
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to retrieve insurance file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file")

@api_router.get("/compliance/insurance/{insurance_id}/download")
async def download_insurance_file(insurance_id: str, user: dict = Depends(get_current_user)):
    """Download an insurance/certificate document file"""
    doc = await db.insurance_docs.find_one({"id": insurance_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Insurance document not found")
    
    file_path = doc.get("file_url")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file uploaded for this document")
    
    try:
        content, content_type = get_object(file_path)
        filename = doc.get("original_filename", "document.pdf")
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to download insurance file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file")

# ==================== COMPLIANCE CENTRE - INCIDENT LOGS ====================

async def generate_incident_reference():
    """Generate unique incident reference number"""
    year = datetime.now().year
    count = await db.incident_logs.count_documents({"reference_number": {"$regex": f"^INC-{year}"}})
    return f"INC-{year}-{str(count + 1).zfill(4)}"

@api_router.get("/compliance/incidents", response_model=List[IncidentLogResponse])
async def get_incident_logs(
    incident_type: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all incident/outbreak logs"""
    query = {}
    if incident_type:
        query["incident_type"] = incident_type
    if status:
        query["status"] = status
    
    incidents = await db.incident_logs.find(query, {"_id": 0}).sort("reported_at", -1).to_list(500)
    return incidents

@api_router.post("/compliance/incidents", response_model=IncidentLogResponse)
async def create_incident_log(
    incident: IncidentLogCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new incident/outbreak log"""
    now = datetime.now(timezone.utc).isoformat()
    ref_number = await generate_incident_reference()
    
    incident_doc = {
        "id": str(uuid.uuid4()),
        "reference_number": ref_number,
        **incident.model_dump(),
        "status": "open",
        "reported_by": user['user_id'],
        "reported_at": now,
        "closed_at": None,
        "closed_by": None,
        "attachments": []
    }
    
    await db.incident_logs.insert_one(incident_doc)
    
    await log_audit_action(user['user_id'], "create_incident", "incident_log", incident_doc["id"], {
        "reference_number": ref_number,
        "type": incident.incident_type
    })
    
    return {**incident_doc, "_id": None}

@api_router.put("/compliance/incidents/{incident_id}", response_model=IncidentLogResponse)
async def update_incident_log(
    incident_id: str,
    update: IncidentLogUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update an incident log"""
    incident = await db.incident_logs.find_one({"id": incident_id})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if update.status == "closed" and incident["status"] != "closed":
        update_data["closed_at"] = datetime.now(timezone.utc).isoformat()
        update_data["closed_by"] = user['user_id']
    
    await db.incident_logs.update_one({"id": incident_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "update_incident", "incident_log", incident_id, update_data)
    
    updated = await db.incident_logs.find_one({"id": incident_id}, {"_id": 0})
    return updated

# ==================== COMPLIANCE CENTRE - REPORTS ====================

@api_router.get("/compliance/reports/staff-dbs")
async def get_staff_dbs_report(user: dict = Depends(get_current_user)):
    """Get staff list with DBS dates"""
    employees = await db.employees.find(
        {"status": {"$in": ["active", "onboarding"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "employee_code": 1, "role": 1, "assignment": 1}
    ).to_list(500)
    
    report = []
    for emp in employees:
        # Get DBS document
        dbs_doc = await db.employee_documents.find_one(
            {"employee_id": emp["id"], "document_type_name": {"$regex": "DBS", "$options": "i"}},
            {"_id": 0}
        )
        
        report.append({
            "employee_id": emp["id"],
            "employee_code": emp["employee_code"],
            "name": f"{emp['first_name']} {emp['last_name']}",
            "role": emp.get("role"),
            "assignment": emp.get("assignment", "Unassigned"),
            "dbs_status": dbs_doc["status"] if dbs_doc else "missing",
            "dbs_expiry": dbs_doc.get("expiry_date") if dbs_doc else None,
            "dbs_number": dbs_doc.get("notes") if dbs_doc else None
        })
    
    return {"report": report, "total": len(report), "generated_at": datetime.now(timezone.utc).isoformat()}

@api_router.get("/compliance/reports/training")
async def get_staff_training_report(
    months: int = 12,
    user: dict = Depends(get_current_user)
):
    """Get staff training report for last N months"""
    employees = await db.employees.find(
        {"status": {"$in": ["active", "onboarding"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "employee_code": 1, "role": 1}
    ).to_list(500)
    
    report = []
    for emp in employees:
        training_records = await db.training_records.find(
            {"employee_id": emp["id"]},
            {"_id": 0}
        ).to_list(100)
        
        completed = [t for t in training_records if t.get("status") == "completed"]
        pending = [t for t in training_records if t.get("status") in ["scheduled", "in_progress"]]
        
        # Check for expiring training
        now = datetime.now(timezone.utc)
        thirty_days = now + timedelta(days=30)
        expiring = []
        for t in completed:
            if t.get("expiry_date"):
                try:
                    expiry_str = t["expiry_date"]
                    if isinstance(expiry_str, datetime):
                        exp = expiry_str if expiry_str.tzinfo else expiry_str.replace(tzinfo=timezone.utc)
                    elif 'T' in str(expiry_str):
                        exp = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                    else:
                        exp = datetime.fromisoformat(f"{expiry_str}T00:00:00+00:00")
                    if exp < thirty_days:
                        expiring.append(t["training_name"])
                except (ValueError, TypeError):
                    pass
        
        report.append({
            "employee_id": emp["id"],
            "employee_code": emp["employee_code"],
            "name": f"{emp['first_name']} {emp['last_name']}",
            "role": emp.get("role"),
            "completed_count": len(completed),
            "pending_count": len(pending),
            "expiring_soon": expiring,
            "training_records": training_records
        })
    
    return {
        "report": report,
        "total_employees": len(report),
        "period_months": months,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/compliance/dashboard")
async def get_compliance_dashboard(user: dict = Depends(get_current_user)):
    """Get compliance centre dashboard summary"""
    
    # Policies summary
    policies = await db.org_policies.find({}, {"_id": 0}).to_list(50)
    policies_active = len([p for p in policies if p.get("status") == "active"])
    policies_missing = len([p for p in policies if p.get("status") == "missing"])
    policies_expired = len([p for p in policies if p.get("status") == "expired"])
    
    # Insurance summary
    insurance = await db.insurance_docs.find({}, {"_id": 0}).to_list(10)
    now = datetime.now(timezone.utc)
    insurance_valid = 0
    insurance_expiring = 0
    insurance_expired = 0
    insurance_missing = 0
    
    for ins in insurance:
        if not ins.get("file_url"):
            insurance_missing += 1
        elif ins.get("expiry_date"):
            try:
                expiry_str = ins["expiry_date"]
                # Handle various date formats
                if isinstance(expiry_str, datetime):
                    exp = expiry_str if expiry_str.tzinfo else expiry_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(expiry_str):
                    exp = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    # Simple date format YYYY-MM-DD
                    exp = datetime.fromisoformat(f"{expiry_str}T00:00:00+00:00")
                
                if exp < now:
                    insurance_expired += 1
                elif exp < now + timedelta(days=30):
                    insurance_expiring += 1
                else:
                    insurance_valid += 1
            except Exception:
                insurance_valid += 1
        else:
            insurance_valid += 1
    
    # Incidents summary
    incidents_open = await db.incident_logs.count_documents({"status": {"$in": ["open", "investigating"]}})
    incidents_total = await db.incident_logs.count_documents({})
    
    # Staff compliance
    active_staff = await db.employees.count_documents({"status": {"$in": ["active", "onboarding"]}})
    
    return {
        "policies": {
            "total": len(policies),
            "active": policies_active,
            "missing": policies_missing,
            "expired": policies_expired
        },
        "insurance": {
            "total": len(insurance),
            "valid": insurance_valid,
            "expiring_soon": insurance_expiring,
            "expired": insurance_expired,
            "missing": insurance_missing
        },
        "incidents": {
            "open": incidents_open,
            "total": incidents_total
        },
        "staff": {
            "active": active_staff
        }
    }

@api_router.post("/contact")
async def submit_contact_form(form: ContactForm):
    contact_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    contact_doc = {
        "id": contact_id,
        **form.model_dump(),
        "status": "new",
        "created_at": now
    }
    await db.contact_submissions.insert_one(contact_doc)
    
    # Send notification email if configured
    if resend.api_key:
        try:
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [os.environ.get('ADMIN_EMAIL', 'admin@osabea.care')],
                "subject": f"New Contact Form: {form.subject}",
                "html": f"""
                <h2>New Contact Form Submission</h2>
                <p><strong>Name:</strong> {form.full_name}</p>
                <p><strong>Email:</strong> {form.email}</p>
                <p><strong>Phone:</strong> {form.phone or 'N/A'}</p>
                <p><strong>Organisation:</strong> {form.organisation or 'N/A'}</p>
                <p><strong>Subject:</strong> {form.subject}</p>
                <p><strong>Message:</strong></p>
                <p>{form.message}</p>
                """
            })
        except Exception as e:
            logger.error(f"Failed to send contact notification: {e}")
    
    return {"message": "Thank you for your enquiry. We will be in touch soon.", "id": contact_id}

@api_router.post("/apply")
async def submit_application(form: ApplicationForm):
    app_id = str(uuid.uuid4())
    employee_code = await generate_employee_code()
    now = datetime.now(timezone.utc).isoformat()
    
    # Create employee record
    employee_doc = {
        "id": app_id,
        "employee_code": employee_code,
        "first_name": form.first_name,
        "last_name": form.last_name,
        "email": form.email,
        "phone": form.phone,
        "role": form.role_applied,
        "assignment": "Unassigned",
        "status": EmployeeStatus.NEW,
        "start_date": None,
        "manager_name": None,
        "driver_status": False,
        "notes": f"Application received. Availability: {form.availability or 'Not specified'}. Experience: {form.experience_summary or 'Not provided'}. How heard: {form.how_heard or 'Not specified'}",
        "completion_percentage": 0,
        "right_to_work": form.right_to_work,
        "has_dbs": form.has_dbs,
        "address": form.address,
        "postcode": form.postcode,
        "created_at": now,
        "updated_at": now
    }
    await db.employees.insert_one(employee_doc)
    
    # Create user account for applicant
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    temp_password = str(uuid.uuid4())[:8]
    user_doc = {
        "user_id": user_id,
        "email": form.email,
        "password": hash_password(temp_password),
        "name": f"{form.first_name} {form.last_name}",
        "role": UserRole.EMPLOYEE,
        "assignment": "Unassigned",
        "picture": None,
        "employee_id": app_id,
        "created_at": now
    }
    await db.users.insert_one(user_doc)
    
    return {"message": "Your application has been submitted successfully. We will review it and be in touch.", "reference": employee_code}

@api_router.get("/assignments")
async def get_assignments():
    """Get all unique assignments/placements"""
    assignments = await db.employees.distinct("assignment")
    return [a for a in assignments if a and a != "Unassigned"]

@api_router.get("/roles")
async def get_roles():
    return [
        "Care Assistant",
        "Senior Care Assistant",
        "Support Worker",
        "Healthcare Assistant",
        "Live-in Carer",
        "Night Carer",
        "Team Leader",
        "Care Coordinator"
    ]

# ==================== EMAIL ROUTES ====================

@api_router.post("/send-email")
async def send_email(request: EmailRequest, user: dict = Depends(require_admin)):
    if not resend.api_key:
        raise HTTPException(status_code=500, detail="Email service not configured")
    
    try:
        email = await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [request.recipient_email],
            "subject": request.subject,
            "html": request.html_content
        })
        return {"status": "success", "message": f"Email sent to {request.recipient_email}", "email_id": email.get("id")}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@api_router.post("/request-document")
async def request_document(
    employee_id: str,
    document_type_id: str,
    message: Optional[str] = None,
    due_date: Optional[str] = None,
    send_email: bool = True,
    user: dict = Depends(require_manager_or_admin)
):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    doc_type = await db.document_types.find_one({"id": document_type_id}, {"_id": 0})
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create or update document record
    existing_doc = await db.employee_documents.find_one({"employee_id": employee_id, "document_type_id": document_type_id})
    
    if existing_doc:
        await db.employee_documents.update_one(
            {"id": existing_doc['id']},
            {"$set": {"status": DocumentStatus.REQUESTED, "notes": message}}
        )
        doc_id = existing_doc['id']
    else:
        doc_id = str(uuid.uuid4())
        doc_data = {
            "id": doc_id,
            "employee_id": employee_id,
            "document_type_id": document_type_id,
            "document_type_name": doc_type['name'],
            "category": doc_type['category'],
            "file_url": None,
            "original_filename": None,
            "status": DocumentStatus.REQUESTED,
            "uploaded_by": None,
            "uploaded_at": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "expiry_date": None,
            "notes": message,
            "version_number": 1,
            "created_at": now
        }
        await db.employee_documents.insert_one(doc_data)
    
    await log_audit_action(user['user_id'], "request_document", "employee_document", doc_id, {"document_type": doc_type['name'], "employee_id": employee_id})
    
    # Send email notification
    if send_email and resend.api_key:
        try:
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [employee['email']],
                "subject": "Document request from Osabea Healthcare Solutions",
                "html": f"""
                <h2>Document Request</h2>
                <p>Dear {employee['first_name']},</p>
                <p>We need you to upload the following document to complete your compliance file:</p>
                <p><strong>{doc_type['name']}</strong></p>
                {f'<p>{message}</p>' if message else ''}
                {f'<p>Due date: {due_date}</p>' if due_date else ''}
                <p>Please log in to your portal and upload the requested document.</p>
                <p>Thank you,<br>Osabea Healthcare Solutions Team</p>
                """
            })
        except Exception as e:
            logger.error(f"Failed to send document request email: {e}")
    
    return {"message": "Document request created", "document_id": doc_id}

# ==================== SEED DATA ====================

@api_router.post("/seed-data")
async def seed_data():
    """Seed initial document types based on care compliance checklist"""
    
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
        {"name": "Consent to Obtain References", "category": "References", "required_before_active": True, "sort_order": 40},
        {"name": "Reference 1", "category": "References", "required_before_active": True, "sort_order": 41},
        {"name": "Reference 2", "category": "References", "required_before_active": True, "sort_order": 42},
        {"name": "Reference 3", "category": "References", "required_before_active": False, "sort_order": 43},
        {"name": "Reference 4", "category": "References", "required_before_active": False, "sort_order": 44},
        
        # DBS
        {"name": "DBS Form / Update Service", "category": "DBS", "required_before_active": True, "sort_order": 50},
        {"name": "DBS Certificate", "category": "DBS", "required_before_active": True, "has_expiry": True, "sort_order": 51},
        {"name": "DBS Risk Assessment", "category": "DBS", "required_before_active": False, "sort_order": 52},
        
        # Consent Forms
        {"name": "Digital Image Consent Form", "category": "Consent Forms", "required_before_active": True, "sort_order": 60},
        {"name": "Electronic File Consent Form", "category": "Consent Forms", "required_before_active": True, "sort_order": 61},
        {"name": "Confidentiality Form", "category": "Consent Forms", "required_before_active": True, "sort_order": 62},
        {"name": "Privacy Form", "category": "Consent Forms", "required_before_active": True, "sort_order": 63},
        
        # Employment Documents
        {"name": "Job Description", "category": "Employment", "required_before_active": True, "sort_order": 70},
        {"name": "Knowledge Test Paper", "category": "Employment", "required_before_active": False, "sort_order": 71},
        {"name": "Driving Acknowledgement", "category": "Employment", "required_before_active": False, "sort_order": 72},
        
        # Health Screening
        {"name": "Health Screening Form", "category": "Health Screening", "required_before_active": True, "sort_order": 80},
        
        # Induction & Shadowing
        {"name": "ID Badge Proof", "category": "Induction", "required_before_active": True, "sort_order": 90},
        {"name": "ID Badge Receipt Form", "category": "Induction", "required_before_active": True, "sort_order": 91},
        {"name": "Uniform Given", "category": "Induction", "required_before_active": True, "sort_order": 92},
        {"name": "Uniform Receipt Form", "category": "Induction", "required_before_active": True, "sort_order": 93},
        {"name": "Shadowing Form", "category": "Induction", "required_before_active": True, "sort_order": 94},
        {"name": "Induction Form Checklist", "category": "Induction", "required_before_active": True, "sort_order": 95},
        
        # HMRC & Contract
        {"name": "HMRC Form", "category": "HMRC", "required_before_active": True, "sort_order": 100},
        {"name": "Contract of Employment", "category": "Contract", "required_before_active": True, "sort_order": 110},
        {"name": "Working Time Opt Out Agreement", "category": "Contract", "required_before_active": False, "sort_order": 111},
        
        # Driver Documents
        {"name": "Car Insurance Business Use", "category": "Driver Documents", "required_before_active": False, "has_expiry": True, "sort_order": 120},
        {"name": "MOT Certificate", "category": "Driver Documents", "required_before_active": False, "has_expiry": True, "sort_order": 121},
        
        # Employee Handbook & Policies
        {"name": "Employee Handbook Receipt", "category": "Policies", "required_before_active": True, "sort_order": 130},
        {"name": "Policies Email Proof", "category": "Policies", "required_before_active": True, "sort_order": 131},
    ]
    
    # Clear existing document types
    await db.document_types.delete_many({})
    
    for doc in document_categories:
        doc_type = {
            "id": str(uuid.uuid4()),
            "name": doc["name"],
            "category": doc["category"],
            "required_for_role": [],
            "has_expiry": doc.get("has_expiry", False),
            "required_before_active": doc.get("required_before_active", False),
            "sort_order": doc.get("sort_order", 0)
        }
        await db.document_types.insert_one(doc_type)
    
    # Create default admin user if not exists
    admin_exists = await db.users.find_one({"email": "admin@osabea.care"})
    if not admin_exists:
        admin_user = {
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": "admin@osabea.care",
            "password": hash_password("admin123"),
            "name": "System Admin",
            "role": UserRole.SUPER_ADMIN,
            "assignment": None,
            "picture": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_user)
    
    return {"message": "Seed data created successfully", "document_types": len(document_categories)}

# CLEANUP endpoint to remove duplicate forms and fix requirement linking
@api_router.post("/admin/cleanup-duplicates")
async def cleanup_duplicates(user: dict = Depends(require_manager_or_admin)):
    """
    Clean up duplicate forms and documents:
    1. For each requirement, keep only the MOST RECENT form
    2. Delete duplicate forms
    3. Add requirement_id to forms that don't have it
    4. Add requirement_id to documents that don't have it
    """
    
    results = {
        "forms_deleted": 0,
        "forms_updated": 0,
        "documents_updated": 0,
        "documents_deleted": 0,
        "details": []
    }
    
    # Define form name to requirement_id mapping
    form_to_requirement = {
        "Reference 1": "reference_1",
        "Reference Request Form": "reference_1",  # Older name
        "Reference 2": "reference_2",
        "Health Screening Questionnaire": "health_screening",
        "Contract Acknowledgement Form": "contract",
        "Contract Acknowledgement": "contract",
        "Induction & Competency Assessment": "induction",
        "Employee Handbook Acknowledgement": "handbook",
        "Application Form": "application_form",
        "Interview Record Form": "interview_record",
        "Personal Information Form": "personal_info",
        "Equal Opportunities Monitoring Form": "equal_opportunities",
        "Recruitment Compliance Checklist": "recruitment_checklist",
    }
    
    # Get all employees
    employees = await db.employees.find({}, {"_id": 0, "id": 1}).to_list(1000)
    
    for emp in employees:
        employee_id = emp['id']
        
        # Get all forms for this employee
        forms = await db.generated_forms.find({"employee_id": employee_id}, {"_id": 0}).to_list(500)
        
        # Group forms by requirement
        forms_by_req = {}
        for form in forms:
            # Determine requirement_id
            req_id = form.get('requirement_id')
            if not req_id:
                # Try to match by template name
                template_name = form.get('template_name', '')
                req_id = form_to_requirement.get(template_name)
                
                # Handle "Reference 1" forms (may have different template_id but same name)
                if not req_id and 'Reference' in template_name:
                    if '2' in template_name:
                        req_id = 'reference_2'
                    else:
                        req_id = 'reference_1'
            
            if req_id:
                if req_id not in forms_by_req:
                    forms_by_req[req_id] = []
                forms_by_req[req_id].append(form)
        
        # For each requirement, keep only the most recent form
        for req_id, req_forms in forms_by_req.items():
            if len(req_forms) > 1:
                # Sort by completed_at or created_at (most recent first)
                req_forms.sort(key=lambda f: f.get('completed_at') or f.get('created_at') or '', reverse=True)
                
                # Keep the first (most recent) one
                keep_form = req_forms[0]
                
                # Update the kept form with requirement_id if missing
                if not keep_form.get('requirement_id'):
                    await db.generated_forms.update_one(
                        {"id": keep_form['id']},
                        {"$set": {"requirement_id": req_id}}
                    )
                    results['forms_updated'] += 1
                
                # Delete duplicates
                for dup_form in req_forms[1:]:
                    await db.generated_forms.delete_one({"id": dup_form['id']})
                    results['forms_deleted'] += 1
                    results['details'].append(f"Deleted duplicate form: {dup_form.get('template_name')} for employee {employee_id}")
            elif len(req_forms) == 1:
                # Single form - just update requirement_id if missing
                if not req_forms[0].get('requirement_id'):
                    await db.generated_forms.update_one(
                        {"id": req_forms[0]['id']},
                        {"$set": {"requirement_id": req_id}}
                    )
                    results['forms_updated'] += 1
        
        # Now clean up documents
        doc_to_requirement = {
            "Application Form": "application_form",
            "CV / Resume": "cv",
            "CV": "cv",
            "Resume": "cv",
            "DBS Certificate": "dbs",
            "DBS Form / Update Service": "dbs",
            "Reference 1": "reference_1",
            "Reference 2": "reference_2",
            "Right to Work in UK": "identity_rtw",
            "Passport": "identity_rtw",
            "Health Screening Form": "health_screening",
            "Health Screening Questionnaire": "health_screening",
            "Contract of Employment": "contract",
            "Contract Acknowledgement": "contract",
            "Employee Handbook Receipt": "handbook",
            "Employee Handbook Acknowledgement": "handbook",
            "Interview Questions": "interview_record",
            "Induction & Competency Assessment": "induction",
        }
        
        # Get all documents for this employee
        docs = await db.employee_documents.find({"employee_id": employee_id}, {"_id": 0}).to_list(500)
        
        # Group documents by requirement
        docs_by_req = {}
        for doc in docs:
            req_id = doc.get('requirement_id')
            if not req_id:
                # Try to match by document type name
                doc_type_name = doc.get('document_type_name', '')
                req_id = doc_to_requirement.get(doc_type_name)
            
            if req_id:
                if req_id not in docs_by_req:
                    docs_by_req[req_id] = []
                docs_by_req[req_id].append(doc)
        
        # For single-file requirements, keep only the most recent
        single_file_reqs = ['cv', 'dbs', 'reference_1', 'reference_2', 'application_form', 
                           'health_screening', 'contract', 'induction', 'handbook',
                           'interview_record', 'personal_info', 'recruitment_checklist']
        
        for req_id, req_docs in docs_by_req.items():
            # Update all docs with missing requirement_id
            for doc in req_docs:
                if not doc.get('requirement_id'):
                    await db.employee_documents.update_one(
                        {"id": doc['id']},
                        {"$set": {"requirement_id": req_id, "requirement_name": req_id.replace('_', ' ').title()}}
                    )
                    results['documents_updated'] += 1
            
            # For single-file requirements with multiple docs, keep only the best one
            if req_id in single_file_reqs and len(req_docs) > 1:
                # Sort by: has file > verified > approved > version > uploaded_at
                req_docs.sort(key=lambda d: (
                    1 if d.get('file_url') else 0,
                    1 if d.get('verified') else 0,
                    1 if d.get('status') == 'approved' else 0,
                    d.get('version_number', 0),
                    d.get('uploaded_at') or ''
                ), reverse=True)
                
                keep_doc = req_docs[0]
                
                # Delete duplicates (only those without files or lower priority)
                for dup_doc in req_docs[1:]:
                    if not dup_doc.get('file_url'):
                        # Delete placeholder docs without files
                        await db.employee_documents.delete_one({"id": dup_doc['id']})
                        results['documents_deleted'] += 1
    
    return {
        "success": True,
        "message": "Cleanup completed",
        **results
    }

# Phase 1 Cleanup for specific employee - comprehensive data cleanup
@api_router.post("/admin/cleanup-employee/{employee_id}")
async def cleanup_employee_data(employee_id: str, user: dict = Depends(require_manager_or_admin)):
    """
    Phase 1 Cleanup for a specific employee:
    1. Delete orphan documents (no file_url)
    2. Deduplicate and normalize training records
    3. Add requirement_id to all forms
    4. Deduplicate single-file documents (mark old ones inactive)
    5. Link orphan documents to requirements
    """
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    results = {
        "orphan_docs_deleted": 0,
        "training_normalized": 0,
        "training_deleted": 0,
        "forms_updated": 0,
        "docs_deduped": 0,
        "docs_linked": 0,
        "details": []
    }
    
    now = datetime.now(timezone.utc).isoformat()
    
    # ========================================
    # STEP 1: Delete orphan documents (no file_url)
    # ========================================
    orphan_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "$or": [
            {"file_url": {"$exists": False}},
            {"file_url": None},
            {"file_url": ""}
        ]
    }).to_list(100)
    
    for doc in orphan_docs:
        await db.employee_documents.delete_one({"id": doc['id']})
        results['orphan_docs_deleted'] += 1
        results['details'].append(f"Deleted orphan doc: {doc.get('document_type_name', 'Unknown')} (no file)")
    
    # ========================================
    # STEP 2: Deduplicate and normalize training
    # ========================================
    # Training name normalization map (training_record name -> MANDATORY_ITEMS training_name)
    training_normalization = {
        "moving & handling": "Manual Handling",
        "moving and handling": "Manual Handling",
        "manual handling": "Manual Handling",
        "health & safety": "Health & Safety",
        "health and safety": "Health & Safety",
        "infection control": "Infection Control",
        "infection control and hygiene": "Infection Control",
        "safeguarding": "Safeguarding",
        "basic life support": "Basic Life Support",
        "bls": "Basic Life Support",
        "fire safety": "Fire Safety",
        "first aid": None,  # Not in mandatory items, will be deleted
        "first aid awareness": None,  # Not in mandatory items, will be deleted
    }
    
    # MANDATORY training names (from MANDATORY_ITEMS)
    mandatory_training = {
        "Safeguarding", "Manual Handling", "Infection Control", 
        "Basic Life Support", "Fire Safety", "Health & Safety"
    }
    
    all_training = await db.training_records.find({"employee_id": employee_id}).to_list(100)
    
    # Group by normalized name
    training_by_normalized = {}
    orphan_training = []
    
    for t in all_training:
        name = t.get('training_name', '')
        normalized = training_normalization.get(name.lower())
        
        if normalized is None:
            # Not in mandatory items, mark for deletion
            orphan_training.append(t)
        else:
            if normalized not in training_by_normalized:
                training_by_normalized[normalized] = []
            training_by_normalized[normalized].append(t)
    
    # Delete orphan training (not in mandatory items)
    for t in orphan_training:
        await db.training_records.delete_one({"id": t['id']})
        results['training_deleted'] += 1
        results['details'].append(f"Deleted non-mandatory training: {t.get('training_name')}")
    
    # For each mandatory training, keep only ONE record (prefer completed, then most recent)
    for normalized_name, records in training_by_normalized.items():
        if len(records) > 1:
            # Sort: completed first, then by created_at
            records.sort(key=lambda r: (
                1 if r.get('status') == 'completed' else 0,
                r.get('completed_at') or r.get('created_at') or ''
            ), reverse=True)
            
            keep = records[0]
            
            # Update the kept record with normalized name
            if keep.get('training_name') != normalized_name:
                await db.training_records.update_one(
                    {"id": keep['id']},
                    {"$set": {"training_name": normalized_name, "updated_at": now}}
                )
                results['training_normalized'] += 1
            
            # Delete duplicates
            for dup in records[1:]:
                await db.training_records.delete_one({"id": dup['id']})
                results['training_deleted'] += 1
                results['details'].append(f"Deleted duplicate training: {dup.get('training_name')}")
        elif len(records) == 1:
            # Single record, just normalize the name
            if records[0].get('training_name') != normalized_name:
                await db.training_records.update_one(
                    {"id": records[0]['id']},
                    {"$set": {"training_name": normalized_name, "updated_at": now}}
                )
                results['training_normalized'] += 1
    
    # ========================================
    # STEP 3: Add requirement_id to all forms
    # ========================================
    form_to_requirement = {
        "Reference 1": "reference_1",
        "Reference Request Form": "reference_1",
        "Reference 2": "reference_2",
        "Health Screening Questionnaire": "health_screening",
        "Contract Acknowledgement Form": "contract",
        "Contract Acknowledgement": "contract",
        "Induction & Competency Assessment": "induction",
        "Employee Handbook Acknowledgement": "handbook",
        "Application Form": "application_form",
        "Interview Record Form": "interview_record",
        "Interview Record": "interview_record",
        "Personal Information Form": "personal_info",
        "Equal Opportunities Monitoring Form": "equal_opportunities",
        "Recruitment Compliance Checklist": "recruitment_checklist",
    }
    
    all_forms = await db.generated_forms.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    
    for form in all_forms:
        current_req_id = form.get('requirement_id')
        if not current_req_id or current_req_id == '' or current_req_id is None:
            template_name = form.get('template_name', '')
            req_id = form_to_requirement.get(template_name)
            
            # Try partial matching if exact match fails
            if not req_id:
                for name, rid in form_to_requirement.items():
                    if name.lower() in template_name.lower() or template_name.lower() in name.lower():
                        req_id = rid
                        break
            
            if req_id:
                await db.generated_forms.update_one(
                    {"id": form['id']},
                    {"$set": {"requirement_id": req_id, "updated_at": now}}
                )
                results['forms_updated'] += 1
                results['details'].append(f"Linked form '{template_name}' to requirement '{req_id}'")
    
    # ========================================
    # STEP 4: Deduplicate single-file documents
    # ========================================
    single_file_reqs = ['cv', 'dbs', 'reference_1', 'reference_2', 'application_form', 
                       'health_screening', 'contract', 'induction', 'handbook',
                       'interview_record', 'personal_info', 'recruitment_checklist']
    
    all_docs = await db.employee_documents.find({"employee_id": employee_id, "file_url": {"$exists": True, "$ne": None}}).to_list(200)
    
    # Group by requirement_id
    docs_by_req = {}
    for doc in all_docs:
        req_id = doc.get('requirement_id')
        if req_id:
            if req_id not in docs_by_req:
                docs_by_req[req_id] = []
            docs_by_req[req_id].append(doc)
    
    for req_id, docs in docs_by_req.items():
        if req_id in single_file_reqs and len(docs) > 1:
            # Sort: verified > approved > highest version > most recent
            docs.sort(key=lambda d: (
                1 if d.get('verified') else 0,
                1 if d.get('status') == 'approved' else 0,
                d.get('version_number', 0),
                d.get('uploaded_at') or ''
            ), reverse=True)
            
            keep = docs[0]
            
            # Mark duplicates as inactive (add inactive flag, don't delete for audit trail)
            for dup in docs[1:]:
                await db.employee_documents.update_one(
                    {"id": dup['id']},
                    {"$set": {
                        "status": "superseded",
                        "superseded_by": keep['id'],
                        "superseded_at": now,
                        "active": False
                    }}
                )
                results['docs_deduped'] += 1
                results['details'].append(f"Marked doc as superseded: {dup.get('document_type_name')} -> kept {keep.get('original_filename')}")
    
    # ========================================
    # STEP 5: Link orphan documents to requirements
    # ========================================
    doc_to_requirement = {
        "Application Form": "application_form",
        "CV / Resume": "cv",
        "CV": "cv",
        "Resume": "cv",
        "DBS Certificate": "dbs",
        "DBS Form / Update Service": "dbs",
        "Reference 1": "reference_1",
        "Reference 2": "reference_2",
        "Right to Work in UK": "identity_rtw",
        "Passport": "identity_rtw",
        "Health Screening Form": "health_screening",
        "Health Screening Questionnaire": "health_screening",
        "Contract of Employment": "contract",
        "Contract Acknowledgement": "contract",
        "Employee Handbook Receipt": "handbook",
        "Employee Handbook Acknowledgement": "handbook",
        "Interview Questions": "interview_record",
        "Induction & Competency Assessment": "induction",
        "New Starter Form": None,  # No matching requirement
    }
    
    orphan_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$exists": False}
    }).to_list(100)
    
    for doc in orphan_docs:
        doc_type_name = doc.get('document_type_name', '')
        req_id = doc_to_requirement.get(doc_type_name)
        
        if req_id:
            await db.employee_documents.update_one(
                {"id": doc['id']},
                {"$set": {"requirement_id": req_id, "requirement_name": req_id.replace('_', ' ').title()}}
            )
            results['docs_linked'] += 1
            results['details'].append(f"Linked doc '{doc_type_name}' to requirement '{req_id}'")
        else:
            # No matching requirement, mark as inactive
            await db.employee_documents.update_one(
                {"id": doc['id']},
                {"$set": {"active": False, "notes": "No matching compliance requirement"}}
            )
            results['details'].append(f"Marked unlinked doc as inactive: {doc_type_name}")
    
    return {
        "success": True,
        "employee_id": employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        **results
    }

# Health check
@api_router.get("/")
async def root():
    return {"message": "Osabea Healthcare Solutions API", "status": "healthy"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    try:
        init_storage()
    except Exception as e:
        logger.error(f"Storage initialization failed: {e}")
    
    # Auto-seed organisation policies and insurance if empty
    try:
        policy_count = await db.org_policies.count_documents({})
        if policy_count == 0:
            now = datetime.now(timezone.utc).isoformat()
            for policy in CORE_POLICIES:
                policy_doc = {
                    "id": str(uuid.uuid4()),
                    "name": policy["name"],
                    "category": policy["category"],
                    "version": "v1.0",
                    "status": "missing",
                    "file_url": None,
                    "original_filename": None,
                    "review_date": None,
                    "last_reviewed_at": None,
                    "reviewed_by": None,
                    "notes": None,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": "system"
                }
                await db.org_policies.insert_one(policy_doc)
            logger.info(f"Auto-seeded {len(CORE_POLICIES)} organisation policies")
        
        insurance_count = await db.insurance_docs.count_documents({})
        if insurance_count == 0:
            now = datetime.now(timezone.utc).isoformat()
            for ins in INSURANCE_TYPES:
                doc = {
                    "id": str(uuid.uuid4()),
                    "name": ins["name"],
                    "insurance_type": ins["type"],
                    "status": "missing",
                    "file_url": None,
                    "original_filename": None,
                    "expiry_date": None,
                    "policy_number": None,
                    "provider": None,
                    "notes": None,
                    "created_at": now,
                    "updated_at": now
                }
                await db.insurance_docs.insert_one(doc)
            logger.info(f"Auto-seeded {len(INSURANCE_TYPES)} insurance documents")
    except Exception as e:
        logger.error(f"Auto-seeding failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
