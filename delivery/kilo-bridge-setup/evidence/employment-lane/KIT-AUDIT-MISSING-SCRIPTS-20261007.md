# KIT AUDIT - MISSING SCRIPTS + NEMOTRON LOG CHECK (2026-10-07)

Order: *"many scripts are missing in the kit setup check nemotron logs"*.
Method: read-only existence audit of every file the kit references + read of every
nemotron log and the crush driver-test logs. Nothing was deleted or moved.

---

## 1. VERDICT IN ONE LINE

The four **production driver scripts** (`lane_resume.py`, `lane_jobs.py`, `lane_apply.py`,
`prove_lane.py`) and their `agent360_client.py` dependency are **all present**. What is
missing is: (a) the three **portal drivers for work-orders C/D/E that were never built**,
(b) two **scratch RCA scripts** referenced in comments (`scripts\_now.py`,
`scripts\_lane_jobs_new.py`), and (c) **git tracking** for the newest scripts.

The **nemotron logs are consistent with `ARCHITECTURE-FINDING-20261006.md`**: every NVIDIA
nemotron reasoning model fails as a `crush run` driver exactly as documented.

---

## 2. SCRIPTS PRESENT (the ones that matter)

| File | Present | Notes |
|---|---|---|
| `scripts/agent360_client.py` | YES | SHA256 `55C8EAE7...B06294` - **byte-identical to `war-log\agent360_client.py`** (verified) |
| `scripts/lane_resume.py` | YES | work-order A driver (proven 2026-10-06 22:47) |
| `scripts/lane_jobs.py` | YES | work-order B driver (proven 2026-10-06 22:56) |
| `scripts/lane_apply.py` | YES | the money step; `py_compile` clean; 21,576 b |
| `scripts/prove_lane.py` | YES | 4-portal live proof (setup verdict depends on it) |
| `scripts/_wire_opencode.py` | YES | config surgery |
| `scripts/_semantic_diff.py` | YES | config diff helper |
| `scripts/_probe_jobs_dom.py` | YES | DOM probe |
| `scripts/apply_answers.txt` | YES | operator record answers (`genai|2`) |
| `scripts/install-task.ps1` / `self-loop.ps1` | YES | unattended loop (buyer copy) |
| `_now.py` (kit root) | YES | the crush tool-test probe |

Root-level confirmations: `D:\anonym\war-log\launch_profile17.py` YES,
`D:\anonym\opencode.json` YES, `D:\anonym\kilo_apply_resume.pdf` YES
(SHA256 `DE81F585...FC339F` - matches the mission pin, byte-equal to
`Kunal Das - Email Only.pdf`). Toolchain present: `browser-mcp\index.js`,
`opencode.exe`, `crush.cmd`, `agy.exe`, node v22.23.2, python 3.11.9.

---

## 3. SCRIPTS MISSING

### 3.1 NEVER BUILT - the real gap (work-orders C, D, E)
`scripts\lane_foundit.py`, `scripts\lane_indeed.py`, `scripts\lane_linkedin.py` **do not
exist anywhere** (kit, war-log, or root). The mission
(`docs\EMPLOYMENT-LANE-MISSION.md` §1, four portals; `MISSION-RUN.txt` steps C/D/E)
names Foundit, Indeed and LinkedIn, but **only Naukri has a driver**. This matches the
honest "NOT DONE" list in `DRIVERS-20261006.md` line 159.

