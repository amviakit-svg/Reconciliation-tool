import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'metadata.db')

def cleanup_old_rules():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Count rules before cleanup
    before = conn.execute("SELECT COUNT(*) as count FROM rules").fetchone()['count']
    print(f"Rules before cleanup: {before}")
    
    # Delete all old rules, keep only the latest rule for each phase
    # For each phase, find the max id and delete all others
    for phase in [1, 2, 3]:
        rules = conn.execute("SELECT id FROM rules WHERE phase = ? ORDER BY id", (phase,)).fetchall()
        if len(rules) > 1:
            ids_to_delete = [r['id'] for r in rules[:-1]]  # Keep only the last one
            placeholders = ','.join('?' * len(ids_to_delete))
            conn.execute(f"DELETE FROM rules WHERE id IN ({placeholders})", ids_to_delete)
            print(f"Deleted {len(ids_to_delete)} old rules for phase {phase}")
    
    conn.commit()
    
    # Count rules after cleanup
    after = conn.execute("SELECT COUNT(*) as count FROM rules").fetchone()['count']
    print(f"Rules after cleanup: {after}")
    
    # Show remaining rules
    rules = conn.execute("SELECT id, phase, name FROM rules ORDER BY phase, id").fetchall()
    for rule in rules:
        print(f"  Phase {rule['phase']}: Rule ID {rule['id']} - {rule['name']}")
    
    conn.close()

if __name__ == '__main__':
    cleanup_old_rules()