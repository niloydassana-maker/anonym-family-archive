# ARCHITECTURE FINDING — WHY AN LLM DRIVER CANNOT RUN THIS LANE ON THE FREE TIER
### Recorded 2026-10-06, after three driver tests. This prevents a fourth wasted night.

## THE THREE ROOT CAUSES OF "THE AGENT TALKS INSTEAD OF ACTING"

All three are measured. All three are self-inflicted, and none is Chrome's fault.

### RC1 — A DEAD TOKEN HUNG EVERY TOOL CALL  (FIXED, see RCA-TOKEN-HANG-20261006.md)
`_acquire_browser_token()` had a dead-pid branch with **no deadline** and a single
release verb (`os.remove`, which raises WinError 32 on a contended file). A stale
token held by dead pid 11204 froze every client forever, silently.
**Status: FIXED and proven** — `TOKEN_DEAD_S = 300`, `_drop_or_take()` with an
`O_TRUNC` take-by-overwrite fallback, deadline on every branch, receipt on every path.

### RC2 — `crush run` DRIVES CORRECTLY; THE MODEL DOES NOT
Receipt that crush works: at 22:11:59, 5 s after launch, crush spawned
`PID 1904 (parent 19844 = crush)  python _now.py`. The tool loop is real.
Receipt that the model fails — the same 3-step test on every candidate:

| model | result |
|---|---|
| `nvidia/nemotron-3-super-120b-a12b` | ran step 1, then emitted crush's **context-summary schema** ("## Current State / ## Files & Changes / ## Technical Context") and stopped |
| `meta/llama-3.2-11b-vision-instruct` | emitted the **same summary schema twice**, and **hallucinated** having run all three commands, and leaked a system reminder |
| `deepseek-ai/deepseek-v4.1-flash` | **stalled at 0.0% CPU for 9+ minutes**, no output (PATIENCE LAW allows 2-5 min; this is past it) |
| `groq/openai/gpt-oss-120b` | **HTTP 413 "request entity too large"** |

The summarization schema is crush's **compaction/summary prompt**. Reasoning-class NVIDIA
models (nemotron, deepseek) obey that prompt or truncate their reasoning channel instead
of emitting tool calls. Non-reasoning models (llama-3.2) fabricate tool executions.

### RC3 — CRUSH'S SYSTEM PROMPT IS 111,464 TOKENS
```
ERROR Agent processing failed: request entity too large: Request too large for model
`openai/gpt-oss-120b` ... tokens per minute (TPM): Limit 8000, Requested 111464
```
This is the measured cause of RC2, and it is fatal on the free tier:
- Groq free (8,000 TPM): **died immediately, 413**
- NVIDIA endpoints: accept the size, then **stall** on a 111k-token prefill
- Any free endpoint with an 8k-32k TPM budget: **unusable for `crush run` at all**

**A `crush run` agent loop cannot be driven by a free endpoint.** No amount of
model-swapping fixes a 111k-token system prompt.

---

## THE ARCHITECTURE THAT ALREADY WORKS (and produced today's real progress)

The lane's real wins today — **15:22-17:54 IST, 12 ledger rows, 10 screenshots** — were
produced by **direct Python scripts**, not by an LLM loop:
```
_naukri_state.py  _naukri_tabs.py  _naukri_links.py  _naukri_realinks.py
_naukri_recs.py   _naukri_recs2.py _naukri_card.py   _naukri_dom.py
_naukri_onepass.py  _naukri_fetch.py  _naukri_results.py
```
They all follow one pattern, and it is the house pattern:

```python
import sys; sys.path.insert(0, r"D:\anonym\war-log")
import agent360_client as A
c = A.Agent360Client(); c.start()
def txt(n, a=None):
    r = c.call_tool(n, a or {}) or {}
    for b in r.get("content", []):
        if b.get("type") == "text":
            t = b.get("text", "")
            try: return json.loads(t)
            except Exception: return t
    return ""
def js(expr):
    r = txt("browser_execute_script", {"code": expr})
    return r.get("result") if isinstance(r, dict) else r
body = js("document.body.innerText")
c.close()
```

**Why this is the correct design here — not a fallback:**
1. **No token ceiling.** A script sends exactly the JS it needs; nothing is pre-filled
   into a 111k-token prompt.
2. **Deterministic and receipted.** The script IS the intelligence (regex parse, JS probe,
   screenshot). Same input, same action, every time.
3. **Fast.** Seconds, not 5-minute reasoning turns.
4. **Composable.** Any judgment that genuinely needs a model is ONE small API call with a
   SMALL prompt — never routed through crush's fat system prompt.

---

## THE DECISION (binding for this lane)

1. **HANDS:** `agent360_client.py` (Agent 360 MCP) — the only browser pipe. **FIXED.**
2. **DRIVER:** a named Python script per mission, written to
   `delivery/kilo-bridge-setup/scripts/`, one screenshot per milestone, one ledger row per
   action. **This is the driver.**
3. **LLM:** used ONLY on demand, directly, with a small prompt — for a recruiter question,
   a comment draft, a judgment call. Never as the thing that walks the browser.
4. **crush:** retained for what it is good at (reasoning about files in a small cwd). It is
   NOT the employment-lane driver until a free endpoint can accept a 111k-token prompt.
5. **Reporting:** every run writes its own log. A run with no log did not happen.

**Do not run a fourth driver test. Do not try another model. The wall is the system prompt,
not the model.**