import os

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    target = """                    pivot_table = pd.pivot_table(filtered_df, **pivot_kwargs)
                    pivot_table = pivot_table.fillna(0)"""
                    
    replacement = """                    pivot_table = pd.pivot_table(filtered_df, **pivot_kwargs)
                    pivot_table = pivot_table.fillna(0)
                    
                    # Drop rows where all numeric values are 0 (e.g. Cartesian product artifacts), excluding Grand Total
                    if not pivot_table.empty:
                        num_cols = pivot_table.select_dtypes(include=['number']).columns
                        if len(num_cols) > 0:
                            non_zero_mask = (pivot_table[num_cols] != 0).any(axis=1)
                            if isinstance(pivot_table.index, pd.MultiIndex):
                                try:
                                    non_zero_mask = non_zero_mask | (pivot_table.index.get_level_values(0) == 'Grand Total')
                                except: pass
                            else:
                                if 'Grand Total' in pivot_table.index:
                                    non_zero_mask.loc['Grand Total'] = True
                            pivot_table = pivot_table[non_zero_mask]"""

    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched Phase 4 pivot successfully")
    else:
        print("Target not found in Phase 4")

    # Also apply to the preview endpoint (around line 4648)
    target_preview = """        pivot_table = pd.pivot_table(preview_df, **pivot_kwargs)
        pivot_table = pivot_table.fillna(0)"""
        
    replacement_preview = """        pivot_table = pd.pivot_table(preview_df, **pivot_kwargs)
        pivot_table = pivot_table.fillna(0)
        
        if not pivot_table.empty:
            num_cols = pivot_table.select_dtypes(include=['number']).columns
            if len(num_cols) > 0:
                non_zero_mask = (pivot_table[num_cols] != 0).any(axis=1)
                if isinstance(pivot_table.index, pd.MultiIndex):
                    try:
                        non_zero_mask = non_zero_mask | (pivot_table.index.get_level_values(0) == 'Grand Total')
                    except: pass
                else:
                    if 'Grand Total' in pivot_table.index:
                        non_zero_mask.loc['Grand Total'] = True
                pivot_table = pivot_table[non_zero_mask]"""
                
    if target_preview in content:
        content = content.replace(target_preview, replacement_preview)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched Preview pivot successfully")
    else:
        print("Target preview not found")

patch_file()
