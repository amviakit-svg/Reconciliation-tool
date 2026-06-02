import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'metadata.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    
    # =================== CORE TABLES ===================
    
    # Companies table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Modules table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Company-Module association
    conn.execute('''
        CREATE TABLE IF NOT EXISTS company_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id),
            FOREIGN KEY (module_id) REFERENCES modules (id),
            UNIQUE(company_id, module_id)
        )
    ''')
    
    # Super Admin table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS super_admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Roles table (global, created by super admin)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            page_permissions TEXT NOT NULL,
            action_permissions TEXT NOT NULL,
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # User-Module assignment table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (module_id) REFERENCES modules (id),
            UNIQUE(user_id, module_id)
        )
    ''')

    # Users table (company users)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'viewer',
            role_id INTEGER,
            status TEXT DEFAULT 'active',
            first_login INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id),
            FOREIGN KEY (role_id) REFERENCES roles (id),
            UNIQUE(company_id, email)
        )
    ''')
    
    # Website Settings table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS website_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            setting_group TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Audit Logs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_role TEXT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT,
            company_id INTEGER,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Recycle Bin table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS recycle_bin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            entity_name TEXT NOT NULL,
            original_path TEXT,
            metadata TEXT,
            deleted_by TEXT,
            module_id INTEGER,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Folders table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            module_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            parent_id INTEGER,
            path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES folders (id)
        )
    ''')
    
    # Files table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            module_id INTEGER,
            folder_id INTEGER NOT NULL,
            name TEXT,
            original_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            format TEXT,
            size INTEGER,
            sheet_names TEXT,
            header_row INTEGER DEFAULT 1,
            sync_status TEXT DEFAULT 'pending',
            sync_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (folder_id) REFERENCES folders (id)
        )
    ''')
    
    # Migrate existing files table if header_row doesn't exist
    cursor = conn.execute("PRAGMA table_info(files)")
    cols = [row['name'] for row in cursor.fetchall()]
    if 'header_row' not in cols:
        try:
            conn.execute("ALTER TABLE files ADD COLUMN header_row INTEGER DEFAULT 1")
            conn.commit()
        except Exception:
            pass
    if 'sync_status' not in cols:
        try:
            conn.execute("ALTER TABLE files ADD COLUMN sync_status TEXT DEFAULT 'pending'")
            conn.execute("ALTER TABLE files ADD COLUMN sync_error TEXT")
            conn.commit()
        except Exception:
            pass
    
    # Master files table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS master_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            module_id INTEGER,
            folder_id INTEGER NOT NULL,
            db_path TEXT NOT NULL,
            sheet_name TEXT,
            columns TEXT,
            header_row INTEGER,
            concat_columns TEXT,
            rejected_files TEXT,
            formulas TEXT,
            auto_sync INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (folder_id) REFERENCES folders (id)
        )
    ''')
    
    # Migrate existing master_files table if auto_sync doesn't exist
    cursor = conn.execute("PRAGMA table_info(master_files)")
    cols = [row['name'] for row in cursor.fetchall()]
    if 'auto_sync' not in cols:
        try:
            conn.execute("ALTER TABLE master_files ADD COLUMN auto_sync INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

    # Notifications table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            module_id INTEGER,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Rules configuration table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            module_id INTEGER,
            name TEXT,
            phase INTEGER NOT NULL,
            config TEXT NOT NULL,
            processing_type TEXT DEFAULT 'both',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Processed files table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            module_id INTEGER,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            report_type TEXT,
            financial_year TEXT,
            month_name TEXT,
            month_number INTEGER,
            year INTEGER,
            source_primary_filename TEXT,
            total_rows INTEGER,
            rules_used INTEGER,
            sheets_data TEXT,
            file_size REAL,
            processing_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # =================== MIGRATIONS ===================
    
    # Helper to check if column exists
    def column_exists(table, column):
        try:
            conn.execute(f"SELECT {column} FROM {table} LIMIT 1")
            return True
        except:
            return False
    
    # Migrate existing tables to add company_id and module_id
    tables_to_migrate = [
        ("folders", ["company_id", "module_id"]),
        ("files", ["company_id", "module_id"]),
        ("master_files", ["company_id", "module_id"]),
        ("rules", ["company_id", "module_id"]),
        ("processed_files", ["company_id", "module_id"]),
        ("recycle_bin", ["company_id", "module_id"])
    ]
    
    for table, columns in tables_to_migrate:
        for col in columns:
            if not column_exists(table, col):
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER")
                except sqlite3.OperationalError:
                    pass
    
    # Migrate existing columns
    migrations = [
        ("rules", "processing_type", "TEXT DEFAULT 'both'"),
        ("master_files", "rejected_files", "TEXT"),
        ("processed_files", "file_size", "REAL"),
        ("processed_files", "processing_time", "TEXT"),
        ("users", "first_login", "INTEGER DEFAULT 1"),
        ("users", "role_id", "INTEGER"),
        ("master_files", "formulas", "TEXT"),
        ("companies", "status", "TEXT DEFAULT 'active'"),
        ("modules", "status", "TEXT DEFAULT 'active'"),
        ("company_modules", "status", "TEXT DEFAULT 'active'"),
        ("users", "status", "TEXT DEFAULT 'active'"),
        ("super_admin", "status", "TEXT DEFAULT 'active'"),
        ("folders", "description", "TEXT"),
        ("folders", "path", "TEXT"),
        ("files", "name", "TEXT"),
    ]
    
    for table, column, col_type in migrations:
        if not column_exists(table, column):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except sqlite3.OperationalError:
                pass
    
    # =================== DEFAULT DATA ===================
    
    # Insert default modules (6 required modules)
    default_modules = [
        ("Own Website", "OWN_WEBSITE", "Own website reconciliation module"),
        ("Amazon", "AMAZON", "Amazon marketplace reconciliation"),
        ("Flipkart", "FLIPKART", "Flipkart marketplace reconciliation"),
        ("Meesho", "MEESHO", "Meesho marketplace reconciliation"),
        ("Myntra", "MYNTRA", "Myntra marketplace reconciliation"),
        ("Hypd", "HYPD", "Hypd marketplace reconciliation")
    ]
    for name, code, desc in default_modules:
        conn.execute('''
            INSERT OR IGNORE INTO modules (name, code, description) VALUES (?, ?, ?)
        ''', (name, code, desc))
    
    # Insert default global roles if none exist
    cursor = conn.execute("SELECT COUNT(*) FROM roles")
    if cursor.fetchone()[0] == 0:
        default_roles = [
            ("Super Admin", json.dumps(["all"]), json.dumps(["all"]), 1),
            ("Company Admin", json.dumps(["dashboard","primary_data","upload_files","rule_mapping","final_processing","user_management","recycle_bin"]), json.dumps(["upload_files","delete_files","edit_rules","run_processing","manage_users","reset_passwords","export_data"]), 1),
            ("Editor", json.dumps(["dashboard","primary_data","upload_files","rule_mapping","final_processing"]), json.dumps(["upload_files","delete_files","edit_rules","run_processing","export_data"]), 1),
            ("Viewer", json.dumps(["dashboard","primary_data"]), json.dumps(["view_data"]), 1)
        ]
        for name, pages, actions, is_def in default_roles:
            conn.execute('''
                INSERT INTO roles (name, page_permissions, action_permissions, is_default) VALUES (?, ?, ?, ?)
            ''', (name, pages, actions, is_def))
    
    # Insert default website settings
    default_settings = [
        ("site_name", "Reconciliation Tool", "general"),
        ("site_logo", "", "general"),
        ("favicon", "", "general"),
        ("theme_color", "#1F4E79", "appearance"),
        ("login_page_title", "Reconciliation Tool", "general"),
        ("footer_text", "Enterprise Reconciliation System", "general")
    ]
    for key, value, group in default_settings:
        conn.execute('''
            INSERT OR IGNORE INTO website_settings (setting_key, setting_value, setting_group) VALUES (?, ?, ?)
        ''', (key, value, group))
    
    conn.commit()
    conn.close()

# =================== HELPER FUNCTIONS ===================

def create_folder(name, company_id=None, module_id=None, description=None, parent_id=None):
    conn = get_db_connection()
    
    # Calculate path dynamically
    path = f"/Root/{name}"
    if parent_id:
        parent = conn.execute("SELECT path FROM folders WHERE id = ?", (parent_id,)).fetchone()
        if parent and parent['path']:
            path = f"{parent['path']}/{name}"
            
    cursor = conn.execute(
        'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
        (name, company_id, module_id, description, parent_id, path)
    )
    folder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return folder_id

def get_folders(company_id=None, module_id=None):
    conn = get_db_connection()
    if company_id and module_id:
        rows = conn.execute(
            'SELECT * FROM folders WHERE company_id = ? AND module_id = ? ORDER BY created_at DESC',
            (company_id, module_id)
        ).fetchall()
    elif company_id:
        rows = conn.execute(
            'SELECT * FROM folders WHERE company_id = ? ORDER BY created_at DESC',
            (company_id,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM folders ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_folder(folder_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM files WHERE folder_id = ?', (folder_id,))
    conn.execute('DELETE FROM master_files WHERE folder_id = ?', (folder_id,))
    try:
        conn.execute('DELETE FROM master_file_configs WHERE folder_id = ?', (folder_id,))
    except Exception:
        pass
    conn.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
    conn.commit()
    conn.close()

def save_file_metadata(folder_id, original_name, file_path, file_format, size, sheet_names, company_id=None, module_id=None, header_row=1):
    conn = get_db_connection()
    cursor = conn.execute(
        '''INSERT INTO files (folder_id, name, original_name, file_path, format, size, sheet_names, company_id, module_id, header_row)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (folder_id, original_name, original_name, file_path, file_format, size, json.dumps(sheet_names) if sheet_names else None, company_id, module_id, header_row)
    )
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id

