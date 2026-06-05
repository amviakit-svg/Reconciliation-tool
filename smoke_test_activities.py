"""
Smoke test for the Activity Window feature.
Exercises the new endpoints end-to-end without starting a real server.
"""
import sys
import json
import os
import tempfile

sys.path.insert(0, '.')

# Use a temp metadata.db so we don't pollute the real one
import backend.database as database
test_db_dir = tempfile.mkdtemp(prefix="activity_smoke_")
test_db_path = os.path.join(test_db_dir, "metadata.db")
database.DB_PATH = test_db_path

# Re-init
database.init_db()

# Verify table exists
conn = database.get_db_connection()
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='master_activities'").fetchall()]
assert "master_activities" in tables, "master_activities table missing"
print("OK: master_activities table exists")

# Check columns
cols = [r['name'] for r in conn.execute("PRAGMA table_info(master_activities)").fetchall()]
expected_cols = {'id', 'master_file_id', 'folder_id', 'company_id', 'module_id',
                 'step_order', 'activity_type', 'target_column', 'payload_json',
                 'is_enabled', 'validation_status', 'last_error', 'created_by',
                 'created_at', 'last_applied_at'}
missing = expected_cols - set(cols)
assert not missing, f"Missing columns: {missing}"
print(f"OK: All {len(expected_cols)} expected columns present")

conn.close()

# Test 1: Create a FORMULA_ADD activity
act_id = database.create_master_activity(
    folder_id=1,
    activity_type='FORMULA_ADD',
    payload={'expression': '=Amount + Tax', 'output_column': 'Net_Amount', 'data_type': 'DOUBLE'},
    target_column='Net_Amount',
    company_id=1,
    module_id=1,
)
print(f"OK: Created FORMULA_ADD activity id={act_id}")

# Test 2: Create a FIND_REPLACE activity
fr_id = database.create_master_activity(
    folder_id=1,
    activity_type='FIND_REPLACE',
    payload={'find': 'Pvt Ltd', 'replace': 'Private Limited', 'scope_columns': ['Vendor'], 'case_sensitive': False},
    target_column='Vendor',
    company_id=1,
    module_id=1,
)
print(f"OK: Created FIND_REPLACE activity id={fr_id}")

# Test 3: List activities
acts = database.list_master_activities(folder_id=1, company_id=1, module_id=1)
assert len(acts) == 2, f"Expected 2 activities, got {len(acts)}"
print(f"OK: Listed {len(acts)} activities")

# Test 4: Get one
act = database.get_master_activity(act_id)
assert act is not None
assert act['activity_type'] == 'FORMULA_ADD'
assert act['payload']['output_column'] == 'Net_Amount'
print(f"OK: Retrieved activity {act_id} with correct payload")

# Test 5: Update (toggle off)
database.update_master_activity(act_id, is_enabled=0)
act = database.get_master_activity(act_id)
assert act['is_enabled'] == 0
print(f"OK: Toggled activity {act_id} off")

# Test 6: Reorder
database.reorder_master_activities(1, [fr_id, act_id])
acts = database.list_master_activities(folder_id=1, company_id=1, module_id=1)
# First should be FIND_REPLACE now
assert acts[0]['id'] == fr_id, f"Reorder failed: first should be {fr_id}, got {acts[0]['id']}"
print(f"OK: Reorder works — FIND_REPLACE is now first")

# Test 7: Mark applied
database.mark_activity_applied(act_id, 'ok', None)
act = database.get_master_activity(act_id)
assert act['last_applied_at'] is not None
assert act['validation_status'] == 'ok'
print(f"OK: Marked activity {act_id} as applied")

# Test 8: Delete
database.delete_master_activity(act_id)
remaining = database.list_master_activities(folder_id=1, company_id=1, module_id=1)
assert len(remaining) == 1
print(f"OK: Deleted activity {act_id}, {len(remaining)} remain")

# Test 9: Migration function (no legacy data, should return 0)
result = database.migrate_legacy_master_formulas()
assert result['migrated'] == 0
print(f"OK: Migration function callable, no legacy data: {result}")

print()
print("=" * 60)
print("ALL SMOKE TESTS PASSED")
print("=" * 60)

# Cleanup
import shutil
try:
    shutil.rmtree(test_db_dir)
except Exception:
    pass