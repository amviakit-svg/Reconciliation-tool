with open('backend/main.py','r',encoding='utf-8') as f:
    src = f.read()

formula_add = '''    # === AUTO-CAPTURE: FORMULA_ADD ===
    try:
        _act_payload = {
            'expression': ','.join([c.strip() for c in source_columns.split(',') if c.strip()]),
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
            folder_id=folder_id, action_type='FORMULA_ADD', payload=_act_payload,
            target_column=column_name,
            company_id=cid if current_user else None, module_id=mid if current_user else None,
            master_file_id=master.get('id'),
            user_id=current_user.get('user_id') if current_user else None,
        )
    except Exception as _e:
        logger.warning(f'Auto-capture FORMULA_ADD failed: {_e}')

'''

expr_capture = '''    # === AUTO-CAPTURE: FORMULA_EXPRESSION ===
    try:
        _act_payload = {
            'expression': expression,
            'output_column': column_name,
            'data_type': 'DOUBLE',
            'formula_type': 'EXPRESSION',
            'source_columns': referenced_cols,
        }
        _create_activity_from_action(
            folder_id=folder_id, action_type='FORMULA_ADD', payload=_act_payload,
            target_column=column_name,
            company_id=cid if current_user else None, module_id=mid if current_user else None,
            master_file_id=master.get('id'),
            user_id=current_user.get('user_id') if current_user else None,
        )
    except Exception as _e:
        logger.warning(f'Auto-capture FORMULA_EXPRESSION failed: {_e}')

'''

ANCHOR = '        # Persist formula for auto-reapply on future merges'

# Inject FORMULA_ADD before the FIRST occurrence
first = src.find(ANCHOR)
if 'AUTO-CAPTURE: FORMULA_ADD' in src:
    print('FORMULA_ADD: already present, skipping')
elif first != -1:
    src = src[:first] + formula_add + src[first:]
    print('FORMULA_ADD: injected before first persist block')
else:
    print('FORMULA_ADD: no anchor found')

# Inject FORMULA_EXPRESSION before the SECOND occurrence
second = src.find(ANCHOR, first + 1 if first != -1 else 0)
if 'AUTO-CAPTURE: FORMULA_EXPRESSION' in src:
    print('FORMULA_EXPRESSION: already present, skipping')
elif second != -1:
    src = src[:second] + expr_capture + src[second:]
    print('FORMULA_EXPRESSION: injected before second persist block')
else:
    print('FORMULA_EXPRESSION: no second anchor found')

with open('backend/main.py','w',encoding='utf-8') as f:
    f.write(src)
print('saved')