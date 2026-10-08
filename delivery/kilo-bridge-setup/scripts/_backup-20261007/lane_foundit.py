"""lane_foundit.py - work-order C: read Foundit job cards, gate, report.

WHY: `lane_jobs.py` proved the Naukri recommended-jobs lane (59 cards, 25 gated,
22 MATCHED). The mission (docs/EMPLOYMENT-LANE-MISSION.md 1; MISSION-RUN.txt step C)
names Foundit next, and audit KIT-AUDIT-MISSING-SCRIPTS-20261007.md 3.1 flagged that
NO Foundit driver existed. This is it - the same shape as lane_jobs.py, on Foundit's
DOM. Foundit is the rebrand of monsterindia.com; the seeker session lives in
Profile 17, so a logged search returns real cards with no login wall.

This script READS and SCORES. It does not apply. An apply is a separate, deliberate
step (lane_apply.py on Naukri is the proven money step; a Foundit apply would need
its own flow driver).

FOUNDIT-DOM WALL (honest, NOT worked around): Foundit is a React SPA and its card
class names are not documented in this house's record the way Naukri's `article` is.
So this driver MEASURES the DOM first - it sweeps candidate selectors, picks the one
with the most real nodes, and reports the selector it used. If no candidate yields
cards, it records BLOCKED with the measured counts rather than guessing. The DOM
result decides whether lane_indeed.py / lane_linkedin.py inherit this pattern.

Driver pattern: agent360_client.py + JS/.click() only (mouse path is dead, PACE 1).
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
EVID.mkdir(parents=True, exist_ok=True)
LEDGER = EVID / "ledger.tsv"
sys.path.insert(0, str(HERE))
import agent360_client as A  # noqa: E402

# Foundit seeker search. A query is required or the page may render no result cards;
# the operator's core lane is AI/agentic, so that is the default.
FOUNDIT_HOME = "https://www.foundit.in/"
DEFAULT_QUERY = "artificial intelligence"

# The operator's REAL skills - IDENTICAL to lane_jobs.py so scores are comparable
# across portals. From the pinned resume + live profile headline. Never invent one.
# (kilo_apply_resume.pdf, SHA256 DE81F585...FC339F)
SKILLS = [
    "ai agents", "agentic", "langchain", "rag", "vector", "generative ai",
    "genai", "llm", "prompt", "python", "java", "spring", "node", "nodejs",
    "aws", "cloud", "api", "microservice", "webrtc", "upi", "npci", "payments",
    "fintech", "sqlite", "sql", "rest", "docker", "kubernetes", "architect",
    "backend", "full stack", "fullstack", "team lead", "technical lead",
    "solution architect", "principal", "staff engineer", "engineering manager",
    "distributed", "scalable", "devops", "ci/cd", "git",
]

# Foundit's own login markers. A logged-OUT search still returns cards, so a wall is
# only declared when the page is SHORT and carries one of these - never on length alone.
WALLS = ("login to apply", "sign in to continue", "jobseeker login",
         "please log in", "create an account", "are you a robot", "captcha")


def log(m):
    print(m, flush=True)


def ledger(portal, source, role, company, score, step, status, receipt, note):
    row = "\t".join([str(date.today()), portal, source, role, company,
                     str(score), step, status, receipt, note])
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(row + "\n")
    log("  LEDGER + " + status + " :: " + step[:70])


# MEASURE, never guess (the lane_jobs.py lesson: a guessed selector matched a footer).
# Sweep candidate selectors, pick the one with the most nodes, and extract card
# text+href. Returns {sel,n,cards}. Never invent a card.
CARDS_JS = (
    "JSON.stringify((function(){"
    "var sels=['article','[class*=cardContainer]','[class*=jobCard]',"
    "'[class*=job-card]','[class*=card]','li[class*=job]','[data-job-id]',"
    "'[class*=tuple]','[class*=srp-job]','[class*=jobTuple]'];"
    "var best=null,bestN=0,i;"
    "for(i=0;i<sels.length;i++){var n=document.querySelectorAll(sels[i]).length;"
    "if(n>bestN){bestN=n;best=sels[i];}}"
    "if(!best||bestN===0)return {sel:null,n:0,cards:[]};"
    "var els=Array.from(document.querySelectorAll(best)).slice(0,60);"
    "var cards=els.map(function(e){"
    "var lines=(e.innerText||'').split(String.fromCharCode(10))"
    ".map(function(s){return s.trim();}).filter(function(s){return s.length>0;});"
    "var as=Array.from(e.querySelectorAll('a')),h='',j;"
    "for(j=0;j<as.length;j++){var x=as[j].getAttribute('href')||'';"
    "if(x.indexOf('job')>-1||x.indexOf('/search/')>-1){h=x;break;}}"
    "return {t:(lines[0]||'').slice(0,90),h:h.slice(0,200),"
    "x:lines.join(' | ').slice(0,700)};});"
    "return {sel:best,n:bestN,cards:cards};})())"
)


def main(argv):
    query = " ".join(argv[1:]).strip() or DEFAULT_QUERY
    search_url = FOUNDIT_HOME + "search/?query=" + query.replace(" ", "%20")
    log("LANE_FOUNDIT start :: query = " + query)

    c = A.Agent360Client()
    try:
        c.start()

        def txt(name, args=None):
            r = c.call_tool(name, args or {}) or {}
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