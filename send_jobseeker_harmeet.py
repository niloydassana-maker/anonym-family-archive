import subprocess, time, os, re, base64
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

def snap(name):
    shot_path = os.path.join(SHOTS_DIR, f"{name}.png")
    xml_path = os.path.join(SHOTS_DIR, f"{name}.xml")
    subprocess.run([ADB, "-s", SERIAL, "shell", "screencap", "-p", f"/sdcard/{name}.png"], capture_output=True, timeout=15)
    subprocess.run([ADB, "-s", SERIAL, "pull", f"/sdcard/{name}.png", shot_path], capture_output=True, timeout=15)
    sh(["uiautomator", "dump", f"/sdcard/{name}.xml"])
    subprocess.run([ADB, "-s", SERIAL, "pull", f"/sdcard/{name}.xml", xml_path], capture_output=True, timeout=15)
    return shot_path, xml_path

def find_node(xml_file, text_pat=None, desc_pat=None, class_pat=None):
    if not os.path.exists(xml_file):
        return None
    tree = ET.parse(xml_file)
    for n in tree.getroot().iter("node"):
        t = n.get("text", "")
        d = n.get("content-desc", "")
        c = n.get("class", "")
        b = n.get("bounds", "")
        
        match = True
        if text_pat and not re.search(text_pat, t, re.IGNORECASE):
            match = False
        if desc_pat and not re.search(desc_pat, d, re.IGNORECASE):
            match = False
        if class_pat and not re.search(class_pat, c, re.IGNORECASE):
            match = False
            
        if match and b:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
            if m:
                cx = (int(m.group(1)) + int(m.group(3))) // 2
                cy = (int(m.group(2)) + int(m.group(4))) // 2
                return {"cx": cx, "cy": cy, "bounds": b, "text": t, "desc": d, "class": c}
    return None

wake_and_unlock()

# Step 1: Open Connections list
sh(["am", "start", "-a", "android.intent.action.VIEW", "-d", "https://www.linkedin.com/mynetwork/invite-connect/connections/"])
time.sleep(2)

shot_list, xml_list = snap("harmeet_conn_view")
print(f"Connections snapshot: {shot_list}")

node = find_node(xml_list, desc_pat="Send a message to Harmeet Singh") or find_node(xml_list, text_pat="Harmeet Singh")
if not node:
    print("Harmeet Singh not in immediate view, scrolling down slightly...")
    sh(["input", "swipe", "540", "1500", "540", "800", "300"])
    time.sleep(1.5)
    shot_list, xml_list = snap("harmeet_conn_scroll")
    node = find_node(xml_list, desc_pat="Send a message to Harmeet Singh") or find_node(xml_list, text_pat="Harmeet Singh")

if not node:
    print("FATAL ERROR: Harmeet Singh not found on screen. Aborting.")
    exit(1)

print(f"Tapping Harmeet message at ({node['cx']}, {node['cy']})...")
sh(["input", "tap", str(node["cx"]), str(node["cy"])])
time.sleep(2)

shot_chat, xml_chat = snap("harmeet_chat_view")

# STRICT VERIFICATION: Verify header says Harmeet
header_match = find_node(xml_chat, text_pat="Harmeet")
if not header_match:
    print("FATAL ERROR: Chat header DOES NOT match Harmeet! Aborting immediately.")
    exit(1)

print(f"VERIFIED: Inside Harmeet Singh's chat. Header: {header_match['text']}")

# Locate EditText
edit_node = find_node(xml_chat, class_pat="EditText") or find_node(xml_chat, text_pat="Write a message")
cx = edit_node["cx"] if edit_node else 540
cy = edit_node["cy"] if edit_node else 1396

print(f"Focusing message input at ({cx}, {cy})...")
sh(["input", "tap", str(cx), str(cy)])
time.sleep(0.5)

msg = """Saw you're Open to Work. Built job automation applying to perfect-fit roles on LinkedIn/Naukri/Foundit while laptop idles (Rs 499 setup). Demo: https://drive.google.com/file/d/1ToXMovfWEuqRBBRwyJpNxbgUVfQMoAOl/view?usp=sharing. Happy to share more if you accept. — Kunal"""

b64_msg = base64.b64encode(msg.encode('utf-8')).decode('utf-8')

print("Pasting message via AdbIME...")
sh(["ime", "set", "com.android.adbkeyboard/.AdbIME"])
time.sleep(0.5)
sh(["am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_msg])
time.sleep(1)
sh(["ime", "set", "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"])
time.sleep(1)

shot_typed, xml_typed = snap("harmeet_msg_typed_verified")
print(f"Typed snapshot: {shot_typed}")

# Find Send button
send_node = find_node(xml_typed, desc_pat="Send") or find_node(xml_typed, text_pat="Send")
if send_node:
    print(f"Tapping Send at ({send_node['cx']}, {send_node['cy']})...")
    sh(["input", "tap", str(send_node["cx"]), str(send_node["cy"])])
else:
    print("Tapping Send fallback at (948, 580)...")
    sh(["input", "tap", "948", "580"])

time.sleep(3)
shot_rec, xml_rec = snap("harmeet_sent_receipt_verified")
print(f"RECEIPT CAPTURED: {shot_rec}")

# Back out safely via top-left action bar button (70, 180)
sh(["input", "tap", "70", "180"])
time.sleep(1)

# Put phone to sleep
sh(["input", "keyevent", "26"])
print("Complete. Phone asleep.")
