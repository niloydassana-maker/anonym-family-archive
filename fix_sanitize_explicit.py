with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = 0
for i, ln in enumerate(lines):
    if 'full_reply = re.sub(r"[' in ln and 'full_reply)' in ln and 'x00-' in ln:
        lines[i] = '                full_reply = re.sub("[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f\\u200b-\\u200f\\ufeff\\ufffd]", "", full_reply)\n'
        fixed += 1

if fixed != 1:
    raise SystemExit('ABORT: matched %d lines, expected 1' % fixed)

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('sanitizer made explicit')
