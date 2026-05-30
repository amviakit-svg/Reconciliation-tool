import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add a dynamic label above the save button in the new details block
    target = '<!-- The original save button block -->'
    replacement = """
                            <!-- Diagnostic Display -->
                            <div class="mb-4 p-3 bg-blue-50 border border-blue-100 rounded-md text-sm">
                                <p class="font-medium text-blue-800">Currently Selected in Phase 1:</p>
                                <p class="text-blue-700 mt-1">
                                    File: <span id="diag-file" class="font-bold">None</span> <br>
                                    Sheet: <span id="diag-sheet" class="font-bold">None</span> <br>
                                    Column: <span id="diag-col" class="font-bold">None</span>
                                </p>
                            </div>
                            
                            <script>
                                // Update diagnostic labels whenever they change or when this tab is opened
                                function updateDiagLabels() {
                                    const f = document.getElementById('phase1-file');
                                    const s = document.getElementById('phase1-sheet');
                                    const c = document.getElementById('phase1-column');
                                    if(document.getElementById('diag-file')) {
                                        document.getElementById('diag-file').textContent = (f && f.value) ? f.options[f.selectedIndex].text : 'None';
                                        document.getElementById('diag-sheet').textContent = (s && s.value) ? s.value : 'None';
                                        document.getElementById('diag-col').textContent = (c && c.value) ? c.value : 'None';
                                    }
                                }
                                
                                // Hook into the existing switchTab to update it when opening the processing tab
                                const origSwitchTab = switchTab;
                                switchTab = function(tabName) {
                                    origSwitchTab(tabName);
                                    if(tabName === 'process') {
                                        updateDiagLabels();
                                    }
                                };
                                
                                // Hook into the dropdowns
                                setTimeout(() => {
                                    const f = document.getElementById('phase1-file');
                                    if(f) f.addEventListener('change', updateDiagLabels);
                                    const s = document.getElementById('phase1-sheet');
                                    if(s) s.addEventListener('change', updateDiagLabels);
                                    const c = document.getElementById('phase1-column');
                                    if(c) c.addEventListener('change', updateDiagLabels);
                                }, 1000);
                            </script>
                            
                            <!-- The original save button block -->
"""
    
    if target in content and 'diag-file' not in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully added diagnostic UI.")
    else:
        print("Could not find the target string or already patched.")

patch_html()
