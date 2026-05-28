"""
Company API Routes
Handles Company Admin functionality: User Management, Recycle Bin, Export.
Accessible by company admins within their own company.
"""

import os
import json
import zipfile
import shutil
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse

from auth import (
    require_role,
    hash_password,
    validate_password_strength,
    generate_secure_password,
    get_current_active_user,
    require_page_permission
)
from database import (
    get_company_users, create_user, update_user, delete_user,
    get_company_by_id, get_company_modules,
    get_recycle_bin_items, permanent_delete_from_recycle_bin, restore_from_recycle_bin,
    save_audit_log,
    get_files_by_folder, get_folders,
    get_roles, get_role_by_id, assign_modules_to_user, get_user_modules,
    export_rules_json, import_rules_from_json, migrate_rules,
    get_company_by_code, get_module_by_id
)

router = APIRouter(prefix="/api/company", tags=["Company"])
logger = __import__('logging').getLogger("reconciliation_tool")


# ============== USER MANAGEMENT (Admin only) ==============

@router.get("/roles")
async def list_available_roles(
    current_user: dict = Depends(get_current_active_user)
):
    """List all available global roles for user assignment."""
    roles = get_roles()
    return {
        "success": True,
        "roles": roles
    }


@router.get("/users")
async def list_company_users(
    current_user: dict = Depends(require_page_permission("user_management"))
):
    """List all users in the current company with role and module info."""
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    users = get_company_users(company_id, status='active')
    
    # Enrich with role name and assigned modules
    for user in users:
        user.pop('password_hash', None)
        # Get role name
        if user.get('role_id'):
            role = get_role_by_id(user['role_id'])
            user['role_name'] = role['name'] if role else 'Unknown'
        else:
            user['role_name'] = user.get('role', 'viewer').capitalize()
        # Get assigned modules
        user['assigned_modules'] = get_user_modules(user['id'])
    
    return {
        "success": True,
        "users": users
    }


@router.post("/users")
async def create_company_user(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    role_id: int = Form(...),
    module_ids: str = Form(...),
    current_user: dict = Depends(require_page_permission("user_management"))
):
    """
    Create a new user in the company with role and module assignments.
    role_id: ID from global roles table
    module_ids: comma-separated list of module IDs
    """
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    # Validate role exists
    role = get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role selected")
    
    # Parse module IDs
    try:
        module_id_list = [int(m.strip()) for m in module_ids.split(',') if m.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid module IDs")
    
    # Validate modules belong to company
    company_modules = get_company_modules(company_id)
    company_module_ids = [m['id'] for m in company_modules]
    for mid in module_id_list:
        if mid not in company_module_ids:
            raise HTTPException(status_code=400, detail=f"Module ID {mid} not assigned to your company")
    
    client_ip = request.client.host if request.client else None
    
    # Generate secure temporary password
    temp_password = generate_secure_password(12)
    
    user_id = create_user(
        email=email,
        password_hash=hash_password(temp_password),
        name=name,
        role=role['name'],
        company_id=company_id
    )
    if not user_id:
        raise HTTPException(status_code=400, detail="User with this email already exists in company")
    
    # Update role_id
    update_user(user_id, role_id=role_id)
    
    # Assign modules to user
    assign_modules_to_user(user_id, module_id_list)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='CREATE_USER',
        entity_type='user',
        entity_id=user_id,
        details=f'Created user {email} with role {role["name"]} and modules {module_id_list}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": f"User '{name}' created successfully",
        "user": {
            "id": user_id,
            "email": email,
            "name": name,
            "role": role['name'],
            "temp_password": temp_password
        }
    }


