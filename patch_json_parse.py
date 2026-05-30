import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The buggy line is: const cfg = savedConfigData.rules[0].config;
    # We need to replace it with: const cfg = typeof savedConfigData.rules[0].config === 'string' ? JSON.parse(savedConfigData.rules[0].config) : savedConfigData.rules[0].config;
    
    target = "const cfg = savedConfigData.rules[0].config;"
    replacement = "const cfg = typeof savedConfigData.rules[0].config === 'string' ? JSON.parse(savedConfigData.rules[0].config) : savedConfigData.rules[0].config;"
    
    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully fixed JSON parsing in fallback.")
    else:
        print("Could not find the target string.")

patch_html()
