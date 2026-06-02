
with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\auto_sync.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the import from the top
text = text.replace('from backend.main import get_physical_storage_path, MASTER_DIR, resolve_primary_file_for_formula\n', '')
text = text.replace('from backend.main import get_physical_storage_path, MASTER_DIR, resolve_primary_file_for_formula', '')

# We need to import them inside the functions that use them.
# 'get_physical_storage_path' and 'MASTER_DIR' might be used in run_incremental_sync
# 'resolve_primary_file_for_formula' might be used in reapply_formulas

target_incremental = '''async def run_incremental_sync(folder_id: int):
    # 1. Fetch Master config'''
replacement_incremental = '''async def run_incremental_sync(folder_id: int):
    from backend.main import get_physical_storage_path, MASTER_DIR
    # 1. Fetch Master config'''
text = text.replace(target_incremental, replacement_incremental)

target_reapply = '''def reapply_formulas(folder_id: int, conn: duckdb.DuckDBPyConnection, company_id: int, module_id: int):
    logger.info(f"Reapplying formulas for folder {folder_id}")'''
replacement_reapply = '''def reapply_formulas(folder_id: int, conn: duckdb.DuckDBPyConnection, company_id: int, module_id: int):
    from backend.main import resolve_primary_file_for_formula
    logger.info(f"Reapplying formulas for folder {folder_id}")'''
text = text.replace(target_reapply, replacement_reapply)

with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\auto_sync.py', 'w', encoding='utf-8') as f:
    f.write(text)
