# KILO-BRIDGE SETUP — delivery package (buyer copy) — $1 (Rs 100 offer)

## What this is
"Disobedient Browser, Tamed." An AI automation setup that works inside YOUR real Chrome — Gmail, LinkedIn, job boards — headless, zero screen disruption, receipts for every act. Watch docs/demo-video.mp4 first: 30 seconds, 11 lanes, laptop idling.

## Architecture (how it works)
1. EXTENSION: Agent360 Browser MCP (Chrome Web Store, $10 one-time) sits inside your real Chrome profile — cookies, 2FA, sessions already there. Sites see a legitimate user, not a bot.
2. SERVER: @agent360/browser-mcp runs headless (no window), speaks JSON-RPC over a local port. Lazy-binds: port opens on first tool call.
3. RUNNER: scripts/agent360_client.py — Python wrapper (navigate, screenshot, click, fill, read). UTF-8 everywhere.
4. MISSION: docs/FINAL-AGY-PROMPT-2026-09-24.md — the run-book (recon -> DNA-rank -> engage -> receipt). Your AI agent (OpenCode/AGY) executes it.
5. RECEIPTS: every act leaves a screenshot + log line. Tool-called is not done; screenshot-shows is done.

## Install (15 minutes)
1. Install the Agent360 Browser MCP extension from the Chrome Web Store; pin it; click Reconnect.
2. Install Node 22+ and Python 3.11+; `pip install faster-whisper` (optional, voice notes).
3. Copy opencode.json.example to your OpenCode config; add your model key.
4. Copy scripts/ beside your mission folder. Run a list-tabs test. Green = go.

## First run (same day)
1. Feed your AI the mission prompt (docs/FINAL-AGY-PROMPT...). 2. It recons your lanes, ranks fits, drafts in your voice. 3. Slow pace on LinkedIn (15/day, 3-min gaps) — never bot-blast. 4. Verify receipts folder. 5. Balance due only after the first verified run.

## UNATTENDED SELF-LOOP (runs while you sleep)
Like our house runs: `scripts/install-task.ps1` registers KILO-MISSION-LOOP at logon — the agent executes the mission, rests, re-executes, forever. Quota holds pause it automatically; a mutex keeps one owner; create `STOP.loop` in this folder to stop gracefully. Logs: mission.log. This is the same loop pattern that ran 11 lanes overnight with zero screen disruption.

## Laws (bind every run)
- THESIS on every word: mirror customer DNA, ASCII-only, never generic.
- One send per thread; badges earned (screenshot proof); pixels overrule logs.
- Never passwords/OTP/bank-calls; your logins never leave your machine.

## Support
7-day fix window included. Retainer available. "Say the word and I begin. - Kunal"

## DONE-FOR-YOU SETUP (we install it for you)
DIY not your lane? We do the full setup on YOUR machine over screenshare: extension + server + first verified run, same day. Setup price follows YOUR DNA (we read your lane, you pay your means):
- VERY POOR / student with nothing: FREE pay-it-forward (1 slot/week — your success story is our ad).
- POOR / fresher: 999 (seeker lanes) / 1,999 (business lanes).
- AFFLUENT / business: 1,999 (seeker) / 4,999 (business) + retainer option.
50% advance (waived for free lane), balance on first verified run. Your logins never leave your machine; we never ask passwords — you stay at the keyboard for logins, we do the rest.
