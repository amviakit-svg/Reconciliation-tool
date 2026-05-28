"""
Super Admin API Routes
Handles all Super Admin functionality: Dashboard, Company Management,
Website Settings, Module/Role Management, and Code Extraction.
"""

import os
import json
import zipfile
import shutil
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Form, HTTPException, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse

from auth import (
    require_super_admin,
    hash_password,
    validate_password_strength,
    generate_secure_password,
    get_current_active_user
)
from database import (
    get_companies, get_company_by_id, get_company_by_code, create_company, update_company, delete_company,
    get_modules, get_module_by_id, get_module_by_code,
    assign_module_to_company, get_company_modules, remove_module_from_company,
    get_company_users, create_user, update_user, delete_user,
    get_all_settings, set_setting,
    get_audit_logs, save_audit_log,
    get_db_connection,
    create_company_file_structure
)

router = APIRouter(prefix="/api/super-admin", tags=["Super Admin"])
logger = __import__('logging').getLogger("reconciliation_tool")


# ============== DASHBOARD ==============

@router.get("/dashboard")
async def super_admin_dashboard(current_user: dict = Depends(require_super_admin)):
    """Get Super Admin dashboard statistics."""
    companies = get_companies()
    active_companies = [c for c in companies if c.get('status') == 'active']
    
    modules = get_modules()
    
    # Count total users across all companies
    total_users = 0
    for company in active_companies:
        users = get_company_users(company['id'], status='active')
        total_users += len(users)
    
    # Recent activity
    recent_logs = get_audit_logs(limit=10)
    
    return {
        "success": True,
        "stats": {
            "total_companies": len(companies),
            "active_companies": len(active_companies),
            "total_modules": len(modules),
            "total_users": total_users,
        },
        "recent_activity": recent_logs
    }


# ============== COMPANY MANAGEMENT ==============

@router.get("/companies")
async def list_companies(
    status: Optional[str] = None,
    current_user: dict = Depends(require_super_admin)
):
    """List all companies with optional status filter."""
    companies = get_companies(status=status)
    
    # Enrich with module count and user count
    for company in companies:
        company['module_count'] = len(get_company_modules(company['id']))
        company['user_count'] = len(get_company_users(company['id'], status='active'))
    
    return {
        "success": True,
        "companies": companies
    }


@router.post("/companies")
async def create_new_company(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    admin_email: str = Form(...),
    admin_name: str = Form(...),
    module_ids: str = Form(...),
    current_user: dict = Depends(require_super_admin)
):
    """
    Create a new company with an admin user and assigned modules.
    module_ids: comma-separated list of module IDs
    """
    client_ip = request.client.host if request.client else None
    
    # Validate company code (alphanumeric, no spaces)
    code = code.strip().upper()
    if not code or ' ' in code:
        raise HTTPException(status_code=400, detail="Company code must not contain spaces")
    
    # Check if code exists
    existing = get_company_by_code(code)
    if existing:
        raise HTTPException(status_code=400, detail="Company code already exists")
    
    # Validate admin email
    if '@' not in admin_email:
        raise HTTPException(status_code=400, detail="Invalid admin email")
    
    # Create company
    company_id = create_company(name, code, email, phone, address)
    if not company_id:
        raise HTTPException(status_code=500, detail="Failed to create company")
    
    # Generate secure password for admin
    temp_password = generate_secure_password(12)
    
    # Create company admin user
    admin_id = create_user(
        email=admin_email,
        password_hash=hash_password(temp_password),
        name=admin_name,
        role="admin",
        company_id=company_id
    )
    if not admin_id:
        # Rollback company creation
        delete_company(company_id)
        raise HTTPException(status_code=500, detail="Failed to create admin user")
    
    # Assign modules
    assigned_modules = []
    module_id_list = []
    try:
        module_id_list = [int(m.strip()) for m in module_ids.split(',') if m.strip()]
        for mid in module_id_list:
            module = get_module_by_id(mid)
            if module:
                assign_module_to_company(company_id, mid)
                assigned_modules.append(module['name'])
    except ValueError:
        pass
    
    # Auto-create physical folder structure for company modules
    storage_result = None
    storage_warnings = []
    if module_id_list:
        storage_result = create_company_file_structure(company_id, module_id_list)
        if not storage_result.get("success"):
            storage_warnings = storage_result.get("errors", [])
            logger.warning(f"Folder creation had issues for company '{name}': {storage_warnings}")
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='CREATE_COMPANY',
        entity_type='company',
        entity_id=company_id,
        details=f'Created company {name} with admin {admin_email}',
        ip_address=client_ip
    )
    
    response = {
        "success": True,
        "message": f"Company '{name}' created successfully",
        "company": {
            "id": company_id,
            "name": name,
            "code": code,
            "email": email,
            "status": "active"
        },
        "admin": {
            "id": admin_id,
            "email": admin_email,
            "name": admin_name,
            "role": "admin",
            "temp_password": temp_password  # Only shown once!
        },
        "assigned_modules": assigned_modules
    }
    
    # Include storage folder creation status
    if storage_result:
        response["storage_folders"] = {
            "created": storage_result.get("created", 0),
            "failed": storage_result.get("failed", 0)
        }
        if storage_warnings:
            response["storage_warnings"] = storage_warnings
            response["message"] += f". Warning: {len(storage_warnings)} storage folder(s) could not be created."
    
    return response


