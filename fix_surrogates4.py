# -*- coding: utf-8 -*-
"""Replace literal astral-escape TEXT with real emoji chars."""
import re

BS = chr(92)
P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    c = f.read()

seqs = sorted(set(re.findall(BS + BS + 'uD83C' + BS + BS + 'u[0-9A-Fa-f]{4}', c)))
print('sequences: %s' % seqs)
pairs = {
    'uD83C' + chr(92) + 'uDFA9': chr(0x1F399),
    'uD83C' + chr(92) + 'uDF10': chr(0x1F310),
    'uD83C' + chr(92) + 'uDFA4': chr(0x1F3A4),
}
total = 0
for seq, emoji in pairs.items():
    lit = chr(92) + seq
    n = c.count(lit)
    if n:
        c = c.replace(lit, emoji)
        total += n
        print('replaced %s x%d' % (seq.replace(chr(92), 'BS'), n))
print('total=%d' % total)

with open(P, 'w', encoding='utf-8') as f:
    f.write(c)

# re-scan
lone = [hex(ord(ch)) for ch in c if 0xD800 <= ord(ch) <= 0xDFFF]
import ast
tree = ast.parse(c)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'WEB_DEMO_HTML':
                val = ast.literal_eval(node.value)
                bad = [hex(ord(ch)) for ch in val if 0xD800 <= ord(ch) <= 0xDFFF]
                print('WEB_DEMO_HTML lone: %s' % bad)
                try:
                    val.encode('utf-8')
                    print('utf8 encode OK')
                except Exception as e:
                    print('ENCODE STILL FAILS: %s' % e)
print('done')
