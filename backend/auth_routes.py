"""
Authentication API Routes
Handles login, password change, profile, and logout for both Super Admin and Company Users.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from auth import (
    validate_password_strength,
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    generate_secure_password,
    require_super_admin,
    require_role,
    get_current_user,
    get_current_active_user,
    log_audit
)
from database import (
    get_super_admin_by_email,
    get_user_by_email,
    get_user_by_id,
    get_company_by_id,
    get_company_modules,
    update_last_login,
    update_user,
    update_super_admin,
    save_audit_log
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
logger = __import__('logging').getLogger("reconciliation_tool")

# ============== LOGIN ==============

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    company_code: Optional[str] = Form(None)
):
    email = email.strip()
    if company_code:
        company_code = company_code.strip()

    client_ip = request.client.host if request.client else None
    
    # Try Super Admin first (no company code needed)
    admin = get_super_admin_by_email(email)
    if admin:
        if admin.get('status') != 'active':
            raise HTTPException(status_code=401, detail="Super Admin account is inactive")
        if not verify_password(password, admin['password_hash']):
            raise HTTPException(status_code=401, detail="User ID or password has been entered incorrectly. Please enter the correct details.")
            
        update_last_login(admin['id'], is_super_admin=True)
        
        token = create_access_token({
            "user_id": admin['id'],
            "email": admin['email'],
            "name": admin.get('name', 'Super Admin'),
            "role": "super_admin",
            "company_id": None,
            "module_id": None,
            "first_login": False
        })
        
        save_audit_log(
            user_id=admin['id'],
            user_role='super_admin',
            action='LOGIN',
            entity_type='super_admin',
            entity_id=admin['id'],
            details='Super Admin logged in',
            ip_address=client_ip
        )
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": admin['id'],
                "email": admin['email'],
                "name": admin.get('name', 'Super Admin'),
                "role": "super_admin",
                "company_id": None
            },
            "requires_password_change": False,
            "message": "Login successful"
        }
    
    # Try Company User
    if not company_code:
        raise HTTPException(status_code=401, detail="Company code required for company users")
    
    from database import get_company_by_code
    company = get_company_by_code(company_code)
    if not company or company.get('status') != 'active':
        raise HTTPException(status_code=401, detail="Company code has been entered incorrectly or is inactive. Please enter the correct details.")
    
    user = get_user_by_email(email, company_id=company['id'])
    if not user or user.get('status') != 'active':
        raise HTTPException(status_code=401, detail="User ID or password has been entered incorrectly. Please enter the correct details.")
    
    if not verify_password(password, user['password_hash']):
        raise HTTPException(status_code=401, detail="User ID or password has been entered incorrectly. Please enter the correct details.")
    
    update_last_login(user['id'])
    
    # Get company modules for context
    modules = get_company_modules(company['id'])
    module_id = modules[0]['id'] if modules else None
    
    # Get user's role_id and assigned modules
    from database import get_user_assigned_module_ids, get_role_by_id
    user_module_ids = get_user_assigned_module_ids(user['id'])
    role_id = user.get('role_id')
    
    page_permissions = []
    if role_id:
        role_data = get_role_by_id(role_id)
        if role_data and role_data.get('page_permissions'):
            page_permissions = role_data['page_permissions']
    
    # If user has no assigned modules, default to company's first module
    if user_module_ids:
        module_id = user_module_ids[0] if user_module_ids[0] in [m['id'] for m in modules] else (modules[0]['id'] if modules else None)
    else:
        module_id = modules[0]['id'] if modules else None
    
    token = create_access_token({
        "user_id": user['id'],
        "email": user['email'],
        "name": user.get('name', ''),
        "role": user['role'],
        "role_id": role_id,
        "company_id": company['id'],
        "company_code": company['code'],
        "company_name": company['name'],
        "module_id": module_id,
        "first_login": bool(user.get('first_login', 0))
    })
    
    save_audit_log(
        user_id=user['id'],
        user_role=user['role'],
        action='LOGIN',
        entity_type='user',
        entity_id=user['id'],
        details=f'User logged in to company {company["name"]}',
        company_id=company['id'],
        ip_address=client_ip
    )
    
    # Filter modules to only those assigned to user
    user_modules = [m for m in modules if m['id'] in user_module_ids] if user_module_ids else modules
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "name": user.get('name', ''),
            "role": user['role'],
            "role_id": role_id,
            "company_id": company['id'],
            "company_name": company['name'],
            "company_code": company['code'],
            "module_id": module_id,
            "first_login": bool(user.get('first_login', 0)),
            "page_permissions": page_permissions
        },
        "modules": user_modules,
        "requires_password_change": bool(user.get('first_login', 0)),
        "message": "Login successful"
    }


# ============== PASSWORD CHANGE ==============

@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Change password for both Super Admin and Company Users.
    Validates new password strength and verifies old password.
    """
    user_id = current_user['user_id']
    role = current_user['role']
    client_ip = request.client.host if request.client else None
    
    # Validate new password strength
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    if role == 'super_admin':
        admin = get_super_admin_by_email(current_user['email'])
        if not admin:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not verify_password(current_password, admin['password_hash']):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        update_super_admin(admin['id'], password_hash=hash_password(new_password))
        
        save_audit_log(
            user_id=admin['id'],
            user_role='super_admin',
            action='PASSWORD_CHANGE',
            entity_type='super_admin',
            entity_id=admin['id'],
            ip_address=client_ip
        )
    else:
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not verify_password(current_password, user['password_hash']):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        update_user(user_id, password_hash=hash_password(new_password), first_login=0)
        
        save_audit_log(
            user_id=user_id,
            user_role=user['role'],
            action='PASSWORD_CHANGE',
            entity_type='user',
            entity_id=user_id,
            company_id=current_user.get('company_id'),
            ip_address=client_ip
        )
    
    return {
        "success": True,
        "message": "Password changed successfully. Please login again with your new password."
    }


