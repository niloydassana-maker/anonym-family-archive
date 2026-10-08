# FIX ALL ISSUES - DIAGNOSIS + REPAIR (2026-10-07, "fix all issues")

Baba pasted the full opencode run where the agent churned ~20 min and never reached an
apply. This is the forensic record + what was built to fix it.

## THE FOUR ROOT CAUSES (all diagnosed from evidence, not guessed)

**1. TAB LOSS / `about:blank` phantom loop — the core bug.**
Evidence: `bind-screenshot2.png` (5 KB, pure white) was taken at the moment `TABS` read
`about:blank`; `apply-01-naukri-genai-architect-before.png` (147 KB) is the real Naukri
page. **The browser was never broken** — the real logged-in page rendered fine.
Cause: the agent spawned a NEW `Agent360Client` on every tool call (each `python -c`
shell-out) → new node child → fresh session group → the Naukri tab "vanished" from
`list_tabs`. It misread `TABS: []` as "extension unbound", then "re-bound" by taking
`browser_screenshot`/`navigate`, which just **creates a fresh blank tab** — feeding the
loop. It never did nav+click in ONE session.

**2. BACKGROUND TAB → CDP mouse timeout.**
`browser_click` on the real card returned `CDP did not respond within 1500 ms ... call
browser_switch_tab`. The tab was `active:false`. The agent correctly read this, but kept
spawning new sessions so `switch_tab` never helped.

**3. INLINE JS ESCAPING — 3 failures.**
`python -c` + PowerShell here-string + `&&`/`(` inside JS produced:
`ParserError: An expression was expected after '('`, `The token '&&' is not a valid
statement separator`, and Python `SyntaxError: unterminated string literal` (x2).
Complex JS in a shell one-liner is structurally unsafe here.

**4. DEAD `/job-apply` HREF SELECTOR.**
JS returned `clicked:false, count:0` — the recommended-jobs page carries **no job URL**
(the named wall in DRIVERS-20261006.md). Selecting by `/job-apply` href can never match.
The card is an `<article class="jobTuple ...">` with an `onclick`, title unique on page.

## THE FIX: `scripts/lane_apply.py` (compiles CLEAN, 10,405 bytes)
One driver, one session, proven `lane_jobs.py` pattern:
- ONE `Agent360Client` for the whole turn (no per-call session churn → no phantom tabs).
- NAVIGATE-FIRST → locate card by EXACT TITLE (not href) → JS `.click()` (mouse is dead)
  → verify by URL change OR an apply-flow marker → screenshot → ledger.
- Recruiter question detected → answer **only** from `apply_answers.txt` (never invent),
  else **BLOCKED** with the verbatim question. Never force-submits past a gate.
- All JS from variables — zero inline shell escaping.

Run: `python scripts\lane_apply.py "<exact job title>"` (or no arg → top MATCHED ledger row).

## LARGER LESSON (the agent's failure was NOT capability)
opencode+Nemotron+Agent360 all worked: it read the constitution, reasoned the money step,
launched Chrome, navigated to logged-in Naukri, and self-diagnosed the `switch_tab` hint.
It failed because it drove the browser **ad-hoc through shell one-liners** instead of the
proven single-session driver. **The driver removes the fumbling; the model was fine.**

## STATE
- Mission proc 21264 ALIVE but output STALLED ~10 min at `TABS: []` (phantom loop) — needs
  intervention (point it at `lane_apply.py` or restart the drive).
- Gate :7880 DOWN → client falls back to file token (by design, not a bug).
- agent360_client.py SHA256 `55C8EAE7...B06294` UNTOUCHED (lock respected).
- **Collected today: Rs 0.** A driver that reaches apply is not a payment.