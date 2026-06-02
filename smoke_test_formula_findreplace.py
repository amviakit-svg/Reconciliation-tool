"""
Smoke test for the three fixes:
  Fix 1: POST /api/master/{folder_id}/find-replace is registered and works.
  Fix 2: POST /api/master/{folder_id}/formula accepts VLOOKUP and HLOOKUP.
  Fix 3: frontend/index.html has NO duplicate "New Column Name" input
         (no element with id="formula-name").

This script uses FastAPI's TestClient to exercise the app in-process and
creates an isolated temp directory for the master DuckDB file so we do
not pollute the project databases.
"""

import importlib
import os
import sys
import tempfile
import types
import shutil
import json
import traceback
from pathlib import Path

ROOT = Path(r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool")
os.chdir(ROOT)

# Make the repo importable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# --- Create a test layout: temp folder containing an empty 'master.db' so the
#     master route handlers that look up 'db_path' resolve to a writable file. ---

TMP = Path(tempfile.mkdtemp(prefix="recon_smoke_"))
print(f"[setup] temp dir = {TMP}")

# Minimal stub for a master_files row. We import the module and patch get_master_file.
import importlib.util
spec = importlib.util.spec_from_file_location("main", str(ROOT / "backend" / "main.py"))
main_mod = importlib.util.module_from_spec(spec)

# Try the import; if it fails, report and exit (some envs may not have fastapi installed).
try:
    spec.loader.exec_module(main_mod)
    print("[setup] backend.main imported")
except Exception as e:
    print("[setup] failed to import backend.main:")
    traceback.print_exc()
    # Still try to do the static checks below.
    main_mod = None

# --- Static checks for Fix 3 (duplicate input removed) ---
index_path = ROOT / "frontend" / "index.html"
html = index_path.read_text(encoding="utf-8", errors="ignore")
# Fix 3 means: no element with id="formula-name" (the duplicate input).
# The legit label "New Column Name" on the real `formula-column-name` input is fine.
fix3_ok = ('id="formula-name"' not in html)
print(f"[fix 3] duplicate 'New Column Name' input (id=formula-name) removed: {fix3_ok}")

# --- Static checks for route registration (Fix 1 & 2) ---
fix1_registered = False
fix2_vlookup_in_apply = False
fix2_hlookup_in_apply = False
fix2_vlookup_in_preview = False
fix2_hlookup_in_preview = False

if main_mod is not None:
    app = getattr(main_mod, "app", None)
    if app is not None:
        routes = [(r.path, sorted(r.methods or [])) for r in app.routes if hasattr(r, 'methods')]
        # Fix 1
        fix1_registered = any(
            p == "/api/master/{folder_id}/find-replace" and "POST" in m
            for (p, m) in routes
        )
        print(f"[fix 1] POST /api/master/{{folder_id}}/find-replace registered: {fix1_registered}")

        # Fix 2: check source for VLOOKUP/HLOOKUP strings in formula & formula-preview
        src = (ROOT / "backend" / "main.py").read_text(encoding="utf-8", errors="ignore")

        # Look between the '/formula' endpoint decorator and the next '@app' to scope to the apply handler
        def slice_handler(start_marker, end_marker):
            i = src.find(start_marker)
            j = src.find(end_marker, i + 1) if i >= 0 else -1
            return src[i:j] if (i >= 0 and j >= 0) else ""

        apply_block = slice_handler('@app.post("/api/master/{folder_id}/formula")', '@app.post(')
        preview_block = slice_handler('@app.post("/api/master/{folder_id}/formula-preview")', '@app.post(')

        fix2_vlookup_in_apply = ("'VLOOKUP'" in apply_block) and ("VLOOKUP" in apply_block)
        fix2_hlookup_in_apply = ("'HLOOKUP'" in apply_block) and ("HLOOKUP" in apply_block)
        fix2_vlookup_in_preview = ("'VLOOKUP'" in preview_block)
        fix2_hlookup_in_preview = ("'HLOOKUP'" in preview_block)
        print(f"[fix 2 apply] VLOOKUP handled: {fix2_vlookup_in_apply}")
        print(f"[fix 2 apply] HLOOKUP handled: {fix2_hlookup_in_apply}")
        print(f"[fix 2 preview] VLOOKUP handled: {fix2_vlookup_in_preview}")
        print(f"[fix 2 preview] HLOOKUP handled: {fix2_hlookup_in_preview}")
    else:
        print("[setup] backend.main has no `app` attribute")
else:
    print("[setup] skipped route-level checks (main_mod is None)")

# --- Dynamic test using TestClient (only if everything imported) ---
dynamic_ok = None
if main_mod is not None:
    try:
        from fastapi.testclient import TestClient
        client = TestClient(main_mod.app)

        # Create a master_files row pointing to a temp DuckDB
        db_path = TMP / "test_master.db"
        # Initialize a duckdb file with master_data table
        try:
            import duckdb
            conn = duckdb.connect(str(db_path))
            conn.execute(
                "CREATE TABLE master_data ("
                "  id INTEGER, "
                "  order_id VARCHAR, "
                "  amount DOUBLE, "
                "  region VARCHAR, "
                "  Source_File_Name VARCHAR"
                ")"
            )
            conn.execute("INSERT INTO master_data VALUES (1,'A-1', 10.0, 'NA', 'f1')")
            conn.execute("INSERT INTO master_data VALUES (2,'A-2', 20.0, 'EU', 'f1')")
            conn.execute("INSERT INTO master_data VALUES (3,'A-3', 30.0, 'APAC', 'f1')")
            # Secondary-equivalent table (we will copy rows into temp_secondary
            # in the handler, but it expects a *file*; we'll use the same file
            # and a fake "file" with id 9999 whose db_path equals the master
            # but a different sheet would normally be selected via xlsx. For a
            # pure logic smoke test we patch get_master_file to return a dict
            # whose secondary_file_path resolves to the same db.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS secondary_lookup ("
                "  match_key VARCHAR, "
                "  vlookup_value VARCHAR, "
                "  hlookup_value DOUBLE"
                ")"
            )
            conn.execute("INSERT INTO secondary_lookup VALUES ('A-1', 'lookup-A1', 100.0)")
            conn.execute("INSERT INTO secondary_lookup VALUES ('A-2', 'lookup-A2', 200.0)")
            conn.execute("INSERT INTO secondary_lookup VALUES ('A-3', 'lookup-A3', 300.0)")
            conn.close()
        except Exception as e:
            print(f"[setup] duckdb not available, skipping dynamic test: {e}")
            conn = None
            db_path = None

        # Patch get_master_file to return our synthetic master
        def fake_get_master_file(folder_id):
            return {
                "id": int(folder_id),
                "folder_id": int(folder_id),
                "db_path": str(db_path),
                "name": "TestMaster",
            }

        # Replace the function in main_mod
        main_mod.get_master_file = fake_get_master_file

        # Also patch the secondary file loader. The formula handler uses
        # 'secondary_file' form param which is a file_id; we don't have
        # an actual file in the system. We monkey-patch a helper used by
        # the handler if it loads from disk. We try to discover it.
        # As a minimal approach, we monkey-patch pandas.read_excel/openpyxl
        # to return a DataFrame read from secondary_lookup.
        try:
            import pandas as pd
            sec_df = pd.DataFrame({
                "match_key": ["A-1", "A-2", "A-3"],
                "vlookup_value": ["lookup-A1", "lookup-A2", "lookup-A3"],
                "hlookup_value": [100.0, 200.0, 300.0],
            })

            # The handler typically loads the secondary file by file_id and
            # then reads a sheet via pandas. We don't know the exact loader
            # name, so try common candidates.
            patched = False
            for name in ("load_secondary_dataframe", "read_secondary_file",
                         "get_secondary_dataframe", "_read_file_to_df"):
                if hasattr(main_mod, name):
                    setattr(main_mod, name,
                            lambda *a, **kw: sec_df)
                    patched = True
                    print(f"[setup] patched secondary loader: {name}")

            # If we couldn't find a loader, the formula endpoint may rely on
            # the secondary file being an .xlsx on disk. We still proceed
            # to test the validation paths (which do not need the secondary
            # file) and the find-replace endpoint (which doesn't need a
            # secondary file at all).
        except Exception as e:
            print(f"[setup] pandas not available: {e}")

        # ----- Test Fix 1: /find-replace -----
        if db_path is not None:
            r = client.post(
                "/api/master/42/find-replace",
                data={
                    "find_text": "APAC",
                    "replace_text": "ASIA_PACIFIC",
                    "match_type": "exact",
                    "case_sensitive": "false",
                    "dry_run": "false",
                    "column": "region",
                },
            )
            print(f"[fix 1 dynamic] status={r.status_code} body={r.text[:300]}")
            fix1_dynamic_ok = r.status_code == 200 and r.json().get("success") is True

            # Verify the replacement actually wrote to disk
            import duckdb as _dd
            cc = _dd.connect(str(db_path))
            row = cc.execute("SELECT region FROM master_data WHERE order_id='A-3'").fetchone()
            cc.close()
            print(f"[fix 1 dynamic] region after replace: {row}")
            fix1_dynamic_ok = fix1_dynamic_ok and (row and row[0] == "ASIA_PACIFIC")
        else:
            fix1_dynamic_ok = False

        # ----- Test Fix 2 validation: VLOOKUP/HLOOKUP without secondary -----
        # Sending without secondary_file should produce a 422 with the
        # "Secondary file is required for VLOOKUP" message (Fix 2 changes).
        if db_path is not None:
            for ftype in ("VLOOKUP", "HLOOKUP"):
                r = client.post(
                    f"/api/master/42/formula",
                    data={
                        "formula_type": ftype,
                        "column_name": f"_test_{ftype.lower()}",
                        "primary_column": "order_id",
                        # intentionally omit secondary_file
                    },
                )
                print(f"[fix 2 validation] {ftype} status={r.status_code} body={r.text[:200]}")
                # Expect 422 because secondary_file is required for VLOOKUP/HLOOKUP
                ok = r.status_code == 422 and ftype in r.text
                print(f"[fix 2 validation] {ftype} returns 422 mentioning {ftype}: {ok}")

            # Also verify preview endpoint now mentions VLOOKUP/HLOOKUP
            r = client.post(
                "/api/master/42/formula-preview",
                data={
                    "formula_type": "VLOOKUP",
                    "column_name": "_test_v",
                    "primary_column": "order_id",
                },
            )
            print(f"[fix 2 preview validation] VLOOKUP status={r.status_code} body={r.text[:200]}")
            preview_ok = r.status_code == 422 and "VLOOKUP" in r.text
            print(f"[fix 2 preview validation] VLOOKUP validation mentions type: {preview_ok}")

        dynamic_ok = fix1_dynamic_ok

    except Exception as e:
        print("[dynamic] test failed:")
        traceback.print_exc()
        dynamic_ok = False

