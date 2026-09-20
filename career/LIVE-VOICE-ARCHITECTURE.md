# LIVE INTERACTION INFERENCE ENGINE — ARCHITECTURE NOTE

Noted by Kilo, 2026-09-13 ~19:19Z, on Baba's request ("keep a note of the live interaction inference engine architecture").
Design agreed with Baba 2026-09-13 (session ses_f6a32a13bffeKW68yMEc3AC709). Local file only.

---

## 1. THE PATTERN — session-per-call, attended, auto-kill

Live XTTS interaction (phone-call feel) runs as **one attended Kaggle session per call, killed when the call ends.** No always-on GPU cost, no idle burn, no fragile 24/7 keep-alive.

Flow, top to bottom:

1. **Pre-warm (the trick).** Cold start — session boot + pip + 1.7GB checkpoint load ≈ 2–3 min — must happen *before* the call, never during. Baba opens the `kilo-voice-live` notebook: it loads the model, then sits in a **polling loop** (NOT a one-shot script) waiting on the relay queue for a call to arrive.
2. **Call arrives.** Relay v4.1 (`war-log/son-relay.js`, port 8777, permanent door `retrain-schnapps-upbeat.ngrok-free.dev` + cloudflared/localtunnel fallbacks) hands the session the incoming call handle.
3. **Streaming synthesis.** Text in → XTTS-v2 streams **chunks** out over the websocket bridge pattern (skeleton already in portfolio repo `Voice-Agent Clinic/websocket_streaming_xtts.py`). First chunk out fast, the rest fills gaps — this is what makes it feel like a call, not a render.
4. **Baba hears it.** Phone/laptop ear bridge: KiloBridge v7 APK (1.5s poll) / xtts-player consumes the streamed wavs.
5. **Call ends → session killed.** GPU hours stop exactly when the conversation stops. Auto-cancel discipline, never left running.

## 2. FLEET MATH (per week, ₹0)

| Lane | Compute | Role |
|---|---|---|
| Kaggle live | 3 seats (kkk3213 / n42888 / kdas19999) × 30 GPU-h = **90 GPU-h** | 150 half-hour calls, or up to 3 warm live seats at a time |
| Colab batch | 6 seats × ~25–30h T4 ≈ **160 GPU-h** | batch lane only — transcription, corpus jobs (4h idle-disconnect + serial GPU assignment make it unfit for live) |

The wall is logistics (Baba opening sessions on request), not compute. Kaggle-first / Colab-second order per standing law.

## 3. LATENCY MEASUREMENT — in progress

`kilo-xtts-infer` v1 (dual-T4 gate, fp16 load, streamed chunks) launches as soon as the `father-xtts` dataset upload (841MB fp16) lands. It outputs the **measured first-chunk and steady-state synthesis latency** per word — that number decides whether the free-tier loop feels like a call or a voicemail. Result goes into VOICE-ARMY-BUSINESS-BRIEF.md §6.

## 4. PAID UPGRADE PATH (only after first income)

If the free-fleet loop doesn't hit call-feel: persistent GPU ($0.5/hr RunPod-class) + always-on websocket bridge — that is the true real-time architecture; free Kaggle fleet is the bootstrapped version of it.

## 5. LEGAL BOUNDARY (standing)

- Live XTTS interaction = **CPML non-commercial** → family archive / tribute / demo only. No monetized calls, no client use.
- Commercial real-time voice = same engine rewired onto a commercial-licensed backbone (F5-TTS/YourTTS-class or ElevenLabs/Azure once income exists). The pipeline, relay, bridge, and fleet discipline are ours and sellable (Lane 2 of the brief).

---

*One call, one session, one kill. The fleet is the phone company; the relay is the switchboard; the model is the voice; none of it idles.*