@router.get("/companies/{company_id}")
async def get_company_details(
    company_id: int,
    current_user: dict = Depends(require_super_admin)
):
    """Get detailed information about a company including users and modules."""
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    users = get_company_users(company_id)
    modules = get_company_modules(company_id)
    
    return {
        "success": True,
        "company": company,
        "users": users,
        "modules": modules
    }


@router.put("/companies/{company_id}")
async def update_company_info(
    request: Request,
    company_id: int,
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    current_user: dict = Depends(require_super_admin)
):
    """Update company information."""
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    client_ip = request.client.host if request.client else None
    
    updates = {}
    if name: updates['name'] = name
    if email: updates['email'] = email
    if phone: updates['phone'] = phone
    if address: updates['address'] = address
    if status and status in ['active', 'inactive', 'deleted', 'suspended']:
        updates['status'] = status
    
    if updates:
        update_company(company_id, **updates)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='UPDATE_COMPANY',
        entity_type='company',
        entity_id=company_id,
        details=f'Updated company fields: {list(updates.keys())}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": "Company updated successfully",
        "updated_fields": list(updates.keys())
    }


@router.delete("/companies/{company_id}")
async def delete_company_soft(
    request: Request,
    company_id: int,
    current_user: dict = Depends(require_super_admin)
):
    """Soft delete a company (mark as deleted)."""
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    client_ip = request.client.host if request.client else None
    
    delete_company(company_id)
    
    # Also deactivate all users
    users = get_company_users(company_id)
    for user in users:
        update_user(user['id'], status='deleted')
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='DELETE_COMPANY',
        entity_type='company',
        entity_id=company_id,
        details=f'Soft deleted company {company["name"]}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": f"Company '{company['name']}' has been deleted"
    }


