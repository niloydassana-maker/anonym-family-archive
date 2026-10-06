"""v60: the faster reference, rendered with spacing between calls so the CUDA assert cannot creep up.

v59 died with 'CUDA error: device-side assert triggered' after exactly two successful syntheses, and
every call after that failed -- a poisoned CUDA context is unrecoverable in-process. So this renders
ONE line, checks /health, and sleeps between lines rather than firing seven requests back to back.
If an assert appears, it is reported at the exact call that caused it instead of five anonymous 500s.
"""
import json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, wave
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\anonym\war-log\voice-live\out"
FF = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffplay.exe"
BASE = "http://127.0.0.1:8777"

def get(u, t=30):
    return urllib.request.urlopen(u, timeout=t).read()

def tunnels():
    try:
        d = json.loads(get("%s/hear?body=KILO&limit=40&token=GOLD24" % BASE, 40).decode("utf-8", "replace"))
    except Exception:
        return []
    out = set()
    for g in d.values():
        for r in g:
            if "VOICE_TUNNEL" in r.get("text", ""):
                out.add(r["text"].split("VOICE_TUNNEL", 1)[1].strip())
    return sorted(out)

url = None
for i in range(45):
    for u in tunnels():
        try:
            p = json.loads(get(u + "/say?probe=1", 25).decode())
            if "clinic_reference_faster" in str(p.get("ref_full", "")):
                url = u
                break
        except Exception:
            continue
    if url:
        break
    print("  waiting for v60 (%d/45)" % (i + 1))
    time.sleep(12)
if not url:
    print("v60 never came up"); raise SystemExit(2)

p = json.loads(get(url + "/say?probe=1", 30).decode())
print("\n*** v60 CONFIG ***")
for k in ("ref", "ref_full", "temperature", "synth_mode", "first_max_hi", "out_sr", "sr"):
    print("   %-13s %s" % (k, p.get(k)))
open(os.path.join(OUT, "live_tunnel.txt"), "w").write(url)
subprocess.run([r"D:\anonym\platform-tools\adb.exe", "shell", "mkdir", "-p",
                "/sdcard/Android/data/io.kilo.bridge/files"], capture_output=True)
subprocess.run([r"D:\anonym\platform-tools\adb.exe", "shell",
                "echo %s > /sdcard/Android/data/io.kilo.bridge/files/voice_url.txt" % url],
               capture_output=True)

# v58 = the slow 9.93 s reference, the thing we are trying to beat
V58 = {"greet": 9.61, "timings": 9.00, "booking": 8.12, "callback": 7.10,
       "emergency": 7.66, "robot": 5.89}
LINES = [
    ("greet",    "नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। मैं क्लिनिक की आवाज़ हूँ। बताइए, मैं आपकी क्या मदद कर सकता हूँ?"),
    ("timings",  "क्लिनिक सुबह नौ बजे से दोपहर दो बजे तक, और शाम पाँच बजे से रात आठ बजे तक खुली रहती है।"),
    ("booking",  "जी, आपका अपॉइंटमेंट कल सुबह ग्यारह बजे डॉक्टर लोतिका पुरोहित के साथ तय हो गया है। धन्यवाद।"),
    ("callback", "जी, आपका नंबर दर्ज हो गया है। हम थोड़ी देर में कॉल करके समय बता देंगे।"),
    ("robot",    "हाँ, मैं एक कंप्यूटर हूँ, सुगर डॉक्टर क्लिनिक की आवाज़।"),
    ("close",    "धन्यवाद। आपका दिन शुभ हो।"),
]

print("\nrendering one at a time with a gap (v59 asserted after two back-to-back calls)")
made = []
for name, text in LINES:
    q = urllib.parse.urlencode({"text": text, "lang": "hi", "use_ref": "1"})
    try:
        raw = get(url + "/say?" + q, 240)
        fp = os.path.join(OUT, "v60_%s.wav" % name)
        open(fp, "wb").write(raw)
        w = wave.open(fp, "rb")
        d = w.getnframes() / float(w.getframerate())
        d58 = V58.get(name)
        chg = ("%+.1f%%" % ((d - d58) / d58 * 100)) if d58 else "n/a"
        print("   %-9s %6.2f s   vs slow %5.2f s = %s" % (name, d, d58 or 0, chg))
        made.append((fp, d, name))
    except urllib.error.HTTPError as e:
        print("   %-9s HTTP %s  %s" % (name, e.code, e.read().decode("utf-8", "replace")[:160]))
        print("   STOPPING HERE -- the CUDA context is poisoned, remaining lines would all fail")
        break
    except Exception as e:
        print("   %-9s EXC %r" % (name, e)); break
    time.sleep(4)

print("\n" + "=" * 70)
print("PLAYING %d LINES ON THE FASTER REFERENCE" % len(made))
print("=" * 70)
time.sleep(3)
for fp, d, name in made:
    print("  -> %s" % name)
    subprocess.Popen([FF, "-nodisp", "-autoexit", fp])
    time.sleep(d + 2)
print("\ndone.")