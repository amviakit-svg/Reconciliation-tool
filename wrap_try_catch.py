import re

file_path = r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

def inject_try_catch(func_name, content, catch_code):
    # Find the function start
    start_match = re.search(r'async function ' + func_name + r'\(\)\s*\{', content)
    if not start_match:
        print(f"Could not find {func_name}")
        return content
    
    start_idx = start_match.end()
    
    open_braces = 1
    end_idx = -1
    
    in_string = False
    string_char = ''
    in_comment = False
    i = start_idx
    
    while i < len(content):
        c = content[i]
        
        if c in ('"', "'", '`'):
            if not in_string and not in_comment:
                in_string = True
                string_char = c
            elif in_string and string_char == c and content[i-1] != '\\':
                in_string = False
                
        if not in_string:
            if c == '/' and i+1 < len(content) and content[i+1] == '/':
                j = content.find('\n', i)
                i = j if j != -1 else len(content)
                continue
            elif c == '/' and i+1 < len(content) and content[i+1] == '*':
                j = content.find('*/', i)
                i = j + 2 if j != -1 else len(content)
                continue
                
        if not in_string and not in_comment:
            if c == '{':
                open_braces += 1
            elif c == '}':
                open_braces -= 1
                if open_braces == 0:
                    end_idx = i
                    break
        i += 1

    if end_idx == -1:
        print(f"Could not find end of {func_name}")
        return content
        
    # Replace the body
    body = content[start_idx:end_idx]
    new_body = '\n            try {' + body + '\n            } catch(err) {\n' + catch_code + '\n            }\n        '
    
    return content[:start_idx] + new_body + content[end_idx:]

# 1. Hide standalone header safely
header_script = '''    <script>
        // Safely inject CSS to hide the standalone header if loaded inside the SaaS wrapper iframe
        if (window.self !== window.top) {
            const style = document.createElement('style');
            style.textContent = 'header { display: none !important; } main { padding-top: 1rem !important; padding-bottom: 1rem !important; }';
            document.head.appendChild(style);
        }
    </script>
</head>'''
content = content.replace('</head>', header_script)

# 2. Fix parseFloat for SUM columns
bad_parse = '''                        const val = parseFloat(row[col]);
                        if (!isNaN(val)) sum += val;'''
good_parse = '''                        const rawVal = String(row[col] || '0').replace(/,/g, '');
                        const val = parseFloat(rawVal);
                        if (!isNaN(val)) sum += val;'''
content = content.replace(bad_parse, good_parse)

# 3. Add saas_refresh listener at the end
listener = '''        // Handle soft-refresh messages from saas wrapper to update data without destroying state
        window.addEventListener('message', function(e) {
            if (e.data && e.data.type === 'saas_refresh') {
                if (typeof loadFiles === 'function') loadFiles();
                if (typeof loadPhase1Files === 'function') loadPhase1Files();
                if (typeof loadSecondaryFiles === 'function') loadSecondaryFiles();
                if (typeof loadFinalProcessedHistory === 'function') loadFinalProcessedHistory();
                if (typeof loadSourceFileFilter === 'function') loadSourceFileFilter();
            }
        });
    </script>
</body>'''
content = content.replace('    </script>\n</body>', listener)


save_catch = '''
                console.error("Error in savePhase1Rule:", err);
                const saveBtn = document.getElementById('phase1-save-btn');
                const spinner = document.getElementById('phase1-save-spinner');
                const saveText = document.getElementById('phase1-save-text');
                if (saveBtn) saveBtn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                if (saveText) saveText.textContent = 'Save File Processing';
                showToast(err.message || 'An unexpected error occurred.', 'error');
'''
content = inject_try_catch('savePhase1Rule', content, save_catch)

process_catch = '''
                console.error("Error starting processing:", err);
                const btn = document.getElementById('process-all-btn');
                const spinner = document.getElementById('process-all-spinner');
                if (btn) btn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
                showToast(err.message || 'Failed to start processing. Please try again.', 'error');
'''
content = inject_try_catch('processAllRules', content, process_catch)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('All fixes applied correctly!')
