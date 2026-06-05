import os
import json
import logging
from typing import List, Dict, Any
import duckdb
import pandas as pd
import openpyxl

from backend.database import get_db_connection, set_file_sync_status, get_files_by_folder, get_master_formulas, get_physical_storage_path

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DIR = os.path.join(BASE_DIR, '..', 'data', 'master_files')


# Global dictionary to act as our Debounce Queue
# Structure: {folder_id: {"is_running": False, "sync_needed": False}}
SYNC_QUEUES = {}

async def trigger_folder_sync(folder_id: int, force_sync: bool = False):
    """
    Triggers a background sync for the given folder.
    Implements the Folder-Level Debounce Queue strategy.
    """
    if folder_id not in SYNC_QUEUES:
        SYNC_QUEUES[folder_id] = {"is_running": False, "sync_needed": False}
        
    queue_state = SYNC_QUEUES[folder_id]
    
    if queue_state["is_running"]:
        # A sync is already running. Flag that another sync is needed after.
        logger.info(f"Sync already running for folder {folder_id}. Flagging for next run.")
        queue_state["sync_needed"] = True
    else:
        # Start the sync process
        queue_state["is_running"] = True
        queue_state["sync_needed"] = False
        
        # We use a while loop to keep running as long as new syncs are requested
        # while the current one was running (Debounce logic).
        while True:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, run_incremental_sync, folder_id, force_sync)
            except Exception as e:
                logger.error(f"Error during background sync for folder {folder_id}: {e}")
                
            # Check if more files arrived while we were processing
            if queue_state["sync_needed"]:
                logger.info(f"More files arrived for folder {folder_id} during sync. Running again.")
                queue_state["sync_needed"] = False
            else:
                # No new files arrived, we can release the lock
                queue_state["is_running"] = False
                break

