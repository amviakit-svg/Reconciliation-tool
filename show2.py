with open('backend/main.py','r',encoding='utf-8') as f:
    lines = f.readlines()
# Show 60 lines starting from 2580
for i in range(2580, min(len(lines), 2700)):
    print(f'{i+1:4d}: {lines[i]}', end='')