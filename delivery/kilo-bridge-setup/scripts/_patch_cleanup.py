"""_patch_cleanup.py - drop two dead spans from lane_apply.py after the
select-then-apply patch:
  1. the now-unused APPLY_MARKERS list (its 'years of experience' token was the
     false-positive that faked a 'moved' flow; the live code uses FLOW_SIGNALS)
  2. an unused `before = href()` leftover from the old CLICK block
Marker-based (line scan), never exact-whitespace matching, so it cannot churn.
"""
import io

p = r"D:\anonym\delivery\kilo-bridge-setup\scripts\lane_apply.py"
src = io.open(p, encoding="utf-8").read()
lines = src.split("\n")

out = []
i = 0
removed = 0
while i < len(lines):
    l = lines[i]
    if l.startswith("APPLY_MARKERS = ["):
        j = i
        while j < len(lines) and lines[j].strip() != "]":
            j += 1
        i = j + 1
        if i < len(lines) and lines[i].strip() == "":
            i += 1
        removed += 1
        continue
    if l.strip() == "before = href()":
        removed += 1
        i += 1
        continue
    out.append(l)
    i += 1

io.open(p, "w", encoding="utf-8").write("\n".join(out))
print("CLEANUP removed spans:", removed)