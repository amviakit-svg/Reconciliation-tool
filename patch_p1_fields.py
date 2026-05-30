import os

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\backend\main.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Move p1_fields definition up to just below p1_config
    # 1. Replace the late assignment with a pass-through or empty string
    late_assignment = "p1_fields = p1_config.get('fields', [])\n        if isinstance(p1_fields, list):"
    if late_assignment in content:
        content = content.replace(late_assignment, "if isinstance(p1_fields, list):")
        print("Removed late assignment")
    else:
        print("Late assignment not found")

    # 2. Add it up where p1_config is initialized (around line 3024)
    early_target = "if not isinstance(p1_config, dict): p1_config = {}"
    new_early = "if not isinstance(p1_config, dict): p1_config = {}\n        p1_fields = p1_config.get('fields', [])"
    if early_target in content:
        content = content.replace(early_target, new_early)
        print("Added early assignment")
    else:
        print("Early target not found")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file()
