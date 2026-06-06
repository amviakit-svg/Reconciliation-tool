import sqlite3
import traceback

conn = sqlite3.connect('data/metadata.db')
conn.row_factory = sqlite3.Row

# Look for recent companies
companies = conn.execute('SELECT * FROM companies ORDER BY id DESC LIMIT 5').fetchall()
for c in companies:
    print(f"Company ID: {c['id']}, Name: {c['name']}, Created: {c['created_at']}")
