import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The line to replace: showToast('Please fix the highlighted fields before saving', 'error');
    target = "showToast('Please fix the highlighted fields before saving', 'error');"
    
    # We want to show a more descriptive error.
    # In savePhase1Rule(), we have:
    # let fieldErrors = []; ... let hasError = false;
    replacement = """
                let errorMsg = 'Please fix the highlighted fields before saving.';
                if (fieldErrors && fieldErrors.length > 0) {
                    errorMsg = fieldErrors.map(e => e.message).join(' | ');
                } else if (!fileId) {
                    errorMsg = 'Please go to Phase 1 and select the Primary File. (If you uploaded a new file, you must select it first!)';
                } else if (!sheetName) {
                    errorMsg = 'Please go to Phase 1 and select the Sheet.';
                } else if (!column) {
                    errorMsg = 'Please go to Phase 1 and select the Primary Column.';
                }
                showToast(errorMsg, 'error');
"""
    
    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched error message.")
    else:
        print("Could not find the target string.")

patch_html()
