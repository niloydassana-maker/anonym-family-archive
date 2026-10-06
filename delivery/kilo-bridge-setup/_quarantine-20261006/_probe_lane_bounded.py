"""Bounded lane probe - tells us EXACTLY where the browser path blocks.

Prints one line per step with flush, so the partial log is the answer even if
the process must be killed. Never hangs more than ~60s in total.
"""
import io, sys, os, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def step(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

step("BEGIN")
step(f"cwd={os.getcwd()}")
step(f"pid={os.getpid()}")

# 0. is a token present before we start?
TOK = r"D:\anonym\war-log\sweep-browser.token"
step(f"token before = {'EXISTS' if os.path.exists(TOK) else 'absent'}")

step("importing agent360_client from D:\\anonym\\war-log ...")
sys.path.insert(0, r"D:\anonym\war-log")
try:
    import agent360_client as A
    step(f"import OK  TOKEN_PATH={A.TOKEN_PATH}")
except Exception as e:
    step(f"IMPORT FAILED {type(e).__name__}: {e}")
    sys.exit(3)

step("constructing client ...")
try:
    c = A.Agent360Client()
    step("constructed")
except Exception as e:
    step(f"CONSTRUCT FAILED {type(e).__name__}: {e}")
    sys.exit(3)

step("calling start() -- THIS is the suspected hang point ...")
t0 = time.time()
try:
    c.start()
    step(f"start() RETURNED in {time.time()-t0:.1f}s  gate_ticket={c._gate_ticket}")
except Exception as e:
    step(f"start() RAISED after {time.time()-t0:.1f}s  {type(e).__name__}: {str(e)[:200]}")
    sys.exit(4)

step("calling browser_screenshot (forces extension bind) ...")
t0 = time.time()
try:
    r = c.call_tool("browser_screenshot", {"format": "png"})
    step(f"screenshot RETURNED in {time.time()-t0:.1f}s  keys={list(r.keys()) if isinstance(r,dict) else type(r)}")
except Exception as e:
    step(f"screenshot RAISED after {time.time()-t0:.1f}s  {type(e).__name__}: {str(e)[:200]}")

step("calling browser_execute_script document.title ...")
t0 = time.time()
try:
    r = c.call_tool("browser_execute_script", {"code": "document.title"})
    step(f"execute_script RETURNED in {time.time()-t0:.1f}s  -> {str(r)[:300]}")
except Exception as e:
    step(f"execute_script RAISED after {time.time()-t0:.1f}s  {type(e).__name__}: {str(e)[:200]}")

step("closing")
try:
    c.close()
    step("closed cleanly")
except Exception as e:
    step(f"close warning: {e}")
step("END")