"""v57 decisive test -- run against the tunnel that actually answers /say.

Finding while wiring this: TWO kernels were live at once. The stale v56 tunnel
(waves-william-...) answered /health and /ab but 404 on /say; the v57 tunnel
(watt-ferrari-...) answers 200. So /say doubles as a VERSION CHECK, and "404 on a route I just
pushed" is the tell that a tunnel is stale rather than that the route is missing.

The live kernel confirms the reference is the SAME FILE v31 used:
    /kaggle/input/father-voice/father.wav   temperature 0.4   full   24000 in and out
which also means the metadata_hi.csv fallback never fires, so the reference cannot have changed.
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request, wave
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\anonym\war-log\voice-live\out"
FF = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffplay.exe"
BASE = "http://127.0.0.1:8777"

GOOD = "नमस्ते, मैं सुगर डॉक्टर क्लिनिक से बोल रही हूँ। आपका अपॉइंटमेंट कल सुबह दस बजे तय हो गया है। धन्यवाद।"

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

# /say exists only in v57, so it doubles as the version marker
url = None
print("finding the v57 tunnel ...")
for i in range(30):
    for u in tunnels():
        try:
            json.loads(get(u + "/say?probe=1", 25).decode())
            url = u
            break
        except Exception:
            continue
    if url:
        print("  v57 IS LIVE: %s" % url)
        break
    print("  no v57 tunnel yet (%d/30)" % (i + 1))
    time.sleep(12)
if not url:
    print("v57 never came up"); raise SystemExit(2)

p = json.loads(get(url + "/say?probe=1", 30).decode())
print("\nKERNEL CONFIG AS RUNNING (read off the live kernel, nothing inferred):")
for k in ("ref", "ref_full", "temperature", "synth_mode", "first_max_hi", "min_piece", "out_sr", "sr"):
    print("   %-13s %s" % (k, p.get(k)))

open(os.path.join(OUT, "live_tunnel.txt"), "w").write(url)
subprocess.run([r"D:\anonym\platform-tools\adb.exe", "shell", "mkdir", "-p",
                "/sdcard/Android/data/io.kilo.bridge/files"], capture_output=True)
subprocess.run([r"D:\anonym\platform-tools\adb.exe", "shell",
                "echo %s > /sdcard/Android/data/io.kilo.bridge/files/voice_url.txt" % url],
               capture_output=True)
print("   phone pointed at the v57 tunnel")

def speak(name, text, use_ref=1):
    q = urllib.parse.urlencode({"text": text, "lang": "hi", "use_ref": str(use_ref)})
    raw = get(url + "/say?" + q, 200)
    fp = os.path.join(OUT, name)
    open(fp, "wb").write(raw)
    w = wave.open(fp, "rb")
    d = w.getnframes() / float(w.getframerate())
    print("   %-26s %6.2f s  %8d b  %d Hz" % (name, d, len(raw), w.getframerate()))
    return fp, d

print("\nSPEAKING YOUR EXACT PRE-RENDERED LINE THROUGH v57:")
p1, d1 = speak("v57_premrendered_line.wav", GOOD, 1)
p2, d2 = speak("v57_premrendered_line_b.wav", GOOD, 1)
p3, d3 = speak("v57_absentence.wav", "डॉक्टर साहब सुबह नौ बजे से शाम पाँच बजे तक मिलते हैं।", 1)

p_orig = os.path.join(OUT, "sugardoctor-demo-lines.wav")
w = wave.open(p_orig, "rb")
d_orig = w.getnframes() / float(w.getframerate())

print("\n" + "=" * 74)
print("PLAYING FOUR CLIPS IN ORDER. Listen for the ACCENT, not the speed.")
print("  1 ORIGINAL   sugardoctor-demo-lines.wav   10-02 02:41, the one you approved")
print("  2 v57 RUN A  same sentence, today's kernel, same father.wav")
print("  3 v57 RUN B  same sentence again (temp 0.4, so runs differ)")
print("  4 v57        the short clinic-timings sentence")
print("=" * 74)
time.sleep(4)
for pth, d, lab in [(p_orig, min(d_orig, 33), "1 ORIGINAL (approved last night)"),
                    (p1, d1, "2 v57 RUN A, same sentence"),
                    (p2, d2, "3 v57 RUN B, same sentence"),
                    (p3, d3, "4 v57, the short timings sentence")]:
    print("  -> %s" % lab)
    subprocess.Popen([FF, "-nodisp", "-autoexit", pth])
    time.sleep(d + 2.5)
print("\ndone.")