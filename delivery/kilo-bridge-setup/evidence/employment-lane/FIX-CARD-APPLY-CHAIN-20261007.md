# FIX: THE NAUKRI CARD->APPLY CHAIN (2026-10-07)

Baba's task: make `lane_apply.py` reach the apply flow — replacing the dead
card-click with the on-screen-proven **select-then-apply** sequence.

## WHAT WAS BROKEN (measured, not guessed)

1. **Dead card click.** A recommended-jobs card has **no `<a>`, no onclick, no React
   nav** — `element.click()` and event-dispatch both did nothing (`clicked-article`,
   page never changed). The page is **select-then-apply**:
   click `.tuple-check-box` in the card → the header `.multi-apply-button` enables
   (`Apply 1 Job`) → click it → the recruiter panel opens.

2. **False `moved` (the fake DONE).** The old verifier treated the token
   `"years of experience"` as a flow signal. That phrase appears in **job
   descriptions on the list page**, so `moved` was true without any flow. The old
   run then grabbed the list widget *"Are these jobs relevant for you?"* as the
   recruiter question and wrote a BLOCKED row over the **wrong** question.

3. **Async panel read race.** The recruiter chatbot panel opens **asynchronously**.
   A fixed 7 s read at 30,471 chars **missed** the question; 8 s showed it at 32,013.

4. **Unreliable screenshot.** A transient image-read failure (`shot -> FAILED`)
   silently lost a needed receipt.

## WHAT WAS CHANGED IN `scripts/lane_apply.py`

- Removed the dead `CLICK_JS` path; added **`CHECK_JS`** (tick `.tuple-check-box`
  in the card), **`APPLY_STATE_JS`** (read the `.multi-apply-button` state) and
  **`APPLY_JS`** (click it; label-matched by `/^apply/i`, since it reads `Apply 1 Job`).
- Replaced the `APPLY_MARKERS` / `"years of experience"` false positive with
  **`FLOW_SIGNALS`** = recruiter-panel text only (`answer all the recruiter`,
  `recruiter's question`, `apply for this job`, ...). `moved = left_list or in_flow`.
- Replaced the fixed `time.sleep(7)` with a **poll** (up to ~20 s) that waits for the
  recruiter panel or the flow signal.
- Added **`_q_from_panel(js)`** which reads the recruiter question from
  `DIV.chatbot_MessageContainer` **only**; `q = panel_q or _find_question(...)`, and
  `_find_question` now **ignores** the `SPAN.feed-title` widget
  (`relevant for you`). The widget is *not* a blocker.
- Screenshot helper now **retries up to 3×** so a transient read never loses a receipt.

## PROOF (the pixels are the receipt)

Run 5 (2026-10-07 00:48 IST), one session, proven mechanism:
```
A3 select card checkbox
   select -> checked
   apply-button state = {"found":true,"disabled":false,"label":"Apply 1 Job"}
A4 click Apply
   apply -> clicked-apply
A5 wait for apply flow / recruiter panel
   left_list=False in_flow=True body_chars=30474
   RECRUITER QUESTION FOUND: How many years of hands-on experience do you have in GenAI/LLM?
   !! not answerable from record -> BLOCKED (never invent)
```

| step | receipt |
|---|---|
| card ticked + `Apply 1 Job` enabled | `apply-02-selected-20261007004825.png` |
| recruiter panel open, real question | `apply-03-after-apply-20261007004828.png` |

Both screenshots were read and match the log exactly.

## HONEST STATE

- The card→apply **chain works**: card selects, button enables, apply click opens the
  recruiter panel, and the driver reports the real gating question.
- The run is **BLOCKED**, not APPLIED: `scripts/apply_answers.txt` does not exist, so
  the lane cannot honestly answer *"How many years of hands-on experience do you have
  in GenAI/LLM?"* without inventing a fact. It refuses and says so.
- Ledger corrected (append-only) per the MISLABEL CLAUSE: the two rows that logged the
  list widget as the blocker are SUPERSEDED, and the `00:42` row that stamped
  **APPLIED** without an answered gate is SUPERSEDED to BLOCKED. **No honest APPLIED
  row exists yet.**
- **Collected today: Rs 0.** A driver that reaches the gate is not an application.

## TO MAKE IT APPLY

Create `scripts/apply_answers.txt` (one `key|answer` per line, lowercase key matched
against the question) with the operator's REAL figure for GenAI/LLM hands-on
experience, e.g. `genai|11`. Then re-run; the driver fills the answer from record and
logs `APPLIED_STEP` (never a force-submit past a gate).