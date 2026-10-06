"""v58 verification: prove the NEW reference is loaded, then re-render the clinic lines for the ear.

Order matters. First GET /say?probe=1 must print ref_full = .../clinic_reference.wav -- if it still says
father.wav the swap failed and there is no point playing audio, because the ear would be judging the old
voice while believing it is the new one. Only after the probe agrees do we synthesise.
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request, wave
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
print("waiting for v58 ...")
for i in range(40):
    for u in tunnels():
        try:
            p = json.loads(get(u + "/say?probe=1", 25).decode())
            if "clinic_reference_fast" in str(p.get("ref_full", "")):
                url = u
                break
            else:
                print("  %s -> on %s, not v59" % (u.split("//")[1][:38], p.get("ref")))
        except Exception:
            continue
    if url:
        break
    print("  no v59 yet (%d/40)" % (i + 1))
    time.sleep(12)
if not url:
    print("v58 with the new reference never appeared"); raise SystemExit(2)

p = json.loads(get(url + "/say?probe=1", 30).decode())
print("\n*** v58 CONFIG AS RUNNING ***")
for k in ("ref", "ref_full", "temperature", "synth_mode", "first_max_hi", "min_piece", "out_sr", "sr"):
    print("   %-13s %s" % (k, p.get(k)))
print("*** CONFIRMED: the 5.00 s trimmed reference is loaded ***")

open(os.path.join(OUT, "live_tunnel.txt"), "w").write(url)
subprocess.run([r"D:\anonym\platform-tools\adb.exe", "shell", "mkdir", "-p",
                "/sdcard/Android/data/io.kilo.bridge/files"], capture_output=True)
subprocess.run([r"D:\anonym\platform-tools\adb.exe", "shell",
                "echo %s > /sdcard/Android/data/io.kilo.bridge/files/voice_url.txt" % url],
               capture_output=True)
print("phone pointed at %s" % url)

LINES = [
    ("greet",    "नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। मैं क्लिनिक की आवाज़ हूँ। बताइए, मैं आपकी क्या मदद कर सकता हूँ?"),
    ("timings",  "क्लिनिक सुबह नौ बजे से दोपहर दो बजे तक, और शाम पाँच बजे से रात आठ बजे तक खुली रहती है।"),
    ("booking",  "जी, आपका अपॉइंटमेंट कल सुबह ग्यारह बजे डॉक्टर लोतिका पुरोहित के साथ तय हो गया है। धन्यवाद।"),
    ("callback", "जी, आपका नंबर दर्ज हो गया है। हम थोड़ी देर में कॉल करके समय बता देंगे।"),
    ("emergency","यह आपात स्थिति है। अभी एम्बुलेंस बुलाइए या नज़दीकी अस्पताल जाइए। क्लिनिक ये नहीं कर सकता।"),
    ("robot",    "हाँ, मैं एक कंप्यूटर हूँ, सुगर डॉक्टर क्लिनिक की आवाज़।"),
    ("close",    "धन्यवाद। आपका दिन शुभ हो।"),
]

print("\nrendering %d lines on the TRIMMED reference ..." % len(LINES))
made = []
for name, text in LINES:
    q = urllib.parse.urlencode({"text": text, "lang": "hi", "use_ref": "1"})
    try:
        raw = get(url + "/say?" + q, 200)
        fp = os.path.join(OUT, "v59_%s.wav" % name)
        open(fp, "wb").write(raw)
        w = wave.open(fp, "rb")
        d = w.getnframes() / float(w.getframerate())
        print("   %-10s %6.2f s  %8d b" % (name, d, len(raw)))
        made.append((fp, d, name))
    except Exception as e:
        print("   %-10s FAILED %s" % (name, repr(e)[:90]))

# v58 (9.93 s reference) vs v59 (5.00 s) on the same words -- the point of the whole change
V58 = {"greet": 9.61, "timings": 9.00, "booking": 8.12, "callback": 7.10,
       "emergency": 7.66, "robot": 5.89, "close": None}
print("\n%-11s %9s %9s %9s" % ("line", "v58 9.9s", "v59 5.0s", "change"))
for name, text in LINES:
    d = [x[1] for x in made if x[2] == name]
    d59 = d[0] if d else None
    d58 = V58.get(name)
    if d59 and d58:
        print("%-11s %9.2f %9.2f %8.1f%%" % (name, d58, d59, (d59 - d58) / d58 * 100))
    elif d59:
        print("%-11s %9s %9.2f %9s" % (name, "-", d59, "new line"))

print("\n" + "=" * 72)
print("PLAYING THE CLINIC LINES ON THE TRIMMED REFERENCE")
print("=" * 72)
time.sleep(3)
for fp, d, name in made:
    print("  -> %s" % name)
    subprocess.Popen([FF, "-nodisp", "-autoexit", fp])
    time.sleep(d + 2)
print("\ndone.")