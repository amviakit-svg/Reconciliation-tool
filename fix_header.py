import re

file_path = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the old script I added
old_script = """    <script>
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
    </script>"""

content = content.replace(old_script, "")

# Add the robust synchronous script right before </head>
robust_script = """    <script>
        // Synchronously inject CSS to hide the standalone header if loaded inside the SaaS wrapper iframe
        if (window.self !== window.top) {
            document.write('<style>header { display: none !important; } main { padding-top: 1rem !important; padding-bottom: 1rem !important; }</style>');
        }
    </script>"""

content = content.replace('</head>', robust_script + '\n</head>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Robust script added")
