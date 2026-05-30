import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the end of Phase 1 section to insert the button
    target = '<!-- Phase 2: Matching Rules -->'
    replacement = """
                    <!-- Local Save Button for Immediate Feedback -->
                    <div class="mt-6 border-t pt-4 flex justify-end">
                        <button onclick="savePhase1Rule(true)" id="phase1-local-save-btn" class="bg-blue-600 text-white font-medium py-2 px-6 rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2">
                            <span id="phase1-local-save-spinner" class="spinner-sm hidden"></span>
                            <span>Confirm & Save Phase 1 Selection</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Phase 2: Matching Rules -->
"""
    
    if target in content and 'phase1-local-save-btn' not in content:
        # We need to insert it right before the end of phase-1 div. 
        # The target string is preceded by closing divs for phase-1.
        # Let's do a replace.
        content = content.replace("""                </div>
            </div>

            <!-- Phase 2: Matching Rules -->""", replacement)
        
        # We also need to modify savePhase1Rule to handle the new spinner
        old_spinner = "document.getElementById('phase1-save-spinner').classList.remove('hidden');"
        new_spinner = """
            if(document.getElementById('phase1-save-spinner')) document.getElementById('phase1-save-spinner').classList.remove('hidden');
            if(document.getElementById('phase1-local-save-spinner')) document.getElementById('phase1-local-save-spinner').classList.remove('hidden');
"""
        content = content.replace(old_spinner, new_spinner)
        
        old_spinner_hide = "document.getElementById('phase1-save-spinner').classList.add('hidden');"
        new_spinner_hide = """
                if(document.getElementById('phase1-save-spinner')) document.getElementById('phase1-save-spinner').classList.add('hidden');
                if(document.getElementById('phase1-local-save-spinner')) document.getElementById('phase1-local-save-spinner').classList.add('hidden');
"""
        content = content.replace(old_spinner_hide, new_spinner_hide)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully added local save button to Phase 1.")
    else:
        print("Could not find the target string or already patched.")

patch_html()
