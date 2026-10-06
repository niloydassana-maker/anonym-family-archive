# -*- coding: utf-8 -*-
"""EN-mode i18n v3: Hindi extracted programmatically, embedded via \\u escapes."""
import json
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    lines = f.readlines()

def jq(s):
    return json.dumps(s, ensure_ascii=True)

def get(i):
    return lines[i - 1]

def put(i, text):
    lines[i - 1] = text

def need(i, frag, name):
    if frag not in get(i):
        raise SystemExit('ABORT %s: line %d lacks %r' % (name, i, frag))

def dq(i):
    m = re.search(r'"([^"]*)"', get(i))
    if not m:
        raise SystemExit('ABORT dq line %d' % i)
    return m.group(1)

def sq(i):
    m = re.search(r"'([^']*)';?\s*$", get(i).rstrip('\n'))
    if not m:
        raise SystemExit('ABORT sq line %d: %r' % (i, get(i)[:100]))
    return m.group(1)

changed = []
def setline(i, text):
    put(i, text)
    changed.append(i)

# ---------- updateLiveButton (650, 654-656): HI dict + L() ----------
need(650, 'btn.title = liveMode ?', 'ulb-title')
need(654, 'status.innerText = !liveMode ?', 'ulb-s0')
need(655, 'assistantBusy ?', 'ulb-s1')
need(656, 'isRecording ?', 'ulb-s2')
hi_stop = re.search(r'liveMode \? "([^"]*)"', get(650)).group(1)
hi_start = re.search(r': "([^"]*)";', get(650)).group(1)
hi_s0 = sq(654)
hi_s1 = sq(655)
hi_s2 = sq(656).split(':')[0].strip().strip("'")
hi_s3 = sq(656).split(':')[-1].strip().strip("';")
new_ulb = (
    "        function updateLiveButton() {\n"
    "            var HI = {stopLive:%s, startLive:%s, statusStart:%s, answering:%s, listening:%s, listeningAgain:%s};\n"
    "            const btn = document.getElementById('micBtn');\n"
    "            btn.classList.toggle('live-mode', liveMode);\n"
    "            btn.title = L(liveMode ? 'stopLive' : 'startLive') || (liveMode ? HI.stopLive : HI.startLive);\n"
    "            btn.innerText = liveMode ? '\\u23F9' : '\\uD83C\\uDFA4';\n"
    "            const status = document.getElementById('liveStatus');\n"
    "            if (status) {\n"
    "                status.innerText = !liveMode ? (L('statusStart') || HI.statusStart) :\n"
    "                    assistantBusy ? (L('answering') || HI.answering) :\n"
    "                    isRecording ? (L('listening') || HI.listening) : (L('listeningAgain') || HI.listeningAgain);\n"
    "            }\n"
    "        }\n"
) % (jq(hi_stop), jq(hi_start), jq(hi_s0), jq(hi_s1), jq(hi_s2), jq(hi_s3))
# find block end: first line == '        }' at/after 656
ej = next(i for i in range(656, 665) if lines[i - 1] == '        }\n')
setline(647, None) if False else None
lines[647 - 1:ej] = [new_ulb]
print('patched: updateLiveButton (lines 647-%d)' % ej, flush=True)

print('PART1-OK (stopping for verification before more edits)')
