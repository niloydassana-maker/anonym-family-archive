import sys, io, json, time, base64
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\anonym\war-log")
OUT = Path(r"D:\anonym\war-log\evidence\L1"); OUT.mkdir(parents=True, exist_ok=True)
import agent360_client as A
c = A.Agent360Client(); c.start()
def txt(n,a=None):
    r=c.call_tool(n,a or {}) or {}
    for b in r.get("content",[]):
        if b.get("type")=="text":
            t=b.get("text","")
            try: return json.loads(t)
            except Exception: return t
    return ""
def js(e):
    r=txt("browser_execute_script",{"code":e}); return r.get("result") if isinstance(r,dict) else r
snap = OUT/f"linkedin-profile-SNAPSHOT-{time.strftime('%Y%m%d-%H%M%S')}.json"
for label,url in [("profile","https://www.linkedin.com/in/kunal-das-technologist/"),
                  ("feed","https://www.linkedin.com/feed/")]:
    txt("browser_navigate",{"url":url}); time.sleep(6)
    body = str(js("document.body.innerText") or "")
    (OUT/f"linkedin-{label}-text-{label}.txt").write_text(body,encoding="utf-8")
    r=c.call_tool("browser_screenshot",{"format":"png"})
    for b in r.get("content",[]):
        if b.get("type")=="image":
            p=OUT/f"linkedin-{label}-{time.strftime('%Y%m%d-%H%M%S')}.png"
            p.write_bytes(base64.b64decode(b["data"])); print("SHOT",label,p.name,p.stat().st_size)
    print(f"{label}: {len(body)} chars captured")
snap.write_text(json.dumps({"ts":time.strftime("%Y-%m-%d %H:%M:%S"),
                            "note":"PRE-CHANGE snapshot for rollback"},indent=1),encoding="utf-8")
print("SNAPSHOT MARKER ->", snap.name)
c.close()
