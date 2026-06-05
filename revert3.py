with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()

# The function body is now:
#   ...try/except metadata at 8/12-space indent (ends at line 2737)
#   blank (2738)
#   '            except HTTPException:' at 12-space (WRONG, should be 4-space)
#   '        raise' (line 2740)
#   '    except Exception as e:' (line 2741)
#   '        logger.error...' (2742)
#   '        raise HTTPException...' (2743)

# Also missing the `return {...}` block entirely (which got deleted).

# Fix: insert the missing return block at 4-space indent, then re-indent the
# except chain to 4-space.

# Step 1: Replace the broken section (lines 2739-2743) with the correct code
# at 4-space indent.

# Read lines 2739-2743 (indices 2738-2742)
broken = lines[2738:2743]
# lstripped content:
for i, l in enumerate(broken):
    print(f'  broken[{i}]: {l!r}')

# Compose the correct replacement
correct = [
    '        return {\n',
    '            "success": True,\n',
    '            "message": f"Column \'{column_name}\' deleted successfully",\n',
    '            "columns": updated_cols\n',
    '        }\n',
    '    except HTTPException:\n',
    '        raise\n',
    '    except Exception as e:\n',
    '        logger.error(f"Delete column error: {e}")\n',
    '        raise HTTPException(status_code=500, detail=str(e))\n',
]

# Replace lines 2739-2743 (0-indexed 2738-2742) with the correct block
new_lines = lines[:2738] + correct + lines[2743:]
print(f'\nOriginal: {len(lines)} lines')
print(f'New: {len(new_lines)} lines')

with open('backend/main.py','w',encoding='utf-8') as f:
    f.writelines(new_lines)
print('saved')