import re

file_path = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The script to detect iframe and hide the header.
iframe_script = """
    <script>
        // If loaded inside the SaaS iframe, hide the standalone tool's header and adjust layout
        document.addEventListener('DOMContentLoaded', () => {
            if (window.self !== window.top) {
                const header = document.querySelector('header');
                if (header) {
                    header.style.display = 'none';
                }
                const main = document.querySelector('main');
                if (main) {
                    main.classList.remove('py-8');
                    main.classList.add('py-4');
                }
            }
        });
    </script>
</head>"""

content = content.replace('</head>', iframe_script)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Iframe header hiding patch applied successfully.")
