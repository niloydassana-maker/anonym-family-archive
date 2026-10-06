# EMPLOYMENT LANE - FULL END-TO-END AUTOMATION
### The mission run-book. This is what the agent executes.

**Baba's order that produced this file:** *"do the actual full end-to-end automation of
the employment lane, whatever you have watched in the video, including commenting in the
feeds, everything."*

---

## 0. WHAT THIS LANE ACTUALLY IS

Not "we apply for you". This lane runs the whole employment machine end to end:

1. BUILD THE PROFILE - drive it to 100%, with keyskills matched to live demand
2. MATCH THE MARKET - score every posting against the candidate's REAL skills
3. APPLY - across Naukri, Foundit and LinkedIn, without a human keystroke
4. **ANSWER THE RECRUITER'S QUESTIONS** - during the application, not afterwards
5. ENGAGE - comment on feeds where a candidate is a real participant, never spam
6. RECEIPT EVERYTHING - a screenshot or a line did not happen

**Step 4 is the whole product.** Naukri's own agent scans ~12,849 jobs a day and
applies, and still cannot answer the recruiter who opens with *"How many years do you
have in Fintech/payment-processing?"* That question is where applications die. An agent
that answers it is worth paying for. An agent that only clicks Apply is free.

---

## 1. THE FOUR PORTALS

| Portal | Surface | How to drive it |
|---|---|---|
| **Naukri** | `/mnjuser/recommendedjobs`, `/myapply/historypage`, `/mnjuser/profile`, `/job-apply-agent` | logged session, real DOM |
| **Foundit** | `foundit.in` job pages, Apply Now | logged session, real DOM |
| **LinkedIn** | `/jobs`, messaging, feed comments | Profile 17 session |
| **Indeed** | `in.indeed.com` | logged session, real DOM |

**Hands:** Agent 360 MCP ONLY — tools, path and the complete list of already-paid-for walls
are in **`AGENTS-EMPLOYMENT.md` §0 and §3**. Read that file before your first browser action.
Do not rediscover a wall the house has already documented; it costs a run every time.

### Naukri specifics worth knowing before you start
- **Neo, the native job agent, is already active on the operator's account.** It scans roughly
  12,000 jobs a day and applies. Read its page: *"Matching with your profile preferences past
  applies."* **That is why the profile work comes first** — Neo can only send what the profile
  tells it to look for. A vague profile produces 1,000+ appearances and no interviews.
- The recommended-jobs page carries **Job match score · Keysills · Early Applicant** per role.
  Read the score before applying; it is free targeting information.
- A recruiter may post a question in the apply flow (*"How many years of experience do you have
  in X?"*). **Answer it.** That step is what this product is for.
- Employment entries show a date range. **A visible gap is a real finding.** Report it; never
  invent an interim role to hide it.

### Matching gate — score before you send
```
score = count of the operator's REAL skills present in the posting text
gate  = score >= 2, or an explicit fit signal in the posting
```
Below the gate: **do not apply.** Record `NO_MATCH` with the reason. A ledger of honest
rejections is worth more than a pile of applications that burn the daily limit.

---

## 2. THE ORDER OF WORK - profile first, always

**A profile is the only lever that applies to every future application.** Do this before
anything else, because every apply made against a weak profile is wasted.

### 2.1 Drive the profile to 100%
- Read the current score. Naukri shows **Job match score / keyskills / work experience**.
- Fill every section that reads incomplete: headline, about, skills, experience, education.
- Write the headline as **capability keywords recruiters actually search**, not a job title.
  A candidate whose profile says only "Manager" is matched to manager roles forever.
- **Skills are the highest-leverage field.** A generic list — Big Data, Hibernate, Agile — describes
  anyone and matches everyone. Replace it with what the operator actually does. (Observed live:
  twenty-one generic skills were replaced with `AI Agents`, which is what the operator builds.)
- Screenshot the 100% state, and record the exact before/after. That is the receipt.

### 2.2 Set preferences to match, not to the title
- Preferences decide what the matching engine sends. Set them to the skills, the locations that
  can actually be worked, and the notice period that is true.
- A preference set copied from the current title is how people end up applying to 300 wrong roles
  and calling it a volume problem. **It is a targeting problem, not a volume problem.**

### 2.3 Report gaps, never fill them with fiction
Employment date ranges, missing education, absent certifications: **state them.** If the profile
shows a gap, the honest fix is a line on the summary about what is actually being done since.
An invented role is a hard failure (law 2 in `AGENTS-EMPLOYMENT.md`).

---

## 3. MATCH - score before you send

Never apply to a posting because the title looked close. Score it.

```
score = number of the candidate's REAL skills present in the posting text
gate  = score >= 2 OR an explicit "fit" signal in the posting
```

- Below the gate: **do not apply.** Record it as NO_MATCH with the reason. A ledger full
  of honest rejections is worth more than a pile of applications that waste the candidate's
  daily limit.
- Record every decision, matched or not, in the ledger. The ledger is how the next run
  knows what was already tried.

---

## 4. APPLY

For each gated posting:
1. Open it. Confirm the title and company match what was scored. Never apply from a stale
   title - the page can change between scoring and clicking.
2. Click Apply.
3. Fill the form fields **from the operator's pinned resume and profile** — never from any
   other document in the workspace. The pinned file is `kilo_apply_resume.pdf`
   (SHA256 `DE81F585…FC339F`, Author *Kunal Das*). A different person's resume also exists in
   this tree; using it is a hard failure, not a typo. Never invent an answer.
4. Screenshot each completed step.
5. Submit.
6. Verify the submission landed: the portal must show the application in history, an
   application-count increment, or a confirmation state. **A click is not a receipt.**
7. Write the ledger row: portal, query, role, company, score, status, receipt path.

**Never let the daily application limit be exceeded.** One exhausted account is a dead
account. Pace below the portal limit, always.

---

## 5. ANSWER THE RECRUITER'S QUESTIONS - the part that matters

When a portal presents an in-flow question, **answer it in the flow.** This is the step
that gets a fresher past a recruiter.

Observed in the field, Naukri, in-application:
> "Hi KUNAL DAS, thank you for showing interest. Kindly answer all the recruiter's
> questions to successfully apply for the job. **How many years of experience do you have
> in Fintech/payment-processing?**"

Rules:
- **Answer from the candidate's own record.** If the posting asks for experience in a
  domain the candidate does not have, answer truthfully and connect what they do have.
  Never invent years, never claim a domain the CV does not support.
- **Keep it short and specific.** One or two sentences. A wall of text gets skimmed.
- **A question that blocks submission is a hard stop.** Report it as BLOCKED with the
  exact question. Do not guess an answer to get past it, and do not abandon the flow.
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