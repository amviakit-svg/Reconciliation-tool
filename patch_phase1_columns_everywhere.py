import os

def patch_index():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Define getPhase1Columns and GLOBAL_PHASE1_COLUMNS before loadRuleColumns
    new_getPhase1 = '''        let GLOBAL_PHASE1_COLUMNS = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
        async function getPhase1Columns() {
            let cols = ['Unique_ID', 'Source_File_Name'];
            try {
                const rulesData = await apiCall('/api/rules/1');
                if (rulesData.success && rulesData.rules && rulesData.rules.length > 0) {
                    let configRaw = rulesData.rules[rulesData.rules.length - 1].config;
                    const p1Config = typeof configRaw === 'string' ? JSON.parse(configRaw) : configRaw;
                    cols.push('Order ID');
                    if (p1Config.fields) {
                        p1Config.fields.forEach(f => {
                            if (f.name) cols.push(f.name);
                        });
                    }
                } else {
                    cols.push('Order ID', 'Sales Amount');
                }
            } catch (e) {
                console.error("Error fetching Phase 1 fields:", e);
                cols.push('Order ID', 'Sales Amount');
            }
            GLOBAL_PHASE1_COLUMNS = cols;
            return cols;
        }

        async function loadRuleColumns(selectElement, rowId, type) {'''

    old_getPhase1 = '''        async function loadRuleColumns(selectElement, rowId, type) {'''

    # Ensure we don't insert it twice
    if 'async function getPhase1Columns()' not in content:
        content = content.replace(old_getPhase1, new_getPhase1)
        print("Injected getPhase1Columns()")

    # 2. Update loadRuleColumns to use getPhase1Columns
    old_p2cols_hardcoded = '''            // Handle primary data files
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
            }'''

    new_p2cols_dynamic = '''            // Handle primary data files
            if (fileId.startsWith('primary_')) {
                if (colSelect) {
                    const label = window.primaryValueColumnName || 'Order ID';
                    const p1Cols = await getPhase1Columns();
                    colSelect.innerHTML = '<option value="">Column</option>';
                    p1Cols.forEach(col => {
                        const dispLabel = col === 'Order ID' ? label : col;
                        colSelect.innerHTML += `<option value="${col}">${dispLabel}</option>`;
                    });
                }
                return;
            }'''

    if old_p2cols_hardcoded in content:
        content = content.replace(old_p2cols_hardcoded, new_p2cols_dynamic)
        print("Updated loadRuleColumns to use dynamic columns")

    # 3. Update getPhase2Columns to use GLOBAL_PHASE1_COLUMNS
    old_getPhase2 = '''        function getPhase2Columns() {
            const columns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];'''

    new_getPhase2 = '''        function getPhase2Columns() {
            const columns = [...GLOBAL_PHASE1_COLUMNS];'''

    if old_getPhase2 in content:
        content = content.replace(old_getPhase2, new_getPhase2)
        print("Updated getPhase2Columns to use GLOBAL_PHASE1_COLUMNS")

    # 4. Update loadAvailableColumnsForSummary (Phase 4)
    old_phase4_cols = '''            let columns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
            
            // Get columns from Phase 2 rules'''

    new_phase4_cols = '''            await getPhase1Columns();
            let columns = [...GLOBAL_PHASE1_COLUMNS];
            
            // Get columns from Phase 2 rules'''

    if old_phase4_cols in content:
        content = content.replace(old_phase4_cols, new_phase4_cols)
        print("Updated Phase 4 to use dynamic columns")

    # 5. Make sure Phase 2 UI loader fetches Phase 1 first
    old_loadPhase2 = '''        async function loadSavedPhase2() {
            const data = await apiCall('/api/rules/2');'''
    
    new_loadPhase2 = '''        async function loadSavedPhase2() {
            await getPhase1Columns(); // Ensure global phase 1 columns are loaded for UI
            const data = await apiCall('/api/rules/2');'''

    if old_loadPhase2 in content:
        content = content.replace(old_loadPhase2, new_loadPhase2)
        print("Updated loadSavedPhase2")
    
    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_index()
