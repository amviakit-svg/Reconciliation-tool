"""
Reverts the broken injection: removes both AUTO-CAPTURE blocks from
apply_master_formula (lines 2615-2657) and re-injects them at the correct
positions with correct 8-space indentation.
"""
import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Remove the broken block (from # === AUTO-CAPTURE: FORMULA_ADD === through
# the empty line before "        # Persist formula for auto-reapply on future merges")
# But ONLY the first occurrence - the FORMULA_EXPRESSION block was meant for the
# apply_formula_expression function, not here.

# Step 1: Remove the first "AUTO-CAPTURE: FORMULA_EXPRESSION" block (wrong place)
# It was injected inside apply_master_formula at indent 4 but the function is below
# Find both blocks and remove FORMULA_EXPRESSION (the misplacement) and the FORMULA_ADD
# that's also misplaced (4-space indent instead of 8).

# Simpler: just remove the entire broken section by finding the markers and the next persist comment
broken_start_marker = "    # === AUTO-CAPTURE: FORMULA_ADD ==="
# The two broken blocks together end right before the next "        # Persist formula"
broken_end_anchor = "        # Persist formula for auto-reapply on future merges"

# Find first occurrence of the start marker and cut everything up to (but not including)
# the next "        # Persist formula" comment
start_idx = src.find(broken_start_marker)
end_idx = src.find(broken_end_anchor, start_idx) if start_idx != -1 else -1
if start_idx != -1 and end_idx != -1:
    # Remove the broken blocks (from start marker up to the persist comment)
    removed = src[start_idx:end_idx]
    src = src[:start_idx] + src[end_idx:]
    print(f'Removed broken blocks: {len(removed)} chars')
else:
    print(f'Could not find boundaries: start={start_idx}, end={end_idx}')

# Verify
print('After cleanup FORMULA_ADD:', 'AUTO-CAPTURE: FORMULA_ADD' in src)
print('After cleanup FORMULA_EXPRESSION:', 'AUTO-CAPTURE: FORMULA_EXPRESSION' in src)
print('After cleanup FIND_REPLACE:', 'AUTO-CAPTURE: FIND_REPLACE' in src)
print('After cleanup COLUMN_DELETE:', 'AUTO-CAPTURE: COLUMN_DELETE' in src)
print('Persist formula blocks:', len(re.findall(r'        # Persist formula for auto-reapply on future merges', src)))

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('saved')