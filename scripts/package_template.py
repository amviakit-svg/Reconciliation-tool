import os
import shutil
import sqlite3

def package_template():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_db_path = os.path.join(base_dir, 'template.db')
    template_data_dir = os.path.join(base_dir, 'data', 'template_master_dbs')
    
    if not os.path.exists(template_db_path):
        print("Error: template.db not found. Run create_template_db.py first.")
        return
        
    print(f"Reading master_files from {template_db_path}")
    conn = sqlite3.connect(template_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, db_path FROM master_files")
    rows = cursor.fetchall()
    
    if not os.path.exists(template_data_dir):
        os.makedirs(template_data_dir)
        
    copied_count = 0
    for row_id, db_path in rows:
        # db_path looks like C:\...\data\uploads\Amviak Consulting\Amazon\folder_26\folder_26_master.duckdb
        # We need to extract everything after 'uploads'
        try:
            # Handle both forward and back slashes
            path_parts = db_path.replace('\\', '/').split('/uploads/')
            if len(path_parts) > 1:
                rel_path = path_parts[1] # e.g. Amviak Consulting/Amazon/folder_26/folder_26_master.duckdb
                
                # Source path on the current machine
                src_path = os.path.join(base_dir, 'data', 'uploads', rel_path.replace('/', os.sep))
                
                # Destination path in the template_master_dbs folder
                dest_path = os.path.join(template_data_dir, rel_path.replace('/', os.sep))
                
                # Ensure destination directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dest_path)
                    print(f"Packaged: {rel_path}")
                    copied_count += 1
                else:
                    print(f"Warning: Source file not found: {src_path}")
            else:
                print(f"Warning: Could not parse relative path from {db_path}")
        except Exception as e:
            print(f"Error packaging file ID {row_id}: {e}")
            
    conn.close()
    
    # Create an empty .gitkeep so the folder is tracked
    gitkeep_path = os.path.join(template_data_dir, '.gitkeep')
    with open(gitkeep_path, 'w') as f:
        pass
        
    print(f"\nSuccessfully packaged {copied_count} template master files into data/template_master_dbs/")
    print("Be sure to commit the new template_master_dbs folder to Git!")

if __name__ == "__main__":
    package_template()
