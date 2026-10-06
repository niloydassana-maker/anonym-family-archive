with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, ln in enumerate(lines):
    if 'full_reply = re.sub' in ln:
        with open(r'D:\anonym\line_dump.txt', 'w', encoding='utf-8') as f:
            f.write('line %d: %r\n' % (i + 1, ln))
        break
print('dumped')
