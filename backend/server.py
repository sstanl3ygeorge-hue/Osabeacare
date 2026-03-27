from fastapi import FastAPI, APIRouter, HTTPException, Depends, File, UploadFile, Query, Header, Response
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import requests
import resend
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

class EmployeeDocumentUpdate(BaseModel):
    status: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    reviewed_by: Optional[str] = None

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
    # Get all required document types
    required_types = await db.document_types.find({"required_before_active": True}, {"_id": 0}).to_list(100)
    if not required_types:
        return 0
    
    total_required = len(required_types)
    approved_count = 0
    
    for doc_type in required_types:
        doc = await db.employee_documents.find_one({
            "employee_id": employee_id,
            "document_type_id": doc_type['id'],
            "status": DocumentStatus.APPROVED
        })
        if doc:
            approved_count += 1
    
    return int((approved_count / total_required) * 100) if total_required > 0 else 0

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
    
    # Calculate completion percentages
    for emp in employees:
        emp['completion_percentage'] = await calculate_completion_percentage(emp['id'])
    
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

# ==================== EMPLOYEE DOCUMENT ROUTES ====================

@api_router.post("/employee-documents", response_model=EmployeeDocumentResponse)
async def create_employee_document(doc: EmployeeDocumentCreate, user: dict = Depends(require_manager_or_admin)):
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc_type = await db.document_types.find_one({"id": doc.document_type_id}, {"_id": 0})
    
    doc_data = {
        "id": doc_id,
        **doc.model_dump(),
        "document_type_name": doc_type['name'] if doc_type else None,
        "category": doc_type['category'] if doc_type else None,
        "file_url": None,
        "original_filename": None,
        "status": DocumentStatus.NOT_STARTED,
        "uploaded_by": None,
        "uploaded_at": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "version_number": 1,
        "created_at": now
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
    
    result = await db.employee_documents.update_one({"id": doc_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await log_audit_action(user['user_id'], "update_document", "employee_document", doc_id, update_data)
    
    doc = await db.employee_documents.find_one({"id": doc_id}, {"_id": 0})
    return EmployeeDocumentResponse(**doc)

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
async def upload_training_certificate(record_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    record = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    path = f"{APP_NAME}/certificates/{record['employee_id']}/{uuid.uuid4()}.{ext}"
    
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/pdf")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.training_records.update_one(
        {"id": record_id},
        {"$set": {"certificate_url": result["path"], "status": "completed", "completion_date": now}}
    )
    
    updated = await db.training_records.find_one({"id": record_id}, {"_id": 0})
    return TrainingRecordResponse(**updated)

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
    
    # Track status changes
    if update.status:
        if update.status == FormStatus.SENT and not form.get('sent_at'):
            update_data['sent_at'] = now
        elif update.status == FormStatus.COMPLETED and not form.get('completed_at'):
            update_data['completed_at'] = now
        elif update.status == FormStatus.REVIEWED and not form.get('reviewed_at'):
            update_data['reviewed_at'] = now
        elif update.status == FormStatus.SIGNED_OFF and not form.get('signed_off_at'):
            update_data['signed_off_at'] = now
            update_data['admin_signoff_by'] = user['user_id']
    
    await db.generated_forms.update_one({"id": form_id}, {"$set": update_data})
    
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
            review_date = datetime.fromisoformat(policy["review_date"].replace('Z', '+00:00'))
            if review_date < now and policy["status"] == "active":
                policy["status"] = "expired"
    
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
            expiry = datetime.fromisoformat(doc["expiry_date"].replace('Z', '+00:00'))
            if expiry < now:
                doc["status"] = "expired"
            elif expiry < thirty_days:
                doc["status"] = "expiring_soon"
            else:
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
                    exp = datetime.fromisoformat(t["expiry_date"].replace('Z', '+00:00'))
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
            exp = datetime.fromisoformat(ins["expiry_date"].replace('Z', '+00:00'))
            if exp < now:
                insurance_expired += 1
            elif exp < now + timedelta(days=30):
                insurance_expiring += 1
            else:
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
