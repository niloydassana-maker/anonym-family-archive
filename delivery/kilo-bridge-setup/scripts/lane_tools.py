"""lane_tools.py - the hardened, self-verifying tool layer for the employment lanes.

WHAT THIS IS
------------
One shared library every employment lane imports. It replaces the copy-pasted
scaffold that used to live in lane_jobs / lane_foundit / lane_resume / lane_apply
(identical session + ledger + screenshot + txt/js + wall code in four files, which
is exactly how four copies drift apart).

WHY IT EXISTS (2026-10-07, Baba's "both" decision)
--------------------------------------------------
A reasoning model handed a BARE GOAL fabricated tool executions when it had to
author its own click choreography. The fix is not a better prompt - it is a tool
layer that PROVES every action before returning:
  * a click returns {ok,url,toast,url_changed} - never a bare "clicked"
  * a fill is RE-READ from the DOM - a fill not read back is not a fill
  * a card read MEASURES which selector actually has nodes - never a guess
Lanes therefore state GOALS; the mechanism (selectors, waits, read-backs) lives
here, in ONE tested place.

SAFE TO ADD: the 20+ live a360_* daemons import agent360_client directly and do
NOT import this module, so adding it cannot disturb any running lane.

LAWS OBEYED: screenshot = receipt; JS .click()/keyboard only (the mouse path times
out, PACE 1); never invent a fact; never spend money; never touch login/OTP; ASCII
out; BLOCKED beats a faked DONE.
"""
from __future__ import annotations

import base64
import io
import json
import sys
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

try:                                   # encoding-safe stdout (Windows cp1252)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent

# LEDGER STATUSES (the mission vocabulary - one place, never a typo per lane)
MATCHED, APPLIED, APPLIED_STEP = "MATCHED", "APPLIED", "APPLIED_STEP"
BLOCKED, NO_MATCH, RATE_LIMITED, FAILED, OK = "BLOCKED", "NO_MATCH", "RATE_LIMITED", "FAILED", "OK"

# Portal walls that mean "this is NOT a live session" - ONE definition for all lanes.
# A wall is never declared on length alone (prove_lane.py: a long login page once
# counted as LIVE; the wall is detected BY NAME).
WALL_TOKENS = (
    "jobseeker's login", "jobseeker login", "sign in to continue",
    "please log in", "log in to indeed", "linkedin login", "sign in to linkedin",
    "create an account", "are you a robot", "verify you are human", "captcha",
)


class Lane:
    """Per-run scaffold: evidence dir, ledger, screenshot, wall test, verdict."""

    def __init__(self, portal, name, land=None):
        self.portal = portal
        self.name = name
        root = Path(land).resolve().parent if land else HERE.parent
        self.evid = root / "evidence" / "employment-lane"
        self.evid.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.evid / "ledger.tsv"
        self.counts = {}

    def log(self, msg):
        print(msg, flush=True)

    def tally(self, status, n=1):
        self.counts[status] = self.counts.get(status, 0) + n

    def row(self, source, role, company, score, step, status, receipt, note):
        """One ledger row per action, written as it happens. Never reconstructed."""
        row = "\t".join([str(date.today()), self.portal, str(source), str(role),
                         str(company), str(score), str(step), str(status),
                         str(receipt), str(note)])
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(row + "\n")
        self.tally(status)
        self.log("  LEDGER + %-12s :: %s" % (status, str(step)[:70]))

    def shot(self, client, tag):
        """One screenshot (the receipt). Returns the Path or None."""
        for _ in range(3):
            r = client.call_tool("browser_screenshot", {"format": "png"}) or {}
            for b in r.get("content", []) or []:
                if b.get("type") == "image":
                    p = self.evid / (tag + ".png")
                    p.write_bytes(base64.b64decode(b["data"]))
                    return p
            time.sleep(1)
        return None

    def wall(self, text, title=""):
        """Return the matched wall token when the page is a login/robot wall, else
        None. NEVER on length alone (the prove_lane.py lesson)."""
        low = (text or "").lower()
        ttl = (title or "").lower()
        hit = [w for w in WALL_TOKENS if w in low[:3000] or w in ttl]
        return hit[0] if hit else None

    def summary(self):
        self.log("")
        self.log("SUMMARY %s :: %s" % (self.portal, self.name))
        for k in sorted(self.counts):
            self.log("  %-12s %d" % (k, self.counts[k]))
        self.log("  ledger -> %s" % self.ledger_path)


