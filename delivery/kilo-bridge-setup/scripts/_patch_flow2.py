"""_patch_flow2.py - two byte-exact fixes to lane_apply.py:
(1) A5 polls until the QUESTION renders (not the "answer all the recruiter" header),
    because the panel opens with a loading spinner (measured 2026-10-07 01:18).
(2) The "no question" branch must NEVER write APPLIED. APPLIED requires an answered
    gate OR a submission-success signal; otherwise BLOCKED (honesty).
Marker-scanned, count==1 enforced."""
from pathlib import Path
P = Path(__file__).resolve().parent / "lane_apply.py"
s = P.read_text(encoding="utf-8")

R1_old = (
    '        log("A5 wait for apply flow / recruiter panel")\n'
    '        panel_q = None\n'
    '        txt_after = ""\n'
    '        for _ in range(10):                       # up to ~20 s\n'
    '            txt_after = body()\n'
    '            low = txt_after.lower()\n'
    '            panel_q = _q_from_panel(js)\n'
    '            if panel_q or ("answer all the recruiter" in low) \\\n'
    '                    or ("apply for this job" in low):\n'
    '                break\n'
    '            time.sleep(2)\n'
)
R1_new = (
    '        log("A5 wait for apply flow / recruiter panel (poll for the QUESTION)")\n'
    '        panel_q = None\n'
    '        txt_after = ""\n'
    '        panel_open = False\n'
    '        # MEASURED 2026-10-07 01:18: the panel opens with a LOADING spinner and the\n'
    '        # header "Kindly answer all the recruiter\'s questions..."; the question\n'
    '        # renders a few seconds LATER. Breaking on the header read q=None and\n'
    '        # wrote a false APPLIED. Poll for the QUESTION itself (up to ~50 s).\n'
    '        for _ in range(25):                       # up to ~50 s\n'
    '            txt_after = body()\n'
    '            low = txt_after.lower()\n'
    '            panel_q = _q_from_panel(js)\n'
    '            if panel_q:\n'
    '                panel_open = True\n'
    '                break\n'
    '            if ("answer all the recruiter" in low) or ("apply for this job" in low):\n'
    '                panel_open = True                 # open; keep waiting for the Q\n'
    '            time.sleep(2)\n'
)

R2_old = (
    '        left_list = (after != JOBS_URL and "recommendedjobs" not in after)\n'
    '        in_flow = any(s in low for s in FLOW_SIGNALS)\n'
    '        moved = left_list or in_flow\n'
)
R2_new = (
    '        left_list = (after != JOBS_URL and "recommendedjobs" not in after)\n'
    '        in_flow = panel_open or any(s in low for s in FLOW_SIGNALS)\n'
    '        moved = left_list or in_flow\n'
)

R3_old = (
    '        log("   apply context reached (no recruiter question yet)")\n'
    '        ledger("naukri", after[:70], title[:70], "-", "-",\n'
    '               "apply flow opened", "APPLIED", str(p) if p else "none",\n'
    '               "url=" + after[:120])\n'
    '        log("DONE - apply flow open with screenshot.")\n'
    '        return 0\n'
)
R3_new = (
    '        # HONESTY (2026-10-07): an open panel is NOT an application. APPLIED\n'
    '        # requires an ANSWERED gate OR a submission-success signal. A panel with\n'
    '        # no rendered question and no success text is BLOCKED, never a fake DONE.\n'
    '        SUCCESS = ["application submitted", "successfully applied",\n'
    '                   "you have successfully applied", "applied successfully"]\n'
    '        submitted = any(s in low for s in SUCCESS)\n'
    '        if submitted:\n'
    '            ledger("naukri", after[:70], title[:70], "-", "-",\n'
    '                   "application submitted", "APPLIED", str(p) if p else "none",\n'
    '                   "submitted url=" + after[:110])\n'
    '            log("DONE - submission success signal present.")\n'
    '            return 0\n'
    '        log("   !! panel open but no recruiter question and no submission evidence"\n'
    '            " - BLOCKED (never a fake APPLIED)")\n'
    '        ledger("naukri", after[:70], title[:70], "-", "-",\n'
    '               "open apply flow", "BLOCKED", str(p) if p else "none",\n'
    '               "panel_open=" + str(panel_open) + " no question rendered")\n'
    '        return 4\n'
)

for tag, old, new in (("R1", R1_old, R1_new), ("R2", R2_old, R2_new), ("R3", R3_old, R3_new)):
    n = s.count(old)
    if n != 1:
        raise SystemExit("%s marker count != 1 (got %d) - aborting, no change" % (tag, n))
    s = s.replace(old, new, 1)
    print(tag, "ok")

P.write_text(s, encoding="utf-8")
print("patched lane_apply.py; lines now:", len(s.splitlines()))