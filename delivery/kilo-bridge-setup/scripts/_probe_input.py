"""_probe_input.py - inspect the recruiter chat input element (no navigate).
The panel should still be open from the last run. Find the real input so
_fill_question can target + VERIFY it (read-back)."""
import sys, io, json
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent360_client as A


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


INPUTS_JS = ("(function(){var els=document.querySelectorAll('input,textarea,[contenteditable]');"
             "var out=[];for(var i=0;i<els.length;i++){var e=els[i];"
             "out.push({tag:e.tagName,type:e.type||'',cls:(e.className||'').toString().slice(0,70),"
             "id:e.id||'',ph:e.placeholder||'',ce:e.getAttribute('contenteditable')||'',"
             "val:(e.value||'').slice(0,25)});}return JSON.stringify(out);})()")
PANEL_JS = ("(function(){var c=document.querySelector('.chatbot_MessageContainer');"
            "if(!c)return 'NO PANEL';var p=c.parentElement;"
            "return (p.innerHTML||'').replace(/\\s+/g,' ').slice(0,1400);})()")
Q_JS = ("(function(){var c=document.querySelector('.chatbot_MessageContainer');"
        "if(!c)return 'NO PANEL';return (c.innerText||'').slice(0,200);})()")

c = A.Agent360Client()
try:
    c.start()
    print("URL:", unwrap(c.call_tool("browser_execute_script", {"code": "location.href"})).get("result"))
    print("PANEL_TEXT:", unwrap(c.call_tool("browser_execute_script", {"code": Q_JS})).get("result"))
    print("INPUTS:", unwrap(c.call_tool("browser_execute_script", {"code": INPUTS_JS})).get("result"))
    print("PANEL_HTML:", unwrap(c.call_tool("browser_execute_script", {"code": PANEL_JS})).get("result"))
finally:
    try:
        c.close()
    except Exception:
        pass