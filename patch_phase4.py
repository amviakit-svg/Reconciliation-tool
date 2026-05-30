import re
import sys

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Map 'Primary_Value' in Phase 4
    old_alias_map = '''                    # Build lookup: generic name → actual column name in primary_df
                    col_alias_map = {}
                    if primary_key_col != 'Order ID' and primary_key_col in primary_df.columns:
                        col_alias_map['Order ID'] = primary_key_col'''
    new_alias_map = '''                    # Build lookup: generic name → actual column name in primary_df
                    col_alias_map = {}
                    if primary_key_col != 'Order ID' and primary_key_col in primary_df.columns:
                        col_alias_map['Order ID'] = primary_key_col
                        col_alias_map['Primary_Value'] = primary_key_col
                    elif primary_key_col == 'Order ID':
                        col_alias_map['Primary_Value'] = 'Order ID'
'''

    if old_alias_map in content:
        content = content.replace(old_alias_map, new_alias_map)
        print("Patched Phase 4 alias map.")
    else:
        print("Failed to patch Phase 4 alias map.")

    # Fix 2: Track 'Summary' in sheets_data
    old_summary_ws = '''            # Write shared summaries to a single "Summary" sheet
            if shared_summaries:
                summary_ws = writer.book.create_sheet('Summary')'''
    new_summary_ws = '''            # Write shared summaries to a single "Summary" sheet
            if shared_summaries:
                summary_ws = writer.book.create_sheet('Summary')
                sheets_data['Summary'] = sum(len(sd['data']) for sd in shared_summaries.values())'''
                
    if old_summary_ws in content:
        content = content.replace(old_summary_ws, new_summary_ws)
        print("Patched sheets_data tracking.")
    else:
        print("Failed to patch sheets_data tracking.")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file()
