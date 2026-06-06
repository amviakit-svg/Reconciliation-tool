import sqlite3

conn = sqlite3.connect('data/metadata.db')
conn.row_factory = sqlite3.Row

# Look for recent users
users = conn.execute('SELECT * FROM users ORDER BY id DESC LIMIT 5').fetchall()
for u in users:
    print(f"User ID: {u['id']}, Email: {u['email']}, Company: {u['company_id']}")
