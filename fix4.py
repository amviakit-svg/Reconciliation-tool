with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()

# Fix the over-indented COLUMN_DELETE block: all lines from 2738 to 2760 need to
# be at exactly 4 less space than they currently are (since I added 4 too many).
# The current state has everything at 8 spaces; the body inside try: should be at 12.

start = 2738  # '        # === AUTO-CAPTURE: COLUMN_DELETE ==='
end = 2760    # up to (but not including) the '    except HTTPException:' line at 4-space indent

for i in range(start, end + 1):
    if lines[i].startswith('            '):  # 12 spaces or more
        # Demote by 4 spaces
        lines[i] = lines[i][4:]
    elif lines[i].startswith('        '):  # 8 spaces
        # Demote by 4 spaces
        lines[i] = lines[i][4:]

# Now re-indent: # marker at 8, try: at 8, body at 12, except: at 8
# Re-add the proper indent (the lines are now bare)
# Add 8 spaces to the marker and try line, 12 to body lines
def re_indent_line(idx, spaces):
    if lines[idx].strip() == '':
        return
    lines[idx] = ' ' * spaces + lines[idx].lstrip()

# After the re-base, the # marker should be at 8, try: at 8, body at 12
# But our current state has all of them at varying levels. Simplest: re-do it all properly.
# Start with stripping all the existing indentation, then re-add.

for i in range(start, end + 1):
    lines[i] = lines[i].lstrip()  # Strip all indentation

# Now add proper indentation:
# Lines 2738-2739: # comment + blank
# Line 2739: 'try:' at 8
# Lines 2740-2751: body at 12
# Line 2752: 'except' at 8
# Line 2753: logger.warning at 12
# Line 2754: blank
# Line 2755: 'return {' at 8
# Lines 2756-2759: dict content at 12

re_indent_line(start, 8)  # comment
re_indent_line(start + 1, 8)  # try:
for i in range(start + 2, start + 14):
    re_indent_line(i, 12)
re_indent_line(start + 14, 8)  # except Exception as _e:
re_indent_line(start + 15, 12)  # logger.warning
# blank line skipped
re_indent_line(start + 17, 8)  # return {
for i in range(start + 18, end + 1):
    re_indent_line(i, 12)

with open('backend/main.py','w',encoding='utf-8') as f:
    f.writelines(lines)
print('saved')