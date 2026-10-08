"""_btn_probe.py - find the recruiter panel's Save button markup.
Does the same first steps as the lane (navigate -> card poll -> select -> apply ->
poll for question), then DUMPS every button's tag/class/text and the HTML around
the chat input. Read-only beyond the apply that opens the panel."""
import sys, io, json, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent360_client as A

JOBS_URL = "https://www.naukri.com/mnjuser/recommendedjobs"
WANT = "GenAI Architect | Generative AI | LLM | RAG | Agentic AI"


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


BTNS_JS = ("(function(){var bs=document.querySelectorAll('button');var o=[];"
           "for(var i=0;i<bs.length;i++){var b=bs[i];var t=(b.innerText||'').trim();"
           "if(t)o.push({t:t.slice(0,22),c:(b.className||'').toString().slice(0,80),"
           "d:b.disabled});}return JSON.stringify(o.slice(0,40));})()")
AROUND_JS = ("(function(){var c=document.querySelector('.chatbot_MessageContainer');"
             "if(!c)return 'NOPANEL';var p=c;for(var i=0;i<4&&p.parentElement;i++){p=p.parentElement;}"
             "return (p.innerHTML||'').replace(/\\s+/g,' ').slice(0,1800);})()")
SAVE_HINT_JS = ("(function(){var els=document.querySelectorAll('*');var o=[];"
                "for(var i=0;i<els.length;i++){var e=els[i];"
                "if(e.childElementCount===0&&(e.innerText||'').trim()==='Save'){"
                "o.push({tag:e.tagName,c:(e.className||'').toString().slice(0,80),"
                "p:(e.parentElement&&(e.parentElement.className||'').toString().slice(0,60))||''});}}"
                "return JSON.stringify(o.slice(0,6));})()")

c = A.Agent360Client()
try:
    c.start()
    unwrap(c.call_tool("browser_navigate", {"url": JOBS_URL}))
    time.sleep(12)
    for _ in range(10):
        n = unwrap(c.call_tool("browser_execute_script", {"code":
                 "document.querySelectorAll('article').length"})).get("result")
        if isinstance(n, int) and n > 0:
            break
        time.sleep(2)
    unwrap(c.call_tool("browser_execute_script", {"code": "(function(){var w=" + json.dumps(WANT)
           + ";var a=document.querySelectorAll('article');for(var i=0;i<a.length;i++){"
           "if((a[i].innerText||'').indexOf(w)>-1){var c=a[i].querySelector('.tuple-check-box');"
           "if(c)c.click();return 'ok';}}return 'no';})()"}))
    time.sleep(2)
    unwrap(c.call_tool("browser_execute_script", {"code":
        "(function(){var b=document.querySelector('.multi-apply-button');"
        "if(b&&!b.disabled)b.click();return 'ap';})()"}))
    time.sleep(8)
    print("BTNS:", unwrap(c.call_tool("browser_execute_script", {"code": BTNS_JS})).get("result"))
    print("SAVE_HINT:", unwrap(c.call_tool("browser_execute_script", {"code": SAVE_HINT_JS})).get("result"))
    print("AROUND:", unwrap(c.call_tool("browser_execute_script", {"code": AROUND_JS})).get("result"))
finally:
    try:
        c.close()
    except Exception:
        pass