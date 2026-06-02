import os

with open("main.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """        # Move to recycle bin first
        try:
            file_dict = dict(file)
            move_to_recycle_bin(
                company_id=cid,
                entity_type='file',
                entity_id=file_id,
                entity_name=file_dict.get('original_name') or file_dict.get('name'),
                original_path=file_dict.get('file_path'),
                metadata=file_dict,
                deleted_by=current_user.get('user_id') if current_user else None,
                module_id=mid
            )"""

replacement = """        # Move to recycle bin first
        try:
            file_dict = dict(file)
            
            # Physically rename the file to avoid conflict if uploaded again
            old_path = file_dict.get('file_path')
            new_path = old_path
            if old_path and os.path.exists(old_path):
                import time
                new_path = f"{old_path}.deleted.{int(time.time())}"
                try:
                    os.rename(old_path, new_path)
                except OSError as e:
                    logger.warning(f"Could not rename file for recycle bin: {e}")
                    new_path = old_path
            
            move_to_recycle_bin(
                company_id=cid,
                entity_type='file',
                entity_id=file_id,
                entity_name=file_dict.get('original_name') or file_dict.get('name'),
                original_path=new_path,
                metadata=file_dict,
                deleted_by=current_user.get('user_id') if current_user else None,
                module_id=mid
            )"""

if target in text:
    text = text.replace(target, replacement)
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Success")
else:
    print("Target not found")
