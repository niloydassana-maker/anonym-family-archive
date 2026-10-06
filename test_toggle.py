# -*- coding: utf-8 -*-
"""Prove toggle law: explicit lang rules STT+LLM+TTS over auto-detect."""
import json
import urllib.request

BASE = "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run"


def post_turn(text, lang, sid):
    payload = {"text": text, "lang": lang, "session_id": sid}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + "/turn?speed=1.2", data=data,
                                 headers={"Content-Type": "application/json; charset=utf-8"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
    idx = raw.rfind(b'{"end": true')
    trailer = json.loads(raw[idx:].decode("utf-8").split("\n")[0])
    pcm_len = len(raw) - (raw.find(b"\n") + 1) - (len(raw) - idx)
    return trailer.get("reply", ""), pcm_len, trailer.get("total_ms")


def last_event():
    with urllib.request.urlopen(BASE + "/lastturns", timeout=60) as resp:
        evs = json.loads(resp.read().decode("utf-8"))
        if isinstance(evs, str):
            evs = json.loads(evs)
    return evs[-1] if evs else {}


results = []
for name, text, lang in [
    ("en-text-en-toggle", "What are the clinic timings?", "en"),
    ("hi-text-hi-toggle", "placeholder", "hi"),
    ("en-text-hi-toggle", "What are the clinic timings?", "hi"),
]:
    if name == "hi-text-hi-toggle":
        text = "क्लिनिक की टाइमिंग क्या है?"
    reply, pcm, total = post_turn(text, lang, "tg_%s" % name)
    ev = last_event()
    line = "%s => reply_chars=%d pcm=%d total_ms=%s turn_lang=%s reply=%s" % (
        name, len(reply), pcm, total, ev.get("turn_lang"), reply[:150])
    results.append(line)
    print("CASE-DONE %s" % name, flush=True)

with open(r"D:\anonym\toggle_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results) + "\n")
print("done")
