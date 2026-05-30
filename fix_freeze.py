import re

file_path = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_script = """    <script>
        // Synchronously inject CSS to hide the standalone header if loaded inside the SaaS wrapper iframe
        if (window.self !== window.top) {
            document.write('<style>header { display: none !important; } main { padding-top: 1rem !important; padding-bottom: 1rem !important; }</style>');
        }
    </script>"""

new_script = """    <script>
        // Safely inject CSS to hide the standalone header if loaded inside the SaaS wrapper iframe
        if (window.self !== window.top) {
            const style = document.createElement('style');
            style.textContent = 'header { display: none !important; } main { padding-top: 1rem !important; padding-bottom: 1rem !important; }';
            document.head.appendChild(style);
        }
    </script>"""

content = content.replace(old_script, new_script)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced document.write")
