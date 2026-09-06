# Software Project Catalog — D:\ Drive (compiled 2026-09-06)

## Master Table (sorted by resume rating)

| # | Rating | Project | What it does | Tech stack | Path |
|---|--------|---------|--------------|------------|------|
| 1 | ★★★★★ | **Emergent Platform (emergentsh_latest)** | Full agentic app-builder platform: AI agents build web apps end-to-end — chat UI, cloud IDE (terminal+Monaco), sandbox orchestration, VFS with git, live event streaming, autonomous QA with visual regression & auto-fix, MCP server | Next.js 14/React/TS, ws WebSocket microservices (orchestrator, sandbox, VFS, streamer, qa-runner w/ Playwright, MCP, deploy/infra), Vitest, Playwright | `D:\emergentsh_latest` |
| 2 | ★★★★★ | **Neon Architect v5.1 (Unified)** | Full-stack autonomous coding agent on NVIDIA NIM: tools, autopilot, SDLC phases, multi-pass app generation core, outer SDLC iteration wrappers, QA browser automation with pixel baselines | Python, NVIDIA NIM (GLM/Nemotron/Llama), httpx/openai, Playwright QA, modular engine architecture | `D:\neon_unified` |
| 3 | ★★★★★ | **OmniRoute Monetizer V1** | Idempotent ops/bootstrap layer over an LLM gateway: provider lifecycle state machine (DISCOVERED→VERIFIED), live-inference verification gates, routing pools, React dashboard, 295-provider verdicts | Python, Playwright browser automation, React/Vite/TS dashboard, evidence-based adapter policy docs, pytest | `D:\omniroute-monetizer` |
| 4 | ★★★★★ | **Voice Agent Clinic** | Production AI receptionist for dental/medical/HVAC/legal/real-estate: inbound voice, appointment booking, CRM handoff, web avatar — on a free/self-hosted stack | FastAPI, WebSocket bridge (ASR→LLM→F5-TTS), Gemini Flash, local Whisper, LivePortrait avatar on Kaggle GPU, Twilio + Cal.com, 1,289-case test suite | `D:\god_ai\voice_agent_avatar\voice-agent-clinic` |
| 5 | ★★★★☆ | **OpenPath** | "Open-source UiPath for web apps": natural-language test cases → AI detects stack, boots app, generates & runs test plan, HTML/JUnit reports from one command | Python, Playwright, LLM NL-test compiler w/ cache, stack detector, plan generator, pytest | `D:\nemo_test` |
| 6 | ★★★★☆ | **The Beholder / Life Archive** | "Complete digital life research and publishing platform": ingests a life's documents/media, knowledge store, AI-assisted authoring → produced 3 published KDP books | Python 3.11 async (SQLAlchemy/Postgres/asyncpg, Neo4j, Meilisearch, MinIO, Redis, Qdrant), OpenAI, PyMuPDF, Typer CLI, docker-compose | `D:\god_ai\the-beholder-project` |
| 7 | ★★★★☆ | **Codex NIM Proxy** | Transparent proxy letting OpenAI Codex CLI use NVIDIA's free top models (DeepSeek V4, Qwen3 Coder, Kimi K2.6): Responses API ↔ Chat Completions, SSE streaming, live model catalog web UI | Node.js/CJS, Express, SSE streaming, NVIDIA NIM | `D:\codex-nvidia-proxy` |
| 8 | ★★★★☆ | **GODSHAND Film Engine** | ComfyUI + WAN 2.2 I2V film engine for unattended Hollywood-grade output on Kaggle 2×T4: gated pipeline, VRAM governor, 4K upscale, forensic defect-fix audits | Python, ComfyUI API graphs, WAN 2.2/LTX, Kaggle notebooks, pytest suites, OOM/throttle tests | `D:\dev\antigravity-kandover` |
| 9 | ★★★★☆ | **FilmForge** | Zero-to-film pipeline: routes each shot to best open video model, fails over between GPU providers (Modal/Beam), stitches finished film; offline dry-run proves pipeline with no GPU | Python, Modal, ComfyUI, Wan 2.2 + LTX-2.3, ffmpeg | `D:\DOWNLOADS\filmforge` |
| 10 | ★★★★☆ | **OMEGA SOTA Agent** | Multi-domain action-taking orchestrator: agents, memory, reasoning, reflection, tools; multi-tenant FastAPI REST API with concurrent goals, CLI, Docker | Python, FastAPI, OpenAI/Anthropic SDKs, DAG scheduling | `D:\DOWNLOADS\OMEGA_SOTA` + `omega_agent` |
| 11 | ★★★☆☆ | **SafeScreen ML Pipeline** | Content-moderation model pipeline for screen safety: auto dataset generation, labeling, TFLite benchmarking, EAST INT8 builds (132 scripts) | Python, TensorFlow/TFLite, EAST OCR | `D:\DOWNLOADS\KUNALS LATEST PROJECTS\SafeScreen_ex` |
| 12 | ★★★☆☆ | **SafeScreen Guard (Android)** | On-device screen/audio profanity masking: screen capture service, toxic-text detection, ultra-low-latency audio beep masking, overlay UI | Kotlin, Android, TFLite/ML, MediaProjection | `D:\god_ai\screen_guard_final` |
| 13 | ★★★☆☆ | **Solana Hybrid Sniper Ultra** | Solana meme-coin trading bot: SNIPER/MG/HWR strategies, XGBoost ML composite scoring (65% rule + 35% ML), trailing stops, cyberpunk React dashboard | TypeScript/Express, React/Shadcn/Vite, Postgres+Drizzle, Python FastAPI ML (XGBoost), Jupiter/Helius RPC | `D:\DOWNLOADS\crypto-app` |
| 14 | ★★★☆☆ | **MemeTrade Terminal** | Meme-coin paper-trading platform: portfolios, bots, AI signals, backtesting, webhook alerts, live Solana swap via Jupiter, explicit risk-control layer | FastAPI + React + MongoDB, JWT auth, risk engine | `D:\DOWNLOADS\emergenttrader` |
| 15 | ★★★☆☆ | **Selenium QA Automation Suite** | 1,220-test WebDriver suite over a Flask demo app: Page Object Model, data factories, parallel xdist runs, HTML/JUnit reports, GitHub Actions CI shards | Python, Selenium, pytest-xdist, Flask, GitHub Actions | `D:\ideation_to_prototype` |
| 16 | ★★★☆☆ | **Claude Code Clone (Neon Architect v4.6)** | Single-file 5,592-line terminal coding agent on NVIDIA NIM: XML interceptor, smart compaction, token bucket, auto-nudge, self-healing streams | Python, NVIDIA NIM | `D:\god_ai\claude_code_clone` |
| 17 | ★★★☆☆ | **Convergence Framework** | Methodology + prompt framework: objective-function-first engineering for agentic systems, trading-bot convergence playbooks | Markdown methodology, prompt engineering kits | `D:\god_ai\convergence_framework` |
| 18 | ★★☆☆☆ | **Guardian App** | Parental control mobile app: child location, maps, notifications, activity charts, biometric lock | Flutter/Dart, Firebase, Google Maps | `D:\god_ai\guardian_app` |
| 19 | ★★☆☆☆ | **AI Video Monetizer** | Faceless-video monetization automation: Google Sheets/Drive content pipeline, AI video generation, deployment scripts | Python, Google Workspace APIs, OAuth | `D:\god_ai\ai_video_monetizer` |
| 20 | ★★☆☆☆ | **Solana Auto-Trader (live + AI variants)** | Solana auto-trading bot with market-condition scoring, auto-pause in bad markets, trending-token discovery, HWR signal engine | Python, Solana web3 | `D:\god_ai\solana-auto-trader-live` |
| 21 | ★★☆☆☆ | **SOL Maximizer** | Modular Solana earner: MEV triangular arb (Jupiter V6), staking optimizer, NFT floor arb, airdrop hunter, validator monitor | Python, Jupiter API | `D:\DOWNLOADS\solana_earner` |
| 22 | ★★☆☆☆ | **Smart LCM Frontend** | Enterprise React dashboard SPA with Azure AD (MSAL) auth, Redux Toolkit, charts, Dockerized/nginx deploy | React 18, TypeScript, Redux Toolkit, MSAL, Docker | `D:\DOWNLOADS\smart_lcm_frontend_react` |
| 23 | ★★☆☆☆ | **API Money Bot v3.0** ⚠️ | Automated account-signup/API-key acquisition across 34 platforms — **gray-area credential harvesting; do NOT showcase publicly** | Python, Playwright stealth, 2Captcha | `D:\god_ai\api_money_bot_complete` |
| 24 | ★☆☆☆☆ | **CRM App** | Minimal contacts CRM — tutorial-grade demo | React, Express, MongoDB | `D:\DOWNLOADS\crm-app-20260606-105900` |