@router.put("/users/{user_id}")
async def update_company_user(
    request: Request,
    user_id: int,
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    role_id: Optional[int] = Form(None),
    module_ids: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    current_user: dict = Depends(require_page_permission("user_management"))
):
    """Update a user in the company."""
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    # Verify user belongs to this company
    from database import get_user_by_id
    target_user = get_user_by_id(user_id)
    if not target_user or target_user.get('company_id') != company_id:
        raise HTTPException(status_code=404, detail="User not found in your company")
    
    client_ip = request.client.host if request.client else None
    
    updates = {}
    if name: updates['name'] = name
    if email: updates['email'] = email
    if status and status in ['active', 'inactive', 'suspended']:
        updates['status'] = status
    
    # Update role if provided
    if role_id:
        role = get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role selected")
        updates['role_id'] = role_id
        updates['role'] = role['name']
    
    if updates:
        update_user(user_id, **updates)
    
    # Update modules if provided
    if module_ids is not None:
        try:
            module_id_list = [int(m.strip()) for m in module_ids.split(',') if m.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid module IDs")
        
        # Validate modules belong to company
        company_modules = get_company_modules(company_id)
        company_module_ids = [m['id'] for m in company_modules]
        for mid in module_id_list:
            if mid not in company_module_ids:
                raise HTTPException(status_code=400, detail=f"Module ID {mid} not assigned to your company")
        
        assign_modules_to_user(user_id, module_id_list)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='UPDATE_USER',
        entity_type='user',
        entity_id=user_id,
        details=f'Updated user fields: {list(updates.keys())}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": "User updated successfully",
        "updated_fields": list(updates.keys())
    }


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    request: Request,
    user_id: int,
    current_user: dict = Depends(require_page_permission("user_management"))
):
    """Reset a user's password and force first-login change."""
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    from database import get_user_by_id
    target_user = get_user_by_id(user_id)
    if not target_user or target_user.get('company_id') != company_id:
        raise HTTPException(status_code=404, detail="User not found in your company")
    
    client_ip = request.client.host if request.client else None
    
    new_password = generate_secure_password(12)
    update_user(user_id, password_hash=hash_password(new_password), first_login=1)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='RESET_PASSWORD',
        entity_type='user',
        entity_id=user_id,
        details=f'Reset password for user {target_user["email"]}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": "Password reset successfully",
        "new_password": new_password  # Only shown once!
    }


@router.delete("/users/{user_id}")
async def delete_company_user(
    request: Request,
    user_id: int,
    current_user: dict = Depends(require_page_permission("user_management"))
):
    """Soft delete a user."""
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    if user_id == current_user['user_id']:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    from database import get_user_by_id
    target_user = get_user_by_id(user_id)
    if not target_user or target_user.get('company_id') != company_id:
        raise HTTPException(status_code=404, detail="User not found in your company")
    
    client_ip = request.client.host if request.client else None
    
    delete_user(user_id)
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='DELETE_USER',
        entity_type='user',
        entity_id=user_id,
        details=f'Deleted user {target_user["email"]}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": f"User '{target_user.get('name', '')}' has been deleted"
    }


# ============== RECYCLE BIN ==============

@router.get("/recycle-bin")
async def get_recycle_bin(
    current_user: dict = Depends(get_current_active_user)
):
    """Get recycle bin items for the company."""
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    items = get_recycle_bin_items(company_id)
    
    return {
        "success": True,
        "items": items,
        "count": len(items)
    }


@router.post("/recycle-bin/restore")
async def restore_items(
    request: Request,
    bin_ids: str = Form(...),
    current_user: dict = Depends(require_role("admin"))
):
    """
    Restore items from recycle bin.
    bin_ids: comma-separated list of recycle bin IDs
    """
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    try:
        id_list = [int(i.strip()) for i in bin_ids.split(',') if i.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bin IDs")
    
    client_ip = request.client.host if request.client else None
    
    restored_count = 0
    for bin_id in id_list:
        # Verify item belongs to this company (indirectly checked by restore_from_recycle_bin too but good to double check)
        items = get_recycle_bin_items(company_id)
        item = next((i for i in items if i['id'] == bin_id), None)
        
        if item:
            restored = restore_from_recycle_bin(bin_id)
            if restored:
                restored_count += 1
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='RESTORE',
        entity_type='recycle_bin',
        details=f'Restored {restored_count} items from recycle bin',
        company_id=company_id,
        ip_address=client_ip
    )
    
    # Optional: if you cache file data, you might need to clear it, but company_routes doesn't import clear_file_cache. 
    # Usually clients fetch fresh data anyway.
    
    return {
        "success": True,
        "message": f"{restored_count} items restored successfully",
        "restored_count": restored_count
    }

