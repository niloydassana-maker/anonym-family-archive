"""lane_apply.py - the money step: ONE turn from a MATCHED title to an application.

WHY THIS EXISTS (2026-10-07, "fix all issues"):
The opencode agent churned for ~20 min across ~10 separate `python -c` shell-outs and
could not reach an apply, for FOUR structural reasons this driver removes:

  1. TAB LOSS / about:blank loop. Evidence: bind-screenshot2.png (5 KB, pure white)
     taken when TABS read about:blank. Each tool call spawned a NEW Agent360Client
     -> new node child -> fresh session -> the Naukri tab "vanished". The agent
     misread TABS:[] as "extension unbound" and kept re-binding (creating blank tabs)
     instead of working the real page. apply-01 before.png (147 KB) is the real Naukri
     page - the browser was never broken.
  2. BACKGROUND TAB. browser_click on the real card returned "CDP did not respond ...
     call browser_switch_tab". A single session does nav -> locate -> switch -> click.
  3. INLINE JS ESCAPING. python -c + here-string + && inside JS => PowerShell
     ParserError / Python unterminated-string, THREE times. This reads JS from a
     variable, never from a shell one-liner.
  4. A dead /job-apply href selector. The recommended-jobs page carries no job URL
     (named wall, DRIVERS-20261006.md). Click by exact TITLE, unique on the page.

DESIGN (mirrors proven lane_jobs.py; agent360_client SHA55C8EAE7...B06294 READ only):
  * ONE client session for the whole turn (start -> navigate -> work -> close).
  * NAVIGATE-FIRST, then switch_tab, then JS .click() (mouse path is dead).
  * Verify by URL change OR a known apply-flow marker in body text.
  * ONE screenshot per state change (PACE law).
  * NEVER invent a fact. In-flow recruiter question => answer from record or BLOCKED.
  * Never spend money, never touch login/password/OTP.

It OPENS the apply flow and screenshots it; a blocking recruiter question is reported
BLOCKED with the verbatim text. It never force-submits past a gate.
"""
import base64
import io
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
EVID = LANE / "evidence" / "employment-lane"
LEDGER = EVID / "ledger.tsv"
sys.path.insert(0, str(HERE))
import agent360_client as A  # noqa: E402

JOBS_URL = "https://www.naukri.com/mnjuser/recommendedjobs"

QUESTION_RE = re.compile(
    r"([A-Z][^?\n]{0,160}\?\s*$)|(how many years[^?\n]{0,120}\?)|(experience do you have[^?\n]{0,80}\?)",
    re.I | re.M,
)


def log(m):
    print(m, flush=True)


def ledger(portal, source, role, company, score, step, status, receipt, note):
    row = "\t".join([str(date.today()), portal, source, role, company,
                     str(score), step, status, receipt, note])
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(row + "\n")
    log("  LEDGER + " + status + " :: " + step[:70])

