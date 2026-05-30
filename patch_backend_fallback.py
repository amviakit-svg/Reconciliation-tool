import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the validation block
    target = """            const fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');
            const sheetName = String(document.getElementById('phase1-sheet').value || sessionStorage.getItem('phase1_sheet_cache') || '');
            const column = String(document.getElementById('phase1-column').value || sessionStorage.getItem('phase1_col_cache') || '');"""
            
    replacement = """            let fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');
            let sheetName = String(document.getElementById('phase1-sheet').value || sessionStorage.getItem('phase1_sheet_cache') || '');
            let column = String(document.getElementById('phase1-column').value || sessionStorage.getItem('phase1_col_cache') || '');
            
            // If DOM is wiped due to tab switching, automatically pull the saved configuration from the backend!
            if (!fileId) {
                try {
                    const savedConfigData = await apiCall('/api/rules/1');
                    if (savedConfigData.success && savedConfigData.rules && savedConfigData.rules.length > 0) {
                        const cfg = savedConfigData.rules[0].config;
                        if (cfg && cfg.file_id) {
                            fileId = cfg.file_id;
                            sheetName = cfg.sheet_name || sheetName;
                            column = cfg.column || column;
                            console.log('Automatically restored Phase 1 config from backend:', fileId);
                        }
                    }
                } catch(e) {
                    console.warn('Failed to restore config from backend', e);
                }
            }
"""
    
    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched to fetch config from backend.")
    else:
        print("Could not find the target string.")

patch_html()
