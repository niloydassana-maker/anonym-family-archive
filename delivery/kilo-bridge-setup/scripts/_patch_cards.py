"""_patch_cards.py - byte-exact patch: poll for SPA-hydrated job cards.
MEASURED 2026-10-07 01:13: `article` count is 0 at +10s on a COLD tab and 63 at
+12s. A fixed sleep(10) after navigate therefore reads an empty list -> false
"card not found". Replace the single FIND_JS call with a bounded poll."""
from pathlib import Path

P = Path(__file__).resolve().parent / "lane_apply.py"
s = P.read_text(encoding="utf-8")

old = (
    '        idx = js(FIND_JS)\n'
    '        log("A2 card index = " + str(idx))\n'
)
new = (
    '        # A1b: the recommended-jobs list is an SPA - cards hydrate AFTER navigate.\n'
    '        # MEASURED 2026-10-07 01:13: `article` count 0 at +10s on a COLD tab, 63\n'
    '        # at +12s. A fixed sleep(10) read an empty list -> false "card not found".\n'
    '        # POLL for the card (up to ~30s) instead of trusting one read.\n'
    '        idx = -1\n'
    '        for _ in range(15):\n'
    '            idx = js(FIND_JS)\n'
    '            if idx is not None and int(idx) >= 0:\n'
    '                break\n'
    '            arts_n = js("document.querySelectorAll(\'article\').length")\n'
    '            log("   A2 wait cards: articles=" + str(arts_n) + " idx=" + str(idx))\n'
    '            time.sleep(2)\n'
    '        log("A2 card index = " + str(idx))\n'
)

n = s.count(old)
if n != 1:
    raise SystemExit("MARKER COUNT != 1 (got %d) - aborting, no change" % n)
P.write_text(s.replace(old, new, 1), encoding="utf-8")
print("patched lane_apply.py: cards poll inserted")
print("lines now:", len(P.read_text(encoding='utf-8').splitlines()))