def get_files_by_folder(folder_id):
    import json
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT * FROM files WHERE folder_id = ? ORDER BY created_at DESC',
        (folder_id,)
    ).fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        try:
            if d.get('sheet_names'):
                sheets = json.loads(d['sheet_names'])
                if isinstance(sheets, str):
                    try:
                        sheets = json.loads(sheets)
                    except Exception:
                        pass
                        
                if isinstance(sheets, list):
                    d['sheet_count'] = len(sheets)
                else:
                    d['sheet_count'] = 1
            else:
                d['sheet_count'] = 0
        except Exception:
            d['sheet_count'] = 0
        result.append(d)
        
    return result

def delete_file(file_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
    conn.commit()
    conn.close()

def move_file(file_id, new_folder_id):
    conn = get_db_connection()
    conn.execute('UPDATE files SET folder_id = ? WHERE id = ?', (new_folder_id, file_id))
    conn.commit()
    conn.close()

def save_master_file(folder_id, db_path, sheet_name=None, columns=None, header_row=None, concat_columns=None, rejected_files=None, formulas=None, company_id=None, module_id=None, auto_sync=None):
    conn = get_db_connection()
    # Check if exists
    existing = conn.execute('SELECT id FROM master_files WHERE folder_id = ?', (folder_id,)).fetchone()
    if existing:
        conn.execute(
            '''UPDATE master_files SET db_path = ?, sheet_name = ?, columns = ?, header_row = ?, 
               concat_columns = ?, rejected_files = ?, formulas = ?, company_id = ?, module_id = ?, auto_sync = COALESCE(?, auto_sync) WHERE folder_id = ?''',
            (db_path, sheet_name, json.dumps(columns) if columns else None, header_row, 
             json.dumps(concat_columns) if concat_columns else None, 
             json.dumps(rejected_files) if rejected_files else None,
             json.dumps(formulas) if formulas else None,
             company_id, module_id, auto_sync, folder_id)
        )
    else:
        conn.execute(
            '''INSERT INTO master_files (folder_id, db_path, sheet_name, columns, header_row, 
               concat_columns, rejected_files, formulas, company_id, module_id, auto_sync)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, 0))''',
            (folder_id, db_path, sheet_name, json.dumps(columns) if columns else None, header_row,
             json.dumps(concat_columns) if concat_columns else None,
             json.dumps(rejected_files) if rejected_files else None,
             json.dumps(formulas) if formulas else None,
             company_id, module_id, auto_sync)
        )
    conn.commit()
    conn.close()

def get_master_file(folder_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM master_files WHERE folder_id = ?', (folder_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_master_file(folder_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM master_files WHERE folder_id = ?', (folder_id,))
    conn.commit()
    conn.close()

def get_master_formulas(folder_id):
    """Get persisted formulas for a master file."""
    conn = get_db_connection()
    row = conn.execute('SELECT formulas FROM master_files WHERE folder_id = ?', (folder_id,)).fetchone()
    conn.close()
    if row and row['formulas']:
        try:
            return json.loads(row['formulas'])
        except (json.JSONDecodeError, TypeError):
            return []
    return []

def update_master_formulas(folder_id, formulas_list):
    """Update persisted formulas for a master file."""
    conn = get_db_connection()
    conn.execute(
        'UPDATE master_files SET formulas = ? WHERE folder_id = ?',
        (json.dumps(formulas_list) if formulas_list else None, folder_id)
    )
    conn.commit()
    conn.close()

def save_rule(phase, config, name=None, company_id=None, module_id=None, processing_type='both'):
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO rules (phase, config, name, company_id, module_id, processing_type) VALUES (?, ?, ?, ?, ?, ?)',
        (phase, json.dumps(config), name, company_id, module_id, processing_type)
    )
    rule_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rule_id

