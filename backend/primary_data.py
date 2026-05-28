import os
import json
import pandas as pd
import openpyxl
from datetime import datetime

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads')
PRIMARY_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads', 'primary_files')
os.makedirs(PRIMARY_DIR, exist_ok=True)

def _get_primary_storage_path(company_id=None, module_id=None):
    """
    Get the primary data storage path using the company-based hierarchy.
    Falls back to legacy PRIMARY_DIR if company/module not provided.
    """
    if company_id is not None and module_id is not None:
        from database import get_company_storage_path
        result = get_company_storage_path(company_id, module_id, "primary_data")
        if result.get("success"):
            return result["path"]
    # Fallback: use legacy path
    os.makedirs(PRIMARY_DIR, exist_ok=True)
    return PRIMARY_DIR

def generate_primary_data(file_id, sheet_name, column_name, header_row=1, sales_amount_column=None):
    """
    Generate unique primary data from selected file/sheet/column.
    Optionally computes SUMIF for a sales amount column.
    Supports regular files and master files (master_{folder_id}).
    Returns the unique values and saves as a new Excel file.
    """
    from database import get_db_connection, get_master_file
    
    # Handle master files: file_id is "master_{folder_id}"
    if isinstance(file_id, str) and file_id.startswith('master_'):
        folder_id = int(file_id.replace('master_', ''))
        master = get_master_file(folder_id)
        
        if not master:
            raise Exception("Master file not found")
        
        company_id = master['company_id']
        module_id = master['module_id']
        db_path = master['db_path']
        original_name = f"Master_File_{folder_id}"
        
        # Read from DuckDB master file
        import duckdb
        conn = duckdb.connect(db_path, read_only=True)
        try:
            df = conn.execute("SELECT * FROM master_data").fetchdf()
        finally:
            conn.close()
        
        # Convert to string to prevent mixed type issues
        df = df.astype(str)
    else:
        # Regular file handling
        conn = get_db_connection()
        file = conn.execute("SELECT file_path, original_name, format, company_id, module_id FROM files WHERE id = ?", (file_id,)).fetchone()
        conn.close()
        
        if not file:
            raise Exception("File not found")
            
        company_id = file['company_id']
        module_id = file['module_id']
        
        file_path = file['file_path']
        if not os.path.exists(file_path):
            filename = os.path.basename(file_path)
            new_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(new_path):
                file_path = new_path

        original_name = file['original_name']
        file_format = file['format'].upper() if file['format'] else ''
        
        # Read the file - IMPORTANT: Use dtype=str to prevent mixed type issues
        # where same values are read as int vs string, causing duplicate unique counts
        if file_format == 'CSV':
            df = pd.read_csv(file_path, header=header_row-1, dtype=str, low_memory=False)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row-1, dtype=str)
    
    # Check if column exists
    if column_name not in df.columns:
        raise Exception(f"Column '{column_name}' not found in file. Available columns: {list(df.columns)}")
    
    # Get unique values — PER SOURCE FILE instead of globally
    # This preserves Order IDs that exist in multiple source files (each gets its own row)
    # Only globally deduplicate when there is no Source_File_Name column (single file upload)
    has_source_file_name = 'Source_File_Name' in df.columns
    if has_source_file_name:
        # Master/merged file: deduplicate within each source file group
        # Same Order ID can appear under different source files → keep all
        grouped = df.dropna(subset=[column_name]).drop_duplicates(
            subset=['Source_File_Name', column_name]
        )
        source_names = grouped['Source_File_Name'].tolist()
        unique_values = grouped[column_name].tolist()
    else:
        # Regular single file: global deduplication (all rows from one file)
        unique_values = df[column_name].dropna().unique().tolist()
        source_names = [original_name] * len(unique_values)
    
    # ---- NEW: Sales Amount SUMIF logic ----
    # Compute SUMIF for sales amount column if provided
    sales_amount_values = [''] * len(unique_values)
    if sales_amount_column and sales_amount_column in df.columns:
        # Convert sales amount to numeric (handle commas, strings, empty)
        df_amt = df.copy()
        df_amt['_sales_num'] = pd.to_numeric(
            df_amt[sales_amount_column].astype(str).str.replace(',', '').str.strip(),
            errors='coerce'
        ).fillna(0)
        
        if has_source_file_name:
            # Per-source-file SUMIF: group by (Source_File_Name, Order ID)
            sum_lookup = df_amt.groupby(['Source_File_Name', column_name])['_sales_num'].sum().to_dict()
            sales_amount_values = [
                float(sum_lookup.get((sn, uv), 0))
                for sn, uv in zip(source_names, unique_values)
            ]
        else:
            # Single file: group by Order ID only
            sum_lookup = df_amt.groupby(column_name)['_sales_num'].sum().to_dict()
            sales_amount_values = [
                float(sum_lookup.get(uv, 0))
                for uv in unique_values
            ]
    # ---- END Sales Amount SUMIF ----
    
    # Create primary data DataFrame
    primary_df = pd.DataFrame({
        'Unique_ID': range(1, len(unique_values) + 1),
        'Source_File_Name': source_names,
        'Order ID': unique_values,
        'Sales Amount': sales_amount_values
    })
    
    # Save as CSV for large datasets (>1M rows) to avoid Excel row limit
    # Excel max rows: 1,048,576
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = original_name.replace('.', '_').replace(' ', '_')
    
    from database import get_physical_storage_path
    storage_dir = get_physical_storage_path(PRIMARY_DIR, company_id, module_id)
    os.makedirs(storage_dir, exist_ok=True)
    
    if len(unique_values) > 1_000_000:
        # Save as CSV for large datasets
        primary_filename = f"primary_file.csv"
        primary_path = os.path.join(storage_dir, primary_filename)
        primary_df.to_csv(primary_path, index=False)
    else:
        # Save as Excel for smaller datasets
        primary_filename = f"primary_file.xlsx"
        primary_path = os.path.join(storage_dir, primary_filename)
        primary_df.to_excel(primary_path, index=False, sheet_name='working')
    
    return {
        'file_path': primary_path,
        'filename': primary_filename,
        'original_file': original_name,
        'sheet_name': sheet_name,
        'column_name': column_name,
        'total_unique': len(unique_values),
        'preview': primary_df.head(10).to_dict(orient='records'),
        'all_values': primary_df.to_dict(orient='records')
    }

