"""
End-to-end smoke test for the apply_activities() engine.
Creates a real master_data DuckDB, writes 2 source-file rows, then runs
multiple activities and verifies the transformations persist.
"""
import sys
import os
import tempfile
import json

sys.path.insert(0, '.')

import duckdb
import pandas as pd
import backend.database as database
from backend.auto_sync import apply_activities

# Use temp metadata.db
test_db_dir = tempfile.mkdtemp(prefix="engine_smoke_")
test_db_path = os.path.join(test_db_dir, "metadata.db")
database.DB_PATH = test_db_path
database.init_db()

# Create a folder + master_files record so list_master_activities has context
conn = database.get_db_connection()
conn.execute("INSERT INTO folders (id, name, company_id, module_id, path) VALUES (?, ?, ?, ?, ?)",
             (1, "SmokeFolder", 1, 1, "/tmp/smoke"))
conn.execute(
    """INSERT INTO master_files
       (id, folder_id, db_path, sheet_name, columns, header_row, auto_sync, company_id, module_id)
       VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
    (1, 1, "", "First_Sheet", "[]", 1, 1, 1)
)
conn.commit()
conn.close()

# Create a real DuckDB master_data with sample rows
master_db_path = os.path.join(test_db_dir, "folder_1_master.duckdb")
conn = duckdb.connect(master_db_path)
conn.execute("""
    CREATE TABLE master_data (
        "Source_File_Name" VARCHAR,
        "Vendor" VARCHAR,
        "Amount" DOUBLE,
        "Tax" DOUBLE
    )
""")
conn.execute("""
    INSERT INTO master_data VALUES
    ('sales_jan.csv', 'Acme Pvt Ltd', 1000.00, 180.00),
    ('sales_jan.csv', 'BetaCorp', 2000.00, 360.00),
    ('sales_feb.csv', 'Acme Pvt Ltd', 500.00, 90.00),
    ('sales_feb.csv', 'Gamma Pvt Ltd', 750.00, 135.00)
""")
conn.close()

# Update master_files with the real path
conn = database.get_db_connection()
conn.execute("UPDATE master_files SET db_path = ? WHERE folder_id = 1", (master_db_path,))
conn.commit()
conn.close()

# ---------- Activity 1: FORMULA_ADD -> Net_Amount = Amount + Tax ----------
act1 = database.create_master_activity(
    folder_id=1,
    activity_type='FORMULA_ADD',
    payload={'expression': '=Amount + Tax', 'output_column': 'Net_Amount', 'data_type': 'DOUBLE'},
    target_column='Net_Amount',
    company_id=1, module_id=1, master_file_id=1,
)
print(f"Created FORMULA_ADD activity id={act1}")

# ---------- Activity 2: FIND_REPLACE -> "Pvt Ltd" -> "Private Limited" on Vendor column ----------
act2 = database.create_master_activity(
    folder_id=1,
    activity_type='FIND_REPLACE',
    payload={'find': 'Pvt Ltd', 'replace': 'Private Limited', 'scope_columns': ['Vendor'],
             'case_sensitive': False, 'regex': False, 'match_whole_cell': False},
    target_column='Vendor',
    company_id=1, module_id=1, master_file_id=1,
)
print(f"Created FIND_REPLACE activity id={act2}")

# ---------- Activity 3: COLUMN_RENAME -> Amount -> NetAmount ----------
act3 = database.create_master_activity(
    folder_id=1,
    activity_type='COLUMN_RENAME',
    payload={'from': 'Amount', 'to': 'NetAmount'},
    target_column='Amount',
    company_id=1, module_id=1, master_file_id=1,
)
print(f"Created COLUMN_RENAME activity id={act3}")

# ---------- Activity 4 (disabled) — should NOT run ----------
act4 = database.create_master_activity(
    folder_id=1,
    activity_type='COLUMN_DELETE',
    payload={'column': 'Tax'},
    target_column='Tax',
    company_id=1, module_id=1, master_file_id=1,
)
database.update_master_activity(act4, is_enabled=0)
print(f"Created COLUMN_DELETE activity id={act4} (disabled)")

# Now run apply_activities()
print()
print("Running apply_activities()...")
conn_duck = duckdb.connect(master_db_path)
apply_activities(conn_duck, folder_id=1, company_id=1, module_id=1)
conn_duck.close()

# Verify the results
print()
print("Verifying results...")
conn_duck = duckdb.connect(master_db_path, read_only=True)
cols = conn_duck.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
print(f"Columns now: {cols}")
assert "Net_Amount" in cols, "FORMULA_ADD failed — Net_Amount column missing"
assert "NetAmount" in cols, "COLUMN_RENAME failed — NetAmount column missing"
assert "Amount" not in cols, "COLUMN_RENAME failed — old 'Amount' still present"
assert "Tax" in cols, "COLUMN_DELETE should NOT have run (it was disabled)"

# Verify FIND_REPLACE ran
vendor_values = conn_duck.execute("SELECT DISTINCT Vendor FROM master_data").fetchdf()['Vendor'].tolist()
print(f"Distinct Vendors after F&R: {vendor_values}")
assert "Acme Private Limited" in vendor_values, "FIND_REPLACE failed on 'Acme Pvt Ltd'"
assert "Gamma Private Limited" in vendor_values, "FIND_REPLACE failed on 'Gamma Pvt Ltd'"
assert "BetaCorp" in vendor_values, "BetaCorp should be untouched"

# Verify FORMULA_ADD evaluated correctly (Net_Amount = Amount + Tax)
# Note: After rename, the formula was evaluated with original 'Amount' column, so values should be Amount+Tax
result = conn_duck.execute('SELECT Vendor, NetAmount, Tax, Net_Amount FROM master_data ORDER BY NetAmount').fetchdf()
print(result.to_string())

# NetAmount (was Amount) + Tax should equal Net_Amount
for _, row in result.iterrows():
    expected = (row['NetAmount'] or 0) + (row['Tax'] or 0)
    actual = row['Net_Amount']
    assert abs(expected - actual) < 0.01, f"Net_Amount mismatch for {row['Vendor']}: expected {expected}, got {actual}"
print("OK: Net_Amount values match NetAmount + Tax for all rows")

# Verify activity validation statuses
acts = database.list_master_activities(folder_id=1, company_id=1, module_id=1)
print()
print("Activity statuses after apply:")
for a in acts:
    print(f"  id={a['id']} type={a['activity_type']} status={a['validation_status']} error={a.get('last_error')}")

for a in acts:
    if a['id'] in (act1, act2, act3):
        assert a['validation_status'] == 'ok', f"Activity {a['id']} should be 'ok', got {a['validation_status']}"
    elif a['id'] == act4:
        # Disabled, so not applied; status remains default
        pass

conn_duck.close()

# Test: Re-run apply_activities() — should be idempotent for FORMULA_ADD and RENAME
print()
print("Re-running apply_activities() to test idempotency...")
conn_duck = duckdb.connect(master_db_path)
apply_activities(conn_activities := conn_duck, folder_id=1, company_id=1, module_id=1)
conn_duck.close()

conn_duck = duckdb.connect(master_db_path, read_only=True)
result2 = conn_duck.execute('SELECT Net_Amount FROM master_data').fetchdf()
print(f"Net_Amount after re-run: {result2['Net_Amount'].tolist()}")
conn_duck.close()

print()
print("=" * 60)
print("APPLY_ACTIVITIES END-TO-END SMOKE TEST PASSED")
print("=" * 60)

# Cleanup
import shutil
try:
    shutil.rmtree(test_db_dir)
except Exception:
    pass