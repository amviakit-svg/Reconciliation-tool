"""
Authentication & Authorization Module
- JWT token management
- Password hashing with bcrypt
- Password strength validation
- Role-based access control (RBAC)
- Company/module context dependencies
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from functools import wraps

import bcrypt
if not hasattr(bcrypt, "__about__"):
    class DummyAbout:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = DummyAbout()

from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt

from database import get_role_by_id

logger = logging.getLogger("reconciliation_tool")

# ==== CONFIGURATION ====
SECRET_KEY = os.environ.get("SECRET_KEY", "reconciliation-tool-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ==== ROLE DEFINITIONS ====
# Hierarchical roles: viewer < editor < admin < super_admin
ROLE_HIERARCHY = {
    "viewer": 1,
    "editor": 2,
    "admin": 3,
    "super_admin": 4
}

# Page permissions mapped to roles
# Each role has access to their own pages + all lower role pages
PAGE_PERMISSIONS = {
    "viewer": ["dashboard", "primary_data"],
    "editor": ["dashboard", "primary_data", "upload_files", "rule_mapping", "final_processing"],
    "admin": ["dashboard", "primary_data", "upload_files", "rule_mapping", "final_processing", "user_management"],
    "super_admin": ["dashboard", "company_management", "website_settings", "module_management", "code_extraction", "all"]
}

# ==== PASSWORD POLICY ====
MIN_PASSWORD_LENGTH = 8
PASSWORD_PATTERN = re.compile(
    r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};:"|,.<>\/?]).{8,}$'
)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets enterprise strength requirements.
    Returns (is_valid, error_message).
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"|,.<>\/?]', password):
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{};:\"|,.<>/?)"
    
    return True, ""


# ==== PASSWORD HASHING ====
def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ==== JWT TOKEN MANAGEMENT ====
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    Data must contain: user_id, email, role, company_id (or null for super_admin)
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    to_encode.update({"iat": datetime.now(timezone.utc)})
    to_encode.update({"type": "access"})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None


# ==== AUTHENTICATION DEPENDENCIES ====
async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and validate current user from JWT token.
    Checks Authorization header first, then falls back to request cookies.
    """
    token = None
    
    # Try Authorization header
    if authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:]
        else:
            token = authorization
    
    # Try cookies as fallback
    if not token and hasattr(request, "cookies"):
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Check required fields
    required = ["user_id", "email", "role"]
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Check token expiration explicitly
    exp = payload.get("exp")
    if exp:
        exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(timezone.utc) > exp_time:
            raise HTTPException(status_code=401, detail="Token expired")
    
    return {
        "user_id": payload["user_id"],
        "email": payload["email"],
        "role": payload["role"],
        "company_id": payload.get("company_id"),
        "name": payload.get("name", ""),
        "module_id": payload.get("module_id"),
        "role_id": payload.get("role_id"),
        "impersonating": payload.get("impersonating", False),
        "first_login": payload.get("first_login", False)
    }