## Top 6 Shortlist + Resume Bullets

**1. Emergent Platform — Agentic App-Builder ★★★★★**
- Architected an end-to-end agentic software platform (Next.js IDE + 8 TypeScript microservices: sandbox, VFS w/ git semantics, WebSocket event streamer, MCP server, deploy/infra) where AI agents build and iterate on real web applications autonomously.
- Built an autonomous QA service (Playwright) performing visual regression, DOM/console/a11y checks, and automated bug fixing inside the agent loop.
- Designed for production: contract-tested services (Vitest), device emulation, session streaming with heartbeat/reconnect.

**2. Neon Architect v5.1 — Autonomous Coding Agent ★★★★★**
- Led development of a unified agentic SDLC engine: interactive coding agent (tools, autopilot, SDLC phases) + multi-pass generation core + outer iteration wrappers that self-evaluate and repair across cycles.
- Integrated NVIDIA NIM model routing with self-healing streams, context compaction, and token-budget governance; QA loop uses Playwright with pixel baselines.
- Proven by artifacts: the agent generated the Flutter/FastAPI/Next.js apps found in sibling sandboxes.

**3. OmniRoute Monetizer — LLM Gateway Ops ★★★★★**
- Engineered an idempotent monetization/ops platform for a multi-provider LLM gateway: explicit provider state machine (DISCOVERED→VERIFIED/DEAD/COOLDOWN) where no route enters production pools without live-inference evidence.
- Ran verification across 295 providers with automated capacity/runway reporting, performance baselines, and regression RCA documentation.
- Enforced "evidence-backed adapter" policy — selectors promoted only from observed DOM, eliminating hallucinated automation.

