"""_patch_flow.py - harden lane_apply.py after the live 2026-10-07 run:
  A) replace the fixed time.sleep(7) with a POLL for the async recruiter panel
     (measured: 7 s read at 30,471 chars missed the question; 8 s showed it).
  B) prefer the PANEL question over the list widget in the `q =` line.
  C) add module-level _q_from_panel(js) reading DIV.chatbot_MessageContainer only
     (the "Are these jobs relevant for you?" SPAN.feed-title is NOT a blocker).
  D) retry screenshots up to 3x so a transient image read never loses a receipt.
Marker-based line scan (the editor tool mangles this file's quoting).
"""
import io

p = r"D:\anonym\delivery\kilo-bridge-setup\scripts\lane_apply.py"
src = io.open(p, encoding="utf-8").read()
lines = src.split("\n")

# ---- A) the A4->A5 read block --------------------------------------------
s7 = None
for i, l in enumerate(lines):
    if l.strip() == "time.sleep(7)" and any("ap = js(APPLY_JS)" in lines[k]
                                            for k in range(max(0, i - 3), i)):
        s7 = i
        break
assert s7 is not None, "time.sleep(7) anchor not found"
e7 = None
for j in range(s7, len(lines)):
    if lines[j].strip() == "low = txt_after.lower()":
        e7 = j
        break
assert e7 is not None, "low = txt_after.lower() anchor not found"

block_a = '''        # A4->A5: the recruiter panel opens ASYNC (measured 2026-10-07: a fixed
        # 7 s read at 30,471 chars missed the question; 8 s showed it at 32,013).
        # POLL instead of sleeping; read the question from the recruiter panel node
        # (.chatbot_MessageContainer), NOT the list alignment widget
        # ("Are these jobs relevant for you?" is a SPAN.feed-title on the page).
        log("A5 wait for apply flow / recruiter panel")
        panel_q = None
        txt_after = ""
        for _ in range(10):                       # up to ~20 s
            txt_after = body()
            low = txt_after.lower()
            panel_q = _q_from_panel(js)
            if panel_q or ("answer all the recruiter" in low) \\
                    or ("apply for this job" in low):
                break
            time.sleep(2)
        after = href()
        low = txt_after.lower()'''.split("\n")
lines[s7:e7 + 1] = block_a

# ---- B) prefer the panel question ----------------------------------------
b = None
for i, l in enumerate(lines):
    if l.strip() == "q = _find_question(txt_after)":
        b = i
        break
assert b is not None, "q = _find_question anchor not found"
lines[b] = "        q = panel_q or _find_question(txt_after)"

# ---- C) insert _q_from_panel before def _find_question -------------------
c = None
for i, l in enumerate(lines):
    if l.startswith("def _find_question("):
        c = i
        break
assert c is not None, "def _find_question anchor not found"

helper = '''def _q_from_panel(js):
    """Read the recruiter question from the apply chat panel ONLY.

    MEASURED 2026-10-07: the apply flow opens a chatbot drawer; the question lives
    in DIV.chatbot_MessageContainer. The page ALSO carries SPAN.feed-title
    "Are these jobs relevant for you?" - a list alignment widget, NOT a blocker.
    Return the first recruiter question text, else None.
    """
    PANEL_JS = ("(function(){"
                "var c=document.querySelector('.chatbot_MessageContainer');"
                "if(!c)return '';"
                "var w=c.ownerDocument.createTreeWalker(c,NodeFilter.SHOW_TEXT,null);"
                "var n;while(n=w.nextNode()){var t=(n.nodeValue||'').trim();"
                "if(t.length>8&&t.charAt(t.length-1)==='?')return t;}return '';})()")
    r = js(PANEL_JS)
    if isinstance(r, dict):
        r = r.get("result")
    return r.strip() if isinstance(r, str) and r.strip() else None


'''.split("\n")
lines[c:c] = helper

# ---- D) retry the screenshot helper --------------------------------------
s = None
for i, l in enumerate(lines):
    if l.strip().startswith("def shot(tag)"):
        s = i
        break
assert s is not None, "def shot anchor not found"
e = None
for j in range(s + 1, len(lines)):
    if lines[j].strip() == "return None":
        e = j
        break
assert e is not None, "shot end anchor not found"

shot_new = '''        def shot(tag):
            for _attempt in range(3):
                r = c.call_tool("browser_screenshot", {"format": "png"}) or {}
                for b in r.get("content", []):
                    if b.get("type") == "image":
                        p = EVID / (tag + ".png")
                        p.write_bytes(base64.b64decode(b["data"]))
                        return p
                time.sleep(1)
            return None'''.split("\n")
lines[s:e + 1] = shot_new

io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("PATCH_FLOW applied; lines now", len(lines))