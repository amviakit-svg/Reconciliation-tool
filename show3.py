with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()
for i in range(2710, min(len(lines), 2780)):
    print(f'{i+1:4d}: {lines[i]}', end='')