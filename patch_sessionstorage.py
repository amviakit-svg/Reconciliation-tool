import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Hook into the dropdowns to save to sessionStorage
    target_diag = 'const f = document.getElementById(\'phase1-file\');'
    replacement_diag = """
                                // Save to sessionStorage whenever changed
                                const f = document.getElementById('phase1-file');
                                if (f && f.value) sessionStorage.setItem('phase1_file_cache', f.value);
                                const s = document.getElementById('phase1-sheet');
                                if (s && s.value) sessionStorage.setItem('phase1_sheet_cache', s.value);
                                const c = document.getElementById('phase1-column');
                                if (c && c.value) sessionStorage.setItem('phase1_col_cache', c.value);
"""
    if 'sessionStorage.setItem(\'phase1_file_cache\'' not in content:
        content = content.replace(target_diag, replacement_diag)

    # Modify savePhase1Rule to use sessionStorage fallback
    target_save = "const fileId = String(document.getElementById('phase1-file').value || '');"
    replacement_save = """
            const fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');
            const sheetName = String(document.getElementById('phase1-sheet').value || sessionStorage.getItem('phase1_sheet_cache') || '');
            const column = String(document.getElementById('phase1-column').value || sessionStorage.getItem('phase1_col_cache') || '');
            
            // Re-populate the DOM just in case the browser wiped it
            if (document.getElementById('phase1-file') && !document.getElementById('phase1-file').value) {
                const opt = document.createElement('option');
                opt.value = fileId; opt.text = "Restored File"; opt.selected = true;
                document.getElementById('phase1-file').appendChild(opt);
            }
            if (document.getElementById('phase1-sheet') && !document.getElementById('phase1-sheet').value) {
                const opt = document.createElement('option');
                opt.value = sheetName; opt.text = sheetName; opt.selected = true;
                document.getElementById('phase1-sheet').appendChild(opt);
            }
            if (document.getElementById('phase1-column') && !document.getElementById('phase1-column').value) {
                const opt = document.createElement('option');
                opt.value = column; opt.text = column; opt.selected = true;
                document.getElementById('phase1-column').appendChild(opt);
            }
"""
    
    # We must replace the original fetch lines
    old_fetch = """            const fileId = String(document.getElementById('phase1-file').value || '');
            const sheetName = String(document.getElementById('phase1-sheet').value || '');
            const column = String(document.getElementById('phase1-column').value || '');"""
    
    if old_fetch in content:
        content = content.replace(old_fetch, replacement_save)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched to use sessionStorage fallback.")
    else:
        print("Could not find old_fetch block.")

patch_html()
