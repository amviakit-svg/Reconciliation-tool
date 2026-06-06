with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        row = conn.execute(
            "SELECT columns, concat_columns, sheet_name, header_row, updated_at FROM master_file_configs WHERE folder_id = ?",
            (folder_id,)
        ).fetchone()"""

replacement = """        row = conn.execute(
            "SELECT columns, concat_columns, sheet_name, header_row, updated_at FROM master_file_configs WHERE folder_id = ?",
            (folder_id,)
        ).fetchone()
        
        master_row = conn.execute("SELECT auto_sync FROM master_files WHERE folder_id = ?", (folder_id,)).fetchone()
        auto_sync = master_row[0] if master_row else 0
        conn.close()
        
        if row:
            logger.info(f"Loaded master config for folder {folder_id}: columns='{row[0]}'")
            # Format updated_at nicely
            updated_at = row[4]
            try:
                if updated_at:
                    dt = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
                    updated_at = dt.strftime('%d %b %Y, %I:%M %p')
            except Exception:
                pass
            return {
                "success": True,
                "config": {
                    "columns": row[0],
                    "concat_columns": row[1],
                    "sheet_name": row[2],
                    "header_row": row[3],
                    "updated_at": updated_at,
                    "auto_sync": auto_sync
                }
            }
            
        # Even if config row is missing, we might have an auto_sync setting in master_files
        if master_row:
            return {"success": True, "config": {"auto_sync": auto_sync}}
            
        logger.debug(f"No master config found for folder {folder_id}")
        return {"success": True, "config": None}
    except Exception as e:
        logger.error(f"Get master config error for folder {folder_id}: {e}")
        return get_error_response("db_connection")"""

content = content.replace(target, replacement)

with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py', 'w', encoding='utf-8') as f:
    f.write(content)
