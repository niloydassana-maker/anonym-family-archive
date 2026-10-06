# -*- coding: utf-8 -*-
"""Replace real lone-surrogate emoji with real emoji chars. ASCII-safe."""
import re

S1A = chr(0xD83C) + chr(0xDFA9)
S1B = chr(0xD83C) + chr(0xDF10)
S1C = chr(0xD83C) + chr(0xDFA4)
R1A = chr(0x1F399)
R1B = chr(0x1F310)
R1C = chr(0x1F3A4)
BS = chr(92)

for path in (r'D:\anonym\modal_voice_service_isearch.py',
             r'D:\anonym\modal_voice_service.py'):
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    n1a, n1b, n1c = c.count(S1A), c.count(S1B), c.count(S1C)
    c = c.replace(S1A, R1A).replace(S1B, R1B).replace(S1C, R1C)
    lone = [hex(ord(ch)) for ch in c if 0xD800 <= ord(ch) <= 0xDFFF]
    literal = re.findall(BS + BS + 'u[Dd][89AaBb][0-9A-Fa-f]{2}', c)
    tag = path.split(chr(92))[-1]
    print('%s: replaced A=%d B=%d C=%d lone=%s literal_astral=%s' % (
        tag, n1a, n1b, n1c, lone, sorted(set(literal))))
    if 'isearch' in path:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print('isearch rewritten')
print('done')
