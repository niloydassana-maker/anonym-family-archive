import json, os, time, urllib.request, sys, urllib.error
# SECRETS FIX 2026-10-07: a literal provider key lived here and was staged for the
# buyer kit. Never hardcode - read from the environment, fail loudly if absent.
KEY = os.environ.get("NVIDIA_API_KEY", "")
if not KEY:
    sys.exit("NVIDIA_API_KEY not set (this probe needs a key; do not hardcode one)")
URL = "https://integrate.api.nvidia.com/v1/chat/completions"

def probe(label, model, extra):
    body = {"model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "max_tokens": 64, "temperature": 0.0, "stream": False}
    body.update(extra)
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json",
        "Accept": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode())
            dt = int((time.time() - t0) * 1000)
            ch = (d.get("choices") or [{}])[0]
            msg = ch.get("message", {}) or {}
            print(f"[{label}] {r.status} {dt}ms finish={ch.get('finish_reason')!r}")
            print(f"    content={ (msg.get('content') or '')[:90]!r}")
            rc = msg.get("reasoning_content")
            if rc:
                print(f"    reasoning={rc[:90]!r}")
    except urllib.error.HTTPError as e:
        dt = int((time.time() - t0) * 1000)
        print(f"[{label}] HTTPError {e.code} {dt}ms {e.read().decode()[:160]!r}")
    except Exception as e:
        dt = int((time.time() - t0) * 1000)
        print(f"[{label}] FAIL {dt}ms {type(e).__name__}: {str(e)[:160]}")

S = "nvidia/nemotron-3-super-120b-a12b"
U = "nvidia/nemotron-3-ultra-550b-a55b"
probe("super baseline",         S, {})
probe("super nested-off",       S, {"chat_template_kwargs": {"enable_thinking": False}})
probe("super reasoning_effort", S, {"reasoning_effort": "none"})
probe("ultra nested-off",       U, {"chat_template_kwargs": {"enable_thinking": False}})
probe("ultra baseline",         U, {})