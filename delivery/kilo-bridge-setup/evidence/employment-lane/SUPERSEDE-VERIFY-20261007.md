# SUPERSEDE VERIFY + LANE STATE (2026-10-07)

Read-back of the `_ledger_supersede.py` run and the lane file, verified on disk.

## 1. LEDGER SUPERSEDE — CONFIRMED (append-only, nothing overwritten)
`scripts/_sup_out.txt` (run output) says:
```
SUPERSEDE rows appended: 2
exit=0
compile_exit=0
```
`evidence/employment-lane/ledger.tsv` tail (last 3 rows) now reads:
- row 72  00:48  `recruiter question`  **BLOCKED**  Q=How many years of hands-on
  experience do you have in GenAI/LLM?   (the honest run)
- row 73  10-07  `SUPERSEDE: widget logged as recruiter question`  **CORRECTED**
- row 74  10-07  `SUPERSEDE: 'apply flow opened' mislabeled as APPLIED`  **CORRECTED**

Files: `apply-03-after-apply-20261007004828.png` (honest BLOCKED).
The two bad rows (`00:11`, `00:36` widget-as-blocker; `00:42` false **APPLIED**) are
corrected **by append** — the originals remain in-file as history. The ledger no longer
*ends* in an APPLIED row; its last status row is the honest BLOCKED, followed by the two
CORRECTED rows. **No honest APPLIED row exists yet.**

## 2. LANE FILE — VERIFIED ON DISK (not from narration)
`scripts/lane_apply.py`: true line count = **340** (python `splitlines()`). An earlier note
saying "341" was drift; a `Measure-Object -Line` reading of "296" was wrong (PowerShell
undercounts). `python -m py_compile` -> **compile_exit=0**.
Patches confirmed present by line scan:
- `def shot(tag)` with 3× retry — L102
- `A5` poll block (up to ~20 s, not a fixed sleep) — L180–189
- `_q_from_panel(js)` reads `DIV.chatbot_MessageContainer` only — L249
- `FLOW_SIGNALS` (no `"years of experience"` false positive) — L194
- `_find_question` ignores `SPAN.feed-title` / "relevant for you" widget — L270–292

## 3. WHY IT IS STILL BLOCKED (genuine, not a bug)
- `scripts/apply_answers.txt` -> **MISSING** (`scripts/_answers_exists.txt`:
  `APPLY_ANSWERS MISSING`).
- `_answer_from_record()` returns `None` when the file is absent, so the driver reports
  **BLOCKED** on the real gate question rather than inventing a number. Honesty rule held.

## 4. GROUNDED BASIS FOR THE MISSING FIGURE (the only record we have)
No `genai|<n>` figure exists anywhere in the house. The ONLY grounded statement is the
operator's own line, `career/EARNING-MAP.md` L51:
> "Since 2024 I've gone fully agentic: 20+ production-grade systems shipped ..."

2024 -> 2026 implies **~2 years** of hands-on GenAI/LLM work. This is evidence, not a
decision: the figure to sign on a Naukri application must come from the operator
(correctness > convenience). Once he sets it, write one `key|answer` line per question,
e.g. `genai|2`, then re-run `lane_apply.py`; it will log **APPLIED_STEP** (never a
force-submit past a gate).

## 5. HONEST SCOREBOARD
- Card -> select -> `Apply 1 Job` -> apply click -> recruiter panel: **PROVEN** (run 5).
- Reaching the gate is **NOT** an application. **Collected today: Rs 0.**