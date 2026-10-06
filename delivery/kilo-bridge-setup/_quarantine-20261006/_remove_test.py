"""Why can't the dead token be removed? Print the EXACT WinError."""
import os, sys, time, json, errno

LOG = r"D:\anonym\delivery\kilo-bridge-setup\_remove_test.log"
def step(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {m}\n"); f.flush(); os.fsync(f.fileno())
open(LOG, "w").close()

TOK = r"D:\anonym\war-log\sweep-browser.token"
step(f"exists before = {os.path.exists(TOK)}")
if os.path.exists(TOK):
    with open(TOK, "rb") as f: step(f"content = {f.read()!r}")

step("attempt os.remove ...")
try:
    os.remove(TOK)
    step("os.remove SUCCEEDED")
except Exception as e:
    step(f"os.remove FAILED  type={type(e).__name__} errno={getattr(e,'errno',None)} "
         f"winerror={getattr(e,'winerror',None)} strerror={getattr(e,'strerror',None)}")

step(f"exists after = {os.path.exists(TOK)}")

# can we overwrite in place instead?
step("attempt in-place overwrite ...")
try:
    with open(TOK, "w", encoding="utf-8") as f:
        f.write(json.dumps({"pid": os.getpid(), "since": "TEST"}) + "\n")
        f.flush(); os.fsync(f.fileno())
    step(f"overwrite OK -> {open(TOK).read()!r}")
    os.remove(TOK)
    step("cleanup remove OK (file released)")
except Exception as e:
    step(f"overwrite FAILED type={type(e).__name__} errno={getattr(e,'errno',None)} winerror={getattr(e,'winerror',None)}")
step("END")