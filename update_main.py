import os

file_path = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = '''def write_pivot_to_worksheet_fast(ws, pivot_df, start_row=1):
    """
    Vectorized pivot table writing to Excel worksheet.
    Professional formatting with Grand Total highlighting and number formatting.
    Ensures Grand Total row is always at the bottom with special formatting.
    """
    from openpyxl.utils.dataframe import dataframe_to_rows'''

replacement = '''def write_pivot_to_worksheet_fast(ws, pivot_df, start_row=1):
    """
    Vectorized pivot table writing to Excel worksheet.
    Professional formatting with Grand Total highlighting and number formatting.
    Ensures Grand Total row is always at the bottom with special formatting.
    """
    from openpyxl.utils.dataframe import dataframe_to_rows
    
    # Reset index to convert row fields from index to regular columns
    if not pivot_df.index.names == [None]:
        pivot_df = pivot_df.reset_index()'''

new_content = content.replace(target, replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("backend/main.py updated successfully.")
