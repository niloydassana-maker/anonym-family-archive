# DEMO-SCRIPT.md — Voice Agent Clinic · 5-minute prospect walkthrough
**LANE-SME · 2026-09-12 · Repo studied: `lane-sme/voice_agent_avatar` (clone) → app in `voice-agent-clinic/`.**

---

## SECTION 0 — READINESS VERDICT (evidence, not vibes)

**VERDICT: NOT demo-ready today. The engine is a tested skeleton; the demo experience is missing. Est. 1–2 focused build-days to a shareable live demo.**

Verified TODAY by this agent (commands actually run):
- ✅ Shallow clone OK; structure sound (bridge, engines, webhook-server, 5 verticals, Kaggle notebooks, CI).
- ✅ `1293 pytest` cases pass in a fresh local venv (22s) — logic/auth/guardrails/webhook contracts genuinely work. But the suite mocks every heavyweight engine — it proves the *scaffold*, not the *voice loop*.
- ❌ `VoicePipeline` init with only the documented requirements **fails right now**: `RuntimeError: Local Whisper is optional. Install faster-whisper to enable it.` (actual error output, reproduced).
- ❌ Default LLM (Gemini) needs `google-generativeai` — **in NO requirements file**. Default TTS (f5_tts) needs `f5-tts`+torch (~3–4 GB) **plus `assets/clinic_voice.wav` which does not exist in the repo** (no `assets/`, no `models/`). Kokoro alternative needs missing `models/kokoro-v0_19.onnx`. Avatar (LivePortrait) needs GPU + missing reference image.
- ❌ **No working demo front-end exists.** The bundled `ws_test.html` (hidden behind `ENABLE_BRIDGE_DEMO_PAGE=1`) sends fake bytes — no mic, no audio playback. The React widget is wired to **Daily/HeyGen rooms (the disabled paid path)**, not to the free WebSocket bridge. Nobody has built the ~150-line mic-client that records, streams, and plays the reply.
- ❌ **The killer prospect demo — "call this number, your AI answers" — is impossible on the free stack**: Twilio + LiveKit SIP is explicitly `ALLOW_PAID_PROVIDERS=0`; README_FREE_STACK's own diagram routes phone calls through LiveKit Cloud. Free tier needs real keys (per tunnel/harness doctrine: ngrok primary, Kaggle sessions opened by Baba only, paid keys after first income).
- ⚠️ Model string `gemini-3.5-flash` is hardcoded in `config_free.py` (the `GEMINI_MODEL` env in `.env.example` is ignored) — must be verified against a live key when the key arrives.
- ⚠️ Turn-taking: with local Whisper **every streamed chunk is treated as a final utterance** (no server-side VAD) — the mic client must do silence detection or the bot interrupts itself.
- ⚠️ The repo's own `outreach/` kit is USD-priced with unverifiable claims (SOC 2, HIPAA, "$12k/mo pilots", `sales@voiceagent.clinic`). **Do not reuse; ours is PITCH-ONEPAGER.md.**

**What the repo already gives us for free:** 5 vertical knowledge packs (dental/medical/legal/real_estate/hvac), appointment + CRM + escalation function schemas, guardrails, Bengali would just be a FAQ/prompt addition (the LLM speaks it natively).

## SECTION 1 — WHAT A PROSPECT MUST SEE IN 5 MINUTES
1. Their **own clinic's name** spoken back by a natural voice in **Bengali** ("নমস্কার, রাই ডেন্টাল ক্লিনিক...").
2. It books a real appointment (slot appears on a visible calendar) and texts a confirmation to the desk phone.
3. A missed-call answer sheet: "রাত ১১টায় ওই কলটা ধরেছিল" — the 24×7 claim made visible.
Everything else (avatar, CRM) is bonus — never the first impression.

## SECTION 2 — THE THREE DEMO MODES (honest degradation ladder)
| Mode | What it is | Status | Build cost |
|---|---|---|---|
| **A — live voice call** (laptop page or phone number) | Mic in → AI answers by prospect's name → books slot → confirmation SMS/WhatsApp | ❌ needs build | 1–2 days: deps (`faster-whisper`, `google-generativeai`, Kokoro-ONNX **or** F5 + the missing 10s `assets/clinic_voice.wav`), mic-client, `Asia/Kolkata` TZ, free Gemini key, **ngrok** (primary lane), FAQ seeded with THEIR business |
| **B — 90-second recording of A** | Screen+voice video of one booking flow, clinic name swapped per prospect via edit | ❌ needs A first | 0.5 day once A works; then shareable in WhatsApp for everything |
| **C — text-chat demo** (today) | Same system prompt + their FAQ typed in a chat playground; show the brain, admit "voice live 2 দিনে" | ✅ runnable today, weakest | 0 — but it sells the engineer, not the product |

