import re
import sys

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update getAllUsedOutputColumns
    old_get_all = '''        /**
         * Get all currently used output columns from Phase 2 and Phase 3
         */
        function getAllUsedOutputColumns() {
            const used = [];
            
            // Phase 2 rules
            document.querySelectorAll('#matching-rules-body .rule-output-column').forEach(input => {
                const val = input.value?.trim();
                if (val) used.push(val);
            });
            
            // Phase 3 remark groups
            document.querySelectorAll('.group-output-col').forEach(input => {
                const val = input.value?.trim();
                if (val) used.push(val);
            });
            
            return used;
        }'''
        
    new_get_all = '''        /**
         * Get all currently used output columns from Phase 1, Phase 2, and Phase 3
         */
        function getAllUsedOutputColumns() {
            const used = [];
            
            document.querySelectorAll('.field-output-col').forEach(input => {
                const val = input.value?.trim();
                if (val) used.push(val);
            });
            
            document.querySelectorAll('.rule-output-column').forEach(input => {
                const val = input.value?.trim();
                if (val) used.push(val);
            });
            
            document.querySelectorAll('.group-output-col').forEach(input => {
                const val = input.value?.trim();
                if (val) used.push(val);
            });
            
            return [...new Set(used)];
        }'''

    if old_get_all in content:
        content = content.replace(old_get_all, new_get_all)
    else:
        print("Failed to replace getAllUsedOutputColumns")

    # 2. Update resequenceOutputColumns
    old_reseq = '''        function resequenceOutputColumns() {
            // Collect all output column elements with their current values
            const phase2Elements = [];
            document.querySelectorAll('#matching-rules-body .rule-output-column').forEach(el => {
                if (el.value?.trim()) {
                    phase2Elements.push({ element: el, oldValue: el.value.trim() });
                }
            });
            
            const phase3Elements = [];
            document.querySelectorAll('.group-output-col').forEach(el => {
                if (el.value?.trim()) {
                    phase3Elements.push({ element: el, oldValue: el.value.trim() });
                }
            });
            
            // Combine and sort by current column letter
            const allElements = [...phase2Elements, ...phase3Elements];
            allElements.sort((a, b) => columnLetterToNumber(a.oldValue) - columnLetterToNumber(b.oldValue));
            
            // Reassign sequentially starting from D (column 4) to reserve A, B, C for primary data
            const MIN_COLUMN_NUMBER = 4; // D
            allElements.forEach((item, index) => {
                const newLetter = numberToColumnLetter(index + MIN_COLUMN_NUMBER);
                if (item.oldValue !== newLetter) {
                    item.element.value = newLetter;
                    // Trigger change event to update any dependent UI
                    item.element.dispatchEvent(new Event('change'));
                }
            });
            
            // Update all dropdowns to reflect new used columns
            refreshAllColumnDropdowns();
        }'''

    new_reseq = '''        function resequenceOutputColumns() {
            // Collect all output column elements with their current values
            const allElements = [];
            
            document.querySelectorAll('.field-output-col').forEach(el => {
                if (el.value?.trim()) allElements.push({ element: el, oldValue: el.value.trim() });
            });
            
            document.querySelectorAll('.rule-output-column').forEach(el => {
                if (el.value?.trim()) allElements.push({ element: el, oldValue: el.value.trim() });
            });
            
            document.querySelectorAll('.group-output-col').forEach(el => {
                if (el.value?.trim()) allElements.push({ element: el, oldValue: el.value.trim() });
            });
            
            // Combine and sort by current column letter
            allElements.sort((a, b) => columnLetterToNumber(a.oldValue) - columnLetterToNumber(b.oldValue));
            
            // Reassign sequentially starting from D (column 4) to reserve A, B, C for primary data
            const MIN_COLUMN_NUMBER = 4; // D
            allElements.forEach((item, index) => {
                const newLetter = numberToColumnLetter(index + MIN_COLUMN_NUMBER);
                if (item.oldValue !== newLetter) {
                    item.element.value = newLetter;
                    // Trigger change event to update any dependent UI
                    item.element.dispatchEvent(new Event('change'));
                }
            });
            
            // Update all dropdowns to reflect new used columns
            refreshAllColumnDropdowns();
        }'''

    if old_reseq in content:
        content = content.replace(old_reseq, new_reseq)
    else:
        print("Failed to replace resequenceOutputColumns")

    # 3. Update refreshAllColumnDropdowns
    old_refresh = '''        function refreshAllColumnDropdowns() {
            const used = getAllUsedOutputColumns();
            
            // Update Phase 2 dropdowns
            document.querySelectorAll('#matching-rules-body .rule-output-column').forEach(select => {
                const currentValue = select.value;
                select.innerHTML = generateColumnLetterOptions(currentValue, used);
            });
            
            // Update Phase 3 dropdowns
            document.querySelectorAll('.group-output-col').forEach(select => {
                const currentValue = select.value;
                select.innerHTML = generateColumnLetterOptions(currentValue, used);
            });
        }'''

    new_refresh = '''        function refreshAllColumnDropdowns() {
            const used = getAllUsedOutputColumns();
            
            document.querySelectorAll('.field-output-col').forEach(select => {
                const currentValue = select.value;
                select.innerHTML = generateColumnLetterOptions(currentValue, used);
            });
            
            document.querySelectorAll('.rule-output-column').forEach(select => {
                const currentValue = select.value;
                select.innerHTML = generateColumnLetterOptions(currentValue, used);
            });
            
            document.querySelectorAll('.group-output-col').forEach(select => {
                const currentValue = select.value;
                select.innerHTML = generateColumnLetterOptions(currentValue, used);
            });
        }'''

    if old_refresh in content:
        content = content.replace(old_refresh, new_refresh)
    else:
        print("Failed to replace refreshAllColumnDropdowns")

    # 4. Global replacements for refreshPhase1FieldColumnDropdowns
    content = content.replace("refreshPhase1FieldColumnDropdowns()", "refreshAllColumnDropdowns()")

    # 5. deletePhase1Field using resequenceOutputColumns
    old_delete = '''        function deletePhase1Field(fieldId) {
            const row = document.getElementById(fieldId);
            if (row) row.remove();
            updatePhase1FieldsEmptyMsg();
            refreshAllColumnDropdowns();
            triggerPhase1PreviewRefresh();
        }'''
    
    new_delete = '''        function deletePhase1Field(fieldId) {
            const row = document.getElementById(fieldId);
            if (row) row.remove();
            updatePhase1FieldsEmptyMsg();
            resequenceOutputColumns();
            triggerPhase1PreviewRefresh();
        }'''

    if old_delete in content:
        content = content.replace(old_delete, new_delete)
    else:
        print("Failed to replace deletePhase1Field")

    # Write changes
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        print("Patched index.html with global column sequence logic")

patch_file()
