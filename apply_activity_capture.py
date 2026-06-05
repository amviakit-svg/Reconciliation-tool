"""
Auto-capture patcher: injects create_activity_from_action() calls into the
4 key apply endpoints (formula, formula-expression, find-replace, delete-column)
in backend/main.py so that every user action is silently persisted as an
Activity step.

Strategy: parse main.py, find the function bodies, insert a single small
auto-capture call before each return statement. Idempotent — re-running this
patcher is safe (checks for a marker comment before inserting).
"""
import os
import re

MAIN_PY = os.path.join('backend', 'main.py')

with open(MAIN_PY, 'r', encoding='utf-8') as f:
    src = f.read()

orig = src

# ------------------ 1. apply_master_formula ------------------
# After "success": True return for non-SUMIF path, capture FORMULA_ADD.
# Inject right BEFORE the existing return that contains formula_type.

MARKER_FORMULA = "    # === AUTO-CAPTURE: FORMULA_ADD ==="

formula_capture = """    # === AUTO-CAPTURE: FORMULA_ADD ===
    try:
        _act_payload = {
            'expression': '=' + ','.join(source_columns.split(',')) if formula_type in ('SUM','SUBTRACT','MULTIPLY','DIVIDE','PERCENTAGE','CONCAT','ABS') else '',
            'output_column': column_name,
            'data_type': 'DOUBLE',
            'formula_type': formula_type,
            'source_columns': [c.strip() for c in source_columns.split(',') if c.strip()] if source_columns else [],
            'constant_value': constant_value,
            'primary_column': primary_column,
            'secondary_file': secondary_file,
            'secondary_sheet': secondary_sheet,
            'secondary_match_column': secondary_match_column,
            'secondary_value_column': secondary_value_column,
        }
        _create_activity_from_action(
            folder_id=folder_id,
            action_type='FORMULA_ADD',
            payload=_act_payload,
            target_column=column_name,
            company_id=cid if current_user else None,
            module_id=mid if current_user else None,
            master_file_id=master.get('id'),
            user_id=current_user.get('user_id') if current_user else None,
        )
    except Exception as _e:
        logger.warning(f"Auto-capture FORMULA_ADD failed: {_e}")
"""

# Find a unique insertion anchor: right after the persist-formulas block in apply_master_formula
# Use the comment "Persist formula for auto-reapply on future merges" — appears in regular-formula path
anchor_formula = "        # Persist formula for auto-reapply on future merges"
if MARKER_FORMULA in src:
    print("FORMULA: marker already present, skipping")
else:
    # Find the FIRST occurrence of the persist-formulas block (in the regular-formula path)
    pattern = re.compile(
        r"(        # Persist formula for auto-reapply on future merges\n"
        r"        try:\n"
        r"            existing_formulas = get_master_formulas\(folder_id\)\n.*?"
        r"        except Exception as e:\n"
        r"            logger\.warning\(f\"Failed to persist formula: \{e\}\"\)\n)"
    )
    m = pattern.search(src)
    if m:
        # Insert the capture block BEFORE this persist block
        new_block = formula_capture + "\n" + m.group(1)
        src = src[:m.start()] + new_block + src[m.end():]
        print("FORMULA: injected auto-capture")
    else:
        print("FORMULA: pattern not found, will need manual injection")

# ------------------ 2. apply_formula_expression ------------------
# Inject before the persist-formulas try block in this function
MARKER_EXPR = "    # === AUTO-CAPTURE: FORMULA_EXPRESSION ==="
expr_capture = """    # === AUTO-CAPTURE: FORMULA_EXPRESSION ===
    try:
        _act_payload = {
            'expression': expression,
            'output_column': column_name,
            'data_type': 'DOUBLE',
            'formula_type': 'EXPRESSION',
            'source_columns': referenced_cols,
        }
        _create_activity_from_action(
            folder_id=folder_id,
            action_type='FORMULA_ADD',
            payload=_act_payload,
            target_column=column_name,
            company_id=cid if current_user else None,
            module_id=mid if current_user else None,
            master_file_id=master.get('id'),
            user_id=current_user.get('user_id') if current_user else None,
        )
    except Exception as _e:
        logger.warning(f"Auto-capture FORMULA_EXPRESSION failed: {_e}")
"""

if MARKER_EXPR in src:
    print("EXPRESSION: marker already present, skipping")
