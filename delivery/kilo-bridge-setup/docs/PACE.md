# PACE — HOW TO RUN FAST WITHOUT LYING
### Added 2026-10-06, after the first run proved slow. Born from its own ledger, not a guess.

The first run took **17 min 40 s** and delivered ~9 ledger rows. That quality was correct and
the pace was not. This file is the fix, and every rule traces to something that actually cost
time in that run.

---

## 1. THE MOUSE PATH IS DEAD. NEVER CALL IT.

`Input.dispatchMouseEvent` **times out at 1500 ms per attempt** on this machine. The tab is
active and the window is foreground — it still times out. Every attempt is pure waste.

- **Use JavaScript `.click()` and keyboard only.** Both were verified working in the first run.
- If a click must be real, press the key instead. Never retry the mouse hoping for a different
  result. Two attempts, then take a different path.
- **Do not remove a chip by hunting for it with the mouse.** If it needs a real pointer and the
  pointer is dead, record `BLOCKED` and move on. The cap is a portal rule, not a puzzle.

## 2. SCREENSHOT AT MILESTONES, NOT AT EVERY KEYSTROKE

Thirteen screenshots in eighteen minutes is a third of the run. That is over-verification.

- **One screenshot per FIELD edited, not per action.** Add five skills, take one shot at the end
  of the fifth — not one each.
- **Batch a section.** Headline + about + skills = one verification pass.
- **One screenshot per portal at close**, always, so the run has a final receipt.
- The law is unchanged: **what you claim must be visible in some screenshot.** Batching does not
  weaken that. It just stops photographing every breath.

## 3. READ STATE ONCE, TRUST IT UNTIL IT CHANGES

The first run re-read page state repeatedly around a single edit.

- Read state once at open. Read it again **only after an action that changes the page** —
  a save, a navigation, a modal open or close.
- **Never re-read to feel safer.** A second identical read is a guess wearing a receipt's clothes.
- Prefer one `document.body.innerText` grab over several narrower queries.

## 4. ACCEPT REJECTION IN ONE ATTEMPT, THEN MOVE ON

Recorded in run one, and it cost real time:

```
add Agentic AI   -> FAILED, absent from Naukri's skill dictionary, silently dropped
add LangChain    -> FAILED, absent from Naukri's skill dictionary, silently dropped
```

**Naukri only accepts skills from its own dictionary.** A skill not in the dictionary is dropped
with no error.

- **Try a term once. If it does not appear in the typeahead, it does not exist there — write it
  to the ledger and move on.**
- Do not retry, do not try a synonym to force it, do not try to bypass the dropdown.
- **The same rule applies to every portal:** one rejection is a fact, not a puzzle.

## 5. WHEN A PORTAL CAPS YOU, NOTE IT AND LEAVE

The key-skills chip count capped at **22**. That is a portal rule.

- Record `BLOCKED` with the cap in the note. **Do not attempt removal to make room.**
- Move to the next field, then the next portal. A cap is not a failure; losing twenty minutes
  fighting it is the failure.

## 6. SPEND THE SAVED TIME ON THE PART THAT EARNS

The saved seconds go to the two things that matter, not to more profile fiddling:

- **Matching fit roles** against real skills, and
- **The apply flow, including answering the recruiter's question.**

Ten minutes on a profile is already generous. The profile is a multiplier on every application
that follows. The applications are the money.

---

## 7. THE UNCHANGED LAWS

Pace never relaxes these. Under speed:

- **A screenshot is still the receipt.** Batched, not skipped.
- **Never invent a fact.** Faster is not looser.
- **Never spend money.** Dismiss upsells and continue.
- **Never touch a login, password or OTP.**
- **`BLOCKED` is a legitimate result.** Reporting a wall in one line is faster and more honest
  than working around it for ten minutes.

**The measure of this lane is not how many things it touched. It is how many applications it
landed, each one verified, and how honestly it reported the ones it did not.**