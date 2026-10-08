"""_apply_save.py - ONE measured step: press the recruiter panel's Save/send
button and report the NEXT state (more questions? submission success?).
Read + one click; no navigate (panel open from the last lane run)."""
import sys, io, json, base64, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
EVID = HERE.parent / "evidence" / "employment-lane"
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


SAVE_JS = ("(function(){var c=document.querySelector('.chatbot_MessageContainer');"
           "if(!c)return JSON.stringify({saved:'nopanel'});"
           "var root=c.closest('div[class*=drawer],div[class*=Drawer],"
           "div[class*=panel],div[class*=Panel]')||c.parentElement;"
           "var bs=Array.prototype.slice.call(root.querySelectorAll('button'));"
           "var b=bs.filter(function(x){return /^save$/i.test((x.innerText||'').trim());})[0];"
           "if(!b)return JSON.stringify({saved:'nobtn',cands:bs.map(function(x){"
           "return (x.innerText||'').trim();}).slice(0,10)});"
           "if(b.disabled)return JSON.stringify({saved:'disabled'});"
           "b.click();return JSON.stringify({saved:'clicked'});})()")
PANEL_JS = ("(function(){var c=document.querySelector('.chatbot_MessageContainer');"
            "return c?(c.innerText||'').slice(0,400):'NO PANEL';})()")
SUCCESS_JS = ("(function(){var t=(document.body.innerText||'').toLowerCase();"
              "var ks=['application submitted','successfully applied',"
              "'you have successfully applied','applied successfully'];"
              "for(var i=0;i<ks.length;i++){if(t.indexOf(ks[i])>-1)return ks[i];}"
              "return '';})()")


c = A.Agent360Client()
try:
    c.start()
    print("URL:", unwrap(c.call_tool("browser_execute_script", {"code": "location.href"})).get("result"))
    print("BEFORE:", unwrap(c.call_tool("browser_execute_script", {"code": PANEL_JS})).get("result"))
    r = unwrap(c.call_tool("browser_execute_script", {"code": SAVE_JS}))
    print("SAVE:", r.get("result") if isinstance(r, dict) else r)
    time.sleep(6)
    print("AFTER:", unwrap(c.call_tool("browser_execute_script", {"code": PANEL_JS})).get("result"))
    print("SUCCESS:", unwrap(c.call_tool("browser_execute_script", {"code": SUCCESS_JS})).get("result"))
    shot = c.call_tool("browser_screenshot", {"format": "png"}) or {}
    for b in shot.get("content", []):
        if b.get("type") == "image":
            p = EVID / ("apply-save-" + time.strftime("%Y%m%d%H%M%S") + ".png")
            p.write_bytes(base64.b64decode(b["data"]))
            print("SHOT:", p)
finally:
    try:
        c.close()
    except Exception:
        pass