import json, os, time, urllib.request, sys
# SECRETS FIX 2026-10-07: a literal provider key lived here and was staged for the
# buyer kit. Never hardcode - read from the environment, fail loudly if absent.
KEY = os.environ.get("NVIDIA_API_KEY", "")
if not KEY:
    sys.exit("NVIDIA_API_KEY not set (this probe needs a key; do not hardcode one)")
URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELS = ["nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3-ultra-550b-a55b"]
for m in MODELS:
    body = json.dumps({
        "model": m,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 8,
        "temperature": 0.0,
        "stream": False,
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=18) as r:
            d = json.loads(r.read().decode())
            dt = int((time.time() - t0) * 1000)
            txt = (d.get("choices") or [{}])[0].get("message", {}).get("content", "")
            print(f"{m}: HTTP {r.status}  {dt}ms  reply={txt!r}")
    except Exception as e:
        dt = int((time.time() - t0) * 1000)
        print(f"{m}: FAIL {dt}ms  {type(e).__name__}: {str(e)[:200]}")