# EMPLOYMENT LANE - FULL END-TO-END AUTOMATION
### The mission run-book. This is what the agent executes.

This run-book defines the requested employment workflow and the evidence required to report
each stage accurately.

---

## 0. WHAT THIS LANE ACTUALLY IS

Not "we apply for you". This lane runs the whole employment machine end to end:

1. AUDIT AND IMPROVE THE PROFILE - update only supported fields from verified facts
2. MATCH THE MARKET - score actual postings on current result pages against verified skills
3. APPLY - across Naukri, Foundit, Indeed and LinkedIn Easy Apply when available
4. **ANSWER THE RECRUITER'S QUESTIONS** - during the application, not afterwards
5. ENGAGE - comment on feeds where a candidate is a real participant, never spam
6. RECEIPT EVERYTHING - a screenshot or a line did not happen

Recruiter questions are a required application step. A workflow that only clicks Apply is
incomplete; answer only from the configured candidate record and report unknown questions.

---

## 1. THE FOUR PORTALS

| Portal | Surface | How to drive it |
|---|---|---|
| **Naukri** | `/mnjuser/recommendedjobs`, `/myapply/historypage`, `/mnjuser/profile`, `/job-apply-agent` | logged session, real DOM |
| **Foundit** | `foundit.in` job pages, Apply Now | logged session, real DOM |
| **LinkedIn** | `/jobs`, feed comments | Existing authenticated session |
| **Indeed** | `in.indeed.com` | logged session, real DOM |

**Hands:** Agent360 MCP only. Read **`AGENTS-EMPLOYMENT.md`** before the first browser
action for the exact tool list and known browser limitations.

**Execution mode:** follow `MISSION-RUN.txt` as the tool-directive prompt. Use the available
Agent360 browser tools to carry out profile edits, applications and feed engagement through
the actual visible UI. These are workflows, not special-purpose MCP tools. Do not write a
new portal driver when the task is to operate the existing authenticated browser. If the UI
does not expose a reliable action or confirmation, mark it BLOCKED with the exact state and
receipt. The coverage matrix in `FEATURE-COVERAGE.md` remains the source of truth for what
has implementation and live proof; a mission directive is not itself feature completion.

### Naukri specifics worth knowing before you start
- A portal may have its own recommendation or application agent. Inspect the current account
  state and application history; do not assume that a native agent is active or has submitted.
- The recommended-jobs page carries **Job match score · Keysills · Early Applicant** per role.
  Read the score before applying; it is free targeting information.
