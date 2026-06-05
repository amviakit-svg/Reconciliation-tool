import os

def inject_getPhase1Columns():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    new_func = '''        async function getPhase1Columns() {
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

        async function updateColumnDropdown(rowId, type) {'''

    old_target = "        async function updateColumnDropdown(rowId, type) {"
    
    if old_target in content:
        content = content.replace(old_target, new_func)
        with open('frontend/index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Injected getPhase1Columns successfully!")
    else:
        print("Could not find updateColumnDropdown to inject.")

if __name__ == '__main__':
    inject_getPhase1Columns()