### 3.2 SCRATCH RCA SCRIPTS REFERENCED IN COMMENTS BUT ABSENT
| File | Where referenced | State |
|---|---|---|
| `scripts\_now.py` | `rca-micro.ps1` (`crush ... python _now.py`), `DRIVERS-20261006.md` line 20 | **absent**; a copy exists at the kit ROOT as `_now.py`, not under `scripts\` |
| `scripts\_lane_jobs_new.py` | `_wrapup.ps1` quarantine list | **absent from both `scripts\` and `_quarantine-20261006\`**; only its stale `__pycache__\_lane_jobs_new.cpython-311.pyc` survives |

Both are RCA scratch, not production - their absence does not stop the lane, but the
crush-era RCA scripts cannot be re-run verbatim.

### 3.3 QUARANTINED (present, intentionally moved - not lost)
`_probe_lane_bounded.py`, `_probe_lane_v2.py`, `_token_micro.py`, `_remove_test.py`,
`_multiturn_test.ps1`, `_probe_nv_live.py`, `_probe_thinking.py` - all live in
`_quarantine-20261006\` (house convention: never delete a record). Not missing.

### 3.4 PRESENT ON DISK, NOT TRACKED BY GIT - the delivery risk
`git ls-files delivery/kilo-bridge-setup/scripts` returns only **7** files. These newer
files are **untracked**, so a buyer who clones the repo would not receive them:

```
scripts\lane_apply.py          <- the money-step driver (the product)
scripts\apply_answers.txt      <- the operator record answers it depends on
scripts\_wire_opencode.py      <- the setup script calls this
scripts\_semantic_diff.py      <- setup helper
_now.py                        <- crush RCA probe
```
(`lane_jobs.py`, `lane_resume.py`, `prove_lane.py`, `agent360_client.py`, `install-task.ps1`,
`self-loop.ps1`, `_probe_jobs_dom.py` ARE tracked.) **`git add` before any buyer copy ships.**

---

## 4. NEMOTRON LOG CHECK (the logs the order pointed at)

| Log | Model | Measured result |
|---|---|---|
| `_drive_test_nv-super120-low.log` | `nvidia/nemotron-3-super-120b-a12b` (`--reasoning-effort low`) | **ERROR "Model does not support reasoning effort"** -> exit=1 after 4 s |
| `_drive_test_nv-deepseek41.log` | `deepseek-ai/deepseek-v4.1-flash` | **EMPTY, 0 bytes** - no output (stall; ARCHITECTURE finding: 0.0% CPU for 9 min) |
| `_drive_test_nv-llama32-11b.log` | `meta/llama-3.2-11b-vision-instruct` | **FABRICATED** the runs ("We executed three Windows commands") and **leaked a system reminder** |
| `_multiturn_test.log` | `nemotron-3-super-120b` via crush | emitted crush's **context-summary schema** ("## Strategy & Approach / ## Exact Next Steps"), exit=0 after 211 s |
| `_drive_test_groq-oss120b.log` | `openai/gpt-oss-120b` (Groq) | **HTTP 413** - "Requested 111464 ... Limit 8000 TPM" |

**Conclusion (unchanged from the record):** nemotron reasoning models answer with crush's
summary prompt instead of emitting tool calls; llama fabricates; deepseek stalls; Groq dies
on size. The wall is `crush`'s **111,464-token system prompt**, not the model
(`ARCHITECTURE-FINDING-20261006.md`). **Do not run a fourth driver test.**
The lane's correct driver is a named Python script through `agent360_client.py`, which is
exactly what `lane_apply.py`/`lane_jobs.py`/`lane_resume.py` are.

Note: unrelated to this kit, `nemotron` also appears as the live *voice* brain in
`war-log\voice-live\` (v55+ `nemotron-3-super-120b` HTTP API, not crush) - that is a
different lane and is healthy there.

---

## 5. WHAT TO DO (in order)

1. **`git add`** the five untracked scripts (3.4) so the delivery package is complete.
2. **Build the C/D/E drivers** (`lane_foundit.py` first - closest DOM shape to Naukri),
   then Indeed, then LinkedIn - the mission's own order.
3. Optional: copy `_now.py` into `scripts\` (or fix the two RCA comments) so the crush-era
   RCA scripts re-run verbatim. Low priority.
4. Do NOT re-run crush driver tests (4).

***Collected: Rs 0.*** An audit is not an application; the money step stays
`lane_apply.py` reaching a real APPLIED with a screenshot.

---

## 6. ADDENDUM - 2026-10-07 (git-add executed, sha pinned, wider staging risk found)

Item 5.1 (the `git add`) is now DONE, not just recommended. Measured:

| File staged | bytes | SHA256 |
|---|---|---|
| `scripts/lane_apply.py` | 21576 | `B49781CDDE77...2C3ED9E` |
| `scripts/apply_answers.txt` | 450 | `8A380A41182C...6DAC916` |
| `scripts/_wire_opencode.py` | 2702 | `BCBDFBE1755B...F5222623` |
| `scripts/_semantic_diff.py` | 1035 | `2FF0FC7A21F3...F11191936BA` |
| `_now.py` (kit root) | 483 | `E37CAA88C62D...0BF963A` |

`git status --porcelain -- delivery/kilo-bridge-setup/scripts(...)` now shows all five as `A`.
`py_compile` clean on `lane_apply.py lane_jobs.py lane_resume.py prove_lane.py agent360_client.py`.

**SECRETS CHECK on this kit: CLEAN.** Zero `nvapi-` / `authtoken` / `sk-` literals in the five
staged files or in the nine production scripts. The kit is safe to commit.

**WIDER STAGING RISK (NOT this kit - other lanes' files sitting in the same index):**
`git diff --cached` also carries files with LITERAL provider keys - must not be committed as-is:
- `RESCUE-kaggle-reset/kernels/{_v42,_v44,_v45,_v49,_v51,_v52,_v53,_v55,kilo-voice-live}.py`
  (1-9 literal `nvapi-` keys each)
- `delivery/kilo-bridge-setup/_quarantine-20261006/_probe_nv_live.py`, `_probe_thinking.py` (1 each)
- `test_nemotron_models.py` (6)
Fix = revoke/replace those keys, then `git rm --cached` the key-bearing files (keep on disk) before
any push. This is why the commit is held for Baba's one decision; the key-carrying staging was
created by earlier sessions and is not un-staged unilaterally.

**LIVE GATE STATE at addendum time:** `HANDS-OFF.flag` = absent (driver work permitted);
relay :8777 = `ok relay-live bank=18437`; `browser-mcp/index.js`, `launch_profile17.py`,
`scripts/agent360_client.py` all present; ledger = 80 rows; Chrome already running (63 procs -
not driven by this audit, single-driver law).