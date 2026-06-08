import sqlite3
import json

conn = sqlite3.connect('data/metadata.db')
conn.row_factory = sqlite3.Row

company = conn.execute('SELECT * FROM companies ORDER BY id DESC LIMIT 1').fetchone()
cid = company['id']
print(f'Latest Company: {cid} - {company["name"]}')

print('--- Master Files ---')
mfs = conn.execute(f'SELECT * FROM master_files WHERE company_id = {cid}').fetchall()
print(f'Count: {len(mfs)}')
for mf in mfs:
    print(dict(mf))

print('--- Rules ---')
rules = conn.execute(f'SELECT * FROM rules WHERE company_id = {cid}').fetchall()
print(f'Count: {len(rules)}')
for r in rules:
    print(dict(r))
