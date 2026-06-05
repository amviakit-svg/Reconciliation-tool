with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()
# Show 30 lines starting from 2738
for i in range(2735, min(len(lines), 2780)):
    print(f'{i+1:4d}: {lines[i]}', end='')