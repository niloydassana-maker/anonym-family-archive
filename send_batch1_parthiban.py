import subprocess, time, os, re
import xml.etree.ElementTree as ET

SERIAL = "10BE8135QM001KK"
ADB = r"D:\anonym\platform-tools\adb.exe"
SHOTS_DIR = r"D:\anonym\war-log\shots"

def sh(args):
    cmd = [ADB, "-s", SERIAL, "shell"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
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
    subprocess.run([ADB, "-s", SERIAL, "shell", "screencap", "-p", f"/sdcard/{name}.png"], capture_output=True, timeout=10)
    subprocess.run([ADB, "-s", SERIAL, "pull", f"/sdcard/{name}.png", shot_path], capture_output=True, timeout=10)
    sh(["uiautomator", "dump", f"/sdcard/{name}.xml"])
    subprocess.run([ADB, "-s", SERIAL, "pull", f"/sdcard/{name}.xml", xml_path], capture_output=True, timeout=10)
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

# Step 1: Tap Message icon for Parthiban Sengottyian
print("Tapping Message icon for Parthiban at (904, 489)...")
sh(["input", "tap", "904", "489"])
time.sleep(2)

shot, xml = snap("parthiban_chat_open")
print(f"Chat open snapped: {shot}")

# Step 2: Locate EditText in chat
cx, cy, b = find_bounds(xml, target_class="android.widget.EditText")
if not cx:
    cx, cy, b = find_bounds(xml, target_text="Write a message")
if not cx:
    # default fallback coordinate for message input
    cx, cy = 540, 2185

print(f"Input field at ({cx}, {cy}). Tapping to focus...")
sh(["input", "tap", str(cx), str(cy)])
time.sleep(1)

# Step 3: Type message
msg = "Saw you're Open to Work. Built job automation applying to perfect-fit roles on LinkedIn/Naukri/Foundit while laptop idles (Rs 499 setup). Demo: https://drive.google.com/file/d/1ToXMovfWEuqRBBRwyJpNxbgUVfQMoAOl/view?usp=sharing. Happy to share more if you accept. - Kunal"
safe = msg.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"').replace("&", "\\&")

print("Typing message...")
sh(["input", "text", safe])
time.sleep(1.5)

shot, xml = snap("parthiban_msg_typed")
print(f"Message typed snapped: {shot}")

# Step 4: Find Send button
scx, scy, sb = find_bounds(xml, target_desc="Send")
if not scx:
    scx, scy, sb = find_bounds(xml, target_text="Send")
if not scx:
    # In LinkedIn, send button is often at bottom right [948, 2220] or [960, 2185]
    print("Send button bounds not explicitly found by text/desc, checking around (980, 2185)...")
    scx, scy = 980, 2185

print(f"Tapping send at ({scx}, {scy})...")
sh(["input", "tap", str(scx), str(scy)])
time.sleep(3)

shot, xml = snap("parthiban_sent_receipt")
print(f"Receipt snapped: {shot}")

# Step 5: Press back to return to connections list
sh(["input", "keyevent", "4"])
time.sleep(1.5)
snap("after_parthiban_back")
print("Returned to connections list.")
