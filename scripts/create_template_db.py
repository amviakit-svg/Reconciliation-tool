import os
import shutil
import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_template():
    source_db = os.path.join(os.path.dirname(__file__), '..', 'data', 'metadata.db')
    target_db = os.path.join(os.path.dirname(__file__), '..', 'template.db')
    
    if not os.path.exists(source_db):
        print(f"Error: Source database not found at {source_db}")
        return
        
    print(f"Copying {source_db} to {target_db}...")
    shutil.copy2(source_db, target_db)
    
    print("Connecting to template database to scrub data...")
    conn = sqlite3.connect(target_db)
    
    try:
        # 1. Identify the target template company
        target_company_name = "Amviak Consulting"
        target_row = conn.execute("SELECT id FROM companies WHERE name = ?", (target_company_name,)).fetchone()
        
        if not target_row:
            # Fallback if the name changed or doesn't exist
            print(f"Warning: Company '{target_company_name}' not found. Using Company ID 1 as template.")
            target_id = 1
        else:
            target_id = target_row[0]
            
        print(f"Locking template to company: '{target_company_name}' (ID {target_id}). Deleting other companies...")
        
        # 2. Delete all data belonging to other companies
        tables_with_company = [
            'company_modules', 'folders', 'files', 'master_files', 'master_activities', 
            'rules', 'processed_files', 'notifications', 'audit_logs', 'recycle_bin', 'users'
        ]
        
        for table in tables_with_company:
            # Some tables might not have company_id directly, but all in this list do.
            conn.execute(f"DELETE FROM {table} WHERE company_id != ?", (target_id,))
            
        conn.execute("DELETE FROM companies WHERE id != ?", (target_id,))
        
        # 3. Remap the target company ID to 1 for a pristine template setup
        if target_id != 1:
            print("Remapping Template Company ID to 1...")
            # We can safely update to 1 because we just deleted ID 1 if it wasn't the target
            conn.execute("UPDATE companies SET id = 1 WHERE id = ?", (target_id,))
            for table in tables_with_company:
                conn.execute(f"UPDATE {table} SET company_id = 1 WHERE company_id = ?", (target_id,))
            target_id = 1

        # 4. Clear private files and logs
        print("Clearing private files, processed data, and logs...")
        conn.execute("DELETE FROM files")
        conn.execute("DELETE FROM processed_files")
        conn.execute("DELETE FROM audit_logs")
        conn.execute("DELETE FROM recycle_bin")
        conn.execute("DELETE FROM notifications")
        
        # 5. Reset Super Admin credentials
        print("Resetting Super Admin credentials...")
        super_hash = get_password_hash("admin123")
        conn.execute(
            "UPDATE super_admin SET email = ?, password_hash = ?, name = ?",
            ("admin@example.com", super_hash, "Super Admin")
        )
        
        # 6. Keep only one user per company (which is now just Company 1)
        conn.execute("DELETE FROM users WHERE id NOT IN (SELECT MIN(id) FROM users GROUP BY company_id)")
        
        # 7. Reset Company User credentials
        print("Resetting Company User credentials...")
        user_hash = get_password_hash("user123")
        conn.execute(
            "UPDATE users SET email = ?, password_hash = ?, name = ?, first_login = 1",
            ("user@example.com", user_hash, "Demo User")
        )
        
        # 8. Anonymize company name for the template
        conn.execute("UPDATE companies SET name = 'Demo Company', email = 'company@example.com' WHERE id = 1")
        
        conn.commit()
        print("Successfully created template.db!")
        print("Super Admin Login: admin@example.com / admin123")
        print("Company User Login: user@example.com / user123")
        
    except Exception as e:
        print(f"Error while scrubbing database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_template()
