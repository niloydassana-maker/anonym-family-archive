# D:\god_ai Monorepo Audit — Full Subfolder Survey (2026-09-06)

**Repo context:** `D:\god_ai` is itself a git repo (remote: `github.com/isearchxsolve/god_ai.git`), created ~2026-06, last root commits 2026-08-28/31. Nearly all work is agent-driven (aider histories, MASTER_WORKLOG.md, AUDIT_REPORT.md everywhere). ~16GB total; the bulk is duplicated node_modules/venvs inside variant folders.

---

## Root level (`D:\god_ai`)

**What it is:** Monolithic coding-agent family + orchestration scripts. `neon_architect.py` (256KB), `neon_architect_v4_7_mobile_env.py` (601KB), `neon_architect_v5_perf.py` (685KB), `nim_agent.py` ("NEON ARCHITECT v4.0 — Monolithic Coding Agent for NVIDIA NIM"). Supporting: `harness_test.py`, `audit_codebase.py`, zip/packaging scripts, `setup_continue_dev_4_projects.*`, `DAILY_IMPLEMENTATION_HANDOFF_2026-08-28.md` (formal handoff doc for OiiOii + EmergentSH), `MASTER_WORKLOG.md`, convergence system prompts, agent input logs (`last_100_inputs.jsonl`). Also 4 stray junk files, `cosmofeed-products.zip`, `instamojo-products.zip`.

- **Verdict: TESTBED** (workbench) — but the `neon_architect` family inside it is a flagship artifact.

## Per-subfolder findings

### ack
Single fragment: `routes.ts` (242KB, 3,746 lines) — Solana meme-trading server routes. **Verdict: JUNK** (orphaned fragment).

### ai_video_monetizer
Faceless-YouTube monetization automation: Google Sheets/Drive pipeline (OAuth), Runway video generation, Gumroad webhook server, deploy scripts. 9 pytest files, pytest.ini, `.coverage`, AUDIT_REPORT.md, ENV_CONFIGURATION_GUIDE. `client_secret.json` present (sensitive). **Verdict: WORKING PROTOTYPE.**

### api_money_bot_complete
"API Money Bot v3.0" — Playwright stealth-browser credential/payment automation across 34 platforms + `universal_harvester` (Crawlee). Run log 2026-06-14: **0/29 platforms configured, mostly failed; only GitHub login succeeded**. `.env` with real values. **Verdict: TESTBED. KEEP STRICTLY PRIVATE** — credential-harvesting optics are toxic in any portfolio.

### ases_v3_1
**ASES v3.1 — Autonomous Software Engineering System**: closed-loop multi-agent freelance automation (n8n orchestrator + Python `agent_service` with ~20+ agents: architect, coder, reviewer, clarifier, debug, autoscaler, billing, canary deployer, chaos replay, failure classifier, knowledge graph…), 3 TDD gates, docker dev stack, 54 test files, changelogs v2.4→v2.10, 142KB AUDIT_REPORT. Honest 14-defect teardown of v1. Last activity 2026-08-22. **Verdict: WORKING PROTOTYPE** (most mature of the SDLC-agent trio).

### claude_code_clone
Duplicate of root `neon_architect.py`. **Verdict: DUPLICATE / JUNK.**

### convergence_framework
Methodology IP: "Convergence" — specification-driven zero-defect optimization (solve/verify modes, objective-function formalization, formalizability walls). Well-written `README_objective_function.md`, deterministic system prompts, trading-bot playbooks, packaged kits, PDF. **Verdict: TESTBED as code — but the strongest "AI-First Leader" methodology/white-paper asset in the repo.**

### crypto-ai-auto-trader
Solana meme-trader script family: HWR signal engine, meme signal engine, market-condition analyzer with auto-pause, trending tokens, backtest, wallet integration. Heavy doc set signaling iterative live-fire debugging. **Verdict: WORKING PROTOTYPE.**

### crypto-app-by-replit
"Solana Hybrid Sniper Ultra" — Express+React (Shadcn) dashboard on Drizzle/Postgres + Python FastAPI ML service (XGBoost, 13 features, 65/35 rule/ML blended scoring), DexScreener 6s-cached scanning, paper/live toggle, strategy modes SNIPER/MG/HWR/AUTO, graceful ML fallback. **Verdict: WORKING PROTOTYPE** (cleanest full-stack trading dashboard).

