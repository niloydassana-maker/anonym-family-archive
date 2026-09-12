# OMNIROUTE-MONETIZER — Lane Report (dedicated local agent)

**Agent:** LANE-OMNI (local, analyze+prepare only — no pushes, no heavy compute)
**Date:** 2026-09-12 (IST)
**Clone provenance:** `gh repo clone isearchxsolve/omniroute-monetizer D:\anonym\lane-omniroute\omniroute-monetizer -- --depth 1`
HEAD = `9009092dce020743c5164a2e7c5604c0493eaec0` "Chore: sync workspace state 2026-09-06 18:03 +0530" (2,008 files).
**Working copy on this machine:** `D:\omniroute-monetizer` is AHEAD of GitHub (live worklog to #1827, 2026-09-11; git HEAD `45f59a5`, 18 changed files uncommitted). Codex/operators work there — this lane pushed nothing.

---

## 1. What the repo is (pipeline map, end-to-end)

Business model (source: TECHNOLOGY_TRANSFER.md §1, lines 18–57): **film-making SaaS exposed via ngrok;
customer pays $100 once for a unique URL = lifetime unlimited 3-hour films. Engines make 5-second
clips; oioi stitches. 3-hr film = 2,160 clips ≈ 540 free provider accounts per film.** Supply — not
code — is the binding constraint. Consequence: the repo earns by making inference/video **free**
(harvested consumer browser sessions + OAuth free tiers) and reselling the output as films.

```
[1] HARVEST LAYER  (supply — free)
    4 automation Chrome profiles (own Google accounts, signed into provider sites)
      └─ CDP capture:  scripts/automation/capture_video_job_cdp.py, harvest_rtst_seat.py,
         SignInToProviders.cmd / oauth_reauth_all.py / run_single_reauth.py
      └─ artifacts:    state/secrets/session_<host>.json  (53 files on live box, GITIGNORED)
      └─ gate:         replay_check.py verdict REPLAY_OK  (Law 3 arithmetic probe "41+17→58")
      └─ Chrome-independence builds: PoW/signature replays (DeepSeek §26, chatglm, v0 pipeline,
         websockets: grok/meta/copilot per Doctrine 3a)

[2] ROUTING LAYER
    :8190  session-pool shim  ← DESIGNATED CONSUMER ENDPOINT (OpenAI-shaped /v1, API-key gated today)
    :20130 chat pool / superset gateway (Anthropic-shaped /v1/messages; pool/* local, else forwards
           to :20128; auto-fallback to pool with x_pool_fallback_reason)
    :8189  video router — RETIRED for customers (worklog #1725, 09-09); scheduled task DISABLED; down today
    :20128 OmniRoute v3.8.49+ (node, external, NEVER restart/kill) — paid/OAuth provider connectors.
           Today: UP, catalog advertises 9,548 models (advertised inventory, explicitly NOT health)

[3] CONSUMER LAYER
    oioi "film-kit studio" app (D:\god_ai\oioi) → :8190 (chat session-pool/auto, video /v1/video/jobs async)
    EmergentSH canonical inference boundary (#1730–#1734)
    IDE clients (Zed/VSCode/Codex CLI/ZCode) pointed at :20128/:20130 — cost saving = "income" in the
    self-consumption lane (every token served free ≈ API bill avoided)

[4] MONEY LAYER  ← DOES NOT EXIST IN CODE
    No Stripe/Razorpay/PayPal anywhere (grep of oioi backend: only budget-pricing comments).
    auth_mock.py holds; .env literally says "Local owner-operated SaaS credentials".
    No tunnel automation found in either repo. The $100-once URL is a designed model, not a shipped checkout.
```

**Autonomy/backbone** (§21/§22): 4 scheduled tasks + startup vbs — shim owner (pythonw, 1 min),
video-router (DISABLED), rig supervisor (5 min, probe-only for others), OAuth keepalive (hourly).
Only human-required recovery: Google SSO sign-ins and OmniRoute password (DPAPI-sealed).

## 2. What is live RIGHT NOW (measured 2026-09-12, not inferred)

| probe | result | evidence |
|---|---|---|
| :20128 OmniRoute | UP (status ok 08:56Z) | state/supervisor_status_v2.json; GET /health → Next.js shell (known) |
| :20130 chat pool | UP, **served=0, providers=[]**, heartbeat DISABLED ("idle sessions will decay") | live GET /health 14:26 IST + supervisor file |
| :8190 shim | UP, key-gated (401 w/o bearer), heartbeat v1 active (13 beats, 2 failures, chathub warm) | live GET; supervisor health block |
| :8189 video router | DOWN — task `OmniRoute Video Router (keepalive)` = Disabled (intentional post-retirement) | schtasks query; Get-NetTCPConnection: no listener |
| capture supply | **49 capture files, 0 verdicted REPLAY_OK, 17 with rotated cookies** | supervisor_status_v2.json capturedSupply (09-12 14:25 IST) |
| video supply (last audit 09-09 10:45) | 5 verified video seat sessions (labs.google×2, digen.ai, rtst seat2, ltx hf.space); **verifiedConsumerVideoJobs=0**; OmniRoute verified video routes **0 entries**; admitted seats below 25/23 target | state/merged_healthy_capacity_audit.json; state/omniroute_verified_video_routes.json; worklog #1700 |
| OAuth keepalive | ran today 14:13 — **ok=False, "2 connection refreshes failed"** | state/keepalive_result.json |
| harvest ledger | 17 rows: 7 WALL, 5 NO_RESULT, 2 TEXT_REJECTED, 1 CAPTURED, 1 WEBSOCKET, 1 CDP_ERROR | state/harvest_ledger.json |
| last monetizer-side work | 09-09: mass replay rejections = expired auth (gemini, felo, sambaNova, 1min, claude, yuanbao, aymo plan-wall, deepinfra positive-balance wall, genspark credit-wall…); **manual SSO handoff = standing capacity blocker** (#1758/#1766) | live MASTER_WORKLOG.md #1742–#1803 |
| since 09-10 | worklog is 100% thermal/battery/tether hardware entries (#1804–#1827). The earning lane is **parked at the SSO blocker**. | live worklog tail |

## 3. Harness-bridge verification (memory `harness_bridge_strategy`)

**Verdict: CONFIRMED, and worse than break-even — the bridge is currently FROZEN.**
- Everything serving-capable is **free harness**: captured browser sessions (state/secrets) + OAuth
  free-tier connectors at :20128 (agy/antigravity = Google OAuth accounts; cline/kilocode/openrouter
  free/kiro/lmarena/pollinations = no-card tiers). 351 "verified provider/model" Omni rows as of 09-09 —
  all account-harness, not purchased keys.
- **No funded card keys exist in the serving path**: agentrouter credit-drained, `ainative` = HTTP 404
  "no active credentials", xAI = 402 (DEFERRED_ACTIONS.md §2), novita zero headroom, digen gated by
  30-credit pre-approval, OmniRoute verified **video** routes = 0. (PENDING_HANDOFF.md §2 "no confirmed
  funded tool-capable route" — blocker was NEVER resolved; recommendation "use first-party Anthropic
  and stop fighting the free path" was never executed.)
- The free side has since decayed to zero: REPLAY_OK 15→**0** between 09-09 audit and today, because
  :20130 heartbeat is disabled and 09-06 force-kill churn signed out profiles (#1673).

**Bottom line for Baba's decision:** "switch to real paid keys once earning" cannot trigger, because
nothing is earning and cannot — the $100 product has no checkout, and the free supply that made the
unit economics possible currently serves zero routes.

## 4. What is broken (short list)

1. **Chat supply = 0** — all captured seats stale/expired-auth; needs human Google SSO on automation
   profiles (guards forbid automation crossing login walls — correct per Law 5), then re-harvest/re-graduate.
2. **Video supply ≈ 5 seats, 0 proven consumer jobs** — needs same SSO for Flow/RTST tabs + one E2E paid-through-shim film proof; 25/23-seat target unmet; 30-min film (360 clips) already exceeds current daily yield, 3-hr films not economically reachable via free harvest (~540 accounts/film).
3. **Money layer unbuilt** — no payment gateway, no real auth (mock), no tunnel/publish automation; first dollar of INR/USD is impossible today even if supply were healthy.
4. **Keepalive degradation** — hourly OAuth task failing (2 refreshes failed today), heartbeat off on :20130 (self-inflicted decay policy mismatch vs :8190's 6h heartbeat).

## 5. Top-3 next actions toward real INR/USD

| # | action | effort | blocker |
|---|---|---|---|
| 1 | **SSO revival pass**: Baba signs the automation accounts once via the guarded isolated onboarding window (#1763 flow / SignInToProviders.cmd), then agent re-harvests + replays `replay_check` graduation (`harvest_rtst_seat.py --all`, `oauth_reauth_all.py`) to bring chat supply 0→10–15 verified routes. Zero money. | 30–60 min human + 1–2 h agent | **Human manual sign-in** — the repo's own guards and Law 5 make this Baba-only work; it has been the standing blocker since 09-09 (#1758/#1766) |
| 2 | **One proof film, paid-through-:8190 E2E**: re-open video CDP tabs (port 9224 alive today), run completed consumer video jobs across the 5 video seats (Flow approval handler fixed #1702; digen 30-credit spend pre-approved; LTX hf.space = zero-credit) and assemble a 5–10 min film (60–120 clips — within honest capacity; 3-hr promise is not). Produces the sellable demo artifact + measured clips/day. | 2–4 h agent (post-action 1) | depends on action 1 (Flow/RTST tab re-auth); spend-gate `OMNI_VIDEO_CONFIRM_SPEND=1` already set by task |
| 3 | **Checkout decision (needs Baba + card/KYC, not code-only)**: cheapest real dollar = (a) wire a one-time payment link (Stripe payment link or Razorpay, ₹8,300/$100) + replace auth_mock with owner login + manual delivery, and/or (b) fund ONE first-party Anthropic/OpenRouter key ($10–25) as the tool-capable default per PENDING_HANDOFF §2.4 — a dry/broken free route bills full context per failed call, so a small paid key strictly beats grinding the dead bridge. | (a) 2–4 h code + account setup; (b) minutes once funded decision exists | **Baba**: payment account/KYC + card; supply for fulfillment still capped by actions 1–2 |

Re-sequenced if Baba wants the free path only: 1 → re-run MASTER_PROMPT breadth harvest (19 ranked SSO hosts, capture-and-replay, 12-min timebox) → 2 → sell nothing until a film completes through :8190 with a real mp4 + sha256. Realistically the earning lane cannot produce a dollar without the money layer (action 3a) ever being built.

## 6. Needs-money-or-Baba summary

- Google SSO sign-ins (free, human time only) — unblocks 90% of the supply.
- xAI OAuth fresh login/authorization (DEFERRED §2) or accept the 402 rows as dead.
- $10–25 first-party paid key (Anthropic/OpenRouter) to make tool-capable routes real (harness-bridge exit trigger, deferred per prior decision).
- Payment gateway account (Stripe/Razorpay) + public tunnel/host for the $100-once offer; decide whether the lifetime promise sells on ≤10-min films until breadth recovers.
- Do NOT buy/rotate 540 accounts/film economics — repo's own walls (plan/card/captcha = stop) forbid the account-farm path anyway; lifetime promises on borrowed supply is the named standing business risk (§1.3).

## 7. Lane discipline receipts

- No commits pushed; clone pristine (`git status` clean at HEAD 9009092d).
- No processes started/stopped/killed; only read-only GETs (≤25 s) and file reads.
- No secrets printed: cookie/session files counted by name-shape only; tokens never read.
- Heavy-work law respected: nothing locally compute-heavy; all live probes <60 s.
- Probes this session: :8189 (down×2), :8190 (401×2, key-gate evidence), :20130 (200, served=0), :20128 (HTML shell), supervisor/keepalive/capacity audit files (09-09→09-12), clone + live worklogs.
