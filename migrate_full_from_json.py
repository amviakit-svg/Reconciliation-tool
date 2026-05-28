import json
import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime

# Paths
JSON_PATH = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\EasyRecon_Metadata_Export_20260519_183457.json"
DB_PATH = "data/metadata.db"
OLD_BASE = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool till all feature are working with condition\Reconciliation tool\data\uploads"
NEW_UPLOADS = "data/uploads"

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(NEW_UPLOADS, exist_ok=True)

# Load JSON
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# ============================================
# STEP 1: Initialize defaults
# ============================================

# Check if TestCorp exists
company = conn.execute("SELECT id FROM companies WHERE code = ?", ("TESTCORP",)).fetchone()
if company:
    company_id = company['id']
    print(f"Using existing company id={company_id}")
else:
    cursor = conn.execute(
        "INSERT INTO companies (name, code, email, status) VALUES (?, ?, ?, ?)",
        ("TestCorp", "TESTCORP", "admin@testcorp.com", "active")
    )
    company_id = cursor.lastrowid
    print(f"Created TestCorp company id={company_id}")

# Check if Own Website module exists
module = conn.execute("SELECT id FROM modules WHERE code = ?", ("OWN_WEBSITE",)).fetchone()
if module:
    module_id = module['id']
    print(f"Using existing module id={module_id}")
else:
    cursor = conn.execute(
        "INSERT INTO modules (name, code, description, status) VALUES (?, ?, ?, ?)",
        ("Own Website", "OWN_WEBSITE", "Own website reconciliation module", "active")
    )
    module_id = cursor.lastrowid
    print(f"Created Own Website module id={module_id}")

# Assign module to company
conn.execute(
    "INSERT OR IGNORE INTO company_modules (company_id, module_id, status) VALUES (?, ?, ?)",
    (company_id, module_id, "active")
)

# Create a default user if none exists
user = conn.execute("SELECT id FROM users WHERE company_id = ? LIMIT 1", (company_id,)).fetchone()
if not user:
    from backend.auth import hash_password
    cursor = conn.execute(
        "INSERT INTO users (company_id, email, password_hash, name, role, status, first_login) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (company_id, "admin@testcorp.com", hash_password("Test@123"), "Admin", "Company Admin", "active", 0)
    )
    user_id = cursor.lastrowid
    print(f"Created default user id={user_id}")

conn.commit()

# ============================================
# STEP 2: Create folders
# ============================================

print("\n--- Creating folders ---")
folder_id_map = {}  # old_id -> new_id

# Sort folders by parent_id to process Root first
folders = sorted(data['folders'], key=lambda x: (x['parent_id'] is not None, x['parent_id'] or 0))

for folder in folders:
    old_id = folder['id']
    name = folder['name']
    old_parent_id = folder['parent_id']
    
    # Map parent
    new_parent_id = folder_id_map.get(old_parent_id) if old_parent_id else None
    
    # For Root, use NULL parent
    if name == "Root":
        new_parent_id = None
    
    # Build path
    if new_parent_id:
        parent = conn.execute("SELECT path FROM folders WHERE id = ?", (new_parent_id,)).fetchone()
        parent_path = parent['path'] if parent else '/Root'
        new_path = f"{parent_path}/{name}"
    else:
        new_path = f"/Root/{name}" if name != "Root" else "/Root"
    
    cursor = conn.execute(
        "INSERT INTO folders (company_id, module_id, name, parent_id, path) VALUES (?, ?, ?, ?, ?)",
        (company_id, module_id, name, new_parent_id, new_path)
    )
    new_id = cursor.lastrowid
    folder_id_map[old_id] = new_id
    print(f"  Folder '{name}' old_id={old_id} -> new_id={new_id}, path={new_path}")

conn.commit()

# ============================================
# STEP 3: Copy files and insert records
# ============================================

print("\n--- Copying files ---")
file_id_map = {}  # old_id -> new_id