def run_incremental_sync(folder_id: int, force_sync: bool = False):
    """
    The core logic for Lightning-Fast Incremental Sync.
    1. Compares files in SQLite vs DuckDB.
    2. Deletes missing files from DuckDB.
    3. Appends new files to DuckDB.
    4. Re-applies formulas.
    """
    conn = get_db_connection()
    try:
        # Get master file config
        master = conn.execute("SELECT * FROM master_files WHERE folder_id = ?", (folder_id,)).fetchone()
        if not master:
            logger.info(f"No master file exists for folder {folder_id}. Sync aborted.")
            return
            
        master = dict(master)
        company_id = master['company_id']
        module_id = master['module_id']
        
        # Get all current files in SQLite for this folder
        sqlite_files = get_files_by_folder(folder_id)
        
        master_storage_dir = get_physical_storage_path(MASTER_DIR, company_id, module_id, folder_id)
        master_db_path = os.path.join(master_storage_dir, f"folder_{folder_id}_master.duckdb")
        
        if not os.path.exists(master_db_path):
            logger.info(f"Master DuckDB does not exist for folder {folder_id}. Triggering full manual rebuild.")
            # If the DB was deleted manually, a full rebuild is needed via the main API.
            # We won't attempt to recreate it from scratch here to keep logic isolated.
            return
            
        # Determine column selection from master config
        column_names = master.get('columns') or 'All'
        is_all_columns = column_names.strip().upper() == 'ALL'
        if not is_all_columns:
            try:
                user_columns = json.loads(column_names)
                if isinstance(user_columns, str):
                    user_columns = json.loads(user_columns)
                if not isinstance(user_columns, list):
                    user_columns = [c.strip() for c in str(user_columns).split(',') if c.strip()]
            except Exception:
                user_columns = [c.strip() for c in column_names.split(',') if c.strip()]
        else:
            user_columns = []
            
        formulas = get_master_formulas(folder_id)
        formula_cols = set([f.get('column_name') for f in formulas if f.get('column_name')])

        
        # Connect to DuckDB
        duck_conn = duckdb.connect(master_db_path)
        try:
            # Check if master_data table exists
            tables = duck_conn.execute("SHOW TABLES").fetchall()
            if ('master_data',) not in tables:
                logger.info("master_data table missing in DuckDB.")
                return
                
            # Get files currently in DuckDB
            duckdb_files_res = duck_conn.execute("SELECT DISTINCT Source_File_Name FROM master_data").fetchall()
            duckdb_files = set([row[0] for row in duckdb_files_res])
            
            # Get files currently in SQLite
            sqlite_file_names = {f['original_name']: f for f in sqlite_files}
            
            # Files to REMOVE from DuckDB (exist in DuckDB, but deleted from SQLite)
            files_to_remove = duckdb_files - set(sqlite_file_names.keys())
            
            # Files to ADD to DuckDB (exist in SQLite, but not in DuckDB, OR are marked for retry/pending)
            files_to_add = []
            auto_sync_enabled = int(master.get('auto_sync', 0)) == 1
            if force_sync or auto_sync_enabled:
                for f in sqlite_files:
                    if f['original_name'] not in duckdb_files or f.get('sync_status') in ('pending', 'rejected'):
                        files_to_add.append(f)
                    
            if not files_to_remove and not files_to_add:
                logger.info(f"Folder {folder_id} is fully in sync.")
                return
                
            logger.info(f"Folder {folder_id} Sync: Removing {len(files_to_remove)} files, Adding {len(files_to_add)} files.")
            
            company_id = master.get('company_id')
            module_id = master.get('module_id')
            
            # 1. REMOVE FILES
            for file_name in files_to_remove:
                duck_conn.execute("DELETE FROM master_data WHERE Source_File_Name = ?", (file_name,))
                logger.info(f"Removed {file_name} from master_data.")
                try:
                    from backend.database import add_notification
                    add_notification(company_id, module_id, 'info', f"File '{file_name}' was successfully removed from master data.", f"?folder={folder_id}")
                except Exception as ne:
                    pass
                
            # 2. ADD FILES
            if files_to_add:
                # Mark as processing
                for f in files_to_add:
                    set_file_sync_status(f['id'], 'in_processing')
                    
                all_new_data = []
                for f in files_to_add:
                    try:
                        file_format = f.get('format', '').upper()
                        file_path = f['file_path']
                        original_name = f['original_name']
                        
                        # Read the file
                        if file_format == 'CSV':
                            sheet_names = ['Sheet1']
                        else:
                            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                            sheet_names = wb.sheetnames
                            wb.close()
                            
                        if len(sheet_names) > 1:
                            raise Exception(f"Multiple sheets found ({len(sheet_names)} sheets). Only single-sheet files are allowed.")
                            
                        header_row = f.get('header_row', 1) or 1
                        header_idx = max(0, header_row - 1)
                        
                        if file_format == 'CSV':
                            df = pd.read_csv(file_path, header=header_idx)
                        else:
                            df = pd.read_excel(file_path, sheet_name=sheet_names[0], header=header_idx)
                            
                        df.columns = [str(col).strip() for col in df.columns]
                        actual_columns = df.columns.tolist()
                        
                        if is_all_columns:
                            selected_columns = actual_columns.copy()
                        else:
                            # Only require columns that are not formulas and not Source_File_Name
                            selected_columns = [c for c in user_columns if c not in formula_cols and c != 'Source_File_Name']
                            
                        missing_columns = [col for col in selected_columns if col not in actual_columns]
                        if missing_columns:
                            raise Exception(f"Column(s) not found: {', '.join(missing_columns)}")
                            
                        df = df[selected_columns]
                        df.insert(0, 'Source_File_Name', original_name)
                        
                        all_new_data.append((f['id'], df))
                        
                    except Exception as e:
                        logger.error(f"Failed to process file {f['original_name']} for sync: {e}")
                        set_file_sync_status(f['id'], 'rejected', str(e))
                        try:
                            from backend.database import add_notification
                            add_notification(company_id, module_id, 'error', f"File '{f['original_name']}' failed to sync: {str(e)}", f"?folder={folder_id}", user_id=f.get('uploaded_by'))
                        except Exception as ne:
                            logger.error(f"Failed to add notification: {ne}")

                        
                # Insert successful new data into DuckDB
                if all_new_data:
                    # To cleanly insert, we align schemas. 
                    # master_data might have formula columns that aren't in the raw df.
                    current_duckdb_cols = duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
                    
                    for file_id, df in all_new_data:
                        try:
                            # Add missing columns as NULL so schema matches master_data
                            for c in current_duckdb_cols:
                                if c not in df.columns:
                                    df[c] = None
                            
                            # Ensure column order perfectly matches
                            df = df[current_duckdb_cols]
                            
                            duck_conn.execute("INSERT INTO master_data SELECT * FROM df")
                            set_file_sync_status(file_id, 'synced', None)
                            try:
                                from backend.database import add_notification
                                add_notification(company_id, module_id, 'success', f"File '{f['original_name']}' was successfully merged.", f"?folder={folder_id}", user_id=f.get('uploaded_by'))
                            except Exception as ne:
                                pass
                        except Exception as e:
                            logger.error(f"Failed to INSERT file ID {file_id}: {e}")
                            set_file_sync_status(file_id, 'rejected', str(e))
                            try:
                                from backend.database import add_notification
                                add_notification(company_id, module_id, 'error', f"Failed to insert file '{f['original_name']}': {str(e)}", f"?folder={folder_id}", user_id=f.get('uploaded_by'))
                            except Exception as ne:
                                pass

            
            # 3. RE-APPLY FORMULAS
            # Even if we just appended, we need to calculate the formula values for the new rows.
            # Running UPDATE on the whole table in DuckDB is lightning fast, so we just run it on all rows to be safe.
            if files_to_add:
                reapply_formulas(duck_conn, folder_id, company_id, module_id)

            # 4. RE-APPLY ALL SAVED ACTIVITIES
            # Run the full apply_activities() engine so Formula, Find & Replace, Column Rename,
            # and Column Delete activities (stored in master_activities) survive incremental sync
            # (file add OR delete). Wrapped in try/except so a single bad activity doesn't break sync.
            if files_to_add or files_to_remove:
                try:
                    apply_activities(duck_conn, folder_id, company_id, module_id)
                except Exception as act_e:
                    logger.warning(f"apply_activities during incremental sync failed: {act_e}")
                
        finally:
            duck_conn.close()
            
    finally:
        conn.close()