async def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Ensure user is active (not suspended)."""
    # Future: Check user status from database
    return current_user


# ==== ROLE-BASED ACCESS CONTROL ====
def require_role(min_role: str):
    """
    Dependency factory to require a minimum role level.
    Usage: Depends(require_role("editor"))
    """
    async def role_checker(current_user: Dict = Depends(get_current_active_user)):
        user_role = current_user.get("role", "viewer")
        
        if user_role not in ROLE_HIERARCHY:
            raise HTTPException(status_code=403, detail="Invalid role")
        
        if ROLE_HIERARCHY[user_role] < ROLE_HIERARCHY[min_role]:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Minimum role required: {min_role}"
            )
        
        return current_user
    
    return role_checker


def require_super_admin(current_user: Dict = Depends(get_current_active_user)) -> Dict:
    """Require super_admin role."""
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return current_user


def require_company_access(company_id: int, current_user: Dict = Depends(get_current_active_user)) -> bool:
    """
    Verify user has access to the specified company.
    Super admins can access all companies. Regular users only their own.
    """
    user_role = current_user.get("role", "")
    user_company = current_user.get("company_id")
    
    if user_role == "super_admin":
        return True
    
    if user_company == company_id:
        return True
    
    raise HTTPException(status_code=403, detail="Access denied for this company")


def has_page_permission(current_user: Dict, page: str) -> bool:
    """
    Check if user has permission to access a specific page/feature.
    Checks DB roles first, falls back to hardcoded PAGE_PERMISSIONS.
    """
    user_role = current_user.get("role", "viewer")
    
    if user_role == "super_admin":
        return True
    
    # Check custom role from DB first
    role_id = current_user.get("role_id")
    if role_id:
        role = get_role_by_id(role_id)
        if role:
            allowed_pages = role.get('page_permissions', [])
            if page in allowed_pages or "all" in allowed_pages:
                return True
            for allowed in allowed_pages:
                if page.startswith(allowed) or allowed.startswith(page):
                    return True
            return False
    
    # Fallback to hardcoded permissions
    allowed_pages = PAGE_PERMISSIONS.get(user_role, [])
    
    if page in allowed_pages or "all" in allowed_pages:
        return True
    
    for allowed in allowed_pages:
        if page.startswith(allowed) or allowed.startswith(page):
            return True
    
    return False


def has_action_permission(current_user: Dict, action: str) -> bool:
    """
    Check if user has permission to perform a specific action.
    """
    user_role = current_user.get("role", "viewer")
    
    if user_role == "super_admin":
        return True
    
    role_id = current_user.get("role_id")
    if role_id:
        role = get_role_by_id(role_id)
        if role:
            allowed_actions = role.get('action_permissions', [])
            return action in allowed_actions or "all" in allowed_actions
    
    return False


def require_page_permission(page: str):
    """
    Dependency factory to require permission for a specific page.
    Usage: Depends(require_page_permission("user_management"))
    """
    async def permission_checker(current_user: Dict = Depends(get_current_active_user)):
        if not has_page_permission(current_user, page):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access: {page}"
            )
        return current_user
    
    return permission_checker


def require_action_permission(action: str):
    """
    Dependency factory to require permission for a specific action.
    Usage: Depends(require_action_permission("delete_files"))
    """
    async def permission_checker(current_user: Dict = Depends(get_current_active_user)):
        if not has_action_permission(current_user, action):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to: {action}"
            )
        return current_user
    
    return permission_checker


# ==== COMPANY CONTEXT ====
def get_company_id(current_user: Dict = Depends(get_current_active_user)) -> Optional[int]:
    """Extract company_id from current user context."""
    return current_user.get("company_id")


def get_module_id(current_user: Dict = Depends(get_current_active_user)) -> Optional[int]:
    """Extract module_id from current user context."""
    return current_user.get("module_id")


# ==== AUDIT LOGGING ====
async def log_audit(
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    details: Optional[str] = None,
    company_id: Optional[int] = None,
    ip_address: Optional[str] = None
):
    """Log an audit event to the database."""
    from database import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, company_id, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, action, entity_type, entity_id, details, company_id, ip_address, datetime.now()))
        conn.commit()
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ==== HELPERS ====
def generate_secure_password(length: int = 12) -> str:
    """
    Generate a secure random password meeting all strength requirements.
    Used for initial company/user creation.
    """
    import random
    import string
    
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice("!@#$%^&*()_+-=[]{};:\"|,.<>/?")
    
    # Fill remaining with mixed characters
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{};:\"|,.<>/?"
    remaining = ''.join(random.choices(all_chars, k=length - 4))
    
    password = uppercase + lowercase + digit + special + remaining
    password_list = list(password)
    random.shuffle(password_list)
    return ''.join(password_list)


def is_first_login_required(current_user: Dict) -> bool:
    """Check if user must change password on first login."""
    return current_user.get("first_login", False)


# ==== OPTIONAL AUTH (for legacy + SaaS compatibility) ====
async def get_optional_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Extract user from JWT token if present, return None otherwise.
    This allows routes to work both in legacy mode (no auth) and SaaS mode (with auth).
    """
    token = None
    
    if authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:]
        else:
            token = authorization
    
    if not token and hasattr(request, "cookies"):
        token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    required = ["user_id", "email", "role"]
    for field in required:
        if field not in payload:
            return None
    
    return {
        "user_id": payload["user_id"],
        "email": payload["email"],
        "role": payload["role"],
        "company_id": payload.get("company_id"),
        "name": payload.get("name", ""),
        "module_id": payload.get("module_id"),
        "role_id": payload.get("role_id"),
        "first_login": payload.get("first_login", False)
    }


async def get_current_user_or_none(
    current_user: Optional[Dict] = Depends(get_optional_user)
) -> Optional[Dict]:
    """Return current user dict or None for unauthenticated requests."""
    return current_user


def get_company_context(current_user: Optional[Dict] = None) -> tuple[Optional[int], Optional[int]]:
    """Extract company_id and module_id from user context."""
    if not current_user:
        return None, None
    return current_user.get("company_id"), current_user.get("module_id")
