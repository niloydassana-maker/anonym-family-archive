# -*- coding: utf-8 -*-
"""EN-mode i18n PART B: wrap call sites. Hindi extracted, never retyped."""
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

DEV = r'[\u0900-\u097F]'

def rep(pat, repl, name):
    global src
    found = re.findall(pat, src)
    if len(found) != 1:
        raise SystemExit('ABORT %s: matched %d (want 1)' % (name, len(found)))
    src = re.sub(pat, repl, src, count=1)
    print('patched: %s' % name, flush=True)

# ---- 7x appendMessage("HINDI", 'ai') in file order ----
pat7 = re.compile(r'appendMessage\("([^"]*)", \'ai\'\)')
ms = [(m.group(1), m.start()) for m in pat7.finditer(src)]
ms = [x for x in ms if re.search(DEV, x[0])]
if len(ms) != 7:
    raise SystemExit('ABORT dq appends: %d (want 7)' % len(ms))
keys7 = ['errMicStart', 'errMicRecord', 'errSend', 'errMicAgain', 'errNoAudio', 'errNoReply', 'errServer']
for (hi, _), key in zip(ms, keys7):
    old = 'appendMessage("%s", \'ai\')' % hi
    new = 'appendMessage(L(%s) || "%s", \'ai\')' % ("'" + key + "'", hi)
    if src.count(old) != 1:
        raise SystemExit('ABORT dq site %s' % key)
    src = src.replace(old, new, 1)
    print('patched: dq %s' % key, flush=True)

# ---- recording placeholder (line ~741) ----
m = re.search(r'document\.getElementById\(\'userInput\'\)\.placeholder = "([^"]*)";', src)
if not m or not re.search(DEV, m.group(1)):
    raise SystemExit('ABORT phListen')
src = src.replace(
    'document.getElementById(\'userInput\').placeholder = "%s";' % m.group(1),
    'document.getElementById(\'userInput\').placeholder = L(\'phListen\') || "%s";' % m.group(1), 1)
print('patched: phListen', flush=True)

# ---- trailer default ----
m = re.search(r'parsed\.trailer\.reply \|\| "([^"]*)"', src)
if not m or not re.search(DEV, m.group(1)):
    raise SystemExit('ABORT trailer default')
src = src.replace(
    'parsed.trailer.reply || "%s"' % m.group(1),
    'parsed.trailer.reply || (L(\'defaultReply\') || "%s")' % m.group(1), 1)
print('patched: defaultReply', flush=True)

# ---- dynamic play button: data-kind/data-txhi + label span ----
m = re.search(r'<span class="btn-text">([^<]*)</span>', src)
if not m or not re.search(DEV, m.group(1)):
    raise SystemExit('ABORT play span')
hi_play = m.group(1)
src = src.replace(
    '<span class="btn-text">%s</span>' % hi_play,
    '<span class="btn-text">${L(\'playVoice\') || "%s"}</span>' % hi_play, 1)
print('patched: play span', flush=True)
m2 = re.search(r'<button class="play-btn" id="btn_\$\{turnId\}" onclick="playTurnAudio\(\'\$\{turnId\}\'\)">', src)
if not m2:
    raise SystemExit('ABORT play button tag')
src = src.replace(
    '<button class="play-btn" id="btn_${turnId}"',
    '<button class="play-btn" data-kind="play" data-txhi="%s" id="btn_${turnId}"' % hi_play, 1)
print('patched: play button data attrs', flush=True)

# ---- thinking span ----
m = re.search(r'<span style="font-size:0\.85rem; color:#9CA3AF;">([^<]*)</span>', src)
if not m or not re.search(DEV, m.group(1)):
    raise SystemExit('ABORT thinking span')
src = src.replace(
    '<span style="font-size:0.85rem; color:#9CA3AF;">%s</span>' % m.group(1),
    '<span style="font-size:0.85rem; color:#9CA3AF;">${L(\'thinkText\') || "%s"}</span>' % m.group(1), 1)
print('patched: thinking', flush=True)

# ---- single-quote labels (order-verified) ----
pat_sq = re.compile(r"label\.innerText = '([^']*)';")
ms = [(m.group(1), m.start()) for m in pat_sq.finditer(src)]
ms = [x for x in ms if re.search(DEV, x[0])]
if len(ms) != 4:
    raise SystemExit('ABORT sq labels: %d (want 4)' % len(ms))
keys_sq = ['stopBtn', 'playVoice', 'greetLoading', 'greetBtn']
for (hi, _), key in zip(ms, keys_sq):
    old = "label.innerText = '%s';" % hi
    new = "label.innerText = L('%s') || '%s';" % (key, hi)
    if src.count(old) != 1:
        raise SystemExit('ABORT sq site %s' % key)
    src = src.replace(old, new, 1)
    print('patched: sq %s' % key, flush=True)

# ---- playGreeting: send current lang (line-anchored) ----
lines = src.split('\n')
hi2 = [i for i, l in enumerate(lines) if "text: 'hello'," in l]
if len(hi2) != 1:
    raise SystemExit('ABORT greeting anchor: %d' % len(hi2))
lines.insert(hi2[0] + 1, "                        lang: (currentLang === 'hi-IN' ? 'hi' : 'en'),")
src = '\n'.join(lines)
print('patched: greeting lang', flush=True)

# ---- 849 wart clean (line-anchored) ----
lines = src.split('\n')
hw = [i for i, l in enumerate(lines) if 'trailerStart < 0' in l]
if len(hw) != 1:
    raise SystemExit('ABORT wart anchor: %d' % len(hw))
lines[hw[0]] = '            if (trailerStart < 0) throw new Error("turn trailer missing");'
src = '\n'.join(lines)
print('patched: parse wart', flush=True)

with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('WROTE PART B')