# --- Summary ---
print()
print("=" * 60)
print("SMOKE TEST SUMMARY")
print("=" * 60)
print(f"Fix 3 (no duplicate 'New Column Name' input):       {fix3_ok}")
print(f"Fix 1 (POST /find-replace route registered):        {fix1_registered}")
if main_mod is not None:
    print(f"Fix 2 apply handler covers VLOOKUP:                  {fix2_vlookup_in_apply}")
    print(f"Fix 2 apply handler covers HLOOKUP:                  {fix2_hlookup_in_apply}")
    print(f"Fix 2 preview handler covers VLOOKUP:                {fix2_vlookup_in_preview}")
    print(f"Fix 2 preview handler covers HLOOKUP:                {fix2_hlookup_in_preview}")
    if dynamic_ok is not None:
        print(f"Fix 1 dynamic round-trip (APAC -> ASIA_PACIFIC):   {dynamic_ok}")

# Clean up
try:
    shutil.rmtree(TMP, ignore_errors=True)
except Exception:
    pass

# Exit code: 0 if all static checks pass
all_static_ok = fix3_ok and fix1_registered and fix2_vlookup_in_apply and fix2_hlookup_in_apply and fix2_vlookup_in_preview and fix2_hlookup_in_preview
sys.exit(0 if all_static_ok else 1)