"""
Authentication Routes Module

This module handles all authentication-related endpoints including:
- Admin/Staff authentication (/auth/*)
- Worker portal authentication (/worker/request-login, /worker/login, /worker/verify-login)
- Password management
- OAuth session exchange (Emergent Google Auth)

Extracted from server.py for modularity.
"""

import os
import re
import uuid
import asyncio
import logging
import jwt
import requests
import resend
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Body
from pydantic import BaseModel, EmailStr
from typing import Optional

from .dependencies import (
    get_db,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    SENDER_EMAIL,
    UserRole,
    UserCreate,
    UserLogin,
    AdminUserCreate,
    WorkerLoginRequest,
    WorkerPasswordLoginRequest,
    WorkerVerifyRequest,
    WorkerSetPasswordRequest,
    hash_password,
    verify_password,
    get_password_hash,
    create_token,
    decode_token,
    get_current_user,
    get_current_worker,
    log_audit_action,
)

# Import rate limiter from security module
from security import login_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

# ==================== ADMIN AUTH ROUTES ====================

@router.post("/auth/register")
async def register(user: UserCreate):
    """
    Register a new user account.
    
    SECURITY RULES:
    - admin and super_admin roles CANNOT be created via public registration
    - Only super_admin can create admin/super_admin accounts (via separate endpoint)
    - branch_manager cannot self-escalate to admin
    """
    db = get_db()
    
    # SECURITY: Block privileged role creation via public registration
    PRIVILEGED_ROLES = [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    if user.role in PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=403, 
            detail="Admin accounts cannot be created via public registration. Contact a super administrator."
        )
    
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
    user_response = {k: v for k, v in user_doc.items() if k not in ['password', '_id']}
    return {"token": token, "user": user_response}


@router.post("/auth/create-admin")
async def create_admin_user(user_data: AdminUserCreate, user: dict = Depends(get_current_user)):
    """
    Create an admin or super_admin account.
    RESTRICTED: Only super_admin can create privileged accounts.
    """
    db = get_db()
    
    # SECURITY: Only super_admin can create admin accounts
    if user.get('role') != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403, 
            detail="Only super administrators can create admin accounts"
        )
    
    # Validate target role is privileged
    PRIVILEGED_ROLES = [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    if user_data.role not in PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Use /auth/register for non-admin accounts"
        )
    
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "assignment": "Admin",
        "picture": None,
        "created_at": now,
        "created_by": user.get('user_id'),
        "created_by_role": user.get('role')
    }
    await db.users.insert_one(user_doc)
    
    await log_audit_action(
        user.get('user_id'),
        "create_admin_user",
        "user",
        user_id,
        {"email": user_data.email, "role": user_data.role}
    )
    
    user_response = {k: v for k, v in user_doc.items() if k not in ['password', '_id']}
    return {"message": "Admin user created", "user": user_response}


@router.post("/auth/login")
async def login(credentials: UserLogin, http_request: Request):
    """Admin login with rate limiting and account lockout protection."""
    db = get_db()
    
    # Rate limiting check
    identifier = f"admin_{credentials.email.lower()}"
    allowed, error_msg = login_rate_limiter.check_rate_limit(identifier)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user['password']):
        login_rate_limiter.record_attempt(identifier, success=False)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    login_rate_limiter.record_attempt(identifier, success=True)
    
    token = create_token(user['user_id'], user['email'], user['role'])
    user_response = {k: v for k, v in user.items() if k != 'password'}
    return {"token": token, "user": user_response}


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {k: v for k, v in user.items() if k != 'password'}


