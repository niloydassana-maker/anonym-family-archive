# -*- coding: utf-8 -*-
"""Replace lone-surrogate emoji with real chars; report literal astral escapes."""
import re

for path in (r'D:\anonym\modal_voice_service_isearch.py',
             r'D:\anonym\modal_voice_service.py'):
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    orig_len = len(c)
    # real surrogate pairs -> real chars
    c = c.replace('ÞÙ', '🎙')
    c = c.replace('ÞØ', '🌐')
    c = c.replace('Þ¤', '🎤')
    lone = [hex(ord(ch)) for ch in c if 0xD800 <= ord(ch) <= 0xDFFF]
    literal_astral = re.findall(r'\\u[Dd][89AaBb][0-9A-Fa-f]{2}', c)
    print('%s: lone=%s literal_astral=%s' % (path.split('\\')[-1], lone, sorted(set(literal_astral))))
    if 'isearch' in path:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print('isearch rewritten %d -> %d chars' % (orig_len, len(c)))
print('done')
