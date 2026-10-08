"""lane_jobs.py - work-order B: read Naukri recommended jobs, gate, report.

WHY: the profile is already 100% complete (ledger 2026-10-06 22:47:52, lane_resume.py).
So work-order A has no incomplete field left. The money step is the job lane, and its
gate is documented in docs/EMPLOYMENT-LANE-MISSION.md:
    score = count of the operator's REAL skills present in the posting text
    gate  = score >= 2, or an explicit fit signal in the posting

This script READS and SCORES. It does not apply. An apply needs the recruiter
question answered, which is a separate, deliberate step (never auto-fired).

Driver pattern: agent360_client.py + JS/.click() only (mouse path is dead).
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

# The operator's REAL skills - from the pinned resume + the live profile headline.
# Never invent one. (kilo_apply_resume.pdf, SHA256 DE81F585...FC339F)
SKILLS = [
    "ai agents", "agentic", "langchain", "rag", "vector", "generative ai",
    "genai", "llm", "prompt", "python", "java", "spring", "node", "nodejs",
    "aws", "cloud", "api", "microservice", "webrtc", "upi", "npci", "payments",
    "fintech", "sqlite", "sql", "rest", "docker", "kubernetes", "architect",
    "backend", "full stack", "fullstack", "team lead", "technical lead",
    "solution architect", "principal", "staff engineer", "engineering manager",
    "distributed", "scalable", "devops", "ci/cd", "git",
]

# Job-card extraction. SELECTOR PROVEN 2026-10-06 22:53: `article` = 63 cards.
# The first version GUESSED a selector with an innerText length filter and matched
# a footer ("Powered by Ambition Box", score 3 on unrelated words). Measure, never guess.
# HREF LAW: the first <a> on a card is an AmbitionBox review link, not the job.
# Prefer job-listings, else the first non-ambitionbox naukri link.
CARDS_JS = (
    "JSON.stringify(Array.from(document.querySelectorAll('article'))"
    ".slice(0,60).map(function(e){"
    "var lines=(e.innerText||'').split(String.fromCharCode(10))"
    ".map(function(s){return s.trim();}).filter(function(s){return s.length>0;});"
    "var t=lines[0]||'';"
    "var as=Array.from(e.querySelectorAll('a')),h='',i;"
    "for(i=0;i<as.length;i++){var x=as[i].getAttribute('href')||'';"
    "if(x.indexOf('job-listings')>-1){h=x;break;}}"
    "if(!h){for(i=0;i<as.length;i++){var y=as[i].getAttribute('href')||'';"
    "if(y.indexOf('ambitionbox')===-1&&"
    "(y.indexOf('naukri.com')>-1||y.charAt(0)=='/')){h=y;break;}}}"
    "if(h&&h.charAt(0)=='/')h='https://www.naukri.com'+h;"
    "return {t:t.slice(0,90),h:h.slice(0,200),"
    "x:lines.join(' | ').slice(0,700)};}))"
)


def log(m):
    print(m, flush=True)


def ledger(portal, source, role, company, score, step, status, receipt, note):
    row = "\t".join([str(date.today()), portal, source, role, company,
                     str(score), step, status, receipt, note])
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(row + "\n")
    log("  LEDGER + " + status + " :: " + (step[:70]))
def main():
    c = A.Agent360Client()
    c.start()
    try:
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
            r = c.call_tool("browser_screenshot", {"format": "png"}) or {}
            for b in r.get("content", []):
                if b.get("type") == "image":
                    p = EVID / (tag + ".png")
                    p.write_bytes(base64.b64decode(b["data"]))
                    return p
            return None

        # NAVIGATE-FIRST LAW: the client attaches to the active tab, which may be
        # about:blank (ledger row 00: chars=0). Always navigate, then read.
        log("B1 navigate -> " + JOBS_URL)
        txt("browser_navigate", {"url": JOBS_URL})
        time.sleep(12)

        url = str(js("location.href") or "")
        body = str(js("document.body.innerText") or "")
        log("   url   = " + url[:110])
        log("   chars = %d" % len(body))

        if len(body) < 800:
            log("   !! page empty/short - recording BLOCKED, not a fake DONE")
            ledger("naukri", url[:60], "-", "-", "-", "open recommended jobs",
                   "BLOCKED", "(none)", "body chars=%d" % len(body))
            return 2

        log("B2 milestone screenshot")
        tag = "40-naukri-recommended-%s" % time.strftime("%Y%m%d-%H%M%S")
        p = shot(tag)
        log("   shot -> " + (str(p) if p else "FAILED"))

        log("B3 parsing job cards ...")
        cards_raw = js(CARDS_JS)
        cards = []
        try:
            cards = json.loads(cards_raw) if isinstance(cards_raw, str) else (cards_raw or [])
        except Exception as e:
            log("   parse fail: %s" % e)

        seen, uniq = set(), []
        for cd in cards:
            t = (cd.get("t") or "").strip()
            if not t or t in seen:
                continue
            seen.add(t)
            uniq.append(cd)

        log("   unique cards: %d" % len(uniq))
        passed = 0
        for i, cd in enumerate(uniq[:25], 1):
            t_ = (cd.get("x") or "")
            low = t_.lower()
            hits = sorted({s for s in SKILLS if s in low})
            score = len(hits)
            gate = score >= 2
            if gate:
                passed += 1
            title = (cd.get("t") or "").strip()[:78]
            msc = re.search(r"(\d{1,3})\s*(?:%|match)", t_, flags=re.I)
            log("   [%02d] score=%-2d %-4s match=%-4s %s" %
                (i, score, "PASS" if gate else "skip",
                 (msc.group(1) if msc else "-"), title or "(no title)"))
            log("        keyskills: %s" % (", ".join(hits[:9]) or "none"))
            src = (cd.get("h") or JOBS_URL).strip()
            ledger("naukri", src[:70], title, "-", score,
                   "jobcard %d read+gated" % i,
                   "MATCHED" if gate else "NO_MATCH",
                   str(p) if p else "(none)",
                   "hits=%s" % ",".join(hits[:8]))

        log("B4 summary")
        log("   evaluated=%d  gate-passed=%d" % (min(len(uniq), 25), passed))
        if passed == 0 and uniq:
            log("   no card cleared the gate - honest result, not a failure to hide")
        return 0
    finally:
        try:
            c.close()
            log("client closed cleanly")
        except Exception as e:
            log("close warning: %s" % e)


if __name__ == "__main__":
    sys.exit(main())