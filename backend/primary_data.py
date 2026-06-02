import os
import json
import re
import pandas as pd
import openpyxl
from datetime import datetime

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads')
PRIMARY_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads', 'primary_files')
os.makedirs(PRIMARY_DIR, exist_ok=True)

# Reserved columns in primary output
RESERVED_COLUMN_LETTERS = {'A', 'B', 'C'}
RESERVED_COLUMN_NAMES = ['Unique_ID', 'Source_File_Name', 'Order ID']

def _column_letter_to_number(letter):
    """Convert Excel column letter to 1-based number (A=1, B=2, ..., Z=26, AA=27)"""
    result = 0
    for char in letter.upper():
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result

def _column_number_to_letter(num):
    """Convert 1-based number to Excel column letter (1=A, 26=Z, 27=AA)"""
    result = ''
    while num > 0:
        num, remainder = divmod(num - 1, 26)
        result = chr(ord('A') + remainder) + result
    return result

def _get_next_available_column(used_letters):
    """Get next available column letter after C, skipping used letters"""
    num = 4  # Start from D (column 4)
    while True:
        letter = _column_number_to_letter(num)
        if letter not in used_letters:
            return letter
        num += 1

def _sort_columns_by_letter(columns_dict):
    """Sort columns by Excel column letter for output ordering"""
    items = list(columns_dict.items())
    items.sort(key=lambda x: _column_letter_to_number(x[0]))
    return {k: v for k, v in items}

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

