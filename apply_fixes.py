import os

file_path = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: parseFloat bug in updatePhase1PreviewTable
old_parsefloat = "const num = parseFloat(displayVal);"
new_parsefloat = "const num = parseFloat(String(displayVal).replace(/,/g, ''));"
content = content.replace(old_parsefloat, new_parsefloat)

# Fix 2: Add try/catch to savePhase1Rule
old_start_save = """            if (saveText) saveText.textContent = 'Processing...';
            

            let fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');"""

new_start_save = """            if (saveText) saveText.textContent = 'Processing...';
            
            try {

            let fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');"""

old_end_save = """                const existingBtn = previewDiv.querySelector('.mt-4.flex');
                if (existingBtn) existingBtn.remove();
                previewDiv.appendChild(downloadBtn);
            }
        }

        // Phase 2: Calculation Rule"""

new_end_save = """                const existingBtn = previewDiv.querySelector('.mt-4.flex');
                if (existingBtn) existingBtn.remove();
                previewDiv.appendChild(downloadBtn);
            }
            } catch (err) {
                console.error("Error in savePhase1Rule:", err);
                const saveBtn = document.getElementById('phase1-save-btn');
                const spinner = document.getElementById('phase1-save-spinner');
                const saveText = document.getElementById('phase1-save-text');
                if (saveBtn) saveBtn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                if (saveText) saveText.textContent = 'Save File Processing';
                showToast(err.message || 'An unexpected error occurred during processing.', 'error');
            }
        }

        // Phase 2: Calculation Rule"""

content = content.replace(old_start_save, new_start_save)
content = content.replace(old_end_save, new_end_save)


# Fix 3: Add try/catch to processAllRules
old_start_process = """            // Start background processing with selected source files
            const formData = new FormData();"""

new_start_process = """            try {
            // Start background processing with selected source files
            const formData = new FormData();"""

old_end_process = """                } else if (statusData.status === 'error') {
                    clearInterval(pollInterval);
                    btn.disabled = false;
                    spinner.classList.add('hidden');
                    showToast(statusData.message || 'Processing failed', 'error');
                }
            }, 2000);
        }
        // ==================== FINAL PROCESSED HISTORY ===================="""

new_end_process = """                } else if (statusData.status === 'error') {
                    clearInterval(pollInterval);
                    btn.disabled = false;
                    spinner.classList.add('hidden');
                    showToast(statusData.message || 'Processing failed', 'error');
                }
            }, 2000);
            } catch (err) {
                console.error("Error starting processing:", err);
                btn.disabled = false;
                spinner.classList.add('hidden');
                showToast(err.message || 'Failed to start processing. Please try again.', 'error');
            }
        }
        // ==================== FINAL PROCESSED HISTORY ===================="""

content = content.replace(old_start_process, new_start_process)
content = content.replace(old_end_process, new_end_process)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("All fixes applied successfully")
