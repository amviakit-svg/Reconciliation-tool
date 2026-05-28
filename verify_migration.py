#!/usr/bin/env python3
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'metadata.db')
print("DB path:", db_path)
print("Exists:", os.path.exists(db_path))
print("Size:", os.path.getsize(db_path), "bytes")

conn = sqlite3.connect(db_path)

cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("\nTables:", tables)

for t in tables:
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} rows")
    except Exception as e:
        print(f"  {t}: ERROR {e}")

if 'folders' in tables:
    print("\n--- Folder details ---")
    cur = conn.execute("SELECT id, name, company_id, module_id, path FROM folders")
    for r in cur.fetchall():
        print(f"  Folder {r[0]}: name='{r[1]}' company={r[2]} module={r[3]} path={r[4]}")

if 'files' in tables:
    print("\n--- Sample files ---")
    cur = conn.execute("SELECT id, name, folder_id, format, size FROM files LIMIT 5")
    for r in cur.fetchall():
        print(f"  File {r[0]}: name='{r[1]}' folder={r[2]} format={r[3]} size={r[4]}")

if 'processed_files' in tables:
    print("\n--- Processed files ---")
    cur = conn.execute("SELECT id, filename, report_type FROM processed_files")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} ({r[2]})")

if 'master_files' in tables:
    print("\n--- Master files ---")
    cur = conn.execute("SELECT id, db_path FROM master_files")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

conn.close()