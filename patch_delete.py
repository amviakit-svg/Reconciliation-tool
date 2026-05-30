import sys

def patch_file():
    filepath = r"c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    old_del = '''                if (currentSelectedFY && currentSelectedType && currentSelectedMonth) {
                    await loadProcessedFiles(currentSelectedFY, currentSelectedType, currentSelectedMonth);
                }'''
    new_del = '''                if (currentSelectedFY && currentSelectedMonth) {
                    await loadProcessedFiles(currentSelectedFY, currentSelectedMonth);
                }'''
    
    if old_del in content:
        content = content.replace(old_del, new_del)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched index.html")
    else:
        print("Failed to replace chunk for deleteProcessFile")

patch_file()
