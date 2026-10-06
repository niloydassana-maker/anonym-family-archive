"""Verify the FIX: _acquire_browser_token must return (or raise) inside its deadline."""
import os, sys, time, json

LOG = r"D:\anonym\delivery\kilo-bridge-setup\_fix_verify.log"
def step(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {m}\n"); f.flush(); os.fsync(f.fileno())
open(LOG, "w").close()

sys.path.insert(0, r"D:\anonym\war-log")
import agent360_client as A

step(f"py ok  TOKEN_PATH={A.TOKEN_PATH}  TOKEN_DEAD_S={A.TOKEN_DEAD_S}  TOKEN_STALE_S={A.TOKEN_STALE_S}")
TOK = A.TOKEN_PATH
if os.path.exists(TOK):
    step(f"token before = {open(TOK).read().strip()!r}")
    step(f"mtime_age = {time.time()-os.path.getmtime(TOK):.1f}s")
else:
    step("token before = ABSENT")

step("TEST 1: _acquire_browser_token(wait_seconds=10)  [must not hang]")
t0 = time.time()
try:
    owner = A._acquire_browser_token(wait_seconds=10)
    step(f"TEST1 ACQUIRED in {time.time()-t0:.1f}s owner={owner}")
    step(f"token now = {open(TOK).read().strip()!r}")
    rel = A._release_browser_token(owner)
    step(f"release -> {rel}; token exists after = {os.path.exists(TOK)}")
except Exception as e:
    step(f"TEST1 RAISED after {time.time()-t0:.1f}s {type(e).__name__}: {e}")

step("TEST 2: plant a DEAD-pid token, acquire must still succeed quickly")
try:
    with open(TOK, "w") as f:
        f.write(json.dumps({"pid": 999999, "since": "DEAD-TEST"}) + "\n")
    t0 = time.time()
    owner = A._acquire_browser_token(wait_seconds=10)
    step(f"TEST2 ACQUIRED in {time.time()-t0:.1f}s owner={owner}")
    A._release_browser_token(owner)
except Exception as e:
    step(f"TEST2 RAISED after {time.time()-t0:.1f}s {type(e).__name__}: {e}")

step("TEST 3: plant a LIVE-but-cold token (our own pid, old mtime) -> cold rule")
try:
    with open(TOK, "w") as f:
        f.write(json.dumps({"pid": os.getpid(), "since": "COLD-TEST"}) + "\n")
    old = time.time() - 999
    os.utime(TOK, (old, old))
    t0 = time.time()
    owner = A._acquire_browser_token(wait_seconds=10)
    step(f"TEST3 ACQUIRED in {time.time()-t0:.1f}s owner={owner}")
    A._release_browser_token(owner)
except Exception as e:
    step(f"TEST3 RAISED after {time.time()-t0:.1f}s {type(e).__name__}: {e}")

step("ALL TESTS DONE")