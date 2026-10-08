"""_probe_pipe.py - read-only Agent360 pipe probe (no navigation, no writes).
Confirms ONE working browser pipe exists before a driver is fired (FIGHTING-HANDS)."""
import sys, io, json
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent360_client as A


def unwrap(r):
    r = r or {}
    if r.get("isError"):
        return {"error": True, "raw": str(r)[:300]}
    for b in r.get("content", []):
        if b.get("type") == "text":
            t = b.get("text", "")
            try:
                return json.loads(t)
            except Exception:
                return t[:300]
    return ""


c = A.Agent360Client()
try:
    c.start()
    print("PIPE started OK")
    tabs = unwrap(c.call_tool("browser_list_tabs", {}))
    if isinstance(tabs, str):
        print("TABS:", tabs[:1500])
    else:
        print("TABS:", json.dumps(tabs)[:1500])
finally:
    try:
        c.close()
        print("PIPE closed")
    except Exception as e:
        print("close warn:", str(e)[:200])