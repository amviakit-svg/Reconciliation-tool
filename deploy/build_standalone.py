#!/usr/bin/env python3
"""
Reconciliation Tool - Standalone Deployment Builder
=====================================================
Builds a standalone .exe deployment package for the Reconciliation Tool.
Run this script to create a deployable ZIP that works on any Windows machine.

Usage:
    python deploy/build_standalone.py

Output:
    dist/ReconciliationTool-v{version}.zip  - Deployable package
"""

import os
import sys
import json
import shutil
import subprocess
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEPLOY_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = DEPLOY_DIR / "config.json"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

DEFAULT_CONFIG = {
    "version": "2.0.0",
    "app_name": "ReconciliationTool",
    "exclude_patterns": [
        "*.pyc",
        "__pycache__",
        ".git",
        ".gitignore",
        "*.log",
        "dist",
        "build",
        "deploy",
        "*.tmp",
        "*.temp",
        "temp_*.py",
        "tmp_*.py",
        "analyze_*.py",
        "inspect_*.py",
        "fix_*.py",
        "cleanup_*.py",
        "cod*_inspect.py",
        "restart_server.py",
        "server_test.log",
        "response.json",
        "*.spec",
        "venv",
        ".env",
        "node_modules",
        "test_*.py",
        "*_test.py"
    ],
    "exclude_files": [
        "analyze_csv.py",
        "cleanup_rules.py",
        "cod2_inspect.py",
        "fix_db.py",
        "inspect_db.py",
        "restart_server.py",
        "server_test.log",
        "response.json",
        "temp_test.py",
        "temp_test2.py",
        "tmp_find_funcs.py",
        "start_server.bat",
        "start_background.vbs",
        "install_service.bat"
    ],
    "include_dirs": [
        "backend",
        "frontend",
        "data"
    ],
    "include_files": [
        "README.md"
    ],
    "pyinstaller_args": [
        "--onefile",
        "--noconfirm",
        "--clean",
        "--name", "ReconciliationTool",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "duckdb",
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "matplotlib",
        "--hidden-import", "PIL",
        "--hidden-import", "pydantic",
        "--hidden-import", "fastapi",
        "--hidden-import", "starlette",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pkg_resources.py2_warn",
        "--collect-all", "duckdb",
        "--collect-all", "openpyxl",
        "--collect-all", "PIL"
    ]
}


