import json
import urllib.request

URL = "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/api/chat"

TESTS = [
    ("hi-fee", "शुगर चेकअप की क्या फीस है?", {}),
    ("hi-time", "क्लिनिक की टाइमिंग क्या है?", {}),
    ("en-time", "What are the clinic timings?", {"lang": "en"}),
    ("en-fee", "What is the sugar checkup fee?", {"lang": "en"}),
    ("hi-hello", "नमस्ते", {}),
    ("en-hello", "Hello", {"lang": "en"}),
]

with open(r"D:\anonym\final_results.txt", "w", encoding="utf-8") as f:
    pass

for name, text, extra in TESTS:
    payload = {"text": text, "session_id": "final_%s" % name}
    payload.update(extra)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
        j = json.loads(raw)
        reply = j.get("reply", "")
        has_audio = "audio_b64" in j and len(j.get("audio_b64") or "") > 1000
        out = "%s => chars=%d audio=%s reply=%s" % (name, len(reply), has_audio, reply[:220])
    except Exception as e:
        out = "%s => ERROR %s: %s" % (name, type(e).__name__, str(e)[:200])
    with open(r"D:\anonym\final_results.txt", "a", encoding="utf-8") as f:
        f.write(out + "\n")
print("done")