import os
path = 'frontend/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find getAutoAssignedColumn function
start = content.find('function getAutoAssignedColumn()')
print('Start:', start)

# Find the matching closing brace
brace_count = 0
found_first = False
end = start
for i in range(start, len(content)):
    if content[i] == '{':
        brace_count += 1
        found_first = True
    elif content[i] == '}' and found_first:
        brace_count -= 1
        if brace_count == 0:
            end = i + 1
            break

snippet = content[start:end]
print('Length:', len(snippet))
print(snippet)
print('---')
print('Line count in snippet:', snippet.count('\n'))

# Also find getNextAvailableColumn
start2 = content.find('function getNextAvailableColumn()')
print('\ngetNextAvailableColumn start:', start2)
if start2 >= 0:
    brace_count = 0
    found_first = False
    end2 = start2
    for i in range(start2, len(content)):
        if content[i] == '{':
            brace_count += 1
            found_first = True
        elif content[i] == '}' and found_first:
            brace_count -= 1
            if brace_count == 0:
                end2 = i + 1
                break
    print(content[start2:end2])