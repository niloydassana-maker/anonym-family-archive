# STATE HANDOFF - Crush session window 2026-09-27 19:35 IST -> 2026-09-28 05:35 IST
Rebuilt from `CRUSH-CONVERSATION-LAST-10-HOURS-2026-09-28.md` (1,205 messages, 10 sessions, 553 tool calls).
Every `write` / `edit` / `multiedit` was replayed in timestamp order. All 8 Python files compile; both JSON files parse.

## 1. What was rebuilt (35 files created in-window + 4 pre-existing)
Under `files/D/anonym/...` (mirrors the D:\ layout):
- **Hunt engine** `war-log/hunt/`: `hunt_engine.py` (crawler -> `leads.db`; cmds add/crawl/stats/export/clock, ASSETS dict + DNA match), `hunt_draft.py` (outreach drafts with evidence block), `evidence.json` (paths normalised as `fix_evidence.py` did at 04:49), `fix_evidence.py`, `seeds/buyer-orgs.txt`.
- **Inbound no-miss queue** `hunt/inbound.py` (SQLite `inbound.db`; NEW->ENGAGED->REPLIED->CLOSED/DEAD, 60-min SLA, 48h nudge, 96h DEAD) and `inbound_ingest.py` (read-only gmail/linkedin/whatsapp via Agent 360, Chrome Profile 17). `war-log/tick-inbound.ps1` runs `sla` + `report`.
- **Ticks/config**: `crush-tick-config/crush.json` (provider `nvidiatick`), `tick-linkedin.txt` (mission), `_ps_*.ps1` / `_ps_peek_*.py` diagnostics, `sweep-step3-navya.txt`.
- **Plans & drafts**: `MORNING-FIRE-PLAN-2026-09-28.md`, `roadmap/SEVEN-DAY-EARNING-PLAN-2026-09-28.md`, `roadmap/ASSET-DNA-2026-09-28.md`, `roadmap/drafts/{ARJUN-advance-chase,KARAN-scope-lock,FIRST-RUPEE}`, `hunt/service_sweep_directives.md`.
- **Lane SME**: `lane-sme/mine_targets.py`; `scripts-from-shell/write_sme_targets_csv.py` regenerates `lane-sme/TARGETS.csv` from `career/li-archive/Connections.csv`.
- **Deep review**: `full-drive-deep-review/ZIP-BUNDLE-REVIEW-2026-09-27.md`; `scripts-from-shell/build_zip_census.ps1` regenerates the census CSV.
- **Pre-existing, patched** (base text recovered from `view` output and verified against each recorded edit): `AGENTS.md` (HARD ROCK RULE), `sweep-step.ps1` (auto-continue), `tick-linkedin.ps1` (model = nvidiatick/deepseek-ai/deepseek-v4.1-flash). Plus `agent360_client.py` snapshot (unpatched, unverified).

## 2. Rails as they stood at 05:20 IST
- Driver law: **Crush CLI + `nvidiatick/deepseek-ai/deepseek-v4.1-flash`** (kimi-k3 tick killed 02:13 as too slow; opencode sweep killed 01:57). Config: `war-log/crush-tick-config/crush.json`.
- One browser only: Agent 360, Chrome **Profile 17**, single cross-process token; relay on port 8777.
- NVIDIA key pool via `nvidia-key-rotate.ps1 -Action status|release|acquire` (stale lease released 02:18).
- Schedule: `KILO-MORNING-FIRE` created 02:51 - every 30 min from 08:00 for 2 h, runs `tick-linkedin.ps1`. The older TICK task showed `Enabled=false` at 03:00.
- Night law: 22:00-08:00 IST = discovery + drafts only, zero sends. Speed law: engage within 60 min in business hours.
- No curl/grep/head/tail in Crush bash.

## 3. Numbers at end of window
- Inbound queue: **44 rows (9 ENGAGED, 35 NEW)** after gmail + linkedin + whatsapp ingest (04:47). SLA check: clean.
- Todos at 05:20: T1 confirm warm threads on Profile 17 (in progress) | T2 drafts verified (done) | T3 SME targets mined (done) | T4 service sweep directives staged (done) | T5 verify rails: relay, NVIDIA 13/13, Agent 360, KILO-MORNING-FIRE (pending).
- Priority stack (MORNING-FIRE-PLAN): 1 Arjun Chowdhury advance (Rs 12,500 of Rs 25,000) | 2 Karan R. Sabale scope lock | 3 premium service feed | 4 SME voice-receptionist cohort | 5 Wasim/3wheels.

## 4. Flags - read these first
1. **Night-law breach, unverified.** The Arjun advance-chase DM was sent via Agent 360 at **05:02 IST**, inside the "zero sends before 08:00" window, and the log shows only a screenshot save, not a thread read-back. T1 was still open. Open the thread and confirm what actually went out.
2. **Live-looking GitHub PAT** was found inside sale/GODSHAND zip bundles (addendum in `ZIP-BUNDLE-REVIEW` and the security findings). Revoke and rotate it; do not ship those zips.
3. **WhatsApp ingest pulled personal chats** (family, guest house, "Photo", voice-note durations) into the leads inbound queue as leads. Filter before trusting the 44-row count or the SLA report.
4. `tick-inbound.ps1` says it runs every 15 min, but no separate scheduled task for it appears in the log.
5. Relay health at 05:00-05:20 was never confirmed (curl blocked; port 8777 check result not captured).
6. Four `api_key` slots in `crush.json` were `[REDACTED_SECRET]` in the log. Fill them only if the live file is lost.
7. One multiedit on `hunt_draft.py` (03:52:03) had malformed arguments and was skipped; the following edit at 03:52:30 applied. Re-run `python hunt_draft.py` on a lead and eyeball one draft.

## 5. Not in the log, so not restorable here
`leads.db`, `inbound.db` contents, screenshots/evidence PNGs, `tick-runs/`, `sweep-visible.ps1`, `nvidia-key-rotate.ps1`, other pre-existing scripts, and the 4 pre-existing docs beyond what `view` showed. `SECURITY-SENSITIVE-DATA-FINDINGS-2026-09-26.md` could not be rebuilt (base not recoverable); its addendum edit is in `patches/patches.json`.

## 6. Restore steps
1. `powershell -File RESTORE.ps1 -DryRun` then without `-DryRun` (never overwrites; differing files land as `.restored`).
2. `python patches\apply_patches.py --dry` then live.
3. `schtasks /query /tn KILO-MORNING-FIRE`; create with `scripts-from-shell\create_morning_fire_task.cmd` if missing.
4. `cd D:\anonym\war-log\hunt; python hunt_engine.py stats; python inbound.py stats`.
