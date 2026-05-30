import os

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the fallback block
    target = """                        # Legacy fallback: if Phase 4 is looking for 'Sales Amount' (old default)
                        # but it's not found, try mapping it to the first Phase 1 field
                        if col_name.lower() == 'sales amount' and len(p1_fields) > 0:
                            first_p1_field = p1_fields[0].get('name')
                            if first_p1_field and first_p1_field in primary_df.columns:
                                col_alias_map[col_name] = first_p1_field
                                return first_p1_field
                                
                        return col_name"""

    new_target = """                        # Legacy fallback: if Phase 4 is looking for 'Sales Amount' (old default)
                        # but it's not found, try mapping it to the first Phase 1 field
                        logger.info(f"PHASE 4 DIAGNOSTIC: resolve_column('{col_name}') fallback check. p1_fields={p1_fields}, primary_df.columns={list(primary_df.columns)}")
                        if col_name.strip().lower() == 'sales amount' and len(p1_fields) > 0:
                            first_p1_field = p1_fields[0].get('name')
                            logger.info(f"PHASE 4 DIAGNOSTIC: first_p1_field='{first_p1_field}'")
                            if first_p1_field and first_p1_field in primary_df.columns:
                                col_alias_map[col_name] = first_p1_field
                                return first_p1_field
                                
                        return col_name"""

    if target in content:
        content = content.replace(target, new_target)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched successfully")
    else:
        print("Target not found")

patch_file()