else:
    # Find the persist-formulas block in apply_formula_expression
    pattern = re.compile(
        r"(        # Persist formula for auto-reapply on future merges\n"
        r"        try:\n"
        r"            existing_formulas = get_master_formulas\(folder_id\)\n.*?"
        r"            update_master_formulas\(folder_id, existing_formulas\)\n"
        r"        except Exception as e:\n"
        r"            logger\.warning\(f\"Failed to persist formula: \{e\}\"\)\n)"
    )
    m = pattern.search(src)
    if m:
        new_block = expr_capture + "\n" + m.group(1)
        src = src[:m.start()] + new_block + src[m.end():]
        print("EXPRESSION: injected auto-capture")
    else:
        print("EXPRESSION: pattern not found")

# ------------------ 3. find_replace_master ------------------
# Inject right after the columns_modified loop
MARKER_FR = "    # === AUTO-CAPTURE: FIND_REPLACE ==="
fr_capture = """    # === AUTO-CAPTURE: FIND_REPLACE ===
    try:
        cid_fr, mid_fr = _get_context(current_user)
        _fr_payload = {
            'find': find_text,
            'replace': replace_text,
            'scope_columns': target_cols,
            'case_sensitive': is_case_sensitive,
            'regex': False,
            'match_whole_cell': False,
        }
        _create_activity_from_action(
            folder_id=folder_id,
            action_type='FIND_REPLACE',
            payload=_fr_payload,
            target_column=target_cols[0] if target_cols else None,
            company_id=cid_fr,
            module_id=mid_fr,
            master_file_id=master.get('id'),
            user_id=current_user.get('user_id') if current_user else None,
        )
    except Exception as _e:
        logger.warning(f"Auto-capture FIND_REPLACE failed: {_e}")
"""

if MARKER_FR in src:
    print("FIND_REPLACE: marker already present, skipping")
else:
    # Find the verb = "would replace" / "replaced" summary line, inject before the return
    pattern = re.compile(
        r"        verb = \"would replace\" if is_dry_run else \"replaced\"\n"
        r"        summary = f\"\{verb\} \{total_rows_affected\} occurrence\(s\) across \{len\(columns_modified\)\} column\(s\)\"\n"
    )
    m = pattern.search(src)
    if m:
        new_block = fr_capture + "\n" + m.group(0)
        src = src[:m.start()] + new_block + src[m.end():]
        print("FIND_REPLACE: injected auto-capture")
    else:
        print("FIND_REPLACE: pattern not found")

# ------------------ 4. delete_master_column ------------------
# Replace the legacy "remove from persisted formulas" with "create COLUMN_DELETE activity"
MARKER_DEL = "    # === AUTO-CAPTURE: COLUMN_DELETE ==="
del_capture = """    # === AUTO-CAPTURE: COLUMN_DELETE ===
    try:
        cid_del, mid_del = _get_context(current_user)
        _create_activity_from_action(
            folder_id=folder_id,
            action_type='COLUMN_DELETE',
            payload={'column': column_name},
            target_column=column_name,
            company_id=cid_del,
            module_id=mid_del,
            master_file_id=master.get('id'),
            user_id=current_user.get('user_id') if current_user else None,
        )
    except Exception as _e:
        logger.warning(f"Auto-capture COLUMN_DELETE failed: {_e}")
"""

if MARKER_DEL in src:
    print("COLUMN_DELETE: marker already present, skipping")
else:
    # Find the legacy "Remove from persisted formulas if present" try block and replace
    pattern = re.compile(
        r"        # Remove from persisted formulas if present\n"
        r"        try:\n"
        r"            existing_formulas = get_master_formulas\(folder_id\)\n"
        r"            new_formulas = \[f for f in existing_formulas if f\.get\('column_name'\) != column_name\]\n"
        r"            if len\(new_formulas\) != len\(existing_formulas\):\n"
        r"                update_master_formulas\(folder_id, new_formulas\)\n"
        r"                logger\.info\(f\"Removed formula for deleted column '\{column_name\}' from persisted formulas\"\)\n"
        r"        except Exception as e:\n"
        r"            logger\.warning\(f\"Failed to update formulas after column delete: \{e\}\"\)\n"
    )
    m = pattern.search(src)
    if m:
        # Replace the entire block with our new COLUMN_DELETE activity capture
        new_block = del_capture
        src = src[:m.start()] + new_block + src[m.end():]
        print("COLUMN_DELETE: injected auto-capture (replaced legacy formula removal)")
    else:
        print("COLUMN_DELETE: pattern not found")

# Save only if changed
if src != orig:
    with open(MAIN_PY, 'w', encoding='utf-8') as f:
        f.write(src)
    print(f"\nPatched {MAIN_PY}: {len(orig)} -> {len(src)} bytes")
else:
    print(f"\nNo changes to {MAIN_PY}")