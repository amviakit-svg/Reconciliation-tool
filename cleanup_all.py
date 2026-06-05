"""
Final cleanup: completely remove all broken auto-capture injections from
backend/main.py. We'll re-implement auto-capture in a clean, separate
endpoint later (not yet done in this session).
"""
with open('backend/main.py','r',encoding='utf-8') as f:
    src = f.read()

orig = src

# Remove the FORMULA_ADD block (from # marker to before # Persist comment)
fm_start = src.find('        # === AUTO-CAPTURE: FORMULA_ADD ===')
if fm_start == -1:
    print('FORMULA_ADD: not found')
else:
    fm_end = src.find('        # Persist formula for auto-reapply on future merges', fm_start)
    if fm_end != -1:
        removed = src[fm_start:fm_end]
        src = src[:fm_start] + src[fm_end:]
        print(f'FORMULA_ADD: removed {len(removed)} chars')

# Remove FORMULA_EXPRESSION block
fe_start = src.find('        # === AUTO-CAPTURE: FORMULA_EXPRESSION ===')
if fe_start == -1:
    print('FORMULA_EXPRESSION: not found')
else:
    fe_end = src.find('        # Persist formula for auto-reapply on future merges', fe_start)
    if fe_end != -1:
        removed = src[fe_start:fe_end]
        src = src[:fe_start] + src[fe_end:]
        print(f'FORMULA_EXPRESSION: removed {len(removed)} chars')

# Remove FIND_REPLACE block
fr_start = src.find('    # === AUTO-CAPTURE: FIND_REPLACE ===')
if fr_start == -1:
    print('FIND_REPLACE: not found')
else:
    fr_end = src.find('    except HTTPException:', fr_start)
    if fr_end == -1:
        # try the verb = "would replace" line as anchor
        fr_end = src.find('        verb = "would replace"', fr_start)
    if fr_end != -1:
        # walk back to find start of the function-block indentation (4 spaces)
        # the marker was injected just before verb line
        # so just remove the marker + everything up to (not including) verb
        # Actually simpler: keep the verb line, remove just the marker+block before it
        # Find the actual start of the auto-capture block (the marker line)
        # The structure is:
        #   '    # === AUTO-CAPTURE: FIND_REPLACE ===\n'
        #   '    try:\n'
        #   '        cid_fr, mid_fr = ...\n'
        #   ... (about 22 lines)
        #   '        verb = "would replace"...\n'
        # We want to keep the verb line.
        # The "end" we found is the verb line. Remove from marker up to verb.
        removed = src[fr_start:fr_end]
        src = src[:fr_start] + src[fr_end:]
        print(f'FIND_REPLACE: removed {len(removed)} chars')

# Verify and save
print()
print('After cleanup:')
print('  FORMULA_ADD present:', 'AUTO-CAPTURE: FORMULA_ADD' in src)
print('  FORMULA_EXPRESSION present:', 'AUTO-CAPTURE: FORMULA_EXPRESSION' in src)
print('  FIND_REPLACE present:', 'AUTO-CAPTURE: FIND_REPLACE' in src)
print('  COLUMN_DELETE present:', 'AUTO-CAPTURE: COLUMN_DELETE' in src)

if src != orig:
    with open('backend/main.py','w',encoding='utf-8') as f:
        f.write(src)
    print(f'\nPatched backend/main.py: {len(orig)} -> {len(src)} bytes')
else:
    print('No changes made')