def main(argv):
    title = " ".join(argv[1:]).strip()
    if not title:
        title = _top_matched_title() or "GenAI Architect | Generative AI | LLM | RAG | Agentic AI"
    log("LANE_APPLY start :: title = " + title)

    c = A.Agent360Client()
    try:
        c.start()

        def txt(name, args=None):
            r = c.call_tool(name, args or {}) or {}
            if r.get("isError"):
                return {"error": True, "raw": r}
            for b in r.get("content", []):
                if b.get("type") == "text":
                    t = b.get("text", "")
                    try:
                        return json.loads(t)
                    except Exception:
                        return t
            return ""

        def js(expr):
            r = txt("browser_execute_script", {"code": expr})
            return r.get("result") if isinstance(r, dict) else r

        def body():
            return str(js("document.body.innerText") or "")

        def href():
            return str(js("location.href") or "")

        def shot(tag):
            for _attempt in range(3):
                r = c.call_tool("browser_screenshot", {"format": "png"}) or {}
                for b in r.get("content", []):
                    if b.get("type") == "image":
                        p = EVID / (tag + ".png")
                        p.write_bytes(base64.b64decode(b["data"]))
                        return p
                time.sleep(1)
            return None

        log("A1 navigate -> " + JOBS_URL)
        txt("browser_navigate", {"url": JOBS_URL})
        time.sleep(10)

        esc = json.dumps(title)
        FIND_JS = ("(function(){var want=" + esc + ";"
                   "var arts=Array.from(document.querySelectorAll('article'));"
                   "for(var i=0;i<arts.length;i++){var h=arts[i].innerText||'';"
                   "if(h.indexOf(want)===0||h.indexOf(want)>-1){return i;}}"
                   "return -1;})()")
        # A1b: the recommended-jobs list is an SPA - cards hydrate AFTER navigate.
        # MEASURED 2026-10-07 01:13: `article` count 0 at +10s on a COLD tab, 63
        # at +12s. A fixed sleep(10) read an empty list -> false "card not found".
        # POLL for the card (up to ~30s) instead of trusting one read.
        idx = -1
        for _ in range(15):
            idx = js(FIND_JS)
            if idx is not None and int(idx) >= 0:
                break
            arts_n = js("document.querySelectorAll('article').length")
            log("   A2 wait cards: articles=" + str(arts_n) + " idx=" + str(idx))
            time.sleep(2)
        log("A2 card index = " + str(idx))
        if idx is None or int(idx) < 0:
            log("   !! card not found - BLOCKED (not a fake attempt)")
            ledger("naukri", JOBS_URL[:70], title[:70], "-", "-",
                   "locate job card", "BLOCKED", "none", "card not found by exact title")
            shot("apply-blocked-no-card")
            return 2

        # PROVEN MECHANISM (measured 2026-10-07): recommended-jobs cards have NO <a>,
        # NO onclick, NO React nav (element.click + event dispatch both did nothing).
        # SELECT-THEN-APPLY: click styled .tuple-check-box in the card -> header button
        # turns "Apply N Job" (enabled) -> click it -> apply flow.
        # Receipt: select-01-checked.png shows checked box + blue "Apply 1 Job".
        CHECK_JS = ("(function(){var want=" + esc + ";"
                    "var arts=Array.from(document.querySelectorAll('article'));"
                    "for(var i=0;i<arts.length;i++){if(arts[i].innerText.indexOf(want)>-1){"
                    "var cb=arts[i].querySelector('.tuple-check-box');"
                    "if(cb){cb.click();return 'checked';}return 'no-checkbox';}}"
                    "return 'nocard';})()")
        log("A3 select card checkbox")
        sel = js(CHECK_JS)
        log("   select -> " + str(sel))
        time.sleep(2)

        APPLY_STATE_JS = ("(function(){var b=document.querySelector('.multi-apply-button')||"
                          "Array.from(document.querySelectorAll('button')).find(function(x){"
                          "return /^apply/i.test((x.innerText||'').trim());});"
                          "if(!b)return JSON.stringify({found:false});"
                          "return JSON.stringify({found:true,disabled:!!b.disabled,"
                          "label:(b.innerText||'').trim()});})()")
        ast = str(js(APPLY_STATE_JS) or "")
        log("   apply-button state = " + ast)
        p1 = shot("apply-02-selected-" + time.strftime("%Y%m%d%H%M%S"))
        log("   shot -> " + (str(p1) if p1 else "FAILED"))

        if sel != "checked":
            log("   !! could not select card - BLOCKED")
            ledger("naukri", JOBS_URL[:70], title[:70], "-", "-",
                   "select job card", "BLOCKED", str(p1) if p1 else "none",
                   "select=" + str(sel))
            return 3

        APPLY_JS = ("(function(){var b=document.querySelector('.multi-apply-button')||"
                    "Array.from(document.querySelectorAll('button')).find(function(x){"
                    "return /^apply/i.test((x.innerText||'').trim());});"
                    "if(!b)return 'nobtn'; if(b.disabled)return 'disabled';"
                    "b.click(); return 'clicked-apply';})()")
        log("A4 click Apply")
        ap = js(APPLY_JS)
        log("   apply -> " + str(ap))
        # A4->A5: the recruiter panel opens ASYNC (measured 2026-10-07: a fixed
        # 7 s read at 30,471 chars missed the question; 8 s showed it at 32,013).
        # POLL instead of sleeping; read the question from the recruiter panel node
        # (.chatbot_MessageContainer), NOT the list alignment widget
        # ("Are these jobs relevant for you?" is a SPAN.feed-title on the page).
        log("A5 wait for apply flow / recruiter panel (poll for the QUESTION)")
        panel_q = None
        txt_after = ""
        panel_open = False
        # MEASURED 2026-10-07 01:18: the panel opens with a LOADING spinner and the
        # header "Kindly answer all the recruiter's questions..."; the question
        # renders a few seconds LATER. Breaking on the header read q=None and
        # wrote a false APPLIED. Poll for the QUESTION itself (up to ~50 s).
        for _ in range(25):                       # up to ~50 s
            txt_after = body()
            low = txt_after.lower()
            panel_q = _q_from_panel(js)
            if panel_q:
                panel_open = True
                break
            if ("answer all the recruiter" in low) or ("apply for this job" in low):
                panel_open = True                 # open; keep waiting for the Q
            time.sleep(2)
        after = href()
        low = txt_after.lower()
        # VERIFY: URL left the list OR a real apply-flow signal. Do NOT use
        # 'years of experience' - it appears in job descriptions (false positive).
        FLOW_SIGNALS = ["answer all the recruiter", "recruiter's question",
                        "apply for this job", "submit application",
                        "additional questions", "application submitted"]
        left_list = (after != JOBS_URL and "recommendedjobs" not in after)
        in_flow = panel_open or any(s in low for s in FLOW_SIGNALS)
        moved = left_list or in_flow
        log("A5 after url=" + after[:110])
        log("   left_list=" + str(left_list) + " in_flow=" + str(in_flow)
            + " body_chars=" + str(len(txt_after)))
        tag = "apply-03-after-apply-" + time.strftime("%Y%m%d%H%M%S")
        p = shot(tag)
        log("   shot -> " + (str(p) if p else "FAILED"))

        if not moved:
            log("   !! apply did not open a flow - BLOCKED (honest, not a fake DONE)")
            ledger("naukri", after[:70], title[:70], "-", "-",
                   "open apply flow", "BLOCKED", str(p) if p else "none",
                   "select=" + str(sel) + " apply=" + str(ap))
            return 3

        # CONVERSATIONAL RECRUITER PANEL (2026-10-07): after Apply, the panel
        # asks questions one at a time; the typed answer is SENT with Save and the
        # next question appears. Loop: read question -> answer from record ->
        # READ BACK -> Save -> next. Never invent; never final-submit past a gate.
        seen = set()
        final = None
        saves_ok = 0
        _rounds = 0
        while _rounds < 5:
            _rounds += 1
            rq = _q_from_panel(js) or _find_question(body())
            if not rq:
                break
            if rq in seen:
                break                       # answered; a final submit is next
            ran = _answer_from_record(rq)
            if not ran:
                log("   !! not answerable from record -> BLOCKED: " + rq[:120])
                pf = shot("apply-05-blocked-" + time.strftime("%H%M%S"))
                ledger("naukri", after[:70], title[:70], "-", "-",
                       "recruiter question", "BLOCKED", str(pf) if pf else "none",
                       "UNANSWERABLE Q=" + rq[:150])
                return 4
            seen.add(rq)
            log("   ANSWERING: " + rq[:110] + " -> " + ran)
            elem, actual = _fill_question(js, ran)
            if not (elem and elem != "nofield"
                    and str(actual).strip() == str(ran).strip()):
                log("   !! fill did NOT land (elem=" + str(elem) + " readback="
                    + str(actual)[:30] + ") - BLOCKED")
                pf = shot("apply-05-fillfail-" + time.strftime("%H%M%S"))
                ledger("naukri", after[:70], title[:70], "-", "-",
                       "recruiter question", "BLOCKED", str(pf) if pf else "none",
                       "FILL FAILED elem=" + str(elem) + " readback=" + str(actual)[:40])
                return 4
            sv = _save(js)
            log("   save -> " + str(sv))
            if str(sv).startswith("clicked"):
                saves_ok += 1
            final = shot("apply-06-answered-" + str(_rounds) + "-"
                         + time.strftime("%H%M%S"))
            time.sleep(3)
        if seen and saves_ok:
            ledger("naukri", after[:70], title[:70], "-", "-",
                   "recruiter questions answered", "APPLIED_STEP",
                   str(final) if final else "none",
                   "answered " + str(len(seen)) + " gate(s); saved; no force-submit")
            log("ANSWERED " + str(len(seen)) + " gate(s), Save clicked, read-back verified.")
            return 0
        if seen:
            log("   !! answered but Save did not register -> BLOCKED (no honest submit)")
            ledger("naukri", after[:70], title[:70], "-", "-",
                   "recruiter questions answered", "BLOCKED",
                   str(final) if final else "none",
                   "answered " + str(len(seen)) + " but save not confirmed")
            return 4

        # HONESTY (2026-10-07): an open panel is NOT an application. APPLIED
        # requires an ANSWERED gate OR a submission-success signal. A panel with
        # no rendered question and no success text is BLOCKED, never a fake DONE.
        SUCCESS = ["application submitted", "successfully applied",
                   "you have successfully applied", "applied successfully"]
        submitted = any(s in low for s in SUCCESS)
        if submitted:
            ledger("naukri", after[:70], title[:70], "-", "-",
                   "application submitted", "APPLIED", str(p) if p else "none",
                   "submitted url=" + after[:110])
            log("DONE - submission success signal present.")
            return 0
        log("   !! panel open but no recruiter question and no submission evidence"
            " - BLOCKED (never a fake APPLIED)")
        ledger("naukri", after[:70], title[:70], "-", "-",
               "open apply flow", "BLOCKED", str(p) if p else "none",
               "panel_open=" + str(panel_open) + " no question rendered")
        return 4
    finally:
        try:
            c.close()
            log("client closed cleanly")
        except Exception as e:
            log("close warning: " + str(e))


