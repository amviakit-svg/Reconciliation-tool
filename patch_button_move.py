import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The block we want to move
    btn_block = """                                                <div class="flex items-center justify-between mt-6 pt-6 border-t border-gray-100">
                        <div class="text-sm text-gray-600">
                            <span class="font-medium">Note:</span> This selection will generate unique values and serve as the foundation for all matching rules.
                        </div>
                        <button onclick="savePhase1Rule()" id="phase1-save-btn" class="bg-blue-600 text-white font-medium py-2 px-6 rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2">
                            <span id="phase1-save-spinner" class="spinner-sm hidden"></span>
                            <span id="phase1-save-text">Save File Processing</span>
                        </button>
                    </div>"""
                    
    # Where we want to insert it
    target = """                <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
                    <details class="group">"""
                    
    new_btn_block = """                <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between mb-4 pb-4 border-b border-gray-100 gap-4">
                        <div class="text-sm text-gray-600">
                            <h3 class="text-lg font-semibold text-gray-900 mb-1">Step 1: Save Rules & Extract Data</h3>
                            <span class="font-medium">Note:</span> Processing this step generates the unique values that serve as the foundation for your reconciliation.
                        </div>
                        <button onclick="savePhase1Rule()" id="phase1-save-btn" class="bg-blue-600 text-white font-medium py-2.5 px-6 rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center justify-center gap-2 shrink-0 shadow-sm">
                            <span id="phase1-save-spinner" class="spinner-sm hidden"></span>
                            <span id="phase1-save-text">Save File Processing</span>
                        </button>
                    </div>
                    <details class="group">"""

    if btn_block in content and target in content:
        # Remove the old button block
        content = content.replace(btn_block, "")
        # Insert the new button block above the details
        content = content.replace(target, new_btn_block)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully moved the save button above the collapsible section.")
    else:
        print("Could not find the button block or target to move.")

patch_html()
