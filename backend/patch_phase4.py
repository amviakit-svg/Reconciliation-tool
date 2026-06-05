import os

def patch_main():
    with open('main.py', 'r') as f:
        content = f.read()
    
    old = '''                    missing_cols = [c for c in all_ref_columns if c and c not in primary_df.columns]
                    if missing_cols:
                        msg = f"Phase 4 summary '{rule_name}' skipped: Columns not found in data: {', '.join(missing_cols)}"
                        logger.warning(msg)
                        phase4_errors.append(msg)
                        continue'''
    
    new = '''                    missing_cols = [c for c in all_ref_columns if c and c not in primary_df.columns]
                    if missing_cols:
                        msg = f"Phase 4 summary '{rule_name}' warning: Columns not found in data: {', '.join(missing_cols)}. Auto-creating them to prevent skip."
                        logger.warning(msg)
                        for c in missing_cols:
                            primary_df[c] = None'''
    
    if old in content:
        content = content.replace(old, new)
        with open('main.py', 'w') as f:
            f.write(content)
        print("Patched successfully!")
    else:
        if new in content:
            print("Already patched!")
        else:
            print("Could not find exact text to replace.")

if __name__ == '__main__':
    patch_main()
