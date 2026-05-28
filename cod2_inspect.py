import pandas as pd
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'metadata.db')

conn = sqlite3.connect(DB_PATH)
file18 = conn.execute('SELECT file_path, original_name, format FROM files WHERE id = 18').fetchone()
conn.close()

if not file18:
    print("File 18 not found!")
    exit()

path = file18[0]
print(f"File: {file18[1]}")
print(f"Format: {file18[2]}")
print(f"Path: {path}")
print(f"Exists: {os.path.exists(path)}")
print()

if not os.path.exists(path):
    print("File does not exist!")
    exit()

# List sheets
try:
    xl = pd.ExcelFile(path)
    print(f"Sheets: {xl.sheet_names}")
    print()
    
    # Read COD 2 sheet - first few rows to see structure
    df = pd.read_excel(path, sheet_name='COD 2', header=None, nrows=5)
    print("First 5 rows (no header):")
    print(df)
    print()
    
    # Now read with header=0 to see what pandas detects
    df_header = pd.read_excel(path, sheet_name='COD 2', header=0, nrows=5)
    print("First 5 rows with header=0:")
    print(df_header)
    print()
    print(f"Columns detected: {df_header.columns.tolist()}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()