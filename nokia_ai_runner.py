import subprocess
import time
import wave
import numpy as np
import sounddevice as sd
import ctypes
import sys

ADB = r"D:\anonym\platform-tools\adb.exe"
IQOO_ID = "10BE8135QM001KK"
NOKIA_ID = "G2866620341C0402558"
NOKIA_NUMBER = "9830739230"
GREETING_WAV = r"d:\anonym\greeting_boosted.wav"

def adb(device, cmd):
    res = subprocess.run([ADB, "-s", device] + cmd, capture_output=True, text=True, errors="ignore")
    return res.stdout.strip()

def get_nokia_call_state():
    out = adb(NOKIA_ID, ["shell", "dumpsys", "telephony.registry"])
    states = []
    for line in out.splitlines():
        if "mCallState" in line:
            parts = line.strip().split("=")
            if len(parts) == 2 and parts[1].isdigit():
                states.append(int(parts[1]))
    if any(s == 2 for s in states):
        return 2
    if any(s == 1 for s in states):
        return 1
    return 0

def answer_nokia():
    print("  --> Auto-answering call on Nokia C30 via KEYCODE_HEADSETHOOK...", flush=True)
    adb(NOKIA_ID, ["shell", "input", "keyevent", "79"])

def maximize_laptop_volume():
    VK_VOLUME_UP = 0xAF
    for _ in range(50):
        ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)

def main():
    print("=" * 65, flush=True)
    print("TEST: NOKIA C30 AS AI RECEPTIONIST PHONE (STOCK ANDROID)")
    print("(iQOO calls Nokia -> Nokia answers -> PC plays into Nokia mic)", flush=True)
    print("=" * 65, flush=True)

    out = subprocess.run([ADB, "devices"], capture_output=True, text=True, errors="ignore").stdout
    print(f"Connected devices:\n{out}", flush=True)
    
    if IQOO_ID not in out or NOKIA_ID not in out:
        print("ERROR: One or both devices not found!", flush=True)
        return

    # 1. Maximize volume and load boosted audio
    print("[0] Maximizing laptop volume and loading boosted greeting...", flush=True)
    maximize_laptop_volume()
    with wave.open(GREETING_WAV, "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    # 2. iQOO calls Nokia
    print(f"[1] Placing call from iQOO -> Nokia C30 ({NOKIA_NUMBER})...", flush=True)
    adb(IQOO_ID, ["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{NOKIA_NUMBER}"])

    # 3. Wait for Nokia to ring and answer
    print("[2] Waiting for Nokia C30 to ring...", flush=True)
    t0 = time.time()
    connected = False
    
    while time.time() - t0 < 35:
        st = get_nokia_call_state()
        if st == 1:
            print(f"  [{time.time()-t0:.1f}s] Nokia C30 is RINGING! Answering...", flush=True)
            answer_nokia()
            time.sleep(1.0)
        elif st == 2:
            print(f"  [{time.time()-t0:.1f}s] Nokia C30 is OFFHOOK (CALL CONNECTED)!", flush=True)
            connected = True
            break
        time.sleep(0.4)

    if not connected:
        print("[!] Call did not connect on Nokia within 35 seconds. Aborting.", flush=True)
        return

    # 4. Wait for cellular audio uplink
    print("[3] Waiting 1.0s for carrier audio uplink to establish...", flush=True)
    time.sleep(1.0)

    # 5. Play greeting into Nokia microphone
    print("[4] >>> PLAYING BOOSTED GREETING INTO NOKIA C30 MIC <<<", flush=True)
    t_play = time.time()
    sd.play(audio, sr, blocking=True)
    play_dur = time.time() - t_play
    print(f"[5] Greeting finished ({play_dur:.2f}s). Audio sent into Nokia mic -> cellular uplink!", flush=True)

    # 6. Hold call active for Baba to verify on iQOO
    print("[6] Holding call active for 15 seconds for Baba to verify on iQOO handset...", flush=True)
    time.sleep(15)

    # 7. Clean hangup
    print("[7] Ending call on iQOO...", flush=True)
    adb(IQOO_ID, ["shell", "input", "keyevent", "KEYCODE_ENDCALL"])
    print("[*] TEST COMPLETE!", flush=True)

if __name__ == "__main__":
    main()