# ============== FORCED FIRST LOGIN PASSWORD CHANGE ==============

@router.post("/force-change-password")
async def force_change_password(
    request: Request,
    new_password: str = Form(...),
    token: str = Form(...)
):
    """
    Change password using a token (for first-login forced change).
    Bypasses current password check.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get('user_id')
    role = payload.get('role')
    
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    client_ip = request.client.host if request.client else None
    
    if role == 'super_admin':
        admin = get_super_admin_by_email(payload['email'])
        if not admin:
            raise HTTPException(status_code=404, detail="User not found")
        update_super_admin(admin['id'], password_hash=hash_password(new_password))
    else:
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        update_user(user_id, password_hash=hash_password(new_password), first_login=0)
    
    return {
        "success": True,
        "message": "Password updated successfully. Please login again."
    }


# ============== PROFILE ==============

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_active_user)):
    """Get current user's profile information."""
    role = current_user['role']
    
    if role == 'super_admin':
        admin = get_super_admin_by_email(current_user['email'])
        if not admin:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "profile": {
                "id": admin['id'],
                "email": admin['email'],
                "name": admin.get('name', 'Super Admin'),
                "role": "super_admin",
                "company_id": None,
                "company_name": None,
                "created_at": admin.get('created_at')
            }
        }
    else:
        user = get_user_by_id(current_user['user_id'])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        company = get_company_by_id(user['company_id']) if user.get('company_id') else None
        
        return {
            "success": True,
            "profile": {
                "id": user['id'],
                "email": user['email'],
                "name": user.get('name', ''),
                "role": user['role'],
                "company_id": user.get('company_id'),
                "company_name": company['name'] if company else None,
                "company_code": company['code'] if company else None,
                "status": user.get('status'),
                "created_at": user.get('created_at'),
                "last_login": user.get('last_login')
            }
        }


@router.post("/profile/update")
async def update_profile(
    request: Request,
    name: str = Form(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Update current user's profile (name only for now)."""
    user_id = current_user['user_id']
    role = current_user['role']
    client_ip = request.client.host if request.client else None
    
    if role == 'super_admin':
        admin = get_super_admin_by_email(current_user['email'])
        if admin:
            update_super_admin(admin['id'], name=name)
    else:
        update_user(user_id, name=name)
    
    save_audit_log(
        user_id=user_id,
        user_role=role,
        action='PROFILE_UPDATE',
        entity_type='user',
        entity_id=user_id,
        company_id=current_user.get('company_id'),
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "name": name
    }


# ============== VERIFY TOKEN ==============

@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_active_user)):
    """Verify if current token is valid and return user info."""
    page_permissions = []
    role_id = current_user.get('role_id')
    if role_id:
        from database import get_role_by_id
        role_data = get_role_by_id(role_id)
        if role_data and role_data.get('page_permissions'):
            page_permissions = role_data['page_permissions']
            
    return {
        "success": True,
        "authenticated": True,
        "user": {
            "id": current_user['user_id'],
            "email": current_user['email'],
            "name": current_user.get('name', ''),
            "role": current_user['role'],
            "role_id": role_id,
            "company_id": current_user.get('company_id'),
            "module_id": current_user.get('module_id'),
            "first_login": current_user.get('first_login', False),
            "page_permissions": page_permissions
        }
    }