@contextmanager
def session(lane):
    """One client session for a whole turn (start -> work -> close). FIGHTING-HANDS:
    the caller must be the only driver; the browser-queue gate enforces exclusivity."""
    import agent360_client as A
    client = A.Agent360Client()
    client.start()
    try:
        yield client
    finally:
        try:
            client.close()
            lane.log("client closed cleanly")
        except Exception as exc:
            lane.log("close warning: %s" % exc)


def read_page(client):
    """Return {url, title, body} for the CURRENT tab (one pass, no re-read)."""
    return {
        "url":   str(client._js("location.href") or ""),
        "title": str(client._js("document.title") or ""),
        "body":  str(client._js("document.body.innerText") or ""),
    }


# JOB CARDS - MEASURE the selector, never guess it (generalises lane_foundit's
# sweep-and-pick method; a portal's class names are not stable across releases).
CARD_SELECTORS = {
    "naukri":  ["article", "[class*=jobTuple]", "[class*=srp-job]", "[class*=job-tuple]"],
    "foundit": ["article", "[class*=cardContainer]", "[class*=jobCard]", "[class*=job-card]",
                "[data-job-id]", "[class*=tuple]", "[class*=srp-job]", "[class*=jobTuple]",
                "li[class*=job]"],
    "indeed":  ["[class*=job_seen_beacon]", "[data-jk]", "td.resultContent",
                "div.jobsearch-ResultsList > div"],
    "linkedin": ["li.jobs-search-results__list-item", "div.job-card-container",
                 "[data-job-id]", "li[class*=jobs-search-results]"],
}

_READ_CARDS_JS = (
    "(function(){var sels=%s;var best=null,bestN=0,i;"
    "for(i=0;i<sels.length;i++){var n=document.querySelectorAll(sels[i]).length;"
    "if(n>bestN){bestN=n;best=sels[i];}}"
    "if(!best||bestN===0)return {selector:null,n:0,cards:[]};"
    "var els=Array.prototype.slice.call(document.querySelectorAll(best)).slice(0,%d);"
    "var cards=els.map(function(e){"
    "var lines=(e.innerText||'').split(String.fromCharCode(10))"
    ".map(function(s){return s.trim();}).filter(function(s){return s.length>0;});"
    "var href='',as=e.querySelectorAll('a'),j;"
    "for(j=0;j<as.length;j++){var x=as[j].getAttribute('href')||'';"
    "if(x.indexOf('job')>-1||x.indexOf('/search/')>-1){href=x;break;}}"
    "return {title:(lines[0]||'').slice(0,110),href:href.slice(0,240),"
    "text:lines.join(' | ').slice(0,900)};});"
    "return {selector:best,n:bestN,cards:cards};})()")


def read_cards(client, portal, limit=60):
    """Read job cards from the CURRENT page. Returns {selector,n,cards}. MEASURED:
    the candidate selector with the most real nodes wins; a guessed selector once
    matched a footer (lane_jobs lesson) - this never guesses."""
    sels = CARD_SELECTORS.get(portal, ["article"])
    r = client._js(_READ_CARDS_JS % (json.dumps(sels), int(limit)))
    if isinstance(r, str):
        try:
            r = json.loads(r)
        except Exception:
            r = {}
    if not isinstance(r, dict):
        return {"selector": None, "n": 0, "cards": []}
    cards = [c for c in (r.get("cards") or []) if isinstance(c, dict)]
    return {"selector": r.get("selector"), "n": int(r.get("n") or 0), "cards": cards}