def get_primary_file_path(filename, company_id=None, module_id=None):
    """Get full path of a primary file by searching in the company's directories"""
    dirs_to_scan = []
    if company_id is not None and module_id is not None:
        from database import get_physical_storage_path
        dirs_to_scan.append(get_physical_storage_path(PRIMARY_DIR, company_id, module_id))
        dirs_to_scan.append(get_physical_storage_path(UPLOAD_DIR, company_id, module_id))
    else:
        dirs_to_scan.extend([PRIMARY_DIR, UPLOAD_DIR])
        
    for scan_dir in dirs_to_scan:
        if os.path.exists(scan_dir):
            for root, dirs, files in os.walk(scan_dir):
                if filename in files:
                    return os.path.join(root, filename)
    return os.path.join(dirs_to_scan[0], filename)

def list_primary_files(company_id=None, module_id=None):
    """List all generated primary files by searching in the company directory"""
    files = []
    seen_names = set()
    
    dirs_to_scan = []
    if company_id is not None and module_id is not None:
        from database import get_physical_storage_path
        dirs_to_scan.append(get_physical_storage_path(PRIMARY_DIR, company_id, module_id))
        dirs_to_scan.append(get_physical_storage_path(UPLOAD_DIR, company_id, module_id))
    else:
        dirs_to_scan.extend([PRIMARY_DIR, UPLOAD_DIR])
    
    for scan_dir in dirs_to_scan:
        if os.path.exists(scan_dir):
            for root, dirs, f_list in os.walk(scan_dir):
                for f in f_list:
                    if f.startswith('primary_file') and (f.endswith('.xlsx') or f.endswith('.csv')):
                        if f not in seen_names:
                            seen_names.add(f)
                            file_path = os.path.join(root, f)
                            files.append({
                                'name': f,
                                'path': file_path,
                                'size': os.path.getsize(file_path),
                                'created': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                            })
    return files

def read_primary_file(filename, company_id=None, module_id=None):
    """Read a primary file (xlsx or csv) and return DataFrame"""
    file_path = get_primary_file_path(filename, company_id, module_id)
    if not os.path.exists(file_path):
        raise Exception(f"Primary file not found: {filename}")
    
    if filename.endswith('.csv'):
        return pd.read_csv(file_path, header=0, dtype=str)
    else:
        try:
            return pd.read_excel(file_path, sheet_name='working', header=0, dtype=str)
        except Exception:
            return pd.read_excel(file_path, sheet_name=0, header=0, dtype=str)
