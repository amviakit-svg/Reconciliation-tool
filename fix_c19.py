import sqlite3
import duckdb

conn = sqlite3.connect('data/metadata.db')
conn.row_factory = sqlite3.Row

# Get company 19 files
c19_files = conn.execute('SELECT * FROM master_files WHERE company_id = 19').fetchall()

# Find the matching template files. Usually they match by module_id and sheet_name and columns.
c2_files = conn.execute('SELECT * FROM master_files WHERE company_id = 2').fetchall()

for c19 in c19_files:
    for c2 in c2_files:
        if c19['module_id'] == c2['module_id'] and c19['sheet_name'] == c2['sheet_name'] and c19['columns'] == c2['columns']:
            print(f'Matching {c19["db_path"]} with {c2["db_path"]}')
            
            # fix duckdb
            try:
                new_con = duckdb.connect(c19['db_path'])
                new_con.execute(f"ATTACH '{c2['db_path']}' AS old_db (READ_ONLY)")
                new_con.execute('CREATE TABLE master_data AS SELECT * FROM old_db.main.master_data LIMIT 10')
                new_con.execute('DETACH old_db')
                new_con.close()
                print('Fixed!')
            except Exception as e:
                print('Error:', e)
            break
