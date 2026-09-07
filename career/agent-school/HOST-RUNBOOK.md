# HOST-RUNBOOK.md — AGENT SCHOOL, COHORT 1

**Deck:** `AGENT-SCHOOL-SLIDES.pptx` (72 slides — 18 per session)
**Workbook:** `STUDENT-WORKBOOK.pdf` (12 pages — print one per student)
**Format:** 4 Sundays × 90 minutes. Demo at ~25 min mark every session.
**Golden rule:** demo before theory gets long. If you're behind schedule, CUT THEORY, never the demo.

---

## TECH CHECKLIST — do this the night before AND 30 min before

### Zoom / Google Meet
- [ ] Meeting link created + sent; passcode works from an incognito window
- [ ] Host + co-host set; waiting room ON
- [ ] Screen-share permissions: "All participants" (students may show homework)
- [ ] Recording ON from minute 0 (local + cloud if available)
- [ ] Breakout rooms pre-created if cohort > 15

### Demo machine (the laptop that runs the agent)
- [ ] WhatsApp Web logged in and STAYS logged in (no re-linking on stage)
- [ ] Agent bridge + agent console open, font size bumped to 16pt+
- [ ] Second phone charged, on mobile data (NOT the same Wi-Fi), test number ready
- [ ] Notification sounds OFF on the demo laptop (avoid surprise pop-ups)
- [ ] All other apps closed; Do Not Disturb ON

### Backup kit (print this page)
- [ ] Slides exported to PDF on a pen drive
- [ ] Screen-captured video of a successful demo (3–5 min, from a previous run)
- [ ] Phone hotspot ready as backup internet
- [ ] One printed copy of the deck (hard fallback if projector dies)

---

## DEMO FALLBACK LADDER (in order — never go below two rungs at once)

1. **Plan A — Live, screen-shared.** Real message from second phone → agent replies.
2. **Plan B — Live, but host types.** If video lags, share only the agent console (not video feed).
3. **Plan C — Recorded demo.** Play the backup video; pause at each loop step and narrate. Still powerful if you narrate live over it.
4. **Plan D — Host replays the log.** Walk through a saved transcript of a real run on the slides.
5. **Plan E — Whiteboard the loop.** GOAL → THINK → ACT → OBSERVE → REPEAT on a whiteboard, students act as "tools". Never happens, but it's there.

> Rule: announce the switch calmly. "The internet gods want us to read the log today" is a lesson, not a failure.

---

# SESSION 1 — What an Agent Really Is (slides 1–18, green)

| Minute | What happens | Slides |
|---|---|---|
| 0–5 | Welcome, names in chat, "write your city in chat" icebreaker | 1–2 |
| 5–12 | The promise: working agent by Day 30. Set homework culture NOW | 3–5 |
| 12–22 | AI vs Agent; brain, tools, loop — one slide each, ask questions | 6–10 |
| 22–25 | **DEMO SETUP** — switch to WhatsApp Web + console (do this SILENTLY fast) | — |
| 25–35 | **LIVE DEMO** — student suggests the message; agent replies live. Break one thing on purpose | 11 (demo) |
| 35–42 | Debrief the demo — map what they just saw onto brain/tools/loop | 12–13 |
| 42–55 | Examples + what agents are NOT (honest talk) | 9–10 |
| 55–65 | Recap anatomy — call on 3 students to "say it back" | 14 |
| 65–75 | **Homework: 3 wish-tasks.** Open workbook page "Session 1", start writing NOW | 15 |
| 75–85 | Q&A pause #1 (questions in chat, host reads aloud) | |
| 85–90 | Close: recap slide + next week teaser. Reminder: bring workbook | 16–18 |

**S1 pitfalls:** don't over-explain "the model" — say *the brain* all session. If demo fails: fallback ladder, step 3, keep timeline.

---

# SESSION 2 — Build Your First Agent (slides 19–36, orange)

