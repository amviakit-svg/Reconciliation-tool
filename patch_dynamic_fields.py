import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    target = """            // Collect dynamic fields configuration
            let dynamicFields = collectPhase1FieldsConfig();"""
            
    replacement = """            // Collect dynamic fields configuration
            let dynamicFields = collectPhase1FieldsConfig();
            
            // If the DOM was wiped, restore dynamicFields from the backend configuration as well
            if (dynamicFields.length === 0 && (!document.getElementById('phase1-file') || !document.getElementById('phase1-file').value)) {
                try {
                    const savedConfigData = await apiCall('/api/rules/1');
                    if (savedConfigData.success && savedConfigData.rules && savedConfigData.rules.length > 0) {
                        const cfg = savedConfigData.rules[0].config;
                        if (cfg && cfg.fields && cfg.fields.length > 0) {
                            dynamicFields = cfg.fields;
                            console.log('Automatically restored Phase 1 dynamic fields from backend.');
                        }
                    }
                } catch(e) {
                    console.warn('Failed to restore dynamic fields from backend', e);
                }
            }"""
            
    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched dynamic fields fallback.")
    else:
        print("Could not find the target string for dynamic fields.")

patch_html()
