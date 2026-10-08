"""_patch_loop2.py - APPLIED_STEP must require a CONFIRMED Save click.
Adds saves_ok tracking; if answered but save never registered -> BLOCKED.
Marker-scanned, count==1 each."""
from pathlib import Path
P = Path(__file__).resolve().parent / "lane_apply.py"
s = P.read_text(encoding="utf-8")

pairs = [
    (
        '        seen = set()\n'
        '        final = None\n'
        '        _rounds = 0\n',
        '        seen = set()\n'
        '        final = None\n'
        '        saves_ok = 0\n'
        '        _rounds = 0\n',
    ),
    (
        '            sv = _save(js)\n'
        '            log("   save -> " + str(sv))\n',
        '            sv = _save(js)\n'
        '            log("   save -> " + str(sv))\n'
        '            if str(sv).startswith("clicked"):\n'
        '                saves_ok += 1\n',
    ),
    (
        '        if seen:\n'
        '            ledger("naukri", after[:70], title[:70], "-", "-",\n'
        '                   "recruiter questions answered", "APPLIED_STEP",\n'
        '                   str(final) if final else "none",\n'
        '                   "answered " + str(len(seen)) + " gate(s); no force-submit")\n'
        '            log("ANSWERED " + str(len(seen)) + " gate(s), read-back verified.")\n'
        '            return 0\n',
        '        if seen and saves_ok:\n'
        '            ledger("naukri", after[:70], title[:70], "-", "-",\n'
        '                   "recruiter questions answered", "APPLIED_STEP",\n'
        '                   str(final) if final else "none",\n'
        '                   "answered " + str(len(seen)) + " gate(s); saved; no force-submit")\n'
        '            log("ANSWERED " + str(len(seen)) + " gate(s), Save clicked, read-back verified.")\n'
        '            return 0\n'
        '        if seen:\n'
        '            log("   !! answered but Save did not register -> BLOCKED (no honest submit)")\n'
        '            ledger("naukri", after[:70], title[:70], "-", "-",\n'
        '                   "recruiter questions answered", "BLOCKED",\n'
        '                   str(final) if final else "none",\n'
        '                   "answered " + str(len(seen)) + " but save not confirmed")\n'
        '            return 4\n',
    ),
]

for i, (old, new) in enumerate(pairs):
    n = s.count(old)
    if n != 1:
        raise SystemExit("marker %d count != 1 (got %d) - aborting" % (i, n))
    s = s.replace(old, new, 1)
    print("marker %d ok" % i)

P.write_text(s, encoding="utf-8")
print("patch loop2 ok; lines:", len(s.splitlines()))