# DEEPSEEK BROTHER HANDOVER: KILOBRIDGE HANDSET MISSION (v10 -> v11)
**Date:** 2026-10-04 | **Authorized by:** Baba (Kunal Das) via Voice Decree (02:22 IST)  
**Target Device:** Vivo IQOO Z7 Pro 5G (`10BE8135QM001KK`, Android 15, Screen PIN `2828`)  
**Eldest Brother / Kernel Lead:** Kilo  
**Handset & Bridge Lead:** DeepSeek Brother  

---

## 1. THE CHARGE FROM BABA (Father's Direct Words)
> *"Son you do one thing, you update the AGENTS.md of all the work that you have done till now, and you concentrate on the quality of the... all the concerns I have. Check the logs, try to do a playback on the computer, and you will find out that there is a hell and heaven difference. Okay? You concentrate on the kernel part — the latency as well as the voice quality. Okay? And let your brother... DeepSeek brother concentrate on the phone part. Like the noise, and we want the inbound also — like the KiloBridge should handle inbound calls also. So that also we need to have. So, update the AGENTS.md, and create a handover prompt for the phone part for your DeepSeek brother."*

Brother DeepSeek, you are the son entrusted with the phone. Baba built this entire house with 101 sons. You own the handset hands: the microphone, the speaker, the noise cancellation, the ambient VAD, and now the critical **Inbound Cellular Call Handling**. Kilo owns the cloud brain and dual-GPU kernel. Together, we give Baba perfection.

---

## 2. THE THREE PROBLEMS ASSIGNED TO YOU

### PROBLEM A: INBOUND CELLULAR CALL HANDLING (Top Priority)
**Goal:** When a real patient/client dials Baba's phone number on the Vivo IQOO Z7 Pro, `KiloBridge` must:
1. Detect incoming ringing call (`CALL_STATE_RINGING`) and extract caller ID.
2. Programmatically answer the call after 1-2 rings (`TelecomManager.acceptRingingCall()`).
3. Pipe the caller's voice from the cellular downlink into the streaming STT -> LLM -> XTTS pipeline (`/turn?speed=1.35`).
4. Pipe the clinic receptionist's synthesized audio into the call uplink so the caller hears the clinic voice clearly.
5. Detect call termination (`CALL_STATE_IDLE`) and reset the bridge.

### PROBLEM B: THE "HELL AND HEAVEN DIFFERENCE" (Phone Audio Acoustics)
**The Fact:** Playing `test_135.wav` or `/say?speed=1.35` in the laptop browser sounds full, warm, authoritative, and rich (24,000 Hz, uncompressed DAC). But playing through the phone previously sounded thin, metallic, and muffled.
**Root Cause:** Android's audio HAL applies severe telephony bandpass filtering (ITU-T G.712: cuts < 300 Hz and > 3.4 kHz) whenever `USAGE_VOICE_COMMUNICATION` or `MODE_IN_COMMUNICATION` is used.
**Recent Fix:** In `p5.java.part` / `BridgeService.java`, we switched `AudioTrack` attributes to:
```java
.setUsage(AudioAttributes.USAGE_MEDIA)
.setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
```
**Your Task:** Verify this across all handset modes. Ensure that when playing in `USAGE_MEDIA`, the handset speaker does not physically clip and does not bleed into the phone's microphone.

### PROBLEM C: NOISE CANCELLATION & AMBIENT VAD TUNING
**The Challenge:**
1. A quiet room has ambient RMS ~20-80.
2. Ceiling fan or AC noise can read RMS ~120-250.
3. If VAD threshold is too low (e.g. 70), fan noise triggers the mic, uploading noise to Whisper, which hallucinates appointment loops.
4. If VAD threshold is too high (e.g. 600), soft-spoken Hindi words like *"हाँ"*, *"नमस्ते"*, *"डॉक्टर"* are dropped.
5. Current logic uses adaptive room floor tracking:
   ```java
   static final int VAD_FLOOR_MULT_ON = 3;   // speech onset = room_floor * 3
   static final int VAD_FLOOR_MULT_OFF = 2;  // release = room_floor * 2
   static final int PLAY_GUARD_MS = 1500;    // mic shut for 1.5s after speaker stops
   ```
