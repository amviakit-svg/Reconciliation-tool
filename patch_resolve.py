import os

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    old_logic = """                            # Sort by score descending (best match first)
                            candidate_matches.sort(key=lambda x: x[0], reverse=True)
                            best_match = candidate_matches[0][1]
                            col_alias_map[col_name] = best_match
                            return best_match
                        return col_name"""

    new_logic = """                            # Sort by score descending (best match first)
                            candidate_matches.sort(key=lambda x: x[0], reverse=True)
                            best_match = candidate_matches[0][1]
                            col_alias_map[col_name] = best_match
                            return best_match
                            
                        # Legacy fallback: if Phase 4 is looking for 'Sales Amount' (old default)
                        # but it's not found, try mapping it to the first Phase 1 field
                        if col_name.lower() == 'sales amount' and len(p1_fields) > 0:
                            first_p1_field = p1_fields[0].get('name')
                            if first_p1_field and first_p1_field in primary_df.columns:
                                col_alias_map[col_name] = first_p1_field
                                return first_p1_field
                                
                        return col_name"""

    if old_logic in content:
        content = content.replace(old_logic, new_logic)
        print("Patched resolve_column legacy fallback successfully.")
    else:
        print("Failed to find old logic for patching resolve_column.")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file()
