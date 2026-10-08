import subprocess, time, os, base64

SERIAL = "10BE8135QM001KK"
ADB = r"D:\anonym\platform-tools\adb.exe"
SHOTS_DIR = r"D:\anonym\war-log\shots"

def sh(args, timeout=20):
    cmd = [ADB, "-s", SERIAL, "shell"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()

# 1. Switch to AdbIME for 100% exact character input without predictive mangling
print("Setting IME to AdbIME...")
sh(["ime", "set", "com.android.adbkeyboard/.AdbIME"])
time.sleep(1)

# 2. Focus the message input field
print("Tapping EditText to focus...")
sh(["input", "tap", "540", "1396"])
time.sleep(1)

# 3. Base64 encode the exact text
msg = """Hi Arayemi, apologies if I sounded abrupt earlier. I am very glad to get on a 1-on-1 call with you to discuss the role. Please let me know what day and time works best for you, or feel free to share your calendar link. You can also share the JD here or to isearch.xsolve@gmail.com so I can review it beforehand. Looking forward to speaking!

Warm regards,
Kunal"""

b64_msg = base64.b64encode(msg.encode('utf-8')).decode('utf-8')
print("Broadcasting base64 message via AdbIME...")
sh(["am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64_msg])
time.sleep(1.5)

# 4. Restore original Gboard IME
print("Restoring Gboard IME...")
sh(["ime", "set", "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"])
time.sleep(1)

# 5. Take screenshot of the pasted text (NO SEND - WAITING FOR BABA'S APPROVAL)
shot_path = os.path.join(SHOTS_DIR, "afeez_pasted_for_approval.png")
subprocess.run([ADB, "-s", SERIAL, "shell", "screencap", "-p", "/sdcard/afeez_pasted_for_approval.png"], capture_output=True, timeout=15)
subprocess.run([ADB, "-s", SERIAL, "pull", "/sdcard/afeez_pasted_for_approval.png", shot_path], capture_output=True, timeout=15)
print(f"Screenshot saved to: {shot_path}")
print("WAITING FOR BABA'S APPROVAL BEFORE SENDING.")
