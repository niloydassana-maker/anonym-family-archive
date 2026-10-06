# -*- coding: utf-8 -*-
import re
lines = open(r'D:\anonym\modal_voice_service_isearch.py', encoding='utf-8').readlines()
with open(r'D:\anonym\hi_lines.txt', 'w', encoding='utf-8') as f:
    for i, l in enumerate(lines):
        if re.search(r'[\u0900-\u097F]', l):
            f.write('%d: %r\n' % (i + 1, l[:160]))
print('wrote inventory')
