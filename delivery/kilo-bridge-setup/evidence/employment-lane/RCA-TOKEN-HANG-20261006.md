# RCA — WHY THE EMPLOYMENT LANE FROZE SILENTLY (2026-10-06)

**Status: ROOT-CAUSED, FIXED, PROVEN.** The lane was never broken by Chrome, the
extension, or the model. It was frozen by a **token file whose dead holder could
never be released**, in a loop that had **no deadline on that branch**.

---

## 1. THE SYMPTOM BABA SAW
Agents launched, answered, and *talked* instead of acting. Runs produced no ledger
rows. Everything was killed and relaunched repeatedly with the same result. The
earlier theory blamed `crush run` being one-shot.

**That theory was WRONG**, and it is corrected here:

**`crush run` DOES execute tool calls.** Measured, not argued — at 22:11:59, 5 s
after launch, crush spawned:
```
PID 1904  parent=19844 (crush)   cmd: python _now.py
PID 19976 parent=1904            cmd: "...\Python311\python.exe" _now.py
```
`crush run` was driving the shell tool correctly. The tool call then **hung forever**,
so the agent looked like it was stalling on text. The freeze was one layer below the agent.

---

## 2. THE ROOT CAUSE — TWO FAULTS IN ONE BRANCH

### Fault A — a DEAD-pid branch with NO deadline
`_acquire_browser_token()` handled a dead holder like this (old code, lines 101-116):

```python
with open(TOKEN_PATH, "rb") as stream:
    if stream.read() == current_bytes:
        for _ in range(40):
            try:
                os.remove(TOKEN_PATH); break
            except PermissionError: time.sleep(0.05)
            except OSError: break
        else:
            time.sleep(0.25)
# ...then falls through to the TOP of `while True:` and repeats
```

The `if _pid_alive(current_pid)` was **False**, so the code never checked the
deadline. If `os.remove()` could not succeed, this loops **forever**, silently.

### Fault B — `os.remove()` CANNOT succeed here, and that is the COMMON case
Measured with the exact handle error:
```
os.remove FAILED  type=PermissionError errno=13 winerror=32
   strerror=The process cannot access the file because it is being used by another process
```
WinError 32 is raised because **the loop's own poll reads hold a handle to the file**
while it tries to delete it — every waiter polls every 250 ms. So the failure is not
rare; it is the normal condition the moment more than one client is waiting.

### The two faults together
A stale token held by a **dead pid**, being **read continuously**, in a branch that
**never checks the deadline** = a perfect infinite loop.

**Receipt of the freeze:**
```
[22:19:39] token before = EXISTS
[22:22:02] current token = {'pid': 11204, 'since': '2026-10-06T15:50:56Z'}
[22:22:02] pid_alive(11204) = False          <- correctly detected as dead
[22:22:02] mtime_age = 3665.8s               <- over an hour cold
[22:22:02] calling _acquire_browser_token(wait_seconds=8)
           ... no return, no exception, past the requested deadline
```
`_pid_alive` worked perfectly. The loop simply never consulted it in a way that
could exit.

---

## 3. THE SECOND STALE COPY (already fixed, worth recording)
`D:\anonym\delivery\kilo-bridge-setup\scripts\sweep-browser.token` was deleted earlier
in the session as "the stale lock". The token that actually mattered lives at
**`D:\anonym\war-log\sweep-browser.token`** — `agent360_client.TOKEN_PATH` resolves
next to the module, and both client copies resolve to `war-log`. **Deleting the copy
in `scripts\` changed nothing.** A stale lock must be cleared at the path the code
actually reads; verify `TOKEN_PATH` from the module, never assume from the folder.

---

## 4. THE FIX (in `D:\anonym\war-log\agent360_client.py`, synced to `scripts\`)

1. **`TOKEN_DEAD_S = 300` — a COLD token is not a driver, whatever its pid says.**
   Age > 300 s neutralises the token. This single rule would have saved the whole session.
2. **`_drop_or_take()` — bounded, and it cannot spin.** Removes the file; on
   `PermissionError` (WinError 32) it retries `12 x 50 ms`, then **TAKES the token by
   exclusive overwrite** (`O_WRONLY | O_TRUNC`) with our own record. Every outcome
   prints a receipt: `BROWSER-TOKEN DROP` / `TAKEN by overwrite` / `UNREMOVABLE`.
3. **No unbounded branch remains.** Every path either returns, neutralises, or raises
   `TimeoutError` at the deadline naming the holder pid and age.
4. **Re-entrancy guard:** if the token already holds *our* pid+since (from a previous
   take-by-overwrite pass), return immediately instead of spinning.
5. **Malformed tokens stay fail-closed** unless they are ALSO cold.

### PROOF — three cases, all resolve in 0.0 s
```
BROWSER-TOKEN DROP pid 14788 (idle yield 230s)
BROWSER-TOKEN DROP pid 999999 (dead pid)
BROWSER-TOKEN DROP pid 14788 (cold token 999s)

TEST1 (stale live owner)     ACQUIRED in 0.0s   release -> True
TEST2 (dead pid 999999)      ACQUIRED in 0.0s
TEST3 (live pid, cold mtime) ACQUIRED in 0.0s
```

### PROOF — the lane itself, end to end, after the fix
```
[22:27:14] token before = absent
[22:27:22] start() RETURNED in 7.7s   gate_ticket=None file_tok=True
[22:27:44] screenshot RETURNED in 22.1s type=dict
[22:27:44] exec_script RETURNED in 0.0s -> {"result":"","method":"debugger"}
[22:27:44] close() RETURNED in 0.0s
[22:27:44] END-REACHED          token after = ABSENT
```

---

## 5. LAWS BORN (binding on this lane)

1. **A LOCK MUST BE RELEASABLE BY AGE, NOT ONLY BY PID.** Pid liveness is necessary,
   never sufficient — a dead pid behind an unremovable file is a deadlock. Any lock
   needs a staleness ceiling that does NOT depend on the holder cooperating.
2. **WHEN A FILE IS HELD, DELETE IS NOT THE ONLY VERB.** `O_TRUNC` overwrite takes a
   contended file where `os.remove` raises WinError 32. Never let a release path have
   exactly one mechanism.
3. **NO LOOP WITHOUT A DEADLINE ON EVERY BRANCH.** A single path without a deadline
   check is a silent freeze. The old code had the check on one branch and not the other.
4. **A FREEZE MUST PRINT.** Every neutralise/refuse path now writes a receipt line.
   A wall with no log line costs a night; this one did.
5. **CLEAR THE LOCK AT THE PATH THE CODE READS.** Read `TOKEN_PATH` from the module.
6. **WHEN A TOOL ANSWERED TEXT INSTEAD OF ACTING, TEST ONE LAYER DOWN.** crush was
   blamed; crush was working. The tool it called was frozen.

---

## 6. ARTIFACTS
- Fix: `D:\anonym\war-log\agent360_client.py` (SHA256 `55C8EAE7...B06294`,
  byte-identical to `scripts\agent360_client.py`)
- Proof scripts: `_token_micro.py`, `_remove_test.py`, `_fix_verify.py`,
  `_probe_lane_v2.py` (step logs `_token_micro.log`, `_remove_test.log`,
  `_fix_verify.log`, `_probe_lane_steps.log`)
- Agent tree receipt: crush PID 19844 -> python PID 1904 `python _now.py`