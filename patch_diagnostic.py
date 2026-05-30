import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add console.log inside savePhase1Rule
    target = "const fileId = String(document.getElementById('phase1-file').value || '');"
    replacement = """
            const fileEl = document.getElementById('phase1-file');
            console.log('Diagnostic: phase1-file value is:', fileEl ? fileEl.value : 'Element not found', 'Options:', fileEl ? fileEl.options.length : 0);
            const fileId = String(fileEl.value || '');
"""
    
    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully added diagnostic console log.")
    else:
        print("Could not find the target string.")

patch_html()