def reapply_formulas(duck_conn, folder_id, company_id, module_id):
    """
    Reapplies all formulas to the master_data table.
    """
    formulas = get_master_formulas(folder_id)
    if not formulas:
        return
        
    current_cols = duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
    
    for f in formulas:
        try:
            ft = f.get('formula_type', '').upper()
            col_name = f.get('column_name', '')
            if not ft or not col_name:
                continue
                
            # If the column doesn't exist (shouldn't happen on incremental, but just in case)
            if col_name not in current_cols:
                duck_conn.execute(f"ALTER TABLE master_data ADD COLUMN IF NOT EXISTS \"{col_name}\" DOUBLE")
                
            if ft in ('SUMIF', 'COUNTIF'):
                pcol = f.get('primary_column')
                sec_file_id = f.get('secondary_file')
                sec_sheet = f.get('secondary_sheet')
                sec_match = f.get('secondary_match_column')
                sec_val = f.get('secondary_value_column')
                
                if not pcol or not sec_file_id or not sec_sheet or not sec_match:
                    continue
                if ft == 'SUMIF' and not sec_val:
                    continue
                    
                resolved = resolve_primary_file_for_formula(sec_file_id, company_id, module_id)
                if not resolved['success']:
                    continue
                    
                sec_path = resolved['path']
                if not os.path.exists(sec_path):
                    continue
                    
                is_csv = sec_path.lower().endswith('.csv')
                
                if ft == 'SUMIF':
                    if is_csv:
                        query = f'''
                            UPDATE master_data 
                            SET "{col_name}" = (
                                SELECT SUM(TRY_CAST(s."{sec_val}" AS DOUBLE))
                                FROM read_csv_auto('{sec_path}') AS s
                                WHERE CAST(s."{sec_match}" AS VARCHAR) = CAST(master_data."{pcol}" AS VARCHAR)
                            )
                        '''
                    else:
                        query = f'''
                            UPDATE master_data 
                            SET "{col_name}" = (
                                SELECT SUM(TRY_CAST(s."{sec_val}" AS DOUBLE))
                                FROM st_read('{sec_path}', layer='{sec_sheet}') AS s
                                WHERE CAST(s."{sec_match}" AS VARCHAR) = CAST(master_data."{pcol}" AS VARCHAR)
                            )
                        '''
                    duck_conn.execute(query)
                    
                elif ft == 'COUNTIF':
                    if is_csv:
                        query = f'''
                            UPDATE master_data 
                            SET "{col_name}" = (
                                SELECT COUNT(*)
                                FROM read_csv_auto('{sec_path}') AS s
                                WHERE CAST(s."{sec_match}" AS VARCHAR) = CAST(master_data."{pcol}" AS VARCHAR)
                            )
                        '''
                    else:
                        query = f'''
                            UPDATE master_data 
                            SET "{col_name}" = (
                                SELECT COUNT(*)
                                FROM st_read('{sec_path}', layer='{sec_sheet}') AS s
                                WHERE CAST(s."{sec_match}" AS VARCHAR) = CAST(master_data."{pcol}" AS VARCHAR)
                            )
                        '''
                    duck_conn.execute(query)
                    
            elif ft == 'VLOOKUP':
                pcol = f.get('primary_column')
                sec_file_id = f.get('secondary_file')
                sec_sheet = f.get('secondary_sheet')
                sec_match = f.get('secondary_match_column')
                sec_val = f.get('secondary_value_column')
                
                if not pcol or not sec_file_id or not sec_sheet or not sec_match or not sec_val:
                    continue
                    
                resolved = resolve_primary_file_for_formula(sec_file_id, company_id, module_id)
                if not resolved['success']:
                    continue
                    
                sec_path = resolved['path']
                if not os.path.exists(sec_path):
                    continue
                    
                is_csv = sec_path.lower().endswith('.csv')
                if is_csv:
                    query = f'''
                        UPDATE master_data 
                        SET "{col_name}" = (
                            SELECT ANY_VALUE(s."{sec_val}")
                            FROM read_csv_auto('{sec_path}') AS s
                            WHERE CAST(s."{sec_match}" AS VARCHAR) = CAST(master_data."{pcol}" AS VARCHAR)
                        )
                    '''
                else:
                    query = f'''
                        UPDATE master_data 
                        SET "{col_name}" = (
                            SELECT ANY_VALUE(s."{sec_val}")
                            FROM st_read('{sec_path}', layer='{sec_sheet}') AS s
                            WHERE CAST(s."{sec_match}" AS VARCHAR) = CAST(master_data."{pcol}" AS VARCHAR)
                        )
                    '''
                duck_conn.execute(query)
                
            elif ft == 'EXPRESSION':
                from backend.formula_engine import parse_formula
                expression = f.get('expression', '')
                if expression:
                    cols_list = duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
                    try:
                        sql_expr, _ = parse_formula(expression, cols_list)
                        duck_conn.execute(f'UPDATE master_data SET "{col_name}" = {sql_expr}')
                    except Exception as e:
                        logger.error(f"Failed to evaluate expression formula '{col_name}': {e}")
                        
        except Exception as e:
            logger.error(f"Error reapplying formula '{f.get('column_name')}': {e}")

