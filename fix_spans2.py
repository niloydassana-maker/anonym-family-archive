# -*- coding: utf-8 -*-
"""Fix swapped spans. Offset-safe: apply end-to-start. Single write."""
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

DEV = r'[\u0900-\u097F]'
spans = [(m.group(1), m.start(), m.end()) for m in
         re.finditer(r'<span class="btn-text">([^<]*)</span>', src)
         if re.search(DEV, m.group(1))]
if len(spans) != 2:
    raise SystemExit('ABORT spans: %d' % len(spans))
(static_txt, s0, s1), (dyn_txt, d0, d1) = spans[0], spans[1]
if '${' not in static_txt or '${' in dyn_txt:
    raise SystemExit('ABORT unexpected span shapes')
m = re.search(r"\$\{L\('playVoice'\) \|\| \"([^\"]*)\"\}", static_txt)
if not m:
    raise SystemExit('ABORT static template shape')
static_hi = m.group(1)

edits = []
# dynamic span (later offset): wrap with template
edits.append((d0, d1, '<span class="btn-text">${L(\'playVoice\') || "%s"}</span>' % dyn_txt))
# static span (earlier offset): plain Hindi
edits.append((s0, s1, '<span class="btn-text">%s</span>' % static_hi))

# static greeting button tag: add data-kind/data-txhi
old_tag = '<button class="play-btn" id="btn_greeting" onclick="playGreeting()">'
if src.count(old_tag) == 1:
    i = src.find(old_tag)
    edits.append((i, i + len(old_tag),
        '<button class="play-btn" data-kind="greet" data-txhi="%s" id="btn_greeting" onclick="playGreeting()">' % static_hi))
elif 'data-kind="greet"' not in src:
    raise SystemExit('ABORT static button tag state unknown')
else:
    print('note: static button data attrs already present', flush=True)

# dynamic button data-txhi must equal DYNAMIC hindi
m2 = re.search(r'<button class="play-btn" data-kind="play" data-txhi="([^"]*)" id="btn_\$\{turnId\}"', src)
if not m2:
    raise SystemExit('ABORT dynamic button tag')
if m2.group(1) != dyn_txt:
    i, j = m2.start(1), m2.end(1)
    edits.append((i, j, dyn_txt))
    print('note: dynamic txhi corrected', flush=True)
else:
    print('note: dynamic txhi already correct', flush=True)

for a, b, rep in sorted(edits, reverse=True):
    src = src[:a] + rep + src[b:]

with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('SPANS FIXED (%d edits)' % len(edits))
