"""
Security Middleware and Utilities for Osabea Healthcare Portal

This module provides:
- Rate limiting for login endpoints
- Security headers middleware
- File type validation by content (not just extension)
- Login attempt tracking and account lockout
- Session timeout utilities
"""

import os
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional, Dict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# ==================== RATE LIMITING ====================

class RateLimiter:
    """Simple in-memory rate limiter for login attempts"""
    
    def __init__(self):
        # Structure: {identifier: [(timestamp, attempts)]}
        self.attempts: Dict[str, list] = defaultdict(list)
        # Structure: {identifier: lockout_until_timestamp}
        self.lockouts: Dict[str, float] = {}
        
        # Configuration
        self.max_attempts = 5  # Max attempts per window
        self.window_seconds = 3600  # 1 hour window
        self.lockout_duration = 900  # 15 minutes lockout after 10 failures
        self.lockout_threshold = 10  # Lock after this many failures
    
    def _cleanup_old_attempts(self, identifier: str):
        """Remove attempts older than the window"""
        now = time.time()
        cutoff = now - self.window_seconds
        self.attempts[identifier] = [
            (ts, count) for ts, count in self.attempts[identifier]
            if ts > cutoff
        ]
    
    def is_locked_out(self, identifier: str) -> tuple[bool, int]:
        """Check if identifier is locked out. Returns (is_locked, seconds_remaining)"""
        now = time.time()
        lockout_until = self.lockouts.get(identifier, 0)
        if now < lockout_until:
            return True, int(lockout_until - now)
        return False, 0
    
    def record_attempt(self, identifier: str, success: bool = False):
        """Record a login attempt"""
        now = time.time()
        
        if success:
            # Clear attempts on successful login
            self.attempts[identifier] = []
            self.lockouts.pop(identifier, None)
            return
        
        # Record failed attempt
        self.attempts[identifier].append((now, 1))
        self._cleanup_old_attempts(identifier)
        
        # Count recent failures
        total_failures = len(self.attempts[identifier])
        
        # Check for lockout threshold
        if total_failures >= self.lockout_threshold:
            self.lockouts[identifier] = now + self.lockout_duration
            logger.warning(f"Account locked out: {identifier[:20]}... after {total_failures} failures")
    
    def check_rate_limit(self, identifier: str) -> tuple[bool, str]:
        """
        Check if rate limit allows this request.
        Returns (allowed, error_message)
        """
        # Check lockout first
        is_locked, seconds_remaining = self.is_locked_out(identifier)
        if is_locked:
            minutes = (seconds_remaining + 59) // 60
            return False, f"Account temporarily locked. Try again in {minutes} minute(s)."
        
        # Check rate limit
        self._cleanup_old_attempts(identifier)
        recent_attempts = len(self.attempts[identifier])
        
        if recent_attempts >= self.max_attempts:
            return False, "Too many login attempts. Please wait before trying again."
        
        return True, ""

# Global rate limiter instance
login_rate_limiter = RateLimiter()


# ==================== SECURITY HEADERS MIDDLEWARE ====================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS - only in production (when not preview environment)
        host = str(request.url)
        if 'preview.emergentagent.com' not in host and 'localhost' not in host:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy (basic)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://assets.emergent.sh; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https: wss:; "
            "frame-ancestors 'none';"
        )
        
        return response


# ==================== FILE TYPE VALIDATION ====================

# Magic bytes for file type detection
FILE_SIGNATURES = {
    # PDF
    b'%PDF': 'application/pdf',
    # JPEG
    b'\xff\xd8\xff': 'image/jpeg',
    # PNG
    b'\x89PNG\r\n\x1a\n': 'image/png',
    # WebP
    b'RIFF': 'image/webp',  # Need to check for WEBP after RIFF
}

