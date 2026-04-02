"""
Supabase Storage Helper for File Uploads
Used for production deployments on Railway/external hosting.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx

logger = logging.getLogger("supabase_storage")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Default bucket for application documents
DEFAULT_BUCKET = "documents"


def is_supabase_storage_configured() -> bool:
    """Check if Supabase storage is configured."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


async def upload_to_supabase(
    file_content: bytes,
    filename: str,
    bucket: str = DEFAULT_BUCKET,
    folder: str = "uploads"
) -> Dict[str, Any]:
    """
    Upload a file to Supabase Storage.
    
    Args:
        file_content: The file bytes
        filename: Original filename
        bucket: Storage bucket name
        folder: Folder within bucket
    
    Returns:
        dict with 'url' and 'path' keys
    
    Raises:
        Exception if upload fails
    """
    if not is_supabase_storage_configured():
        raise Exception("Supabase storage not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    
    # Generate unique path
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_filename = filename.replace(" ", "_").replace("/", "_")
    storage_path = f"{folder}/{timestamp}_{safe_filename}"
    
    # Upload URL
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"
    
    # Determine content type
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    content_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
    }
    content_type = content_types.get(ext, 'application/octet-stream')
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true"  # Overwrite if exists
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            upload_url,
            content=file_content,
            headers=headers
        )
        
        if response.status_code not in [200, 201]:
            error_detail = response.text
            logger.error(f"Supabase upload failed: {response.status_code} - {error_detail}")
            raise Exception(f"Upload failed: {response.status_code} - {error_detail}")
    
    # Generate public URL
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"
    
    logger.info(f"Uploaded to Supabase: {storage_path}")
    
    return {
        "url": public_url,
        "path": storage_path,
        "bucket": bucket,
        "filename": filename
    }


async def delete_from_supabase(
    path: str,
    bucket: str = DEFAULT_BUCKET
) -> bool:
    """
    Delete a file from Supabase Storage.
    
    Args:
        path: The storage path
        bucket: Storage bucket name
    
    Returns:
        True if deleted successfully
    """
    if not is_supabase_storage_configured():
        return False
    
    delete_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(delete_url, headers=headers)
        
        if response.status_code in [200, 204]:
            logger.info(f"Deleted from Supabase: {path}")
            return True
        else:
            logger.warning(f"Delete failed: {response.status_code}")
            return False


def get_supabase_public_url(path: str, bucket: str = DEFAULT_BUCKET) -> str:
    """Get the public URL for a stored file."""
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
