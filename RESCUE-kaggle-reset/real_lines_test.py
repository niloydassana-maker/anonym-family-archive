"""v58 test -- CORRECTION. I spoke the WRONG sentence.

Baba (2026-10-03): "There is a mistake from my side. I said last night actually it should be
first of October night." So the good recording is the night of 1 Oct into 2 Oct, 02:41 -- which is
sugardoctor-demo-lines.wav, confirmed on disk (CreationTime 10/2/2026 2:27 AM, LastWrite 2:41 AM).
That is the clip I played as #1, so the comparison stands.

But the sentence I sent through v57 was WRONG, on two counts, both found by reading
prerender_demo.py rather than assuming:
  1. It was NOT a line from that clip. test_line_hi.txt is a different sentence.
     The real lines are the LINES list at prerender_demo.py:33-39.
  2. It carried the FEMININE verb "बोल रही हूँ" on a MALE voice -- the exact defect the GENDER
     LAW at prerender_demo.py:31-32 exists to prevent. I fed the kernel text that its own code
     forbids.
And a third fact I had wrong: the good clip was produced by posting those lines to the RELAY as
LIVE_CALL (prerender_demo.py:47-50), i.e. the v31-era seat path -- not the HTTP /turn path.

This speaks the FIVE REAL LINES through v57 and plays them beside the original clip.
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request, wave
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\anonym\war-log\voice-live\out"
FF = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffplay.exe"
URL = open(os.path.join(OUT, "live_tunnel.txt")).read().strip()

# The real lines, verbatim from prerender_demo.py:33-39
LINES = [
    ("answer",   "नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। मैं क्लिनिक से बोल रहा हूँ। बताइए, मैं आपकी क्या मदद कर सकता हूँ?"),
    ("timings",  "क्लिनिक सुबह नौ बजे से दोपहर दो बजे तक, और शाम पाँच बजे से रात आठ बजे तक खुली रहती है।"),
    ("booking",  "जी, आपका अपॉइंटमेंट कल सुबह ग्यारह बजे डॉक्टर लोतिका पुरोहित के साथ तय हो गया है। धन्यवाद।"),
    ("callback", "जी, आपका नंबर दर्ज हो गया है। हम थोड़ी देर में कॉल करके समय बता देंगे।"),
    ("close",    "धन्यवाद। आपका दिन शुभ हो।"),
]

print("v57 tunnel: %s" % URL)
p = json.loads(urllib.request.urlopen(URL + "/say?probe=1", timeout=30).read().decode())
print("ref=%s temp=%s mode=%s sr=%s\n" % (p.get("ref_full"), p.get("temperature"),
                                          p.get("synth_mode"), p.get("out_sr")))

made = []
for name, text in LINES:
    q = urllib.parse.urlencode({"text": text, "lang": "hi", "use_ref": "1"})
    raw = urllib.request.urlopen(URL + "/say?" + q, timeout=200).read()
    fp = os.path.join(OUT, "v57_demo_%s.wav" % name)
    open(fp, "wb").write(raw)
    w = wave.open(fp, "rb")
    d = w.getnframes() / float(w.getframerate())
    print("  %-10s %6.2f s  %8d b  %d Hz" % (name, d, len(raw), w.getframerate()))
    made.append((fp, d, name))
print()

orig = os.path.join(OUT, "sugardoctor-demo-lines.wav")
w = wave.open(orig, "rb")
d_orig = w.getnframes() / float(w.getframerate())

print("=" * 74)
print("PLAYING: the ORIGINAL 1-oct night clip first, then v57's five lines, same order.")
print("=" * 74)
time.sleep(4)
print("  -> ORIGINAL sugardoctor-demo-lines.wav  (%.1f s, the night of 1 Oct, 02:41)" % d_orig)
subprocess.Popen([FF, "-nodisp", "-autoexit", orig])
time.sleep(d_orig + 2.5)
for fp, d, name in made:
    print("  -> v57 %s" % name)
    subprocess.Popen([FF, "-nodisp", "-autoexit", fp])
    time.sleep(d + 2)
print("\ndone.")