def score_card(text, skills):
    """count of the operator's REAL skills present in a posting; gate = >=2."""
    low = (text or "").lower()
    hits = sorted({s for s in skills if s in low})
    return len(hits), hits


# ----------------------------------------------------------------------------
# RECRUITER PANEL - the measured Naukri apply-flow mechanism, in ONE place.
# The apply flow opens a chatbot drawer; the QUESTION lives in
# DIV.chatbot_MessageContainer. The page ALSO carries SPAN.feed-title "Are these
# jobs relevant for you?" - a list alignment widget, NOT a blocker. Only the panel
# question is treated as a gate (the 2026-10-07 SUPERSEDE lesson, ledger rows 73-74).
# ----------------------------------------------------------------------------
_PANEL_Q_JS = (
    "(function(){var c=document.querySelector('.chatbot_MessageContainer');"
    "if(!c)return '';"
    "var w=c.ownerDocument.createTreeWalker(c,NodeFilter.SHOW_TEXT,null);"
    "var n;while(n=w.nextNode()){var t=(n.nodeValue||'').trim();"
    "if(t.length>8&&t.charAt(t.length-1)==='?')return t;}return '';})()")


def read_recruiter_question(client):
    """Return the recruiter question text from the apply panel ONLY, else None."""
    r = client._js(_PANEL_Q_JS)
    if isinstance(r, dict):
        r = r.get("result")
    return r.strip() if isinstance(r, str) and r.strip() else None


def answer_from_record(question, answers_path):
    """Look up the operator-confirmed answer for a question (substring match).
    Format of answers file: one 'key|answer' per line; '#' comments. Returns the
    answer string or None. NEVER invents one (correctness > convenience)."""
    p = Path(answers_path)
    if not p.exists():
        return None
    qlow = (question or "").lower()
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        key, _, ans = line.partition("|")
        if key.strip().lower() and key.strip().lower() in qlow:
            return ans.strip()
    return None


_FILL_JS = (
    "(function(){var ans=%s;"
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

_SAVE_JS = (
    "(function(){function clicky(el){var e=el;for(var i=0;i<4&&e;i++){"
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


def _fill_panel(client, answer):
    """Write `answer` into the recruiter input and READ IT BACK.
    Returns (elem_tag, actual_value). Caller MUST verify actual == answer: on
    2026-10-07 the old version reported 'filled' while the field stayed EMPTY."""
    r = client._js(_FILL_JS % json.dumps(answer))
    if isinstance(r, str):
        try:
            r = json.loads(r)
        except Exception:
            r = {}
    d = r if isinstance(r, dict) else {}
    if "elem" not in d and isinstance(d.get("result"), dict):
        d = d["result"]              # tolerate a {'result': {...}} wrapper
    return d.get("elem", ""), d.get("actual", "")


def _save_panel(client):
    """Press the recruiter panel's Save/Send control (not a <button> - measured).
    Returns the click state string."""
    r = client._js(_SAVE_JS)
    if isinstance(r, dict):
        r = r.get("result")
    return r


def answer_and_save(client, question, answer):
    """Fill the recruiter answer, VERIFY the read-back, then click Save.
    Returns {ok, elem, actual, expected, save}. ok is True only when the field
    actually holds `answer`. A fill not read back is NOT a fill - this is the exact
    defect (2026-10-07) that produced a false APPLIED_STEP."""
    elem, actual = _fill_panel(client, answer)
    ok = bool(elem) and elem != "nofield" and str(actual).strip() == str(answer).strip()
    save = _save_panel(client) if ok else "skipped(fill-failed)"
    return {"ok": ok, "elem": elem, "actual": actual, "expected": answer, "save": save}


def click_by_text(client, text):
    """VERIFIED click by visible text -> {ok,url,toast,url_changed,clicked}."""
    return client.find_and_click(text)


def fill_then_verify(client, selector, value):
    """VERIFIED fill -> {ok,selector,expected,actual,attempts}."""
    return client.fill_verified(selector, value)