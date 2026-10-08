"""_patch_findq.py - make _find_question prefer the recruiter-panel question and
never treat the list-page alignment widget ("Are these jobs relevant for you?")
as the apply blocker. Marker-based: replace the body of def _find_question up to
the next top-level def. Idempotent-ish: safe to re-run (it swaps a known shape).
"""
import io

p = r"D:\anonym\delivery\kilo-bridge-setup\scripts\lane_apply.py"
src = io.open(p, encoding="utf-8").read()
lines = src.split("\n")

start = None
for i, l in enumerate(lines):
    if l.startswith("def _find_question("):
        start = i
        break
assert start is not None, "def _find_question not found"

# find the end: first line after start that starts a new top-level def
end = None
for j in range(start + 1, len(lines)):
    if lines[j].startswith("def "):
        end = j
        break
assert end is not None, "end of _find_question not found"

new_func = '''def _find_question(body_text):
    """Return the question the APPLY FLOW is actually gating on.

    MEASURED 2026-10-07: after a select-then-apply the page carries TWO question
    shapes - a list-page alignment widget ("Are these jobs relevant for you?",
    the 'Applies (62) / Profile / Preferences' chips) AND the real SaaS recruiter
    panel ("How many years of hands-on experience do you have in GenAI/LLM?").
    The widget is NOT a blocker; treat only the recruiter question as one.
    """
    widget = re.compile(r"relevant for you", re.I)
    recruiter = re.compile(r"recruiter|experience|ctc|notice period|hand", re.I)
    candidates = []
    for ln in (body_text or "").splitlines():
        s = ln.strip()
        if 15 <= len(s) <= 200 and s.endswith("?") and not widget.search(s):
            candidates.append(s)
    for s in candidates:                     # prefer a recruiter-shaped question
        if recruiter.search(s):
            return s
    m = QUESTION_RE.search(body_text or "")  # else the first non-widget question
    if m and not widget.search(m.group(0) or ""):
        return (m.group(0) or "").strip()
    return candidates[0] if candidates else None


'''.split("\n")

lines[start:end] = new_func
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("PATCH_FINDQ replaced lines", start + 1, "to", end)