### crypto-trader-v1_1
**Flagship trading monorepo** (1GB): systemd units (`trading-engine.service` + `trading-failsafe.service`), liquidator build target, panic/halt/resume safety commands, npm `gate` = typecheck+smoke+integration+safety, exhaustive production-safety tests, `incidents/` dir, heavy run logs (66MB app.log.1, 7.5MB paper_run.log, live-runner logs June 2026, crash/failsafe logs) — live trading June 2026, paper runs through July. Last commit 2026-08-22. ⚠️ **`gmgn_keys/gmgn_private.pem` present — live private key on disk.** **Verdict: WORKING PROTOTYPE with real production attempts — portfolio-worthy as engineering, PRIVATE as code (keys + legal exposure).**

### crypto-trading-ai-agent
Small standalone Python agent, educational scale. **Verdict: TESTBED.**

### emergentsh-standalone-clean
**NeonBuild** (emergent.sh clone) — prompt→full-stack-app SaaS. FastAPI backend (`agent_pipeline.py`, `code_generation.py`, `sandbox_executor.py` hardened Docker sandbox, `nim_client.py`, `mobile_targets.py`), Next.js frontend with Playwright e2e, 12 Python test files, alembic migrations, docker-compose smoke+prod, `preview_apps/` outputs, ARCHITECTURE/DESIGN docs. **Actively developed to 2026-08-31** (EM-1…EM-5 hardening series: fail-closed SECRET_KEY, per-user credit ledger, sandbox hardening, suite 8 failures→0, admin customer activity centre). Canonical checkout per handoff doc. **Verdict: WORKING PROTOTYPE → near-PRODUCTION-READY.**

### emergentsh-standalone_old / emergentsh_old
Earlier variants; `emergentsh_old` is 4.6GB. **Verdict: DUPLICATE (archive).**

### god_ai_scripts
ML training/ops pipeline for on-device toxicity/profanity detection (feeds screen_guard_final): dataset builders/cleaners, collectors, YOLO/ONNX/TFLite converters, `train_toxic_detector.py`, TFLite int8 export, inference/benchmark tooling. **Verdict: TESTBED** — but a supporting ML library with a real deploy target.

### guardian_app
Flutter parental-control app (Firebase auth/Firestore/messaging/storage, Google Maps, geolocator, local_auth, fl_chart) + Node/Express backend (firebase-admin, helmet, rate-limit). `AGENTS.md` is the Convergence system prompt — built by agent under the convergence doctrine. **Verdict: WORKING PROTOTYPE** (scaffolded full app, unproven build).

### gumroad-products
Sales packaging: 6 product READMEs, email sequences, social calendar, Gumroad descriptions, payout guide. DELIVERED_SUMMARY: 2 of 7 items pending. **Verdict: TESTBED (marketing kit — keep private).**

### hsf
**"Hardened adversarial suite — Neon Architect"**: 4-tier adversarial QA harness (WriteTool/EditTool/file-tools/stack-gate) targeting the neon_architect agent — fence stripping, AST gates, path traversal, symlink escape, ReDoS probes (out-of-process w/ hard timeout), destructive-git bypass attempts. Stdlib-only, <2 min run. **README records last result: PASS 111/115.** **Verdict: WORKING PROTOTYPE — as a red-team test suite for an LLM agent's tool layer, this is a portfolio standout.**

### ikon_agent-main
Full vendored clone of n8n source + docker-compose with hardcoded postgres password. **Verdict: JUNK / DUPLICATE** (third-party code).

### lasthelp
4.5GB release-QA mega-container: snapshots of most projects + `release_control/` (master_orchestrator, policies.yaml, artifacts/evidence/logs, quality-audit generators) + `SALE_BUNDLE` with **QA_TOTAL_OUTCOME 2026-08-09: sequential per-project QA — PASS 11 / FAIL 4 / SKIP 2**, plus `qa_evidence/` screenshots and personal folders (lifedocs). **Verdict: TESTBED / DUPLICATE** — QA evidence valuable; duplicated GBs are not. Private.

### lateststablecode / stabletcode
Loose copies of crypto-trader server files. **Verdict: JUNK (snapshot fragments).**

### live_generated_expo-node / fastapi-react / flutter-fastapi / nextjs-postgres
Neon Architect's generated "task management app" in 4 stacks, each with ARCHITECTURE.md, PLAN.md, docker-compose, CI, tests. The `VERIFICATION.md` files are honest failure reports. **Verdict: TESTBED** (agent-output samples; the verification discipline is the value).

### oioi / oioi\oioi
Container has variant duplicates. The real project: **"OiiOii" film-generation SaaS**: Next.js + Prisma/Postgres schema (User/Project/Asset/Scene/Character/Style/GenerationJob), admin customers console, Python FastAPI backend (`film_pipeline/`, `studio_pipeline/`, `providers/`, `agent_contracts.py`, Groq adapter, models registry), Node `server/` routes, docs, tests. **Git active through 2026-08-31 — the most recent work in the whole repo**: approved seven-stage crew + Director handoff gating, closed owner-provisioned SaaS access, content-addressed artifact storage, customer activity centre. Sibling `oioi\film-kit-studio` is its FastAPI film-pipeline service. **Verdict: WORKING PROTOTYPE → near-PRODUCTION-READY** (best-maintained project).

