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

msg = """Saw you're Open to Work. Built job automation applying to perfect-fit roles on LinkedIn/Naukri/Foundit while laptop idles (Rs 499 setup). Demo: https://drive.google.com/file/d/1ToXMovfWEuqRBBRwyJpNxbgUVfQMoAOl/view?usp=sharing. Happy to share more if you accept. — Kunal"""
b64_msg = base64.b64encode(msg.encode('utf-8')).decode('utf-8')

wake_and_unlock()

# Step 0: Ensure we are on Connections list
# If in a chat, back out
sh(["input", "keyevent", "4"])
time.sleep(1)

# Navigate cleanly to connections
sh(["am", "start", "-a", "android.intent.action.VIEW", "-d", "https://www.linkedin.com/mynetwork/invite-connect/connections/"])
time.sleep(2)

shot, xml = snap("batch1_connections_view")
print(f"Connections list opened: {shot}")

targets = ["Harmeet Singh", "Parthiban Sengottyian"]

for target in targets:
    print(f"\n--- Processing {target} ---")
    node = find_node(xml, desc_pat=f"Send a message to {target}")
    if not node:
        print(f"Could not find message button for {target} on screen. Trying text search...")
        node = find_node(xml, text_pat=target)
        if node:
            # Tap row
            sh(["input", "tap", str(node["cx"]), str(node["cy"])])
            time.sleep(2)
            shot_p, xml_p = snap(f"{target}_profile")
            msg_btn = find_node(xml_p, text_pat="Message") or find_node(xml_p, desc_pat="Message")
            if msg_btn:
                sh(["input", "tap", str(msg_btn["cx"]), str(msg_btn["cy"])])
                time.sleep(2)
    else:
        print(f"Found message button for {target} at ({node['cx']}, {node['cy']})")
        sh(["input", "tap", str(node["cx"]), str(node["cy"])])
        time.sleep(2)

    # In chat
    clean_target = target.replace(" ", "_").lower()
    shot_chat, xml_chat = snap(f"{clean_target}_chat_open")
    
    # Find EditText
    edit_node = find_node(xml_chat, class_pat="EditText") or find_node(xml_chat, text_pat="Write a message")
    if edit_node:
        print(f"Focusing EditText at ({edit_node['cx']}, {edit_node['cy']})...")
        sh(["input", "tap", str(edit_node["cx"]), str(edit_node["cy"])])
    else:
        print("Fallback tap for EditText at (540, 1396)...")
        sh(["input", "tap", "540", "1396"])
    time.sleep(1)

    # Set IME to AdbIME and paste
    sh(["ime", "set", "com.android.adbkeyboard/.AdbIME"])
    time.sleep(0.5)
    sh(["am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_msg])
    time.sleep(1)
    sh(["ime", "set", "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"])
    time.sleep(1)

    shot_typed, xml_typed = snap(f"{clean_target}_msg_typed")
    print(f"Typed snapshot: {shot_typed}")

    # Find Send button
    send_node = find_node(xml_typed, desc_pat="Send") or find_node(xml_typed, text_pat="Send")
    if send_node:
        print(f"Tapping Send at ({send_node['cx']}, {send_node['cy']})...")
        sh(["input", "tap", str(send_node["cx"]), str(send_node["cy"])])
    else:
        # Check standard send button coordinates above keyboard
        print("Tapping Send fallback at (948, 580)...")
        sh(["input", "tap", "948", "580"])
    
    time.sleep(3)
    shot_rec, xml_rec = snap(f"{clean_target}_sent_receipt")
    print(f"Sent receipt captured: {shot_rec}")

    # Back out to Connections list
    sh(["input", "keyevent", "4"])
    time.sleep(1)
    shot, xml = snap("connections_return")

print("\nBatch 1 initial targets complete.")