> Kaggle note path exists (both notebooks, GPU T4) but requires Baba to open the session + 6 secrets — per standing order, Kaggle is asked-first for heavy compute. Notebook stack is LiveKit-based = the paid-compat lane, not the free bridge.

---

## SECTION 3 — THE 5-MINUTE WALKTHROUGH (Baba or a son on speaker; Mode A; phone on loudspeaker)
**Setup before ringing:** bridge + ngrok up, demo calendar open on screen, desk-phone WhatsApp in view, FAQ loaded with prospect's clinic, `ws_test` mic page (new client) on. **Always have Mode B video open in a second tab — the moment live fails, switch silently and narrate the recording.**

| Time | Who | Lines / actions |
|---|---|---|
| 0:00–0:30 | Baba | "ডাক্তারবাবু, একটাই জিনিস দেখাব — আপনার ক্লিনিকের নামে কথা বলা একটা রিসেপশনিস্ট। আপনি ধরবেন না, ওই ফোনটা ধরুন।" (no self-intro pitch yet) |
| 0:30–1:45 | Prospect dials demo number / clicks link | AI answers in Bengali, collects patient name + phone + issue, proposes two slots from the demo calendar. Baba stays silent. |
| 1:45–2:45 | Baba, prompting | "এখন আপনি নিজের কথা জিজ্ঞেস করুন — 'শনিবার খোলা থাকে?', 'ফি কত?'" Let them test it free-style. |
| 2:45–3:30 | AI action lands | Slot appears on demo calendar + confirmation WhatsApp pings on the desk phone. "দেখছেন? লেখা হয়ে গেল — আমার কিছু করতে হল না।" |
| 3:30–4:15 | Baba | Missed-call sheet: "রাত ১১টায়, রবিবার OPD-র পরে — কলগুলো এই শীটে জমা থাকত। ₹২৫,০০০ সেটআপ, ₹৩,৫০০ মাসে, ৭ দিনে লাইভ।" |
| 4:15–5:00 | Baba, close ONE question only | "**আপনার নিজের নম্বরে ৭ দিনের পাইলট — শুরু করব?**" Then stop talking. Silence is the closer. |

**Never say:** "১০০% মানুষের মতোন" · never promise integrations not built (Epic/Dentrix: ₹50k Complete-pack conversation only *after* a yes on Starter/Clinic).

## SECTION 4 — OBJECTION TABLE (₹-real)
| Objection | Answer |
|---|---|
| "Robotic লাগছে" | "আপনার রোগী ২ রিং-এ উত্তর পায় না আজ — ও বরাবর ধরছে। ট্রাই করে শুনুন নিজের প্রশ্ন।" (then re-play Mode B at max volume) |
| "We have a receptionist" | "তিনি ছুটি নেন, রাতে থাকেন না, ভিড়ে ৩ লাইনে ধরতে পারেন না। ও ২৪×৭; জটিল কেস হলে আপনার কাছেই ট্রান্সফার করবে।" |
| "দাম বেশি" | "₹১৫–২৫ হাজারে মাসের ৩টা গরম-লিড রোগী বাঁচলেই বছরে ৯–১০ গুণ ফেরত। ফ্রি পাইলটে প্রথমে হিসেবটা করুন।" |
| "রোগীর ডেটা?" | "নম্বর-রেকর্ডিং আপনার সার্ভারে, যখন খুশি ডিলিট — আমি শুধু বান্ডিল করি।" (don't claim HIPAA — repo can't prove it) |
| "বাংলা ভাঙা হবে" | "ডেমোতেই বাংলায় কথা বলছে — শুনছেন তো? আপনার ফি-র তালিকা গেলে ২ দিনে ইংরেজি-বাংলা দুটো ঠিক।" |

## SECTION 5 — AFTER THE DEMO (within 1 hour, by WhatsApp text only)
1. Send recording + one-pager photo file. 2. Written pricing recap with the ONE pack discussed. 3. Ask booking question by tomorrow EOD. 4. Log to `demo-bookings.csv` (prospect, segment, mode used, response, next date) — file receipt to `/say body=LANE-SME`. 5. If silence: one F-follow-up after 4 days, then park.