for file in data['files']:
    old_id = file['id']
    old_folder_id = file['folder_id']
    new_folder_id = folder_id_map.get(old_folder_id)
    
    if not new_folder_id:
        print(f"  WARNING: No folder mapping for file {old_id}, skipping")
        continue
    
    # Get folder path
    folder = conn.execute("SELECT path FROM folders WHERE id = ?", (new_folder_id,)).fetchone()
    folder_rel_path = folder['path'].lstrip('/').replace('/', os.sep)
    
    # Build new path
    file_name = file['name']
    new_file_dir = os.path.join(NEW_UPLOADS, folder_rel_path)
    os.makedirs(new_file_dir, exist_ok=True)
    new_file_path = os.path.join(new_file_dir, file_name)
    
    # Copy physical file from old location
    old_file_path = file['file_path']
    old_file_path_alt = old_file_path.replace(
        "Reconciliation tool till all feature are working with condition\\Reconciliation tool\\backend\\..\\data\\uploads\\",
        "Reconciliation tool till all feature are working with condition\\Reconciliation tool\\data\\uploads\\"
    )
    
    copied = False
    for src in [old_file_path, old_file_path_alt]:
        src = os.path.normpath(src)
        if os.path.exists(src):
            try:
                shutil.copy2(src, new_file_path)
                copied = True
                print(f"  Copied file {old_id}: {os.path.basename(src)}")
                break
            except Exception as e:
                print(f"  ERROR copying {src}: {e}")
    
    if not copied:
        print(f"  WARNING: Could not find source for file {old_id}: {file_name}")
        # Still insert record, but note missing file
        new_file_path = old_file_path  # keep old path as fallback
    
    # Normalize path for storage
    new_file_path = os.path.normpath(new_file_path)
    
    # Insert with explicit ID? No, let AUTOINCREMENT work, but we need mapping
    cursor = conn.execute(
        """INSERT INTO files 
           (company_id, module_id, name, original_name, folder_id, file_path, size, format, 
            sheet_count, row_count, column_count, sheet_names, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (company_id, module_id, file_name, file['original_name'], new_folder_id, 
         new_file_path, file['size'], file['format'], file['sheet_count'],
         file['row_count'], file['column_count'], file['sheet_names'], file['created_at'])
    )
    new_id = cursor.lastrowid
    file_id_map[old_id] = new_id
    print(f"    old_id={old_id} -> new_id={new_id}")

conn.commit()

# ============================================
# STEP 4: Create master files
# ============================================

print("\n--- Creating master files ---")

for mf in data.get('master_files', []):
    old_folder_id = mf['folder_id']
    new_folder_id = folder_id_map.get(old_folder_id)
    
    if not new_folder_id:
        print(f"  WARNING: No folder for master file in folder {old_folder_id}")
        continue
    
    # Copy master file if exists
    old_db_path = mf['db_path']
    old_db_path_alt = old_db_path.replace(
        "Reconciliation tool till all feature are working with condition\\Reconciliation tool\\backend\\..\\data\\master_files\\",
        "Reconciliation tool till all feature are working with condition\\Reconciliation tool\\data\\master_files\\"
    )
    
    new_master_dir = "data/master_files"
    os.makedirs(new_master_dir, exist_ok=True)
    
    # Use original master file name pattern
    old_name = os.path.basename(old_db_path)
    new_db_path = os.path.join(new_master_dir, f"folder_{new_folder_id}_master.duckdb")
    
    copied = False
    for src in [old_db_path, old_db_path_alt]:
        src = os.path.normpath(src)
        if os.path.exists(src):
            try:
                shutil.copy2(src, new_db_path)
                copied = True
                print(f"  Copied master for folder {new_folder_id}")
                break
            except Exception as e:
                print(f"  ERROR copying master {src}: {e}")
    
    if not copied:
        print(f"  WARNING: Could not find master file for folder {new_folder_id}")
        new_db_path = old_db_path  # fallback
    
    new_db_path = os.path.normpath(new_db_path)
    
    conn.execute(
        """INSERT INTO master_files 
           (company_id, module_id, folder_id, db_path, sheet_name, columns, header_row, 
            concat_columns, rejected_files, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (company_id, module_id, new_folder_id, new_db_path, mf['sheet_name'],
         mf['columns'], mf['header_row'], mf['concat_columns'], 
         mf.get('rejected_files'), mf['created_at'])
    )
    print(f"  Created master file for folder {new_folder_id}")

conn.commit()

# ============================================
# STEP 5: Import rules
# ============================================

print("\n--- Importing rules ---")

for rule in data.get('rules', []):
    phase = rule['phase']
    name = rule['name']
    config = rule['config']
    processing_type = rule.get('processing_type', 'both')
    created_at = rule['created_at']
    
    # The config contains file IDs that need remapping
    # For now, keep as-is since rule configs reference file IDs and we preserved them
    # Actually, the rules reference IDs like "34", "22" which are string IDs in the config
    # These need to be remapped to new IDs
    
    conn.execute(
        "INSERT INTO rules (company_id, module_id, name, phase, config, processing_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (company_id, module_id, name, phase, config, processing_type, created_at)
    )
    print(f"  Rule '{name}' phase={phase}")

conn.commit()

# ============================================
# STEP 6: Import processed files metadata
# ============================================

print("\n--- Importing processed files ---")

for pf in data.get('processed_files', []):
    # Copy processed file if it exists
    old_path = pf['file_path']
    old_path_alt = old_path.replace(
        "Reconciliation tool till all feature are working with condition\\Reconciliation tool\\backend\\..\\data\\processed\\",
        "Reconciliation tool till all feature are working with condition\\Reconciliation tool\\data\\processed\\"
    )
    old_path_alt2 = old_path.replace(
        "Reconciliation tool\\backend\\..\\data\\uploads\\",
        "Reconciliation tool\\data\\uploads\\"
    )
    
    new_processed_dir = "data/processed"
    os.makedirs(new_processed_dir, exist_ok=True)
    
    filename = pf['filename']
    new_path = os.path.join(new_processed_dir, filename)
    
    copied = False
    for src in [old_path, old_path_alt, old_path_alt2]:
        src = os.path.normpath(src)
        if os.path.exists(src):
            try:
                shutil.copy2(src, new_path)
                copied = True
                print(f"  Copied processed file: {filename}")
                break
            except Exception as e:
                print(f"  ERROR copying processed {src}: {e}")
    
    if not copied:
        print(f"  WARNING: Could not find processed file: {filename}")
        new_path = old_path
    
    new_path = os.path.normpath(new_path)
    
    conn.execute(
        """INSERT INTO processed_files 
           (company_id, module_id, filename, file_path, report_type, financial_year, 
            month_name, month_number, year, source_primary_filename, total_rows, 
            rules_used, sheets_data, file_size, processing_time, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (company_id, module_id, filename, new_path, pf['report_type'],
         pf['financial_year'], pf['month_name'], pf['month_number'], pf['year'],
         pf['source_primary_filename'], pf['total_rows'], pf['rules_used'],
         pf['sheets_data'], pf['file_size'], pf['processing_time'], pf['created_at'])
    )

conn.commit()

# ============================================
# Summary
# ============================================

print("\n" + "="*50)
print("MIGRATION COMPLETE")
print("="*50)
print(f"Company ID: {company_id}")
print(f"Module ID: {module_id}")
print(f"Folders created: {len(folder_id_map)}")
print(f"Files created: {len(file_id_map)}")
print(f"File ID mappings:")
for old_id, new_id in file_id_map.items():
    print(f"  {old_id} -> {new_id}")

conn.close()
print("\nDone! metadata.db is now populated.")