**4. Voice Agent Clinic — AI Receptionist Infrastructure ★★★★★**
- Shipped production voice-AI infrastructure for five verticals: WebSocket bridge (ASR→LLM→F5-TTS), FastAPI webhook server (Twilio + Cal.com validation), knowledge cache, and a LivePortrait web avatar — on a zero-cost/self-hosted stack.
- Authored a 1,289-parameterized-test release gate (PII, injection attempts, webhook contracts) plus widget CI and compose validation.
- Provider-agnostic fail-safe design: paid providers disabled unless explicitly opted in.

**5. OpenPath — AI-Native Test Automation ★★★★☆**
- Created an open-source RPA alternative: natural-language test cases compiled by LLM (with caching), automatic stack detection, server boot, generated smoke/auth/CRUD suites, rich HTML/JUnit reporting from a single command.
- Dual-runner architecture: deterministic Playwright execution + AI runner for exploratory coverage.

**6. The Beholder / Life Archive ★★★★☆**
- Built a personal digital-life research & publishing platform: multi-store ingestion (Postgres, Neo4j graph, Meilisearch, MinIO, Redis, Qdrant vectors), privacy/hashing layers, connector framework, and an automated book-builder that produced three published KDP titles end-to-end.

## Skipped (dead/backup/junk)
gpt_terra, real, raw_uncompiled, morning-sprint-20260810, DOWNLOADS\sale, empty SafeScreen shells, god_ai\ikon_agent-main (n8n clone), test_coding_agent (testbed), OMEGA variants, all *_BACKUP/-Copy/chrome-profile/node_modules dirs, Solana_ex/SafeScreen_lite duplicates.
