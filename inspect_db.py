import sqlite3
import json
import os

db_path = 'data/metadata.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

output = []

# Get table schema
cursor.execute('PRAGMA table_info(rules)')
columns = cursor.fetchall()
output.append('Rules table columns:')
for col in columns:
    output.append(f'  {dict(col)}')

# Get raw rules data with config parsed
output.append('\n=== ALL RULES ===')
rules = cursor.execute('SELECT * FROM rules ORDER BY phase, id').fetchall()
for r in rules:
    config = r['config']
    name = r['name']
    phase = r['phase']
    rule_id = r['id']
    output.append(f'Rule ID={rule_id}, Phase={phase}, Name={name}')
    output.append(f'  Config type: {type(config).__name__}')
    output.append(f'  Config: {str(config)[:300]}')
    
    # Try to parse as JSON
    try:
        if isinstance(config, str):
            parsed = json.loads(config)
            output.append(f'  Parsed: {json.dumps(parsed, indent=2)[:300]}')
        else:
            output.append(f'  ERROR: Config is not a string, it is {type(config).__name__}')
    except Exception as e:
        output.append(f'  JSON parse error: {e}')

# Get all files
output.append('\n=== ALL FILES ===')
files = cursor.execute('SELECT id, original_name, format, sheet_names FROM files').fetchall()
for f in files:
    output.append(f'ID {f[0]}: {f[1]} (format: {f[2]}, sheets: {f[3]})')

conn.close()

# Write to file
with open('db_inspection.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('Inspection complete. Check db_inspection.txt')