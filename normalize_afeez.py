import subprocess, time, os, base64
import xml.etree.ElementTree as ET

SERIAL = "10BE8135QM001KK"
ADB = r"D:\anonym\platform-tools\adb.exe"
SHOTS_DIR = r"D:\anonym\war-log\shots"

def sh(args, timeout=20):
    cmd = [ADB, "-s", SERIAL, "shell"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()

# Tap Afeez message button at (904, 484)
sh(["input", "tap", "904", "484"])
time.sleep(2)

# Verify chat header
subprocess.run([ADB, "-s", SERIAL, "shell", "uiautomator", "dump", "/sdcard/afeez_fix.xml"])
subprocess.run([ADB, "-s", SERIAL, "pull", "/sdcard/afeez_fix.xml", "D:/anonym/war-log/shots/afeez_fix.xml"])

tree = ET.parse("D:/anonym/war-log/shots/afeez_fix.xml")
header_found = False
for n in tree.getroot().iter("node"):
    if "Arayemi" in n.get("text", ""):
        header_found = True
        break

if not header_found:
    print("Error: Not in Arayemi chat! Aborting.")
    exit(1)

print("Confirmed in Arayemi chat. Typing clarification note...")
sh(["ime", "set", "com.android.adbkeyboard/.AdbIME"])
time.sleep(0.5)

# Focus input field (center)
sh(["input", "tap", "540", "1396"])
time.sleep(0.5)

note = "Please disregard the automated demo snippet above, Arayemi — was running a live test of our search script! Looking forward to our 1-on-1."
b64_note = base64.b64encode(note.encode('utf-8')).decode('utf-8')
sh(["am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_note])
time.sleep(1)

sh(["ime", "set", "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"])
time.sleep(1)

# Dump to find send button
subprocess.run([ADB, "-s", SERIAL, "shell", "uiautomator", "dump", "/sdcard/afeez_fix_typed.xml"])
subprocess.run([ADB, "-s", SERIAL, "pull", "/sdcard/afeez_fix_typed.xml", "D:/anonym/war-log/shots/afeez_fix_typed.xml"])

tree = ET.parse("D:/anonym/war-log/shots/afeez_fix_typed.xml")
send_coords = None
for n in tree.getroot().iter("node"):
    if n.get("content-desc", "").lower() == "send" or n.get("text", "").lower() == "send":
        b = n.get("bounds", "")
        import re
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if m:
            send_coords = ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)
            break

if send_coords:
    sh(["input", "tap", str(send_coords[0]), str(send_coords[1])])
else:
    # default send button location
    sh(["input", "tap", "948", "580"])

time.sleep(2)
subprocess.run([ADB, "-s", SERIAL, "shell", "screencap", "-p", "/sdcard/afeez_normalized.png"])
subprocess.run([ADB, "-s", SERIAL, "pull", "/sdcard/afeez_normalized.png", "D:/anonym/war-log/shots/afeez_normalized.png"])

# Exit back to connections list using action bar back button at (70, 180)
sh(["input", "tap", "70", "180"])
time.sleep(1)
print("Afeez chat cleanly normalized and exited.")
