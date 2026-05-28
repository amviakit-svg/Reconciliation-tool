import os
import re

file_path = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace createdColumns array
content = content.replace(
    "createdColumns = ['Unique_ID', 'Source_File_Name', 'Order ID', ...createdColumns];",
    "createdColumns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount', ...createdColumns];"
)

# 2. Replace availableCols array
content = content.replace(
    "availableCols = ['Unique_ID', 'Source_File_Name', 'Order ID'];",
    "availableCols = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];"
)

# 3. Replace columns array assignments
content = content.replace(
    "columns = ['Unique_ID', 'Source_File_Name', 'Order ID'];",
    "columns = ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount'];"
)

# 4. Replace object property assignments
content = content.replace(
    "columns: ['Unique_ID', 'Source_File_Name', 'Order ID']",
    "columns: ['Unique_ID', 'Source_File_Name', 'Order ID', 'Sales Amount']"
)

# 5. Fix Primary Column Dropdown logic in loadAvailableColumns
pCol_target = """                    const sSelected = rule.primary_column === 'Source_File_Name' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    pCol.innerHTML = '<option value="">Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>`;"""

pCol_replacement = """                    const sSelected = rule.primary_column === 'Source_File_Name' ? 'selected' : '';
                    const salesSelected = rule.primary_column === 'Sales Amount' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    pCol.innerHTML = '<option value="">Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>` +
                        '<option value="Sales Amount"' + (salesSelected ? ' selected' : '') + '>Sales Amount</option>';"""

content = content.replace(pCol_target, pCol_replacement)

# 6. Fix Secondary Column Dropdown logic in loadAvailableColumns
sCol_target = """                    const sSelected = rule.secondary_column === 'Source_File_Name' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    sCol.innerHTML = '<option value="">Match Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>`;"""

sCol_replacement = """                    const sSelected = rule.secondary_column === 'Source_File_Name' ? 'selected' : '';
                    const salesSelected = rule.secondary_column === 'Sales Amount' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    sCol.innerHTML = '<option value="">Match Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>` +
                        '<option value="Sales Amount"' + (salesSelected ? ' selected' : '') + '>Sales Amount</option>';"""

content = content.replace(sCol_target, sCol_replacement)

# 7. Fix Extract Column Dropdown logic in loadAvailableColumns
eCol_target = """                    const sSelected = rule.extract_column === 'Source_File_Name' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    eCol.innerHTML = '<option value="">Extract Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>`;"""

eCol_replacement = """                    const sSelected = rule.extract_column === 'Source_File_Name' ? 'selected' : '';
                    const salesSelected = rule.extract_column === 'Sales Amount' ? 'selected' : '';
                    const label = window.primaryValueColumnName || 'Order ID';
                    eCol.innerHTML = '<option value="">Extract Column</option>' +
                        '<option value="Unique_ID"' + (uSelected ? ' selected' : '') + '>Unique_ID</option>' +
                        '<option value="Source_File_Name"' + (sSelected ? ' selected' : '') + '>Source_File_Name</option>' +
                        '<option value="Order ID"' + (pSelected ? ' selected' : '') + `>${label}</option>` +
                        '<option value="Sales Amount"' + (salesSelected ? ' selected' : '') + '>Sales Amount</option>';"""

content = content.replace(eCol_target, eCol_replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Replacements completed.")