def validate_file_content(file_bytes: bytes, claimed_type: str = None) -> tuple[bool, str, str]:
    """
    Validate file by actual content, not just extension.
    
    Returns: (is_valid, detected_type, error_message)
    """
    if not file_bytes:
        return False, "", "Empty file"
    
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_bytes) > max_size:
        return False, "", "File too large. Maximum size is 10MB."
    
    # Detect actual file type by magic bytes
    detected_type = None
    
    # PDF check
    if file_bytes[:4] == b'%PDF':
        detected_type = 'application/pdf'
    
    # JPEG check
    elif file_bytes[:3] == b'\xff\xd8\xff':
        detected_type = 'image/jpeg'
    
    # PNG check
    elif file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        detected_type = 'image/png'
    
    # WebP check (RIFF....WEBP)
    elif file_bytes[:4] == b'RIFF' and len(file_bytes) > 12 and file_bytes[8:12] == b'WEBP':
        detected_type = 'image/webp'
    
    if not detected_type:
        return False, "", "Invalid file type. Only PDF, JPG, PNG, and WebP files are allowed."
    
    # If claimed type was provided, verify it matches
    if claimed_type:
        claimed_clean = claimed_type.lower().replace('image/jpg', 'image/jpeg')
        if claimed_clean not in [detected_type, 'application/octet-stream']:
            logger.warning(f"File type mismatch: claimed {claimed_type}, detected {detected_type}")
            # Allow if detected type is valid (user might have wrong extension)
    
    return True, detected_type, ""


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks.
    """
    if not filename:
        return "unnamed_file"
    
    # Remove path separators and parent directory references
    filename = filename.replace('\\', '/').split('/')[-1]
    
    # Remove dangerous patterns
    dangerous_patterns = ['..', './', '/.', '<', '>', ':', '"', '|', '?', '*', '\x00']
    for pattern in dangerous_patterns:
        filename = filename.replace(pattern, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    # Ensure it's not empty after cleaning
    if not filename or filename.startswith('.'):
        filename = 'file_' + filename.lstrip('.')
    
    return filename


# ==================== SESSION TIMEOUT ====================

# Session timeout configuration (in seconds)
ADMIN_SESSION_TIMEOUT = 15 * 60  # 15 minutes for admins
WORKER_SESSION_TIMEOUT = 30 * 60  # 30 minutes for workers

def check_session_activity(last_activity: str, role: str = 'worker') -> bool:
    """
    Check if session is still active based on last activity.
    Returns True if session is valid, False if timed out.
    """
    if not last_activity:
        return True  # No activity tracking yet
    
    try:
        last_dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        timeout = ADMIN_SESSION_TIMEOUT if role == 'admin' else WORKER_SESSION_TIMEOUT
        
        if (now - last_dt).total_seconds() > timeout:
            return False
        
        return True
    except Exception:
        return True  # Default to valid if parsing fails


# ==================== CORS CONFIGURATION ====================

def get_allowed_origins() -> list:
    """
    Get allowed CORS origins based on environment.
    Production should NOT use * wildcard.
    """
    cors_env = os.environ.get('CORS_ORIGINS', '')
    
    # Default allowed origins - production domains
    allowed = [
        'https://app.osabeacares.co.uk',
        'https://www.osabeacares.co.uk',
        'https://osabeacares.co.uk',
        'https://api.osabeacares.co.uk',  # API domain (for same-origin requests)
    ]
    
    # Add preview URL for development
    if os.environ.get('ENVIRONMENT', 'development') != 'production':
        allowed.extend([
            'https://caretrust-portal.preview.emergentagent.com',
            'http://localhost:3000',
            'http://localhost:5173',
        ])
    
    # Add any custom origins from env
    if cors_env:
        for origin in cors_env.split(','):
            origin = origin.strip()
            if origin and origin not in allowed and origin != '*':
                allowed.append(origin)
    
    # Log origins for debugging
    print(f"[CORS] Allowed origins: {allowed}")
    
    return allowed


# ==================== PASSWORD VALIDATION ====================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.
    
    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    special_chars = set('!@#$%^&*()_+-=[]{}|;:,.<>?')
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*...)"
    
    return True, ""


# ==================== AUDIT LOGGING SANITIZATION ====================

def sanitize_log_data(data: dict) -> dict:
    """
    Remove sensitive data from dictionaries before logging.
    """
    sensitive_keys = {
        'password', 'token', 'secret', 'api_key', 'apikey', 
        'access_token', 'refresh_token', 'magic_token', 'authorization',
        'credit_card', 'card_number', 'cvv', 'ssn', 'national_insurance'
    }
    
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        lower_key = key.lower()
        
        # Redact sensitive fields
        if any(sensitive in lower_key for sensitive in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_data(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized
