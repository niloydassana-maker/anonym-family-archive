"""prove_lane.py - the live proof the setup script's verdict depends on.

IT PROVES FOUR THINGS, ON THE REAL CHROME, IN ONE SESSION:
    1. Agent 360 binds at all (a screenshot forces the bind)
    2. Naukri   is reachable and the operator's session is LIVE (not a login wall)
    3. Foundit  is reachable
    4. Indeed   is reachable
plus it records whether the employment lane's real signals are visible
(profile score, recruiter-question surface).

WHY IT EXISTS: the setup script must never print GREEN because a config file was
written. A config proves nothing. This drives the browser and looks.

VERDICT: prints "LANE-VERDICT: GREEN" only if Agent360 answered AND at least three
portals answered. Everything else is RED, and says exactly what to fix.
"""
import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
OUT = HERE.parent / "evidence" / "L1"

PORTALS = [
    ("Naukri",  "https://www.naukri.com/mnjuser/homepage"),
    ("Foundit", "https://www.foundit.in/"),
    ("Indeed",  "https://in.indeed.com/"),
    ("LinkedIn","https://www.linkedin.com/feed/"),
]


def main():
    c = None
    try:
        import agent360_client as A
    except Exception as e:
        print(f"agent360_client import failed: {e}")
        print("LANE-VERDICT: RED")
        return 1

    try:
        c = A.Agent360Client()
        c.start()
    except Exception as e:
        print(f"client failed to start: {type(e).__name__}: {str(e)[:160]}")
        print("LANE-VERDICT: RED")
        return 1

    try:
        def txt(n, a=None):
            r = c.call_tool(n, a or {}) or {}
            for b in r.get("content", []):
                if b.get("type") == "text":
                    t = b.get("text", "")
                    try:
                        return json.loads(t)
                    except Exception:
                        return t
            return ""

        def js(e):
            r = txt("browser_execute_script", {"code": e})
            return r.get("result") if isinstance(r, dict) else r

        # 1. screenshot forces the extension to bind
        print("binding Agent 360 (screenshot forces it)...")
        bound = False
        try:
            c.call_tool("browser_screenshot", {"format": "png"})
            bound = True
            print("  screenshot returned -> extension bound")
        except Exception as e:
            print(f"  screenshot failed: {type(e).__name__}: {str(e)[:140]}")

        results = []
        for name, url in PORTALS:
            try:
                txt("browser_navigate", {"url": url})
                time.sleep(6)
                body = str(js("document.body.innerText") or "")
                title = str(txt("browser_execute_script",
                                {"code": "document.title"}) or "")
                low = body.lower()
                # A LOGIN PAGE IS NOT A LIVE SESSION. The first version of this proof
                # counted "Jobseeker's Login: Search the Best Jobs" as LIVE because the
                # page was long enough, and printed GREEN for four walls. That is the
                # exact failure this file exists to prevent - so it is detected by name.
                walls = ("jobseeker's login", "jobseeker login", "linkedin login",
                         "sign in to continue", "please log in", "log in to indeed",
                         "captcha", "are you a robot", "verify you are human")
                hit = [w for w in walls if w in low[:2000] or w in str(title).lower()]
                live = len(body) > 200 and not hit
                results.append((name, live, len(body), title[:44]))
                state = "LIVE" if live else ("LOGIN-WALL" if hit else "EMPTY")
                extra = (" <- " + hit[0]) if hit else ""
                print(f"  {name:9} {state:11} chars={len(body):6}  {title[:40]}{extra}")
            except Exception as e:
                results.append((name, False, 0, ""))
                print(f"  {name:9} ERROR {type(e).__name__}: {str(e)[:110]}")

        # employment-lane signals, on Naukri where they live
        print("\nemployment-lane signals on Naukri:")
        try:
            txt("browser_navigate", {"url": "https://www.naukri.com/mnjuser/homepage"})
            time.sleep(6)
            body = str(js("document.body.innerText") or "")
            for probe in ("KUNAL", "Search appearances", "Recruiter actions", "100%"):
                print(f"  {probe:20} {'yes' if probe.lower() in body.lower() else 'no'}")
        except Exception as e:
            print(f"  signal read failed: {str(e)[:110]}")

        live_n = sum(1 for _, live, _, _ in results if live)
        print("")
        print(f"portals with a LIVE session: {live_n}/{len(results)}")
        if live_n == 0:
            print("")
            print("NOTE: every portal answered but none is a logged-in session.")
            print("      The browser reached them; the sessions are signed out.")
        if bound and live_n >= 3:
            print("LANE-VERDICT: GREEN")
            return 0
        print("LANE-VERDICT: RED")
        if live_n < len(results):
            print("  Sign in to the portals by hand, in that Chrome window, then re-run.")
            print("  (The agent never types your login - LAW 4.)")
        print("  Chrome open + Agent 360 extension installed and CONNECTED, then re-run.")
        return 1
    finally:
        if c is not None:
            try:
                c.close()
                print("Agent360Client closed cleanly")
            except Exception as e:
                print(f"close() warning: {e}")


if __name__ == "__main__":
    sys.exit(main())