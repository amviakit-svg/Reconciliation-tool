import sqlite3

conn = sqlite3.connect('data/metadata.db')
c = conn.cursor()

print('=== FILES TABLE ===')
c.execute('PRAGMA table_info(files)')
print('Columns:', [r[1] for r in c.fetchall()])

print('\nFiles (first 10):')
c.execute('SELECT id, name, folder_id, file_path, company_id, module_id FROM files LIMIT 10')
for row in c.fetchall():
    print(' ', row)

conn.close()