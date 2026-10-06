# -*- coding: utf-8 -*-
"""EN-mode i18n: content-anchored, Hindi extracted programmatically."""
import json
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

def rep(pat, repl, name):
    """Regex replace exactly once (DOTALL where needed)."""
    global src
    found = re.findall(pat, src)
    if len(found) != 1:
        raise SystemExit('ABORT %s: matched %d (want 1)' % (name, len(found)))
    src = re.sub(pat, repl, src, count=1)
    print('patched: %s' % name, flush=True)

def jq(s):
    return json.dumps(s, ensure_ascii=True)

# ---------- 1. updateLiveButton: HI dict + L(), Hindi extracted ----------
m = re.search(r"        function updateLiveButton\(\) \{\n(?:.*\n)*?        \}\n", src)
if not m:
    raise SystemExit('ABORT find updateLiveButton')
old_fn = m.group(0)
lits = re.findall(r'"([^"]*)"', old_fn)
if len(lits) != 2:
    raise SystemExit('ABORT ulb dq literals: %d' % len(lits))
lits_sq = re.findall(r"'([^']*)'", old_fn)
# single-quoted literals in fn: 'micBtn', 'live-mode', 'liveStatus', emojis, 4 status strings...
if len([x for x in lits_sq if re.search(r'[\u0900-\u097F]', x)]) != 6:
    raise SystemExit('ABORT ulb hi literals')
hi_list = [x for x in lits_sq if re.search(r'[\u0900-\u097F]', x)]
# order in fn: titleA, titleB, s0, s1, s2, s3
HI_stop, HI_start, HI_s0, HI_s1, HI_s2, HI_s3 = lits[0], lits[1], hi_list[0], hi_list[1], hi_list[2], hi_list[3]
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
) % (jq(HI_stop), jq(HI_start), jq(HI_s0), jq(HI_s1), jq(HI_s2), jq(HI_s3))
src = src.replace(old_fn, new_fn, 1)
print('patched: updateLiveButton', flush=True)

print('PART1 DONE')