def load_config():
    """Load deployment config or create default."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG


def should_exclude(file_path: Path, config: dict) -> bool:
    """Check if a file should be excluded based on patterns."""
    name = file_path.name
    rel = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

    # Exact file exclusions
    if name in config.get("exclude_files", []):
        return True

    # Pattern exclusions
    for pattern in config.get("exclude_patterns", []):
        import fnmatch
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
            return True

    return False


def collect_source_files(config: dict):
    """Collect all files to include in the deployment."""
    files = []
    dirs = []

    # Collect specific directories
    for dir_name in config.get("include_dirs", []):
        src_dir = PROJECT_ROOT / dir_name
        if not src_dir.exists():
            print(f"WARNING: Directory not found: {src_dir}")
            continue

        for item in src_dir.rglob("*"):
            if item.is_file() and not should_exclude(item, config):
                rel_path = item.relative_to(PROJECT_ROOT)
                files.append((item, rel_path))
            elif item.is_dir() and not should_exclude(item, config):
                rel_path = item.relative_to(PROJECT_ROOT)
                dirs.append(rel_path)

    # Collect top-level files
    for file_name in config.get("include_files", []):
        src_file = PROJECT_ROOT / file_name
        if src_file.exists() and not should_exclude(src_file, config):
            files.append((src_file, Path(file_name)))

    return files, dirs


def ensure_pyinstaller():
    """Check if PyInstaller is installed, try to install if not."""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("PyInstaller not found. Attempting to install...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                         check=True, capture_output=False)
            print("PyInstaller installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to install PyInstaller: {e}")
            return False


def build_executable(config: dict):
    """Run PyInstaller to build the .exe."""
    print("\n" + "=" * 60)
    print("STEP 1: Building executable with PyInstaller")
    print("=" * 60)

    launcher = DEPLOY_DIR / "launcher.py"
    if not launcher.exists():
        print(f"ERROR: Launcher script not found: {launcher}")
        sys.exit(1)

    # Build PyInstaller command (use python -m PyInstaller for reliability)
    cmd = [sys.executable, "-m", "PyInstaller"] + config.get("pyinstaller_args", []) + [str(launcher)]

    print(f"Command: {' '.join(cmd)}")

    # Clean previous build
    spec_file = PROJECT_ROOT / f"{config['app_name']}.spec"
    if spec_file.exists():
        spec_file.unlink()

    # Run PyInstaller
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=False)
    if result.returncode != 0:
        print("ERROR: PyInstaller build failed!")
        sys.exit(1)

    exe_path = PROJECT_ROOT / "dist" / f"{config['app_name']}.exe"
    if not exe_path.exists():
        print(f"ERROR: Expected exe not found: {exe_path}")
        sys.exit(1)

    print(f"\nSUCCESS: Executable built at {exe_path}")
    return exe_path


def create_deployment_package(config: dict, exe_path: Path):
    """Create the final ZIP package with .exe + data + frontend."""
    print("\n" + "=" * 60)
    print("STEP 2: Creating deployment package")
    print("=" * 60)

    # Ensure output directory
    DIST_DIR.mkdir(exist_ok=True)

    # Collect all source files
    files, dirs = collect_source_files(config)

    # Create staging directory
    version = config.get("version", "1.0.0")
    pkg_name = f"{config['app_name']}-v{version}"
    stage_dir = DIST_DIR / pkg_name
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)

    # Create directory structure
    for d in dirs:
        (stage_dir / d).mkdir(parents=True, exist_ok=True)

    # Copy files (skip data/ contents - only keep directory structure)
    data_files_count = 0
    other_files_count = 0
    print(f"Processing {len(files)} files to staging directory...")
    for src, rel in files:
        dst = stage_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Skip actual data files (uploads, processed, etc.) but keep structure
        if str(rel).startswith("data" + os.sep):
            data_files_count += 1
            continue
        
        shutil.copy2(str(src), str(dst))
        other_files_count += 1
    
    # Ensure empty data directories exist
    for subdir in ["uploads", "master_files", "processed", "logs"]:
        (stage_dir / "data" / subdir).mkdir(parents=True, exist_ok=True)
    
    print(f"  Skipped {data_files_count} data files (user content, recreated empty)")
    print(f"  Copied {other_files_count} application files")

    # Copy the executable
    exe_dst = stage_dir / f"{config['app_name']}.exe"
    shutil.copy2(str(exe_path), str(exe_dst))
    print(f"Copied executable: {exe_dst}")

    # Create launch script with proper server readiness polling
    launch_bat = stage_dir / "Start_Reconciliation_Tool.bat"
    with open(launch_bat, 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('setlocal EnableDelayedExpansion\n')
        f.write('echo ==========================================\n')
        f.write(f'echo   {config["app_name"]} v{version}\n')
        f.write('echo ==========================================\n')
        f.write('echo Starting server... Please wait...\n')
        f.write('echo (This may take 15-30 seconds on first run)\n')
        f.write('echo.\n')
        f.write('cd /d "%~dp0"\n')
        f.write(f'start "" "{config["app_name"]}.exe"\n')
        f.write('echo Waiting for server to start...\n')
        f.write('set /a retries=0\n')
        f.write(':check_loop\n')
        f.write('  timeout /t 1 /nobreak >nul\n')
        f.write('  curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/health >http_check.tmp 2>nul\n')
        f.write('  set /p status=<http_check.tmp\n')
        f.write('  del http_check.tmp 2>nul\n')
        f.write('  if "%%status%%"=="200" goto server_ready\n')
        f.write('  set /a retries+=1\n')
        f.write('  if %%retries%% lss 45 goto check_loop\n')
        f.write('  echo ERROR: Server failed to start within 45 seconds.\n')
        f.write('  echo Please check the application window for errors.\n')
        f.write('  pause\n')
        f.write('  exit /b 1\n')
        f.write(':server_ready\n')
        f.write('echo Server is ready! Opening browser...\n')
        f.write('start http://127.0.0.1:8000\n')
        f.write('echo.\n')
        f.write('echo You can close this window - the server will keep running.\n')
        f.write('echo To stop: close the application window or press Ctrl+C there.\n')
        f.write('echo.\n')
        f.write('pause\n')
    print(f"Created launcher: {launch_bat}")

    # Create README for deployment
    deploy_readme = stage_dir / "DEPLOYMENT_README.txt"
    with open(deploy_readme, 'w', encoding='utf-8') as f:
        f.write(f"{config['app_name']} v{version}\n")
        f.write("=" * 50 + "\n\n")
        f.write("To start the application:\n")
        f.write("  1. Double-click 'Start_Reconciliation_Tool.bat'\n")
        f.write("  2. Your browser will open automatically\n")
        f.write("  3. The application runs at http://127.0.0.1:8000\n\n")
        f.write("No installation required. All data is stored locally.\n")
        f.write(f"\nBuilt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"Created README: {deploy_readme}")

    # Create ZIP
    zip_name = f"{pkg_name}.zip"
    zip_path = DIST_DIR / zip_name
    if zip_path.exists():
        zip_path.unlink()

    print(f"\nCreating ZIP: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in stage_dir.rglob("*"):
            if item.is_file():
                arcname = str(item.relative_to(stage_dir))
                zf.write(str(item), arcname)

    # Calculate size
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print("DEPLOYMENT PACKAGE READY")
    print(f"{'=' * 60}")
    print(f"File: {zip_path}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Version: {version}")
    print(f"\nDistribute '{zip_name}' to target machines.")
    print(f"Users just extract and run 'Start_Reconciliation_Tool.bat'")

    # Clean up staging directory
    shutil.rmtree(stage_dir)
    print(f"\nCleaned staging directory.")


def verify_source_files():
    """Quick verification that key files exist."""
    required = [
        PROJECT_ROOT / "backend" / "main.py",
        PROJECT_ROOT / "backend" / "database.py",
        PROJECT_ROOT / "backend" / "primary_data.py",
        PROJECT_ROOT / "backend" / "filename_parser.py",
        PROJECT_ROOT / "frontend" / "index.html",
        PROJECT_ROOT / "backend" / "requirements.txt",
    ]
    missing = [str(f) for f in required if not f.exists()]
    if missing:
        print("ERROR: Required files missing:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Build standalone deployment")
    parser.add_argument("--version", "-v", help="Override version number")
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip PyInstaller, use existing .exe")
    args = parser.parse_args()

    print("=" * 60)
    print("Reconciliation Tool - Standalone Deployment Builder")
    print("=" * 60)
    print(f"Project root: {PROJECT_ROOT}")

    # Verify source files
    verify_source_files()

    # Load config
    config = load_config()
    if args.version:
        config["version"] = args.version

    print(f"Version: {config['version']}")
    print(f"App name: {config['app_name']}")

    # Ensure PyInstaller
    if not args.skip_build:
        if not ensure_pyinstaller():
            print("ERROR: Cannot proceed without PyInstaller.")
            sys.exit(1)

        # Build the .exe
        exe_path = build_executable(config)
    else:
        exe_path = PROJECT_ROOT / "dist" / f"{config['app_name']}.exe"
        if not exe_path.exists():
            print(f"ERROR: --skip-build specified but no exe found: {exe_path}")
            sys.exit(1)
        print(f"Using existing executable: {exe_path}")

    # Create deployment package
    create_deployment_package(config, exe_path)

    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())