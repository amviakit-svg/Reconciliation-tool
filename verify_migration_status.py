import sqlite3

conn = sqlite3.connect('data/metadata.db')
c = conn.cursor()

tables = ['companies','modules','folders','files','master_files','rules','processed_files','users']
print("=== METADATA.DB COUNTS ===")
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t}: {c.fetchone()[0]}")

print("\n=== COMPANIES ===")
for row in c.execute("SELECT id, name, code FROM companies").fetchall():
    print(row)

print("\n=== USERS ===")
for row in c.execute("SELECT id, email, name, role, company_id FROM users").fetchall():
    print(row)

print("\n=== FOLDERS ===")
for row in c.execute("SELECT id, name, path, company_id, module_id FROM folders").fetchall():
    print(row)

print("\n=== FILES (first 5) ===")
for row in c.execute("SELECT id, name, folder_id, company_id, module_id FROM files LIMIT 5").fetchall():
    print(row)

print("\n=== RULES ===")
for row in c.execute("SELECT id, name, phase, company_id, module_id FROM rules").fetchall():
    print(row)

print("\n=== MASTER FILES ===")
for row in c.execute("SELECT id, folder_id, sheet_name, company_id, module_id FROM master_files").fetchall():
    print(row)

conn.close()