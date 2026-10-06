"""Micro-test _acquire_browser_token against the ACTUAL stale token state."""
import os, sys, time, json

LOG = r"D:\anonym\delivery\kilo-bridge-setup\_token_micro.log"
def step(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {m}\n"); f.flush(); os.fsync(f.fileno())

open(LOG, "w").close()
sys.path.insert(0, r"D:\anonym\war-log")
import agent360_client as A

TOK = A.TOKEN_PATH
step(f"TOKEN_PATH={TOK}")
if os.path.exists(TOK):
    with open(TOK) as f: cur = json.load(f)
    step(f"current token = {cur}")
    step(f"pid_alive({cur['pid']}) = {A._pid_alive(int(cur['pid']))}")
    st = os.stat(TOK)
    step(f"mtime_age = {time.time() - st.st_mtime:.1f}s   TOKEN_STALE_S = {A.TOKEN_STALE_S}")
step(f"pid_alive(self={os.getpid()}) = {A._pid_alive(os.getpid())}")

step("calling _acquire_browser_token(wait_seconds=8) ...")
t0 = time.time()
try:
    owner = A._acquire_browser_token(wait_seconds=8)
    step(f"ACQUIRED in {time.time()-t0:.1f}s owner={owner}")
    A._release_browser_token(owner)
    step("released")
except Exception as e:
    step(f"RAISED after {time.time()-t0:.1f}s {type(e).__name__}: {e}")
step("micro END")