import sys
import os

filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Patch addPhase1Field
target1 = """            // Refresh preview if there are fields
            triggerPhase1PreviewRefresh();
            
            return fieldId;
        }"""
repl1 = """            // Refresh preview if there are fields
            triggerPhase1PreviewRefresh();
            resequenceOutputColumns();
            
            return fieldId;
        }"""
if target1 in content:
    content = content.replace(target1, repl1)
    print("Patched addPhase1Field")
else:
    print("Failed to patch addPhase1Field")

# 2. Patch loadRulePageData
target2 = """                updateProgress('Loading Phase 4...');
                await loadSavedPhase4();
                
                updateProgress('Complete!');
                isRulesPageLoaded = true; // Mark as loaded"""
repl2 = """                updateProgress('Loading Phase 4...');
                await loadSavedPhase4();
                
                resequenceOutputColumns();
                
                updateProgress('Complete!');
                isRulesPageLoaded = true; // Mark as loaded"""
if target2 in content:
    content = content.replace(target2, repl2)
    print("Patched loadRulePageData")
else:
    print("Failed to patch loadRulePageData")

# 3. Patch addCalculationRuleRow
target3 = """            `;
            
            tbody.appendChild(tr);
            if (!savedData) {
                showToast('Calculation rule added. Add multiple columns to sum.', 'info');
            }
        }"""
repl3 = """            `;
            
            tbody.appendChild(tr);
            if (!savedData) {
                showToast('Calculation rule added. Add multiple columns to sum.', 'info');
            }
            resequenceOutputColumns();
        }"""
if target3 in content:
    content = content.replace(target3, repl3)
    print("Patched addCalculationRuleRow")
else:
    print("Failed to patch addCalculationRuleRow")

# 4. Patch addMatchingRuleRow
target4 = """            `;
            
            tbody.appendChild(tr);
            
            // Populate file dropdowns
            populateRuleFileDropdowns(rowId);
        }"""
repl4 = """            `;
            
            tbody.appendChild(tr);
            
            // Populate file dropdowns
            populateRuleFileDropdowns(rowId);
            resequenceOutputColumns();
        }"""
if target4 in content:
    content = content.replace(target4, repl4)
    print("Patched addMatchingRuleRow")
else:
    print("Failed to patch addMatchingRuleRow")

# 5. Patch addRemarksGroup
target5 = """            container.appendChild(groupDiv);
            showToast('Remarks group added. Add remark rules with conditions.', 'success');
        }"""
repl5 = """            container.appendChild(groupDiv);
            showToast('Remarks group added. Add remark rules with conditions.', 'success');
            resequenceOutputColumns();
        }"""
if target5 in content:
    content = content.replace(target5, repl5)
    print("Patched addRemarksGroup")
else:
    print("Failed to patch addRemarksGroup")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patching complete.")
