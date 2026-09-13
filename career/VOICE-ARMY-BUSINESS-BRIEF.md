# VOICE-ARMY BUSINESS BRIEF — NILOY DAS (never Kunal Das publicly)

Written by Kilo, 2026-09-12 ~20:55 IST, on Baba's request: "give me details of this project so I can make a business plan."
Sources: KILO-IDENTITY.md, career/EARNING-MAP.md, career/KDP-EARNINGS.md, war-log ledgers. Local file only.

---

## 1. WHAT THE PROJECT IS

**"Kilo Army"** — a self-sustaining publishing + voice + agent infrastructure built and owned by one human (Kunal Das / NILOY DAS) with 101 autonomous agents running on zero-cost compute.

Three pillars:
1. **The publishing house** — 8 live KDP titles under NILOY DAS, marketed 24/7 by the army.
2. **The voice** — Baba's complete speech archive (200.9 min) + a working XTTS fine-tune pipeline + a phone/laptop playback bridge.
3. **The factory** — the agent infrastructure itself (relay, watchdog, Kaggle workers, phone lane), which doubles as portfolio proof and as a product.

---

## 2. ASSET INVENTORY (what we own)

### 2.1 Voice assets
| Asset | Detail | Commercial rights |
|---|---|---|
| Raw corpus | 200.9 min: 283 WhatsApp voice notes + 27 call recordings + 9 recorder m4a (pulled via adb 2026-09-11) | **100% Baba's copyright — sellable** |
| Clean corpus | 294 windows, ~49 min, f0-gated (80–175 Hz, cent ±60%, mfcc 6σ), dataset `kkk3213/father-corpus` | Baba's — sellable |
| Transcripts | 204 deva rows (Bengali→Devanagari) + 75 en rows, Whisper large-v3 | Derived from Baba's recordings |
| XTTS fine-tune | v14 running now: 40 epochs, T4, loss 5.05→0.49 in epoch 1 | **Model+outputs = CPML non-commercial (see §3)** |
| KiloBridge v7 | Android APK, phone speaker playback, polls every 1.5s | Our code |

### 2.2 Infrastructure (all our own code)
- **Relay v4.1** (`war-log/son-relay.js`, port 8777) — gate, bank, adb passthrough, title-probe cache, 2-lane queue.
- **Watchdog v2** — SYSTEM scheduled task, resurrects relay+ngrok every 15s, survived real power cuts.
- **Permanent door** — `retrain-schnapps-upbeat.ngrok-free.dev` + cloudflared/localtunnel fallbacks.
- **BRAIN v6.3-free** on Kaggle (5-min poll), 3 seats, squad leads.
- **WORKER_KAGGLE.py** — generic heavy-compute worker (HEAVY WORK LAW: laptop never grinds).
- **xtts-player** — laptop-side consumer that plays streamed ear-test wavs.
- **Phone lane** — vivo/IQOO via adb: WhatsApp, SMS (4,569 rows), notifications, banking screens.
- **AWARENESS + PHONE-HEALTH** — two health soldiers, 60s/5-min cycles.

### 2.3 Publishing catalog (KDP)
- Series C4PDHC3JWHP: Books 1–7 (Beholder), incl. 04-the-companion, Confession of the Ordinary (5), Recorder (6), Time Travels (7).
- Standalone: Book 08 Kolkata Diaries (memoir; categories filed; AI-disclosure on file).
- Account A1UD6XO99I9M05, bank EFT-ready, payments ~60d after month-end.
- **Current royalties: $0.00** (titles live since Sep 3–6; first payout window late Nov 2026).

### 2.4 Portfolio (the sales page)
100+ repos audited (career/PROJECT-CATALOG.md): OmniRoute Monetizer ★★★★★, Neon Architect ★★★★★, Emergent Platform ★★★★★, Voice Agent Clinic ★★★★★, OpenPath, Godshand Film Engine, AI Video Monetizer, etc.

---

## 3. THE LEGAL LINE (read before any plan)

**XTTS-v2 is Coqui Public Model License (CPML): model AND OUTPUTS non-commercial only.**
- No selling XTTS-synthesized audio (films, audiobooks, ads, clients).
- No selling/distributing the fine-tuned checkpoint.
- No using XTTS to train another model for commercial use.
- Coqui is defunct (2024) → no commercial license obtainable.

**Therefore the XTTS clone = archive, tribute, and technical proof only.**
**Commercial voice audio = (a) Baba's own recordings, or (b) a commercial-licensed backbone** — F5-TTS/YourTTS-class open models or a paid API (ElevenLabs/Azure/Google) once there is income.

