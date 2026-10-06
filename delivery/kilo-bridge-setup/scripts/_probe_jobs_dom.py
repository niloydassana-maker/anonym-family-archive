"""One-shot DOM probe: how are Naukri recommended-job cards structured right now?
Prints candidate selectors and their counts, plus a real card's text.
Read-only. No edits.
"""
import io, json, sys, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent360_client as A

c = A.Agent360Client(); c.start()
def txt(n, a=None):
    r = c.call_tool(n, a or {}) or {}
    for b in r.get("content", []):
        if b.get("type") == "text":
            t = b.get("text", "")
            try: return json.loads(t)
            except Exception: return t
    return ""
def js(e):
    r = txt("browser_execute_script", {"code": e})
    return r.get("result") if isinstance(r, dict) else r

# navigate FIRST - the client attaches to whatever tab is active, which may be
# about:blank (ledger row 00: "tool requires a real page"). A read-only probe
# that does not navigate reads an empty tab and learns nothing.
txt("browser_navigate", {"url": "https://www.naukri.com/mnjuser/recommendedjobs"})
time.sleep(12)

url = str(js("location.href") or "")
print("URL:", url[:110], flush=True)
body = str(js("document.body.innerText") or "")
print("CHARS:", len(body), flush=True)

print("\n--- candidate job-card selectors ---", flush=True)
probe = ("JSON.stringify(['article','div[class*=job]','div[class*=tuple]',"
         "'div[class*=card]','li[class*=job]','[class*=cust-job-tuple]',"
         "'[class*=srp-jobtuple]','[class*=jobTuple]','[data-job-id]',"
         "'a[href*=job-listings]'].map(function(s){"
         "return {sel:s, n:document.querySelectorAll(s).length};}))")
print(str(js(probe))[:900], flush=True)

print("\n--- ids/classes containing job-ish words ---", flush=True)
probe2 = ("JSON.stringify(Array.from(document.querySelectorAll('*')).map(function(e){"
          "var c=(e.className||'').toString(); return c;})"
          ".filter(function(c){return /tuple|jobtuple|srp|card|job-card/i.test(c)})"
          ".slice(0,20))")
print(str(js(probe2))[:900], flush=True)

print("\n--- first 600 chars of page text ---", flush=True)
print(body[:600], flush=True)

print("\n--- job listing anchors (title + href) ---", flush=True)
probe3 = ("JSON.stringify(Array.from(document.querySelectorAll('a[href*=job-listings]'))"
          ".slice(0,12).map(function(a){return {t:(a.innerText||'').trim().slice(0,70),"
          "h:(a.getAttribute('href')||'').slice(0,90)};}))")
print(str(js(probe3))[:1400], flush=True)

c.close()