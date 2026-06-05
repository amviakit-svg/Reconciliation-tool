"""
Completely remove the broken AUTO-CAPTURE: COLUMN_DELETE block (lines 2739-2758)
and clean up the file to restore the original delete_master_column function.

Strategy: just delete lines 2739 through 2758 (inclusive).
"""
with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()

# Delete lines 2739-2758 (1-indexed), which is 0-indexed 2738-2757
# This removes the broken block
# The remaining "    except HTTPException:" is at line 2759, which is what we want.
print(f'Line 2739: {lines[2738].rstrip()!r}')
print(f'Line 2758: {lines[2757].rstrip()!r}')
print(f'Line 2759: {lines[2758].rstrip()!r}')

# Delete from line 2739 (1-indexed) which is index 2738, up to and including 2758
del lines[2738:2758]
# Now the file should have:
# ... line 2738 (empty line after logger.warning)
# ... line 2739 (the original 'return {' which was at line 2755 before)

with open('backend/main.py','w',encoding='utf-8') as f:
    f.writelines(lines)
print('saved')