import re

with open("backend/database.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find def clone_company_module and the next function def set_module_template
start_idx = content.find("def clone_company_module(")
end_idx = content.find("def set_module_template(")

if start_idx == -1 or end_idx == -1:
    print("Could not find functions")
    exit(1)

new_func = """def clone_company_module(source_company_id: int, target_company_id: int, module_id: int):
    \"\"\"
    Clones all configuration (folders, rules, master files, activities) from a source 
    company to a target company for a specific module.
    \"\"\"
    import logging
    import uuid
    import shutil
    import os
    import json
    
    conn = get_db_connection()
    try:
        # 1. Clone Folders
        folder_map = {} # old_id -> new_id
        
        old_folders = conn.execute(
            "SELECT * FROM folders WHERE company_id = ? AND module_id = ? ORDER BY id ASC", 
            (source_company_id, module_id)
        ).fetchall()
        
        for f in old_folders:
            old_id = f['id']
            new_parent_id = folder_map.get(f['parent_id']) if f['parent_id'] else None
            
            cursor = conn.execute(
                \"\"\"INSERT INTO folders (company_id, module_id, name, description, parent_id, path)
                   VALUES (?, ?, ?, ?, ?, ?)\"\"\",
                (target_company_id, module_id, f['name'], f['description'], new_parent_id, f['path'])
            )
            folder_map[old_id] = cursor.lastrowid
            
        # 2. Clone Master Files (to get master_file_map first)
        master_file_map = {} # old_id -> new_id
        old_master_files = conn.execute(
            "SELECT * FROM master_files WHERE company_id = ? AND module_id = ?",
            (source_company_id, module_id)
        ).fetchall()
        
        for mf in old_master_files:
            old_mf_id = mf['id']
            if mf['folder_id'] not in folder_map:
                continue
                
            new_db_path = f"data/master_dbs/folder_{folder_map[mf['folder_id']]}_{uuid.uuid4().hex[:8]}.duckdb"
            
            # Physically copy the duckdb file if it exists
            if os.path.exists(mf['db_path']):
                os.makedirs(os.path.dirname(new_db_path), exist_ok=True)
                shutil.copy2(mf['db_path'], new_db_path)
            
            cursor = conn.execute(
                \"\"\"INSERT INTO master_files (company_id, module_id, folder_id, db_path, sheet_name, columns, header_row, concat_columns, rejected_files, formulas, auto_sync)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
                (target_company_id, module_id, folder_map[mf['folder_id']], new_db_path, mf['sheet_name'], mf['columns'], mf['header_row'], mf['concat_columns'], mf['rejected_files'], mf['formulas'], mf['auto_sync'])
            )
            master_file_map[old_mf_id] = cursor.lastrowid
            
        def remap_json_ids(obj):
            if isinstance(obj, dict):
                new_obj = {}
                for k, v in obj.items():
                    if k in ['secondary_file', 'extract_file'] and isinstance(v, str) and v.isdigit():
                        new_obj[k] = str(master_file_map.get(int(v), v))
                    elif k == 'file_id' and isinstance(v, str) and v.startswith('master_'):
                        old_id_str = v.replace('master_', '')
                        if old_id_str.isdigit():
                            new_obj[k] = f"master_{master_file_map.get(int(old_id_str), old_id_str)}"
                        else:
                            new_obj[k] = v
                    elif k == 'file_id' and isinstance(v, str) and v.isdigit():
                        new_obj[k] = str(master_file_map.get(int(v), v))
                    else:
                        new_obj[k] = remap_json_ids(v)
                return new_obj
            elif isinstance(obj, list):
                return [remap_json_ids(item) for item in obj]
            else:
                return obj

        # 3. Clone Rules
        old_rules = conn.execute(
            "SELECT * FROM rules WHERE company_id = ? AND module_id = ?",
            (source_company_id, module_id)
        ).fetchall()
        
        for r in old_rules:
            config_str = r['config']
            try:
                if config_str:
                    config_data = json.loads(config_str)
                    config_data = remap_json_ids(config_data)
                    config_str = json.dumps(config_data)
            except Exception:
                pass # If it fails to parse, just use original
                
            conn.execute(
                \"\"\"INSERT INTO rules (company_id, module_id, name, phase, config, processing_type)
                   VALUES (?, ?, ?, ?, ?, ?)\"\"\",
                (target_company_id, module_id, r['name'], r['phase'], config_str, r['processing_type'])
            )
            
        # 4. Clone Master Activities
        old_activities = conn.execute(
            "SELECT * FROM master_activities WHERE company_id = ? AND module_id = ?",
            (source_company_id, module_id)
        ).fetchall()
        
        for act in old_activities:
            new_folder_id = folder_map.get(act['folder_id'])
            new_mf_id = master_file_map.get(act['master_file_id']) if act['master_file_id'] else None
            
            if not new_folder_id:
                continue
                
            payload_str = act['payload_json']
            try:
                if payload_str:
                    payload_data = json.loads(payload_str)
                    payload_data = remap_json_ids(payload_data)
                    payload_str = json.dumps(payload_data)
            except Exception:
                pass
                
            conn.execute(
                \"\"\"INSERT INTO master_activities (master_file_id, folder_id, company_id, module_id, step_order, activity_type, target_column, payload_json, is_enabled)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
                (new_mf_id, new_folder_id, target_company_id, module_id, act['step_order'], act['activity_type'], act['target_column'], payload_str, act['is_enabled'])
            )

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        import logging
        logging.getLogger("reconciliation_tool").error(f"Error cloning module {module_id} from {source_company_id} to {target_company_id}: {e}")
        raise e
    finally:
        conn.close()


"""

new_content = content[:start_idx] + new_func + content[end_idx:]

with open("backend/database.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Patched database.py successfully")
