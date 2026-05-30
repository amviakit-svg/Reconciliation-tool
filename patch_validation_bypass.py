import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find where dynamicFields is declared and the backend logic runs
    target1 = """// Collect dynamic fields configuration
            let dynamicFields = collectPhase1FieldsConfig();"""
            
    replacement1 = """// Collect dynamic fields configuration
            let dynamicFields = collectPhase1FieldsConfig();
            let isRestoredFromBackend = false;"""

    if target1 in content:
        content = content.replace(target1, replacement1)

    target2 = """if (cfg.fields && cfg.fields.length > 0 && dynamicFields.length === 0) {
                                dynamicFields = cfg.fields;
                            }"""
                            
    replacement2 = """if (cfg.fields && cfg.fields.length > 0 && dynamicFields.length === 0) {
                                dynamicFields = cfg.fields;
                                isRestoredFromBackend = true;
                            }"""
                            
    if target2 in content:
        content = content.replace(target2, replacement2)

    target3 = """// Validate dynamic fields if present
            let fieldErrors = [];
            if (dynamicFields.length > 0) {
                fieldErrors = validatePhase1Fields();
            }"""
            
    replacement3 = """// Validate dynamic fields if present
            let fieldErrors = [];
            if (dynamicFields.length > 0 && !isRestoredFromBackend) {
                fieldErrors = validatePhase1Fields();
            }"""
            
    if target3 in content:
        content = content.replace(target3, replacement3)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched validation bypass for restored backend configs.")

patch_html()
