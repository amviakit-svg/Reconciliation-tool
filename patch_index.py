import re
import sys

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace Custom Output File Name
    old_input = '''                    <!-- Custom Filename Input -->
                    <div class="bg-white rounded-lg border border-gray-200 p-5 mb-6">
                        <label class="block text-sm font-semibold text-gray-900 mb-2">Custom Output File Name <span class="text-red-500">*</span></label>
                        <p class="text-xs text-gray-500 mb-3">Enter the name for the final processed Excel file. The current Date and Time will be automatically appended.</p>
                        <input type="text" id="custom-output-filename" class="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm" placeholder="e.g. Myntra_May_Settlement">
                    </div>'''
                    
    new_input = '''                    <!-- Custom Filename Input -->
                    <div class="bg-white rounded-lg border border-gray-200 p-5 mb-6">
                        <label class="block text-sm font-semibold text-gray-900 mb-2">Output File Details <span class="text-red-500">*</span></label>
                        <p class="text-xs text-gray-500 mb-3">Select Month and Year. The file name will be fixed as "Reconciliation Report [Month] [Year]".</p>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-medium text-gray-700 mb-1">Month</label>
                                <select id="output-month" class="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm">
                                    <option value="">Select Month</option>
                                    <option value="January">January</option>
                                    <option value="February">February</option>
                                    <option value="March">March</option>
                                    <option value="April">April</option>
                                    <option value="May">May</option>
                                    <option value="June">June</option>
                                    <option value="July">July</option>
                                    <option value="August">August</option>
                                    <option value="September">September</option>
                                    <option value="October">October</option>
                                    <option value="November">November</option>
                                    <option value="December">December</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-700 mb-1">Year</label>
                                <select id="output-year" class="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm">
                                    <option value="">Select Year</option>
                                    <option value="2023">2023</option>
                                    <option value="2024">2024</option>
                                    <option value="2025">2025</option>
                                    <option value="2026">2026</option>
                                    <option value="2027">2027</option>
                                    <option value="2028">2028</option>
                                    <option value="2029">2029</option>
                                    <option value="2030">2030</option>
                                </select>
                            </div>
                        </div>
                    </div>'''

    if old_input in content:
        content = content.replace(old_input, new_input)
    else:
        print("Failed to replace chunk 1")

    # 2. currentSelectedType
    old_sel = '''        let currentSelectedFY = null;
        let currentSelectedType = null;
        let currentSelectedMonth = null;'''
    new_sel = '''        let currentSelectedFY = null;
        let currentSelectedMonth = null;'''
    
    if old_sel in content:
        content = content.replace(old_sel, new_sel)
    else:
        print("Failed to replace chunk 2")

    # 3. renderProcessedTree
    old_render = '''        function renderProcessedTree(tree) {
            const container = document.getElementById('processed-tree-container');
            
            if (!tree || tree.length === 0) {
                container.innerHTML = '<p class="text-sm text-gray-500 text-center py-8">No processed files yet. Run processing to create reports.</p>';
                return;
            }
            
            let html = '';
            tree.forEach((fyNode, fyIdx) => {
                const fy = fyNode.financial_year;
                html += `
                    <div class="mb-2">
                        <div class="flex items-center space-x-2 px-2 py-2 rounded-lg hover:bg-gray-50 cursor-pointer" onclick="toggleFY('${fy}')">
                            <svg id="fy-icon-${fy}" class="w-4 h-4 text-gray-500 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                            </svg>
                            <span class="text-sm font-semibold text-gray-800">${fy}</span>
                        </div>
                        <div id="fy-children-${fy}" class="ml-6 hidden">
                `;
                
                fyNode.report_types.forEach(typeNode => {
                    const rt = typeNode.report_type;
                    html += `
                        <div class="mb-1">
                            <div class="flex items-center space-x-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 cursor-pointer" onclick="toggleType('${fy}', '${rt}')">
                                <svg id="type-icon-${fy}-${rt}" class="w-3 h-3 text-gray-400 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                </svg>
                                <span class="text-xs font-medium text-gray-600">${rt}</span>
                                <span class="text-xs text-gray-400">(${typeNode.months.length} months)</span>
                            </div>
                            <div id="type-children-${fy}-${rt}" class="ml-4 hidden">
                    `;
                    
                    typeNode.months.forEach(monthNode => {
                        const mn = monthNode.month_name;
                        const count = monthNode.file_count;
                        html += `
                            <div class="flex items-center space-x-2 px-2 py-1 rounded-lg hover:bg-blue-50 cursor-pointer transition-colors" 
                                 onclick="selectMonth('${fy}', '${rt}', '${mn}')"
                                 id="month-item-${fy}-${rt}-${mn}">
                                <svg class="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                                </svg>
                                <span class="text-xs text-gray-700">${mn}</span>
                                <span class="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full">${count}</span>
                            </div>
                        `;
                    });
                    
                    html += '</div></div>';
                });
                
                html += '</div></div>';
            });
            
            container.innerHTML = html;
        }

        function toggleFY(fy) {
            const children = document.getElementById(`fy-children-${fy}`);
            const icon = document.getElementById(`fy-icon-${fy}`);
            if (children.classList.contains('hidden')) {
                children.classList.remove('hidden');
                icon.classList.add('rotate-90');
            } else {
                children.classList.add('hidden');
                icon.classList.remove('rotate-90');
            }
        }

        function toggleType(fy, type) {
            const children = document.getElementById(`type-children-${fy}-${type}`);
            const icon = document.getElementById(`type-icon-${fy}-${type}`);
            if (children.classList.contains('hidden')) {
                children.classList.remove('hidden');
                icon.classList.add('rotate-90');
            } else {
                children.classList.add('hidden');
                icon.classList.remove('rotate-90');
            }
        }

        async function selectMonth(fy, type, month) {
            // Highlight selected
            document.querySelectorAll('[id^="month-item-"]').forEach(el => {
                el.classList.remove('bg-blue-100', 'border-l-2', 'border-blue-500');
            });
            const selected = document.getElementById(`month-item-${fy}-${type}-${month}`);
            if (selected) {
                selected.classList.add('bg-blue-100', 'border-l-2', 'border-blue-500');
            }
            
            currentSelectedFY = fy;
            currentSelectedType = type;
            currentSelectedMonth = month;
            
            document.getElementById('processed-files-title').textContent = `${fy} > ${type} > ${month}`;
            
            await loadProcessedFiles(fy, type, month);
        }

        async function loadProcessedFiles(fy, type, month) {
            try {
                const data = await apiCall(`/api/processed/files?financial_year=${encodeURIComponent(fy)}&report_type=${encodeURIComponent(type)}&month_name=${encodeURIComponent(month)}`);'''
    
    new_render = '''        function renderProcessedTree(tree) {
            const container = document.getElementById('processed-tree-container');
            
            if (!tree || tree.length === 0) {
                container.innerHTML = '<p class="text-sm text-gray-500 text-center py-8">No processed files yet. Run processing to create reports.</p>';
                return;
            }
            
            let html = '';
            tree.forEach((fyNode, fyIdx) => {
                const fy = fyNode.financial_year;
                html += `
                    <div class="mb-2">
                        <div class="flex items-center space-x-2 px-2 py-2 rounded-lg hover:bg-gray-50 cursor-pointer" onclick="toggleFY('${fy}')">
                            <svg id="fy-icon-${fy}" class="w-4 h-4 text-gray-500 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                            </svg>
                            <span class="text-sm font-semibold text-gray-800">${fy}</span>
                        </div>
                        <div id="fy-children-${fy}" class="ml-6 hidden">
                `;
                
                fyNode.months.forEach(monthNode => {
                    const mn = monthNode.month_name;
                    const count = monthNode.file_count;
                    html += `
                        <div class="flex items-center space-x-2 px-2 py-1.5 rounded-lg hover:bg-blue-50 cursor-pointer transition-colors" 
                             onclick="selectMonth('${fy}', '${mn}')"
                             id="month-item-${fy}-${mn}">
                            <svg class="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                            </svg>
                            <span class="text-xs font-medium text-gray-700">${mn}</span>
                            <span class="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full">${count}</span>
                        </div>
                    `;
                });
                
                html += '</div></div>';
            });
            
            container.innerHTML = html;
        }

        function toggleFY(fy) {
            const children = document.getElementById(`fy-children-${fy}`);
            const icon = document.getElementById(`fy-icon-${fy}`);
            if (children.classList.contains('hidden')) {
                children.classList.remove('hidden');
                icon.classList.add('rotate-90');
            } else {
                children.classList.add('hidden');
                icon.classList.remove('rotate-90');
            }
        }

        async function selectMonth(fy, month) {
            // Highlight selected
            document.querySelectorAll('[id^="month-item-"]').forEach(el => {
                el.classList.remove('bg-blue-100', 'border-l-2', 'border-blue-500');
            });
            const selected = document.getElementById(`month-item-${fy}-${month}`);
            if (selected) {
                selected.classList.add('bg-blue-100', 'border-l-2', 'border-blue-500');
            }
            
            currentSelectedFY = fy;
            currentSelectedMonth = month;
            
            document.getElementById('processed-files-title').textContent = `${fy} > ${month}`;
            
            await loadProcessedFiles(fy, month);
        }

        async function loadProcessedFiles(fy, month) {
            try {
                const data = await apiCall(`/api/processed/files?financial_year=${encodeURIComponent(fy)}&month_name=${encodeURIComponent(month)}`);'''
    if old_render in content:
        content = content.replace(old_render, new_render)
    else:
        print("Failed to replace chunk 3")

    # 4. delete process logic
    old_del = '''            if (data.success) {
                showToast('File deleted successfully', 'success');
                // Refresh the current view
                if (currentSelectedFY && currentSelectedType && currentSelectedMonth) {
                    await loadProcessedFiles(currentSelectedFY, currentSelectedType, currentSelectedMonth);
                }
                await loadDashboardStats();'''
    new_del = '''            if (data.success) {
                showToast('File deleted successfully', 'success');
                // Refresh the current view
                if (currentSelectedFY && currentSelectedMonth) {
                    await loadProcessedFiles(currentSelectedFY, currentSelectedMonth);
                }
                await loadDashboardStats();'''
    if old_del in content:
        content = content.replace(old_del, new_del)
    else:
        print("Failed to replace chunk 4")

    # 5. processAllRules logic
    old_proc = '''            // Validate custom output filename
            const customFilenameInput = document.getElementById('custom-output-filename');
            const customFilename = customFilenameInput ? customFilenameInput.value.trim() : '';
            if (!customFilename) {
                btn.disabled = false;
                spinner.classList.add('hidden');
                showToast('Please enter a custom output file name', 'error');
                if (customFilenameInput) customFilenameInput.focus();
                return;
            }'''
    new_proc = '''            // Validate custom output filename
            const monthInput = document.getElementById('output-month');
            const yearInput = document.getElementById('output-year');
            const month = monthInput ? monthInput.value : '';
            const year = yearInput ? yearInput.value : '';
            if (!month || !year) {
                btn.disabled = false;
                spinner.classList.add('hidden');
                showToast('Please select both Month and Year', 'error');
                return;
            }
            const customFilename = `Reconciliation Report ${month} ${year}`;'''
    
    if old_proc in content:
        content = content.replace(old_proc, new_proc)
    else:
        print("Failed to replace chunk 5")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        print("Patched index.html")

patch_file()
