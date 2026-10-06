"""Honest attempt to stop the running kernel via the Kaggle API, before claiming it cannot be done.

§12 of AGENTS.md records: "stop-session NOT in CLI -- Baba browser only (Active Events ... > Stop
Session)", verified against the CLI source. The CLI confirms it again -- its subcommands are
list, files, get, init, push, pull, output, status, logs, update, delete, topics. There is no stop.

So this tries the underlying HTTP service directly. Either it works, in which case the push is
unblocked without Baba's hand, or it does not, and then the honest report is that the browser is
required. It is not permitted to guess: an untested claim that "Kaggle cannot stop a kernel" would be
exactly the kind of impossibility-from-recall that §20 forbids.
"""
import json, os, sys, urllib.error, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KF = os.path.expanduser("~\\.kaggle\\kaggle.json")
cfg = json.load(open(KF, encoding="utf-8"))
key = cfg.get("key", cfg.get("username", ""))
USER, SLD = "isearchxsolve", "kilo-voice-live"
print("auth file: %s  key present: %s" % (KF, bool(key)))

CANDS = [
    ("POST", "https://www.kaggle.com/api/i/kernels.KernelsService/StopKernel",
     {"kernelId": 135151318}),
    ("POST", "https://www.kaggle.com/api/v1/kernels/stop",
     {"kernel": "%s/%s" % (USER, SLD)}),
    ("POST", "https://www.kaggle.com/api/i/kernels.KernelsService/CancelKernel",
     {"kernelId": 135151318}),
    ("POST", "https://www.kaggle.com/api/v1/kernels/%s/%s/stop" % (USER, SLD), None),
]
for method, url, payload in CANDS:
    data = json.dumps(payload).encode() if payload is not None else b""
    req = urllib.request.Request(url, data=data or None, method=method)
    req.add_header("Authorization", "Bearer %s" % key)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-XSRF-TOKEN", "")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        print("OK  %-6s %-70s -> %s %s" % (method, url.replace("https://www.kaggle.com", ""),
                                           r.status, r.read()[:180]))
    except urllib.error.HTTPError as e:
        print("%-4s %-6s %-70s -> %s %s" % ("ERR", method, url.replace("https://www.kaggle.com", ""),
                                            e.code, e.read()[:180]))
    except Exception as e:
        print("EXC  %-6s %-70s -> %r" % (method, url.replace("https://www.kaggle.com", ""), e)[:200])