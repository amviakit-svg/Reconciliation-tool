
with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\saas.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = "iframe.src = targetSrc + '?v=' + new Date().getTime();"
replacement = "iframe.src = targetSrc;"

text = text.replace(target, replacement)

with open(r'c:\Users\Nikhil Kumar\.gemini\antigravity\scratch\Reconciliation tool\frontend\saas.html', 'w', encoding='utf-8') as f:
    f.write(text)
