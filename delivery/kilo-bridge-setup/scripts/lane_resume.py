"""lane_resume.py - the employment-lane driver, DETERMINISTIC (house pattern).

WHY A SCRIPT AND NOT AN LLM LOOP (evidence/employment-lane/ARCHITECTURE-FINDING-20261006.md):
  crush's system prompt is 111,464 tokens. Groq free killed it with HTTP 413
  (limit 8,000 TPM); Nemotron and Llama answered with crush's context-SUMMARY
  schema instead of tool calls; deepseek stalled. A free endpoint cannot drive
  `crush run`. This script drives instead - no prompt ceiling, deterministic,
  receipted, seconds per action.

Thin GOAL-RUNNER (2026-10-07): session, ledger, screenshot, page read and the wall
test live in lane_tools.py. This file states the GOAL: open the Naukri profile, READ
it, report. It NEVER edits anything. It is the eyes, not the hands.
"""
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lane_tools as T  # noqa: E402

PROFILE_URL = "https://www.naukri.com/mnjuser/profile"

SECTION_PROBES = [
    ("section anchors",
     "JSON.stringify(Array.from(document.querySelectorAll('a,div,span'))"
     ".filter(function(e){return /education|career profile|employment|"
     "profile summary|key skills|headline/i.test((e.innerText||'').trim())"
     "&&(e.innerText||'').trim().length<60})"
     ".slice(0,14).map(function(e){return (e.innerText||'').trim().slice(0,50)}))"),
    ("resume headline",
     "((document.querySelector('#resumeHeadlineTxt')||{}).innerText||"
     "(document.querySelector('[class*=headline]')||{}).innerText||'').slice(0,260)"),
]


def main():
    lane = T.Lane("naukri", "profile read")
    with T.session(lane) as c:
        # ---- A1 open profile -------------------------------------------------
        lane.log("A1 navigate -> " + PROFILE_URL)
        c.call_tool("browser_navigate", {"url": PROFILE_URL})
        time.sleep(10)

        page = T.read_page(c)
        lane.log("   url   = " + page["url"][:110])
        lane.log("   title = " + page["title"][:90])
        lane.log("   chars = %d" % len(page["body"]))

        # is the session still alive? (LAW 4: never type a credential)
        wall = lane.wall(page["body"], page["title"])
        if wall and len(page["body"]) < 6000:
            lane.log("   !! LOGIN WALL - report and stop, never type a credential")
            lane.row(page["url"][:60], "-", "-", "-", "session check", T.BLOCKED,
                     "(none)", "login wall detected; sign in by hand")
            return 2

        # ---- A2 milestone screenshot ----------------------------------------
        p = lane.shot(c, "30-naukri-profile-resume-%s" % time.strftime("%Y%m%d-%H%M%S"))
        lane.log("A2 shot -> " + (str(p) if p else "FAILED"))

        # ---- A3 read the sections that matter --------------------------------
        lane.log("A3 reading profile sections ...")
        for probe, expr in SECTION_PROBES:
            try:
                res = c._js(expr)
                lane.log("   %-16s %s" % (probe + ":", str(res)[:300]))
            except Exception as e:
                lane.log("   %-16s ERROR %s" % (probe + ":", str(e)[:120]))

        inc = re.findall(r"([A-Z][A-Za-z /]{4,48})\s*\n?\s*(?:incomplete|pending|add )",
                         page["body"], flags=re.I)
        lane.log("   incomplete markers: " +
                 (", ".join(sorted(set(x.strip() for x in inc))[:12]) or "none found in text"))

        # ---- A4 report + ledger ---------------------------------------------
        low = page["body"].lower()
        lane.log("A4 report")
        lane.log("   session_ok  = %s"
                 % (page["url"].startswith("https://www.naukri.com") and "login" not in low[:1500]))
        lane.log("   handle      = %s" % ("KUNAL DAS" if "kunal" in low else "not found in text"))
        lane.log("   completion  = %s" % ("100" if "100%" in page["body"] else "unknown"))
        lane.row("/mnjuser/profile", "-", "-", "-",
                 "resume: profile read + section state captured", T.OK,
                 str(p) if p else "(none)",
                 "driver=lane_resume.py; chars=%d; no edit made" % len(page["body"]))
        lane.summary()
        return 0


if __name__ == "__main__":
    sys.exit(main())