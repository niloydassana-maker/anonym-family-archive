import json
import urllib.request

URLS = {
    "isearch": "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/api/chat",
    "kunal": "https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/api/chat",
}

TESTS = [
    ("hi-fee", "शुगर चेकअप की क्या फीस है?", {}),
    ("hi-time", "क्लिनिक की टाइमिंग क्या है?", {}),
    ("en-time", "What are the clinic timings?", {"lang": "en"}),
]

for name, text, extra in TESTS:
    for site, url in URLS.items():
        if site == "kunal" and name == "en-time":
            continue
        payload = {"text": text, "session_id": "cmp_%s_%s" % (site, name)}
        payload.update(extra)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
            j = json.loads(raw)
            reply = j.get("reply", "")
            out = "%s | %s => chars=%d reply=%s" % (site, name, len(reply), reply[:220])
        except Exception as e:
            out = "%s | %s => ERROR %s: %s" % (site, name, type(e).__name__, str(e)[:200])
        with open(r"D:\anonym\cmp_results.txt", "a", encoding="utf-8") as f:
            f.write(out + "\n")
print("done")