def get_rules_by_phase(phase, company_id=None, module_id=None):
    conn = get_db_connection()
    if company_id and module_id:
        rows = conn.execute(
            'SELECT * FROM rules WHERE phase = ? AND company_id = ? AND module_id = ? ORDER BY created_at ASC',
            (phase, company_id, module_id)
        ).fetchall()
    elif company_id:
        rows = conn.execute(
            'SELECT * FROM rules WHERE phase = ? AND company_id = ? ORDER BY created_at ASC',
            (phase, company_id)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM rules WHERE phase = ? ORDER BY created_at ASC', (phase,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_rules(company_id=None, module_id=None):
    conn = get_db_connection()
    if company_id and module_id:
        rows = conn.execute(
            'SELECT * FROM rules WHERE company_id = ? AND module_id = ? ORDER BY phase ASC, created_at ASC',
            (company_id, module_id)
        ).fetchall()
    elif company_id:
        rows = conn.execute(
            'SELECT * FROM rules WHERE company_id = ? ORDER BY phase ASC, created_at ASC',
            (company_id,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM rules ORDER BY phase ASC, created_at ASC').fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_rule(rule_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM rules WHERE id = ?', (rule_id,))
    conn.commit()
    conn.close()

def move_to_recycle_bin(company_id=None, entity_type=None, entity_id=None, entity_name=None, original_path=None, metadata=None, deleted_by=None, module_id=None):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO recycle_bin (company_id, entity_type, entity_id, entity_name, original_path, metadata, deleted_by, module_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (company_id, entity_type, entity_id, entity_name, original_path, json.dumps(metadata) if metadata else None, deleted_by, module_id)
    )
    conn.commit()
    conn.close()

# =================== STORAGE ERROR HANDLING ===================

STORAGE_ERROR_MAP = {
    "company_not_found": {
        "reason": "Company record not found in database",
        "suggestion": "Verify the company exists. Super Admin must create the company first."
    },
    "module_not_found": {
        "reason": "Module record not found in database",
        "suggestion": "Verify the module exists. Check Modules page in Super Admin panel."
    },
    "dir_create_failed": {
        "reason_template": "Unable to create directory: {path}",
        "suggestion": "Check disk space and write permissions on the server filesystem. Error: {os_error}"
    },
    "disk_full": {
        "reason": "No disk space remaining on the server",
        "suggestion": "Free up disk space or contact your server administrator."
    },
    "permission_denied": {
        "reason_template": "Write permission denied for directory: {path}",
        "suggestion": "The server process needs write access. Check folder permissions and ensure the directory is writable."
    },
    "invalid_folder_name": {
        "reason_template": "Folder name '{name}' contains invalid characters",
        "suggestion": "Use only letters, numbers, spaces, hyphens, and underscores. Avoid characters: \\ / : * ? \" < > |"
    },
    "path_too_long": {
        "reason": "File path exceeds operating system limit (260 characters)",
        "suggestion": "Use shorter folder and file names. Keep the full path under 260 characters."
    },
    "file_exists": {
        "reason_template": "A file named '{name}' already exists in this folder",
        "suggestion": "Rename the file before uploading, or delete the existing file first."
    },
    "parent_missing": {
        "reason": "Parent directory does not exist on disk",
        "suggestion": "The folder structure may be incomplete. Try recreating the folder or contact support."
    },
    "unknown": {
        "reason": "An unexpected storage error occurred",
        "suggestion": "Check server logs for details and contact support if the issue persists."
    }
}

def format_storage_error(error_key, extra_context=None, status_code=500):
    """Build a structured storage error response with reason and actionable suggestion."""
    import os
    mapping = STORAGE_ERROR_MAP.get(error_key, STORAGE_ERROR_MAP["unknown"])
    reason = mapping.get("reason_template", mapping.get("reason", "Unknown error"))
    suggestion = mapping.get("suggestion", "Check server logs for details.")
    
    if extra_context:
        for k, v in extra_context.items():
            placeholder = "{" + k + "}"
            if placeholder in reason:
                reason = reason.replace(placeholder, str(v))
            if placeholder in suggestion:
                suggestion = suggestion.replace(placeholder, str(v))
    
    return {
        "success": False,
        "error_code": error_key,
        "reason": reason,
        "suggestion": suggestion,
        "path": extra_context.get("path", "") if extra_context else ""
    }

def is_valid_folder_name(name):
    """Validate folder name against forbidden characters."""
    if not name or not name.strip():
        return False
    forbidden = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}
    if any(c in name for c in forbidden):
        return False
    if name.strip() in ('.', '..'):
        return False
    return True

def get_company_storage_path(company_id, module_id=None, subfolder=None):
    """
    Build storage path using human-readable company/module names.
    Returns dict: {"success": True/False, "path": "...", ...}
    Path format: data/uploads/{CompanyName}_{CompanyCode}/{ModuleName}/{subfolder}/
    Creates directories on demand.
    """
    import os
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    conn = get_db_connection()
    try:
        # Resolve company
        company = conn.execute("SELECT name, code FROM companies WHERE id = ?", (company_id,)).fetchone()
        if not company:
            return format_storage_error("company_not_found", {"company_id": company_id})
        
        company_folder = str(company['name']).strip()
        # Sanitize folder name by replacing invalid characters
        import re
        company_folder = re.sub(r'[\\/*?:"<>|]', "", company_folder)
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads')
        path = os.path.join(base_dir, company_folder)
        
        if module_id is not None:
            module = conn.execute("SELECT name FROM modules WHERE id = ?", (module_id,)).fetchone()
            if not module:
                return format_storage_error("module_not_found", {"module_id": module_id})
            path = os.path.join(path, module['name'])
        
        if subfolder:
            path = os.path.join(path, subfolder)
        
        # Create directories
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory '{path}': {e}")
            if e.errno == 28:  # No space left
                return format_storage_error("disk_full", {"path": path})
            elif e.errno == 13:  # Permission denied
                return format_storage_error("permission_denied", {"path": path, "os_error": str(e)})
            else:
                return format_storage_error("dir_create_failed", {"path": path, "os_error": str(e)})
        
        return {"success": True, "path": path}
    except Exception as e:
        logger.error(f"get_company_storage_path error: {e}")
        return format_storage_error("unknown", {"detail": str(e)})
    finally:
        conn.close()

def add_notification(company_id: int, module_id: int, notif_type: str, message: str, link: str = None):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO notifications (company_id, module_id, type, message, link) VALUES (?, ?, ?, ?, ?)",
            (company_id, module_id, notif_type, message, link)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error adding notification: {e}")

def get_recent_notifications(company_id: int, module_id: int, limit: int = 50):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        query = "SELECT * FROM notifications WHERE 1=1"
        params = []
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        if module_id:
            query += " AND module_id = ?"
            params.append(module_id)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return []

def mark_notification_read(notification_id: int, company_id: int = None):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        if company_id:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND company_id = ?", (notification_id, company_id))
        else:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        return False

def mark_all_notifications_read(company_id: int, module_id: int = None):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        query = "UPDATE notifications SET is_read = 1 WHERE company_id = ?"
        params = [company_id]
        if module_id:
            query += " AND module_id = ?"
            params.append(module_id)
            
        conn.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error marking all notifications read: {e}")
        return False

def cleanup_old_notifications(days: int = 30):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM notifications WHERE created_at < datetime('now', ?)", (f'-{days} days',))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {e}")