def _q_from_panel(js):
    """Read the recruiter question from the apply chat panel ONLY.

    MEASURED 2026-10-07: the apply flow opens a chatbot drawer; the question lives
    in DIV.chatbot_MessageContainer. The page ALSO carries SPAN.feed-title
    "Are these jobs relevant for you?" - a list alignment widget, NOT a blocker.
    Return the first recruiter question text, else None.
    """
    PANEL_JS = ("(function(){"
                "var c=document.querySelector('.chatbot_MessageContainer');"
                "if(!c)return '';"
                "var w=c.ownerDocument.createTreeWalker(c,NodeFilter.SHOW_TEXT,null);"
                "var n;while(n=w.nextNode()){var t=(n.nodeValue||'').trim();"
                "if(t.length>8&&t.charAt(t.length-1)==='?')return t;}return '';})()")
    r = js(PANEL_JS)
    if isinstance(r, dict):
        r = r.get("result")
    return r.strip() if isinstance(r, str) and r.strip() else None



def _find_question(body_text):
    """Return the question the APPLY FLOW is actually gating on.

    MEASURED 2026-10-07: after a select-then-apply the page carries TWO question
    shapes - a list-page alignment widget ("Are these jobs relevant for you?",
    the 'Applies (62) / Profile / Preferences' chips) AND the real SaaS recruiter
    panel ("How many years of hands-on experience do you have in GenAI/LLM?").
    The widget is NOT a blocker; treat only the recruiter question as one.
    """
    widget = re.compile(r"relevant for you", re.I)
    recruiter = re.compile(r"recruiter|experience|ctc|notice period|hand", re.I)
    candidates = []
    for ln in (body_text or "").splitlines():
        s = ln.strip()
        if 15 <= len(s) <= 200 and s.endswith("?") and not widget.search(s):
            candidates.append(s)
    for s in candidates:                     # prefer a recruiter-shaped question
        if recruiter.search(s):
            return s
    m = QUESTION_RE.search(body_text or "")  # else the first non-widget question
    if m and not widget.search(m.group(0) or ""):
        return (m.group(0) or "").strip()
    return candidates[0] if candidates else None



