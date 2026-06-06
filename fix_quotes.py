with open('backend/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\\"\\"\\"', '"""')

with open('backend/database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed syntax')
