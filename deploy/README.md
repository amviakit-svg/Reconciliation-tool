# Reconciliation Tool - Deployment System

## Quick Start (One-Click Build)

### Windows
1. Double-click **`deploy.bat`** in the project root
2. Wait for PyInstaller to build the `.exe` (first run takes ~5-15 minutes)
3. Find the deployable ZIP in **`dist/ReconciliationTool-v2.0.0.zip`**

### Command Line
```bash
# From project root
python deploy/build_standalone.py
```

## What Gets Built

| File | Description |
|------|-------------|
| `ReconciliationTool.exe` | Standalone executable (no Python needed on target) |
| `backend/` | Python backend source files |
| `frontend/` | Static frontend files (index.html) |
| `data/` | Data directories (uploads, master_files, processed, logs) |
| `Start_Reconciliation_Tool.bat` | One-click launcher for end users |
| `DEPLOYMENT_README.txt` | Instructions for the deployed package |

## Deployment for End Users

1. Extract `ReconciliationTool-vX.X.X.zip` on the target machine
2. Double-click **`Start_Reconciliation_Tool.bat`**
3. Browser opens automatically at `http://127.0.0.1:8000`
4. No Python installation required!

## Configuration

Edit `deploy/config.json` to customize:

```json
{
    "version": "2.0.0",
    "app_name": "ReconciliationTool",
    "exclude_files": ["dev_script.py", "test.py"],
    "include_dirs": ["backend", "frontend", "data"],
    "include_files": ["README.md"]
}
```

### Auto-Exclude Rules (No config needed)
These patterns are **automatically excluded**:
- `temp_*.py`, `tmp_*.py`, `test_*.py`, `*_test.py`
- `analyze_*.py`, `inspect_*.py`, `fix_*.py`, `cleanup_*.py`
- `*.pyc`, `__pycache__`, `.git`, `*.log`
- `dist/`, `build/`, `venv/`, `node_modules/`

## How It Works

1. **`deploy/launcher.py`** - Entry point that detects frozen runtime and sets paths
2. **`deploy/build_standalone.py`** - Orchestrates PyInstaller + packaging
3. **`backend/main.py`** - Modified to use `sys.executable` when frozen (PyInstaller)

### Path Handling for Frozen Runtime
When bundled as `.exe`, `__file__` points to a temporary directory. The app now detects this:

```python
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)  # .exe location
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # dev mode
```

This ensures data directories are always relative to the `.exe`, not the temp folder.

## Rebuilding After Code Changes

Just run `deploy.bat` again - it automatically picks up all new files in `backend/` and `frontend/`.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| PyInstaller not found | Build script auto-installs it, or run `pip install pyinstaller` |
| Build fails with import errors | Check `--hidden-import` args in `deploy/build_standalone.py` |
| .exe crashes on target | Ensure `backend/main.py` has `frozen` path detection |
| Port 8000 in use | Change port in `deploy/launcher.py` |
| Large file size | Normal for Python bundles (~30-50MB) due to dependencies |