| Minute | What happens | Slides |
|---|---|---|
| 0–5 | Recap in 60 seconds — ask: "who wrote their wish-tasks?" | 19–20 |
| 5–20 | The loop, one slide per step. Ask a student to give the GOAL test each time | 21–26 |
| 20–28 | Tools are functions; tool-design checklist | 27–28 |
| 28–33 | **DEMO SETUP** — code slides ready, font bumped | — |
| 33–50 | **LIVE BUILD** — type the pseudocode WITH them, one slide per chunk (skeleton → loop → prompt). Students copy into workbook page 5 | 29–32 |
| 50–58 | Prompt = instructions; write-like-a-boss rules | 33 |
| 58–66 | Guardrails — the NEVERs, step caps, human gates | 34 |
| 66–75 | Homework: design wish-task #1 (workbook page "Session 2") | 35 |
| 75–85 | Q&A pause #2 — 2–3 students read their goal aloud, class critiques kindly | |
| 85–90 | Close + teaser: "next week your agent goes on WhatsApp" | 36 |

**S2 pitfalls:** typing too fast. Pause after every 3rd code line. If a student's goal is vague, fix ONE live as a class example.

---

# SESSION 3 — Agents on WhatsApp (slides 37–54, green)

| Minute | What happens | Slides |
|---|---|---|
| 0–5 | Recap; show of hands: "who finished the S2 design?" | 37–38 |
| 5–15 | Why WhatsApp = where India lives; why not an app | 39–41 |
| 15–22 | Zero-cost stack + architecture (the round trip) — draw it on the whiteboard as you talk | 42–46 |
| 22–25 | **DEMO SETUP** — bridge on, agent loaded, test phone ready | 47 |
| 25–40 | **LIVE DEMO end-to-end** — customer writes → agent thinks (console visible) → reply lands → logs written. Then flip on `ask_human` and escalate a discount request. Then break the bridge, show the failure, fix it | 48 (demo) |
| 40–47 | Demo debrief — students sketch the round trip in workbook page "Session 3" | 49 |
| 47–62 | Safety: identity, pacing, human approval — one wall per slide, real stories | 50–52 |
| 62–70 | Failure modes table — "it WILL break, here's how you'll fix it" | 53 |
| 70–78 | Homework: map your task onto the architecture | 54 |
| 78–85 | Q&A pause #3 | |
| 85–90 | Close + teaser: "next week: ship it and earn" | 54 |

**S3 pitfalls:** WhatsApp Web session expiring mid-demo → re-login BEFORE class, keep phone linked. Never demo with a student's personal number without asking.

---

# SESSION 4 — Ship It & Earn (slides 55–72, orange)

| Minute | What happens | Slides |
|---|---|---|
| 0–5 | Journey recap — "4 weeks ago you couldn't define 'agent'" | 55–56 |
| 5–15 | Deployment stages + shipped checklist | 57–58 |
| 15–27 | Cost truth: zero-cost vs API; when to pay | 59–61 |
| 27–42 | The three earn paths + pricing + first three clients. Students fill workbook page "Session 4" client table LIVE | 62–67 |
| 42–52 | **Demo slot kept free** — best student volunteer shows THEIR agent (ask for the volunteer 1 week ahead). Host demo as fallback | — |
| 52–62 | Certificates: submission = goal + tools + prompt + 1 screenshot | 68 |
| 62–70 | 30-day map review; next cohort + alumni/referral offer | 69–71 |
| 70–80 | Closing: stay hungry, stay foolish. Ask 3 students: "what will your agent do by Day 30?" (record clips for next cohort) | 71–72 |
| 80–90 | Final Q&A + group photo screenshot + WhatsApp group: post submission instructions | |

**S4 pitfalls:** don't let cost-talk turn into fear — the rule is *pay only when a client pays you*.

---

## UNIVERSAL HOST RULES

1. **Timer on your phone, visible.** If a section runs 5 min over, cut the NEXT theory slide — never the demo, never homework time.
2. **Chat is your co-host.** Co-host drops timestamps and workbook page numbers in chat.
3. **Every session ends with:** homework shown ON SCREEN + where it goes in the workbook + exact due time.
4. **Names, not "you".** Call on 3–5 students by name per session. Cohort 1 is small — use that.
5. **Record everything.** Recordings are next cohort's asset and this cohort's revision.