### OMEGA
**OMEGA SOTA UI** — dynamic automation agent: web research → DAG plan → materialize deliverables → verify/learn/fix loop → zip. Full `omega_agent` package, Gradio UI, 17 test files (convergence smoke, DAG parallel, tenant, MoE…), Dockerfile, FAISS index + vault, docs (CONVERGENCE, SCALING with multitenancy), Colab/Kaggle vLLM notebooks, SOTA roadmap, AUDIT_REPORT, mock-mode quickstart. **Verdict: WORKING PROTOTYPE** (strongest test culture after hsf).

### screen_guard_final
**SafeScreenGuard** — real Android app (Kotlin, minSdk 29/target 35): real-time screen capture + audio profanity/toxicity detection (TFLite + Whisper, noCompress tflite/bin packaging, ultra-low-latency beep player, capture service), ARM-only ABI split. Consumes models trained in god_ai_scripts. **Verdict: WORKING PROTOTYPE.**

### solana-auto-trader-live
Re-packaged subset of crypto-ai-auto-trader. **Verdict: DUPLICATE.**

### test_coding_agent
`neon_architect.py` copy + `test_windows_shim.py` — a thoughtful Windows diagnostic for the agent's RunTool executable-resolution. **Verdict: TESTBED.**

### test_sdlc_sandbox
Neon-Architect-generated Flutter+FastAPI realtime chat app with project state, working memory, 1.7MB agent TUI session log, PLAN.md. **Verdict: TESTBED.**

### the-beholder-project ★ deep dive
**Life Archive platform + the publishing pipeline that produced the published Beholder books.**
- **Architecture:** Python package `life_archive/` — connectors (`local-files`, `git` bundle+metadata, `github` REST w/ pagination+backoff, `google-takeout` zip fan-out, `whatsapp` export parser, `linkedin` CSV/JSON by category), append-only `storage` abstraction (local → MinIO/S3), `manifest` + `hash` (SHA-256) + `schemas/provenance` (dedupe), `privacy`, `indexing`, Typer CLI.
- **Tests:** 9 pytest files / 32 passing; honest LIMITATIONS.md (exemplary accounting).
- **Infra:** docker-compose (Traefik, Postgres 16 w/ secrets); locally-run Meilisearch, MinIO (life-archive-raw bucket), Qdrant (archive_objects collection with real vectors) — the stack actually ran.
- **Book-builder pipeline:** `book_builder.py` (ReportLab typography framework) → `build_vol1/2/3.py` → `build_kdp_final.py` (6×9″ KDP specs: gutter, full-bleed covers, copyright pages, back-cover blurbs) → `compile_lifedocs_books.py` (54KB; declarative BOOK_SPECS compiled from source PDFs via PyMuPDF, with a test enforcing every non-duplicate PDF assigned exactly once).
- **Output:** FINAL Vol I–III PDFs, `PUBLISHING_DELIVERABLES/books/{commercial,release,kdp}` (~20+ titles incl. The Beholder Cycle, Broken Light Screenplays, GODSHAND, Build Ship Sell, Free GPU Film Lab, First Rupee Playbook) with covers; Gumroad+LinkedIn launch kit.
- **Verdict: WORKING PROTOTYPE with shipped output** — closest to PRODUCTION-READY here, because its product (published KDP books) exists in the market.

### timeofmylife ★ deep dive
Same Life Archive codebase forked as the personal-life instance, and the second book factory:
- `LIFE_ARCHIVE/` with full 00_RAW → 12_AUDIT + 99_PRIVATE numbered pipeline; `.qdrant-initialized`; `.env` + secrets generator; native/docker start scripts.
- `RESEARCH_OUTPUT/47_YEAR_CONVERGENCE_RESEARCH_REPORT` + archive inventory.
- Publishing: `Time_of_My_Life_An_Autobiography_of_a_Beholder.pdf`, **51 deliverables** incl. 9 KDP-formatted books + covers, LinkedIn 30-post packs (artist/founder/memoir/direct-offer), DM scripts, launch checklist, monetization handbook, Gumroad listings, `DAILY_EARNING_REMINDER_10AM.md`.
- `AGENTS.md` shows matured three-pillar doctrine (business-vision compliance, deep audits, UI polish).
- **Verdict: WORKING PROTOTYPE with shipped output.** ⚠️ **Never publish this folder** — 99_PRIVATE and life-archive raw data.

