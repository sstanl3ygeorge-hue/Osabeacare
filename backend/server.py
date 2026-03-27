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

app = FastAPI(title="Osabea Care Solutions API")
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    BRANCH_MANAGER = "branch_manager"
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

# User Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = UserRole.EMPLOYEE
    branch: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    role: str
    branch: Optional[str] = None
    picture: Optional[str] = None
    created_at: str

# Employee Models
class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    branch: str
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
    branch: Optional[str] = None
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
    branch: str
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
        "branch": user.branch,
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
                "branch": None,
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
        except:
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
    branch: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    missing_dbs: bool = False,
    missing_rtw: bool = False,
    missing_references: bool = False,
    unsigned_policies: bool = False,
    expiring_soon: bool = False,
    user: dict = Depends(get_current_user)
):
    query = {}
    
    # Branch filter for branch managers
    if user['role'] == UserRole.BRANCH_MANAGER:
        query["branch"] = user.get('branch')
    elif branch:
        query["branch"] = branch
    
    if status:
        query["status"] = status
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

@api_router.get("/files/{path:path}")
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
    branch_filter = {}
    if user['role'] == UserRole.BRANCH_MANAGER:
        branch_filter = {"branch": user.get('branch')}
    
    # Get counts
    total_employees = await db.employees.count_documents({**branch_filter, "status": {"$in": [EmployeeStatus.ACTIVE, EmployeeStatus.ONBOARDING]}})
    total_applicants = await db.employees.count_documents({**branch_filter, "status": {"$in": [EmployeeStatus.NEW, EmployeeStatus.SCREENING, EmployeeStatus.INTERVIEW, EmployeeStatus.COMPLIANCE_REVIEW]}})
    onboarding = await db.employees.count_documents({**branch_filter, "status": EmployeeStatus.ONBOARDING})
    
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

# ==================== PUBLIC ROUTES ====================

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
        "branch": "Pending Assignment",
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
        "branch": None,
        "picture": None,
        "employee_id": app_id,
        "created_at": now
    }
    await db.users.insert_one(user_doc)
    
    return {"message": "Your application has been submitted successfully. We will review it and be in touch.", "reference": employee_code}

@api_router.get("/branches")
async def get_branches():
    branches = await db.employees.distinct("branch")
    return [b for b in branches if b and b != "Pending Assignment"]

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
                "subject": "Document request from Osabea Care Solutions",
                "html": f"""
                <h2>Document Request</h2>
                <p>Dear {employee['first_name']},</p>
                <p>We need you to upload the following document to complete your compliance file:</p>
                <p><strong>{doc_type['name']}</strong></p>
                {f'<p>{message}</p>' if message else ''}
                {f'<p>Due date: {due_date}</p>' if due_date else ''}
                <p>Please log in to your portal and upload the requested document.</p>
                <p>Thank you,<br>Osabea Care Solutions Team</p>
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
            "branch": None,
            "picture": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_user)
    
    return {"message": "Seed data created successfully", "document_types": len(document_categories)}

# Health check
@api_router.get("/")
async def root():
    return {"message": "Osabea Care Solutions API", "status": "healthy"}

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
