# METHOD1 REPORT — LINE-AGENT — 2026-09-13 night (run 18:39Z→19:30Z)

**RUN END STATE (honest):** number NOT issued — trial form is pre-filled and held at the consent line; the signup box "Business name" + verification OTP belong to Baba and the single consolidated checklist went to the KILO wire at 19:12Z (seq 28025). No reply by T+50min → **ZERO guardian windows consumed** (opening the one window with no number to forward to = pure exposure, refused), radio never left POWER_OFF (final `RADIO-REKILL SUCCESS` events at 19:24 were the guardian's own silence-enforcer doing its job against traffic not from this agent — verified `radioOff:true` before and after my run). CFU + softphone ringing test therefore NOT run; no ring claim made.


## VERDICT
**Indian virtual business number ≤₹600/mo for a solo non-GST individual: NO provider passes all filters tonight.** All four researched are business-SaaS: instant trials exist (free, no payment) but every *permanent* plan is either ≥₹5,000/mo or sales-gated with GST/PAN KYC. Method 1 is therefore staged: tonight = FREE TRIAL sandbox (proves the chain end-to-end at ₹0), permanent number = decision for Baba after proof.

## PROVIDER SCAN (evidence in this dir; screenshots + saved HTML/text)
| Provider | Lowest price (verified 13-Sep) | KYC to start | Instant? | Own app / SIP | Verdict |
|---|---|---|---|---|---|
| myoperator.com (.in/pricing = 404; real site is .com) | **₹5,000/mo** Sedan (annual billing, GST extra; "30-day full refund" banner). 1800 toll-free add-on ₹500/mo needs a base plan. | Free-trial signup = full name + business name + email + WhatsApp mobile + OTP — no PAN/GST on the form | Trial yes; number issuance after OTP | Own Android app `com.myoperatorapp` ("attend customer calls directly from their mobile" = Wi-Fi softphone routing) + web panel; no raw SIP creds published | **CHOSEN for tonight's free-trial sandbox** (lowest-friction self-serve), FAILS ≤₹600 permanently |
| exotel.com | No self-serve price published; trial = 7 days + "Rs.500 worth free usage (Calls & SMS)"; startup grant ₹6,000 credits | Self-serve form: Name/Company/Email/Phone/Country ("go live in 2 mins"); full virtual number KYC (TAC: PAN/GST or proprietor docs) at activation per their compliance flow | Trial instant; paid plans via Talk-to-Sales | Agents answer via Exotel app/webcall; API-first | Backup sandbox candidate; also over-budget permanent |
| ozonetel.com | Not published — every page funnels to "Request a Demo"; product page claims "Live in under a day" (sales-driven) | Sales-led onboarding | No self-serve | Demo-gated | ELIMINATED (friction; site even rejected our pinned VPN exit: `ERR_EMPTY_RESPONSE` — receipt `05-ozonetel-unreachable-error.png`) |
| airtel.in CloudCC (airtelbusiness) | Not public — /b2b/cloudcc = SPA that never renders without sales funnel; product = demo-request | Enterprise: form + agent follow-up, GST expected | No | — | ELIMINATED (manual/sales KYC = mission-abandon trigger) |

**Chosen: MyOperator free trial** — zero payment, zero PAN/GST on the signup form, own Android softphone app + browser panel, virtual local number selectable (Kolkata 033 pending in-trial picker check).

## WHAT IS DONE (evidence)
- Provider claim pages captured: `01-myoperator-pricing-top.png`, `02-exotel-pricing-top.png`, `exotel-bps.txt`, `airtel-cloudcc.txt` (loader-only proof), `ozonetel-virtual-number.txt`, `myoperator-app-listing.txt` (Play Store: "attend customer calls **directly from their mobile phones**").
- Linphone **installed & launched** this machine: winget reported `No package found matching input criteria` for `Linphone.Linphone`; correct id is `BelledonneCommunications.Linphone` 6.2.2 → "Successfully installed", screenshot `06-linphone-launched.png`. Held as backup SIP client; MyOperator is app-based (no SIP creds exposed) → for tonight the softphone = **MyOperator web panel (app.myoperator.com, Chrome tab already open side-lane)** / their Android app on phone over Wi-Fi.
- MyOperator signup **pre-filled and held before Proceed** (tab 25): Full name `Kunal Das`, Business email `isearch.xsolve@gmail.com`, WhatsApp mobile `9830739230` — Business name deliberately blank (never guessed). Receipt `03-myoperator-signup-form.png` + `.html`.
- **Baba consolidated checklist sent once** to KILO wire at 19:12:26Z (relay seq **28025**, body saved `baba-checklist-0913.json`): needs (1) his brand-name string, (2) cooperation for ONE 2-min window at the end (SMS OTP + `*21*` CFU inside same window), (3) explicit approval for ANY payment (≤₹600 ceiling restated; no payment tonight).
- Device read-only verified before window decision: `airplane_mode_on=1`, guardian `/status → radioOff:true`, both SIM slots Jio (`405873`), `mVoiceRegState=3(POWER_OFF)`. Dual-SIM caveat recorded: this vivo shows a SIM-picker sheet on USSD CALL intent — inside the window I will resolve it via uiautomator dump tap on the 9830739230 slot only.
- **Radio discipline: ZERO windows opened this run** — nothing was issuable that didn't need Baba. Guardian window will be used exactly once, at the end, ONLY after the virtual number exists.

## WHAT IS PARKED WAITING FOR BABA (exact remaining actions)
1. Baba replies on KILO wire with **brand name** → I click Proceed on the held form.
2. If MyOperator sends verification as **WhatsApp** OTP → arrives over Wi-Fi with radio OFF: I read it from notification logs (adb, no taps) — no window consumed for this. If **SMS** → batch it into the single end window below.
3. Trial dashboard → pick virtual number (prefer **033 Kolkata**; else any local; else Exotel 7-day trial as fallback sandbox).
4. ONE guardian window: `POST 127.0.0.1:8768/callwindow {"force":"GOLD24BLINKONLY","minutes":2,"radio":"on"}` → on SIM holding 9830739230: `adb shell am start -a android.intent.action.CALL -d "tel:*21*98307392XX"` (the new number; `*` URL-encoded, SIM-sheet tap handled) → uiautomator dump receipt of the "呼叫转移已启用/Call forwarding enabled" toast → window self-closes → verify `GET /status radioOff=true` + `mVoiceRegState=3(POWER_OFF)×2`.
5. Baba (or Prasun/Subham line) dials the new number → screenshot MyOperator web-panel incoming call over Wi-Fi with radio OFF → report number on wire.
6. Only after ringing succeeds: paid-plan decision (₹5,000/mo is way over ceiling; realistic permanent options at ≤₹600 = none found tonight → escalate the parked-second-phone fallback or accept Jio's own plan with weekly windows).

## FALLBACK IF ALL ELSE FAILS (documented, ready)
**Parked second phone:** dumb handset + cheap prepaid SIM kept at Silchar home, always ON (its tower = the stale home coordinate, zero new exposure — matches GHOST-PROTOCOL §3 note). Jio numbers CFU to it during booked meeting windows only (30–40 min, scheduled to confirmed call slots per MEETING-CALL-RUNBOOK Plan B). Baba's decision only; costs ~₹120 recharge/month, well under ceiling.

## PUBLISHED WORK NUMBER (for LinkedIn service page — pending activation)
`+91 XXXXX XXXXX (MyOperator trial — Kolkata local, answers over Business WhatsApp; calls route to a quiet office line. Hours 10:00–19:00 IST, missed calls get an instant WhatsApp/callback reply.)` — number string to be filled at step 4; publish ONLY after live test rings. Public identity on the service page remains the consulting brand — no KYC-identity details.

## LAW NOTES
- No family/Raktima contact, no money spent, form never submitted past the consent line, WhatsApp-line 8617216163 untouched, zero windows opened this run, exposure ledger: 45s-max policy not exercised (blinkCount unchanged at 1, verified above).
