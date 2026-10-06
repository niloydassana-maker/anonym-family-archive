"""Upload clinic_reference_fast.wav to the SAME Kaggle dataset (a version update, not a new one).

Baba: "little slow" (2026-10-03). Cause was measured, not guessed -- the 9.93 s reference stretched
every clinic line by 25-35%. The trimmed window is 5.00 s with loudness held at -20 LUFS, so the only
variable is speaking rate.

HONEST NOTE ON THE PICK: every candidate window measured mean -21.9 to -22.8 dB, i.e. all of them
are essentially the same loudness. So the selection had almost nothing to discriminate on and it
chose the shortest window on that near-tie. That is a weak selection, not a strong one -- it is
recorded here so nobody later reads "densest speech window" as a measured fact.
"""
import hashlib, json, os, shutil, subprocess, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"D:\anonym\realhindivoice\clinic_reference_fast.wav"
STAGE = r"D:\anonym\war-log\voice-live\kaggle-ref-clinic"

dst = os.path.join(STAGE, "clinic_reference_fast.wav")
shutil.copyfile(SRC, dst)
h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
print("staged %s  %d bytes" % (dst, os.path.getsize(dst)))
print("sha256 %s" % h)

r = subprocess.run(["kaggle", "datasets", "version", "-p", STAGE, "--dir-mode", "tar",
                    "-m", "Add clinic_reference_fast.wav: 5.00 s trimmed window of the same clinic "
                          "voice. Baba 2026-10-03 'little slow' -- the 9.93 s reference stretched every "
                          "clinic line 25-35%; loudness held at -20 LUFS so only speaking rate changes. "
                          "SHA256 E60261FA08D543ABCD72452535BAFF22FA5279137E03A873BFE07771DA968856"],
                   capture_output=True, text=True, timeout=600)
print("\nupdate -> exit %s" % r.returncode)
print((r.stdout or "").strip()[:600])
if (r.stderr or "").strip():
    print("stderr:", r.stderr.strip()[:400])

time.sleep(3)
v = subprocess.run(["kaggle", "datasets", "files", "isearchxsolve/clinic-reference-voice"],
                   capture_output=True, text=True, timeout=180)
print("\ndataset files now:")
print((v.stdout or "").strip()[:600])