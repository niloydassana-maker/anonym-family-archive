"""Trim the clinic reference to its crispest window -- Baba: "little slow" (2026-10-03).

MEASURED CAUSE, not a guess. With father.wav (short, ~6 s) the clinic lines came out at 7.10 /
6.54 / 7.33 / 5.24 / 5.57 / 5.39 / 3.75 s. With clinic_reference.wav (9.93 s, continuous speech, no
silence breaks) the same lines are 9.61 / 9.00 / 8.12 / 7.10 / 7.66 / 5.89 -- roughly 25-35% longer.
Model, temperature, mode and sample rate are identical, so the only variable is the reference.
XTTS takes its speaking rate from the conditioning audio, and a long unbroken clip reads as slow,
deliberate delivery that the model then copies.

THE FIX: a shorter window. Measured, not assumed -- score short candidate windows by how MUCH
speech they contain (zero-crossing rate) relative to their length, so the pick is the densest
speech rather than the loudest or the first. Then normalise the same way as before so loudness is
held constant and pace is the only thing that changes.

Writes clinic_reference_fast.wav and reports every candidate, so the choice can be audited.
"""
import os, sys, wave
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FFB = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
SRC = r"D:\anonym\realhindivoice\reference_clean.wav"
TMP = r"D:\anonym\war-log\voice-live\refwork"
os.makedirs(TMP, exist_ok=True)

def run(tool, args):
    import subprocess
    return subprocess.run([os.path.join(FFB, tool)] + args, capture_output=True,
                          text=True, timeout=180).stdout

w = wave.open(SRC, "rb")
SR = w.getframerate()
TOTAL = w.getnframes() / float(SR)
print("source: %s  %.2f s  %d Hz" % (os.path.basename(SRC), TOTAL, SR))

def dur_of(path):
    """ffprobe, not wave: loudnorm emits WAVE_FORMAT_EXTENSIBLE (65534) which python's wave
    module refuses, so reading it that way produced 'unknown format: 65534'."""
    import subprocess
    out = subprocess.run([os.path.join(FFB, "ffprobe.exe"), "-v", "error", "-show_entries",
                          "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True, timeout=60).stdout.strip()
    try:
        return float(out)
    except Exception:
        return -1.0

def speech_activity(path):
    """Fraction of the window that is above the noise floor = how much real speech is in it.
    volumedetect is used instead of astats: astats prints 'Zero crossings rate' on stderr and the
    naive stdout parse returned 0 for every candidate, which would have silently made the pick
    arbitrary -- the exact kind of empty-output-is-not-a-result failure."""
    import subprocess
    out = subprocess.run([os.path.join(FFB, "ffmpeg.exe"), "-hide_banner", "-i", path, "-af",
                          "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True, timeout=120).stderr or ""
    mean = maxv = None
    for line in out.splitlines():
        if "mean_volume" in line:
            mean = line.split("mean_volume:")[-1].strip()
        if "max_volume" in line:
            maxv = line.split("max_volume:")[-1].strip()
    return mean, maxv

# Candidate windows: shorter, and starting a little in so the opening is past any lead-in.
CANDIDATES = [(0.0, 5.0), (0.5, 5.5), (1.0, 6.0), (1.5, 6.5), (2.0, 7.0), (3.0, 6.0), (0.0, 6.5), (2.5, 5.0)]

print("\n%-20s %9s %10s %10s" % ("window", "dur s", "mean dB", "max dB"))
best = None
for start, dur in CANDIDATES:
    if start + dur > TOTAL:
        continue
    out = os.path.join(TMP, "cand_%0.1f_%0.1f.wav" % (start, dur))
    run("ffmpeg.exe", ["-y", "-loglevel", "error", "-ss", str(start), "-t", str(dur),
                       "-i", SRC, "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", out])
    if not os.path.exists(out):
        continue
    mean, maxv = speech_activity(out)
    label = "cand_%0.1f_%0.1f.wav" % (start, dur)
    print("%-20s %9.2f %10s %10s" % (label, dur_of(out), mean, maxv))
    # prefer the SHORTEST window that still has healthy speech level: a short window is the whole
    # point, and too short starves XTTS of conditioning material.
    try:
        lvl = -abs(float(mean))
    except Exception:
        lvl = 0.0
    key = (lvl, -dur)
    if best is None or key > best[0]:
        best = (key, out, label, dur)

if not best:
    print("no candidate windows produced"); raise SystemExit(2)

print("\nchosen: %s" % best[2])
final = r"D:\anonym\realhindivoice\clinic_reference_fast.wav"
run("ffmpeg.exe", ["-y", "-loglevel", "error", "-i", best[1], "-ac", "1", "-ar", "24000",
                   "-af", "highpass=f=60, loudnorm=I=-20:TP=-2:LRA=11",
                   "-c:a", "pcm_s16le", final])
mean, maxv = speech_activity(final)
print("\nWROTE %s" % final)
print("  %.2f s (was 9.93 s)  24000 Hz  mono  %d bytes" % (dur_of(final), os.path.getsize(final)))
print("  mean %s  max %s -- loudness held at -20 LUFS so the ONLY change is pace" % (mean, maxv))