import re

with open('patch_db.py', 'r', encoding='utf-8') as f:
    patch_code = f.read()

# Extract the new_func string
match = re.search(r'new_func = \"\"\"(.*?)\"\"\"', patch_code, re.DOTALL)
if not match:
    print('Failed to extract')
    exit(1)

func_code = match.group(1)

with open('backend/database.py', 'a', encoding='utf-8') as f:
    f.write('\n\n')
    f.write(func_code)
    
    # Also append set_module_template
    f.write('''
def set_module_template(module_id: int, template_company_id: int):
    conn = get_db_connection()
    conn.execute('UPDATE modules SET template_company_id = ? WHERE id = ?', (template_company_id, module_id))
    conn.commit()
    conn.close()
''')

print('Successfully appended functions to database.py')
