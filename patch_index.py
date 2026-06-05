import os

def patch_index():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
    old_p2 = """            // Handle primary data files
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
            }"""
            
    new_p2 = """            // Handle primary data files
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
            }"""

    old_p4 = """        async function loadAvailableColumnsForSummary() {
            // Get columns from Phase 1 primary data
            const primaryData = await apiCall('/api/primary/files');
            const rulesData = await apiCall('/api/rules/1');
            
            let columns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];"""

    new_p4 = """        async function loadAvailableColumnsForSummary() {
            const p1Cols = await getPhase1Columns();
            let columns = [...p1Cols];"""

    if old_p2 in content:
        content = content.replace(old_p2, new_p2)
        print("Replaced Phase 2 columns")
    else:
        print("Could not find Phase 2 columns block")
        
    if old_p4 in content:
        content = content.replace(old_p4, new_p4)
        print("Replaced Phase 4 columns")
    else:
        print("Could not find Phase 4 columns block")

    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_index()
