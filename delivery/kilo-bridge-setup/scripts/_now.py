import sys, io, json, time, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\anonym\war-log")
import agent360_client as A
c = A.Agent360Client(); c.start()
def js(e):
    r = c.call_tool("browser_execute_script", {"code": e})
    return r.get("result") if isinstance(r, dict) else r
t = str(js("document.body.innerText") or "")
print("CHARS:", len(t))
print("=== LAST 2000 CHARS ===")
print(t[-2000:])
c.close()
