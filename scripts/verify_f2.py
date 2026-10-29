with open('D:/anonym/scripts/actions_dispatch.py') as f:
    content = f.read()
if 'prepared.get("base_branch")' in content or "prepared.get('base_branch')" in content:
    print('F2: base_branch from prepared IS used in actions_dispatch.py - CORRECT')
elif 'prepared["base_branch"]' in content or "prepared['base_branch']" in content:
    print('F2: base_branch from prepared IS used in actions_dispatch.py - CORRECT')
else:
    for line in content.split('\n'):
        if 'default_branch = prepared' in line:
            print(f'F2: default_branch is set from: {line.strip()}')
            break
    else:
        print('F2: base_branch from prepared NOT found in actions_dispatch.py')
        if 'default_branch' in content:
            print('  default_branch variable exists in file')
        else:
            print('  default_branch variable NOT found')