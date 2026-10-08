"""_live_check.py - is the browser lane bound to the logged-in Naukri session?
Read-only: lists tabs + reads location.href. No click, no navigate.
Writes JSON to _live_check.txt so a lost stdout cannot hide the result.
"""
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent360_client as A  # noqa: E402

out = {}


def txt(c, name, args=None):
    r = c.call_tool(name, args or {}) or {}
    if r.get("isError"):
        return {"error": True, "raw": str(r)[:400]}
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
    out["tabs"] = txt(c, "browser_list_tabs")
    out["href"] = txt(c, "browser_execute_script", {"code": "location.href"})
    out["title"] = txt(c, "browser_execute_script", {"code": "document.title"})
    body = txt(c, "browser_execute_script", {"code": "document.body.innerText"})
    out["body_chars"] = len(body) if isinstance(body, str) else -1
    low = (body or "").lower() if isinstance(body, str) else ""
    out["naukri_session"] = ("recommendedjobs" in (out.get("href") or "")) or ("naukri" in (out.get("href") or ""))
    out["has_login_wall"] = ("login" in (out.get("href") or "").lower()) or ("sign in" in low[:2000])
except Exception as e:
    out["exception"] = repr(e)

(HERE / "_live_check.txt").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
print("LIVE_CHECK written")