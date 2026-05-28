import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2070, 2100):
    if 'SELECT file_path, format FROM files WHERE id = ?' in lines[i]:
        lines[i] = lines[i].replace('SELECT file_path, format FROM', 'SELECT file_path, format, header_row FROM')
    
    if 'sec_df = pd.read_csv(file_record[\'file_path\'])' in lines[i]:
        indent = lines[i][:lines[i].find('sec_df')]
        lines.insert(i, indent + "header_row = file_record['header_row'] if ('header_row' in file_record.keys() and file_record['header_row']) else 1\n")
        lines[i+1] = lines[i+1].replace("pd.read_csv(file_record['file_path'])", "pd.read_csv(file_record['file_path'], header=header_row-1)")
        lines[i+3] = lines[i+3].replace("pd.read_excel(file_record['file_path'], sheet_name=secondary_sheet)", "pd.read_excel(file_record['file_path'], sheet_name=secondary_sheet, header=header_row-1)")
        break

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
