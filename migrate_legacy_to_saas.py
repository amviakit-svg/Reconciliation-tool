#!/usr/bin/env python3
"""
Migrate legacy reconciliation tool data into SaaS metadata.db
All data assigned to: TestCorp (company_id=1) -> Own Website (module_id=1)
"""

import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'metadata.db')
COMPANY_ID = 1
MODULE_ID = 1  # Own Website

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_folder(conn, name, path, parent_id=None):
    """Create a folder in the SaaS database"""
    cursor = conn.execute(
        """INSERT INTO folders (company_id, module_id, name, parent_id, path, created_at)
           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (COMPANY_ID, MODULE_ID, name, parent_id, path)
    )
    conn.commit()
    return cursor.lastrowid

def insert_file(conn, folder_id, original_name, file_path, size, fmt, sheet_names=None):
    """Insert a file record into the files table"""
    cursor = conn.execute(
        """INSERT INTO files (company_id, module_id, folder_id, name, original_name, file_path, size, format, sheet_names, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (COMPANY_ID, MODULE_ID, folder_id, os.path.basename(file_path), original_name, file_path, size, fmt, sheet_names)
    )
    conn.commit()
    return cursor.lastrowid

def insert_processed_file(conn, filename, file_path, report_type="Reconciliation", financial_year="FY2025-26", month_name="Apr", month_number=4, year=2025):
    """Insert a processed file record"""
    cursor = conn.execute(
        """INSERT INTO processed_files (company_id, module_id, filename, file_path, report_type, financial_year, month_name, month_number, year, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (COMPANY_ID, MODULE_ID, filename, file_path, report_type, financial_year, month_name, month_number, year)
    )
    conn.commit()
    return cursor.lastrowid

def insert_master_file(conn, folder_id, db_path, sheet_name=None, columns=None, header_row=None):
    """Insert a master file record"""
    cursor = conn.execute(
        """INSERT INTO master_files (company_id, module_id, folder_id, db_path, sheet_name, columns, header_row, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (COMPANY_ID, MODULE_ID, folder_id, db_path, sheet_name, columns, header_row)
    )
    conn.commit()
    return cursor.lastrowid

def migrate_all():
    conn = get_db()
    
    # Clear existing data for this company+module to avoid duplicates
    print("Clearing existing data for TestCorp -> Own Website...")
    conn.execute("DELETE FROM files WHERE company_id = ? AND module_id = ?", (COMPANY_ID, MODULE_ID))
    conn.execute("DELETE FROM processed_files WHERE company_id = ? AND module_id = ?", (COMPANY_ID, MODULE_ID))
    conn.execute("DELETE FROM master_files WHERE company_id = ? AND module_id = ?", (COMPANY_ID, MODULE_ID))
    conn.execute("DELETE FROM folders WHERE company_id = ? AND module_id = ?", (COMPANY_ID, MODULE_ID))
    conn.commit()
    
    # Create root folder structure
    print("Creating folder structure...")
    root_path = f"companies/{COMPANY_ID}/modules/{MODULE_ID}"
    
    uploads_folder = create_folder(conn, "Uploads", f"{root_path}/uploads")
    primary_folder = create_folder(conn, "Primary Data", f"{root_path}/primary_data")
    processed_folder = create_folder(conn, "Processed Reports", f"{root_path}/processed")
    master_folder = create_folder(conn, "Master Data", f"{root_path}/master")
    results_folder = create_folder(conn, "Reconciliation Results", f"{root_path}/results")
    
    print(f"  Created folders: Uploads(ID={uploads_folder}), Primary(ID={primary_folder}), Processed(ID={processed_folder}), Master(ID={master_folder}), Results(ID={results_folder})")
    
    # Migrate uploads
    uploads_dir = os.path.join('data', 'uploads')
    uploaded_count = 0
    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            fpath = os.path.join(uploads_dir, fname)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                ext = os.path.splitext(fname)[1].lower().replace('.', '')
                if ext == 'xlsx':
                    ext = 'xlsx'
                elif ext == 'csv':
                    ext = 'csv'
                insert_file(conn, uploads_folder, fname, fpath, size, ext)
                uploaded_count += 1
    print(f"  Migrated {uploaded_count} uploaded files")
    
    # Migrate primary files
    primary_dir = os.path.join('data', 'uploads', 'primary_files')
    primary_count = 0
    if os.path.exists(primary_dir):
        for fname in os.listdir(primary_dir):
            fpath = os.path.join(primary_dir, fname)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                ext = os.path.splitext(fname)[1].lower().replace('.', '')
                if ext == 'xlsx':
                    ext = 'xlsx'
                elif ext == 'csv':
                    ext = 'csv'
                insert_file(conn, primary_folder, fname, fpath, size, ext)
                primary_count += 1
    print(f"  Migrated {primary_count} primary files")
    
    # Migrate processed files
    processed_dir = os.path.join('data', 'processed')
    processed_count = 0
    if os.path.exists(processed_dir):
        for root, dirs, files in os.walk(processed_dir):
            for fname in files:
                if fname.endswith('.xlsx'):
                    fpath = os.path.join(root, fname)
                    size = os.path.getsize(fpath)
                    # Parse info from filename: Apr25_Sales_Reconciliation_20260513_180306.xlsx
                    report_type = "Sales Reconciliation"
                    financial_year = "FY2025-26"
                    month_name = "Apr"
                    month_number = 4
                    year = 2025
                    insert_processed_file(conn, fname, fpath, report_type, financial_year, month_name, month_number, year)
                    processed_count += 1
    print(f"  Migrated {processed_count} processed files")
    
    # Migrate master files
    master_dir = os.path.join('data', 'master_files')
    master_count = 0
    if os.path.exists(master_dir):
        for fname in os.listdir(master_dir):
            fpath = os.path.join(master_dir, fname)
            if os.path.isfile(fpath) and fname.endswith('.duckdb'):
                insert_master_file(conn, master_folder, fpath)
                master_count += 1
    print(f"  Migrated {master_count} master files")
    
    # Migrate reconciliation result files (those in uploads root with Reconciliation_Result_* prefix)
    results_count = 0
    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            if fname.startswith('Reconciliation_Result_') and fname.endswith('.xlsx'):
                fpath = os.path.join(uploads_dir, fname)
                size = os.path.getsize(fpath)
                insert_file(conn, results_folder, fname, fpath, size, 'xlsx')
                results_count += 1
    print(f"  Migrated {results_count} reconciliation result files")
    
    conn.close()
    print("\nMigration complete!")
    print(f"Summary: {uploaded_count} uploads + {primary_count} primary + {processed_count} processed + {master_count} master + {results_count} results = Total migrated")

if __name__ == '__main__':
    migrate_all()