def _save(js):
    """Press the recruiter panel's Save (send) button, panel-scoped.
    Returns the click state string."""
    SAVE_JS = ("(function(){function clicky(el){var e=el;for(var i=0;i<4&&e;i++){"
               "if(e.tagName==='BUTTON'||e.getAttribute('role')==='button'||"
               "/btn|button|save|send/i.test(e.className||''))return e;e=e.parentElement;}"
               "return el;}var els=document.querySelectorAll('*'),c=[];"
               "for(var i=0;i<els.length;i++){var e=els[i];"
               "if(e.childElementCount>2)continue;var t=(e.innerText||'').trim();"
               "if(t==='Save'||t==='Send'){var r=e.getBoundingClientRect();"
               "if(r.width>0&&r.height>0)c.push({e:e,x:r.x,t:t});}}"
               "if(!c.length)return 'nobtn';c.sort(function(a,b){return b.x-a.x;});"
               "var tgt=clicky(c[0].e);try{tgt.click();}catch(e){return 'clickerr';}"
               "return 'clicked:'+c[0].t+'@'+Math.round(c[0].x);})()")
    r = js(SAVE_JS)
    if isinstance(r, dict):
        r = r.get("result")
    return r


def _answer_from_record(question):
    rec = HERE / "apply_answers.txt"
    if not rec.exists():
        return None
    qlow = question.lower()
    for line in rec.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        key, _, ans = line.partition("|")
        if key.strip().lower() and key.strip().lower() in qlow:
            return ans.strip()
    return None


