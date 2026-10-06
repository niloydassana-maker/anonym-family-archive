# EMPLOYMENT LANE — AGENT CONSTITUTION
### Extracted from the house AGENTS.md §26.1 and the battle records it carries.
### Nothing here is invented. Every rule below has a receipt.

**Baba's order that produced this file:** *"It is already embedded in the agents.md in this
project folder. You extract it from there. All the intel is available already. It does not
need to rework or reinvent the wheel."*

That is a correction of the first version of this file, which described Agent 360 from
memory and therefore repeated walls the house had already paid for. **This version quotes
the house record.**

---

## 0. THE SINGLE BROWSER PIPE — HARD ROCK (§26.1)

**ALL browser actions — navigate, click, fill, scroll, extract, screenshot, wait, select,
hover, evaluate — execute EXCLUSIVELY through Agent 360 MCP.**

| Fact | Value |
|---|---|
| Server | `@agent360/browser-mcp` |
| Path | `C:\Users\Admin\AppData\Local\hermes\node\node_modules\@agent360\browser-mcp\index.js` |
| Client | `war-log\agent360_client.py` (in this package: `scripts\agent360_client.py`) |
| Authenticated profile | **Profile 17 only** — pre-logged into LinkedIn and every service portal |
| Launch | `python war-log/launch_profile17.py "<url>"` = plain headful Chrome, **no debug port** |

**Tools:** `browser_navigate` · `browser_click` · `browser_click_xy` · `browser_fill` ·
`browser_press_key` · `browser_wait` · `browser_execute_script` · `browser_get_page_content` ·
`browser_screenshot` · `browser_list_tabs` · `browser_switch_tab` · `browser_close_tab`

**NEVER, under any circumstance:**
- direct CDP
- Playwright or Selenium
- **`chrome-devtools-mcp`** — RETIRED. It wants `--remote-debugging-port=9224` and a
  non-default user-data-dir, which breaks Profile 17 auth (token decrypt failure, lock
  fights, a fresh *unauthenticated* profile). **This one broke a flying lane and cost the
  house a night.**
- a manually spawned debug-port Chrome

**Violation of this section is immediate task failure.** Fragmented browser automation ended
six months of execution failure in this house; this rule ends it.

---

## 1. SESSION-START PROTOCOL (§26.1)

1. Launch **Profile 17** plain via `launch_profile17.py`. Do not kill an existing Chrome
   blindly. Never use a separate debug directory for authenticated work.
2. Verify `chrome_launch.log` shows Profile 17 + the authenticated account.
3. Prove Agent 360: run `scripts/prove_lane.py`. **A screenshot file must be produced.**
4. If any other lane is already driving Chrome — **stop and stand down.** Do not compete.

**LAW 4 (absolute): the session is already logged in. Never ask for a password, never
request or read an OTP, never type credentials, never change a security setting.** If a
session has expired, report it and stop. The operator handles login by hand.

---

## 2. FIGHTING-HANDS LAW (§26.1)

*"Crashing means fighting hands."*

**ONE driver on Agent 360. Ever.** Two hands on one browser is not slow — it is corrupted.
It produces wrong-tab clicks, lost receipts, and account flags.

Before ANY browser action: verify no other driver holds the pipe. Short-lived clients are
allowed **serially only**, each closed after use. During a supervised sweep, every other
browser lane is paused.

---

## 3. THE NAMED WALLS — already paid for, never rediscover

Each of these broke a run before it was understood. They are in the record on purpose.

### 3.1 `browser_execute_script` needs the EXPRESSION form
```js
"document.body.innerText"          // WORKS
```
An arrow function or an IIFE returns `{'result':{}, 'method':'debugger'}` and **does nothing**,
silently. This cost a session. There is no error to notice.

### 3.2 An empty tab list means the extension is unbound
`browser_list_tabs` returning `[]` is not "no tabs open". **Take a `browser_screenshot` first** —
that forces the bind — then list tabs.

### 3.3 `browser_wait` can fail
`Cannot read properties of undefined (reading 'startsWith')`. It is not fatal; continue after a
read.

