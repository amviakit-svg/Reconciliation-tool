with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()
for i in range(3060, min(len(lines), 3110)):
    print(f'{i+1:4d}: {lines[i]}', end='')