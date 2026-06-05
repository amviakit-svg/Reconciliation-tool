import os
import re

def patch_process_api():
    with open('backend/main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    old_endpoint = '''@app.post("/api/process")
async def process_all_rules(
    selected_source_files: Optional[str] = Form(None),
    custom_filename: Optional[str] = Form(None),
    current_user: Optional[dict] = Depends(get_optional_user)
):'''

    new_endpoint = '''@app.post("/api/process")
async def process_all_rules(
    selected_source_files: Optional[str] = Form(None),
    custom_filename: Optional[str] = Form(None),
    force: bool = Form(False),
    current_user: Optional[dict] = Depends(get_optional_user)
):'''

    content = content.replace(old_endpoint, new_endpoint)

    validation_logic = '''
    cid, mid = _get_context(current_user)
    
    # --- NEW: Pre-flight Validation ---
    if not force:
        try:
            conn = get_db_connection()
            if cid is not None and mid is not None:
                all_rules = conn.execute("SELECT * FROM rules WHERE company_id = ? AND module_id = ? ORDER BY phase, id", (cid, mid)).fetchall()
            else:
                all_rules = conn.execute("SELECT * FROM rules ORDER BY phase, id").fetchall()
            conn.close()
            
            p1 = [dict(r) for r in all_rules if r['phase'] == 1]
            p2 = [dict(r) for r in all_rules if r['phase'] == 2]
            p3 = [dict(r) for r in all_rules if r['phase'] == 3]
            p4 = [dict(r) for r in all_rules if r['phase'] == 4]
            
            p1_rules = p1[-1] if p1 else None
            p2_rules = p2[-1] if p2 else None
            p3_rules = p3[-1] if p3 else None
            
            generated_cols = {'Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'}
            
            if p1_rules:
                try:
                    c1 = json.loads(p1_rules['config'])
                    generated_cols.add(c1.get('column', 'Order ID'))
                    for f in c1.get('fields', []):
                        if f.get('name'): generated_cols.add(f['name'])
                except: pass
                
            if p2_rules:
                try:
                    c2 = json.loads(p2_rules['config'])
                    for r in c2:
                        if r.get('column_name'): generated_cols.add(r['column_name'])
                except: pass
                
            if p3_rules:
                try:
                    c3 = json.loads(p3_rules['config'])
                    for g in c3:
                        if g.get('column_name'): generated_cols.add(g['column_name'])
                except: pass
                
            required_cols = set()
            for r in p4:
                try:
                    c4 = json.loads(r['config'])
                    for f in c4.get('value_fields', []):
                        if f.get('column'): required_cols.add(f['column'])
                    for f in c4.get('row_fields', []):
                        if f: required_cols.add(f)
                    for f in c4.get('column_fields', []):
                        if f: required_cols.add(f)
                except: pass
                
            missing = required_cols - generated_cols
            if missing:
                return {
                    "success": False,
                    "type": "validation_warning",
                    "missing_columns": list(missing),
                    "message": "Validation warning"
                }
        except Exception as e:
            logger.error(f"Validation error: {e}")
            # Ignore validation errors and proceed
    # --- END Validation ---
'''

    old_cid_mid = '''    cid, mid = _get_context(current_user)
    
    with processing_lock:'''

    new_cid_mid = validation_logic + '''
    with processing_lock:'''

    if old_cid_mid in content:
        content = content.replace(old_cid_mid, new_cid_mid)
        print("Patched /api/process endpoint validation")
    else:
        print("Could not find insertion point for validation")

    with open('backend/main.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_process_api()
