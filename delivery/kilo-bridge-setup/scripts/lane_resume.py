"""lane_resume.py - the employment-lane driver, DETERMINISTIC (house pattern).

WHY A SCRIPT AND NOT AN LLM LOOP (evidence/employment-lane/ARCHITECTURE-FINDING-20261006.md):
  crush's system prompt is 111,464 tokens. Groq free killed it with HTTP 413
  (limit 8,000 TPM); Nemotron and Llama both answered with crush's context-SUMMARY
  schema instead of tool calls; deepseek stalled at 0.0% CPU. A free endpoint cannot
  drive `crush run`. This script drives instead - no prompt ceiling, deterministic,
  receipted, seconds per action.

WHAT IT DOES (resume point per evidence/employment-lane/ledger.tsv):
  A1. open the Naukri profile
  A2. screenshot (milestone receipt)
  A3. read the Education / Career / profile-incomplete state as TEXT
  A4. print a compact report and append ONE ledger row
  It NEVER edits anything. It is the eyes, not the hands.

LAWS OBEYED: one screenshot per milestone; JS/.click() only (mouse path is dead);
never touch login/OTP; never spend money; ASCII out; BLOCKED beats a faked DONE.
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

PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def log(m):
    print(m, flush=True)


def ledger(portal, source, role, company, score, step, status, receipt, note):
    row = "\t".join([str(date.today()), portal, source, role, company,
                     str(score), step, status, receipt, note])
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(row + "\n")
    log("  LEDGER + " + status + " :: " + step)
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

        # ---- A1 open profile -------------------------------------------------
        log("A1 navigate -> " + PROFILE_URL)
        txt("browser_navigate", {"url": PROFILE_URL})
        time.sleep(10)

        url = str(js("location.href") or "")
        title = str(js("document.title") or "")
        body = str(js("document.body.innerText") or "")
        log("   url   = " + url[:110])
        log("   title = " + title[:90])
        log("   chars = %d" % len(body))

        # is the session still alive? (LAW 4: never type a credential)
        low = body.lower()
        wall = any(w in low[:3000] or w in title.lower()
                   for w in ("jobseeker's login", "sign in", "please log in"))
        if wall and len(body) < 6000:
            log("   !! LOGIN WALL - report and stop, never type a credential")
            ledger("naukri", url[:60], "-", "-", "-", "session check", "BLOCKED",
                   "(none)", "login wall detected; operator must sign in by hand")
            return 2

        # ---- A2 milestone screenshot ----------------------------------------
        tag = "30-naukri-profile-resume-%s" % time.strftime("%Y%m%d-%H%M%S")
        p = shot(tag)
        log("A2 shot -> " + (str(p) if p else "FAILED"))

        # ---- A3 read the sections that matter --------------------------------
        log("A3 reading profile sections ...")
        for probe, expr in [
            ("section anchors",
             "JSON.stringify(Array.from(document.querySelectorAll('a,div,span'))"
             ".filter(function(e){return /education|career profile|employment|"
             "profile summary|key skills|headline/i.test((e.innerText||'').trim())"
             "&&(e.innerText||'').trim().length<60})"
             ".slice(0,14).map(function(e){return (e.innerText||'').trim().slice(0,50)}))"),
            ("resume headline",
             "((document.querySelector('#resumeHeadlineTxt')||{}).innerText||"
             "(document.querySelector('[class*=headline]')||{}).innerText||'').slice(0,260)"),
        ]:
            try:
                res = js(expr)
                log("   %-16s %s" % (probe + ":", str(res)[:300]))
            except Exception as e:
                log("   %-16s ERROR %s" % (probe + ":", str(e)[:120]))

        inc = re.findall(r"([A-Z][A-Za-z /]{4,48})\s*\n?\s*(?:incomplete|pending|add )",
                         body, flags=re.I)
        log("   incomplete markers: " +
            (", ".join(sorted(set(x.strip() for x in inc))[:12]) or "none found in text"))

        # ---- A4 report + ledger ---------------------------------------------
        log("A4 report")
        log("   session_ok  = %s" % (url.startswith("https://www.naukri.com") and "login" not in low[:1500]))
        log("   handle      = %s" % ("KUNAL DAS" if "kunal" in low else "not found in text"))
        log("   completion  = %s" % ("100" if "100%" in body else "unknown"))
        ledger("naukri", "/mnjuser/profile", "-", "-", "-",
               "resume: profile read + section state captured", "OK",
               str(p) if p else "(none)",
               "driver=lane_resume.py; chars=%d; no edit made" % len(body))
        return 0
    finally:
        try:
            c.close()
            log("client closed cleanly")
        except Exception as e:
            log("close warning: %s" % e)


if __name__ == "__main__":
    sys.exit(main())