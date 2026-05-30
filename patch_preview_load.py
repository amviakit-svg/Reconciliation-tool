import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the switchTab hook in index.html
    target = """                                const origSwitchTab = switchTab;
                                switchTab = function(tabName) {
                                    origSwitchTab(tabName);
                                    if(tabName === 'process') {
                                        updateDiagLabels();
                                    }
                                };"""
                                
    replacement = """                                const origSwitchTab = switchTab;
                                switchTab = async function(tabName) {
                                    origSwitchTab(tabName);
                                    if(tabName === 'process') {
                                        updateDiagLabels();
                                        
                                        // Load the preview data if it's currently empty
                                        const tbody = document.getElementById('phase1-preview-body');
                                        if (tbody && tbody.innerHTML.trim() === '') {
                                            try {
                                                const savedConfigData = await apiCall('/api/rules/1');
                                                if (savedConfigData.success && savedConfigData.rules && savedConfigData.rules.length > 0) {
                                                    const cfg = typeof savedConfigData.rules[0].config === 'string' ? JSON.parse(savedConfigData.rules[0].config) : savedConfigData.rules[0].config;
                                                    
                                                    // Set primary header
                                                    window.primaryValueColumnName = cfg.column || 'Order ID';
                                                    const pHeader = document.getElementById('phase1-preview-primary-header');
                                                    if (pHeader) pHeader.textContent = window.primaryValueColumnName;
                                                    
                                                    // Set unique count badge
                                                    const countBadge = document.getElementById('phase1-unique-count');
                                                    if (countBadge) {
                                                        countBadge.textContent = `${cfg.total_unique ? cfg.total_unique.toLocaleString() : '0'} unique values`;
                                                    }
                                                    
                                                    // Load the actual preview table
                                                    if (cfg.primary_file) {
                                                        await loadPrimaryPreview(cfg.primary_file);
                                                    }
                                                }
                                            } catch (e) {
                                                console.error('Failed to load preview for process tab:', e);
                                            }
                                        }
                                    }
                                };"""

    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched switchTab to load preview.")
    else:
        print("Could not find switchTab hook.")

patch_html()
