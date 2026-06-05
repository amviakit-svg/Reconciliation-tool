import re
with open('backend/main.py','r',encoding='utf-8') as f:
    src = f.read()
print('Persist formula blocks:', len(re.findall(r'        # Persist formula for auto-reapply on future merges', src)))
print('FORMULA_ADD markers:', src.count('AUTO-CAPTURE: FORMULA_ADD'))
print('FORMULA_EXPRESSION markers:', src.count('AUTO-CAPTURE: FORMULA_EXPRESSION'))
print('FIND_REPLACE markers:', src.count('AUTO-CAPTURE: FIND_REPLACE'))
print('COLUMN_DELETE markers:', src.count('AUTO-CAPTURE: COLUMN_DELETE'))
for m in re.finditer(r'AUTO-CAPTURE: \w+', src):
    print(' -', m.group(), 'at', m.start())