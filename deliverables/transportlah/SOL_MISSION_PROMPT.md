# TransportLah — Mission Brief for Codex (GPT-6.1 Sol)

Copy everything below the line into Codex as the first message of the mission. Attach: the spec/proposal PDF, `WALKTHROUGH_OVERVIEW.md`, `MILESTONES.md`, and the five seed files (`lta_datamall_proxy.py`, `spatial_verification.py`, `test_spatial_engine.py`, `schema_postgis.sql`, `docker-compose.yml`, `demo_runner.py`).

---

## MISSION: TransportLah — build the journey-verification platform to Milestone 3

You are the lead engineer on TransportLah, a commuter journey-verification platform for Singapore built on LTA DataMall. A working local testbench already exists (proxy with TTL cache, Haversine corridor matching, PostGIS schema, verification engine, passing test suite). Your mission is to take it from testbench to delivered product across three acceptance-gated milestones, working independently across multiple sessions.

### Product in one paragraph
Commuters' smartphones emit GPS pings while riding buses. A Spatial Verification Engine matches those pings against live vehicle positions (via an LTA DataMall proxy with in-memory 30s TTL cache) using geodesic corridor matching in PostGIS. A ride is verified when >= 75% of pings correlate within a 100m corridor and 30s temporal drift. Verified rides feed an engagement/rewards/sustainability platform for the client.

### Working agreements (read once, obey always)
1. **State lives in files, not in your context.** Maintain `PLAN.md` (task breakdown, next 5 actions), `STATE.md` (exact resume point: done / in-progress / blocked, with file:line references), and `DECISIONS.md` (every architectural decision with rationale). Update them BEFORE ending any session. Any session must be able to resume cold from these three files.
2. **Tests are the contract.** Every engine change ships with tests. The existing suite (`test_spatial_engine.py`) must stay green. New behavior = new tests first.
3. **Do not fabricate data.** The walkthrough labels assumptions as `[ASSUMPTION: ...]` and test outputs as `[TEST VECTOR ...]`. Preserve this discipline: any number you produce that isn't from a real LTA response or a real device is labeled. When the real LTA DataMall key arrives, re-verify every labeled number and update the docs.
4. **No secrets in the repo.** LTA key, Apple credentials, any API key → environment variables / `.env` (gitignored) only. The client will provision Apple Developer ($99), Google Play ($25), LTA DataMall key, and cloud hosting — your job is to make every credential a configuration plug-in point, and to keep the system fully functional in `OFFLINE_FIXTURE` mode until keys arrive.
5. **Honesty over polish.** The disclosed known limits stay disclosed (single-ping rejection, 90m parallel-pedestrian false-pass, replay/spoof passes without device attestation). Where you can mitigate (e.g., accelerometer/sensor-fusion design for the pedestrian case), design it and document it — do not silently claim it solved.
6. **Commit discipline.** One logical commit per unit of work, message = what + why. Never leave the repo red (failing tests) at session end.

### Milestones and acceptance gates

**M1 — Transit Telemetry Ingestion Pipeline (start here)**
- Harden `lta_datamall_proxy.py` into a production-shaped service: multi-stop polling with per-stop rate limiting, 30s TTL cache, `LIVE_NETWORK` / `OFFLINE_FIXTURE` modes, health endpoint, structured logs.
- ACCEPT: proxy processes arrival telemetry for multiple stops; rate limits respected under a simulated burst test; OFFLINE_FIXTURE mode fully exercises the same code path as LIVE (only the transport differs).

**M2 — Database-Backed Corridor Verification + Fuzz Battery**
- Move spatial matching from pure Haversine to the PostGIS schema (`schema_postgis.sql`): GiST geometry indices, corridor queries, differential fuzz battery comparing PostGIS results vs the Haversine reference implementation.
- ACCEPT: corridor evaluation <= 30.0s temporal drift tolerance with GiST-indexed queries; fuzz battery passes; performance benchmark documented (pings/sec per core).

**M3 — Commuter iOS client, TestFlight-ready**
- Native iOS app (Swift/SwiftUI): background GPS ping capture (significant-location + continuous modes, battery-aware), sync client for the verification API, trip status screen.
- Since Apple Developer credentials arrive later: deliver the complete Xcode project, CI-ready build workflow (GitHub Actions with Xcode build), a simulator test target, and a step-by-step TestFlight upload runbook that the client executes in 15 minutes when credentials arrive.
- ACCEPT: project builds clean in CI; simulator integration test passes against the M2 backend running in OFFLINE_FIXTURE mode; runbook validated end-to-end except the final App Store Connect step (documented as pending credentials).

### Repo layout target
```
transportlah/
├── backend/            # proxy + verification engine (M1, M2)
│   ├── app/            # FastAPI service
│   ├── migrations/     # PostGIS schema
│   └── tests/
├── ios/                # TransportLah iOS client (M3)
├── docs/               # PLAN.md, STATE.md, DECISIONS.md, runbooks
├── docker-compose.yml
└── README.md
```

### First session instructions
1. Read all seed files. Write `PLAN.md` (break M1 into <= 10 tasks) and `STATE.md`.
2. Implement M1 in OFFLINE_FIXTURE mode with fixtures recorded from the test vectors in the walkthrough (Orchard/Tangs 09048, service 190).
3. End the session with: tests green, STATE.md updated to the exact resume point, one commit.
4. Report: what is done, what is next, any risk you see in the plan.

### Definition of done (whole mission)
M1 + M2 + M3 accepted, docs honest, client can plug in keys and reach TestFlight without touching code.
