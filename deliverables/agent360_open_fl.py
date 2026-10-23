import sys, json, time, io, os, ctypes

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client
from take_screen import capture

user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
if hdesk:
    user32.SetThreadDesktop(hdesk)

def focus_chrome():
    chrome_hwnd = None
    def enum_cb(hwnd, lp):
        nonlocal chrome_hwnd
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            if 'Chrome' in buf.value or 'Terac' in buf.value or 'Gmail' in buf.value or 'LinkedIn' in buf.value:
                if not chrome_hwnd:
                    chrome_hwnd = hwnd
        return True
    PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumDesktopWindows(hdesk, PROC(enum_cb), 0)
    if chrome_hwnd:
        user32.ShowWindow(chrome_hwnd, 9)
        time.sleep(0.1)
        user32.ShowWindow(chrome_hwnd, 3)
        time.sleep(0.1)
        user32.BringWindowToTop(chrome_hwnd)
        user32.SetForegroundWindow(chrome_hwnd)
        time.sleep(0.5)

print("[1] Focusing Chrome...")
focus_chrome()

print("[2] Starting Agent360Client...")
client = Agent360Client()
client.start()

target_url = "https://www.freelancer.com/projects/azure/Senior-Camel-Integration-Support"
print(f"[3] Navigating to {target_url}...")
res = client.navigate(target_url, new_tab=True)
print("Navigate res:", res)

print("[4] Waiting 8s for load...")
time.sleep(8)
focus_chrome()

title = client.execute_script("document.title")
url = client.execute_script("window.location.href")
print(f"Current Title: {title}")
print(f"Current URL: {url}")

print("[5] Capturing screen...")
capture(r"D:\anonym\deliverables\fl_camel_focused.png")

client.close()
print("Done.")
