code = """

# =================== TEMPLATE CLONING ===================
def clone_company_module(source_company_id: int, target_company_id: int, module_id: int):
    \"\"\"
    Clones all configuration (folders, rules, master files, activities) from a source 
    company to a target company for a specific module.
    \"\"\"
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
            
        # 2. Clone Rules
        old_rules = conn.execute(
            "SELECT * FROM rules WHERE company_id = ? AND module_id = ?",
            (source_company_id, module_id)
        ).fetchall()
        
        for r in old_rules:
            config_str = r['config']
            conn.execute(
                \"\"\"INSERT INTO rules (company_id, module_id, name, phase, config, processing_type)
                   VALUES (?, ?, ?, ?, ?, ?)\"\"\",
                (target_company_id, module_id, r['name'], r['phase'], config_str, r['processing_type'])
            )
            
        # 3. Clone Master Files & Master Activities
        master_file_map = {} # old_id -> new_id
        old_master_files = conn.execute(
            "SELECT * FROM master_files WHERE company_id = ? AND module_id = ?",
            (source_company_id, module_id)
        ).fetchall()
        
        import uuid
        for mf in old_master_files:
            old_mf_id = mf['id']
            if mf['folder_id'] not in folder_map:
                continue
                
            new_db_path = f"data/master_dbs/folder_{folder_map[mf['folder_id']]}_{uuid.uuid4().hex[:8]}.duckdb"
            
            cursor = conn.execute(
                \"\"\"INSERT INTO master_files (company_id, module_id, folder_id, db_path, sheet_name, columns, header_row, concat_columns, rejected_files, formulas, auto_sync)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
                (target_company_id, module_id, folder_map[mf['folder_id']], new_db_path, mf['sheet_name'], mf['columns'], mf['header_row'], mf['concat_columns'], mf['rejected_files'], mf['formulas'], mf['auto_sync'])
            )
            master_file_map[old_mf_id] = cursor.lastrowid
            
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
                
            conn.execute(
                \"\"\"INSERT INTO master_activities (master_file_id, folder_id, company_id, module_id, step_order, activity_type, target_column, payload_json, is_enabled)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\",
                (new_mf_id, new_folder_id, target_company_id, module_id, act['step_order'], act['activity_type'], act['target_column'], act['payload_json'], act['is_enabled'])
            )

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        import logging
        logging.getLogger(__name__).error(f"Error cloning module {module_id} from {source_company_id} to {target_company_id}: {e}")
        raise e
    finally:
        conn.close()
"""
with open("c:\\Users\\Nikhil Kumar\\.gemini\\antigravity\\scratch\\Reconciliation tool\\backend\\database.py", "a", encoding="utf-8") as f:
    f.write(code)
print("done")
