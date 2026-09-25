# KILO ARCHITECTURE BLUEPRINT (2026-09-22, Baba-ordered, laptop-only stack)

Companion: KILO-IDENTITY.md (who we are) + war-log/kilo-bridge-thesis.md
(why we win). This file is HOW the machine is built.

ASCII-only by house law.

```
                    +---------------- BRAIN -----------------+
                    | AGY persistent loop per lane            |
                    | mission-once + stdin-continue, 3.6-flash|
                    | accounts: kunal <-> isearch (rotate)    |
                    +------^---------------------v------------+
                           | mission file        | DONE+files
              +------------+---------------------v------------+
              | L2 DUTY/DIGEST (30m / 22:30): own lanes, plan |
              +------------+---------------------^------------+
                           | queue               | receipts
              +------------+---------------------^------------+
              | L1 TRIAGE (15m): judge every event from       |
              | scratch, author D- verdicts + WEB steps       |
              +------------+---------------------^------------+
                           | directives          | snapshots
              +------------v---------------------+------------+
              | L0 MAILBOX: relay :8778 (dumb hands)          |
              +------------^---------------------+------------+
                           | /event poll         | directive
              +------------+---------------------v------------+
              | HANDS: Kilo Bridge v1.9 (content+background)  |
              +--------------------+--------------------------+
                                   | acts on Chrome tabs
                          WORLDWIDE WEB (was disobedient)
```

## 1. BRAIN (AGY)

