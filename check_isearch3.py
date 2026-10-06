with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

with open(r'D:\anonym\debug_out.txt', 'w', encoding='utf-8') as f:
    f.write(repr(c[3300:3370]))