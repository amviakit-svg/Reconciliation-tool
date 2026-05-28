import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2070, 2100):
    if 'header_row = file_record[\'header_row\']' in lines[i]:
        # Unindent it by 4 spaces
        lines[i] = lines[i].replace('                        header_row', '                    header_row')
        break

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
