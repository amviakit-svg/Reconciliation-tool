
        // ==================== GLOBAL STATE ====================
        const API_BASE = '';
        let currentFolderId = 1;
        let selectedItems = new Set();
        let allFolders = [];
        let allFiles = [];
        let matchingRuleCounter = 1;
        let remarksGroupCounter = 1;
        
        // ==================== EXCEL COLUMN HELPERS ====================
        
        /**
         * Convert a number to Excel column letter (1=A, 26=Z, 27=AA, 702=ZZ)
         */
        function numberToColumnLetter(num) {
            let result = '';
            while (num > 0) {
                num--;
                result = String.fromCharCode(65 + (num % 26)) + result;
                num = Math.floor(num / 26);
            }
            return result;
        }
        
        /**
         * Convert Excel column letter to number (A=1, Z=26, AA=27, ZZ=702)
         */
        function columnLetterToNumber(letter) {
            let result = 0;
            for (let i = 0; i < letter.length; i++) {
                result = result * 26 + (letter.charCodeAt(i) - 64);
            }
            return result;
        }
        
        /**
         * Generate dropdown options for Excel columns (A to ZZ)
         * @param {string} selectedValue - Currently selected column letter
         * @param {Array} usedColumns - Array of already-used column letters to mark as disabled
         */
        function generateColumnLetterOptions(selectedValue = '', usedColumns = []) {
            let options = '<option value="">-- Select --</option>';
            for (let i = 1; i <= 702; i++) {
                const letter = numberToColumnLetter(i);
                const isSelected = letter === selectedValue ? 'selected' : '';
                const isUsed = usedColumns.includes(letter) && letter !== selectedValue;
                const disabled = isUsed ? 'disabled' : '';
                const cssClass = isUsed ? 'text-gray-400 bg-gray-100' : '';
                options += `<option value="${letter}" ${isSelected} ${disabled} class="${cssClass}">${letter}</option>`;
            }
            return options;
        }
        
        /**
         * Get all currently used output columns from Phase 2 and Phase 3
         */
        function getAllUsedOutputColumns() {
            const used = [];
            
            // Phase 2 rules
            document.querySelectorAll('#matching-rules-body .rule-output-column').forEach(input => {
                const val = input.value?.trim();
                if (val) used.push(val);
            });
            
            // Phase 3 remark groups
            document.querySelectorAll('.group-output-col').forEach(input => {
                const val = input.value?.trim();
                if (val) used.push(val);
            });
            
            return used;
        }
        
        /**
         * Get the next available column letter
         * CRITICAL: Starts from D (column 4) to reserve A, B, C for primary data
         */
        function getNextAvailableColumn() {
            const used = getAllUsedOutputColumns();
            const MIN_COLUMN_NUMBER = 4; // D
            for (let i = MIN_COLUMN_NUMBER; i <= 702; i++) {
                const letter = numberToColumnLetter(i);
                if (!used.includes(letter)) {
                    return letter;
                }
            }
            return null; // All columns used (shouldn't happen)
        }
        
        /**
         * Find the first gap in column sequence and return that letter,
         * or return the next available letter after the last one
         * CRITICAL: Starts from D (column 4) to reserve A, B, C for primary data
         */
        function getAutoAssignedColumn() {
            const used = getAllUsedOutputColumns();
            
            // CRITICAL FIX: Reserve columns A, B, C for primary data columns
            // (Unique_ID, Source_File_Name, Primary_Value)
            // Always start auto-assignment from column D (number 4)
            const MIN_COLUMN_NUMBER = 4; // D
            
            if (used.length === 0) {
                return numberToColumnLetter(MIN_COLUMN_NUMBER);
            }
            
            // Sort by numeric value
            const usedNumbers = used.map(col => columnLetterToNumber(col)).sort((a, b) => a - b);
            
            // Find first gap starting from MIN_COLUMN_NUMBER
            let expected = MIN_COLUMN_NUMBER;
            for (const num of usedNumbers) {
                if (num < expected) continue; // Skip primary columns if present
                if (num > expected) {
                    return numberToColumnLetter(expected);
                }
                expected = num + 1;
            }
            
            // No gap found, return next after last
            return numberToColumnLetter(Math.max(expected, MIN_COLUMN_NUMBER));
        }
        
        /**
         * Resequence all output columns to fill gaps (D, E, F... with no gaps)
         * This is called after a row/group is deleted
         * CRITICAL: Starts from D (column 4) to reserve A, B, C for primary data
         */
        function resequenceOutputColumns() {
            // Collect all output column elements with their current values
            const phase2Elements = [];
            document.querySelectorAll('#matching-rules-body .rule-output-column').forEach(el => {
                if (el.value?.trim()) {
                    phase2Elements.push({ element: el, oldValue: el.value.trim() });
                }
            });
            
            const phase3Elements = [];
            document.querySelectorAll('.group-output-col').forEach(el => {
                if (el.value?.trim()) {
                    phase3Elements.push({ element: el, oldValue: el.value.trim() });
                }
            });
            
            // Combine and sort by current column letter
            const allElements = [...phase2Elements, ...phase3Elements];
            allElements.sort((a, b) => columnLetterToNumber(a.oldValue) - columnLetterToNumber(b.oldValue));
            
            // Reassign sequentially starting from D (column 4) to reserve A, B, C for primary data
            const MIN_COLUMN_NUMBER = 4; // D
            allElements.forEach((item, index) => {
                const newLetter = numberToColumnLetter(index + MIN_COLUMN_NUMBER);
                if (item.oldValue !== newLetter) {
                    item.element.value = newLetter;
                    // Trigger change event to update any dependent UI
                    item.element.dispatchEvent(new Event('change'));
                }
            });
            
            // Update all dropdowns to reflect new used columns
            refreshAllColumnDropdowns();
        }
        
        /**
         * Refresh all output column dropdowns to show currently used columns as disabled
         */
        function refreshAllColumnDropdowns() {
            const used = getAllUsedOutputColumns();
            
            // Update Phase 2 dropdowns
            document.querySelectorAll('#matching-rules-body .rule-output-column').forEach(select => {
                const currentValue = select.value;
                select.innerHTML = generateColumnLetterOptions(currentValue, used);
            });
            
            // Update Phase 3 dropdowns
            document.querySelectorAll('.group-output-col').forEach(select => {
                const currentValue = select.value;
                select.innerHTML = generateColumnLetterOptions(currentValue, used);
            });
        }
        
        let currentFileDetails = null;
        let rulePageLoadPromise = null;
        let isRulesPageLoaded = false;

        // ==================== UTILITY FUNCTIONS ====================
        function showToast(message, type = 'success', suggestion = null) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            const colors = {
                success: 'bg-green-50 border-green-200 text-green-800',
                error: 'bg-red-50 border-red-200 text-red-800',
                warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
                info: 'bg-blue-50 border-blue-200 text-blue-800'
            };
            
            const suggestionHtml = suggestion ? `
                <div class="mt-2 pt-2 border-t border-red-100">
                    <p class="text-xs font-semibold text-red-700">Suggestion:</p>
                    <p class="text-xs text-red-600 mt-0.5">${suggestion}</p>
                </div>
            ` : '';
            
            toast.className = `toast ${colors[type]} border rounded-lg p-4 shadow-lg max-w-sm`;
            toast.innerHTML = `
                <div class="flex items-start space-x-3">
                    <div class="flex-1 min-w-0">
                        <span class="font-medium text-sm block">${message}</span>
                        ${suggestionHtml}
                    </div>
                    <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-gray-400 hover:text-gray-600 flex-shrink-0">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            `;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 8000);
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.add('hidden');
        }

        function showModal(modalId) {
            document.getElementById(modalId).classList.remove('hidden');
        }

        async function apiCall(url, options = {}) {
            const maxRetries = 3;
            let lastError;
            
            for (let attempt = 1; attempt <= maxRetries; attempt++) {
                try {
                    // Inject JWT token from SaaS localStorage if present
                    const token = localStorage.getItem('access_token');
                    if (token) {
                        options.headers = {
                            ...(options.headers || {}),
                            'Authorization': `Bearer ${token}`
                        };
                    }
                    const response = await fetch(url, options);
                    
                    if (!response.ok) {
                        // Handle HTTP errors with detailed diagnostics
                        const errorData = await response.json().catch(() => ({}));
                        const errorMsg = errorData.detail || `HTTP ${response.status}: ${response.statusText}`;
                        const suggestion = errorData.suggestion || null;
                        
                        // Enhanced logging for 422 errors
                        if (response.status === 422) {
                            console.group(`🔴 422 Validation Error: ${url}`);
                            console.error(`Endpoint: ${options.method || 'GET'} ${url}`);
                            console.error(`Status: ${response.status} ${response.statusText}`);
                            if (errorData.detail && Array.isArray(errorData.detail)) {
                                console.error('Field Errors:');
                                errorData.detail.forEach((err, idx) => {
                                    console.error(`  ${idx + 1}. Field: "${err.field}" | Issue: ${err.message} | Type: ${err.type}`);
                                });
                            } else {
                                console.error('Response:', errorData);
                            }
                            if (options.body) {
                                const bodyPreview = typeof options.body === 'string' 
                                    ? options.body.substring(0, 500) 
                                    : (options.body instanceof FormData 
                                        ? `FormData with ${Array.from(options.body.entries()).length} fields` 
                                        : String(options.body).substring(0, 200));
                                console.error('Request Body:', bodyPreview);
                            }
                            console.groupEnd();
                        }
                        
                        // Attach suggestion to the error for later use
                        const err = new Error(errorMsg);
                        err.suggestion = suggestion;
                        throw err;
                    }
                    
                    const data = await response.json();
                    return data;
                } catch (error) {
                    lastError = error;
                    
                    // Check if it's a network error that might be temporary (like ERR_NETWORK_CHANGED)
                    const isNetworkError = error.name === 'TypeError' || 
                                           error.message.includes('Failed to fetch') ||
                                           error.message.includes('NetworkError') ||
                                           error.message.includes('network');
                    
                    if (isNetworkError && attempt < maxRetries) {
                        // Wait before retrying (exponential backoff)
                        await new Promise(resolve => setTimeout(resolve, attempt * 1000));
                        console.log(`Retrying API call to ${url}, attempt ${attempt + 1}/${maxRetries}`);
                        continue;
                    }
                    
                    // Non-network error or final attempt - show toast with suggestion if available
                    showToast(`Error: ${error.message}`, 'error', error.suggestion || null);
                    throw error;
                }
            }
            
            throw lastError;
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // ==================== FORM VALIDATION HELPERS ====================
        function showFieldError(elementId, message) {
            const el = document.getElementById(elementId);
            if (!el) return;
            _applyFieldError(el, message);
        }

        function showElementError(element, message) {
            if (!element) return;
            _applyFieldError(element, message);
        }

        function _applyFieldError(el, message) {
            if (!el) return;
            
            // Add error styling to the element itself
            el.classList.add('field-error');
            
            // For table rows (Phase 2), highlight the entire row
            const tableRow = el.closest('tr');
            if (tableRow) {
                tableRow.classList.add('field-error-row');
                // Also add error class to the cell containing this element
                const cell = el.closest('td');
                if (cell) cell.classList.add('field-error-cell');
            }
            
            // Find the closest container (div, td, or the element's parent)
            let container = el.closest('div, td, .space-y-2, .space-y-1');
            if (!container) container = el.parentElement;
            
            if (container) {
                // Find label inside container
                const label = container.querySelector('label, .text-xs.font-medium');
                if (label) label.classList.add('field-error-label');
                
                // Also highlight label that directly precedes this element
                const prevLabel = el.previousElementSibling;
                if (prevLabel && (prevLabel.tagName === 'LABEL' || prevLabel.classList.contains('text-xs'))) {
                    prevLabel.classList.add('field-error-label');
                }
                
                // Remove any existing error text in this container
                const existingError = container.querySelector('.field-error-text');
                if (existingError) existingError.remove();
                
                // Add error message - for table cells, insert after the last select/input in the cell
                const errorDiv = document.createElement('div');
                errorDiv.className = 'field-error-text';
                errorDiv.textContent = message;
                container.appendChild(errorDiv);
            }
        }

        function clearFieldErrors() {
            // Remove all error styles
            document.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
            document.querySelectorAll('.field-error-label').forEach(el => el.classList.remove('field-error-label'));
            document.querySelectorAll('.field-error-text').forEach(el => el.remove());
            document.querySelectorAll('.field-error-row').forEach(el => el.classList.remove('field-error-row'));
            document.querySelectorAll('.field-error-cell').forEach(el => el.classList.remove('field-error-cell'));
        }

        function scrollToFirstError() {
            const firstError = document.querySelector('.field-error');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Also focus if it's an input/select
                if (firstError.focus && (firstError.tagName === 'INPUT' || firstError.tagName === 'SELECT' || firstError.tagName === 'TEXTAREA')) {
                    setTimeout(() => firstError.focus(), 300);
                }
            }
        }

        // ==================== TAB NAVIGATION ====================
        function switchTab(tabName) {
            // Hide all pages
            document.querySelectorAll('.page-content').forEach(el => el.classList.add('hidden'));
            // Show selected page
            document.getElementById(`page-${tabName}`).classList.remove('hidden');
            
            // Update tab styles
            document.querySelectorAll('nav button').forEach(btn => {
                btn.classList.remove('tab-active');
                btn.classList.add('tab-inactive');
            });
            document.getElementById(`tab-${tabName}`).classList.remove('tab-inactive');
            document.getElementById(`tab-${tabName}`).classList.add('tab-active');

            // Save to URL hash for persistence
            window.location.hash = tabName;

            // Load data for specific tabs
            if (tabName === 'upload') {
                loadFolders();
                loadFiles(currentFolderId);
                updateFolderSelects();
            } else if (tabName === 'dashboard') {
                // Load from cache first for instant render, then refresh from API
                loadCachedDashboardData();
                loadDashboardStats();
                loadProcessedTree();
                startDashboardAutoRefresh();
            } else if (tabName === 'rules') {
                loadRulePageData();
                stopDashboardAutoRefresh();
            } else if (tabName === 'process') {
                // Load from cache first for instant render, then refresh from API
                loadCachedProcessData();
                loadFinalProcessedHistory();
                loadSourceFileFilter();
                startDashboardAutoRefresh();
            } else if (tabName === 'recycle') {
                loadRecycleBin();
                stopDashboardAutoRefresh();
            }
        }

        // Restore tab from URL hash on page load
        function restoreTabFromHash() {
            const hash = window.location.hash.replace('#', '');
            const validTabs = ['dashboard', 'upload', 'rules', 'process'];
            if (hash && validTabs.includes(hash)) {
                switchTab(hash);
            } else {
                switchTab('dashboard');
            }
        }

        // ==================== DASHBOARD CACHING & AUTO-REFRESH ====================
        let dashboardAutoRefreshInterval = null;
        
        function loadCachedDashboardData() {
            try {
                const cached = localStorage.getItem('dashboard_tree_data');
                if (cached) {
                    const data = JSON.parse(cached);
                    if (data.tree) renderProcessedTree(data.tree);
                    if (data.stats) updateDashboardStats(data.stats);
                }
            } catch (e) {
                // Ignore cache errors, will load from API
            }
        }
        
        function loadCachedProcessData() {
            try {
                const cached = localStorage.getItem('process_history_data');
                if (cached) {
                    const data = JSON.parse(cached);
                    if (data.files) renderProcessedFiles(data.files);
                }
            } catch (e) {
                // Ignore cache errors, will load from API
            }
        }
        
        function saveDashboardCache(tree, stats) {
            try {
                localStorage.setItem('dashboard_tree_data', JSON.stringify({
                    tree: tree,
                    stats: stats,
                    timestamp: Date.now()
                }));
            } catch (e) {
                // Ignore storage errors
            }
        }
        
        function saveProcessCache(files) {
            try {
                localStorage.setItem('process_history_data', JSON.stringify({
                    files: files,
                    timestamp: Date.now()
                }));
            } catch (e) {
                // Ignore storage errors
            }
        }
        
        function startDashboardAutoRefresh() {
            if (dashboardAutoRefreshInterval) clearInterval(dashboardAutoRefreshInterval);
            dashboardAutoRefreshInterval = setInterval(async () => {
                const currentTab = window.location.hash.replace('#', '') || 'dashboard';
                if (currentTab === 'dashboard') {
                    await loadDashboardStats();
                    await loadProcessedTree();
                } else if (currentTab === 'process') {
                    await loadFinalProcessedHistory();
                }
            }, 30000); // Refresh every 30 seconds
        }
        
        function stopDashboardAutoRefresh() {
            if (dashboardAutoRefreshInterval) {
                clearInterval(dashboardAutoRefreshInterval);
                dashboardAutoRefreshInterval = null;
            }
        }

        // ==================== DASHBOARD ====================
        async function loadDashboardStats() {
            const data = await apiCall('/api/dashboard/stats');
            if (!data.success) return;

            // Safely set stats - only update elements that exist in the DOM
            const setText = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val ?? 0;
            };
            setText('dash-total-files', data.stats.total_files);
            setText('dash-processed-files', data.stats.processed_files); // mapped from backend
            setText('dash-financial-years', data.stats.financial_years);
            setText('dash-report-types', data.stats.report_types);
            setText('dash-months-covered', data.stats.months);
            
            // Save to cache for instant render on next tab switch
            saveDashboardCache(null, data.stats);
        }

        // ==================== UPLOAD & FILE MANAGEMENT ====================
        
        // Drag and drop
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');

        dropZone.addEventListener('click', () => fileInput.click());
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            fileInput.files = e.dataTransfer.files;
            showSelectedFiles();
            detectFolderForFiles();
        });

        fileInput.addEventListener('change', () => {
            showSelectedFiles();
            detectFolderForFiles();
        });

        function showSelectedFiles() {
            const files = fileInput.files;
            const previewDiv = document.getElementById('selected-files-preview');
            const listDiv = document.getElementById('selected-files-list');
            
            if (!files.length) {
                previewDiv.classList.add('hidden');
                return;
            }

            previewDiv.classList.remove('hidden');
            listDiv.innerHTML = Array.from(files).map(file => `
                <div class="flex items-center space-x-3 p-2 bg-gray-50 rounded-lg">
                    <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-900 truncate">${file.name}</p>
                        <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                    </div>
                </div>
            `).join('');
        }

        function clearSelectedFiles() {
            fileInput.value = '';
            document.getElementById('selected-files-preview').classList.add('hidden');
        }

        // Auto folder detection based on filename patterns
        function detectFolderForFiles() {
            const files = fileInput.files;
            if (!files.length || !allFolders.length) return;

            // Extract patterns from filenames (e.g., "Sales_Jan2024.xlsx" -> suggest "Sales" or "Jan2024")
            const patterns = new Map();
            
            for (const file of files) {
                const name = file.name.replace(/\.[^/.]+$/, ''); // Remove extension
                const parts = name.split(/[_\-\s]+/); // Split by underscore, hyphen, space
                
                for (const part of parts) {
                    if (part.length < 2) continue; // Skip short parts
                    const count = patterns.get(part) || 0;
                    patterns.set(part, count + 1);
                }
            }

            // Find the most common pattern
            let bestPattern = '';
            let maxCount = 0;
            for (const [pattern, count] of patterns) {
                if (count > maxCount && pattern.length > 2) {
                    maxCount = count;
                    bestPattern = pattern;
                }
            }

            // Try to find a matching folder
            const uploadSelect = document.getElementById('upload-folder-select');
            let matchedFolderId = null;
            
            for (const folder of allFolders) {
                if (folder.name.toLowerCase().includes(bestPattern.toLowerCase()) ||
                    bestPattern.toLowerCase().includes(folder.name.toLowerCase())) {
                    matchedFolderId = folder.id;
                    break;
                }
            }

            // Show suggestion to user
            if (matchedFolderId && matchedFolderId != uploadSelect.value) {
                const folderName = allFolders.find(f => f.id == matchedFolderId)?.name || '';
                showToast(`Suggested folder "${folderName}" detected based on filename pattern`, 'info');
                uploadSelect.value = matchedFolderId;
            }
        }

        async function uploadFiles() {
            const files = fileInput.files;
            if (!files.length) {
                showToast('Please select files to upload', 'warning');
                return;
            }

            const folderId = document.getElementById('upload-folder-select').value;
            const progressDiv = document.getElementById('upload-progress');
            progressDiv.classList.remove('hidden');

            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('folder_id', folderId);

                try {
                    const data = await apiCall('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (data.success) {
                        showToast(`Uploaded: ${file.name}`, 'success');
                    } else {
                        showToast(`Failed to upload: ${file.name}`, 'error');
                    }
                } catch (error) {
                    showToast(`Error uploading: ${file.name}`, 'error');
                }
            }

            progressDiv.classList.add('hidden');
            fileInput.value = '';
            loadFiles(currentFolderId);
            loadDashboardStats();
        }

        // Folder Management
        async function loadFolders() {
            const data = await apiCall('/api/folders');
            if (data.success) {
                allFolders = data.folders;
                renderFolderTree(data.folders);
                updateFolderSelects();
            }
        }

        function renderFolderTree(folders) {
            const container = document.getElementById('folder-tree');
            container.innerHTML = '';
            
            function renderFolder(folder, level = 0) {
                const div = document.createElement('div');
                div.className = `folder-tree-item flex items-center space-x-2 px-3 py-2 rounded-lg ${folder.id === currentFolderId ? 'folder-selected' : ''}`;
                div.style.paddingLeft = `${12 + (level * 16)}px`;
                div.onclick = () => selectFolder(folder.id);
                
                div.innerHTML = `
                    <svg class="w-4 h-4 text-yellow-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path>
                    </svg>
                    <span class="flex-1 text-sm font-medium text-gray-700 truncate">${folder.name}</span>
                    ${folder.id !== 1 && folder.name !== 'Root' ? `
                        <button onclick="event.stopPropagation(); renameFolder(${folder.id}, '${folder.name.replace(/'/g, "\\'")}')" class="p-1 text-blue-400 hover:text-blue-600 rounded hover:bg-blue-50 transition-colors opacity-0 group-hover:opacity-100" title="Rename folder">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                        </button>
                        <button onclick="event.stopPropagation(); deleteFolder(${folder.id})" class="p-1 text-red-400 hover:text-red-600 rounded hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100" title="Delete folder">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    ` : ''}
                `;
                div.classList.add('group');
                
                container.appendChild(div);
                
                // Render children
                const children = folders.filter(f => f.parent_id === folder.id);
                children.forEach(child => renderFolder(child, level + 1));
            }

            // Start with root - find by name or parent_id === null
            const root = folders.find(f => f.name === 'Root' || f.parent_id === null);
            if (root) {
                renderFolder(root);
            } else {
                // Fallback: render all top-level folders
                const topLevel = folders.filter(f => f.parent_id === null);
                topLevel.forEach(folder => renderFolder(folder));
            }
        }

        async function selectFolder(folderId) {
            currentFolderId = folderId;
            selectedItems.clear();
            updateSelectedCount();
            loadFolders(); // Re-render to update selection
            loadFiles(folderId);
            
            const folder = allFolders.find(f => f.id === folderId);
            document.getElementById('current-folder-name').textContent = folder ? folder.name : 'Root';
            
            // Show/hide master file button
            document.getElementById('master-file-btn').classList.remove('hidden');
            
            // Check if master file exists and show/hide View button
            try {
                const masterData = await apiCall(`/api/master/${folderId}`);
                const viewBtn = document.getElementById('view-master-btn');
                if (masterData.success && masterData.master && masterData.master.exists) {
                    viewBtn.classList.remove('hidden');
                } else {
                    viewBtn.classList.add('hidden');
                }
            } catch (error) {
                document.getElementById('view-master-btn').classList.add('hidden');
            }
        }

        function getFolderDisplayPath(folder) {
            // Build a clean name-based display path by traversing parent_id
            if (!folder) return 'Unknown';
            if (folder.name === 'Root' && folder.parent_id === null) return 'Root';
            
            const pathParts = [];
            let current = folder;
            const visited = new Set();
            
            while (current) {
                if (visited.has(current.id)) break; // Prevent infinite loop
                visited.add(current.id);
                pathParts.unshift(current.name);
                
                if (current.parent_id === null || current.parent_id === current.id) break;
                current = allFolders.find(f => f.id === current.parent_id);
            }
            
            return pathParts.join(' > ');
        }

        function updateFolderSelects() {
            const selects = ['upload-folder-select', 'new-folder-parent', 'move-target-folder'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (!select) return;
                const currentValue = select.value;
                select.innerHTML = allFolders.map(f => 
                    `<option value="${f.id}">${getFolderDisplayPath(f)}</option>`
                ).join('');
                if (currentValue) select.value = currentValue;
            });
        }

        async function loadFiles(folderId) {
            const data = await apiCall(`/api/files/${folderId}`);
            if (data.success) {
                allFiles = data.files;
                renderFileList(data.files);
            }
        }

        function renderFileList(files) {
            const container = document.getElementById('file-list');
            
            if (files.length === 0) {
                container.innerHTML = '<p class="text-gray-500 text-sm text-center py-8">No files in this folder</p>';
                return;
            }

            container.innerHTML = files.map(file => `
                <div class="file-row flex items-center space-x-3 p-3 rounded-lg border border-gray-100 hover:border-gray-200 transition-all cursor-pointer" 
                     onclick="toggleItemSelection('file', ${file.id})"
                     ondblclick="showFileDetails(${file.id})">
                    <input type="checkbox" class="item-checkbox" data-type="file" data-id="${file.id}" 
                           ${selectedItems.has(`file-${file.id}`) ? 'checked' : ''}
                           onclick="event.stopPropagation(); toggleItemSelection('file', ${file.id})">
                    <svg class="w-5 h-5 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-900 truncate">${file.original_name}</p>
                        <p class="text-xs text-gray-500">${formatFileSize(file.size)} • ${file.format} • ${file.sheet_count} sheets</p>
                    </div>
                    <div class="flex items-center space-x-1">
                        <button onclick="event.stopPropagation(); showFileDetails(${file.id})" class="p-1.5 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 transition-colors" title="View Details">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            `).join('');
        }

        function toggleItemSelection(type, id) {
            const key = `${type}-${id}`;
            if (selectedItems.has(key)) {
                selectedItems.delete(key);
            } else {
                selectedItems.add(key);
            }
            updateSelectedCount();
            renderFileList(allFiles); // Re-render to update checkboxes
        }

        function updateSelectedCount() {
            document.getElementById('selected-count').textContent = `${selectedItems.size} selected`;
        }

        function toggleSelectAll() {
            const checkbox = document.getElementById('select-all-checkbox');
            const isChecked = checkbox.checked;
            
            if (isChecked) {
                // Select all files in current folder
                allFiles.forEach(file => {
                    selectedItems.add(`file-${file.id}`);
                });
            } else {
                // Deselect all files
                allFiles.forEach(file => {
                    selectedItems.delete(`file-${file.id}`);
                });
            }
            
            updateSelectedCount();
            renderFileList(allFiles); // Re-render to update checkboxes
        }

        function refreshFileManager() {
            loadFolders();
            loadFiles(currentFolderId);
        }

        // Folder Actions
        function showCreateFolderModal() {
            showModal('create-folder-modal');
        }

        async function createFolder() {
            const name = document.getElementById('new-folder-name').value.trim();
            const parentId = document.getElementById('new-folder-parent').value;
            
            if (!name) {
                showToast('Please enter a folder name', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('name', name);
            formData.append('parent_id', String(parentId || '1'));

            const data = await apiCall('/api/folders', {
                method: 'POST',
                body: formData
            });

            if (data.success) {
                showToast('Folder created successfully', 'success');
                closeModal('create-folder-modal');
                document.getElementById('new-folder-name').value = '';
                loadFolders();
                loadDashboardStats();
            }
        }

        function showMoveItemsModal() {
            if (selectedItems.size === 0) {
                showToast('Please select items to move', 'warning');
                return;
            }
            showModal('move-items-modal');
        }

        async function executeMove() {
            const targetFolderId = document.getElementById('move-target-folder').value;
            
            for (const itemKey of selectedItems) {
                const [type, id] = itemKey.split('-');
                if (type === 'file') {
                    const formData = new FormData();
                    formData.append('file_id', String(id));
                    formData.append('new_folder_id', String(targetFolderId));
                    
                    await apiCall('/api/files/move', {
                        method: 'POST',
                        body: formData
                    });
                }
            }
            
            showToast('Items moved successfully', 'success');
            closeModal('move-items-modal');
            selectedItems.clear();
            updateSelectedCount();
            loadFiles(currentFolderId);
        }

        // Rename file functionality
        function renameSelectedFile() {
            // Only allow renaming a single file at a time
            const selectedFileItems = Array.from(selectedItems).filter(key => key.startsWith('file-'));
            
            if (selectedFileItems.length === 0) {
                showToast('Please select a file to rename', 'warning');
                return;
            }
            
            if (selectedFileItems.length > 1) {
                showToast('Please select only one file to rename', 'warning');
                return;
            }
            
            const fileId = selectedFileItems[0].replace('file-', '');
            const file = allFiles.find(f => f.id == fileId);
            
            if (!file) {
                showToast('File not found', 'error');
                return;
            }
            
            // Pre-fill with current file name (without extension for cleaner editing)
            const currentName = file.original_name;
            const nameWithoutExt = currentName.replace(/\.[^/.]+$/, '');
            
            document.getElementById('rename-file-input').value = nameWithoutExt;
            document.getElementById('rename-file-input').dataset.fileId = fileId;
            document.getElementById('rename-file-input').dataset.originalName = currentName;
            
            showModal('rename-file-modal');
            
            // Focus and select the input text after modal opens
            setTimeout(() => {
                const input = document.getElementById('rename-file-input');
                input.focus();
                input.select();
            }, 100);
        }

        async function executeRename() {
            const input = document.getElementById('rename-file-input');
            const fileId = input.dataset.fileId;
            let newName = input.value.trim();
            const originalName = input.dataset.originalName;
            
            if (!newName) {
                showToast('Please enter a file name', 'warning');
                return;
            }
            
            // Preserve original extension if user didn't include one
            const originalExt = originalName.match(/\.[^/.]+$/)?.[0] || '';
            const hasExtension = /\.[^/.]+$/.test(newName);
            if (!hasExtension && originalExt) {
                newName = newName + originalExt;
            }
            
            // Don't rename if name hasn't changed
            if (newName === originalName) {
                closeModal('rename-file-modal');
                showToast('No changes made', 'info');
                return;
            }
            
            const formData = new FormData();
            formData.append('new_name', newName);
            
            try {
                const data = await apiCall(`/api/files/${fileId}/rename`, {
                    method: 'POST',
                    body: formData
                });
                
                if (data.success) {
                    showToast(`File renamed to "${newName}"`, 'success');
                    closeModal('rename-file-modal');
                    
                    // Clear selection and refresh
                    selectedItems.clear();
                    updateSelectedCount();
                    loadFiles(currentFolderId);
                    loadDashboardStats();
                } else {
                    showToast(data.message || 'Rename failed', 'error');
                }
            } catch (error) {
                showToast('Rename failed: ' + error.message, 'error');
            }
        }

        // Allow Enter key to submit rename
        document.addEventListener('DOMContentLoaded', () => {
            const renameFileInput = document.getElementById('rename-file-input');
            if (renameFileInput) {
                renameFileInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        executeRename();
                    }
                });
            }
            const renameFolderInput = document.getElementById('rename-folder-input');
            if (renameFolderInput) {
                renameFolderInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        executeRenameFolder();
                    }
                });
            }
        });

        async function deleteSelectedItems() {
            if (selectedItems.size === 0) {
                showToast('Please select items to delete', 'warning');
                return;
            }

            if (!confirm('Are you sure you want to delete the selected items?')) return;

            for (const itemKey of selectedItems) {
                const [type, id] = itemKey.split('-');
                if (type === 'file') {
                    await apiCall(`/api/files/${id}`, { method: 'DELETE' });
                } else if (type === 'folder') {
                    await apiCall(`/api/folders/${id}`, { method: 'DELETE' });
                }
            }

            showToast('Items deleted successfully', 'success');
            selectedItems.clear();
            updateSelectedCount();
            loadFolders();
            loadFiles(currentFolderId);
            loadDashboardStats();
        }

        async function deleteFolder(folderId) {
            if (!folderId) return;
            if (folderId === 1) {
                showToast('Root folder cannot be deleted', 'warning');
                return;
            }
            if (!confirm('Are you sure you want to delete this folder? All files inside will also be deleted.')) return;

            try {
                const data = await apiCall(`/api/folders/${folderId}`, { method: 'DELETE' });
                if (data.success) {
                    showToast('Folder deleted successfully', 'success');
                    if (currentFolderId === folderId) {
                        currentFolderId = 1;
                        loadFiles(1);
                    }
                    loadFolders();
                    loadDashboardStats();
                } else {
                    showToast(data.message || 'Delete failed', 'error');
                }
            } catch (error) {
                showToast('Delete failed: ' + error.message, 'error');
            }
        }

        // Rename folder functionality
        function renameFolder(folderId, currentName) {
            if (!folderId) return;
            if (folderId === 1) {
                showToast('Root folder cannot be renamed', 'warning');
                return;
            }
            
            document.getElementById('rename-folder-input').value = currentName;
            document.getElementById('rename-folder-input').dataset.folderId = folderId;
            document.getElementById('rename-folder-input').dataset.originalName = currentName;
            
            showModal('rename-folder-modal');
            
            setTimeout(() => {
                const input = document.getElementById('rename-folder-input');
                input.focus();
                input.select();
            }, 100);
        }

        async function executeRenameFolder() {
            const input = document.getElementById('rename-folder-input');
            const folderId = input.dataset.folderId;
            const newName = input.value.trim();
            const originalName = input.dataset.originalName;
            
            if (!newName) {
                showToast('Please enter a folder name', 'warning');
                return;
            }
            
            if (newName === originalName) {
                closeModal('rename-folder-modal');
                showToast('No changes made', 'info');
                return;
            }
            
            const formData = new FormData();
            formData.append('new_name', newName);
            
            try {
                const data = await apiCall(`/api/folders/${folderId}/rename`, {
                    method: 'POST',
                    body: formData
                });
                
                if (data.success) {
                    showToast(`Folder renamed to "${newName}"`, 'success');
                    closeModal('rename-folder-modal');
                    loadFolders();
                    loadDashboardStats();
                } else {
                    showToast(data.message || 'Rename failed', 'error');
                }
            } catch (error) {
                showToast('Rename failed: ' + error.message, 'error');
            }
        }

        // File Details
        async function showFileDetails(fileId) {
            const data = await apiCall(`/api/files/${fileId}/details`);
            if (data.success) {
                const file = data.file;
                const content = document.getElementById('file-details-content');
                
                let sheetsHtml = '';
                if (file.sheets_detail && file.sheets_detail.length > 0) {
                    sheetsHtml = `
                        <h4 class="text-sm font-semibold text-gray-700 mb-2">Sheets Detail</h4>
                        <div class="overflow-x-auto mb-4">
                            <table class="min-w-full text-sm border border-gray-200 rounded-lg">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2">Sheet Name</th>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2">Rows</th>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2">Columns</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${file.sheets_detail.map(s => `
                                        <tr class="border-t border-gray-100">
                                            <td class="px-3 py-2">${s.name}</td>
                                            <td class="px-3 py-2">${s.rows}</td>
                                            <td class="px-3 py-2">${s.columns}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                }

                content.innerHTML = `
                    <div class="space-y-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="bg-gray-50 rounded-lg p-3">
                                <p class="text-xs text-gray-500">Original Name</p>
                                <p class="text-sm font-medium text-gray-900">${file.original_name}</p>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-3">
                                <p class="text-xs text-gray-500">Size</p>
                                <p class="text-sm font-medium text-gray-900">${formatFileSize(file.size)}</p>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-3">
                                <p class="text-xs text-gray-500">Format</p>
                                <p class="text-sm font-medium text-gray-900">${file.format}</p>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-3">
                                <p class="text-xs text-gray-500">Total Sheets</p>
                                <p class="text-sm font-medium text-gray-900">${file.sheet_count}</p>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-3">
                                <p class="text-xs text-gray-500">Total Rows</p>
                                <p class="text-sm font-medium text-gray-900">${file.row_count}</p>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-3">
                                <p class="text-xs text-gray-500">Total Columns</p>
                                <p class="text-sm font-medium text-gray-900">${file.column_count}</p>
                            </div>
                        </div>
                        ${sheetsHtml}
                        <div class="bg-blue-50 rounded-lg p-3">
                            <p class="text-xs text-blue-600 font-medium">File Path</p>
                            <p class="text-xs text-blue-800 break-all">${file.file_path}</p>
                        </div>
                    </div>
                `;
                
                showModal('file-details-modal');
            }
        }

        // ==================== MASTER FILE ====================
        async function showMasterFileModal() {
            if (!currentFolderId) {
                showToast('Please select a folder first', 'warning');
                return;
            }

            // Check if there are files in the folder
            const filesData = await apiCall(`/api/files/${currentFolderId}`);
            if (!filesData.success || filesData.files.length === 0) {
                showToast('No files in this folder to merge', 'warning');
                return;
            }

            // Load saved config if available
            await loadSavedMasterConfig();

            showModal('master-file-modal');
        }

        async function loadSavedMasterConfig() {
            try {
                const data = await apiCall(`/api/master/config?folder_id=${currentFolderId}`);
                if (data.success && data.config && data.config.columns) {
                    // Show saved config info
                    document.getElementById('master-saved-config-info').classList.remove('hidden');
                    document.getElementById('master-no-config-info').classList.add('hidden');
                    document.getElementById('master-saved-columns').textContent = data.config.columns;
                    document.getElementById('master-config-timestamp').textContent = data.config.updated_at || 'Previously saved';
                    document.getElementById('master-column-names').value = data.config.columns;
                } else {
                    // Show no config info
                    document.getElementById('master-saved-config-info').classList.add('hidden');
                    document.getElementById('master-no-config-info').classList.remove('hidden');
                    // Only clear if no user input exists
                    const currentVal = document.getElementById('master-column-names').value.trim();
                    if (!currentVal) {
                        document.getElementById('master-column-names').value = '';
                    }
                }
            } catch (e) {
                showToast('Failed to load saved column config: ' + e.message, 'warning');
                // Don't clear on error - user may have typed something
            }
        }

        async function executeMasterMerge() {
            // Reset previous error states
            clearFieldErrors();
            
            const columnNamesInput = document.getElementById('master-column-names').value.trim();
            
            let hasError = false;
            let firstErrorElement = null;

            // Validate Column Names (mandatory)
            if (!columnNamesInput) {
                showFieldError('master-column-names', 'Please enter column names to merge');
                hasError = true;
                if (!firstErrorElement) firstErrorElement = document.getElementById('master-column-names');
            }

            if (hasError) {
                if (firstErrorElement) {
                    firstErrorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return;
            }

            const progressDiv = document.getElementById('merge-progress');
            const mergeBtn = document.getElementById('merge-btn');
            progressDiv.classList.remove('hidden');
            mergeBtn.disabled = true;

            const formData = new FormData();
            formData.append('folder_id', currentFolderId);
            formData.append('column_names', columnNamesInput);

            try {
                const data = await apiCall('/api/master/merge', {
                    method: 'POST',
                    body: formData
                });

                progressDiv.classList.add('hidden');
                mergeBtn.disabled = false;

                if (data.success) {
                    // Build success message with rejected files info
                    let message = `Successfully merged ${data.merged_files} files! ${data.rows} rows in master file.`;
                    
                    // Show instant popup notification for rejected files
                    if (data.rejected_files && data.rejected_files.length > 0) {
                        const rejectedCount = data.rejected_files.length;
                        message += ` (${rejectedCount} file(s) rejected)`;
                        
                        // Show warning toast with rejection summary
                        let rejectionDetails = data.rejected_files.map(r => `${r.file}: ${r.reason}`).join('\\n');
                        showToast(`${rejectedCount} file(s) rejected:\\n${rejectionDetails}`, 'warning');
                    }
                    
                    showToast(message, 'success');
                    
                    // Save the config for next time
                    try {
                        const saveForm = new FormData();
                        saveForm.append('folder_id', String(currentFolderId));
                        saveForm.append('columns', columnNamesInput);
                        await apiCall('/api/master/config', { method: 'POST', body: saveForm });
                    } catch (e) {
                        console.warn('Failed to save master config:', e);
                    }
                    
                    closeModal('master-file-modal');
                    loadDashboardStats();
                    document.getElementById('view-master-btn').classList.remove('hidden');
                    
                    // Refresh master view panel if it's open, or pre-load summary for next view
                    if (masterViewOpen) {
                        loadMasterSummary();
                    }
                } else {
                    showToast(data.message || 'Merge failed', 'error');
                }
            } catch (error) {
                progressDiv.classList.add('hidden');
                mergeBtn.disabled = false;
                showToast('Merge failed: ' + error.message, 'error');
            }
        }

        // ==================== MASTER FILE VIEW ====================
        let masterViewOpen = false;
        let masterPreviewDebounceTimer = null;

        function debouncedLoadMasterPreview() {
            clearTimeout(masterPreviewDebounceTimer);
            masterPreviewDebounceTimer = setTimeout(() => loadMasterPreview(), 400);
        }

        async function toggleMasterView() {
            const panel = document.getElementById('master-view-panel');
            
            if (masterViewOpen) {
                panel.classList.add('hidden');
                masterViewOpen = false;
                return;
            }
            
            if (!currentFolderId) {
                showToast('Please select a folder first', 'warning');
                return;
            }
            
            panel.classList.remove('hidden');
            masterViewOpen = true;
            
            // Load all data in parallel
            await Promise.all([
                loadMasterSummary(),
                loadSourceFilesDropdown(),
                loadMasterPreview(),
                loadMasterStats(),
                loadMasterValidation()
            ]);
        }

        async function loadMasterSummary() {
            try {
                const data = await apiCall(`/api/master/${currentFolderId}`);
                if (!data.success || !data.master || !data.master.exists) {
                    document.getElementById('master-total-rows').textContent = '-';
                    document.getElementById('master-merged-count').textContent = '-';
                    document.getElementById('master-rejected-count').textContent = '-';
                    document.getElementById('master-column-count').textContent = '-';
                    document.getElementById('master-config-section').classList.add('hidden');
                    return;
                }
                
                const master = data.master;
                document.getElementById('master-total-rows').textContent = master.row_count || 0;
                document.getElementById('master-merged-count').textContent = master.merged_files ? master.merged_files.length : 0;
                document.getElementById('master-rejected-count').textContent = master.rejected_files ? master.rejected_files.length : 0;
                
                // Count columns from the master
                try {
                    const previewData = await apiCall(`/api/master/${currentFolderId}/preview?limit=1`);
                    document.getElementById('master-column-count').textContent = previewData.columns ? previewData.columns.length : '-';
                } catch(e) {
                    document.getElementById('master-column-count').textContent = '-';
                }
                
                // Populate configuration section if saved config exists
                const configSection = document.getElementById('master-config-section');
                if (master.saved_config) {
                    configSection.classList.remove('hidden');
                    document.getElementById('master-config-updated').textContent = master.saved_config.updated_at || 'Previously saved';
                    document.getElementById('master-config-columns').textContent = master.saved_config.columns || 'All';
                    document.getElementById('master-config-sheet').textContent = master.saved_config.sheet_name || 'First sheet';
                    document.getElementById('master-config-header').textContent = master.saved_config.header_row ? `Row ${master.saved_config.header_row}` : 'Row 1';
                } else {
                    configSection.classList.add('hidden');
                }
                
                // Populate merged files table
                const mergedBody = document.getElementById('master-merged-body');
                if (master.merged_files && master.merged_files.length > 0) {
                    mergedBody.innerHTML = master.merged_files.map(f => `
                        <tr>
                            <td class="px-3 py-2 text-sm text-gray-900">${f.file}</td>
                            <td class="px-3 py-2 text-sm text-gray-900 text-right">${f.row_count}</td>
                        </tr>
                    `).join('');
                } else {
                    mergedBody.innerHTML = '<tr><td colspan="2" class="px-3 py-2 text-sm text-gray-500 text-center">No merged files</td></tr>';
                }
                
                // Populate rejected files table
                const rejectedBody = document.getElementById('master-rejected-body');
                if (master.rejected_files && master.rejected_files.length > 0) {
                    rejectedBody.innerHTML = master.rejected_files.map(r => `
                        <tr>
                            <td class="px-3 py-2 text-sm text-gray-900 font-medium">${r.file}</td>
                            <td class="px-3 py-2 text-sm text-red-600">${r.reason}</td>
                        </tr>
                    `).join('');
                } else {
                    rejectedBody.innerHTML = '<tr><td colspan="2" class="px-3 py-2 text-sm text-gray-500 text-center">No rejected files</td></tr>';
                }
                
            } catch (error) {
                showToast('Error loading master summary: ' + error.message, 'error');
            }
        }

        async function loadSourceFilesDropdown() {
            try {
                const data = await apiCall(`/api/master/${currentFolderId}/source-files`);
                const select = document.getElementById('master-source-filter');
                
                if (data.success && data.source_files) {
                    select.innerHTML = '<option value="All Files">All Files</option>';
                    data.source_files.forEach(f => {
                        select.innerHTML += `<option value="${f.name}">${f.name} (${f.row_count} rows)</option>`;
                    });
                }
            } catch (error) {
                console.error('Error loading source files:', error);
            }
        }

        async function loadMasterPreview() {
            const limitStr = document.getElementById('master-row-limit').value || 10;
            let limit = parseInt(limitStr, 10);
            if (isNaN(limit) || limit < 1) limit = 10;
            if (limit > 10000) limit = 10000;
            const sourceFile = document.getElementById('master-source-filter').value;
            const search = document.getElementById('master-search').value;
            
            try {
                let url = `/api/master/${currentFolderId}/preview?limit=${limit}`;
                if (sourceFile && sourceFile !== 'All Files') {
                    url += `&source_file=${encodeURIComponent(sourceFile)}`;
                }
                if (search) {
                    url += `&search=${encodeURIComponent(search)}`;
                }
                
                const data = await apiCall(url);
                
                const headEl = document.getElementById('master-preview-head');
                const bodyEl = document.getElementById('master-preview-body');
                const infoEl = document.getElementById('master-preview-info');
                
                if (!data.success || !data.columns || data.columns.length === 0) {
                    headEl.innerHTML = '<tr><th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">No Data</th></tr>';
                    bodyEl.innerHTML = '<tr><td class="px-3 py-2 text-sm text-gray-500 text-center">No data available</td></tr>';
                    infoEl.textContent = 'Showing 0 of 0 rows';
                    return;
                }
                
                // Render headers
                headEl.innerHTML = '<tr>' + data.columns.map(col => 
                    `<th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${col}</th>`
                ).join('') + '</tr>';
                
                // Render data rows
                if (data.data && data.data.length > 0) {
                    bodyEl.innerHTML = data.data.map(row => 
                        '<tr>' + data.columns.map(col => 
                            `<td class="px-3 py-2 text-sm text-gray-900 whitespace-nowrap">${row[col] !== null && row[col] !== undefined ? String(row[col]).substring(0, 100) : ''}</td>`
                        ).join('') + '</tr>'
                    ).join('');
                } else {
                    bodyEl.innerHTML = '<tr><td colspan="' + data.columns.length + '" class="px-3 py-2 text-sm text-gray-500 text-center">No matching rows found</td></tr>';
                }
                
                infoEl.textContent = `Showing ${data.returned_count || 0} of ${data.total_count || 0} rows`;
                
            } catch (error) {
                console.error('Error loading preview:', error);
            }
        }

        async function loadMasterStats() {
            try {
                const data = await apiCall(`/api/master/${currentFolderId}/stats`);
                const bodyEl = document.getElementById('master-stats-body');
                
                if (!data.success || !data.columns) {
                    bodyEl.innerHTML = '<tr><td colspan="6" class="px-3 py-2 text-sm text-gray-500 text-center">Statistics unavailable</td></tr>';
                    return;
                }
                
                bodyEl.innerHTML = data.columns.map(col => {
                    const isProtected = col.column === 'Source_File_Name';
                    return `
                    <tr>
                        <td class="px-3 py-2 text-sm text-gray-900 font-medium">${col.column}</td>
                        <td class="px-3 py-2 text-sm text-gray-700">
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${col.data_type === 'Numeric' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}">
                                ${col.data_type}
                            </span>
                        </td>
                        <td class="px-3 py-2 text-sm text-gray-900 text-right">${col.non_null_count}</td>
                        <td class="px-3 py-2 text-sm text-gray-900 text-right">${col.null_count}</td>
                        <td class="px-3 py-2 text-sm text-gray-900 text-right">${col.unique_values}</td>
                        <td class="px-3 py-2 text-center">
                            ${isProtected ? 
                                '<span class="text-xs text-gray-400" title="Protected column">—</span>' :
                                `<button onclick="deleteMasterColumn('${col.column.replace(/'/g, "\\'")}')" class="text-red-500 hover:text-red-700 transition-colors" title="Delete column">
                                    <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                    </svg>
                                </button>`
                            }
                        </td>
                    </tr>
                `}).join('');
                
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        async function loadMasterValidation() {
            try {
                const data = await apiCall(`/api/master/${currentFolderId}`);
                if (!data.success || !data.master) return;
                
                const master = data.master;
                const originalRows = master.merged_files ? master.merged_files.reduce((sum, f) => sum + (f.row_count || 0), 0) : 0;
                const mergedRows = master.row_count || 0;
                
                let text = '';
                if (originalRows === mergedRows) {
                    text = `✓ Validation passed: Original files contain ${originalRows.toLocaleString()} rows → Merged file contains ${mergedRows.toLocaleString()} rows. Row counts match.`;
                } else if (originalRows > mergedRows) {
                    text = `⚠ Mismatch: Original files contain ${originalRows.toLocaleString()} rows total, but merged file only has ${mergedRows.toLocaleString()} rows. ${originalRows - mergedRows} rows were lost during merge (possibly due to duplicates or header handling).`;
                } else {
                    text = `ℹ Original files: ${originalRows.toLocaleString()} rows → Merged: ${mergedRows.toLocaleString()} rows. The merged file has more rows, possibly due to file overlap or repeated data.`;
                }
                
                document.getElementById('master-validation-text').textContent = text;
                
            } catch (error) {
                document.getElementById('master-validation-text').textContent = 'Unable to calculate validation.';
            }
        }

        async function exportMasterData() {
            const limit = document.getElementById('master-row-limit').value || 10;
            const sourceFile = document.getElementById('master-source-filter').value;
            const search = document.getElementById('master-search').value;
            
            const formData = new FormData();
            formData.append('folder_id', currentFolderId);
            formData.append('limit', limit);
            if (sourceFile && sourceFile !== 'All Files') {
                formData.append('source_file', sourceFile);
            }
            if (search) {
                formData.append('search', search);
            }
            
            try {
                const response = await fetch(`/api/master/${currentFolderId}/export`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    showToast('Export failed: ' + (err.detail || response.statusText), 'error');
                    return;
                }
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `master_export_${currentFolderId}_${new Date().toISOString().slice(0,10)}.xlsx`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                
                showToast('Export downloaded successfully', 'success');
            } catch (error) {
                showToast('Export failed: ' + error.message, 'error');
            }
        }

        // Advanced SQL Section
        let masterSqlOpen = false;
        
        function toggleMasterSql() {
            const panel = document.getElementById('master-sql-panel');
            const chevron = document.getElementById('master-sql-chevron');
            
            if (masterSqlOpen) {
                panel.classList.add('hidden');
                chevron.classList.remove('rotate-180');
                masterSqlOpen = false;
            } else {
                panel.classList.remove('hidden');
                chevron.classList.add('rotate-180');
                masterSqlOpen = true;
            }
        }

        async function runMasterSql() {
            const query = document.getElementById('master-sql-query').value.trim();
            if (!query) {
                showToast('Please enter a SQL query', 'warning');
                return;
            }
            if (!currentFolderId) {
                showToast('Please select a folder first', 'warning');
                return;
            }
            
            const formData = new FormData();
            formData.append('folder_id', String(currentFolderId));
            formData.append('query', query);
            
            try {
                const data = await apiCall('/api/master/query', {
                    method: 'POST',
                    body: formData
                });
                
                const resultDiv = document.getElementById('master-sql-result');
                const headEl = document.getElementById('master-sql-head');
                const bodyEl = document.getElementById('master-sql-body');
                const infoEl = document.getElementById('master-sql-info');
                
                if (!data.success || !data.columns) {
                    headEl.innerHTML = '';
                    bodyEl.innerHTML = '<tr><td class="px-3 py-2 text-sm text-gray-500 text-center">No results</td></tr>';
                    infoEl.textContent = '0 rows';
                    resultDiv.classList.remove('hidden');
                    return;
                }
                
                headEl.innerHTML = '<tr>' + data.columns.map(col => 
                    `<th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${col}</th>`
                ).join('') + '</tr>';
                
                bodyEl.innerHTML = data.data.map(row => 
                    '<tr>' + data.columns.map(col => 
                        `<td class="px-3 py-2 text-sm text-gray-900 whitespace-nowrap">${row[col] !== null && row[col] !== undefined ? String(row[col]).substring(0, 100) : ''}</td>`
                    ).join('') + '</tr>'
                ).join('');
                
                infoEl.textContent = `${data.row_count} rows returned`;
                resultDiv.classList.remove('hidden');
                
            } catch (error) {
                showToast('Query failed: ' + error.message, 'error');
            }
        }

        async function exportMasterSql() {
            const query = document.getElementById('master-sql-query').value.trim();
            if (!query) {
                showToast('Please enter a SQL query first', 'warning');
                return;
            }
            
            const formData = new FormData();
            formData.append('folder_id', currentFolderId);
            formData.append('query', query);
            
            try {
                const response = await fetch(`/api/master/${currentFolderId}/export`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    showToast('Export failed: ' + (err.detail || response.statusText), 'error');
                    return;
                }
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `master_sql_export_${currentFolderId}_${new Date().toISOString().slice(0,10)}.xlsx`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                
                showToast('SQL export downloaded', 'success');
            } catch (error) {
                showToast('Export failed: ' + error.message, 'error');
            }
        }

        // ==================== RULE MAPPING ====================
        function switchPhase(phase) {
            document.querySelectorAll('.phase-content').forEach(el => el.classList.add('hidden'));
            document.getElementById(`phase-${phase}`).classList.remove('hidden');
            
            document.querySelectorAll('.phase-btn').forEach(btn => {
                btn.classList.remove('bg-white', 'shadow-sm', 'text-gray-900');
                btn.classList.add('text-gray-600');
            });
            document.getElementById(`phase-${phase}-btn`).classList.add('bg-white', 'shadow-sm', 'text-gray-900');
            document.getElementById(`phase-${phase}-btn`).classList.remove('text-gray-600');
        }

        // Cache for folder files to avoid repeated API calls
        let folderFilesCache = null;
        let folderFilesCacheTime = 0;
        const CACHE_TTL = 30000; // 30 seconds cache

        async function getAllFilesList() {
            const now = Date.now();
            if (folderFilesCache && (now - folderFilesCacheTime) < CACHE_TTL) {
                return folderFilesCache;
            }
            
            const allFilesData = await apiCall('/api/folders');
            if (!allFilesData.success) return [];
            
            // Fetch all folder files in parallel using Promise.all
            const folderPromises = allFilesData.folders.map(folder => 
                apiCall(`/api/files/${folder.id}`).then(res => res.success ? res.files : [])
            );
            
            const folderResults = await Promise.all(folderPromises);
            let allFilesList = [];
            folderResults.forEach(files => {
                allFilesList = allFilesList.concat(files);
            });
            
            // Fetch master files for all folders
            const masterPromises = allFilesData.folders.map(folder => 
                apiCall(`/api/master/${folder.id}`).then(res => {
                    if (res.success && res.master && res.master.exists) {
                        return {
                            id: `master_${folder.id}`,
                            original_name: `Master_File_${folder.name}`,
                            is_master: true,
                            folder_id: folder.id,
                            folder_name: folder.name,
                            row_count: res.master.row_count
                        };
                    }
                    return null;
                }).catch(() => null)
            );
            
            const masterResults = await Promise.all(masterPromises);
            const masterFiles = masterResults.filter(m => m !== null);
            
            folderFilesCache = { files: allFilesList, masterFiles };
            folderFilesCacheTime = now;
            return folderFilesCache;
        }

        async function loadRulePageData() {
            // If already loaded, skip full reload — just ensure data is fresh silently
            if (isRulesPageLoaded) {
                // Silently refresh file list in dropdowns without overlay
                try {
                    const allFilesData = await getAllFilesList();
                    const allFilesList = allFilesData.files || [];
                    const masterFiles = allFilesData.masterFiles || [];
                    const phase1File = document.getElementById('phase1-file');
                    if (phase1File) {
                        const currentVal = phase1File.value;
                        phase1File.innerHTML = '<option value="">-- Select File --</option>';
                        allFilesList.forEach(file => {
                            phase1File.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                        });
                        if (masterFiles.length > 0) {
                            phase1File.innerHTML += `<optgroup label="--- Master Files ---">`;
                            masterFiles.forEach(file => {
                                phase1File.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                            });
                            phase1File.innerHTML += `</optgroup>`;
                        }
                        if (currentVal) phase1File.value = currentVal;
                    }
                } catch (e) {
                    console.warn('Silent refresh failed:', e);
                }
                return;
            }

            // First-time load: show loading indicator
            const rulesContainer = document.getElementById('page-rules');
            let loadingOverlay = document.getElementById('rules-loading-overlay');
            if (!loadingOverlay) {
                loadingOverlay = document.createElement('div');
                loadingOverlay.id = 'rules-loading-overlay';
                loadingOverlay.className = 'fixed inset-0 bg-white bg-opacity-90 z-50 flex items-center justify-center';
                loadingOverlay.innerHTML = `
                    <div class="text-center">
                        <div class="spinner mx-auto mb-4 w-12 h-12 border-4"></div>
                        <p class="text-lg font-medium text-gray-700">Loading Rule Configuration...</p>
                        <p class="text-sm text-gray-500 mt-2" id="loading-progress">Initializing...</p>
                    </div>
                `;
                document.body.appendChild(loadingOverlay);
            } else {
                loadingOverlay.classList.remove('hidden');
            }
            
            const updateProgress = (msg) => {
                const el = document.getElementById('loading-progress');
                if (el) el.textContent = msg;
            };

            try {
                // Load files in parallel
                updateProgress('Loading files...');
                const allFilesData = await getAllFilesList();
                const allFilesList = allFilesData.files || [];
                const masterFiles = allFilesData.masterFiles || [];
                
                // Populate Phase 1 file dropdown
                const phase1File = document.getElementById('phase1-file');
                if (phase1File) {
                    phase1File.innerHTML = '<option value="">-- Select File --</option>';
                    allFilesList.forEach(file => {
                        phase1File.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                    });
                    if (masterFiles.length > 0) {
                        phase1File.innerHTML += `<optgroup label="--- Master Files ---">`;
                        masterFiles.forEach(file => {
                            phase1File.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                        });
                        phase1File.innerHTML += `</optgroup>`;
                    }
                }

                // Load saved phases in parallel where possible
                updateProgress('Loading Phase 1...');
                await loadSavedPhase1();
                
                updateProgress('Loading Phase 2 (this may take a moment)...');
                await loadSavedPhase2();
                
                updateProgress('Loading Phase 3...');
                await loadSavedPhase3();
                
                updateProgress('Loading Phase 4...');
                await loadSavedPhase4();
                
                updateProgress('Complete!');
                isRulesPageLoaded = true; // Mark as loaded
            } catch (error) {
                console.error('Error loading rule page:', error);
                showToast('Error loading rules: ' + error.message, 'error');
            } finally {
                // Hide loading overlay with a small delay so user sees completion
                setTimeout(() => {
                    if (loadingOverlay) loadingOverlay.classList.add('hidden');
                }, 500);
            }
        }

        async function loadPrimaryPreview(filename) {
            try {
                const data = await apiCall(`/api/primary/preview/${encodeURIComponent(filename)}`);
                const tbody = document.getElementById('phase1-preview-body');
                
                if (data.success && data.preview && data.preview.length > 0) {
                    tbody.innerHTML = data.preview.map((row, idx) => `
                        <tr class="border-b border-gray-100">
                            <td class="px-3 py-2 text-gray-900 font-medium">${row.Unique_ID || idx + 1}</td>
                            <td class="px-3 py-2 text-gray-700">${row.Source_File_Name || ''}</td>
                            <td class="px-3 py-2 text-gray-700">${row['Order ID'] || ''}</td>
                            <td class="px-3 py-2 text-gray-700">${row['Sales Amount'] != null ? row['Sales Amount'].toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : ''}</td>
                        </tr>
                    `).join('');
                    
                    // Update count badge with total from preview API
                    const countBadge = document.getElementById('phase1-unique-count');
                    if (countBadge && data.total_rows) {
                        countBadge.textContent = `${data.total_rows.toLocaleString()} unique values`;
                    }
                } else {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="4" class="px-3 py-4 text-center text-sm text-gray-500">
                                Preview not available
                            </td>
                        </tr>
                    `;
                }
            } catch(e) {
                console.error('Error loading primary preview:', e);
                const tbody = document.getElementById('phase1-preview-body');
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="px-3 py-4 text-center text-sm text-gray-500">
                            Error loading preview data
                        </td>
                    </tr>
                `;
            }
        }

        async function loadSavedPhase1() {
            // Load saved Phase 1 rules
            const data = await apiCall('/api/rules/1');
            if (data.success && data.rules && data.rules.length > 0) {
                const latestRule = data.rules[data.rules.length - 1];
                try {
                    const config = JSON.parse(latestRule.config);
                    window.primaryValueColumnName = config.column || 'Order ID';
                    
                    // Update preview table header label dynamically
                    const pHeader = document.getElementById('phase1-preview-primary-header');
                    if (pHeader) {
                        pHeader.textContent = 'Order ID';
                    }
                    
                    // Set dropdown values
                    document.getElementById('phase1-file').value = config.file_id;
                    await loadPhase1Sheets();
                    document.getElementById('phase1-sheet').value = config.sheet_name;
                    await loadPhase1Columns();
                    document.getElementById('phase1-column').value = config.column;
                    if (document.getElementById('phase1-sales-column') && config.sales_column) {
                        document.getElementById('phase1-sales-column').value = config.sales_column;
                    }

                    // Show preview area
                    document.getElementById('phase1-preview').classList.remove('hidden');
                    const countBadge = document.getElementById('phase1-unique-count');
                    if (countBadge) {
                        countBadge.textContent = `${config.total_unique ? config.total_unique.toLocaleString() : '0'} unique values`;
                    }
                    
                    // Load preview data from the primary file if available
                    if (config.primary_file) {
                        await loadPrimaryPreview(config.primary_file);
                    }
                    
                    // Show saved info
                    const previewDiv = document.getElementById('phase1-preview');
                    // Check if saved info already exists
                    let savedInfo = previewDiv.querySelector('#phase1-saved-info');
                    if (!savedInfo) {
                        savedInfo = document.createElement('div');
                        savedInfo.id = 'phase1-saved-info';
                        savedInfo.className = 'mt-4 p-3 bg-green-50 border border-green-200 rounded-lg';
                        previewDiv.insertBefore(savedInfo, previewDiv.firstChild);
                    }
                    savedInfo.innerHTML = `
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-sm font-medium text-green-800">Saved Primary Selection</p>
                                <p class="text-xs text-green-600">File: ${config.file_id} | Sheet: ${config.sheet_name} | Column: ${config.column}</p>
                                <p class="text-xs text-green-600">Total Unique: ${config.total_unique ? config.total_unique.toLocaleString() : 'N/A'}</p>
                            </div>
                            ${config.primary_file ? `
                                <a href="/api/primary/download/${config.primary_file}" target="_blank" class="text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700 transition-colors">
                                    Download
                                </a>
                            ` : ''}
                        </div>
                    `;
                } catch(e) {
                    console.error('Error loading saved phase 1:', e);
                }
            }
        }

        async function loadSavedPhase2() {
            const tbody = document.getElementById('matching-rules-body');
            
            // Always clear tbody first - remove any stuck spinner
            tbody.innerHTML = '';
            
            let data;
            try {
                data = await apiCall('/api/rules/2');
            } catch (e) {
                console.error('Failed to load Phase 2 rules:', e);
                tbody.innerHTML = '<tr><td colspan="9" class="px-3 py-8 text-center text-sm text-gray-500">Unable to load saved rules. Add new rules below.</td></tr>';
                return;
            }
            
            if (!data.success || !data.rules || data.rules.length === 0) {
                // No saved rules - show empty state
                tbody.innerHTML = '<tr><td colspan="9" class="px-3 py-8 text-center text-sm text-gray-500">No saved rules yet. Click "Add Match Rule" or "Add Calculation" to get started.</td></tr>';
                return;
            }
            
            const latestRule = data.rules[data.rules.length - 1];
            let rulesList;
            try {
                rulesList = JSON.parse(latestRule.config);
            } catch(e) {
                console.error('Error parsing phase 2 config:', e);
                return;
            }
            
            if (!Array.isArray(rulesList) || rulesList.length === 0) return;
            
            // CRITICAL FIX: Migrate old saved output columns A, B, C to start from D
            // Primary data always occupies A, B, C (Unique_ID, Source_File_Name, Primary_Value)
            const MIN_COLUMN_NUMBER = 4; // D
            const reservedCols = ['A', 'B', 'C'];
            
            // Collect all output columns from saved rules
            const savedOutputCols = rulesList.map(r => r.output_column).filter(Boolean);
            const hasReservedCols = savedOutputCols.some(col => reservedCols.includes(col));
            const hasEmptyCols = rulesList.some(r => !r.output_column);
            
            if (hasReservedCols || hasEmptyCols) {
                // Sort rules by their current output column
                rulesList.sort((a, b) => {
                    const aNum = columnLetterToNumber(a.output_column || 'Z');
                    const bNum = columnLetterToNumber(b.output_column || 'Z');
                    return aNum - bNum;
                });
                
                // Reassign output columns starting from D, skipping reserved ones
                let nextColNum = MIN_COLUMN_NUMBER;
                const usedNewCols = new Set();
                
                for (const rule of rulesList) {
                    if (reservedCols.includes(rule.output_column)) {
                        // Find next available column
                        while (usedNewCols.has(numberToColumnLetter(nextColNum))) {
                            nextColNum++;
                        }
                        rule.output_column = numberToColumnLetter(nextColNum);
                        usedNewCols.add(rule.output_column);
                        nextColNum++;
                    } else if (rule.output_column) {
                        usedNewCols.add(rule.output_column);
                    } else {
                        // FIX: Assign a new column to rules with empty/missing output_column
                        while (usedNewCols.has(numberToColumnLetter(nextColNum))) {
                            nextColNum++;
                        }
                        rule.output_column = numberToColumnLetter(nextColNum);
                        usedNewCols.add(rule.output_column);
                        nextColNum++;
                    }
                }
            }
            
            // Reset IDs to be sequential: 1, 2, 3, 4, 5...
            rulesList.forEach((rule, idx) => {
                rule.id = (idx + 1).toString();
            });
            matchingRuleCounter = rulesList.length + 1;
            
            // tbody was already declared and cleared at the top of this function
            // Just confirm it's empty before adding rows
            tbody.innerHTML = '';
            
            // Collect all created column names for calculation rules
            let createdColumns = [];
            
            // Step 1: Collect ALL column names from ALL rules
            for (const rule of rulesList) {
                if (rule.column_name) {
                    createdColumns.push(rule.column_name);
                }
            }
            createdColumns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount', ...createdColumns];
            createdColumns = [...new Set(createdColumns)];
            
            // Step 2: Create all rows with sequential IDs
            const rowIds = [];
            for (const rule of rulesList) {
                const rowId = parseInt(rule.id);
                rowIds.push({ rowId, rule });
                
                const tr = document.createElement('tr');
                tr.className = 'rule-row bg-white border-b border-gray-100';
                tr.id = `rule-row-${rowId}`;
                
                // Check if this is a calculation rule
                if (rule.rule_type === 'calculation') {
                    tr.dataset.ruleType = 'calculation';
                    
                    // Support both old format (first_column, second_column) and new format (columns array)
                    let savedCols = rule.columns || [];
                    if (!savedCols.length && (rule.first_column || rule.second_column)) {
                        if (rule.first_column) savedCols.push(rule.first_column);
                        if (rule.second_column) savedCols.push(rule.second_column);
                    }
                    
            // Prevent circular dependency: exclude the current rule's own column name
            // from being selectable as its own input
            const currentColName = rule.column_name || '';
            const filteredOptions = createdColumns.filter(col => col !== currentColName);
            const colOptions = filteredOptions.map(col => `<option value="${col}">${col}</option>`).join('');
            
            let initialColsHtml = '';
            if (savedCols.length > 0) {
                savedCols.forEach((col, idx) => {
                    initialColsHtml += buildCalcColumnRow(rowId, idx, colOptions, col);
                });
            } else {
                initialColsHtml += buildCalcColumnRow(rowId, 0, colOptions, '');
                initialColsHtml += buildCalcColumnRow(rowId, 1, colOptions, '');
            }
                    
                    tr.innerHTML = `
                        <td class="px-2 py-3 text-center">
                            <input type="checkbox" class="row-condition-checkbox w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500" 
                                onchange="onToggleConditionCheckbox(${rowId})" title="Enable Column Condition">
                        </td>
                        <td class="px-3 py-3 font-mono text-sm text-gray-500">#${rowId}</td>
                        <td class="px-3 py-3" colspan="4">
                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <label class="text-xs font-medium text-gray-600">Columns to Calculate</label>
                                    <select class="calc-operation w-32 text-xs border border-gray-300 rounded px-2 py-1 ml-2">
                                        <option value="addition" ${rule.operation === 'addition' ? 'selected' : ''}>Addition (+)</option>
                                        <option value="subtraction" ${rule.operation === 'subtraction' ? 'selected' : ''}>Subtraction (-)</option>
                                        <option value="multiply" ${rule.operation === 'multiply' ? 'selected' : ''}>Multiply (×)</option>
                                        <option value="divide" ${rule.operation === 'divide' ? 'selected' : ''}>Divide (÷)</option>
                                    </select>
                                </div>
                                <div class="calc-columns-list space-y-1">
                                    ${initialColsHtml}
                                </div>
                                <button onclick="addCalcColumn(this)" class="mt-1 flex items-center space-x-1 text-xs text-orange-600 hover:text-orange-800 font-medium">
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                                    </svg>
                                    <span>Add Column</span>
                                </button>
                            </div>
                        </td>
                        <td class="px-3 py-3">
                            <select class="rule-output-column w-full text-xs border border-gray-300 rounded px-2 py-1 uppercase"
                                onchange="refreshAllColumnDropdowns()">
                                ${generateColumnLetterOptions(rule.output_column || '', getAllUsedOutputColumns())}
                            </select>
                        </td>
                        <td class="px-3 py-3">
                            <div class="space-y-2">
                                <input type="text" class="rule-column-name w-full text-xs border border-gray-300 rounded px-2 py-1" 
                                    placeholder="e.g. Grand_Total" maxlength="50" value="${rule.column_name || ''}">
                                <input type="text" class="rule-default-value w-full text-xs border border-gray-300 rounded px-2 py-1" 
                                    placeholder="Default Value (optional)" maxlength="100" value="${rule.default_value || ''}">
                            </div>
                        </td>
                        <td class="px-3 py-3">
                            <button onclick="deleteRuleRow(${rowId})" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                            </button>
                        </td>
                    `;
                } else {
                    // Match rule
                    tr.innerHTML = `
                        <td class="px-2 py-3 text-center">
                            <input type="checkbox" class="row-condition-checkbox w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500" 
                                onchange="onToggleConditionCheckbox(${rowId})" title="Enable Column Condition">
                        </td>
                        <td class="px-3 py-3 font-mono text-sm text-gray-500">#${rowId}</td>
                        <td class="px-3 py-3">
                            <div class="space-y-2">
                                <select class="rule-primary-file w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleSheets(this, ${rowId}, 'primary')">
                                    <option value="">File</option>
                                </select>
                                <select class="rule-primary-sheet w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleColumns(this, ${rowId}, 'primary')">
                                    <option value="">Sheet</option>
                                </select>
                                <select class="rule-primary-column w-full text-xs border border-gray-300 rounded px-2 py-1">
                                    <option value="">Column</option>
                                </select>
                            </div>
                        </td>
                        <td class="px-3 py-3">
                            <select class="rule-type w-full text-xs border border-gray-300 rounded px-2 py-1">
                                <option value="match" ${rule.rule_type === 'match' ? 'selected' : ''}>Match (VLOOKUP)</option>
                                <option value="sumif" ${rule.rule_type === 'sumif' ? 'selected' : ''}>Sumif Match</option>
                                <option value="countif" ${rule.rule_type === 'countif' ? 'selected' : ''}>Countif Match</option>
                                <option value="addition" ${rule.rule_type === 'addition' ? 'selected' : ''}>Addition</option>
                                <option value="subtraction" ${rule.rule_type === 'subtraction' ? 'selected' : ''}>Subtraction</option>
                            </select>
                        </td>
                        <td class="px-3 py-3">
                            <div class="space-y-2">
                                <select class="rule-secondary-file w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleSheets(this, ${rowId}, 'secondary')">
                                    <option value="">File</option>
                                </select>
                                <select class="rule-secondary-sheet w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleColumns(this, ${rowId}, 'secondary')">
                                    <option value="">Sheet</option>
                                </select>
                                <select class="rule-secondary-column w-full text-xs border border-gray-300 rounded px-2 py-1">
                                    <option value="">Match Column</option>
                                </select>
                            </div>
                        </td>
                        <td class="px-3 py-3">
                            <div class="space-y-2">
                                <select class="rule-extract-file w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleSheets(this, ${rowId}, 'extract')">
                                    <option value="">File</option>
                                </select>
                                <select class="rule-extract-sheet w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleColumns(this, ${rowId}, 'extract')">
                                    <option value="">Sheet</option>
                                </select>
                                <select class="rule-extract-column w-full text-xs border border-gray-300 rounded px-2 py-1">
                                    <option value="">Extract Column</option>
                                </select>
                            </div>
                        </td>
                        <td class="px-3 py-3">
                            <select class="rule-output-column w-full text-xs border border-gray-300 rounded px-2 py-1 uppercase"
                                onchange="refreshAllColumnDropdowns()">
                                ${generateColumnLetterOptions(rule.output_column || '', getAllUsedOutputColumns())}
                            </select>
                        </td>
                        <td class="px-3 py-3">
                            <div class="space-y-2">
                                <input type="text" class="rule-column-name w-full text-xs border border-gray-300 rounded px-2 py-1" 
                                    placeholder="e.g. Order_ID, Result" maxlength="50" value="${rule.column_name || ''}">
                                <input type="text" class="rule-default-value w-full text-xs border border-gray-300 rounded px-2 py-1" 
                                    placeholder="Default Value (optional)" maxlength="100" value="${rule.default_value || ''}">
                            </div>
                        </td>
                        <td class="px-3 py-3">
                            <button onclick="deleteRuleRow(${rowId})" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                            </button>
                        </td>
                    `;
                }
                tbody.appendChild(tr);
            }
            
            // Step 3: Fetch all file lists ONCE
            const foldersData = await apiCall('/api/folders');
            let allFilesList = [];
            let masterFiles = [];
            if (foldersData.success) {
                // Fetch all folder files in parallel
                const folderPromises = foldersData.folders.map(folder => 
                    apiCall(`/api/files/${folder.id}`)
                );
                const folderResults = await Promise.all(folderPromises);
                folderResults.forEach(res => {
                    if (res.success) allFilesList = allFilesList.concat(res.files);
                });
                
                // Fetch master files for all folders
                const masterPromises = foldersData.folders.map(folder => 
                    apiCall(`/api/master/${folder.id}`).then(res => {
                        if (res.success && res.master && res.master.exists) {
                            return {
                                id: `master_${folder.id}`,
                                original_name: `Master_File_${folder.name}`,
                                is_master: true,
                                folder_id: folder.id,
                                folder_name: folder.name,
                                row_count: res.master.row_count
                            };
                        }
                        return null;
                    }).catch(() => null)
                );
                const masterResults = await Promise.all(masterPromises);
                masterFiles = masterResults.filter(m => m !== null);
            }
            
            // Get primary file info
            const primaryData = await apiCall('/api/primary/files');
            const rulesData1 = await apiCall('/api/rules/1');
            let primaryOption = '';
            if (primaryData.success && primaryData.files && primaryData.files.length > 0) {
                const sorted = primaryData.files.sort((a, b) => new Date(b.created) - new Date(a.created));
                const latest = sorted[0];
                let columnName = 'Primary Data';
                let totalUnique = '';
                if (rulesData1.success && rulesData1.rules && rulesData1.rules.length > 0) {
                    try {
                        const c = JSON.parse(rulesData1.rules[rulesData1.rules.length - 1].config);
                        if (c.column) columnName = c.column;
                        if (c.total_unique) totalUnique = ` (${c.total_unique.toLocaleString()} unique)`;
                    } catch(e) {}
                }
                primaryOption = `<optgroup label="--- Primary Data (Latest) ---"><option value="primary_latest" data-primary="true" data-real-name="${latest.name}">Primary file${totalUnique}</option></optgroup>`;
            }
            
            // Build file options HTML once
            let fileOptionsHtml = '<option value="">File</option>' + 
                allFilesList.map(f => `<option value="${f.id}">${f.original_name}</option>`).join('');
            if (masterFiles.length > 0) {
                fileOptionsHtml += `<optgroup label="--- Master Files ---">` +
                    masterFiles.map(f => `<option value="${f.id}">${f.original_name}</option>`).join('') +
                    `</optgroup>`;
            }
            fileOptionsHtml += primaryOption;
            
            // Pre-fetch all sheet/column data in parallel for match rules
            // Build a set of unique (file_id, sheet_name) pairs needed
            const neededLookups = new Set();
            const masterFileIds = new Set();
            const matchRules = rowIds.filter(({rule}) => rule.rule_type !== 'calculation');
            
            for (const {rule} of matchRules) {
                if (rule.primary_file && !rule.primary_file.startsWith('primary_') && !rule.primary_file.startsWith('master_')) 
                    neededLookups.add(rule.primary_file);
                if (rule.secondary_file && !rule.secondary_file.startsWith('primary_') && !rule.secondary_file.startsWith('master_')) 
                    neededLookups.add(rule.secondary_file);
                if (rule.extract_file && rule.extract_file !== rule.secondary_file && !rule.extract_file.startsWith('primary_') && !rule.extract_file.startsWith('master_')) 
                    neededLookups.add(rule.extract_file);
                
                // Track master file IDs
                if (rule.primary_file && rule.primary_file.startsWith('master_')) masterFileIds.add(rule.primary_file);
                if (rule.secondary_file && rule.secondary_file.startsWith('master_')) masterFileIds.add(rule.secondary_file);
                if (rule.extract_file && rule.extract_file.startsWith('master_')) masterFileIds.add(rule.extract_file);
            }
            
            // Fetch all sheets in parallel (for regular files only - master files always have "Working" sheet)
            const sheetPromises = {};
            for (const fileId of neededLookups) {
                sheetPromises[fileId] = apiCall(`/api/files/${fileId}/sheets`).catch(() => ({ success: false }));
            }
            const sheetResults = await Promise.all(Object.values(sheetPromises));
            const sheetData = {};
            Object.keys(sheetPromises).forEach((fileId, idx) => {
                sheetData[fileId] = sheetResults[idx];
            });
            // Master files always have Working sheet
            for (const fileId of masterFileIds) {
                sheetData[fileId] = { success: true, sheets: ['Working'] };
            }
            
            // Fetch all columns in parallel
            const colPromises = {};
            for (const {rule} of matchRules) {
                const combos = [
                    [rule.primary_file, rule.primary_sheet],
                    [rule.secondary_file, rule.secondary_sheet],
                    [rule.extract_file, rule.extract_sheet]
                ];
                for (const [fileId, sheetName] of combos) {
                    if (!fileId || !sheetName || fileId.startsWith('primary_')) continue;
                    
                    const key = `${fileId}|${sheetName}`;
                    if (colPromises[key]) continue;
                    
                    if (fileId.startsWith('master_')) {
                        const folderId = fileId.replace('master_', '');
                        colPromises[key] = apiCall(`/api/master/${folderId}/columns`).catch(() => ({ success: false }));
                    } else {
                        colPromises[key] = apiCall(`/api/files/${fileId}/columns?sheet_name=${encodeURIComponent(sheetName)}`).catch(() => ({ success: false }));
                    }
                }
            }
            const colResults = await Promise.all(Object.values(colPromises));
            const colData = {};
            
            let hasMissingFiles = false;
            
            Object.keys(colPromises).forEach((key, idx) => {
                colData[key] = colResults[idx];
                if (colResults[idx] && colResults[idx].success === false) hasMissingFiles = true;
            });
            
            Object.keys(sheetPromises).forEach((fileId, idx) => {
                if (sheetResults[idx] && sheetResults[idx].success === false) hasMissingFiles = true;
            });
            
            if (hasMissingFiles) {
                showToast('Warning: One or more files referenced in your rules are missing or deleted. Please update your rules.', 'warning', 7000);
            }
            
            // Populate match rule file dropdowns
            for (const { rowId, rule } of rowIds) {
                if (rule.rule_type === 'calculation') continue; // Skip calculation rules
                
                const row = document.getElementById(`rule-row-${rowId}`);
                const selects = row.querySelectorAll('select[class*="file"]');
                selects.forEach(sel => {
                    sel.innerHTML = fileOptionsHtml;
                });
                
                // Set values using pre-fetched data
                // Primary
                const pFile = row.querySelector('.rule-primary-file');
                pFile.value = rule.primary_file || '';
                const pSheet = row.querySelector('.rule-primary-sheet');
                if (rule.primary_file) {
                    if (rule.primary_file.startsWith('primary_')) {
                        pSheet.innerHTML = '<option value="Working" selected>Working</option>';
                    } else if (sheetData[rule.primary_file]?.success) {
                        pSheet.innerHTML = '<option value="">Sheet</option>' + 
                            sheetData[rule.primary_file].sheets.map(s => `<option value="${s}" ${s === rule.primary_sheet ? 'selected' : ''}>${s}</option>`).join('');
                    }
                }
                const pCol = row.querySelector('.rule-primary-column');
                const pColKey = `${rule.primary_file}|${rule.primary_sheet}`;
                if (colData[pColKey]?.success) {
                    pCol.innerHTML = '<option value="">Column</option>' + 
                        colData[pColKey].columns.map(c => `<option value="${c}" ${String(c) === String(rule.primary_column) ? 'selected' : ''}>${c}</option>`).join('');
                } else if (rule.primary_file?.startsWith('primary_')) {
                    const pSelected = rule.primary_column === 'Order ID' ? 'selected' : '';
                    const uSelected = rule.primary_column === 'Unique_ID' ? 'selected' : '';
                    const sSelected = rule.primary_column === 'Source_File_Name' ? 'selected' : '';
                    const salesSelected = rule.primary_column === 'Sales Amount' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    pCol.innerHTML = '<option value="">Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>` +
                        '<option value="Sales Amount"' + (salesSelected ? ' selected' : '') + '>Sales Amount</option>';
                }
                
                // Secondary
                const sFile = row.querySelector('.rule-secondary-file');
                sFile.value = rule.secondary_file || '';
                const sSheet = row.querySelector('.rule-secondary-sheet');
                if (rule.secondary_file) {
                    if (rule.secondary_file.startsWith('primary_')) {
                        sSheet.innerHTML = '<option value="Working" selected>Working</option>';
                    } else if (sheetData[rule.secondary_file]?.success) {
                        sSheet.innerHTML = '<option value="">Sheet</option>' + 
                            sheetData[rule.secondary_file].sheets.map(s => `<option value="${s}" ${s === rule.secondary_sheet ? 'selected' : ''}>${s}</option>`).join('');
                    }
                }
                const sCol = row.querySelector('.rule-secondary-column');
                const sColKey = `${rule.secondary_file}|${rule.secondary_sheet}`;
                if (colData[sColKey]?.success) {
                    sCol.innerHTML = '<option value="">Column</option>' + 
                        colData[sColKey].columns.map(c => `<option value="${c}" ${String(c) === String(rule.secondary_column) ? 'selected' : ''}>${c}</option>`).join('');
                } else if (rule.secondary_file?.startsWith('primary_')) {
                    const pSelected = rule.secondary_column === 'Order ID' ? 'selected' : '';
                    const uSelected = rule.secondary_column === 'Unique_ID' ? 'selected' : '';
                    const sSelected = rule.secondary_column === 'Source_File_Name' ? 'selected' : '';
                    const salesSelected = rule.secondary_column === 'Sales Amount' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    sCol.innerHTML = '<option value="">Match Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>` +
                        '<option value="Sales Amount"' + (salesSelected ? ' selected' : '') + '>Sales Amount</option>';
                }
                
                // Extract
                const eFile = row.querySelector('.rule-extract-file');
                eFile.value = rule.extract_file || '';
                const eSheet = row.querySelector('.rule-extract-sheet');
                if (rule.extract_file) {
                    if (rule.extract_file.startsWith('primary_')) {
                        eSheet.innerHTML = '<option value="Working" selected>Working</option>';
                    } else if (sheetData[rule.extract_file]?.success) {
                        eSheet.innerHTML = '<option value="">Sheet</option>' + 
                            sheetData[rule.extract_file].sheets.map(s => `<option value="${s}" ${s === rule.extract_sheet ? 'selected' : ''}>${s}</option>`).join('');
                    }
                }
                const eCol = row.querySelector('.rule-extract-column');
                const eColKey = `${rule.extract_file}|${rule.extract_sheet}`;
                if (colData[eColKey]?.success) {
                    eCol.innerHTML = '<option value="">Column</option>' + 
                        colData[eColKey].columns.map(c => `<option value="${c}" ${String(c) === String(rule.extract_column) ? 'selected' : ''}>${c}</option>`).join('');
                } else if (rule.extract_file?.startsWith('primary_')) {
                    const pSelected = rule.extract_column === 'Order ID' ? 'selected' : '';
                    const uSelected = rule.extract_column === 'Unique_ID' ? 'selected' : '';
                    const sSelected = rule.extract_column === 'Source_File_Name' ? 'selected' : '';
                    const salesSelected = rule.extract_column === 'Sales Amount' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    eCol.innerHTML = '<option value="">Extract Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>` +
                        '<option value="Sales Amount"' + (salesSelected ? ' selected' : '') + '>Sales Amount</option>';
                }
            }
            
            // Update counter
            const maxId = Math.max(...rowIds.map(r => parseInt(r.rowId) || 0));
            matchingRuleCounter = maxId + 1;
            
            // Step 4: Restore column conditions for match rules
            for (const { rowId, rule } of rowIds) {
                if (rule.rule_type === 'calculation') continue;
                if (rule.column_condition && rule.column_condition.enabled) {
                    restoreColumnCondition(rowId, rule.column_condition);
                }
            }
            
            // Step 5: Refresh all output column dropdowns to show used columns as disabled
            refreshAllColumnDropdowns();
        }

        async function populateRuleFileDropdownsForRow(rowId) {
            // Same as populateRuleFileDropdowns but for a specific row
            const foldersData = await apiCall('/api/folders');
            let allFilesList = [];
            let masterFiles = [];
            
            if (foldersData.success) {
                for (const folder of foldersData.folders) {
                    const filesData = await apiCall(`/api/files/${folder.id}`);
                    if (filesData.success) {
                        allFilesList = allFilesList.concat(filesData.files);
                    }
                }
                
                // Fetch master files for all folders
                const masterPromises = foldersData.folders.map(folder => 
                    apiCall(`/api/master/${folder.id}`).then(res => {
                        if (res.success && res.master && res.master.exists) {
                            return {
                                id: `master_${folder.id}`,
                                original_name: `Master_File_${folder.name}`,
                                is_master: true,
                                folder_id: folder.id,
                                folder_name: folder.name,
                                row_count: res.master.row_count
                            };
                        }
                        return null;
                    }).catch(() => null)
                );
                const masterResults = await Promise.all(masterPromises);
                masterFiles = masterResults.filter(m => m !== null);
            }

            const primaryData = await apiCall('/api/primary/files');
            const rulesData = await apiCall('/api/rules/1');
            
            let primaryFiles = [];
            if (primaryData.success && primaryData.files && primaryData.files.length > 0) {
                const sorted = primaryData.files.sort((a, b) => new Date(b.created) - new Date(a.created));
                const latest = sorted[0];
                
                let columnName = 'Primary Data';
                let totalUnique = '';
                if (rulesData.success && rulesData.rules && rulesData.rules.length > 0) {
                    const latestRule = rulesData.rules[rulesData.rules.length - 1];
                    try {
                        const config = JSON.parse(latestRule.config);
                        if (config.column) columnName = config.column;
                        if (config.total_unique) totalUnique = ` (${config.total_unique.toLocaleString()} unique)`;
                    } catch(e) {}
                }
                
                primaryFiles = [{
                    id: `primary_latest`,
                    original_name: `Primary file${totalUnique}`,
                    is_primary: true,
                    file_path: latest.path,
                    real_name: latest.name
                }];
            }

            const row = document.getElementById(`rule-row-${rowId}`);
            const fileSelects = row.querySelectorAll('select[class*="file"]');
            
            fileSelects.forEach(select => {
                const isPrimaryFileSelect = select.classList.contains('rule-primary-file');
                const currentValue = select.value;
                
                if (isPrimaryFileSelect) {
                    select.innerHTML = '';
                    if (primaryFiles.length > 0) {
                        const pf = primaryFiles[0];
                        select.innerHTML += `<option value="${pf.id}" data-primary="true" data-real-name="${pf.real_name}">${pf.original_name}</option>`;
                        select.value = pf.id;
                        // Auto-trigger change to load sheets
                        setTimeout(() => {
                            if (select.onchange) {
                                select.onchange();
                            } else {
                                select.dispatchEvent(new Event('change'));
                            }
                        }, 50);
                    } else {
                        select.innerHTML = '<option value="">-- No Primary Data --</option>';
                    }
                } else {
                    select.innerHTML = '<option value="">File</option>';
                    
                    // Add regular files
                    allFilesList.forEach(file => {
                        select.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                    });
                    
                    // Add master files
                    if (masterFiles.length > 0) {
                        select.innerHTML += `<optgroup label="--- Master Files ---">`;
                        masterFiles.forEach(file => {
                            select.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                        });
                        select.innerHTML += `</optgroup>`;
                    }
                    
                    // Add ONLY the latest primary file with column name
                    if (primaryFiles.length > 0) {
                        const pf = primaryFiles[0];
                        select.innerHTML += `<optgroup label="--- Primary Data (Latest) ---">`;
                        select.innerHTML += `<option value="${pf.id}" data-primary="true" data-real-name="${pf.real_name}">${pf.original_name}</option>`;
                        select.innerHTML += `</optgroup>`;
                    }
                    
                    if (currentValue) select.value = currentValue;
                }
            });
        }

        async function loadPhase1Sheets() {
            const fileId = document.getElementById('phase1-file').value;
            const sheetSelect = document.getElementById('phase1-sheet');
            const salesCol = document.getElementById('phase1-sales-column');
            
            if (!fileId) {
                sheetSelect.innerHTML = '<option value="">-- Select Sheet --</option>';
                if (salesCol) salesCol.innerHTML = '<option value="">-- Select Column --</option>';
                return;
            }

            let data;
            if (fileId.startsWith('master_')) {
                // Master file - extract folder_id and call master API
                const folderId = fileId.replace('master_', '');
                data = await apiCall(`/api/master/${folderId}/sheets`);
            } else if (fileId.startsWith('primary_')) {
                // Primary data file - always has Working sheet
                data = { success: true, sheets: ['Working'] };
            } else {
                // Regular file
                data = await apiCall(`/api/files/${fileId}/sheets`);
            }
            
            sheetSelect.innerHTML = '<option value="">-- Select Sheet --</option>';
            
            if (data.success && data.sheets) {
                data.sheets.forEach(sheet => {
                    sheetSelect.innerHTML += `<option value="${sheet}">${sheet}</option>`;
                });
            }
        }

        async function loadPhase1Columns() {
            const fileId = document.getElementById('phase1-file').value;
            const sheetName = document.getElementById('phase1-sheet').value;
            const colSelect = document.getElementById('phase1-column');
            const salesSelect = document.getElementById('phase1-sales-column');
            
            if (!fileId || !sheetName) {
                colSelect.innerHTML = '<option value="">-- Select Column --</option>';
                if (salesSelect) salesSelect.innerHTML = '<option value="">-- Select Column --</option>';
                return;
            }

            let data;
            if (fileId.startsWith('master_')) {
                // Master file - extract folder_id and call master API
                const folderId = fileId.replace('master_', '');
                data = await apiCall(`/api/master/${folderId}/columns`);
            } else if (fileId.startsWith('primary_')) {
                // Primary data file - always has Unique_ID, Source_File_Name and Primary_Value
                data = { success: true, columns: ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'] };
            } else {
                // Regular file
                data = await apiCall(`/api/files/${fileId}/columns?sheet_name=${encodeURIComponent(sheetName)}`);
            }
            
            colSelect.innerHTML = '<option value="">-- Select Column --</option>';
            
            if (data.success && data.columns) {
                data.columns.forEach(col => {
                    colSelect.innerHTML += `<option value="${col}">${col}</option>`;
                });
            }
            
            // Also populate sales amount column dropdown
            if (salesSelect) {
                salesSelect.innerHTML = '<option value="">-- Select Column --</option>';
                if (data.success && data.columns) {
                    data.columns.forEach(col => {
                        salesSelect.innerHTML += `<option value="${col}">${col}</option>`;
                    });
                }
            }
        }

        async function savePhase1Rule() {
            try {
            clearFieldErrors();
            
            // Show processing spinner
            const saveBtn = document.getElementById('phase1-save-btn');
            const spinner = document.getElementById('phase1-save-spinner');
            const saveText = document.getElementById('phase1-save-text');
            if (saveBtn) saveBtn.disabled = true;
            if (spinner) spinner.classList.remove('hidden');
            if (saveText) saveText.textContent = 'Processing...';
            
            const fileId = String(document.getElementById('phase1-file').value || '');
            const sheetName = String(document.getElementById('phase1-sheet').value || '');
            const column = String(document.getElementById('phase1-column').value || '');
            const salesColumn = String(document.getElementById('phase1-sales-column')?.value || '');

            let hasError = false;
            let firstErrorElement = null;

            if (!fileId) {
                showFieldError('phase1-file', 'Please select a file');
                hasError = true;
                if (!firstErrorElement) firstErrorElement = document.getElementById('phase1-file');
            }
            if (!sheetName) {
                showFieldError('phase1-sheet', 'Please select a sheet');
                hasError = true;
                if (!firstErrorElement) firstErrorElement = document.getElementById('phase1-sheet');
            }
            if (!column) {
                showFieldError('phase1-column', 'Please select a column');
                hasError = true;
                if (!firstErrorElement) firstErrorElement = document.getElementById('phase1-column');
            }
            if (!salesColumn) {
                showFieldError('phase1-sales-column', 'Please select a sales amount column');
                hasError = true;
                if (!firstErrorElement) firstErrorElement = document.getElementById('phase1-sales-column');
            }

            if (hasError) {
                // Reset spinner on validation failure
                if (saveBtn) saveBtn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                if (saveText) saveText.textContent = 'Save File Processing';
                showToast('Please fix the highlighted fields before saving', 'error');
                if (firstErrorElement) firstErrorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }

            // Step 1: Generate primary data file with unique values
            const generateForm = new FormData();
            generateForm.append('file_id', fileId);
            generateForm.append('sheet_name', sheetName);
            generateForm.append('column_name', column);
            generateForm.append('header_row', 1);
            generateForm.append('sales_amount_column', salesColumn);

            const genData = await apiCall('/api/primary/generate', {
                method: 'POST',
                body: generateForm
            });
            
            if (!genData || !genData.success) {
                if (saveBtn) saveBtn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                if (saveText) saveText.textContent = 'Save File Processing';
                showToast('Failed to generate primary data: ' + (genData?.detail || 'Unknown error'), 'error');
                return;
            }

            // Step 2: Save the rule configuration
            const config = JSON.stringify({
                file_id: fileId,
                sheet_name: sheetName,
                column: column,
                sales_column: salesColumn || null,
                primary_file: genData.primary_file,
                total_unique: genData.total_unique
            });

            const formData = new FormData();
            formData.append('phase', 1);
            formData.append('config', config);
            formData.append('name', 'Primary Data Selection');

            const data = await apiCall('/api/rules', {
                method: 'POST',
                body: formData
            });

            if (data.success) {
                // Reset spinner on success
                if (saveBtn) saveBtn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                if (saveText) saveText.textContent = 'Save File Processing';
                isRulesPageLoaded = false; // Force reload on next visit since data changed
                window.primaryValueColumnName = column;
                showToast(`Primary data generated! ${genData.total_unique} unique values found.`, 'success');
                
                // Immediately update Phase 4 available columns
                await loadAvailableColumnsForSummary();
                
                // Update preview table header label dynamically
                const pHeader = document.getElementById('phase1-preview-primary-header');
                if (pHeader) {
                    pHeader.textContent = 'Order ID';
                }
                
                // Show real preview of unique values
                document.getElementById('phase1-preview').classList.remove('hidden');
                
                // Update unique count badge
                const countBadge = document.getElementById('phase1-unique-count');
                if (countBadge) {
                    countBadge.textContent = `${genData.total_unique.toLocaleString()} unique values`;
                }
                
                if (genData.preview && genData.preview.length > 0) {
                    document.getElementById('phase1-preview-body').innerHTML = genData.preview.map((row, idx) => `
                        <tr>
                            <td class="px-3 py-2 text-gray-900 font-medium">${row.Unique_ID}</td>
                            <td class="px-3 py-2 text-gray-700">${row.Source_File_Name || ''}</td>
                            <td class="px-3 py-2 text-gray-700">${row['Order ID']}</td>
                            <td class="px-3 py-2 text-gray-700">${row['Sales Amount'] != null ? row['Sales Amount'].toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : ''}</td>
                        </tr>
                    `).join('');
                }

                // Add download button
                const downloadBtn = document.createElement('div');
                downloadBtn.className = 'mt-4 flex items-center justify-between';
                downloadBtn.innerHTML = `
                    <span class="text-sm text-gray-600">Download the generated primary file to verify:</span>
                    <a href="${genData.download_url}" target="_blank" class="inline-flex items-center space-x-2 bg-green-600 text-white text-sm font-medium py-2 px-4 rounded-lg hover:bg-green-700 transition-colors">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        <span>Download Primary File</span>
                    </a>
                `;
                
                const previewDiv = document.getElementById('phase1-preview');
                // Remove existing download button if any
                const existingBtn = previewDiv.querySelector('.mt-4.flex');
                if (existingBtn) existingBtn.remove();
                previewDiv.appendChild(downloadBtn);
            }
        
            } catch(err) {

                console.error("Error in savePhase1Rule:", err);
                const saveBtn = document.getElementById('phase1-save-btn');
                const spinner = document.getElementById('phase1-save-spinner');
                const saveText = document.getElementById('phase1-save-text');
                if (saveBtn) saveBtn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                if (saveText) saveText.textContent = 'Save File Processing';
                showToast(err.message || 'An unexpected error occurred.', 'error');

            }
        }

        // Phase 2: Calculation Rule (operates on already-created columns)
        async function addCalculationRuleRow(savedData = null) {
            const tbody = document.getElementById('matching-rules-body');
            
            // Remove empty state / message row if present so it doesn't interfere with save
            const emptyMsg = tbody.querySelector('td[colspan="9"]');
            if (emptyMsg) {
                const msgRow = emptyMsg.closest('tr');
                if (msgRow) msgRow.remove();
            }
            
            const rowId = matchingRuleCounter++;
            
            // Get all previously created column names from existing rows
            // Include columns from ALL rules (both match and calculation)
            // This allows chaining calculations (e.g., Variance = Net Sales - Net Settlement)
            const existingRows = tbody.querySelectorAll('tr');
            let createdColumns = [];
            existingRows.forEach(row => {
                const colNameInput = row.querySelector('.rule-column-name');
                if (colNameInput && colNameInput.value.trim()) {
                    createdColumns.push(colNameInput.value.trim());
                }
            });
            
            // Also add primary data columns
            createdColumns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount', ...createdColumns];
            // Remove duplicates
            createdColumns = [...new Set(createdColumns)];
            
            const tr = document.createElement('tr');
            tr.className = 'rule-row bg-white border-b border-gray-100';
            tr.id = `rule-row-${rowId}`;
            tr.dataset.ruleType = 'calculation'; // Mark as calculation rule
            
            // Prevent circular dependency: exclude the current rule's own column name
            // from being selectable as its own input
            const currentColName = savedData?.column_name || '';
            const filteredOptions = createdColumns.filter(col => col !== currentColName);
            const colOptions = filteredOptions.map(col => `<option value="${col}">${col}</option>`).join('');
            
            // Determine initial columns (for saved data loading)
            let initialColsHtml = '';
            if (savedData && savedData.columns && savedData.columns.length > 0) {
                savedData.columns.forEach((col, idx) => {
                    initialColsHtml += buildCalcColumnRow(rowId, idx, colOptions, col);
                });
            } else {
                // Default: start with 2 columns
                initialColsHtml += buildCalcColumnRow(rowId, 0, colOptions, '');
                initialColsHtml += buildCalcColumnRow(rowId, 1, colOptions, '');
            }
            
            tr.innerHTML = `
                <td class="px-2 py-3 text-center">
                    <input type="checkbox" class="row-condition-checkbox w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500" 
                        onchange="onToggleConditionCheckbox(${rowId})" title="Enable Column Condition">
                </td>
                <td class="px-3 py-3 font-mono text-sm text-gray-500">#${rowId}</td>
                <td class="px-3 py-3" colspan="4">
                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <label class="text-xs font-medium text-gray-600">Columns to Calculate</label>
                            <select class="calc-operation w-32 text-xs border border-gray-300 rounded px-2 py-1 ml-2">
                                <option value="addition" ${savedData?.operation === 'addition' ? 'selected' : ''}>Addition (+)</option>
                                <option value="subtraction" ${savedData?.operation === 'subtraction' ? 'selected' : ''}>Subtraction (-)</option>
                                <option value="multiply" ${savedData?.operation === 'multiply' ? 'selected' : ''}>Multiply (×)</option>
                                <option value="divide" ${savedData?.operation === 'divide' ? 'selected' : ''}>Divide (÷)</option>
                            </select>
                        </div>
                        <div class="calc-columns-list space-y-1">
                            ${initialColsHtml}
                        </div>
                        <button onclick="addCalcColumn(this)" class="mt-1 flex items-center space-x-1 text-xs text-orange-600 hover:text-orange-800 font-medium">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                            </svg>
                            <span>Add Column</span>
                        </button>
                    </div>
                </td>
                <td class="px-3 py-3">
                    <select class="rule-output-column w-full text-xs border border-gray-300 rounded px-2 py-1 uppercase"
                        onchange="refreshAllColumnDropdowns()">
                        ${generateColumnLetterOptions(savedData?.output_column || getAutoAssignedColumn(), getAllUsedOutputColumns())}
                    </select>
                </td>
                <td class="px-3 py-3">
                    <div class="space-y-2">
                        <input type="text" class="rule-column-name w-full text-xs border border-gray-300 rounded px-2 py-1" 
                            placeholder="e.g. Grand_Total" maxlength="50" value="${savedData?.column_name || ''}">
                        <input type="text" class="rule-default-value w-full text-xs border border-gray-300 rounded px-2 py-1" 
                            placeholder="Default Value (optional)" maxlength="100" value="${savedData?.default_value || ''}">
                    </div>
                </td>
                <td class="px-3 py-3">
                    <button onclick="deleteRuleRow(${rowId})" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </td>
            `;
            
            tbody.appendChild(tr);
            if (!savedData) {
                showToast('Calculation rule added. Add multiple columns to sum.', 'info');
            }
        }

        function buildCalcColumnRow(rowId, colIndex, colOptions, selectedValue = '') {
            return `
                <div class="calc-col-row flex items-center space-x-2" data-col-idx="${colIndex}">
                    <span class="text-xs text-gray-500 w-6">${colIndex + 1}.</span>
                    <select class="calc-column w-full text-xs border border-gray-300 rounded px-2 py-1">
                        <option value="">Select Column</option>
                        ${colOptions}
                    </select>
                    <button onclick="removeCalcColumn(this)" class="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50 transition-colors" title="Remove">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            `.replace(`<option value="${selectedValue}">`, `<option value="${selectedValue}" selected>`);
        }

        function addCalcColumn(source) {
            let list = null;
            let element = source;
            
            // Climb up DOM tree looking for .calc-columns-list
            for (let i = 0; i < 6; i++) {
                if (!element || !(element instanceof Element)) break;
                // Check if current element has the list as a child
                const found = element.querySelector('.calc-columns-list');
                if (found) {
                    list = found;
                    break;
                }
                element = element.parentElement;
            }
            
            if (!list) {
                console.error('Could not find .calc-columns-list');
                showToast('Error: Could not find column list', 'error');
                return;
            }
            
            const colIndex = list.querySelectorAll('.calc-col-row').length;
            
            // Get current column options from all existing rows
            // Include columns from ALL rules to allow calculation chaining
            const existingRows = document.querySelectorAll('#matching-rules-body tr');
            let createdColumns = [];
            existingRows.forEach(r => {
                const colNameInput = r.querySelector('.rule-column-name');
                if (colNameInput && colNameInput.value.trim()) {
                    createdColumns.push(colNameInput.value.trim());
                }
            });
            createdColumns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount', ...createdColumns];
            createdColumns = [...new Set(createdColumns)];
            
            // Prevent circular dependency: exclude the column name of the calculation rule
            // that the user is currently adding columns to
            const rowNameInput = source.closest('tr')?.querySelector('.rule-column-name');
            const currentColName = rowNameInput?.value?.trim() || '';
            const filteredOptions = createdColumns.filter(col => col !== currentColName);
            const colOptions = filteredOptions.map(col => `<option value="${col}">${col}</option>`).join('');
            
            const div = document.createElement('div');
            div.innerHTML = buildCalcColumnRow(0, colIndex, colOptions);
            if (div.firstElementChild) {
                list.appendChild(div.firstElementChild);
            }
        }

        function removeCalcColumn(btn) {
            const row = btn.closest('.calc-col-row');
            if (row) {
                // Check if this is the last column
                const list = row.parentElement;
                if (list.querySelectorAll('.calc-col-row').length <= 2) {
                    showToast('Minimum 2 columns required for calculation', 'warning');
                    return;
                }
                row.remove();
                // Re-index remaining columns
                list.querySelectorAll('.calc-col-row').forEach((r, idx) => {
                    r.querySelector('span').textContent = `${idx + 1}.`;
                });
            }
        }

        // Column Condition Feature Handlers
        function onToggleConditionCheckbox(rowId) {
            const checkboxes = document.querySelectorAll('.row-condition-checkbox:checked');
            const btn = document.getElementById('btn-add-column-condition');
            if (checkboxes.length > 0) {
                btn.classList.remove('hidden');
            } else {
                btn.classList.add('hidden');
                // Also close any open condition panels
                document.querySelectorAll('.condition-panel').forEach(p => p.remove());
            }
        }

        function openColumnConditions() {
            const checkedRows = document.querySelectorAll('.row-condition-checkbox:checked');
            if (checkedRows.length === 0) {
                showToast('Please check at least one rule row to add a condition', 'warning');
                return;
            }
            
            checkedRows.forEach(cb => {
                const row = cb.closest('tr');
                const rowId = row.id.replace('rule-row-', '');
                // Remove existing panel if any
                const existing = document.getElementById(`condition-panel-${rowId}`);
                if (existing) {
                    existing.remove();
                    return;
                }
                
                // Build condition panel
                const panel = document.createElement('tr');
                panel.id = `condition-panel-${rowId}`;
                panel.className = 'condition-panel bg-purple-50 border-b border-purple-200';
                
                // Get available columns for condition dropdowns
                const allRows = document.querySelectorAll('#matching-rules-body tr');
                let availableCols = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
                allRows.forEach(r => {
                    const cn = r.querySelector('.rule-column-name');
                    if (cn && cn.value.trim()) availableCols.push(cn.value.trim());
                });
                availableCols = [...new Set(availableCols)];
                const colOptions = availableCols.map(c => {
                    const label = (c === 'Order ID') ? (window.primaryValueColumnName || 'Order ID') : c;
                    return `<option value="${c}">${label}</option>`;
                }).join('');
                
                panel.innerHTML = `
                    <td colspan="9" class="px-4 py-4">
                        <div class="bg-white rounded-lg border border-purple-200 p-4 shadow-sm">
                            <div class="flex items-center justify-between mb-3">
                                <h4 class="text-sm font-bold text-purple-800">Column Condition for Rule #${rowId}</h4>
                                <button onclick="document.getElementById('condition-panel-${rowId}').remove()" class="text-gray-400 hover:text-gray-600">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                                </button>
                            </div>
                            
                            <!-- Logic Toggle -->
                            <div class="flex items-center space-x-4 mb-3">
                                <span class="text-xs font-medium text-gray-600">Condition Logic:</span>
                                <label class="flex items-center space-x-1 cursor-pointer">
                                    <input type="radio" name="logic-${rowId}" value="AND" checked class="text-purple-600 focus:ring-purple-500">
                                    <span class="text-xs text-gray-700">AND (all must match)</span>
                                </label>
                                <label class="flex items-center space-x-1 cursor-pointer">
                                    <input type="radio" name="logic-${rowId}" value="OR" class="text-purple-600 focus:ring-purple-500">
                                    <span class="text-xs text-gray-700">OR (any can match)</span>
                                </label>
                            </div>
                            
                            <!-- Conditions List -->
                            <div id="conditions-list-${rowId}" class="space-y-2 mb-3">
                                ${buildConditionRow(rowId, 0, colOptions)}
                            </div>
                            
                            <button onclick="addConditionRowToPanel(${rowId})" class="flex items-center space-x-1 text-xs text-purple-600 hover:text-purple-800 font-medium mb-4">
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
                                <span>Add Condition</span>
                            </button>
                            
                            <!-- Extract Output Section -->
                            <div class="border-t border-purple-100 pt-3 mt-3">
                                <h5 class="text-xs font-bold text-purple-700 mb-2">EXTRACT OUTPUT (Copy & Paste)</h5>
                                <div class="flex items-center space-x-3">
                                    <div class="flex-1">
                                        <label class="text-xs text-gray-600 block mb-1">Copy data FROM column:</label>
                                        <select id="extract-source-${rowId}" class="w-full text-xs border border-gray-300 rounded px-2 py-1.5">
                                            <option value="">Select Source Column</option>
                                            ${colOptions}
                                        </select>
                                    </div>
                                    <div class="flex items-center justify-center">
                                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                                    </div>
                                    <div class="flex-1">
                                        <label class="text-xs text-gray-600 block mb-1">Paste INTO column (this rule's output):</label>
                                        <input type="text" id="extract-target-${rowId}" class="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-gray-100" readonly 
                                            value="${row.querySelector('.rule-column-name')?.value || ''}">
                                    </div>
                                </div>
                                <p class="text-xs text-gray-500 mt-2 italic">When conditions match, source column data will be copied into the target column for those rows only.</p>
                            </div>
                        </div>
                    </td>
                `;
                
                row.parentNode.insertBefore(panel, row.nextSibling);
            });
        }

        function buildConditionRow(rowId, idx, colOptions, selectedCol='', selectedOp='equal_to', val='') {
            const operators = [
                ['equal_to', 'Equal to (Numbers only)'],
                ['not_equal_to', 'Doesn\'t equal to (Numbers only)'],
                ['zero_or_blank', 'Zero or Blank'],
                ['no_zero_or_no_blank', 'No Zero or No Blank'],
                ['greater_than', 'Greater than (Numbers only)'],
                ['smaller_than', 'Smaller than (Numbers only)'],
                ['contain', 'Contain (Text)'],
                ['not_contain', 'Doesn\'t Contain (Text)'],
                ['begin_with', 'Begin with (Text)'],
                ['end_with', 'End with (Text)']
            ];
            
            let valueField = `<input type="text" class="cond-val w-40 text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Value" value="${val}">`;
            if (selectedOp === 'zero_or_blank' || selectedOp === 'no_zero_or_no_blank') {
                valueField = `<span class="text-xs text-gray-500 italic py-1.5">(no value needed)</span><input type="hidden" class="cond-val" value="">`;
            }
            
            // Warning message for equal_to and not_equal_to operators
            const showWarning = selectedOp === 'equal_to' || selectedOp === 'not_equal_to';
            const warningHtml = showWarning ? `
                <div class="col-span-full text-yellow-700 text-xs mt-1 font-medium">
                    ⚠️ Use for numeric values only. For text data like names or codes, use <strong>Contain (Text)</strong> for reliable matching.
                </div>
            ` : '';
            
            return `
                <div class="condition-row-item flex flex-wrap items-center space-x-2 bg-gray-50 rounded p-2 border border-gray-200" data-idx="${idx}">
                    <span class="text-xs font-medium text-gray-600 mr-1">(</span>
                    <span class="text-xs font-medium text-gray-500 w-8">${idx === 0 ? 'IF' : 'AND'}</span>
                    <select class="cond-col w-40 text-xs border border-gray-300 rounded px-2 py-1.5">
                        <option value="">Select Column</option>
                        ${colOptions.replace(`value="${selectedCol}"`, `value="${selectedCol}" selected`)}
                    </select>
                    <select class="cond-op w-44 text-xs border border-gray-300 rounded px-2 py-1.5" onchange="onPanelConditionOpChange(this)">
                        ${operators.map(([op, label]) => `<option value="${op}" ${op === selectedOp ? 'selected' : ''}>${label}</option>`).join('')}
                    </select>
                    <div class="cond-val-container">${valueField}</div>
                    <span class="text-xs font-medium text-gray-600 mr-1">)</span>
                    <button onclick="this.closest('.condition-row-item').remove(); reindexConditions(${rowId})" class="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                    ${warningHtml}
                </div>
            `;
        }

        function onPanelConditionOpChange(select) {
            const container = select.closest('.condition-row-item').querySelector('.cond-val-container');
            const op = select.value;
            if (op === 'zero_or_blank' || op === 'no_zero_or_no_blank') {
                container.innerHTML = `<span class="text-xs text-gray-500 italic py-1.5">(no value needed)</span><input type="hidden" class="cond-val" value="">`;
            } else {
                container.innerHTML = `<input type="text" class="cond-val w-40 text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Value">`;
            }
        }

        function addConditionRowToPanel(rowId) {
            const list = document.getElementById(`conditions-list-${rowId}`);
            const idx = list.querySelectorAll('.condition-row-item').length;
            
            const allRows = document.querySelectorAll('#matching-rules-body tr');
            let availableCols = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
            allRows.forEach(r => {
                const cn = r.querySelector('.rule-column-name');
                if (cn && cn.value.trim()) availableCols.push(cn.value.trim());
            });
            availableCols = [...new Set(availableCols)];
            const colOptions = availableCols.map(c => {
                const label = (c === 'Order ID') ? (window.primaryValueColumnName || 'Order ID') : c;
                return `<option value="${c}">${label}</option>`;
            }).join('');
            
            const div = document.createElement('div');
            div.innerHTML = buildConditionRow(rowId, idx, colOptions);
            list.appendChild(div.firstElementChild);
        }

        function reindexConditions(rowId) {
            const list = document.getElementById(`conditions-list-${rowId}`);
            list.querySelectorAll('.condition-row-item').forEach((item, idx) => {
                item.querySelector('span').textContent = idx === 0 ? 'IF' : 'AND';
            });
        }

        function getColumnConditionConfig(rowId) {
            const panel = document.getElementById(`condition-panel-${rowId}`);
            if (!panel) return null;
            
            const logic = panel.querySelector(`input[name="logic-${rowId}"]:checked`)?.value || 'AND';
            const conditions = [];
            
            panel.querySelectorAll('.condition-row-item').forEach(item => {
                const col = item.querySelector('.cond-col').value;
                const op = item.querySelector('.cond-op').value;
                const val = item.querySelector('.cond-val')?.value || '';
                if (col && op) {
                    conditions.push({ column: col, operator: op, value: val });
                }
            });
            
            const sourceCol = panel.querySelector(`#extract-source-${rowId}`)?.value || '';
            
            // Always use the CURRENT column name from the rule row, not the stale readonly input
            const row = document.getElementById(`rule-row-${rowId}`);
            const targetCol = row?.querySelector('.rule-column-name')?.value?.trim() || '';
            
            if (conditions.length === 0 || !sourceCol || !targetCol) return null;
            
            return {
                enabled: true,
                logic: logic,
                conditions: conditions,
                extract_source_column: sourceCol,
                extract_target_column: targetCol
            };
        }

        function restoreColumnCondition(rowId, colCondData) {
            if (!colCondData || !colCondData.enabled) return;
            
            const row = document.getElementById(`rule-row-${rowId}`);
            if (!row) return;
            
            // Check the checkbox
            const checkbox = row.querySelector('.row-condition-checkbox');
            if (checkbox) checkbox.checked = true;
            
            // Show the "Add Column Condition" button
            onToggleConditionCheckbox(rowId);
            
            // Remove existing panel if any
            const existing = document.getElementById(`condition-panel-${rowId}`);
            if (existing) existing.remove();
            
            // Get available columns for condition dropdowns
            const allRows = document.querySelectorAll('#matching-rules-body tr');
            let availableCols = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
            allRows.forEach(r => {
                const cn = r.querySelector('.rule-column-name');
                if (cn && cn.value.trim()) availableCols.push(cn.value.trim());
            });
            availableCols = [...new Set(availableCols)];
            const colOptions = availableCols.map(c => {
                const label = (c === 'Order ID') ? (window.primaryValueColumnName || 'Order ID') : c;
                return `<option value="${c}">${label}</option>`;
            }).join('');
            
            // Build condition rows from saved data
            let conditionsHtml = '';
            if (colCondData.conditions && colCondData.conditions.length > 0) {
                colCondData.conditions.forEach((cond, idx) => {
                    conditionsHtml += buildConditionRow(rowId, idx, colOptions, cond.column, cond.operator, cond.value);
                });
            } else {
                conditionsHtml = buildConditionRow(rowId, 0, colOptions);
            }
            
            // Create the panel
            const panel = document.createElement('tr');
            panel.id = `condition-panel-${rowId}`;
            panel.className = 'condition-panel bg-purple-50 border-b border-purple-200';
            
            const logicValue = colCondData.logic || 'AND';
            const sourceCol = colCondData.extract_source_column || '';
            const targetCol = colCondData.extract_target_column || '';
            
            panel.innerHTML = `
                <td colspan="9" class="px-4 py-4">
                    <div class="bg-white rounded-lg border border-purple-200 p-4 shadow-sm">
                        <div class="flex items-center justify-between mb-3">
                            <h4 class="text-sm font-bold text-purple-800">Column Condition for Rule #${rowId}</h4>
                            <button onclick="document.getElementById('condition-panel-${rowId}').remove()" class="text-gray-400 hover:text-gray-600">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                            </button>
                        </div>
                        
                        <!-- Logic Toggle -->
                        <div class="flex items-center space-x-4 mb-3">
                            <span class="text-xs font-medium text-gray-600">Condition Logic:</span>
                            <label class="flex items-center space-x-1 cursor-pointer">
                                <input type="radio" name="logic-${rowId}" value="AND" ${logicValue === 'AND' ? 'checked' : ''} class="text-purple-600 focus:ring-purple-500">
                                <span class="text-xs text-gray-700">AND (all must match)</span>
                            </label>
                            <label class="flex items-center space-x-1 cursor-pointer">
                                <input type="radio" name="logic-${rowId}" value="OR" ${logicValue === 'OR' ? 'checked' : ''} class="text-purple-600 focus:ring-purple-500">
                                <span class="text-xs text-gray-700">OR (any can match)</span>
                            </label>
                        </div>
                        
                        <!-- Conditions List -->
                        <div id="conditions-list-${rowId}" class="space-y-2 mb-3">
                            ${conditionsHtml}
                        </div>
                        
                        <button onclick="addConditionRowToPanel(${rowId})" class="flex items-center space-x-1 text-xs text-purple-600 hover:text-purple-800 font-medium mb-4">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
                            <span>Add Condition</span>
                        </button>
                        
                        <!-- Extract Output Section -->
                        <div class="border-t border-purple-100 pt-3 mt-3">
                            <h5 class="text-xs font-bold text-purple-700 mb-2">EXTRACT OUTPUT (Copy & Paste)</h5>
                            <div class="flex items-center space-x-3">
                                <div class="flex-1">
                                    <label class="text-xs text-gray-600 block mb-1">Copy data FROM column:</label>
                                    <select id="extract-source-${rowId}" class="w-full text-xs border border-gray-300 rounded px-2 py-1.5">
                                        <option value="">Select Source Column</option>
                                        ${colOptions.replace(`value="${sourceCol}"`, `value="${sourceCol}" selected`)}
                                    </select>
                                </div>
                                <div class="flex items-center justify-center">
                                    <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                                </div>
                                <div class="flex-1">
                                    <label class="text-xs text-gray-600 block mb-1">Paste INTO column (this rule's output):</label>
                                    <input type="text" id="extract-target-${rowId}" class="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-gray-100" readonly 
                                        value="${targetCol}">
                                </div>
                            </div>
                            <p class="text-xs text-gray-500 mt-2 italic">When conditions match, source column data will be copied into the target column for those rows only.</p>
                        </div>
                    </div>
                </td>
            `;
            
            row.parentNode.insertBefore(panel, row.nextSibling);
        }

        // Phase 2: Matching Rules
        function addMatchingRuleRow() {
            const tbody = document.getElementById('matching-rules-body');
            
            // Remove empty state / message row if present so it doesn't interfere with save
            const emptyMsg = tbody.querySelector('td[colspan="9"]');
            if (emptyMsg) {
                const msgRow = emptyMsg.closest('tr');
                if (msgRow) msgRow.remove();
            }
            
            const rowId = matchingRuleCounter++;
            
            // Get auto-assigned column
            const autoColumn = getAutoAssignedColumn();
            const usedColumns = getAllUsedOutputColumns();
            
            const tr = document.createElement('tr');
            tr.className = 'rule-row bg-white border-b border-gray-100';
            tr.id = `rule-row-${rowId}`;
            
            tr.innerHTML = `
                <td class="px-2 py-3 text-center">
                    <input type="checkbox" class="row-condition-checkbox w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500" 
                        onchange="onToggleConditionCheckbox(${rowId})" title="Enable Column Condition">
                </td>
                <td class="px-3 py-3 font-mono text-sm text-gray-500">#${rowId}</td>
                <td class="px-3 py-3">
                    <div class="space-y-2">
                        <select class="rule-primary-file w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleSheets(this, ${rowId}, 'primary')">
                            <option value="">File</option>
                        </select>
                        <select class="rule-primary-sheet w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleColumns(this, ${rowId}, 'primary')">
                            <option value="">Sheet</option>
                        </select>
                        <select class="rule-primary-column w-full text-xs border border-gray-300 rounded px-2 py-1">
                            <option value="">Column</option>
                        </select>
                    </div>
                </td>
                <td class="px-3 py-3">
                    <select class="rule-type w-full text-xs border border-gray-300 rounded px-2 py-1">
                                <option value="match">Match (VLOOKUP)</option>
                                <option value="sumif">Sumif Match</option>
                                <option value="countif">Countif Match</option>
                                <option value="addition">Addition</option>
                                <option value="subtraction">Subtraction</option>
                    </select>
                </td>
                <td class="px-3 py-3">
                    <div class="space-y-2">
                        <select class="rule-secondary-file w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleSheets(this, ${rowId}, 'secondary')">
                            <option value="">File</option>
                        </select>
                        <select class="rule-secondary-sheet w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleColumns(this, ${rowId}, 'secondary')">
                            <option value="">Sheet</option>
                        </select>
                        <select class="rule-secondary-column w-full text-xs border border-gray-300 rounded px-2 py-1">
                            <option value="">Match Column</option>
                        </select>
                    </div>
                </td>
                <td class="px-3 py-3">
                    <div class="space-y-2">
                        <select class="rule-extract-file w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleSheets(this, ${rowId}, 'extract')">
                            <option value="">File</option>
                        </select>
                        <select class="rule-extract-sheet w-full text-xs border border-gray-300 rounded px-2 py-1" onchange="loadRuleColumns(this, ${rowId}, 'extract')">
                            <option value="">Sheet</option>
                        </select>
                        <select class="rule-extract-column w-full text-xs border border-gray-300 rounded px-2 py-1">
                            <option value="">Extract Column</option>
                        </select>
                    </div>
                </td>
                <td class="px-3 py-3">
                    <select class="rule-output-column w-full text-xs border border-gray-300 rounded px-2 py-1 uppercase"
                        onchange="refreshAllColumnDropdowns()">
                        ${generateColumnLetterOptions(autoColumn, usedColumns)}
                    </select>
                </td>
                <td class="px-3 py-3">
                    <div class="space-y-2">
                        <input type="text" class="rule-column-name w-full text-xs border border-gray-300 rounded px-2 py-1" 
                            placeholder="e.g. Order_ID, Result" maxlength="50">
                        <input type="text" class="rule-default-value w-full text-xs border border-gray-300 rounded px-2 py-1" 
                            placeholder="Default Value (optional)" maxlength="100">
                    </div>
                </td>
                <td class="px-3 py-3">
                    <button onclick="deleteRuleRow(${rowId})" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </td>
            `;
            
            tbody.appendChild(tr);
            
            // Populate file dropdowns
            populateRuleFileDropdowns(rowId);
        }

        async function populateRuleFileDropdowns(rowId) {
            // Get all files from all folders
            const foldersData = await apiCall('/api/folders');
            let allFilesList = [];
            let masterFiles = [];
            
            if (foldersData.success) {
                for (const folder of foldersData.folders) {
                    const filesData = await apiCall(`/api/files/${folder.id}`);
                    if (filesData.success) {
                        allFilesList = allFilesList.concat(filesData.files);
                    }
                }
                
                // Fetch master files for all folders
                const masterPromises = foldersData.folders.map(folder => 
                    apiCall(`/api/master/${folder.id}`).then(res => {
                        if (res.success && res.master && res.master.exists) {
                            return {
                                id: `master_${folder.id}`,
                                original_name: `Master_File_${folder.name}`,
                                is_master: true,
                                folder_id: folder.id,
                                folder_name: folder.name,
                                row_count: res.master.row_count
                            };
                        }
                        return null;
                    }).catch(() => null)
                );
                const masterResults = await Promise.all(masterPromises);
                masterFiles = masterResults.filter(m => m !== null);
            }

            // Get primary data files - fetch rules to get column names
            const primaryData = await apiCall('/api/primary/files');
            const rulesData = await apiCall('/api/rules/1');
            
            let primaryFiles = [];
            if (primaryData.success && primaryData.files && primaryData.files.length > 0) {
                // Sort by creation date (newest first) and take only the LATEST one
                const sorted = primaryData.files.sort((a, b) => new Date(b.created) - new Date(a.created));
                const latest = sorted[0];
                
                // Get column name from the rule config
                let columnName = 'Primary Data';
                let totalUnique = '';
                if (rulesData.success && rulesData.rules && rulesData.rules.length > 0) {
                    // Get the latest rule
                    const latestRule = rulesData.rules[rulesData.rules.length - 1];
                    try {
                        const config = JSON.parse(latestRule.config);
                        if (config.column) columnName = config.column;
                        if (config.total_unique) totalUnique = ` (${config.total_unique.toLocaleString()} unique)`;
                    } catch(e) {}
                }
                window.primaryValueColumnName = columnName;
                
                primaryFiles = [{
                    id: `primary_latest`,
                    original_name: `Primary file${totalUnique}`,
                    is_primary: true,
                    file_path: latest.path,
                    real_name: latest.name
                }];
            }

            const row = document.getElementById(`rule-row-${rowId}`);
            const fileSelects = row.querySelectorAll('select[class*="file"]');
            
            fileSelects.forEach(select => {
                const isPrimaryFileSelect = select.classList.contains('rule-primary-file');
                const currentValue = select.value;
                
                if (isPrimaryFileSelect) {
                    select.innerHTML = '';
                    if (primaryFiles.length > 0) {
                        const pf = primaryFiles[0];
                        select.innerHTML += `<option value="${pf.id}" data-primary="true" data-real-name="${pf.real_name}">${pf.original_name}</option>`;
                        select.value = pf.id;
                        // Auto-trigger change to load sheets
                        setTimeout(() => {
                            if (select.onchange) {
                                select.onchange();
                            } else {
                                select.dispatchEvent(new Event('change'));
                            }
                        }, 50);
                    } else {
                        select.innerHTML = '<option value="">-- No Primary Data --</option>';
                    }
                } else {
                    select.innerHTML = '<option value="">File</option>';
                    
                    // Add regular files
                    allFilesList.forEach(file => {
                        select.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                    });
                    
                    // Add master files
                    if (masterFiles.length > 0) {
                        select.innerHTML += `<optgroup label="--- Master Files ---">`;
                        masterFiles.forEach(file => {
                            select.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                        });
                        select.innerHTML += `</optgroup>`;
                    }
                    
                    // Add ONLY the latest primary file with column name
                    if (primaryFiles.length > 0) {
                        const pf = primaryFiles[0];
                        select.innerHTML += `<optgroup label="--- Primary Data (Latest) ---">`;
                        select.innerHTML += `<option value="${pf.id}" data-primary="true" data-real-name="${pf.real_name}">${pf.original_name}</option>`;
                        select.innerHTML += `</optgroup>`;
                    }
                    
                    if (currentValue) select.value = currentValue;
                }
            });
        }

        async function loadRuleSheets(selectElement, rowId, type) {
            const fileId = selectElement.value;
            if (!fileId) return;

            const row = document.getElementById(`rule-row-${rowId}`);
            let sheetSelect;
            if (type === 'primary') sheetSelect = row.querySelector('.rule-primary-sheet');
            else if (type === 'secondary') sheetSelect = row.querySelector('.rule-secondary-sheet');
            else if (type === 'extract') sheetSelect = row.querySelector('.rule-extract-sheet');

            // Handle primary data files (special IDs like primary_0, primary_1)
            if (fileId.startsWith('primary_')) {
                if (sheetSelect) {
                    sheetSelect.innerHTML = '<option value="">Sheet</option>';
                    sheetSelect.innerHTML += `<option value="Working" selected>Working</option>`;
                    // Trigger onchange to auto-load columns for primary file
                    sheetSelect.dispatchEvent(new Event('change'));
                }
                return;
            }

            // Handle master files
            if (fileId.startsWith('master_')) {
                if (sheetSelect) {
                    sheetSelect.innerHTML = '<option value="">Sheet</option>';
                    sheetSelect.innerHTML += `<option value="Working" selected>Working</option>`;
                    // Trigger onchange to auto-load columns for master file
                    sheetSelect.dispatchEvent(new Event('change'));
                }
                return;
            }

            const data = await apiCall(`/api/files/${fileId}/sheets`);
            
            if (sheetSelect && data.success) {
                sheetSelect.innerHTML = '<option value="">Sheet</option>';
                data.sheets.forEach(sheet => {
                    sheetSelect.innerHTML += `<option value="${sheet}">${sheet}</option>`;
                });
            }
        }

        async function loadRuleColumns(selectElement, rowId, type) {
            const row = document.getElementById(`rule-row-${rowId}`);
            let fileSelect, sheetName;
            
            if (type === 'primary') {
                fileSelect = row.querySelector('.rule-primary-file');
                sheetName = row.querySelector('.rule-primary-sheet').value;
            } else if (type === 'secondary') {
                fileSelect = row.querySelector('.rule-secondary-file');
                sheetName = row.querySelector('.rule-secondary-sheet').value;
            } else if (type === 'extract') {
                fileSelect = row.querySelector('.rule-extract-file');
                sheetName = row.querySelector('.rule-extract-sheet').value;
            }
            
            const fileId = fileSelect.value;
            if (!fileId || !sheetName) return;

            let colSelect;
            if (type === 'primary') colSelect = row.querySelector('.rule-primary-column');
            else if (type === 'secondary') colSelect = row.querySelector('.rule-secondary-column');
            else if (type === 'extract') colSelect = row.querySelector('.rule-extract-column');

            // Handle primary data files
            if (fileId.startsWith('primary_')) {
                if (colSelect) {
                    const label = window.primaryValueColumnName || 'Order ID';
                    colSelect.innerHTML = '<option value="">Column</option>';
                    colSelect.innerHTML += `<option value="Unique_ID">Unique_ID</option>`;
                    colSelect.innerHTML += `<option value="Source_File_Name">Source_File_Name</option>`;
                    colSelect.innerHTML += `<option value="Order ID">${label}</option>`;
                    colSelect.innerHTML += `<option value="Sales Amount">Sales Amount</option>`;
                }
                return;
            }

            // Handle master files
            if (fileId.startsWith('master_')) {
                const folderId = fileId.replace('master_', '');
                const data = await apiCall(`/api/master/${folderId}/columns`);
                if (colSelect && data.success) {
                    colSelect.innerHTML = '<option value="">Column</option>';
                    data.columns.forEach(col => {
                        colSelect.innerHTML += `<option value="${col}">${col}</option>`;
                    });
                }
                return;
            }

            const data = await apiCall(`/api/files/${fileId}/columns?sheet_name=${encodeURIComponent(sheetName)}`);
            
            if (colSelect && data.success) {
                colSelect.innerHTML = '<option value="">Column</option>';
                data.columns.forEach(col => {
                    colSelect.innerHTML += `<option value="${col}">${col}</option>`;
                });
            }
        }

        function deleteRuleRow(rowId) {
            const row = document.getElementById(`rule-row-${rowId}`);
            if (row) {
                row.remove();
                // Resequence output columns to fill gaps
                resequenceOutputColumns();
            }
        }

        async function savePhase2Rules() {
            clearFieldErrors();
            
            const rows = document.querySelectorAll('#matching-rules-body tr');
            const rules = [];
            let hasError = false;
            let firstErrorElement = null;
            
            rows.forEach(row => {
                // Skip condition panel rows — they are not rule rows
                if (row.classList.contains('condition-panel') || row.id.startsWith('condition-panel-')) {
                    return;
                }
                
                // Skip empty state / message rows that have no form fields
                if (!row.querySelector('.rule-column-name, .calc-operation, .rule-primary-file')) {
                    return;
                }
                
                const ruleId = row.id.replace('rule-row-', '');
                const isCalculation = row.dataset.ruleType === 'calculation';
                
                // Get and trim column name
                const colNameInput = row.querySelector('.rule-column-name');
                const columnName = colNameInput ? colNameInput.value.trim() : '';
                const outputColumnInput = row.querySelector('.rule-output-column');
                const outputColumn = outputColumnInput?.value?.trim() || '';
                
                // Validate column name is not empty
                if (!columnName) {
                    showElementError(colNameInput, 'Column Name is required (e.g. Order_ID, Result)');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = colNameInput;
                } else if (/[^a-zA-Z0-9_\s\-]/.test(columnName)) {
                    showElementError(colNameInput, 'Do not use special characters (like quotes) in the column name. Use only letters, numbers, spaces, underscores, or hyphens.');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = colNameInput;
                }
                
                // Validate output column is not empty
                if (!outputColumn) {
                    showElementError(outputColumnInput, 'Output Column is required (e.g. A, B, C)');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = outputColumnInput;
                }
                
                if (isCalculation) {
                    // Multi-column calculation rule
                    const calcColSelects = row.querySelectorAll('.calc-column');
                    const calcCols = [];
                    calcColSelects.forEach(sel => {
                        if (sel.value) calcCols.push(sel.value.trim());
                    });
                    
                    // Validate at least 2 columns for calculation
                    if (calcCols.length < 2) {
                        const calcList = row.querySelector('.calc-columns-list');
                        if (calcList) {
                            // Mark empty selects as errors
                            calcColSelects.forEach(sel => {
                                if (!sel.value) showElementError(sel, 'Select a column');
                            });
                            // Show error on the add button container if not enough columns
                            const addBtn = row.querySelector('button[onclick*="addCalcColumn"]');
                            if (addBtn) {
                                const msg = calcCols.length === 0 
                                    ? 'Please add at least 2 columns to calculate' 
                                    : `Please add ${2 - calcCols.length} more column(s)`;
                                showElementError(addBtn, msg);
                            }
                        }
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = calcColSelects[0];
                    }
                    
                    if (!hasError || (columnName && outputColumn && calcCols.length >= 2)) {
                        rules.push({
                            id: ruleId,
                            rule_type: 'calculation',
                            columns: calcCols,
                            operation: row.querySelector('.calc-operation').value,
                            output_column: outputColumn,
                            column_name: columnName
                        });
                    }
                } else {
                    // Match rule - validate required fields
                    const primaryFile = row.querySelector('.rule-primary-file');
                    const primarySheet = row.querySelector('.rule-primary-sheet');
                    const primaryColumn = row.querySelector('.rule-primary-column');
                    
                    const secondaryFile = row.querySelector('.rule-secondary-file');
                    const secondarySheet = row.querySelector('.rule-secondary-sheet');
                    const secondaryColumn = row.querySelector('.rule-secondary-column');
                    
                    const extractFile = row.querySelector('.rule-extract-file');
                    const extractSheet = row.querySelector('.rule-extract-sheet');
                    const extractColumn = row.querySelector('.rule-extract-column');
                    
                    if (!primaryFile?.value) {
                        showElementError(primaryFile, 'Primary File is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = primaryFile;
                    }
                    if (primaryFile?.value && !primarySheet?.value) {
                        showElementError(primarySheet, 'Primary Sheet is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = primarySheet;
                    }
                    if (primaryFile?.value && primarySheet?.value && !primaryColumn?.value) {
                        showElementError(primaryColumn, 'Primary Column is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = primaryColumn;
                    }
                    
                    if (!secondaryFile?.value) {
                        showElementError(secondaryFile, 'Secondary File is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = secondaryFile;
                    }
                    if (secondaryFile?.value && !secondarySheet?.value) {
                        showElementError(secondarySheet, 'Secondary Sheet is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = secondarySheet;
                    }
                    if (secondaryFile?.value && secondarySheet?.value && !secondaryColumn?.value) {
                        showElementError(secondaryColumn, 'Match Column is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = secondaryColumn;
                    }
                    
                    if (!extractFile?.value) {
                        showElementError(extractFile, 'Extract File is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = extractFile;
                    }
                    if (extractFile?.value && !extractSheet?.value) {
                        showElementError(extractSheet, 'Extract Sheet is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = extractSheet;
                    }
                    if (extractFile?.value && extractSheet?.value && !extractColumn?.value) {
                        showElementError(extractColumn, 'Extract Column is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = extractColumn;
                    }
                    
                    if (!hasError) {
                        const ruleObj = {
                            id: ruleId,
                            primary_file: primaryFile.value,
                            primary_sheet: primarySheet.value || '',
                            primary_column: primaryColumn.value,
                            rule_type: row.querySelector('.rule-type')?.value || 'match',
                            secondary_file: secondaryFile.value,
                            secondary_sheet: secondarySheet.value || '',
                            secondary_column: secondaryColumn.value,
                            extract_file: extractFile.value,
                            extract_sheet: extractSheet.value || '',
                            extract_column: extractColumn.value,
                            output_column: outputColumn,
                            column_name: columnName,
                            default_value: row.querySelector('.rule-default-value')?.value || ''
                        };
                        // Capture column condition if panel exists
                        const colCond = getColumnConditionConfig(ruleId);
                        if (colCond) {
                            ruleObj.column_condition = colCond;
                        }
                        rules.push(ruleObj);
                    }
                }
            });

            if (hasError) {
                showToast('Please fix the highlighted fields before saving', 'error');
                scrollToFirstError();
                return;
            }
            
            if (rules.length === 0) {
                showToast('Please add at least one rule row', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('phase', 2);
            formData.append('config', JSON.stringify(rules));
            formData.append('name', 'Matching Rules');

            const data = await apiCall('/api/rules', {
                method: 'POST',
                body: formData
            });

            if (data.success) {
                isRulesPageLoaded = false; // Force reload on next visit since rules changed
                showToast('Rules saved successfully', 'success');
                
                // Immediately update Phase 4 available columns
                await loadAvailableColumnsForSummary();
            }
        }

        // ==================== PHASE 3: REMARKS & ACTIONS ====================
        
        let conditionCounter = 1; // Global counter for condition rows across all groups

        // Get all available columns from Phase 2 rules AND Phase 3 remark groups
        function getPhase2Columns() {
            const columns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
            
            // Phase 2: Matching rules columns
            const rows = document.querySelectorAll('#matching-rules-body tr');
            rows.forEach(row => {
                const colNameInput = row.querySelector('.rule-column-name');
                if (colNameInput && colNameInput.value.trim()) {
                    columns.push(colNameInput.value.trim());
                }
            });
            
            // Phase 3: Remark group columns (so they show up for other remarks)
            const remarkGroups = document.querySelectorAll('#remarks-groups-container > div');
            remarkGroups.forEach(group => {
                const colNameInput = group.querySelector('.group-column-name');
                if (colNameInput && colNameInput.value.trim()) {
                    columns.push(colNameInput.value.trim());
                }
            });
            
            return [...new Set(columns)];
        }

        function addRemarksGroup() {
            const container = document.getElementById('remarks-groups-container');
            const groupId = remarksGroupCounter++;
            
            // Get auto-assigned column
            const autoColumn = getAutoAssignedColumn();
            const usedColumns = getAllUsedOutputColumns();
            
            const groupDiv = document.createElement('div');
            groupDiv.className = 'bg-white rounded-xl shadow-sm border border-gray-200 p-6';
            groupDiv.id = `remarks-group-${groupId}`;
            
            groupDiv.innerHTML = `
                <div class="flex items-center justify-between mb-4 pb-4 border-b border-gray-100">
                    <div class="flex items-center space-x-3">
                        <span class="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center text-sm font-bold text-indigo-600">#${groupId}</span>
                        <h4 class="text-lg font-semibold text-gray-900">Remarks Group</h4>
                    </div>
                    <button onclick="deleteRemarksGroup(${groupId})" class="text-red-500 hover:text-red-700 p-2 rounded-lg hover:bg-red-50 transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
                
                <!-- Group Header Fields -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Column Name</label>
                        <input type="text" class="group-column-name w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500" 
                            placeholder="e.g. Status_Remark" maxlength="50">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Output Column</label>
                        <select class="group-output-col w-full border border-gray-300 rounded-lg px-3 py-2 text-sm uppercase focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                            onchange="refreshAllColumnDropdowns()">
                            ${generateColumnLetterOptions(autoColumn, usedColumns)}
                        </select>
                    </div>
                </div>
                
                <!-- Remark Rules Container -->
                <div class="remark-rules-container space-y-4">
                    <!-- Remark rules will be added here -->
                </div>
                
                <!-- Add Remark Rule Button -->
                <div class="mt-4">
                    <button onclick="addRemarkRule(${groupId})" class="flex items-center space-x-2 bg-indigo-50 text-indigo-700 font-medium py-2 px-4 rounded-lg hover:bg-indigo-100 transition-colors border border-indigo-200">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                        </svg>
                        <span>Add Remark Rule</span>
                    </button>
                </div>
                
                <!-- Default Remark -->
                <div class="mt-4 pt-4 border-t border-gray-100">
                    <label class="block text-sm font-medium text-gray-700 mb-2">Default Remark (if no conditions match)</label>
                    <input type="text" class="group-default-remark w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500" 
                        placeholder="Leave blank for no default remark">
                </div>
            `;
            
            container.appendChild(groupDiv);
            showToast('Remarks group added. Add remark rules with conditions.', 'success');
        }

        function deleteRemarksGroup(groupId) {
            const group = document.getElementById(`remarks-group-${groupId}`);
            if (group) {
                group.remove();
                // Resequence output columns to fill gaps
                resequenceOutputColumns();
                showToast('Remarks group deleted', 'info');
            }
        }

        function addRemarkRule(groupId) {
            const container = document.querySelector(`#remarks-group-${groupId} .remark-rules-container`);
            const ruleId = Date.now() + Math.floor(Math.random() * 1000); // Unique integer ID for this rule
            const phase2Cols = getPhase2Columns();
            
            const ruleDiv = document.createElement('div');
            ruleDiv.className = 'bg-gray-50 rounded-lg p-4 border border-gray-200';
            ruleDiv.id = `remark-rule-${ruleId}`;
            
            ruleDiv.innerHTML = `
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center space-x-2">
                        <span class="text-sm font-medium text-gray-700">Remark Text:</span>
                        <input type="text" class="remark-text w-64 border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500" 
                            placeholder="e.g. Order Validated" maxlength="100">
                    </div>
                    <button onclick="deleteRemarkRule(${ruleId})" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
                
                <!-- Conditions Container -->
                <div class="conditions-container space-y-2">
                    <!-- Conditions will be added here -->
                </div>
                
                <!-- Add Condition Button -->
                <button onclick="addConditionRow(${ruleId})" class="mt-2 flex items-center space-x-1 text-sm text-indigo-600 hover:text-indigo-800 font-medium">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                    </svg>
                    <span>Add Condition</span>
                </button>
            `;
            
            container.appendChild(ruleDiv);
            
            // Add first condition automatically
            addConditionRow(ruleId);
        }

        function deleteRemarkRule(ruleId) {
            const rule = document.getElementById(`remark-rule-${ruleId}`);
            if (rule) {
                rule.remove();
            }
        }

        function addConditionRow(ruleId) {
            const container = document.querySelector(`#remark-rule-${ruleId} .conditions-container`);
            const condId = conditionCounter++;
            const phase2Cols = getPhase2Columns();
            
            const condDiv = document.createElement('div');
            condDiv.className = 'condition-row flex items-center space-x-2 bg-white rounded p-2 border border-gray-100';
            condDiv.id = `condition-${condId}`;
            
            condDiv.innerHTML = `
                <span class="text-xs font-medium text-gray-500 w-6">IF</span>
                <select class="cond-column w-32 text-xs border border-gray-300 rounded px-2 py-1.5">
                    <option value="">Column</option>
                    ${phase2Cols.map(col => {
                        const label = col === 'Order ID' ? (window.primaryValueColumnName || 'Order ID') : col;
                        return `<option value="${col}">${label}</option>`;
                    }).join('')}
                </select>
                <select class="cond-operator w-40 text-xs border border-gray-300 rounded px-2 py-1.5" onchange="onConditionChange(${condId})">
                    <option value="equal_to">Equal to</option>
                    <option value="greater_than">Greater than</option>
                    <option value="smaller_than">Smaller than</option>
                    <option value="between">Between</option>
                    <option value="blank">Blank</option>
                    <option value="not_equal_to">Does not equal to</option>
                    <option value="begin_with">Begin with</option>
                    <option value="end_with">End with</option>
                    <option value="contain">Contain</option>
                    <option value="not_contain">Does not contain</option>
                </select>
                <div class="cond-value-container flex items-center space-x-2 flex-1">
                    <input type="text" class="cond-value w-full text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Value">
                </div>
                <button onclick="deleteConditionRow(${condId})" class="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            `;
            
            container.appendChild(condDiv);
        }

        function onConditionChange(condId) {
            const condDiv = document.getElementById(`condition-${condId}`);
            const operator = condDiv.querySelector('.cond-operator').value;
            const valueContainer = condDiv.querySelector('.cond-value-container');
            
            if (operator === 'blank') {
                valueContainer.innerHTML = '<span class="text-xs text-gray-500 italic">(no value needed)</span>';
            } else if (operator === 'between') {
                valueContainer.innerHTML = `
                    <input type="text" class="cond-value-min w-20 text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Min">
                    <span class="text-xs text-gray-500">and</span>
                    <input type="text" class="cond-value-max w-20 text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Max">
                `;
            } else {
                valueContainer.innerHTML = `<input type="text" class="cond-value w-full text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Value">`;
            }
        }

        function deleteConditionRow(condId) {
            const cond = document.getElementById(`condition-${condId}`);
            if (cond) {
                cond.remove();
            }
        }

        async function savePhase3Rules() {
            clearFieldErrors();
            
            const groups = [];
            const groupDivs = document.querySelectorAll('#remarks-groups-container > div');
            let hasError = false;
            let firstErrorElement = null;
            
            groupDivs.forEach(groupDiv => {
                const groupId = groupDiv.id.replace('remarks-group-', '');
                const colNameInput = groupDiv.querySelector('.group-column-name');
                const outputColInput = groupDiv.querySelector('.group-output-col');
                const columnName = colNameInput.value.trim();
                const outputCol = outputColInput.value.trim();
                const defaultRemark = groupDiv.querySelector('.group-default-remark').value.trim();
                
                if (!columnName) {
                    showElementError(colNameInput, 'Column Name is required');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = colNameInput;
                } else if (/[^a-zA-Z0-9_\s\-]/.test(columnName)) {
                    showElementError(colNameInput, 'Do not use special characters (like quotes) in the column name. Use only letters, numbers, spaces, underscores, or hyphens.');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = colNameInput;
                }
                if (!outputCol) {
                    showElementError(outputColInput, 'Output Column is required');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = outputColInput;
                }
                
                const remarkRules = [];
                const ruleDivs = groupDiv.querySelectorAll('.remark-rules-container > div');
                
                ruleDivs.forEach(ruleDiv => {
                    const remarkInput = ruleDiv.querySelector('.remark-text');
                    const remarkText = remarkInput.value.trim();
                    
                    if (!remarkText) {
                        showElementError(remarkInput, 'Remark text is required');
                        hasError = true;
                        if (!firstErrorElement) firstErrorElement = remarkInput;
                        return;
                    }
                    
                    const conditions = [];
                    const condDivs = ruleDiv.querySelectorAll('.condition-row');
                    
                    condDivs.forEach(condDiv => {
                        const colSelect = condDiv.querySelector('.cond-column');
                        const opSelect = condDiv.querySelector('.cond-operator');
                        const column = colSelect.value;
                        const operator = opSelect.value;
                        
                        if (!column) {
                            showElementError(colSelect, 'Select a column');
                            hasError = true;
                            if (!firstErrorElement) firstErrorElement = colSelect;
                            return;
                        }
                        if (!operator) {
                            showElementError(opSelect, 'Select an operator');
                            hasError = true;
                            if (!firstErrorElement) firstErrorElement = opSelect;
                            return;
                        }
                        
                        let value, valueMin, valueMax;
                        
                        if (operator === 'blank') {
                            value = null;
                        } else if (operator === 'between') {
                            valueMin = condDiv.querySelector('.cond-value-min')?.value || '';
                            valueMax = condDiv.querySelector('.cond-value-max')?.value || '';
                            
                            // Validation: min and max are both required for "between"
                            if (!valueMin.trim()) {
                                const minInput = condDiv.querySelector('.cond-value-min');
                                showElementError(minInput, 'Minimum value is required for "between"');
                                hasError = true;
                                if (!firstErrorElement) firstErrorElement = minInput;
                            }
                            if (!valueMax.trim()) {
                                const maxInput = condDiv.querySelector('.cond-value-max');
                                showElementError(maxInput, 'Maximum value is required for "between"');
                                hasError = true;
                                if (!firstErrorElement) firstErrorElement = maxInput;
                            }
                        } else {
                            value = condDiv.querySelector('.cond-value')?.value || '';
                            
                            // Validation: non-blank operators need a value
                            if (!value.trim()) {
                                const valInput = condDiv.querySelector('.cond-value');
                                showElementError(valInput, 'Value is required for this operator');
                                hasError = true;
                                if (!firstErrorElement) firstErrorElement = valInput;
                            }
                        }
                        
                        conditions.push({
                            column,
                            operator,
                            value,
                            value_min: valueMin,
                            value_max: valueMax
                        });
                    });
                    
                    if (conditions.length > 0) {
                        remarkRules.push({
                            remark: remarkText,
                            conditions
                        });
                    }
                });
                
                if (remarkRules.length > 0) {
                    groups.push({
                        group_id: groupId,
                        column_name: columnName,
                        output_column: outputCol,
                        default_remark: defaultRemark,
                        remark_rules: remarkRules
                    });
                }
            });
            
            if (hasError) {
                showToast('Please fix the highlighted fields before saving', 'error');
                scrollToFirstError();
                return;
            }
            
            if (groups.length === 0) {
                showToast('No valid remark groups to save', 'warning');
                return;
            }
            
            const formData = new FormData();
            formData.append('phase', 3);
            formData.append('config', JSON.stringify(groups));
            formData.append('name', 'Remarks & Actions');
            
            const data = await apiCall('/api/rules', {
                method: 'POST',
                body: formData
            });
            
            if (data.success) {
                isRulesPageLoaded = false; // Force reload on next visit since rules changed
                showToast('Remarks configuration saved successfully', 'success');
                
                // Immediately update Phase 4 available columns
                await loadAvailableColumnsForSummary();
            }
        }

        async function loadSavedPhase3() {
            const data = await apiCall('/api/rules/3');
            if (!data.success || !data.rules || data.rules.length === 0) return;
            
            const latestRule = data.rules[data.rules.length - 1];
            let groups;
            try {
                groups = JSON.parse(latestRule.config);
            } catch(e) {
                console.error('Error parsing phase 3 config:', e);
                return;
            }
            
            if (!Array.isArray(groups) || groups.length === 0) return;
            
            const container = document.getElementById('remarks-groups-container');
            container.innerHTML = '';
            
            for (const group of groups) {
                addRemarksGroup();
                const groupDiv = container.lastElementChild;
                
                // Fill header
                groupDiv.querySelector('.group-column-name').value = group.column_name || '';
                groupDiv.querySelector('.group-output-col').value = group.output_column || '';
                groupDiv.querySelector('.group-default-remark').value = group.default_remark || '';
                
                // Refresh dropdowns after setting values
                refreshAllColumnDropdowns();
                
                // Fill remark rules
                const rulesContainer = groupDiv.querySelector('.remark-rules-container');
                rulesContainer.innerHTML = '';
                
                for (const rule of group.remark_rules || []) {
                    const ruleId = Date.now() + Math.floor(Math.random() * 1000);
                    const phase2Cols = getPhase2Columns();
                    
                    const ruleDiv = document.createElement('div');
                    ruleDiv.className = 'bg-gray-50 rounded-lg p-4 border border-gray-200';
                    ruleDiv.id = `remark-rule-${ruleId}`;
                    
                    let conditionsHtml = '';
                    for (const cond of rule.conditions || []) {
                        const condId = conditionCounter++;
                        let valueHtml;
                        
                        if (cond.operator === 'blank') {
                            valueHtml = '<span class="text-xs text-gray-500 italic">(no value needed)</span>';
                        } else if (cond.operator === 'between') {
                            valueHtml = `
                                <input type="text" class="cond-value-min w-20 text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Min" value="${cond.value_min || ''}">
                                <span class="text-xs text-gray-500">and</span>
                                <input type="text" class="cond-value-max w-20 text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Max" value="${cond.value_max || ''}">
                            `;
                        } else {
                            valueHtml = `<input type="text" class="cond-value w-full text-xs border border-gray-300 rounded px-2 py-1.5" placeholder="Value" value="${cond.value || ''}">`;
                        }
                        
                        conditionsHtml += `
                            <div class="condition-row flex items-center space-x-2 bg-white rounded p-2 border border-gray-100" id="condition-${condId}">
                                <span class="text-xs font-medium text-gray-500 w-6">IF</span>
                                <select class="cond-column w-32 text-xs border border-gray-300 rounded px-2 py-1.5">
                                    <option value="">Column</option>
                                    ${phase2Cols.map(col => {
                                        const label = col === 'Order ID' ? (window.primaryValueColumnName || 'Order ID') : col;
                                        return `<option value="${col}" ${col === cond.column ? 'selected' : ''}>${label}</option>`;
                                    }).join('')}
                                </select>
                                <select class="cond-operator w-40 text-xs border border-gray-300 rounded px-2 py-1.5" onchange="onConditionChange(${condId})">
                                    <option value="equal_to" ${cond.operator === 'equal_to' ? 'selected' : ''}>Equal to</option>
                                    <option value="greater_than" ${cond.operator === 'greater_than' ? 'selected' : ''}>Greater than</option>
                                    <option value="smaller_than" ${cond.operator === 'smaller_than' ? 'selected' : ''}>Smaller than</option>
                                    <option value="between" ${cond.operator === 'between' ? 'selected' : ''}>Between</option>
                                    <option value="blank" ${cond.operator === 'blank' ? 'selected' : ''}>Blank</option>
                                    <option value="not_equal_to" ${cond.operator === 'not_equal_to' ? 'selected' : ''}>Does not equal to</option>
                                    <option value="begin_with" ${cond.operator === 'begin_with' ? 'selected' : ''}>Begin with</option>
                                    <option value="end_with" ${cond.operator === 'end_with' ? 'selected' : ''}>End with</option>
                                    <option value="contain" ${cond.operator === 'contain' ? 'selected' : ''}>Contain</option>
                                    <option value="not_contain" ${cond.operator === 'not_contain' ? 'selected' : ''}>Does not contain</option>
                                </select>
                                <div class="cond-value-container flex items-center space-x-2 flex-1">
                                    ${valueHtml}
                                </div>
                                <button onclick="deleteConditionRow(${condId})" class="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50 transition-colors">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                </button>
                            </div>
                        `;
                    }
                    
                    ruleDiv.innerHTML = `
                        <div class="flex items-center justify-between mb-3">
                            <div class="flex items-center space-x-2">
                                <span class="text-sm font-medium text-gray-700">Remark Text:</span>
                                <input type="text" class="remark-text w-64 border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500" 
                                    placeholder="e.g. Order Validated" maxlength="100" value="${rule.remark || ''}">
                            </div>
                            <button onclick="deleteRemarkRule(${ruleId})" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                            </button>
                        </div>
                        <div class="conditions-container space-y-2">
                            ${conditionsHtml}
                        </div>
                        <button onclick="addConditionRow(${ruleId})" class="mt-2 flex items-center space-x-1 text-sm text-indigo-600 hover:text-indigo-800 font-medium">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                            </svg>
                            <span>Add Condition</span>
                        </button>
                    `;
                    
                    rulesContainer.appendChild(ruleDiv);
                }
            }
        }

        // ==================== PHASE 4: SUMMARY & PIVOT ====================
        let summaryCounter = 1;
        let availableColumnsForSummary = [];

        async function loadAvailableColumnsForSummary() {
            // Get columns from Phase 1 primary data
            const primaryData = await apiCall('/api/primary/files');
            const rulesData = await apiCall('/api/rules/1');
            
            let columns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
            
            // Get columns from Phase 2 rules
            const phase2Data = await apiCall('/api/rules/2');
            if (phase2Data.success && phase2Data.rules && phase2Data.rules.length > 0) {
                try {
                    const rules = JSON.parse(phase2Data.rules[phase2Data.rules.length - 1].config);
                    rules.forEach(rule => {
                        if (rule.column_name) columns.push(rule.column_name);
                    });
                } catch(e) {}
            }
            
            // Get columns from Phase 3 rules
            const phase3Data = await apiCall('/api/rules/3');
            if (phase3Data.success && phase3Data.rules && phase3Data.rules.length > 0) {
                try {
                    const groups = JSON.parse(phase3Data.rules[phase3Data.rules.length - 1].config);
                    groups.forEach(group => {
                        if (group.column_name) columns.push(group.column_name);
                    });
                } catch(e) {}
            }
            
            availableColumnsForSummary = [...new Set(columns)];
            
            // Update available columns display
            const container = document.getElementById('available-columns');
            if (availableColumnsForSummary.length > 0) {
                container.innerHTML = availableColumnsForSummary.map(col => {
                    const label = col === 'Order ID' ? (window.primaryValueColumnName || 'Order ID') : col;
                    // Properly escape quotes to prevent HTML attribute injection issues
                    const escapedCol = col.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    return `<span class="inline-block px-2 py-1 bg-white border border-blue-300 rounded text-xs text-blue-700 font-medium cursor-move" draggable="true" ondragstart="dragColumn(event, '${escapedCol}')">${label}</span>`;
                }).join('');
            }
            
            return availableColumnsForSummary;
        }

        let draggedTag = null;

        function dragColumn(event, colName) {
            draggedTag = event.target.closest('[data-column]');
            event.dataTransfer.setData('text/plain', colName);
            if (draggedTag && draggedTag.closest('.drop-zone')) {
                event.dataTransfer.effectAllowed = 'move';
                setTimeout(() => draggedTag.classList.add('opacity-50'), 0);
            } else {
                event.dataTransfer.effectAllowed = 'copy';
            }
        }
        
        function dragTagEnd(event) {
            if (draggedTag) {
                draggedTag.classList.remove('opacity-50');
                draggedTag = null;
            }
        }

        function allowDrop(event) {
            event.preventDefault();
            event.target.closest('.drop-zone')?.classList.add('bg-blue-50', 'border-blue-400');
        }

        function leaveDrop(event) {
            event.target.closest('.drop-zone')?.classList.remove('bg-blue-50', 'border-blue-400');
        }

        function dropColumn(event, zoneType, summaryId) {
            event.preventDefault();
            const colName = event.dataTransfer.getData('text/plain');
            if (!colName) return;
            
            const zone = document.getElementById(`summary-${summaryId}-${zoneType}`);
            if (!zone) return;
            
            zone.classList.remove('bg-blue-50', 'border-blue-400');
            
            const targetTag = event.target.closest('[data-column]');
            
            if (draggedTag && draggedTag.closest('.drop-zone') !== null) {
                if (draggedTag.parentElement === zone) {
                    if (targetTag && targetTag !== draggedTag) {
                        const rect = targetTag.getBoundingClientRect();
                        const isAfter = event.clientY > rect.top + rect.height / 2 || event.clientX > rect.left + rect.width / 2;
                        if (isAfter) {
                            targetTag.after(draggedTag);
                        } else {
                            targetTag.before(draggedTag);
                        }
                    } else if (!targetTag) {
                        zone.appendChild(draggedTag);
                    }
                    updateSummaryConfig(summaryId);
                    return;
                } else {
                    draggedTag.remove();
                }
            }
            
            if (zoneType === 'value-fields') {
                addValueField(summaryId, colName);
            } else if (zoneType === 'filter-fields') {
                addFilterField(summaryId, colName);
            } else {
                addFieldTag(zone, colName, zoneType, summaryId);
            }
        }

        function addFieldTag(container, colName, zoneType, summaryId) {
            const tag = document.createElement('div');
            tag.className = 'inline-flex items-center space-x-1 px-2 py-1 bg-teal-100 border border-teal-300 rounded text-xs text-teal-800 font-medium cursor-move';
            tag.draggable = true;
            tag.setAttribute('ondragstart', `dragColumn(event, '${colName.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')`);
            tag.setAttribute('ondragend', 'dragTagEnd(event)');
            tag.dataset.column = colName;
            const label = colName === 'Order ID' ? (window.primaryValueColumnName || 'Order ID') : colName;
            tag.innerHTML = `
                <span>${label}</span>
                <button onclick="this.parentElement.remove(); updateSummaryConfig(${summaryId})" class="text-teal-600 hover:text-teal-800 ml-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            `;
            tag.dataset.column = colName;
            container.appendChild(tag);
            updateSummaryConfig(summaryId);
        }

        function addValueField(summaryId, colName) {
            const container = document.getElementById(`summary-${summaryId}-value-fields`);
            const div = document.createElement('div');
            div.className = 'flex items-center space-x-2 p-2 bg-white border border-gray-200 rounded cursor-move';
            div.draggable = true;
            div.setAttribute('ondragstart', `dragColumn(event, '${colName.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')`);
            div.setAttribute('ondragend', 'dragTagEnd(event)');
            const label = colName === 'Order ID' ? (window.primaryValueColumnName || 'Order ID') : colName;
            div.innerHTML = `
                <span class="text-sm font-medium text-gray-700 flex-1">${label}</span>
                <select class="agg-function text-xs border border-gray-300 rounded px-2 py-1" onchange="updateSummaryConfig(${summaryId})">
                    <option value="sum">Sum</option>
                    <option value="count">Count</option>
                    <option value="average">Average</option>
                    <option value="min">Min</option>
                    <option value="max">Max</option>
                </select>
                <button onclick="this.parentElement.remove(); updateSummaryConfig(${summaryId})" class="text-red-500 hover:text-red-700 p-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            `;
            div.dataset.column = colName;
            container.appendChild(div);
            updateSummaryConfig(summaryId);
        }

        function addFilterField(summaryId, colName) {
            const container = document.getElementById(`summary-${summaryId}-filter-fields`);
            const div = document.createElement('div');
            div.className = 'flex items-center space-x-2 p-2 bg-white border border-gray-200 rounded cursor-move';
            div.draggable = true;
            div.setAttribute('ondragstart', `dragColumn(event, '${colName.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')`);
            div.setAttribute('ondragend', 'dragTagEnd(event)');
            const label = colName === 'Order ID' ? (window.primaryValueColumnName || 'Order ID') : colName;
            div.innerHTML = `
                <span class="text-sm font-medium text-gray-700">${label}</span>
                <select class="filter-op text-xs border border-gray-300 rounded px-2 py-1" onchange="updateSummaryConfig(${summaryId})">
                    <option value="equal_to">=</option>
                    <option value="not_equal_to">≠</option>
                    <option value="greater_than">></option>
                    <option value="smaller_than"><</option>
                    <option value="contain">Contains</option>
                </select>
                <input type="text" class="filter-value text-xs border border-gray-300 rounded px-2 py-1 w-24" placeholder="Value" onchange="updateSummaryConfig(${summaryId})">
                <button onclick="this.parentElement.remove(); updateSummaryConfig(${summaryId})" class="text-red-500 hover:text-red-700 p-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            `;
            div.dataset.column = colName;
            container.appendChild(div);
            updateSummaryConfig(summaryId);
        }

        async function addSummaryConfig(savedData = null) {
            const container = document.getElementById('summary-configs-container');
            const summaryId = savedData?.id || summaryCounter++;
            
            // Load available columns if not loaded
            if (availableColumnsForSummary.length === 0) {
                await loadAvailableColumnsForSummary();
            }
            
            const div = document.createElement('div');
            div.className = 'bg-white rounded-xl shadow-sm border border-gray-200 p-6';
            div.id = `summary-card-${summaryId}`;
            
            div.innerHTML = `
                <div class="flex items-center justify-between mb-4 pb-4 border-b border-gray-100">
                    <div class="flex items-center space-x-3">
                        <span class="w-8 h-8 bg-teal-100 rounded-lg flex items-center justify-center text-sm font-bold text-teal-600">#${summaryId}</span>
                        <input type="text" class="summary-name text-lg font-semibold text-gray-900 border border-gray-300 rounded px-3 py-1" 
                            placeholder="Summary Name" value="${savedData?.name || ''}" onchange="updateSummaryConfig(${summaryId})">
                    </div>
                    <div class="flex items-center space-x-2">
                        <button onclick="previewSummary(${summaryId})" class="flex items-center space-x-1 bg-blue-50 text-blue-700 text-sm font-medium py-1.5 px-3 rounded-lg hover:bg-blue-100 transition-colors border border-blue-200">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                            <span>Preview</span>
                        </button>
                        <button onclick="deleteSummaryConfig(${summaryId})" class="text-red-500 hover:text-red-700 p-2 rounded-lg hover:bg-red-50 transition-colors">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        </button>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div>
                        <label class="text-xs font-medium text-gray-600 mb-1 block">Row Fields</label>
                        <div id="summary-${summaryId}-row-fields" class="drop-zone min-h-[60px] p-2 rounded-lg bg-gray-50 flex flex-wrap gap-2" 
                             ondragover="allowDrop(event)" ondragleave="leaveDrop(event)" ondrop="dropColumn(event, 'row-fields', ${summaryId})">
                            <span class="text-xs text-gray-400 italic">Drag columns here</span>
                        </div>
                    </div>
                    <div>
                        <label class="text-xs font-medium text-gray-600 mb-1 block">Column Fields</label>
                        <div id="summary-${summaryId}-column-fields" class="drop-zone min-h-[60px] p-2 rounded-lg bg-gray-50 flex flex-wrap gap-2" 
                             ondragover="allowDrop(event)" ondragleave="leaveDrop(event)" ondrop="dropColumn(event, 'column-fields', ${summaryId})">
                            <span class="text-xs text-gray-400 italic">Drag columns here</span>
                        </div>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div>
                        <label class="text-xs font-medium text-gray-600 mb-1 block">Value Fields</label>
                        <div id="summary-${summaryId}-value-fields" class="drop-zone min-h-[60px] p-2 rounded-lg bg-gray-50 space-y-2" 
                             ondragover="allowDrop(event)" ondragleave="leaveDrop(event)" ondrop="dropColumn(event, 'value-fields', ${summaryId})">
                            <span class="text-xs text-gray-400 italic">Drag columns here</span>
                        </div>
                    </div>
                    <div>
                        <label class="text-xs font-medium text-gray-600 mb-1 block">Filter Fields</label>
                        <div id="summary-${summaryId}-filter-fields" class="drop-zone min-h-[60px] p-2 rounded-lg bg-gray-50 space-y-2" 
                             ondragover="allowDrop(event)" ondragleave="leaveDrop(event)" ondrop="dropColumn(event, 'filter-fields', ${summaryId})">
                            <span class="text-xs text-gray-400 italic">Drag columns here</span>
                        </div>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-100">
                    <div class="flex items-center space-x-3">
                        <label class="flex items-center space-x-2">
                            <input type="checkbox" class="summary-include rounded border-gray-300 text-teal-600 focus:ring-teal-500" ${savedData?.include_in_final !== false ? 'checked' : ''} onchange="updateSummaryConfig(${summaryId})">
                            <span class="text-sm text-gray-700">Include in Final Report</span>
                        </label>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="text-sm text-gray-700">Chart:</span>
                        <select class="summary-chart-type text-xs border border-gray-300 rounded px-2 py-1" onchange="updateSummaryConfig(${summaryId})">
                            <option value="none" ${savedData?.chart_type === 'none' ? 'selected' : ''}>None</option>
                            <option value="bar_chart" ${savedData?.chart_type === 'bar_chart' ? 'selected' : ''}>Bar Chart</option>
                            <option value="pie_chart" ${savedData?.chart_type === 'pie_chart' ? 'selected' : ''}>Pie Chart</option>
                            <option value="line_chart" ${savedData?.chart_type === 'line_chart' ? 'selected' : ''}>Line Chart</option>
                        </select>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="text-sm text-gray-700">Output:</span>
                        <select class="summary-output-mode text-xs border border-gray-300 rounded px-2 py-1" onchange="updateSummaryConfig(${summaryId})">
                            <option value="summary_sheet" ${savedData?.output_mode === 'summary_sheet' ? 'selected' : ''}>Summary Sheet</option>
                            <option value="separate_sheet" ${savedData?.output_mode === 'separate_sheet' ? 'selected' : ''}>Separate Sheet</option>
                        </select>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="text-sm text-gray-700">Chart Position:</span>
                        <select class="summary-chart-position text-xs border border-gray-300 rounded px-2 py-1" onchange="updateSummaryConfig(${summaryId})">
                            <option value="right" ${savedData?.chart_position === 'right' ? 'selected' : ''}>Right</option>
                            <option value="below" ${savedData?.chart_position === 'below' ? 'selected' : ''}>Below</option>
                        </select>
                    </div>
                </div>
            `;
            
            container.appendChild(div);
            
            // If saved data, populate fields
            if (savedData) {
                if (savedData.row_fields) {
                    const zone = document.getElementById(`summary-${summaryId}-row-fields`);
                    zone.innerHTML = '';
                    savedData.row_fields.forEach(col => addFieldTag(zone, col, 'row-fields', summaryId));
                }
                if (savedData.column_fields) {
                    const zone = document.getElementById(`summary-${summaryId}-column-fields`);
                    zone.innerHTML = '';
                    savedData.column_fields.forEach(col => addFieldTag(zone, col, 'column-fields', summaryId));
                }
                if (savedData.value_fields) {
                    const zone = document.getElementById(`summary-${summaryId}-value-fields`);
                    zone.innerHTML = '';
                    savedData.value_fields.forEach(vf => {
                        addValueField(summaryId, vf.column);
                        const divs = zone.querySelectorAll('[data-column]');
                        const lastDiv = divs[divs.length - 1];
                        if (lastDiv) {
                            lastDiv.querySelector('.agg-function').value = vf.aggregation || 'sum';
                        }
                    });
                }
                if (savedData.filter_fields) {
                    const zone = document.getElementById(`summary-${summaryId}-filter-fields`);
                    zone.innerHTML = '';
                    savedData.filter_fields.forEach(ff => {
                        addFilterField(summaryId, ff.column);
                        const divs = zone.querySelectorAll('[data-column]');
                        const lastDiv = divs[divs.length - 1];
                        if (lastDiv) {
                            lastDiv.querySelector('.filter-op').value = ff.operator || 'equal_to';
                            lastDiv.querySelector('.filter-value').value = ff.value || '';
                        }
                    });
                }
            }
        }

        async function deleteSummaryConfig(summaryId) {
            const card = document.getElementById(`summary-card-${summaryId}`);
            if (!card) return;
            
            // INSTANT UI removal - no waiting for API
            card.remove();
            showToast('Summary deleted', 'info');
            
            // Delete from backend in background (non-blocking)
            const backendId = card.dataset.backendId;
            if (backendId) {
                apiCall(`/api/summary/${backendId}`, { method: 'DELETE' }).catch(e => {
                    console.warn('Backend delete failed:', e);
                });
            }
        }

        function getSummaryConfig(summaryId) {
            const card = document.getElementById(`summary-card-${summaryId}`);
            if (!card) return null;
            
            const name = card.querySelector('.summary-name')?.value?.trim() || `Summary ${summaryId}`;
            
            const rowFields = Array.from(card.querySelectorAll(`#summary-${summaryId}-row-fields > div`)).map(el => {
                return el.dataset.column;
            }).filter(Boolean);
            
            const colFields = Array.from(card.querySelectorAll(`#summary-${summaryId}-column-fields > div`)).map(el => {
                return el.dataset.column;
            }).filter(Boolean);
            
            const valueFields = Array.from(card.querySelectorAll(`#summary-${summaryId}-value-fields > div`)).map(el => ({
                column: el.dataset.column,
                aggregation: el.querySelector('.agg-function')?.value || 'sum'
            }));
            
            const filterFields = Array.from(card.querySelectorAll(`#summary-${summaryId}-filter-fields > div`)).map(el => ({
                column: el.dataset.column,
                operator: el.querySelector('.filter-op')?.value || 'equal_to',
                value: el.querySelector('.filter-value')?.value || ''
            }));
            
            return {
                id: summaryId,
                name,
                row_fields: rowFields,
                column_fields: colFields,
                value_fields: valueFields,
                filter_fields: filterFields,
                include_in_final: card.querySelector('.summary-include')?.checked ?? true,
                chart_type: card.querySelector('.summary-chart-type')?.value || 'none',
                output_mode: card.querySelector('.summary-output-mode')?.value || 'summary_sheet',
                chart_position: card.querySelector('.summary-chart-position')?.value || 'right'
            };
        }

        function updateSummaryConfig(summaryId) {
            // Config is updated automatically in the DOM, no need to save yet
        }

        async function previewSummary(summaryId) {
            const config = getSummaryConfig(summaryId);
            if (!config) {
                showToast('Summary not found', 'error');
                return;
            }
            
            if (config.row_fields.length === 0 && config.column_fields.length === 0) {
                showToast('Please add at least Row or Column fields', 'warning');
                return;
            }
            
            if (config.value_fields.length === 0) {
                showToast('Please add at least one Value field', 'warning');
                return;
            }
            
            showToast('Generating preview...', 'info');
            
            const formData = new FormData();
            formData.append('config', JSON.stringify(config));
            
            const data = await apiCall('/api/summary/preview', {
                method: 'POST',
                body: formData
            });
            
            if (data.success) {
                showSummaryPreviewModal(data, config);
            } else {
                showToast(data.message || 'Preview generation failed', 'error');
            }
        }

        function showSummaryPreviewModal(data, config) {
            // Create modal if not exists
            let modal = document.getElementById('summary-preview-modal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'summary-preview-modal';
                modal.className = 'modal-overlay fixed inset-0 z-50 hidden flex items-center justify-center';
                document.body.appendChild(modal);
            }
            
            const columns = data.columns || [];
            const previewData = data.preview_data || [];
            
            let tableHtml = '';
            if (previewData.length > 0) {
                tableHtml = `
                    <table class="min-w-full text-sm border border-gray-200 rounded-lg">
                        <thead class="bg-gray-50">
                            <tr>
                                ${columns.map(col => `<th class="text-left font-medium text-gray-600 px-3 py-2 border-b">${col}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${previewData.map((row, index) => {
                                // Detect Grand Total row (last row or contains 'Grand Total' in first column)
                                const firstCol = columns[0];
                                const isGrandTotal = row[firstCol] === 'Grand Total' || (index === previewData.length - 1 && row[firstCol] && String(row[firstCol]).includes('Total'));
                                const rowClass = isGrandTotal ? 'bg-blue-50 border-t-2 border-blue-300' : 'border-b border-gray-100';
                                const cellClass = isGrandTotal ? 'px-3 py-2 text-blue-800 font-bold' : 'px-3 py-2 text-gray-700';
                                return `
                                    <tr class="${rowClass}">
                                        ${columns.map(col => `<td class="${cellClass}">${row[col] !== undefined ? row[col] : ''}</td>`).join('')}
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                `;
            } else {
                tableHtml = '<p class="text-gray-500 text-center py-8">No data to preview</p>';
            }
            
            let chartHtml = '';
            if (data.chart_image) {
                chartHtml = `
                    <div class="mt-4 bg-white rounded-lg border border-gray-200 p-4">
                        <div class="flex items-center justify-between mb-2">
                            <h4 class="text-sm font-semibold text-gray-700">Visualization</h4>
                            <span class="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">${config.chart_type ? config.chart_type.replace('_', ' ').toUpperCase() : 'CHART'}</span>
                        </div>
                        <div class="overflow-hidden rounded-lg bg-gray-50">
                            <img src="${data.chart_image}" class="max-w-full mx-auto" style="max-height: 400px;" alt="Chart">
                        </div>
                    </div>
                `;
            }
            
            modal.innerHTML = `
                <div class="bg-white rounded-xl shadow-xl w-full max-w-4xl mx-4 p-6 max-h-[90vh] overflow-y-auto">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">Preview: ${config.name}</h3>
                        <button onclick="document.getElementById('summary-preview-modal').classList.add('hidden')" class="text-gray-400 hover:text-gray-600">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>
                    
                    <div class="overflow-x-auto mb-4">
                        ${tableHtml}
                    </div>
                    
                    ${chartHtml}
                    
                    <div class="mt-4 flex justify-end space-x-3">
                        <button onclick="document.getElementById('summary-preview-modal').classList.add('hidden')" class="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">Close</button>
                        <button onclick="downloadSummaryPreview()" class="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Download Preview</button>
                    </div>
                </div>
            `;
            
            modal.classList.remove('hidden');
        }

        function downloadSummaryPreview() {
            showToast('Download feature coming soon', 'info');
        }

        async function savePhase4Rules() {
            clearFieldErrors();
            
            const cards = document.querySelectorAll('#summary-configs-container > div[id^="summary-card-"]');
            const summaries = [];
            let hasError = false;
            let firstErrorElement = null;
            
            if (cards.length === 0) {
                showToast('Please add at least one summary configuration to save', 'warning');
                return;
            }
            
            cards.forEach(card => {
                const summaryId = parseInt(card.id.replace('summary-card-', ''));
                const nameInput = card.querySelector('.summary-name');
                const config = getSummaryConfig(summaryId);
                
                if (!nameInput.value.trim()) {
                    showElementError(nameInput, 'Summary name is required');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = nameInput;
                }
                
                const rowFields = card.querySelector(`#summary-${summaryId}-row-fields`);
                const colFields = card.querySelector(`#summary-${summaryId}-column-fields`);
                const valFields = card.querySelector(`#summary-${summaryId}-value-fields`);
                
                // Check if at least one field is configured
                const hasRowFields = rowFields && rowFields.querySelectorAll('div').length > 0;
                const hasColFields = colFields && colFields.querySelectorAll('div').length > 0;
                const hasValFields = valFields && valFields.querySelectorAll('div').length > 0;
                
                if (!hasRowFields && !hasColFields) {
                    showElementError(rowFields, 'Add at least Row or Column fields');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = rowFields;
                }
                
                if (!hasValFields) {
                    showElementError(valFields, 'Add at least one Value field');
                    hasError = true;
                    if (!firstErrorElement) firstErrorElement = valFields;
                }
                
                if (config && nameInput.value.trim() && (hasRowFields || hasColFields) && hasValFields) {
                    summaries.push(config);
                }
            });
            
            if (hasError) {
                showToast('Please fix the highlighted fields before saving', 'error');
                scrollToFirstError();
                return;
            }
            
            if (summaries.length === 0) {
                showToast('No valid summaries to save', 'warning');
                return;
            }
            
            isRulesPageLoaded = false; // Force reload on next visit since summaries changed
            
            // FIX BUG #1: Clear all existing summaries first to prevent stale/deleted summaries from persisting
            try {
                await apiCall('/api/summary/clear-all', { method: 'POST' });
            } catch (e) {
                console.warn('Failed to clear existing summaries:', e);
                // Continue anyway - saving will still work for matching names
            }
            
            // Save each summary
            for (const summary of summaries) {
                const formData = new FormData();
                formData.append('name', summary.name);
                formData.append('config', JSON.stringify(summary));
                
                await apiCall('/api/summary/save', {
                    method: 'POST',
                    body: formData
                });
            }
            
            showToast(`${summaries.length} summary(s) saved successfully`, 'success');
        }

        async function loadSavedPhase4() {
            try {
                const data = await apiCall('/api/summary/list');
                console.log('Phase 4 loaded:', data);
                
                const container = document.getElementById('summary-configs-container');
                
                if (!data.success || !data.summaries || data.summaries.length === 0) {
                    console.log('No saved Phase 4 summaries found');
                    // Show a helpful message when no summaries exist
                    container.innerHTML = `
                        <div class="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
                            <div class="w-16 h-16 bg-teal-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg class="w-8 h-8 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                </svg>
                            </div>
                            <h3 class="text-lg font-medium text-gray-900 mb-2">No Saved Summaries Yet</h3>
                            <p class="text-sm text-gray-600 max-w-md mx-auto mb-4">
                                Create your first summary/pivot configuration by clicking 
                                <span class="font-medium text-teal-700">"Add Summary"</span> above.
                                Configure row fields, column fields, value fields and filters.
                            </p>
                            <button onclick="addSummaryConfig()" class="bg-teal-600 text-white font-medium py-2 px-6 rounded-lg hover:bg-teal-700 transition-colors">
                                Create Your First Summary
                            </button>
                        </div>
                    `;
                    return;
                }
                
                // Clear existing
                container.innerHTML = '';
                
                // Load available columns first (needed for drag-and-drop tags)
                await loadAvailableColumnsForSummary();
                
                // Use for...of to properly await each async addSummaryConfig call
                // forEach does NOT wait for async callbacks!
                let maxId = 0;
                for (const summary of data.summaries) {
                    console.log('Loading summary:', summary.name, summary.config);
                    await addSummaryConfig(summary.config);
                    if (summary.config && summary.config.id > maxId) {
                        maxId = summary.config.id;
                    }
                }
                
                // Update counter so new summaries get unique IDs
                if (maxId > 0) {
                    summaryCounter = maxId + 1;
                }
                
                showToast(`Loaded ${data.summaries.length} saved summary configuration(s)`, 'success');
            } catch (error) {
                console.error('Error loading Phase 4:', error);
                showToast('Error loading saved summaries: ' + error.message, 'error');
            }
        }

        // ==================== PROCESSED FILES DASHBOARD ====================
        let currentSelectedFY = null;
        let currentSelectedType = null;
        let currentSelectedMonth = null;
        let autoRefreshInterval = null;

        async function loadProcessedTree() {
            const indicator = document.getElementById('sync-indicator');
            indicator.classList.remove('hidden');
            
            try {
                const data = await apiCall('/api/processed/tree');
                if (data.success) {
                    renderProcessedTree(data.tree);
                    updateDashboardStats(data.stats);
                    // Save to cache for instant render on next tab switch
                    saveDashboardCache(data.tree, data.stats);
                }
            } catch (e) {
                showToast('Failed to load processed files', 'error');
            } finally {
                indicator.classList.add('hidden');
            }
        }

        function updateDashboardStats(stats) {
            if (!stats) return;
            
            // Safely update stats - elements may not exist if user is on a different tab
            const setText = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val ?? 0;
            };
            setText('dash-processed-files', stats.processed_files ?? stats.total_files);
            setText('dash-financial-years', stats.financial_years);
            setText('dash-report-types', stats.report_types);
            setText('dash-months-covered', stats.months);
        }

        function renderProcessedTree(tree) {
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
                const data = await apiCall(`/api/processed/files?financial_year=${encodeURIComponent(fy)}&report_type=${encodeURIComponent(type)}&month_name=${encodeURIComponent(month)}`);
                if (data.success) {
                    renderProcessedFiles(data.files);
                }
            } catch (e) {
                showToast('Failed to load files', 'error');
            }
        }

        function renderProcessedFiles(files) {
            const container = document.getElementById('processed-files-container');
            document.getElementById('processed-files-count').textContent = `${files.length} files`;
            
            if (!files || files.length === 0) {
                container.innerHTML = '<p class="text-sm text-gray-500 text-center py-8">No files found</p>';
                return;
            }
            
            container.innerHTML = `
                <div class="overflow-x-auto">
                    <table class="min-w-full text-sm">
                        <thead>
                            <tr class="bg-gray-50 border-b border-gray-200">
                                <th class="text-left font-medium text-gray-600 px-3 py-2">Date & Time</th>
                                <th class="text-left font-medium text-gray-600 px-3 py-2">Source File</th>
                                <th class="text-left font-medium text-gray-600 px-3 py-2">Rows</th>
                                <th class="text-left font-medium text-gray-600 px-3 py-2">Rules</th>
                                <th class="text-left font-medium text-gray-600 px-3 py-2">Size</th>
                                <th class="text-left font-medium text-gray-600 px-3 py-2">Process Time</th>
                                <th class="text-left font-medium text-gray-600 px-3 py-2">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${files.map(file => `
                                <tr class="border-b border-gray-100 hover:bg-gray-50">
                                    <td class="px-3 py-3">
                                        <div class="text-sm font-medium text-gray-900">${file.created_at || 'N/A'}</div>
                                    </td>
                                    <td class="px-3 py-3">
                                        <div class="text-sm font-medium text-gray-900 truncate max-w-[200px]">${file.source_primary_filename || 'Unknown'}</div>
                                        <div class="text-xs text-gray-500 truncate max-w-[200px]">${file.filename}</div>
                                    </td>
                                    <td class="px-3 py-3 text-sm text-gray-700">${file.total_rows?.toLocaleString() || 0}</td>
                                    <td class="px-3 py-3 text-sm text-gray-700">${file.rules_used || 0}</td>
                                    <td class="px-3 py-3 text-sm text-gray-700">${file.file_size ? file.file_size + ' MB' : 'N/A'}</td>
                                    <td class="px-3 py-3 text-sm text-gray-700">${file.processing_time || 'N/A'}</td>
                                    <td class="px-3 py-3">
                                        <div class="flex items-center space-x-1">
                                            <button onclick="previewProcessedFile(${file.id})" class="p-1.5 text-blue-500 hover:text-blue-700 rounded hover:bg-blue-50 transition-colors" title="Preview">
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                                            </button>
                                            <button onclick="downloadProcessedFile(${file.id})" class="p-1.5 text-green-500 hover:text-green-700 rounded hover:bg-green-50 transition-colors" title="Download">
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                                            </button>
                                            <button onclick="deleteProcessedFile(${file.id})" class="p-1.5 text-red-500 hover:text-red-700 rounded hover:bg-red-50 transition-colors" title="Delete">
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        async function previewProcessedFile(fileId) {
            try {
                const data = await apiCall(`/api/processed/${fileId}/preview`);
                if (data.success) {
                    showProcessedPreviewModal(data, fileId);
                }
            } catch (e) {
                showToast('Failed to load preview', 'error');
            }
        }

        function showProcessedPreviewModal(data, fileId) {
            let modal = document.getElementById('processed-preview-modal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'processed-preview-modal';
                modal.className = 'modal-overlay fixed inset-0 z-50 hidden flex items-start justify-center overflow-y-auto p-2 sm:p-4';
                document.body.appendChild(modal);
            }
            
            const sections = data.sections || [];
            let summaryHtml = '';
            
            // Responsive table wrapper with horizontal scroll
            const tableWrapperClass = 'overflow-x-auto w-full rounded-lg border border-gray-200';
            
            sections.forEach(section => {
                // Check if section has data
                if (!section.headers || section.headers.length === 0) {
                    summaryHtml += `
                        <div class="mb-6">
                            <h4 class="text-sm font-semibold text-gray-800 mb-2">${section.name || 'Summary'}</h4>
                            <p class="text-sm text-gray-500 py-4 text-center">No data available</p>
                        </div>
                    `;
                    return;
                }
                
                const headerCount = section.headers.length;
                
                summaryHtml += `
                    <div class="mb-6">
                        <h4 class="text-sm font-semibold text-gray-800 mb-2">${section.name}</h4>
                        <div class="${tableWrapperClass}">
                            <table class="min-w-full text-xs">
                                <thead class="bg-gray-50">
                                    <tr>
                                        ${section.headers.map((h, idx) => `<th class="text-left font-medium text-gray-600 px-2 py-2 border-b whitespace-nowrap ${idx === 0 ? 'sticky left-0 bg-gray-50 z-10' : ''}">${h}</th>`).join('')}
                                    </tr>
                                </thead>
                                <tbody>
                                    ${section.data.map((row, ridx) => {
                                        const isGrandTotal = row && row[0] && String(row[0]).includes('Grand Total');
                                        const rowClass = isGrandTotal ? 'bg-blue-50 border-t-2 border-blue-300 font-semibold' : 'border-b border-gray-100 hover:bg-gray-50';
                                        return `
                                            <tr class="${rowClass}">
                                                ${section.headers.map((h, cidx) => {
                                                    const cell = row[cidx];
                                                    const cellClass = isGrandTotal 
                                                        ? 'px-2 py-2 text-blue-800 font-semibold whitespace-nowrap' 
                                                        : 'px-2 py-2 text-gray-700 whitespace-nowrap';
                                                    const stickyClass = cidx === 0 ? 'sticky left-0 bg-inherit z-10' : '';
                                                    return `<td class="${cellClass} ${stickyClass}">${cell !== undefined && cell !== null ? cell : ''}</td>`;
                                                }).join('')}
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            });
            
            modal.innerHTML = `
                <div class="bg-white rounded-xl shadow-xl w-full max-w-7xl mx-auto my-4 sm:my-8 p-4 sm:p-6">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between mb-4 border-b border-gray-200 pb-4 gap-2">
                        <div class="min-w-0">
                            <h3 class="text-base sm:text-lg font-semibold text-gray-900 truncate">Preview: ${data.file.filename}</h3>
                            <p class="text-xs text-gray-500">Source: ${data.file.source || 'Unknown'} | Rows: ${data.file.total_rows?.toLocaleString() || 0}</p>
                        </div>
                        <div class="flex items-center flex-shrink-0">
                            <button onclick="closeModal('processed-preview-modal')" class="text-gray-400 hover:text-gray-600 p-1">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Tabs -->
                    <div class="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-4 w-fit">
                        <button onclick="switchPreviewTab('summary')" id="preview-tab-summary" class="px-3 py-1.5 text-xs font-medium rounded bg-white shadow-sm text-gray-900 whitespace-nowrap">Summary</button>
                        <button onclick="switchPreviewTab('data')" id="preview-tab-data" class="px-3 py-1.5 text-xs font-medium rounded text-gray-600 hover:text-gray-900 whitespace-nowrap">All Data (100 rows)</button>
                    </div>
                    
                    <!-- Summary Tab -->
                    <div id="preview-content-summary" class="max-h-[60vh] sm:max-h-[500px] overflow-y-auto">
                        ${summaryHtml || '<p class="text-sm text-gray-500 text-center py-8">No summary sections available</p>'}
                    </div>
                    
                    <!-- Data Tab -->
                    <div id="preview-content-data" class="hidden max-h-[60vh] sm:max-h-[500px] overflow-y-auto">
                        <div id="preview-data-container" class="text-sm text-gray-500 py-4 text-center">
                            <div class="spinner-sm mx-auto mb-2"></div>
                            <div>Loading data...</div>
                        </div>
                    </div>
                    
                    <div class="mt-4 flex flex-col sm:flex-row justify-end space-y-2 sm:space-y-0 sm:space-x-3 border-t border-gray-200 pt-4">
                        <button onclick="downloadProcessedFile(${fileId})" class="w-full sm:w-auto px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center space-x-2">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                            <span>Download</span>
                        </button>
                        <button onclick="closeModal('processed-preview-modal')" class="w-full sm:w-auto px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">Close</button>
                    </div>
                </div>
            `;
            
            modal.classList.remove('hidden');
            
            // Load data tab in background
            loadPreviewData(fileId);
        }

        function switchPreviewTab(tab) {
            document.getElementById('preview-content-summary').classList.toggle('hidden', tab !== 'summary');
            document.getElementById('preview-content-data').classList.toggle('hidden', tab !== 'data');
            document.getElementById('preview-tab-summary').classList.toggle('bg-white', tab === 'summary');
            document.getElementById('preview-tab-summary').classList.toggle('shadow-sm', tab === 'summary');
            document.getElementById('preview-tab-summary').classList.toggle('text-gray-900', tab === 'summary');
            document.getElementById('preview-tab-summary').classList.toggle('text-gray-600', tab !== 'summary');
            document.getElementById('preview-tab-data').classList.toggle('bg-white', tab === 'data');
            document.getElementById('preview-tab-data').classList.toggle('shadow-sm', tab === 'data');
            document.getElementById('preview-tab-data').classList.toggle('text-gray-900', tab === 'data');
            document.getElementById('preview-tab-data').classList.toggle('text-gray-600', tab !== 'data');
        }

        async function updatePreviewChart(fileId) {
            const chartType = document.getElementById('preview-chart-type')?.value || 'bar_chart';
            const container = document.getElementById('preview-chart-container');
            
            container.innerHTML = '<div class="spinner-sm mx-auto my-4"></div>';
            
            try {
                const data = await apiCall(`/api/processed/${fileId}/chart?chart_type=${chartType}`);
                if (data.success && data.chart_image) {
                    container.innerHTML = `<img src="${data.chart_image}" class="max-h-64 rounded-lg border border-gray-200" alt="Chart">`;
                } else {
                    container.innerHTML = '<div class="text-sm text-gray-500 py-4">No chart data available</div>';
                }
            } catch (e) {
                container.innerHTML = '<div class="text-sm text-red-500 py-4">Failed to generate chart</div>';
            }
        }

        async function loadPreviewData(fileId) {
            const container = document.getElementById('preview-data-container');
            try {
                const data = await apiCall(`/api/processed/${fileId}/data?page=1&limit=100`);
                if (data.success) {
                    container.innerHTML = `
                        <div class="overflow-x-auto">
                            <table class="min-w-full text-xs border border-gray-200 rounded-lg">
                                <thead class="bg-gray-50">
                                    <tr>
                                        ${data.columns.map(col => `<th class="text-left font-medium text-gray-600 px-2 py-1 border-b">${col}</th>`).join('')}
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.data.map(row => `
                                        <tr class="border-b border-gray-100">
                                            ${data.columns.map(col => `<td class="px-2 py-1 text-gray-700">${row[col] !== undefined ? row[col] : ''}</td>`).join('')}
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                            <div class="text-xs text-gray-500 text-center mt-2">
                                Showing ${data.data.length} of ${data.file.total_rows?.toLocaleString() || 0} rows (Page 1 of ${data.total_pages})
                            </div>
                        </div>
                    `;
                }
            } catch (e) {
                container.innerHTML = '<div class="text-sm text-red-500">Failed to load data</div>';
            }
        }

        async function deleteProcessedFile(fileId) {
            if (!confirm('Are you sure you want to delete this processed file?')) return;
            
            try {
                await apiCall(`/api/processed/${fileId}`, { method: 'DELETE' });
                showToast('File deleted', 'success');
                if (currentSelectedFY && currentSelectedType && currentSelectedMonth) {
                    await loadProcessedFiles(currentSelectedFY, currentSelectedType, currentSelectedMonth);
                }
                await loadProcessedTree();
            } catch (e) {
                showToast('Failed to delete file', 'error');
            }
        }

        function downloadProcessedFile(fileId) {
            window.open(`/api/processed/${fileId}/download`, '_blank');
        }

        function startAutoRefresh() {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(async () => {
                const statusData = await apiCall('/api/process/status');
                if (statusData.status === 'completed') {
                    await loadProcessedTree();
                }
            }, 10000); // Check every 10 seconds
        }

        function stopAutoRefresh() {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }
        }

        // ==================== SOURCE FILE FILTER ====================
        async function loadSourceFileFilter() {
            const container = document.getElementById('source-file-filter-container');
            const countEl = document.getElementById('source-file-selected-count');
            
            container.innerHTML = '<p class="text-xs text-gray-500 text-center py-2">Loading source files...</p>';
            countEl.textContent = '0 of 0 selected';
            
            try {
                const data = await apiCall('/api/primary/source-files');
                
                if (!data.success) {
                    container.innerHTML = `<p class="text-xs text-red-500 text-center py-2">${data.message || 'No source files available'}</p>`;
                    return;
                }
                
                if (!data.sources || data.sources.length === 0) {
                    container.innerHTML = '<p class="text-xs text-gray-500 text-center py-2">No source files found</p>';
                    return;
                }
                
                container.innerHTML = data.sources.map(source => `
                    <label class="flex items-center space-x-2 p-1 hover:bg-gray-100 rounded cursor-pointer">
                        <input type="checkbox" class="source-file-checkbox w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500" value="${source}" checked onchange="updateSourceFileCounter()">
                        <span class="text-sm text-gray-700 truncate">${source}</span>
                    </label>
                `).join('');
                
                updateSourceFileCounter();
            } catch (e) {
                container.innerHTML = '<p class="text-xs text-red-500 text-center py-2">Failed to load source files</p>';
            }
        }
        
        function selectAllSourceFiles() {
            document.querySelectorAll('.source-file-checkbox').forEach(cb => cb.checked = true);
            updateSourceFileCounter();
        }
        
        function clearAllSourceFiles() {
            document.querySelectorAll('.source-file-checkbox').forEach(cb => cb.checked = false);
            updateSourceFileCounter();
        }
        
        function getSelectedSourceFiles() {
            return Array.from(document.querySelectorAll('.source-file-checkbox:checked')).map(cb => cb.value);
        }
        
        function updateSourceFileCounter() {
            const checkboxes = document.querySelectorAll('.source-file-checkbox');
            const checked = document.querySelectorAll('.source-file-checkbox:checked');
            const countEl = document.getElementById('source-file-selected-count');
            countEl.textContent = `${checked.length} of ${checkboxes.length} selected`;
        }
        
        // ==================== FINAL PROCESSING ====================
        async function processAllRules() {
            try {
            const btn = document.getElementById('process-btn');
            const spinner = document.getElementById('process-spinner');
            const resultDiv = document.getElementById('process-result');
            
            btn.disabled = true;
            spinner.classList.remove('hidden');
            resultDiv.classList.add('hidden');
            
            // Get selected source files
            const selectedSourceFiles = getSelectedSourceFiles();
            if (selectedSourceFiles.length === 0) {
                btn.disabled = false;
                spinner.classList.add('hidden');
                showToast('Please select at least one source file', 'error');
                return;
            }
            
            // Validate custom output filename
            const customFilenameInput = document.getElementById('custom-output-filename');
            const customFilename = customFilenameInput ? customFilenameInput.value.trim() : '';
            if (!customFilename) {
                btn.disabled = false;
                spinner.classList.add('hidden');
                showToast('Please enter a custom output file name', 'error');
                if (customFilenameInput) customFilenameInput.focus();
                return;
            }
            
            // Reset all statuses
            document.getElementById('process-phase1-status').textContent = 'Pending';
            document.getElementById('process-phase2-status').textContent = 'Pending';
            document.getElementById('process-phase3-status').textContent = 'Pending';
            
            // Start background processing with selected source files
            const formData = new FormData();
            formData.append('selected_source_files', JSON.stringify(selectedSourceFiles));
            formData.append('custom_filename', customFilename);
            
            const startData = await apiCall('/api/process', { 
                method: 'POST',
                body: formData
            });
            
            if (!startData.success) {
                btn.disabled = false;
                spinner.classList.add('hidden');
                showToast(startData.message || 'Failed to start processing', 'error');
                return;
            }
            
            const filterInfo = startData.filtered ? ` (Filtering ${startData.filter_count} source files)` : '';
            showToast(`Processing started${filterInfo}. Please wait...`, 'success');
            
            // Poll for status every 2 seconds
            const pollInterval = setInterval(async () => {
                const statusData = await apiCall('/api/process/status');
                
                if (statusData.status === 'processing') {
                    // Update phase statuses based on progress
                    const progress = statusData.progress;
                    if (progress === 'loading_primary') {
                        document.getElementById('process-phase1-status').textContent = 'Running...';
                    } else if (progress === 'phase2') {
                        document.getElementById('process-phase1-status').textContent = 'Completed';
                        document.getElementById('process-phase2-status').textContent = 'Running...';
                    } else if (progress === 'phase3') {
                        document.getElementById('process-phase1-status').textContent = 'Completed';
                        document.getElementById('process-phase2-status').textContent = 'Completed';
                        document.getElementById('process-phase3-status').textContent = 'Running...';
                    } else if (progress === 'saving') {
                        document.getElementById('process-phase1-status').textContent = 'Completed';
                        document.getElementById('process-phase2-status').textContent = 'Completed';
                        document.getElementById('process-phase3-status').textContent = 'Saving...';
                    }
                } else if (statusData.status === 'completed') {
                    clearInterval(pollInterval);
                    btn.disabled = false;
                    spinner.classList.add('hidden');
                    
                    // All completed
                    document.getElementById('process-phase1-status').textContent = 'Completed';
                    document.getElementById('process-phase2-status').textContent = 'Completed';
                    document.getElementById('process-phase3-status').textContent = 'Completed';
                    document.getElementById('process-phase4-status').textContent = 'Completed';
                    
                    // Auto-refresh dashboard stats
                    loadDashboardStats();
                    loadProcessedTree();
                    
                    // Hide any lingering loading overlays
                    const loadingOverlay = document.getElementById('rules-loading-overlay');
                    if (loadingOverlay) loadingOverlay.classList.add('hidden');
                    
                    // Show result info (no download button - file saved to processed)
                    const result = statusData.result;
                    if (result && result.success) {
                        resultDiv.classList.remove('hidden');
                        
                        // Populate the info spans
                        document.getElementById('result-processed-at').textContent = result.processed_at || 'N/A';
                        document.getElementById('result-rows-processed').textContent = result.rows_processed?.toLocaleString() || 0;
                        document.getElementById('result-rules-applied').textContent = result.total_rules || 0;
                        document.getElementById('result-time-taken').textContent = result.processing_time || 'N/A';
                        
                        showToast(result.message || 'Processing completed successfully!', 'success');
                        // Auto-refresh the processed files history
                        loadFinalProcessedHistory();
                    }
                } else if (statusData.status === 'error') {
                    clearInterval(pollInterval);
                    btn.disabled = false;
                    spinner.classList.add('hidden');
                    showToast(statusData.message || 'Processing failed', 'error');
                }
            }, 2000);
        
            } catch(err) {

                console.error("Error starting processing:", err);
                const btn = document.getElementById('process-all-btn');
                const spinner = document.getElementById('process-all-spinner');
                if (btn) btn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                showToast(err.message || 'Failed to start processing. Please try again.', 'error');

            }
        }
        // ==================== FINAL PROCESSED HISTORY ====================
        async function loadFinalProcessedHistory() {
            const container = document.getElementById('final-processed-history-container');
            container.innerHTML = '<div class="flex items-center justify-center space-x-2 py-8"><div class="spinner-sm"></div><span class="text-sm text-gray-500">Loading...</span></div>';
            
            try {
                const data = await apiCall('/api/processed/files');
                if (data.success) {
                    // Save to cache for instant render on next tab switch
                    if (data.files) {
                        saveProcessCache(data.files);
                    }
                }
                if (data.success && data.files && data.files.length > 0) {
                    container.innerHTML = `
                        <div class="overflow-x-auto">
                            <table class="min-w-full text-sm border border-gray-200 rounded-lg">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2 border-b">File Name</th>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2 border-b">Processed Date & Time</th>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2 border-b">File Size</th>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2 border-b">Process Time</th>
                                        <th class="text-left font-medium text-gray-600 px-3 py-2 border-b w-24">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.files.map(file => `
                                        <tr class="border-b border-gray-100 hover:bg-gray-50">
                                            <td class="px-3 py-3">
                                                <div class="text-sm font-medium text-gray-900">${file.filename}</div>
                                                <div class="text-xs text-gray-500">Source: ${file.source_primary_filename || 'Unknown'}</div>
                                            </td>
                                            <td class="px-3 py-3">
                                                <div class="text-sm text-gray-700">${file.created_at || 'N/A'}</div>
                                            </td>
                                            <td class="px-3 py-3 text-sm text-gray-700">${file.file_size ? file.file_size + ' MB' : 'N/A'}</td>
                                            <td class="px-3 py-3 text-sm text-gray-700">${file.processing_time || 'N/A'}</td>
                                            <td class="px-3 py-3">
                                                <div class="flex items-center space-x-1">
                                                    <a href="/api/processed/${file.id}/download" target="_blank" class="p-1.5 text-green-500 hover:text-green-700 rounded hover:bg-green-50 transition-colors" title="Download">
                                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                                                    </a>
                                                    <button onclick="deleteProcessedFile(${file.id})" class="p-1.5 text-red-500 hover:text-red-700 rounded hover:bg-red-50 transition-colors" title="Delete">
                                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                } else {
                    container.innerHTML = '<p class="text-sm text-gray-500 text-center py-8">No processed files yet. Run processing to see history here.</p>';
                }
            } catch (e) {
                container.innerHTML = '<p class="text-sm text-red-500 text-center py-8">Failed to load processed file history</p>';
            }
        }

        // ==================== RULE EXPORT / IMPORT / MIGRATE ====================
        async function exportRules() {
            try {
                const companyId = localStorage.getItem('company_id') || '';
                const moduleId = localStorage.getItem('module_id') || '';
                if (!companyId || !moduleId) {
                    showToast('Please select a company and module first', 'warning');
                    return;
                }
                
                const formData = new FormData();
                formData.append('company_id', companyId);
                formData.append('module_id', moduleId);
                
                const response = await fetch('/api/company/export-rules', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` },
                    body: formData
                });
                
                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    showToast(err.detail || 'Export failed', 'error');
                    return;
                }
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const filename = response.headers.get('content-disposition')?.match(/filename="(.+)"/)?.[1] || 'rules_export.json';
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                
                showToast('Rules exported successfully', 'success');
            } catch (error) {
                showToast('Export failed: ' + error.message, 'error');
            }
        }

        async function importRules() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            
            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                try {
                    const text = await file.text();
                    const companyId = localStorage.getItem('company_id') || '';
                    const moduleId = localStorage.getItem('module_id') || '';
                    if (!companyId || !moduleId) {
                        showToast('Please select a company and module first', 'warning');
                        return;
                    }
                    
                    const formData = new FormData();
                    formData.append('company_id', companyId);
                    formData.append('module_id', moduleId);
                    formData.append('rules_json', text);
                    
                    const data = await apiCall('/api/company/import-rules', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (data.success) {
                        showToast(`Imported ${data.imported_count} rules successfully`, 'success');
                        isRulesPageLoaded = false;
                        await loadRulePageData();
                    } else {
                        showToast(data.message || 'Import failed', 'error');
                    }
                } catch (error) {
                    showToast('Import failed: ' + error.message, 'error');
                }
            };
            
            input.click();
        }

        async function migrateRules() {
            const sourceCompanyId = prompt('Enter Source Company ID:');
            if (!sourceCompanyId) return;
            const sourceModuleId = prompt('Enter Source Module ID:');
            if (!sourceModuleId) return;
            
            const targetCompanyId = localStorage.getItem('company_id') || '';
            const targetModuleId = localStorage.getItem('module_id') || '';
            if (!targetCompanyId || !targetModuleId) {
                showToast('Please select a target company and module first', 'warning');
                return;
            }
            
            if (!confirm(`Migrate rules from Company ${sourceCompanyId}/Module ${sourceModuleId} to Company ${targetCompanyId}/Module ${targetModuleId}?`)) {
                return;
            }
            
            try {
                const formData = new FormData();
                formData.append('source_company_id', sourceCompanyId);
                formData.append('source_module_id', sourceModuleId);
                formData.append('target_company_id', targetCompanyId);
                formData.append('target_module_id', targetModuleId);
                
                const data = await apiCall('/api/company/migrate-rules', {
                    method: 'POST',
                    body: formData
                });
                
                if (data.success) {
                    showToast(`Migrated ${data.migrated_count} rules successfully`, 'success');
                    isRulesPageLoaded = false;
                    await loadRulePageData();
                } else {
                    showToast(data.message || 'Migration failed', 'error');
                }
            } catch (error) {
                showToast('Migration failed: ' + error.message, 'error');
            }
        }

        // ==================== IFRAME DETECTION ====================
        function detectIframeMode() {
            // Detect if running inside an iframe (embedded in saas.html)
            if (window.parent !== window) {
                // Hide the header navigation (we're in the SaaS app shell)
                const header = document.querySelector('header');
                if (header) header.style.display = 'none';
                
                // Adjust main padding since header is hidden
                document.querySelector('main').style.paddingTop = '0';
                
                // Parse the hash from parent URL fragment if available
                // The parent sets the hash like #upload or #rules
                const iframeTab = window.location.hash.replace('#', '');
                if (iframeTab) {
                    switchTab(iframeTab);
                } else {
                    switchTab('dashboard');
                }
            } else {
                restoreTabFromHash();
            }
        }

        // ==================== INITIALIZATION ====================
        document.addEventListener('DOMContentLoaded', () => {
            detectIframeMode();
        });

        // ==================== MASTER FILE FORMULA & DELETE ====================

        async function deleteMasterFile() {
            if (!currentFolderId) {
                showToast('Please select a folder first', 'warning');
                return;
            }
            if (!confirm('Are you sure you want to delete the master file? This action cannot be undone.')) {
                return;
            }
            try {
                const data = await apiCall(`/api/master/${currentFolderId}`, { method: 'DELETE' });
                if (data.success) {
                    showToast('Master file deleted successfully', 'success');
                    toggleMasterView();
                    document.getElementById('view-master-btn').classList.add('hidden');
                    document.getElementById('master-file-btn').classList.remove('hidden');
                } else {
                    showToast(data.message || 'Delete failed', 'error');
                }
            } catch (error) {
                showToast('Delete failed: ' + error.message, 'error');
            }
        }

        let formulaColumnsList = [];

        function openFormulaModal() {
            if (!currentFolderId) {
                showToast('Please select a folder first', 'warning');
                return;
            }
            document.getElementById('formula-modal').classList.remove('hidden');
            loadFormulaColumns();
            resetFormulaForm();
        }

        function closeFormulaModal() {
            document.getElementById('formula-modal').classList.add('hidden');
        }

        function resetFormulaForm() {
            document.getElementById('formula-type').value = 'SUM';
            document.getElementById('formula-column-name').value = '';
            document.getElementById('formula-constant').value = '';
            document.getElementById('formula-preview-result').classList.add('hidden');
            document.getElementById('formula-error').classList.add('hidden');
            document.getElementById('formula-progress').classList.add('hidden');
            document.getElementById('formula-apply-btn').disabled = false;
            updateFormulaUI();
        }

        async function loadFormulaColumns() {
            try {
                const data = await apiCall(`/api/master/${currentFolderId}/columns`);
                if (data.success && data.columns) {
                    formulaColumnsList = data.columns;
                } else {
                    formulaColumnsList = [];
                }
            } catch (e) {
                formulaColumnsList = [];
            }
        }

        function updateFormulaUI() {
            const type = document.getElementById('formula-type').value;
            const container = document.getElementById('formula-columns-container');
            const sumifContainer = document.getElementById('formula-sumif-container');
            const constantContainer = document.getElementById('formula-constant-container');
            const valueContainer = document.getElementById('formula-secondary-value-container');
            const countContainer = document.getElementById('formula-count-column-container');
            const labels = {
                SUM: 'Columns to Sum (comma-separated or add multiple)',
                '-SUM': 'Columns to Sum (will negate the total)',
                SUBTRACT: 'Minuend, Subtrahend (2 columns)',
                MULTIPLY: 'Multiplicand, Multiplier (2 columns)',
                DIVIDE: 'Dividend, Divisor (2 columns)',
                PERCENTAGE: 'Part, Whole (2 columns)',
                CONCAT: 'Columns to Join (comma-separated or add multiple)',
                ABS: 'Column to convert to absolute value (1 column)'
            };
            document.getElementById('formula-columns-label').textContent = labels[type] || 'Columns';
            
            // Show/hide containers based on formula type
            if (type === 'SUMIF' || type === 'COUNTIF' || type === 'VLOOKUP' || type === 'HLOOKUP') {
                container.classList.add('hidden');
                sumifContainer.classList.remove('hidden');
                constantContainer.classList.add('hidden');
                // Show/hide value vs count column based on formula type
                if (type === 'SUMIF' || type === 'VLOOKUP' || type === 'HLOOKUP') {
                    valueContainer.classList.remove('hidden');
                    countContainer.classList.add('hidden');
                    // Update value column label for VLOOKUP/HLOOKUP vs SUMIF
                    const valLabel = sumifContainer.querySelector('#formula-secondary-value-container label');
                    if (valLabel) {
                        valLabel.textContent = type === 'SUMIF' ? 'Value Column to Sum *' : 'Value Column to Extract *';
                    }
                    const valHelp = sumifContainer.querySelector('#formula-secondary-value-container .text-xs');
                    if (valHelp) {
                        valHelp.textContent = type === 'SUMIF' ? 'Column from secondary file whose values will be summed' : 'Column from secondary file to extract first matched value from';
                    }
                } else { // COUNTIF
                    valueContainer.classList.add('hidden');
                    countContainer.classList.remove('hidden');
                }
                // Populate primary columns and secondary file dropdown
                populateFormulaPrimaryColumns();
                populateFormulaSecondaryFiles();
            } else {
                container.classList.remove('hidden');
                sumifContainer.classList.add('hidden');
                constantContainer.classList.remove('hidden');
            }
            
            updateFormulaHints();
        }

        async function populateFormulaPrimaryColumns() {
            const select = document.getElementById('formula-primary-column');
            select.innerHTML = '<option value="">-- Select Column --</option>';
            try {
                const data = await apiCall(`/api/master/${currentFolderId}/columns`);
                if (data.success && data.columns) {
                    data.columns.forEach(col => {
                        select.innerHTML += `<option value="${col}">${col}</option>`;
                    });
                }
            } catch (e) {
                console.error('Failed to load primary columns:', e);
            }
        }

        async function populateFormulaSecondaryFiles() {
            const select = document.getElementById('formula-secondary-file');
            select.innerHTML = '<option value="">-- Select File --</option>';
            
            try {
                // Get all files from all folders
                const foldersData = await apiCall('/api/folders');
                let allFilesList = [];
                let masterFiles = [];
                
                if (foldersData.success) {
                    for (const folder of foldersData.folders) {
                        const filesData = await apiCall(`/api/files/${folder.id}`);
                        if (filesData.success) {
                            allFilesList = allFilesList.concat(filesData.files);
                        }
                    }
                    
                    // Fetch master files for all folders
                    const masterPromises = foldersData.folders.map(folder => 
                        apiCall(`/api/master/${folder.id}`).then(res => {
                            if (res.success && res.master && res.master.exists) {
                                return {
                                    id: `master_${folder.id}`,
                                    original_name: `Master_File_${folder.name}`,
                                    is_master: true,
                                    folder_id: folder.id,
                                    folder_name: folder.name
                                };
                            }
                            return null;
                        }).catch(() => null)
                    );
                    const masterResults = await Promise.all(masterPromises);
                    masterFiles = masterResults.filter(m => m !== null);
                }

                // Add regular files
                allFilesList.forEach(file => {
                    select.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                });
                
                // Add master files
                if (masterFiles.length > 0) {
                    select.innerHTML += `<optgroup label="--- Master Files ---">`;
                    masterFiles.forEach(file => {
                        select.innerHTML += `<option value="${file.id}">${file.original_name}</option>`;
                    });
                    select.innerHTML += `</optgroup>`;
                }
            } catch (e) {
                console.error('Failed to load secondary files:', e);
            }
        }

        async function loadFormulaSecondarySheets() {
            const fileId = document.getElementById('formula-secondary-file').value;
            const sheetSelect = document.getElementById('formula-secondary-sheet');
            sheetSelect.innerHTML = '<option value="">-- Select Sheet --</option>';
            
            if (!fileId) return;
            
            if (fileId.startsWith('master_')) {
                sheetSelect.innerHTML += `<option value="Working" selected>Working</option>`;
                loadFormulaSecondaryColumns();
                return;
            }
            
            try {
                const data = await apiCall(`/api/files/${fileId}/sheets`);
                if (data.success && data.sheets) {
                    data.sheets.forEach(sheet => {
                        sheetSelect.innerHTML += `<option value="${sheet}">${sheet}</option>`;
                    });
                }
            } catch (e) {
                console.error('Failed to load secondary sheets:', e);
            }
        }

        async function loadFormulaSecondaryColumns() {
            const fileId = document.getElementById('formula-secondary-file').value;
            const sheetName = document.getElementById('formula-secondary-sheet').value;
            const matchColSelect = document.getElementById('formula-secondary-match-column');
            const valueColSelect = document.getElementById('formula-secondary-value-column');
            const countColSelect = document.getElementById('formula-count-column');
            
            matchColSelect.innerHTML = '<option value="">-- Match Column --</option>';
            valueColSelect.innerHTML = '<option value="">-- Select Column --</option>';
            countColSelect.innerHTML = '<option value="">-- Select Column --</option>';
            
            if (!fileId || !sheetName) return;
            
            try {
                let data;
                if (fileId.startsWith('master_')) {
                    const folderId = fileId.replace('master_', '');
                    data = await apiCall(`/api/master/${folderId}/columns`);
                } else {
                    data = await apiCall(`/api/files/${fileId}/columns?sheet_name=${encodeURIComponent(sheetName)}`);
                }
                
                if (data.success && data.columns) {
                    data.columns.forEach(col => {
                        matchColSelect.innerHTML += `<option value="${col}">${col}</option>`;
                        valueColSelect.innerHTML += `<option value="${col}">${col}</option>`;
                        countColSelect.innerHTML += `<option value="${col}">${col}</option>`;
                    });
                }
            } catch (e) {
                console.error('Failed to load secondary columns:', e);
            }
        }

        function updateFormulaHints() {
            const input = document.getElementById('formula-columns-input');
            const hints = document.getElementById('formula-hints');
            const val = input.value;
            const lastComma = val.lastIndexOf(',');
            const currentPart = lastComma >= 0 ? val.substring(lastComma + 1).trim() : val.trim();
            if (!currentPart) {
                hints.classList.add('hidden');
                return;
            }
            const matches = formulaColumnsList.filter(c =>
                c.toLowerCase().includes(currentPart.toLowerCase()) &&
                !val.split(',').map(s => s.trim()).includes(c)
            ).slice(0, 8);
            if (matches.length === 0) {
                hints.classList.add('hidden');
                return;
            }
            hints.innerHTML = matches.map(c =>
                `<div class="px-3 py-1.5 hover:bg-blue-50 cursor-pointer text-sm text-gray-700" onclick="selectFormulaHint('${c.replace(/'/g, "\\'")}')">${c}</div>`
            ).join('');
            hints.classList.remove('hidden');
        }

        function selectFormulaHint(columnName) {
            const input = document.getElementById('formula-columns-input');
            const val = input.value;
            const lastComma = val.lastIndexOf(',');
            if (lastComma >= 0) {
                input.value = val.substring(0, lastComma + 1) + ' ' + columnName + ', ';
            } else {
                input.value = columnName + ', ';
            }
            input.focus();
            updateFormulaHints();
        }

        function validateFormulaColumns() {
            const input = document.getElementById('formula-columns-input');
            const errorEl = document.getElementById('formula-error');
            const cols = input.value.split(',').map(s => s.trim()).filter(s => s);
            const invalid = cols.filter(c => !formulaColumnsList.includes(c));
            if (invalid.length > 0) {
                errorEl.textContent = `Invalid column(s): ${invalid.join(', ')}`;
                errorEl.classList.remove('hidden');
                return null;
            }
            errorEl.classList.add('hidden');
            return cols;
        }

        function showFormulaProgress(msg) {
            const el = document.getElementById('formula-progress');
            el.textContent = msg;
            el.classList.remove('hidden');
        }

        function hideFormulaProgress() {
            document.getElementById('formula-progress').classList.add('hidden');
        }

        async function previewFormula() {
            const type = document.getElementById('formula-type').value;
            
            // Handle SUMIF/COUNTIF/VLOOKUP/HLOOKUP validation
            if (type === 'SUMIF' || type === 'COUNTIF' || type === 'VLOOKUP' || type === 'HLOOKUP') {
                const primaryCol = document.getElementById('formula-primary-column').value;
                const secFile = document.getElementById('formula-secondary-file').value;
                const secSheet = document.getElementById('formula-secondary-sheet').value;
                const secMatchCol = document.getElementById('formula-secondary-match-column').value;
                const secValueCol = (type === 'SUMIF' || type === 'VLOOKUP' || type === 'HLOOKUP') ? document.getElementById('formula-secondary-value-column').value : null;
                const countCol = type === 'COUNTIF' ? document.getElementById('formula-count-column').value : null;
                
                if (!primaryCol) {
                    document.getElementById('formula-error').textContent = 'Please select a primary column';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (!secFile) {
                    document.getElementById('formula-error').textContent = 'Please select a secondary file';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (!secSheet) {
                    document.getElementById('formula-error').textContent = 'Please select a secondary sheet';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (!secMatchCol) {
                    document.getElementById('formula-error').textContent = 'Please select a match column';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if ((type === 'SUMIF' || type === 'VLOOKUP' || type === 'HLOOKUP') && !secValueCol) {
                    document.getElementById('formula-error').textContent = type === 'SUMIF' ? 'Please select a value column' : 'Please select a value column to extract';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (type === 'COUNTIF' && !countCol) {
                    document.getElementById('formula-error').textContent = 'Please select a count column';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                
                document.getElementById('formula-error').classList.add('hidden');
                showFormulaProgress('Computing preview...');
                try {
                    const formData = new FormData();
                    formData.append('formula_type', type);
                    formData.append('source_columns', ''); // Required but not used for SUMIF/COUNTIF
                    formData.append('primary_column', primaryCol);
                    formData.append('secondary_file', secFile);
                    formData.append('secondary_sheet', secSheet);
                    formData.append('secondary_match_column', secMatchCol);
                    if (secValueCol) formData.append('secondary_value_column', secValueCol);
                    if (countCol) formData.append('count_column', countCol);
                    formData.append('match_type', document.getElementById('formula-match-type').value);
                    
                    const data = await apiCall(`/api/master/${currentFolderId}/formula-preview`, {
                        method: 'POST',
                        body: formData
                    });
                    hideFormulaProgress();
                    if (data.success) {
                        const resultEl = document.getElementById('formula-preview-result');
                        resultEl.innerHTML = `<p class="text-xs text-gray-500 mb-1">Preview (first 5 rows):</p>` +
                            data.preview.map((v, i) => `<div class="text-sm font-mono text-gray-700">Row ${i + 1}: ${v !== null && v !== undefined ? v : 'NULL'}</div>`).join('');
                        resultEl.classList.remove('hidden');
                    } else {
                        showToast(data.message || 'Preview failed', 'error');
                    }
                } catch (error) {
                    hideFormulaProgress();
                    showToast('Preview failed: ' + error.message, 'error');
                }
                return;
            }
            
            // Regular formulas
            const cols = validateFormulaColumns();
            if (!cols) return;
            const typeReqs = { SUBTRACT: 2, MULTIPLY: 2, DIVIDE: 2, PERCENTAGE: 2, ABS: 1 };
            if (typeReqs[type] && cols.length !== typeReqs[type]) {
                document.getElementById('formula-error').textContent = `${type} requires exactly ${typeReqs[type]} column${typeReqs[type] > 1 ? 's' : ''}`;
                document.getElementById('formula-error').classList.remove('hidden');
                return;
            }
            document.getElementById('formula-error').classList.add('hidden');
            showFormulaProgress('Computing preview...');
            try {
                const formData = new FormData();
                formData.append('formula_type', type);
                formData.append('source_columns', cols.join(','));
                const constant = document.getElementById('formula-constant').value;
                if (constant) formData.append('constant_value', constant);
                const data = await apiCall(`/api/master/${currentFolderId}/formula-preview`, {
                    method: 'POST',
                    body: formData
                });
                hideFormulaProgress();
                if (data.success) {
                    const resultEl = document.getElementById('formula-preview-result');
                    resultEl.innerHTML = `<p class="text-xs text-gray-500 mb-1">Preview (first 5 rows):</p>` +
                        data.preview.map((v, i) => `<div class="text-sm font-mono text-gray-700">Row ${i + 1}: ${v !== null && v !== undefined ? v : 'NULL'}</div>`).join('');
                    resultEl.classList.remove('hidden');
                } else {
                    showToast(data.message || 'Preview failed', 'error');
                }
            } catch (error) {
                hideFormulaProgress();
                showToast('Preview failed: ' + error.message, 'error');
            }
        }

        async function applyFormula() {
            const type = document.getElementById('formula-type').value;
            const columnName = document.getElementById('formula-column-name').value.trim();
            
            if (!columnName) {
                document.getElementById('formula-error').textContent = 'Please enter a new column name';
                document.getElementById('formula-error').classList.remove('hidden');
                return;
            }
            
            // Handle SUMIF/COUNTIF/VLOOKUP/HLOOKUP validation and submission
            if (type === 'SUMIF' || type === 'COUNTIF' || type === 'VLOOKUP' || type === 'HLOOKUP') {
                const primaryCol = document.getElementById('formula-primary-column').value;
                const secFile = document.getElementById('formula-secondary-file').value;
                const secSheet = document.getElementById('formula-secondary-sheet').value;
                const secMatchCol = document.getElementById('formula-secondary-match-column').value;
                const secValueCol = (type === 'SUMIF' || type === 'VLOOKUP' || type === 'HLOOKUP') ? document.getElementById('formula-secondary-value-column').value : null;
                const countCol = type === 'COUNTIF' ? document.getElementById('formula-count-column').value : null;
                
                if (!primaryCol) {
                    document.getElementById('formula-error').textContent = 'Please select a primary column';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (!secFile) {
                    document.getElementById('formula-error').textContent = 'Please select a secondary file';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (!secSheet) {
                    document.getElementById('formula-error').textContent = 'Please select a secondary sheet';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (!secMatchCol) {
                    document.getElementById('formula-error').textContent = 'Please select a match column';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (type === 'SUMIF' && !secValueCol) {
                    document.getElementById('formula-error').textContent = 'Please select a value column';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                if (type === 'COUNTIF' && !countCol) {
                    document.getElementById('formula-error').textContent = 'Please select a count column';
                    document.getElementById('formula-error').classList.remove('hidden');
                    return;
                }
                
                document.getElementById('formula-error').classList.add('hidden');
                document.getElementById('formula-apply-btn').disabled = true;
                showFormulaProgress('Applying formula, please wait...');
                try {
                    const formData = new FormData();
                    formData.append('formula_type', type);
                    formData.append('column_name', columnName);
                    formData.append('source_columns', ''); // Required but not used for SUMIF/COUNTIF
                    formData.append('primary_column', primaryCol);
                    formData.append('secondary_file', secFile);
                    formData.append('secondary_sheet', secSheet);
                    formData.append('secondary_match_column', secMatchCol);
                    if (secValueCol) formData.append('secondary_value_column', secValueCol);
                    if (countCol) formData.append('count_column', countCol);
                    formData.append('match_type', document.getElementById('formula-match-type').value);
                    
                    const data = await apiCall(`/api/master/${currentFolderId}/formula`, {
                        method: 'POST',
                        body: formData
                    });
                    hideFormulaProgress();
                    document.getElementById('formula-apply-btn').disabled = false;
                    if (data.success) {
                        showToast(`Formula applied to ${(data.rows_affected || 0).toLocaleString()} rows in '${data.column_name}'`, 'success');
                        closeFormulaModal();
                        await Promise.all([
                            loadMasterPreview(),
                            loadMasterStats(),
                            loadMasterSummary()
                        ]);
                    } else {
                        showToast(data.message || 'Apply failed', 'error');
                    }
                } catch (error) {
                    hideFormulaProgress();
                    document.getElementById('formula-apply-btn').disabled = false;
                    showToast('Apply failed: ' + error.message, 'error');
                }
                return;
            }
            
            // Regular formulas
            const cols = validateFormulaColumns();
            if (!cols) return;
            const typeReqs = { SUBTRACT: 2, MULTIPLY: 2, DIVIDE: 2, PERCENTAGE: 2, ABS: 1 };
            if (typeReqs[type] && cols.length !== typeReqs[type]) {
                document.getElementById('formula-error').textContent = `${type} requires exactly ${typeReqs[type]} column${typeReqs[type] > 1 ? 's' : ''}`;
                document.getElementById('formula-error').classList.remove('hidden');
                return;
            }
            document.getElementById('formula-error').classList.add('hidden');
            document.getElementById('formula-apply-btn').disabled = true;
            showFormulaProgress('Applying formula, please wait...');
            try {
                const formData = new FormData();
                formData.append('formula_type', type);
                formData.append('column_name', columnName);
                formData.append('source_columns', cols.join(','));
                const constant = document.getElementById('formula-constant').value;
                if (constant) formData.append('constant_value', constant);
                const data = await apiCall(`/api/master/${currentFolderId}/formula`, {
                    method: 'POST',
                    body: formData
                });
                hideFormulaProgress();
                document.getElementById('formula-apply-btn').disabled = false;
                if (data.success) {
                    showToast(`Formula applied to ${(data.rows_affected || 0).toLocaleString()} rows in '${data.column_name}'`, 'success');
                    closeFormulaModal();
                    await Promise.all([
                        loadMasterPreview(),
                        loadMasterStats(),
                        loadMasterSummary()
                    ]);
                } else {
                    showToast(data.message || 'Apply failed', 'error');
                }
            } catch (error) {
                hideFormulaProgress();
                document.getElementById('formula-apply-btn').disabled = false;
                showToast('Apply failed: ' + error.message, 'error');
            }
        }

        async function deleteMasterColumn(columnName) {
            if (!confirm(`Delete column '${columnName}'? This cannot be undone.`)) return;
            try {
                const data = await apiCall(`/api/master/${currentFolderId}/columns/${encodeURIComponent(columnName)}`, {
                    method: 'DELETE'
                });
                if (data.success) {
                    showToast(`Column '${columnName}' deleted`, 'success');
                    await Promise.all([
                        loadMasterPreview(),
                        loadMasterStats(),
                        loadMasterSummary()
                    ]);
                } else {
                    showToast(data.message || 'Delete failed', 'error');
                }
            } catch (error) {
                showToast('Delete failed: ' + error.message, 'error');
            }
        }

        // ==================== RECYCLE BIN FUNCTIONS ====================
        
        async function loadRecycleBin() {
            try {
                const data = await apiCall('/api/recycle-bin');
                const tbody = document.getElementById('recycle-bin-body');
                if (!data.success || !data.items || data.items.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-sm text-gray-500">Recycle bin is empty</td></tr>';
                    return;
                }
                
                const typeLabels = {
                    'file': 'File',
                    'folder': 'Folder',
                    'master_file': 'Master File'
                };
                const typeBadgeColors = {
                    'file': 'bg-blue-100 text-blue-700',
                    'folder': 'bg-yellow-100 text-yellow-700',
                    'master_file': 'bg-purple-100 text-purple-700'
                };
                
                tbody.innerHTML = data.items.map(item => {
                    const type = item.entity_type || 'unknown';
                    const label = typeLabels[type] || type;
                    const badgeColor = typeBadgeColors[type] || 'bg-gray-100 text-gray-700';
                    const deletedAt = item.deleted_at ? new Date(item.deleted_at).toLocaleString() : 'Unknown';
                    
                    return `
                        <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                            <td class="px-4 py-3">
                                <span class="inline-flex px-2 py-1 text-xs font-medium rounded-full ${badgeColor}">${label}</span>
                            </td>
                            <td class="px-4 py-3 text-sm text-gray-900 font-medium">${escapeHtml(item.entity_name || 'Unknown')}</td>
                            <td class="px-4 py-3 text-sm text-gray-500">${deletedAt}</td>
                            <td class="px-4 py-3 text-sm text-gray-500">${item.deleted_by || 'System'}</td>
                            <td class="px-4 py-3 text-right">
                                <button onclick="restoreRecycleBinItem(${item.id})" class="inline-flex items-center px-3 py-1 text-xs font-medium text-green-700 bg-green-50 rounded-lg hover:bg-green-100 transition-colors mr-2" title="Restore">
                                    <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                    </svg>
                                    Restore
                                </button>
                                <button onclick="permanentDeleteRecycleBinItem(${item.id})" class="inline-flex items-center px-3 py-1 text-xs font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors" title="Permanently Delete">
                                    <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                    </svg>
                                    Permanent Delete
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            } catch (error) {
                document.getElementById('recycle-bin-body').innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-sm text-red-500">Failed to load: ' + escapeHtml(error.message) + '</td></tr>';
            }
        }

        async function restoreRecycleBinItem(recycleId) {
            if (!confirm('Restore this item back to its original location?')) return;
            try {
                const data = await apiCall(`/api/recycle-bin/${recycleId}/restore`, { method: 'POST' });
                if (data.success) {
                    showToast('Item restored successfully!', 'success');
                    loadRecycleBin();
                    loadFolders();
                    loadDashboardStats();
                } else {
                    showToast(data.message || 'Restore failed', 'error');
                }
            } catch (error) {
                showToast('Restore failed: ' + error.message, 'error');
            }
        }

        async function permanentDeleteRecycleBinItem(recycleId) {
            if (!confirm('Permanently delete this item? This action cannot be undone!')) return;
            try {
                const data = await apiCall(`/api/recycle-bin/${recycleId}/permanent-delete`, { method: 'DELETE' });
                if (data.success) {
                    showToast('Item permanently deleted', 'success');
                    loadRecycleBin();
                } else {
                    showToast(data.message || 'Delete failed', 'error');
                }
            } catch (error) {
                showToast('Delete failed: ' + error.message, 'error');
            }
        }
        // ==================== FIND & REPLACE FUNCTIONS ====================

        async function openFindReplaceModal() {
            if (!currentFolderId) {
                showToast('Please select a folder first', 'warning');
                return;
            }
            document.getElementById('find-replace-modal').classList.remove('hidden');
            resetFindReplaceForm();
            await populateFindReplaceColumns();
        }

        function closeFindReplaceModal() {
            document.getElementById('find-replace-modal').classList.add('hidden');
        }

        function resetFindReplaceForm() {
            document.getElementById('find-text').value = '';
            document.getElementById('replace-text').value = '';
            document.getElementById('find-replace-column').value = '';
            document.getElementById('find-match-type').value = 'contains';
            document.getElementById('find-case-sensitive').checked = false;
            document.getElementById('find-replace-error').classList.add('hidden');
            document.getElementById('find-replace-progress').classList.add('hidden');
            document.getElementById('find-replace-result').classList.add('hidden');
        }

        async function populateFindReplaceColumns() {
            const select = document.getElementById('find-replace-column');
            select.innerHTML = '<option value="">All Text Columns</option>';
            try {
                const data = await apiCall(`/api/master/${currentFolderId}/columns`);
                if (data.success && data.columns) {
                    data.columns.forEach(col => {
                        if (col !== 'Source_File_Name') {
                            select.innerHTML += `<option value="${col}">${col}</option>`;
                        }
                    });
                }
            } catch (e) {
                console.error('Failed to load columns for find/replace:', e);
            }
        }

        async function previewFindReplace() {
            const findText = document.getElementById('find-text').value;
            if (!findText) {
                document.getElementById('find-replace-error').textContent = 'Find text cannot be empty';
                document.getElementById('find-replace-error').classList.remove('hidden');
                return;
            }
            document.getElementById('find-replace-error').classList.add('hidden');
            await executeFindReplaceOperation(true);
        }

        async function executeFindReplace(dryRun = false) {
            // If called from Replace All button, dryRun is false (default)
            const findText = document.getElementById('find-text').value;
            if (!findText) {
                document.getElementById('find-replace-error').textContent = 'Find text cannot be empty';
                document.getElementById('find-replace-error').classList.remove('hidden');
                return;
            }
            document.getElementById('find-replace-error').classList.add('hidden');
            await executeFindReplaceOperation(false);
        }

        async function executeFindReplaceOperation(dryRun) {
            const findText = document.getElementById('find-text').value;
            const replaceText = document.getElementById('replace-text').value;
            const column = document.getElementById('find-replace-column').value;
            const matchType = document.getElementById('find-match-type').value;
            const caseSensitive = document.getElementById('find-case-sensitive').checked;

            // Show progress
            document.getElementById('find-replace-progress').classList.remove('hidden');
            document.getElementById('find-replace-result').classList.add('hidden');
            document.getElementById('find-replace-apply-btn').disabled = true;

            try {
                const formData = new FormData();
                formData.append('find_text', findText);
                formData.append('replace_text', replaceText);
                formData.append('match_type', matchType);
                formData.append('case_sensitive', caseSensitive.toString());
                formData.append('dry_run', dryRun.toString());
                if (column) {
                    formData.append('column', column);
                }

                const data = await apiCall(`/api/master/${currentFolderId}/find-replace`, {
                    method: 'POST',
                    body: formData
                });

                document.getElementById('find-replace-progress').classList.add('hidden');
                document.getElementById('find-replace-apply-btn').disabled = false;

                if (data.success) {
                    const resultEl = document.getElementById('find-replace-result');
                    const resultTextEl = document.getElementById('find-replace-result-text');
                    const resultDetailsEl = document.getElementById('find-replace-result-details');

                    resultTextEl.textContent = data.message;
                    
                    if (data.columns_modified && data.columns_modified.length > 0) {
                        resultDetailsEl.innerHTML = data.columns_modified.map(col =>
                            `<li>Column "${col.column}": ${col.rows_affected} row(s) affected</li>`
                        ).join('');
                    } else {
                        resultDetailsEl.innerHTML = '<li>No matches found</li>';
                    }
                    
                    resultEl.classList.remove('hidden');

                    if (!dryRun && data.total_rows_affected > 0) {
                        showToast(`Replaced ${data.total_rows_affected} occurrences`, 'success');
                        // Refresh master preview
                        if (masterViewOpen) {
                            await loadMasterPreview();
                            await loadMasterStats();
                        }
                    }
                } else {
                    showToast(data.message || 'Find & Replace failed', 'error');
                }
            } catch (error) {
                document.getElementById('find-replace-progress').classList.add('hidden');
                document.getElementById('find-replace-apply-btn').disabled = false;
                showToast('Find & Replace failed: ' + error.message, 'error');
            }
        }

        // Handle soft-refresh messages from saas wrapper to update data without destroying state
        window.addEventListener('message', function(e) {
            if (e.data && e.data.type === 'saas_refresh') {
                if (typeof loadFiles === 'function') loadFiles();
                if (typeof loadPhase1Files === 'function') loadPhase1Files();
                if (typeof loadSecondaryFiles === 'function') loadSecondaryFiles();
                if (typeof loadFinalProcessedHistory === 'function') loadFinalProcessedHistory();
                if (typeof loadSourceFileFilter === 'function') loadSourceFileFilter();
            }
        });
    