# -*- coding: utf-8 -*-
import re
P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()
pat = re.compile(r'data-txhi="\$\{L\(\'playVoice\'\) \|\| "([^"]*)"\}"')
found = pat.findall(src)
if len(found) != 1:
    raise SystemExit('ABORT txhi sites: %d' % len(found))
src = pat.sub(lambda m: 'data-txhi="%s"' % m.group(1), src, count=1)
print('fixed: static button txhi plain', flush=True)
# verify static span 545 is plain (no template)
i = src.find('id="greetText"')
seg = src[src.find('id="bubble_greeting"'):src.find('id="bubble_greeting"') + 1200]
if '${' in seg:
    raise SystemExit('ABORT static bubble still templated')
print('static bubble plain OK', flush=True)
with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('WROTE FIX')
