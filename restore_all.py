import subprocess
import os

scripts = [
    "patch_index.py",
    "patch_delete.py",
    "patch_main.py",
    "patch_columns.py",
    "patch_phase4.py",
    "patch_p1_fields.py",
    "patch_resolve.py",
    "patch_resolve2.py",
    "patch_zero_rows.py",
    "patch_phase1_ui.py",
    "patch_error_toast.py",
    "patch_diagnostic.py",
    "patch_diag_ui.py",
    "patch_sessionstorage.py",
    "patch_local_save.py",
    "patch_backend_fallback.py",
    "patch_dynamic_fields.py",
    "patch_json_parse.py",
    "patch_clean_fallback.py",
    "patch_validation_bypass.py",
    "patch_button_move.py",
    "patch_remove_diag.py",
    "patch_preview_load.py",
    "patch_backend_preview.py",
    "fix_column_sequence.py",
    "wrap_try_catch.py"
]

for script in scripts:
    print(f"Running {script}...")
    if not os.path.exists(script):
        print(f"Skipping {script} - not found")
        continue
        
    try:
        result = subprocess.run(["python", script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FAILED {script}: {result.stderr}")
        else:
            print(f"SUCCESS {script}: {result.stdout.strip()}")
    except Exception as e:
        print(f"ERROR {script}: {e}")

print("All restores completed.")