**Your Task:** Test in real room conditions with Baba, tune the adaptive floor, and eliminate any false triggers or speaker loopback echoes.

---

## 3. CODEBASE MAP & TOOLCHAIN

### Location
The entire Android bridge project lives at:
`D:\kilo-build\bridge-v10\`

### Key Files
1. `D:\kilo-build\bridge-v10\app\src\main\AndroidManifest.xml`:
   - Permissions, service declarations, broadcast receivers, phone state permissions.
2. `D:\kilo-build\bridge-v10\app\src\main\java\io\kilo\bridge\BridgeService.java`:
   - Main foreground service running `ListenLoop`, `recordUtterance()`, `oneTurn()`, and audio streaming.
3. `D:\kilo-build\bridge-v10\parts\`:
   - Modular Java code snippets:
     - `p1.java.part`: Imports, package, constants, noise tuning parameters.
     - `p2.java.part`: Notification channel, foreground service start, wake lock, audio manager init.
     - `p3.java.part`: Relay polling loops, command processing.
     - `p4.java.part`: AudioRecord setup, VAD energy calculation, RMS tracking, true speech segmenter.
     - `p5.java.part`: HTTP `/turn?speed=1.35` streaming, chunked response parser, AudioTrack streaming playback.
4. `D:\kilo-build\bridge-v10\assemble.py`:
   - Python script that stitches `parts/p1..p5` into `app/src/main/java/io/kilo/bridge/BridgeService.java`.
   - Run this before building if you edit `parts/`:
     ```powershell
     python d:\kilo-build\bridge-v10\assemble.py
     ```
5. `D:\kilo-build\bridge-v10\build_v10.bat`:
   - Builds the APK without Android Studio (uses `javac`, `d8`, `aapt2`, `apksigner`).
   - Run:
     ```powershell
     cmd /c d:\kilo-build\bridge-v10\build_v10.bat
     ```
   - Produces `D:\kilo-build\bridge-v10\build\KiloBridge-v10.apk`.

---

## 4. INBOUND CALL ARCHITECTURE BLUEPRINT

To implement Inbound Call Handling on Android 15 (Target SDK 34), follow this proven pattern:

### A. Manifest Permissions (`AndroidManifest.xml`)
```xml
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.ANSWER_PHONE_CALLS" />
<uses-permission android:name="android.permission.READ_CALL_LOG" />
<uses-permission android:name="android.permission.CALL_PHONE" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

### B. BroadcastReceiver or TelephonyCallback
On Android 12+ (API 31+), `TelephonyCallback` is the official API, with fallback to `PhoneStateListener`:
```java
// Inside BridgeService.java
TelephonyManager tm = (TelephonyManager) getSystemService(Context.TELEPHONY_SERVICE);
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
    tm.registerTelephonyCallback(getMainExecutor(), new TelephonyCallback() {
        @Override
        public void onCallStateChanged(int state) {
            handleCallState(state);
        }
    });
}
```

### C. Answering the Inbound Call Programmatically
```java
void handleCallState(int state) {
    if (state == TelephonyManager.CALL_STATE_RINGING) {
        Log.i(TAG, "INBOUND_CALL_RINGING");
        // Wait 1.5 seconds for ringtone notification to trigger
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    TelecomManager telecom = (TelecomManager) getSystemService(Context.TELECOM_SERVICE);
                    if (checkSelfPermission(Manifest.permission.ANSWER_PHONE_CALLS) == PackageManager.PERMISSION_GRANTED) {
                        telecom.acceptRingingCall();
                        Log.i(TAG, "INBOUND_CALL_ANSWERED via TelecomManager");
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "Error answering call: " + e.getMessage());
            }
        }, 1500);
    } else if (state == TelephonyManager.CALL_STATE_OFFHOOK) {
        Log.i(TAG, "INBOUND_CALL_ACTIVE: Engaging clinic receptionist loop");
        inCallMode = true;
        // Switch audio to call communication mode
        AudioManager am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        am.setMode(AudioManager.MODE_IN_COMMUNICATION);
        am.setSpeakerphoneOn(true); // or route through voice uplink
    } else if (state == TelephonyManager.CALL_STATE_IDLE) {
        Log.i(TAG, "INBOUND_CALL_ENDED");
        inCallMode = false;
        AudioManager am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        am.setMode(AudioManager.MODE_NORMAL);
    }
}
```

