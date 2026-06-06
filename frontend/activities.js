/* ============================================================================
   ACTIVITY STEPS VIEWER + RENAME COLUMN
   Auto-loaded by wireMasterViewToolbar() and other handlers.
   ============================================================================ */

// -------- Activity rendering & management --------
let __masterActivities = [];

async function loadMasterActivities() {
    const container = document.getElementById('master-activities-list');
    const emptyEl = document.getElementById('master-activities-empty');
    if (!container || !emptyEl) return;
    if (!currentFolderId) {
        container.innerHTML = '';
        emptyEl.classList.remove('hidden');
        return;
    }
    try {
        const data = await apiCall(`/api/master/${currentFolderId}/activities`);
        if (data.success) {
            __masterActivities = data.activities || [];
            renderMasterActivities();
        } else {
            container.innerHTML = '';
            emptyEl.classList.remove('hidden');
        }
    } catch (e) {
        console.warn('loadMasterActivities failed:', e);
        container.innerHTML = '';
        emptyEl.classList.remove('hidden');
    }
}

function renderMasterActivities() {
    const container = document.getElementById('master-activities-list');
    const emptyEl = document.getElementById('master-activities-empty');
    if (!container || !emptyEl) return;

    if (!__masterActivities || __masterActivities.length === 0) {
        container.innerHTML = '';
        container.classList.add('hidden');
        emptyEl.classList.remove('hidden');
        return;
    }
    container.classList.remove('hidden');
    emptyEl.classList.add('hidden');

    const iconFor = (t) => {
        switch (t) {
            case 'FORMULA_ADD':
            case 'FORMULA_UPDATE':
                return { color: 'purple', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h3M13 17h.01M9 13h.01M13 13h.01M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>' };
            case 'FIND_REPLACE':
                return { color: 'amber', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>' };
            case 'COLUMN_RENAME':
                return { color: 'blue', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>' };
            case 'COLUMN_DELETE':
                return { color: 'red', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>' };
            default:
                return { color: 'gray', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>' };
        }
    };

    const badgeFor = (t) => {
        const map = {
            FORMULA_ADD: ['Formula', 'bg-purple-100 text-purple-800'],
            FORMULA_UPDATE: ['Formula', 'bg-purple-100 text-purple-800'],
            FIND_REPLACE: ['Find & Replace', 'bg-amber-100 text-amber-800'],
            COLUMN_RENAME: ['Rename', 'bg-blue-100 text-blue-800'],
            COLUMN_DELETE: ['Delete Column', 'bg-red-100 text-red-800']
        };
        const m = map[t] || [t, 'bg-gray-100 text-gray-800'];
        return m;
    };

    // Build a human-readable display name for the activity (e.g. "Expense column added",
    // "Find & Replace: Pvt Ltd → Private Limited")
    function buildActivityDisplayName(a) {
        const t = a.target_column || '';
        const p = a.payload || {};
        switch (a.activity_type) {
            case 'FORMULA_ADD':
            case 'FORMULA_UPDATE':
                if (t) {
                    const ft = p.formula_type || '';
                    if (ft) return `${t} column added (${ft})`;
                    return `${t} column added`;
                }
                return 'Formula column added';
            case 'FIND_REPLACE': {
                const find = p.find_text || p.find || '';
                const repl = p.replace_text || p.replace || '';
                if (find) return `Find & Replace: "${find}" → "${repl}"`;
                return 'Find & Replace applied';
            }
            case 'COLUMN_RENAME':
                if (p.from && p.to) return `Column renamed: ${p.from} → ${p.to}`;
                return 'Column renamed';
            case 'COLUMN_DELETE':
                if (t) return `Column deleted: ${t}`;
                return 'Column deleted';
            default:
                return a.activity_type;
        }
    }

    const html = __masterActivities.map(a => {
        const [label, colorClass] = badgeFor(a.activity_type);
        const isEnabled = a.is_enabled !== false;
        const status = a.validation_status || 'ok';
        const statusBadge = status === 'broken'
            ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-700">broken</span>'
            : status === 'warn'
                ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-yellow-100 text-yellow-700">warn</span>'
                : '<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-green-700">ok</span>';
        const lastApplied = a.last_applied_at ? new Date(a.last_applied_at).toLocaleString() : 'never';
        const lastErr = a.last_error ? `<div class="text-[10px] text-red-600 mt-1" title="${escapeHtml(a.last_error)}">${escapeHtml(a.last_error.substring(0, 60))}${a.last_error.length > 60 ? '…' : ''}</div>` : '';
        const displayName = buildActivityDisplayName(a);
        return `
        <div class="activity-row flex items-start space-x-2 p-2 bg-white border border-gray-200 rounded-lg" draggable="true" data-activity-id="${a.id}">
            <div class="flex flex-col items-center pt-1 text-gray-400 cursor-move select-none" title="Drag to reorder">
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><circle cx="7" cy="5" r="1"/><circle cx="7" cy="10" r="1"/><circle cx="7" cy="15" r="1"/><circle cx="13" cy="5" r="1"/><circle cx="13" cy="10" r="1"/><circle cx="13" cy="15" r="1"/></svg>
                <span class="text-[10px] text-gray-500">#${a.step_order}</span>
            </div>
            <label class="inline-flex items-center pt-1 cursor-pointer" title="Enable / disable this step">
                <input type="checkbox" ${isEnabled ? 'checked' : ''} onchange="toggleActivityEnabled(${a.id}, this.checked)" class="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500">
            </label>
            <div class="flex-1 min-w-0">
                <div class="flex items-center space-x-1.5 flex-wrap">
                    <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${colorClass}">${escapeHtml(label)}</span>
                    <span class="text-xs font-medium text-gray-900 truncate" title="${escapeHtml(displayName)}">${escapeHtml(displayName)}</span>
                    ${statusBadge}
                </div>
                <div class="text-[10px] text-gray-500 mt-0.5">Last applied: ${lastApplied}</div>
                ${lastErr}
            </div>
            <div class="flex items-center space-x-1">
                <button onclick="testActivity(${a.id})" class="p-1 text-blue-500 hover:text-blue-700 rounded hover:bg-blue-50" title="Dry-run / test">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                </button>
                <button onclick="deleteActivity(${a.id})" class="p-1 text-red-500 hover:text-red-700 rounded hover:bg-red-50" title="Delete this activity">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></path></svg>
                </button>
            </div>
        </div>`;
    }).join('');

    container.innerHTML = html;
}

async function toggleActivityEnabled(id, enabled) {
    try {
        await apiCall(`/api/master/${currentFolderId}/activities/${id}/toggle`, {
            method: 'POST',
            body: (() => { const f = new FormData(); f.append('enabled', enabled ? '1' : '0'); return f; })()
        });
        showToast(enabled ? 'Activity enabled' : 'Activity disabled', 'success', 1500);
        await loadMasterActivities();
    } catch (e) {
        showToast('Failed to toggle activity: ' + e.message, 'error');
        await loadMasterActivities();
    }
}

async function deleteActivity(id) {
    if (!confirm('Delete this activity? It will no longer be re-applied during auto-sync.')) return;
    try {
        await apiCall(`/api/master/${currentFolderId}/activities/${id}`, { method: 'DELETE' });
        showToast('Activity deleted', 'success');
        await loadMasterActivities();
    } catch (e) {
        showToast('Delete failed: ' + e.message, 'error');
    }
}

async function testActivity(id) {
    showToast('Running dry-run test…', 'info');
    try {
        const data = await apiCall(`/api/master/${currentFolderId}/activities/${id}/test`, { method: 'POST' });
        if (data.success) {
            showToast(`✓ Test passed`, 'success');
        } else {
            showToast(`Test failed: ${data.message || data.error || 'unknown error'}`, 'error', data.suggestion || null);
        }
        await loadMasterActivities();
    } catch (e) {
        showToast('Test failed: ' + e.message, 'error');
    }
}

async function reorderActivity(activityId, newIndex) {
    try {
        await apiCall(`/api/master/${currentFolderId}/activities/reorder`, {
            method: 'POST',
            body: (() => { const f = new FormData(); f.append('ordered_ids', JSON.stringify(__masterActivities.map(a => a.id))); return f; })()
        });
    } catch (e) {
        showToast('Reorder failed: ' + e.message, 'error');
    }
}

// -------- Rename column --------
function renameMasterColumn(columnName) {
    if (!currentFolderId) {
        showToast('Please select a folder first', 'warning');
        return;
    }
    const newName = prompt(`Rename column "${columnName}" to:`, columnName);
    if (!newName || !newName.trim()) return;
    if (newName.trim() === columnName) {
        showToast('No change', 'info');
        return;
    }
    const formData = new FormData();
    formData.append('new_name', newName.trim());
    apiCall(`/api/master/${currentFolderId}/columns/${encodeURIComponent(columnName)}`, {
        method: 'PATCH', body: formData
    }).then(async (data) => {
        if (data.success) {
            showToast(`Column renamed to '${newName.trim()}' and saved as activity`, 'success');
            await Promise.all([loadMasterPreview(), loadMasterStats(), loadMasterSummary()]);
            await loadMasterActivities();
        } else {
            showToast(data.message || data.detail || 'Rename failed', 'error');
        }
    }).catch(e => showToast('Rename failed: ' + e.message, 'error'));
}

// -------- Wrap the existing apply handlers to capture activity IDs in the toast --------
function showAutoCaptureToast(originalMessage, json) {
    try {
        if (json && json.activity_id) {
            showToast(`${originalMessage} · Activity #${json.activity_id} saved`, 'success', 4000);
        } else {
            showToast(originalMessage, 'success');
        }
    } catch (e) {
        showToast(originalMessage, 'success');
    }
}