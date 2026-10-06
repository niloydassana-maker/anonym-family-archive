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
GREETING_WAV = r"d:\anonym\greeting.wav"

def adb(device, cmd):
    res = subprocess.run([ADB, "-s", device] + cmd, capture_output=True, text=True, errors="ignore")
    return res.stdout.strip()

def get_call_state():
    out = adb(IQOO_ID, ["shell", "dumpsys", "telephony.registry"])
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

def answer_iqoo():
    print("  --> Answering incoming call on iQOO via ADB...", flush=True)
    adb(IQOO_ID, ["shell", "input", "keyevent", "79"])

def maximize_laptop_volume():
    VK_VOLUME_UP = 0xAF
    for _ in range(50):
        ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)

def main():
    print("=" * 60, flush=True)
    print("KILO VOICE ASSISTANT: PURE ADB + LAPTOP MIC TEST (SOUNDDEVICE)", flush=True)
    print("=" * 60, flush=True)
    
    # Check devices
    out = subprocess.run([ADB, "devices"], capture_output=True, text=True, errors="ignore").stdout
    print(f"Connected devices:\n{out}", flush=True)
    
    if IQOO_ID not in out or NOKIA_ID not in out:
        print("ERROR: One or both devices not found!", flush=True)
        return

    # 1. Preload audio and maximize volume
    print("[0] Maximizing laptop master volume and loading greeting.wav...", flush=True)
    maximize_laptop_volume()
    with wave.open(GREETING_WAV, "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    print("[1] Placing call from Nokia C30 (+919830739230) -> iQOO (8617216163)...", flush=True)
    adb(NOKIA_ID, ["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", "tel:8617216163"])
    
    print("[2] Waiting for iQOO to ring and auto-answering via ADB...", flush=True)
    t0 = time.time()
    connected = False
    
    while time.time() - t0 < 35:
        st = get_call_state()
        if st == 1:
            print(f"  [{time.time()-t0:.1f}s] iQOO is RINGING! Answering...", flush=True)
            answer_iqoo()
            time.sleep(0.8)
        elif st == 2:
            print(f"  [{time.time()-t0:.1f}s] iQOO is OFFHOOK (CALL CONNECTED)!", flush=True)
            connected = True
            break
        time.sleep(0.4)
        
    if not connected:
        print("[!] Call did not connect within 35 seconds. Aborting.", flush=True)
        return
        
    # Wait 1.0s for carrier audio uplink to establish
    print("[3] Waiting 1.0s for carrier audio channel to stabilize...", flush=True)
    time.sleep(1.0)
    
    print("[4] >>> PLAYING GREETING AT FULL VOLUME VIA SOUNDDEVICE INTO iQOO MIC <<<", flush=True)
    t_play = time.time()
    sd.play(audio, sr, blocking=True)
    play_dur = time.time() - t_play
    print(f"[5] Greeting finished ({play_dur:.2f}s). Audio sent into iQOO mic -> cellular uplink!", flush=True)
    
    print("[6] Holding call active for 15 seconds for Baba to verify on Nokia...", flush=True)
    time.sleep(15)
    
    print("[7] Ending call on Nokia C30...", flush=True)
    adb(NOKIA_ID, ["shell", "input", "keyevent", "KEYCODE_ENDCALL"])
    print("[*] TEST COMPLETE!", flush=True)

if __name__ == "__main__":
    main()