def get_user_folder_path(company_id, module_id, folder_name):
    """
    Get the physical path for a user-created folder within the uploads hierarchy.
    Returns dict: {"success": True/False, "path": "..."}
    Path: {CompanyName_CODE}/{ModuleName}/uploads/{folder_name}/
    """
    import os
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    # Validate folder name
    if not is_valid_folder_name(folder_name):
        return format_storage_error("invalid_folder_name", {"name": folder_name})
    
    result = get_company_storage_path(company_id, module_id, "uploads_files")
    if not result.get("success"):
        return result
    
    full_path = os.path.join(result["path"], folder_name)
    
    # Check path length
    if len(full_path) > 260:
        return format_storage_error("path_too_long", {"path": full_path})
    
    try:
        os.makedirs(full_path, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create user folder '{full_path}': {e}")
        if e.errno == 28:
            return format_storage_error("disk_full", {"path": full_path})
        elif e.errno == 13:
            return format_storage_error("permission_denied", {"path": full_path, "os_error": str(e)})
        else:
            return format_storage_error("dir_create_failed", {"path": full_path, "os_error": str(e)})
    
    return {"success": True, "path": full_path}

def create_company_file_structure(company_id, module_ids):
    """
    Create the full directory tree for a company's modules AND
    insert Root folder records in the folders database table.
    Returns dict: {"success": True/False, "created": N, "failed": N, "errors": [...]}
    """
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    subfolders = ["uploads_files", "master_files", "primary_data", "processed"]
    created = 0
    failed = 0
    errors = []
    
    for mid in module_ids:
        for sf in subfolders:
            result = get_company_storage_path(company_id, mid, sf)
            if result.get("success"):
                created += 1
            else:
                failed += 1
                errors.append({
                    "module_id": mid,
                    "subfolder": sf,
                    "error_code": result.get("error_code", "unknown"),
                    "reason": result.get("reason", ""),
                    "suggestion": result.get("suggestion", "")
                })
                logger.warning(f"Folder creation failed: company={company_id}, module={mid}, subfolder={sf}: {result}")
        
        # Auto-create Root folder record in the folders DB table for this module
        # if one doesn't already exist (ensures folder dropdown is populated)
        try:
            conn = get_db_connection()
            existing = conn.execute(
                'SELECT id FROM folders WHERE company_id = ? AND module_id = ? AND name = ? AND parent_id IS NULL',
                (company_id, mid, 'Root')
            ).fetchone()
            if not existing:
                # Build the display path: /Root
                display_path = '/Root'
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                    ('Root', company_id, mid, None, None, display_path)
                )
                root_id = cursor.lastrowid
                
                # Insert ONLY the 'Uploads' folder for standard manual file uploads
                f_path = f"{display_path}/Uploads"
                cursor.execute(
                    'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                    ('Uploads', company_id, mid, None, root_id, f_path)
                )
                
                logger.info(f"Created Root and Uploads folder for company={company_id}, module={mid}")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to create Root folder record for company={company_id}, module={mid}: {e}")
    
    return {
        "success": failed == 0,
        "created": created,
        "failed": failed,
        "errors": errors
    }