def generate_primary_data(file_id, sheet_name, column_name, header_row=1, sales_amount_column=None, fields=None):
    """
    Generate unique primary data from selected file/sheet/column.
    Supports multi-field extraction with SUM and VLOOKUP aggregations.
    Supports regular files and master files (master_{folder_id}).
    
    Parameters:
        fields: list of dicts, each with:
            - name: str              # Field display name (e.g. "Sales Amount")
            - source_column: str     # Column in source file
            - aggregation: str       # "SUM" or "VLOOKUP"
            - output_column: str     # Excel column letter (e.g. "D", "E")
    
    Backward compatibility: if fields is None/empty and sales_amount_column is set,
    auto-creates a single "Sales Amount" field with SUM aggregation at column D.
    """
    from database import get_db_connection, get_master_file
    
    # ---- Backward compatibility: migrate old sales_amount_column to fields ----
    if not fields and sales_amount_column:
        fields = [{
            'name': 'Sales Amount',
            'source_column': sales_amount_column,
            'aggregation': 'SUM',
            'output_column': 'D'
        }]
    elif not fields:
        fields = []
    
    # Handle master files: file_id is "master_{folder_id}"
    if isinstance(file_id, str) and file_id.startswith('master_'):
        folder_id = int(file_id.replace('master_', ''))
        master = get_master_file(folder_id)
        
        if not master:
            raise Exception("Master file not found")
            
        # [DATA INTEGRITY GUARD] Check sync status of all files in this folder
        conn_sync = get_db_connection()
        try:
            sync_statuses = conn_sync.execute("SELECT sync_status FROM files WHERE folder_id = ?", (folder_id,)).fetchall()
            statuses = [row['sync_status'] for row in sync_statuses]
            if 'in_processing' in statuses:
                raise Exception("Cannot generate primary data: Files in this folder are currently syncing. Please wait for sync to complete.")
            if 'rejected' in statuses or 'pending' in statuses:
                raise Exception("Cannot generate primary data: Some files in this folder failed to sync (Rejected) or are Pending. Please resolve them first to ensure data completeness.")
        finally:
            conn_sync.close()
        
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
        if file_format == 'CSV':
            df = pd.read_csv(file_path, header=header_row-1, dtype=str, low_memory=False)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row-1, dtype=str)
    
    # Check if column exists
    if column_name not in df.columns:
        raise Exception(f"Column '{column_name}' not found in file. Available columns: {list(df.columns)}")
    
    # Validate all field source columns exist
    for field in fields:
        if field['source_column'] not in df.columns:
            raise Exception(f"Field '{field['name']}' source column '{field['source_column']}' not found in file. Available columns: {list(df.columns)}")
    
    # ---- Get unique values (Order IDs) ----
    has_source_file_name = 'Source_File_Name' in df.columns
    if has_source_file_name:
        grouped = df.dropna(subset=[column_name]).drop_duplicates(
            subset=['Source_File_Name', column_name]
        )
        source_names = grouped['Source_File_Name'].tolist()
        unique_values = grouped[column_name].tolist()
    else:
        unique_values = df[column_name].dropna().unique().tolist()
        source_names = [original_name] * len(unique_values)
    
    num_rows = len(unique_values)
    
    # ---- Build primary DataFrame with reserved columns ----
    primary_data = {
        'Unique_ID': range(1, num_rows + 1),
        'Source_File_Name': source_names,
        column_name: unique_values,  # Order ID column (keeps original name)
    }
    
    # Track field metadata for response
    field_columns_meta = []
    warnings = []
    
    # ---- Process each dynamic field ----
    for field in fields:
        field_name = field.get('name', field['source_column'])
        source_col = field['source_column']
        aggregation = field.get('aggregation', 'SUM').upper()
        output_col = field.get('output_column', 'D')
        
        values = [''] * num_rows
        
        if aggregation == 'SUM':
            # ---- SUM aggregation ----
            df_work = df.copy()
            numeric_series = pd.to_numeric(
                df_work[source_col].astype(str).str.replace(',', '').str.strip(),
                errors='coerce'
            )
            
            # Check if column contains mostly non-numeric data
            non_null = numeric_series.notna().sum()
            total = len(numeric_series)
            if non_null == 0:
                warnings.append(f"PH1-011: Field '{field_name}' column contains no numeric data; SUM will produce zeros.")
            elif non_null < total * 0.5:
                warnings.append(f"PH1-011: Field '{field_name}' column contains mostly non-numeric data ({total - non_null}/{total} rows); consider switching to VLOOKUP.")
            
            df_work['_num'] = numeric_series.fillna(0)
            
            if has_source_file_name:
                sum_lookup = df_work.groupby(['Source_File_Name', column_name])['_num'].sum().to_dict()
                values = [
                    float(sum_lookup.get((sn, uv), 0))
                    for sn, uv in zip(source_names, unique_values)
                ]
            else:
                sum_lookup = df_work.groupby(column_name)['_num'].sum().to_dict()
                values = [
                    float(sum_lookup.get(uv, 0))
                    for uv in unique_values
                ]
                
        elif aggregation == 'VLOOKUP':
            # ---- VLOOKUP aggregation (first value per group) ----
            dup_count = 0
            if has_source_file_name:
                # Group by (Source_File_Name, Order ID), take first value
                for i, (sn, uv) in enumerate(zip(source_names, unique_values)):
                    mask = (df['Source_File_Name'] == sn) & (df[column_name] == uv)
                    matches = df.loc[mask, source_col]
                    if len(matches) > 1:
                        dup_count += 1
                    values[i] = str(matches.iloc[0]) if len(matches) > 0 else ''
            else:
                # Single file: group by Order ID only
                for i, uv in enumerate(unique_values):
                    mask = df[column_name] == uv
                    matches = df.loc[mask, source_col]
                    if len(matches) > 1:
                        dup_count += 1
                    values[i] = str(matches.iloc[0]) if len(matches) > 0 else ''
            
            if dup_count > 0:
                warnings.append(f"PH1-010: {dup_count} duplicate matches found for VLOOKUP on field '{field_name}'. The first value is used for each duplicate group.")
        
        else:
            raise Exception(f"Unknown aggregation type '{aggregation}' for field '{field_name}'. Use 'SUM' or 'VLOOKUP'.")
        
        primary_data[field_name] = values
        field_columns_meta.append({
            'name': field_name,
            'source_column': source_col,
            'aggregation': aggregation,
            'output_column': output_col,
            'label': f"{field_name} | {aggregation} | Col {output_col}"
        })
    
    # Create DataFrame
    primary_df = pd.DataFrame(primary_data)
    
    # ---- Build output columns metadata (sorted by letter) ----
    # Reserved columns
    output_columns = [
        {'letter': 'A', 'name': 'Unique_ID', 'reserved': True},
        {'letter': 'B', 'name': 'Source_File_Name', 'reserved': True},
        {'letter': 'C', 'name': column_name, 'reserved': True, 'is_primary': True},
    ]
    for f in field_columns_meta:
        output_columns.append({
            'letter': f['output_column'],
            'name': f['name'],
            'reserved': False,
            'aggregation': f['aggregation'],
            'source_column': f['source_column']
        })
    
    # Sort by column letter
    output_columns.sort(key=lambda c: _column_letter_to_number(c['letter']))
    
    # ---- Save primary file ----
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = original_name.replace('.', '_').replace(' ', '_')
    
    from database import get_physical_storage_path
    storage_dir = get_physical_storage_path(PRIMARY_DIR, company_id, module_id)
    os.makedirs(storage_dir, exist_ok=True)
    
    if num_rows > 1_000_000:
        primary_filename = f"primary_file.csv"
        primary_path = os.path.join(storage_dir, primary_filename)
        primary_df.to_csv(primary_path, index=False)
    else:
        primary_filename = f"primary_file.xlsx"
        primary_path = os.path.join(storage_dir, primary_filename)
        primary_df.to_excel(primary_path, index=False, sheet_name='working')
    
    # ---- Build preview data with proper formatting ----
    preview_records = primary_df.head(10).to_dict(orient='records')
    # Format numeric values for preview
    for record in preview_records:
        for f in field_columns_meta:
            field_name = f['name']
            if f['aggregation'] == 'SUM' and field_name in record:
                try:
                    val = float(record[field_name])
                    if val == 0:
                        record[field_name] = '0.00'
                    else:
                        record[field_name] = f"{val:,.2f}"
                except (ValueError, TypeError):
                    pass
    
    return {
        'file_path': primary_path,
        'filename': primary_filename,
        'original_file': original_name,
        'sheet_name': sheet_name,
        'column_name': column_name,
        'total_unique': num_rows,
        'preview': preview_records,
        'all_values': primary_df.to_dict(orient='records'),
        'fields': field_columns_meta,
        'columns': output_columns,
        'warnings': warnings
    }