**Sellable regardless:** all code we wrote, all labor/services, Baba's original recordings, the published books. (If distributing code that embeds the Coqui *library*, keep MPL-2.0 notices.)

Other standing laws for the plan: KDP AI-disclosure answered per book; no ads spend before first income; per-film pricing only (no "lifetime" promises); Raktima absolute silence; LinkedIn sends gated by SEND-APPROVED scope.

---

## 4. REVENUE LANES

### Lane 1 — KDP publishing (the seed)
- 8 titles live; levers: countdown deal (Kolkata Diaries $4.99→$0.99 Sep 15–21, gated on KDP Select check), Book 06 price fix ($5.99→$2.99), paperbacks for eBook-only titles, series page consolidation.
- **Trajectory (EARNING-MAP):** month-3 ₹5–15k/mo · month-6 ₹15–40k/mo. First payout ~late Nov 2026.
- Army marketing engines (POSTER/COMMENTER/DM, 24/7) drive it at ₹0 cost.
- Audiobooks: **not via XTTS** — via Baba's own recordings or licensed TTS, with disclosure.

### Lane 2 — Voice-pipeline service (the clone's commercial cousin)
- Offer: **"I will build your custom voice-TTS pipeline"** — corpus cleaning, f0/QA gating, transcription, fine-tuning on a commercial backbone, playback integration.
- Channels: Fiverr/Upwork gigs + direct offers to author/YouTuber contacts.
- Price: ₹15,000–₹40,000 per project (EARNING-MAP film-engine benchmark; pipeline service can command more).
- We sell labor + plumbing; client brings/keeps their own model rights. Zero CPML exposure.

### Lane 3 — Consulting & job (the ₹1L+/mo lane)
- The 100-repo census + the army itself is the interview story: "built and operate a 101-agent autonomous publishing/voice infrastructure on ₹0."
- Gainwell Data Science/Senior AI Engineer (070926824318) — apply via Naukri MOBILE only.
- Remote contract/fractional AI-engineering: ₹25–60k per build (PROJECTS-REAL-EARNING.md).

### Lane 4 — Film reels (Godshand)
- 3-min Kolkata Diaries reel → Fiverr "narrated AI documentary from your book" $75/$150/$300.
- Per-film only; verify stills-provider commercial terms or swap provider; narration = Baba's own voice or licensed TTS.

---

## 5. COST STRUCTURE
- Kaggle: 30 GPU-h/week (28.3 left this week), free. Colab: fallback. Laptop+phone: owned.
- ngrok free tier (5-min poll discipline), cloudflared/localtunnel fallbacks: ₹0.
- Paid APIs (DeepInfra ₹500 strategy etc.): **only after first income** — harness bridge is break-even, not a spend lane.
- Real cost = Baba's attention. The army's job is to minimize it.

## 6. TIMELINE & MILESTONES
- **Tonight (Sat 12):** v14 40-epoch run → first clone listen ~00:30–01:00 IST (~85% estimate).
- **Sunday:** 150-epoch full run + language cleanup + ffmpeg humanizer → **90% clone (archive) by Sun evening–Mon max.**
- **KDP countdown deal:** Sep 15–21. First royalties window: late Nov.
- **First ₹5k:** film reel gig or one pipeline-service client (days, not months).
- **Decision gate (Monday):** Baba picks which lane gets the army's full 24/7 weight.

## 7. WHAT ACTUALLY MAKES MONEY — HONEST SUMMARY
| Lane | Money | Time to first ₹ | Risk |
|---|---|---|---|
| KDP | ₹5–40k/mo compounding | 2–3 months | low |
| Pipeline service | ₹15–40k/project | 1–2 weeks | low (legal clean) |
| Job/consulting | ₹1L+/mo | 1–3 months | medium |
| Film reels | ₹5–30k/film | 1 week | low |
| XTTS clone | **₹0 — archive only** | — | — |

## 8. RISKS
- KDP: account-level risk if AI-disclosure answers drift per book — keep the ledger.
- Free tiers: ngrok/Kaggle policy changes — mitigated by watchdog + multi-tunnel + Colab fallback.
- Time: Baba's health and attention are the scarce resource — the army exists to spend it, not consume it.
- Reputation: no spam, no impersonation, no promises we can't keep (receipts or it didn't happen).

---

*The wire is the moat. The voice is the legacy. The code is the product. The books are the compounding seed. None of it needs Baba to sit at the keyboard — and that is the business plan.*