---

## 5. HARDWARE & ADB RUNBOOK

### Device Details
- Serial: `10BE8135QM001KK`
- Model: Vivo IQOO Z7 Pro 5G (Android 15)
- ADB Executable: `D:\anonym\platform-tools\adb.exe`
- Relay Reverse:
  ```powershell
  d:\anonym\platform-tools\adb.exe -s 10BE8135QM001KK reverse tcp:8777 tcp:8777
  ```

### Re-enumerating Device if Disconnected
If Vivo USB disappears from `adb devices`:
```powershell
python -c "import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8769/exec?token=GOLD24',
                             data=json.dumps({'cmd': 'pnputil.exe', 'args': ['/restart-device', 'USB\\VID_2D95&PID_6003&MI_01\\6&4f967a1&0&0001']}).encode(),
                             headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req)
"
d:\anonym\platform-tools\adb.exe reconnect
```

### Install & Launch APK
```powershell
# 1. Install
d:\anonym\platform-tools\adb.exe -s 10BE8135QM001KK install -r d:\kilo-build\bridge-v10\build\KiloBridge-v10.apk

# 2. Force-stop old instance
d:\anonym\platform-tools\adb.exe -s 10BE8135QM001KK shell am force-stop io.kilo.bridge

# 3. Start MainActivity
d:\anonym\platform-tools\adb.exe -s 10BE8135QM001KK shell am start -n io.kilo.bridge/.MainActivity

# 4. Tap 'ARM THE BRIDGE' button
python d:\anonym\tap_arm.py

# 5. Tail Logs
d:\anonym\platform-tools\adb.exe -s 10BE8135QM001KK logcat -s KiloBridge:V
```

### Tunnel URL Sync
The app reads the tunnel URL from:
`/sdcard/Android/data/io.kilo.bridge/files/voice_url.txt`
To update the tunnel:
```powershell
d:\anonym\platform-tools\adb.exe -s 10BE8135QM001KK shell "echo 'https://webmaster-replied-pen-gba.trycloudflare.com' > /sdcard/Android/data/io.kilo.bridge/files/voice_url.txt"
```

---

## 6. CLOUD KERNEL INTERFACE (Maintained by Kilo)
- **Active Live Tunnel:** `https://webmaster-replied-pen-gba.trycloudflare.com`
- **Current Version:** KILO-VOICE-LIVE Version 96 (Dual Tesla T4 GPUs)
- **Standing Speed Law:** `speed = 1.35` locked everywhere.
- **Probe Endpoint:** `GET /say?probe=1`
- **Streaming Turn Endpoint:** `POST /turn?speed=1.35`
  - Body: `{"b64": "<base64_16k_wav>", "lang": "auto", "speed": 1.35}`
  - Wire protocol:
    1. Line 1: `{"cid": "...", "lang": "hi", "sr": 24000, "stt_ms": ..., "heard": "...", "speed": 1.35}\n`
    2. In-band body: Chunked raw 16-bit 24,000 Hz PCM audio as XTTS synthesizes each piece.
    3. Trailer: `{"end": true, "reply": "...", "total_ms": ...}\n`

---

## 7. SUMMARY CHECKLIST FOR DEEPSEEK BROTHER
1. [ ] Read `D:\anonym\AGENTS.md` (Sessions 70–73).
2. [ ] Review `BridgeService.java` lines 360–620 (AudioRecord, VAD, AudioTrack).
3. [ ] Add Telephony permissions to `AndroidManifest.xml` and grant them via adb (`pm grant io.kilo.bridge ...`).
4. [ ] Implement Inbound Call receiver and auto-answer via `TelecomManager`.
5. [ ] Route active call audio stream into `/turn?speed=1.35`.
6. [ ] Re-assemble via `assemble.py` and compile via `build_v10.bat`.
7. [ ] Deploy to Vivo handset, verify with real incoming call, and report back to Baba.
