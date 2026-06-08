import os
import glob
import duckdb
import sqlite3

def truncate_duckdb_files():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads', 'Amviak Consulting')
    
    if not os.path.exists(base_dir):
        print(f"Directory not found: {base_dir}")
        return
        
    duckdb_files = glob.glob(os.path.join(base_dir, '**', '*.duckdb'), recursive=True)
    
    print(f"Found {len(duckdb_files)} DuckDB files to truncate.")
    
    for db_path in duckdb_files:
        try:
            print(f"Processing {os.path.basename(db_path)}...")
            conn = duckdb.connect(db_path)
            
            # Check if master_data table exists
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            
            if 'master_data' in table_names:
                # Get current row count
                count = conn.execute("SELECT COUNT(*) FROM master_data").fetchone()[0]
                
                if count > 10:
                    print(f"  - Truncating from {count} rows down to 10...")
                    # Truncate
                    conn.execute("CREATE TABLE temp_table AS SELECT * FROM master_data LIMIT 10;")
                    conn.execute("DROP TABLE master_data;")
                    conn.execute("ALTER TABLE temp_table RENAME TO master_data;")
                    # Reclaim disk space
                    conn.execute("VACUUM;")
                    print("  - Truncation and VACUUM successful.")
                else:
                    print(f"  - Skipped. File only has {count} rows.")
            else:
                print("  - Skipped. No 'master_data' table found.")
                
            conn.close()
            
        except Exception as e:
            print(f"Error processing {db_path}: {e}")

if __name__ == "__main__":
    truncate_duckdb_files()
