"""
Migration Script: Move existing files into the new company/module hierarchy.
Run this ONCE after upgrading to the new storage structure.

Usage:
    python backend/migrate_file_paths.py [--dry-run]

Options:
    --dry-run    Preview changes without actually moving files
    --force      Skip confirmation prompt

This script:
1. Reads all file records from files, master_files, processed_files tables
2. Determines the correct new path based on company/module names
3. Moves files from old flat paths to new hierarchical paths
4. Updates file_path columns in the database
5. Logs per-file results with error details

New hierarchy:
    data/uploads/{CompanyName}_{CompanyCode}/{ModuleName}/
        uploads/       ← uploaded files
        master_files/  ← master DuckDB files
        primary_data/  ← primary data files
        processed/     ← final output
"""

import os
import sys
import json
import shutil
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection, get_company_storage_path

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("migration_tool")


def migrate_files_table(conn, dry_run=False):
    """Migrate uploaded files to new hierarchy."""
    logger.info("=" * 60)
    logger.info("MIGRATING: Uploaded Files (files table)")
    logger.info("=" * 60)
    
    files = conn.execute(
        "SELECT f.id, f.file_path, f.original_name, f.company_id, f.module_id, f.folder_id "
        "FROM files f WHERE f.file_path IS NOT NULL"
    ).fetchall()
    
    if not files:
        logger.info("No uploaded files to migrate.")
        return {"total": 0, "migrated": 0, "skipped": 0, "failed": 0, "errors": []}
    
    results = {"total": len(files), "migrated": 0, "skipped": 0, "failed": 0, "errors": []}
    
    for f in files:
        file_id = f['id']
        old_path = f['file_path']
        original_name = f['original_name'] or os.path.basename(old_path)
        company_id = f['company_id']
        module_id = f['module_id']
        
        if not company_id or not module_id:
            logger.warning(f"  [SKIP] File ID={file_id} '{original_name}': Missing company_id or module_id")
            results["skipped"] += 1
            continue
        
        # Get new storage path
        result = get_company_storage_path(company_id, module_id, "uploads")
        if not result.get("success"):
            logger.error(f"  [FAIL] File ID={file_id} '{original_name}': Cannot determine storage path: {result}")
            results["failed"] += 1
            results["errors"].append({
                "file_id": file_id,
                "name": original_name,
                "old_path": old_path,
                "error": result.get("reason", "Unknown storage path error")
            })
            continue
        
        new_dir = result["path"]
        new_path = os.path.join(new_dir, original_name)
        
        # Skip if already at correct path
        if os.path.normpath(old_path) == os.path.normpath(new_path):
            logger.info(f"  [SKIP] File ID={file_id} '{original_name}': Already at correct path")
            results["skipped"] += 1
            continue
        
        if dry_run:
            logger.info(f"  [DRY-RUN] Would move: {old_path} -> {new_path}")
            results["migrated"] += 1
            continue
        
        # Ensure target directory exists
        os.makedirs(new_dir, exist_ok=True)
        
        # Handle filename conflicts
        if os.path.exists(new_path):
            # Add timestamp suffix to avoid overwriting
            base, ext = os.path.splitext(original_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{base}_{timestamp}{ext}"
            new_path = os.path.join(new_dir, new_name)
            logger.warning(f"  [CONFLICT] File ID={file_id}: '{original_name}' exists, renamed to '{new_name}'")
        
        try:
            if os.path.exists(old_path):
                shutil.move(old_path, new_path)
                logger.info(f"  [MOVED] File ID={file_id} '{original_name}': {old_path} -> {new_path}")
            else:
                logger.warning(f"  [WARN] File ID={file_id} '{original_name}': Source not found at {old_path}, updating DB only")
            
            # Update database
            conn.execute("UPDATE files SET file_path = ?, name = ? WHERE id = ?",
                         (new_path, os.path.basename(new_path), file_id))
            conn.commit()
            results["migrated"] += 1
        except Exception as e:
            logger.error(f"  [FAIL] File ID={file_id} '{original_name}': {e}")
            results["failed"] += 1
            results["errors"].append({
                "file_id": file_id,
                "name": original_name,
                "old_path": old_path,
                "new_path": new_path,
                "error": str(e)
            })
    
    return results


def migrate_master_files_table(conn, dry_run=False):
    """Migrate master files (DuckDB) to new hierarchy."""
    logger.info("=" * 60)
    logger.info("MIGRATING: Master Files (master_files table)")
    logger.info("=" * 60)
    
    files = conn.execute(
        "SELECT m.id, m.db_path, m.folder_id, m.company_id, m.module_id "
        "FROM master_files m WHERE m.db_path IS NOT NULL"
    ).fetchall()
    
    if not files:
        logger.info("No master files to migrate.")
        return {"total": 0, "migrated": 0, "skipped": 0, "failed": 0, "errors": []}
    
    results = {"total": len(files), "migrated": 0, "skipped": 0, "failed": 0, "errors": []}
    
    for m in files:
        master_id = m['id']
        old_path = m['db_path']
        folder_id = m['folder_id']
        company_id = m['company_id']
        module_id = m['module_id']
        
        if not company_id or not module_id:
            logger.warning(f"  [SKIP] Master ID={master_id}: Missing company_id or module_id")
            results["skipped"] += 1
            continue
        
        # Get new storage path
        result = get_company_storage_path(company_id, module_id, "master_files")
        if not result.get("success"):
            logger.error(f"  [FAIL] Master ID={master_id}: Cannot determine storage path: {result}")
            results["failed"] += 1
            results["errors"].append({
                "master_id": master_id,
                "folder_id": folder_id,
                "old_path": old_path,
                "error": result.get("reason", "Unknown storage path error")
            })
            continue
        
        new_dir = result["path"]
        original_name = os.path.basename(old_path) or f"folder_{folder_id}_master.duckdb"
        new_path = os.path.join(new_dir, original_name)
        
        # Skip if already at correct path
        if os.path.normpath(old_path) == os.path.normpath(new_path):
            logger.info(f"  [SKIP] Master ID={master_id}: Already at correct path")
            results["skipped"] += 1
            continue
        
        if dry_run:
            logger.info(f"  [DRY-RUN] Would move master: {old_path} -> {new_path}")
            results["migrated"] += 1
            continue
        
        os.makedirs(new_dir, exist_ok=True)
        
        try:
            if os.path.exists(old_path):
                shutil.move(old_path, new_path)
                logger.info(f"  [MOVED] Master ID={master_id}: {old_path} -> {new_path}")
            else:
                logger.warning(f"  [WARN] Master ID={master_id}: Source not found at {old_path}, updating DB only")
            
            conn.execute("UPDATE master_files SET db_path = ? WHERE id = ?", (new_path, master_id))
            conn.commit()
            results["migrated"] += 1
        except Exception as e:
            logger.error(f"  [FAIL] Master ID={master_id}: {e}")
            results["failed"] += 1
            results["errors"].append({
                "master_id": master_id,
                "folder_id": folder_id,
                "old_path": old_path,
                "new_path": new_path,
                "error": str(e)
            })
    
    return results


def migrate_processed_files_table(conn, dry_run=False):
    """Migrate processed output files to new hierarchy."""
    logger.info("=" * 60)
    logger.info("MIGRATING: Processed Files (processed_files table)")
    logger.info("=" * 60)
    
    files = conn.execute(
        "SELECT p.id, p.file_path, p.filename, p.company_id, p.module_id "
        "FROM processed_files p WHERE p.file_path IS NOT NULL"
    ).fetchall()
    
    if not files:
        logger.info("No processed files to migrate.")
        return {"total": 0, "migrated": 0, "skipped": 0, "failed": 0, "errors": []}
    
    results = {"total": len(files), "migrated": 0, "skipped": 0, "failed": 0, "errors": []}
    
    for p in files:
        proc_id = p['id']
        old_path = p['file_path']
        filename = p['filename'] or os.path.basename(old_path)
        company_id = p['company_id']
        module_id = p['module_id']
        
        if not company_id or not module_id:
            logger.warning(f"  [SKIP] Processed ID={proc_id} '{filename}': Missing company_id or module_id")
            results["skipped"] += 1
            continue
        
        # Get new storage path
        result = get_company_storage_path(company_id, module_id, "processed")
        if not result.get("success"):
            logger.error(f"  [FAIL] Processed ID={proc_id} '{filename}': Cannot determine storage path: {result}")
            results["failed"] += 1
            results["errors"].append({
                "processed_id": proc_id,
                "filename": filename,
                "old_path": old_path,
                "error": result.get("reason", "Unknown storage path error")
            })
            continue
        
        new_dir = result["path"]
        new_path = os.path.join(new_dir, filename)
        
        # Skip if already at correct path
        if os.path.normpath(old_path) == os.path.normpath(new_path):
            logger.info(f"  [SKIP] Processed ID={proc_id} '{filename}': Already at correct path")
            results["skipped"] += 1
            continue
        
        if dry_run:
            logger.info(f"  [DRY-RUN] Would move processed: {old_path} -> {new_path}")
            results["migrated"] += 1
            continue
        
        os.makedirs(new_dir, exist_ok=True)
        
        try:
            if os.path.exists(old_path):
                shutil.move(old_path, new_path)
                logger.info(f"  [MOVED] Processed ID={proc_id} '{filename}': {old_path} -> {new_path}")
            else:
                logger.warning(f"  [WARN] Processed ID={proc_id} '{filename}': Source not found at {old_path}, updating DB only")
            
            conn.execute("UPDATE processed_files SET file_path = ? WHERE id = ?", (new_path, proc_id))
            conn.commit()
            results["migrated"] += 1
        except Exception as e:
            logger.error(f"  [FAIL] Processed ID={proc_id} '{filename}': {e}")
            results["failed"] += 1
            results["errors"].append({
                "processed_id": proc_id,
                "filename": filename,
                "old_path": old_path,
                "new_path": new_path,
                "error": str(e)
            })
    
    return results


def print_summary(all_results):
    """Print migration summary."""
    total_all = sum(r["total"] for r in all_results.values())
    migrated_all = sum(r["migrated"] for r in all_results.values())
    skipped_all = sum(r["skipped"] for r in all_results.values())
    failed_all = sum(r["failed"] for r in all_results.values())
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total files scanned : {total_all}")
    logger.info(f"  Successfully migrated: {migrated_all}")
    logger.info(f"  Skipped (no context) : {skipped_all}")
    logger.info(f"  Failed               : {failed_all}")
    
    if failed_all > 0:
        logger.info("")
        logger.info("FAILED ITEMS:")
        for table, results in all_results.items():
            for err in results.get("errors", []):
                logger.info(f"  [{table}] {err.get('name', err.get('filename', 'unknown'))}: {err['error']}")
    
    logger.info("")
    logger.info(f"Full log saved to: {log_file}")


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    
    if dry_run:
        logger.info("*** DRY RUN MODE - No files will be moved ***")
    
    logger.info(f"Migration started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    if not force and not dry_run:
        print("\n" + "=" * 60)
        print("  FILE PATH MIGRATION TOOL")
        print("=" * 60)
        print()
        print("This script will move all existing files from the old flat")
        print("directory structure to the new company/module hierarchy:")
        print()
        print("  data/uploads/{CompanyName}_{CompanyCode}/{ModuleName}/")
        print("      uploads/")
        print("      master_files/")
        print("      primary_data/")
        print("      processed/")
        print()
        print("NOTE: This is a ONE-TIME operation. Backup your data first!")
        print()
        response = input("Continue with migration? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("Migration cancelled.")
            return
    
    conn = get_db_connection()
    
    try:
        all_results = {}
        
        # Migrate each table
        all_results["files"] = migrate_files_table(conn, dry_run)
        all_results["master_files"] = migrate_master_files_table(conn, dry_run)
        all_results["processed_files"] = migrate_processed_files_table(conn, dry_run)
        
        print_summary(all_results)
        
    finally:
        conn.close()
    
    if dry_run:
        logger.info("\n*** DRY RUN COMPLETE - Run without --dry-run to execute ***")
    else:
        logger.info("\n*** MIGRATION COMPLETE ***")
        logger.info("Please restart the server for changes to take effect.")


if __name__ == "__main__":
    main()