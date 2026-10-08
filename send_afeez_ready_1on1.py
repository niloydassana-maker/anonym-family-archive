import subprocess, time, os, re
import xml.etree.ElementTree as ET

SERIAL = "10BE8135QM001KK"
ADB = r"D:\anonym\platform-tools\adb.exe"
SHOTS_DIR = r"D:\anonym\war-log\shots"

def sh(args, timeout=20):
    cmd = [ADB, "-s", SERIAL, "shell"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()

def wake_and_unlock():
    power = sh(["dumpsys", "power"])
    if "mWakefulness=Asleep" in power:
        sh(["input", "keyevent", "224"])
        time.sleep(0.5)
    sh(["wm", "dismiss-keyguard"])
    time.sleep(0.5)
    sh(["input", "swipe", "540", "1800", "540", "500", "300"])
    time.sleep(0.5)
    window = sh(["dumpsys", "window"])
    if "KeyguardBouncer" in window or "pin" in window.lower():
        sh(["input", "text", "2828"])
        time.sleep(0.5)
        sh(["input", "keyevent", "66"])
        time.sleep(1)

def snap(name):
    shot_path = os.path.join(SHOTS_DIR, f"{name}.png")
    xml_path = os.path.join(SHOTS_DIR, f"{name}.xml")
    subprocess.run([ADB, "-s", SERIAL, "shell", "screencap", "-p", f"/sdcard/{name}.png"], capture_output=True, timeout=15)
    subprocess.run([ADB, "-s", SERIAL, "pull", f"/sdcard/{name}.png", shot_path], capture_output=True, timeout=15)
    sh(["uiautomator", "dump", f"/sdcard/{name}.xml"])
    subprocess.run([ADB, "-s", SERIAL, "pull", f"/sdcard/{name}.xml", xml_path], capture_output=True, timeout=15)
    return shot_path, xml_path

def find_bounds(xml_file, target_text=None, target_desc=None, target_class=None):
    tree = ET.parse(xml_file)
    for n in tree.getroot().iter("node"):
        t = n.get("text", "")
        d = n.get("content-desc", "")
        c = n.get("class", "")
        b = n.get("bounds", "")
        
        match = True
        if target_text and target_text.lower() not in t.lower():
            match = False
        if target_desc and target_desc.lower() not in d.lower():
            match = False
        if target_class and target_class != c:
            match = False
            
        if match and b:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
            if m:
                cx = (int(m.group(1)) + int(m.group(3))) // 2
                cy = (int(m.group(2)) + int(m.group(4))) // 2
                return cx, cy, b
    return None, None, None

wake_and_unlock()

# Step 1: Tap Message icon for Arayemi Afeez at (904, 484)
print("Tapping Message icon for Arayemi Afeez at (904, 484)...")
sh(["input", "tap", "904", "484"])
time.sleep(2)

shot, xml = snap("afeez_chat_open")
print(f"Chat open snapped: {shot}")

# Step 2: Locate EditText in chat
cx, cy, b = find_bounds(xml, target_class="android.widget.EditText")
if not cx:
    cx, cy, b = find_bounds(xml, target_text="Write a message")
if not cx:
    cx, cy = 540, 2185

print(f"Input field at ({cx}, {cy}). Tapping to focus...")
sh(["input", "tap", str(cx), str(cy)])
time.sleep(1)

# Step 3: Type message
msg = "Hi Arayemi, apologies if I sounded abrupt earlier. I am very glad to get on a 1-on-1 with you to discuss the role. Please let me know what day and time works best for you, or feel free to share your calendar link. You can also share the JD here or to isearch.xsolve@gmail.com so I can review it beforehand. Looking forward to speaking. - Warm regards, Kunal"

# Escape for ADB input text
safe = msg.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"').replace("&", "\\&")

print("Typing message...")
sh(["input", "text", safe])
time.sleep(2)

shot, xml = snap("afeez_ready_msg_typed")
print(f"Message typed snapped: {shot}")

# Step 4: Find Send button
scx, scy, sb = find_bounds(xml, target_desc="Send")
if not scx:
    scx, scy, sb = find_bounds(xml, target_text="Send")
if not scx:
    scx, scy = 980, 2185

print(f"Tapping send at ({scx}, {scy})...")
sh(["input", "tap", str(scx), str(scy)])
time.sleep(3)

shot, xml = snap("afeez_ready_1on1_receipt")
print(f"Receipt snapped: {shot}")

# Step 5: Sleep phone
sh(["input", "keyevent", "26"])
print("Phone asleep. Send complete!")
