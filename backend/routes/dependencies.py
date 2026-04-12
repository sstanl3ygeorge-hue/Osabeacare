"""
Shared dependencies and utilities for route modules.

This module provides common dependencies, authentication helpers, and
database access that are shared across multiple route modules.
"""

import os
import jwt
import bcrypt
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
# This will be set from server.py during app initialization
db = None

def set_database(database):
    """Set the shared database instance from server.py"""
    global db
    db = database

def get_db():
    """Get the database instance"""
    if db is None:
        raise RuntimeError("Database not initialized. Call set_database() first.")
    return db

# ==================== JWT CONFIG ====================
JWT_SECRET = os.environ.get('JWT_SECRET', 'care-recruitment-jwt-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

# ==================== EMAIL CONFIG ====================
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'Osabea Recruitment Team <recruitment@osabeacares.co.uk>')
REPLY_TO_EMAIL = os.environ.get('REPLY_TO_EMAIL', 'info@beamedicare.co.uk')

# ==================== USER ROLES ====================
class UserRole:
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    BRANCH_MANAGER = "branch_manager"
    EMPLOYEE = "employee"
    AUDITOR = "auditor"

# ==================== AUTH MODELS ====================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = UserRole.EMPLOYEE
    assignment: Optional[str] = "Unassigned"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str  # Must be admin or super_admin

class WorkerLoginRequest(BaseModel):
    email: EmailStr

class WorkerPasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str

class WorkerVerifyRequest(BaseModel):
    token: str

class WorkerSetPasswordRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str
    confirm_password: str

# ==================== PASSWORD HELPERS ====================
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Alias for compatibility
get_password_hash = hash_password

# ==================== TOKEN HELPERS ====================
def create_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token for admin/staff users"""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== AUTHENTICATION DEPENDENCIES ====================
async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    FastAPI dependency to get the current authenticated admin/staff user.
    Raises HTTPException if not authenticated or user not found.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        user = await get_db().users.find_one({"user_id": payload['user_id']}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

async def get_current_worker(authorization: str = Header(None)) -> dict:
    """
    FastAPI dependency to get the current authenticated worker.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "worker":
            raise HTTPException(status_code=403, detail="Not authorized as worker")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_or_worker(authorization: str = Header(None)) -> dict:
    """
    Unified auth dependency that accepts both admin/user and worker tokens.
    Used for endpoints that need to serve both portal types.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Worker token
        if payload.get("role") == "worker" or payload.get("type") == "worker_session":
            return {
                "role": "worker",
                "employee_id": payload.get("employee_id"),
                "email": payload.get("email"),
                "is_worker": True
            }
        
        # Admin/User token - look up user in database
        user_id = payload.get("user_id")
        if user_id:
            user = await get_db().users.find_one({"user_id": user_id}, {"_id": 0})
            if user:
                user["is_worker"] = False
                return user
        
        raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin or super_admin role"""
    if user['role'] not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_manager_or_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require manager, admin, or super_admin role"""
    if user['role'] not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.BRANCH_MANAGER]:
        raise HTTPException(status_code=403, detail="Manager or admin access required")
    return user

# ==================== AUDIT LOGGING ====================
async def log_audit_action(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Dict[str, Any] = None
):
    """Log an audit action to the database"""
    try:
        audit_entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await get_db().audit_logs.insert_one(audit_entry)
    except Exception as e:
        logger.warning(f"Failed to log audit action: {e}")
