"""_panel_probe.py - READ-ONLY forensic: drive select+apply, then DUMP the panel
DOM so we can find where the recruiter question actually lives. No answering,
no submit. Writes dumps to disk (stdout is unreliable under the tool cap).
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent360_client as A  # noqa: E402

TITLE = "GenAI Architect | Generative AI | LLM | RAG | Agentic AI"
JOBS_URL = "https://www.naukri.com/mnjuser/recommendedjobs"

DUMP_JS = (
    "(function(){"
    "var out={href:location.href,inner_len:(document.body.innerText||'').length,"
    "q:[],panels:[]};"
    "var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);var n;"
    "while(n=w.nextNode()){var t=(n.nodeValue||'').trim();"
    "if(t.length>8&&t.charAt(t.length-1)==='?'){var el=n.parentElement;"
    "out.q.push({tag:el?el.tagName:'',cls:el?String(el.className).slice(0,70):'',"
    "txt:t.slice(0,150)});}}"
    "var all=document.querySelectorAll('div,section,form,ul');"
    "for(var i=0;i<all.length;i++){var c=String(all[i].className||'');"
    "if(/chat|recruit|qna|question|applybar|chatsupport/i.test(c)){"
    "out.panels.push({tag:all[i].tagName,cls:c.slice(0,90),"
    "len:(all[i].innerText||'').length});}}"
    "return JSON.stringify(out);})()"
)


def txt(c, n, a=None):
    r = c.call_tool(n, a or {}) or {}
    for b in r.get("content", []):
        if b.get("type") == "text":
            t = b.get("text", "")
            try:
                return json.loads(t)
            except Exception:
                return t
    return ""


def js(c, expr):
    r = txt(c, "browser_execute_script", {"code": expr})
    return r.get("result") if isinstance(r, dict) else r


c = A.Agent360Client()
report = {}
try:
    c.start()
    txt(c, "browser_navigate", {"url": JOBS_URL})
    time.sleep(10)
    esc = json.dumps(TITLE)
    FIND_JS = ("(function(){var want=" + esc + ";"
               "var a=Array.from(document.querySelectorAll('article'));"
               "for(var i=0;i<a.length;i++){if((a[i].innerText||'').indexOf(want)>-1)"
               "return i;}return -1;})()")
    report["idx"] = js(c, FIND_JS)
    CHECK_JS = ("(function(){var want=" + esc + ";"
                "var a=Array.from(document.querySelectorAll('article'));"
                "for(var i=0;i<a.length;i++){if((a[i].innerText||'').indexOf(want)>-1){"
                "var cb=a[i].querySelector('.tuple-check-box');"
                "if(cb){cb.click();return 'checked';}return 'no-cb';}}"
                "return 'nocard';})()")
    report["sel"] = js(c, CHECK_JS)
    time.sleep(2)
    APPLY_JS = ("(function(){var b=document.querySelector('.multi-apply-button')||"
                "Array.from(document.querySelectorAll('button')).find(function(x){"
                "return /^apply/i.test((x.innerText||'').trim());});"
                "if(!b)return 'nobtn';if(b.disabled)return 'disabled';"
                "b.click();return 'clicked';})()")
    report["apply"] = js(c, APPLY_JS)
    time.sleep(8)
    raw = js(c, DUMP_JS)
    (HERE / "_panel_dump_raw.txt").write_text(str(raw), encoding="utf-8")
    body = js(c, "document.body.innerText")
    (HERE / "_panel_body.txt").write_text(str(body), encoding="utf-8")
except Exception as e:
    report["exc"] = repr(e)
finally:
    try:
        c.close()
    except Exception:
        pass

(HERE / "_panel_report.txt").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print("panel probe done")