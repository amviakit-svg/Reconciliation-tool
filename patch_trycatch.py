import os

file_path = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_start = """            if (saveText) saveText.textContent = 'Processing...';
            

            let fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');"""

new_start = """            if (saveText) saveText.textContent = 'Processing...';
            
            try {

            let fileId = String(document.getElementById('phase1-file').value || sessionStorage.getItem('phase1_file_cache') || '');"""

old_end = """                const existingBtn = previewDiv.querySelector('.mt-4.flex');
                if (existingBtn) existingBtn.remove();
                previewDiv.appendChild(downloadBtn);
            }
        }

        // Phase 2: Calculation Rule"""

new_end = """                const existingBtn = previewDiv.querySelector('.mt-4.flex');
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

content = content.replace(old_start, new_start)
content = content.replace(old_end, new_end)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied")
