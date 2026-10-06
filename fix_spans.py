# -*- coding: utf-8 -*-
"""Fix swapped button spans: static=plain Hindi, dynamic=template. Verified."""
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

DEV = r'[\u0900-\u097F]'

# locate the two btn-text spans with Devanagari content
spans = [(m.group(1), m.start(), m.end()) for m in
         re.finditer(r'<span class="btn-text">([^<]*)</span>', src)
         if re.search(DEV, m.group(1))]
if len(spans) != 2:
    raise SystemExit('ABORT spans: %d (want static+dynamic)' % len(spans))
(static_txt, s0, s1), (dyn_txt, d0, d1) = spans[0], spans[1]
print('static span txt len=%d dyn span txt len=%d' % (len(static_txt), len(dyn_txt)), flush=True)
if '${' not in static_txt:
    raise SystemExit('ABORT static span has no template (already fixed?)')
if '${' in dyn_txt:
    raise SystemExit('ABORT dynamic span already templated')
m = re.search(r"\$\{L\('playVoice'\) \|\| \"([^\"]*)\"\}", static_txt)
if not m:
    raise SystemExit('ABORT static template shape')
static_hi = m.group(1)

# 1. static span -> plain Hindi text
src = src[:s0] + '<span class="btn-text">%s</span>' % static_hi + src[s1:]
print('fixed: static span plain', flush=True)

# 2. dynamic span -> template (locate again post-edit)
spans2 = [(m.group(1), m.start(), m.end()) for m in
          re.finditer(r'<span class="btn-text">([^<]*)</span>', src)
          if re.search(DEV, m.group(1))]
dyn = [x for x in spans2 if '${' not in x[0]]
if len(dyn) != 1:
    raise SystemExit('ABORT dynamic span: %d' % len(dyn))
dtxt, t0, t1 = dyn[0]
src = src[:t0] + '<span class="btn-text">${L(\'playVoice\') || "%s"}</span>' % dtxt + src[t1:]
print('fixed: dynamic span template', flush=True)

# 3. static greeting button tag: ensure data-kind/data-txhi with STATIC hindi
old_tag = '<button class="play-btn" id="btn_greeting" onclick="playGreeting()">'
if src.count(old_tag) == 1:
    src = src.replace(old_tag,
        '<button class="play-btn" data-kind="greet" data-txhi="%s" id="btn_greeting" onclick="playGreeting()">' % static_hi, 1)
    print('fixed: static button data attrs', flush=True)
elif 'data-kind="greet"' in src:
    print('static button data attrs already present', flush=True)
else:
    raise SystemExit('ABORT static button tag state unknown')

# 4. dynamic button data-txhi must equal DYNAMIC hindi (currently greet text?)
m = re.search(r'<button class="play-btn" data-kind="play" data-txhi="([^"]*)" id="btn_\$\{turnId\}"', src)
if not m:
    raise SystemExit('ABORT dynamic button tag')
if m.group(1) != dtxt:
    src = src.replace(
        '<button class="play-btn" data-kind="play" data-txhi="%s" id="btn_${turnId}"' % m.group(1),
        '<button class="play-btn" data-kind="play" data-txhi="%s" id="btn_${turnId}"' % dtxt, 1)
    print('fixed: dynamic button txhi', flush=True)
else:
    print('dynamic button txhi already correct', flush=True)

with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('SPANS FIXED')
