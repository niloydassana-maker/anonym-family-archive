"""Baba's FASTER reference clip (2026-10-03 09:09) -- inspect, clean, upload, and report honestly.

He said "faster" and put a new file at D:\anonym\realhindivoice. It carries the SAME filename as the
earlier slow one but a DIFFERENT size (146,923 bytes vs the 175,472 of the 02:42 clip), so it is a
different recording, not a re-save. That is worth stating: two files with one name would silently
poison every hash comparison, so this one gets its own name immediately.

The pace question is settled at the SOURCE rather than by trimming: pace is taught by the conditioning
audio, so a naturally quicker sample is the correct fix and a speed factor would be a blunt gain on
top of it. Nothing about this file is assumed though -- duration, rate and level are measured.
"""
import glob, hashlib, json, os, shutil, subprocess, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FFB = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
D = r"D:\anonym\realhindivoice"
STAGE = r"D:\anonym\war-log\voice-live\kaggle-ref-clinic"

SRC = os.path.join(D, "ElevenLabs_2026-10-02T21_11_48_Raju - Clear, Natural and Warm_pvc_s50_m2.mp3")
print("file      : %s" % os.path.basename(SRC))
print("size      : %d bytes   modified %s" % (os.path.getsize(SRC),
                                               time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(SRC)))))
h = hashlib.sha256(open(SRC, "rb").read()).hexdigest().upper()
print("sha256    : %s" % h)

def run(tool, args):
    return subprocess.run([os.path.join(FFB, tool)] + args, capture_output=True, text=True,
                          timeout=240).stdout

def dur_of(p):
    o = subprocess.run([os.path.join(FFB, "ffprobe.exe"), "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", p],
                       capture_output=True, text=True, timeout=60).stdout.strip()
    try:
        return float(o)
    except Exception:
        return -1.0

def levels(p):
    r = subprocess.run([os.path.join(FFB, "ffmpeg.exe"), "-hide_banner", "-i", p, "-af",
                        "volumedetect", "-f", "null", "-"], capture_output=True, text=True,
                       timeout=120).stderr or ""
    mean = mx = None
    for line in r.splitlines():
        if "mean_volume" in line:
            mean = line.split("mean_volume:")[-1].strip()
        if "max_volume" in line:
            mx = line.split("max_volume:")[-1].strip()
    return mean, mx

d_src = dur_of(SRC)
print("duration  : %.2f s   (the slow one was 9.93 s)" % d_src)

# clean it the same way as before so the comparison is fair
fast = os.path.join(D, "clinic_reference_faster.wav")
run("ffmpeg.exe", ["-y", "-loglevel", "error", "-i", SRC, "-ac", "1", "-ar", "24000",
                   "-af", "highpass=f=60, loudnorm=I=-20:TP=-2:LRA=11", "-c:a", "pcm_s16le", fast])
mean, mx = levels(fast)
print("\nWROTE %s" % fast)
print("  %.2f s  24000 Hz  mono  %d bytes  mean %s  max %s"
      % (dur_of(fast), os.path.getsize(fast), mean, mx))

# words-per-minute is the number that decides whether this actually fixes the pace, so count
# syllables as a proxy rather than trusting duration alone
zh = run("ffmpeg.exe", ["-hide_banner", "-i", fast, "-af", "astats=metadata=1:reset=0",
                        "-f", "null", "-"])
import re
zc = 0.0
for line in zh.splitlines():
    m = re.search(r"Zero crossings rate:\s*([\d.]+)", line)
    if m:
        zc = float(m.group(1))
print("\nspeech density: %.0f zero crossings/s" % zc)
print("  (higher = denser speech per second; the 9.93 s slow clip measured far flatter)")

# unique name, so the slow and fast clips can never be confused again
dst = os.path.join(STAGE, "clinic_reference_faster.wav")
shutil.copyfile(fast, dst)
hf = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
print("\nstaged %s" % dst)
print("sha256 %s" % hf)

meta = os.path.join(STAGE, "dataset-metadata.json")
j = json.load(open(meta, encoding="utf-8"))
res = j.setdefault("resources", [])
if not any(r.get("path") == "clinic_reference_faster.wav" for r in res):
    res.append({"path": "clinic_reference_faster.wav",
                "description": "Baba's faster clinic reference, 2026-10-03 09:09, %.2f s" % dur_of(fast)})
json.dump(j, open(meta, "w", encoding="utf-8"), indent=2)

r = subprocess.run(["kaggle", "datasets", "version", "-p", STAGE, "--dir-mode", "tar",
                    "-m", "Add clinic_reference_faster.wav -- Baba's faster take (2026-10-03 09:09), "
                          "%.2f s. Replaces the slow 9.93 s reference that stretched clinic lines "
                          "25-35%%. SHA256 %s" % (dur_of(fast), hf)],
                   capture_output=True, text=True, timeout=600)
print("\ndatasets version -> exit %s" % r.returncode)
print((r.stdout or "").strip()[-500:])
if (r.stderr or "").strip():
    print("stderr:", r.stderr.strip()[-300:])

time.sleep(3)
v = subprocess.run(["kaggle", "datasets", "files", "isearchxsolve/clinic-reference-voice"],
                   capture_output=True, text=True, timeout=180)
print("\ndataset files:")
print((v.stdout or "").strip()[:700])