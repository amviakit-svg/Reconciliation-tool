import sqlite3
import json

conn = sqlite3.connect('data/metadata.db')
conn.row_factory = sqlite3.Row

# Get a few rules and print their JSON
rules = conn.execute('SELECT * FROM rules LIMIT 5').fetchall()
for r in rules:
    print(f"--- Rule {r['id']} ({r['phase']}) ---")
    print(json.dumps(json.loads(r['config']), indent=2))
