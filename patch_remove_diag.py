import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The block we want to remove
    target = """                            <!-- Diagnostic Display -->
                            <div class="mb-4 p-3 bg-blue-50 border border-blue-100 rounded-md text-sm">
                                <p class="font-medium text-blue-800">Currently Selected in Phase 1:</p>
                                <p class="text-blue-700 mt-1">
                                    File: <span id="diag-file" class="font-bold">None</span> <br>
                                    Sheet: <span id="diag-sheet" class="font-bold">None</span> <br>
                                    Column: <span id="diag-col" class="font-bold">None</span>
                                </p>
                            </div>"""

    if target in content:
        content = content.replace(target, "")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully removed the Diagnostic Display section.")
    else:
        print("Could not find the Diagnostic Display section.")

patch_html()
