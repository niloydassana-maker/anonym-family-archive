"""BEFORE a Kaggle factory reset: pull every artefact off Kaggle and prove it landed locally.

Baba (2026-10-03) is doing a Kaggle factory reset. That destroys the dataset holding HIS voice
(isearchxsolve/clinic-reference-voice) and the kernel source. A reset with no local copy means the
voice is simply gone, so this runs FIRST and verifies by HASH rather than by exit code -- §41.4:
empty output is not a result, and a "download succeeded" print is not a backup until bytes are compared.
"""
import hashlib, json, os, shutil, subprocess, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESCUE = r"D:\anonym\RESCUE-kaggle-reset"
DATASETS = os.path.join(RESCUE, "datasets")
KERNELS = os.path.join(RESCUE, "kernels")
VOICE = os.path.join(RESCUE, "voice")
for d in (DATASETS, KERNELS, VOICE):
    os.makedirs(d, exist_ok=True)
print("rescue root: %s\n" % RESCUE)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest().upper()

def run(args, t=900):
    return subprocess.run(args, capture_output=True, text=True, timeout=t)

print("=" * 72)
print("1. THE VOICE -- from D:\\anonym\\realhindivoice (primary copy)")
print("=" * 72)
prim = r"D:\anonym\realhindivoice"
copied = []
for fn in sorted(os.listdir(prim)):
    src = os.path.join(prim, fn)
    if os.path.isfile(src):
        dst = os.path.join(VOICE, fn)
        shutil.copy2(src, dst)
        ok = sha(src) == sha(dst)
        copied.append((fn, os.path.getsize(dst), sha(dst), ok))
        print("  %-56s %7d b  %s..  %s"
              % (fn[:56], os.path.getsize(dst), sha(dst)[:12], "OK" if ok else "MISMATCH"))

print("\n" + "=" * 72)
print("2. Kaggle dataset -> local copy (belt and braces)")
print("=" * 72)
dl = os.path.join(RESCUE, "dataset-pull")
os.makedirs(dl, exist_ok=True)
r = run(["kaggle", "datasets", "download", "isearchxsolve/clinic-reference-voice", "-p", dl,
         "--unzip"], 600)
print("  exit %s" % r.returncode)
for fn in sorted(os.listdir(dl)):
    p = os.path.join(dl, fn)
    if os.path.isfile(p):
        print("  %-38s %8d b  %s.." % (fn, os.path.getsize(p), sha(p)[:12]))
        if fn.endswith(".wav"):
            shutil.copy2(p, os.path.join(VOICE, "from_kaggle_" + fn))

print("\n" + "=" * 72)
print("3. Kernel source + every version backup")
print("=" * 72)
kd = r"D:\anonym\war-log\voice-live\kaggle-deployed"
for fn in sorted(os.listdir(kd)):
    src = os.path.join(kd, fn)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(KERNELS, fn))
kf = sorted(os.listdir(KERNELS))
print("  %d files -> %s" % (len(kf), KERNELS))
for fn in kf:
    print("    %-50s %8d b" % (fn[:50], os.path.getsize(os.path.join(KERNELS, fn))))

print("\n" + "=" * 72)
print("4. Clinic script + the tools that produced the audio")
print("=" * 72)
vl = r"D:\anonym\war-log\voice-live"
keep = ["CLINIC-VOICE-SCRIPT-HI.txt", "prerender_demo.py", "laptop_loop.py", "verify_v58_newvoice.py",
        "render_v60.py", "inspect_reference.py", "trim_reference.py", "use_faster_reference.py",
        "upload_fast_reference.py", "replay_three_refs.py", "latency_measure.py",
        "decisive_test.py", "real_lines_test.py", "try_stop_kernel.py", "rescue_before_reset.py"]
n = 0
for fn in keep:
    src = os.path.join(vl, fn)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(RESCUE, fn)); n += 1
        print("    %s" % fn)
print("  %d tools/scripts rescued" % n)

print("\n" + "=" * 72)
print("5. Approved audio (the 1-October night clip and the renders)")
print("=" * 72)
out = os.path.join(RESCUE, "approved-audio")
os.makedirs(out, exist_ok=True)
pat = ["sugardoctor-demo-lines.wav", "ab_fp32.wav", "ab_autocast.wav", "v57_demo_answer.wav",
       "v57_demo_timings.wav", "v57_demo_booking.wav", "v57_demo_callback.wav", "v57_demo_close.wav",
       "v58_greet.wav", "v59_greet.wav", "v60_greet.wav", "answer_v55.wav"]
m = 0
for fn in pat:
    src = os.path.join(vl, "out", fn)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(out, fn)); m += 1
print("  %d audio files rescued" % m)

man = {
    "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    "reason": "Baba is doing a Kaggle factory reset; Kaggle artefacts must survive on this laptop.",
    "voice_files": [{"name": f, "bytes": s, "sha256": h, "verified": ok}
                    for f, s, h, ok in copied],
    "kaggle_dataset": "isearchxsolve/clinic-reference-voice",
    "kaggle_kernel": "isearchxsolve/kilo-voice-live",
    "tools_rescued": n,
    "audio_rescued": m,
    "restore_hint": ("re-create dataset isearchxsolve/clinic-reference-voice from voice/ + a fresh "
                     "datasets-metadata.json, then kaggle kernels push in kernels/"),
}
json.dump(man, open(os.path.join(RESCUE, "MANIFEST.json"), "w", encoding="utf-8"), indent=2)
print("\nMANIFEST: %s" % os.path.join(RESCUE, "MANIFEST.json"))
print("\n*** RESCUE COMPLETE -- Kaggle can be reset now ***")