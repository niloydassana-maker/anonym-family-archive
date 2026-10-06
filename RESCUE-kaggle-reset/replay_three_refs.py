"""Replay the greeting on all three references, back to back, so the pace can be judged by ear.

Three files exist for the SAME sentence:
  v58_greet.wav  9.61 s  the original 9.93 s reference  (slow)
  v59_greet.wav  9.61 s  the 5.00 s trimmed window      (measured -0.0%, i.e. no help)
  v60_greet.wav  8.54 s  Baba's faster take, 8.12 s ref  (measured -11.1%)

v60 rendered only this one line before the CUDA context asserted again on the second call, so the
other five lines do not exist for v60. Rather than leave Baba with nothing but a number, this plays the
greeting on all three references in one go -- the sentence is identical in each, so the only variable
the ear can hear is the reference. Nothing is re-synthesised: these are the files already on disk.
"""
import os, subprocess, sys, time, wave
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\anonym\war-log\voice-live\out"
FF = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffplay.exe"

CLIPS = [
    ("v58_greet.wav", "SLOW   -- your first clip, 9.93 s reference"),
    ("v59_greet.wav", "TRIMMED -- 5.00 s window, measured no help"),
    ("v60_greet.wav", "FASTER -- your new take, 8.12 s reference"),
]

print("=" * 72)
print("THE SAME SENTENCE, THREE REFERENCES")
print("=\"नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। ...\"")
print("=" * 72)
durs = []
for fn, lab in CLIPS:
    p = os.path.join(OUT, fn)
    if not os.path.exists(p):
        print("  MISSING %s" % fn); continue
    w = wave.open(p, "rb")
    d = w.getnframes() / float(w.getframerate())
    durs.append((p, d, lab))

print("\n%-11s %9s" % ("version", "seconds"))
for _, d, lab in durs:
    print("%-11s %9.2f   %s" % (lab.split(" --")[0], d, lab.split("--")[1].strip()))
if len(durs) >= 2:
    print("\nfastest vs slowest: %.1f%% shorter" % ((durs[0][1] - durs[-1][1]) / durs[0][1] * 100))

print("\nPLAYING, 3 s apart:")
for p, d, lab in durs:
    print("  -> %s (%.2f s)" % (lab, d))
    time.sleep(3)
    subprocess.Popen([FF, "-nodisp", "-autoexit", p])
    time.sleep(d + 2.5)
print("\ndone.")