def get_physical_storage_path(base_dir, company_id, module_id, folder_id=None):
    """
    Legacy: Build physical storage path using human-readable company/module names.
    Now delegates to get_company_storage_path for name-based paths.
    Falls back to ID-based paths if DB lookup fails.
    """
    import os
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    result = get_company_storage_path(company_id, module_id)
    path = result.get("path") if result.get("success") else base_dir
    
    # Fallback: if name-based path failed, use old ID-based naming
    if not result.get("success"):
        path = base_dir
        if company_id is not None:
            path = os.path.join(path, f"company_{company_id}")
        if module_id is not None:
            path = os.path.join(path, f"module_{module_id}")
    
    if folder_id is not None:
        path = os.path.join(path, f"folder_{folder_id}")
    
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        logger.warning(f"get_physical_storage_path: could not create {path}: {e}")
    
    return path


# =================== AUTH / USER FUNCTIONS ===================

def get_super_admin_by_email(email):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM super_admin WHERE LOWER(email) = LOWER(?)', (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email, company_id=None):
    conn = get_db_connection()
    if company_id:
        row = conn.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND company_id = ?', (email, company_id)).fetchone()
    else:
        row = conn.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?)', (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_company_by_id(company_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_company_by_code(code):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM companies WHERE LOWER(code) = LOWER(?)', (code,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_company_modules(company_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT m.* FROM modules m
        JOIN company_modules cm ON m.id = cm.module_id
        WHERE cm.company_id = ? AND cm.status = 'active'
        ORDER BY m.name
    ''', (company_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_assigned_module_ids(user_id):
    conn = get_db_connection()
    rows = conn.execute('SELECT module_id FROM user_modules WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    return [row['module_id'] for row in rows]


def get_role_by_id(role_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM roles WHERE id = ?', (role_id,)).fetchone()
    conn.close()
    if not row:
        return None
    role = dict(row)
    # Parse JSON permissions
    for field in ('page_permissions', 'action_permissions'):
        if role.get(field):
            try:
                role[field] = json.loads(role[field])
            except (json.JSONDecodeError, TypeError):
                role[field] = []
        else:
            role[field] = []
    return role


def update_last_login(user_id, is_super_admin=False):
    conn = get_db_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if is_super_admin:
        conn.execute('UPDATE super_admin SET last_login = ? WHERE id = ?', (now, user_id))
    else:
        conn.execute('UPDATE users SET last_login = ? WHERE id = ?', (now, user_id))
    conn.commit()
    conn.close()


def update_user(user_id, **kwargs):
    if not kwargs:
        return
    allowed = {'name', 'email', 'password_hash', 'role', 'role_id', 'status', 'first_login'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    conn = get_db_connection()
    set_clause = ', '.join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [user_id]
    conn.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()


def update_super_admin(admin_id, **kwargs):
    if not kwargs:
        return
    allowed = {'name', 'email', 'password_hash', 'status'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    conn = get_db_connection()
    set_clause = ', '.join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [admin_id]
    conn.execute(f'UPDATE super_admin SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()


def save_audit_log(user_id=None, user_role=None, action=None, entity_type=None, entity_id=None, details=None, company_id=None, ip_address=None):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO audit_logs (user_id, user_role, action, entity_type, entity_id, details, company_id, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, user_role, action, entity_type, entity_id, details, company_id, ip_address))
    conn.commit()
    conn.close()


# =================== COMPANY FUNCTIONS ===================

def get_companies(status=None):
    conn = get_db_connection()
    if status:
        rows = conn.execute('SELECT * FROM companies WHERE status = ? ORDER BY created_at DESC', (status,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM companies ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_company(name, code, email=None, phone=None, address=None):
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO companies (name, code, email, phone, address) VALUES (?, ?, ?, ?, ?)',
        (name, code, email, phone, address)
    )
    company_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return company_id


def update_company(company_id, **kwargs):
    if not kwargs:
        return
    allowed = {'name', 'code', 'email', 'phone', 'address', 'status'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    conn = get_db_connection()
    set_clause = ', '.join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [company_id]
    conn.execute(f'UPDATE companies SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()


def delete_company(company_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM companies WHERE id = ?', (company_id,))
    conn.commit()
    conn.close()


# =================== MODULE FUNCTIONS ===================

def get_modules():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM modules ORDER BY name').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_module_by_id(module_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM modules WHERE id = ?', (module_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_module_by_code(code):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM modules WHERE code = ?', (code,)).fetchone()
    conn.close()
    return dict(row) if row else None


def assign_module_to_company(company_id, module_id):
    conn = get_db_connection()
    conn.execute('''
        INSERT OR IGNORE INTO company_modules (company_id, module_id) VALUES (?, ?)
    ''', (company_id, module_id))
    conn.commit()
    conn.close()
    
    # Initialize physical storage directories and the database Root folder 
    # for this newly assigned module
    create_company_file_structure(company_id, module_ids=[module_id])


def remove_module_from_company(company_id, module_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM company_modules WHERE company_id = ? AND module_id = ?', (company_id, module_id))
    conn.commit()
    conn.close()


# =================== USER MANAGEMENT FUNCTIONS ===================

def get_company_users(company_id, status=None):
    conn = get_db_connection()
    if status:
        rows = conn.execute('SELECT * FROM users WHERE company_id = ? AND status = ? ORDER BY created_at DESC', (company_id, status)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM users WHERE company_id = ? ORDER BY created_at DESC', (company_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_user(email, password_hash, name=None, role='viewer', company_id=None, role_id=None):
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO users (email, password_hash, name, role, company_id, role_id) VALUES (?, ?, ?, ?, ?, ?)',
        (email, password_hash, name, role, company_id, role_id)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def delete_user(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def get_roles():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM roles ORDER BY name').fetchall()
    conn.close()
    roles = []
    for row in rows:
        role = dict(row)
        # Parse JSON permissions
        for field in ('page_permissions', 'action_permissions'):
            if role.get(field):
                try:
                    role[field] = json.loads(role[field])
                except (json.JSONDecodeError, TypeError):
                    role[field] = []
            else:
                role[field] = []
        roles.append(role)
    return roles


# =================== USER MODULE ASSIGNMENT ===================

def assign_modules_to_user(user_id, module_ids):
    conn = get_db_connection()
    conn.execute('DELETE FROM user_modules WHERE user_id = ?', (user_id,))
    for module_id in module_ids:
        conn.execute('INSERT OR IGNORE INTO user_modules (user_id, module_id) VALUES (?, ?)', (user_id, module_id))
    conn.commit()
    conn.close()


def get_user_modules(user_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT m.* FROM modules m
        JOIN user_modules um ON m.id = um.module_id
        WHERE um.user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =================== WEBSITE SETTINGS ===================

def get_all_settings():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM website_settings ORDER BY setting_group, setting_key').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_setting(key, value, group='general'):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO website_settings (setting_key, setting_value, setting_group)
        VALUES (?, ?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            setting_group = excluded.setting_group,
            updated_at = CURRENT_TIMESTAMP
    ''', (key, value, group))
    conn.commit()
    conn.close()


# =================== AUDIT LOGS ===================

def get_audit_logs(limit=100, offset=0, company_id=None):
    conn = get_db_connection()
    if company_id:
        rows = conn.execute('''
            SELECT * FROM audit_logs WHERE company_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?
        ''', (company_id, limit, offset)).fetchall()
    else:
        rows = conn.execute('''
            SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =================== RECYCLE BIN ===================

def get_recycle_bin_items(company_id=None, module_id=None):
    conn = get_db_connection()
    if company_id and module_id:
        rows = conn.execute('SELECT * FROM recycle_bin WHERE company_id = ? AND module_id = ? ORDER BY deleted_at DESC', (company_id, module_id)).fetchall()
    elif company_id:
        rows = conn.execute('SELECT * FROM recycle_bin WHERE company_id = ? ORDER BY deleted_at DESC', (company_id,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM recycle_bin ORDER BY deleted_at DESC').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recycle_bin_item(recycle_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM recycle_bin WHERE id = ?', (recycle_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def restore_from_recycle_bin(recycle_id):
    """Restore an item from recycle bin back to its original state.
    Returns the restored entity info or None if not found."""
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM recycle_bin WHERE id = ?', (recycle_id,)).fetchone()
    if not item:
        conn.close()
        return None
    
    item = dict(item)
    entity_type = item.get('entity_type')
    entity_id = item.get('entity_id')
    entity_name = item.get('entity_name')
    original_path = item.get('original_path')
    metadata = item.get('metadata')
    company_id = item.get('company_id')
    module_id = item.get('module_id')
    
    if metadata:
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    
    restored = None
    
    if entity_type == 'folder':
        # Re-create folder record
        cursor = conn.execute(
            'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
            (entity_name, company_id, module_id, metadata.get('description'), metadata.get('parent_id'), original_path)
        )
        restored = {'id': cursor.lastrowid, 'name': entity_name, 'type': 'folder'}
        
        # Re-create physical directory if path exists
        if original_path:
            folder_dir = os.path.dirname(original_path)
            os.makedirs(folder_dir, exist_ok=True)
            
    elif entity_type == 'file':
        # Re-create file record (without the physical file - it was moved, not deleted)
        cursor = conn.execute(
            'INSERT INTO files (folder_id, name, original_name, file_path, format, size, sheet_names, company_id, module_id, header_row) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (metadata.get('folder_id', 1), metadata.get('name', entity_name), entity_name, original_path, metadata.get('format'), 
             metadata.get('size'), metadata.get('sheet_names'), company_id, module_id, metadata.get('header_row', 1))
        )
        restored = {'id': cursor.lastrowid, 'name': entity_name, 'type': 'file'}
        
    elif entity_type == 'master_file':
        # Re-create master file record
        cursor = conn.execute(
            'INSERT INTO master_files (folder_id, db_path, sheet_name, columns, header_row, concat_columns, rejected_files, formulas, company_id, module_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (entity_id, original_path, metadata.get('sheet_name'), metadata.get('columns'), 
             metadata.get('header_row'), metadata.get('concat_columns'), metadata.get('rejected_files'),
             metadata.get('formulas'), company_id, module_id)
        )
        restored = {'id': cursor.lastrowid, 'name': entity_name, 'type': 'master_file'}
    
    # Remove from recycle bin
    conn.execute('DELETE FROM recycle_bin WHERE id = ?', (recycle_id,))
    conn.commit()
    conn.close()
    return restored


def permanent_delete_from_recycle_bin(recycle_id):
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM recycle_bin WHERE id = ?', (recycle_id,)).fetchone()
    if item:
        item = dict(item)
        # Physically delete the file/folder if it still exists on disk
        entity_type = item.get('entity_type')
        original_path = item.get('original_path')
        
        if original_path:
            if entity_type == 'file' and os.path.isfile(original_path):
                try:
                    os.remove(original_path)
                except OSError:
                    pass
            elif entity_type == 'folder' and os.path.isdir(original_path):
                try:
                    # Only delete if empty
                    if not os.listdir(original_path):
                        os.rmdir(original_path)
                except OSError:
                    pass
            elif entity_type == 'master_file' and os.path.isfile(original_path):
                try:
                    os.remove(original_path)
                except OSError:
                    pass
        
        conn.execute('DELETE FROM recycle_bin WHERE id = ?', (recycle_id,))
    conn.commit()
    conn.close()


# =================== RULE IMPORT/EXPORT ===================

def export_rules_json(company_id=None, module_id=None):
    conn = get_db_connection()
    if company_id and module_id:
        rows = conn.execute('SELECT * FROM rules WHERE company_id = ? AND module_id = ? ORDER BY phase', (company_id, module_id)).fetchall()
    elif company_id:
        rows = conn.execute('SELECT * FROM rules WHERE company_id = ? ORDER BY phase', (company_id,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM rules ORDER BY phase').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def import_rules_from_json(rules_list, company_id=None, module_id=None):
    conn = get_db_connection()
    imported = 0
    for rule in rules_list:
        conn.execute('''
            INSERT INTO rules (phase, config, name, company_id, module_id, processing_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (rule.get('phase'), json.dumps(rule.get('config')), rule.get('name'), company_id, module_id, rule.get('processing_type', 'both')))
        imported += 1
    conn.commit()
    conn.close()
    return imported


def migrate_rules(from_company_id, to_company_id, from_module_id=None, to_module_id=None):
    conn = get_db_connection()
    if from_module_id:
        rows = conn.execute('SELECT * FROM rules WHERE company_id = ? AND module_id = ?', (from_company_id, from_module_id)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM rules WHERE company_id = ?', (from_company_id,)).fetchall()
    migrated = 0
    for row in rows:
        target_mod = to_module_id if to_module_id else row.get('module_id')
        conn.execute('''
            INSERT INTO rules (phase, config, name, company_id, module_id, processing_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (row['phase'], row['config'], row['name'], to_company_id, target_mod, row.get('processing_type', 'both')))
        migrated += 1
    conn.commit()
    conn.close()
    return migrated


# =================== PROCESSED FILES ===================

def save_processed_file(filename, file_path, report_type=None, financial_year=None, month_name=None, month_number=None, year=None, source_primary_filename=None, total_rows=None, rules_used=None, sheets_data=None, file_size=None, processing_time=None, company_id=None, module_id=None):
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO processed_files (filename, file_path, report_type, financial_year, month_name, month_number, year, source_primary_filename, total_rows, rules_used, sheets_data, file_size, processing_time, company_id, module_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (filename, file_path, report_type, financial_year, month_name, month_number, year, source_primary_filename, total_rows, rules_used, sheets_data, file_size, processing_time, company_id, module_id))
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id


def get_processed_files(company_id=None, module_id=None, financial_year=None, report_type=None, month_name=None):
    conn = get_db_connection()
    query = 'SELECT * FROM processed_files WHERE 1=1'
    params = []
    
    if company_id is not None:
        query += ' AND company_id = ?'
        params.append(company_id)
    if module_id is not None:
        query += ' AND module_id = ?'
        params.append(module_id)
    if financial_year is not None:
        if financial_year == 'Unknown':
            query += ' AND (financial_year IS NULL OR financial_year = ?)'
            params.append('Unknown')
        else:
            query += ' AND financial_year = ?'
            params.append(financial_year)
            
    if report_type is not None:
        if report_type == 'Unknown':
            query += ' AND (report_type IS NULL OR report_type = ?)'
            params.append('Unknown')
        else:
            query += ' AND report_type = ?'
            params.append(report_type)
            
    if month_name is not None:
        if month_name == 'Unknown':
            query += ' AND (month_name IS NULL OR month_name = ?)'
            params.append('Unknown')
        else:
            query += ' AND month_name = ?'
            params.append(month_name)
    
    query += ' ORDER BY created_at DESC'
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_processed_file_by_id(file_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM processed_files WHERE id = ?', (file_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_processed_file(file_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM processed_files WHERE id = ?', (file_id,)).fetchone()
    conn.execute('DELETE FROM processed_files WHERE id = ?', (file_id,))
    conn.commit()
    conn.close()
    return dict(row) if row else None


def get_processed_tree(company_id=None, module_id=None):
    """Return processed files grouped by financial_year and month_name for tree view."""
    conn = get_db_connection()
    query = 'SELECT * FROM processed_files'
    params = []
    if company_id is not None and module_id is not None:
        query += ' WHERE company_id = ? AND module_id = ?'
        params = [company_id, module_id]
    elif company_id is not None:
        query += ' WHERE company_id = ?'
        params = [company_id]
    query += ' ORDER BY year DESC, month_number DESC, created_at DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()

    fy_nodes = []
    fy_map = {}
    
    for row in rows:
        r = dict(row)
        fy = r.get('financial_year') or str(r.get('year') or 'Unknown')
        mn = r.get('month_name') or 'Unknown'
        
        # 1. Get or create financial_year node
        if fy not in fy_map:
            fy_node = {
                "financial_year": fy,
                "months": []
            }
            fy_nodes.append(fy_node)
            fy_map[fy] = (fy_node, {})
            
        fy_node, mn_map = fy_map[fy]
        
        # 2. Get or create month node
        if mn not in mn_map:
            mn_node = {
                "month_name": mn,
                "file_count": 0
            }
            fy_node["months"].append(mn_node)
            mn_map[mn] = mn_node
            
        mn_node = mn_map[mn]
        mn_node["file_count"] += 1
        
    return fy_nodes


def get_processed_stats(company_id=None, module_id=None):
    """Return processed file statistics."""
    conn = get_db_connection()
    
    where_clause = ""
    params = []
    if company_id is not None and module_id is not None:
        where_clause = " WHERE company_id = ? AND module_id = ?"
        params = [company_id, module_id]
    elif company_id is not None:
        where_clause = " WHERE company_id = ?"
        params = [company_id]
        
    # Total files
    total_files = conn.execute(f"SELECT COUNT(*) FROM processed_files{where_clause}", params).fetchone()[0]
    
    # Financial years count
    financial_years = conn.execute(f"SELECT COUNT(DISTINCT financial_year) FROM processed_files{where_clause}", params).fetchone()[0]
    
    # Report types count
    report_types = conn.execute(f"SELECT COUNT(DISTINCT report_type) FROM processed_files{where_clause}", params).fetchone()[0]
    
    # Months count
    months = conn.execute(f"SELECT COUNT(DISTINCT(financial_year || '-' || month_name)) FROM processed_files{where_clause}", params).fetchone()[0]
    
    conn.close()
    
    return {
        "total_files": total_files,
        "financial_years": financial_years,
        "report_types": report_types,
        "months": months
    }


# --- AUTO-SYNC HELPER FUNCTIONS ---

def set_file_sync_status(file_id, status, error=None):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE files SET sync_status = ?, sync_error = ? WHERE id = ?', (status, error, file_id))
        conn.commit()
    finally:
        conn.close()

def get_files_with_sync_status(folder_id):
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT id, original_name, sync_status, sync_error FROM files WHERE folder_id = ?', (folder_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
