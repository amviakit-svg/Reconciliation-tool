import os

def patch_backend_phase4_and_notifications():
    with open('backend/main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Revert silent skip logic in Phase 4
    old_missing_cols = '''                    missing_cols = [c for c in all_ref_columns if c and c not in primary_df.columns]
                    if missing_cols:
                        msg = f"Phase 4 summary '{rule_name}' warning: Columns not found in data: {', '.join(missing_cols)}. Auto-creating them to prevent skip."
                        logger.warning(msg)
                        for c in missing_cols:
                            primary_df[c] = None'''

    new_missing_cols = '''                    missing_cols = [c for c in all_ref_columns if c and c not in primary_df.columns]
                    if missing_cols:
                        msg = f"Phase 4 summary '{rule_name}' skipped: Columns not found in data: {', '.join(missing_cols)}"
                        logger.warning(msg)
                        phase4_errors.append(msg)
                        continue'''

    if old_missing_cols in content:
        content = content.replace(old_missing_cols, new_missing_cols)
        print("Reverted silent skip logic")
    else:
        print("Could not find silent skip logic")

    # 2. Add notifications at the end of process_rules_background
    old_success = '''            processing_status["result"] = {
                "success": True,'''
    
    new_success = '''            from database import add_notification
            if phase4_errors:
                add_notification(cid, mid, 'warning', f"Processing completed with warnings: {len(phase4_errors)} summaries skipped due to missing columns.", "?page=processed")
            else:
                add_notification(cid, mid, 'success', f"Processing completed successfully. {len(summary_sheets)} summaries generated.", "?page=processed")
            
            processing_status["result"] = {
                "success": True,'''
                
    if old_success in content:
        content = content.replace(old_success, new_success)
        print("Added success notifications")
    else:
        print("Could not find success block")

    old_error = '''        with processing_lock:
            processing_status["error"] = str(e)'''
            
    new_error = '''        with processing_lock:
            from database import add_notification
            cid = processing_status.get("company_id")
            mid = processing_status.get("module_id")
            if cid and mid:
                add_notification(cid, mid, 'error', f"Processing failed: {str(e)[:100]}...", "?page=process")
            processing_status["error"] = str(e)'''

    if old_error in content:
        content = content.replace(old_error, new_error)
        print("Added error notifications")
    else:
        print("Could not find error block")

    with open('backend/main.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_backend_phase4_and_notifications()
