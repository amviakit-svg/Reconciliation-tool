import os

def patch_frontend():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add HTML Modal for validation warnings
    modal_html = """
    <!-- Validation Warning Modal -->
    <div id="validation-warning-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full hidden z-50">
        <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
            <div class="mt-3 text-center">
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100">
                    <svg class="h-6 w-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                    </svg>
                </div>
                <h3 class="text-lg leading-6 font-medium text-gray-900 mt-4">Validation Warning</h3>
                <div class="mt-2 px-7 py-3">
                    <p class="text-sm text-gray-500 text-left mb-2">
                        The following columns are required by your Phase 4 Summary Rules, but they are NOT being generated in earlier phases (Phase 1, 2, or 3):
                    </p>
                    <ul id="validation-missing-columns" class="text-sm text-red-600 text-left list-disc list-inside mb-4 font-semibold">
                    </ul>
                    <p class="text-sm text-gray-500 text-left">
                        <strong>Solution:</strong> Please go to Phase 2 (Matching & Mapping) or Phase 3 (Remarks) and add rules to generate these columns.
                    </p>
                </div>
                <div class="items-center px-4 py-3 sm:flex sm:flex-row-reverse">
                    <button id="validation-force-btn" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm">
                        Process Anyway
                    </button>
                    <button id="validation-cancel-btn" class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                        Cancel and Fix
                    </button>
                </div>
            </div>
        </div>
    </div>
    """

    # Inject modal right before the closing body tag or near other modals
    if '<!-- Validation Warning Modal -->' not in content:
        if '<div id="toast-container"' in content:
            content = content.replace('<div id="toast-container"', modal_html + '\n    <div id="toast-container"')

    old_func = '''async function processAllRules() {'''
    new_func = '''async function processAllRules(force = false) {'''

    if old_func in content:
        content = content.replace(old_func, new_func)

    old_api_call = '''            // Start background processing with selected source files
            const formData = new FormData();
            formData.append('selected_source_files', JSON.stringify(selectedSourceFiles));
            formData.append('custom_filename', customFilename);
            
            const startData = await apiCall('/api/process', { 
                method: 'POST',
                body: formData
            });'''

    new_api_call = '''            // Start background processing with selected source files
            const formData = new FormData();
            formData.append('selected_source_files', JSON.stringify(selectedSourceFiles));
            formData.append('custom_filename', customFilename);
            formData.append('force', force);
            
            const startData = await apiCall('/api/process', { 
                method: 'POST',
                body: formData
            });
            
            if (startData.type === 'validation_warning') {
                btn.disabled = false;
                spinner.classList.add('hidden');
                
                const ul = document.getElementById('validation-missing-columns');
                ul.innerHTML = startData.missing_columns.map(c => `<li>${c}</li>`).join('');
                
                const modal = document.getElementById('validation-warning-modal');
                modal.classList.remove('hidden');
                
                document.getElementById('validation-force-btn').onclick = () => {
                    modal.classList.add('hidden');
                    processAllRules(true);
                };
                
                document.getElementById('validation-cancel-btn').onclick = () => {
                    modal.classList.add('hidden');
                };
                return;
            }'''

    if old_api_call in content:
        content = content.replace(old_api_call, new_api_call)

    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_frontend()
