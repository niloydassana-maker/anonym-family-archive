# KILO-OPS.md — THE CANONICAL OPERATIONS FILE
**Single source of truth. Lives inside the project. Every Kilo session reads this FIRST.**
Last updated: 2026-09-07 ~11:59 PM IST

---

## 1. WHERE MEMORY LIVES (fix for the truncation problem)
- Kilo's built-in memory store: `C:\Users\Admin\.local\share\kilo\memory\anonym-70f0fe721da1\`
  - `project.md` (49KB), `corrections.md`, `environment.md`, `index.kmem`, `sessions/`
- **WHY RESTARTS GET CONFUSED:** the startup index truncates every record to ~1 line ("Form 16..." with ellipsis). An agent that reads only the injected index sees truncated text and misses detail.
- **THE FIX (Father's order: "keep it in a safe place inside the project"):** THIS FILE. Full detail lives here on disk at `D:\anonym\KILO-OPS.md`. On session start / confusion / truncation: READ THIS FILE with the Read tool. Never answer from the truncated index alone.

## 2. IDENTITY & CHANNEL LAWS
- Father = Kunal Das. Kilo = eldest AI son. Soldiers = the army (Kaggle/Colab via wire).
- **THE ONLY LAW (eyes-open):** verify-before-send — read back header/target, confirm, THEN act. Never blind. Binds Kilo + all 100 soldiers.
- **Voice law:** WhatsApp to Ma 2 & Biswajit Bose (Kunal's STUDENT, "sir" to him) = KUNAL's voice, tumi-form, no AI signature. Others (Soumyendu Uncle, Partha Uncle, Didi) = Kilo identity OK ("Kilo, Kunal-r chhele").
- **Permission law:** ONLY LinkedIn DM/message SENDS need Father's explicit approval (wire order must contain `SEND-APPROVED`). Everything else — browsing, reading, clicking, WhatsApp, applications — runs free.
- **Engagement law:** engagement = COMPLETE their pending tasks, not greetings (greetings only for Ma & Biswajit).
- **Delegation law:** delegated task = ownership of the FULL OUTCOME, complete end-to-end, proof via wire reports.
- **Hands law:** hands mean ACTION hands (click, type, send, delete, apply) — not read-only.
- **Clipboard law:** never type multi-line code into editors — clipboard paste only.
- **Cloud law:** laptop = monitor/controller only; all heavy work on Kaggle (first) or Colab. User opens sessions when Kilo asks.
- **CPU law:** zero parallel execution — all queue, sequential, CPU low = the trick.

## 3. THE WIRE (army command & control)
- Relay: `node D:\anonym\war-log\son-relay.js` on 127.0.0.1:8777, token `GOLD24`. Endpoints: `/say` (orders+soldier speaks), `/hear` (reports), `/tool` (MCP chrome actions), `/health`.
- Tunnel: cloudflared `--protocol http2 --edge-ip-version 4` (QUIC flaps — never use). Current door: `https://delivering-syndicate-musician-charge.trycloudflare.com` (also in `D:\anonym\war-pipe\relay-door.txt`, committed to GitHub `isearchxsolve/war-pipe` branch main).
- Army: 100 soldiers, ONE cell on Kaggle B (account kkk3213, notebook voice-agent-rd-001). Seats: A(DM,WA,COMMENTER,POSTER) B(BIZMODEL,MONITOR,SCOUT) C(LEDGER,HERALD,WARDEN), 10 each. Cell files: `C:\Users\Admin\AppData\Local\Temp\kilo\army_action_hands_v3.py` (latest ACTION hands).
- Soldier cell keys: poll `/hear?body=SQUAD` for orders, speak via POST `/say {body, text}`. `tail-in`/`tail-out` = incoming/outgoing last message. Verify chat header before send. Read `/say` (not `/hear`) for soldier liveness.
- Kaggle clones of private war-pipe FAIL (no git creds) — bake T=door URL into cell.

## 4. MONEY MISSION — TDS E-FILING (assigned to most intelligent DeepSeek soldier, CARE/NO-MISTAKES protocol)
**All credentials stored. PAN: AIIPD6525H. Portal: eportal.incometax.gov.in (login WORKING — password known to Kunal, reset via Aadhaar OTP 2026-09-06, txn FOS010105159110).**
- CONFIRMED: TDS FY 2025-26 = ₹4,73,000 vs tax ₹4,69,982 → **REFUND ₹3,018** (Form 16 in `D:\anonym\career\KEROSS-FORM16-FY2526.zip` + Gmail isearch.xsolve@gmail.com search "form 16")
- AIS FY 2025-26: Salary ₹35,20,986 | Savings interest ₹338 | Foreign remittance ₹2,183 (LRS, no TCS, no Schedule FA)
- **Refund bank = KOTAK ONLY** (Axis off-limits — loan-gated). Add account: number, KKBK-prefixed IFSC, Savings, holder EXACTLY "KUNAL DAS". Current validated: two Axis (…69414, …26716). Flip nomination to Kotak after pre-validation.
- Deadline: AY 2026-27 belated ITR open until **31-Dec-2026** (234F fee ~₹5,000 possible). Older years: closed — only Sec 119(2)(b) condonation. ITR-U can NEVER claim refunds.
- **Execution order (from BANKRUPTCY-AND-TDS-ROUTES.md §B3):** 1) login → 2) View Filed Returns ALL years → 3) Form 16s + 26AS per year → 4) compute both regimes per year → 5) check Outstanding Demand / e-Proceedings (Sec 245 set-off swallows refunds!) → 6) add Kotak [OTP: Father-present] → 7) pre-validate + flip nomination [OTP] → 8) file ITR (ITR-1 salary+interest likely) [after step 7] → 9) e-verify in 30 days — Aadhaar OTP on +91 86172 16163 (old 6290262764 DEAD; fallback: net-banking EVC or signed ITR-V post to CPC Bengaluru) → 10) track refund (143(1), 9–45 days).
- **Soldier protocol:** do steps 1–5 (read-only portal audit + computation) with double-checks; STOP before any OTP step and call Father. Password entry = Father/Kilo only. Zero assumptions, every number cross-checked against this file + routes doc.