- Binary: C:\Users\Admin\AppData\Local\agy\bin\agy.exe, --dangerously-skip-permissions.
- Wrapper: war-log\agy-loop.ps1 (Baba's command, looped). Short -p prompt
  references war-log\agy-mission-<lane>.txt; mission = tick file + digest.
  stream-json output; result.response extracted; D- and WEB- JSON
  re-extracted with no-BOM writes. Rest 120s. Mutex Global\KiloTriage
  on the scheduled side.
- Model: gemini-3.6-flash-high (headroom for instruction-following;
  artifacts+mission carry the intelligence, 2026-09-22 Baba order).
- Accounts: kunal.colab (Chrome silent) <-> isearch.xsolve (Pro ticks).
  Rotate script war-log\agy-account-rotate.ps1 + task KILO-AGY-ROTATE 15m:
  evidence-gated switch, 60m cooldown, double-fail hold + flag Baba.
  Bundles: war-log\agy-accounts\isearch.blob.b64 (+kunal.json/raw).
- Scheduled runners: KILO-TRIAGE 15m (tick-triage.ps1, file-based prompt
  since v-fix 2026-09-21), KILO-DUTY 30m, KILO-DIGEST 22:30,
  KILO-WATCHDOG 10m, KILO-RELAY-NANNY 5m. Battery gates OFF (all 10).

## 2. L1 TRIAGE (judgment, 15m)

- Mission: war-log\tick-triage.txt = FULL OWNERSHIP PASS (since 2026-09-21
  night; before that a read-only classifier - the dead-day root cause).
- Digest: war-log\tick-triage-prep.py shrinks 9000+ event files to
  war-log\triage-inbox-now.txt (actionable-first: messaging/mail/jobs/
  marketplace first, feeds last) + OPEN BUYER QUEUE appended.
- Playbooks: war-log\l1-playbooks.md - CLASS-1..6 are EXAMPLES, never rules.
  Every case reasoned from scratch + MENU. THESIS/DNA LAW supreme:
  mirror customer DNA, numbered deliverables in client words, price+days,
  Day 1-2/3-5/6-7 schedule, Phase-2 boundary, access list, 50% advance,
  kickoff tomorrow, close "Say the word and I begin. - Kunal".
  Generic "take a look at my proposal" is FORBIDDEN.
- Outputs per tick: D-<stamp>.json verdicts {event, class_or_NOVEL,
  draft_reply, send, reason}; WEB-<stamp>-*.json physical steps
  {action, match_url_substring, require_body_contains, text/match/url/
  index, reason, done:false}; seen.json; kilo-say.log lines;
  triage-heartbeat.txt (UTC).
- send=true ONLY: fresh reason + floor fit + WHO-PAYS-WHOM explicit +
  standing-GO. Night 22:00-08:00 IST: drafts only (live Baba order
  overrides).

## 3. L2 DUTY/DIGEST (ownership, 30m/22:30)

- tick-duty.txt / tick-digest.txt missions via tick-duty.ps1 / tick-digest.ps1.
- Duty owns lane distance-to-rupee; Digest owns nightly scoreboard.
- KNOWN DEBT: both still pass prompts inline + old model slug; queued for
  the same file-based rewrite tick-triage.ps1 received.

## 4. L0 MAILBOX (relay :8778, dumb by design)

- war-log\li_relay.py (ThreadingHTTPServer 127.0.0.1:8778).
- POST /event {page:{url,title,body,buttons,tabId,isPrimary}} ->
  stores war-log/events/WEB-<stamp>.json -> returns next directive or {}.
- pick(): oldest unconsumed WEB-*.json with done=false where
  match_url_substring in url AND require_body_contains in body (case-ins).
  Marks done=true, logs "DIRECTIVE served" to kilo-say.log.
  Reads utf-8-sig (BOM-tolerant, v-fix), writes utf-8 no-BOM.
- Tab registry keyed hostname+first-path (scope_key mirrors extension
  PRIMARY_SCOPE v3); only scope-primary tabs receive directives.
- served-is-NOT-done: next tick must verify snapshot before next step.
- Logs: war-log/relay.log (WEB-EVENT lines), kilo-say.log (serves).
  15,625+ events banked. GET /health, /debug (registry).

## 5. HANDS (Kilo Bridge v1.9, Chrome extension)

- li-bridge\content.js (hands) + background.js (bridge+keepalive) +
  manifest.json. Profile 17 mains (session 1); army Chrome separate
  (session 0, port 9224).
- Poll loop: snapshot (url/title/body-6000/buttons/tabId/isPrimary) ->
  POST /event -> execute ONE directive -> human-paced sleeps.
- Actions: click(text) lane-aware selectors + deepest-shortest fallback;
  fill(match,text) never-overwrite default; fillforce (v1.8, Baba-go
  overwrite); fillfast (v1.9, one-shot set beats background freeze);
  uncheck, open (https + allowlist), huntvideo/transcript/hunt (YouTube).
- Guards: phone-consultation checkbox NEVER touched (no-calls law);
  never dismiss/decline; human text protected unless fillforce/fillfast.
- Keepalive: chrome.alarms 30s (MV3 worker death fix) + badge clock.
- v1.7 adds: huntvideo/transcript, scoped primaries, alarms. v1.8:
  fillforce. v1.9: fillfast + version label.

## 6. MONEY LANES

- MENU: DASH-B 15k/5d, DEV-B 25k/7d, ML-B 40000/10d, AUD-B 8000/1d.
  50% advance. First rupee funds next spend.
- Marketplace runbook (proven 2026-09-21 night, 6/6 sent+receipts):
  Submit click -> verify dialog open -> fill/fillforce THESIS (<=1500ch)
  -> verify counter -> Send click -> verify dialog-closed + DM thread.
  STRICT one-dialog-at-a-time (modal traps card clicks; text-click is
  ambiguous across identical buttons).
- Buyer watch: reply = hottest class, same-cycle CLASS-4 lock or
  CLASS-1/THESIS answer. Supplier-trap (job-seekers) = CLASS-3 one-liner
  + BENCH, never re-engaged.
- ARJUN WATCH: any Arjun signal outranks everything; file/access/start-date
  closers; never ages a cycle. Founder @ Namahtrix, rtsarjun@duck.com,
  Phase-1 Rs25k/7d assessment-only, 9 deliverables + walkthrough.
- Boards: war-log/roadmap/PROPOSALS.md (pipeline), first-rupee.md (order),
  earn-lanes.json (ledger), drafts/ (exact THESIS texts).
- Job lanes: Indeed LEAD tracking + Easy Apply clicks; Naukri desktop
  questionnaire BROKEN (mobile-app lane only); Foundit pending-action
  clicks (industry tap armed).

## 7. VOICE / XTTS

- Kernel: war-pipe/kilo-core/kernels/kilo-voice-live (isearchxsolve/
  kilo-voice-live), v11. Pretrained XTTS-v2 zero-shot (fine-tune merge
  impossible: arch mismatch gpt.gpt.h.* vs gpt_inference).
  Fixes: SameFileError skip, get_conditioning_latents + correct XTTS API.
- Lock: machine_shape NvidiaTeslaT4 + enable_gpu + CUDA_VISIBLE_DEVICES=0
  + in-kernel nvidia-smi assert (HARDWARE GATE LAW: P100/v9-v11 lessons).
  Datasets: father-voice + xtts-v2-pretrained. Awaiting Baba Run All WARM.
- Voice army: KiloBridge v7 APK (MediaPlayback), full_tribute.wav 870K,
  tribute/live base64 lanes. DEVA variant locked for calls.
- Monetization twin: training kernel + live inference kernel, demo + DM.

## 8. FLEET (watchers + tasks)

- feed-watch.py (4m request-feed sentry), service-desk.py (quote drafts,
  never sends), thread-weaver.py (GUARDED chats), legal-watch.py (30m
  court/loan sentry, fixed Didi templates), li-notif.py, gmail-yahoo-watch.
- Relay nanny + watchdog tasks; sudo-hands :8769 GOLD24 (elevated lane).
- Phones: IQOO 10BE8135QM001KK (apps), Nokia C30 G2866620341C0402558
  (Jio USB SMS OTP). NOKIA-AWAY LAW: WhatsApp Baba +91 86172 16163.

## 9. FORENSIC LEDGER (all paid for, all fixed unless noted)

- F1 read-only mission -> full-ownership rewrite (root cause of dead day).
- F2 loop extractor dropped WEB -> saves D- and WEB-, no-BOM.
- F3 BOM + born-done directives skipped silently -> utf-8-sig relay +
  done=false authoring rule.
- F4 ghost-card deadlock (Hirdaya) -> absent-buyer fallback (DM/My
  Proposals verify, CLOSE or re-drive).
- F5 fake-Z timestamps -> UtcNow everywhere.
- F6 dead scheduled task (arg-split) -> file-based prompt rewrite.
- F7 generic proposals -> staged THESIS drafts, CLASS-6 enforced.
- P8 snapshots hide textarea content -> verify via counter delta.
- P9 modal traps card clicks -> strict one-dialog sequencing.
- P10 text-click can't target one card -> per-buyer require_body_contains
  + sequential flow.
- P11 never-overwrite is CODE not LAW (content.js:588) -> fillforce
  (Baba-go) + fillfast (freeze-proof). House laws binding: night,
  never-decline, receipts, ASCII, no-calls, THESIS.
- P12 background-tab timer freeze (~1 char/sec) -> foreground tab or
  fillfast; bulk-set + input/change pair.
- P13 LinkedIn drops typed drafts on re-render (649->180) -> refire by
  force; verify before Send.
- P14 loop self-match in process scans (checker matched itself) ->
  split-string filter discipline.
- OPEN: tick-duty/digest inline prompts; fillfast unfired in combat;
  Hirdaya recard watch.
- J1-J8 job-lane forensic 2026-09-22 -> relay v1.4 (primary-migrate,
  buttons-require, atomic writes) + hands v2.0 (captcha backoff, cold-scope
  10min poll, no Gmail deep-scroll) + mission liveness check. Needs Baba
  extension reload to take effect.
- RECON LAW 2026-09-22 (all lanes): sweep market on 2+ boards, rank fits,
  engage only on Baba word/standing-GO. Search -> fit -> engage is the
  product. Relay v2.2 composer flag + hands v2.1 visible-click + Discord lane.

## 10. MONETIZATION DOCTRINE (pointer)

- war-log/kilo-bridge-thesis.md: disobedient browser was the wall, Bridge
  is the $10 answer, Parallel does it the hard way. Students/freshers
  (jobs) + businesses (brand). NEVER product posts: DMs/InMails + demo
  recordings (YouTube/Naukri/LinkedIn versions). XTTS twins same way.

The wire never dies. Customer is god. Served-is-not-done.
