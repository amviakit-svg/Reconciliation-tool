
with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

js_append = '''
        // --- AUTO SYNC LOGIC ---
        let syncPollInterval = null;

        async function triggerManualSync() {
            if (!currentFolderId) return;
            showToast("Starting manual sync...", "info");
            const res = await apiCall(`/api/folders/${currentFolderId}/sync`, { method: 'POST' });
            if (res.success) {
                // Ensure files visually transition to processing immediately
                allFiles.forEach(f => {
                    if (f.sync_status === 'pending' || f.sync_status === 'rejected') {
                        f.sync_status = 'in_processing';
                    }
                });
                renderFileList(allFiles);
                startSyncPolling();
            }
        }

        function startSyncPolling() {
            if (syncPollInterval) return;
            syncPollInterval = setInterval(pollSyncStatus, 2000);
        }

        function stopSyncPolling() {
            if (syncPollInterval) {
                clearInterval(syncPollInterval);
                syncPollInterval = null;
            }
        }

        async function pollSyncStatus() {
            if (!currentFolderId) {
                stopSyncPolling();
                return;
            }
            const res = await apiCall(`/api/folders/${currentFolderId}/sync-status`);
            if (res.success && res.files) {
                let hasProcessing = false;
                let uiNeedsUpdate = false;
                
                res.files.forEach(sf => {
                    const file = allFiles.find(f => f.id === sf.id);
                    if (file) {
                        if (file.sync_status !== sf.sync_status) {
                            uiNeedsUpdate = true;
                            if (file.sync_status === 'in_processing' && sf.sync_status === 'synced') {
                                showToast(`${file.original_name} synced successfully`, 'success');
                            }
                            if (file.sync_status === 'in_processing' && sf.sync_status === 'rejected') {
                                showToast(`${file.original_name} sync rejected`, 'error');
                            }
                            file.sync_status = sf.sync_status;
                            file.sync_error = sf.sync_error;
                        }
                        
                        if (sf.sync_status === 'in_processing') {
                            hasProcessing = true;
                        }
                    }
                });
                
                if (uiNeedsUpdate) {
                    renderFileList(allFiles);
                }
                
                if (!hasProcessing) {
                    stopSyncPolling();
                }
            }
        }
'''

text = text.replace('        async function apiCall(url, options = {}) {', js_append + '\n        async function apiCall(url, options = {}) {')

with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html', 'w', encoding='utf-8') as f:
    f.write(text)
