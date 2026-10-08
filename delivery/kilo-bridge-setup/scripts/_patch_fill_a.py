"""_patch_fill_a.py - HONEST answer step (answer branch).
MEASURED 2026-10-07: _fill_question returned 'filled' while the field stayed
EMPTY -> APPLIED_STEP was a false claim. Now: verify readback == answer, else
BLOCKED. Marker-scanned, count==1 enforced."""
from pathlib import Path
P = Path(__file__).resolve().parent / "lane_apply.py"
s = P.read_text(encoding="utf-8")

old = (
    '            if ans:\n'
    '                log("   answer (from record): " + ans)\n'
    '                _fill_question(js, ans)\n'
    '                time.sleep(3)\n'
    '                p2 = shot("apply-03-question-answered-" + time.strftime("%H%M%S"))\n'
    '                ledger("naukri", after[:70], title[:70], "-", "-",\n'
    '                       "recruiter question answered", "APPLIED_STEP",\n'
    '                       str(p2) if p2 else "none",\n'
    '                       "Q=" + q[:110] + " || A=" + ans[:110])\n'
    '                log("ANSWERED - screenshot + ledger written. No force-submit past a gate.")\n'
    '                return 0\n'
)
new = (
    '            if ans:\n'
    '                log("   answer (from record): " + ans)\n'
    '                # WRITE, then READ BACK. 2026-10-07: the old version wrote the\n'
    '                # wrong element and still reported \'filled\' - the field stayed\n'
    '                # EMPTY, so APPLIED_STEP was a false claim. Verify, or BLOCK.\n'
    '                elem, actual = _fill_question(js, ans)\n'
    '                log("   fill elem=" + str(elem) + " readback=" + str(actual)[:25])\n'
    '                time.sleep(1)\n'
    '                p2 = shot("apply-03-question-answered-" + time.strftime("%H%M%S"))\n'
    '                if elem and elem != "nofield" and str(actual).strip() == str(ans).strip():\n'
    '                    ledger("naukri", after[:70], title[:70], "-", "-",\n'
    '                           "recruiter question answered", "APPLIED_STEP",\n'
    '                           str(p2) if p2 else "none",\n'
    '                           "Q=" + q[:110] + " || A=" + ans[:110])\n'
    '                    log("ANSWERED (read-back verified) - ledger written."\n'
    '                        " No force-submit past a gate.")\n'
    '                    return 0\n'
    '                log("   !! fill did NOT land (elem=" + str(elem) + " readback="\n'
    '                    + str(actual)[:30] + ") - BLOCKED (not a fake APPLIED_STEP)")\n'
    '                ledger("naukri", after[:70], title[:70], "-", "-",\n'
    '                       "recruiter question", "BLOCKED", str(p2) if p2 else "none",\n'
    '                       "FILL FAILED elem=" + str(elem) + " readback=" + str(actual)[:40])\n'
    '                return 4\n'
)

n = s.count(old)
if n != 1:
    raise SystemExit("marker count != 1 (got %d) - aborting" % n)
P.write_text(s.replace(old, new, 1), encoding="utf-8")
print("patch A ok; lines:", len(P.read_text(encoding='utf-8').splitlines()))