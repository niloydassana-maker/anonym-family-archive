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
def js(e):
    r = txt("browser_execute_script", {"code": e})
    return r.get("result") if isinstance(r, dict) else r
# screenshot to bind, then list tabs
c.call_tool("browser_screenshot", {"format":"png"}); import time; time.sleep(2)
tabs = txt("browser_list_tabs", {})
print("TABS:")
if isinstance(tabs, list):
    for t in tabs: print("  id=", t.get("tab_id"), "url=", str(t.get("url"))[:80], "title=", str(t.get("title"))[:60])
else:
    print("  (raw)", str(tabs)[:200])
c.close()
