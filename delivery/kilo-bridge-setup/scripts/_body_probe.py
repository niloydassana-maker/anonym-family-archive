"""_body_probe.py - READ-ONLY: dump the live page's innerText so we can see
which questions are actually present (page widgets vs the recruiter panel).
No click, no navigate. Writes the raw text + a questions digest to disk.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent360_client as A  # noqa: E402


def txt(c, n, a=None):
    r = c.call_tool(n, a or {}) or {}
    if r.get("isError"):
        return {"error": True, "raw": str(r)[:300]}
    for b in r.get("content", []):
        if b.get("type") == "text":
            t = b.get("text", "")
            try:
                return json.loads(t)
            except Exception:
                return t
    return ""


c = A.Agent360Client()
try:
    c.start()
    href = txt(c, "browser_execute_script", {"code": "location.href"})
    body = txt(c, "browser_execute_script", {"code": "document.body.innerText"})
    body = body if isinstance(body, str) else str(body)
    (HERE / "_body_probe.txt").write_text(body, encoding="utf-8")
    qs = [ln.strip() for ln in body.splitlines() if ln.strip().endswith("?")]
    hits = [ln.strip() for ln in body.splitlines()
            if any(k in ln.lower() for k in
                   ("recruiter", "years", "relevant for you", "ctc",
                    "notice period", "hand") and ln.strip())]
    digest = ["HREF=" + str(href), "BODY_CHARS=" + str(len(body)),
              "", "QUESTIONS (lines ending in ?):"]
    digest += qs
    digest += ["", "SIGNAL LINES:"]
    digest += hits
    (HERE / "_body_probe_q.txt").write_text("\n".join(digest), encoding="utf-8")
except Exception as e:
    (HERE / "_body_probe_q.txt").write_text("EXC " + repr(e), encoding="utf-8")
finally:
    try:
        c.close()
    except Exception:
        pass
print("body probe done")