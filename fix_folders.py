import sqlite3
import os

DB_PATH = 'data/metadata.db'

def fix_folders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("=== FIXING FOLDER STRUCTURE ===")
    
    # Step 1: Check current state
    c.execute('SELECT COUNT(*) FROM folders')
    print(f"Total folders before fix: {c.fetchone()[0]}")
    
    # Step 2: Create Root folder for Company 1, Module 1 (TestCorp / Own Website)
    c.execute('SELECT id FROM folders WHERE company_id = 1 AND module_id = 1 AND name = ?', ('Root',))
    existing = c.fetchone()
    if existing:
        root_1_1 = existing[0]
        print(f"Root for Company 1 Module 1 already exists: id={root_1_1}")
    else:
        c.execute('INSERT INTO folders (name, parent_id, path, company_id, module_id) VALUES (?, ?, ?, ?, ?)',
                  ('Root', None, '/Root/TestCorp/Own Website', 1, 1))
        root_1_1 = c.lastrowid
        print(f"Created Root for Company 1 Module 1: id={root_1_1}")
    
    # Step 3: Create Root folder for Company 1, Module 2 (TestCorp / Amazon)
    c.execute('SELECT id FROM folders WHERE company_id = 1 AND module_id = 2 AND name = ?', ('Root',))
    existing = c.fetchone()
    if existing:
        root_1_2 = existing[0]
        print(f"Root for Company 1 Module 2 already exists: id={root_1_2}")
    else:
        c.execute('INSERT INTO folders (name, parent_id, path, company_id, module_id) VALUES (?, ?, ?, ?, ?)',
                  ('Root', None, '/Root/TestCorp/Amazon', 1, 2))
        root_1_2 = c.lastrowid
        print(f"Created Root for Company 1 Module 2: id={root_1_2}")
    
    conn.commit()
    
    # Step 4: Update existing folders for Company 1 Module 1 to have Root as parent
    c.execute('UPDATE folders SET parent_id = ? WHERE company_id = 1 AND module_id = 1 AND id != ?',
              (root_1_1, root_1_1))
    print(f"Updated {c.rowcount} folders for Module 1 to have Root as parent")
    
    # Step 5: Update existing folder for Company 1 Module 2 to have Root as parent
    c.execute('UPDATE folders SET parent_id = ? WHERE company_id = 1 AND module_id = 2 AND id != ?',
              (root_1_2, root_1_2))
    print(f"Updated {c.rowcount} folders for Module 2 to have Root as parent")
    
    conn.commit()
    
    # Step 6: Update all paths for Company 1 Module 1
    c.execute('SELECT id, name, parent_id FROM folders WHERE company_id = 1 AND module_id = 1')
    folders = c.fetchall()
    for fid, name, parent_id in folders:
        if parent_id is None:
            # This is the root folder
            new_path = '/Root/TestCorp/Own Website'
        else:
            c.execute('SELECT path FROM folders WHERE id = ?', (parent_id,))
            parent_path = c.fetchone()[0]
            new_path = f'{parent_path}/{name}'
        c.execute('UPDATE folders SET path = ? WHERE id = ?', (new_path, fid))
    print(f"Updated paths for {len(folders)} folders in Module 1")
    
    # Step 7: Update all paths for Company 1 Module 2
    c.execute('SELECT id, name, parent_id FROM folders WHERE company_id = 1 AND module_id = 2')
    folders = c.fetchall()
    for fid, name, parent_id in folders:
        if parent_id is None:
            new_path = '/Root/TestCorp/Amazon'
        else:
            c.execute('SELECT path FROM folders WHERE id = ?', (parent_id,))
            parent_path = c.fetchone()[0]
            new_path = f'{parent_path}/{name}'
        c.execute('UPDATE folders SET path = ? WHERE id = ?', (new_path, fid))
    print(f"Updated paths for {len(folders)} folders in Module 2")
    
    conn.commit()
    
    # Step 8: Verify
    c.execute('SELECT COUNT(*) FROM folders')
    print(f"\nTotal folders after fix: {c.fetchone()[0]}")
    
    print("\nCompany 1 folders after fix:")
    c.execute('SELECT id, name, parent_id, path, company_id, module_id FROM folders WHERE company_id = 1 ORDER BY id')
    for row in c.fetchall():
        print(f"  {row}")
    
    conn.close()
    print("\n=== FIX COMPLETE ===")

if __name__ == '__main__':
    fix_folders()