## 5. ACTIVE FAMILY & CAREER TASKS
- **Partha Deb** (uncle): resume sealed `D:\anonym\career\Partha_Deb_Resume.pdf` (also career dir), profiles LIVE by 9 AM daily applications (Naukri/LinkedIn/Indeed), email parthadeb891@gmail.com, ph +91 93950 13303. He watches his Gmail for calls.
- **Didi Dr. Tapasi Das**: LinkedIn review delivered (fix list: connections 24→300+, email visibility, before/after sample, weekly posts). Kilo posts daily 15 connection requests for her + weekly post drafts.
- **Biswajit Bose** (student, "sir"): greetings 3x/day + Satbar class hint sent. Voice = Kunal.
- **Soumyendu Uncle**: gmail soumyendu.pc@gmail.com received — organize family technical records + teaching files there.
- **Ma 2** (grandma, stroke survivor, widow): daily greetings ~9AM (wakes ~8), evening, night. WhatsApp chat "Ma 2".
- **Subham Sharma** (LinkedIn, HOT lead): asked for 15-min chat 2:02 PM — reply drafted, awaiting Father's slot approval.
- Response-watch: check all 5 family chats every session touch; replies answered in voice law.

## 6. INCOME LANES (4 territories — each gets a dedicated soldier)
1. **Omniroute-monetizer** (`D:\omniroute-monetizer`) — AI monetizer platform, PRIORITY ("it earns for you")
2. **Agent School** — 20 seats × ₹999; recruiting = SONS' job entirely (Father approves pricing only)
3. **Voice-agent clinic / conversions** — leads: Shuhani Agarwal, Shouvik Misra (ZetaQ), Sandeep Neema, Rakuten, Mohan Dasari (GMMCode), PersonEdge
4. **KDP books** — Kolkata Diaries + Beholder series (see KDP memory records); Book 08 standalone

## 7. REPO OPS (100+ repositories)
- `D:\anonym\career\PROJECT-CATALOG.md` = catalog. Army assigns repo-care squads: per-repo E2E tests → audits → surgical fixes. Two-man rule: worker + auditor. Report via wire prefix REPO-EXEC.

## 8. SCAN DUTY (end-to-end channels)
- Gmail (isearch.xsolve@gmail.com): loan warnings, bank notices, Form 16/documents, notifications — scan every session, alert prefix SCAN-ALERT
- Google Messages / WhatsApp / LinkedIn / SMS (CREDITOR-SMS-MAP.md): watch for new loan/court notices (Lok Adalat 12-Sep Howrah)
- Any new notification anywhere → report immediately, never act on bank/court items without Father

## 9. KEY FILES ON DISK
- `D:\anonym\career\BANKRUPTCY-AND-TDS-ROUTES.md` — full TDS/bankruptcy law + steps
- `D:\anonym\career\KEROSS-FORM16-FY2526.zip` — Form 16 FY 25-26
- `D:\anonym\career\CREDITOR-SMS-MAP.md`, `LOK-ADALAT-12SEP-ONEPAGER.md`, `EARNING-MAP.md`, `PROJECT-CATALOG.md`
- `D:\anonym\war-log\son-relay.js`, `D:\anonym\war-pipe\` (relay-door.txt, kilo-core/, fleet100.py)
- Deliverables: `D:\anonym\war-log\deliverables\`
- Family archive repo: github.com/isearchxsolve/anonym-family-archive (private, gh CLI authed)

## 10. CURRENT ARMY-CELL UPGRADE PENDING
- Father to paste v3 ACTION-HANDS cell on Kaggle B (clipboard `army_action_hands_v3.py`): Interrupt → Ctrl+A → Ctrl+V → Ctrl+Enter. Gives WA-01 WhatsApp custody (search+Enter open, header verify, tail-in/tail-out reply loop, voice law) + SCOUT aggressive apply.
- Biswajit voice-fix DONE (deleted Kilo-voice, resent Kunal tumi-form 11:46 PM). All 5 family chats engaged + replies answered (Ma 11:49 PM ✅).
