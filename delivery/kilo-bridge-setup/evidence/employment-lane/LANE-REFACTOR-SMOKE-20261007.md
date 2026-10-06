# LANE REFACTOR + LIVE SMOKE RECEIPT (2026-10-07)

Order: harden `agent360_client.py` with self-verifying verbs, refactor the four
employment lanes into thin goal-runners over ONE shared tool layer, then prove it
live. This file is the receipt. Every number below was measured, not asserted.

## 1. WHAT WAS BUILT

- `scripts/agent360_client.py` (**+126 lines, additive**) - verifying verbs that
  return POST-ACTION STATE, not a bare "done":
  `_js`, `url`, `toast`, `readback`, `fill_verified`/`fill_checked`,
  `find_and_click`/`findclick`. A click hands back `{ok,url,toast,url_changed}`;
  a fill is RE-READ from the DOM (`ok` only when readback == value).
  Additive/self-contained (uses only `call_tool`) -> the 20+ live `a360_*`
  daemons are untouched.
- `scripts/lane_tools.py` (NEW, ~14K) - the shared layer: `Lane` (evidence dir,
  ledger, screenshot, wall test, verdict), `session`, `read_page`, `read_cards`
  (MEASURES which candidate selector has the most real nodes - never guesses),
  `score_card`, `click_by_text`, `fill_then_verify`, `read_recruiter_question`,
  `answer_from_record`, `answer_and_save` (verified read-back + Save).
- `lane_jobs / lane_foundit / lane_resume / lane_apply` rewritten as thin
  GOAL-RUNNERS over that layer. Sizes: apply 21.6K->9.6K, jobs 7.5K->3.9K,
  resume 6.4K->4.3K, foundit 6.1K->4.7K.
- `scripts/_test_lane_tools.py` (NEW) - offline regression suite.

## 2. OFFLINE VERIFICATION (before any browser)

| check | result |
|---|---|
| `python _test_lane_tools.py` | **26/26 PASS** (no Chrome, no network) |
| `py_compile` on all six modules | **OK** |
| both `agent360_client.py` copies | **byte-identical**, SHA256 `9D44781F1E02...A89EDA2` |
| `git diff --numstat agent360_client.py` | `126 0` (purely additive) |
| key literals in lane scripts / staged diff | **none** |
| leftover `*.NEW.py` | **none** |

Bug caught while testing: `_js` already parses JSON strings to a dict, so
`_fill_panel`'s second unwrap would have made EVERY fill read as failed. Fixed and
covered by test 7 (`_fill_panel reads dict-direct` / `tolerates result-wrap` /
`parses a JSON string`).

## 3. LIVE SMOKE (real Chrome, one driver)

Driver state before the run: browser-queue gate `:7880` = `held:null` (free);
`@agent360/browser-mcp` (PID 21096) alive; `chrome-devtools-mcp` on `:9224` =
port DEAD (husks only, cannot fight for Chrome) -> single-driver condition met.

### 3.1 prove_lane.py -> LANE-VERDICT: GREEN

```
screenshot returned -> extension bound
  Naukri    LIVE  chars=  6099  Home | Mynaukri
  Foundit   LIVE  chars=  3339  8,00,000+ Jobs in India
  Indeed    LIVE  chars=  3409  Job Search India | Indeed
  LinkedIn  LIVE  chars=  5223  Feed | LinkedIn
employment-lane signals on Naukri: KUNAL yes / Search appearances yes /
  Recruiter actions yes / 100% yes
portals with a LIVE session: 4/4
LANE-VERDICT: GREEN
Agent360Client closed cleanly
```
Receipt: `prove_lane-run-20261007.log`.

### 3.2 lane_jobs.py -> cards read + gated (measured selector)

```
B1 navigate -> .../recommendedjobs   chars=30304
shot -> 40-naukri-recommended-20261007-025000.png
B3 cards: selector=[class*=jobTuple] n=177
  [16] score=10 PASS GenAI Architect | Generative AI | LLM | RAG | Agentic AI
  [19] score=7  PASS Architect/Lead AI Engineer (Agentic AI)
  [13] score=3  PASS Core Gen AI / Generative AI Architect- Healthcare
  ...
B4 evaluated=12  gate-passed=8
SUMMARY naukri :: MATCHED 8  NO_MATCH 4
client closed cleanly
```
Receipt: `lane_jobs-run-20261007.log`. The selector was MEASURED
(`[class*=jobTuple]`, 177 nodes), not guessed. Ledger wrote one row per action.

## 4. LEDGER

`evidence/employment-lane/ledger.tsv` - 92 rows. New rows carry source URL,
title, score, step, status, the screenshot path as the receipt, and the matched
skills. One row per action, written as it happens (never reconstructed).

## 5. COMMIT (gated on no-key-in-diff)

`fb09eba` "employment lanes: self-verifying client verbs + shared lane_tools
(thin goal-runners)" - 8 files, **+908 / -654**. Pushed to `origin/master`
(`isearchxsolve/anonym-family-archive`). Commit was EXPLICIT-PATH scoped:
`git add -A` would have swept in untracked key-bearing files (see 6).

## 6. FINDINGS FLAGGED (NOT mine to fix - REPORT ONLY)

1. **Key-bearing untracked files in the working tree** (would leak on a blanket
   add): `opencode.json.bak-20261006-234023`, `opencode.json.bak-20261006-234814`,
   `tmp-opencode-config.txt` - each holds a literal `nvapi-` key. Left in place,
   NOT staged. Fix = revoke/replace the keys in the NVIDIA dashboard, then remove
   the local copies. (Same class as FLAG 2.)
2. **Dead `chrome-devtools-mcp` husks** (PID 22348 + child 8280) - the RETIRED
   package (HARD ROCK 26.1). `:9224` is dead and no Chrome carries
   `--remote-debugging-port`, so they drive nothing. Reported, not killed
   (NEVER-KILL-BROTHERS: not confirmed to be a brother's live lane).
3. **MISMATCH lesson on `prove_lane` title echo**: `browser_execute_script`
   returns `{'result': <value>, 'method':...}`; `prove_lane`'s local `txt()`
   JSON-parses only the raw text, so a JS-object return shows as the raw dict
   rather than the bare string. Liveness is judged on `document.body.innerText`
   (a plain string) - unaffected. `lane_tools` routes through `client._js`, which
   unwraps `result` correctly.

## 7. HONEST STATE

**Collected: Rs 0.** This session proved the tooling and the read/scoring lanes
end to end. It did not reach an application submit. The money step stays
`lane_apply.py` reaching a real APPLIED with a submission-success signal and a
screenshot - an apply is not an application until that signal is on the page.