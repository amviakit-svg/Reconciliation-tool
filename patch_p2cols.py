import os

def patch_index():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    new_getPhase1 = '''        let GLOBAL_PHASE1_COLUMNS = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];
        async function getPhase1Columns() {
            let cols = ['Unique_ID', 'Source_File_Name'];
            try {
                const rulesData = await apiCall('/api/rules/1');
                if (rulesData.success && rulesData.rules && rulesData.rules.length > 0) {
                    const p1Config = JSON.parse(rulesData.rules[0].config);
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
                cols.push('Order ID', 'Sales Amount');
            }
            GLOBAL_PHASE1_COLUMNS = cols;
            return cols;
        }

        async function loadRuleColumns(selectElement, rowId, type) {'''

    old_getPhase1 = '''        async function getPhase1Columns() {
            let cols = ['Unique_ID', 'Source_File_Name'];
            try {
                const rulesData = await apiCall('/api/rules/1');
                if (rulesData.success && rulesData.rules && rulesData.rules.length > 0) {
                    const p1Config = JSON.parse(rulesData.rules[0].config);
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
                cols.push('Order ID', 'Sales Amount');
            }
            return cols;
        }

        async function loadRuleColumns(selectElement, rowId, type) {'''

    if old_getPhase1 in content:
        content = content.replace(old_getPhase1, new_getPhase1)
        print("Patched getPhase1Columns")
    else:
        print("Could not find getPhase1Columns")

    old_p2cols = '''        function getPhase2Columns() {
            const columns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];'''

    new_p2cols = '''        function getPhase2Columns() {
            const columns = [...GLOBAL_PHASE1_COLUMNS];'''

    if old_p2cols in content:
        content = content.replace(old_p2cols, new_p2cols)
        print("Patched getPhase2Columns")
    else:
        print("Could not find getPhase2Columns")

    # We also need to ensure GLOBAL_PHASE1_COLUMNS is loaded before loadSavedPhase3 is called.
    # Where does the rules page initialize?
    # Usually in loadPhase2Rules() or similar.
    # We can just call getPhase1Columns() at the very start of loadSavedPhase2()!

    old_loadPhase2 = '''        async function loadSavedPhase2() {
            const data = await apiCall('/api/rules/2');'''
    
    new_loadPhase2 = '''        async function loadSavedPhase2() {
            await getPhase1Columns(); // Ensure global phase 1 columns are loaded for UI
            const data = await apiCall('/api/rules/2');'''

    if old_loadPhase2 in content:
        content = content.replace(old_loadPhase2, new_loadPhase2)
        print("Patched loadSavedPhase2")
    else:
        print("Could not find loadSavedPhase2")

    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_index()
