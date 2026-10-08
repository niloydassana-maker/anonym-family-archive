"""_diag_page.py - read-only page diagnostic (why is the card not found?).
Navigates to recommended-jobs, settles, dumps URL + body head + article titles +
screenshot. NO clicks, NO writes."""
import sys, io, json, base64, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
EVID = HERE.parent / "evidence" / "employment-lane"
sys.path.insert(0, str(HERE))
import agent360_client as A

JOBS_URL = "https://www.naukri.com/mnjuser/recommendedjobs"


def unwrap(r):
    r = r or {}
    if r.get("isError"):
        return {"error": True, "raw": str(r)[:200]}
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
    def js(expr):
        r = unwrap(c.call_tool("browser_execute_script", {"code": expr}))
        return r.get("result") if isinstance(r, dict) else r

    unwrap(c.call_tool("browser_navigate", {"url": JOBS_URL}))
    time.sleep(12)
    url = str(js("location.href") or "")
    title = str(js("document.title") or "")
    arty = js("(function(){var a=Array.from(document.querySelectorAll('article'));"
              "return JSON.stringify(a.slice(0,8).map(function(x){"
              "return (x.innerText||'').split('\\n')[0].slice(0,80);}));})()")
    body = str(js("document.body.innerText") or "")
    print("URL:", url)
    print("TITLE:", title)
    print("ARTICLES:", arty)
    print("BODY_CHARS:", len(body))
    print("BODY_HEAD:", body[:600].replace("\n", " / "))
    # screenshot receipt
    r = c.call_tool("browser_screenshot", {"format": "png"}) or {}
    for b in r.get("content", []):
        if b.get("type") == "image":
            p = EVID / ("diag-" + time.strftime("%Y%m%d%H%M%S") + ".png")
            p.write_bytes(base64.b64decode(b["data"]))
            print("SHOT:", p)
finally:
    try:
        c.close()
    except Exception:
        pass