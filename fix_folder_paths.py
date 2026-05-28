"""
One-time script to recompute and fix broken folder display paths.
The 'path' column should contain display paths like /Root/SubFolder, not physical paths.
Run this once, then it can be discarded.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'metadata.db')

def fix_folder_paths():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get all folders
    folders = conn.execute('SELECT * FROM folders').fetchall()
    folders_by_id = {f['id']: dict(f) for f in folders}
    
    fixed_count = 0
    already_correct = 0
    
    for folder_id, folder in folders_by_id.items():
        current_path = folder.get('path', '') or ''
        
        # Compute the correct display path by traversing parent hierarchy
        if folder.get('name') == 'Root' and folder.get('parent_id') is None:
            correct_path = '/Root'
        else:
            path_parts = [folder['name']]
            current = folder
            visited = set()
            
            while current.get('parent_id') and current['parent_id'] != current['id']:
                parent_id = current['parent_id']
                if parent_id in visited:
                    break
                visited.add(parent_id)
                parent = folders_by_id.get(parent_id)
                if not parent:
                    break
                path_parts.insert(0, parent['name'])
                current = parent
            
            correct_path = '/' + '/'.join(path_parts)
        
        # Check if the current path looks like a physical path (contains backslash or data/)
        is_physical = (
            '\\' in current_path or 
            current_path.startswith('C:') or 
            current_path.startswith('/data/') or
            'uploads' in current_path.lower() or
            current_path == '' or
            current_path == 'None'
        )
        
        # Also fix if the path doesn't match the computed display path
        needs_fix = is_physical or current_path != correct_path
        
        if needs_fix:
            conn.execute(
                'UPDATE folders SET path = ? WHERE id = ?',
                (correct_path, folder_id)
            )
            print(f"  FIXED: folder '{folder['name']}' (id={folder_id}): '{current_path[:80]}' -> '{correct_path}'")
            fixed_count += 1
        else:
            already_correct += 1
            print(f"  OK:    folder '{folder['name']}' (id={folder_id}): '{correct_path}'")
    
    conn.commit()
    conn.close()
    
    print(f"\n=== Summary ===")
    print(f"Total folders: {len(folders)}")
    print(f"Already correct: {already_correct}")
    print(f"Fixed: {fixed_count}")
    print(f"\nAll folder paths now use the clean display format (e.g., /Root/SubFolder)")

if __name__ == '__main__':
    fix_folder_paths()