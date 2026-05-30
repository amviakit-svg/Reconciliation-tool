import re

def patch_html():
    filepath = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the Phase 1 save button and preview section
    start_str = '<div class="flex items-center justify-between mt-4">'
    start_idx = content.find(start_str)
    
    # We need to find where Phase 1 ends. It ends right before <!-- Phase 2: Matching Rules -->
    end_str = '<!-- Phase 2: Matching Rules -->'
    end_idx = content.find(end_str)
    
    if start_idx == -1 or end_idx == -1:
        print("Could not find start or end index.")
        return
        
    # The block to extract
    # Wait, the end_idx includes some closing divs for Phase 1. 
    # Let's extract exactly what we need using regex.
    
    # Extract the save button div
    save_btn_match = re.search(r'<div class="flex items-center justify-between mt-4">.*?<button onclick="savePhase1Rule\(\)"[^>]*>.*?</button>\s*</div>', content, re.DOTALL)
    
    # Extract the preview div
    preview_match = re.search(r'<div id="phase1-preview"[^>]*>.*?</div>\s*</div>\s*</div>\s*</div>', content, re.DOTALL)
    # The above regex might grab too much. Let's just grab by specific IDs to be safe.
    
    save_btn_str = """                    <div class="flex items-center justify-between mt-4">
                        <div class="text-sm text-gray-600">
                            <span class="font-medium">Note:</span> This selection will generate unique values and serve as the foundation for all matching rules.
                        </div>
                        <button onclick="savePhase1Rule()" id="phase1-save-btn" class="bg-blue-600 text-white font-medium py-2 px-6 rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2">
                            <span id="phase1-save-spinner" class="spinner-sm hidden"></span>
                            <span id="phase1-save-text">Save File Processing</span>
                        </button>
                    </div>"""
                    
    preview_str = """                    <div id="phase1-preview" class="mt-6 hidden">
                        <div class="flex items-center justify-between mb-3">
                            <h4 class="text-sm font-semibold text-gray-700">Preview - Unique Values (First 10)</h4>
                            <span id="phase1-unique-count" class="text-xs font-medium bg-blue-100 text-blue-700 px-3 py-1.5 rounded-full">0 unique values</span>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 overflow-x-auto border border-gray-200">
                            <table class="min-w-full text-sm" id="phase1-preview-table">
                                <thead>
                                    <tr id="phase1-preview-head-row">
                                        <th class="text-left font-semibold text-gray-600 px-4 py-3 bg-gray-100 whitespace-nowrap min-w-[60px]">Unique ID</th>
                                        <th class="text-left font-semibold text-gray-600 px-4 py-3 bg-gray-100 whitespace-nowrap min-w-[120px]">Source File</th>
                                        <th id="phase1-preview-primary-header" class="text-left font-semibold text-gray-600 px-4 py-3 bg-gray-100 whitespace-nowrap min-w-[100px]">Order ID</th>
                                    </tr>
                                </thead>
                                <tbody id="phase1-preview-body"></tbody>
                            </table>
                        </div>
                    </div>"""
                    
    if save_btn_str not in content or preview_str not in content:
        print("Exact strings not found. Aborting.")
        return
        
    # Remove from original location
    content = content.replace(save_btn_str, "")
    content = content.replace(preview_str, "")
    
    # Construct the new block for Final Processing page
    new_block = f"""
                <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
                    <details class="group">
                        <summary class="flex justify-between items-center font-medium cursor-pointer list-none text-lg text-gray-900">
                            <span>Primary Data Preview & Rules Mapping</span>
                            <span class="transition group-open:rotate-180">
                                <svg fill="none" height="24" shape-rendering="geometricPrecision" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" viewBox="0 0 24 24" width="24"><path d="M6 9l6 6 6-6"></path></svg>
                            </span>
                        </summary>
                        <div class="text-gray-600 mt-3 group-open:animate-fadeIn">
                            <p class="text-sm mb-4">Review the unique values generated from your primary data selection before proceeding.</p>
                            
                            <!-- The original preview block (un-hidden by default inside the details so it shows when expanded) -->
                            {preview_str.replace('class="mt-6 hidden"', 'class="mt-6"')}
                            
                            <!-- The original save button block -->
                            {save_btn_str.replace('class="flex items-center justify-between mt-4"', 'class="flex items-center justify-between mt-6 pt-6 border-t border-gray-100"')}
                        </div>
                    </details>
                </div>
"""

    # Insert into Final processing page
    target_insert = """                <div class="text-center mb-8">
                    <h2 class="text-2xl font-bold text-gray-900">Processing</h2>
                    <p class="text-gray-600 mt-1">Execute all configured rules and generate reconciliation results</p>
                </div>"""
                
    if target_insert in content:
        content = content.replace(target_insert, target_insert + new_block)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully moved Phase 1 UI elements to Final Processing page.")
    else:
        print("Could not find the target insertion point in Final Processing page.")

patch_html()