def preview_primary_data(file_id, sheet_name, column_name, header_row=1, fields=None):
    """
    Generate a quick preview without saving to disk.
    Returns preview rows and unique count only.
    """
    from database import get_db_connection, get_master_file
    
    if not fields:
        fields = []
    
    # Handle master files
    if isinstance(file_id, str) and file_id.startswith('master_'):
        folder_id = int(file_id.replace('master_', ''))
        master = get_master_file(folder_id)
        if not master:
            raise Exception("Master file not found")
        import duckdb
        conn = duckdb.connect(master['db_path'], read_only=True)
        try:
            df = conn.execute("SELECT * FROM master_data").fetchdf()
        finally:
            conn.close()
        df = df.astype(str)
        original_name = f"Master_File_{folder_id}"
    else:
        conn = get_db_connection()
        file = conn.execute("SELECT file_path, original_name, format FROM files WHERE id = ?", (file_id,)).fetchone()
        conn.close()
        if not file:
            raise Exception("File not found")
        file_path = file['file_path']
        if not os.path.exists(file_path):
            filename = os.path.basename(file_path)
            new_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(new_path):
                file_path = new_path
        original_name = file['original_name']
        file_format = file['format'].upper() if file['format'] else ''
        if file_format == 'CSV':
            df = pd.read_csv(file_path, header=header_row-1, dtype=str, low_memory=False)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row-1, dtype=str)
    
    if column_name not in df.columns:
        raise Exception(f"Column '{column_name}' not found in file.")
    
    # Validate source columns
    for field in fields:
        if field.get('source_column') and field['source_column'] not in df.columns:
            raise Exception(f"Field '{field.get('name', '?')}' source column '{field['source_column']}' not found.")
    
    # Get unique values
    has_source_file_name = 'Source_File_Name' in df.columns
    if has_source_file_name:
        grouped = df.dropna(subset=[column_name]).drop_duplicates(
            subset=['Source_File_Name', column_name]
        )
        source_names = grouped['Source_File_Name'].tolist()
        unique_values = grouped[column_name].tolist()
    else:
        unique_values = df[column_name].dropna().unique().tolist()
        source_names = [original_name] * len(unique_values)
    
    num_rows = len(unique_values)
    
    # Build preview data
    preview_data = {
        'Unique_ID': range(1, min(num_rows, 10) + 1),
        'Source_File_Name': source_names[:10],
        column_name: unique_values[:10],
    }
    
    for field in fields:
        field_name = field.get('name', field.get('source_column', 'Field'))
        source_col = field.get('source_column', '')
        aggregation = field.get('aggregation', 'SUM').upper()
        
        if not source_col or source_col not in df.columns:
            preview_data[field_name] = [''] * min(num_rows, 10)
            continue
        
        values = [''] * min(num_rows, 10)
        if aggregation == 'SUM':
            df_work = df.copy()
            numeric_series = pd.to_numeric(
                df_work[source_col].astype(str).str.replace(',', '').str.strip(),
                errors='coerce'
            ).fillna(0)
            df_work['_num'] = numeric_series
            if has_source_file_name:
                sum_lookup = df_work.groupby(['Source_File_Name', column_name])['_num'].sum().to_dict()
                values = [
                    float(sum_lookup.get((sn, uv), 0))
                    for sn, uv in zip(source_names[:10], unique_values[:10])
                ]
            else:
                sum_lookup = df_work.groupby(column_name)['_num'].sum().to_dict()
                values = [float(sum_lookup.get(uv, 0)) for uv in unique_values[:10]]
        elif aggregation == 'VLOOKUP':
            if has_source_file_name:
                for i, (sn, uv) in enumerate(zip(source_names[:10], unique_values[:10])):
                    mask = (df['Source_File_Name'] == sn) & (df[column_name] == uv)
                    matches = df.loc[mask, source_col]
                    values[i] = str(matches.iloc[0]) if len(matches) > 0 else ''
            else:
                for i, uv in enumerate(unique_values[:10]):
                    mask = df[column_name] == uv
                    matches = df.loc[mask, source_col]
                    values[i] = str(matches.iloc[0]) if len(matches) > 0 else ''
        
        preview_data[field_name] = values
    
    preview_df = pd.DataFrame(preview_data)
    
    return {
        'preview': preview_df.head(10).to_dict(orient='records'),
        'total_unique': num_rows,
        'has_source_file_name': has_source_file_name
    }


