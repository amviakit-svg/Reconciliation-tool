import os

def patch_index():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    old_getPhase1 = '''                    const p1Config = typeof configRaw === 'string' ? JSON.parse(configRaw) : configRaw;
                    cols.push('Order ID');
                    if (p1Config.fields) {'''
                    
    new_getPhase1 = '''                    const p1Config = typeof configRaw === 'string' ? JSON.parse(configRaw) : configRaw;
                    cols.push('Order ID', 'Sales Amount');
                    if (p1Config.fields) {'''

    if old_getPhase1 in content:
        content = content.replace(old_getPhase1, new_getPhase1)
        print("Patched getPhase1Columns to include Sales Amount")
    
    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_index()
