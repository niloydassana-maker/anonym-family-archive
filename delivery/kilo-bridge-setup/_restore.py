import sys, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\anonym\war-log")
import agent360_client as A
c = A.Agent360Client(); c.start()
def txt(n, a=None):
    r = c.call_tool(n, a or {}) or {}
    for b in r.get("content", []):
        if b.get("type") == "text":
            t = b.get("text","")
            try: return json.loads(t)
            except Exception: return t
    return ""
c.call_tool("browser_navigate", {"url": "https://www.naukri.com/mnjuser/profile"}); import time; time.sleep(7)
body = str(c.call_tool("browser_execute_script", {"code": "document.body.innerText"}) or "")
print("CHARS:", len(body))
if "KUNAL" in body.upper(): print("KUNAL FOUND - logged in")
if "AI Agents" in body: print("AI Agents present")
c.close()
