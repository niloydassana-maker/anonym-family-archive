# -*- coding: utf-8 -*-
"""EN-mode i18n v2: Hindi extracted programmatically, never retyped."""
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

def rep_once(pat, repl, name):
    global src
    found = re.findall(pat, src)
    if len(found) != 1:
        raise SystemExit('ABORT %s: matched %d (want 1)' % (name, len(found)))
    src = re.sub(pat, repl, src, count=1)
    print('patched: %s' % name, flush=True)

# ---------- 1. updateLiveButton: extract HI literals, rebuild with L() ----------
m = re.search(r"(        function updateLiveButton\(\) \{\n(?:.*\n)*?        \}\n)", src)
if not m:
    raise SystemExit('ABORT find updateLiveButton')
old_fn = m.group(1)
q = re.findall(r'"([^"]*)"', old_fn)
# expect: [stopLive_hi, startLive_hi, statusStart_hi, answering_hi, listening_hi, listeningAgain_hi]
if len(q) != 6:
    raise SystemExit('ABORT updateLiveButton literals: %d' % len(q))
(HI_stop, HI_start, HI_s0, HI_s1, HI_s2, HI_s3) = q
new_fn = (
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
) % tuple(json_q(x) for x in (HI_stop, HI_start, HI_s0, HI_s1, HI_s2, HI_s3))
src = src.replace(old_fn, new_fn, 1)
print('patched: updateLiveButton', flush=True)

with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('WROTE updateLiveButton (stopping here for review)')