# ============== LOGOUT ==============

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_active_user)):
    """Client-side logout - instructs client to clear token."""
    return {
        "success": True,
        "message": "Logged out successfully"
    }


# ============== SESSION / MODULE CONTEXT ==============

@router.post("/set-module")
async def set_module_context(
    module_id: int = Form(...),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update the user's active module in their session.
    Returns a new token with updated module_id.
    """
    if current_user['role'] == 'super_admin' and not current_user.get('impersonating'):
        raise HTTPException(status_code=403, detail="Super Admin does not need module context")
    
    # Verify module belongs to company and user
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    from database import get_company_modules, get_user_assigned_module_ids
    modules = get_company_modules(company_id)
    company_module_ids = [m['id'] for m in modules]
    
    if module_id not in company_module_ids:
        raise HTTPException(status_code=403, detail="Module not assigned to your company")
    
    # Check if user has specific module assignments (admin users bypass this)
    user_role = current_user.get('role', '').lower()
    if 'admin' not in user_role:
        user_module_ids = get_user_assigned_module_ids(current_user['user_id'])
        if user_module_ids and module_id not in user_module_ids:
            raise HTTPException(status_code=403, detail="Module not assigned to you")
    
    # Generate new token with updated module
    new_token = create_access_token({
        "user_id": current_user['user_id'],
        "email": current_user['email'],
        "name": current_user.get('name', ''),
        "role": current_user['role'],
        "company_id": company_id,
        "module_id": module_id,
        "impersonating": current_user.get('impersonating', False),
        "first_login": current_user.get('first_login', False)
    })
    
    return {
        "success": True,
        "token": new_token,
        "module_id": module_id,
        "message": "Module context updated"
    }


# ============== SUPER ADMIN IMPERSONATION ==============

@router.post("/switch-context")
async def switch_context(
    request: Request,
    company_id: int = Form(...),
    module_id: Optional[int] = Form(None),
    current_user: dict = Depends(require_super_admin)
):
    """
    Super Admin only: Generate a temporary token to view a company as a company user.
    Preserves super_admin role but adds company/module context and impersonating flag.
    """
    from database import get_company_by_id, get_company_modules
    
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if company.get('status') != 'active':
        raise HTTPException(status_code=400, detail="Company is not active")
    
    # Get modules for this company
    modules = get_company_modules(company_id)
    if not modules:
        raise HTTPException(status_code=400, detail="Company has no modules assigned")
    
    # Use first module if none specified
    target_module_id = module_id if module_id else modules[0]['id']
    module_ids = [m['id'] for m in modules]
    if target_module_id not in module_ids:
        raise HTTPException(status_code=400, detail="Module not assigned to this company")
    
    target_module = next((m for m in modules if m['id'] == target_module_id), None)
    
    client_ip = request.client.host if request.client else None
    
    # Generate impersonation token
    new_token = create_access_token({
        "user_id": current_user['user_id'],
        "email": current_user['email'],
        "name": current_user.get('name', 'Super Admin'),
        "role": "super_admin",  # Keep super_admin role for permissions
        "company_id": company_id,
        "company_name": company['name'],
        "company_code": company['code'],
        "module_id": target_module_id,
        "impersonating": True,
        "first_login": False
    })
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='IMPERSONATE_COMPANY',
        entity_type='company',
        entity_id=company_id,
        details=f'Super Admin started impersonating company {company["name"]} (module: {target_module["name"] if target_module else "unknown"})',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "token": new_token,
        "company": {
            "id": company['id'],
            "name": company['name'],
            "code": company['code']
        },
        "module": {
            "id": target_module['id'],
            "name": target_module['name']
        } if target_module else None,
        "message": f"Now viewing as {company['name']}"
    }


@router.post("/restore-context")
async def restore_context(
    request: Request,
    current_user: dict = Depends(require_super_admin)
):
    """
    Super Admin only: Restore original Super Admin context (remove company impersonation).
    """
    client_ip = request.client.host if request.client else None
    
    # Generate clean super admin token without company context
    new_token = create_access_token({
        "user_id": current_user['user_id'],
        "email": current_user['email'],
        "name": current_user.get('name', 'Super Admin'),
        "role": "super_admin",
        "company_id": None,
        "module_id": None,
        "impersonating": False,
        "first_login": False
    })
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='STOP_IMPERSONATE',
        entity_type='company',
        details='Super Admin returned to normal view',
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "token": new_token,
        "message": "Returned to Super Admin view"
    }
