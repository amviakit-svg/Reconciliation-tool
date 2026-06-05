"""
Revert the broken COLUMN_DELETE injection. Simply delete the entire auto-capture
block in the delete_master_column function. The column delete behavior
returns to its original (correct) state where it just drops the column
without creating an activity. We'll re-implement this properly in a
separate endpoint later.
"""
with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()

# Find the broken block
start = None
for i, line in enumerate(lines):
    if 'AUTO-CAPTURE: COLUMN_DELETE' in line:
        start = i
        break

if start is None:
    print('COLUMN_DELETE marker not found, nothing to revert')
else:
    # Find the end: scan forward until we see the line "    except HTTPException:"
    # which is at 4-space indent and signals the end of the broken block
    end = None
    for j in range(start, min(len(lines), start + 40)):
        if lines[j].lstrip().startswith('except HTTPException:') and not lines[j].startswith(' ' * 8):
            end = j
            break

    if end is None:
        print('Could not find end anchor')
    else:
        # Delete lines start through end-1
        del lines[start:end]
        print(f'Reverted COLUMN_DELETE block (removed lines {start+1} to {end})')

with open('backend/main.py','w',encoding='utf-8') as f:
    f.writelines(lines)
print('saved')