@router.post("/recycle-bin/permanent-delete")
async def permanent_delete_items(
    request: Request,
    bin_ids: str = Form(...),
    current_user: dict = Depends(require_role("admin"))
):
    """
    Permanently delete items from recycle bin.
    bin_ids: comma-separated list of recycle bin IDs
    """
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    try:
        id_list = [int(i.strip()) for i in bin_ids.split(',') if i.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bin IDs")
    
    client_ip = request.client.host if request.client else None
    
    deleted_count = 0
    for bin_id in id_list:
        # Verify item belongs to this company
        items = get_recycle_bin_items(company_id)
        item = next((i for i in items if i['id'] == bin_id), None)
        
        if item:
            if item['entity_type'] in ['file', 'master_file'] and item.get('original_path'):
                try:
                    if os.path.exists(item['original_path']):
                        os.remove(item['original_path'])
                except Exception as e:
                    logger.error(f"Error deleting file {item['original_path']}: {e}")
            
            permanent_delete_from_recycle_bin(bin_id)
            deleted_count += 1
    
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='PERMANENT_DELETE',
        entity_type='recycle_bin',
        details=f'Permanently deleted {deleted_count} items from recycle bin',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": f"{deleted_count} items permanently deleted",
        "deleted_count": deleted_count
    }


# ============== EXPORT ==============

@router.get("/export/upload-data")
async def export_upload_data(
    current_user: dict = Depends(require_role("editor"))
):
    """
    Export all upload data as ZIP with exact folder hierarchy.
    Includes original file names and folder structure.
    """
    company_id = current_user.get('company_id')
    module_id = current_user.get('module_id')
    
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    # Get all folders for this company/module
    folders = get_folders(company_id=company_id, module_id=module_id)
    
    if not folders:
        raise HTTPException(status_code=404, detail="No folders found")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"upload_data_export_{timestamp}.zip"
    export_path = os.path.join('data', 'processed', zip_name)
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in folders:
            folder_id = folder['id']
            files = get_files_by_folder(folder_id)
            
            for file in files:
                if os.path.exists(file['file_path']):
                    # Use original name in ZIP, maintaining folder path
                    arc_name = os.path.join(folder['name'], file['original_name'])
                    zipf.write(file['file_path'], arc_name)
    
    return FileResponse(
        export_path,
        filename=zip_name,
        media_type='application/zip'
    )


# ============== COMPANY MODULES ==============

@router.get("/modules")
async def list_company_modules(
    current_user: dict = Depends(get_current_active_user)
):
    """List all active modules assigned to the current user's company."""
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    modules = get_company_modules(company_id)
    
    # Filter modules for non-admin users to only show their assigned modules
    user_role = current_user.get('role', '').lower()
    if 'admin' not in user_role:
        from database import get_user_assigned_module_ids
        user_module_ids = get_user_assigned_module_ids(current_user['user_id'])
        if user_module_ids:
            modules = [m for m in modules if m['id'] in user_module_ids]
    
    return {
        "success": True,
        "modules": modules,
        "current_module_id": current_user.get('module_id')
    }


# ============== COMPANY DASHBOARD ==============

@router.get("/dashboard")
async def company_dashboard(
    current_user: dict = Depends(get_current_active_user)
):
    """Get company dashboard statistics."""
    company_id = current_user.get('company_id')
    if not company_id:
        raise HTTPException(status_code=400, detail="No company context")
    
    company = get_company_by_id(company_id)
    modules = get_company_modules(company_id)
    users = get_company_users(company_id, status='active')
    
    # Count files
    folders = get_folders(company_id=company_id)
    total_files = 0
    for folder in folders:
        files = get_files_by_folder(folder['id'])
        total_files += len(files)
    
    return {
        "success": True,
        "company": {
            "id": company['id'],
            "name": company['name'],
            "code": company['code']
        },
        "stats": {
            "modules": len(modules),
            "users": len(users),
            "folders": len(folders),
            "files": total_files
        },
        "modules": modules
    }


# ============== RULE EXPORT / IMPORT / MIGRATION ==============

@router.post("/export-rules")
async def export_rules(
    request: Request,
    company_id: int = Form(...),
    module_id: int = Form(...),
    current_user: dict = Depends(require_role("admin"))
):
    """
    Export all rules for a specific company+module as JSON.
    Returns a downloadable JSON file.
    """
    # Verify admin has access to this company
    user_company = current_user.get('company_id')
    user_role = current_user.get('role', '').lower()
    if 'super_admin' not in user_role and user_company != company_id:
        raise HTTPException(status_code=403, detail="Access denied for this company")
    
    company = get_company_by_id(company_id)
    module = get_module_by_id(module_id)
    if not company or not module:
        raise HTTPException(status_code=404, detail="Company or module not found")
    
    data = export_rules_json(company_id, module_id)
    
    # Save to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rules_{company['code']}_{module['code']}_{timestamp}.json"
    filepath = os.path.join('data', 'processed', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    client_ip = request.client.host if request.client else None
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='EXPORT_RULES',
        entity_type='rules',
        entity_id=company_id,
        details=f'Exported rules for company {company["name"]} module {module["name"]}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return FileResponse(
        filepath,
        filename=filename,
        media_type='application/json'
    )