@router.get("/auth/session-info")
async def get_session_info(request: Request, user: dict = Depends(get_current_user)):
    """
    Get session information including expiry time for timeout warnings.
    
    Returns:
    - expires_at: ISO timestamp when session expires
    - expires_in_seconds: Seconds until expiration
    - warning_threshold_seconds: When to show warning (5 minutes before expiry)
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
    
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp_timestamp = payload.get("exp")
        
        if exp_timestamp:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            expires_in_seconds = int((expires_at - now).total_seconds())
            warning_threshold_seconds = 300  # 5 minutes
            
            return {
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "role": user.get("role"),
                "expires_at": expires_at.isoformat(),
                "expires_in_seconds": max(0, expires_in_seconds),
                "warning_threshold_seconds": warning_threshold_seconds,
                "show_warning": expires_in_seconds <= warning_threshold_seconds and expires_in_seconds > 0,
                "session_expired": expires_in_seconds <= 0
            }
    except jwt.ExpiredSignatureError:
        return {
            "session_expired": True,
            "expires_in_seconds": 0,
            "show_warning": False,
            "message": "Session has expired. Please log in again."
        }
    except Exception as e:
        logger.warning(f"Session info error: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")


# Emergent Google OAuth session exchange
@router.post("/auth/session")
async def exchange_session(session_id: str = Header(None, alias="X-Session-ID")):
    """Exchange Emergent OAuth session for local JWT token"""
    db = get_db()
    
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
        
        existing_user = await db.users.find_one({"email": session_data['email']}, {"_id": 0})
        
        if existing_user:
            user_id = existing_user['user_id']
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"name": session_data.get('name', existing_user['name']), "picture": session_data.get('picture')}}
            )
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        else:
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


# ==================== ADMIN USER MANAGEMENT ====================

@router.get("/admin/users")
async def list_admin_users(user: dict = Depends(get_current_user)):
    """List all admin/manager users. Only super_admin and admin can view."""
    db = get_db()
    
    if user.get('role') not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find(
        {"role": {"$in": ["super_admin", "admin", "manager", "auditor"]}},
        {"_id": 0, "password": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"users": users, "count": len(users)}


@router.put("/admin/users/{user_id}")
async def update_admin_user(
    user_id: str,
    update_data: dict = Body(...),
    user: dict = Depends(get_current_user)
):
    """Update an admin user's details. Only super_admin can update."""
    db = get_db()
    
    if user.get('role') != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super administrators can update admin accounts")
    
    target_user = await db.users.find_one({"user_id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user['user_id'] == user['user_id'] and update_data.get('role') != 'super_admin':
        raise HTTPException(status_code=400, detail="Cannot demote yourself")
    
    allowed_fields = ['name', 'role']
    update_doc = {}
    for field in allowed_fields:
        if field in update_data:
            update_doc[field] = update_data[field]
    
    if not update_doc:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_doc['updated_at'] = datetime.now(timezone.utc).isoformat()
    update_doc['updated_by'] = user.get('user_id')
    
    await db.users.update_one({"user_id": user_id}, {"$set": update_doc})
    
    await log_audit_action(user.get('user_id'), "update_admin_user", "user", user_id, update_doc)
    
    return {"message": "User updated", "user_id": user_id}


@router.delete("/admin/users/{user_id}")
async def delete_admin_user(user_id: str, user: dict = Depends(get_current_user)):
    """Delete an admin user. Only super_admin can delete."""
    db = get_db()
    
    if user.get('role') != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super administrators can delete admin accounts")
    
    if user_id == user.get('user_id'):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    target_user = await db.users.find_one({"user_id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.get('role') == 'super_admin':
        super_admin_count = await db.users.count_documents({"role": "super_admin"})
        if super_admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last super administrator")
    
    await db.users.delete_one({"user_id": user_id})
    
    await log_audit_action(
        user.get('user_id'),
        "delete_admin_user",
        "user",
        user_id,
        {"deleted_email": target_user.get('email'), "deleted_role": target_user.get('role')}
    )
    
    return {"message": "User deleted", "user_id": user_id}


@router.post("/admin/users/{user_id}/reset-password")
async def reset_admin_password(
    user_id: str,
    password_data: dict = Body(...),
    user: dict = Depends(get_current_user)
):
    """Reset an admin user's password. Only super_admin can reset."""
    db = get_db()
    
    if user.get('role') != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super administrators can reset passwords")
    
    target_user = await db.users.find_one({"user_id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_password = password_data.get('password')
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    hashed = hash_password(new_password)
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "password": hashed,
            "password_updated_at": datetime.now(timezone.utc).isoformat(),
            "password_updated_by": user.get('user_id')
        }}
    )
    
    await log_audit_action(
        user.get('user_id'),
        "reset_admin_password",
        "user",
        user_id,
        {"target_email": target_user.get('email')}
    )
    
    return {"message": "Password reset successfully"}


# ==================== WORKER PORTAL AUTH ====================

@router.post("/worker/request-login")
async def worker_request_login(request: WorkerLoginRequest, http_request: Request):
    """
    Send magic link to worker's email.
    No password required - link expires in 24 hours.
    Rate limited: 5 attempts per email per hour.
    """
    db = get_db()
    
    # Rate limiting check
    identifier = request.email.lower()
    allowed, error_msg = login_rate_limiter.check_rate_limit(identifier)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    # Find employee by email
    employee = await db.employees.find_one({
        "email": {"$regex": f"^{re.escape(request.email)}$", "$options": "i"}
    }, {"_id": 1, "id": 1, "first_name": 1, "last_name": 1, "email": 1, "employee_code": 1})

    # 🔥 FORCE SEND DEBUG
    logger.warning(f"[DEBUG] LOGIN REQUEST FOR EMAIL: {request.email}")

    # Create token anyway (even if employee not found)
    token_payload = {
        "employee_id": str(employee.get("_id")) if employee else "debug-no-user",
        "email": request.email,
        "type": "worker_login",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }

    magic_token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")

    frontend_url = os.environ.get(
        "FRONTEND_URL",
        "https://app.osabeacares.co.uk"
    )

    magic_link = f"{frontend_url}/worker/verify?token={magic_token}"

    logger.warning(f"[DEBUG] MAGIC LINK: {magic_link}")

    # 🔥 FORCE email send attempt
    try:
        if resend.api_key:
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": request.email,
                "subject": "DEBUG Login Link",
                "html": f"<p>Debug login link:</p><a href='{magic_link}'>{magic_link}</a>"
            })
            logger.warning("[DEBUG] EMAIL SENT VIA RESEND")
        else:
            logger.error("[DEBUG] RESEND API KEY MISSING")

    except Exception as e:
        logger.error(f"[DEBUG] EMAIL SEND FAILED: {e}")

    # Always return success
    return {"status": "ok"}


@router.post("/worker/login")
async def worker_password_login(request: WorkerPasswordLoginRequest):
    """
    Password-based login for workers/applicants.
    
    Workers can login with:
    1. Magic link (primary, always available)
    2. Their own password (if they have set one via /worker/set-password)
    3. Test password from env var (for testing - remove in production)
    """
    db = get_db()
    email = request.email.lower().strip()
    
    employee = await db.employees.find_one(
        {"email": {"$regex": f"^{email}$", "$options": "i"}},
        {"_id": 0, "id": 1, "email": 1, "first_name": 1, "last_name": 1, "status": 1, "role": 1}
    )
    
    if not employee:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    worker_user = await db.worker_accounts.find_one(
        {"employee_id": employee["id"]},
        {"_id": 0}
    )
    
    password_valid = False
    login_method = None
    
    # Check test password first (from env var)
    test_password = os.environ.get("WORKER_TEST_PASSWORD")
    if test_password and request.password == test_password:
        password_valid = True
        login_method = "test_password"
    elif worker_user and worker_user.get("password_hash"):
        if verify_password(request.password, worker_user["password_hash"]):
            password_valid = True
            login_method = "own_password"
    
    if not password_valid:
        if worker_user and worker_user.get("password_hash"):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        else:
            raise HTTPException(
                status_code=401, 
                detail="Invalid password. You can also use 'Send Login Link' to access your account."
            )
    
    session_token = jwt.encode({
        "employee_id": employee["id"],
        "email": employee["email"],
        "role": "worker",
        "type": "worker_session",
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    if worker_user:
        await db.worker_accounts.update_one(
            {"employee_id": employee["id"]},
            {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
        )
    
    await log_audit_action(
        employee["id"],
        "worker_login",
        "employee",
        employee["id"],
        {"login_method": login_method, "email": email}
    )
    
    return {
        "success": True,
        "token": session_token,
        "employee": {
            "id": employee["id"],
            "email": employee["email"],
            "first_name": employee.get("first_name"),
            "last_name": employee.get("last_name"),
            "status": employee.get("status"),
            "role": employee.get("role")
        }
    }


@router.post("/worker/verify-login")
async def worker_verify_login(request: WorkerVerifyRequest):
    """
    Verify magic link and return JWT for worker session.
    Token is single-use and expires after 24 hours.
    """
    db = get_db()
    
    try:
        payload = jwt.decode(request.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        if payload.get("type") != "worker_login":
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        employee_id = payload.get("employee_id")
        email = payload.get("email")
        
        token_record = await db.magic_tokens.find_one({
            "token": request.token,
            "used": False
        })
        
        if not token_record:
            raise HTTPException(status_code=400, detail="Token already used or invalid")
        
        await db.magic_tokens.update_one(
            {"token": request.token},
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        
        is_applicant = False
        if not employee:
            employee = await db.applications.find_one({"id": employee_id}, {"_id": 0})
            is_applicant = True
            
        if not employee:
            employee = await db.employees.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}}, {"_id": 0})
            if not employee:
                employee = await db.applications.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}}, {"_id": 0})
                is_applicant = True
        
        if not employee:
            raise HTTPException(status_code=404, detail="Account not found. Your application may still be under review.")
        
        access_token = jwt.encode({
            "sub": email,
            "user_id": f"worker_{employee.get('id', employee_id)}",
            "employee_id": employee.get('id', employee_id),
            "role": "worker",
            "is_applicant": is_applicant,
            "name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        await log_audit_action(
            f"worker_{employee.get('id', employee_id)}",
            "worker_login",
            "employee" if not is_applicant else "application",
            employee.get('id', employee_id),
            {"login_method": "magic_link", "is_applicant": is_applicant}
        )
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "is_applicant": is_applicant,
            "employee": {
                "id": employee.get('id', employee_id),
                "name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
                "email": employee.get("email"),
                "employee_code": employee.get("employee_code"),
                "status": employee.get("status", "pending_review" if is_applicant else "unknown")
            }
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Login link has expired. Please request a new one.")
    except jwt.PyJWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid login link")


@router.post("/worker/set-password")
async def worker_set_password(
    request: WorkerSetPasswordRequest,
    worker: dict = Depends(get_current_worker)
):
    """
    Allow worker to set or change their password.
    First time: No current_password needed
    Changing: current_password required
    """
    db = get_db()
    employee_id = worker.get("employee_id")
    
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to account")
    
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in request.new_password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in request.new_password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    
    worker_account = await db.worker_accounts.find_one(
        {"employee_id": employee_id},
        {"_id": 0}
    )
    
    if worker_account and worker_account.get("password_hash"):
        if not request.current_password:
            raise HTTPException(status_code=400, detail="Current password required to change password")
        if not verify_password(request.current_password, worker_account["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    new_password_hash = get_password_hash(request.new_password)
    now = datetime.now(timezone.utc).isoformat()
    
    await db.worker_accounts.update_one(
        {"employee_id": employee_id},
        {
            "$set": {
                "password_hash": new_password_hash,
                "has_password": True,
                "password_set_at": now,
                "updated_at": now
            },
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "email": worker.get("email"),
                "created_at": now
            }
        },
        upsert=True
    )
    
    await log_audit_action(
        employee_id,
        "password_set" if not (worker_account and worker_account.get("password_hash")) else "password_changed",
        "worker_account",
        employee_id,
        {"method": "worker_portal"}
    )
    
    return {
        "success": True,
        "message": "Password set successfully. You can now login with your email and password."
    }


@router.get("/worker/account-status")
async def worker_account_status(worker: dict = Depends(get_current_worker)):
    """Get worker's account status including whether password is set."""
    db = get_db()
    employee_id = worker.get("employee_id")
    
    worker_account = await db.worker_accounts.find_one(
        {"employee_id": employee_id},
        {"_id": 0, "has_password": 1, "password_set_at": 1, "last_login": 1}
    )
    
    return {
        "has_password": bool(worker_account and worker_account.get("has_password")),
        "password_set_at": worker_account.get("password_set_at") if worker_account else None,
        "last_login": worker_account.get("last_login") if worker_account else None
    }
