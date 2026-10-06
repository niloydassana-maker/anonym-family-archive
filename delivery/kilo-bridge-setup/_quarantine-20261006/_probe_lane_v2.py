"""Bounded lane probe v2 - writes EVERY step straight to a file with fsync.

No stdout buffering, no job wrapper: even if this process is killed mid-way,
the file on disk is the complete answer to "where does it block?".
"""
import os, sys, time

LOG = r"D:\anonym\delivery\kilo-bridge-setup\_probe_lane_steps.log"

def step(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())

open(LOG, "w", encoding="utf-8").close()
step("BEGIN")
step(f"cwd={os.getcwd()} pid={os.getpid()}")

TOK = r"D:\anonym\war-log\sweep-browser.token"
step(f"token before = {'EXISTS' if os.path.exists(TOK) else 'absent'}")

step("import agent360_client ...")
sys.path.insert(0, r"D:\anonym\war-log")
try:
    import agent360_client as A
    step(f"import OK  TOKEN_PATH={A.TOKEN_PATH}")
    step(f"GATE={A.GATE}")
except Exception as e:
    step(f"IMPORT FAIL {type(e).__name__}: {e}")
    sys.exit(3)

step("constructing client ...")
c = A.Agent360Client()
step("constructed")

step("start() -- suspected hang point")
t0 = time.time()
try:
    c.start()
    step(f"start() RETURNED in {time.time()-t0:.1f}s gate_ticket={c._gate_ticket} file_tok={bool(c._browser_token)}")
except Exception as e:
    step(f"start() RAISED after {time.time()-t0:.1f}s {type(e).__name__}: {str(e)[:200]}")
    sys.exit(4)

step("browser_screenshot ...")
t0 = time.time()
try:
    r = c.call_tool("browser_screenshot", {"format": "png"})
    step(f"screenshot RETURNED in {time.time()-t0:.1f}s type={type(r).__name__}")
except Exception as e:
    step(f"screenshot RAISED after {time.time()-t0:.1f}s {type(e).__name__}: {str(e)[:200]}")

step("browser_execute_script document.title ...")
t0 = time.time()
try:
    r = c.call_tool("browser_execute_script", {"code": "document.title"})
    step(f"exec_script RETURNED in {time.time()-t0:.1f}s -> {str(r)[:200]}")
except Exception as e:
    step(f"exec_script RAISED after {time.time()-t0:.1f}s {type(e).__name__}: {str(e)[:200]}")

step("close() ...")
t0 = time.time()
try:
    c.close()
    step(f"close() RETURNED in {time.time()-t0:.1f}s")
except Exception as e:
    step(f"close warning: {e}")
step("END-REACHED")