from fastapi import FastAPI, APIRouter, HTTPException, Depends, File, UploadFile, Query, Header, Response, Form
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import logging
import uuid
import asyncio
import io
import zipfile
import base64
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
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
import pytesseract
from PIL import Image as PILImage
from pdf2image import convert_from_bytes
import pdfplumber  # Primary method for typed PDF extraction

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
        
        # ======== CATEGORY 1: LEGAL & SAFETY (Required to Start Work) ========
        {"id": "right_to_work_documents", "name": "Right to Work Documents", 
         "category": "1_Legal_Safety", "type": "document", "source": "employee",
         "document_types": ["visa", "brp", "share_code", "settled_status"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "start_required", "priority_order": 1,
         "status_group": "start_status",
         "description": "Visa, BRP, share code evidence, settled status proof",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "right_to_work_check", "name": "Right to Work Verification", 
         "category": "1_Legal_Safety", "type": "document", "source": "internal",
         "document_types": ["rtw_check", "share_code_check"],
         "allow_multiple_files": True,
         "priority": "start_required", "priority_order": 2,
         "status_group": "start_status",
         "description": "Internal RTW verification - share code check result",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "identity_documents", "name": "Identity Documents", 
         "category": "1_Legal_Safety", "type": "document", "source": "employee",
         "document_types": ["passport", "driving_licence", "national_id"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "start_required", "priority_order": 3,
         "status_group": "start_status",
         "description": "Passport, driving licence, or other photo ID",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "dbs_certificate", "name": "DBS Certificate", "category": "1_Legal_Safety",
         "type": "document", "source": "employee",
         "document_types": ["dbs", "dbs_certificate"],
         "allow_multiple_files": True,
         "priority": "start_required", "priority_order": 4,
         "status_group": "start_status",
         "description": "DBS certificate from employee",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "dbs_check", "name": "DBS Update Service Check", "category": "1_Legal_Safety",
         "type": "document", "source": "internal",
         "document_types": ["dbs_check", "dbs_update_service"],
         "allow_multiple_files": True,
         "priority": "start_required", "priority_order": 5,
         "status_group": "start_status",
         "description": "Internal DBS verification - update service check result",
         "work_ready_hint": "Required before employee can start work"},
        
        # ======== PROOF OF ADDRESS (NHS Standard - Requires 2 Documents) ========
        {"id": "proof_of_address", "name": "Proof of Address", 
         "category": "1_Legal_Safety", "type": "document", "source": "employee",
         "document_types": ["utility_bill", "bank_statement", "council_tax", "tenancy_agreement"],
         "allow_multiple_files": True, 
         "min_files": 2,  # NHS standard: requires 2 separate documents
         "required_count": 2,
         "priority": "start_required", "priority_order": 6,
         "status_group": "start_status",
         "description": "2 separate documents required: utility bill, bank statement, council tax, or tenancy agreement (dated within 3 months)",
         "work_ready_hint": "NHS Standard: 2 verified documents required before employee can start work",
         "verification_required": True},
        
        # ======== CATEGORY 2: CORE TRAINING (Required to Start Work) ========
        # (Defined in "training" section below)
        
        # ======== CATEGORY 3: COMPETENCY & HEALTH (For Supervised Start) ========
        # ARCHIVED: Legacy health screening - replaced by Staff Health Questionnaire
        # Historical submissions preserved, hidden from new employee files
        {"id": "health_screening", "name": "Health Screening Questionnaire", 
         "category": "3_Competency_Health", "type": "form-generated",
         "template_name": "Health Screening Questionnaire",
         "allow_multiple_files": True, "source": "form",
         "priority": "supervised_start", "priority_order": 20,
         "status_group": "competency_health",
         "description": "Health questionnaire and medical attachments",
         "work_ready_hint": "Required for supervised start",
         "archived": True,  # Hidden from UI - replaced by staff_health_questionnaire
         "archived_reason": "Replaced by Staff Health Questionnaire (Osabea official form)"},
        
        {"id": "staff_health_questionnaire", "name": "Staff Health Questionnaire", 
         "category": "3_Competency_Health", "type": "form-generated",
         "template_name": "Staff Health Questionnaire",
         "form_requirement_id": "staff_health_questionnaire",
         "allow_multiple_files": False, "source": "form",
         "priority": "supervised_start", "priority_order": 20,
         "status_group": "competency_health",
         "description": "Official Osabea Health Questionnaire - required for employment",
         "work_ready_hint": "Required for supervised start"},
        
        {"id": "induction", "name": "Induction & Competency Assessment", 
         "category": "3_Competency_Health", "type": "form-generated",
         "template_name": "Induction & Competency Assessment",
         "allow_multiple_files": True, "source": "internal",
         "priority": "supervised_start", "priority_order": 21,
         "status_group": "competency_health",
         "description": "Induction checklist, shadowing records, competency sign-offs",
         "work_ready_hint": "Required for supervised start"},
        
        # ======== CATEGORY 4: RECRUITMENT RECORD (Pre-employment File) ========
        {"id": "interview_record", "name": "Interview Record", 
         "category": "4_Recruitment_Record", "type": "form-generated",
         "template_name": "Interview Record Form",
         "allow_multiple_files": True, "source": "internal",
         "priority": "recruitment", "priority_order": 30,
         "status_group": "recruitment_file",
         "description": "Interview notes, assessment, and supporting documents",
         "work_ready_hint": "Required for complete recruitment file"},
        
        {"id": "reference_1", "name": "Reference 1", "category": "4_Recruitment_Record",
         "type": "document", "source": "employee",
         "document_types": ["reference"],
         "allow_multiple_files": True,
         "priority": "recruitment", "priority_order": 31,
         "status_group": "recruitment_file",
         "description": "First professional reference - verified and documented",
         "work_ready_hint": "Important pre-employment check"},
        
        {"id": "reference_2", "name": "Reference 2", "category": "4_Recruitment_Record",
         "type": "document", "source": "employee",
         "document_types": ["reference"],
         "allow_multiple_files": True,
         "priority": "recruitment", "priority_order": 32,
         "status_group": "recruitment_file",
         "description": "Second professional reference - verified and documented",
         "work_ready_hint": "Important pre-employment check"},
        
        {"id": "recruitment_checklist", "name": "Recruitment Compliance Checklist", 
         "category": "4_Recruitment_Record", "type": "form-generated", 
         "template_name": "Recruitment Compliance Checklist",
         "allow_multiple_files": True, "source": "internal",
         "priority": "recruitment", "priority_order": 33,
         "status_group": "recruitment_file",
         "description": "Internal recruitment tracking checklist",
         "work_ready_hint": "Required for complete recruitment file"},
        
        {"id": "application_form", "name": "Application Form", "category": "4_Recruitment_Record", 
         "type": "form-generated", "template_name": "Application Form", 
         "allow_multiple_files": False, "source": "form",
         "priority": "recruitment", "priority_order": 34,
         "status_group": "recruitment_file",
         "description": "Completed application form",
         "work_ready_hint": "Required for complete recruitment file"},
        
        {"id": "cv", "name": "CV / Resume", "category": "4_Recruitment_Record", 
         "type": "document", "source": "employee",
         "document_types": ["cv", "resume"], 
         "allow_multiple_files": True,
         "priority": "recruitment", "priority_order": 35,
         "status_group": "recruitment_file",
         "description": "CV and supporting documents",
         "work_ready_hint": "Required for complete recruitment file"},
        
        # ======== CATEGORY 5: AGREEMENTS ========
        {"id": "contract", "name": "Contract Acknowledgement", 
         "category": "5_Agreements", "type": "acknowledgement",
         "allow_multiple_files": False, "source": "internal",
         "priority": "secondary", "priority_order": 40,
         "status_group": "other",
         "description": "Employee confirms they have received and understood their contract",
         "acknowledgement_text": "I confirm I have received, read, and understood my employment contract and its terms.",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "handbook", "name": "Employee Handbook Acknowledgement", 
         "category": "5_Agreements", "type": "acknowledgement",
         "allow_multiple_files": False, "source": "internal",
         "priority": "secondary", "priority_order": 41,
         "status_group": "other",
         "description": "Employee confirms they have received and understood the employee handbook",
         "acknowledgement_text": "I confirm I have received, read, and understood the Employee Handbook and company policies.",
         "work_ready_hint": "Complete after employee starts"},
        
        # ======== CATEGORY 6: ADMIN / OTHER ========
        {"id": "staff_personal_info", "name": "Staff Personal Information", 
         "category": "6_Admin", "type": "form-generated", 
         "template_name": "Staff Personal Information",
         "form_requirement_id": "staff_personal_info",
         "allow_multiple_files": False, "source": "form",
         "priority": "secondary", "priority_order": 42,
         "status_group": "other",
         "updates_profile": True,
         "description": "Personal details form - can update employee profile",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "hmrc_starter_checklist", "name": "HMRC Starter Checklist", 
         "category": "6_Admin", "type": "form-generated",
         "template_name": "HMRC Starter Checklist",
         "form_requirement_id": "hmrc_starter_checklist",
         "allow_multiple_files": False, "source": "form",
         "priority": "secondary", "priority_order": 43,
         "status_group": "other",
         "conditional_on": "p45",  # Only required if no P45 on file
         "conditional_inverse": True,  # Required when p45 is ABSENT
         "description": "Complete if employee does not have a P45. Used for payroll/tax setup.",
         "work_ready_hint": "Complete if no P45 provided"},
        
        {"id": "equal_opportunities", "name": "Equal Opportunities Monitoring", 
         "category": "6_Admin", "type": "form-generated",
         "template_name": "Equal Opportunities Monitoring Form",
         "form_requirement_id": "equal_opportunities",
         "allow_multiple_files": False, "source": "form",
         "priority": "optional", "priority_order": 44,
         "status_group": "other",
         "optional": True,
         "description": "Diversity monitoring form (optional - does not affect compliance)",
         "work_ready_hint": "Optional - employee may decline"},
    ],
    
    "training": [  # Training items with priority
        # ======== CORE TRAINING (Required to Start Work) ========
        {"id": "safeguarding", "name": "Safeguarding Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Safeguarding",
         "allow_multiple_files": True,
         "priority": "start_required", "priority_order": 6,
         "status_group": "start_status",
         "description": "Safeguarding certificate and transcript",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "manual_handling", "name": "Manual Handling Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Manual Handling",
         "allow_multiple_files": True,
         "priority": "start_required", "priority_order": 7,
         "status_group": "start_status",
         "description": "Manual handling certificate",
         "work_ready_hint": "Required before employee can start work"},
        
        {"id": "infection_control", "name": "Infection Control Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Infection Control",
         "allow_multiple_files": True,
         "priority": "start_required", "priority_order": 8,
         "status_group": "start_status",
         "description": "Infection control certificate",
         "work_ready_hint": "Required before employee can start work"},
        
        # ======== ADDITIONAL TRAINING (Supervised Start) ========
        {"id": "bls", "name": "Basic Life Support (BLS)", "category": "2_Core_Training",
         "type": "training", "training_name": "Basic Life Support",
         "allow_multiple_files": True,
         "priority": "supervised_start", "priority_order": 22,
         "status_group": "competency_health",
         "description": "BLS certificate, renewal card",
         "work_ready_hint": "Required for supervised start"},
        
        {"id": "fire_safety", "name": "Fire Safety Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Fire Safety",
         "allow_multiple_files": True,
         "priority": "secondary", "priority_order": 44,
         "status_group": "other",
         "description": "Fire safety certificate",
         "work_ready_hint": "Complete after employee starts"},
        
        {"id": "health_safety", "name": "Health & Safety Training", "category": "2_Core_Training",
         "type": "training", "training_name": "Health & Safety",
         "allow_multiple_files": True,
         "priority": "secondary", "priority_order": 45,
         "status_group": "other",
         "description": "Health & Safety certificate",
         "work_ready_hint": "Complete after employee starts"},
    ],
    
    "nurse_specific": [  # Additional items for Nurses only
        # ======== MANDATORY for Nurses (Required to Start Work) ========
        {"id": "nmc_registration", "name": "NMC Registration", "category": "1_Legal_Safety",
         "type": "document", "source": "employee",
         "document_types": ["nmc_registration", "professional_registration"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "start_required", "priority_order": 9,
         "status_group": "start_status",
         "description": "NMC PIN card, registration letter",
         "work_ready_hint": "Required before nurse can start work"},
        
        # ======== NURSE COMPETENCY & HEALTH ========
        {"id": "clinical_competency", "name": "Clinical Competency Evidence", 
         "category": "3_Competency_Health", "type": "document", "source": "employee",
         "document_types": ["clinical_competency", "competency_assessment"],
         "allow_multiple_files": True, "min_files": 1,
         "priority": "supervised_start", "priority_order": 23,
         "status_group": "competency_health",
         "description": "Clinical competency assessments, skill sign-offs",
         "work_ready_hint": "Required for supervised start"},
        
        {"id": "medication_competency", "name": "Medication Competency", 
         "category": "3_Competency_Health", "type": "training", "training_name": "Medication",
         "allow_multiple_files": True,
         "priority": "supervised_start", "priority_order": 24,
         "status_group": "competency_health",
         "description": "Medication administration competency certificate",
         "work_ready_hint": "Required for supervised start"},
    ]
}

# ============================================================================
# PHASE 1: TRAINING CATALOGUE FOUNDATION
# ============================================================================
# Feature flag - when False, employee_training_assignments are IGNORED
# This ensures Phase 1 is behavior-neutral until explicitly enabled
ENABLE_EMPLOYEE_TRAINING_ASSIGNMENTS = False  # DO NOT ENABLE until Phase 2

async def ensure_training_catalogue_exists():
    """
    Creates and seeds training_catalogue collection from MANDATORY_ITEMS.
    Safe to call multiple times - will not duplicate entries.
    """
    # Get existing catalogue entries
    existing_ids = set()
    async for doc in db.training_catalogue.find({}, {"id": 1}):
        existing_ids.add(doc["id"])
    
    # Seed from MANDATORY_ITEMS["training"]
    training_items = MANDATORY_ITEMS.get("training", [])
    nurse_training = [i for i in MANDATORY_ITEMS.get("nurse_specific", []) if i.get("type") == "training"]
    all_training = training_items + nurse_training
    
    inserted_count = 0
    for item in all_training:
        if item["id"] not in existing_ids:
            catalogue_entry = {
                "id": item["id"],
                "name": item["name"],
                "training_name": item.get("training_name", item["name"]),
                "category": "core" if item.get("priority") == "start_required" else "standard",
                "default_required": True,  # All existing training is required by default
                "priority": item.get("priority", "secondary"),
                "priority_order": item.get("priority_order", 99),
                "description": item.get("description", ""),
                "expiry_months": 12,  # Default 12 month expiry
                "source": "mandatory_items",  # Indicates seeded from hardcoded items
                "created_at": datetime.now(timezone.utc).isoformat(),
                "active": True
            }
            await db.training_catalogue.insert_one(catalogue_entry)
            inserted_count += 1
            existing_ids.add(item["id"])
    
    return {"seeded": inserted_count, "total": len(existing_ids)}


async def get_training_catalogue() -> List[dict]:
    """
    Returns all active training types from catalogue.
    Phase 1: Read-only, for admin visibility.
    """
    catalogue = await db.training_catalogue.find(
        {"active": True}, 
        {"_id": 0}
    ).to_list(100)
    return catalogue


async def get_employee_training_assignments(employee_id: str) -> List[dict]:
    """
    Returns training assignments for a specific employee.
    Phase 1: Always returns empty list (feature flag disabled).
    Phase 2+: Returns actual assignments when flag enabled.
    """
    if not ENABLE_EMPLOYEE_TRAINING_ASSIGNMENTS:
        return []  # Feature disabled - no assignments affect compliance
    
    assignments = await db.employee_training_assignments.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).to_list(50)
    return assignments


async def get_required_training_for_employee(employee_id: str, role: str) -> List[dict]:
    """
    FUTURE USE: Returns merged list of required training for an employee.
    
    Phase 1: Returns ONLY MANDATORY_ITEMS["training"] (behavior unchanged)
    Phase 2+: Will merge:
      - MANDATORY_ITEMS["training"] (global defaults)
      - employee_training_assignments where is_required=True
    
    This function is NOT YET USED in calculate_employee_compliance().
    It is prepared for Phase 2 integration.
    """
    # Phase 1: Return existing behavior exactly
    items = MANDATORY_ITEMS["training"].copy()
    
    # Add nurse-specific training if applicable
    if role and "nurse" in role.lower():
        nurse_training = [i for i in MANDATORY_ITEMS["nurse_specific"] if i.get("type") == "training"]
        items.extend(nurse_training)
    
    # Phase 2 would add:
    # if ENABLE_EMPLOYEE_TRAINING_ASSIGNMENTS:
    #     assignments = await get_employee_training_assignments(employee_id)
    #     for assign in assignments:
    #         if assign.get("is_required"):
    #             # Merge from catalogue...
    
    return items


# ============================================================================
# END PHASE 1 FOUNDATION
# ============================================================================

# Priority display configuration
PRIORITY_CONFIG = {
    "start_required": {
        "label": "Required to Start Work",
        "color": "red",
        "emoji": "🔴"
    },
    "supervised_start": {
        "label": "Required for Supervised Start",
        "color": "orange",
        "emoji": "🟠"
    },
    "recruitment": {
        "label": "Recruitment File",
        "color": "blue",
        "emoji": "🔵"
    },
    "secondary": {
        "label": "Complete After Start",
        "color": "gray",
        "emoji": "⚪"
    }
}

# Category display names (updated)
CATEGORY_DISPLAY_NAMES = {
    "1_Legal_Safety": "Legal & Safety",
    "2_Core_Training": "Core Training",
    "3_Competency_Health": "Competency & Health",
    "4_Recruitment_Record": "Recruitment Record",
    "5_Agreements": "Agreements",
    "6_Admin": "Admin / Other"
}

# Status group definitions
STATUS_GROUPS = {
    "start_status": {
        "name": "Start Status",
        "description": "Shows whether this employee can safely start work.",
        "items": ["right_to_work_documents", "right_to_work_check", "identity_documents", 
                  "dbs_certificate", "dbs_check", "nmc_registration",
                  "safeguarding", "manual_handling", "infection_control"]
    },
    "competency_health": {
        "name": "Competency & Health",
        "description": "Health and competency assessments required for supervised work.",
        "items": ["health_screening", "induction", "bls", "clinical_competency", "medication_competency"]
    },
    "recruitment_file": {
        "name": "Recruitment File",
        "description": "Shows whether the pre-employment record is complete.",
        "items": ["interview_record", "reference_1", "reference_2", "recruitment_checklist", 
                  "application_form", "cv"]
    }
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
    """Get the set of requirement IDs that are mandatory for work readiness (Start Status)"""
    work_ready = WORK_READY_REQUIREMENTS.copy()
    
    # Add nurse-specific mandatory item
    if role and "nurse" in role.lower():
        work_ready.add("nmc_registration")
    
    return work_ready

def get_recruitment_file_items() -> set:
    """Get the set of requirement IDs for recruitment file"""
    return {
        "interview_record", "reference_1", "reference_2", 
        "recruitment_checklist", "application_form", "cv"
    }

def get_competency_health_items(role: str) -> set:
    """Get the set of requirement IDs for competency & health"""
    items = {"health_screening", "induction", "bls"}
    if role and "nurse" in role.lower():
        items.add("clinical_competency")
        items.add("medication_competency")
    return items

# Critical documents that override work readiness if expired
CRITICAL_EXPIRY_DOCS = {
    "right_to_work_documents",
    "right_to_work_check",
    "dbs_certificate",
    "dbs_check"
}

def calculate_separated_statuses(requirements: List[dict], role: str, policies_data: dict = None) -> dict:
    """
    Calculate the three separated status types:
    1. Start Status - Can the employee safely start work?
    2. Recruitment File - Is the pre-employment record complete?
    3. Policies - Have assigned policies been acknowledged?
    
    Returns a unified status object for the overview.
    """
    work_ready_ids = get_work_ready_items_for_role(role)
    recruitment_ids = get_recruitment_file_items()
    competency_ids = get_competency_health_items(role)
    
    # Initialize counters
    start_items = []
    recruitment_items = []
    competency_items = []
    other_items = []
    
    # Track expiry status
    expired_docs = []
    expiring_soon_docs = []
    valid_docs = []
    
    for req in requirements:
        req_id = req.get('id')
        status_group = req.get('status_group', 'other')
        
        # Track document expiry
        if req.get('has_evidence'):
            evidence_files = req.get('evidence_files', [])
            for ef in evidence_files:
                if ef.get('status') == 'active' and ef.get('expiry_date'):
                    exp_status = calculate_expiry_status(ef.get('expiry_date'))
                    doc_info = {
                        "req_id": req_id,
                        "req_name": req.get('name'),
                        "file_name": ef.get('original_filename'),
                        "expiry_date": ef.get('expiry_date'),
                        "expiry_status": exp_status
                    }
                    if exp_status.get('status') == 'expired':
                        expired_docs.append(doc_info)
                    elif exp_status.get('status') == 'expiring_soon':
                        expiring_soon_docs.append(doc_info)
                    else:
                        valid_docs.append(doc_info)
        
        if req_id in work_ready_ids or status_group == 'start_status':
            start_items.append(req)
        elif req_id in recruitment_ids or status_group == 'recruitment_file':
            recruitment_items.append(req)
        elif req_id in competency_ids or status_group == 'competency_health':
            competency_items.append(req)
        else:
            other_items.append(req)
    
    # Check for critical expired documents (override work readiness)
    critical_expired = [d for d in expired_docs if d['req_id'] in CRITICAL_EXPIRY_DOCS]
    has_critical_expired = len(critical_expired) > 0
    
    # Calculate Start Status
    start_complete = sum(1 for r in start_items if r.get('status') == 'completed' and r.get('has_evidence'))
    start_verified = sum(1 for r in start_items if r.get('verified', False))
    start_total = len(start_items)
    start_missing = [{"id": r['id'], "name": r['name']} for r in start_items 
                     if not (r.get('status') == 'completed' and r.get('has_evidence'))]
    
    # Determine Start Status - with expiry override
    if has_critical_expired:
        # Critical document expired - cannot work
        start_status = "not_ready"
        start_label = "Not Ready"
        start_color = "error"
        start_reason = f"Critical document expired: {critical_expired[0]['req_name']}"
    elif start_verified == start_total and start_total > 0:
        start_status = "ready_to_work"
        start_label = "Ready to Work"
        start_color = "success"
        start_reason = "All required checks are complete. This employee can safely start work."
    elif start_complete == start_total and start_total > 0:
        # All start items complete but not all verified - check competency/health
        competency_complete = sum(1 for r in competency_items if r.get('status') == 'completed' and r.get('has_evidence'))
        if competency_complete < len(competency_items):
            start_status = "supervised_start_only"
            start_label = "Supervised Start"
            start_color = "warning"
            start_reason = "Employee can start with supervision. Some training is still needed."
        else:
            start_status = "supervised_start_only"
            start_label = "Supervised Start"
            start_color = "warning"
            start_reason = "Employee can start with supervision. Some training is still needed."
    else:
        start_status = "not_ready"
        start_label = "Not Ready"
        start_color = "error"
        start_reason = "Essential checks are missing. This employee cannot start work."
    
    # Calculate Recruitment File Status
    recruitment_complete = sum(1 for r in recruitment_items if r.get('status') == 'completed' and r.get('has_evidence'))
    recruitment_total = len(recruitment_items)
    recruitment_missing = [{"id": r['id'], "name": r['name']} for r in recruitment_items 
                           if not (r.get('status') == 'completed' and r.get('has_evidence'))]
    
    if recruitment_complete == recruitment_total and recruitment_total > 0:
        recruitment_status = "complete"
        recruitment_label = "Complete"
        recruitment_color = "success"
    else:
        recruitment_status = "incomplete"
        recruitment_label = "Incomplete"
        recruitment_color = "warning"
    
    # Calculate Policies Status (from policies_data if provided)
    if policies_data:
        policies_assigned = policies_data.get('assigned', 0)
        policies_acknowledged = policies_data.get('acknowledged', 0)
        
        if policies_assigned == 0:
            policies_status = "no_policies"
            policies_label = "No Policies Assigned"
            policies_color = "neutral"
        elif policies_acknowledged == policies_assigned:
            policies_status = "all_acknowledged"
            policies_label = "All Policies Acknowledged"
            policies_color = "success"
        else:
            policies_status = "policies_assigned"
            policies_label = f"{policies_assigned} Assigned · {policies_acknowledged} Acknowledged"
            policies_color = "warning"
    else:
        policies_status = "no_policies"
        policies_label = "No Policies Assigned"
        policies_color = "neutral"
        policies_assigned = 0
        policies_acknowledged = 0
    
    # Calculate Document Status (Expiry)
    total_docs_with_expiry = len(expired_docs) + len(expiring_soon_docs) + len(valid_docs)
    if len(expired_docs) > 0:
        doc_status = "expired"
        doc_label = f"{len(expired_docs)} Expired"
        doc_color = "error"
    elif len(expiring_soon_docs) > 0:
        doc_status = "expiring_soon"
        doc_label = f"{len(expiring_soon_docs)} Expiring Soon"
        doc_color = "warning"
    elif total_docs_with_expiry > 0:
        doc_status = "all_valid"
        doc_label = "All Valid"
        doc_color = "success"
    else:
        doc_status = "no_expiry_tracked"
        doc_label = "No Expiry Dates"
        doc_color = "neutral"
    
    # Calculate Overall Compliance Percentage
    # UNIFIED LOGIC: Exclude optional items from both numerator and denominator
    non_optional_requirements = [r for r in requirements if not r.get('optional', False)]
    total_items = len(non_optional_requirements)
    total_complete = sum(1 for r in non_optional_requirements if r.get('status') == 'completed' and r.get('has_evidence'))
    total_verified = sum(1 for r in non_optional_requirements if r.get('verified', False))
    overall_percentage = int((total_complete / total_items) * 100) if total_items > 0 else 0
    
    return {
        "start_status": {
            "status": start_status,
            "label": start_label,
            "color": start_color,
            "complete": start_complete,
            "verified": start_verified,
            "total": start_total,
            "missing": start_missing,
            "reason": start_reason
        },
        "recruitment_file": {
            "status": recruitment_status,
            "label": recruitment_label,
            "color": recruitment_color,
            "complete": recruitment_complete,
            "total": recruitment_total,
            "missing": recruitment_missing
        },
        "policies": {
            "status": policies_status,
            "label": policies_label,
            "color": policies_color,
            "assigned": policies_assigned if policies_data else 0,
            "acknowledged": policies_acknowledged if policies_data else 0
        },
        "document_status": {
            "status": doc_status,
            "label": doc_label,
            "color": doc_color,
            "expired_count": len(expired_docs),
            "expiring_soon_count": len(expiring_soon_docs),
            "valid_count": len(valid_docs),
            "expired_docs": expired_docs,
            "expiring_soon_docs": expiring_soon_docs,
            "has_critical_expired": has_critical_expired
        },
        "overall_compliance": {
            "percentage": overall_percentage,
            "complete": total_complete,
            "verified": total_verified,
            "total": total_items
        },
        # Legacy compatibility
        "is_work_ready": start_status == "ready_to_work",
        "is_fully_compliant": total_verified == total_items and total_items > 0
    }

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
        
        if req_id in work_ready_ids or priority == 'start_required':
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
        elif priority in ['supervised_start', 'recruitment']:
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
        status_label = "Ready to Work"
        status_color = "success"
    elif all_mandatory_complete:
        status = "supervised_start"
        status_label = "Supervised Start Only"
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
    """Quick expiry alerts calculation for list views.
    Only includes ACTIVE, CURRENT records - excludes test, deleted, replaced records.
    """
    expired_count = 0
    expiring_soon_count = 0
    
    # Check documents with expiry dates (only active documents with evidence)
    docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "expiry_date": {"$exists": True, "$ne": None},
        # Must have actual evidence
        "$or": [
            {"file_url": {"$exists": True, "$ne": None}},
            {"evidence_files": {"$exists": True, "$ne": []}}
        ],
        # Exclude soft-deleted or replaced
        "status": {"$nin": ["deleted", "replaced", "removed", "archived"]}
    }, {"_id": 0, "expiry_date": 1, "evidence_files": 1}).to_list(100)
    
    for doc in docs:
        # Check document-level expiry
        doc_expiry = doc.get('expiry_date')
        if doc_expiry:
            status = calculate_expiry_status(doc_expiry)
            if status:
                if status['status'] == 'expired':
                    expired_count += 1
                elif status['status'] == 'expiring_soon':
                    expiring_soon_count += 1
        
        # Also check evidence file level expiry
        for ef in doc.get('evidence_files', []):
            if ef.get('status') == 'active' and ef.get('expiry_date'):
                status = calculate_expiry_status(ef.get('expiry_date'))
                if status:
                    if status['status'] == 'expired':
                        expired_count += 1
                    elif status['status'] == 'expiring_soon':
                        expiring_soon_count += 1
    
    # Check training records with expiry dates
    # EXCLUDE test records and ensure linked to valid requirement
    training = await db.training_records.find({
        "employee_id": employee_id,
        "expiry_date": {"$exists": True, "$ne": None},
        # Must have actual evidence
        "$or": [
            {"certificate_url": {"$exists": True, "$ne": None}},
            {"evidence_files": {"$exists": True, "$ne": []}}
        ],
        # Must be completed
        "status": {"$in": ["completed", "expiring"]},
        # Exclude TEST records
        "training_name": {"$not": {"$regex": "^TEST", "$options": "i"}}
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

# ============================================================================
# VERIFICATION STAMP SYSTEM
# Reuses: verified/verified_by/verified_at fields from existing collections
# New: Helper function to generate verification footer for PDFs
# ============================================================================

def generate_verification_stamp(
    verified_by: str = None,
    verified_at: str = None,
    document_type: str = "Document",
    include_hash: bool = True,
    content_bytes: bytes = None
) -> dict:
    """
    Generate verification stamp data for PDF footer.
    
    REUSES:
    - Existing verified_by/verified_at fields from collections
    - Existing PDF generation infrastructure (ReportLab)
    
    NO NEW COLLECTIONS - This is a presentation-layer enhancement
    
    Args:
        verified_by: Name of person who verified (from existing field)
        verified_at: Timestamp of verification (from existing field)
        document_type: Type of document for stamp text
        include_hash: Whether to generate integrity hash
        content_bytes: PDF content for hash generation
    
    Returns:
        dict with stamp text, hash, and formatted verification info
    """
    import hashlib
    
    now = datetime.now(timezone.utc)
    
    stamp = {
        "generated_at": now.isoformat(),
        "generated_at_formatted": now.strftime("%d %B %Y at %H:%M UTC"),
        "document_type": document_type,
        "verification_status": "unverified",
        "verification_text": "This document has not been verified.",
        "integrity_hash": None,
        "stamp_footer_text": ""
    }
    
    # Build verification text based on existing verified fields
    if verified_by and verified_at:
        try:
            if isinstance(verified_at, str):
                if 'T' in verified_at:
                    verified_dt = datetime.fromisoformat(verified_at.replace('Z', '+00:00'))
                else:
                    verified_dt = datetime.fromisoformat(f"{verified_at}T00:00:00+00:00")
            else:
                verified_dt = verified_at if verified_at.tzinfo else verified_at.replace(tzinfo=timezone.utc)
            
            verified_formatted = verified_dt.strftime("%d %B %Y at %H:%M UTC")
        except:
            verified_formatted = str(verified_at)
        
        stamp["verification_status"] = "verified"
        stamp["verification_text"] = f"Verified by {verified_by} on {verified_formatted}"
        stamp["verified_by"] = verified_by
        stamp["verified_at"] = verified_at
    
    # Generate integrity hash if content provided
    if include_hash and content_bytes:
        hash_obj = hashlib.sha256(content_bytes)
        stamp["integrity_hash"] = hash_obj.hexdigest()[:16].upper()  # Short hash for display
    
    # Build footer text for PDF
    footer_parts = [
        f"Generated: {stamp['generated_at_formatted']}",
    ]
    if stamp["verification_status"] == "verified":
        footer_parts.append(f"Verified: {stamp['verification_text']}")
    if stamp["integrity_hash"]:
        footer_parts.append(f"Document ID: {stamp['integrity_hash']}")
    
    stamp["stamp_footer_text"] = " | ".join(footer_parts)
    
    return stamp


def create_verification_footer_elements(
    stamp: dict,
    styles: dict = None
) -> list:
    """
    Create ReportLab elements for verification footer.
    
    REUSES: Existing ReportLab infrastructure
    
    Args:
        stamp: dict from generate_verification_stamp()
        styles: ReportLab styles dict (optional)
    
    Returns:
        List of ReportLab elements to append to PDF
    """
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    elements = []
    
    # Create styles if not provided
    if not styles:
        stamp_style = ParagraphStyle(
            'VerificationStamp',
            fontName='Helvetica',
            fontSize=7,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER
        )
        verified_style = ParagraphStyle(
            'VerifiedBadge',
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.HexColor('#059669'),
            alignment=TA_CENTER
        )
    else:
        stamp_style = styles.get('SmallText', ParagraphStyle('Default', fontSize=7))
        verified_style = styles.get('SmallText', stamp_style)
    
    # Separator line
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#D1D5DB')))
    elements.append(Spacer(1, 3*mm))
    
    # Verification badge
    if stamp.get("verification_status") == "verified":
        badge_text = f"✓ VERIFIED — {stamp.get('verified_by', 'Unknown')} — {stamp.get('verified_at', '')[:10] if stamp.get('verified_at') else ''}"
        elements.append(Paragraph(badge_text, verified_style))
        elements.append(Spacer(1, 2*mm))
    
    # Footer text
    footer_text = stamp.get("stamp_footer_text", "")
    if footer_text:
        elements.append(Paragraph(footer_text, stamp_style))
    
    # Integrity notice
    if stamp.get("integrity_hash"):
        hash_text = f"Document integrity hash: {stamp['integrity_hash']} — For verification: contact compliance@osabea.care"
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph(hash_text, stamp_style))
    
    return elements


# ============================================================================
# REFERENCE INTEGRITY SYSTEM
# Ensures references match CV OR require documented justification
# ============================================================================

def validate_reference_integrity(reference_num: int, employee_data: dict) -> dict:
    """
    Validate reference integrity rules.
    
    CRITICAL RULES:
    1. Cannot verify reference unless from_cv=True OR override_reason exists
    2. If from_cv=False, override_reason is REQUIRED
    
    Returns dict with:
    - is_valid: bool
    - can_verify: bool
    - errors: list of error messages
    - warnings: list of warning messages
    """
    prefix = f"reference_{reference_num}"
    
    from_cv = employee_data.get(f"{prefix}_from_cv")
    override_reason = employee_data.get(f"{prefix}_override_reason")
    verified = employee_data.get(f"{prefix}_verified", False)
    has_name = bool(employee_data.get(f"{prefix}_name"))
    
    result = {
        "is_valid": True,
        "can_verify": False,
        "errors": [],
        "warnings": [],
        "reference_num": reference_num
    }
    
    if not has_name:
        # No reference data yet - nothing to validate
        return result
    
    # Check if reference can be verified
    if from_cv is True:
        result["can_verify"] = True
    elif from_cv is False:
        if override_reason and len(override_reason.strip()) > 10:
            result["can_verify"] = True
        else:
            result["can_verify"] = False
            result["errors"].append(f"Reference {reference_num} does not match CV - justification required (min 10 characters)")
            result["is_valid"] = False
    else:
        # from_cv not set - warn but allow
        result["warnings"].append(f"Reference {reference_num} CV match status not confirmed")
        result["can_verify"] = True  # Allow verification but warn
    
    # Check if verified without meeting requirements
    if verified and not result["can_verify"]:
        result["errors"].append(f"Reference {reference_num} cannot be verified without CV match or documented justification")
        result["is_valid"] = False
    
    return result


def check_all_references_integrity(employee_data: dict) -> dict:
    """
    Check integrity of all references for an employee.
    
    Returns dict with:
    - all_valid: bool
    - can_complete_recruitment: bool
    - reference_1: validation result
    - reference_2: validation result
    """
    ref1 = validate_reference_integrity(1, employee_data)
    ref2 = validate_reference_integrity(2, employee_data)
    
    all_errors = ref1["errors"] + ref2["errors"]
    all_warnings = ref1["warnings"] + ref2["warnings"]
    
    return {
        "all_valid": ref1["is_valid"] and ref2["is_valid"],
        "can_complete_recruitment": len(all_errors) == 0,
        "reference_1": ref1,
        "reference_2": ref2,
        "errors": all_errors,
        "warnings": all_warnings
    }


# ============================================================================
# CV GAP ANALYSIS SYSTEM
# Detects and requires explanation of employment gaps
# ============================================================================

MIN_GAP_DAYS = 30  # Gaps less than 30 days are not flagged

def detect_cv_gaps(employment_history: List[dict]) -> List[dict]:
    """
    Detect gaps in employment history.
    
    Employment history format:
    [
        {
            "company": "...",
            "role": "...",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD" or None (current job),
            ...
        }
    ]
    
    Returns list of detected gaps:
    [
        {
            "gap_id": "gap_1",
            "previous_job": {"company": "...", "end_date": "..."},
            "next_job": {"company": "...", "start_date": "..."},
            "gap_start": "YYYY-MM-DD",
            "gap_end": "YYYY-MM-DD",
            "gap_duration_days": 45,
            "explanation": None,
            "verified": False,
            "verified_by": None,
            "verified_at": None
        }
    ]
    """
    if not employment_history or len(employment_history) < 2:
        return []
    
    # Sort by start date descending (most recent first)
    def parse_date(date_str):
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            if isinstance(date_str, str):
                if 'T' in date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
            return date_str if date_str.tzinfo else date_str.replace(tzinfo=timezone.utc)
        except:
            return datetime.now(timezone.utc)
    
    sorted_jobs = sorted(
        [j for j in employment_history if j.get("start_date")],
        key=lambda x: parse_date(x.get("start_date")),
        reverse=True  # Most recent first
    )
    
    gaps = []
    
    for i in range(len(sorted_jobs) - 1):
        current_job = sorted_jobs[i]
        previous_job = sorted_jobs[i + 1]
        
        # Get dates
        current_start = parse_date(current_job.get("start_date"))
        previous_end = parse_date(previous_job.get("end_date"))
        
        # Calculate gap
        gap_days = (current_start - previous_end).days
        
        if gap_days > MIN_GAP_DAYS:
            gaps.append({
                "gap_id": f"gap_{i+1}",
                "previous_job": {
                    "company": previous_job.get("company", "Unknown"),
                    "role": previous_job.get("role", ""),
                    "end_date": previous_job.get("end_date")
                },
                "next_job": {
                    "company": current_job.get("company", "Unknown"),
                    "role": current_job.get("role", ""),
                    "start_date": current_job.get("start_date")
                },
                "gap_start": previous_job.get("end_date"),
                "gap_end": current_job.get("start_date"),
                "gap_duration_days": gap_days,
                "explanation": current_job.get("gap_explanation") or previous_job.get("gap_after_explanation"),
                "verified": False,
                "verified_by": None,
                "verified_at": None
            })
    
    return gaps


def check_cv_gaps_complete(employee_data: dict) -> dict:
    """
    Check if all CV gaps have required explanations.
    
    Returns:
    - all_gaps_explained: bool
    - unexplained_gaps: list
    - can_complete_recruitment: bool
    """
    gaps = employee_data.get("cv_gaps_detected", [])
    
    if not gaps:
        return {
            "all_gaps_explained": True,
            "unexplained_gaps": [],
            "total_gaps": 0,
            "can_complete_recruitment": True
        }
    
    unexplained = []
    for gap in gaps:
        explanation = gap.get("explanation")
        if not explanation or len(str(explanation).strip()) < 10:
            unexplained.append(gap)
    
    return {
        "all_gaps_explained": len(unexplained) == 0,
        "unexplained_gaps": unexplained,
        "total_gaps": len(gaps),
        "explained_gaps": len(gaps) - len(unexplained),
        "can_complete_recruitment": len(unexplained) == 0
    }



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
    """Check if a specific mandatory item is complete for an employee.
    UNIFIED LOGIC - Used by all compliance calculations.
    
    COMPLETED means:
    - verified document OR
    - valid training record (completed/expiring, not deleted/superseded) OR
    - completed acknowledgement
    
    EXCLUDED from counts:
    - optional requirements
    - deleted/superseded/archived records
    - test data
    """
    result = {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "type": item["type"],
        "status": "missing",
        "verified": False,
        "details": None,
        "expiry_date": None,
        "optional": item.get("optional", False),
        "has_evidence": False
    }
    
    requirement_id = item["id"]
    item_type = item.get("type", "document")
    
    # ====== ACKNOWLEDGEMENT TYPE ======
    if item_type == "acknowledgement":
        ack = await db.requirement_acknowledgements.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "acknowledged": True
        }, {"_id": 0})
        
        if ack:
            result["status"] = "complete"
            result["verified"] = True  # Acknowledgements auto-verify
            result["has_evidence"] = True
            result["details"] = f"Acknowledged by {ack.get('acknowledged_by_name', 'Unknown')}"
        return result
    
    # ====== FORM-GENERATED TYPE ======
    if item_type in ["form", "form-generated"]:
        # FIRST: Check for structured form submissions (new system)
        form_submission = await db.form_submissions.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "status": {"$nin": ["deleted", "superseded"]}
        }, {"_id": 0, "id": 1, "status": 1, "verified": 1, "submitted_at": 1, "submitted_by_name": 1})
        
        if form_submission:
            result["status"] = "complete"
            result["verified"] = form_submission.get("verified", False)
            result["has_evidence"] = True
            result["details"] = f"Form submitted by {form_submission.get('submitted_by_name', 'Unknown')}"
            result["form_submission_id"] = form_submission.get("id")
            return result
        
        # Check for completed form with PDF evidence (legacy generated_forms)
        form = await db.generated_forms.find_one({
            "employee_id": employee_id,
            "$or": [
                {"requirement_id": requirement_id},
                {"template_name": {"$regex": item.get("template_name", "NOMATCH"), "$options": "i"}}
            ],
            "status": {"$in": ["completed", "completed_imported", "reviewed", "signed_off"]}
        }, {"_id": 0, "id": 1, "status": 1, "pdf_url": 1, "completed_at": 1, "signed_off_at": 1})
        
        if form:
            has_pdf = bool(form.get("pdf_url"))
            result["status"] = "complete" if has_pdf else "completed_no_evidence"
            result["verified"] = form.get("status") == "signed_off"
            result["has_evidence"] = has_pdf
            result["details"] = f"Form ID: {form['id']}"
            return result
        
        # Fallback: Check for documents uploaded against this requirement
        # (handles case where document was uploaded instead of form)
        docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "file_url": {"$exists": True, "$ne": None},
            "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]},
            "$or": [
                {"active": {"$exists": False}},
                {"active": True}
            ]
        }, {"_id": 0, "id": 1, "status": 1, "verified": 1}).to_list(5)
        
        if docs:
            result["status"] = "complete"
            result["verified"] = all(d.get("verified") or d.get("status") == "approved" for d in docs)
            result["has_evidence"] = True
            result["details"] = f"{len(docs)} document(s) uploaded"
            return result
        
        return result
    
    # ====== DOCUMENT TYPE ======
    if item_type == "document":
        min_count = item.get("min_files", 1)
        
        # Get active documents (exclude deleted/superseded)
        docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]},
            "$or": [
                {"active": {"$exists": False}},
                {"active": True}
            ]
        }, {"_id": 0}).to_list(20)
        
        # Count documents with active evidence (file_url or active evidence_files)
        active_docs_count = 0
        for doc in docs:
            has_active_evidence = False
            
            # Check evidence_files array for active files
            evidence_files = doc.get('evidence_files', [])
            if evidence_files:
                for ef in evidence_files:
                    ef_status = ef.get('status', 'active')
                    if ef_status in ['active', None] and ef.get('file_url'):
                        has_active_evidence = True
                        break
            # Fallback: check file_url (legacy format) only if no evidence_files with any status
            elif doc.get('file_url'):
                has_active_evidence = True
            
            if has_active_evidence:
                active_docs_count += 1
        
        if active_docs_count >= min_count:
            result["status"] = "complete"
            result["verified"] = all(d.get("verified") or d.get("status") == "approved" for d in docs if d.get("file_url") or d.get("evidence_files"))
            result["has_evidence"] = True
            result["details"] = f"{active_docs_count} document(s) with active evidence"
            
            # Check for expiring documents
            for doc in docs:
                exp_date_str = doc.get("expiry_date")
                if exp_date_str:
                    try:
                        exp_date = datetime.fromisoformat(exp_date_str.replace('Z', '+00:00'))
                        if exp_date < datetime.now(timezone.utc):
                            result["status"] = "expired"
                            result["expiry_date"] = exp_date_str
                            break
                        elif exp_date < datetime.now(timezone.utc) + timedelta(days=30):
                            result["status"] = "expiring"
                            result["expiry_date"] = exp_date_str
                    except:
                        pass
        return result
    
    # ====== TRAINING TYPE ======
    if item_type == "training":
        # Check for training records (exclude deleted/superseded/TEST)
        # Match by requirement_id OR training name (same logic as /compliance-requirements)
        training_name = item.get("training_name", item.get("name", ""))
        
        # First try by requirement_id (newer records)
        training = await db.training_records.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "status": {"$in": ["completed", "expiring"]},
            "$and": [
                {"training_name": {"$not": {"$regex": "^TEST", "$options": "i"}}}
            ]
        }, {"_id": 0, "id": 1, "status": 1, "verified": 1, "completed_at": 1, "expiry_date": 1, 
            "certificate_url": 1, "evidence_files": 1})
        
        # Fallback to training name matching (legacy records)
        if not training and training_name:
            training = await db.training_records.find_one({
                "employee_id": employee_id,
                "status": {"$in": ["completed", "expiring"]},
                "$and": [
                    {"training_name": {"$regex": training_name, "$options": "i"}},
                    {"training_name": {"$not": {"$regex": "^TEST", "$options": "i"}}}
                ]
            }, {"_id": 0, "id": 1, "status": 1, "verified": 1, "completed_at": 1, "expiry_date": 1, 
                "certificate_url": 1, "evidence_files": 1})
        
        if training:
            # Has evidence = has certificate URL or evidence files
            has_evidence = bool(training.get("certificate_url") or training.get("evidence_files"))
            result["status"] = "complete" if has_evidence else "completed_no_evidence"
            result["verified"] = training.get("verified", False)
            result["has_evidence"] = has_evidence
            result["details"] = f"Completed: {training.get('completed_at', 'N/A')}"
            
            if training.get("expiry_date"):
                try:
                    exp_date = datetime.fromisoformat(training["expiry_date"].replace('Z', '+00:00'))
                    if exp_date < datetime.now(timezone.utc):
                        result["status"] = "expired"
                        result["expiry_date"] = training["expiry_date"]
                    elif exp_date < datetime.now(timezone.utc) + timedelta(days=30):
                        result["status"] = "expiring"
                        result["expiry_date"] = training["expiry_date"]
                except:
                    pass
        return result
    
    return result

async def calculate_employee_compliance(employee_id: str, role: str) -> dict:
    """
    UNIFIED COMPLIANCE CALCULATION - Single source of truth for all views.
    
    Used by:
    - Employee list view
    - Employee profile
    - Dashboard
    - Audit View
    
    Rules:
    - COMPLETED = verified document OR valid training OR completed acknowledgement
    - EXCLUDE optional items from BOTH numerator and denominator
    - EXCLUDE deleted/superseded/test records
    """
    mandatory_items = get_mandatory_items_for_role(role)
    
    results = []
    complete_count = 0
    verified_count = 0
    expiring_count = 0
    missing_count = 0
    optional_count = 0  # Track optional items to exclude from total
    archived_count = 0  # Track archived items to exclude from total
    
    for item in mandatory_items:
        # Skip archived items from compliance calculation (hidden from UI, historical only)
        if item.get("archived", False):
            archived_count += 1
            continue
        
        # Skip optional items from compliance calculation
        is_optional = item.get("optional", False)
        if is_optional:
            optional_count += 1
        
        check = await check_item_completion(employee_id, item)
        results.append(check)
        
        # Only count non-optional items toward compliance
        if not is_optional:
            if check["status"] in ["complete", "expiring", "expired"]:
                # Must have evidence to count
                if check.get("has_evidence", True):  # Default True for backwards compat
                    complete_count += 1
                    if check["verified"]:
                        verified_count += 1
                    if check["status"] == "expiring":
                        expiring_count += 1
                else:
                    missing_count += 1  # Completed but no evidence = still missing
            else:
                missing_count += 1
    
    # Total excludes optional and archived items
    total_items = len(mandatory_items) - optional_count - archived_count
    
    # Calculate percentages
    completion_percentage = int((complete_count / total_items) * 100) if total_items > 0 else 0
    verification_percentage = int((verified_count / complete_count) * 100) if complete_count > 0 else 0
    
    return {
        "items": results,
        "total_items": total_items,
        "complete_count": complete_count,
        "verified_count": verified_count,
        "expiring_count": expiring_count,
        "missing_count": missing_count,
        "optional_count": optional_count,
        "completion_percentage": completion_percentage,
        "verification_percentage": verification_percentage
    }


async def get_employee_dbs_summary(employee_id: str) -> dict:
    """
    SINGLE SOURCE OF TRUTH for DBS status across all views.
    
    SAFETY ENGINE: Computes blocking status for work readiness.
    
    Derives DBS summary from existing evidence:
    - DBS Certificate (requirement_id: dbs_certificate)
    - DBS Update Service Check (requirement_id: dbs_check)
    
    Returns computed status, dates, review schedule, and blocking state.
    
    STATUS BANDS:
    - current: >30 days until review
    - due_soon: 31-60 days until review  
    - urgent: 1-30 days until review
    - overdue: review date passed
    
    BLOCKING RULES:
    - Missing DBS where required = BLOCKING
    - Overdue review beyond grace period = BLOCKING (14 day grace)
    - Pending verification = WARNING only
    - Due soon = WARNING only
    """
    DBS_REVIEW_INTERVAL_DAYS = 365  # 12 months for DBS Update Service checks
    DBS_BLOCKING_GRACE_DAYS = 14  # Grace period before overdue becomes blocking
    
    # Initialize summary with safety engine fields
    summary = {
        # Core identification
        "dbs_status": "missing",
        "dbs_status_label": "Missing",
        "dbs_status_color": "red",
        
        # Status band (current/due_soon/urgent/overdue)
        "status_band": "overdue",
        
        # Dates
        "certificate_issue_date": None,
        "update_service_last_checked": None,
        "review_due_date": None,
        "days_remaining": None,
        
        # Evidence flags
        "certificate_on_file": False,
        "certificate_verified": False,
        "certificate_date": None,
        "update_service_active": False,
        "update_service_verified": False,
        "update_service_date": None,
        
        # Safety engine outputs
        "is_blocking": True,  # Default to blocking if missing
        "blocking_reason": "DBS evidence missing",
        "needs_attention": True,
        
        # Audit trail
        "source_date_used": None,
        "rule_applied": "no_evidence"
    }
    
    # Get DBS Certificate record (most recent active)
    dbs_cert = await db.employee_documents.find_one({
        "employee_id": employee_id,
        "requirement_id": "dbs_certificate",
        "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]},
        "$or": [
            {"active": {"$exists": False}},
            {"active": True}
        ],
        "file_url": {"$exists": True, "$ne": None}
    }, {"_id": 0}, sort=[("uploaded_at", -1)])
    
    # Get DBS Update Service Check record (most recent active)
    dbs_update = await db.employee_documents.find_one({
        "employee_id": employee_id,
        "requirement_id": "dbs_check",
        "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]},
        "$or": [
            {"active": {"$exists": False}},
            {"active": True}
        ],
        "file_url": {"$exists": True, "$ne": None}
    }, {"_id": 0}, sort=[("uploaded_at", -1)])
    
    now = datetime.now(timezone.utc)
    
    # Process DBS Certificate
    if dbs_cert:
        summary["certificate_on_file"] = True
        summary["certificate_verified"] = dbs_cert.get("verified", False)
        
        # Use issue_date if available, else uploaded_at
        cert_date = dbs_cert.get("issue_date") or dbs_cert.get("uploaded_at")
        if cert_date:
            if isinstance(cert_date, str):
                try:
                    cert_date = datetime.fromisoformat(cert_date.replace('Z', '+00:00'))
                except:
                    cert_date = None
            if cert_date:
                summary["certificate_date"] = cert_date.isoformat()
                summary["certificate_issue_date"] = cert_date.isoformat()
    
    # Process DBS Update Service Check
    if dbs_update:
        summary["update_service_active"] = True
        summary["update_service_verified"] = dbs_update.get("verified", False)
        
        # Use uploaded_at or issue_date as the check date
        check_date = dbs_update.get("uploaded_at") or dbs_update.get("issue_date")
        if isinstance(check_date, str):
            try:
                check_date = datetime.fromisoformat(check_date.replace('Z', '+00:00'))
            except:
                check_date = None
        
        if check_date:
            summary["update_service_date"] = check_date.isoformat()
            summary["update_service_last_checked"] = check_date.isoformat()
            summary["source_date_used"] = check_date.isoformat()
            
            # Calculate next review due (12 months from last check)
            next_review = check_date + timedelta(days=DBS_REVIEW_INTERVAL_DAYS)
            summary["review_due_date"] = next_review.isoformat()
            summary["next_dbs_review_due"] = next_review.isoformat()  # Legacy field
            
            # Calculate days until review
            days_until = (next_review - now).days
            summary["days_remaining"] = days_until
            summary["days_until_review"] = days_until  # Legacy field
    
    # Determine overall DBS status and blocking state
    if summary["update_service_active"] and summary["update_service_verified"]:
        # Update Service is the gold standard
        days_until = summary["days_remaining"]
        summary["rule_applied"] = "update_service_verified"
        
        if days_until is not None:
            if days_until < -DBS_BLOCKING_GRACE_DAYS:
                # Beyond grace period - BLOCKING
                summary["dbs_status"] = "review_overdue"
                summary["dbs_status_label"] = f"Overdue by {abs(days_until)}d"
                summary["dbs_status_color"] = "red"
                summary["status_band"] = "overdue"
                summary["is_blocking"] = True
                summary["blocking_reason"] = f"DBS review overdue by {abs(days_until)} days (exceeds {DBS_BLOCKING_GRACE_DAYS}d grace)"
                summary["needs_attention"] = True
            elif days_until < 0:
                # Within grace period - WARNING only
                summary["dbs_status"] = "review_overdue"
                summary["dbs_status_label"] = f"Overdue by {abs(days_until)}d"
                summary["dbs_status_color"] = "red"
                summary["status_band"] = "overdue"
                summary["is_blocking"] = False
                summary["blocking_reason"] = None
                summary["needs_attention"] = True
            elif days_until <= 30:
                # Urgent - WARNING
                summary["dbs_status"] = "review_urgent"
                summary["dbs_status_label"] = f"Due in {days_until}d"
                summary["dbs_status_color"] = "amber"
                summary["status_band"] = "urgent"
                summary["is_blocking"] = False
                summary["blocking_reason"] = None
                summary["needs_attention"] = True
            elif days_until <= 60:
                # Due soon - WARNING
                summary["dbs_status"] = "review_due_soon"
                summary["dbs_status_label"] = f"Due in {days_until}d"
                summary["dbs_status_color"] = "amber"
                summary["status_band"] = "due_soon"
                summary["is_blocking"] = False
                summary["blocking_reason"] = None
                summary["needs_attention"] = True
            else:
                # Current - all good
                summary["dbs_status"] = "current"
                summary["dbs_status_label"] = "Current"
                summary["dbs_status_color"] = "green"
                summary["status_band"] = "current"
                summary["is_blocking"] = False
                summary["blocking_reason"] = None
                summary["needs_attention"] = False
        else:
            summary["dbs_status"] = "current"
            summary["dbs_status_label"] = "Current"
            summary["dbs_status_color"] = "green"
            summary["status_band"] = "current"
            summary["is_blocking"] = False
            summary["blocking_reason"] = None
            summary["needs_attention"] = False
            
    elif summary["update_service_active"]:
        # Has update service but not verified - WARNING only
        summary["dbs_status"] = "pending_verification"
        summary["dbs_status_label"] = "Awaiting Verification"
        summary["dbs_status_color"] = "blue"
        summary["status_band"] = "urgent"
        summary["is_blocking"] = False  # Not blocking, just needs verification
        summary["blocking_reason"] = None
        summary["needs_attention"] = True
        summary["rule_applied"] = "update_service_unverified"
        
    elif summary["certificate_on_file"] and summary["certificate_verified"]:
        # Has certificate only (no update service) - WARNING, recommend update service
        summary["dbs_status"] = "certificate_only"
        summary["dbs_status_label"] = "Certificate Only (Needs Update Service)"
        summary["dbs_status_color"] = "amber"
        summary["status_band"] = "due_soon"
        summary["is_blocking"] = False
        summary["blocking_reason"] = None
        summary["needs_attention"] = True
        summary["rule_applied"] = "certificate_only_no_update_service"
        # Use certificate date as source
        if summary["certificate_date"]:
            summary["source_date_used"] = summary["certificate_date"]
            summary["update_service_last_checked"] = summary["certificate_date"]  # For display
            
    elif summary["certificate_on_file"]:
        # Has certificate but not verified - WARNING only
        summary["dbs_status"] = "pending_verification"
        summary["dbs_status_label"] = "Awaiting Verification"
        summary["dbs_status_color"] = "blue"
        summary["status_band"] = "urgent"
        summary["is_blocking"] = False
        summary["blocking_reason"] = None
        summary["needs_attention"] = True
        summary["rule_applied"] = "certificate_unverified"
        
    else:
        # No DBS evidence at all - BLOCKING
        summary["dbs_status"] = "missing"
        summary["dbs_status_label"] = "Missing"
        summary["dbs_status_color"] = "red"
        summary["status_band"] = "overdue"
        summary["is_blocking"] = True
        summary["blocking_reason"] = "DBS certificate and Update Service check both missing"
        summary["needs_attention"] = True
        summary["rule_applied"] = "no_evidence"
    
    return summary


async def get_employee_rtw_summary(employee_id: str) -> dict:
    """
    SINGLE SOURCE OF TRUTH for Right to Work status across all views.
    
    SAFETY ENGINE: Computes blocking status for work readiness.
    
    DATA SOURCES (SIMPLIFIED):
    ═══════════════════════════════════════════════════════════════════
    RIGHT TO WORK DOCUMENTS (requirement_id: right_to_work_documents)
      → evidence_type (passport, BRP, etc.)
      → documents_on_file flag
      → documents_verified flag
      → Used for: Evidence presence only
      → NOT used for: Expiry display, countdown, alerts
    
    RIGHT TO WORK VERIFICATION (requirement_id: right_to_work_check)
      → permission_type (permanent / time_limited)
      → expiry_date (for card display and countdown)
      → checked_at, checked_by
      → Used for: ALL status, expiry, countdown, blocking logic
    ═══════════════════════════════════════════════════════════════════
    
    STATUS BANDS:
    - current: >60 days until expiry OR permanent
    - due_soon: 31-60 days until expiry
    - urgent: 1-30 days until expiry
    - expired: expiry date passed
    
    BLOCKING RULES:
    - Missing RTW verification = BLOCKING
    - Expired RTW = BLOCKING
    - Not verified = BLOCKING (legal requirement)
    - Expiring soon = WARNING only
    """
    summary = {
        # Core status (derived from VERIFICATION)
        "rtw_status": "missing",
        "rtw_status_label": "Missing Verification",
        "rtw_status_color": "red",
        "status_band": "expired",
        
        # From RTW DOCUMENTS (evidence only)
        "evidence_type": None,  # passport, brp, share_code, etc.
        "documents_on_file": False,
        "documents_verified": False,
        
        # From RTW VERIFICATION (source of truth for monitoring)
        "permission_type": None,  # permanent or time_limited
        "expiry_date": None,  # From verification - drives card display
        "days_remaining": None,  # Computed from verification expiry
        "checked_at": None,
        "checked_by": None,
        "verified_date": None,
        "verification_on_file": False,
        "verification_verified": False,
        
        # Safety engine outputs
        "is_blocking": True,
        "blocking_reason": "Right to Work verification missing",
        "needs_attention": True,
        
        # Audit trail
        "source": "verification",  # Always verification for expiry
        "rule_applied": "no_verification"
    }
    
    # Get Right to Work Documents (evidence only - NOT used for expiry)
    rtw_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": "right_to_work_documents",
        "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]},
        "$or": [{"active": {"$exists": False}}, {"active": True}],
        "file_url": {"$exists": True, "$ne": None}
    }, {"_id": 0}).to_list(10)
    
    # Get Right to Work Verification (SOURCE OF TRUTH for status/expiry)
    rtw_check = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": "right_to_work_check",
        "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]},
        "$or": [{"active": {"$exists": False}}, {"active": True}],
        "file_url": {"$exists": True, "$ne": None}
    }, {"_id": 0}).to_list(5)
    
    now = datetime.now(timezone.utc)
    
    # ═══════════════════════════════════════════════════════════════════
    # STEP 1: Process RTW Documents (evidence presence ONLY)
    # ═══════════════════════════════════════════════════════════════════
    if rtw_docs:
        summary["documents_on_file"] = True
        summary["documents_verified"] = all(
            d.get("verified") or d.get("status") == "approved" 
            for d in rtw_docs
        )
        
        # Detect evidence type from document metadata
        for doc in rtw_docs:
            doc_type = (doc.get("document_type") or doc.get("evidence_type") or "").lower()
            notes = (doc.get("notes") or "").lower()
            
            if "passport" in doc_type or "passport" in notes:
                summary["evidence_type"] = "passport"
            elif "brp" in doc_type or "biometric" in notes:
                summary["evidence_type"] = "brp"
            elif "share" in doc_type or "share code" in notes:
                summary["evidence_type"] = "share_code"
            elif "settled" in notes or "euss" in notes:
                summary["evidence_type"] = "settled_status"
            elif not summary["evidence_type"]:
                summary["evidence_type"] = "document"
    
    # ═══════════════════════════════════════════════════════════════════
    # STEP 2: Process RTW Verification (SOURCE OF TRUTH for all status)
    # ═══════════════════════════════════════════════════════════════════
    if rtw_check:
        summary["verification_on_file"] = True
        summary["verification_verified"] = all(
            c.get("verified") or c.get("status") == "approved" 
            for c in rtw_check
        )
        
        # Get the most recent verification record
        for check in rtw_check:
            # Extract checked_at
            if not summary["checked_at"]:
                summary["checked_at"] = check.get("uploaded_at") or check.get("verified_at")
            
            # Extract checked_by
            if not summary["checked_by"]:
                summary["checked_by"] = check.get("verified_by") or check.get("uploaded_by")
            
            # Extract verified_date
            if not summary["verified_date"] and check.get("verified"):
                summary["verified_date"] = check.get("uploaded_at") or check.get("verified_at")
            
            # ═══════════════════════════════════════════════════════════
            # EXPIRY DATE: From VERIFICATION record ONLY
            # This drives the card display and countdown
            # ═══════════════════════════════════════════════════════════
            if check.get("expiry_date") and not summary["expiry_date"]:
                summary["expiry_date"] = check.get("expiry_date")
            
            # Detect permission type from verification notes/metadata
            notes = (check.get("notes") or "").lower()
            doc_type = (check.get("document_type") or "").lower()
            
            if not summary["permission_type"]:
                if "permanent" in notes or "british" in notes or "irish" in notes or "settled status" in notes or "indefinite" in notes:
                    summary["permission_type"] = "permanent"
                elif "visa" in notes or "limited" in notes or "pre-settled" in notes or "brp" in doc_type or "time" in notes:
                    summary["permission_type"] = "time_limited"
        
        # If expiry_date exists, it's time-limited; if not, check if explicitly permanent
        if summary["expiry_date"]:
            summary["permission_type"] = "time_limited"
        elif not summary["permission_type"]:
            # No expiry date and no explicit type = permanent
            summary["permission_type"] = "permanent"
    
    # ═══════════════════════════════════════════════════════════════════
    # STEP 3: Calculate days_remaining from VERIFICATION expiry
    # ═══════════════════════════════════════════════════════════════════
    if summary["expiry_date"]:
        try:
            expiry_str = summary["expiry_date"]
            if 'T' in expiry_str:
                expiry_dt = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            else:
                expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            
            summary["days_remaining"] = (expiry_dt - now).days
        except Exception as e:
            print(f"RTW verification expiry date parsing error: {e} for date: {summary['expiry_date']}")
    
    # Determine status and blocking state
    if summary["documents_on_file"] and summary["verification_on_file"]:
        if summary["documents_verified"] and summary["verification_verified"]:
            summary["rule_applied"] = "fully_verified"
            
            # Check expiry status for time-limited permission
            days_remaining = summary.get("days_remaining")
            
            if days_remaining is not None:
                if days_remaining < 0:
                    # EXPIRED - BLOCKING
                    summary["rtw_status"] = "expired"
                    summary["rtw_status_label"] = f"Expired {abs(days_remaining)}d ago"
                    summary["rtw_status_color"] = "red"
                    summary["status_band"] = "expired"
                    summary["is_blocking"] = True
                    summary["blocking_reason"] = f"Right to Work expired {abs(days_remaining)} days ago - cannot legally employ"
                    summary["needs_attention"] = True
                elif days_remaining <= 30:
                    # Urgent - WARNING
                    summary["rtw_status"] = "expiring_urgent"
                    summary["rtw_status_label"] = f"Expires in {days_remaining}d"
                    summary["rtw_status_color"] = "amber"
                    summary["status_band"] = "urgent"
                    summary["is_blocking"] = False
                    summary["blocking_reason"] = None
                    summary["needs_attention"] = True
                    summary["expiry_status"] = "expiring_soon"
                elif days_remaining <= 60:
                    # Due soon - WARNING
                    summary["rtw_status"] = "expiring_soon"
                    summary["rtw_status_label"] = f"Expires in {days_remaining}d"
                    summary["rtw_status_color"] = "amber"
                    summary["status_band"] = "due_soon"
                    summary["is_blocking"] = False
                    summary["blocking_reason"] = None
                    summary["needs_attention"] = True
                    summary["expiry_status"] = "expiring_soon"
                else:
                    # Current (>60 days until expiry)
                    summary["rtw_status"] = "verified"
                    # Show time-limited status clearly
                    summary["rtw_status_label"] = "Verified (Time-Limited)"
                    summary["rtw_status_color"] = "green"
                    summary["status_band"] = "current"
                    summary["is_blocking"] = False
                    summary["blocking_reason"] = None
                    summary["needs_attention"] = False
                    summary["expiry_status"] = "valid"
            else:
                # No expiry date - permanent permission
                summary["rtw_status"] = "verified"
                summary["rtw_status_label"] = "Verified (Permanent)"
                summary["rtw_status_color"] = "green"
                summary["status_band"] = "current"
                summary["is_blocking"] = False
                summary["blocking_reason"] = None
                summary["needs_attention"] = False
                summary["expiry_status"] = "permanent"
                summary["permission_type"] = "permanent"  # Ensure permission_type is set
        else:
            # Not verified - BLOCKING (legal requirement)
            summary["rtw_status"] = "pending_verification"
            summary["rtw_status_label"] = "Awaiting Verification"
            summary["rtw_status_color"] = "blue"
            summary["status_band"] = "urgent"
            summary["is_blocking"] = True
            summary["blocking_reason"] = "Right to Work not verified - legal requirement before employment"
            summary["needs_attention"] = True
            summary["rule_applied"] = "pending_verification"
            
    elif summary["documents_on_file"] or summary["verification_on_file"]:
        # Partial - only one of the two requirements - BLOCKING
        summary["rtw_status"] = "incomplete"
        summary["rtw_status_label"] = "Incomplete"
        summary["rtw_status_color"] = "amber"
        summary["status_band"] = "urgent"
        summary["is_blocking"] = True
        summary["blocking_reason"] = "Right to Work incomplete - both documents and verification check required"
        summary["needs_attention"] = True
        summary["rule_applied"] = "incomplete_evidence"
    else:
        # Missing - BLOCKING
        summary["rtw_status"] = "missing"
        summary["rtw_status_label"] = "Missing"
        summary["rtw_status_color"] = "red"
        summary["status_band"] = "expired"
        summary["is_blocking"] = True
        summary["blocking_reason"] = "Right to Work evidence missing - cannot legally employ"
        summary["needs_attention"] = True
        summary["rule_applied"] = "no_evidence"
    
    return summary


# Core/Start-Critical Training Requirements that BLOCK work readiness
CORE_TRAINING_REQUIREMENTS = [
    "safeguarding_adults",
    "safeguarding_children", 
    "moving_handling",
    "manual_handling",
    "infection_control",
    "medication_awareness",
    "health_safety",
    "basic_life_support",
    "first_aid",
    "food_hygiene",
    "fire_safety",
    "coshh",
    "gdpr_data_protection",
    "equality_diversity",
    "mental_capacity_act",
    "deprivation_of_liberty"
]

# Training renewal intervals (days) - default is 365 (annual)
TRAINING_RENEWAL_RULES = {
    "safeguarding_adults": 365,
    "safeguarding_children": 365,
    "moving_handling": 365,
    "manual_handling": 365,
    "infection_control": 365,
    "medication_awareness": 365,
    "health_safety": 365,
    "basic_life_support": 365,
    "first_aid": 1095,  # 3 years
    "food_hygiene": 1095,  # 3 years
    "fire_safety": 365,
    "default": 365  # Default to annual
}


async def get_employee_training_safety_summary(employee_id: str) -> dict:
    """
    SINGLE SOURCE OF TRUTH for Training status across all views.
    
    SAFETY ENGINE: Computes blocking status for work readiness.
    
    Only CORE/START-CRITICAL training blocks work readiness:
    - Safeguarding, Manual Handling, Infection Control, etc.
    
    Supplementary/additional training = warning only, never blocks.
    
    STATUS BANDS:
    - current: >30 days until expiry
    - due_soon: 31-60 days until expiry
    - urgent: 1-30 days until expiry
    - expired: expiry date passed OR missing core training
    
    BLOCKING RULES:
    - Missing core/start-critical training = BLOCKING
    - Expired core/start-critical training = BLOCKING
    - Unverified core training = BLOCKING
    - Supplementary training expired/missing = WARNING only
    
    EXPIRY CALCULATION:
    - Use explicit expiry_date if present
    - Otherwise compute: completion_date + renewal_interval
    - Use earlier of the two if both exist (unless policy override)
    """
    summary = {
        # Core counts
        "required_current_count": 0,  # Core training that is current
        "required_total_count": 0,    # Total core training required
        "expiring_soon_count": 0,     # Training expiring in 60 days
        "expired_count": 0,           # Expired training
        
        # Status band
        "status_band": "current",
        "training_status": "current",
        "training_status_label": "Up to Date",
        "training_status_color": "green",
        
        # Items needing attention
        "next_due_items": [],         # List of {name, days_remaining, status}
        "missing_core_items": [],     # Core training not started
        "expired_items": [],          # Expired training names
        
        # Safety engine outputs
        "is_blocking": False,
        "blocking_reason": None,
        "needs_attention": False,
        
        # Audit trail
        "rule_applied": "all_current"
    }
    
    now = datetime.now(timezone.utc)
    
    # Get all active training records for employee
    training_records = await db.training_records.find({
        "employee_id": employee_id,
        "status": {"$in": ["completed", "verified", "expiring", "active"]},
        "deleted_at": {"$exists": False}
    }, {"_id": 0}).to_list(100)
    
    # Get requirements from MANDATORY_ITEMS (single source of truth for requirements)
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "role": 1})
    role = employee.get("role", "care_worker") if employee else "care_worker"
    
    # Build set of required training IDs from MANDATORY_ITEMS
    required_training_ids = set()
    core_training_ids = set()
    
    # Get training items from MANDATORY_ITEMS (source of truth)
    training_items = MANDATORY_ITEMS.get("training", [])
    # Add nurse-specific training if applicable
    if role and "nurse" in role.lower():
        training_items = training_items + [i for i in MANDATORY_ITEMS.get("nurse_specific", []) if i.get("type") == "training"]
    
    for item in training_items:
        req_id = item.get("id", "")
        priority = item.get("priority", "secondary")
        
        # All training items are required
        required_training_ids.add(req_id)
        
        # Check if it's core/start-critical training
        if priority == "start_required":
            core_training_ids.add(req_id)
        elif any(core in req_id.lower() for core in CORE_TRAINING_REQUIREMENTS):
            core_training_ids.add(req_id)
    
    # Process training records
    completed_training = {}  # req_id -> {record, expiry_date, days_remaining, is_core}
    
    for record in training_records:
        req_id = record.get("requirement_id", "")
        training_name = record.get("training_name", req_id)
        
        # Skip if not verified (only count verified training)
        if not record.get("verified", False) and record.get("status") != "verified":
            # Check if this is core training that's unverified
            if req_id in core_training_ids or any(core in req_id.lower() for core in CORE_TRAINING_REQUIREMENTS):
                summary["missing_core_items"].append(f"{training_name} (unverified)")
            continue
        
        # Calculate expiry
        explicit_expiry = record.get("expiry_date")
        completion_date = record.get("completed_at") or record.get("completion_date")
        
        # Get renewal interval for this training type
        renewal_days = TRAINING_RENEWAL_RULES.get("default", 365)
        for rule_key, rule_days in TRAINING_RENEWAL_RULES.items():
            if rule_key in req_id.lower():
                renewal_days = rule_days
                break
        
        # Calculate computed expiry from completion date
        computed_expiry = None
        if completion_date:
            try:
                if isinstance(completion_date, str):
                    comp_dt = datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
                else:
                    comp_dt = completion_date
                computed_expiry = (comp_dt + timedelta(days=renewal_days)).isoformat()
            except:
                pass
        
        # Use explicit expiry if present, else computed, take earlier date
        final_expiry = None
        if explicit_expiry and computed_expiry:
            final_expiry = min(explicit_expiry, computed_expiry)
        elif explicit_expiry:
            final_expiry = explicit_expiry
        elif computed_expiry:
            final_expiry = computed_expiry
        
        # Calculate days remaining
        days_remaining = None
        if final_expiry:
            try:
                exp_dt = datetime.fromisoformat(final_expiry.replace('Z', '+00:00'))
                days_remaining = (exp_dt - now).days
            except:
                pass
        
        is_core = req_id in core_training_ids or any(core in req_id.lower() for core in CORE_TRAINING_REQUIREMENTS)
        
        completed_training[req_id] = {
            "name": training_name,
            "expiry_date": final_expiry,
            "days_remaining": days_remaining,
            "is_core": is_core,
            "verified": record.get("verified", False) or record.get("status") == "verified"
        }
    
    # Analyze training status
    core_missing = []
    core_expired = []
    expiring_soon = []
    
    for req_id in core_training_ids:
        if req_id not in completed_training:
            # Find requirement name from training_items
            req_name = req_id
            for item in training_items:
                if item.get("id") == req_id:
                    req_name = item.get("name", req_id)
                    break
            core_missing.append(req_name)
    
    for req_id, data in completed_training.items():
        days = data.get("days_remaining")
        name = data.get("name", req_id)
        is_core = data.get("is_core", False)
        
        if days is not None:
            if days < 0:
                # Expired
                summary["expired_count"] += 1
                summary["expired_items"].append(name)
                if is_core:
                    core_expired.append(name)
            elif days <= 30:
                # Urgent
                summary["expiring_soon_count"] += 1
                summary["next_due_items"].append({
                    "name": name,
                    "days_remaining": days,
                    "status": "urgent",
                    "is_core": is_core
                })
                expiring_soon.append(name)
            elif days <= 60:
                # Due soon
                summary["expiring_soon_count"] += 1
                summary["next_due_items"].append({
                    "name": name,
                    "days_remaining": days,
                    "status": "due_soon",
                    "is_core": is_core
                })
    
    # Count current core training
    summary["required_total_count"] = len(core_training_ids)
    summary["required_current_count"] = len([
        req_id for req_id in core_training_ids 
        if req_id in completed_training 
        and (completed_training[req_id].get("days_remaining") is None or completed_training[req_id].get("days_remaining", 0) >= 0)
    ])
    
    # Update missing core items
    summary["missing_core_items"].extend(core_missing)
    
    # Determine blocking status
    if core_missing:
        summary["is_blocking"] = True
        summary["blocking_reason"] = f"Missing core training: {', '.join(core_missing[:3])}" + (f" (+{len(core_missing)-3} more)" if len(core_missing) > 3 else "")
        summary["status_band"] = "expired"
        summary["training_status"] = "missing_core"
        summary["training_status_label"] = f"{len(core_missing)} Core Missing"
        summary["training_status_color"] = "red"
        summary["rule_applied"] = "core_training_missing"
        summary["needs_attention"] = True
        
    elif core_expired:
        summary["is_blocking"] = True
        summary["blocking_reason"] = f"Expired core training: {', '.join(core_expired[:3])}" + (f" (+{len(core_expired)-3} more)" if len(core_expired) > 3 else "")
        summary["status_band"] = "expired"
        summary["training_status"] = "core_expired"
        summary["training_status_label"] = f"{len(core_expired)} Core Expired"
        summary["training_status_color"] = "red"
        summary["rule_applied"] = "core_training_expired"
        summary["needs_attention"] = True
        
    elif summary["expiring_soon_count"] > 0:
        # Check if any core training is in urgent band
        core_urgent = [item for item in summary["next_due_items"] if item.get("is_core") and item.get("status") == "urgent"]
        
        if core_urgent:
            summary["status_band"] = "urgent"
            summary["training_status"] = "core_expiring"
            summary["training_status_label"] = f"{len(core_urgent)} Core Due Soon"
            summary["training_status_color"] = "amber"
        else:
            summary["status_band"] = "due_soon"
            summary["training_status"] = "expiring_soon"
            summary["training_status_label"] = f"{summary['expiring_soon_count']} Expiring Soon"
            summary["training_status_color"] = "amber"
        
        summary["is_blocking"] = False
        summary["blocking_reason"] = None
        summary["rule_applied"] = "training_expiring_soon"
        summary["needs_attention"] = True
        
    elif summary["expired_count"] > 0:
        # Non-core training expired - WARNING only
        summary["status_band"] = "due_soon"
        summary["training_status"] = "supplementary_expired"
        summary["training_status_label"] = f"{summary['expired_count']} Supplementary Expired"
        summary["training_status_color"] = "amber"
        summary["is_blocking"] = False
        summary["blocking_reason"] = None
        summary["rule_applied"] = "supplementary_expired_warning"
        summary["needs_attention"] = True
        
    else:
        # All good
        summary["status_band"] = "current"
        summary["training_status"] = "current"
        summary["training_status_label"] = "Up to Date"
        summary["training_status_color"] = "green"
        summary["is_blocking"] = False
        summary["blocking_reason"] = None
        summary["rule_applied"] = "all_current"
        summary["needs_attention"] = False
    
    # Sort next due items by days remaining
    summary["next_due_items"].sort(key=lambda x: x.get("days_remaining", 999))
    
    return summary


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
    middle_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
    role: Optional[str] = None
    onboarding_status: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    manager_name: Optional[str] = None
    driver_status: Optional[bool] = None
    notes: Optional[str] = None
    profile_photo_url: Optional[str] = None
    # Extended profile fields - populated from application form extraction
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    ni_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    marital_status: Optional[str] = None
    # Next of kin / Emergency contact - extended fields
    next_of_kin_name: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_phone: Optional[str] = None
    next_of_kin_email: Optional[str] = None
    next_of_kin_address: Optional[str] = None
    next_of_kin_address_line_1: Optional[str] = None
    next_of_kin_city: Optional[str] = None
    next_of_kin_county: Optional[str] = None
    next_of_kin_postcode: Optional[str] = None
    next_of_kin_country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    # Reference details (informational only - not evidence)
    reference_1_name: Optional[str] = None
    reference_1_company: Optional[str] = None
    reference_1_phone: Optional[str] = None
    reference_1_email: Optional[str] = None
    reference_1_start_date: Optional[str] = None
    reference_1_end_date: Optional[str] = None
    # Reference 1 Integrity Fields (CRITICAL FOR AUDIT)
    reference_1_from_cv: Optional[bool] = None  # True if reference matches CV, False if different
    reference_1_override_reason: Optional[str] = None  # Required if from_cv=False - explains why different
    reference_1_verified: Optional[bool] = False
    reference_1_verified_by: Optional[str] = None
    reference_1_verified_at: Optional[str] = None
    reference_2_name: Optional[str] = None
    reference_2_company: Optional[str] = None
    reference_2_phone: Optional[str] = None
    reference_2_email: Optional[str] = None
    reference_2_start_date: Optional[str] = None
    reference_2_end_date: Optional[str] = None
    # Reference 2 Integrity Fields (CRITICAL FOR AUDIT)
    reference_2_from_cv: Optional[bool] = None  # True if reference matches CV, False if different
    reference_2_override_reason: Optional[str] = None  # Required if from_cv=False - explains why different
    reference_2_verified: Optional[bool] = False
    reference_2_verified_by: Optional[str] = None
    reference_2_verified_at: Optional[str] = None
    # Employment History & CV Gap Analysis (CRITICAL FOR AUDIT)
    employment_history: Optional[List[dict]] = None  # List of employment records with gap analysis
    cv_gaps_detected: Optional[List[dict]] = None  # Detected gaps requiring explanation
    cv_gaps_all_explained: Optional[bool] = None  # True if all gaps have explanations
    # Driving / Vehicle
    has_driving_licence: Optional[bool] = None
    driving_licence_type: Optional[str] = None
    driving_licence_number: Optional[str] = None
    has_own_vehicle: Optional[bool] = None
    vehicle_registration: Optional[str] = None
    vehicle_make_model: Optional[str] = None
    # Bank details (for Staff Personal Info form)
    bank_name: Optional[str] = None
    bank_sort_code: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    # Working declarations from application form
    working_time_opt_out: Optional[bool] = None
    dbs_update_service_consent: Optional[bool] = None
    criminal_offence_declared: Optional[bool] = None
    professional_misconduct_declared: Optional[bool] = None
    health_issue_declared: Optional[bool] = None

class EmployeeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_code: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    title: Optional[str] = None
    email: str
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
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
    # Extended profile fields
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    ni_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    marital_status: Optional[str] = None
    # Next of kin / Emergency contact - extended fields
    next_of_kin_name: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_phone: Optional[str] = None
    next_of_kin_email: Optional[str] = None
    next_of_kin_address: Optional[str] = None
    next_of_kin_address_line_1: Optional[str] = None
    next_of_kin_city: Optional[str] = None
    next_of_kin_county: Optional[str] = None
    next_of_kin_postcode: Optional[str] = None
    next_of_kin_country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    # Reference details (informational only - not evidence)
    reference_1_name: Optional[str] = None
    reference_1_company: Optional[str] = None
    reference_1_phone: Optional[str] = None
    reference_1_email: Optional[str] = None
    reference_1_start_date: Optional[str] = None
    reference_1_end_date: Optional[str] = None
    # Reference 1 Integrity Fields (CRITICAL FOR AUDIT)
    reference_1_from_cv: Optional[bool] = None  # True if reference matches CV, False if different
    reference_1_override_reason: Optional[str] = None  # Required if from_cv=False - explains why different
    reference_1_verified: Optional[bool] = False
    reference_1_verified_by: Optional[str] = None
    reference_1_verified_at: Optional[str] = None
    reference_2_name: Optional[str] = None
    reference_2_company: Optional[str] = None
    reference_2_phone: Optional[str] = None
    reference_2_email: Optional[str] = None
    reference_2_start_date: Optional[str] = None
    reference_2_end_date: Optional[str] = None
    # Reference 2 Integrity Fields (CRITICAL FOR AUDIT)
    reference_2_from_cv: Optional[bool] = None  # True if reference matches CV, False if different
    reference_2_override_reason: Optional[str] = None  # Required if from_cv=False - explains why different
    reference_2_verified: Optional[bool] = False
    reference_2_verified_by: Optional[str] = None
    reference_2_verified_at: Optional[str] = None
    # Employment History & CV Gap Analysis (CRITICAL FOR AUDIT)
    employment_history: Optional[List[dict]] = None  # List of employment records with gap analysis
    cv_gaps_detected: Optional[List[dict]] = None  # Detected gaps requiring explanation
    cv_gaps_all_explained: Optional[bool] = None  # True if all gaps have explanations
    # Driving / Vehicle
    has_driving_licence: Optional[bool] = None
    driving_licence_type: Optional[str] = None
    driving_licence_number: Optional[str] = None
    has_own_vehicle: Optional[bool] = None
    vehicle_registration: Optional[str] = None
    vehicle_make_model: Optional[str] = None
    # Bank details (for Staff Personal Info form)
    bank_name: Optional[str] = None
    bank_sort_code: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    # Working declarations from application form - using Any to handle string or bool
    working_time_opt_out: Optional[Any] = None
    dbs_update_service_consent: Optional[Any] = None
    criminal_offence_declared: Optional[Any] = None
    professional_misconduct_declared: Optional[Any] = None
    health_issue_declared: Optional[Any] = None

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


# ============================================================================
# FORM SUBMISSION MODELS
# ============================================================================
# For structured in-system forms (Health Screening, Induction, Interview, etc.)

# Form types that replace document uploads
FORM_BASED_REQUIREMENTS = {
    # ========================================================================
    # 1. HEALTH SCREENING FORM - Care Sector Standard
    # ========================================================================
    "health_screening": {
        "name": "Health Screening Questionnaire",
        "form_type": "health_screening",
        "auto_fill_fields": ["full_name", "date_of_birth", "job_title", "address", "phone", "email"],
        "sections": [
            {
                "id": "section_a",
                "title": "Section A: Personal Details",
                "description": "Auto-filled where possible from employee profile",
                "fields": [
                    {"id": "full_name", "label": "Full Name", "type": "text", "auto_fill": "full_name"},
                    {"id": "date_of_birth", "label": "Date of Birth", "type": "date", "auto_fill": "date_of_birth"},
                    {"id": "job_title", "label": "Job Title", "type": "text", "auto_fill": "role"},
                    {"id": "address", "label": "Address", "type": "textarea", "auto_fill": "full_address"},
                    {"id": "phone", "label": "Phone Number", "type": "text", "auto_fill": "phone"},
                    {"id": "email", "label": "Email Address", "type": "text", "auto_fill": "email"},
                    {"id": "gp_name", "label": "GP Name", "type": "text"},
                    {"id": "gp_address", "label": "GP Address", "type": "textarea"},
                ]
            },
            {
                "id": "section_b",
                "title": "Section B: Job Exposure",
                "description": "Does your role involve exposure to any of the following?",
                "fields": [
                    {"id": "exposure_manual_handling", "label": "Manual handling / lifting", "type": "checkbox"},
                    {"id": "exposure_blood_fluids", "label": "Human blood / bodily fluids", "type": "checkbox"},
                    {"id": "exposure_food_handling", "label": "Food handling", "type": "checkbox"},
                    {"id": "exposure_night_shifts", "label": "Night shifts", "type": "checkbox"},
                    {"id": "exposure_hazardous_substances", "label": "Hazardous substances", "type": "checkbox"},
                    {"id": "exposure_driving", "label": "Driving (company or personal vehicle)", "type": "checkbox"},
                    {"id": "exposure_dse", "label": "Display Screen Equipment (DSE)", "type": "checkbox"},
                    {"id": "exposure_noisy_environments", "label": "Noisy environments", "type": "checkbox"},
                    {"id": "exposure_working_at_height", "label": "Working at height", "type": "checkbox"},
                    {"id": "exposure_other", "label": "Other exposure (please specify)", "type": "text"},
                ]
            },
            {
                "id": "section_c",
                "title": "Section C: Health History",
                "description": "Do you have or have you previously had any of the following?",
                "fields": [
                    {"id": "has_epilepsy_fainting", "label": "Epilepsy / fainting", "type": "select", "options": ["No", "Yes"]},
                    {"id": "epilepsy_fainting_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_epilepsy_fainting", "conditional_value": "Yes"},
                    {"id": "has_heart_problems", "label": "Heart problems / blood pressure", "type": "select", "options": ["No", "Yes"]},
                    {"id": "heart_problems_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_heart_problems", "conditional_value": "Yes"},
                    {"id": "has_mental_health", "label": "Mental health conditions (anxiety / depression)", "type": "select", "options": ["No", "Yes"]},
                    {"id": "mental_health_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_mental_health", "conditional_value": "Yes"},
                    {"id": "has_diabetes", "label": "Diabetes", "type": "select", "options": ["No", "Yes"]},
                    {"id": "diabetes_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_diabetes", "conditional_value": "Yes"},
                    {"id": "has_asthma_chest", "label": "Asthma / chest issues", "type": "select", "options": ["No", "Yes"]},
                    {"id": "asthma_chest_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_asthma_chest", "conditional_value": "Yes"},
                    {"id": "has_back_joint", "label": "Back / joint problems", "type": "select", "options": ["No", "Yes"]},
                    {"id": "back_joint_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_back_joint", "conditional_value": "Yes"},
                    {"id": "has_injury_operations", "label": "Serious injury or operations", "type": "select", "options": ["No", "Yes"]},
                    {"id": "injury_operations_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_injury_operations", "conditional_value": "Yes"},
                    {"id": "has_skin_conditions", "label": "Skin conditions", "type": "select", "options": ["No", "Yes"]},
                    {"id": "skin_conditions_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_skin_conditions", "conditional_value": "Yes"},
                    {"id": "has_hearing_problems", "label": "Hearing problems", "type": "select", "options": ["No", "Yes"]},
                    {"id": "hearing_problems_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_hearing_problems", "conditional_value": "Yes"},
                    {"id": "has_vision_problems", "label": "Vision problems", "type": "select", "options": ["No", "Yes"]},
                    {"id": "vision_problems_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_vision_problems", "conditional_value": "Yes"},
                    {"id": "has_other_conditions", "label": "Any other medical conditions?", "type": "select", "options": ["No", "Yes"]},
                    {"id": "other_conditions_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_other_conditions", "conditional_value": "Yes"},
                    {"id": "taking_medication", "label": "Are you currently taking any medication?", "type": "select", "options": ["No", "Yes"]},
                    {"id": "medication_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "taking_medication", "conditional_value": "Yes"},
                    {"id": "has_allergies", "label": "Do you have any allergies?", "type": "select", "options": ["No", "Yes"]},
                    {"id": "allergies_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_allergies", "conditional_value": "Yes"},
                    {"id": "has_implanted_device", "label": "Do you have any implanted medical device (pacemaker, etc.)?", "type": "select", "options": ["No", "Yes"]},
                    {"id": "days_absent_3_years", "label": "Days absent due to illness in last 3 years", "type": "number"},
                ]
            },
            {
                "id": "section_d",
                "title": "Section D: Functional Ability",
                "description": "Do you have any difficulty with the following activities?",
                "fields": [
                    {"id": "difficulty_standing", "label": "Standing for prolonged periods", "type": "select", "options": ["No difficulty", "Some difficulty", "Unable"]},
                    {"id": "standing_details", "label": "Details if applicable", "type": "text"},
                    {"id": "difficulty_walking", "label": "Walking", "type": "select", "options": ["No difficulty", "Some difficulty", "Unable"]},
                    {"id": "walking_details", "label": "Details if applicable", "type": "text"},
                    {"id": "difficulty_climbing", "label": "Climbing stairs", "type": "select", "options": ["No difficulty", "Some difficulty", "Unable"]},
                    {"id": "climbing_details", "label": "Details if applicable", "type": "text"},
                    {"id": "difficulty_lifting", "label": "Lifting and carrying", "type": "select", "options": ["No difficulty", "Some difficulty", "Unable"]},
                    {"id": "lifting_details", "label": "Details if applicable", "type": "text"},
                    {"id": "difficulty_using_hands", "label": "Using hands / manual dexterity", "type": "select", "options": ["No difficulty", "Some difficulty", "Unable"]},
                    {"id": "hands_details", "label": "Details if applicable", "type": "text"},
                    {"id": "difficulty_driving", "label": "Driving", "type": "select", "options": ["No difficulty", "Some difficulty", "Unable", "Do not drive"]},
                    {"id": "driving_details", "label": "Details if applicable", "type": "text"},
                    {"id": "difficulty_working_height", "label": "Working at height", "type": "select", "options": ["No difficulty", "Some difficulty", "Unable"]},
                    {"id": "height_details", "label": "Details if applicable", "type": "text"},
                ]
            },
            {
                "id": "section_e",
                "title": "Section E: Employee Declaration",
                "description": "",
                "fields": [
                    {"id": "declaration_accurate", "label": "I confirm that the information provided above is accurate and complete to the best of my knowledge", "type": "checkbox", "required": True},
                    {"id": "employee_signature", "label": "Employee Signature (type full name)", "type": "text", "required": True},
                    {"id": "employee_sign_date", "label": "Date Signed", "type": "date", "required": True},
                ]
            },
            {
                "id": "section_f",
                "title": "Section F: Employer Use Only",
                "description": "To be completed by recruiting manager/HR",
                "admin_only": True,
                "fields": [
                    {"id": "employer_notes", "label": "Notes / Comments", "type": "textarea"},
                    {"id": "adjustments_required", "label": "Adjustments Required", "type": "textarea"},
                    {"id": "fit_for_role", "label": "Fitness for Role Assessment", "type": "select", "options": ["Fit", "Fit with adjustments", "Not fit - refer to Occupational Health"], "required": True},
                    {"id": "assessor_name", "label": "Assessor Name", "type": "text"},
                    {"id": "assessment_date", "label": "Assessment Date", "type": "date"},
                ]
            }
        ],
        # Flattened fields for backward compatibility
        "fields": []
    },
    
    # ========================================================================
    # 2. STAFF HEALTH QUESTIONNAIRE - Based on Osabea Official Template
    # ========================================================================
    "staff_health_questionnaire": {
        "name": "Staff Health Questionnaire",
        "form_type": "staff_health_questionnaire",
        "auto_fill_fields": ["full_name", "date_of_birth", "phone"],
        "branding": {
            "show_logo": True,
            "header_color": "#2E7D32",  # Green header like the official document
            "company_name": "Osabea Healthcare Solutions Ltd"
        },
        "sections": [
            {
                "id": "personal_info",
                "title": "Personal Information",
                "fields": [
                    {"id": "full_name", "label": "Full Name", "type": "text", "required": True, "auto_fill": "full_name"},
                    {"id": "date_of_birth", "label": "Date of Birth", "type": "date", "required": True, "auto_fill": "date_of_birth"},
                    {"id": "contact_number", "label": "Contact Number", "type": "text", "required": True, "auto_fill": "contact_number"},
                    {"id": "gp_name", "label": "GP Name", "type": "text"},
                    {"id": "gp_address", "label": "GP Address", "type": "textarea"},
                    {"id": "gp_contact_number", "label": "GP Contact Number", "type": "text"},
                    {"id": "nhs_number", "label": "NHS Number", "type": "text"},
                    {"id": "flu_vaccination_date", "label": "Date of last Flu vaccination", "type": "date", "auto_fill": "flu_vaccination_date"},
                    {"id": "covid_vaccination_dates", "label": "Dates of Covid-19 vaccinations", "type": "text", "placeholder": "e.g., 01/03/2021, 15/06/2021, 20/12/2021"},
                ]
            },
            {
                "id": "health_questions",
                "title": "Health Questions",
                "description": "Please answer the following questions honestly. If you answer 'Yes' to any question, please provide details in the space provided.",
                "fields": [
                    {"id": "significant_illness", "label": "Do you have, or have you ever had any significant illness? (i.e. Asthma, Diabetes, Heart Disease, Other)", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "significant_illness_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "significant_illness", "conditional_value": "Yes"},
                    
                    {"id": "ongoing_gp_treatment", "label": "Are you regularly seeing your GP for any ongoing health condition?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "ongoing_gp_treatment_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "ongoing_gp_treatment", "conditional_value": "Yes"},
                    
                    {"id": "specialist_waiting_list", "label": "Are you on a waiting list to see a specialist, or have you seen one in the past 5 years?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "specialist_waiting_list_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "specialist_waiting_list", "conditional_value": "Yes"},
                    
                    {"id": "hospital_admissions_last_5_years", "label": "Have you had any hospital admissions in the last 5 years?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "hospital_admissions_last_5_years_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "hospital_admissions_last_5_years", "conditional_value": "Yes"},
                    
                    {"id": "work_related_condition", "label": "Have you ever had any illness/impairment/disability which may have been caused by, or made worse by your work?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "work_related_condition_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "work_related_condition", "conditional_value": "Yes"},
                    
                    {"id": "medical_problems_affecting_work", "label": "Are you aware of any other medical problems you have that may cause you difficulty in performing your normal working role or attending work?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "medical_problems_affecting_work_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "medical_problems_affecting_work", "conditional_value": "Yes"},
                    
                    {"id": "needs_adjustments", "label": "Do you think you may need any adjustments or assistance in order for you to undertake your normal working duties?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "needs_adjustments_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "needs_adjustments", "conditional_value": "Yes"},
                    
                    {"id": "taking_medication", "label": "Are you regularly taking any prescription medication?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "taking_medication_details", "label": "If yes, please give details", "type": "textarea", "conditional_on": "taking_medication", "conditional_value": "Yes"},
                    
                    {"id": "other_health_concerns", "label": "Are there any other matters concerning your health not covered by the previous questions, which we should know about?", "type": "textarea"},
                ]
            },
            {
                "id": "declaration",
                "title": "Declaration",
                "description": "Please be advised, Osabea Healthcare Solutions Ltd will ensure the confidentiality of ALL information provided in this document is maintained and ONLY accessed in an emergency situation. Where required, any reasonable adjustments and/or risk assessments will be implemented and regularly reviewed on an individual basis to ensure you are safeguarded at all times.",
                "fields": [
                    {"id": "declaration_confirmed", "label": "To the best of my knowledge and belief the information given above is true and correct", "type": "checkbox", "required": True},
                    {"id": "signature_name", "label": "Signature (type full name)", "type": "text", "required": True},
                    {"id": "signature_date", "label": "Date", "type": "date", "required": True, "auto_fill": "today"},
                ]
            }
        ],
        "fields": []
    },
    
    # ========================================================================
    # 3. RECRUITMENT CHECKLIST - Simplified Verification Form
    # ========================================================================
    "recruitment_checklist": {
        "name": "Recruitment Compliance Checklist",
        "form_type": "recruitment_checklist",
        "auto_fill_fields": ["employee_name", "position"],
        "sections": [
            {
                "id": "identity_legal",
                "title": "Identity & Legal",
                "fields": [
                    {"id": "identity_verified", "label": "Identity verified?", "type": "select", "options": ["Yes", "No", "Pending"], "required": True},
                    {"id": "photo_available", "label": "Photo available?", "type": "select", "options": ["Yes", "No"], "required": True},
                    {"id": "identity_notes", "label": "Details / Notes", "type": "textarea"},
                ]
            },
            {
                "id": "dbs_section",
                "title": "DBS Check",
                "fields": [
                    {"id": "dbs_verified", "label": "DBS seen or Update Service checked?", "type": "select", "options": ["Yes", "No", "Pending"], "required": True},
                    {"id": "dbs_notes", "label": "Details (certificate number, date, level)", "type": "textarea"},
                ]
            },
            {
                "id": "employment_history",
                "title": "Employment History",
                "fields": [
                    {"id": "employment_verified", "label": "Previous employment verified?", "type": "select", "options": ["Yes", "No", "N/A"], "required": True},
                    {"id": "conduct_satisfactory", "label": "Conduct satisfactory?", "type": "select", "options": ["Yes", "No", "N/A"], "required": True},
                    {"id": "reason_leaving_verified", "label": "Reason for leaving verified where required?", "type": "select", "options": ["Yes", "No", "N/A"], "required": True},
                    {"id": "employment_notes", "label": "Notes", "type": "textarea"},
                ]
            },
            {
                "id": "qualifications",
                "title": "Qualifications",
                "fields": [
                    {"id": "qualifications_verified", "label": "Qualifications verified?", "type": "select", "options": ["Yes", "No", "N/A"], "required": True},
                    {"id": "qualifications_notes", "label": "Details", "type": "textarea"},
                ]
            },
            {
                "id": "final_section",
                "title": "Final Sign-off",
                "fields": [
                    {"id": "completed_by", "label": "Completed By (Name)", "type": "text", "required": True},
                    {"id": "signature", "label": "Signature (type full name)", "type": "text", "required": True},
                    {"id": "completion_date", "label": "Date", "type": "date", "required": True},
                ]
            }
        ],
        "fields": []
    },
    
    # ========================================================================
    # 3. STAFF PERSONAL INFORMATION FORM - Profile Data (NEW)
    # ========================================================================
    "staff_personal_info": {
        "name": "Staff Personal Information",
        "form_type": "staff_personal_info",
        "auto_fill_fields": ["title", "first_name", "middle_name", "last_name", "date_of_birth", "address_line_1", "address_line_2", "city", "county", "postcode", "country", "phone", "email", "ni_number", "emergency_contact_name", "emergency_contact_relationship", "emergency_contact_phone", "emergency_contact_email", "emergency_contact_address", "has_driving_licence", "driving_licence_number", "has_own_vehicle", "vehicle_registration"],
        "updates_profile": True,  # This form can update employee profile fields
        "sections": [
            {
                "id": "basic_details",
                "title": "Basic Details",
                "fields": [
                    {"id": "title", "label": "Title", "type": "select", "options": ["Mr", "Mrs", "Ms", "Miss", "Dr", "Other"], "auto_fill": "title"},
                    {"id": "first_name", "label": "First Name", "type": "text", "required": True, "auto_fill": "first_name"},
                    {"id": "middle_name", "label": "Middle Name(s)", "type": "text", "auto_fill": "middle_name"},
                    {"id": "last_name", "label": "Last Name", "type": "text", "required": True, "auto_fill": "last_name"},
                    {"id": "date_of_birth", "label": "Date of Birth", "type": "date", "auto_fill": "date_of_birth"},
                    {"id": "marital_status", "label": "Marital Status", "type": "select", "options": ["Single", "Married", "Civil Partnership", "Divorced", "Widowed", "Prefer not to say"]},
                ]
            },
            {
                "id": "contact_details",
                "title": "Contact Details",
                "fields": [
                    {"id": "address_line_1", "label": "Address Line 1", "type": "text", "auto_fill": "address_line_1"},
                    {"id": "address_line_2", "label": "Address Line 2", "type": "text", "auto_fill": "address_line_2"},
                    {"id": "city", "label": "City", "type": "text", "auto_fill": "city"},
                    {"id": "county", "label": "County", "type": "text", "auto_fill": "county"},
                    {"id": "postcode", "label": "Postcode", "type": "text", "auto_fill": "postcode"},
                    {"id": "country", "label": "Country", "type": "text", "auto_fill": "country"},
                    {"id": "phone_primary", "label": "Primary Phone", "type": "text", "auto_fill": "phone"},
                    {"id": "phone_secondary", "label": "Secondary Phone", "type": "text", "auto_fill": "phone_secondary"},
                    {"id": "email", "label": "Email Address", "type": "text", "auto_fill": "email"},
                ]
            },
            {
                "id": "national_insurance",
                "title": "National Insurance",
                "fields": [
                    {"id": "ni_number", "label": "National Insurance Number", "type": "text", "auto_fill": "ni_number", "placeholder": "e.g., AB123456C"},
                ]
            },
            {
                "id": "emergency_contact",
                "title": "Emergency Contact / Next of Kin",
                "fields": [
                    {"id": "emergency_name", "label": "Contact Name", "type": "text", "auto_fill": "next_of_kin_name"},
                    {"id": "emergency_relationship", "label": "Relationship", "type": "text", "auto_fill": "next_of_kin_relationship"},
                    {"id": "emergency_phone", "label": "Phone Number", "type": "text", "auto_fill": "next_of_kin_phone"},
                    {"id": "emergency_email", "label": "Email Address", "type": "text"},
                    {"id": "emergency_address", "label": "Address", "type": "textarea", "auto_fill": "next_of_kin_address"},
                ]
            },
            {
                "id": "bank_details",
                "title": "Bank Details",
                "description": "For payroll purposes only",
                "fields": [
                    {"id": "bank_name", "label": "Bank Name", "type": "text"},
                    {"id": "sort_code", "label": "Sort Code", "type": "text", "placeholder": "00-00-00"},
                    {"id": "account_number", "label": "Account Number", "type": "text"},
                    {"id": "account_name", "label": "Account Holder Name", "type": "text"},
                ]
            },
            {
                "id": "driving_vehicle",
                "title": "Driving & Vehicle Information",
                "fields": [
                    {"id": "has_driving_licence", "label": "Do you have a driving licence?", "type": "select", "options": ["Yes", "No"], "auto_fill": "has_driving_licence"},
                    {"id": "licence_number", "label": "Driving Licence Number", "type": "text", "conditional_on": "has_driving_licence", "conditional_value": "Yes"},
                    {"id": "licence_categories", "label": "Licence Categories (e.g., B, BE)", "type": "text", "conditional_on": "has_driving_licence", "conditional_value": "Yes"},
                    {"id": "has_own_vehicle", "label": "Do you have access to your own vehicle?", "type": "select", "options": ["Yes", "No"], "auto_fill": "has_own_vehicle"},
                    {"id": "vehicle_make_model", "label": "Vehicle Make/Model", "type": "text", "conditional_on": "has_own_vehicle", "conditional_value": "Yes"},
                    {"id": "vehicle_registration", "label": "Registration Number", "type": "text", "conditional_on": "has_own_vehicle", "conditional_value": "Yes", "auto_fill": "vehicle_registration"},
                ]
            },
            {
                "id": "declaration",
                "title": "Declaration",
                "fields": [
                    {"id": "info_accurate", "label": "I confirm the information provided is accurate and I will notify the company of any changes", "type": "checkbox", "required": True},
                    {"id": "signature", "label": "Signature (type full name)", "type": "text", "required": True},
                    {"id": "sign_date", "label": "Date", "type": "date", "required": True},
                ]
            }
        ],
        "fields": []
    },
    
    # ========================================================================
    # 4. EQUAL OPPORTUNITIES FORM - Optional, No Compliance Impact
    # ========================================================================
    "equal_opportunities": {
        "name": "Equal Opportunities Monitoring",
        "form_type": "equal_opportunities",
        "is_optional": True,  # This form is optional and does not affect compliance
        "description": "This information is collected for equality monitoring purposes only and will be kept strictly confidential. Completion is entirely voluntary and will have no impact on your application or employment.",
        "sections": [
            {
                "id": "monitoring_info",
                "title": "Equality Monitoring Information",
                "fields": [
                    {"id": "intro_note", "label": "All fields below are optional. You may select 'Prefer not to say' for any question.", "type": "info"},
                    {"id": "ethnicity", "label": "Ethnicity", "type": "select", "options": [
                        "Asian or Asian British - Bangladeshi",
                        "Asian or Asian British - Chinese", 
                        "Asian or Asian British - Indian",
                        "Asian or Asian British - Pakistani",
                        "Asian or Asian British - Other Asian background",
                        "Black or Black British - African",
                        "Black or Black British - Caribbean",
                        "Black or Black British - Other Black background",
                        "Mixed - White and Asian",
                        "Mixed - White and Black African",
                        "Mixed - White and Black Caribbean",
                        "Mixed - Other mixed background",
                        "White - British",
                        "White - Irish",
                        "White - Gypsy or Irish Traveller",
                        "White - Other White background",
                        "Arab",
                        "Other ethnic group",
                        "Prefer not to say"
                    ]},
                    {"id": "gender", "label": "Gender", "type": "select", "options": [
                        "Female",
                        "Male",
                        "Non-binary",
                        "Other",
                        "Prefer not to say"
                    ]},
                    {"id": "sexual_orientation", "label": "Sexual Orientation", "type": "select", "options": [
                        "Heterosexual/Straight",
                        "Gay",
                        "Lesbian",
                        "Bisexual",
                        "Other",
                        "Prefer not to say"
                    ]},
                    {"id": "religion", "label": "Religion or Belief", "type": "select", "options": [
                        "Buddhist",
                        "Christian",
                        "Hindu",
                        "Jewish",
                        "Muslim",
                        "Sikh",
                        "No religion",
                        "Other",
                        "Prefer not to say"
                    ]},
                    {"id": "disability", "label": "Do you consider yourself to have a disability?", "type": "select", "options": [
                        "Yes",
                        "No",
                        "Prefer not to say"
                    ]},
                    {"id": "disability_details", "label": "If you selected 'Yes', please provide details if you wish (optional)", "type": "textarea", "conditional_on": "disability", "conditional_value": "Yes"},
                    {"id": "caring_responsibilities", "label": "Do you have caring responsibilities?", "type": "select", "options": [
                        "Yes",
                        "No",
                        "Prefer not to say"
                    ]},
                    {"id": "caring_type", "label": "If yes, please select all that apply", "type": "multi_select", "options": [
                        "Children under 18",
                        "Disabled person",
                        "Elderly person"
                    ], "conditional_on": "caring_responsibilities", "conditional_value": "Yes"},
                ]
            },
            {
                "id": "declaration",
                "title": "Declaration",
                "fields": [
                    {"id": "submission_consent", "label": "I understand this form is optional and my answers will be used solely for equality monitoring purposes", "type": "checkbox"},
                ]
            }
        ],
        "fields": []
    },
    
    # ========================================================================
    # 5. HMRC STARTER CHECKLIST - Conditional on P45 Absence
    # ========================================================================
    "hmrc_starter_checklist": {
        "name": "HMRC Starter Checklist",
        "form_type": "hmrc_starter_checklist",
        "is_conditional": True,  # Only required if no P45
        "condition_field": "p45",  # If P45 exists, this is not required
        "auto_fill_fields": ["full_name", "address", "postcode", "country", "ni_number", "date_of_birth"],
        "description": "Complete this form if the employee does not have a P45 from a previous employer. This is used for payroll/tax setup.",
        "sections": [
            {
                "id": "employee_details",
                "title": "Employee Details",
                "description": "Pre-filled from employee profile where available",
                "fields": [
                    {"id": "full_name", "label": "Full Name (as shown on official documents)", "type": "text", "required": True, "auto_fill": "full_name"},
                    {"id": "address", "label": "Address", "type": "textarea", "required": True, "auto_fill": "full_address"},
                    {"id": "postcode", "label": "Postcode", "type": "text", "required": True, "auto_fill": "postcode"},
                    {"id": "country", "label": "Country", "type": "text", "auto_fill": "country"},
                    {"id": "ni_number", "label": "National Insurance Number", "type": "text", "auto_fill": "ni_number", "placeholder": "e.g., AB123456C"},
                    {"id": "date_of_birth", "label": "Date of Birth", "type": "date", "required": True, "auto_fill": "date_of_birth"},
                    {"id": "employment_start_date", "label": "Employment Start Date", "type": "date", "auto_fill": "start_date"},
                ]
            },
            {
                "id": "tax_statement",
                "title": "Employee Tax Statement",
                "description": "Select the statement that applies to you",
                "fields": [
                    {"id": "employee_statement", "label": "Select one statement", "type": "select", "required": True, "options": [
                        "A - This is my first job since 6 April and I have not been receiving taxable Jobseeker's Allowance, Employment and Support Allowance, taxable Incapacity Benefit, State or Occupational Pension",
                        "B - This is now my only job, but since 6 April I have had another job, or received taxable Jobseeker's Allowance, Employment and Support Allowance or taxable Incapacity Benefit. I do not receive a State or Occupational Pension",
                        "C - I have another job or receive a State or Occupational Pension"
                    ]},
                ]
            },
            {
                "id": "student_loans",
                "title": "Student Loan",
                "fields": [
                    {"id": "has_student_loan", "label": "Do you have a student loan?", "type": "select", "options": ["No", "Yes"], "required": True},
                    {"id": "student_loan_plan", "label": "Which student loan plan type?", "type": "select", "options": [
                        "Plan 1 (started before 1 September 2012)",
                        "Plan 2 (started on or after 1 September 2012, England/Wales)",
                        "Plan 4 (Scottish students from April 2021)",
                        "Plan 5 (started on or after 1 August 2023, England)",
                        "Postgraduate Loan"
                    ], "conditional_on": "has_student_loan", "conditional_value": "Yes"},
                    {"id": "has_postgrad_loan", "label": "Do you have a Postgraduate Loan (separate from student loan)?", "type": "select", "options": ["No", "Yes"]},
                ]
            },
            {
                "id": "additional_info",
                "title": "Additional Information",
                "fields": [
                    {"id": "has_additional_income", "label": "Do you have any other income or employment?", "type": "select", "options": ["No", "Yes"]},
                    {"id": "additional_income_details", "label": "If yes, please provide details", "type": "textarea", "conditional_on": "has_additional_income", "conditional_value": "Yes"},
                ]
            },
            {
                "id": "declaration",
                "title": "Declaration",
                "fields": [
                    {"id": "declaration_accurate", "label": "I confirm the information provided is correct to the best of my knowledge", "type": "checkbox", "required": True},
                    {"id": "signature", "label": "Signature (type full name)", "type": "text", "required": True},
                    {"id": "sign_date", "label": "Date", "type": "date", "required": True},
                ]
            }
        ],
        "fields": []
    },
    
    # ========================================================================
    # 6. INDUCTION & COMPETENCY ASSESSMENT
    # ========================================================================
    "induction": {
        "name": "Induction & Competency Assessment",
        "form_type": "induction",
        "auto_fill_fields": ["employee_name", "job_title", "start_date"],
        "sections": [
            {
                "id": "induction_details",
                "title": "Induction Details",
                "fields": [
                    {"id": "employee_name", "label": "Employee Name", "type": "text", "auto_fill": "full_name"},
                    {"id": "job_title", "label": "Job Title", "type": "text", "auto_fill": "role"},
                    {"id": "induction_date", "label": "Induction Date", "type": "date", "required": True},
                    {"id": "inducted_by", "label": "Inducted By", "type": "text", "required": True},
                    {"id": "location", "label": "Location/Site", "type": "text"},
                ]
            },
            {
                "id": "policies_procedures",
                "title": "Policies & Procedures",
                "fields": [
                    {"id": "policies_reviewed", "label": "Key policies reviewed and understood?", "type": "checkbox"},
                    {"id": "employee_handbook", "label": "Employee handbook issued and explained?", "type": "checkbox"},
                    {"id": "reporting_structure", "label": "Reporting structure explained?", "type": "checkbox"},
                    {"id": "absence_procedures", "label": "Absence reporting procedures explained?", "type": "checkbox"},
                ]
            },
            {
                "id": "health_safety",
                "title": "Health & Safety",
                "fields": [
                    {"id": "fire_safety_briefed", "label": "Fire safety and evacuation procedures explained?", "type": "checkbox"},
                    {"id": "first_aid_location", "label": "First aid facilities location shown?", "type": "checkbox"},
                    {"id": "manual_handling_demo", "label": "Manual handling principles demonstrated?", "type": "checkbox"},
                    {"id": "infection_control_briefed", "label": "Infection control procedures explained?", "type": "checkbox"},
                    {"id": "ppe_issued", "label": "PPE issued and explained where required?", "type": "checkbox"},
                    {"id": "coshh_awareness", "label": "COSHH awareness (if applicable)?", "type": "checkbox"},
                ]
            },
            {
                "id": "safeguarding",
                "title": "Safeguarding & Care",
                "fields": [
                    {"id": "safeguarding_awareness", "label": "Safeguarding awareness and reporting explained?", "type": "checkbox"},
                    {"id": "dignity_care", "label": "Dignity in care principles discussed?", "type": "checkbox"},
                    {"id": "medication_admin", "label": "Medication administration procedures (if applicable)?", "type": "checkbox"},
                    {"id": "emergency_procedures", "label": "Emergency procedures and contacts provided?", "type": "checkbox"},
                ]
            },
            {
                "id": "competency",
                "title": "Competency Assessment",
                "fields": [
                    {"id": "equipment_training", "label": "Equipment training completed where required?", "type": "checkbox"},
                    {"id": "competency_assessment_passed", "label": "Initial competency assessment", "type": "select", "options": ["Passed", "Needs follow-up", "Not assessed yet"], "required": True},
                    {"id": "follow_up_required", "label": "Follow-up actions required", "type": "textarea"},
                ]
            },
            {
                "id": "sign_off",
                "title": "Sign-off",
                "fields": [
                    {"id": "employee_confirmation", "label": "Employee confirms completion of induction", "type": "checkbox", "required": True},
                    {"id": "employee_signature", "label": "Employee Signature", "type": "text", "required": True},
                    {"id": "inductor_signature", "label": "Inductor Signature", "type": "text", "required": True},
                    {"id": "sign_date", "label": "Date", "type": "date", "required": True},
                    {"id": "assessor_notes", "label": "Assessor Notes", "type": "textarea"},
                ]
            }
        ],
        "fields": []
    },
    
    # ========================================================================
    # 7. INTERVIEW RECORD
    # ========================================================================
    "interview_record": {
        "name": "Interview Record",
        "form_type": "interview_record",
        "auto_fill_fields": ["candidate_name", "position_applied"],
        "sections": [
            {
                "id": "interview_info",
                "title": "Interview Information",
                "fields": [
                    {"id": "candidate_name", "label": "Candidate Name", "type": "text", "auto_fill": "full_name", "required": True},
                    {"id": "position_applied", "label": "Position Applied For", "type": "text", "auto_fill": "role", "required": True},
                    {"id": "interview_date", "label": "Interview Date", "type": "date", "required": True},
                    {"id": "interview_type", "label": "Interview Type", "type": "select", "options": ["In-person", "Video call", "Phone"], "required": True},
                    {"id": "interviewer_name", "label": "Interviewer Name(s)", "type": "text", "required": True},
                ]
            },
            {
                "id": "assessment",
                "title": "Assessment",
                "fields": [
                    {"id": "experience_summary", "label": "Relevant Experience Summary", "type": "textarea"},
                    {"id": "strengths", "label": "Identified Strengths", "type": "textarea"},
                    {"id": "areas_for_development", "label": "Areas for Development", "type": "textarea"},
                    {"id": "right_to_work_verified", "label": "Right to Work discussed/verified at interview?", "type": "checkbox"},
                    {"id": "references_discussed", "label": "References discussed?", "type": "checkbox"},
                    {"id": "availability_confirmed", "label": "Availability confirmed?", "type": "checkbox"},
                ]
            },
            {
                "id": "decision",
                "title": "Interview Outcome",
                "fields": [
                    {"id": "overall_impression", "label": "Overall Impression", "type": "select", "options": ["Strongly recommend", "Recommend", "Consider", "Do not recommend"], "required": True},
                    {"id": "decision", "label": "Interview Decision", "type": "select", "options": ["Offer", "Second interview", "Hold", "Reject"], "required": True},
                    {"id": "interviewer_notes", "label": "Interviewer Notes", "type": "textarea"},
                    {"id": "interviewer_signature", "label": "Interviewer Signature", "type": "text", "required": True},
                    {"id": "interview_sign_date", "label": "Date", "type": "date", "required": True},
                ]
            }
        ],
        "fields": []
    }
}


class FormSubmissionCreate(BaseModel):
    employee_id: str
    requirement_id: str  # e.g., "health_screening", "induction"
    form_type: str
    data: dict  # JSON form data
    

class FormSubmissionUpdate(BaseModel):
    data: Optional[dict] = None
    verified: Optional[bool] = None
    verified_by: Optional[str] = None
    notes: Optional[str] = None


class FormSubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_id: str
    requirement_id: str
    form_type: str
    data: dict
    submitted_at: str
    submitted_by: Optional[str] = None
    submitted_by_name: Optional[str] = None
    verified: bool = False
    verified_by: Optional[str] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[str] = None
    status: str = "submitted"  # submitted, verified, superseded
    version: int = 1
    notes: Optional[str] = None


# ============================================================================
# PDF TEMPLATE MODELS - Template-Backed Forms Architecture
# ============================================================================

class PDFTemplateCreate(BaseModel):
    """Create a new PDF template for a form type"""
    form_type: str  # e.g., 'staff_health_questionnaire'
    name: str  # e.g., 'Osabea Staff Health Questionnaire v1.0'
    version: str = "1.0"
    mapping_config: Optional[Dict[str, Any]] = None  # Field mapping configuration

class PDFTemplateResponse(BaseModel):
    """Response model for PDF templates"""
    model_config = ConfigDict(extra="ignore")
    id: str
    form_type: str
    name: str
    version: str
    file_url: Optional[str] = None
    storage_path: Optional[str] = None
    is_active: bool = False
    mapping_config: Optional[Dict[str, Any]] = None
    created_by: str
    created_by_name: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class PDFExportResponse(BaseModel):
    """Response model for generated PDF exports"""
    model_config = ConfigDict(extra="ignore")
    id: str
    submission_id: str
    template_id: Optional[str] = None
    employee_id: str
    employee_name: str
    form_type: str
    file_url: str
    storage_path: str
    created_at: str
    created_by: str


# ============================================================================
# STAFF HEALTH QUESTIONNAIRE - PDF Field Mapping Configuration
# ============================================================================

STAFF_HEALTH_PDF_MAPPING = {
    "form_type": "staff_health_questionnaire",
    "template_name": "Staff Health Questionnaire",
    "company_branding": {
        "name": "Osabea Healthcare Solutions Ltd",
        "logo_text": "O",
        "header_color": "#2E7D32",
        "confidentiality_notice": "CONFIDENTIAL - For Occupational Health Use Only"
    },
    "sections": [
        {
            "id": "personal_info",
            "title": "Personal Information",
            "fields": [
                {"field_id": "full_name", "label": "Full Name", "type": "text"},
                {"field_id": "date_of_birth", "label": "Date of Birth", "type": "date"},
                {"field_id": "contact_number", "label": "Contact Number", "type": "text"},
                {"field_id": "gp_name", "label": "GP Name", "type": "text"},
                {"field_id": "gp_address", "label": "GP Address", "type": "text"},
                {"field_id": "gp_contact_number", "label": "GP Contact Number", "type": "text"},
                {"field_id": "nhs_number", "label": "NHS Number", "type": "text"},
                {"field_id": "flu_vaccination_date", "label": "Date of last Flu vaccination", "type": "date"},
                {"field_id": "covid_vaccination_dates", "label": "Dates of Covid-19 vaccinations", "type": "text"}
            ]
        },
        {
            "id": "health_questions",
            "title": "Health Questions",
            "fields": [
                {"field_id": "significant_illness", "label": "Significant illness (Asthma, Diabetes, Heart Disease, Other)", "type": "yes_no", "details_field": "significant_illness_details"},
                {"field_id": "ongoing_gp_treatment", "label": "Regularly seeing GP for ongoing health condition", "type": "yes_no", "details_field": "ongoing_gp_treatment_details"},
                {"field_id": "specialist_waiting_list", "label": "On waiting list to see specialist / seen one in past 5 years", "type": "yes_no", "details_field": "specialist_waiting_list_details"},
                {"field_id": "hospital_admissions_last_5_years", "label": "Hospital admissions in last 5 years", "type": "yes_no", "details_field": "hospital_admissions_last_5_years_details"},
                {"field_id": "work_related_condition", "label": "Illness/impairment caused or worsened by work", "type": "yes_no", "details_field": "work_related_condition_details"},
                {"field_id": "medical_problems_affecting_work", "label": "Medical problems affecting normal working role", "type": "yes_no", "details_field": "medical_problems_affecting_work_details"},
                {"field_id": "needs_adjustments", "label": "Need adjustments/assistance for normal duties", "type": "yes_no", "details_field": "needs_adjustments_details"},
                {"field_id": "taking_medication", "label": "Regularly taking prescription medication", "type": "yes_no", "details_field": "taking_medication_details"},
                {"field_id": "other_health_concerns", "label": "Other health matters not covered above", "type": "text"}
            ]
        },
        {
            "id": "declaration",
            "title": "Declaration",
            "fields": [
                {"field_id": "declaration_confirmed", "label": "Declaration confirmed", "type": "checkbox"},
                {"field_id": "signature_name", "label": "Signature", "type": "text"},
                {"field_id": "signature_date", "label": "Date", "type": "date"}
            ]
        }
    ]
}

# Global mapping registry for all form types
PDF_FIELD_MAPPINGS = {
    "staff_health_questionnaire": STAFF_HEALTH_PDF_MAPPING
}


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

# Policy Assignment Models - Audit-Safe Acknowledgement System
class PolicyAssignmentCreate(BaseModel):
    policy_id: str
    employee_ids: List[str]
    message: Optional[str] = None

class PolicyAssignmentResponse(BaseModel):
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

# Organisation Settings Models
class OrgSettingsUpdate(BaseModel):
    service_type: Optional[str] = None  # adults_only, children_only, mixed
    organisation_name: Optional[str] = None

class OrgSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    service_type: str = "adults_only"  # Default to adults_only
    organisation_name: str = "Osabea Healthcare Solutions"
    created_at: str
    updated_at: str

# Training Record Models
class TrainingRecordCreate(BaseModel):
    employee_id: str
    training_name: str
    requirement_id: Optional[str] = None
    mandatory: bool = True
    completion_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str = "not_started"  # not_started, in_progress, completed, expiring, expired

class TrainingRecordResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    employee_id: str
    training_name: str
    requirement_id: Optional[str] = None
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
    record_status: str = "active"  # active, superseded, deleted (distinct from completion status)
    status: str  # completion status: not_started, in_progress, completed, expiring, expired
    evidence_files: Optional[List[dict]] = []
    created_at: str
    updated_at: Optional[str] = None
    # COMPUTED fields (from compute_training_record_status) - SINGLE SOURCE OF TRUTH
    computed_status: Optional[str] = None  # not_started, expired, needs_renewal, completed
    renewal_status: Optional[str] = None  # expired, expiring_soon, valid, no_expiry
    days_until_expiry: Optional[int] = None  # Negative if expired
    status_label: Optional[str] = None  # Human readable label
    status_color: Optional[str] = None  # green, amber, red, gray


# Training validity periods (in days) - CQC requirements
TRAINING_VALIDITY_PERIODS = {
    "safeguarding": 365,  # Annual
    "safeguarding_of_vulnerable_adults": 365,
    "moving_and_handling": 365,
    "manual_handling": 365,
    "health_and_safety": 365,
    "infection_control": 365,
    "infection_control_and_hygiene": 365,
    "medication_administration": 365,
    "food_hygiene_nutrition_and_hydration": 365,
    "food_hygiene": 365,
    "first_aid_awareness": 1095,  # 3 years
    "first_aid": 1095,
    "fire_safety": 365,
    "covid_19": 365,
    "default": 365  # Default to annual
}


def get_training_validity_days(requirement_id: str) -> int:
    """Get validity period in days for a training requirement."""
    req_lower = requirement_id.lower().replace(' ', '_').replace('-', '_')
    return TRAINING_VALIDITY_PERIODS.get(req_lower, TRAINING_VALIDITY_PERIODS['default'])


def calculate_training_expiry(completion_date: str, requirement_id: str) -> str:
    """Calculate expiry date based on completion date and requirement validity period."""
    validity_days = get_training_validity_days(requirement_id)
    completion = datetime.fromisoformat(completion_date.replace('Z', '+00:00')) if 'T' in completion_date else datetime.strptime(completion_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    expiry = completion + timedelta(days=validity_days)
    return expiry.strftime('%Y-%m-%d')  # Return date-only format


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL DATE STORAGE RULES
# ═══════════════════════════════════════════════════════════════════════════════
# - expiry_date: YYYY-MM-DD (date-only, no timezone)
# - completion_date: YYYY-MM-DD (date-only, no timezone)  
# - created_at, updated_at, verified_at: Full ISO with timezone
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_date_only(date_value: str) -> Optional[str]:
    """
    Normalize a date value to YYYY-MM-DD format.
    Used for expiry_date and completion_date fields.
    
    Accepts:
    - YYYY-MM-DD: returns as-is
    - Full ISO: extracts date part
    - None/empty: returns None
    """
    if not date_value:
        return None
    
    if isinstance(date_value, str):
        # Already in correct format
        if len(date_value) == 10 and date_value[4] == '-' and date_value[7] == '-':
            return date_value
        
        # Full ISO format - extract date part
        if 'T' in date_value:
            return date_value.split('T')[0]
        
        # Try parsing other formats
        try:
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except Exception:
            pass
    
    return date_value  # Return as-is if can't parse


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE SOURCE OF TRUTH: Training Record Status Computation
# ═══════════════════════════════════════════════════════════════════════════════
# This is the CANONICAL function for computing training status.
# All APIs MUST use this function. Frontend MUST NOT compute status locally.
# ═══════════════════════════════════════════════════════════════════════════════

def compute_training_record_status(record: dict) -> dict:
    """
    SINGLE SOURCE OF TRUTH for training record status.
    
    Canonical fields used:
    - completion_date: When training was completed
    - expiry_date: When training expires (if set)
    - verified: Whether training has been verified
    
    Computed status values:
    - "not_started": No completion_date
    - "expired": expiry_date exists AND today > expiry_date
    - "needs_renewal": expiry_date exists AND within 30 days of expiry
    - "completed": Has completion_date, not expired, not near expiry
    - "valid": Same as completed (alias for clarity)
    
    Returns dict with:
    - computed_status: The canonical status string
    - renewal_status: Detailed expiry info (or None)
    - days_until_expiry: Number (negative if expired)
    - status_label: Human readable label
    - status_color: UI color (green/amber/red)
    """
    completion_date = record.get('completion_date')
    expiry_date = record.get('expiry_date')
    verified = record.get('verified', False)
    
    # No completion date = not started
    if not completion_date:
        return {
            "computed_status": "not_started",
            "renewal_status": None,
            "days_until_expiry": None,
            "status_label": "Not Started",
            "status_color": "gray"
        }
    
    # If no expiry date, it's completed/valid indefinitely
    if not expiry_date:
        return {
            "computed_status": "completed",
            "renewal_status": "no_expiry",
            "days_until_expiry": None,
            "status_label": "Completed" if not verified else "Verified",
            "status_color": "green"
        }
    
    # Calculate days until expiry
    try:
        now = datetime.now(timezone.utc)
        if isinstance(expiry_date, str):
            if 'T' in expiry_date:
                exp_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            else:
                exp_dt = datetime.strptime(expiry_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            exp_dt = expiry_date
        
        days_until_expiry = (exp_dt - now).days
        expiry_date_str = exp_dt.strftime('%Y-%m-%d')
        
        if days_until_expiry < 0:
            # EXPIRED
            return {
                "computed_status": "expired",
                "renewal_status": "expired",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Expired ({abs(days_until_expiry)}d ago)",
                "status_color": "red"
            }
        elif days_until_expiry <= EXPIRY_WARNING_DAYS:
            # NEEDS RENEWAL (within 30 days)
            return {
                "computed_status": "needs_renewal",
                "renewal_status": "expiring_soon",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Expires in {days_until_expiry}d",
                "status_color": "amber"
            }
        else:
            # VALID
            return {
                "computed_status": "completed",
                "renewal_status": "valid",
                "days_until_expiry": days_until_expiry,
                "expiry_date": expiry_date_str,
                "status_label": f"Valid ({days_until_expiry}d left)",
                "status_color": "green"
            }
    except Exception as e:
        logger.error(f"Error computing training status: {e}")
        return {
            "computed_status": "completed",
            "renewal_status": "unknown",
            "days_until_expiry": None,
            "status_label": "Completed",
            "status_color": "green"
        }


def enrich_training_record_with_computed_status(record: dict) -> dict:
    """
    Enrich a training record with computed status fields.
    This REPLACES any stale persisted status with freshly computed values.
    """
    computed = compute_training_record_status(record)
    
    # Create enriched record (copy to avoid mutation)
    enriched = dict(record)
    
    # Add computed fields
    enriched['computed_status'] = computed['computed_status']
    enriched['renewal_status'] = computed['renewal_status']
    enriched['days_until_expiry'] = computed['days_until_expiry']
    enriched['status_label'] = computed['status_label']
    enriched['status_color'] = computed['status_color']
    
    # IMPORTANT: Override persisted 'status' with computed value
    # This ensures stale "expired" or "expiring" flags don't persist incorrectly
    if computed['computed_status'] == 'expired':
        enriched['status'] = 'expired'
    elif computed['computed_status'] == 'needs_renewal':
        enriched['status'] = 'expiring'
    elif computed['computed_status'] == 'not_started':
        enriched['status'] = 'not_started'
    else:
        # Keep original status if completed (could be in_progress -> completed)
        if record.get('status') not in ['completed', 'verified']:
            enriched['status'] = 'completed'
    
    return enriched


async def get_or_create_training_record(
    employee_id: str, 
    requirement_id: str, 
    training_name: str,
    create_if_missing: bool = True
) -> Optional[dict]:
    """
    Get the SINGLE ACTIVE training record for an employee+requirement.
    Creates one if missing and create_if_missing=True.
    Enforces single source of truth.
    """
    # Find active record (NOT superseded or deleted)
    record = await db.training_records.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0})
    
    if record:
        return record
    
    # Try by training name if not found by requirement_id
    record = await db.training_records.find_one({
        "employee_id": employee_id,
        "training_name": {"$regex": f"^{re.escape(training_name)}$", "$options": "i"},
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0})
    
    if record:
        # Update requirement_id if missing
        if not record.get('requirement_id'):
            await db.training_records.update_one(
                {"id": record['id']},
                {"$set": {"requirement_id": requirement_id}}
            )
            record['requirement_id'] = requirement_id
        return record
    
    if not create_if_missing:
        return None
    
    # Create new record
    # HARDENING: Do not store derived status - will be computed at runtime
    now = datetime.now(timezone.utc).isoformat()
    new_record = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "training_name": training_name,
        "mandatory": True,
        # REMOVED: "status": "not_started" - derived from completion_date being None
        "record_status": "active",
        "completion_date": None,
        "expiry_date": None,
        "certificate_url": None,
        "evidence_files": [],
        "verified": False,
        "created_at": now,
        "updated_at": now
    }
    await db.training_records.insert_one(new_record)
    return new_record


async def supersede_training_record(record_id: str, user_id: str, reason: str = None):
    """Mark a training record as superseded (replaced by a newer one)."""
    now = datetime.now(timezone.utc).isoformat()
    
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        return False
    
    await db.training_records.update_one(
        {"id": record_id},
        {"$set": {
            "record_status": "superseded",
            "superseded_at": now,
            "superseded_by": user_id,
            "updated_at": now
        }}
    )
    
    await log_audit_action(user_id, "training_superseded", "training_record", record_id, {
        "training_name": record.get('training_name'),
        "employee_id": record.get('employee_id'),
        "reason": reason or "Replaced with newer record"
    })
    
    return True

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
    status: str  # missing, active, expired, under_review, due_soon
    required: Optional[bool] = True
    conditional: Optional[bool] = False
    review_period_months: Optional[int] = 12
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    review_date: Optional[str] = None  # Next review due date
    last_reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_status: Optional[str] = None  # current, due_soon, overdue
    assigned_staff_count: Optional[int] = 0
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
    category: Optional[str] = "insurance"  # insurance, regulatory, safety
    required: Optional[bool] = True
    conditional: Optional[bool] = False
    renewal_period_months: Optional[int] = 12
    requires_expiry_date: Optional[bool] = True  # Whether expiry date is mandatory for this cert type
    valid_until_replaced: Optional[bool] = False  # Whether cert is valid until replaced (no expiry)
    status: str  # valid, expiring_soon, expired, missing
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
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


# Amendment models with required reason for audit trail
class InsuranceDocUpdate(BaseModel):
    """Update model for insurance/certificates with audit trail"""
    name: Optional[str] = None
    expiry_date: Optional[str] = None
    policy_number: Optional[str] = None
    provider: Optional[str] = None
    issue_date: Optional[str] = None
    notes: Optional[str] = None
    reason: str  # Required for audit trail


class OrgPolicyAmend(BaseModel):
    """Amendment model for policies with audit trail"""
    name: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    review_date: Optional[str] = None
    notes: Optional[str] = None
    reason: str  # Required for audit trail


class IncidentLogAmend(BaseModel):
    """Amendment model for incidents with audit trail"""
    title: Optional[str] = None
    description: Optional[str] = None
    incident_type: Optional[str] = None
    date_occurred: Optional[str] = None
    location: Optional[str] = None
    persons_involved: Optional[str] = None
    immediate_actions: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_actions: Optional[str] = None
    lessons_learned: Optional[str] = None
    reason: str  # Required for audit trail


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
    """
    Calculate completion percentage using UNIFIED compliance logic.
    This is a convenience wrapper around calculate_employee_compliance.
    
    MUST return identical values to what profile/dashboard show.
    """
    # Get employee role
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "role": 1})
    if not employee:
        return 0
    
    role = employee.get('role', '')
    
    # Use the SINGLE unified calculation function
    compliance = await calculate_employee_compliance(employee_id, role)
    return compliance["completion_percentage"]

async def calculate_work_readiness_quick(employee_id: str, role: str) -> dict:
    """
    Quick work readiness calculation for list views.
    HARDENING: Now includes critical expiry check to match full readiness logic.
    """
    work_ready_ids = get_work_ready_items_for_role(role)
    
    # ===== CRITICAL EXPIRY CHECK (HARDENING) =====
    # Check for expired critical documents FIRST - this overrides everything
    # Reuses CRITICAL_EXPIRY_DOCS from calculate_separated_statuses()
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Check documents for critical expiry
    critical_expired_docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$in": list(CRITICAL_EXPIRY_DOCS)},
        "expiry_date": {"$exists": True, "$ne": None, "$lt": today_str},
        "verified": True,  # Only verified docs count for work readiness
        "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]}
    }, {"_id": 0, "requirement_id": 1, "expiry_date": 1}).to_list(10)
    
    if critical_expired_docs:
        expired_req = critical_expired_docs[0].get('requirement_id', 'document')
        return {
            "status": "not_ready", 
            "label": f"Critical Doc Expired", 
            "color": "error",
            "reason": f"Expired: {expired_req}"
        }
    
    # Also check training records for critical training expiry
    critical_training_ids = {"safeguarding", "manual_handling", "infection_control"}
    critical_expired_training = []
    
    for train_id in critical_training_ids:
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "requirement_id": train_id,
            "verified": True,
            "expiry_date": {"$exists": True, "$ne": None}
        }, {"_id": 0, "expiry_date": 1, "requirement_id": 1, "completion_date": 1})
        
        if record and record.get('expiry_date'):
            # Check if expired using canonical logic
            exp_date = record['expiry_date']
            if isinstance(exp_date, str) and exp_date < today_str:
                critical_expired_training.append(record)
    
    if critical_expired_training:
        expired_req = critical_expired_training[0].get('requirement_id', 'training')
        return {
            "status": "not_ready",
            "label": "Training Expired",
            "color": "error", 
            "reason": f"Expired: {expired_req}"
        }
    # ===== END CRITICAL EXPIRY CHECK =====
    
    # Get documents for mandatory items
    docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "requirement_id": {"$in": list(work_ready_ids)},
        "verified": True,
        # Exclude deleted/replaced/archived records
        "status": {"$nin": ["deleted", "replaced", "removed", "archived", "superseded"]}
    }, {"_id": 0, "requirement_id": 1}).to_list(100)
    
    # Get verified training for mandatory items
    training_ids = {r for r in work_ready_ids if r in ["safeguarding", "manual_handling", "infection_control"]}
    training = await db.training_records.find({
        "employee_id": employee_id,
        "requirement_id": {"$in": list(training_ids)},
        "verified": True,
        # HARDENING: Check for completion_date instead of status field
        "completion_date": {"$exists": True, "$ne": None},
        # HARDENING: Exclude superseded/deleted records
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0, "requirement_id": 1}).to_list(100)
    
    verified_ids = {d['requirement_id'] for d in docs}
    verified_ids.update({t['requirement_id'] for t in training})
    
    mandatory_complete = len(verified_ids.intersection(work_ready_ids))
    total_mandatory = len(work_ready_ids)
    
    # Calculate missing items for Not Ready reason
    missing_items = work_ready_ids - verified_ids
    
    # Build human-readable reason for missing items
    def get_missing_reason():
        if not missing_items:
            return None
        # Map IDs to readable names
        id_to_name = {
            "dbs_certificate": "DBS",
            "dbs_check": "DBS",
            "right_to_work_documents": "Right to Work",
            "right_to_work_check": "Right to Work",
            "safeguarding": "Safeguarding",
            "manual_handling": "Manual Handling",
            "infection_control": "Infection Control",
            "references": "References",
            "proof_of_identity": "ID",
            "proof_of_address": "Address"
        }
        names = [id_to_name.get(item, item.replace('_', ' ').title()) for item in list(missing_items)[:2]]
        if len(missing_items) > 2:
            return f"Missing: {', '.join(names)} +{len(missing_items)-2}"
        return f"Missing: {', '.join(names)}"
    
    if mandatory_complete == total_mandatory:
        return {"status": "work_ready", "label": "Ready to Work", "color": "success"}
    elif mandatory_complete >= total_mandatory - 2:
        return {"status": "supervised_start", "label": "Supervised Start Only", "color": "warning", "reason": get_missing_reason()}
    elif mandatory_complete > 0:
        return {"status": "in_progress", "label": "Not Ready", "color": "error", "reason": get_missing_reason()}
    else:
        return {"status": "not_started", "label": "Not Ready", "color": "error", "reason": get_missing_reason()}

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


@api_router.get("/dbs-register")
async def get_dbs_register(
    status_filter: Optional[str] = None,
    needs_attention: bool = False,
    user: dict = Depends(get_current_user)
):
    """
    DBS Register - Single source of truth for DBS status across all employees.
    Uses get_employee_dbs_summary() to compute all values.
    """
    # Get all non-archived employees
    employees = await db.employees.find(
        {"status": {"$ne": EmployeeStatus.ARCHIVED}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1, "email": 1}
    ).to_list(1000)
    
    register = []
    for emp in employees:
        # Use the SINGLE computed DBS summary function
        dbs_summary = await get_employee_dbs_summary(emp["id"])
        
        # Apply filters
        if status_filter and dbs_summary["dbs_status"] != status_filter:
            continue
        if needs_attention and not dbs_summary["needs_attention"]:
            continue
        
        register.append({
            "employee_id": emp["id"],
            "employee_name": f"{emp['first_name']} {emp['last_name']}",
            "role": emp.get("role", ""),
            "email": emp.get("email", ""),
            **dbs_summary
        })
    
    # Sort: needs_attention first, then by next_dbs_review_due
    register.sort(key=lambda x: (
        not x.get("needs_attention", False),  # needs_attention=True first
        x.get("next_dbs_review_due") or "9999"  # earliest review due first
    ))
    
    # Summary stats
    stats = {
        "total": len(register),
        "current": len([r for r in register if r["dbs_status"] == "current"]),
        "certificate_only": len([r for r in register if r["dbs_status"] == "certificate_only"]),
        "pending_verification": len([r for r in register if r["dbs_status"] == "pending_verification"]),
        "review_due_soon": len([r for r in register if r["dbs_status"] == "review_due_soon"]),
        "review_overdue": len([r for r in register if r["dbs_status"] == "review_overdue"]),
        "missing": len([r for r in register if r["dbs_status"] == "missing"]),
        "needs_attention": len([r for r in register if r["needs_attention"]])
    }
    
    return {
        "register": register,
        "stats": stats
    }


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


# ============================================================================
# REFERENCE INTEGRITY ENDPOINTS
# Ensures references match CV OR require documented justification
# ============================================================================

class ReferenceVerificationRequest(BaseModel):
    reference_num: int  # 1 or 2
    from_cv: bool
    override_reason: Optional[str] = None  # Required if from_cv=False

@api_router.post("/employees/{employee_id}/verify-reference")
async def verify_reference(
    employee_id: str,
    request: ReferenceVerificationRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Verify a reference with integrity check.
    
    CRITICAL RULES:
    1. If from_cv=False, override_reason is REQUIRED (min 10 chars)
    2. Cannot verify without meeting integrity requirements
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if request.reference_num not in [1, 2]:
        raise HTTPException(status_code=400, detail="Reference number must be 1 or 2")
    
    prefix = f"reference_{request.reference_num}"
    
    # Check if reference exists
    if not employee.get(f"{prefix}_name"):
        raise HTTPException(status_code=400, detail=f"Reference {request.reference_num} has no data to verify")
    
    # INTEGRITY CHECK: If not from CV, require override reason
    if not request.from_cv:
        if not request.override_reason or len(request.override_reason.strip()) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Reference does not match CV - justification required (minimum 10 characters explaining why this reference differs from CV)"
            )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee with reference integrity fields
    update_data = {
        f"{prefix}_from_cv": request.from_cv,
        f"{prefix}_override_reason": request.override_reason if not request.from_cv else None,
        f"{prefix}_verified": True,
        f"{prefix}_verified_by": user['user_id'],
        f"{prefix}_verified_at": now,
        "updated_at": now
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'],
        "verify_reference",
        "employee",
        employee_id,
        {
            "reference_num": request.reference_num,
            "from_cv": request.from_cv,
            "override_reason": request.override_reason if not request.from_cv else None,
            "reference_name": employee.get(f"{prefix}_name"),
            "reference_company": employee.get(f"{prefix}_company")
        }
    )
    
    return {
        "message": f"Reference {request.reference_num} verified successfully",
        "reference_num": request.reference_num,
        "from_cv": request.from_cv,
        "has_override": not request.from_cv,
        "verified_by": user.get('name', user.get('email')),
        "verified_at": now
    }


@api_router.get("/employees/{employee_id}/reference-integrity")
async def get_reference_integrity_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get reference integrity status for an employee.
    Returns validation status for both references.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    integrity_status = check_all_references_integrity(employee)
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
        "reference_integrity": integrity_status,
        "references": {
            "reference_1": {
                "name": employee.get("reference_1_name"),
                "company": employee.get("reference_1_company"),
                "from_cv": employee.get("reference_1_from_cv"),
                "override_reason": employee.get("reference_1_override_reason"),
                "verified": employee.get("reference_1_verified", False),
                "verified_by": employee.get("reference_1_verified_by"),
                "verified_at": employee.get("reference_1_verified_at")
            },
            "reference_2": {
                "name": employee.get("reference_2_name"),
                "company": employee.get("reference_2_company"),
                "from_cv": employee.get("reference_2_from_cv"),
                "override_reason": employee.get("reference_2_override_reason"),
                "verified": employee.get("reference_2_verified", False),
                "verified_by": employee.get("reference_2_verified_by"),
                "verified_at": employee.get("reference_2_verified_at")
            }
        }
    }


# ============================================================================
# CV GAP ANALYSIS ENDPOINTS
# Detects and requires explanation of employment gaps
# ============================================================================

class EmploymentRecord(BaseModel):
    company: str
    role: Optional[str] = None
    start_date: str  # YYYY-MM-DD
    end_date: Optional[str] = None  # None = current job
    gap_after_explanation: Optional[str] = None  # Explanation for gap after this job

class UpdateEmploymentHistoryRequest(BaseModel):
    employment_history: List[EmploymentRecord]

@api_router.post("/employees/{employee_id}/employment-history")
async def update_employment_history(
    employee_id: str,
    request: UpdateEmploymentHistoryRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Update employment history and auto-detect gaps.
    
    Gaps > 30 days are flagged and require explanation.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Convert to dict format
    history_data = [r.model_dump() for r in request.employment_history]
    
    # Detect gaps automatically
    gaps = detect_cv_gaps(history_data)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update employee with history and detected gaps
    update_data = {
        "employment_history": history_data,
        "cv_gaps_detected": gaps,
        "cv_gaps_all_explained": all(g.get("explanation") and len(str(g.get("explanation", "")).strip()) >= 10 for g in gaps) if gaps else True,
        "updated_at": now
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    await log_audit_action(
        user['user_id'],
        "update_employment_history",
        "employee",
        employee_id,
        {
            "job_count": len(history_data),
            "gaps_detected": len(gaps),
            "gaps_explained": sum(1 for g in gaps if g.get("explanation"))
        }
    )
    
    return {
        "message": "Employment history updated",
        "employment_history": history_data,
        "gaps_detected": gaps,
        "gaps_all_explained": update_data["cv_gaps_all_explained"],
        "gaps_requiring_explanation": [g for g in gaps if not g.get("explanation") or len(str(g.get("explanation", "")).strip()) < 10]
    }


class ExplainGapRequest(BaseModel):
    gap_id: str
    explanation: str  # Required, min 10 characters

@api_router.post("/employees/{employee_id}/explain-cv-gap")
async def explain_cv_gap(
    employee_id: str,
    request: ExplainGapRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Provide explanation for a CV gap.
    
    REQUIRED: Explanation must be at least 10 characters.
    """
    if len(request.explanation.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Gap explanation must be at least 10 characters"
        )
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    gaps = employee.get("cv_gaps_detected", [])
    if not gaps:
        raise HTTPException(status_code=400, detail="No gaps detected for this employee")
    
    # Find and update the specific gap
    gap_found = False
    for gap in gaps:
        if gap.get("gap_id") == request.gap_id:
            gap["explanation"] = request.explanation
            gap["verified"] = True
            gap["verified_by"] = user['user_id']
            gap["verified_at"] = datetime.now(timezone.utc).isoformat()
            gap_found = True
            break
    
    if not gap_found:
        raise HTTPException(status_code=404, detail=f"Gap '{request.gap_id}' not found")
    
    # Check if all gaps now explained
    all_explained = all(
        g.get("explanation") and len(str(g.get("explanation", "")).strip()) >= 10 
        for g in gaps
    )
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "cv_gaps_detected": gaps,
            "cv_gaps_all_explained": all_explained,
            "updated_at": now
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "explain_cv_gap",
        "employee",
        employee_id,
        {
            "gap_id": request.gap_id,
            "explanation": request.explanation,
            "all_gaps_explained": all_explained
        }
    )
    
    return {
        "message": "Gap explanation recorded",
        "gap_id": request.gap_id,
        "explanation": request.explanation,
        "all_gaps_explained": all_explained,
        "remaining_unexplained": len([g for g in gaps if not g.get("explanation") or len(str(g.get("explanation", "")).strip()) < 10])
    }


@api_router.get("/employees/{employee_id}/cv-gaps")
async def get_cv_gaps_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get CV gap analysis status for an employee.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    gaps_status = check_cv_gaps_complete(employee)
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
        "employment_history": employee.get("employment_history", []),
        "gaps_detected": employee.get("cv_gaps_detected", []),
        "gaps_status": gaps_status,
        "can_complete_recruitment": gaps_status["can_complete_recruitment"]
    }


@api_router.get("/employees/{employee_id}/recruitment-status")
async def get_recruitment_status(
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get full recruitment status including reference integrity and CV gaps.
    
    Shows all blockers that prevent recruitment from being marked complete.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get compliance requirements which now includes recruitment status
    compliance = await get_compliance_requirements(employee_id, user)
    
    # Build comprehensive recruitment status
    reference_integrity = compliance.get("reference_integrity", {})
    cv_gaps_status = compliance.get("cv_gaps_status", {})
    recruitment_status = compliance.get("recruitment_status", {})
    
    # Check proof of address requirement
    proof_of_address_req = None
    for req in compliance.get("requirements", []):
        if req.get("id") == "proof_of_address":
            proof_of_address_req = req
            break
    
    proof_of_address_status = {
        "required_count": 2,
        "current_count": proof_of_address_req.get("document_count", 0) if proof_of_address_req else 0,
        "verified_count": len([d for d in (proof_of_address_req or {}).get("documents", []) if d.get("verified")]) if proof_of_address_req else 0,
        "complete": proof_of_address_req.get("verified", False) if proof_of_address_req else False
    }
    
    # Calculate overall recruitment readiness
    recruitment_blockers = recruitment_status.get("blockers", [])
    if not proof_of_address_status["complete"]:
        if proof_of_address_status["current_count"] < 2:
            recruitment_blockers.append(f"Proof of Address: {proof_of_address_status['current_count']}/2 documents uploaded")
        elif proof_of_address_status["verified_count"] < 2:
            recruitment_blockers.append(f"Proof of Address: {proof_of_address_status['verified_count']}/2 documents verified")
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
        "recruitment_complete": len(recruitment_blockers) == 0,
        "blockers": recruitment_blockers,
        "details": {
            "reference_integrity": reference_integrity,
            "cv_gaps": cv_gaps_status,
            "proof_of_address": proof_of_address_status
        },
        "summary": {
            "references_valid": reference_integrity.get("all_valid", False),
            "cv_gaps_explained": cv_gaps_status.get("all_gaps_explained", True),
            "proof_of_address_complete": proof_of_address_status["complete"]
        }
    }




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


# ==================== APPLICATION FORM EXTRACTION ====================
# Extracts profile data from uploaded application forms using AI/OCR
# NOTE: This populates PROFILE DATA ONLY - NOT compliance evidence

# Complete mapping of application form fields to employee profile fields
APPLICATION_FORM_FIELD_MAPPING = {
    # Personal Details
    "first_name": "first_name",
    "last_name": "last_name",
    "middle_name": "middle_name",
    "title": "title",
    "street": "address_line_1",
    "address_line_1": "address_line_1",
    "address_line_2": "address_line_2",
    "city": "city",
    "county": "county",
    "postcode": "postcode",
    "country": "country",
    "national_insurance_number": "ni_number",
    "ni_number": "ni_number",
    "contact_number": "phone",
    "phone": "phone",
    "other_contact_number": "phone_secondary",
    "phone_secondary": "phone_secondary",
    "primary_email_address": "email",
    "email": "email",
    "date_of_birth": "date_of_birth",
    "do_you_drive": "has_driving_licence",
    "has_driving_licence": "has_driving_licence",
    "driving_licence_number": "driving_licence_number",
    "do_you_have_access_to_your_own_vehicle": "has_own_vehicle",
    "has_own_vehicle": "has_own_vehicle",
    "vehicle_registration": "vehicle_registration",
    "vehicle_make_model": "vehicle_make_model",
    
    # Next of Kin
    "next_of_kin_name": "next_of_kin_name",
    "nok_name": "next_of_kin_name",
    "next_of_kin_relationship": "next_of_kin_relationship",
    "nok_relationship": "next_of_kin_relationship",
    "next_of_kin_phone": "next_of_kin_phone",
    "nok_phone": "next_of_kin_phone",
    "next_of_kin_address": "next_of_kin_address",
    "nok_address": "next_of_kin_address",
    "next_of_kin_city": "next_of_kin_city",
    "nok_city": "next_of_kin_city",
    "next_of_kin_county": "next_of_kin_county",
    "nok_county": "next_of_kin_county",
    "next_of_kin_postcode": "next_of_kin_postcode",
    "nok_postcode": "next_of_kin_postcode",
    "next_of_kin_country": "next_of_kin_country",
    "nok_country": "next_of_kin_country",
    
    # References
    "referee_1_name": "reference_1_name",
    "reference_1_name": "reference_1_name",
    "referee_1_organisation": "reference_1_company",
    "reference_1_company": "reference_1_company",
    "referee_1_email": "reference_1_email",
    "reference_1_email": "reference_1_email",
    "referee_1_phone": "reference_1_phone",
    "reference_1_phone": "reference_1_phone",
    "referee_1_start_date": "reference_1_start_date",
    "reference_1_end_date": "reference_1_end_date",
    "referee_2_name": "reference_2_name",
    "reference_2_name": "reference_2_name",
    "referee_2_organisation": "reference_2_company",
    "reference_2_company": "reference_2_company",
    "referee_2_email": "reference_2_email",
    "reference_2_email": "reference_2_email",
    "referee_2_phone": "reference_2_phone",
    "reference_2_phone": "reference_2_phone",
    "referee_2_start_date": "reference_2_start_date",
    "reference_2_end_date": "reference_2_end_date",
    
    # Declarations (flags only - not evidence)
    "working_time_opt_out": "working_time_opt_out",
    "dbs_update_service_consent": "dbs_update_service_consent",
    "criminal_offence_declaration": "criminal_offence_declared",
    "professional_misconduct_declaration": "professional_misconduct_declared",
    "health_issue_declaration": "health_issue_declared",
    
    # Health-related fields (STRICTLY LIMITED for CQC compliance)
    # Only these 3 health fields can be extracted - no other medical data
    "health_issues_disability": "health_issues_disability",  # Maps to medical_problems_affecting_work
    "influenza_vaccine_status": "influenza_vaccine_status",
    "influenza_vaccine_date": "flu_vaccination_date",
    "flu_vaccination_date": "flu_vaccination_date",
    
    # Professional registration
    "professional_registration_number": "professional_registration_number",
}

# Fields that can be extracted from application forms
EXTRACTABLE_PROFILE_FIELDS = list(set(APPLICATION_FORM_FIELD_MAPPING.values()))

# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT-SAFE EXTRACTION RULES
# ═══════════════════════════════════════════════════════════════════════════════
# Fields that can be safely auto-applied (default apply=True when field is empty)
# These are non-sensitive personal info fields that don't affect CQC compliance
SAFE_AUTO_APPLY_FIELDS = {
    "first_name", "last_name", "middle_name", "title",
    "address_line_1", "address_line_2", "city", "county", "postcode", "country",
    "phone", "phone_secondary", "email", "date_of_birth",
    "has_driving_licence", "driving_licence_number", "has_own_vehicle",
    "vehicle_registration", "vehicle_make_model",
    "next_of_kin_name", "next_of_kin_relationship", "next_of_kin_phone",
    "next_of_kin_address", "next_of_kin_city", "next_of_kin_county",
    "next_of_kin_postcode", "next_of_kin_country",
    "ni_number",  # NI number is profile data (evidence is separate)
    "professional_registration_number",
}

# Fields that require manual review before applying (default apply=False)
# These are sensitive fields that affect compliance or require verification
REVIEW_BEFORE_APPLY_FIELDS = {
    # References - require verification from referees
    "reference_1_name", "reference_1_company", "reference_1_email", "reference_1_phone",
    "reference_1_start_date", "reference_1_end_date",
    "reference_2_name", "reference_2_company", "reference_2_email", "reference_2_phone",
    "reference_2_start_date", "reference_2_end_date",
    # Declarations - critical CQC compliance fields
    "working_time_opt_out", "dbs_update_service_consent",
    "criminal_offence_declared", "professional_misconduct_declared",
    "health_issue_declared",
    # Health data - sensitive, requires explicit review
    "health_issues_disability", "influenza_vaccine_status", "flu_vaccination_date",
}

class ExtractedField(BaseModel):
    """A single extracted field with its value and confidence"""
    field_name: str
    extracted_value: Optional[str] = None
    current_value: Optional[str] = None
    confidence: float = 0.5  # 0.0 to 1.0 numeric confidence score
    confidence_label: str = "medium"  # low, medium, high - for display
    apply: bool = True  # Default to apply, user can skip
    extraction_method: Optional[str] = None  # "ai" or "ocr"

class ExtractionResult(BaseModel):
    """Result of application form extraction"""
    employee_id: str
    document_id: str
    extraction_id: str
    fields: List[ExtractedField]
    extraction_notes: Optional[str] = None
    extracted_at: str
    status: str = "pending_review"  # pending_review, applied, discarded

class ApplyExtractionRequest(BaseModel):
    """Request to apply extracted values"""
    extraction_id: str
    fields_to_apply: List[str]  # List of field names to apply


class ExtractionLog(BaseModel):
    """Detailed extraction log for debugging"""
    file_type: str
    file_size_bytes: int
    ai_extraction_attempted: bool = False
    ai_extraction_success: bool = False
    ai_error: Optional[str] = None
    ai_overall_confidence: Optional[float] = None  # Overall AI confidence score
    ocr_attempted: bool = False
    ocr_success: bool = False
    ocr_error: Optional[str] = None
    final_method: Optional[str] = None  # "ai", "ocr", "ai+ocr", "failed"
    failure_reason: Optional[str] = None
    fields_extracted: int = 0
    low_confidence_fields: List[str] = []
    ocr_retry_reason: Optional[str] = None  # Why OCR was triggered after AI


def perform_ocr_extraction(file_bytes: bytes, content_type: str) -> tuple[str, str]:
    """
    Perform OCR on document bytes using Tesseract.
    Returns (extracted_text, error_message)
    
    NOTE: This is now a FALLBACK method. pdfplumber is primary for PDFs.
    """
    try:
        extracted_texts = []
        
        # Handle PDFs - convert to images first
        if 'pdf' in content_type.lower():
            try:
                images = convert_from_bytes(file_bytes, dpi=200)
                for i, image in enumerate(images):
                    text = pytesseract.image_to_string(image, lang='eng')
                    if text.strip():
                        extracted_texts.append(f"--- Page {i+1} ---\n{text}")
            except Exception as pdf_err:
                return "", f"PDF conversion failed: {str(pdf_err)}"
        else:
            # Handle image files directly
            try:
                image = PILImage.open(io.BytesIO(file_bytes))
                # Convert to RGB if necessary (for RGBA or other modes)
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')
                text = pytesseract.image_to_string(image, lang='eng')
                if text.strip():
                    extracted_texts.append(text)
            except Exception as img_err:
                return "", f"Image processing failed: {str(img_err)}"
        
        combined_text = "\n".join(extracted_texts)
        if combined_text.strip():
            return combined_text, ""
        else:
            return "", "OCR produced no readable text"
            
    except Exception as e:
        return "", f"OCR extraction error: {str(e)}"


def perform_pdfplumber_extraction(file_bytes: bytes) -> tuple[str, str]:
    """
    PRIMARY METHOD: Extract text directly from PDF using pdfplumber.
    Works best with typed/structured forms (not scanned images).
    
    Returns (extracted_text, error_message)
    """
    try:
        import pdfplumber
        
        extracted_texts = []
        
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            logger.info(f"pdfplumber: Processing PDF with {len(pdf.pages)} pages")
            
            for i, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text() or ""
                
                # Also try extracting tables if present
                tables = page.extract_tables()
                table_text = ""
                for table in tables:
                    if table:
                        for row in table:
                            if row:
                                row_text = " | ".join([str(cell or "").strip() for cell in row])
                                if row_text.strip():
                                    table_text += row_text + "\n"
                
                # Combine text and table data
                page_content = text
                if table_text:
                    page_content += f"\n\n[TABLE DATA]\n{table_text}"
                
                if page_content.strip():
                    extracted_texts.append(f"--- Page {i+1} ---\n{page_content}")
        
        combined_text = "\n\n".join(extracted_texts)
        
        if combined_text and len(combined_text.strip()) > 50:
            logger.info(f"pdfplumber: Extracted {len(combined_text)} characters from PDF")
            return combined_text, ""
        else:
            return "", "pdfplumber extracted insufficient text (may be scanned/image PDF)"
            
    except ImportError:
        return "", "pdfplumber not installed"
    except Exception as e:
        return "", f"pdfplumber extraction error: {str(e)}"


def validate_extracted_value(field_name: str, value: str) -> tuple[bool, str]:
    """
    Validate extracted values before saving.
    Returns (is_valid, rejection_reason)
    
    Rejects:
    - Placeholder/test values (TEST_, SAMPLE_, etc.)
    - Invalid NI number formats
    - Malformed emails
    - Empty or whitespace-only values
    """
    if not value or not value.strip():
        return False, "Empty or whitespace value"
    
    value = value.strip()
    
    # Reject placeholder values
    placeholder_patterns = [
        r'^TEST_',
        r'^SAMPLE_',
        r'^EXAMPLE_',
        r'^XXX',
        r'^000000',
        r'^placeholder',
        r'^N/A$',
        r'^TBD$',
        r'^TBC$',
        r'^\[.*\]$',  # [brackets]
        r'^<.*>$',    # <angle brackets>
    ]
    
    for pattern in placeholder_patterns:
        if re.match(pattern, value, re.IGNORECASE):
            return False, f"Appears to be placeholder value: {value}"
    
    # Field-specific validation
    if field_name == 'ni_number':
        # UK NI format: 2 letters, 6 numbers, 1 letter (e.g., AB123456C)
        ni_pattern = r'^[A-Z]{2}\d{6}[A-Z]$'
        if not re.match(ni_pattern, value.upper().replace(' ', '')):
            return False, f"Invalid NI number format: {value}"
    
    if field_name == 'email':
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            return False, f"Invalid email format: {value}"
    
    if field_name == 'phone' or field_name == 'emergency_phone':
        # Basic phone validation - must have at least 10 digits
        digits = re.sub(r'\D', '', value)
        if len(digits) < 10:
            return False, f"Phone number too short: {value}"
    
    if field_name == 'postcode':
        # UK postcode pattern (simplified)
        postcode_pattern = r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$'
        if not re.match(postcode_pattern, value.upper().replace('  ', ' ')):
            return False, f"Invalid UK postcode format: {value}"
    
    if field_name == 'date_of_birth':
        # Must be valid date
        try:
            # Try common formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    parsed = datetime.strptime(value, fmt)
                    # Basic sanity check - DOB should be 16-100 years ago
                    age = (datetime.now() - parsed).days / 365
                    if age < 16 or age > 100:
                        return False, f"Date of birth implies unrealistic age: {value}"
                    break
                except:
                    continue
            else:
                return False, f"Cannot parse date of birth: {value}"
        except:
            return False, f"Invalid date of birth: {value}"
    
    return True, ""


async def extract_text_from_document(file_url: str) -> tuple[str, ExtractionLog]:
    """
    Extract text content from a document using IMPROVED pipeline.
    
    NEW EXTRACTION ORDER (for typed/structured forms):
    ═══════════════════════════════════════════════════════════════════
    1. pdfplumber (PRIMARY) - Direct text extraction for typed PDFs
    2. OCR fallback (pdf2image + pytesseract) - For scanned/image PDFs
    3. AI extraction - For image files or supplemental extraction
    ═══════════════════════════════════════════════════════════════════
    
    Returns (extracted_text, extraction_log)
    """
    extraction_log = ExtractionLog(
        file_type="unknown",
        file_size_bytes=0
    )
    
    try:
        # Get document bytes
        file_bytes, content_type = get_object(file_url)
        extraction_log.file_type = content_type or "unknown"
        extraction_log.file_size_bytes = len(file_bytes)
        
        logger.info(f"[EXTRACTION] Started - Type: {content_type}, Size: {len(file_bytes)} bytes")
        
        is_pdf = 'pdf' in (content_type or '').lower()
        extracted_text = ""
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: pdfplumber (PRIMARY for PDFs)
        # ═══════════════════════════════════════════════════════════════════
        if is_pdf:
            logger.info("[EXTRACTION] Step 1: Trying pdfplumber (primary method for typed PDFs)...")
            
            pdf_text, pdf_error = perform_pdfplumber_extraction(file_bytes)
            
            if pdf_text and len(pdf_text.strip()) > 100:
                logger.info(f"[EXTRACTION] pdfplumber SUCCESS - {len(pdf_text)} chars extracted")
                extraction_log.final_method = "pdfplumber"
                extraction_log.ai_extraction_attempted = False
                extraction_log.ocr_attempted = False
                return pdf_text, extraction_log
            else:
                logger.info(f"[EXTRACTION] pdfplumber insufficient: {pdf_error}")
                # Continue to OCR fallback
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: OCR Fallback (for scanned PDFs or images)
        # ═══════════════════════════════════════════════════════════════════
        logger.info("[EXTRACTION] Step 2: Trying OCR (fallback for scanned documents)...")
        extraction_log.ocr_attempted = True
        
        ocr_text, ocr_error = perform_ocr_extraction(file_bytes, content_type)
        
        if ocr_text and len(ocr_text.strip()) > 100:
            logger.info(f"[EXTRACTION] OCR SUCCESS - {len(ocr_text)} chars extracted")
            extraction_log.ocr_success = True
            extraction_log.final_method = "ocr"
            return ocr_text, extraction_log
        else:
            extraction_log.ocr_error = ocr_error or "OCR produced insufficient text"
            logger.info(f"[EXTRACTION] OCR insufficient: {ocr_error}")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: AI Vision Extraction (final fallback)
        # ═══════════════════════════════════════════════════════════════════
        logger.info("[EXTRACTION] Step 3: Trying AI Vision extraction (final fallback)...")
        extraction_log.ai_extraction_attempted = True
        
        try:
            api_key = os.environ.get('EMERGENT_LLM_KEY')
            if not api_key:
                extraction_log.ai_error = "LLM API key not configured"
                logger.warning("[EXTRACTION] AI skipped: LLM API key not configured")
            else:
                # For PDFs, convert to images first (GPT-5.2 only accepts images)
                images_to_process = []
                
                if is_pdf:
                    try:
                        from pdf2image import convert_from_bytes
                        pdf_images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=3)
                        for i, img in enumerate(pdf_images):
                            img_buffer = io.BytesIO()
                            img.save(img_buffer, format='PNG')
                            img_bytes = img_buffer.getvalue()
                            images_to_process.append(base64.b64encode(img_bytes).decode('utf-8'))
                        logger.info(f"[EXTRACTION] Converted PDF to {len(images_to_process)} image(s) for AI")
                    except Exception as pdf_err:
                        extraction_log.ai_error = f"PDF to image conversion failed: {str(pdf_err)}"
                        logger.warning(f"[EXTRACTION] Failed to convert PDF to images: {pdf_err}")
                else:
                    images_to_process.append(base64.b64encode(file_bytes).decode('utf-8'))
                
                if images_to_process:
                    all_extracted_text = []
                    ai_quality_score = 0
                    
                    for i, image_base64 in enumerate(images_to_process):
                        chat = LlmChat(
                            api_key=api_key,
                            session_id=f"extraction-{uuid.uuid4()}",
                            system_message="""You are a document data extraction specialist. Extract all visible text and data from the provided document image.
Focus on identifying form fields, their labels, and the values filled in.
Return the extracted content in a structured, readable format.
At the end, rate your confidence in the extraction quality from 0-100 on a new line like: CONFIDENCE_SCORE: 85"""
                        ).with_model("openai", "gpt-5.2")
                        
                        image_content = ImageContent(image_base64=image_base64)
                        user_message = UserMessage(
                            text=f"Extract all text and data from this document image (page {i+1}). Include form field labels and their values. End with CONFIDENCE_SCORE: X (0-100).",
                            file_contents=[image_content]
                        )
                        
                        page_text = await chat.send_message(user_message)
                        if page_text and page_text.strip():
                            # Extract confidence score if present
                            confidence_match = re.search(r'CONFIDENCE_SCORE:\s*(\d+)', page_text)
                            if confidence_match:
                                page_confidence = int(confidence_match.group(1))
                                ai_quality_score = max(ai_quality_score, page_confidence)
                                page_text = re.sub(r'\n*CONFIDENCE_SCORE:\s*\d+\s*$', '', page_text).strip()
                            all_extracted_text.append(f"--- Page {i+1} ---\n{page_text}")
                    
                    ai_text = "\n\n".join(all_extracted_text)
                    
                    if ai_text and len(ai_text.strip()) > 50:
                        extraction_log.ai_extraction_success = True
                        extraction_log.ai_overall_confidence = ai_quality_score / 100.0 if ai_quality_score else 0.7
                        extraction_log.final_method = "ai"
                        logger.info(f"[EXTRACTION] AI SUCCESS - {len(ai_text)} chars, confidence: {ai_quality_score}")
                        return ai_text, extraction_log
                    else:
                        extraction_log.ai_error = "AI returned insufficient text"
                else:
                    extraction_log.ai_error = "No images to process"
                    
        except Exception as ai_err:
            extraction_log.ai_error = str(ai_err)
            logger.warning(f"[EXTRACTION] AI failed: {ai_err}")
        
        # All methods failed
        extraction_log.final_method = "failed"
        extraction_log.failure_reason = f"All extraction methods failed. pdfplumber: N/A, OCR: {extraction_log.ocr_error}, AI: {extraction_log.ai_error}"
        logger.error(f"[EXTRACTION] FAILED - All methods exhausted")
        return "", extraction_log
            
    except Exception as e:
        extraction_log.failure_reason = f"Document retrieval error: {str(e)}"
        extraction_log.final_method = "failed"
        logger.error(f"[EXTRACTION] Failed to retrieve document: {e}")
        return "", extraction_log


async def parse_extracted_text_to_fields(extracted_text: str, employee_id: str, extraction_method: str = "ai") -> tuple[List[ExtractedField], List[str]]:
    """
    Parse extracted text into structured profile fields using AI.
    Returns (list of extracted fields, list of low confidence field names)
    """
    low_confidence_fields = []
    
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            return [], []
        
        # Get current employee data for comparison
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        current_values = {}
        if employee:
            for field in EXTRACTABLE_PROFILE_FIELDS:
                current_values[field] = employee.get(field)
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"parsing-{uuid.uuid4()}",
            system_message="""You are a data parsing specialist. Parse the extracted document text into structured profile fields.
Return a JSON array of objects with NUMERIC confidence scores.
Each object has: field_name, extracted_value, confidence (0.0 to 1.0 number).
- confidence 0.9-1.0 = clearly visible and readable
- confidence 0.6-0.89 = partially visible or slightly unclear
- confidence 0.0-0.59 = unclear, guessed, or uncertain
Only include fields where you found data. Use exact field names from the allowed list."""
        ).with_model("openai", "gpt-5.2")
        
        field_list = ", ".join(EXTRACTABLE_PROFILE_FIELDS)
        prompt = f"""Parse this extracted application form text into profile fields.

Allowed field names: {field_list}

For boolean fields (has_driving_licence, has_own_vehicle), use "true" or "false" as strings.
For date_of_birth, use format YYYY-MM-DD if possible.
For ni_number, preserve the format (e.g., AB123456C).

Extracted text:
---
{extracted_text}
---

Return ONLY a JSON array like:
[
  {{"field_name": "first_name", "extracted_value": "John", "confidence": 0.95}},
  {{"field_name": "postcode", "extracted_value": "SW1A 1AA", "confidence": 0.72}},
  {{"field_name": "ni_number", "extracted_value": "AB123456C", "confidence": 0.55}}
]

Rules for confidence scoring:
- 0.9-1.0: Text is clearly printed/typed, fully visible, unambiguous
- 0.7-0.89: Text is readable but has minor issues (slight blur, handwriting)
- 0.5-0.69: Text is partially unclear, some guessing involved
- Below 0.5: Significant uncertainty, may be wrong

If no data can be extracted, return an empty array: []"""

        response = await chat.send_message(UserMessage(text=prompt))
        
        # Parse JSON response
        import json
        try:
            # Find JSON array in response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                parsed_fields = json.loads(json_match.group())
            else:
                parsed_fields = []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response as JSON: {response[:200]}")
            parsed_fields = []
        
        # Convert to ExtractedField objects with current values and VALIDATION
        result = []
        rejected_fields = []
        
        for field_data in parsed_fields:
            field_name = field_data.get('field_name', '')
            if field_name in EXTRACTABLE_PROFILE_FIELDS:
                extracted_val = field_data.get('extracted_value')
                current_val = current_values.get(field_name)
                
                # Convert current value to string for comparison
                if current_val is not None and not isinstance(current_val, str):
                    current_val = str(current_val)
                
                # ═══════════════════════════════════════════════════════════
                # VALIDATION: Reject invalid/placeholder values
                # ═══════════════════════════════════════════════════════════
                if extracted_val:
                    is_valid, rejection_reason = validate_extracted_value(field_name, str(extracted_val))
                    if not is_valid:
                        rejected_fields.append(f"{field_name}: {rejection_reason}")
                        logger.warning(f"[EXTRACTION] Rejected field '{field_name}': {rejection_reason}")
                        continue  # Skip this field
                
                # Handle confidence - could be string or number
                raw_confidence = field_data.get('confidence', 0.5)
                if isinstance(raw_confidence, str):
                    # Convert old string format to numeric
                    confidence_map = {'high': 0.9, 'medium': 0.7, 'low': 0.4}
                    confidence_score = confidence_map.get(raw_confidence.lower(), 0.5)
                else:
                    confidence_score = float(raw_confidence) if raw_confidence else 0.5
                
                # Determine confidence label
                if confidence_score >= 0.8:
                    confidence_label = "high"
                elif confidence_score >= 0.5:
                    confidence_label = "medium"
                else:
                    confidence_label = "low"
                    low_confidence_fields.append(field_name)
                
                # ═══════════════════════════════════════════════════════════
                # AUDIT-SAFE APPLY RULES
                # ═══════════════════════════════════════════════════════════
                # Rule 1: If current value exists, NEVER auto-apply (preserve verified data)
                # Rule 2: If field requires review (declarations, references, health), default to False
                # Rule 3: Only safe personal info fields can auto-apply when empty
                if current_val:
                    # Existing value - never overwrite automatically
                    should_apply = False
                elif field_name in REVIEW_BEFORE_APPLY_FIELDS:
                    # Sensitive field - always require manual review
                    should_apply = False
                elif field_name in SAFE_AUTO_APPLY_FIELDS:
                    # Safe field with no existing value - can auto-apply
                    should_apply = True
                else:
                    # Unknown field - default to requiring review
                    should_apply = False
                
                result.append(ExtractedField(
                    field_name=field_name,
                    extracted_value=extracted_val,
                    current_value=current_val,
                    confidence=confidence_score,
                    confidence_label=confidence_label,
                    apply=should_apply,
                    extraction_method=extraction_method
                ))
        
        if rejected_fields:
            logger.info(f"[EXTRACTION] Rejected {len(rejected_fields)} fields with invalid values: {rejected_fields}")
        
        logger.info(f"[EXTRACTION] Parsed {len(result)} valid fields, {len(low_confidence_fields)} with low confidence")
        return result, low_confidence_fields
    except Exception as e:
        logger.error(f"Failed to parse extracted text: {e}")
        return []


@api_router.post("/employees/{employee_id}/extract-from-application")
async def extract_from_application_form(
    employee_id: str,
    document_id: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Extract profile data from an uploaded application form.
    
    This extracts data into a REVIEW queue - values are NOT applied automatically.
    User must review and approve each field before it updates the profile.
    
    NOTE: This populates PROFILE fields only. It does NOT:
    - Complete compliance requirements
    - Provide evidence for NI number verification, address proof, etc.
    - Affect compliance calculations
    
    If extraction fails, returns extraction_failed=True with options for user.
    """
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find application form document
    query = {"employee_id": employee_id, "requirement_id": "application_form"}
    if document_id:
        query["id"] = document_id
    
    app_form_doc = await db.employee_documents.find_one(
        query,
        {"_id": 0},
        sort=[("uploaded_at", -1)]  # Get most recent
    )
    
    if not app_form_doc:
        # Also check generated_forms collection
        app_form = await db.generated_forms.find_one(
            {"employee_id": employee_id, "template_name": {"$regex": "Application", "$options": "i"}},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        if app_form and app_form.get('pdf_url'):
            doc_id = app_form['id']
            file_url = app_form['pdf_url']
        else:
            raise HTTPException(
                status_code=404, 
                detail="No application form found. Please upload an application form first."
            )
    else:
        doc_id = app_form_doc['id']
        file_url = app_form_doc.get('file_url')
        if not file_url:
            # Check evidence_files
            evidence_files = app_form_doc.get('evidence_files', [])
            if evidence_files:
                file_url = evidence_files[0].get('file_url')
    
    if not file_url:
        raise HTTPException(status_code=404, detail="Application form has no file attached")
    
    # Step 1: Extract text from document (with OCR fallback)
    logger.info(f"Extracting text from application form for employee {employee_id}")
    extracted_text, extraction_log = await extract_text_from_document(file_url)
    
    # Log extraction attempt details
    log_details = {
        "employee_id": employee_id,
        "document_id": doc_id,
        "file_type": extraction_log.file_type,
        "file_size_bytes": extraction_log.file_size_bytes,
        "ai_attempted": extraction_log.ai_extraction_attempted,
        "ai_success": extraction_log.ai_extraction_success,
        "ocr_attempted": extraction_log.ocr_attempted,
        "ocr_success": extraction_log.ocr_success,
        "final_method": extraction_log.final_method,
        "failure_reason": extraction_log.failure_reason
    }
    logger.info(f"Extraction log: {log_details}")
    
    # Store extraction log in DB for debugging
    await db.extraction_logs.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "document_id": doc_id,
        "file_url": file_url,
        **log_details,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Handle extraction failure gracefully - do NOT block the user
    if not extracted_text:
        return JSONResponse(
            status_code=200,  # Return 200 to prevent blocking error
            content={
                "extraction_failed": True,
                "employee_id": employee_id,
                "document_id": doc_id,
                "file_url": file_url,
                "message": "We couldn't automatically extract data from this document. You can still fill the form manually.",
                "extraction_log": {
                    "file_type": extraction_log.file_type,
                    "file_size_bytes": extraction_log.file_size_bytes,
                    "ai_attempted": extraction_log.ai_extraction_attempted,
                    "ocr_attempted": extraction_log.ocr_attempted,
                    "failure_reason": extraction_log.failure_reason
                },
                "options": [
                    {"action": "fill_manually", "label": "Fill form manually", "description": "Enter profile data manually"},
                    {"action": "view_document", "label": "View uploaded document", "description": "Open the document to reference while filling"},
                    {"action": "retry", "label": "Retry extraction", "description": "Try extracting again"}
                ]
            }
        )
    
    # Step 2: Parse text into structured fields
    logger.info(f"Parsing extracted text into profile fields for employee {employee_id}")
    extracted_fields, low_confidence_fields = await parse_extracted_text_to_fields(
        extracted_text, 
        employee_id,
        extraction_method=extraction_log.final_method or "unknown"
    )
    
    # Update extraction log with field info
    extraction_log.fields_extracted = len(extracted_fields)
    extraction_log.low_confidence_fields = low_confidence_fields
    
    if not extracted_fields:
        # Still don't block - return graceful failure with options
        return JSONResponse(
            status_code=200,
            content={
                "extraction_failed": True,
                "employee_id": employee_id,
                "document_id": doc_id,
                "file_url": file_url,
                "message": "We extracted text but couldn't identify profile fields. You can still fill the form manually.",
                "extraction_log": {
                    "file_type": extraction_log.file_type,
                    "file_size_bytes": extraction_log.file_size_bytes,
                    "extraction_method": extraction_log.final_method,
                    "text_extracted": True,
                    "fields_parsed": False
                },
                "options": [
                    {"action": "fill_manually", "label": "Fill form manually", "description": "Enter profile data manually"},
                    {"action": "view_document", "label": "View uploaded document", "description": "Open the document to reference while filling"},
                    {"action": "retry", "label": "Retry extraction", "description": "Try extracting again"}
                ]
            }
        )
    
    # Step 3: Save extraction result for review
    extraction_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    extraction_record = {
        "id": extraction_id,
        "employee_id": employee_id,
        "document_id": doc_id,
        "file_url": file_url,
        "fields": [f.model_dump() for f in extracted_fields],
        "extracted_text_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
        "extraction_method": extraction_log.final_method,
        "low_confidence_fields": low_confidence_fields,
        "ai_overall_confidence": extraction_log.ai_overall_confidence,
        "ocr_retry_reason": extraction_log.ocr_retry_reason,
        "status": "pending_review",
        "extracted_at": now,
        "extracted_by": user['user_id'],
        "extracted_by_name": user.get('name', user.get('email', 'Unknown')),
        "created_at": now,
        "updated_at": now
    }
    
    await db.profile_extractions.insert_one(extraction_record)
    
    await log_audit_action(
        user['user_id'],
        "extract_from_application",
        "employee",
        employee_id,
        {
            "extraction_id": extraction_id,
            "document_id": doc_id,
            "fields_count": len(extracted_fields),
            "low_confidence_count": len(low_confidence_fields),
            "extraction_method": extraction_log.final_method
        }
    )
    
    return {
        "extraction_id": extraction_id,
        "employee_id": employee_id,
        "document_id": doc_id,
        "fields": extracted_fields,
        "low_confidence_fields": low_confidence_fields,
        "extraction_method": extraction_log.final_method,
        "status": "pending_review",
        "message": "Extraction complete. Review fields below and apply selected values to profile.",
        "compliance_note": "Extracted values update PROFILE DATA only. They do NOT complete compliance evidence requirements."
    }


@api_router.get("/employees/{employee_id}/extractions")
async def get_employee_extractions(
    employee_id: str,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all extraction results for an employee"""
    query = {"employee_id": employee_id}
    if status:
        query["status"] = status
    
    extractions = await db.profile_extractions.find(
        query,
        {"_id": 0}
    ).sort("extracted_at", -1).to_list(50)
    
    return {"extractions": extractions}


@api_router.get("/extractions/{extraction_id}")
async def get_extraction(extraction_id: str, user: dict = Depends(get_current_user)):
    """Get a specific extraction result"""
    extraction = await db.profile_extractions.find_one(
        {"id": extraction_id},
        {"_id": 0}
    )
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    return extraction


@api_router.post("/extractions/{extraction_id}/apply")
async def apply_extraction(
    extraction_id: str,
    request: ApplyExtractionRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Apply selected extracted fields to employee profile.
    
    SUPPORTS PARTIAL UPDATES: Only the selected fields are updated.
    Each field is validated individually, allowing some to succeed even if others fail.
    
    IMPORTANT: This updates PROFILE DATA only. It does NOT:
    - Mark any compliance requirements as complete
    - Provide evidence for document requirements
    - Affect compliance percentage calculations
    
    Example: Extracting NI number populates the profile field,
    but "Proof of NI Number" remains a separate evidence requirement.
    """
    extraction = await db.profile_extractions.find_one(
        {"id": extraction_id},
        {"_id": 0}
    )
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    if extraction['status'] != 'pending_review':
        raise HTTPException(
            status_code=400, 
            detail=f"Extraction already processed (status: {extraction['status']})"
        )
    
    employee_id = extraction['employee_id']
    fields_to_apply = request.fields_to_apply
    
    if not fields_to_apply:
        raise HTTPException(status_code=400, detail="No fields selected to apply")
    
    # Build update dict from selected fields with validation
    update_data = {}
    applied_fields = []
    failed_fields = []
    unsupported_fields = []
    
    for field_data in extraction['fields']:
        field_name = field_data['field_name']
        if field_name not in fields_to_apply:
            continue
            
        extracted_value = field_data.get('extracted_value')
        if not extracted_value:
            continue
        
        # Check if field is in supported list
        if field_name not in EXTRACTABLE_PROFILE_FIELDS:
            unsupported_fields.append({
                "field": field_name,
                "reason": "Field not in supported profile schema"
            })
            continue
        
        try:
            value = extracted_value
            
            # Type conversion for boolean fields
            boolean_fields = ['has_driving_licence', 'has_own_vehicle', 'driver_status',
                             'working_time_opt_out', 'dbs_update_service_consent',
                             'criminal_offence_declared', 'professional_misconduct_declared',
                             'health_issue_declared']
            
            if field_name in boolean_fields:
                if isinstance(value, str):
                    # Convert common string values to boolean
                    value_lower = value.lower().strip()
                    if value_lower in ['true', 'yes', '1', 'y']:
                        value = True
                    elif value_lower in ['false', 'no', '0', 'n']:
                        value = False
                    else:
                        # Keep as string for human-readable declarations
                        value = value
                else:
                    value = bool(value)
            
            # Validate specific field formats
            if field_name == 'ni_number' and value:
                # Clean NI number format
                clean_ni = value.upper().replace(' ', '').replace('-', '')
                if len(clean_ni) == 9:
                    value = clean_ni
            
            if field_name == 'postcode' and value:
                # Normalize postcode format
                value = value.upper().strip()
            
            if field_name == 'email' and value:
                # Normalize email
                value = value.lower().strip()
            
            update_data[field_name] = value
            applied_fields.append({
                "field": field_name,
                "value": value,
                "previous": field_data.get('current_value')
            })
            
        except Exception as field_error:
            failed_fields.append({
                "field": field_name,
                "reason": str(field_error),
                "attempted_value": str(extracted_value)[:100]
            })
    
    # Proceed with save even if some fields failed (partial success)
    if not update_data and not applied_fields:
        if unsupported_fields:
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "No valid fields to apply",
                    "unsupported_fields": unsupported_fields,
                    "failed_fields": failed_fields
                }
            )
        raise HTTPException(status_code=400, detail="No valid fields to apply")
    
    # Update employee profile with partial data
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    try:
        result = await db.employees.update_one(
            {"id": employee_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Employee not found")
            
    except Exception as db_error:
        logger.error(f"Database update failed: {db_error}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to save profile updates",
                "error": str(db_error),
                "applied_fields_attempted": [f["field"] for f in applied_fields]
            }
        )
    
    # Mark extraction as applied
    await db.profile_extractions.update_one(
        {"id": extraction_id},
        {"$set": {
            "status": "applied",
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "applied_by": user['user_id'],
            "applied_by_name": user.get('name', user.get('email', 'Unknown')),
            "applied_fields": applied_fields,
            "failed_fields": failed_fields,
            "unsupported_fields": unsupported_fields,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_audit_action(
        user['user_id'],
        "apply_extraction",
        "employee",
        employee_id,
        {
            "extraction_id": extraction_id,
            "applied_fields": applied_fields,
            "failed_fields": failed_fields
        }
    )
    
    response = {
        "success": True,
        "message": f"Successfully applied {len(applied_fields)} field(s) to profile",
        "applied_fields": applied_fields,
        "compliance_note": "Profile data updated. Compliance evidence requirements remain unchanged."
    }
    
    # Add warnings if some fields failed
    if failed_fields:
        response["warnings"] = {
            "failed_fields": failed_fields,
            "message": f"{len(failed_fields)} field(s) could not be applied"
        }
    
    if unsupported_fields:
        response["unsupported"] = {
            "fields": unsupported_fields,
            "message": f"{len(unsupported_fields)} field(s) not supported in profile schema"
        }
    
    return response


@api_router.post("/extractions/{extraction_id}/discard")
async def discard_extraction(
    extraction_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Discard an extraction without applying any values"""
    extraction = await db.profile_extractions.find_one(
        {"id": extraction_id},
        {"_id": 0}
    )
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    await db.profile_extractions.update_one(
        {"id": extraction_id},
        {"$set": {
            "status": "discarded",
            "discarded_at": datetime.now(timezone.utc).isoformat(),
            "discarded_by": user['user_id'],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Extraction discarded"}


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
    
    # Generate verification stamp using helper function (reuses existing verified fields)
    verification_stamp = generate_verification_stamp(
        verified_by=verified_by,
        verified_at=datetime.now(timezone.utc).isoformat(),
        document_type="Employee Compliance Summary",
        include_hash=True,
        content_bytes=f"{employee_id}{compliance['completion_percentage']}{verified}".encode()
    )
    
    # Add verification stamp footer
    stamp_footer = create_verification_footer_elements(verification_stamp, styles)
    elements.extend(stamp_footer)
    
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
        # For training, use SINGLE SOURCE OF TRUTH - training_records collection
        training_name = requirement.get('training_name', requirement['name'])
        
        # Get or create the SINGLE ACTIVE training record for this employee+requirement
        existing = await db.training_records.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "record_status": {"$nin": ["superseded", "deleted"]}
        }, {"_id": 0})
        
        # Also check by training name if not found by requirement_id
        if not existing:
            existing = await db.training_records.find_one({
                "employee_id": employee_id,
                "training_name": {"$regex": f"^{re.escape(training_name)}$", "$options": "i"},
                "record_status": {"$nin": ["superseded", "deleted"]}
            }, {"_id": 0})
        
        # Calculate expiry from completion date if not provided
        calculated_expiry = expiry_date
        if not calculated_expiry:
            calculated_expiry = calculate_training_expiry(now, requirement_id)
        
        if existing:
            # Add to existing evidence files (SINGLE record, multiple evidence files OK)
            evidence_files = existing.get('evidence_files', [])
            
            # Migrate old certificate_url to evidence_files if needed
            if existing.get('certificate_url') and not evidence_files:
                evidence_files.append({
                    "file_id": str(uuid.uuid4()),
                    "file_url": existing['certificate_url'],
                    "original_filename": existing.get('original_filename', 'certificate'),
                    "uploaded_at": existing.get('uploaded_at', existing.get('created_at')),
                    "source_type": "migrated",
                    "status": "active"
                })
            
            evidence_files.append(evidence_file)
            
            # Update the SINGLE training record
            # HARDENING: Store only canonical fields, NOT derived status
            await db.training_records.update_one(
                {"id": existing['id']},
                {"$set": {
                    "evidence_files": evidence_files,
                    "certificate_url": result["path"],  # Keep for backward compat
                    "original_filename": file.filename,
                    "uploaded_at": now,
                    # REMOVED: "status": "completed" - derived at runtime from completion_date/expiry_date
                    "record_status": "active",  # Ensure active
                    "completion_date": now,
                    "completion_method": "certificate",
                    "requirement_id": requirement_id,
                    "updated_at": now,
                    "expiry_date": calculated_expiry
                }}
            )
            record_id = existing['id']
            
            # Log the update
            await log_audit_action(user['user_id'], "training_evidence_added", "training_record", record_id, {
                "training_name": training_name,
                "requirement_id": requirement_id,
                "filename": file.filename,
                "expiry_date": calculated_expiry,
                "action": "added_evidence"
            })
        else:
            # Create new training record (SINGLE ACTIVE record)
            # HARDENING: Store only canonical fields, NOT derived status
            record_id = str(uuid.uuid4())
            new_record = {
                "id": record_id,
                "employee_id": employee_id,
                "training_name": training_name,
                "mandatory": True,
                # REMOVED: "status": "completed" - derived at runtime from completion_date/expiry_date
                "record_status": "active",  # SINGLE ACTIVE record
                "completion_date": now,
                "expiry_date": calculated_expiry,
                "certificate_url": result["path"],
                "original_filename": file.filename,
                "uploaded_at": now,
                "evidence_files": [evidence_file],
                "verified": False,
                "completion_method": "certificate",
                "requirement_id": requirement_id,
                "created_at": now,
                "updated_at": now
            }
            await db.training_records.insert_one(new_record)
            
            # Log the creation
            await log_audit_action(user['user_id'], "training_record_created", "training_record", record_id, {
                "training_name": training_name,
                "requirement_id": requirement_id,
                "filename": file.filename,
                "expiry_date": calculated_expiry,
                "action": "created_with_evidence"
            })
        
        # Update compliance for this employee
        await update_employee_compliance(employee_id)
    
    else:
        # For documents/form-generated, create/update employee_documents
        # Check for existing ACTIVE document for this requirement
        # BUGFIX: Exclude superseded/archived documents to prevent updating them
        # while compliance queries filter them out (causing "silent success" bug)
        existing = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "requirement_id": requirement_id,
            "status": {"$nin": ["superseded", "archived", "deleted"]}
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
        # HARDENING: Exclude superseded/deleted training records
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "record_status": {"$nin": ["superseded", "deleted"]},
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
        
        # HARDENING: Exclude superseded/archived documents
        docs = await db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": {"$in": req_ids_to_search},
            "status": {"$nin": ["superseded", "archived", "deleted"]}
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


class DeleteFileRequest(BaseModel):
    """Request to permanently delete a file with audit trail"""
    reason: Optional[str] = None  # Optional reason for deletion


@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/evidence/{file_id}/delete")
async def delete_requirement_evidence_permanently(
    employee_id: str,
    requirement_id: str,
    file_id: str,
    request: DeleteFileRequest = DeleteFileRequest(),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Permanently delete an evidence file from active use.
    - Removes from active requirement immediately
    - Removes from compliance calculation
    - Removes from verification flow
    - Keeps audit trail with file details
    """
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
    
    deleted_file_info = None
    
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
            # Get file info before deletion for audit
            for f in record.get('evidence_files', []):
                if f.get('file_id') == file_id:
                    deleted_file_info = {
                        "filename": f.get('original_filename') or f.get('filename'),
                        "file_id": file_id,
                        "uploaded_at": f.get('uploaded_at'),
                        "file_url": f.get('url')
                    }
                    break
            
            evidence_files = [f for f in record.get('evidence_files', []) if f.get('file_id') != file_id]
            update_data = {"evidence_files": evidence_files, "updated_at": now}
            
            # If no more evidence files, reset the record
            # HARDENING: Clear completion_date instead of writing derived status
            if not evidence_files:
                update_data["certificate_url"] = None
                update_data["completion_method"] = "manual"
                update_data["verified"] = False
                update_data["completion_date"] = None  # Reset to derive "not_started" status
                # REMOVED: "status": "not_started" - derived from completion_date being None
            
            await db.training_records.update_one(
                {"id": record['id']},
                {"$set": update_data}
            )
    else:
        # Find document record
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "$or": [
                {"id": file_id},
                {"evidence_files.file_id": file_id}
            ]
        }, {"_id": 0})
        
        if doc:
            # Get file info before deletion for audit
            for f in doc.get('evidence_files', []):
                if f.get('file_id') == file_id:
                    deleted_file_info = {
                        "filename": f.get('original_filename') or f.get('filename'),
                        "file_id": file_id,
                        "uploaded_at": f.get('uploaded_at'),
                        "file_url": f.get('url')
                    }
                    break
            
            # If no file info found, it might be the main document
            if not deleted_file_info:
                deleted_file_info = {
                    "filename": doc.get('original_filename') or doc.get('file_name'),
                    "file_id": file_id,
                    "uploaded_at": doc.get('uploaded_at'),
                    "file_url": doc.get('file_url')
                }
            
            evidence_files = [f for f in doc.get('evidence_files', []) if f.get('file_id') != file_id]
            
            if not evidence_files and (doc['id'] == file_id or len(doc.get('evidence_files', [])) <= 1):
                # Delete the entire document record if this was the only file
                await db.employee_documents.delete_one({"id": doc['id']})
            else:
                # Just remove the file from evidence_files
                update_data = {
                    "evidence_files": evidence_files, 
                    "updated_at": now,
                    "verified": False  # Reset verification when file is deleted
                }
                await db.employee_documents.update_one(
                    {"id": doc['id']},
                    {"$set": update_data}
                )
        else:
            # Not found in employee_documents - check if it's a form submission
            # Form submissions use the submission ID as the file_id
            submission = await db.form_submissions.find_one({
                "employee_id": employee_id,
                "id": file_id
            }, {"_id": 0})
            
            if submission:
                deleted_file_info = {
                    "filename": f"{submission.get('template_name', 'Form')} (Form Submission)",
                    "file_id": file_id,
                    "uploaded_at": submission.get('submitted_at') or submission.get('created_at'),
                    "file_url": None,
                    "source_type": "form_submission"
                }
                
                # Archive the form submission (soft delete)
                await db.form_submissions.update_one(
                    {"id": file_id},
                    {"$set": {
                        "status": "deleted",
                        "deleted_at": now,
                        "deleted_by": user['user_id'],
                        "deleted_reason": request.reason.strip() if request.reason else None
                    }}
                )
                
                # Also remove any associated PDF exports
                await db.form_pdf_exports.update_many(
                    {"submission_id": file_id},
                    {"$set": {"deleted_at": now}}
                )
    
    # Create detailed audit log entry
    audit_metadata = {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "requirement_id": requirement_id,
        "requirement_name": requirement.get('name', requirement_id),
        "deleted_by": user_name,
        "deleted_at": now,
        "action_type": "permanent_delete"
    }
    
    if deleted_file_info:
        audit_metadata["filename"] = deleted_file_info.get("filename")
        audit_metadata["original_file_id"] = deleted_file_info.get("file_id")
        audit_metadata["original_uploaded_at"] = deleted_file_info.get("uploaded_at")
    
    if request.reason:
        audit_metadata["reason"] = request.reason.strip()
    
    await log_audit_action(
        user['user_id'], 
        "file_deleted", 
        "requirement", 
        requirement_id,
        audit_metadata
    )
    
    # Update compliance calculation
    await update_employee_compliance(employee_id)
    
    return {
        "success": True, 
        "message": "File permanently deleted",
        "deleted_file": deleted_file_info
    }


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
                
                # HARDENING: If no active files remain, reset the training record
                if not active_files:
                    update_data["verified"] = False
                    update_data["completion_method"] = "manual"
                    update_data["completion_date"] = None  # Reset so status derives to "not_started"
                    update_data["certificate_url"] = None
                
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
    
    await log_audit_action(user['user_id'], "document_verified", "requirement", requirement_id,
                           {
                               "employee_id": employee_id,
                               "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
                               "requirement_name": requirement['name'],
                               "verified_by_name": verified_by_name,
                               "verified_at": now
                           })
    
    await update_employee_compliance(employee_id)
    
    return {"success": True, "message": f"'{requirement['name']}' verified", "verified": True}


@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/acknowledge")
async def acknowledge_requirement(
    employee_id: str,
    requirement_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Submit an acknowledgement for a requirement (Contract, Handbook, etc.)
    Does not require file upload - just confirmation that employee has read/understood.
    Automatically marks the requirement as completed AND verified.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    all_items = get_mandatory_items_for_role(employee.get('role', ''))
    requirement = next((item for item in all_items if item['id'] == requirement_id), None)
    
    if not requirement:
        raise HTTPException(status_code=400, detail=f"Invalid requirement_id: {requirement_id}")
    
    if requirement.get('type') != 'acknowledgement':
        raise HTTPException(status_code=400, detail="This requirement does not support acknowledgement. Use upload instead.")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if already acknowledged
    existing = await db.requirement_acknowledgements.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id
    })
    
    if existing and existing.get('acknowledged'):
        return {"success": True, "message": f"'{requirement['name']}' already acknowledged", "acknowledged": True}
    
    # Create or update acknowledgement record
    ack_id = existing['id'] if existing else str(uuid.uuid4())
    ack_record = {
        "id": ack_id,
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "requirement_name": requirement['name'],
        "acknowledged": True,
        "acknowledged_at": now,
        "acknowledged_by": user['user_id'],
        "acknowledged_by_name": user['name'],
        "acknowledgement_text": requirement.get('acknowledgement_text', ''),
        "created_at": existing.get('created_at', now) if existing else now,
        "updated_at": now
    }
    
    await db.requirement_acknowledgements.update_one(
        {"employee_id": employee_id, "requirement_id": requirement_id},
        {"$set": ack_record},
        upsert=True
    )
    
    # Log audit action
    await log_audit_action(
        user['user_id'], 
        "acknowledgement_completed", 
        "requirement", 
        requirement_id,
        {
            "employee_id": employee_id,
            "employee_name": f"{employee['first_name']} {employee['last_name']}",
            "requirement_name": requirement['name'],
            "acknowledged_by": user['name'],
            "acknowledged_at": now
        }
    )
    
    return {
        "success": True, 
        "message": f"'{requirement['name']}' acknowledged and completed",
        "acknowledged": True,
        "acknowledged_at": now,
        "acknowledged_by": user['name']
    }


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
    
    # Check for existing ACTIVE document with same requirement_id to prevent duplicates
    # BUGFIX: Exclude superseded/archived documents to prevent updating them
    if requirement_id:
        existing_doc = await db.employee_documents.find_one({
            "employee_id": doc.employee_id,
            "requirement_id": requirement_id,
            "status": {"$nin": ["superseded", "archived", "deleted"]}
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
    
    # Get all training records - ENRICH WITH COMPUTED STATUS (SINGLE SOURCE OF TRUTH)
    # HARDENING: Exclude superseded/deleted records from compliance calculations
    raw_training = await db.training_records.find({
        "employee_id": employee_id,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0}).to_list(100)
    all_training = [enrich_training_record_with_computed_status(t) for t in raw_training]
    
    # Get all acknowledgements for this employee
    all_acknowledgements = await db.requirement_acknowledgements.find({
        "employee_id": employee_id
    }, {"_id": 0}).to_list(100)
    
    requirements = []
    completed_count = 0
    verified_count = 0
    evidence_backed_count = 0
    optional_count = 0  # Track optional items to exclude from total
    
    # Track conditional requirements for summary info
    conditional_not_required = []
    
    for item in mandatory_items:
        req_id = item['id']
        req_type = item.get('type', 'document')
        allow_multiple = item.get('allow_multiple_files', True)  # Default to True now
        min_files = item.get('min_files', 1)
        source = item.get('source', 'employee')
        priority = item.get('priority', 'secondary')
        priority_order = item.get('priority_order', 99)
        work_ready_hint = item.get('work_ready_hint', '')
        is_optional = item.get('optional', False)
        
        # ======== Skip archived requirements (hide from UI, preserve historical data) ========
        if item.get('archived', False):
            continue
        
        # ======== Handle Conditional Requirements ========
        # Check if this item has a conditional dependency (e.g., HMRC form depends on P45 absence)
        conditional_on = item.get('conditional_on')
        conditional_inverse = item.get('conditional_inverse', False)
        
        if conditional_on:
            # Check if the conditional document exists for this employee
            # Look for documents where document_type or requirement_id matches the conditional_on value
            condition_met = False
            for doc in all_docs:
                doc_type = (doc.get('document_type') or '').lower()
                doc_type_name = (doc.get('document_type_name') or '').lower()
                doc_req_id = (doc.get('requirement_id') or '').lower()
                
                # Check if this document matches the conditional_on value
                if conditional_on.lower() in [doc_type, doc_type_name, doc_req_id]:
                    condition_met = True
                    break
                # Also check if the document_type_name contains the conditional value
                if conditional_on.lower() in doc_type_name:
                    condition_met = True
                    break
            
            # Apply conditional logic
            # conditional_inverse=True means: required when condition is NOT met (e.g., HMRC required if NO P45)
            # conditional_inverse=False means: required when condition IS met
            if conditional_inverse:
                # Required when condition is NOT met (P45 absent = HMRC required)
                if condition_met:
                    # P45 exists, so HMRC is NOT required - skip this item
                    conditional_not_required.append({
                        "id": req_id,
                        "name": item['name'],
                        "reason": f"Not required because {conditional_on.upper()} document exists"
                    })
                    continue
            else:
                # Required when condition IS met
                if not condition_met:
                    # Condition not met, skip this item
                    conditional_not_required.append({
                        "id": req_id,
                        "name": item['name'],
                        "reason": f"Not required because {conditional_on.upper()} document is missing"
                    })
                    continue
        
        # Track optional items
        if is_optional:
            optional_count += 1
        
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
            "completion_method": None,  # NEW: "evidence" or "manual" or "form" or "acknowledgement"
            # Work Readiness fields
            "priority": priority,
            "priority_order": priority_order,
            "priority_label": PRIORITY_CONFIG.get(priority, {}).get('label', 'Complete After Start'),
            "priority_color": PRIORITY_CONFIG.get(priority, {}).get('color', 'yellow'),
            "work_ready_hint": work_ready_hint,
            "is_mandatory_for_work": req_id in WORK_READY_REQUIREMENTS or priority == 'mandatory',
            # Optional flag
            "optional": is_optional,
            # Acknowledgement fields
            "acknowledgement_text": item.get('acknowledgement_text', ''),
            "acknowledged": False,
            "acknowledged_at": None,
            "acknowledged_by": None
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
                        # HARDENING: Skip removed/superseded files - only include active files
                        file_status = ef.get('status', 'active')
                        if file_status not in ['active', None]:
                            continue  # Skip removed/superseded/archived files
                        
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
                            "expiry_status": calculate_expiry_status(file_expiry) if file_expiry else None,
                            "status": "active"  # Explicitly mark as active
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
                        "expiry_status": calculate_expiry_status(doc_expiry_date) if doc_expiry_date else None,
                        "status": "active"  # HARDENING: Explicitly mark as active
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
                            "verified": False,  # Forms need separate verification
                            "status": "active"  # HARDENING: Explicitly mark as active
                        })
            
            # NEW: Check for structured form submissions (from form_submissions collection)
            form_submission = await db.form_submissions.find_one({
                "employee_id": employee_id,
                "requirement_id": req_id,
                "status": {"$nin": ["deleted", "superseded"]}
            }, {"_id": 0})
            
            if form_submission:
                # Check for PDF export
                pdf_export = await db.form_pdf_exports.find_one({
                    "submission_id": form_submission['id']
                }, {"_id": 0}, sort=[("created_at", -1)])
                
                req['form_submission'] = {
                    "id": form_submission['id'],
                    "status": form_submission['status'],
                    "submitted_at": form_submission.get('submitted_at'),
                    "submitted_by_name": form_submission.get('submitted_by_name'),
                    "verified": form_submission.get('verified', False),
                    "verified_by_name": form_submission.get('verified_by_name'),
                    "verified_at": form_submission.get('verified_at'),
                    "data": form_submission.get('data', {}),
                    # PDF export info for button state
                    "has_pdf_export": pdf_export is not None,
                    "pdf_export_url": pdf_export.get('file_url') if pdf_export else None,
                    "pdf_export_filename": pdf_export.get('filename') if pdf_export else None,
                    "pdf_export_created_at": pdf_export.get('created_at') if pdf_export else None
                }
                
                # Form submission counts as evidence
                evidence_files.append({
                    "file_id": form_submission['id'],
                    "file_url": None,  # No file URL - it's structured data
                    "original_filename": f"{item['name']} (Form)",
                    "uploaded_at": form_submission.get('submitted_at'),
                    "uploaded_by_name": form_submission.get('submitted_by_name'),
                    "source_type": "structured_form",
                    "file_label": f"Submitted {item['name']}",
                    "verified": form_submission.get('verified', False),
                    "status": "active"  # HARDENING: Explicitly mark as active
                })
                
                # Update verified status if form is verified
                if form_submission.get('verified'):
                    req['verified'] = True
                    req['verified_by'] = form_submission.get('verified_by_name')
                    req['verified_at'] = form_submission.get('verified_at')
        
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
                
                # Extract evidence files from training - FILTER TO ACTIVE ONLY
                if linked_training.get('evidence_files'):
                    for ef in linked_training['evidence_files']:
                        # HARDENING: Skip removed/superseded files - only include active files
                        file_status = ef.get('status', 'active')
                        if file_status not in ['active', None]:
                            continue  # Skip removed/superseded/archived files
                        
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
                            "expiry_status": calculate_expiry_status(file_expiry) if file_expiry else None,
                            "status": "active"  # Explicitly mark as active
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
                        "expiry_status": calculate_expiry_status(training_expiry_date) if training_expiry_date else None,
                        "status": "active"  # HARDENING: Explicitly mark as active
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
                    "has_evidence": bool(evidence_files),
                    # COMPUTED STATUS FIELDS - SINGLE SOURCE OF TRUTH
                    "computed_status": linked_training.get('computed_status'),
                    "renewal_status": linked_training.get('renewal_status'),
                    "days_until_expiry": linked_training.get('days_until_expiry'),
                    "status_label": linked_training.get('status_label'),
                    "status_color": linked_training.get('status_color')
                }
                
                if linked_training.get('verified') and evidence_files:
                    req['verified'] = True
                    req['verified_by'] = linked_training.get('verified_by')
                    req['verified_at'] = linked_training.get('verified_at')
        
        # ======== Handle Acknowledgements ========
        if req_type == 'acknowledgement':
            # Find acknowledgement for this requirement
            linked_ack = None
            for ack in all_acknowledgements:
                if ack.get('requirement_id') == req_id:
                    linked_ack = ack
                    break
            
            if linked_ack and linked_ack.get('acknowledged'):
                req['acknowledged'] = True
                req['acknowledged_at'] = linked_ack.get('acknowledged_at')
                req['acknowledged_by'] = linked_ack.get('acknowledged_by_name')
                req['has_evidence'] = True  # Acknowledgement counts as evidence
                req['verified'] = True  # Acknowledgements are auto-verified
                req['verified_at'] = linked_ack.get('acknowledged_at')
                req['verified_by'] = linked_ack.get('acknowledged_by_name')
        
        # ======== Calculate Status (EVIDENCE-BASED) ========
        req['evidence_files'] = evidence_files
        req['evidence_count'] = len(evidence_files)
        req['has_evidence'] = len(evidence_files) > 0 or req.get('acknowledged', False)
        req['can_verify'] = req['has_evidence'] and not req['verified']
        
        # Skip optional items from compliance counts
        is_optional = req.get('optional', False)
        
        if req.get('acknowledged'):
            # Acknowledgement type - marked complete and verified when acknowledged
            req['status'] = 'completed'
            req['completion_method'] = 'acknowledgement'
            if not is_optional:
                completed_count += 1
                evidence_backed_count += 1
                verified_count += 1  # Acknowledgements auto-verify
        elif evidence_files:
            # Has evidence = complete
            req['status'] = 'completed'
            req['completion_method'] = 'evidence'
            if not is_optional:
                completed_count += 1
                evidence_backed_count += 1
            
            if req['verified'] and not is_optional:
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
                if not is_optional:
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
    
    total_count = len(requirements) - optional_count  # Exclude optional items from total
    # EVIDENCE-BASED SCORING: Only evidence-backed completions count
    completion_percentage = int((evidence_backed_count / total_count) * 100) if total_count > 0 else 0
    verification_percentage = int((verified_count / evidence_backed_count) * 100) if evidence_backed_count > 0 else 0
    
    # Fetch policies data for the employee - using policy_assignments collection
    # Only count active assignments (not unassigned or withdrawn)
    assigned_policies = await db.policy_assignments.find({
        "employee_id": employee_id,
        "status": {"$nin": ["unassigned", "withdrawn"]}
    }, {"_id": 0, "status": 1, "acknowledged_at": 1}).to_list(100)
    
    policies_assigned = len(assigned_policies)
    # Count acknowledged - support both old 'signed' status and new 'acknowledged' status
    policies_acknowledged = sum(1 for p in assigned_policies if p.get('status') in ['acknowledged', 'signed'])
    
    policies_data = {
        "assigned": policies_assigned,
        "acknowledged": policies_acknowledged
    }
    
    # Calculate Work Readiness
    work_readiness = calculate_work_readiness(requirements, role)
    
    # Calculate Separated Statuses (new model)
    separated_statuses = calculate_separated_statuses(requirements, role, policies_data)
    
    result = {
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
        "statuses": separated_statuses,  # New separated status model
        "expiry_alerts": {
            "expiring_soon": expiring_soon_items,
            "expired": expired_items,
            "expiring_soon_count": len(expiring_soon_items),
            "expired_count": len(expired_items),
            "has_alerts": len(expiring_soon_items) > 0 or len(expired_items) > 0
        },
        # DBS Summary - computed from single source (SAFETY ENGINE)
        "dbs_summary": await get_employee_dbs_summary(employee_id),
        # RTW Summary - computed from single source (SAFETY ENGINE)
        "rtw_summary": await get_employee_rtw_summary(employee_id),
        # Training Summary - computed from single source (SAFETY ENGINE)
        "training_summary": await get_employee_training_safety_summary(employee_id),
        # Conditional requirements that were excluded
        "conditional_not_required": conditional_not_required
    }
    
    # === SAFETY ENGINE: Derive is_work_ready from blocking engines ===
    dbs_blocking = result["dbs_summary"].get("is_blocking", False)
    rtw_blocking = result["rtw_summary"].get("is_blocking", False)
    training_blocking = result["training_summary"].get("is_blocking", False)
    
    any_blocking = dbs_blocking or rtw_blocking or training_blocking
    
    # Build blocking reasons list
    blocking_reasons = []
    if dbs_blocking:
        blocking_reasons.append(result["dbs_summary"].get("blocking_reason"))
    if rtw_blocking:
        blocking_reasons.append(result["rtw_summary"].get("blocking_reason"))
    if training_blocking:
        blocking_reasons.append(result["training_summary"].get("blocking_reason"))
    
    # Override is_work_ready based on safety engines
    # Original logic: all_mandatory_verified
    # New logic: all_mandatory_verified AND no blocking engines
    original_work_ready = result["statuses"]["is_work_ready"]
    safety_work_ready = not any_blocking
    
    result["statuses"]["is_work_ready"] = original_work_ready and safety_work_ready
    result["statuses"]["safety_blocking"] = any_blocking
    result["statuses"]["safety_blocking_reasons"] = blocking_reasons
    
    # Add overall safety status for easy consumption
    result["safety_status"] = {
        "is_safe_to_deploy": not any_blocking,
        "dbs_blocking": dbs_blocking,
        "rtw_blocking": rtw_blocking,
        "training_blocking": training_blocking,
        "blocking_reasons": blocking_reasons,
        "summary": "Ready to Work" if not any_blocking else blocking_reasons[0] if blocking_reasons else "Safety check failed"
    }
    
    # === REFERENCE INTEGRITY CHECK ===
    reference_integrity = check_all_references_integrity(employee)
    result["reference_integrity"] = reference_integrity
    
    # === CV GAP ANALYSIS CHECK ===
    cv_gaps_status = check_cv_gaps_complete(employee)
    result["cv_gaps_status"] = cv_gaps_status
    
    # Add recruitment blocking reasons
    recruitment_blockers = []
    if not reference_integrity["can_complete_recruitment"]:
        recruitment_blockers.extend(reference_integrity["errors"])
    if not cv_gaps_status["can_complete_recruitment"]:
        recruitment_blockers.append(f"{len(cv_gaps_status['unexplained_gaps'])} unexplained employment gap(s)")
    
    result["recruitment_status"] = {
        "can_complete": len(recruitment_blockers) == 0,
        "blockers": recruitment_blockers,
        "reference_issues": reference_integrity["errors"],
        "cv_gap_issues": cv_gaps_status["unexplained_gaps"]
    }
    
    return result

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


# ==================== FORM SUBMISSION ROUTES ====================
# Structured in-system forms (Health Screening, Induction, Interview Record, etc.)

@api_router.get("/form-submissions/templates")
async def get_form_templates(user: dict = Depends(get_current_user)):
    """Get available form templates for structured forms"""
    templates = []
    for req_id, config in FORM_BASED_REQUIREMENTS.items():
        templates.append({
            "requirement_id": req_id,
            "name": config["name"],
            "form_type": config["form_type"],
            "fields": config["fields"]
        })
    return templates


@api_router.get("/form-submissions/template/{requirement_id}")
async def get_form_template(requirement_id: str, user: dict = Depends(get_current_user)):
    """Get a specific form template"""
    if requirement_id not in FORM_BASED_REQUIREMENTS:
        raise HTTPException(status_code=404, detail="Form template not found")
    
    config = FORM_BASED_REQUIREMENTS[requirement_id]
    
    # Return sections if available, otherwise fallback to flat fields
    return {
        "requirement_id": requirement_id,
        "name": config["name"],
        "form_type": config["form_type"],
        "description": config.get("description"),
        "is_optional": config.get("is_optional", False),
        "is_conditional": config.get("is_conditional", False),
        "updates_profile": config.get("updates_profile", False),
        "auto_fill_fields": config.get("auto_fill_fields", []),
        "branding": config.get("branding"),  # Include branding for styled forms
        "sections": config.get("sections", []),
        "fields": config.get("fields", [])  # Backward compatibility
    }


@api_router.get("/form-submissions/auto-fill/{requirement_id}/{employee_id}")
async def get_form_auto_fill_data(
    requirement_id: str,
    employee_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get auto-fill data for a form from employee profile.
    
    This pre-fills form fields from existing employee profile data.
    Does NOT write any data - just provides suggested values.
    
    Forms that support auto-fill:
    - Health Screening: name, address, phone, email, job title
    - Staff Personal Info: all non-sensitive profile fields
    - HMRC Starter Checklist: name, address, NI number, DOB, start date
    - Recruitment Checklist: employee name, position
    - Induction: employee name, job title, start date
    - Interview Record: candidate name, position
    
    Medical answers, identity/DBS verifications, and equality data
    are NEVER auto-filled - these must be explicitly entered.
    """
    if requirement_id not in FORM_BASED_REQUIREMENTS:
        raise HTTPException(status_code=404, detail="Form template not found")
    
    # Get employee data
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    config = FORM_BASED_REQUIREMENTS[requirement_id]
    auto_fill_fields = config.get("auto_fill_fields", [])
    
    # Build auto-fill data map
    auto_fill_data = {}
    
    # Helper to build full address
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
    
    # Helper to build full name
    def build_full_name():
        parts = [
            employee.get("first_name"),
            employee.get("middle_name"),
            employee.get("last_name")
        ]
        return " ".join(filter(None, parts))
    
    # Helper to build next of kin full address
    def build_nok_address():
        parts = [
            employee.get("next_of_kin_address_line_1") or employee.get("next_of_kin_address"),
            employee.get("next_of_kin_city"),
            employee.get("next_of_kin_county"),
            employee.get("next_of_kin_postcode"),
            employee.get("next_of_kin_country")
        ]
        return ", ".join(filter(None, parts))
    
    # Map auto-fill field IDs to employee data
    field_value_map = {
        "full_name": build_full_name(),
        "first_name": employee.get("first_name"),
        "middle_name": employee.get("middle_name"),
        "last_name": employee.get("last_name"),
        "title": employee.get("title"),
        "date_of_birth": employee.get("date_of_birth"),
        "job_title": employee.get("role"),
        "role": employee.get("role"),
        "position": employee.get("role"),
        "full_address": build_full_address(),
        "address": build_full_address(),
        "address_line_1": employee.get("address_line_1"),
        "address_line_2": employee.get("address_line_2"),
        "city": employee.get("city"),
        "county": employee.get("county"),
        "postcode": employee.get("postcode"),
        "country": employee.get("country"),
        "phone": employee.get("phone"),
        "contact_number": employee.get("phone"),  # For Staff Health Questionnaire
        "phone_primary": employee.get("phone"),
        "phone_secondary": employee.get("phone_secondary"),
        "email": employee.get("email"),
        "ni_number": employee.get("ni_number"),
        "start_date": employee.get("start_date"),
        "employment_start_date": employee.get("start_date"),
        "marital_status": employee.get("marital_status"),
        # Health-related fields from extraction
        "flu_vaccination_date": employee.get("flu_vaccination_date"),
        # Next of kin / Emergency contact
        "next_of_kin_name": employee.get("next_of_kin_name") or employee.get("emergency_contact_name"),
        "emergency_name": employee.get("next_of_kin_name") or employee.get("emergency_contact_name"),
        "next_of_kin_relationship": employee.get("next_of_kin_relationship") or employee.get("emergency_contact_relationship"),
        "emergency_relationship": employee.get("next_of_kin_relationship") or employee.get("emergency_contact_relationship"),
        "next_of_kin_phone": employee.get("next_of_kin_phone") or employee.get("emergency_contact_phone"),
        "emergency_phone": employee.get("next_of_kin_phone") or employee.get("emergency_contact_phone"),
        "next_of_kin_address": build_nok_address(),
        "emergency_address": build_nok_address(),
        # Driving
        "has_driving_licence": "Yes" if employee.get("has_driving_licence") else "No" if employee.get("has_driving_licence") == False else None,
        "driving_licence_number": employee.get("driving_licence_number"),
        "has_own_vehicle": "Yes" if employee.get("has_own_vehicle") else "No" if employee.get("has_own_vehicle") == False else None,
        "vehicle_registration": employee.get("vehicle_registration"),
        "vehicle_make_model": employee.get("vehicle_make_model"),
        # For interview/recruitment forms
        "candidate_name": build_full_name(),
        "employee_name": build_full_name(),
        "position_applied": employee.get("role"),
        # Today's date for signature fields
        "today": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
    }
    
    # Build the auto-fill response based on what the form requests
    # Go through each section and field, matching auto_fill keys
    sections = config.get("sections", [])
    
    for section in sections:
        for field in section.get("fields", []):
            field_id = field.get("id")
            auto_fill_key = field.get("auto_fill")
            
            if auto_fill_key and auto_fill_key in field_value_map:
                value = field_value_map[auto_fill_key]
                if value is not None and value != "":
                    auto_fill_data[field_id] = value
    
    return {
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "auto_fill_data": auto_fill_data,
        "source": "employee_profile",
        "note": "Auto-fill data from employee profile. Review before applying to form."
    }


@api_router.post("/form-submissions", response_model=FormSubmissionResponse)
async def create_form_submission(submission: FormSubmissionCreate, user: dict = Depends(get_current_user)):
    """Submit a structured form"""
    employee_id = submission.employee_id
    requirement_id = submission.requirement_id
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Verify form type exists
    if requirement_id not in FORM_BASED_REQUIREMENTS:
        raise HTTPException(status_code=400, detail=f"Unknown form type: {requirement_id}")
    
    # Check for existing submission (supersede if exists)
    existing = await db.form_submissions.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "status": {"$nin": ["deleted", "superseded"]}
    })
    
    if existing:
        # Supersede the existing submission
        await db.form_submissions.update_one(
            {"id": existing["id"]},
            {"$set": {"status": "superseded", "superseded_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    now = datetime.now(timezone.utc).isoformat()
    submission_id = str(uuid.uuid4())
    
    # Get submitter name
    submitter = await db.users.find_one({"id": user['user_id']})
    submitter_name = submitter.get("name", user['user_id']) if submitter else user['user_id']
    
    new_submission = {
        "id": submission_id,
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "form_type": submission.form_type,
        "data": submission.data,
        "submitted_at": now,
        "submitted_by": user['user_id'],
        "submitted_by_name": submitter_name,
        "verified": False,
        "verified_by": None,
        "verified_by_name": None,
        "verified_at": None,
        "status": "submitted",
        "version": (existing.get("version", 0) + 1) if existing else 1,
        "notes": None
    }
    
    await db.form_submissions.insert_one(new_submission)
    
    # Log audit action
    await log_audit_action(user['user_id'], "form_submitted", "form_submission", submission_id, {
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "form_type": submission.form_type,
        "version": new_submission["version"]
    })
    
    return FormSubmissionResponse(**new_submission)


@api_router.get("/form-submissions")
async def get_form_submissions(
    employee_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get form submissions with optional filtering"""
    query = {"status": {"$nin": ["deleted", "superseded"]}}
    
    if employee_id:
        query["employee_id"] = employee_id
    if requirement_id:
        query["requirement_id"] = requirement_id
    
    submissions = await db.form_submissions.find(query, {"_id": 0}).to_list(100)
    return submissions


@api_router.get("/form-submissions/{submission_id}", response_model=FormSubmissionResponse)
async def get_form_submission(submission_id: str, user: dict = Depends(get_current_user)):
    """Get a specific form submission"""
    submission = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    return FormSubmissionResponse(**submission)


@api_router.put("/form-submissions/{submission_id}", response_model=FormSubmissionResponse)
async def update_form_submission(
    submission_id: str, 
    update: FormSubmissionUpdate, 
    user: dict = Depends(get_current_user)
):
    """Update a form submission"""
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {"updated_at": now}
    
    if update.data is not None:
        update_fields["data"] = update.data
    if update.notes is not None:
        update_fields["notes"] = update.notes
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": update_fields}
    )
    
    # Log audit action
    await log_audit_action(user['user_id'], "form_updated", "form_submission", submission_id, {
        "updated_fields": list(update_fields.keys())
    })
    
    updated = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    return FormSubmissionResponse(**updated)


@api_router.post("/form-submissions/{submission_id}/verify")
async def verify_form_submission(submission_id: str, user: dict = Depends(require_admin)):
    """Verify a form submission"""
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get verifier name
    verifier = await db.users.find_one({"id": user['user_id']})
    verifier_name = verifier.get("name", user['user_id']) if verifier else user['user_id']
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "verified": True,
            "verified_by": user['user_id'],
            "verified_by_name": verifier_name,
            "verified_at": now,
            "status": "verified"
        }}
    )
    
    # Log audit action
    await log_audit_action(user['user_id'], "form_verified", "form_submission", submission_id, {
        "employee_id": submission["employee_id"],
        "requirement_id": submission["requirement_id"]
    })
    
    updated = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    return FormSubmissionResponse(**updated)


@api_router.post("/form-submissions/{submission_id}/unverify")
async def unverify_form_submission(submission_id: str, user: dict = Depends(require_admin)):
    """Remove verification from a form submission"""
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "verified": False,
            "verified_by": None,
            "verified_by_name": None,
            "verified_at": None,
            "status": "submitted"
        }}
    )
    
    # Log audit action
    await log_audit_action(user['user_id'], "form_unverified", "form_submission", submission_id, {
        "employee_id": submission["employee_id"],
        "requirement_id": submission["requirement_id"]
    })
    
    updated = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    return FormSubmissionResponse(**updated)


@api_router.delete("/form-submissions/{submission_id}")
async def delete_form_submission(submission_id: str, user: dict = Depends(require_admin)):
    """Delete a form submission (soft delete)"""
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": user['user_id']
        }}
    )
    
    # Log audit action
    await log_audit_action(user['user_id'], "form_deleted", "form_submission", submission_id, {
        "employee_id": submission["employee_id"],
        "requirement_id": submission["requirement_id"]
    })
    
    return {"success": True, "message": "Form submission deleted"}


# ============================================================================
# PDF TEMPLATE MANAGEMENT & GENERATION - Template-Backed Forms Architecture
# ============================================================================

async def generate_staff_health_pdf(submission_data: dict, employee_data: dict, template_config: dict = None) -> bytes:
    """
    Generate a completed Staff Health Questionnaire PDF from structured form data.
    Uses reportlab to create a professional PDF matching the official template layout.
    
    Args:
        submission_data: The structured form data from form_submissions
        employee_data: Employee profile data for additional context
        template_config: Optional custom template configuration
    
    Returns:
        bytes: The generated PDF content
    """
    buffer = io.BytesIO()
    
    # Use the mapping config or default
    mapping = template_config or STAFF_HEALTH_PDF_MAPPING
    branding = mapping.get("company_branding", {})
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles matching Osabea branding
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=6
    )
    
    label_style = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        fontName='Helvetica-Bold'
    )
    
    value_style = ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#000000')
    )
    
    question_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#333333'),
        leftIndent=10
    )
    
    # Build story (content elements)
    story = []
    
    # Header with green background
    green_color = colors.HexColor(branding.get("header_color", "#2E7D32"))
    
    # Company header table
    header_data = [[
        Paragraph(f"<b>{branding.get('logo_text', 'O')}</b>", 
                  ParagraphStyle('Logo', fontSize=24, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(f"<b>{branding.get('name', 'Osabea Healthcare Solutions Ltd')}</b><br/><font size='10'>Staff Health Questionnaire</font>", 
                  ParagraphStyle('HeaderText', fontSize=14, textColor=colors.white, alignment=TA_LEFT))
    ]]
    
    header_table = Table(header_data, colWidths=[25*mm, 145*mm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), green_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 3*mm))
    
    # Confidentiality notice
    confidentiality = branding.get("confidentiality_notice", "CONFIDENTIAL - For Occupational Health Use Only")
    story.append(Paragraph(f"<i>{confidentiality}</i>", 
                          ParagraphStyle('Confidential', fontSize=8, textColor=colors.HexColor('#666666'), alignment=TA_CENTER)))
    story.append(Spacer(1, 5*mm))
    
    # Helper function to format field value
    def format_value(value, field_type="text"):
        if value is None or value == "":
            return "-"
        if field_type == "date" and value:
            try:
                # Parse ISO date and format nicely
                if 'T' in str(value):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.strftime('%d/%m/%Y')
                return value
            except:
                return value
        if field_type == "checkbox":
            return "Yes" if value else "No"
        return str(value)
    
    # Process each section
    for section in mapping.get("sections", []):
        # Section header with green background
        section_data = [[Paragraph(f"<b>{section['title']}</b>", section_header_style)]]
        section_table = Table(section_data, colWidths=[170*mm])
        section_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), green_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(section_table)
        story.append(Spacer(1, 2*mm))
        
        # Build field rows
        if section['id'] == 'health_questions':
            # Health questions in a special format
            for field in section.get('fields', []):
                field_id = field['field_id']
                field_type = field.get('type', 'text')
                label = field['label']
                value = submission_data.get(field_id, '')
                
                if field_type == 'yes_no':
                    answer = format_value(value)
                    details_field = field.get('details_field')
                    details = submission_data.get(details_field, '') if details_field and value == 'Yes' else ''
                    
                    q_data = [[
                        Paragraph(f"{label}", question_style),
                        Paragraph(f"<b>{answer}</b>", value_style)
                    ]]
                    q_table = Table(q_data, colWidths=[140*mm, 30*mm])
                    q_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
                    ]))
                    story.append(q_table)
                    
                    if details:
                        details_data = [[Paragraph(f"<i>Details: {details}</i>", 
                                                   ParagraphStyle('Details', fontSize=9, textColor=colors.HexColor('#555555'), leftIndent=20))]]
                        details_table = Table(details_data, colWidths=[170*mm])
                        details_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F5')),
                            ('LEFTPADDING', (0, 0), (-1, -1), 10),
                            ('TOPPADDING', (0, 0), (-1, -1), 3),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ]))
                        story.append(details_table)
                else:
                    # Free text field
                    value_formatted = format_value(value, field_type)
                    q_data = [[
                        Paragraph(f"{label}", question_style),
                        Paragraph(f"{value_formatted}", value_style)
                    ]]
                    q_table = Table(q_data, colWidths=[140*mm, 30*mm])
                    q_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
                    ]))
                    story.append(q_table)
        else:
            # Regular fields in a 2-column layout
            field_rows = []
            for field in section.get('fields', []):
                field_id = field['field_id']
                field_type = field.get('type', 'text')
                label = field['label']
                value = submission_data.get(field_id, '')
                value_formatted = format_value(value, field_type)
                
                field_rows.append([
                    Paragraph(f"<b>{label}:</b>", label_style),
                    Paragraph(value_formatted, value_style)
                ])
            
            if field_rows:
                field_table = Table(field_rows, colWidths=[60*mm, 110*mm])
                field_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F8F8')),
                ]))
                story.append(field_table)
        
        story.append(Spacer(1, 4*mm))
    
    # Footer with submission info
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E0E0E0')))
    story.append(Spacer(1, 3*mm))
    
    submitted_at = submission_data.get('_submitted_at', '')
    if submitted_at:
        try:
            dt = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
            submitted_at = dt.strftime('%d/%m/%Y at %H:%M')
        except:
            pass
    
    footer_text = f"Generated from Osabea Compliance Portal | Form submitted: {submitted_at} | Employee: {employee_data.get('first_name', '')} {employee_data.get('last_name', '')} ({employee_data.get('employee_code', '')})"
    story.append(Paragraph(footer_text, ParagraphStyle('Footer', fontSize=8, textColor=colors.HexColor('#888888'), alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()


@api_router.get("/pdf-templates")
async def list_pdf_templates(
    form_type: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """List all PDF templates, optionally filtered by form type"""
    query = {}
    if form_type:
        query["form_type"] = form_type
    
    templates = await db.form_pdf_templates.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return templates


@api_router.get("/pdf-templates/{template_id}")
async def get_pdf_template(template_id: str, user: dict = Depends(require_admin)):
    """Get a specific PDF template"""
    template = await db.form_pdf_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")
    return template


@api_router.post("/pdf-templates", response_model=PDFTemplateResponse)
async def create_pdf_template(
    form_type: str = Form(...),
    name: str = Form(...),
    version: str = Form("1.0"),
    file: UploadFile = File(...),
    user: dict = Depends(require_admin)
):
    """
    Upload a new PDF template for a form type.
    The template PDF is stored in object storage and can be used for reference.
    """
    template_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Validate form type exists
    if form_type not in FORM_BASED_REQUIREMENTS and form_type not in PDF_FIELD_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown form type: {form_type}")
    
    # Upload file to storage
    content = await file.read()
    storage_path = f"{APP_NAME}/pdf-templates/{form_type}/{template_id}_{file.filename}"
    content_type = file.content_type or "application/pdf"
    
    result = put_object(storage_path, content, content_type)
    
    # Get default mapping for this form type
    default_mapping = PDF_FIELD_MAPPINGS.get(form_type, {})
    
    template_doc = {
        "id": template_id,
        "form_type": form_type,
        "name": name,
        "version": version,
        "file_url": result.get("path"),
        "storage_path": storage_path,
        "original_filename": file.filename,
        "is_active": False,  # Not active by default
        "mapping_config": default_mapping,
        "created_by": user['user_id'],
        "created_by_name": user.get('name', 'Unknown'),
        "created_at": now,
        "updated_at": now
    }
    
    await db.form_pdf_templates.insert_one(template_doc)
    
    await log_audit_action(user['user_id'], "pdf_template_created", "pdf_template", template_id, {
        "form_type": form_type,
        "name": name,
        "version": version
    })
    
    return {**template_doc, "_id": None}


@api_router.put("/pdf-templates/{template_id}/activate")
async def activate_pdf_template(template_id: str, user: dict = Depends(require_admin)):
    """Mark a PDF template as active (deactivates other templates for the same form type)"""
    template = await db.form_pdf_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")
    
    form_type = template["form_type"]
    now = datetime.now(timezone.utc).isoformat()
    
    # Deactivate all other templates for this form type
    await db.form_pdf_templates.update_many(
        {"form_type": form_type, "id": {"$ne": template_id}},
        {"$set": {"is_active": False, "updated_at": now}}
    )
    
    # Activate this template
    await db.form_pdf_templates.update_one(
        {"id": template_id},
        {"$set": {"is_active": True, "updated_at": now}}
    )
    
    await log_audit_action(user['user_id'], "pdf_template_activated", "pdf_template", template_id, {
        "form_type": form_type
    })
    
    return {"success": True, "message": f"Template activated for {form_type}"}


@api_router.delete("/pdf-templates/{template_id}")
async def delete_pdf_template(template_id: str, user: dict = Depends(require_admin)):
    """Delete a PDF template"""
    template = await db.form_pdf_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")
    
    await db.form_pdf_templates.delete_one({"id": template_id})
    
    await log_audit_action(user['user_id'], "pdf_template_deleted", "pdf_template", template_id, {
        "form_type": template["form_type"],
        "name": template["name"]
    })
    
    return {"success": True, "message": "Template deleted"}


@api_router.post("/form-submissions/{submission_id}/generate-pdf")
async def generate_form_pdf(submission_id: str, user: dict = Depends(require_admin)):
    """
    Generate a completed PDF from a form submission.
    
    This endpoint:
    1. Loads structured data from form_submissions (source of truth)
    2. Loads active template config for the form type (if any)
    3. Renders a completed PDF using the template layout + structured data
    4. Saves the generated PDF as an export artifact
    5. Returns the PDF file URL
    
    The PDF is purely an export artifact - form_submissions remains the source of truth.
    """
    # Get the form submission
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    form_type = submission.get("form_type")
    employee_id = submission.get("employee_id")
    
    # Get employee data
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get active template for this form type (if any)
    active_template = await db.form_pdf_templates.find_one({
        "form_type": form_type,
        "is_active": True
    })
    
    # Get mapping config - use template's config if available, otherwise use default
    mapping_config = None
    if active_template and active_template.get("mapping_config"):
        mapping_config = active_template["mapping_config"]
    elif form_type in PDF_FIELD_MAPPINGS:
        mapping_config = PDF_FIELD_MAPPINGS[form_type]
    
    if not mapping_config:
        raise HTTPException(status_code=400, detail=f"No PDF mapping configured for form type: {form_type}")
    
    # Prepare submission data with metadata
    submission_data = submission.get("data", {})
    submission_data["_submitted_at"] = submission.get("submitted_at", "")
    submission_data["_verified"] = submission.get("verified", False)
    submission_data["_status"] = submission.get("status", "submitted")
    
    # Generate PDF based on form type
    if form_type == "staff_health_questionnaire":
        pdf_bytes = await generate_staff_health_pdf(submission_data, employee, mapping_config)
    else:
        # Generic PDF generation for other form types (can be extended)
        raise HTTPException(status_code=400, detail=f"PDF generation not yet implemented for form type: {form_type}")
    
    # Save generated PDF to storage
    export_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    employee_name = f"{employee.get('first_name', '')}_{employee.get('last_name', '')}".replace(' ', '_')
    filename = f"{form_type}_{employee_name}_{timestamp}.pdf"
    storage_path = f"{APP_NAME}/pdf-exports/{form_type}/{export_id}_{filename}"
    
    result = put_object(storage_path, pdf_bytes, "application/pdf")
    
    # Save export record
    export_doc = {
        "id": export_id,
        "submission_id": submission_id,
        "template_id": active_template["id"] if active_template else None,
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
        "employee_code": employee.get("employee_code", ""),
        "form_type": form_type,
        "file_url": result.get("path"),
        "storage_path": storage_path,
        "filename": filename,
        "created_at": now,
        "created_by": user['user_id'],
        "created_by_name": user.get('name', 'Unknown')
    }
    
    await db.form_pdf_exports.insert_one(export_doc)
    
    await log_audit_action(user['user_id'], "pdf_generated", "form_submission", submission_id, {
        "export_id": export_id,
        "form_type": form_type,
        "employee_id": employee_id
    })
    
    return {
        "success": True,
        "export_id": export_id,
        "file_url": result.get("path"),
        "filename": filename,
        "message": "PDF generated successfully"
    }


@api_router.get("/form-submissions/{submission_id}/download-pdf")
async def download_form_pdf(submission_id: str, user: dict = Depends(get_current_user)):
    """
    Download the most recent PDF export for a form submission.
    Returns the actual PDF file bytes for download.
    If no export exists and user is admin, generates one on-the-fly.
    """
    # Check for existing export
    export = await db.form_pdf_exports.find_one(
        {"submission_id": submission_id},
        sort=[("created_at", -1)]
    )
    
    if export and export.get("file_url"):
        # Retrieve and return the actual PDF file
        file_path = export.get("file_url")
        filename = export.get("filename", "form.pdf")
        
        try:
            content, content_type = get_object(file_path)
            safe_filename = filename.replace('"', '\\"')
            
            return Response(
                content=content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_filename}"',
                    "Cache-Control": "private, max-age=3600"
                }
            )
        except Exception as e:
            # File exists in DB but not in storage - mark as corrupted
            logger.error(f"PDF file retrieval failed for export {export.get('id')}: {e}")
            await log_audit_action(
                user['user_id'], "file_retrieval_failed", "form_pdf_export", export.get('id'),
                {"file_path": file_path, "error": str(e), "submission_id": submission_id}
            )
            raise HTTPException(
                status_code=500, 
                detail="PDF file not found in storage. Record may be corrupted. Please regenerate the PDF."
            )
    
    # No export exists - generate one (requires admin)
    # For non-admins, return error
    if not user.get('role') == 'admin':
        raise HTTPException(status_code=404, detail="No PDF export found. Admin can generate one.")
    
    # Generate PDF on-the-fly and return the file bytes directly
    submission = await db.form_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    # Generate the PDF (this also saves to storage)
    result = await generate_form_pdf(submission_id, user)
    
    # Now retrieve and return the generated file
    file_path = result.get("file_url")
    filename = result.get("filename", "form.pdf")
    
    try:
        content, content_type = get_object(file_path)
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Failed to retrieve newly generated PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve generated PDF")



@api_router.get("/form-submissions/{submission_id}/view-pdf")
async def view_form_pdf(submission_id: str, user: dict = Depends(get_current_user)):
    """
    View the most recent PDF export for a form submission inline.
    Returns the actual PDF file for browser viewing (not download).
    """
    # Check for existing export
    export = await db.form_pdf_exports.find_one(
        {"submission_id": submission_id},
        sort=[("created_at", -1)]
    )
    
    if not export or not export.get("file_url"):
        raise HTTPException(status_code=404, detail="No PDF export found for this submission")
    
    file_path = export.get("file_url")
    filename = export.get("filename", "form.pdf")
    
    try:
        content, content_type = get_object(file_path)
        safe_filename = filename.replace('"', '\\"')
        
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{safe_filename}"',
                "Cache-Control": "private, max-age=3600"
            }
        )
    except Exception as e:
        # File exists in DB but not in storage
        logger.error(f"PDF file retrieval failed for viewing: {e}")
        await log_audit_action(
            user['user_id'], "file_retrieval_failed", "form_pdf_export", export.get('id'),
            {"file_path": file_path, "error": str(e), "action": "view"}
        )
        raise HTTPException(
            status_code=500, 
            detail="PDF file not found in storage. Record may be corrupted."
        )



@api_router.get("/pdf-exports")
async def list_pdf_exports(
    form_type: Optional[str] = None,
    employee_id: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """List PDF exports with optional filters"""
    query = {}
    if form_type:
        query["form_type"] = form_type
    if employee_id:
        query["employee_id"] = employee_id
    
    exports = await db.form_pdf_exports.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return exports


@api_router.get("/pdf-field-mappings/{form_type}")
async def get_pdf_field_mapping(form_type: str, user: dict = Depends(require_admin)):
    """Get the field mapping configuration for a form type"""
    if form_type not in PDF_FIELD_MAPPINGS:
        raise HTTPException(status_code=404, detail=f"No field mapping found for form type: {form_type}")
    
    return PDF_FIELD_MAPPINGS[form_type]


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
    
    # Get counts - now using "acknowledged" status instead of "signed"
    for policy in policies:
        assigned_count = await db.policy_assignments.count_documents({"policy_id": policy['id']})
        acknowledged_count = await db.policy_assignments.count_documents({
            "policy_id": policy['id'], 
            "status": {"$in": ["acknowledged", "signed"]}  # Support both old and new status
        })
        policy['assigned_count'] = assigned_count
        policy['signed_count'] = acknowledged_count  # This is acknowledged count for backwards compat
    
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
    
    now = datetime.now(timezone.utc).isoformat()
    await db.policies.update_one({"id": policy_id}, {"$set": {
        "file_url": result["path"],
        "original_filename": file.filename,
        "uploaded_at": now
    }})
    
    # Audit log for policy upload
    await log_audit_action(
        user['user_id'],
        "policy_uploaded",
        "policy",
        policy_id,
        {
            "policy_title": policy['title'],
            "filename": file.filename,
            "version": policy.get('version', '1.0')
        }
    )
    
    updated_policy = await db.policies.find_one({"id": policy_id}, {"_id": 0})
    return PolicyResponse(**updated_policy)


@api_router.get("/policies/{policy_id}/file")
async def get_policy_file(policy_id: str, user: dict = Depends(get_current_user)):
    """Get policy file for viewing - used when employee views assigned policy"""
    policy = await db.policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if not policy.get('file_url'):
        raise HTTPException(status_code=404, detail="No file uploaded for this policy")
    
    try:
        data, content_type = get_object(policy['file_url'])
        filename = policy.get('original_filename', f"policy_{policy_id}.pdf")
        return StreamingResponse(
            io.BytesIO(data),
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename=\"{filename}\""}
        )
    except Exception as e:
        logger.error(f"Error retrieving policy file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve policy file")

@api_router.post("/policies/assign")
async def assign_policies(assignment: PolicyAssignmentCreate, user: dict = Depends(require_admin)):
    # Check both policies and org_policies collections (Compliance Centre uses org_policies)
    policy = await db.policies.find_one({"id": assignment.policy_id}, {"_id": 0})
    if not policy:
        # Try org_policies collection (used by Compliance Centre)
        policy = await db.org_policies.find_one({"id": assignment.policy_id}, {"_id": 0})
        if policy:
            # Map org_policies fields to expected format
            policy = {
                "id": policy.get("id"),
                "title": policy.get("name"),  # org_policies uses 'name', policies uses 'title'
                "version": policy.get("version", "1.0"),
                "file_url": policy.get("file_url")
            }
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    assignments = []
    
    for emp_id in assignment.employee_ids:
        # Check if already assigned (not unassigned or withdrawn)
        existing = await db.policy_assignments.find_one({
            "policy_id": assignment.policy_id, 
            "employee_id": emp_id,
            "status": {"$nin": ["unassigned", "withdrawn"]}
        })
        if existing:
            continue
        
        # Get employee name for audit trail
        emp = await db.employees.find_one({"id": emp_id}, {"_id": 0})
        emp_name = f"{emp['first_name']} {emp['last_name']}" if emp else "Unknown"
        
        assignment_doc = {
            "id": str(uuid.uuid4()),
            "policy_id": assignment.policy_id,
            "policy_title": policy['title'],
            "policy_version": policy.get('version', '1.0'),
            "employee_id": emp_id,
            "employee_name": emp_name,
            "assigned_at": now,
            "assigned_by": user['user_id'],
            "assigned_by_name": user.get('name', user.get('email', 'Admin')),
            "status": "assigned",
            "viewed_at": None,
            "acknowledged_at": None,
            "acknowledged_by_employee_name": None,
            "admin_reviewed": False,
            "admin_reviewed_at": None,
            "admin_reviewed_by": None,
            "admin_reviewed_by_name": None
        }
        await db.policy_assignments.insert_one(assignment_doc)
        assignments.append(assignment_doc)
        
        await log_audit_action(
            user['user_id'], 
            "policy_assigned", 
            "policy_assignment", 
            assignment_doc['id'], 
            {
                "policy_id": assignment.policy_id, 
                "policy_title": policy['title'],
                "policy_version": policy.get('version', '1.0'),
                "employee_id": emp_id,
                "employee_name": emp_name,
                "assigned_by_name": user.get('name', user.get('email', 'Admin'))
            }
        )
    
    return {"assigned": len(assignments), "message": f"Policy assigned to {len(assignments)} employees"}

@api_router.get("/policy-assignments", response_model=List[PolicyAssignmentResponse])
async def get_policy_assignments(
    employee_id: Optional[str] = None,
    policy_id: Optional[str] = None,
    status: Optional[str] = None,
    include_inactive: bool = False,
    user: dict = Depends(get_current_user)
):
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


@api_router.put("/policy-assignments/{assignment_id}/view")
async def mark_policy_viewed(assignment_id: str, user: dict = Depends(get_current_user)):
    """Mark a policy assignment as viewed by the employee"""
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

@api_router.put("/policy-assignments/{assignment_id}/acknowledge")
async def acknowledge_policy(assignment_id: str, user: dict = Depends(get_current_user)):
    """
    Employee acknowledges policy - "I have read and understood this policy"
    Stores: employee_id, policy_id, policy_version, acknowledged_at
    """
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
    
    update_data = {
        "status": "acknowledged",
        "acknowledged_at": now,
        "acknowledged_by_employee_name": emp_name
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
            "employee_name": emp_name,
            "acknowledged_at": now
        }
    )
    
    updated = await db.policy_assignments.find_one({"id": assignment_id}, {"_id": 0})
    return PolicyAssignmentResponse(**updated)


@api_router.put("/policy-assignments/{assignment_id}/admin-review")
async def admin_review_policy(assignment_id: str, user: dict = Depends(require_admin)):
    """
    Admin reviews and approves the policy acknowledgement
    Stores: admin_id, reviewed_at, admin_name
    """
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


class PolicyReversalRequest(BaseModel):
    reason: Optional[str] = None


@api_router.put("/policy-assignments/{assignment_id}/unassign")
async def unassign_policy(
    assignment_id: str, 
    request: PolicyReversalRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Unassign a policy BEFORE it has been acknowledged.
    For policies not yet acknowledged, simply marks as unassigned.
    """
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


@api_router.put("/policy-assignments/{assignment_id}/withdraw")
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


# ==================== ORGANISATION SETTINGS ====================

@api_router.get("/org-settings")
async def get_org_settings(user: dict = Depends(get_current_user)):
    """Get organisation settings including service type"""
    settings = await db.org_settings.find_one({}, {"_id": 0})
    if not settings:
        # Create default settings
        now = datetime.now(timezone.utc).isoformat()
        settings = {
            "id": str(uuid.uuid4()),
            "service_type": "adults_only",
            "organisation_name": "Osabea Healthcare Solutions",
            "created_at": now,
            "updated_at": now
        }
        await db.org_settings.insert_one(settings)
    return OrgSettingsResponse(**settings)


@api_router.put("/org-settings")
async def update_org_settings(
    update_data: OrgSettingsUpdate,
    user: dict = Depends(require_admin)
):
    """Update organisation settings"""
    settings = await db.org_settings.find_one({}, {"_id": 0})
    now = datetime.now(timezone.utc).isoformat()
    
    if not settings:
        settings = {
            "id": str(uuid.uuid4()),
            "service_type": update_data.service_type or "adults_only",
            "organisation_name": update_data.organisation_name or "Osabea Healthcare Solutions",
            "created_at": now,
            "updated_at": now
        }
        await db.org_settings.insert_one(settings)
    else:
        changes = {}
        if update_data.service_type and update_data.service_type != settings.get('service_type'):
            changes['service_type'] = {
                'old': settings.get('service_type'),
                'new': update_data.service_type
            }
        if update_data.organisation_name and update_data.organisation_name != settings.get('organisation_name'):
            changes['organisation_name'] = {
                'old': settings.get('organisation_name'),
                'new': update_data.organisation_name
            }
        
        update_fields = {"updated_at": now}
        if update_data.service_type:
            update_fields["service_type"] = update_data.service_type
        if update_data.organisation_name:
            update_fields["organisation_name"] = update_data.organisation_name
        
        await db.org_settings.update_one({}, {"$set": update_fields})
        
        if changes:
            await log_audit_action(
                user['user_id'],
                "org_settings_updated",
                "org_settings",
                settings['id'],
                changes
            )
    
    updated = await db.org_settings.find_one({}, {"_id": 0})
    return OrgSettingsResponse(**updated)


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
    
    # CRITICAL: Enrich with computed status - SINGLE SOURCE OF TRUTH
    enriched_record = enrich_training_record_with_computed_status(record_doc)
    return TrainingRecordResponse(**enriched_record)

@api_router.get("/training-records", response_model=List[TrainingRecordResponse])
async def get_training_records(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    mandatory: Optional[bool] = None,
    include_test: Optional[bool] = False,
    include_superseded: Optional[bool] = False,
    include_deleted: Optional[bool] = False,
    user: dict = Depends(get_current_user)
):
    """
    Get training records with COMPUTED status.
    Status is computed fresh from canonical fields (completion_date, expiry_date).
    Frontend MUST use the returned computed fields, not compute locally.
    """
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    # NOTE: status filter now applies to COMPUTED status, handled after enrichment
    if mandatory is not None:
        query["mandatory"] = mandatory
    
    # Exclude TEST records by default (unless explicitly requested)
    if not include_test:
        query["training_name"] = {"$not": {"$regex": "^TEST", "$options": "i"}}
    
    # Exclude superseded/deleted records by default - SINGLE SOURCE OF TRUTH
    if not include_superseded and not include_deleted:
        query["record_status"] = {"$nin": ["superseded", "deleted"]}
    elif not include_superseded:
        query["record_status"] = {"$ne": "superseded"}
    elif not include_deleted:
        query["record_status"] = {"$ne": "deleted"}
    
    records = await db.training_records.find(query, {"_id": 0}).to_list(1000)
    
    # CRITICAL: Enrich all records with computed status
    enriched_records = [enrich_training_record_with_computed_status(r) for r in records]
    
    # Apply status filter on computed status if provided
    if status:
        enriched_records = [r for r in enriched_records if r.get('computed_status') == status or r.get('status') == status]
    
    return [TrainingRecordResponse(**r) for r in enriched_records]


@api_router.delete("/training-records/cleanup-test")
async def cleanup_test_training_records(user: dict = Depends(require_admin)):
    """Admin-only: Permanently delete all TEST training records.
    These are records where training_name starts with 'TEST'.
    """
    result = await db.training_records.delete_many({
        "training_name": {"$regex": "^TEST", "$options": "i"}
    })
    
    return {
        "deleted_count": result.deleted_count,
        "message": f"Deleted {result.deleted_count} TEST training records"
    }


class DeleteTrainingRequest(BaseModel):
    """Request to delete a training record with audit trail"""
    reason: Optional[str] = None


@api_router.delete("/training-records/{record_id}")
async def delete_training_record(
    record_id: str,
    reason: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Delete a single training record.
    - Removes from active use
    - Keeps audit trail
    - Updates employee compliance
    """
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    employee_id = record.get('employee_id')
    training_name = record.get('training_name')
    
    # Get user name for audit
    user_doc = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    # Create audit log entry before deletion
    now = datetime.now(timezone.utc).isoformat()
    await log_audit_action(
        user['user_id'],
        "training_deleted",
        "training_record",
        record_id,
        {
            "training_name": training_name,
            "employee_id": employee_id,
            "deleted_by": user_name,
            "deleted_at": now,
            "reason": reason,
            "original_status": record.get('status'),
            "had_evidence": bool(record.get('certificate_url') or record.get('evidence_files'))
        }
    )
    
    # SOFT DELETE - set record_status to "deleted" instead of hard delete
    await db.training_records.update_one(
        {"id": record_id},
        {"$set": {
            "record_status": "deleted",
            "deleted_at": now,
            "deleted_by": user_name,
            "updated_at": now
        }}
    )
    
    # Update employee compliance
    if employee_id:
        await update_employee_compliance(employee_id)
    
    return {
        "success": True,
        "message": f"Training record '{training_name}' deleted",
        "deleted_record_id": record_id
    }


class BulkDeleteTrainingRequest(BaseModel):
    """Request to bulk delete training records"""
    record_ids: List[str]
    reason: Optional[str] = None


@api_router.post("/training-records/bulk-delete")
async def bulk_delete_training_records(
    request: BulkDeleteTrainingRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Bulk delete multiple training records.
    - Removes from active use
    - Keeps audit trail for each
    - Updates affected employees' compliance
    """
    if not request.record_ids:
        raise HTTPException(status_code=400, detail="No record IDs provided")
    
    # Get user name for audit
    user_doc = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    now = datetime.now(timezone.utc).isoformat()
    deleted_count = 0
    affected_employees = set()
    
    for record_id in request.record_ids:
        record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
        if not record:
            continue
        
        employee_id = record.get('employee_id')
        training_name = record.get('training_name')
        
        # Create audit log entry
        await log_audit_action(
            user['user_id'],
            "training_deleted",
            "training_record",
            record_id,
            {
                "training_name": training_name,
                "employee_id": employee_id,
                "deleted_by": user_name,
                "deleted_at": now,
                "reason": request.reason,
                "bulk_delete": True,
                "original_status": record.get('status'),
                "had_evidence": bool(record.get('certificate_url') or record.get('evidence_files'))
            }
        )
        
        # SOFT DELETE - set record_status to "deleted"
        await db.training_records.update_one(
            {"id": record_id},
            {"$set": {
                "record_status": "deleted",
                "deleted_at": now,
                "deleted_by": user_name,
                "updated_at": now
            }}
        )
        deleted_count += 1
        if employee_id:
            affected_employees.add(employee_id)
    
    # Update compliance for affected employees
    for emp_id in affected_employees:
        await update_employee_compliance(emp_id)
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "affected_employees": len(affected_employees),
        "message": f"Deleted {deleted_count} training records"
    }


@api_router.put("/training-records/{record_id}", response_model=TrainingRecordResponse)
async def update_training_record(record_id: str, update: TrainingRecordCreate, user: dict = Depends(require_manager_or_admin)):
    result = await db.training_records.update_one({"id": record_id}, {"$set": update.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    # CRITICAL: Enrich with computed status - SINGLE SOURCE OF TRUTH
    enriched_record = enrich_training_record_with_computed_status(record)
    return TrainingRecordResponse(**enriched_record)


class TrainingRecordUpdateRequest(BaseModel):
    """Request to update a training record - SINGLE SOURCE OF TRUTH"""
    completion_date: Optional[str] = None
    expiry_date: Optional[str] = None
    clear_expiry_date: Optional[bool] = False  # Set to true to explicitly clear expiry
    status: Optional[str] = None  # not_started, in_progress, completed, expiring, expired
    verified: Optional[bool] = None
    notes: Optional[str] = None
    reason: str  # Required for audit


@api_router.patch("/employees/{employee_id}/training/{requirement_id}")
async def update_employee_training_record(
    employee_id: str,
    requirement_id: str,
    update: TrainingRecordUpdateRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Update a training record directly - SINGLE SOURCE OF TRUTH.
    This endpoint should be used from "What's Needed" modal to edit training.
    All training edits go through this endpoint to ensure consistency.
    """
    # Validate reason
    if not update.reason or len(update.reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 3 characters)")
    
    # Find the SINGLE ACTIVE training record
    record = await db.training_records.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0})
    
    if not record:
        # Try by training name pattern
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "training_name": {"$regex": requirement_id, "$options": "i"},
            "record_status": {"$nin": ["superseded", "deleted"]}
        }, {"_id": 0})
    
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    user_doc = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    user_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    # Build update data
    update_data = {"updated_at": now}
    changes = {}
    
    if update.completion_date is not None:
        # CANONICAL: Normalize to YYYY-MM-DD format
        normalized_completion = normalize_date_only(update.completion_date)
        changes["completion_date"] = {"old": record.get('completion_date'), "new": normalized_completion}
        update_data["completion_date"] = normalized_completion
        # Auto-calculate expiry if completion date changes
        if normalized_completion and not update.expiry_date:
            update_data["expiry_date"] = calculate_training_expiry(normalized_completion, requirement_id)
            changes["expiry_date"] = {"old": record.get('expiry_date'), "new": update_data["expiry_date"]}
    
    if update.expiry_date is not None:
        # CANONICAL: Normalize to YYYY-MM-DD format
        normalized_expiry = normalize_date_only(update.expiry_date)
        changes["expiry_date"] = {"old": record.get('expiry_date'), "new": normalized_expiry}
        update_data["expiry_date"] = normalized_expiry
    elif update.clear_expiry_date:
        # Explicitly clear expiry date
        changes["expiry_date"] = {"old": record.get('expiry_date'), "new": None}
        update_data["expiry_date"] = None
    
    if update.status is not None:
        changes["status"] = {"old": record.get('status'), "new": update.status}
        update_data["status"] = update.status
    
    if update.verified is not None:
        changes["verified"] = {"old": record.get('verified'), "new": update.verified}
        update_data["verified"] = update.verified
        if update.verified:
            update_data["verified_at"] = now
            update_data["verified_by"] = user_name
        else:
            update_data["verified_at"] = None
            update_data["verified_by"] = None
    
    # Apply update
    await db.training_records.update_one(
        {"id": record['id']},
        {"$set": update_data}
    )
    
    # Create audit log
    await log_audit_action(user['user_id'], "training_record_updated", "training_record", record['id'], {
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "training_name": record.get('training_name'),
        "changes": changes,
        "reason": update.reason.strip(),
        "updated_by": user_name,
        "updated_at": now
    })
    
    # Update employee compliance
    await update_employee_compliance(employee_id)
    
    # Return updated record with COMPUTED STATUS - SINGLE SOURCE OF TRUTH
    updated_record = await db.training_records.find_one({"id": record['id']}, {"_id": 0})
    enriched_record = enrich_training_record_with_computed_status(updated_record)
    
    return {
        "success": True,
        "training_record": enriched_record,
        "changes": changes
    }


@api_router.get("/employees/{employee_id}/training/{requirement_id}")
async def get_employee_training_record(
    employee_id: str,
    requirement_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get the SINGLE ACTIVE training record for an employee+requirement.
    Returns COMPUTED status - SINGLE SOURCE OF TRUTH.
    """
    # Find the active record
    record = await db.training_records.find_one({
        "employee_id": employee_id,
        "requirement_id": requirement_id,
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0})
    
    if not record:
        # Try by training name pattern
        record = await db.training_records.find_one({
            "employee_id": employee_id,
            "training_name": {"$regex": requirement_id, "$options": "i"},
            "record_status": {"$nin": ["superseded", "deleted"]}
        }, {"_id": 0})
    
    if not record:
        return {"exists": False, "training_record": None}
    
    # CRITICAL: Enrich with computed status - SINGLE SOURCE OF TRUTH
    enriched_record = enrich_training_record_with_computed_status(record)
    
    # Also include legacy expiry_status for backward compatibility
    expiry_status = None
    if record.get('expiry_date'):
        expiry_status = calculate_expiry_status(record.get('expiry_date'))
    
    return {
        "exists": True,
        "training_record": enriched_record,
        "expiry_status": expiry_status
    }


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
    # HARDENING: Store only canonical fields, NOT derived status
    # Status is computed at runtime via compute_training_record_status()
    update_data = {
        "certificate_url": result["path"], 
        "original_filename": file.filename,
        "uploaded_at": now,
        # REMOVED: "status": "completed" - derived from completion_date/expiry_date
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
    
    # Check for existing ACTIVE training record (exclude deleted/superseded)
    # BUGFIX: Must filter out deleted records to avoid "silent success" where
    # upload succeeds but file doesn't appear (because deleted record gets updated
    # but compliance query filters it out)
    existing_record = await db.training_records.find_one({
        "employee_id": employee_id,
        "record_status": {"$nin": ["superseded", "deleted"]},
        "$or": [
            {"training_name": {"$regex": training_name, "$options": "i"}},
            {"requirement_id": requirement_id}
        ]
    }, {"_id": 0})
    
    if existing_record:
        # Update existing record
        # HARDENING: Store only canonical fields, NOT derived status
        update_data = {
            "certificate_url": result["path"],
            "original_filename": file.filename,
            "uploaded_at": now,
            # REMOVED: "status": "completed" - derived at runtime
            "completion_date": now,
            "completion_method": "certificate",
            "requirement_id": requirement_id,
            "updated_at": now,
            "record_status": "active"  # BUGFIX: Ensure record remains active
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
        # HARDENING: Store only canonical fields, NOT derived status
        record_id = str(uuid.uuid4())
        new_record = {
            "id": record_id,
            "employee_id": employee_id,
            "training_name": training_name,
            "mandatory": True,
            "record_status": "active",  # Explicit active status for compliance queries
            # REMOVED: "status": "completed" - derived at runtime from completion_date/expiry_date
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
    # HARDENING: Check for completion_date existence instead of stored status
    # Status is derived at runtime from completion_date/expiry_date
    existing_training = await db.training_records.find_one({
        "employee_id": employee_id,
        "$or": [
            {"training_name": {"$regex": training_name, "$options": "i"}},
            {"training_name": {"$regex": training_name.replace(" ", ""), "$options": "i"}}
        ],
        "completion_date": {"$exists": True, "$ne": None}  # Has completion = "completed"
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
        # HARDENING: Store only canonical fields, NOT derived status
        await db.training_records.update_one(
            {"id": request.link_existing_id},
            {"$set": {
                # REMOVED: "status": "completed" - derived at runtime
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
        # HARDENING: Store only canonical fields, NOT derived status
        await db.training_records.update_one(
            {"id": existing_incomplete['id']},
            {"$set": {
                # REMOVED: "status": "completed" - derived at runtime
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
    # HARDENING: Store only canonical fields, NOT derived status
    record_id = str(uuid.uuid4())
    new_record = {
        "id": record_id,
        "employee_id": employee_id,
        "training_name": training_name,
        "mandatory": True,
        # REMOVED: "status": "completed" - derived at runtime from completion_date/expiry_date
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


class TrainingCorrectionRequest(BaseModel):
    """Request to correct a training record with mandatory audit reason"""
    field: str  # 'completion_date', 'expiry_date', 'status', 'training_name'
    old_value: Optional[str] = None
    new_value: str
    reason: str  # Mandatory reason for the correction


@api_router.post("/training-records/{record_id}/correct")
async def correct_training_record(
    record_id: str,
    correction: TrainingCorrectionRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Safe correction endpoint for training records.
    - Requires a reason for every change
    - Preserves original value in audit log
    - Creates immutable audit trail
    - Flags if record was verified before correction
    """
    # Validate reason
    if not correction.reason or len(correction.reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 3 characters)")
    
    # Valid fields that can be corrected
    allowed_fields = ['completion_date', 'expiry_date', 'status', 'training_name']
    if correction.field not in allowed_fields:
        raise HTTPException(status_code=400, detail=f"Field '{correction.field}' cannot be corrected. Allowed: {allowed_fields}")
    
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    # Get the actual old value from the record
    actual_old_value = record.get(correction.field)
    was_verified = record.get('verified', False)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get user name for audit
    user_doc = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    changed_by_name = user_doc.get('name', user.get('email', 'Unknown')) if user_doc else user.get('email', 'Unknown')
    
    # Create audit log entry
    audit_entry = {
        "id": str(uuid.uuid4()),
        "entity_type": "training_record",
        "entity_id": record_id,
        "employee_id": record.get('employee_id'),
        "action": "training_correction",
        "field_changed": correction.field,
        "old_value": str(actual_old_value) if actual_old_value else None,
        "new_value": correction.new_value,
        "reason": correction.reason.strip(),
        "was_verified_before_correction": was_verified,
        "changed_by": user['user_id'],
        "changed_by_name": changed_by_name,
        "created_at": now
    }
    await db.audit_logs.insert_one(audit_entry)
    
    # Apply the correction
    update_data = {
        correction.field: correction.new_value,
        "updated_at": now,
        "last_corrected_at": now,
        "last_corrected_by": changed_by_name
    }
    
    # If verified and being corrected, add a flag
    if was_verified:
        update_data["corrected_after_verification"] = True
    
    await db.training_records.update_one(
        {"id": record_id},
        {"$set": update_data}
    )
    
    updated_record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    # CRITICAL: Enrich with computed status - SINGLE SOURCE OF TRUTH
    enriched_record = enrich_training_record_with_computed_status(updated_record)
    
    return {
        "success": True,
        "message": f"Training record corrected: {correction.field}",
        "training_record": enriched_record,
        "audit_entry": {
            "field_changed": correction.field,
            "old_value": str(actual_old_value) if actual_old_value else None,
            "new_value": correction.new_value,
            "reason": correction.reason,
            "was_verified_before": was_verified,
            "corrected_at": now,
            "corrected_by": changed_by_name
        }
    }


@api_router.get("/training-records/{record_id}/history")
async def get_training_record_history(
    record_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get complete audit history for a training record.
    Shows all corrections with old/new values and reasons.
    """
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    # Get all audit entries for this training record
    history = await db.audit_logs.find(
        {"entity_id": record_id, "entity_type": "training_record"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "training_record": record,
        "history": history,
        "total_corrections": sum(1 for h in history if h.get('action') == 'training_correction')
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


@api_router.get("/compliance/centre-summary")
async def get_compliance_centre_summary(user: dict = Depends(get_current_user)):
    """
    Enhanced Compliance Centre summary for CQC audit readiness.
    Returns summary counts for policies, certificates, and staff compliance.
    """
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    exp_30 = (now + thirty_days).isoformat()
    
    # === POLICIES SUMMARY ===
    policies = await db.org_policies.find({}, {"_id": 0}).to_list(200)
    policies_total = len(policies)
    policies_active = 0
    policies_missing = 0
    policies_due_soon = 0
    policies_overdue = 0
    policies_required_complete = 0
    policies_required_total = 0
    missing_required_policies = []
    
    for policy in policies:
        is_required = policy.get("required", True)
        if is_required:
            policies_required_total += 1
        
        if policy.get("status") == "missing":
            policies_missing += 1
            if is_required:
                missing_required_policies.append({
                    "id": policy["id"],
                    "name": policy["name"],
                    "category": policy.get("category"),
                    "required": is_required,
                    "conditional": policy.get("conditional", False)
                })
        elif policy.get("status") == "active":
            policies_active += 1
            if is_required:
                policies_required_complete += 1
        
        # Check review date
        if policy.get("review_date"):
            try:
                review_str = policy["review_date"]
                if 'T' in str(review_str):
                    review_date = datetime.fromisoformat(review_str.replace('Z', '+00:00'))
                else:
                    review_date = datetime.fromisoformat(f"{review_str}T00:00:00+00:00")
                
                if review_date < now:
                    policies_overdue += 1
                elif review_date < now + thirty_days:
                    policies_due_soon += 1
            except Exception:
                pass
    
    # === CERTIFICATES SUMMARY ===
    certificates = await db.insurance_docs.find({}, {"_id": 0}).to_list(100)
    certs_total = len(certificates)
    certs_valid = 0
    certs_missing = 0
    certs_expiring = 0
    certs_expired = 0
    certs_required_complete = 0
    certs_required_total = 0
    missing_required_certs = []
    
    for cert in certificates:
        is_required = cert.get("required", True)
        if is_required:
            certs_required_total += 1
        
        status = cert.get("status", "missing")
        
        # Recalculate status based on expiry date
        if cert.get("expiry_date"):
            try:
                exp_str = cert["expiry_date"]
                if 'T' in str(exp_str):
                    exp_date = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                else:
                    exp_date = datetime.fromisoformat(f"{exp_str}T00:00:00+00:00")
                
                if exp_date < now:
                    status = "expired"
                elif exp_date < now + thirty_days:
                    status = "expiring_soon"
                elif cert.get("file_url"):
                    status = "valid"
            except Exception:
                pass
        elif cert.get("file_url"):
            status = "valid"  # Has file but no expiry date
        
        if status == "missing":
            certs_missing += 1
            if is_required:
                missing_required_certs.append({
                    "id": cert["id"],
                    "name": cert["name"],
                    "type": cert.get("insurance_type"),
                    "category": cert.get("category", "insurance"),
                    "required": is_required,
                    "conditional": cert.get("conditional", False)
                })
        elif status == "valid":
            certs_valid += 1
            if is_required:
                certs_required_complete += 1
        elif status == "expiring_soon":
            certs_expiring += 1
            if is_required:
                certs_required_complete += 1  # Still counts as complete
        elif status == "expired":
            certs_expired += 1
    
    # === STAFF COMPLIANCE SUMMARY ===
    employees = await db.employees.find(
        {"status": {"$ne": "archived"}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
    ).to_list(1000)
    
    staff_total = len(employees)
    staff_compliant = 0
    staff_with_issues = 0
    
    # DBS Register status
    dbs_valid = 0
    dbs_missing = 0
    dbs_expiring = 0
    
    # Training in last 12 months
    twelve_months_ago = (now - timedelta(days=365)).isoformat()
    training_completed_recently = 0
    
    for emp in employees:
        emp_id = emp["id"]
        
        # Check DBS status
        dbs_doc = await db.employee_documents.find_one({
            "employee_id": emp_id,
            "requirement_id": {"$in": ["dbs_certificate", "dbs_check"]}
        }, {"_id": 0, "expiry_date": 1})
        
        if dbs_doc:
            if dbs_doc.get("expiry_date"):
                try:
                    exp_str = dbs_doc["expiry_date"]
                    if 'T' in str(exp_str):
                        exp_date = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                    else:
                        exp_date = datetime.fromisoformat(f"{exp_str}T00:00:00+00:00")
                    
                    if exp_date < now:
                        dbs_missing += 1  # Expired counts as missing
                    elif exp_date < now + thirty_days:
                        dbs_expiring += 1
                    else:
                        dbs_valid += 1
                except Exception:
                    dbs_valid += 1
            else:
                dbs_valid += 1
        else:
            dbs_missing += 1
        
        # Check recent training
        recent_training = await db.training_records.count_documents({
            "employee_id": emp_id,
            "completion_date": {"$gte": twelve_months_ago}
        })
        if recent_training > 0:
            training_completed_recently += 1
    
    # Calculate overall status
    policies_ok = policies_missing == 0 and policies_overdue == 0
    certs_ok = certs_missing == 0 and certs_expired == 0
    staff_ok = dbs_missing == 0
    
    if policies_ok and certs_ok and staff_ok:
        overall_status = "OK"
    elif (policies_missing > 5 or certs_missing > 3 or dbs_missing > (staff_total * 0.2)):
        overall_status = "Critical"
    else:
        overall_status = "Needs Attention"
    
    return {
        "overall_status": overall_status,
        "policies": {
            "complete": policies_active,
            "total": policies_total,
            "missing": policies_missing,
            "due_soon": policies_due_soon,
            "overdue": policies_overdue,
            "required_complete": policies_required_complete,
            "required_total": policies_required_total
        },
        "certificates": {
            "valid": certs_valid,
            "total": certs_total,
            "missing": certs_missing,
            "expiring": certs_expiring,
            "expired": certs_expired,
            "required_complete": certs_required_complete,
            "required_total": certs_required_total
        },
        "staff_compliance": {
            "total": staff_total,
            "dbs_valid": dbs_valid,
            "dbs_missing": dbs_missing,
            "dbs_expiring": dbs_expiring,
            "training_last_12_months": training_completed_recently
        },
        "missing_items": {
            "required_policies": missing_required_policies[:10],
            "required_certificates": missing_required_certs[:10],
            "has_more_policies": len(missing_required_policies) > 10,
            "has_more_certificates": len(missing_required_certs) > 10
        }
    }



# ==================== CQC EVIDENCE MAPPING ====================
# Read-only mapping layer for CQC inspection readiness
# Maps existing system evidence to CQC 5 Key Questions
# Does NOT change any compliance calculations or employee readiness

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
            {"name": "Induction & Probation Policy", "source_type": "policy", "source_id": "Induction & Probation Policy"},
            {"name": "Supervision & Appraisal Policy", "source_type": "policy", "source_id": "Supervision & Appraisal Policy"},
            {"name": "Care Planning Policy", "source_type": "policy", "source_id": "Care Planning Policy"},
            {"name": "Nutrition & Hydration Policy", "source_type": "policy", "source_id": "Nutrition & Hydration Policy"},
            {"name": "Mental Capacity Act & DoLS Policy", "source_type": "policy", "source_id": "Mental Capacity Act & DoLS Policy"},
            # Registers & Summaries
            {"name": "Training Matrix", "source_type": "register", "source_id": "training_matrix"},
            {"name": "Staff Training Records", "source_type": "register", "source_id": "training_records"},
            # Forms
            {"name": "Induction & Competency Assessments", "source_type": "form", "source_id": "induction"},
            {"name": "Recruitment Checklists", "source_type": "form", "source_id": "recruitment_checklist"},
            {"name": "Interview Records", "source_type": "form", "source_id": "interview_record"},
        ]
    },
    "caring": {
        "title": "Caring",
        "description": "Staff involve and treat people with compassion, kindness, dignity and respect",
        "items": [
            # Policies
            {"name": "Equality, Diversity & Inclusion Policy", "source_type": "policy", "source_id": "Equality, Diversity & Inclusion Policy"},
            {"name": "Confidentiality Policy", "source_type": "policy", "source_id": "Confidentiality Policy"},
            {"name": "Pressure Ulcer Prevention Policy", "source_type": "policy", "source_id": "Pressure Ulcer Prevention Policy"},
            {"name": "End of Life Care Policy", "source_type": "policy", "source_id": "End of Life Care Policy"},
            {"name": "Code of Conduct", "source_type": "policy", "source_id": "Code of Conduct"},
            # Forms
            {"name": "Equal Opportunities Monitoring", "source_type": "form", "source_id": "equal_opportunities"},
            # Training
            {"name": "Person-Centred Care Training", "source_type": "training", "source_id": "person_centred_care"},
            {"name": "Dignity in Care Training", "source_type": "training", "source_id": "dignity_care"},
        ]
    },
    "responsive": {
        "title": "Responsive",
        "description": "Services are organised to meet people's needs",
        "items": [
            # Policies
            {"name": "Complaints Policy", "source_type": "policy", "source_id": "Complaints Policy"},
            {"name": "Business Continuity Policy", "source_type": "policy", "source_id": "Business Continuity Policy"},
            {"name": "Incident Reporting Policy", "source_type": "policy", "source_id": "Incident Reporting Policy"},
            {"name": "Service User Feedback Policy", "source_type": "policy", "source_id": "Service User Feedback Policy"},
            {"name": "Record Keeping Policy", "source_type": "policy", "source_id": "Record Keeping Policy"},
            # Reports/Logs
            {"name": "Complaints Log", "source_type": "report", "source_id": "complaints"},
            {"name": "Incident Reports", "source_type": "report", "source_id": "incidents"},
            # Certificates (Conditional)
            {"name": "Food Hygiene Rating", "source_type": "certificate", "source_id": "food_hygiene", "conditional": True},
        ]
    },
    "well_led": {
        "title": "Well-led",
        "description": "Leadership, management and governance assure high-quality, person-centred care",
        "items": [
            # Policies
            {"name": "Recruitment & Selection Policy", "source_type": "policy", "source_id": "Recruitment & Selection Policy"},
            {"name": "DBS & Vetting Policy", "source_type": "policy", "source_id": "DBS & Vetting Policy"},
            {"name": "Disciplinary & Grievance Policy", "source_type": "policy", "source_id": "Disciplinary & Grievance Policy"},
            {"name": "Data Protection & GDPR Policy", "source_type": "policy", "source_id": "Data Protection & GDPR Policy"},
            {"name": "Whistleblowing Policy", "source_type": "policy", "source_id": "Whistleblowing Policy"},
            # Certificates
            {"name": "CQC Registration Certificate", "source_type": "certificate", "source_id": "cqc_registration"},
            {"name": "ICO Registration Certificate", "source_type": "certificate", "source_id": "ico_registration"},
            {"name": "Public Liability Insurance", "source_type": "certificate", "source_id": "public_liability"},
            {"name": "Employer's Liability Insurance", "source_type": "certificate", "source_id": "employers_liability"},
            {"name": "Professional Indemnity Insurance", "source_type": "certificate", "source_id": "professional_indemnity"},
            {"name": "Company Registration Certificate", "source_type": "certificate", "source_id": "company_registration"},
            # Reports/Audits
            {"name": "Audit Trail / Amendment History", "source_type": "report", "source_id": "audit_trail"},
            {"name": "Policy Review Schedule", "source_type": "report", "source_id": "policy_reviews"},
        ]
    }
}


@api_router.get("/compliance/cqc-evidence-map")
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
        count = await db.form_submissions.count_documents({"requirement_id": form_type})
        form_counts[form_type] = count
    
    # Get incident counts
    incident_count = await db.incident_logs.count_documents({})
    open_incidents = await db.incident_logs.count_documents({"status": {"$in": ["open", "under_investigation"]}})
    
    # Get staff counts
    total_staff = await db.employees.count_documents({"status": {"$ne": "archived"}})
    
    # Get DBS summary
    dbs_valid = 0
    dbs_missing = 0
    employees = await db.employees.find({"status": {"$ne": "archived"}}, {"_id": 0, "id": 1}).to_list(1000)
    for emp in employees:
        dbs_doc = await db.employee_documents.find_one({
            "employee_id": emp["id"],
            "requirement_id": {"$in": ["dbs_certificate", "dbs_check"]}
        })
        if dbs_doc:
            dbs_valid += 1
        else:
            dbs_missing += 1
    
    # Get RTW summary
    rtw_approved = 0
    for emp in employees:
        rtw_docs = await db.employee_documents.count_documents({
            "employee_id": emp["id"],
            "requirement_id": {"$in": ["right_to_work_documents", "right_to_work_check"]}
        })
        if rtw_docs > 0:
            rtw_approved += 1
    
    # Get training summary
    training_count = await db.training_records.count_documents({})
    twelve_months_ago = (now - timedelta(days=365)).isoformat()
    recent_training = await db.training_records.count_documents({"completion_date": {"$gte": twelve_months_ago}})
    
    # Get policy review stats
    policies_due_review = 0
    policies_overdue = 0
    for p in policies:
        if p.get("review_date"):
            try:
                review_str = p["review_date"]
                if 'T' in str(review_str):
                    review_date = datetime.fromisoformat(review_str.replace('Z', '+00:00'))
                else:
                    review_date = datetime.fromisoformat(f"{review_str}T00:00:00+00:00")
                
                if review_date < now:
                    policies_overdue += 1
                elif review_date < now + thirty_days:
                    policies_due_review += 1
            except Exception:
                pass
    
    # Get audit trail count
    audit_count = await db.audit_log.count_documents({})
    
    # Helper to determine item status
    def get_item_status(item):
        source_type = item["source_type"]
        source_id = item["source_id"]
        status = "missing"
        details = None
        link = None
        review_date = None
        expiry_date = None
        
        if source_type == "policy":
            policy = policies_map.get(source_id)
            if policy:
                if policy.get("status") == "active":
                    status = "present"
                    if policy.get("review_date"):
                        try:
                            review_str = policy["review_date"]
                            if 'T' in str(review_str):
                                rev_date = datetime.fromisoformat(review_str.replace('Z', '+00:00'))
                            else:
                                rev_date = datetime.fromisoformat(f"{review_str}T00:00:00+00:00")
                            review_date = policy["review_date"]
                            if rev_date < now:
                                status = "overdue"
                            elif rev_date < now + thirty_days:
                                status = "due_review"
                        except Exception:
                            pass
                elif policy.get("status") == "expired":
                    status = "expired"
                link = f"/portal/compliance-centre?tab=policies&policy={policy.get('id')}"
                details = f"Version {policy.get('version', 'N/A')}"
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
                        except Exception:
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
                link = "/portal/compliance-centre?tab=reports"
            elif source_id == "training_records":
                if recent_training > 0:
                    status = "present"
                    details = f"{recent_training} in last 12 months"
                else:
                    status = "missing"
                link = "/portal/compliance-centre?tab=reports"
        
        elif source_type == "report":
            if source_id == "incidents":
                if incident_count > 0:
                    status = "present"
                    details = f"{incident_count} logged, {open_incidents} open"
                else:
                    status = "n/a"
                    details = "No incidents logged"
                link = "/portal/compliance-centre?tab=incidents"
            elif source_id == "complaints":
                # Complaints tracked via incidents with type
                complaint_count = 0  # Would need specific query
                status = "n/a"
                details = "Track via Incident Logs"
                link = "/portal/compliance-centre?tab=incidents"
            elif source_id == "audit_trail":
                if audit_count > 0:
                    status = "present"
                    details = f"{audit_count} audit entries"
                else:
                    status = "present"
                    details = "Audit trail active"
                link = "/portal/compliance-centre"
            elif source_id == "policy_reviews":
                status = "present"
                details = f"{policies_due_review} due soon, {policies_overdue} overdue"
                link = "/portal/compliance-centre?tab=policies"
        
        elif source_type == "training":
            # Training types - check if any staff have this training
            status = "n/a"
            details = "Check training records"
            link = "/portal/compliance-centre?tab=reports"
        
        return {
            "name": item["name"],
            "source_type": source_type,
            "status": status,
            "details": details,
            "link": link,
            "review_date": review_date,
            "expiry_date": expiry_date,
            "conditional": item.get("conditional", False)
        }
    
    # Build response
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

# Define compliance-relevant audit actions
COMPLIANCE_AUDIT_ACTIONS = {
    # Document actions
    "upload_evidence", "document_uploaded", "document_replaced", "document_removed", "document_verified",
    "verify_requirement", "unverify_requirement", "delete_evidence", "remove_evidence",
    # Policy actions
    "policy_assigned", "policy_viewed", "policy_acknowledged", "policy_admin_reviewed",
    "policy_uploaded", "policy_unassigned", "policy_withdrawn",
    # Status changes
    "status_change", "refresh_status", "update_employee",
    # Form actions (if they generate evidence)
    "signoff_form", "complete_form",
    # Training
    "upload_training_certificate", "verify_training",
    # Organisation settings
    "org_settings_updated"
}

@api_router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    user_id: Optional[str] = None,
    compliance_only: bool = False,
    limit: int = 100,
    user: dict = Depends(require_manager_or_admin)
):
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    
    # Search by entity_id OR metadata.employee_id
    if entity_id:
        if employee_id:
            query["$or"] = [
                {"entity_id": entity_id},
                {"metadata.employee_id": entity_id},
                {"entity_id": employee_id},
                {"metadata.employee_id": employee_id}
            ]
        else:
            query["$or"] = [
                {"entity_id": entity_id},
                {"metadata.employee_id": entity_id}
            ]
    elif employee_id:
        query["$or"] = [
            {"entity_id": employee_id},
            {"metadata.employee_id": employee_id}
        ]
    
    if user_id:
        query["user_id"] = user_id
    
    # Filter to compliance-relevant actions only
    if compliance_only:
        query["action"] = {"$in": list(COMPLIANCE_AUDIT_ACTIONS)}
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Enrich with user names and transform metadata to details for frontend compatibility
    for log in logs:
        if log.get('user_id'):
            user_doc = await db.users.find_one({"user_id": log['user_id']}, {"_id": 0})
            if user_doc:
                log['user_name'] = user_doc.get('name', 'Unknown')
        # Copy metadata to details for frontend compatibility
        if 'metadata' in log and 'details' not in log:
            log['details'] = log['metadata']
    
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
            "policies_signed": sum(1 for p in policy_assignments if p.get('status') in ['acknowledged', 'signed']),
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
# Comprehensive Organisation Policies organised by category with REQUIRED/CONDITIONAL tags
CORE_POLICIES = [
    # Core Policies - Essential Safeguarding & Safety (ALL REQUIRED by CQC)
    {"name": "Safeguarding Adults Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Safeguarding Children Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Mental Capacity Act & DoLS Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Health & Safety Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Fire Safety Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "First Aid Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Equality, Diversity & Inclusion Policy", "category": "Core", "required": True, "review_period_months": 12},
    {"name": "Whistleblowing Policy", "category": "Core", "required": True, "review_period_months": 12},
    
    # Clinical Policies - Care & Medical (REQUIRED for domiciliary care)
    {"name": "Medication Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Infection Prevention & Control Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Manual Handling Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "COSHH Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Care Planning Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "End of Life Care Policy", "category": "Clinical", "required": False, "conditional": True, "review_period_months": 24},
    {"name": "Nutrition & Hydration Policy", "category": "Clinical", "required": True, "review_period_months": 12},
    {"name": "Pressure Ulcer Prevention Policy", "category": "Clinical", "required": False, "conditional": True, "review_period_months": 24},
    
    # Operational Policies - Day-to-Day Operations (REQUIRED)
    {"name": "Lone Working Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Risk Assessment Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Record Keeping Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Confidentiality Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Complaints Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Incident Reporting Policy", "category": "Operational", "required": True, "review_period_months": 12},
    {"name": "Business Continuity Policy", "category": "Operational", "required": True, "review_period_months": 24},
    {"name": "Service User Feedback Policy", "category": "Operational", "required": True, "review_period_months": 12},
    
    # Governance Policies - HR & Regulatory (REQUIRED)
    {"name": "Recruitment & Selection Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "DBS & Vetting Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Induction & Probation Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Training & Development Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Supervision & Appraisal Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Disciplinary & Grievance Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Data Protection & GDPR Policy", "category": "Governance", "required": True, "review_period_months": 12},
    {"name": "Code of Conduct", "category": "Governance", "required": True, "review_period_months": 12},
]

@api_router.post("/compliance/seed-policies")
async def seed_org_policies(user: dict = Depends(require_admin)):
    """Seed core organisation policies as placeholders with review tracking"""
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
                "required": policy.get("required", True),
                "conditional": policy.get("conditional", False),
                "review_period_months": policy.get("review_period_months", 12),
                "file_url": None,
                "original_filename": None,
                "review_date": None,  # Next review due date
                "last_reviewed_at": None,
                "reviewed_by": None,
                "assigned_staff_count": 0,
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
    """Get all organisation policies with review status tracking"""
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    policies = await db.org_policies.find(query, {"_id": 0}).sort("category", 1).to_list(100)
    
    # Compute review status based on review date and last reviewed
    now = datetime.now(timezone.utc)
    thirty_days = timedelta(days=30)
    
    # Get assignment counts per policy
    assignments_pipeline = [
        {"$match": {"status": {"$ne": "removed"}}},
        {"$group": {"_id": "$policy_id", "count": {"$sum": 1}}}
    ]
    assignment_counts = {}
    try:
        assignments = await db.policy_assignments.aggregate(assignments_pipeline).to_list(1000)
        for a in assignments:
            assignment_counts[a["_id"]] = a["count"]
    except Exception:
        pass
    
    for policy in policies:
        # Update assigned staff count
        policy["assigned_staff_count"] = assignment_counts.get(policy["id"], 0)
        
        # Determine review status
        if policy.get("review_date"):
            try:
                review_str = policy["review_date"]
                if isinstance(review_str, datetime):
                    review_date = review_str if review_str.tzinfo else review_str.replace(tzinfo=timezone.utc)
                elif 'T' in str(review_str):
                    review_date = datetime.fromisoformat(review_str.replace('Z', '+00:00'))
                else:
                    review_date = datetime.fromisoformat(f"{review_str}T00:00:00+00:00")
                
                if review_date < now:
                    policy["review_status"] = "overdue"
                    if policy["status"] == "active":
                        policy["status"] = "expired"
                elif review_date < now + thirty_days:
                    policy["review_status"] = "due_soon"
                else:
                    policy["review_status"] = "current"
            except Exception:
                policy["review_status"] = None
        else:
            policy["review_status"] = None if policy["status"] == "missing" else "current"
    
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

# Insurance & Certificates required for care agency compliance (CQC aligned)
# Structure: Required certificates are mandatory, Conditional depend on service type
COMPLIANCE_CERTIFICATES = [
    # REQUIRED - Insurance (All expire annually)
    {
        "name": "Public Liability Insurance", 
        "type": "public_liability", 
        "category": "insurance", 
        "required": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": True,
        "valid_until_replaced": False,
    },
    {
        "name": "Employer's Liability Insurance", 
        "type": "employers_liability", 
        "category": "insurance", 
        "required": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": True,
        "valid_until_replaced": False,
    },
    {
        "name": "Professional Indemnity Insurance", 
        "type": "professional_indemnity", 
        "category": "insurance", 
        "required": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": True,
        "valid_until_replaced": False,
    },
    
    # REQUIRED - Regulatory Certificates
    {
        "name": "CQC Registration Certificate", 
        "type": "cqc_registration", 
        "category": "regulatory", 
        "required": True, 
        "renewal_period_months": 0,
        "requires_expiry_date": False,  # Valid until replaced/cancelled
        "valid_until_replaced": True,
    },
    {
        "name": "ICO Registration Certificate", 
        "type": "ico_registration", 
        "category": "regulatory", 
        "required": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": True,  # ICO registration expires annually
        "valid_until_replaced": False,
    },
    {
        "name": "Company Registration Certificate", 
        "type": "company_registration", 
        "category": "regulatory", 
        "required": True, 
        "renewal_period_months": 0,
        "requires_expiry_date": False,  # No expiry - valid until company dissolved
        "valid_until_replaced": True,
    },
    
    # REQUIRED - Safety Certificates
    {
        "name": "Fire Safety Certificate", 
        "type": "fire_safety", 
        "category": "safety", 
        "required": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": True,
        "valid_until_replaced": False,
    },
    {
        "name": "Electrical Installation Certificate (EICR)", 
        "type": "electrical_inspection", 
        "category": "safety", 
        "required": True, 
        "renewal_period_months": 60,  # 5 years
        "requires_expiry_date": True,
        "valid_until_replaced": False,
    },
    {
        "name": "Gas Safety Certificate", 
        "type": "gas_safety", 
        "category": "safety", 
        "required": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": True,
        "valid_until_replaced": False,
    },
    {
        "name": "PAT Testing Certificate", 
        "type": "pat_testing", 
        "category": "safety", 
        "required": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": True,
        "valid_until_replaced": False,
    },
    
    # CONDITIONAL - Based on service type
    {
        "name": "Legionella Risk Assessment", 
        "type": "legionella", 
        "category": "safety", 
        "required": False, 
        "conditional": True, 
        "renewal_period_months": 24,
        "requires_expiry_date": False,  # Review-based, not hard expiry
        "review_interval_months": 24,
        "valid_until_replaced": False,
    },
    {
        "name": "Food Hygiene Rating Certificate", 
        "type": "food_hygiene", 
        "category": "safety", 
        "required": False, 
        "conditional": True, 
        "renewal_period_months": 12,
        "requires_expiry_date": False,  # Rating doesn't expire
        "valid_until_replaced": True,
    },
    {
        "name": "Asbestos Survey Report", 
        "type": "asbestos_survey", 
        "category": "safety", 
        "required": False, 
        "conditional": True, 
        "renewal_period_months": 0,
        "requires_expiry_date": False,  # Valid until property changes
        "valid_until_replaced": True,
    },
]

# Legacy compatibility - keep old list for backward compatibility
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
    """Seed insurance and certificate document placeholders (CQC aligned)"""
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    updated = 0
    
    for cert in COMPLIANCE_CERTIFICATES:
        existing = await db.insurance_docs.find_one({"insurance_type": cert["type"]})
        if not existing:
            doc = {
                "id": str(uuid.uuid4()),
                "name": cert["name"],
                "insurance_type": cert["type"],
                "category": cert.get("category", "insurance"),
                "required": cert.get("required", True),
                "conditional": cert.get("conditional", False),
                "renewal_period_months": cert.get("renewal_period_months", 12),
                "requires_expiry_date": cert.get("requires_expiry_date", True),
                "valid_until_replaced": cert.get("valid_until_replaced", False),
                "review_interval_months": cert.get("review_interval_months"),
                "status": "missing",
                "file_url": None,
                "original_filename": None,
                "expiry_date": None,
                "issue_date": None,
                "policy_number": None,
                "provider": None,
                "notes": None,
                "created_at": now,
                "updated_at": now
            }
            await db.insurance_docs.insert_one(doc)
            created += 1
        else:
            # Update existing doc with new config fields
            await db.insurance_docs.update_one(
                {"insurance_type": cert["type"]},
                {"$set": {
                    "requires_expiry_date": cert.get("requires_expiry_date", True),
                    "valid_until_replaced": cert.get("valid_until_replaced", False),
                    "review_interval_months": cert.get("review_interval_months"),
                    "updated_at": now
                }}
            )
            updated += 1
    
    return {"message": f"Created {created}, updated {updated} certificate placeholders", "total": len(COMPLIANCE_CERTIFICATES)}

@api_router.get("/compliance/insurance", response_model=List[InsuranceDocResponse])
async def get_insurance_docs(user: dict = Depends(get_current_user)):
    """Get all insurance documents"""
    docs = await db.insurance_docs.find({}, {"_id": 0}).to_list(20)
    
    # Calculate status based on expiry date
    now = datetime.now(timezone.utc)
    thirty_days = now + timedelta(days=30)
    
    for doc in docs:
        # Ensure requires_expiry_date and valid_until_replaced are always present
        if "requires_expiry_date" not in doc:
            doc["requires_expiry_date"] = True  # Default to requiring expiry
        if "valid_until_replaced" not in doc:
            doc["valid_until_replaced"] = False
        
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
            # No expiry date - valid if file exists (for valid_until_replaced certs)
            doc["status"] = "valid"
    
    return docs

@api_router.post("/compliance/insurance/{insurance_id}/upload")
async def upload_insurance_doc(
    insurance_id: str,
    file: UploadFile = File(...),
    expiry_date: Optional[str] = Query(None),  # Now optional - depends on requires_expiry_date
    policy_number: Optional[str] = None,
    provider: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """Upload an insurance document"""
    insurance = await db.insurance_docs.find_one({"id": insurance_id})
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance record not found")
    
    # Check if expiry date is required for this certificate type
    requires_expiry = insurance.get("requires_expiry_date", True)
    if requires_expiry and not expiry_date:
        raise HTTPException(status_code=400, detail="Expiry date is required for this certificate type")
    
    now = datetime.now(timezone.utc).isoformat()
    
    content = await file.read()
    path = f"{APP_NAME}/insurance/{insurance_id}/{str(uuid.uuid4())}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"
    result = put_object(path, content, content_type)
    
    update_data = {
        "file_url": result["path"],
        "original_filename": file.filename,
        "status": "valid",
        "updated_at": now
    }
    
    # Only set expiry_date if provided (certificates that don't require expiry won't have one)
    if expiry_date:
        update_data["expiry_date"] = expiry_date
    
    if policy_number:
        update_data["policy_number"] = policy_number
    if provider:
        update_data["provider"] = provider
    
    await db.insurance_docs.update_one({"id": insurance_id}, {"$set": update_data})
    
    await log_audit_action(user['user_id'], "upload_insurance", "insurance", insurance_id, {
        "filename": file.filename,
        "expiry_date": expiry_date or "N/A (valid until replaced)"
    })
    
    updated = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0})
    return updated




# ==================== DOCUMENT REPLACEMENT & REMOVAL ENDPOINTS ====================

@api_router.post("/compliance/insurance/{insurance_id}/replace")
async def replace_insurance_doc(
    insurance_id: str,
    file: UploadFile = File(...),
    reason: str = Query(..., description="Reason for replacement"),
    expiry_date: Optional[str] = Query(None),
    policy_number: Optional[str] = None,
    provider: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Replace an insurance document with full audit trail.
    Stores the previous file info in history before uploading new file.
    """
    insurance = await db.insurance_docs.find_one({"id": insurance_id})
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance record not found")
    
    # Check if expiry date is required for this certificate type
    requires_expiry = insurance.get("requires_expiry_date", True)
    if requires_expiry and not expiry_date:
        raise HTTPException(status_code=400, detail="Expiry date is required for this certificate type")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Capture the previous state (for history tracking)
    previous_state = {
        "file_url": insurance.get("file_url"),
        "original_filename": insurance.get("original_filename"),
        "expiry_date": insurance.get("expiry_date"),
        "policy_number": insurance.get("policy_number"),
        "provider": insurance.get("provider"),
        "status": insurance.get("status"),
        "replaced_at": now,
        "replaced_by": user['user_id'],
        "replacement_reason": reason,
        "action": "replaced"
    }
    
    # Upload new file
    content = await file.read()
    path = f"{APP_NAME}/insurance/{insurance_id}/{str(uuid.uuid4())}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"
    result = put_object(path, content, content_type)
    
    update_data = {
        "file_url": result["path"],
        "original_filename": file.filename,
        "status": "valid",
        "updated_at": now
    }
    
    if expiry_date:
        update_data["expiry_date"] = expiry_date
    if policy_number:
        update_data["policy_number"] = policy_number
    if provider:
        update_data["provider"] = provider
    
    # Push previous state to history and update with new file
    await db.insurance_docs.update_one(
        {"id": insurance_id},
        {
            "$push": {"history": previous_state},
            "$set": update_data
        }
    )
    
    await log_audit_action(user['user_id'], "replace_insurance", "insurance", insurance_id, {
        "reason": reason,
        "old_filename": previous_state.get("original_filename"),
        "new_filename": file.filename
    })
    
    updated = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0})
    return updated


@api_router.delete("/compliance/insurance/{insurance_id}/file")
async def remove_insurance_file(
    insurance_id: str,
    reason: str = Query(..., description="Reason for removal"),
    user: dict = Depends(require_admin)
):
    """
    Remove an insurance document file (marks as missing, keeps history).
    Use this to correct an accidental upload.
    """
    insurance = await db.insurance_docs.find_one({"id": insurance_id})
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance record not found")
    
    if not insurance.get("file_url"):
        raise HTTPException(status_code=400, detail="No file to remove")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Capture the previous state (for history tracking)
    previous_state = {
        "file_url": insurance.get("file_url"),
        "original_filename": insurance.get("original_filename"),
        "expiry_date": insurance.get("expiry_date"),
        "status": insurance.get("status"),
        "removed_at": now,
        "removed_by": user['user_id'],
        "removal_reason": reason,
        "action": "removed"
    }
    
    # Clear file and mark as missing
    update_data = {
        "file_url": None,
        "original_filename": None,
        "status": "missing",
        "updated_at": now
    }
    
    await db.insurance_docs.update_one(
        {"id": insurance_id},
        {
            "$push": {"history": previous_state},
            "$set": update_data
        }
    )
    
    await log_audit_action(user['user_id'], "remove_insurance_file", "insurance", insurance_id, {
        "reason": reason,
        "removed_filename": previous_state.get("original_filename")
    })
    
    return {"message": "File removed successfully", "status": "missing"}


@api_router.post("/compliance/policies/{policy_id}/replace")
async def replace_org_policy_doc(
    policy_id: str,
    file: UploadFile = File(...),
    reason: str = Query(..., description="Reason for replacement"),
    version: Optional[str] = None,
    review_date: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Replace an organisation policy document with full audit trail.
    Stores the previous file info in history before uploading new file.
    """
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Capture the previous state (for history tracking)
    previous_state = {
        "file_url": policy.get("file_url"),
        "original_filename": policy.get("original_filename"),
        "version": policy.get("version"),
        "review_date": policy.get("review_date"),
        "status": policy.get("status"),
        "replaced_at": now,
        "replaced_by": user['user_id'],
        "replacement_reason": reason,
        "action": "replaced"
    }
    
    # Upload new file
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
    
    # Push previous state to history and update with new file
    await db.org_policies.update_one(
        {"id": policy_id},
        {
            "$push": {"history": previous_state},
            "$set": update_data
        }
    )
    
    await log_audit_action(user['user_id'], "replace_policy", "org_policy", policy_id, {
        "reason": reason,
        "old_filename": previous_state.get("original_filename"),
        "new_filename": file.filename
    })
    
    updated = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    return updated


@api_router.delete("/compliance/policies/{policy_id}/file")
async def remove_org_policy_file(
    policy_id: str,
    reason: str = Query(..., description="Reason for removal"),
    user: dict = Depends(require_admin)
):
    """
    Remove an organisation policy document file (marks as missing, keeps history).
    Use this to correct an accidental upload.
    """
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if not policy.get("file_url"):
        raise HTTPException(status_code=400, detail="No file to remove")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Capture the previous state (for history tracking)
    previous_state = {
        "file_url": policy.get("file_url"),
        "original_filename": policy.get("original_filename"),
        "version": policy.get("version"),
        "status": policy.get("status"),
        "removed_at": now,
        "removed_by": user['user_id'],
        "removal_reason": reason,
        "action": "removed"
    }
    
    # Clear file and mark as missing
    update_data = {
        "file_url": None,
        "original_filename": None,
        "status": "missing",
        "updated_at": now
    }
    
    await db.org_policies.update_one(
        {"id": policy_id},
        {
            "$push": {"history": previous_state},
            "$set": update_data
        }
    )
    
    await log_audit_action(user['user_id'], "remove_policy_file", "org_policy", policy_id, {
        "reason": reason,
        "removed_filename": previous_state.get("original_filename")
    })
    
    return {"message": "File removed successfully", "status": "missing"}


# ==================== AMENDMENT ENDPOINTS (with history tracking) ====================

@api_router.put("/compliance/insurance/{insurance_id}/amend")
async def amend_insurance_doc(
    insurance_id: str,
    update: InsuranceDocUpdate,
    user: dict = Depends(require_admin)
):
    """
    Amend an insurance/certificate record with full audit trail.
    Stores previous state in history array and requires a reason.
    """
    insurance = await db.insurance_docs.find_one({"id": insurance_id})
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Capture the previous state (excluding _id and history)
    previous_state = {k: v for k, v in insurance.items() if k not in ['_id', 'history']}
    previous_state['amended_at'] = now
    previous_state['amended_by'] = user['user_id']
    previous_state['amendment_reason'] = update.reason
    
    # Build update dict from non-null fields (excluding reason)
    update_fields = {}
    if update.name is not None:
        update_fields['name'] = update.name
    if update.expiry_date is not None:
        update_fields['expiry_date'] = update.expiry_date
    if update.policy_number is not None:
        update_fields['policy_number'] = update.policy_number
    if update.provider is not None:
        update_fields['provider'] = update.provider
    if update.issue_date is not None:
        update_fields['issue_date'] = update.issue_date
    if update.notes is not None:
        update_fields['notes'] = update.notes
    
    update_fields['updated_at'] = now
    
    # Push previous state to history array and update document
    await db.insurance_docs.update_one(
        {"id": insurance_id},
        {
            "$push": {"history": previous_state},
            "$set": update_fields
        }
    )
    
    # Log to audit trail with old and new values
    await log_audit_action(user['user_id'], "amend_insurance", "insurance", insurance_id, {
        "reason": update.reason,
        "changes": update_fields,
        "previous_values": {k: previous_state.get(k) for k in update_fields.keys() if k != 'updated_at'}
    })
    
    updated = await db.insurance_docs.find_one({"id": insurance_id}, {"_id": 0})
    return updated


@api_router.get("/compliance/insurance/{insurance_id}/history")
async def get_insurance_history(
    insurance_id: str,
    user: dict = Depends(get_current_user)
):
    """Get amendment history for an insurance/certificate record"""
    insurance = await db.insurance_docs.find_one({"id": insurance_id})
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance record not found")
    
    history = insurance.get('history', [])
    # Sort by amended_at descending (most recent first)
    history = sorted(history, key=lambda x: x.get('amended_at', ''), reverse=True)
    
    return {"history": history, "total": len(history)}


@api_router.put("/compliance/policies/{policy_id}/amend")
async def amend_org_policy(
    policy_id: str,
    update: OrgPolicyAmend,
    user: dict = Depends(require_admin)
):
    """
    Amend an organisation policy record with full audit trail.
    Stores previous state in history array and requires a reason.
    """
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Capture the previous state (excluding _id and history)
    previous_state = {k: v for k, v in policy.items() if k not in ['_id', 'history']}
    previous_state['amended_at'] = now
    previous_state['amended_by'] = user['user_id']
    previous_state['amendment_reason'] = update.reason
    
    # Build update dict from non-null fields (excluding reason)
    update_fields = {}
    if update.name is not None:
        update_fields['name'] = update.name
    if update.category is not None:
        update_fields['category'] = update.category
    if update.version is not None:
        update_fields['version'] = update.version
    if update.review_date is not None:
        update_fields['review_date'] = update.review_date
    if update.notes is not None:
        update_fields['notes'] = update.notes
    
    update_fields['updated_at'] = now
    
    # Push previous state to history array and update document
    await db.org_policies.update_one(
        {"id": policy_id},
        {
            "$push": {"history": previous_state},
            "$set": update_fields
        }
    )
    
    # Log to audit trail with old and new values
    await log_audit_action(user['user_id'], "amend_policy", "org_policy", policy_id, {
        "reason": update.reason,
        "changes": update_fields,
        "previous_values": {k: previous_state.get(k) for k in update_fields.keys() if k != 'updated_at'}
    })
    
    updated = await db.org_policies.find_one({"id": policy_id}, {"_id": 0})
    return updated


@api_router.get("/compliance/policies/{policy_id}/history")
async def get_policy_history(
    policy_id: str,
    user: dict = Depends(get_current_user)
):
    """Get amendment history for an organisation policy"""
    policy = await db.org_policies.find_one({"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    history = policy.get('history', [])
    # Sort by amended_at descending (most recent first)
    history = sorted(history, key=lambda x: x.get('amended_at', ''), reverse=True)
    
    return {"history": history, "total": len(history)}


@api_router.put("/compliance/incidents/{incident_id}/amend")
async def amend_incident_log(
    incident_id: str,
    update: IncidentLogAmend,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Amend an incident log with full audit trail.
    Stores previous state in history array and requires a reason.
    """
    incident = await db.incident_logs.find_one({"id": incident_id})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Capture the previous state (excluding _id and history)
    previous_state = {k: v for k, v in incident.items() if k not in ['_id', 'history']}
    previous_state['amended_at'] = now
    previous_state['amended_by'] = user['user_id']
    previous_state['amendment_reason'] = update.reason
    
    # Build update dict from non-null fields (excluding reason)
    update_fields = {}
    if update.title is not None:
        update_fields['title'] = update.title
    if update.description is not None:
        update_fields['description'] = update.description
    if update.incident_type is not None:
        update_fields['incident_type'] = update.incident_type
    if update.date_occurred is not None:
        update_fields['date_occurred'] = update.date_occurred
    if update.location is not None:
        update_fields['location'] = update.location
    if update.persons_involved is not None:
        update_fields['persons_involved'] = update.persons_involved
    if update.immediate_actions is not None:
        update_fields['immediate_actions'] = update.immediate_actions
    if update.root_cause is not None:
        update_fields['root_cause'] = update.root_cause
    if update.corrective_actions is not None:
        update_fields['corrective_actions'] = update.corrective_actions
    if update.lessons_learned is not None:
        update_fields['lessons_learned'] = update.lessons_learned
    
    update_fields['updated_at'] = now
    
    # Push previous state to history array and update document
    await db.incident_logs.update_one(
        {"id": incident_id},
        {
            "$push": {"history": previous_state},
            "$set": update_fields
        }
    )
    
    # Log to audit trail with old and new values
    await log_audit_action(user['user_id'], "amend_incident", "incident_log", incident_id, {
        "reason": update.reason,
        "changes": update_fields,
        "previous_values": {k: previous_state.get(k) for k in update_fields.keys() if k != 'updated_at'}
    })
    
    updated = await db.incident_logs.find_one({"id": incident_id}, {"_id": 0})
    return updated


@api_router.get("/compliance/incidents/{incident_id}/history")
async def get_incident_history(
    incident_id: str,
    user: dict = Depends(get_current_user)
):
    """Get amendment history for an incident log"""
    incident = await db.incident_logs.find_one({"id": incident_id})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    history = incident.get('history', [])
    # Sort by amended_at descending (most recent first)
    history = sorted(history, key=lambda x: x.get('amended_at', ''), reverse=True)
    
    return {"history": history, "total": len(history)}


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


# ============================================================================
# TRAINING MATRIX EXPORT
# Reuses: training_records, MANDATORY_ITEMS["training"], compute_training_record_status()
# New: Export endpoint returning CSV or PDF
# ============================================================================

@api_router.get("/training-matrix/export")
async def export_training_matrix(
    format: str = "csv",  # csv or pdf
    user: dict = Depends(get_current_user)
):
    """
    Export Training Matrix as CSV or PDF.
    
    REUSES:
    - training_records collection (existing data)
    - MANDATORY_ITEMS["training"] (training type definitions)
    - compute_training_record_status() (expiry/status logic)
    - ReportLab (PDF generation - already imported)
    
    NO NEW COLLECTIONS - pure export layer
    """
    import csv
    import io
    
    now = datetime.now(timezone.utc)
    
    # Get all training types from MANDATORY_ITEMS (single source of truth)
    training_types = MANDATORY_ITEMS.get("training", [])
    nurse_training = [t for t in MANDATORY_ITEMS.get("nurse_specific", []) if t.get("type") == "training"]
    all_training_types = training_types + nurse_training
    
    # Build column headers from training types
    training_columns = [{"id": t["id"], "name": t.get("training_name", t["name"])} for t in all_training_types]
    
    # Get all active employees
    employees = await db.employees.find(
        {"status": {"$in": ["active", "onboarding"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "employee_code": 1, "role": 1}
    ).to_list(500)
    
    # Build matrix data
    matrix_data = []
    for emp in employees:
        # Get employee's training records
        training_records = await db.training_records.find(
            {"employee_id": emp["id"], "record_status": {"$nin": ["deleted", "superseded"]}},
            {"_id": 0}
        ).to_list(100)
        
        # Create lookup by training name/id
        training_lookup = {}
        for record in training_records:
            key = record.get("requirement_id") or record.get("training_name", "").lower().replace(" ", "_")
            if key not in training_lookup or record.get("completion_date"):
                training_lookup[key] = record
        
        # Build row
        row = {
            "employee_code": emp.get("employee_code", ""),
            "name": f"{emp['first_name']} {emp['last_name']}",
            "role": emp.get("role", ""),
            "training": {}
        }
        
        for col in training_columns:
            training_id = col["id"]
            training_name = col["name"]
            
            # Find matching record (by id or name)
            record = training_lookup.get(training_id)
            if not record:
                # Try matching by training name
                for key, rec in training_lookup.items():
                    if rec.get("training_name", "").lower() == training_name.lower():
                        record = rec
                        break
            
            if record and record.get("status") == "completed":
                # Use existing compute_training_record_status() logic inline
                expiry_date = record.get("expiry_date")
                completion_date = record.get("completion_date")
                status = "completed"
                expiry_display = ""
                
                if expiry_date:
                    try:
                        if isinstance(expiry_date, str):
                            if 'T' in expiry_date:
                                exp = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                            else:
                                exp = datetime.fromisoformat(f"{expiry_date}T00:00:00+00:00")
                        else:
                            exp = expiry_date if expiry_date.tzinfo else expiry_date.replace(tzinfo=timezone.utc)
                        
                        days_until = (exp - now).days
                        expiry_display = exp.strftime("%d/%m/%Y")
                        
                        if days_until < 0:
                            status = "expired"
                        elif days_until <= 30:
                            status = "expiring"
                    except:
                        pass
                
                row["training"][training_id] = {
                    "status": status,
                    "expiry": expiry_display,
                    "verified": record.get("verified", False)
                }
            else:
                row["training"][training_id] = {
                    "status": "missing",
                    "expiry": "",
                    "verified": False
                }
        
        matrix_data.append(row)
    
    # Generate export based on format
    if format.lower() == "csv":
        # CSV Export
        output = io.StringIO()
        
        # Headers
        headers = ["Employee Code", "Name", "Role"]
        for col in training_columns:
            headers.append(f"{col['name']} Status")
            headers.append(f"{col['name']} Expiry")
        
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # Data rows
        for row in matrix_data:
            csv_row = [row["employee_code"], row["name"], row["role"]]
            for col in training_columns:
                training_data = row["training"].get(col["id"], {})
                status = training_data.get("status", "missing")
                expiry = training_data.get("expiry", "")
                verified = training_data.get("verified", False)
                
                # Status display
                if status == "completed":
                    status_display = "✓ Verified" if verified else "✓ Complete"
                elif status == "expired":
                    status_display = "✗ Expired"
                elif status == "expiring":
                    status_display = "⚠ Expiring"
                else:
                    status_display = "— Missing"
                
                csv_row.append(status_display)
                csv_row.append(expiry)
            
            writer.writerow(csv_row)
        
        # Return CSV
        csv_content = output.getvalue()
        filename = f"training_matrix_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format.lower() == "pdf":
        # PDF Export using existing ReportLab infrastructure
        buffer = io.BytesIO()
        
        # Create PDF with landscape A4
        from reportlab.lib.pagesizes import A4, landscape
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                               leftMargin=15*mm, rightMargin=15*mm, 
                               topMargin=20*mm, bottomMargin=20*mm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            alignment=TA_CENTER
        )
        elements.append(Paragraph("Training Matrix", title_style))
        elements.append(Paragraph(f"Generated: {now.strftime('%d/%m/%Y %H:%M')}", 
                                 ParagraphStyle('Date', fontSize=10, alignment=TA_CENTER, spaceAfter=20)))
        
        # Build table data
        # Simplified headers for PDF (just training names, not status/expiry separate columns)
        pdf_headers = ["Staff Member", "Role"]
        for col in training_columns:
            # Shorten long names
            name = col["name"]
            if len(name) > 12:
                name = name[:10] + "..."
            pdf_headers.append(name)
        
        table_data = [pdf_headers]
        
        for row in matrix_data:
            pdf_row = [
                Paragraph(row["name"], ParagraphStyle('Cell', fontSize=7)),
                Paragraph(row["role"] or "", ParagraphStyle('Cell', fontSize=7))
            ]
            
            for col in training_columns:
                training_data = row["training"].get(col["id"], {})
                status = training_data.get("status", "missing")
                expiry = training_data.get("expiry", "")
                verified = training_data.get("verified", False)
                
                # Compact cell content
                if status == "completed":
                    cell_text = f"✓ {expiry}" if expiry else "✓"
                    if verified:
                        cell_text = f"✓✓ {expiry}" if expiry else "✓✓"
                elif status == "expired":
                    cell_text = f"✗ {expiry}" if expiry else "✗"
                elif status == "expiring":
                    cell_text = f"⚠ {expiry}" if expiry else "⚠"
                else:
                    cell_text = "—"
                
                pdf_row.append(Paragraph(cell_text, ParagraphStyle('Cell', fontSize=6, alignment=TA_CENTER)))
            
            table_data.append(pdf_row)
        
        # Calculate column widths
        available_width = landscape(A4)[0] - 30*mm
        name_width = 70*mm
        role_width = 50*mm
        remaining = available_width - name_width - role_width
        training_col_width = remaining / len(training_columns) if training_columns else 30*mm
        
        col_widths = [name_width, role_width] + [training_col_width] * len(training_columns)
        
        # Create table
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style table
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.18, 0.49, 0.2)),  # Green header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ])
        
        # Add conditional formatting for status
        for row_idx, row in enumerate(matrix_data, start=1):
            for col_idx, col in enumerate(training_columns, start=2):
                training_data = row["training"].get(col["id"], {})
                status = training_data.get("status", "missing")
                
                if status == "expired":
                    table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.Color(1, 0.9, 0.9))
                elif status == "expiring":
                    table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.Color(1, 0.95, 0.8))
                elif status == "missing":
                    table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.Color(0.95, 0.95, 0.95))
        
        table.setStyle(table_style)
        elements.append(table)
        
        # Legend
        elements.append(Spacer(1, 10*mm))
        legend_style = ParagraphStyle('Legend', fontSize=8, spaceAfter=4)
        elements.append(Paragraph("<b>Legend:</b> ✓✓ = Verified | ✓ = Complete | ⚠ = Expiring Soon | ✗ = Expired | — = Missing", legend_style))
        elements.append(Paragraph(f"<i>Total Staff: {len(matrix_data)}</i>", legend_style))
        
        # Add verification stamp (reuses existing infrastructure)
        verification_stamp = generate_verification_stamp(
            verified_by=user.get('name', user.get('email', 'System')),
            verified_at=now.isoformat(),
            document_type="Training Matrix",
            include_hash=True,
            content_bytes=f"training_matrix_{len(matrix_data)}_{now.isoformat()}".encode()
        )
        stamp_elements = create_verification_footer_elements(verification_stamp)
        elements.extend(stamp_elements)
        
        # Build PDF
        doc.build(elements)
        
        pdf_content = buffer.getvalue()
        filename = f"training_matrix_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'pdf'")



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

# ==================== EMAIL NOTIFICATION ENGINE ====================
# Automated notifications for compliance and recruitment triggers

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@osabea.care')
PORTAL_URL = os.environ.get('PORTAL_URL', 'https://caretrust-portal.preview.emergentagent.com')

# Notification Types Enum
class NotificationType:
    # Recruitment triggers
    CV_GAP_DETECTED = "cv_gap_detected"
    REFERENCE_NOT_VERIFIED = "reference_not_verified"
    REFERENCE_MISMATCH = "reference_mismatch"
    MISSING_PROOF_OF_ADDRESS = "missing_proof_of_address"
    
    # Compliance triggers
    DOCUMENT_EXPIRING_60_DAYS = "document_expiring_60_days"
    DOCUMENT_EXPIRING_30_DAYS = "document_expiring_30_days"
    TRAINING_EXPIRED = "training_expired"
    MISSING_MANDATORY_ITEM = "missing_mandatory_item"
    UNVERIFIED_SUBMISSION = "unverified_submission"

# Email Templates for Notifications
NOTIFICATION_TEMPLATES = {
    NotificationType.CV_GAP_DETECTED: {
        "subject": "Employment Gap Requires Explanation - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Employment Gap Detected</h2>
            <p>Dear {employee_name},</p>
            <p>We have identified a gap in your employment history that requires explanation:</p>
            <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
                <strong>Gap Period:</strong> {gap_start} to {gap_end}<br>
                <strong>Duration:</strong> {gap_days} days<br>
                <strong>Between:</strong> {previous_job} → {next_job}
            </div>
            <p>Please log in to provide an explanation for this gap:</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Explain Gap</a></p>
            <p>If you have questions, please contact your recruitment manager.</p>
            <p>Kind regards,<br><strong>Osabea Healthcare Solutions</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">CV Gap Alert: {employee_name}</h2>
            <p>An employment gap has been detected for <strong>{employee_name}</strong>:</p>
            <div style="background: #f8f9fa; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
                <strong>Gap Period:</strong> {gap_start} to {gap_end}<br>
                <strong>Duration:</strong> {gap_days} days<br>
                <strong>Between:</strong> {previous_job} → {next_job}
            </div>
            <p>The employee has been notified to provide an explanation.</p>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Employee Profile</a></p>
        </div>
        """
    },
    
    NotificationType.REFERENCE_NOT_VERIFIED: {
        "subject": "Reference Verification Required - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Reference Verification Required</h2>
            <p>Dear {employee_name},</p>
            <p>Your reference from <strong>{reference_name}</strong> at <strong>{reference_company}</strong> requires verification.</p>
            <p>Please ensure your reference contact details are correct and that your referee is available to respond.</p>
            <div style="background: #e8f4f8; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
                <strong>Reference:</strong> {reference_name}<br>
                <strong>Company:</strong> {reference_company}
            </div>
            <p>If your referee has changed, please update your details in the portal:</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Update Reference</a></p>
            <p>Kind regards,<br><strong>Osabea Healthcare Solutions</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Reference Pending: {employee_name}</h2>
            <p>Reference {reference_num} for <strong>{employee_name}</strong> requires verification:</p>
            <div style="background: #f8f9fa; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
                <strong>Referee:</strong> {reference_name}<br>
                <strong>Company:</strong> {reference_company}
            </div>
            <p><a href="{admin_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Reference</a></p>
        </div>
        """
    },
    
    NotificationType.REFERENCE_MISMATCH: {
        "subject": "Reference Does Not Match CV - {employee_name}",
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Reference Mismatch Alert</h2>
            <p>A reference for <strong>{employee_name}</strong> does not match their CV:</p>
            <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
                <strong>Reference {reference_num}:</strong> {reference_name} at {reference_company}<br>
                <strong>Status:</strong> Does not match CV - requires justification
            </div>
            <p>Please review and document the justification for this mismatch.</p>
            <p><a href="{admin_link}" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Review Now</a></p>
        </div>
        """
    },
    
    NotificationType.MISSING_PROOF_OF_ADDRESS: {
        "subject": "Proof of Address Required - {employee_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Proof of Address Required</h2>
            <p>Dear {employee_name},</p>
            <p>To complete your compliance file, we require <strong>2 separate proof of address documents</strong> (NHS Standard).</p>
            <div style="background: #e8f4f8; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
                <strong>Current Status:</strong> {current_count}/2 documents uploaded<br>
                <strong>Accepted Documents:</strong><br>
                • Utility bill (gas, electric, water)<br>
                • Bank statement<br>
                • Council tax bill<br>
                • Tenancy agreement
            </div>
            <p>Please upload the required documents:</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Upload Documents</a></p>
            <p>Kind regards,<br><strong>Osabea Healthcare Solutions</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Missing Proof of Address: {employee_name}</h2>
            <p><strong>{employee_name}</strong> has insufficient proof of address documents:</p>
            <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
                <strong>Required:</strong> 2 documents<br>
                <strong>Uploaded:</strong> {current_count}<br>
                <strong>Verified:</strong> {verified_count}
            </div>
            <p>The employee has been notified to upload additional documents.</p>
        </div>
        """
    },
    
    NotificationType.DOCUMENT_EXPIRING_60_DAYS: {
        "subject": "Document Expiring in 60 Days - {document_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ffc107;">Document Expiring Soon</h2>
            <p>Dear {employee_name},</p>
            <p>The following document will expire in <strong>60 days</strong>:</p>
            <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
                <strong>Document:</strong> {document_name}<br>
                <strong>Expiry Date:</strong> {expiry_date}
            </div>
            <p>Please renew this document and upload the new version before it expires.</p>
            <p><a href="{portal_link}" style="background: #ffc107; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Upload Renewal</a></p>
            <p>Kind regards,<br><strong>Osabea Healthcare Solutions</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ffc107;">Expiry Alert (60 Days): {employee_name}</h2>
            <p>Document expiring for <strong>{employee_name}</strong>:</p>
            <div style="background: #fef3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
                <strong>Document:</strong> {document_name}<br>
                <strong>Expiry Date:</strong> {expiry_date}
            </div>
            <p>The employee has been notified.</p>
        </div>
        """
    },
    
    NotificationType.DOCUMENT_EXPIRING_30_DAYS: {
        "subject": "URGENT: Document Expiring in 30 Days - {document_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Urgent: Document Expiring Soon</h2>
            <p>Dear {employee_name},</p>
            <p>The following document will expire in <strong>30 days</strong>:</p>
            <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
                <strong>Document:</strong> {document_name}<br>
                <strong>Expiry Date:</strong> {expiry_date}
            </div>
            <p><strong>Action Required:</strong> Please renew this document immediately to avoid compliance issues.</p>
            <p><a href="{portal_link}" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Upload Renewal Now</a></p>
            <p>Kind regards,<br><strong>Osabea Healthcare Solutions</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">URGENT Expiry Alert (30 Days): {employee_name}</h2>
            <p>Document expiring soon for <strong>{employee_name}</strong>:</p>
            <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
                <strong>Document:</strong> {document_name}<br>
                <strong>Expiry Date:</strong> {expiry_date}
            </div>
            <p>The employee has been notified urgently.</p>
        </div>
        """
    },
    
    NotificationType.TRAINING_EXPIRED: {
        "subject": "Training Expired - Action Required - {training_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Training Expired</h2>
            <p>Dear {employee_name},</p>
            <p>Your training certification has <strong>expired</strong>:</p>
            <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
                <strong>Training:</strong> {training_name}<br>
                <strong>Expired On:</strong> {expiry_date}
            </div>
            <p><strong>You cannot work until this training is renewed.</strong> Please complete the refresher training and upload your new certificate.</p>
            <p><a href="{portal_link}" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Upload Certificate</a></p>
            <p>Kind regards,<br><strong>Osabea Healthcare Solutions</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">Training Expired: {employee_name}</h2>
            <p><strong>{employee_name}</strong> has expired training:</p>
            <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0;">
                <strong>Training:</strong> {training_name}<br>
                <strong>Expired On:</strong> {expiry_date}<br>
                <strong>Work Status:</strong> Employee should not be allocated shifts
            </div>
            <p><a href="{admin_link}" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Training Records</a></p>
        </div>
        """
    },
    
    NotificationType.MISSING_MANDATORY_ITEM: {
        "subject": "Missing Compliance Document - {document_name}",
        "employee_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Missing Compliance Document</h2>
            <p>Dear {employee_name},</p>
            <p>We are missing the following mandatory document from your compliance file:</p>
            <div style="background: #e8f4f8; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
                <strong>Document:</strong> {document_name}<br>
                <strong>Category:</strong> {category}
            </div>
            <p>Please upload this document to complete your compliance requirements.</p>
            <p><a href="{portal_link}" style="background: #0d6c6c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Upload Document</a></p>
            <p>Kind regards,<br><strong>Osabea Healthcare Solutions</strong></p>
        </div>
        """,
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0d6c6c;">Missing Document: {employee_name}</h2>
            <p><strong>{employee_name}</strong> is missing a mandatory document:</p>
            <div style="background: #f8f9fa; border-left: 4px solid #0d6c6c; padding: 15px; margin: 15px 0;">
                <strong>Document:</strong> {document_name}<br>
                <strong>Category:</strong> {category}
            </div>
            <p>The employee has been notified.</p>
        </div>
        """
    },
    
    NotificationType.UNVERIFIED_SUBMISSION: {
        "subject": "Document Awaiting Verification - {document_name}",
        "admin_body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #17a2b8;">Document Awaiting Verification</h2>
            <p>A document has been uploaded and requires verification:</p>
            <div style="background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin: 15px 0;">
                <strong>Employee:</strong> {employee_name}<br>
                <strong>Document:</strong> {document_name}<br>
                <strong>Uploaded:</strong> {uploaded_at}
            </div>
            <p><a href="{admin_link}" style="background: #17a2b8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Review & Verify</a></p>
        </div>
        """
    }
}

# Helper function to send notification email
async def send_notification_email(
    notification_type: str,
    recipient_email: str,
    recipient_type: str,  # "employee" or "admin"
    template_data: dict,
    employee_id: str = None
) -> dict:
    """Send a notification email and log it"""
    if not resend.api_key:
        logger.warning("Email service not configured, skipping notification")
        return {"status": "skipped", "reason": "Email service not configured"}
    
    template = NOTIFICATION_TEMPLATES.get(notification_type)
    if not template:
        logger.error(f"Unknown notification type: {notification_type}")
        return {"status": "error", "reason": f"Unknown notification type: {notification_type}"}
    
    # Get the appropriate body template
    body_key = f"{recipient_type}_body"
    if body_key not in template:
        body_key = "admin_body"  # Fallback to admin body
    
    try:
        subject = template["subject"].format(**template_data)
        body = template[body_key].format(**template_data)
    except KeyError as e:
        logger.error(f"Missing template data key: {e}")
        return {"status": "error", "reason": f"Missing template data: {e}"}
    
    try:
        email_result = await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": subject,
            "html": body
        })
        
        # Log the notification
        notification_log = {
            "id": str(uuid.uuid4()),
            "notification_type": notification_type,
            "recipient_email": recipient_email,
            "recipient_type": recipient_type,
            "employee_id": employee_id,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "email_id": email_result.get("id"),
            "status": "sent",
            "template_data": {k: v for k, v in template_data.items() if not k.endswith('_link')}  # Don't log full URLs
        }
        await db.notification_logs.insert_one(notification_log)
        
        logger.info(f"Notification sent: {notification_type} to {recipient_email}")
        return {"status": "sent", "email_id": email_result.get("id"), "notification_id": notification_log["id"]}
        
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        
        # Log the failure
        notification_log = {
            "id": str(uuid.uuid4()),
            "notification_type": notification_type,
            "recipient_email": recipient_email,
            "recipient_type": recipient_type,
            "employee_id": employee_id,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "error": str(e)
        }
        await db.notification_logs.insert_one(notification_log)
        
        return {"status": "failed", "error": str(e)}

# Trigger notification for recruitment issues
async def trigger_recruitment_notifications(employee_id: str, issues: dict):
    """Trigger notifications for recruitment compliance issues"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    employee_email = employee.get('email')
    
    base_data = {
        "employee_name": employee_name,
        "portal_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=recruitment",
        "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=recruitment"
    }
    
    # CV Gap notifications
    for gap in issues.get('cv_gaps', []):
        template_data = {
            **base_data,
            "gap_start": gap.get('gap_start', 'Unknown'),
            "gap_end": gap.get('gap_end', 'Unknown'),
            "gap_days": gap.get('gap_duration_days', 0),
            "previous_job": f"{gap.get('previous_job', {}).get('company', 'Unknown')} ({gap.get('previous_job', {}).get('role', '')})",
            "next_job": f"{gap.get('next_job', {}).get('company', 'Unknown')} ({gap.get('next_job', {}).get('role', '')})"
        }
        
        # Send to employee
        if employee_email:
            await send_notification_email(
                NotificationType.CV_GAP_DETECTED,
                employee_email,
                "employee",
                template_data,
                employee_id
            )
        
        # Send to admin
        await send_notification_email(
            NotificationType.CV_GAP_DETECTED,
            ADMIN_EMAIL,
            "admin",
            template_data,
            employee_id
        )
    
    # Reference notifications
    for ref in issues.get('unverified_references', []):
        template_data = {
            **base_data,
            "reference_num": ref.get('reference_num', 1),
            "reference_name": ref.get('name', 'Unknown'),
            "reference_company": ref.get('company', 'Unknown')
        }
        
        if employee_email:
            await send_notification_email(
                NotificationType.REFERENCE_NOT_VERIFIED,
                employee_email,
                "employee",
                template_data,
                employee_id
            )
        
        await send_notification_email(
            NotificationType.REFERENCE_NOT_VERIFIED,
            ADMIN_EMAIL,
            "admin",
            template_data,
            employee_id
        )
    
    # Proof of Address notifications
    poa = issues.get('proof_of_address', {})
    if poa.get('missing', False):
        template_data = {
            **base_data,
            "current_count": poa.get('current_count', 0),
            "verified_count": poa.get('verified_count', 0)
        }
        
        if employee_email:
            await send_notification_email(
                NotificationType.MISSING_PROOF_OF_ADDRESS,
                employee_email,
                "employee",
                template_data,
                employee_id
            )
        
        await send_notification_email(
            NotificationType.MISSING_PROOF_OF_ADDRESS,
            ADMIN_EMAIL,
            "admin",
            template_data,
            employee_id
        )

# API endpoint to manually trigger recruitment notifications
@api_router.post("/notifications/trigger-recruitment/{employee_id}")
async def trigger_recruitment_notification(employee_id: str, user: dict = Depends(require_admin)):
    """Manually trigger recruitment compliance notifications for an employee"""
    # Get recruitment status
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    issues = {"cv_gaps": [], "unverified_references": [], "proof_of_address": {}}
    
    # Check CV gaps
    employment_history = employee.get('employment_history', [])
    for job in employment_history:
        gap = job.get('gap_after', {})
        if gap and not gap.get('explanation') and gap.get('gap_duration_days', 0) > 30:
            issues['cv_gaps'].append(gap)
    
    # Check references
    for ref_num in [1, 2]:
        ref_name = employee.get(f'reference_{ref_num}_name')
        if ref_name and not employee.get(f'reference_{ref_num}_verified'):
            issues['unverified_references'].append({
                "reference_num": ref_num,
                "name": ref_name,
                "company": employee.get(f'reference_{ref_num}_company', '')
            })
    
    # Check proof of address
    poa_items = await db.compliance_status.find({
        "employee_id": employee_id,
        "requirement_id": "proof_of_address"
    }, {"_id": 0}).to_list(100)
    
    verified_count = sum(1 for item in poa_items if item.get('verified'))
    current_count = len([item for item in poa_items if item.get('evidence_files')])
    
    if verified_count < 2:
        issues['proof_of_address'] = {
            "missing": True,
            "current_count": current_count,
            "verified_count": verified_count
        }
    
    if not any([issues['cv_gaps'], issues['unverified_references'], issues['proof_of_address'].get('missing')]):
        return {"message": "No recruitment issues found", "issues": issues}
    
    await trigger_recruitment_notifications(employee_id, issues)
    
    return {"message": "Notifications triggered", "issues_found": {
        "cv_gaps": len(issues['cv_gaps']),
        "unverified_references": len(issues['unverified_references']),
        "missing_proof_of_address": issues['proof_of_address'].get('missing', False)
    }}

# API endpoint to check and trigger expiry notifications
@api_router.post("/notifications/check-expiries")
async def check_expiry_notifications(user: dict = Depends(require_admin)):
    """Check for expiring documents and training, send notifications"""
    now = datetime.now(timezone.utc)
    thirty_days = now + timedelta(days=30)
    sixty_days = now + timedelta(days=60)
    
    notifications_sent = {"60_day": 0, "30_day": 0, "expired": 0}
    
    # Get all employees
    employees = await db.employees.find({}, {"_id": 0}).to_list(1000)
    
    for employee in employees:
        employee_id = employee.get('id')
        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        employee_email = employee.get('email')
        
        base_data = {
            "employee_name": employee_name,
            "portal_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist",
            "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist"
        }
        
        # Check compliance items for expiry
        compliance_items = await db.compliance_status.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
        
        for item in compliance_items:
            expiry_str = item.get('expiry_date')
            if not expiry_str:
                continue
            
            try:
                expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            except:
                continue
            
            # Check if already notified recently (within 7 days)
            recent_notification = await db.notification_logs.find_one({
                "employee_id": employee_id,
                "notification_type": {"$in": [NotificationType.DOCUMENT_EXPIRING_30_DAYS, NotificationType.DOCUMENT_EXPIRING_60_DAYS]},
                "template_data.document_name": item.get('requirement_id'),
                "sent_at": {"$gte": (now - timedelta(days=7)).isoformat()}
            })
            
            if recent_notification:
                continue
            
            template_data = {
                **base_data,
                "document_name": item.get('requirement_id', '').replace('_', ' ').title(),
                "expiry_date": expiry_date.strftime('%d %B %Y')
            }
            
            if expiry_date <= thirty_days:
                notification_type = NotificationType.DOCUMENT_EXPIRING_30_DAYS
                notifications_sent["30_day"] += 1
            elif expiry_date <= sixty_days:
                notification_type = NotificationType.DOCUMENT_EXPIRING_60_DAYS
                notifications_sent["60_day"] += 1
            else:
                continue
            
            if employee_email:
                await send_notification_email(notification_type, employee_email, "employee", template_data, employee_id)
            await send_notification_email(notification_type, ADMIN_EMAIL, "admin", template_data, employee_id)
        
        # Check training for expiry
        training_records = await db.training_records.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
        
        for record in training_records:
            expiry_str = record.get('expiry_date')
            if not expiry_str:
                continue
            
            try:
                expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            except:
                continue
            
            template_data = {
                **base_data,
                "training_name": record.get('training_id', '').replace('_', ' ').title(),
                "expiry_date": expiry_date.strftime('%d %B %Y'),
                "portal_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=training",
                "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=training"
            }
            
            if expiry_date < now:
                # Already expired
                recent_notification = await db.notification_logs.find_one({
                    "employee_id": employee_id,
                    "notification_type": NotificationType.TRAINING_EXPIRED,
                    "template_data.training_name": record.get('training_id'),
                    "sent_at": {"$gte": (now - timedelta(days=7)).isoformat()}
                })
                
                if not recent_notification:
                    if employee_email:
                        await send_notification_email(NotificationType.TRAINING_EXPIRED, employee_email, "employee", template_data, employee_id)
                    await send_notification_email(NotificationType.TRAINING_EXPIRED, ADMIN_EMAIL, "admin", template_data, employee_id)
                    notifications_sent["expired"] += 1
    
    return {
        "message": "Expiry check complete",
        "notifications_sent": notifications_sent,
        "checked_employees": len(employees)
    }

# API endpoint to get notification logs
@api_router.get("/notifications/logs")
async def get_notification_logs(
    employee_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(require_admin)
):
    """Get notification logs with optional filters"""
    query = {}
    
    if employee_id:
        query["employee_id"] = employee_id
    if notification_type:
        query["notification_type"] = notification_type
    if status:
        query["status"] = status
    
    logs = await db.notification_logs.find(query, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "count": len(logs)}

# API endpoint to trigger notifications for missing mandatory items
@api_router.post("/notifications/trigger-missing-items/{employee_id}")
async def trigger_missing_items_notification(employee_id: str, user: dict = Depends(require_admin)):
    """Trigger notifications for missing mandatory compliance items"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    employee_email = employee.get('email')
    
    # Get compliance status
    compliance_items = await db.compliance_status.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    compliance_map = {item['requirement_id']: item for item in compliance_items}
    
    missing_items = []
    
    for category, items in MANDATORY_ITEMS.items():
        for item in items:
            item_id = item['id']
            status = compliance_map.get(item_id, {})
            
            # Check if missing (no evidence files and not verified)
            if not status.get('evidence_files') and not status.get('verified'):
                missing_items.append({
                    "document_name": item.get('name', item_id.replace('_', ' ').title()),
                    "category": category.replace('_', ' ').title()
                })
    
    if not missing_items:
        return {"message": "No missing items found", "missing_count": 0}
    
    notifications_sent = 0
    for item in missing_items:
        template_data = {
            "employee_name": employee_name,
            "document_name": item['document_name'],
            "category": item['category'],
            "portal_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist",
            "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist"
        }
        
        if employee_email:
            await send_notification_email(
                NotificationType.MISSING_MANDATORY_ITEM,
                employee_email,
                "employee",
                template_data,
                employee_id
            )
        
        await send_notification_email(
            NotificationType.MISSING_MANDATORY_ITEM,
            ADMIN_EMAIL,
            "admin",
            template_data,
            employee_id
        )
        notifications_sent += 1
    
    return {"message": "Notifications sent", "missing_count": len(missing_items), "notifications_sent": notifications_sent}

# API endpoint to notify about unverified submissions
@api_router.post("/notifications/unverified-submissions")
async def notify_unverified_submissions(user: dict = Depends(require_admin)):
    """Send notifications for all unverified document submissions"""
    now = datetime.now(timezone.utc)
    
    # Find all compliance items with evidence but not verified (uploaded > 24 hours ago)
    twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()
    
    pipeline = [
        {"$match": {
            "evidence_files": {"$exists": True, "$ne": []},
            "verified": {"$ne": True}
        }},
        {"$lookup": {
            "from": "employees",
            "localField": "employee_id",
            "foreignField": "id",
            "as": "employee"
        }},
        {"$unwind": "$employee"}
    ]
    
    unverified_items = await db.compliance_status.aggregate(pipeline).to_list(500)
    
    notifications_sent = 0
    
    for item in unverified_items:
        employee = item.get('employee', {})
        employee_id = employee.get('id')
        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        
        # Check if already notified recently
        recent_notification = await db.notification_logs.find_one({
            "employee_id": employee_id,
            "notification_type": NotificationType.UNVERIFIED_SUBMISSION,
            "template_data.document_name": item.get('requirement_id'),
            "sent_at": {"$gte": (now - timedelta(days=1)).isoformat()}
        })
        
        if recent_notification:
            continue
        
        template_data = {
            "employee_name": employee_name,
            "document_name": item.get('requirement_id', '').replace('_', ' ').title(),
            "uploaded_at": item.get('updated_at', 'Unknown'),
            "admin_link": f"{PORTAL_URL}/portal/employees/{employee_id}?tab=checklist"
        }
        
        await send_notification_email(
            NotificationType.UNVERIFIED_SUBMISSION,
            ADMIN_EMAIL,
            "admin",
            template_data,
            employee_id
        )
        notifications_sent += 1
    
    return {"message": "Unverified submission check complete", "notifications_sent": notifications_sent}

# ==================== SERVICE USERS (CQC Care Records) ====================
# Service User File structure aligned with CQC expectations
# Sections 1-10 based on standard care file requirements

# Service User File Section Definitions
SERVICE_USER_SECTIONS = {
    "1_personal_referral": {
        "section_number": 1,
        "name": "Personal Info & Referral",
        "description": "Basic personal information, referral details, and initial contact",
        "document_types": ["referral_form", "initial_assessment", "personal_details"],
    },
    "2_consent_contracts": {
        "section_number": 2,
        "name": "Consent & Contracts",
        "description": "Service agreements, consent forms, and contractual documents",
        "document_types": ["service_agreement", "consent_form", "terms_conditions", "confidentiality"],
    },
    "3_assessments": {
        "section_number": 3,
        "name": "Assessments",
        "description": "Initial and ongoing needs assessments",
        "document_types": ["needs_assessment", "capacity_assessment", "mental_health_assessment"],
    },
    "4_care_plans": {
        "section_number": 4,
        "name": "Care Plans",
        "description": "Individual care plans and support plans",
        "document_types": ["care_plan", "support_plan", "daily_routine"],
    },
    "5_risk_assessments": {
        "section_number": 5,
        "name": "Risk Assessments",
        "description": "Risk assessments and management plans",
        "document_types": ["risk_assessment", "moving_handling_risk", "falls_risk", "medication_risk"],
    },
    "6_monitoring": {
        "section_number": 6,
        "name": "Monitoring",
        "description": "Daily logs, charts, and monitoring records",
        "document_types": ["daily_log", "fluid_chart", "food_chart", "repositioning_chart"],
    },
    "7_medication": {
        "section_number": 7,
        "name": "Medication",
        "description": "Medication records, MAR charts, and prescriptions",
        "document_types": ["mar_chart", "prescription", "medication_list", "prn_protocol"],
    },
    "8_health_visits": {
        "section_number": 8,
        "name": "Health Visits",
        "description": "GP visits, hospital appointments, and professional visits",
        "document_types": ["gp_visit", "hospital_letter", "district_nurse_visit", "specialist_report"],
    },
    "9_reviews": {
        "section_number": 9,
        "name": "Reviews",
        "description": "Care reviews, quality checks, and feedback",
        "document_types": ["care_review", "quality_check", "family_feedback", "annual_review"],
    },
    "10_correspondence": {
        "section_number": 10,
        "name": "Letters & Correspondence",
        "description": "General correspondence, letters, and other documents",
        "document_types": ["letter", "email_correspondence", "other"],
    },
}


class ServiceUserCreate(BaseModel):
    """Create a new service user"""
    full_name: str
    date_of_birth: Optional[str] = None
    nhs_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postcode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    gp_name: Optional[str] = None
    gp_surgery: Optional[str] = None
    gp_phone: Optional[str] = None
    notes: Optional[str] = None


class ServiceUserUpdate(BaseModel):
    """Update service user details"""
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nhs_number: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postcode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    gp_name: Optional[str] = None
    gp_surgery: Optional[str] = None
    gp_phone: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ServiceUserDocumentCreate(BaseModel):
    """Upload a document to a service user's file"""
    section_id: str  # e.g., "3_assessments"
    document_type: Optional[str] = None
    title: str
    notes: Optional[str] = None
    file_url: str
    file_name: str
    expiry_date: Optional[str] = None


@api_router.get("/service-users")
async def list_service_users(
    status: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """List all service users with optional filtering"""
    query = {}
    
    if status:
        query["status"] = status
    
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"nhs_number": {"$regex": search, "$options": "i"}},
            {"postcode": {"$regex": search, "$options": "i"}},
        ]
    
    service_users = await db.service_users.find(query, {"_id": 0}).sort("full_name", 1).to_list(500)
    
    # Add document counts per section
    for su in service_users:
        doc_counts = await db.service_user_documents.aggregate([
            {"$match": {"service_user_id": su["id"]}},
            {"$group": {"_id": "$section_id", "count": {"$sum": 1}}}
        ]).to_list(20)
        su["document_counts"] = {d["_id"]: d["count"] for d in doc_counts}
        su["total_documents"] = sum(d["count"] for d in doc_counts)
    
    return service_users


@api_router.post("/service-users")
async def create_service_user(
    data: ServiceUserCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Create a new service user"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate unique ID and code
    su_id = str(uuid.uuid4())
    
    # Generate service user code (SU-XXXX format)
    count = await db.service_users.count_documents({})
    su_code = f"SU-{count + 1:04d}"
    
    service_user = {
        "id": su_id,
        "service_user_code": su_code,
        "full_name": data.full_name,
        "date_of_birth": data.date_of_birth,
        "nhs_number": data.nhs_number,
        "address_line_1": data.address_line_1,
        "address_line_2": data.address_line_2,
        "city": data.city,
        "county": data.county,
        "postcode": data.postcode,
        "phone": data.phone,
        "email": data.email,
        "emergency_contact_name": data.emergency_contact_name,
        "emergency_contact_phone": data.emergency_contact_phone,
        "emergency_contact_relationship": data.emergency_contact_relationship,
        "gp_name": data.gp_name,
        "gp_surgery": data.gp_surgery,
        "gp_phone": data.gp_phone,
        "notes": data.notes,
        "status": "active",
        "created_at": now,
        "created_by": user.get("user_id"),
        "updated_at": now,
    }
    
    await db.service_users.insert_one(service_user)
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user",
        "entity_id": su_id,
        "action": "created",
        "performed_by": user.get("user_id"),
        "details": {"full_name": data.full_name, "service_user_code": su_code},
        "timestamp": now
    })
    
    return {"id": su_id, "service_user_code": su_code, "message": "Service user created successfully"}


@api_router.get("/service-users/{service_user_id}")
async def get_service_user(
    service_user_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Get service user details with all sections"""
    service_user = await db.service_users.find_one({"id": service_user_id}, {"_id": 0})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    # Get documents grouped by section
    documents = await db.service_user_documents.find(
        {"service_user_id": service_user_id},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(500)
    
    # Organize documents by section
    sections = {}
    for section_id, section_info in SERVICE_USER_SECTIONS.items():
        section_docs = [d for d in documents if d.get("section_id") == section_id]
        sections[section_id] = {
            "section_number": section_info["section_number"],
            "name": section_info["name"],
            "description": section_info["description"],
            "document_types": section_info["document_types"],
            "documents": section_docs,
            "document_count": len(section_docs),
        }
    
    service_user["sections"] = sections
    service_user["total_documents"] = len(documents)
    
    return service_user


@api_router.put("/service-users/{service_user_id}")
async def update_service_user(
    service_user_id: str,
    data: ServiceUserUpdate,
    user: dict = Depends(require_manager_or_admin)
):
    """Update service user details"""
    service_user = await db.service_users.find_one({"id": service_user_id}, {"_id": 0})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.service_users.update_one(
        {"id": service_user_id},
        {"$set": update_data}
    )
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user",
        "entity_id": service_user_id,
        "action": "updated",
        "performed_by": user.get("user_id"),
        "details": {"fields_updated": list(update_data.keys())},
        "timestamp": update_data["updated_at"]
    })
    
    return {"message": "Service user updated successfully"}


@api_router.post("/service-users/{service_user_id}/documents")
async def upload_service_user_document(
    service_user_id: str,
    data: ServiceUserDocumentCreate,
    user: dict = Depends(require_manager_or_admin)
):
    """Upload a document to a service user's file"""
    service_user = await db.service_users.find_one({"id": service_user_id}, {"_id": 0})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    if data.section_id not in SERVICE_USER_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section: {data.section_id}")
    
    now = datetime.now(timezone.utc).isoformat()
    doc_id = str(uuid.uuid4())
    
    document = {
        "id": doc_id,
        "service_user_id": service_user_id,
        "section_id": data.section_id,
        "section_name": SERVICE_USER_SECTIONS[data.section_id]["name"],
        "document_type": data.document_type,
        "title": data.title,
        "notes": data.notes,
        "file_url": data.file_url,
        "file_name": data.file_name,
        "expiry_date": data.expiry_date,
        "uploaded_at": now,
        "uploaded_by": user.get("user_id"),
        "verified": False,
        "verified_at": None,
        "verified_by": None,
    }
    
    await db.service_user_documents.insert_one(document)
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user_document",
        "entity_id": doc_id,
        "action": "uploaded",
        "performed_by": user.get("user_id"),
        "details": {
            "service_user_id": service_user_id,
            "section": data.section_id,
            "title": data.title
        },
        "timestamp": now
    })
    
    return {"id": doc_id, "message": "Document uploaded successfully"}


@api_router.get("/service-users/{service_user_id}/documents")
async def get_service_user_documents(
    service_user_id: str,
    section_id: Optional[str] = None,
    user: dict = Depends(require_manager_or_admin)
):
    """Get all documents for a service user, optionally filtered by section"""
    query = {"service_user_id": service_user_id}
    
    if section_id:
        query["section_id"] = section_id
    
    documents = await db.service_user_documents.find(query, {"_id": 0}).sort("uploaded_at", -1).to_list(500)
    
    return documents


@api_router.put("/service-users/{service_user_id}/documents/{document_id}/verify")
async def verify_service_user_document(
    service_user_id: str,
    document_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Mark a service user document as verified"""
    document = await db.service_user_documents.find_one({
        "id": document_id,
        "service_user_id": service_user_id
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.service_user_documents.update_one(
        {"id": document_id},
        {"$set": {
            "verified": True,
            "verified_at": now,
            "verified_by": user.get("user_id")
        }}
    )
    
    return {"message": "Document verified successfully"}



# ==================== TEST DATA CLEANUP ENDPOINTS ====================

@api_router.delete("/service-users/{service_user_id}")
async def delete_service_user(
    service_user_id: str,
    user: dict = Depends(require_admin)
):
    """Delete a service user (admin only - for test data cleanup)"""
    service_user = await db.service_users.find_one({"id": service_user_id})
    
    if not service_user:
        raise HTTPException(status_code=404, detail="Service user not found")
    
    # Delete associated documents first
    await db.service_user_documents.delete_many({"service_user_id": service_user_id})
    
    # Delete the service user
    await db.service_users.delete_one({"id": service_user_id})
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user",
        "entity_id": service_user_id,
        "action": "deleted",
        "performed_by": user.get("user_id"),
        "details": {"name": service_user.get("full_name"), "reason": "Test data cleanup"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Service user deleted successfully", "id": service_user_id}


@api_router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    user: dict = Depends(require_admin)
):
    """Delete a policy (admin only - for test data cleanup)"""
    policy = await db.policies.find_one({"id": policy_id})
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Delete associated assignments
    await db.employee_policy_assignments.delete_many({"policy_id": policy_id})
    
    # Delete the policy
    await db.policies.delete_one({"id": policy_id})
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "policy",
        "entity_id": policy_id,
        "action": "deleted",
        "performed_by": user.get("user_id"),
        "details": {"title": policy.get("title"), "reason": "Test data cleanup"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Policy deleted successfully", "id": policy_id}



@api_router.delete("/service-users/{service_user_id}/documents/{document_id}")
async def delete_service_user_document(
    service_user_id: str,
    document_id: str,
    user: dict = Depends(require_manager_or_admin)
):
    """Delete a service user document"""
    document = await db.service_user_documents.find_one({
        "id": document_id,
        "service_user_id": service_user_id
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.service_user_documents.delete_one({"id": document_id})
    
    # Log audit entry
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "entity_type": "service_user_document",
        "entity_id": document_id,
        "action": "deleted",
        "performed_by": user.get("user_id"),
        "details": {"title": document.get("title"), "section": document.get("section_id")},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Document deleted successfully"}


@api_router.get("/service-user-sections")
async def get_service_user_sections(user: dict = Depends(require_manager_or_admin)):
    """Get all available service user file sections"""
    return [
        {
            "id": section_id,
            "section_number": info["section_number"],
            "name": info["name"],
            "description": info["description"],
            "document_types": info["document_types"],
        }
        for section_id, info in SERVICE_USER_SECTIONS.items()
    ]


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


# ============================================================================
# PHASE 1: TRAINING CATALOGUE ADMIN ENDPOINTS
# ============================================================================

@api_router.get("/admin/training-catalogue")
async def get_training_catalogue_endpoint(user: dict = Depends(require_admin)):
    """
    Admin endpoint to view training catalogue.
    Phase 1: Read-only view of seeded training types.
    """
    catalogue = await get_training_catalogue()
    
    # Get assignment feature flag status
    return {
        "catalogue": catalogue,
        "total": len(catalogue),
        "feature_flag": {
            "ENABLE_EMPLOYEE_TRAINING_ASSIGNMENTS": ENABLE_EMPLOYEE_TRAINING_ASSIGNMENTS,
            "status": "DISABLED - Phase 1 foundation only"
        }
    }


@api_router.post("/admin/training-catalogue/seed")
async def seed_training_catalogue_endpoint(user: dict = Depends(require_admin)):
    """
    Admin endpoint to manually seed training catalogue.
    Safe to call multiple times - will not duplicate entries.
    """
    result = await ensure_training_catalogue_exists()
    
    # Create indexes for training_catalogue
    await db.training_catalogue.create_index("id", unique=True)
    await db.training_catalogue.create_index("active")
    
    # Create indexes for employee_training_assignments (empty for now)
    await db.employee_training_assignments.create_index([("employee_id", 1), ("training_id", 1)], unique=True)
    await db.employee_training_assignments.create_index("employee_id")
    
    return {
        "success": True,
        "message": f"Training catalogue seeded",
        "seeded_count": result["seeded"],
        "total_count": result["total"],
        "collections_created": ["training_catalogue", "employee_training_assignments"],
        "indexes_created": True
    }


@api_router.get("/admin/training-catalogue/status")
async def get_training_catalogue_status(user: dict = Depends(require_admin)):
    """
    Check status of training catalogue system.
    """
    catalogue_count = await db.training_catalogue.count_documents({})
    assignments_count = await db.employee_training_assignments.count_documents({})
    
    return {
        "phase": "Phase 1 - Foundation",
        "collections": {
            "training_catalogue": {
                "exists": catalogue_count > 0,
                "count": catalogue_count
            },
            "employee_training_assignments": {
                "exists": True,
                "count": assignments_count,
                "note": "Empty until Phase 2"
            }
        },
        "feature_flags": {
            "ENABLE_EMPLOYEE_TRAINING_ASSIGNMENTS": ENABLE_EMPLOYEE_TRAINING_ASSIGNMENTS
        },
        "behavior": "UNCHANGED - compliance calculation uses MANDATORY_ITEMS only"
    }


# ============================================================================
# INSPECTION PACK GENERATION
# Reuses: org_policies, insurance_docs, CQC_EVIDENCE_MAPPING, verification stamp
# New: Bundle endpoint + cover sheet generator
# ============================================================================

@api_router.get("/inspection-pack/generate")
async def generate_inspection_pack(
    include_policies: bool = True,
    include_certificates: bool = True,
    include_staff_summary: bool = True,
    user: dict = Depends(get_current_user)
):
    """
    Generate CQC Inspection Pack - bundles existing documents for inspector use.
    
    REUSES:
    - org_policies collection (existing governance documents)
    - insurance_docs collection (existing certificates)
    - CQC_EVIDENCE_MAPPING (existing CQC alignment)
    - generate_verification_stamp() (existing verification infrastructure)
    
    NO NEW COLLECTIONS - This aggregates and exports existing data
    
    Returns: ZIP file containing:
    - Cover sheet PDF with organisation summary
    - Policy documents folder
    - Certificates folder
    - Staff compliance summary
    """
    import zipfile
    
    now = datetime.now(timezone.utc)
    
    # Fetch all source data (REUSING existing collections)
    policies = await db.org_policies.find(
        {"status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    certificates = await db.insurance_docs.find(
        {"file_url": {"$ne": None}},
        {"_id": 0}
    ).to_list(50)
    
    # Get organisation stats (REUSING existing queries)
    employee_count = await db.employees.count_documents({"status": {"$in": ["active", "onboarding"]}})
    
    # Calculate work readiness stats
    employees = await db.employees.find(
        {"status": {"$in": ["active", "onboarding"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1}
    ).to_list(500)
    
    ready_count = 0
    supervised_count = 0
    not_ready_count = 0
    
    for emp in employees:
        readiness = await calculate_work_readiness_quick(emp["id"], emp.get("role", ""))
        if readiness["status"] == "work_ready":
            ready_count += 1
        elif readiness["status"] == "supervised_start":
            supervised_count += 1
        else:
            not_ready_count += 1
    
    # Create ZIP buffer
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. COVER SHEET PDF
        cover_buffer = io.BytesIO()
        cover_doc = SimpleDocTemplate(
            cover_buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=20*mm
        )
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CoverTitle',
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=colors.HexColor('#0F5C5E'),
            alignment=TA_CENTER,
            spaceAfter=10*mm
        ))
        styles.add(ParagraphStyle(
            name='CoverSubtitle',
            fontName='Helvetica',
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            alignment=TA_CENTER,
            spaceAfter=15*mm
        ))
        styles.add(ParagraphStyle(
            name='CoverSection',
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.HexColor('#1F2937'),
            spaceBefore=8*mm,
            spaceAfter=4*mm
        ))
        styles.add(ParagraphStyle(
            name='CoverBody',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            spaceAfter=2*mm
        ))
        
        cover_elements = []
        
        # Title
        cover_elements.append(Spacer(1, 30*mm))
        cover_elements.append(Paragraph("OSABEA HEALTHCARE SOLUTIONS", styles['CoverTitle']))
        cover_elements.append(Paragraph("CQC Inspection Pack", styles['CoverSubtitle']))
        cover_elements.append(Paragraph(f"Generated: {now.strftime('%d %B %Y at %H:%M')}", 
                                        ParagraphStyle('Date', fontSize=10, alignment=TA_CENTER, spaceAfter=20*mm)))
        
        cover_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F5C5E')))
        cover_elements.append(Spacer(1, 10*mm))
        
        # Organisation Summary
        cover_elements.append(Paragraph("Organisation Summary", styles['CoverSection']))
        
        summary_data = [
            ["Total Staff:", str(employee_count)],
            ["Ready to Work:", f"{ready_count} ({round(ready_count/employee_count*100) if employee_count > 0 else 0}%)"],
            ["Supervised Start:", str(supervised_count)],
            ["Not Yet Ready:", str(not_ready_count)],
            ["Active Policies:", str(len(policies))],
            ["Certificates on File:", str(len(certificates))],
        ]
        
        summary_table = Table(summary_data, colWidths=[60*mm, 80*mm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4*mm),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ]))
        cover_elements.append(summary_table)
        
        # Contents
        cover_elements.append(Spacer(1, 10*mm))
        cover_elements.append(Paragraph("Pack Contents", styles['CoverSection']))
        
        contents = []
        if include_policies:
            contents.append(f"• Policies Folder ({len(policies)} documents)")
        if include_certificates:
            contents.append(f"• Certificates Folder ({len(certificates)} documents)")
        if include_staff_summary:
            contents.append("• Staff Compliance Summary (PDF)")
        
        for item in contents:
            cover_elements.append(Paragraph(item, styles['CoverBody']))
        
        # CQC Alignment
        cover_elements.append(Spacer(1, 10*mm))
        cover_elements.append(Paragraph("CQC Key Questions Coverage", styles['CoverSection']))
        
        for key, section in CQC_EVIDENCE_MAPPING.items():
            cover_elements.append(Paragraph(f"• {section['title']}: {len(section['items'])} evidence items mapped", styles['CoverBody']))
        
        # Verification stamp (REUSING existing helper)
        verification_stamp = generate_verification_stamp(
            verified_by=user.get('name', user.get('email', 'System')),
            verified_at=now.isoformat(),
            document_type="CQC Inspection Pack Cover Sheet",
            include_hash=True,
            content_bytes=f"inspection_pack_{employee_count}_{len(policies)}_{len(certificates)}".encode()
        )
        stamp_elements = create_verification_footer_elements(verification_stamp)
        cover_elements.extend(stamp_elements)
        
        cover_doc.build(cover_elements)
        cover_buffer.seek(0)
        zf.writestr("00_Cover_Sheet.pdf", cover_buffer.getvalue())
        
        # 2. POLICIES (if included)
        if include_policies:
            for i, policy in enumerate(policies, 1):
                policy_name = policy.get('name', 'Unknown Policy').replace('/', '-').replace('\\', '-')
                # Create a text summary since we don't have actual PDF files
                policy_info = f"""
POLICY: {policy.get('name')}
Status: {policy.get('status', 'N/A')}
Version: {policy.get('version', 'N/A')}
Review Date: {policy.get('review_date', 'Not Set')}
Last Updated: {policy.get('updated_at', 'N/A')}

This policy is active and available in the Osabea Healthcare Compliance Portal.
For the full policy document, please access: Compliance Centre > Policies
"""
                zf.writestr(f"01_Policies/{i:02d}_{policy_name}.txt", policy_info)
        
        # 3. CERTIFICATES (if included)
        if include_certificates:
            for i, cert in enumerate(certificates, 1):
                cert_name = cert.get('name', cert.get('insurance_type', 'Unknown')).replace('/', '-').replace('\\', '-')
                cert_info = f"""
CERTIFICATE: {cert.get('name', cert.get('insurance_type'))}
Type: {cert.get('insurance_type', 'N/A')}
Provider: {cert.get('provider', 'N/A')}
Policy Number: {cert.get('policy_number', 'N/A')}
Expiry Date: {cert.get('expiry_date', 'No Expiry Set')}
Status: {'Active' if cert.get('file_url') else 'Missing'}

File available in system: {cert.get('file_url', 'Not uploaded')}
"""
                zf.writestr(f"02_Certificates/{i:02d}_{cert_name}.txt", cert_info)
        
        # 4. STAFF SUMMARY (if included)
        if include_staff_summary:
            staff_buffer = io.BytesIO()
            staff_doc = SimpleDocTemplate(
                staff_buffer,
                pagesize=A4,
                rightMargin=15*mm,
                leftMargin=15*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            staff_elements = []
            staff_elements.append(Paragraph("Staff Compliance Summary", styles['CoverTitle']))
            staff_elements.append(Paragraph(f"Generated: {now.strftime('%d %B %Y')}", 
                                           ParagraphStyle('Date', fontSize=10, alignment=TA_CENTER, spaceAfter=10*mm)))
            
            # Staff table
            staff_data = [["Name", "Role", "Work Status", "Compliance"]]
            for emp in employees[:50]:  # Limit to 50 for PDF size
                readiness = await calculate_work_readiness_quick(emp["id"], emp.get("role", ""))
                compliance = await calculate_employee_compliance(emp["id"], emp.get("role", ""))
                staff_data.append([
                    f"{emp['first_name']} {emp['last_name']}",
                    emp.get('role', 'N/A'),
                    readiness["label"],
                    f"{compliance['completion_percentage']}%"
                ])
            
            staff_table = Table(staff_data, colWidths=[50*mm, 40*mm, 45*mm, 30*mm])
            staff_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F5C5E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
                ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
            ]))
            staff_elements.append(staff_table)
            
            # Add verification stamp
            staff_stamp = generate_verification_stamp(
                verified_by=user.get('name', user.get('email', 'System')),
                verified_at=now.isoformat(),
                document_type="Staff Compliance Summary",
                include_hash=True
            )
            staff_stamp_elements = create_verification_footer_elements(staff_stamp)
            staff_elements.extend(staff_stamp_elements)
            
            staff_doc.build(staff_elements)
            staff_buffer.seek(0)
            zf.writestr("03_Staff_Compliance_Summary.pdf", staff_buffer.getvalue())
    
    zip_buffer.seek(0)
    
    # Log the action
    await log_audit_action(user['user_id'], "generate_inspection_pack", "organisation", "inspection_pack", {
        "included_policies": include_policies,
        "included_certificates": include_certificates,
        "included_staff_summary": include_staff_summary,
        "policy_count": len(policies),
        "certificate_count": len(certificates),
        "staff_count": employee_count
    })
    
    filename = f"CQC_Inspection_Pack_{now.strftime('%Y%m%d_%H%M%S')}.zip"
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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
    except Exception as e:
        logger.error(f"Auto-seeding policies failed: {e}")


@app.on_event("startup")
async def startup_db_client():
    """Auto-seed compliance items on startup"""
    try:
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
        
        # Phase 1: Auto-seed training catalogue from MANDATORY_ITEMS
        catalogue_count = await db.training_catalogue.count_documents({})
        if catalogue_count == 0:
            result = await ensure_training_catalogue_exists()
            # Create indexes
            await db.training_catalogue.create_index("id", unique=True)
            await db.training_catalogue.create_index("active")
            await db.employee_training_assignments.create_index([("employee_id", 1), ("training_id", 1)], unique=True)
            await db.employee_training_assignments.create_index("employee_id")
            logger.info(f"Phase 1: Auto-seeded training catalogue with {result['seeded']} items")
    except Exception as e:
        logger.error(f"Auto-seeding failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
