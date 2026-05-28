import sqlite3
import csv
import os

DB_PATH = 'data/metadata.db'

print("Connecting to database:", DB_PATH)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get current row count for Dot & Key
cursor.execute("SELECT id, original_name, format, row_count FROM files WHERE id = 34")
row = cursor.fetchone()
print("Before update - ID 34:", row)

# Get all CSV files
cursor.execute("SELECT id, file_path, original_name, row_count FROM files WHERE format = 'CSV'")
files = cursor.fetchall()
print(f"\nFound {len(files)} CSV files to update")

updated = 0
for fid, fpath, orig, old_count in files:
    if not os.path.exists(fpath):
        print(f"  SKIP (not found): {orig}")
        continue
    try:
        total_rows = 0
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or all(field.strip() == '' for field in row):
                    continue
                total_rows += 1
        cursor.execute('UPDATE files SET row_count = ? WHERE id = ?', (total_rows, fid))
        updated += 1
        print(f"  UPDATED: {orig} | old={old_count} -> new={total_rows}")
    except Exception as e:
        print(f"  ERROR with {orig}: {e}")

conn.commit()

# Verify
cursor.execute("SELECT id, original_name, format, row_count FROM files WHERE id = 34")
row = cursor.fetchone()
print("\nAfter update - ID 34:", row)

cursor.execute("SELECT id, original_name, row_count FROM files WHERE format = 'CSV' ORDER BY id DESC")
all_csv = cursor.fetchall()
print(f"\nAll CSV files ({len(all_csv)}):")
for r in all_csv:
    print(f"  ID {r[0]}: {r[1]} = {r[2]} rows")

conn.close()
print(f"\nTotal updated: {updated}")