with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()

# Lines 2739-2759 (0-indexed 2738-2758): the COLUMN_DELETE block at 4-space indent
# We need to re-indent those 21 lines with 8 spaces
start = 2738  # line containing '    # === AUTO-CAPTURE: COLUMN_DELETE ==='
# Find the end: the line that says "    except HTTPException:" at 4-space indent
end = None
for i in range(start + 1, min(len(lines), start + 30)):
    if lines[i].lstrip().startswith('except HTTPException:') and not lines[i].startswith('        '):
        end = i
        break

print(f'Block from line {start+1} to {end+1} (count: {end-start+1})')
if end is None:
    print('Could not find end anchor')
else:
    for i in range(start, end):
        if lines[i].startswith('    ') and not lines[i].startswith('     '):
            lines[i] = '    ' + lines[i]
    print('Re-indented with 4 more spaces')

with open('backend/main.py','w',encoding='utf-8') as f:
    f.writelines(lines)
print('saved')