def _fill_question(js, answer):
    """Find the recruiter input (panel-scoped), write `answer`, READ IT BACK.
    Return (elem_tag, actual_value). Caller MUST verify actual == answer:
    2026-10-07 the old version returned 'filled' while the field stayed EMPTY."""
    esc = json.dumps(answer)
    FILL_JS = ("(function(){var ans=" + esc + ";"
               "var scope=document.querySelector('.chatbot_MessageContainer');"
               "scope=scope?(scope.parentElement||scope):document;"
               "var f=scope.querySelector('textarea')||"
               "scope.querySelector('input[type=text]')||"
               "scope.querySelector('[contenteditable=true]')||"
               "document.querySelector('input[placeholder]');"
               "if(!f)return JSON.stringify({elem:'nofield',actual:''});"
               "try{f.focus();}catch(e){}"
               "if(f.getAttribute('contenteditable')==='true'){f.textContent=ans;}"
               "else{var d=Object.getOwnPropertyDescriptor((f.tagName==='TEXTAREA'?"
               "window.HTMLTextAreaElement:window.HTMLInputElement).prototype,'value');"
               "if(d&&d.set){d.set.call(f,ans);}else{f.value=ans;}}"
               "try{f.dispatchEvent(new Event('input',{bubbles:true}));"
               "f.dispatchEvent(new Event('change',{bubbles:true}));}catch(e){}"
               "var v=(f.getAttribute('contenteditable')==='true')?"
               "f.textContent:(f.value||'');"
               "var tag=f.tagName+'.'+((f.className||'').toString().split(' ')[0]);"
               "return JSON.stringify({elem:tag,actual:v});})()")
    r = js(FILL_JS)
    if isinstance(r, dict):
        r = r.get("result")
    d = {}
    if isinstance(r, str) and r.strip().startswith("{"):
        try:
            d = json.loads(r)
        except Exception:
            d = {}
    return d.get("elem", ""), d.get("actual", "")


def _top_matched_title():
    try:
        rows = LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None
    for ln in reversed(rows):
        parts = ln.split("\t")
        if len(parts) >= 8 and parts[7].strip() == "MATCHED":
            return parts[3].strip() or None
    return None


if __name__ == "__main__":
    sys.exit(main(sys.argv))
