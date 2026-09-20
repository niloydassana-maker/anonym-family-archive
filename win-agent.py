"""win-agent.py — OS-level worker for one already-open window.

Multi-process architecture: coordinator (Kilo) spawns one worker process per
target window. Worker drives the REAL screen (focus, click, type, read via
screenshot+OCR-free coordinates) like a human. No debug ports, no launching
browsers — works only with what is already open.

Usage:
  python win-agent.py list                     -> enumerate visible windows
  python win-agent.py focus <title-substring>  -> bring window to front
  python win-agent.py type <title> <text>      -> focus + type (human-paced)
  python win-agent.py key <title> <keys>       -> focus + press key combo
  python win-agent.py scroll <title> <amount>  -> focus + scroll
  python win-agent.py shot <title> <out.png>   -> focus + screenshot of window
  python win-agent.py clickrel <title> <xr> <yr>  -> click at relative pos (0-1)
"""
import sys, time, json
import pygetwindow as gw
import pyautogui

pyautogui.FAILSAFE = True  # slam mouse to top-left corner aborts everything
pyautogui.PAUSE = 0.35     # human-ish pacing built in


def find_window(title_sub):
    matches = [w for w in gw.getAllWindows()
               if w.visible and title_sub.lower() in (w.title or "").lower()]
    if not matches:
        raise SystemExit(json.dumps({"ok": False, "error": f"no window matching {title_sub!r}"}))
    # prefer the largest visible match
    w = max(matches, key=lambda x: (x.width * x.height))
    return w


def list_windows():
    out = []
    for w in gw.getAllWindows():
        if w.visible and (w.title or "").strip():
            out.append({"title": w.title[:100], "x": w.left, "y": w.top,
                        "w": w.width, "h": w.height, "max": w.isMaximized})
    print(json.dumps({"ok": True, "windows": out}))


def focus(title):
    w = find_window(title)
    try:
        if w.isMinimized:
            w.restore()
        w.activate()
    except Exception:
        # fallback: click its titlebar area via alt-tab ring
        pyautogui.hotkey("alt", "tab")
    time.sleep(0.6)
    print(json.dumps({"ok": True, "focused": w.title[:100], "box": [w.left, w.top, w.width, w.height]}))


def do_type(title, text):
    w = find_window(title)
    if w.isMinimized: w.restore()
    w.activate(); time.sleep(0.7)
    pyautogui.write(text, interval=0.03)
    print(json.dumps({"ok": True, "typed": len(text)}))


def do_key(title, keys):
    w = find_window(title)
    if w.isMinimized: w.restore()
    w.activate(); time.sleep(0.7)
    combo = [k.strip() for k in keys.split("+")]
    pyautogui.hotkey(*combo)
    print(json.dumps({"ok": True, "pressed": keys}))


def do_scroll(title, amount):
    w = find_window(title)
    if w.isMinimized: w.restore()
    w.activate(); time.sleep(0.7)
    # move mouse into window center so scroll applies there
    cx, cy = w.left + w.width // 2, w.top + w.height // 2
    pyautogui.moveTo(cx, cy, duration=0.2)
    pyautogui.scroll(int(amount))
    print(json.dumps({"ok": True, "scrolled": amount}))


def do_shot(title, outpng):
    w = find_window(title)
    if w.isMinimized: w.restore()
    w.activate(); time.sleep(0.7)
    box = (max(w.left, 0), max(w.top, 0),
           min(w.width, pyautogui.size().width - max(w.left, 0)),
           min(w.height, pyautogui.size().height - max(w.top, 0)))
    img = pyautogui.screenshot(region=(box[0], box[1], box[2], box[3]))
    img.save(outpng)
    print(json.dumps({"ok": True, "saved": outpng, "box": box}))


def do_clickrel(title, xr, yr):
    w = find_window(title)
    if w.isMinimized: w.restore()
    w.activate(); time.sleep(0.7)
    x = w.left + int(w.width * float(xr))
    y = w.top + int(w.height * float(yr))
    pyautogui.moveTo(x, y, duration=0.25)
    pyautogui.click()
    print(json.dumps({"ok": True, "clicked": [x, y]}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list": list_windows()
    elif cmd == "focus": focus(sys.argv[2])
    elif cmd == "type": do_type(sys.argv[2], sys.argv[3])
    elif cmd == "key": do_key(sys.argv[2], sys.argv[3])
    elif cmd == "scroll": do_scroll(sys.argv[2], sys.argv[3])
    elif cmd == "shot": do_shot(sys.argv[2], sys.argv[3])
    elif cmd == "clickrel": do_clickrel(sys.argv[2], sys.argv[3], sys.argv[4])
    else: print(json.dumps({"ok": False, "error": "unknown command"}))