def resolve_primary_file_for_formula(sec_file_id, company_id, module_id):
    """
    Resolves the physical path of a secondary file or master file.
    """
    try:
        if str(sec_file_id).startswith('master_'):
            folder_id = int(str(sec_file_id).replace('master_', ''))
            conn = get_db_connection()
            master = conn.execute("SELECT db_path FROM master_files WHERE folder_id = ?", (folder_id,)).fetchone()
            conn.close()
            if master:
                return {'success': True, 'path': master['db_path']}
            return {'success': False}
        
        conn = get_db_connection()
        file_rec = conn.execute("SELECT file_path FROM files WHERE id = ?", (int(sec_file_id),)).fetchone()
        conn.close()
        if file_rec:
            return {'success': True, 'path': file_rec['file_path']}
        return {'success': False}
    except Exception as e:
        logger.error(f"Error resolving primary file: {e}")
        return {'success': False}


# =============================================================================
# ACTIVITY WINDOW ENGINE
# =============================================================================
# Re-applies user-saved "Activity" steps (FORMULA_ADD, FIND_REPLACE, COLUMN_RENAME,
# COLUMN_DELETE, ROW_FILTER) to master_data every time the auto-sync engine runs.
# This is what makes the user's ETL steps survive across auto-sync cycles.
# =============================================================================

def _sql_escape(value: str) -> str:
    """Escape a string for safe inclusion inside a single-quoted SQL literal."""
    if value is None:
        return "''"
    return "'" + str(value).replace("'", "''") + "'"


