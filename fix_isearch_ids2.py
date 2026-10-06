# -*- coding: utf-8 -*-
"""Add missing HTML ids + greeting data attrs. Programmatic, verified."""
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

def rep(pat, repl, name):
    global src
    found = re.findall(pat, src)
    if len(found) != 1:
        raise SystemExit('ABORT %s: matched %d (want 1)' % (name, len(found)))
    src = re.sub(pat, repl, src, count=1)
    print('patched: %s' % name, flush=True)

# heroSub
rep(r'<h1>SugarDoctor AI Clinic</h1>\n( *)<p>',
    r'<h1>SugarDoctor AI Clinic</h1>\n\1<p id="heroSub">', 'heroSub id')
# doctorH2
rep(r'<div class="doctor-info">\n( *)<h2>',
    r'<div class="doctor-info">\n\1<h2 id="doctorH2">', 'doctorH2 id')
# doctorP: <p>AI ... (ASCII prefix anchor)
m = re.search(r'( *)<p>AI ', src)
if not m:
    raise SystemExit('ABORT doctorP anchor')
src = src[:m.start(1)] + m.group(1) + '<p id="doctorP">AI ' + src[m.end():]
print('patched: doctorP id', flush=True)
# voiceTag: Magpie line
lines = src.split('\n')
hit = [i for i, l in enumerate(lines) if '<span class="tag">' in l and 'Magpie Leo' in l]
if len(hit) != 1:
    raise SystemExit('ABORT voiceTag anchor: %d' % len(hit))
lines[hit[0]] = lines[hit[0]].replace('<span class="tag">', '<span class="tag" id="voiceTag">', 1)
src = '\n'.join(lines)
print('patched: voiceTag id', flush=True)
# greetText: <p> right after bubble_greeting div
lines = src.split('\n')
bi = next(i for i, l in enumerate(lines) if 'id="bubble_greeting"' in l)
pj = next(i for i in range(bi, min(bi + 5, len(lines))) if '<p>' in lines[i] and 'id=' not in lines[i])
lines[pj] = lines[pj].replace('<p>', '<p id="greetText">', 1)
src = '\n'.join(lines)
print('patched: greetText id', flush=True)
# greeting button data-kind/data-txhi (txhi extracted from its span)
m = re.search(r'<span class="btn-text">([^<]*)</span>', src)
spans = [(mm.group(1), mm.start()) for mm in re.finditer(r'<span class="btn-text">([^<]*)</span>', src)]
greet_spans = [x for x in spans if re.search(r'[\u0900-\u097F]', x[0])]
if len(greet_spans) != 2:
    raise SystemExit('ABORT greet spans: %d (want static+dynamic)' % len(greet_spans))
# static greeting span is the one nearest after btn_greeting button tag
btag = src.find('id="btn_greeting"')
static_span = min(greet_spans, key=lambda x: abs(x[1] - btag))
hi_greet_btn = static_span[0]
old_tag = '<button class="play-btn" id="btn_greeting" onclick="playGreeting()">'
if src.count(old_tag) != 1:
    raise SystemExit('ABORT greet button tag')
src = src.replace(old_tag,
    '<button class="play-btn" data-kind="greet" data-txhi="%s" id="btn_greeting" onclick="playGreeting()">' % hi_greet_btn, 1)
print('patched: greet button data attrs', flush=True)

with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('IDS ADDED')