@router.post("/companies/{company_id}/reset-admin-password")
async def reset_company_admin_password(
    request: Request,
    company_id: int,
    current_user: dict = Depends(require_super_admin)
):
    """
    Reset the admin user's password for a company.
    Accessible only by Super Admin.
    """
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    # Find the active admin user for this company
    conn = get_db_connection()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE company_id = ? AND LOWER(role) IN ('admin', 'company admin') AND status = 'active' LIMIT 1",
            (company_id,)
        ).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="No active admin user found for this company")
            
        user_id = user['id']
        admin_email = user['email']
        
        temp_password = generate_secure_password(12)
        
        # Reset password and force change
        update_user(user_id, password_hash=hash_password(temp_password), first_login=1)
        
        client_ip = request.client.host if request.client else None
        save_audit_log(
            user_id=current_user['user_id'],
            user_role='super_admin',
            action='RESET_COMPANY_ADMIN_PASSWORD',
            entity_type='user',
            entity_id=user_id,
            details=f'Super Admin reset password for company admin {admin_email}',
            company_id=company_id,
            ip_address=client_ip
        )
        
        return {
            "success": True,
            "message": f"Password reset successfully for admin '{admin_email}'",
            "temp_password": temp_password
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ============== MODULE MANAGEMENT ==============

@router.get("/modules")
async def list_modules(current_user: dict = Depends(require_super_admin)):
    """List all available modules."""
    modules = get_modules()
    return {
        "success": True,
        "modules": modules
    }


@router.post("/modules")
async def create_module(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(require_super_admin)
):
    """Create a new module."""
    client_ip = request.client.host if request.client else None
    
    code = code.strip().upper().replace(' ', '_')
    
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO modules (name, code, description) VALUES (?, ?, ?)
        ''', (name, code, description))
        module_id = cursor.lastrowid
        conn.commit()
        
        save_audit_log(
            user_id=current_user['user_id'],
            user_role='super_admin',
            action='CREATE_MODULE',
            entity_type='module',
            entity_id=module_id,
            details=f'Created module {name} ({code})',
            ip_address=client_ip
        )
        
        return {
            "success": True,
            "message": f"Module '{name}' created successfully",
            "module": {
                "id": module_id,
                "name": name,
                "code": code,
                "description": description
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create module: {str(e)}")
    finally:
        conn.close()


@router.post("/companies/{company_id}/modules/{module_id}")
async def assign_module(
    request: Request,
    company_id: int,
    module_id: int,
    current_user: dict = Depends(require_super_admin)
):
    """Assign a module to a company."""
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    module = get_module_by_id(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    client_ip = request.client.host if request.client else None
    
    assign_module_to_company(company_id, module_id)
    
    # Auto-create folder structure for this module
    storage_result = create_company_file_structure(company_id, [module_id])
    storage_warning = None
    if not storage_result.get("success"):
        storage_warning = storage_result.get("errors", [])
        logger.warning(f"Folder creation failed for module assignment: company={company_id}, module={module_id}: {storage_warning}")
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='ASSIGN_MODULE',
        entity_type='company_module',
        entity_id=company_id,
        details=f'Assigned module {module["name"]} to company {company["name"]}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    response = {
        "success": True,
        "message": f"Module '{module['name']}' assigned to company '{company['name']}'"
    }
    
    if storage_warning:
        response["storage_warning"] = storage_warning[0]["suggestion"] if storage_warning else "Module assigned but storage folders could not be created."
    
    return response


@router.delete("/companies/{company_id}/modules/{module_id}")
async def unassign_module(
    request: Request,
    company_id: int,
    module_id: int,
    current_user: dict = Depends(require_super_admin)
):
    """Remove a module from a company."""
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    module = get_module_by_id(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    client_ip = request.client.host if request.client else None
    
    remove_module_from_company(company_id, module_id)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='REMOVE_MODULE',
        entity_type='company_module',
        entity_id=company_id,
        details=f'Removed module {module["name"]} from company {company["name"]}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": f"Module '{module['name']}' removed from company '{company['name']}'"
    }


# ============== ROLE MANAGEMENT ==============

@router.get("/roles")
async def list_roles(current_user: dict = Depends(require_super_admin)):
    """List all global roles."""
    from database import get_roles
    roles = get_roles()
    return {
        "success": True,
        "roles": roles
    }


@router.post("/roles")
async def create_role(
    request: Request,
    name: str = Form(...),
    page_permissions: str = Form(...),
    action_permissions: str = Form(...),
    current_user: dict = Depends(require_super_admin)
):
    """
    Create a new global role.
    page_permissions: JSON array of page slugs
    action_permissions: JSON array of action slugs
    """
    from database import create_role
    import json
    
    try:
        pages = json.loads(page_permissions)
        actions = json.loads(action_permissions)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in permissions")
    
    role_id = create_role(name, pages, actions)
    if not role_id:
        raise HTTPException(status_code=400, detail="Failed to create role")
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='CREATE_ROLE',
        entity_type='role',
        entity_id=role_id,
        details=f'Created role {name}',
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": f"Role '{name}' created",
        "role": {
            "id": role_id,
            "name": name,
            "page_permissions": pages,
            "action_permissions": actions
        }
    }


@router.put("/roles/{role_id}")
async def update_role(
    request: Request,
    role_id: int,
    name: Optional[str] = Form(None),
    page_permissions: Optional[str] = Form(None),
    action_permissions: Optional[str] = Form(None),
    current_user: dict = Depends(require_super_admin)
):
    """Update a global role."""
    from database import get_role_by_id, update_role as db_update_role
    import json
    
    role = get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    updates = {}
    if name:
        updates['name'] = name
    if page_permissions:
        try:
            updates['page_permissions'] = json.loads(page_permissions)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in page_permissions")
    if action_permissions:
        try:
            updates['action_permissions'] = json.loads(action_permissions)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in action_permissions")
    
    db_update_role(role_id, **updates)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='UPDATE_ROLE',
        entity_type='role',
        entity_id=role_id,
        details=f'Updated role {role["name"]}',
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": "Role updated successfully"
    }


@router.delete("/roles/{role_id}")
async def delete_role(
    request: Request,
    role_id: int,
    current_user: dict = Depends(require_super_admin)
):
    """Delete a global role (only if no users are using it)."""
    from database import delete_role as db_delete_role, get_role_by_id
    
    role = get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    success = db_delete_role(role_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete role: users are still assigned to it")
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='DELETE_ROLE',
        entity_type='role',
        entity_id=role_id,
        details=f'Deleted role {role["name"]}',
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "message": f"Role '{role['name']}' deleted"
    }


# ============== WEBSITE SETTINGS ==============

@router.get("/settings")
async def get_settings(current_user: dict = Depends(require_super_admin)):
    """Get all website settings."""
    settings = get_all_settings()
    return {
        "success": True,
        "settings": settings
    }


@router.post("/settings")
async def update_settings(
    request: Request,
    settings: str = Form(...),
    current_user: dict = Depends(require_super_admin)
):
    """
    Update website settings.
    settings: JSON string of key-value pairs
    """
    try:
        settings_dict = json.loads(settings)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in settings")
    
    client_ip = request.client.host if request.client else None
    
    for key, value in settings_dict.items():
        set_setting(key, value)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='UPDATE_SETTINGS',
        entity_type='website_settings',
        details=f'Updated settings: {list(settings_dict.keys())}',
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": "Settings updated successfully",
        "updated": list(settings_dict.keys())
    }


@router.post("/settings/upload-logo")
async def upload_logo(
    request: Request,
    logo: UploadFile = File(...),
    current_user: dict = Depends(require_super_admin)
):
    """Upload site logo."""
    allowed_types = ['image/png', 'image/jpeg', 'image/svg+xml']
    if logo.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, SVG allowed")
    
    ext = logo.filename.split('.')[-1].lower()
    logo_name = f"site_logo.{ext}"
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'assets', logo_name)
    os.makedirs(os.path.dirname(logo_path), exist_ok=True)
    
    with open(logo_path, "wb") as f:
        shutil.copyfileobj(logo.file, f)
    
    set_setting('site_logo', f"/static/assets/{logo_name}")
    
    return {
        "success": True,
        "message": "Logo uploaded successfully",
        "logo_url": f"/static/assets/{logo_name}"
    }


# ============== CODE EXTRACTION / DEPLOYMENT ==============

@router.get("/code-extract")
async def get_code_structure(current_user: dict = Depends(require_super_admin)):
    """Get the current code structure for extraction."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    
    structure = []
    for root, dirs, files in os.walk(project_dir):
        # Skip data directory, __pycache__, node_modules, .git
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'node_modules', '.git', 'data', 'deploy']]
        
        rel_path = os.path.relpath(root, project_dir)
        if rel_path == '.':
            rel_path = ''
        
        file_list = [f for f in files if not f.endswith('.pyc') and not f.endswith('.db')]
        if file_list:
            structure.append({
                "path": rel_path,
                "files": file_list
            })
    
    return {
        "success": True,
        "project_root": project_dir,
        "structure": structure,
        "exclude_dirs": ['data', '__pycache__', 'node_modules', '.git', 'deploy']
    }


@router.post("/code-extract/download")
async def download_code(
    request: Request,
    modules: str = Form(...),
    include_docs: bool = Form(True),
    include_tests: bool = Form(False),
    current_user: dict = Depends(require_super_admin)
):
    """
    Generate a clean ZIP with tool code, no company data.
    modules: comma-separated list of module codes to include
    """
    try:
        module_list = [m.strip().upper() for m in modules.split(',') if m.strip()]
    except:
        module_list = ['PRIMARY_DATA', 'BANK_RECON', 'GST_RECON', 'INVENTORY']
    
    client_ip = request.client.host if request.client else None
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"ReconciliationTool_v2.0_{timestamp}.zip"
    zip_path = os.path.join(project_dir, 'data', zip_name)
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    
    exclude_patterns = [
        '__pycache__', '*.pyc', '*.db', '.git', 'node_modules',
        'deploy', 'data/uploads', 'data/master_files', 'data/processed', 'data/logs'
    ]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'node_modules', '.git', 'deploy']]
            
            rel_path = os.path.relpath(root, project_dir)
            
            # Skip data subdirectories
            if rel_path.startswith('data'):
                continue
            
            for file in files:
                if file.endswith('.pyc') or file.endswith('.db'):
                    continue
                
                file_path = os.path.join(root, file)
                arc_name = os.path.join("ReconciliationTool", rel_path, file)
                zipf.write(file_path, arc_name)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role='super_admin',
        action='CODE_EXTRACTION',
        entity_type='deployment',
        details=f'Extracted code ZIP with modules: {module_list}',
        ip_address=client_ip
    )
    
    return FileResponse(
        zip_path,
        filename=zip_name,
        media_type='application/zip'
    )


# ============== AUDIT LOGS ==============

@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(require_super_admin)
):
    """Get system-wide audit logs."""
    logs = get_audit_logs(limit=limit, offset=offset)
    
    return {
        "success": True,
        "logs": logs,
        "limit": limit,
        "offset": offset
    }