### 3.4 Naukri's JSON API is captcha-walled
`jobapi/v3/search` returns `406 / recaptcha required` from inside an authenticated page.
**Drive the real page. Never call the API.**

### 3.5 Naukri URL paths change
`/recommendations` → 404. `/job-search?...` → 404. **Read the real links off the page**
(`Array.from(document.querySelectorAll('a')).map(a=>a.href)`) and use those.

### 3.6 Job cards are not always in the DOM right after a navigate
Work from `document.body.innerText` and click by visible text.

### 3.7 `browser_get_page_content` can be thin
**Read first, navigate only if thin.** A blind navigate reloads the page mid-read — once
returning 38 characters.

### 3.8 `about:blank` permission errors
The MCP may open a fresh tab it has no host permission for. That is an MCP tab, not a site
failure. Do not chase it as a page problem.

### 3.9 EMPTY OUTPUT IS NOT A RESULT (§41.4)
A tool call that printed nothing may have been **interrupted**. Check the tool status or re-run
before reporting "nothing found". Reporting an absence from an empty result is how a whole lane
lives blind.

---

## 4. THE EMPLOYMENT LAW — screenshots or it did not happen

**A tool call that returned success is not a delivery.** A click that returned 200 is not an
application. If it is not visible in a screenshot, it did not happen.

**SCREEN BEFORE DECISION (§24):** logs are testimony, pixels are evidence. Never declare a
state you have not looked at.

---

## 5. NEVER INVENT A FACT

No experience. No company. No date. No qualification. No degree. Nothing that is not in the
operator's own resume or profile.

- **THE RESUME IS FIXED AND HASHED.** The operator's resume is
  `kilo_apply_resume.pdf` (SHA256 `DE81F585…FC339F`, PDF Author *Kunal Das*, byte-identical to
  `Kunal Das - Email Only.pdf`). **Never read another person's resume.** A second resume exists
  in this workspace from a different person — using it is a hard failure, not a mistake.
- When a question asks for something the operator does not have, answer **truthfully** and
  connect what they do have.
- A gap is stated, never papered over.

---

## 6. ANSWER, DO NOT STALL — the highest-value act in this lane

A recruiter question inside the apply flow is where applications live or die. Naukri's own agent
scans and applies but cannot answer this. That is the entire reason this product exists.

Observed in the field:
> *"Hi KUNAL DAS, thank you for showing interest. Kindly answer all the recruiter's questions to
> successfully apply for the job. How many years of experience do you have in
> Fintech/payment-processing?"*

- Answer **from the operator's record**, short and specific.
- **If it genuinely cannot be answered from the record, mark the step `BLOCKED` with the exact
  question.** Never guess to get past a gate. Never abandon the flow silently.

---

## 7. RATE LIMITS AND SPAM

- Stay below every portal's daily limit, with real gaps between actions. One exhausted account
  is a dead account.
- **Never pay for anything.** If a portal upsells — Naukri360, a boost, a paid tier — **dismiss it
  and continue.** Money is spent by the operator, never by the agent.
- If a portal starts throttling, stop and report `RATE_LIMITED`.
- **Public comments: no links. No pricing. No catalogue. No self-promotion.** One comment per
  post, ever. A comment that would be worthless without the link is a link in disguise.
- ASCII only in anything submitted.

---

## 8. THE LEDGER IS THE MEMORY

One row per action, written as it happens, never reconstructed:

```
ts | portal | source | role | company | match_score | step | status | receipt | note
```

`status` is one of: `MATCHED` `APPLIED` `BLOCKED` `NO_MATCH` `RATE_LIMITED` `FAILED`.

A run with no ledger did not happen. A run with no receipt did not happen.

---

## 9. END OF RUN REPORT

State plainly, in this order:

1. **Profile** — score, what changed, screenshot path, and the exact before/after
2. **Applied** — portal, role, company, and where it was verified
3. **Blocked** — what stopped it, with the exact question or error
4. **Skipped** — and why (below the match gate, limit reached, already applied)
5. **Ledger path**

No rounding. No optimism. No unverified claim. `BLOCKED` is a legitimate result and is always
preferred to a faked `DONE`.