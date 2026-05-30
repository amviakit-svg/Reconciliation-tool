import re

def patch_backend():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The buggy line:
    # preview_data = clean_nan_values(df.head(10).to_dict(orient='records'))
    
    target = "        preview_data = clean_nan_values(df.head(10).to_dict(orient='records'))"
    
    # We will replace it with a bulletproof serialization that handles all pandas/numpy types
    replacement = """        # Safely convert pandas types to python native types to prevent FastAPI serialization crashes
        df_preview = df.head(10).fillna("")
        preview_data_raw = df_preview.to_dict(orient='records')
        import json
        preview_data = json.loads(json.dumps(preview_data_raw, default=str))"""

    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched get_primary_preview to prevent 500 errors.")
    else:
        print("Could not find the target string in get_primary_preview.")

patch_backend()