def get_primary_file_path(filename, company_id=None, module_id=None):
    """Get full path of a primary file by searching in the company's directories.
    Searches broadly across all possible storage locations, including nested
    company/module subdirectories that may have been created by the physical
    storage path resolution system.
    """
    from database import get_physical_storage_path
    dirs_to_scan = []
    
    if company_id is not None and module_id is not None:
        dirs_to_scan.append(get_physical_storage_path(PRIMARY_DIR, company_id, module_id))
        dirs_to_scan.append(get_physical_storage_path(UPLOAD_DIR, company_id, module_id))
    
    # Always include base directories as fallback (especially for legacy/non-SaaS usage)
    base_dirs = [PRIMARY_DIR, UPLOAD_DIR]
    for bd in base_dirs:
        if os.path.exists(bd) and bd not in dirs_to_scan:
            dirs_to_scan.append(bd)
    
    # First pass: search in the preferred directories (company-scoped)
    for scan_dir in dirs_to_scan:
        if os.path.exists(scan_dir):
            for root, dirs, files in os.walk(scan_dir):
                if filename in files:
                    return os.path.join(root, filename)
    
    # Second pass: if file not found, search ALL possible locations recursively
    # This covers edge cases where the file was saved under a different company context
    # or the directory structure has changed since the file was created
    all_search_roots = []
    for bd in base_dirs:
        if os.path.exists(bd):
            all_search_roots.append(bd)
    # Also search from data directory root
    data_root = os.path.join(os.path.dirname(__file__), '..', 'data')
    if os.path.exists(data_root) and data_root not in all_search_roots:
        all_search_roots.append(data_root)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Primary file '{filename}' not found in company-scoped directories. "
                   f"Performing broad search across {len(all_search_roots)} root(s)")
    
    for scan_root in all_search_roots:
        if os.path.exists(scan_root):
            for root, dirs, files in os.walk(scan_root):
                if filename in files:
                    found_path = os.path.join(root, filename)
                    logger.info(f"Found primary file via broad search: {found_path}")
                    return found_path
    
    logger.error(f"Primary file '{filename}' could not be found anywhere. "
                 f"Searched directories: {dirs_to_scan}, fallback roots: {all_search_roots}")
    return os.path.join(PRIMARY_DIR, filename)

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


def get_primary_field_columns(company_id=None, module_id=None):
    """
    Get the list of field column definitions from the most recent Phase 1 rule config.
    Used by Phase 2 and Phase 4 to know available primary data columns.
    """
    from database import get_db_connection
    conn = get_db_connection()
    try:
        rule = conn.execute(
            "SELECT config FROM rules WHERE phase = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not rule:
            return []
        
        config = json.loads(rule['config'])
        fields = config.get('fields', [])
        
        # Backward compatibility: convert legacy sales_column
        if not fields and config.get('sales_column'):
            fields = [{
                'name': 'Sales Amount',
                'source_column': config['sales_column'],
                'aggregation': 'SUM',
                'output_column': 'D'
            }]
        
        return fields
    except Exception:
        return []
    finally:
        conn.close()