def _safe_sql_ident(name: str) -> str:
    """Quote a DuckDB identifier safely. Raises if name is suspicious."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("identifier must be a non-empty string")
    bad = ['"', '\n', '\r', ';', '\0']
    for ch in bad:
        if ch in name:
            raise ValueError(f"identifier contains forbidden char: {ch!r}")
    return '"' + name.replace('"', '""') + '"'


def _column_exists(duck_conn, table: str, column: str) -> bool:
    try:
        rows = duck_conn.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name = ? AND column_name = ? LIMIT 1",
            (table.lower(), column)
        ).fetchall()
        return len(rows) > 0
    except Exception:
        try:
            cols = duck_conn.execute(f"SELECT * FROM {table} LIMIT 0").fetchdf().columns.tolist()
            return column in cols
        except Exception:
            return False


def _ensure_column(duck_conn, table: str, column: str, data_type: str = 'VARCHAR'):
    """Add column if it does not exist. data_type is bounded to a whitelist."""
    if _column_exists(duck_conn, table, column):
        return
    if data_type not in ('VARCHAR', 'DOUBLE', 'INTEGER', 'BIGINT', 'BOOLEAN', 'DATE', 'TIMESTAMP'):
        data_type = 'VARCHAR'
    duck_conn.execute(f"ALTER TABLE {table} ADD COLUMN {_safe_sql_ident(column)} {data_type}")


def _apply_formula_activity(duck_conn, act):
    """FORMULA_ADD: ensure the column exists, then UPDATE with parsed formula SQL."""
    payload = act.get('payload') or {}
    expression = payload.get('expression') or payload.get('sql') or ''
    col_name = act.get('target_column') or payload.get('output_column') or payload.get('column_name')
    if not col_name:
        raise ValueError("FORMULA_ADD missing target_column / output_column")
    if not expression:
        raise ValueError("FORMULA_ADD missing expression / sql")
    col_ident = _safe_sql_ident(col_name)
    _ensure_column(duck_conn, 'master_data', col_name, 'DOUBLE')
    try:
        duck_conn.execute(f"UPDATE master_data SET {col_ident} = ({expression})")
    except Exception:
        # If a plain SQL expression fails (e.g. legacy CSV) try TRY_CAST wrapping
        duck_conn.execute(f"UPDATE master_data SET {col_ident} = TRY_CAST(({expression}) AS DOUBLE)")


def _apply_formula_update_activity(duck_conn, act):
    """FORMULA_UPDATE: update an existing column with a new expression."""
    return _apply_formula_activity(duck_conn, act)


def _apply_find_replace_activity(duck_conn, act):
    """FIND_REPLACE: apply text replacement on one or more columns.
    payload: {find, replace, scope_columns, case_sensitive, match_type, regex}
    """
    payload = act.get('payload') or {}
    find_val = payload.get('find', '')
    replace_val = payload.get('replace', '')
    if not find_val:
        raise ValueError("FIND_REPLACE missing 'find' value")
    scope = payload.get('scope_columns') or []
    if not scope:
        cols = duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
        scope = [c for c in cols if c != 'Source_File_Name']
    case_sensitive = bool(payload.get('case_sensitive', False))
    regex = bool(payload.get('regex', False))
    match_type = (payload.get('match_type') or 'contains').lower()

    for col in scope:
        if not _column_exists(duck_conn, 'master_data', col):
            continue
        col_ident = _safe_sql_ident(col)
        if regex:
            flags = 'g' if case_sensitive else 'gi'
            expr = f"regexp_replace(CAST({col_ident} AS VARCHAR), {_sql_escape(find_val)}, {_sql_escape(replace_val)}, '{flags}')"
        else:
            if case_sensitive:
                if match_type == 'exact':
                    where_clause = f"CAST({col_ident} AS VARCHAR) = {_sql_escape(find_val)}"
                elif match_type == 'starts_with':
                    where_clause = f"CAST({col_ident} AS VARCHAR) LIKE {_sql_escape(find_val + '%')}"
                elif match_type == 'ends_with':
                    where_clause = f"CAST({col_ident} AS VARCHAR) LIKE {_sql_escape('%' + find_val)}"
                else:
                    where_clause = f"CAST({col_ident} AS VARCHAR) LIKE {_sql_escape('%' + find_val + '%')}"
                expr = f"REPLACE(CAST({col_ident} AS VARCHAR), {_sql_escape(find_val)}, {_sql_escape(replace_val)})"
                duck_conn.execute(f"UPDATE master_data SET {col_ident} = {expr} WHERE {where_clause}")
            else:
                # Case-insensitive: build the WHERE clause based on match_type
                if match_type == 'exact':
                    where_clause = f"LOWER(CAST({col_ident} AS VARCHAR)) = LOWER({_sql_escape(find_val)})"
                elif match_type == 'starts_with':
                    where_clause = f"LOWER(CAST({col_ident} AS VARCHAR)) LIKE LOWER({_sql_escape(find_val + '%')})"
                elif match_type == 'ends_with':
                    where_clause = f"LOWER(CAST({col_ident} AS VARCHAR)) LIKE LOWER({_sql_escape('%' + find_val)})"
                else:
                    # 'contains' (default) - substring match
                    where_clause = f"LOWER(CAST({col_ident} AS VARCHAR)) LIKE LOWER({_sql_escape('%' + find_val + '%')})"
                # Use regexp_replace with 'gi' flags (case-insensitive, global)
                expr = f"regexp_replace(CAST({col_ident} AS VARCHAR), {_sql_escape(find_val)}, {_sql_escape(replace_val)}, 'gi')"
                duck_conn.execute(f"UPDATE master_data SET {col_ident} = {expr} WHERE {where_clause}")


def _apply_rename_activity(duck_conn, act):
    """COLUMN_RENAME: rename an existing column."""
    payload = act.get('payload') or {}
    frm = payload.get('from') or payload.get('from_column') or act.get('target_column')
    to = payload.get('to') or payload.get('to_column')
    if not frm or not to:
        raise ValueError("COLUMN_RENAME requires 'from' and 'to'")
    if not _column_exists(duck_conn, 'master_data', frm):
        raise ValueError(f"Column '{frm}' does not exist")
    if _column_exists(duck_conn, 'master_data', to) and frm != to:
        raise ValueError(f"Column '{to}' already exists")
    cols = duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
    select_list = ', '.join(
        f'{_safe_sql_ident(c)} AS {_safe_sql_ident(to)}' if c == frm else _safe_sql_ident(c)
        for c in cols
    )
    duck_conn.execute(f"CREATE TABLE master_data_new AS SELECT {select_list} FROM master_data")
    duck_conn.execute("DROP TABLE master_data")
    duck_conn.execute("ALTER TABLE master_data_new RENAME TO master_data")


def _apply_delete_activity(duck_conn, act):
    """COLUMN_DELETE: drop a column."""
    payload = act.get('payload') or {}
    col = payload.get('column') or act.get('target_column')
    if not col:
        raise ValueError("COLUMN_DELETE missing 'column'")
    if not _column_exists(duck_conn, 'master_data', col):
        return  # already gone
    duck_conn.execute(f"ALTER TABLE master_data DROP COLUMN {_safe_sql_ident(col)}")


def _apply_filter_activity(duck_conn, act):
    """ROW_FILTER: create/replace a `master_data_filtered` VIEW from the conditions.

    This is intentionally a VIEW (not a destructive mutation): master_data is left
    untouched and downstream consumers that know about the filtered view can
    query `master_data_filtered`. Filter is re-applied on every auto-sync cycle.
    """
    payload = act.get('payload') or {}
    conds = payload.get('conditions') or []
    if not conds:
        raise ValueError("ROW_FILTER missing 'conditions'")
    logic = (payload.get('logic') or 'AND').upper()
    if logic not in ('AND', 'OR'):
        logic = 'AND'

    cols = duck_conn.execute("SELECT * FROM master_data LIMIT 0").fetchdf().columns.tolist()
    where_clauses = []
    for c in conds:
        col = c.get('column', '')
        if not col or col not in cols:
            continue
        op = (c.get('operator') or '').lower()
        val = c.get('value', '')
        vmin = c.get('value_min', '')
        vmax = c.get('value_max', '')
        col_ident = _safe_sql_ident(col)
        if op == 'equal_to':
            where_clauses.append(f"CAST({col_ident} AS VARCHAR) = {_sql_escape(str(val))}")
        elif op == 'not_equal_to':
            where_clauses.append(f"(CAST({col_ident} AS VARCHAR) != {_sql_escape(str(val))} OR {col_ident} IS NULL)")
        elif op == 'contains':
            where_clauses.append(f"CAST({col_ident} AS VARCHAR) LIKE {_sql_escape('%' + str(val) + '%')}")
        elif op == 'not_contains':
            where_clauses.append(f"(CAST({col_ident} AS VARCHAR) NOT LIKE {_sql_escape('%' + str(val) + '%')} OR {col_ident} IS NULL)")
        elif op == 'starts_with':
            where_clauses.append(f"CAST({col_ident} AS VARCHAR) LIKE {_sql_escape(str(val) + '%')}")
        elif op == 'ends_with':
            where_clauses.append(f"CAST({col_ident} AS VARCHAR) LIKE {_sql_escape('%' + str(val))}")
        elif op == 'greater_than':
            try:
                fv = float(val) if val not in (None, '') else 0
                where_clauses.append(f"TRY_CAST({col_ident} AS DOUBLE) > {_sql_escape(fv)}")
            except Exception:
                pass
        elif op == 'less_than':
            try:
                fv = float(val) if val not in (None, '') else 0
                where_clauses.append(f"TRY_CAST({col_ident} AS DOUBLE) < {_sql_escape(fv)}")
            except Exception:
                pass
        elif op == 'between':
            try:
                fmin = float(vmin) if vmin not in (None, '') else 0
                fmax = float(vmax) if vmax not in (None, '') else 0
                where_clauses.append(f"TRY_CAST({col_ident} AS DOUBLE) BETWEEN {_sql_escape(fmin)} AND {_sql_escape(fmax)}")
            except Exception:
                pass
        elif op == 'blank':
            where_clauses.append(f"({col_ident} IS NULL OR TRIM(CAST({col_ident} AS VARCHAR)) = '')")
        elif op == 'not_blank':
            where_clauses.append(f"({col_ident} IS NOT NULL AND TRIM(CAST({col_ident} AS VARCHAR)) != '')")

    joiner = ' AND ' if logic == 'AND' else ' OR '
    where_sql = joiner.join(where_clauses) if where_clauses else 'TRUE'

    duck_conn.execute("DROP VIEW IF EXISTS master_data_filtered")
    duck_conn.execute(f"CREATE VIEW master_data_filtered AS SELECT * FROM master_data WHERE {where_sql}")


def apply_activities(duck_conn, folder_id, company_id, module_id):
    """
    Re-apply all user-saved activity steps in order to the master_data table.
    Supports: FORMULA_ADD, FORMULA_UPDATE, FIND_REPLACE, COLUMN_RENAME, COLUMN_DELETE, ROW_FILTER.
    Updates `master_activities.validation_status` / `last_error` / `last_applied_at` as it goes.
    """
    from backend.database import list_master_activities, mark_activity_applied
    try:
        activities = list_master_activities(folder_id, company_id=company_id, module_id=module_id, enabled_only=True)
    except Exception as e:
        logger.error(f"apply_activities: failed to list activities: {e}")
        return
    activities.sort(key=lambda a: (a.get('step_order', 0), a.get('id', 0)))
    for act in activities:
        act_id = act.get('id')
        act_type = (act.get('activity_type') or '').upper()
        try:
            if act_type == 'FORMULA_ADD':
                _apply_formula_activity(duck_conn, act)
            elif act_type == 'FORMULA_UPDATE':
                _apply_formula_update_activity(duck_conn, act)
            elif act_type == 'FIND_REPLACE':
                _apply_find_replace_activity(duck_conn, act)
            elif act_type == 'COLUMN_RENAME':
                _apply_rename_activity(duck_conn, act)
            elif act_type == 'COLUMN_DELETE':
                _apply_delete_activity(duck_conn, act)
            elif act_type == 'ROW_FILTER':
                _apply_filter_activity(duck_conn, act)
            else:
                mark_activity_applied(act_id, 'warning', f"Unknown activity type: {act_type}")
                continue
            mark_activity_applied(act_id, 'ok', None)
        except Exception as e:
            logger.error(f"Activity {act_id} ({act_type}) failed: {e}")
            try:
                mark_activity_applied(act_id, 'error', str(e))
            except Exception:
                pass

