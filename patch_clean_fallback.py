import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # We will replace everything from `let fileId = ...` down to `let fieldErrors = [];`
    # Let's find the start and end markers
    start_marker = "let fileId = String(document.getElementById('phase1-file').value"
    end_marker = "let fieldErrors = [];"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("Could not find start or end markers.")
        return
        
    replacement = """let fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');
            let sheetName = String(document.getElementById('phase1-sheet').value || sessionStorage.getItem('phase1_sheet_cache') || '');
            let column = String(document.getElementById('phase1-column').value || sessionStorage.getItem('phase1_col_cache') || '');
            let salesColumn = String(document.getElementById('phase1-sales-column')?.value || '');
            
            // Collect dynamic fields configuration
            let dynamicFields = collectPhase1FieldsConfig();
            
            // If DOM is wiped due to tab switching (fileId empty), automatically pull the ENTIRE saved configuration from the backend!
            if (!fileId) {
                try {
                    const savedConfigData = await apiCall('/api/rules/1');
                    if (savedConfigData.success && savedConfigData.rules && savedConfigData.rules.length > 0) {
                        const cfg = typeof savedConfigData.rules[0].config === 'string' ? JSON.parse(savedConfigData.rules[0].config) : savedConfigData.rules[0].config;
                        if (cfg && cfg.file_id) {
                            fileId = cfg.file_id;
                            sheetName = cfg.sheet_name || sheetName;
                            column = cfg.column || column;
                            salesColumn = cfg.sales_column || salesColumn;
                            if (cfg.fields && cfg.fields.length > 0 && dynamicFields.length === 0) {
                                dynamicFields = cfg.fields;
                            }
                            console.log('Automatically restored Phase 1 config (including dynamic fields) from backend:', fileId);
                        }
                    }
                } catch(e) {
                    console.warn('Failed to restore config from backend', e);
                }
            }
            
            // Re-populate the DOM just in case the browser wiped it, so validation logic doesn't crash on undefined elements
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
            if (document.getElementById('phase1-sales-column') && !document.getElementById('phase1-sales-column').value && salesColumn) {
                const opt = document.createElement('option');
                opt.value = salesColumn; opt.text = salesColumn; opt.selected = true;
                document.getElementById('phase1-sales-column').appendChild(opt);
            }

            // Validate dynamic fields if present
            """
            
    content = content[:start_idx] + replacement + content[end_idx:]
    
    # Let's also fix the duplicate logic block below that check for salesColumn since we moved it up.
    # We will search and remove the duplicate salesColumn extraction.
    dup_sales = "const salesColumn = String(document.getElementById('phase1-sales-column')?.value || '');"
    content = content.replace(dup_sales, "")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched logic.")

patch_html()
