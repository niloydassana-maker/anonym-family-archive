"""tile-windows.py — lay out the already-open account windows into a fixed grid.

No window is launched, none is closed, none overlaps. Each account window is
moved+resized to its own dedicated tile on the desktop so multiple agents can
work side by side without covering each other.

Layout (1600x900 screen, adjustable via GRID below):
  +----------------+----------------+
  | LinkedIn       | Indeed         |
  +----------------+----------------+
  | Gmail          | Naukri/Foundit |
  +----------------+----------------+
Taskbar-safe: grid height leaves 40px for taskbar.
"""
import sys
import pygetwindow as gw

SW, SH = 1600, 900
TASKBAR = 40
GAP = 2

# title-substring -> tile slot (col, row)
GRID = {
    "linkedin": (0, 0),
    "indeed": (1, 0),
    "gmail": (0, 1),
    "mynaukri": (1, 1),
    "foundit": (1, 1),   # shares slot with naukri, only one at a time focused
}

def tile():
    tw = SW // 2 - GAP
    th = (SH - TASKBAR) // 2 - GAP
    placed = []
    used = set()
    for w in gw.getAllWindows():
        t = (w.title or "").lower()
        if not w.visible or not t.strip():
            continue
        key = None
        for name in GRID:
            if name in t and name not in used:
                key = name
                break
        if not key:
            continue
        used.add(key)
        col, row = GRID[key]
        try:
            if w.isMaximized:
                w.restore()
            w.resizeTo(tw - GAP * 2, th - GAP * 2)
            w.moveTo(col * (tw + GAP), row * (th + GAP))
            placed.append({"account": key, "title": w.title[:60],
                           "box": [w.left, w.top, w.width, w.height]})
        except Exception as e:
            placed.append({"account": key, "error": str(e)[:60]})
    return placed

if __name__ == "__main__":
    import json
    print(json.dumps(tile(), indent=1))
