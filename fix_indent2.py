with open('backend/main.py','r',encoding='utf-8') as f:
    src = f.read()

# The COLUMN_DELETE block needs to be indented with 8 spaces, not 4.
# Replace the broken block with the correct one.
old = '''    # === AUTO-CAPTURE: COLUMN_DELETE ===
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
        logger.warning(f'Auto-capture COLUMN_DELETE failed: {_e}')

        return {'''

new = '''        # === AUTO-CAPTURE: COLUMN_DELETE ===
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
            logger.warning(f'Auto-capture COLUMN_DELETE failed: {_e}')

        return {'''

if old in src:
    src = src.replace(old, new)
    print('Fixed COLUMN_DELETE indent')
else:
    print('COLUMN_DELETE block not found in expected form')

with open('backend/main.py','w',encoding='utf-8') as f:
    f.write(src)
print('saved')