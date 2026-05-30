import re

file_path = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

listener_code = """
        // Handle soft-refresh messages from saas wrapper to update data without destroying state
        window.addEventListener('message', function(e) {
            if (e.data && e.data.type === 'saas_refresh') {
                if (typeof loadFiles === 'function') loadFiles();
                if (typeof loadPhase1Files === 'function') loadPhase1Files();
                if (typeof loadSecondaryFiles === 'function') loadSecondaryFiles();
                if (typeof loadFinalProcessedHistory === 'function') loadFinalProcessedHistory();
                if (typeof loadSourceFileFilter === 'function') loadSourceFileFilter();
            }
        });
"""

# Insert it before the last script tag closure
idx = content.rfind('</script>')
if idx != -1:
    content = content[:idx] + listener_code + '\n    </script>' + content[idx+9:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Listener added successfully.")
else:
    print("Could not find </script>")