@router.post("/import-rules")
async def import_rules(
    request: Request,
    company_id: int = Form(...),
    module_id: int = Form(...),
    rules_json: str = Form(...),
    current_user: dict = Depends(require_role("admin"))
):
    """
    Import rules from JSON string into a company+module.
    rules_json: JSON string containing exported rules data.
    """
    # Verify admin has access to this company
    user_company = current_user.get('company_id')
    user_role = current_user.get('role', '').lower()
    if 'super_admin' not in user_role and user_company != company_id:
        raise HTTPException(status_code=403, detail="Access denied for this company")
    
    company = get_company_by_id(company_id)
    module = get_module_by_id(module_id)
    if not company or not module:
        raise HTTPException(status_code=404, detail="Company or module not found")
    
    # Validate JSON
    try:
        rules_data = json.loads(rules_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    # Validate structure
    if isinstance(rules_data, dict) and 'phases' in rules_data:
        rules_list = rules_data['phases']
    elif isinstance(rules_data, list):
        rules_list = rules_data
    else:
        raise HTTPException(status_code=400, detail="Invalid rules JSON structure")
    
    # Import
    success_count = import_rules_from_json(rules_list, company_id, module_id)
    errors = []
    
    client_ip = request.client.host if request.client else None
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='IMPORT_RULES',
        entity_type='rules',
        entity_id=company_id,
        details=f'Imported {success_count} rules into company {company["name"]} module {module["name"]}. Errors: {len(errors)}',
        company_id=company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": f"Imported {success_count} rules successfully",
        "imported_count": success_count,
        "errors": errors,
        "company_id": company_id,
        "module_id": module_id
    }


@router.post("/migrate-rules")
async def migrate_rules_endpoint(
    request: Request,
    source_company_id: int = Form(...),
    source_module_id: int = Form(...),
    target_company_id: int = Form(...),
    target_module_id: int = Form(...),
    current_user: dict = Depends(require_role("admin"))
):
    """
    Migrate rules from source company/module to target company/module.
    Admin can migrate within their own company. Super Admin can migrate anywhere.
    """
    user_company = current_user.get('company_id')
    user_role = current_user.get('role', '').lower()
    is_super = 'super_admin' in user_role
    
    # Permission checks
    if not is_super:
        if user_company != source_company_id or user_company != target_company_id:
            raise HTTPException(status_code=403, detail="You can only migrate rules within your own company")
    
    # Validate companies and modules exist
    source_company = get_company_by_id(source_company_id)
    target_company = get_company_by_id(target_company_id)
    source_module = get_module_by_id(source_module_id)
    target_module = get_module_by_id(target_module_id)
    
    if not all([source_company, target_company, source_module, target_module]):
        raise HTTPException(status_code=404, detail="One or more companies/modules not found")
    
    # Validate module assignments
    source_modules = get_company_modules(source_company_id)
    target_modules = get_company_modules(target_company_id)
    if source_module_id not in [m['id'] for m in source_modules]:
        raise HTTPException(status_code=400, detail="Source module not assigned to source company")
    if target_module_id not in [m['id'] for m in target_modules]:
        raise HTTPException(status_code=400, detail="Target module not assigned to target company")
    
    # Execute migration
    success_count = migrate_rules(source_company_id, target_company_id, source_module_id, target_module_id)
    errors = []
    
    client_ip = request.client.host if request.client else None
    save_audit_log(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        action='MIGRATE_RULES',
        entity_type='rules',
        entity_id=source_company_id,
        details=f'Migrated {success_count} rules from {source_company["name"]}/{source_module["name"]} to {target_company["name"]}/{target_module["name"]}',
        company_id=target_company_id,
        ip_address=client_ip
    )
    
    return {
        "success": True,
        "message": f"Migrated {success_count} rules successfully",
        "migrated_count": success_count,
        "errors": errors,
        "source": {
            "company_id": source_company_id,
            "company_name": source_company['name'],
            "module_id": source_module_id,
            "module_name": source_module['name']
        },
        "target": {
            "company_id": target_company_id,
            "company_name": target_company['name'],
            "module_id": target_module_id,
            "module_name": target_module['name']
        }
    }
