"""_dom_probe.py - find the CURRENT card element shape on recommended-jobs.
Read-only: navigate + report the container markup around the target title + any
checkbox-ish nodes, so lane_apply selectors can be re-pointed. No clicks/Writes."""
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


PROBE_JS = ("(function(){var want=" + json.dumps(WANT) + ";"
            "var all=document.querySelectorAll('*');var node=null;"
            "for(var i=0;i<all.length;i++){var el=all[i];"
            "var t=el.innerText||'';"
            "if(el.childElementCount<=8 && t.indexOf(want)===0){node=el;}}"
            "function d(e){return e?{tag:e.tagName,cls:(e.className||'').toString()"
            ".slice(0,140),id:e.id||''}:null;}"
            "var out={articles:document.querySelectorAll('article').length,"
            "sections:document.querySelectorAll('section').length,"
            "card:d(node),parent:node?d(node.parentElement):null,"
            "grand:node&&node.parentElement?d(node.parentElement.parentElement):null};"
            "var scope=node?(node.closest('div')||node):document;"
            "var cbs=scope.querySelectorAll('[class*=check],[class*=Check],[type=checkbox]');"
            "out.checks=Array.prototype.slice.call(cbs,0,6).map(function(c){"
            "return {tag:c.tagName,cls:(c.className||'').toString().slice(0,90)};});"
            "var btns=document.querySelectorAll('.multi-apply-button,button');"
            "out.buttons=Array.prototype.slice.call(btns,0,8).map(function(b){"
            "return (b.innerText||'').trim().slice(0,30);});"
            "return JSON.stringify(out);})()")


c = A.Agent360Client()
try:
    c.start()
    unwrap(c.call_tool("browser_navigate", {"url": JOBS_URL}))
    time.sleep(12)
    r = unwrap(c.call_tool("browser_execute_script", {"code": PROBE_JS}))
    res = r.get("result") if isinstance(r, dict) else r
    print("PROBE:", flush=True)
    print(res, flush=True)
finally:
    try:
        c.close()
    except Exception:
        pass