- A recruiter may post a question in the apply flow (*"How many years of experience do you have
  in X?"*). **Answer it.** That step is what this product is for.
- Employment entries show a date range. **A visible gap is a real finding.** Report it; never
  invent an interim role to hide it.

### Matching gate — score before you send
```
score = count of the configured candidate's verified skills present in the posting text
gate  = score >= 2, or an explicit fit signal in the posting
```
Below the gate: **do not apply.** Record `NO_MATCH` with the reason. A ledger of honest
rejections is worth more than a pile of applications that burn the daily limit.

---

## 2. THE ORDER OF WORK - profile first, always

Audit the profile before applying. Improve only fields supported by the verified candidate
record; profile completeness is not a reason to invent or infer facts.

### 2.1 Audit and improve supported fields
- Read the current completion score and fields the portal exposes; verify the displayed score
  in the screenshot rather than inferring it from a text token.
- Fill every section that reads incomplete: headline, about, skills, experience, education.
- Write the headline as **capability keywords recruiters actually search**, not a job title.
  Use only wording supported by the candidate's verified work history and target preferences.
- Skills should reflect the configured candidate record and current target roles. Do not replace
  existing skills unless the candidate record supports the change.
- Screenshot the resulting profile state and record before/after. Do not promise 100% completion
  when the portal or candidate record leaves fields unavailable or unverified.

### 2.2 Set preferences only from verified candidate choices
- Preferences affect job matching. Change location, notice period, compensation, or role choices
  only when the configured candidate record or current operator instruction supplies the value.

### 2.3 Report gaps, never fill them with fiction
Employment date ranges, missing education, absent certifications: **state them.** If the profile
shows a gap, the honest fix is a line on the summary about what is actually being done since.
An invented role is a hard failure (law 2 in `AGENTS-EMPLOYMENT.md`).

---

## 3. MATCH - score before you send

Never apply to a posting because the title looked close. Score the actual posting.

```
score = number of the configured candidate's verified skills present in the posting text
gate  = score >= 2 OR an explicit "fit" signal in the posting
```

- Below the gate: **do not apply.** Record it as NO_MATCH with the reason. A ledger full
  of honest rejections is worth more than a pile of applications that waste the candidate's
  daily limit.
- Record every decision, matched or not, in the ledger. The ledger is how the next run
  knows what was already tried.
- Resolve prior attempts by chronological history per exact portal and role. A later
  screenshot-backed `APPLIED` status closes an earlier `BLOCKED` attempt; do not restart
  from the first old non-OK row or submit again.

**Validate extracted cards before scoring.** Search pages contain non-job fragments
(dates, location labels, employer names, filters and Save controls); do not record these as
roles. Confirm a visible job title and employer from the card or open detail page. If the
available browser tools cannot distinguish a real posting, record the extraction defect
as BLOCKED and update the tool directive before continuing.

---

## 4. APPLY

For each gated posting:
1. Open it. Confirm the title and company match what was scored. Never apply from a stale
   title - the page can change between scoring and clicking.
2. Click Apply.
3. Fill form fields only from the resume and facts configured for this candidate. Verify the
   configured resume hash first. Never use unrelated documents from the workspace or invent
   an answer.
4. Screenshot each completed step.
5. Submit.
6. Verify the submission landed: the portal must show the application in history, an
   application-count increment, or a confirmation state. **A click is not a receipt.**
7. Write the ledger row: portal, query, role, company, score, status, receipt path.

If the apply panel closes after Save/Continue without a success banner, navigate to the
portal's application history with Agent360 and inspect the exact role, employer, and status.
Capture a screenshot. Log APPLIED only when the exact history entry shows it was sent/applied.
Do not classify unrelated title text as a duplicate, and never retry an application that the
history already confirms.

**Never exceed a portal's application limit.** Check visible portal limits and applications
already sent today. If the limit is not exposed, keep to one application per portal per run
and report that the limit could not be independently verified.

---

## 5. ANSWER THE RECRUITER'S QUESTIONS - the part that matters

When a portal presents an in-flow question, answer it from the configured candidate record.

Example: a recruiter asks how many years of experience the candidate has in a particular
domain. Use only an exact verified answer from the candidate record; otherwise stop with the
question recorded as BLOCKED.

Rules:
- **Answer from the candidate's own record.** If the posting asks for experience in a
  domain the candidate does not have, answer truthfully and connect what they do have.
  Never invent years, never claim a domain the CV does not support.
- **Keep it short and specific.** One or two sentences. A wall of text gets skimmed.
- **A question that blocks submission is a hard stop.** Report it as BLOCKED with the
  exact question. Do not guess an answer to get past it; leave the portal in a safe state.
- Screenshot the answered question and the resulting state.

---

## 6. ENGAGE - comment on feeds, and only where it is true

LinkedIn commenting is a real channel and it is also the fastest way to get a profile
suppressed. Rules that are not optional:

- Comment **only on posts the candidate can genuinely speak to.** A hiring manager asking
  how they run an AI hiring pipeline is a real conversation. A motivational meme is not.
- **Never drop a link** in a public comment. No catalogue link, no demo link, no pricing.
  Links in public comments are how a profile gets flagged as spam.
- **Add value in the comment itself.** If the comment would be worthless without the link,
  it is a link in disguise and it is banned.
- Never comment twice on the same post. Never comment on a competitor's post to argue.
- Record every comment with the post URL and a screenshot.
- Do not publish a comment without explicit SEND-APPROVED authorization for the exact text;
  otherwise leave a draft and record it as pending approval.

---

## 7. THE LAWS THAT BIND EVERY ACTION

1. **THE SCREENSHOT IS THE RECEIPT.** A tool call that returned `200` is not a delivery.
   If it is not visible in a screenshot, it did not happen. This is the single law that
   makes the rest of this document trustworthy.
2. **NEVER INVENT A FACT.** No experience, no company, no date, no qualification. If the
   candidate's record does not contain it, it is not in the application.
3. **ONE PORTAL AT A TIME.** Never hold two drives on the same Chrome. Finish, release, move on.
4. **NEVER TOUCH THE CANDIDATE'S LOGIN.** The session is already logged in. If it expires,
   report it. Never ask for a password, never take an OTP, never type credentials.
5. **RATE LIMITS ARE LAW.** Below every portal limit, with gaps between actions.
6. **STOP BEFORE A SPAM WALL.** If the portal starts throttling, stop and report. A banned
   account ends the lane permanently.
7. **ASCII ONLY** in anything that gets submitted on a portal.
8. **REPORT HONESTLY.** A failed step is reported with its exact error and attempt count.
   A half-finished apply is `BLOCKED`, never `DONE`.

---

## 8. THE LEDGER

One row per action, always written, never assumed:

```
ts | portal | query_or_source | role | company | match_score | step | status | receipt | note
```

`status` is one of: `MATCHED` `APPLIED` `BLOCKED` `NO_MATCH` `RATE_LIMITED` `FAILED`.

At the end of a run, state plainly: what was applied, what was blocked, what was skipped
and why. If a portal shows an application in history, it happened. If it does not, it
did not happen, no matter what the click returned.