### voice_agent_avatar / voice-agent-clinic
Container: 52-file line-by-line AUDIT_REPORT + F5-TTS vs ElevenLabs research doc.
**voice-agent-clinic:** AI-receptionist infrastructure for 5 verticals (dental, medical, HVAC, legal, real-estate): free WebSocket bridge (local Whisper → Gemini Flash → F5-TTS), FastAPI webhook server (Twilio + Cal.com validation), web widget, Kaggle GPU notebooks for TTS/LivePortrait avatar, monitoring, outreach, `config_free.py` (paid providers gated behind `ALLOW_PAID_PROVIDERS=1`), CI workflow, pytest markers (smoke/release-gate), FIX_LOG + FLEET_WORKLOG. **Verdict: WORKING PROTOTYPE** (best doc/story of the "free-stack AI infrastructure" thesis).

---

# Final Summary

## Public portfolio vs private

**Public portfolio-worthy (sanitize `.env`, keys, personal data first):**
1. **the-beholder-project + timeofmylife publishing pipeline** — "AI publishing pipeline: connector-based life-archive ingestion → provenance/hashing → vector index → declarative ReportLab book compiler → 20+ KDP-formatted books, 3 TDD gates, honest LIMITATIONS docs." Strongest story *because it shipped*.
2. **oioi (OiiOii film SaaS)** — multi-agent film studio SaaS, most recent and most disciplined engineering.
3. **emergentsh-standalone-clean (NeonBuild)** — prompt-to-full-stack-app platform with hardened sandbox + credit ledger.
4. **hsf** — adversarial QA suite for LLM-agent tooling (111/115 PASS) — rare, credible, interview-gold.
5. **OMEGA** — DAG-planner agent with verify/fix convergence loop.
6. **ASES v3.1** — multi-agent SDLC system with 54 tests and honest v1 teardown.
7. **convergence_framework** — publish as methodology/white paper ("Convergence Engineering").
8. **voice-agent-clinic** — free-stack AI receptionist infra.
9. **neon_architect family + test_coding_agent/test_sdlc_sandbox** — the monolithic-agent lineage, presented as one project.

**Private (never public):**
- crypto-trader-v1_1, crypto-app-by-replit, crypto-ai-auto-trader, solana-auto-trader-live, crypto-trading-ai-agent, ack, lateststablecode, stabletcode — live private keys, `.env` secrets, regulatory optics. Cite as "algorithmic trading engine (private)" only.
- api_money_bot_complete — credential-harvesting framing is disqualifying; delete from any pitch.
- timeofmylife LIFE_ARCHIVE / lasthelp (lifedocs, 99_PRIVATE) — personal data.
- ikon_agent-main — vendored n8n, not your code.
- gumroad-products — internal marketing kit.
- emergentsh_old, emergentsh-standalone_old, oioi/lasthelp duplicates, node_modules, __pycache__, stray root files — archive/delete candidates (~12GB+ reclaimable).

## Cross-project shared patterns (the "AI-First Technology Leader" narrative)

1. **Convergence doctrine as shared IP** — same spec-driven zero-defect method as system prompts (root), convergence_framework, guardian_app's AGENTS.md, OMEGA's verify/fix loop, hsf's adversarial tiers. One method across 5+ codebases — a leadership artifact, not a hobby.
2. **Honest-verification culture** — VERIFICATION.md files recording failures, LIMITATIONS.md, QA_OUTCOME matrices, AUDIT_REPORT teardowns. Unusual and highly presentable.
3. **Platform architecture replayed 3×** — ASES (dev-agent SaaS), NeonBuild (app-builder SaaS), OiiOii (film SaaS) share one skeleton: closed owner-provisioned access, customer/credit ledger, job gating, artifact storage abstraction, admin activity consoles.
4. **Monolithic-agent lineage** — one evolving single-file agent (v4.0 → v4.7 mobile → v5_perf) with tool lifecycle, AST gates, and a dedicated adversarial suite — a self-built alternative to Claude Code with its own red-team harness.
5. **Free/self-hosted AI stack engineering** — voice-agent-clinic, OMEGA (Groq/vLLM), god_ai_scripts (TFLite int8) — consistent "AI for ₹0 infra" theme.
6. **Life-data connector framework** — reusable IP for any personal-data-archive/compliance product.
7. **Observed weaknesses to own and fix:** secrets in working trees (one live trading private key), duplicate variant sprawl, junk fragments, hard-coded credentials in vendored compose. A one-day hygiene pass (secrets rotation, `_ARCHIVE/` consolidation) would make the public-story repos actually publishable.
