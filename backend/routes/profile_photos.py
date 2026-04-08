"""
Profile Photo routes for employee profile photo management.

Handles:
- Upload profile photo
- Delete profile photo
- View/stream profile photo
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response

from .dependencies import (
    get_db,
    get_current_user,
    require_manager_or_admin,
    log_audit_action
)

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter(tags=["Profile Photos"])


# ==================== LAZY IMPORTS ====================

def get_upload_to_supabase():
    """Lazy import of upload_to_supabase from supabase_storage"""
    from supabase_storage import upload_to_supabase
    return upload_to_supabase


def get_download_from_storage():
    """Lazy import of download_file_from_storage from supabase_storage"""
    from supabase_storage import download_file_from_storage
    return download_file_from_storage


def get_app_name():
    """Get APP_NAME from server.py"""
    from server import APP_NAME
    return APP_NAME


# ==================== PROFILE PHOTO ENDPOINTS ====================

@router.post("/employees/{employee_id}/profile-photo")
async def upload_profile_photo(
    employee_id: str, 
    file: UploadFile = File(...),
    user: dict = Depends(require_manager_or_admin)
):
    """Upload profile photo for an employee"""
    db = get_db()
    upload_to_supabase = get_upload_to_supabase()
    APP_NAME = get_app_name()
    
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
    filename = f"photo.{file_ext}"
    folder = f"employees/{employee_id}/profile"
    
    try:
        result = await upload_to_supabase(
            file_content=content,
            filename=filename,
            folder=folder
        )
        file_url = result.get("url", "")
        
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


@router.delete("/employees/{employee_id}/profile-photo")
async def remove_profile_photo(employee_id: str, user: dict = Depends(require_manager_or_admin)):
    """Remove profile photo for an employee"""
    db = get_db()
    
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


@router.get("/employees/{employee_id}/profile-photo/view")
async def view_profile_photo(employee_id: str, user: dict = Depends(get_current_user)):
    """View/stream profile photo for an employee"""
    db = get_db()
    download_file_from_storage = get_download_from_storage()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "profile_photo_url": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    photo_url = employee.get("profile_photo_url")
    if not photo_url:
        raise HTTPException(status_code=404, detail="No profile photo")
    
    try:
        file_bytes = await download_file_from_storage(photo_url)
        if not file_bytes:
            raise HTTPException(status_code=404, detail="Photo file not found")
        
        # Determine content type from extension
        ext = photo_url.split('.')[-1].lower() if '.' in photo_url else 'jpg'
        content_types = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'webp': 'image/webp'
        }
        content_type = content_types.get(ext, 'image/jpeg')
        return Response(content=file_bytes, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve profile photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve photo")
