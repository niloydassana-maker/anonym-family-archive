# %% [code]
# %% [code]

# %% [code]
# KILO-VOICE-LIVE v103 (Recorded Male XTTS Voice Opener + Strict Male Clinic Persona + Silence Collapse 80ms + Speed=1.35 Locked)
# Forensic Architecture (Baba's Law, 2026-10-04 03:20 IST):
#   LAPTOP vs PHONE DISCREPANCY ROOT CAUSE:
#     - /say on laptop synthesized the ENTIRE natural sentence in one pass -> perfect prosody, pronunciation, punctuation.
#     - /turn on phone previously chopped sentences into tiny 24-char fragments via SpeechChunker to chase latency,
#       but destroyed XTTS Hindi conjunct pronunciation, pitch contour, and natural cadence.
#   THE PERMANENT RESOLUTION:
#     - FILLER_ON=1 plays instant pre-cached "जी, एक मिनट।" at ~800ms (lasting 4.92 seconds).
#     - During those 4.9 seconds, XTTS synthesizes the WHOLE sentence in one clean pass (~2.4s) on dual GPUs.
#     - Perceived latency stays at ~800ms; speech quality matches the crystal-clear laptop benchmark 1:1.
# Also still serves scripted LIVE_CALL orders. Pre-warms XTTS on a T4, polls the relay for LIVE_CALL / HEAR / AUTO_* orders,
# stream chunk wavs home, log per-chunk latency to latency_log.jsonl, auto-kill when idle so Kaggle quota stops.
# Law 15: hardware gate first. HEAVY WORK LAW: synthesis never touches the laptop. DEVA LAW: bn has no XTTS lane - hi-deva IS Baba's tongue.
#
# v42 = v41 + (1) hang-up handling (no BrokenPipe tracebacks, LLM stream and GPU work stop when the caller leaves),
#       (2) self-check fixed (NameError: requests), (3) LATENCY PROBE: every hop of a voice turn is timed,
#       returned in the /turn trailer, logged to latency_log.jsonl, served at GET /lat, and a boot-time probe
#       (components -> loopback turn -> tunnel turn) writes probe_report.json. Order "PROBE" re-runs it live.
import os, re, io, glob, json, time, base64, shutil, subprocess, sys, threading, queue, urllib.request, urllib.parse, concurrent.futures
import socket, statistics, collections
import http.server
import socketserver
from contextlib import nullcontext

RELAY_URL = os.environ.get("RELAY_URL", "https://traveling-carlo-fine-breeds.trycloudflare.com")
RELAY_FALLBACKS = [c.strip() for c in os.environ.get("RELAY_FALLBACKS", "https://kennedy-til-defend-artistic.trycloudflare.com,https://retrain-schnapps-upbeat.ngrok-free.dev").split(",") if c.strip()]
RELAY_TOKEN = os.environ.get("RELAY_TOKEN", "GOLD24")
SELF_BODY = os.environ.get("SELF_BODY", "LIVE-VOX1")
OUT_BODY = os.environ.get("OUT_BODY", "KILO")
# v58 (Baba, 2026-10-03): "D:\anonym\realhindivoice this is your reference voice" ... and then, when the
# trade-off was laid out plainly, "keep this one only". So the reference is the ElevenLabs clinic voice
# and father.wav is OUT -- not an extra A/B leg. The father-voice dataset was dropped from
# kernel-metadata.json so the fallback can never silently pick an old clip back up.
# Verified by hash, not by the upload's exit code: local reference_clean.wav and the copy now in
# isearchxsolve/clinic-reference-voice both hash to
#   9C28F6F261041D9D6799E58707AA7CD2D0BF2F7AA83907B8CFAE8957E220381F
# The kernel resolves the stem "clinic_reference" out of /kaggle/input, and GET /say?probe=1 prints the
# full path it actually loaded, so the swap is checkable rather than assumed.
# v63 (Baba, 2026-10-03): "the voice is different, the one i gave was deeper voice i want that".
# MEASURED, not assumed. Two recordings arrived under the SAME filename, so they were told apart by
# fundamental frequency (median f0 over voiced frames, autocorrelation):
#     reference_clean.wav        <- the 02:42 clip  -> 133 Hz  = THE DEEPER VOICE  (what he wants)
#     clinic_reference_faster.wav <- the 09:09 clip  -> 160 Hz  = lighter, 27 Hz higher (17.1%)
# So the 02:42 take was BOTH deeper and slower; the 09:09 take was a different, lighter voice. Baba's
# word is the deeper one, so the reference goes back to it -- and pace is fixed by XTTS's own speed
# factor instead of by swapping the voice out, which is what caused this whole detour.
# It is not lost: the deep clip survives as clinic_reference.wav in the Kaggle dataset and in
# D:\anonym\RESCUE-kaggle-reset\ (hash 9C28F6F261041D9D6799E58707AA7CD2D0BF2F7AA83907B8CFAE8957E220381F).
VOICE_REF = os.environ.get("VOICE_REF", "clinic_reference.wav")
# NOTE: plain LANGUAGE is a Linux locale variable (Kaggle sets it to "en_US"), so it must not be used here.
LANGUAGE = os.environ.get("KILO_LANG", "hi")

# ---- polling: adaptive. Fast while a conversation is live, slow when idle. ----
POLL_SEC = float(os.environ.get("POLL_SEC", "2"))              # idle poll period
POLL_HOT_SEC = float(os.environ.get("POLL_HOT_SEC", "0.35"))   # poll period while hot (cuts ~1 s average pickup lag)
HOT_WINDOW_SEC = float(os.environ.get("HOT_WINDOW_SEC", "600"))  # stay hot this long after the last order
HEARTBEAT_SEC = int(os.environ.get("HEARTBEAT_SEC", "60"))
# v39 (Baba 2026-10-02): "keep it alive for 2 hours". The seat must survive an unattended stretch so the
# direct voice tunnel stays up and the phone can call it whenever the demo happens. IDLE_KILL_MIN was 10
# minutes, which killed the kernel before a caller ever dialled in (first proof run: IDLE_KILL at gpu_s=600
# with the tunnel healthy the whole time). HARD_CAP_MIN sat at 120 = the same moment as the old idle kill, so it
# is lifted clear of it; Kaggle allows 12 h, so 175 min leaves an hour of headroom over the 2 h request.
IDLE_KILL_MIN = float(os.environ.get("IDLE_KILL_MIN", "120"))
HARD_CAP_MIN = float(os.environ.get("HARD_CAP_MIN", "175"))

# ---- synthesis ----
# v61 DIAGNOSTIC INSTRUMENT -- this is a probe, NOT a fix. Read the reasoning before changing anything.
#
# MEASURED FACTS that change the diagnosis:
#   v59 asserted on the second /say call. v60 asserted on the second /say call. v60 was a BRAND NEW
#   kernel version = fresh container, fresh process, fresh GPU allocation. So the assert is
#   REPRODUCIBLE FROM COLD -- it is not stale session state. That is also why a Kaggle "factory
#   reset" cannot help (Baba tried, 2026-10-03): factory reset IS a cold start, and cold is exactly
#   where it already fails.
#
#   And "first call works, second fails" is the WRONG reading. The boot A/B block synthesises THREE
#   clips (/ab_ref, /ab_builtin, /ab_english) before /say is ever served, so the first /say is already
#   the FOURTH inference. The real pattern is a fixed COUNT of inferences and then death -- the
#   signature of a state or memory leak, not of a bad reference. It happened on three different
#   references (father.wav, clinic_reference_fast, clinic_reference_faster).
#
#   NOTE: §62.6's "seat_first_pcm=-1, trailer straddles two socket reads" is a SEPARATE known gap.
#   Do NOT go and "fix" that while chasing this.
#
# WHY EACH KNOB IS HERE:
#   CUDA_LAUNCH_BLOCKING=1   makes the assert report AT the failing launch instead of at some later
#                            API call, so we finally learn WHICH kernel dies.
#   torch.cuda.synchronize() forces the error to surface inside the call that caused it, instead of
#                            being silently deferred to the next one.
#   torch.cuda.empty_cache() between calls, to test the memory-leak reading directly.
#   SELFTEST_N               eight SEQUENTIAL syntheses logged one by one. The index at which it dies
#                            IS the diagnosis.
#   Errors are CAUGHT so the run continues -- one death must not hide the pattern behind six 500s.
import os

# v61: CUDA_LAUNCH_BLOCKING must be set BEFORE torch initialises CUDA, and it must be the real `os`
# module -- the first draft of this block used `_os` with no `import os as _os` anywhere in the file,
# so the kernel died with a NameError at boot and the whole instrument never ran. My own bug, found
# by reading the imports rather than assuming they were there (§62.6's boot-order lesson again).
DIAG = os.environ.get("KILO_DIAG", "0") == "1"   # 1 = the v61 instrument (blocking launches, empty_cache, self-test)
# v66 -- handed to Claude for the latency pass. READ THIS BEFORE EDITING (Baba, 2026-10-03).
#
# 1. VOICE IS SETTLED. DO NOT TOUCH THESE. Baba's ear, 2026-10-03, on the rendered samples:
#       SPEED        1.00   "the 1x sample is perfect speed and voice"  -> this is the DEFAULT now
#       TEMPERATURE  0.65   v64 raised it from 0.4 (0.4 gave flat, slow delivery)
#       VOICE_REF    clinic_reference.wav  (the DEEP 133 Hz take; the 160 Hz take is rejected)
#       SYNTH_MODE   full   (stream was tried and REVERTED -- it pads and drifts out of language)
#       OUT_SR       0 = native 24 kHz (a 16 kHz experiment cost the brightness and intelligibility)
#    Anything that changes how the voice is GENERATED must be proven by rendering the same
#    sentence and letting Baba listen. Latency is bought in the pipeline, never in the synthesis.
#    "I cannot deliver a compromised product. I have a matter of reputation."
#
# 2. THE NUMBER THAT MATTERS IS PHONE_FIRST_AUDIO. The kernel's own first_pcm_ms is NOT it.
#    Measured on the handset: 7442 ms -> 3719 ms after the phone began streaming PCM into
#    AudioTrack as it arrived. A server-side number is never a latency claim. Quote the phone clock.
#
# 3. WHAT IS ALREADY DONE, so it is not re-done or undone:
#    - streaming AudioTrack on the phone; server sends raw PCM (header line, PCM, {"end"} trailer)
#    - cross-host LLM failover: 8 measured-good NVIDIA keys, then OpenRouter (IP-level throttle escape)
#    - brain = nvidia/nemotron-3-super-120b-a12b (567 ms, cleanest Hindi of 10 models measured)
#    - relay /say bank fixed to append-only + debounced snapshot (was rewriting 70 MB per POST)
#    - VAD 70/40 measured against the real room, 6 s upload cap, 450 ms hang
#
# 4. KNOWN OPEN GAPS (honest list, measured, not speculation):
#    - seat_first_pcm is -1 on some turns: the {"end"} trailer straddles two socket reads and the
#      phone-side parse does not buffer across reads
#    - the phone still uploads the whole captured utterance before the reply starts
#    - echo: some turns transcribe the phone's own speaker ("apunṭmaṇṭ" repeated in `heard`)
#
# 5. THIS COPY HAS NO KEYS. Every provider key literal was replaced by its NAME
#    (NVIDIA_KEY_00..07, OPENROUTER_KEY_00..01) and the real values are read back at runtime
#    through _secret() -> os.environ -> Kaggle Secrets. Do not paste real keys back into the source.
os.environ["CUDA_LAUNCH_BLOCKING"] = "1" if DIAG else "0"
SELFTEST_N = int(os.environ.get("SELFTEST_N", "8" if DIAG else "0"))
SELFTEST_TEXT = ("नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। मैं क्लिनिक की आवाज़ हूँ। "
                 "बताइए, मैं आपकी क्या मदद कर सकता हूँ?")
SPEED = 1.35    # Baba Law (2026-10-04 02:02): "speed should always equal 1.35" — crisp, confident, brisk clinic receptionist voice
#   # v66 (Baba 2026-10-03): "the 1x sample is perfect speed and voice". MEASURED on v64: 1.00 -> 7.75 s, 1.05 -> 7.56 s, 1.10 -> 7.15 s (same sentence, deep clinic_reference.wav). 1.00 is the default; ?speed= is still honoured for ear tests.
SPEED_UNSUPPORTED = {"yes": False}
GPT_COND_LEN = float(os.environ.get("GPT_COND_LEN", "10"))
GPT_COND_CHUNK = float(os.environ.get("GPT_COND_CHUNK", "6"))   # v64: must be <= GPT_COND_LEN
MAX_REF_LEN = int(os.environ.get("MAX_REF_LEN", "30"))
SOUND_NORM_REFS = os.environ.get("SOUND_NORM_REFS", "1") == "1"
HF_SHELF_DB = float(os.environ.get("HF_SHELF_DB", "0"))         # v64: try 2-3 if the voice still sounds dull
HF_SHELF_HZ = float(os.environ.get("HF_SHELF_HZ", "4000"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.65"))   # v64: 0.4 gave flat, slow delivery (XTTS default 0.75)
WARM_UP = os.environ.get("WARM_UP", "1") == "1"
# v45 STREAMING (Baba's 1-2 s order, 2026-10-02). Measured on this kernel from v44's own /lat endpoint:
#   stt 270 | llm_to_first_piece 2,169 | tts_gen 2,146-4,122 | stall 2,571 | first answer 6,112 ms.
# inference_stream() yields ~80 ms of audio WHILE it generates, so the caller hears after the first latent
# instead of after the last. Same model, same weights, same speaker embedding -- only WHEN bytes leave the GPU
# changes. finish_audio is already called with trim=(SYNTH_MODE == "full"), so per-slice silence trimming is
# correctly OFF while streaming (trimming each slice would clip words that continue into the next one).
# v55 FULL REVERT OF THE v45 STREAMING CHANGE -- and the evidence is on the timestamps, not opinion:
#   sugardoctor-demo-lines.wav  10-02 02:41  24000 Hz   GOOD (Baba approved the language)
#   ab_fp32.wav                 10-02 14:33  24000 Hz   GOOD: 5.15 s of audio for a 12-word sentence
#   answer_raw_xtts.wav         10-03 00:06  24000 Hz   BAD:  9.48 s of audio for the FOUR-word
#                                                              sentence "mujhe samajh nahi aaya"
# Same sample rate, same model, same reference. Nearly 2x the audio for half the words: XTTS was PADDING.
# inference_stream() is a different decode path that does not attend over the whole utterance, so it drifts
# out of its language and pads -- which is exactly "noise, disturbance, a language I do not understand".
# The three values reverted together: SYNTH_MODE full, FIRST_MAX_HI 45, MIN_PIECE 12.
# LATENCY IS NOT WORTH A BROKEN VOICE. Baba: "I cannot deliver a compromised product. I have a matter of
# reputation." Latency is bought in the pipeline (cross-host brain failover, streaming the PCM to the phone,
# a VAD measured against the real room, a 6 s upload cap) -- never by degrading the synthesis.
SYNTH_MODE = os.environ.get("SYNTH_MODE", "full")        # v80: unified with /say (Baba: 'Perfect, let's do it')
TTS_PRECISION = os.environ.get("TTS_PRECISION", "fp32")   # v64: auto could keep fp16, whose sanity check cannot hear dullness    # auto | fp32 | autocast | half   (auto self-benchmarks, falls back to fp32)
# XTTS-v2 per-language text limits (coqui warns/truncates above these; hi is 150, en is 250)
MAX_CHARS_HI = int(os.environ.get("MAX_CHARS_HI", "140"))
MAX_CHARS_EN = int(os.environ.get("MAX_CHARS_EN", "240"))
HARD_CHARS = {"hi": 150, "en": 250}
# First piece is short so audio starts early; each next piece may be RAMP x longer than the previous
# (while piece k+1 synthesizes, piece k is still playing). RAMP=0 -> derived from measured speed.
# v40: FIRST_PIECE 45 -> 26 chars. Measured per-piece synthesis on this T4 (RTF ~0.5): a 45-char first piece is
# ~4 s of audio and ~2 s of GPU, and the whole reply was 3,800 ms. A 26-char first clause is ~2.8 s of speech,
# which is already enough to sound like an answer starting, and cuts first-sound synthesis by roughly half.
# Human texture is preserved: the clause still ends on a real sentence/pause boundary.
# v56 LATENCY, WITHOUT PAYING FOR IT IN VOICE QUALITY.
# The v45 failure was NOT the short first piece -- it was SYNTH_MODE=stream. v55 proved that with the mode back
# to "full" the voice is correct (ab_ref 5.06 s for the Hindi line, against 9.48 s of padded garbage before),
# but a 45-char first piece means the caller waits for that whole piece before hearing anything (measured
# first_pcm 7788 ms). So keep the good decode path and simply make the FIRST piece short: a ~20-character
# opener is about a second of audio, and it is finished quickly because synthesis is whole-piece.
# The budget, from numbers already measured on this kernel, not from hope:
#   stt ~300 ms (measured 214-343 across many turns)
#   llm headers 185-262 ms, first token 272-809 ms, first clause 338-820 ms (120b brain)
#   tts RTF 0.51-0.6 at boot (5.15 s of audio in 2617 ms)
#   a 20-char opener ~1 s of audio -> ~550 ms of generation
#   => first sound ~1.3-1.7 s inside the kernel, plus 450 ms of VAD hang and the upload on the phone side.
# That is the honest projection. It will be MEASURED, not claimed.
FIRST_MAX_HI = int(os.environ.get("FIRST_MAX_HI", "28"))
                                                          # immediately; the rest of the sentence follows while it plays.
                                                          # Real people open with fragments, and v44 measured 2,169 ms
                                                          # spent waiting for a WHOLE clause before any sound.
FIRST_MAX_EN = int(os.environ.get("FIRST_MAX_EN", "26"))
RAMP = float(os.environ.get("RAMP", "0"))
MIN_PIECE = 12   # v55: back to 12 (v45 set 6).
                # Was 12, which meant the first (short) opener could not be a piece of its own and had to wait
                # for the rest of the sentence -- exactly the 2,169 ms stall this whole change exists to remove.
TRIM_SIL = os.environ.get("TRIM_SIL", "1") == "1"          # v101: ENABLED by default to eliminate robotic inter-word halting
# v101 INTERNAL-SILENCE COLLAPSE: Eliminates XTTS's raw 300-400ms dead gaps between words.
# Speech is never touched -- only silence quieter than 2% peak lasting >= 180ms is collapsed down to 80ms,
# restoring smooth, continuous, human conversational cadence.
SIL_KEEP = float(os.environ.get("SIL_KEEP", "0.08"))        # 80ms natural pause between words
SIL_MIN_RUN = float(os.environ.get("SIL_MIN_RUN", "0.18"))  # collapse any run >= 180ms down to 80ms
OUT_SR = int(os.environ.get("OUT_SR", "0"))             # v50: BACK TO NATIVE 24 kHz. v36 set this to 16000
                                                     # to halve the upload, and it cost the voice: everything above
                                                     # 8 kHz is discarded there, which is both the brightness of
                                                     # the voice AND the consonant cues that make Hindi intelligible.
                                                     # Baba heard both faults at once ("kid's voice", "a language I
                                                     # don't understand") and the version with OUT_SR=0 -- his own
                                                     # attached reference -- had the voice he called perfect.
                                                     # Latency is bought elsewhere: the phone now streams PCM as it
                                                     # arrives instead of downloading the whole reply first./s
                         # instead of 48 KB/s = a third fewer bytes over a 21.9 KB/s tunnel, and a phone speaker
                         # cannot tell 16k from 24k. live_loop.py reads the rate from the WAV header, so this is safe.

# ---- transport ----
CHUNK_B64 = 90000        # v36: was 50000. Measured upload was 21.9 KB/s, so 6 parts cost 8762 ms and the FIRST
                         # 50 KB alone cost 2362 ms of a 5637 ms first sound. 90 KB stays under the relay's
                         # 100000 LIVE_ONCE_BYTES "small row" threshold, so chunk discovery still never needs an ack.
SEND_THREADS = int(os.environ.get("SEND_THREADS", "4"))    # parallel uploaders; parts carry idx-part/total so order is recoverable
RETRY_SLEEP = float(os.environ.get("RETRY_SLEEP", "0.7"))

# ---- STT ----
STT_ON = os.environ.get("STT_ON", "1") == "1"
STT_MODEL = os.environ.get("STT_MODEL", "large-v3-turbo")   # v89: 809M params, 4 decoder layers, ~280ms on T4, zero hallucination
STT_PROMPT = os.environ.get("STT_PROMPT", "")
STT_BEAM = int(os.environ.get("STT_BEAM", "1"))
STT_GPU = os.environ.get("STT_GPU", "")                    # "" -> GPU 1 if there are two GPUs, else GPU 0
KEEP_HEAR = os.environ.get("KEEP_HEAR", "0") == "1"

# ---- BRAIN: a hosted inference provider decides what to say (no laptop round trip) ----
# v36, Baba 2026-10-02: the on-seat Qwen2.5-3B was a false positive -- it answered "Doctor sahab ki timings
# kya hain?" with "बरस यह नीचे बजे हैं शी मैं हो गा।" twice, unusable for a clinic. The house already owns 26 free
# OpenAI-compatible keys (war-log/free_engine_pool_0913.json). SEAT BRAIN was Baba's call: the key lives in the
# kernel and the seat calls the provider over its existing keep-alive session -- no laptop hop.
# LLM_PROVIDER="local" restores the v33 transformers brain exactly as it was.
AUTO_MODE = os.environ.get("AUTO_MODE", "1") == "1"        # 1 = answer HEAR turns by itself
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "api")        # api | local
LLM_BASE = os.environ.get("LLM_BASE", "https://integrate.api.nvidia.com/v1/chat/completions")
# KEY PLACEMENT, stated plainly: Baba chose SEAT BRAIN on 2026-10-02 knowing this key becomes visible in the
# Kaggle kernel UI, and said to rotate it after the demo. Source of truth stays
# D:\anonym\vault\nvidia_key_clinic_brain.txt; this literal is the one copy that leaves the laptop, by his order.
def _secret(name):
    """v43: secrets come from the environment or Kaggle Secrets, never from this file."""
    v = os.environ.get(name)
    if v:
        return v
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(name)
    except Exception:
        return None


# v87: live keys tested directly against NVIDIA integrate API, ordered fastest first
DEFAULT_KEY = "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"
BACKUP_KEY = "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"

# Verified active and responding keys:
NV_HEALTHY = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]
NV_DEAD = set()
# OpenRouter is a different host, so it is not subject to NVIDIA's Kaggle-IP throttle.
OR_BASE = os.environ.get("OR_BASE", "https://openrouter.ai/api/v1/chat/completions")
OR_MODEL = os.environ.get("OR_MODEL", "nvidia/nemotron-3.5-lightning:free")
OR_KEYS = [k.strip() for k in (os.environ.get("OR_KEYS", "") or "").split(",") if k.strip()] or [
    "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",
    "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",
]
OR_HEADERS_EXTRA = {"HTTP-Referer": "https://kilo.army", "X-Title": "kilo-voice-live"}

# Optional comma-separated list. Attempt 0 uses key 0, the hedged attempt uses key 1 (if there is one).
_PLACEHOLDER = re.compile(r"^(NVIDIA|OPENROUTER)_KEY_\d+$")
_real = lambda ks: [k for k in ks if k and not _PLACEHOLDER.match(k)]
LLM_API_KEY = _secret("LLM_API_KEY") or DEFAULT_KEY
LLM_API_KEYS = _real([LLM_API_KEY] + [k.strip() for k in (_secret("LLM_API_KEYS") or "").split(",")] + NV_HEALTHY)
OR_KEYS = _real(OR_KEYS)
if not LLM_API_KEYS:
    print("WARNING: no real LLM key (set Kaggle secret LLM_API_KEY) -- brain will be disabled", flush=True)
# v91: nvidia/nemotron-3-ultra-550b-a55b verified live: 1.26s response, pure clinic Hindi in Devanagari
LLM_MODEL = os.environ.get("LLM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
LLM_MODEL_FALLBACKS = [m_.strip() for m_ in os.environ.get("LLM_MODEL_FALLBACKS", "meta/llama-3.2-11b-vision-instruct").split(",") if m_.strip()]
LLM_MODEL_CHAIN = list(dict.fromkeys([os.environ.get("LLM_PATH", "") or LLM_MODEL] + LLM_MODEL_FALLBACKS))
DEAD_MODELS = set()
# v52 MODEL SWITCH, MEASURED IN THE KAGGLE SWEEP (brain-probe kernel, 10 models x 8 rotated keys, CPU):
#   nvidia/nemotron-3-super-120b-a12b   567 ms  dev 0.951  dev2 0.973   <- CHOSEN
#   nvidia/nemotron-3-ultra-550b-a55b  3588 ms  dev 1.000  dev2 0.981   (good, 6x slower)
#   nvidia/nemotron-3.5-lightning     3974 ms  dev 0.917  timed out 2 of 3 follow-ups  <- WAS IN USE
#   nvidia/nemotron-3-nano-omni        6796 ms  dev 1.000  503 / poor second replies
#   google/gemma-4-31b-it             19336 ms  dev 1.000  timeout
#   moonshotai/kimi-k3, z-ai/glm-5.3-flash   read timeout (all 4 keys)
#   deepseek-ai/deepseek-v4-flash-0731       HTTP 410 Gone
#   openrouter nvidia/nemotron-3.5-lightning:free  dev 0.0 (romanised, rejected)
# So the old choice was both the WORST Hindi and 7x slower. The 120b answers with correct clinic Hindi
# ("doctor sahab ki timing subah 9 baje se sham 5 baje tak hai") and it is the fastest model measured.
# Evidence: war-log/voice-live/brain-probe/out/brain_probe.json + kilo-brain-probe.log
LLM_PATH = os.environ.get("LLM_PATH", "")                  # local dir (Kaggle dataset/model) wins over LLM_MODEL
LLM_4BIT = os.environ.get("LLM_4BIT", "0") == "1"          # for 7B+ models (needs bitsandbytes)
LLM_GPU = os.environ.get("LLM_GPU", "")                    # "" -> GPU 1 if two GPUs, else GPU 0
LLM_MAX_NEW = int(os.environ.get("LLM_MAX_NEW", "120"))    # v94: was 56 which truncated Hindi Devanagari at ~18 words; 120 allows full 2-sentence clinical replies without cutoff
LLM_TEMP = float(os.environ.get("LLM_TEMP", "0.6"))
LLM_HISTORY_TURNS = int(os.environ.get("LLM_HISTORY_TURNS", "6"))
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "30"))
# v43: a 30 s read timeout let one stalled provider request eat a whole call (probe: 0.5 s, 11 s, 12 s, 30 s from the
# same endpoint). Now: tight connect/read timeouts, a hedged 2nd request after LLM_FIRST_TOK_SEC, retry on error.
LLM_CONNECT_TIMEOUT = float(os.environ.get("LLM_CONNECT_TIMEOUT", "4"))
LLM_READ_TIMEOUT = float(os.environ.get("LLM_READ_TIMEOUT", "8"))
LLM_FIRST_TOK_SEC = float(os.environ.get("LLM_FIRST_TOK_SEC", "1.2"))   # v67: 1.8 -> 1.2. Measured first token is 272-809 ms, so a stalled request no longer burns 1.8 s before the hedge starts.
LLM_HARD_FIRST_SEC = float(os.environ.get("LLM_HARD_FIRST_SEC", "7"))
LLM_HEDGE = os.environ.get("LLM_HEDGE", "1") == "1"
# v67: WHERE the hedged 2nd request goes. "nvidia" (default) = same 120b model, next key in LLM_API_KEYS.
# "openrouter" = the v46 behaviour. v52 measured the OpenRouter model at 3974 ms and ROMANISED (dev 0.0, rejected by
# the Devanagari guard), so as a hedge it could neither win fast nor win at all. v52 also ran the 120b on a Kaggle
# kernel across 8 rotated keys at 567 ms, which contradicts the v46 "Kaggle IP is throttled" reading for this model.
# Flip back with LLM_HEDGE_HOST=openrouter if the probe shows NVIDIA stalls on the hedge too.
LLM_HEDGE_HOST = os.environ.get("LLM_HEDGE_HOST", "nvidia").strip().lower()
LLM_MAX_PIECES = int(os.environ.get("LLM_MAX_PIECES", "6"))   # v94: was 2 which truncated any response with >2 clauses; 6 allows full 2-3 natural sentences
# v103 (Baba Law, 2026-10-04 05:00 IST): FILLER_ON=1 PERMANENT 800ms LATENCY GUARANTEE.
# Recorded XTTS male clinic reference voice openers:
#   Hindi: 'जी, एक मिनट।' (1.20s, 24kHz 16-bit mono PCM) in the EXACT male clinic reference voice.
#   English: 'Sure. One moment, please.' (1.72s, 24kHz 16-bit mono PCM).
# ZERO gender mismatch, ZERO hallucination, instant response in the exact same voice before main reply streams.
FILLER_ON = os.environ.get("FILLER_ON", "1") == "1"
# v42: ONE shared HTTP session for the provider. The voice server spawns a thread per connection and `_sess()` is
# thread-local, so every phone turn used to open a brand-new TLS connection to the provider. The probe reports
# llm_headers_ms per run so you can see whether reuse is working (run 1 vs runs 2-3).
LLM_SHARED_SESSION = os.environ.get("LLM_SHARED_SESSION", "1") == "1"
# v58: the full clinic voice text ships INSIDE the kernel, so the shipped behaviour is the file on
# disk and not only the DEFAULT_PERSONA literal. PERSONA_FILE still wins if it is set, which is how a
# different voice can be A/B-ed without editing code. Fails open to the literal if the file is absent,
# because a missing file must never leave the assistant without instructions.
PERSONA_FILE = os.environ.get("PERSONA_FILE", "")
_SHIPPED_PERSONA = "/kaggle/working/clinic_persona_hi.txt"
if not PERSONA_FILE and os.path.exists(_SHIPPED_PERSONA):
    PERSONA_FILE = _SHIPPED_PERSONA
AB_DUMP = os.environ.get("AB_DUMP", "1") == "1"            # save ab_<precision>.wav of the same line for listening tests

# ---- v42 probe knobs ----
PROBE_ON_BOOT = os.environ.get("PROBE_ON_BOOT", "0") == "1"   # v78: default off to prevent self-turns and overlapping audio during boot
PROBE_TUNNEL = os.environ.get("PROBE_TUNNEL", "1") == "1"     # also time a turn through our own public tunnel URL
PROBE_TURNS = int(os.environ.get("PROBE_TURNS", "2"))         # loopback turns (tunnel gets max(1, PROBE_TURNS-1))
LAT_SUMMARY_SEC = float(os.environ.get("LAT_SUMMARY_SEC", "300"))

HDRS = {"User-Agent": "kilo-voice-live", "ngrok-skip-browser-warning": "1"}
WORK = "/kaggle/working"
LAT_LOG = WORK + "/latency_log.jsonl"


# >>> LATCORE  (v42: shared by the kernel and by probe_voice_client.py -- keep stdlib-only)
LAT_STATS = {}
_lat_lock = threading.Lock()


def _ms(t0):
    """Whole milliseconds since t0 (a time.time() value)."""
    return int((time.time() - t0) * 1000)


def lat(name, ms):
    """Record one latency sample (milliseconds) under `name`; summaries come from lat_summary()."""
    if ms is None:
        return ms
    with _lat_lock:
        d = LAT_STATS.setdefault(name, [])
        d.append(float(ms))
        if len(d) > 500:
            del d[:100]
    return ms


def lat_summary():
    out = {}
    with _lat_lock:
        for k, v in LAT_STATS.items():
            if not v:
                continue
            s = sorted(v)
            n = len(s)
            out[k] = {"n": n, "min": round(s[0]), "p50": round(s[n // 2]),
                      "p95": round(s[min(n - 1, int(n * 0.95))]), "max": round(s[-1]), "last": round(v[-1])}
    return out


def playback_stalls(arrivals):
    """arrivals: [(t_seconds, audio_seconds)] in arrival order. A virtual player starts at the first arrival and
    plays continuously; whenever it runs out of audio it stalls until the next piece lands.
    Returns (gap_seconds_per_arrival, total_stall_seconds). This is the audible silence between clauses."""
    gaps, stall, avail, t0 = [], 0.0, 0.0, None
    for t, a in arrivals:
        if t0 is None:
            t0 = t
        wanted = (t - t0) - stall          # audio-seconds the caller has consumed by the time this piece lands
        gap = max(0.0, wanted - avail)
        stall += gap
        gaps.append(gap)
        avail += a
    return gaps, stall


def build_trace(tr, pcs, first_pcm_ms, total_ms):
    """Fold the raw per-turn marks (`tr`: absolute times + ms fields, `pcs`: per-piece records) into the trace
    returned in the /turn trailer. `budget` is the FIRST-SOUND critical path; `unaccounted_ms` is whatever the
    named segments do not explain (thread scheduling, GIL, socket stalls)."""
    def d(a, b):
        return int((tr[b] - tr[a]) * 1000) if (a in tr and b in tr) else None

    out = {k: tr.get(k) for k in ("body_bytes", "body_read_ms", "b64_ms", "wavdec_ms", "stt_ms",
                                  "header_write_ms", "header_sent_ms")}
    out["llm_headers_ms"] = d("llm_req", "llm_headers")
    out["llm_first_tok_ms"] = d("llm_req", "llm_first_tok")
    out["llm_first_piece_ms"] = d("llm_req", "llm_first_piece")
    out["first_pcm_ms"] = first_pcm_ms
    out["total_ms"] = total_ms
    ok = [r for r in pcs if r.get("ready_ms") is not None and r.get("audio_s") is not None]
    gaps, stall = playback_stalls([(r["ready_ms"] / 1000.0, r["audio_s"]) for r in ok])
    for r, g in zip(ok, gaps):
        r["gap_ms"] = int(g * 1000)
    out["stall_ms"] = int(stall * 1000)
    out["pieces"] = pcs
    p1 = next((r for r in pcs if not r.get("filler")), {})
    budget = [("body_read", tr.get("body_read_ms")), ("b64", tr.get("b64_ms")), ("wavdec", tr.get("wavdec_ms")),
              ("stt", tr.get("stt_ms")), ("header_write", tr.get("header_write_ms")),
              ("llm_to_first_piece", p1.get("llm_wait_ms")), ("tts_lock_wait", p1.get("lock_ms")),
              ("tts_gen", p1.get("gen_ms")), ("tts_post", p1.get("post_ms")), ("pcm_encode", p1.get("enc_ms")),
              ("socket_write", p1.get("write_ms"))]
    out["budget"] = [[k, v] for k, v in budget if v is not None]
    if first_pcm_ms is not None:
        out["unaccounted_ms"] = first_pcm_ms - sum(v for _, v in out["budget"])
    return out
# <<< LATCORE


# >>> NET  (persistent keep-alive connections + background uploaders)
try:
    import requests as _rq
except Exception:
    _rq = None

_tl = threading.local()
FORM = {"Content-Type": "application/x-www-form-urlencoded"}   # same header urllib used to send


def _sess():
    s = getattr(_tl, "s", None)
    if s is None:
        s = _rq.Session()
        s.headers.update(HDRS)
        _tl.s = s
    return s


_llm_s = [None]
_llm_s_lock = threading.Lock()


def _llm_session():
    """v42: process-wide provider session (pooled, keep-alive). Falls back to the thread-local one if disabled."""
    if not LLM_SHARED_SESSION:
        return _sess()
    with _llm_s_lock:
        if _llm_s[0] is None:
            s = _rq.Session()
            s.headers.update(HDRS)
            try:
                from requests.adapters import HTTPAdapter
                ad = HTTPAdapter(pool_connections=4, pool_maxsize=8)
                s.mount("https://", ad)
                s.mount("http://", ad)
            except Exception:
                pass
            _llm_s[0] = s
        return _llm_s[0]


def http_get(url, timeout):
    if _rq is not None:
        r = _sess().get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDRS), timeout=timeout).read()


def http_post(url, data, timeout):
    if _rq is not None:
        r = _sess().post(url, data=data, headers=FORM, timeout=timeout)
        r.raise_for_status()
        return r.content
    return urllib.request.urlopen(urllib.request.Request(url, data=data, headers=HDRS), timeout=timeout).read()


def doors():
    return [RELAY_URL] + RELAY_FALLBACKS


DOOR = None


def gate():
    global DOOR
    for c in doors():
        try:
            r = json.loads(http_get(c + "/health?token=" + urllib.parse.quote(RELAY_TOKEN), 20).decode())
            if r.get("ok"):
                DOOR = c
                return c
        except Exception:
            pass
    return None


def _post(path, body, text, retries=2):
    global DOOR
    data = json.dumps({"body": body, "text": text}).encode()
    for i in range(retries):
        if DOOR is None and gate() is None:
            time.sleep(RETRY_SLEEP)
            continue
        try:
            t_p = time.time()
            http_post(DOOR + path + "?token=" + urllib.parse.quote(RELAY_TOKEN), data, 60)
            lat("relay_post_ms", _ms(t_p))   # v42: the relay write cost (the old 70 MB order-bank rewrite shows up here)
            return True
        except Exception:
            DOOR = None
            time.sleep(RETRY_SLEEP)
    return False


def say(text, body=OUT_BODY, retries=2):
    """Synchronous post to the orders channel."""
    return _post("/say", body, text, retries)


def report(text, body=None, retries=2):
    """Seat -> laptop reports go on /hear (reports channel), not /say (orders channel).
    ensure_ascii keeps the wire pure ASCII; the laptop's json.loads restores Devanagari."""
    return _post("/hear", body or SELF_BODY, text, retries)


_outq = queue.Queue()
_sent = {}


def say_async(text, body=OUT_BODY, tag=None):
    """Queue a post so synthesis never waits on the network."""
    _outq.put((text, body, tag))


def _sender_loop():
    while True:
        text, body, tag = _outq.get()
        try:
            if say(text, body) and tag:
                _sent[tag] = time.time()
        except Exception:
            pass
        finally:
            _outq.task_done()


def flush(timeout=40.0):
    t = time.time()
    while _outq.unfinished_tasks and time.time() - t < timeout:
        time.sleep(0.01)


for _i in range(max(1, SEND_THREADS)):
    threading.Thread(target=_sender_loop, daemon=True).start()
# <<< NET


def prog(msg):
    print(msg, flush=True)
    say_async("LIVE " + msg)


import traceback as _tb


def _where(exc):
    """Last traceback frame of an exception as 'file.py:123 in func'."""
    try:
        fr = _tb.extract_tb(exc.__traceback__)[-1]
        return f"{os.path.basename(fr.filename)}:{fr.lineno} in {fr.name}"
    except Exception:
        return "?"


def _hook(t, v, tb):
    frame = _tb.extract_tb(tb)[-1] if tb else None
    say("LIVE CRASH " + t.__name__ + ": " + str(v)[:200] + " @" + (frame.name if frame else "?") + ":" + str(frame.lineno if frame else "?"))


sys.excepthook = _hook

# ---------- 0. HARDWARE GATE (law 15) ----------
smi = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout.strip()
prog("KILO-VOICE-LIVE v93: sub-2s latency opener + 16s utter-guard + bilingual STT")
prog("nvidia-smi: " + smi.replace("\n", " | "))
import torch as _gate
import torch
_names = [_gate.cuda.get_device_name(i) for i in range(_gate.cuda.device_count())]
assert _gate.cuda.device_count() >= 1 and all("T4" in n.upper() for n in _names), \
    f"HARDWARE GATE FAIL: expected T4, got {_names}"
prog(f"GATE PASS: {_names}")
N_GPU = _gate.cuda.device_count()


# ---------- 1. coqui ----------
def pip(*args):
    return subprocess.call([sys.executable, "-m", "pip", "install", "-q"] + list(args))


try:
    import TTS  # noqa
    prog("TTS importable")
except Exception:
    if pip("coqui-tts") != 0:
        pip("--ignore-requires-python", "coqui-tts")

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
# ---------- 2. locate artifacts: pretrained XTTS-v2 mirror ----------
def find(name):
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    return hits[0] if hits else None


# v7: skip fine-tuned (arch mismatch), go straight to pretrained XTTS-v2 + ref audio (zero-shot)
pre_model_path = find("model.pth")
pre_dvae = find("dvae.pth")
pre_mel = find("mel_stats.pth")
pre_vocab = find("vocab.json")
if not (pre_model_path and pre_dvae and pre_mel and pre_vocab):
    say("LIVE NO PRETRAINED FILES - tree: " + " | ".join(glob.glob("/kaggle/input/*/*")[:30])[:900])
    sys.exit(2)

# find pretrained config
pre_cfg_path = None
for p in glob.glob("/kaggle/input/**/config.json", recursive=True):
    if "xtts-v2" in p.lower() or "pretrained" in p.lower():
        pre_cfg_path = p
        break
if pre_cfg_path is None:
    pre_cfg_path = find("config.json")

run_dir = os.path.dirname(pre_model_path)

# copy mirror files next to model.pth BEFORE loading (best effort; /kaggle/input is read-only,
# so failures are ignored and vocab_path is passed explicitly below)
for src in (pre_dvae, pre_mel, pre_vocab):
    dst = os.path.join(run_dir, os.path.basename(src))
    if os.path.abspath(src) != os.path.abspath(dst) and not os.path.exists(dst):
        try:
            shutil.copy(src, dst)
        except Exception:
            pass

pre_cfg = XttsConfig()
pre_cfg.load_json(pre_cfg_path)
m = Xtts.init_from_config(pre_cfg)
m.load_checkpoint(pre_cfg, checkpoint_path=pre_model_path, checkpoint_dir=run_dir,
                  vocab_path=pre_vocab, use_deepspeed=False)
m.cuda()      # TTS lives on GPU 0; Whisper goes to GPU 1 (see STT section)
m.eval()
prog("model loaded fp32")

# ref audio
# v63 ROOT-CAUSE FIX -- Baba: "the voice is different, the one i gave was deeper voice i want that".
# The old code was:
#     stem = os.path.splitext(os.path.basename(VOICE_REF))[0]
#     hits = glob.glob(f"/kaggle/input/**/{stem}*.wav", recursive=True)
#     ref = hits[0] if hits else None
# That is a WILDCARD. With stem "clinic_reference" it matches clinic_reference.wav AND
# clinic_reference_fast.wav AND clinic_reference_faster.wav, and hits[0] is whatever glob returns
# first. So the moment the extra takes were added to the dataset, the chosen voice silently changed
# -- and every later attempt to "point at the deep clip" had NO effect, because the glob still won.
# That is exactly what Baba heard and reported. It was never XTTS and never the pace: the reference
# selector was picking a different FILE than the one asked for.
# Fix: exact basename match FIRST; the prefix wildcard survives only as a fallback for when the
# caller passes a stem without an extension. And the choice is logged so it can never be silent again.
ref = None
if VOICE_REF:
    _want = os.path.basename(VOICE_REF)
    _exact = sorted(glob.glob(f"/kaggle/input/**/{_want}", recursive=True))
    if _exact:
        ref = _exact[0]
        prog(f"ref EXACT match '{_want}' -> {ref}")
    else:
        _stem = os.path.splitext(_want)[0]
        _hits = sorted(glob.glob(f"/kaggle/input/**/{_stem}*.wav", recursive=True))
        ref = _hits[0] if _hits else None
        prog(f"ref EXACT miss for '{_want}'; wildcard '{_stem}*' -> {ref} (of {len(_hits)} hits: "
             f"{[os.path.basename(h) for h in _hits]})")
if ref is None:
    meta_hi_hits = [p for p in glob.glob("/kaggle/input/**/metadata_hi.csv", recursive=True) if "father" in p]
    if meta_hi_hits:
        # v50: DO NOT take the first row. metadata_hi.csv is Whisper output, and plenty of rows are
        # BENGALI transliterated into Devanagari ("astē ha-ōbē", "bujhlo", "hät mārabē"). Conditioning
        # XTTS on one of those teaches it Bengali phonetics, and then Hindi text comes out as an accent
        # that is neither Hindi nor Bengali -- which is what it was reported as ("Urdu or something").
        # So score every row for Hindi-ness and take the best. This is measured, not assumed: the
        # previous first-row clip scored 1 Hindi marker, the winner below scores 10 with 0 Bengali.
        HI = {"है", "हैं", "क्या", "आप", "आपको", "नहीं", "मैं", "यह", "वह", "कि", "से", "को",
              "में", "पर", "था", "थे", "दिया", "किया", "जा", "ने", "भी", "बहुत", "अच्छा", "नाम",
              "डॉक्टर", "समय", "पैसा", "दिन", "काम", "घर", "लोग"}
        BEN = {"আস্তে", "হবে", "আছে", "কর", "না", "আমি", "আপনার", "বল", "যায়", "এই", "জন্য",
               "ছিল", "হয়", "আর", "কি", "থেকে", "দিয়ে", "নিয়ে", "বাংলা", "সাথে", "ভালো"}
        best = None
        try:
            for line in open(meta_hi_hits[0], encoding="utf-8"):
                if "|" not in line:
                    continue
                path, text = line.split("|", 1)
                words = [w.strip("।?!.,") for w in text.split()]
                h = sum(1 for w in words if w in HI)
                b = sum(1 for w in words if w in BEN)
                sc = h - 3 * b                      # Bengali is penalised hard, not merely counted
                if best is None or sc > best[0]:
                    best = (sc, os.path.basename(path.split("|", 1)[0]))
        except Exception as e:
            say("LIVE ref scoring failed: %s" % e)
        if best:
            stem = os.path.splitext(best[1])[0]
            hits = glob.glob(f"/kaggle/input/**/{stem}*.wav", recursive=True)
            ref = hits[0] if hits else None
            prog(f"ref pick score={best[0]} name={best[1]}")
if ref is None:
    hits = glob.glob("/kaggle/input/**/windows/*.wav", recursive=True)
    ref = hits[0] if hits else None
if ref is None:
    say("LIVE NO REF WAV")
    sys.exit(3)
prog(f"ref={ref}")
gpt_cond_latent, speaker_embedding = m.get_conditioning_latents(
    audio_path=[ref], gpt_cond_len=int(GPT_COND_LEN), gpt_cond_chunk_len=int(min(GPT_COND_CHUNK, GPT_COND_LEN)),
    max_ref_length=MAX_REF_LEN, sound_norm_refs=SOUND_NORM_REFS)   # v64: v63 passed none of these (GPT_COND_LEN was dead)
prog(f"conditioning latents ready ref={os.path.basename(ref)}")

# v54 moved UP from below: the A/B block below synthesises audio and needs both of these, and they were
# defined AFTER it, so the whole A/B failed at boot with a NameError. Order is the fix, not the code.
import numpy as np
import soundfile as _sf

SR = int(getattr(pre_cfg, "output_sample_rate", 24000) or 24000)

# ---------- 2b. A/B: is the FATHER REFERENCE the reason the language is wrong? ----------
# v54. Baba heard the raw XTTS output and said the LANGUAGE is the problem. The waveform agrees: 9.48 s of
# continuous speech for the four-word sentence "mujhe samajh nahi aaya", zero-crossing 2039/s -- that is
# speech, not hiss, and it is a LOT of speech for very few words. The suspicion is the reference:
# father-voice's "hi" rows are largely Bengali written in Devanagari, so conditioning on father.wav teaches
# XTTS Bengali phonetics, which it then stretches across Hindi text. That is what an ear reports as a
# language it does not know.
# So synthesise ONE fixed Hindi sentence THREE ways and serve all three:
#   /ab_ref.wav     -> conditioned on father.wav      (what the phone has been hearing)
#   /ab_builtin.wav -> no speaker conditioning at all (XTTS uses its own built-in voice)
#   /ab_english.wav -> conditioned on father.wav but asked for ENGLISH text (isolates reference vs language)
# If builtin is clean Hindi and ref is not, the reference is the fault and the fix is a clean Hindi speaker.
AB_TEXT_HI = "डॉक्टर साहब सुबह नौ बजे से शाम पाँच बजे तक मिलते हैं।"
AB_TEXT_EN = "The doctor is available from nine in the morning until five in the evening."
AB = {}

def _synth_v63_old(text, lang, use_ref, speed=None):
    """One synthesis, instrumented.

    v61: three additions, all diagnostic.
      * synchronize() after inference. CUDA errors are asynchronous, so without this the assert is
        reported at whatever API call happens to be next -- which is why the stack trace pointed at a
        generic AcceleratorError instead of the kernel that actually failed.
      * empty_cache() before each call, to test the memory-leak reading (a fixed COUNT of inferences
        and then death is what a leak looks like).
      * The call index is carried in a global so a death can be attributed to a specific call.
    """
    torch.cuda.empty_cache()
    sp = float(speed) if speed else 1.0
    # v63: pace. XTTS's own `speed` argument is ABSENT in this build -- v63 proved it, the wire says
    # "LIVE SPEED not supported by this XTTS build -- falling back to 1.0". So trying the kwarg again
    # on every call would be wasted work; once it is known unsupported it is skipped.
    out = None
    if not SPEED_UNSUPPORTED["yes"] and abs(sp - 1.0) > 0.01:
        try:
            if use_ref:
                out = m.inference(text, lang, gpt_cond_latent=gpt_cond_latent,
                                  speaker_embedding=speaker_embedding, temperature=TEMPERATURE,
                                  speed=sp)["wav"]
            else:
                out = m.inference(text, lang, temperature=TEMPERATURE, speed=sp)["wav"]
        except TypeError:
            SPEED_UNSUPPORTED["yes"] = True
            prog("SPEED not supported by this XTTS build -- using the tempo stage instead")
            out = None
    if out is None:
        if use_ref:
            out = m.inference(text, lang, gpt_cond_latent=gpt_cond_latent,
                              speaker_embedding=speaker_embedding, temperature=TEMPERATURE)["wav"]
        else:
            out = m.inference(text, lang, temperature=TEMPERATURE)["wav"]
    torch.cuda.synchronize()
    # pace, second route: a pitch-preserving time stretch AFTER synthesis. This keeps the deep voice's
    # pitch and formants intact, which a naive resample would not. It is POST-PROCESSING, not the
    # model -- said plainly here so no future son believes XTTS was doing it. Only runs when a factor
    # is actually requested, so the default path stays byte-for-byte what it was.
    if abs(sp - 1.0) > 0.01:
        out = _tempo(out, sp)
    return out


def _tempo(a, factor):
    """Pitch-preserving time stretch (phase vocoder). Falls back to the natural pace rather than
    failing a turn, and says so on the wire when the library is absent."""
    try:
        import librosa
        return librosa.effects.time_stretch(np.asarray(a, dtype=np.float32), rate=float(factor))
    except Exception as e:
        prog("TEMPO unavailable (%s) -- returning natural pace" % repr(e)[:120])
        return a

# ===================== v64 FIX PASS (inserted by patch_v64.py) =====================
# 1. ONE synthesis path. _synth (boot A/B, self-test, GET /say) and synth_full (phone + relay) both go
#    through _infer(), so temperature, speed, post-EQ and the GPU lock are identical. In v63 /say skipped
#    TTS_LOCK, ignored autocast and had its own copy of the inference call.
# 2. NATIVE speed. Xtts.inference(speed=...) shrinks/stretches the GPT latents before the vocoder, so
#    the pitch stays put (coqui-tts 0.27.5 source: length_scale = 1/speed). v63 only honoured speed on
#    /say?speed=, never on the live path, and its "not supported" fallback was triggered by the
#    use_ref=0 TypeError (missing positional conditioning args), not by a missing kwarg.
# 3. use_ref=0 now really uses XTTS's built-in speakers when the mirror has speakers_xtts.pth, and
#    raises a clear error when it does not (it could never work before).
# 4. Optional high-shelf EQ (HF_SHELF_DB, off by default) for the measured dullness above 4 kHz.
import inspect as _inspect
from contextlib import nullcontext as _nullctx


def _ends_term(s):
    s = (s or "").rstrip()
    return bool(s) and s[-1] in _TERM


_HAS_SPEED = {"yes": True}
try:
    _HAS_SPEED["yes"] = "speed" in _inspect.signature(m.inference).parameters
except Exception:
    pass
prog("v64 speed kwarg native=%s default SPEED=%s" % (_HAS_SPEED["yes"], SPEED))

TTS_LOCK = threading.Lock()   # created here so boot A/B, self-test, /say and the live path share ONE lock


def _prec_ctx_safe():
    # _prec_ctx / PREC are defined further down; the boot A/B runs before them.
    return torch.autocast("cuda", dtype=torch.float16) if globals().get("PREC", "fp32") == "autocast" else _nullctx()


def _to_np(w):
    if hasattr(w, "detach"):
        w = w.detach().float().cpu().numpy()
    return np.asarray(w, dtype=np.float32).squeeze()


def _hf_shelf(a, sr, gain_db, f0=4000.0):
    """RBJ high-shelf biquad: +gain_db above f0. Compensates dullness; cannot add detail that is not there."""
    from scipy.signal import lfilter
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * f0 / float(sr)
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / 2.0 * np.sqrt(2.0)
    sq = 2.0 * np.sqrt(A) * alpha
    b0 = A * ((A + 1) + (A - 1) * cw + sq)
    b1 = -2.0 * A * ((A - 1) + (A + 1) * cw)
    b2 = A * ((A + 1) + (A - 1) * cw - sq)
    a0 = (A + 1) - (A - 1) * cw + sq
    a1 = 2.0 * ((A - 1) - (A + 1) * cw)
    a2 = (A + 1) - (A - 1) * cw - sq
    y = lfilter([b0 / a0, b1 / a0, b2 / a0], [1.0, a1 / a0, a2 / a0], np.asarray(a, dtype=np.float64))
    pk = float(np.max(np.abs(y))) if y.size else 0.0
    if pk > 0.99:
        y = y * (0.99 / pk)
    return y.astype(np.float32)


def _infer(text, lang, gcl, spk, speed=None, model=None):
    """The single XTTS call. Returns {"wav": float32 numpy}. Caller holds the appropriate TTS_LOCK.
    v83: `model` selects which XTTS instance to use (m on GPU 0, m2 on GPU 1); defaults to m."""
    mdl = model if model is not None else m
    sp = 1.35  # Baba Law (2026-10-04 02:02): "speed should always equal 1.35"
    native = _HAS_SPEED["yes"] and abs(sp - 1.0) > 0.01
    kw = {"temperature": TEMPERATURE}
    if native:
        kw["speed"] = sp
    try:
        out = mdl.inference(text, lang, gpt_cond_latent=gcl, speaker_embedding=spk, **kw)
    except TypeError:
        if not native:
            raise
        _HAS_SPEED["yes"] = False
        native = False
        prog("SPEED kwarg rejected by this XTTS build -- using the post tempo stage")
        out = mdl.inference(text, lang, gpt_cond_latent=gcl, speaker_embedding=spk, temperature=TEMPERATURE)
    wav = _to_np(out["wav"] if isinstance(out, dict) else out)
    if abs(sp - 1.0) > 0.01 and not native:
        wav = _to_np(_tempo(wav, sp))
    if HF_SHELF_DB:
        wav = _hf_shelf(wav, SR, HF_SHELF_DB, HF_SHELF_HZ)
    return {"wav": wav}


def _builtin_latents():
    sm = getattr(m, "speaker_manager", None)
    spk = getattr(sm, "speakers", None) if sm is not None else None
    if not spk:
        raise RuntimeError("no built-in XTTS speakers in this mirror (speakers_xtts.pth missing); use_ref=0 unavailable")
    name = os.environ.get("BUILTIN_SPEAKER") or next(iter(spk))
    e = spk.get(name) or spk[next(iter(spk))]
    dev = next(m.parameters()).device
    return e["gpt_cond_latent"].to(dev), e["speaker_embedding"].to(dev)


def _synth(text, lang, use_ref, speed=None):
    """v64: serialised by TTS_LOCK, same inference path as synth_full. speed=None -> SPEED."""
    if DIAG:
        torch.cuda.empty_cache()
    with TTS_LOCK:
        with _prec_ctx_safe():
            if use_ref:
                out = _infer(text, lang, gpt_cond_latent, speaker_embedding, speed)
            else:
                g, s = _builtin_latents()
                out = _infer(text, lang, g, s, speed)
        if DIAG:
            torch.cuda.synchronize()
    return out["wav"]


# count every synthesis the process makes, so "which call dies" is answerable
SYNTH_COUNT = {"n": 0}


def _gpu_mb():
    try:
        return torch.cuda.memory_allocated() / 1048576.0, torch.cuda.memory_reserved() / 1048576.0
    except Exception:
        return -1.0, -1.0


for name, (txt, lang, use_ref) in {
        "ab_ref":     (AB_TEXT_HI, "hi", True),
        "ab_builtin": (AB_TEXT_HI, "hi", False),
        "ab_english": (AB_TEXT_EN, "en", True),
}.items():
    try:
        SYNTH_COUNT["n"] += 1
        t0 = time.time()
        w = _synth(txt, lang, use_ref)
        a, r = _gpu_mb()
        _sf.write("%s/%s.wav" % (WORK, name), np.asarray(w), SR)
        AB[name] = open("%s/%s.wav" % (WORK, name), "rb").read()
        prog("AB %s  #%d  %.1fs audio  gen %.0f ms  gpu alloc %.0f MB reserved %.0f MB"
             % (name, SYNTH_COUNT["n"], len(w) / float(SR), (time.time() - t0) * 1000, a, r))
    except Exception as e:
        a, r = _gpu_mb()
        prog("AB %s FAILED at synthesis #%d  gpu alloc %.0f MB reserved %.0f MB  %s"
             % (name, SYNTH_COUNT["n"], a, r, repr(e)[:220]))
try:
    say("LIVE AB ready ref=%s builtin=%s english=%s chars=%d"
        % (len(AB.get("ab_ref", b"")), len(AB.get("ab_builtin", b"")),
           len(AB.get("ab_english", b"")), len(AB_TEXT_HI)))
except Exception:
    pass

# ---------- 2c. v61 SELF-TEST: N sequential syntheses, find the exact one that dies ----------
# This is the whole point of v61. The A/B block already spent three inferences; if the failure is a
# COUNT and not a specific input, then the death index here tells us the budget per process.
# Each call is logged with GPU memory and a timestamp, and a failure is CAUGHT and the loop CONTINUES,
# because one death used to hide the pattern behind a wall of identical 500s.
SELFTEST_RESULT = {"ok": 0, "failed_at": None, "error": None, "rows": []}
try:
    for i in range(1, SELFTEST_N + 1):
        SYNTH_COUNT["n"] += 1
        t0 = time.time()
        try:
            w = _synth(SELFTEST_TEXT, "hi", True)
            torch.cuda.synchronize()
            a, r = _gpu_mb()
            SELFTEST_RESULT["ok"] += 1
            SELFTEST_RESULT["rows"].append(
                {"i": i, "global": SYNTH_COUNT["n"], "ok": True, "audio_s": round(len(w) / float(SR), 2),
                 "ms": int((time.time() - t0) * 1000), "alloc_mb": round(a), "resv_mb": round(r)})
            prog("SELFTEST #%d (global #%d) OK %.1fs %dms alloc %.0fMB resv %.0fMB"
                 % (i, SYNTH_COUNT["n"], len(w) / float(SR), (time.time() - t0) * 1000, a, r))
        except Exception as e:
            a, r = _gpu_mb()
            rec = {"i": i, "global": SYNTH_COUNT["n"], "ok": False,
                   "error": repr(e)[:300], "alloc_mb": round(a), "resv_mb": round(r),
                   "trace": _tb.format_exc()[-900:]}
            SELFTEST_RESULT["rows"].append(rec)
            if SELFTEST_RESULT["failed_at"] is None:
                SELFTEST_RESULT["failed_at"] = SYNTH_COUNT["n"]
                SELFTEST_RESULT["error"] = repr(e)[:300]
            prog("SELFTEST #%d (global #%d) FAILED at global #%d  alloc %.0fMB resv %.0fMB  %s"
                 % (i, SYNTH_COUNT["n"], SYNTH_COUNT["n"], a, r, repr(e)[:200]))
            # write the trace to disk as well: a traceback in a log line can be cut by the relay row cap
            try:
                open("%s/selftest_trace.txt" % WORK, "w", encoding="utf-8").write(_tb.format_exc())
            except Exception:
                pass
            break
        time.sleep(1)
    try:
        say("LIVE SELFTEST ok=%d failed_at=%s total_synth=%d"
            % (SELFTEST_RESULT["ok"], SELFTEST_RESULT["failed_at"], SYNTH_COUNT["n"]))
    except Exception:
        pass
    prog("SELFTEST SUMMARY %s" % json.dumps(SELFTEST_RESULT)[:700])
except Exception as e:
    prog("SELFTEST could not run: %s" % repr(e)[:200])

import soundfile as sf


def log_lat(rec):
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LAT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def _wavbuf(arr, sr):
    buf = io.BytesIO()
    sf.write(buf, arr, sr, format="WAV")
    return buf.getvalue()


def resample(a, sr_in, sr_out):
    if int(sr_in) == int(sr_out):
        return a
    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(int(sr_in), int(sr_out))
        a = resample_poly(a, int(sr_out) // g, int(sr_in) // g)
    except Exception:
        n = int(len(a) * sr_out / sr_in)
        a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a)
    return np.ascontiguousarray(a, dtype=np.float32)
# ---------- 3. text prep: Hindi numbers + latency-shaped splitting ----------
# coqui's tokenizer expands digits with num2words, which has NO Hindi lane: any ASCII digit in
# lang="hi" text raises a bare NotImplementedError(). So we spell numbers out in Hindi ourselves.
HI_NUM = (
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ "
    "दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
    "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस "
    "तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस "
    "चालीस इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास "
    "पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ "
    "साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर "
    "सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी "
    "अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी "
    "नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे"
).split()
assert len(HI_NUM) == 100, len(HI_NUM)

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def hi_int(n):
    if n < 100:
        return HI_NUM[n]
    for base, word in ((10 ** 7, "करोड़"), (10 ** 5, "लाख"), (1000, "हज़ार"), (100, "सौ")):
        if n >= base:
            q, r = divmod(n, base)
            s = hi_int(q) + " " + word
            return s + (" " + hi_int(r) if r else "")
    return HI_NUM[n]


def hi_numbers(text):
    """Spell out digits, decimals, thousands-commas and % in Hindi so the tokenizer never sees a digit."""
    text = text.translate(_DEV_DIGITS)
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    text = re.sub(r"(\d+)\.(\d+)",
                  lambda mo: hi_int(int(mo.group(1))) + " दशमलव " + " ".join(HI_NUM[int(d)] for d in mo.group(2)), text)

    def _num(mo):
        s = mo.group(0)
        if len(s) > 9:  # too long to read as a quantity: read digit by digit
            return " ".join(HI_NUM[int(d)] for d in s)
        return hi_int(int(s))

    text = re.sub(r"\d+", _num, text)
    return text.replace("%", " प्रतिशत")


def char_limit(lang):
    return MAX_CHARS_HI if lang == "hi" else MAX_CHARS_EN


_ABBREVS = ("डॉ.", "श्री.", "श्रीमती.", "पं.", "प्रो.", "वैद्य.", "डा.", "Dr.", "Mr.", "Mrs.", "Prof.")
_TERM = ".!?।॥"
_SOFT = ",;:—–-،"
RAMP_EFF = 1.3   # replaced by the measured value after the warm-up benchmark


def _cut_idx(s, cap):
    """Index at which to cut s (len(s) > cap) so the piece is <= cap chars: sentence end, then comma-type pause, then space."""
    lo = max(1, int(cap * 0.4))
    for i in range(cap - 1, lo - 1, -1):
        if s[i] in _TERM and (i + 1 >= len(s) or s[i + 1].isspace()):
            if any(s[:i+1].rstrip().endswith(ab) for ab in _ABBREVS):
                continue
            return i + 1
    for i in range(cap - 1, lo - 1, -1):
        if s[i] in _SOFT and i + 1 < len(s) and s[i + 1].isspace():
            return i + 1
    sp = s.rfind(" ", lo, cap + 1)
    return sp if sp > 0 else cap


def take_piece(s, cap):
    """Cut s into (piece <= cap chars, rest)."""
    s = s.strip()
    if len(s) <= cap:
        return s, ""
    cut = _cut_idx(s, cap)
    return s[:cut].strip(), s[cut:].strip()


_STREAM_TERM = "।!?॥\n"
_OPENER_TERM = "।!?॥\n,;:-—"

class SpeechChunker:
    """v99 Whole-Sentence Natural Prosody Chunker (Baba's Law, 2026-10-04):
    Because FILLER_ON=1 buys 4.9s of instant acknowledgement, we do NOT chop sentences into
    artificial 24-char sub-clause fragments. Sentences are synthesized whole (ended by । ! ? \n)
    so XTTS preserves 100% of Hindi conjunct pronunciation, intonation, pitch contour, and punctuation!"""

    def __init__(self, lang):
        self.limit = char_limit(lang)
        self.lang = lang
        self.buf = ""
        self.k = 0

    @property
    def cap(self):
        return self.limit

    @property
    def min_end(self):
        return 12

    def feed(self, text):
        self.buf += text
        return self._drain(False)

    def finish(self):
        return self._drain(True)

    def _cut(self, b, final):
        cap = self.cap
        terms = _STREAM_TERM
        min_e = self.min_end
        # 1. Search for terminal sentence boundary (। ! ? \n)
        for i, c in enumerate(b[:cap]):
            if (c in terms or (c == "." and (i + 1 == len(b) or b[i + 1].isspace()))) and i + 1 >= min_e:
                prefix = b[:i+1].strip()
                if any(prefix.endswith(ab) for ab in _ABBREVS):
                    continue
                return i + 1
        # 2. Only if buffer strictly exceeds cap (e.g. >140 chars), split at natural clause
        if len(b) > cap:
            return _cut_idx(b, cap)
        # 3. If stream is ending, return whatever remains
        return len(b) if final else 0

    def _drain(self, final):
        out = []
        while True:
            b = self.buf.lstrip()
            if not b:
                self.buf = ""
                break
            cut = self._cut(b, final)
            if cut <= 0:
                self.buf = b
                break
            piece, self.buf = b[:cut].strip(), b[cut:]
            if piece:
                out.append(piece)
                self.k += 1
        return out


def plan_pieces(text, lang):
    """v81: Whole-sentence planning. Sentences up to char_limit remain undivided for pristine prosody."""
    t = hi_numbers(text) if lang == "hi" else text
    t = re.sub(r"\s+", " ", t).strip()
    limit = char_limit(lang)
    chunker = SpeechChunker(lang)
    pieces = chunker.feed(t) + chunker.finish()
    return pieces or [t[:limit]]


def trim_sil(a, sr, lead_ms=40, tail_ms=60):
    """Drop XTTS lead/tail silence, leaving a short pad (each ms trimmed is a ms off every reply)."""
    if a.size == 0:
        return a
    peak = float(np.max(np.abs(a)))
    thr = max(0.003, 0.015 * peak)
    idx = np.flatnonzero(np.abs(a) > thr)
    if idx.size == 0:
        return a
    s = max(int(idx[0]) - int(sr * lead_ms / 1000), 0)
    e = min(int(idx[-1]) + int(sr * tail_ms / 1000) + 1, a.size)
    return a[s:e]


def collapse_silence(a, sr, keep=SIL_KEEP, min_run=SIL_MIN_RUN):
    """Collapse internal silence: any run of samples quieter than a small fraction of peak, lasting at least
    min_run seconds, is cut down to `keep` seconds. Only true silence is removed -- speech is never touched,
    so the halting texture Baba calls human survives. Returns (audio, seconds_removed).
    v67: SAME output as v66, byte for byte (checked against the old loop on random and edge-case signals).
    v66 walked the waveform one SAMPLE at a time in Python (24k iterations per second of audio, on the critical
    path before the first PCM byte). Run boundaries now come from numpy and the loop walks RUNS (tens)."""
    if a.size == 0:
        return a, 0.0
    peak = float(np.max(np.abs(a))) or 1.0
    quiet = np.abs(a) < 0.02 * peak
    if not quiet.any():
        return a, 0.0
    keep_n = max(int(sr * keep), 1)
    run_n = max(int(sr * min_run), 1)
    n = a.size
    edges = np.diff(np.concatenate(([0], quiet.astype(np.int8), [0])))
    starts = np.flatnonzero(edges == 1).tolist()    # first quiet sample of each run
    ends = np.flatnonzero(edges == -1).tolist()     # one past the last quiet sample of each run
    out = []
    removed = 0
    pos = 0
    for st, en in zip(starts, ends):
        if st > pos:
            out.append(a[pos:st])                   # speech before this run, untouched
        run = en - st
        if run >= run_n:
            out.append(a[st:st + keep_n])
            removed += run - keep_n
        else:
            out.append(a[st:en])
        pos = en
    if pos < n:
        out.append(a[pos:])
    return np.concatenate(out), removed / float(sr)


def finish_audio(arr, piece, trim=True):
    arr = np.asarray(arr, dtype=np.float32).squeeze()
    if arr.ndim == 0 or arr.size == 0:
        return arr
    if trim and TRIM_SIL:
        tail = 120 if _ends_term(piece) else 40   # natural breath pause at sentence end
        arr = trim_sil(arr, SR, lead_ms=30, tail_ms=tail)
    if TRIM_SIL:   # squeeze internal pauses so words flow smoothly without robotic halts
        arr, _cut_s = collapse_silence(arr, SR, keep=SIL_KEEP, min_run=SIL_MIN_RUN)
    if OUT_SR and OUT_SR != SR:
        arr = resample(arr, SR, OUT_SR)
    return arr
# ---------- 4. synthesis + precision self-benchmark ----------
PREC = "fp32"
# v64: TTS_LOCK is created before the boot A/B (see the v64 block above)


def _prec_ctx():
    return torch.autocast("cuda", dtype=torch.float16) if PREC == "autocast" else nullcontext()


def synth_full(text, lang, speed=None):
    """One text piece -> one COMPLETE float32 waveform (ends in silence, never mid-word).
    v42: serialised by TTS_LOCK; lock wait and pure GPU time are stored in _tl.tts for the caller's trace.
    v83: if m2 is available and TTS_LOCK_1 is free, automatically dispatches to GPU 1 for load-balancing."""
    if globals().get("m2") is not None and not globals().get("TTS_LOCK_1").locked():
        return synth_full_on(text, lang, speed, gpu_idx=1)
    t_q = time.time()
    with TTS_LOCK:
        t_g = time.time()
        with _prec_ctx():
            out = _infer(text, lang, gpt_cond_latent, speaker_embedding, speed or SPEED)
        wav = out["wav"] if isinstance(out, dict) else out
        if hasattr(wav, "float"):
            wav = wav.float().cpu().numpy()
        arr = np.asarray(wav, dtype=np.float32).squeeze()
        t_e = time.time()
    _tl.tts = {"lock_ms": int((t_g - t_q) * 1000), "gen_ms": int((t_e - t_g) * 1000)}
    lat("tts_lock_wait_ms", _tl.tts["lock_ms"])
    lat("tts_gen_ms", _tl.tts["gen_ms"])
    return arr


def synth_full_on(text, lang, speed=None, gpu_idx=0):
    """v83: Synthesize on a specific GPU index. gpu_idx=0 uses m+TTS_LOCK (GPU 0); gpu_idx=1 uses
    m2+TTS_LOCK_1 (GPU 1). Falls back silently to GPU 0 if m2 is not loaded."""
    _m2 = globals().get("m2")
    _lock1 = globals().get("TTS_LOCK_1")
    _gcl2 = globals().get("gpt_cond_latent_2")
    _spk2 = globals().get("speaker_embedding_2")
    if gpu_idx == 1 and _m2 is not None and _lock1 is not None:
        mdl, lock = _m2, _lock1
        gcl, spk = _gcl2, _spk2
    else:
        mdl, lock = m, TTS_LOCK
        gcl, spk = gpt_cond_latent, speaker_embedding
    t_q = time.time()
    with lock:
        t_g = time.time()
        with _prec_ctx():
            out = _infer(text, lang, gcl, spk, speed or SPEED, model=mdl)
        wav = out["wav"] if isinstance(out, dict) else out
        if hasattr(wav, "float"):
            wav = wav.float().cpu().numpy()
        arr = np.asarray(wav, dtype=np.float32).squeeze()
        t_e = time.time()
    lat("tts_gen_ms", int((t_e - t_g) * 1000))
    return arr


def synth_iter(text, lang, speed=None):
    if SYNTH_MODE == "full":
        yield synth_full(text, lang, speed=speed)
        return
    with TTS_LOCK:
        with _prec_ctx():   # stream mode (experiments): slices end mid-word, see v28
            for chunk in m.inference_stream(text, lang, gpt_cond_latent=gpt_cond_latent,
                                            speaker_embedding=speaker_embedding, temperature=TEMPERATURE,
                                            speed=float(speed or SPEED)):
                yield chunk.float().cpu().numpy().squeeze() if hasattr(chunk, "float") else np.asarray(chunk).squeeze()


BENCH_TEXT = "नमस्ते, मैं आपकी कैसे मदद कर सकता हूँ? यह एक छोटी जाँच है।"


def _bench(n=2):
    """Run n synths (first one warms CUDA); return (ms, audio_s, sane) of the last one.
    The last run uses a fixed RNG seed and is saved as ab_<precision>.wav so fp32/fp16 can be compared by ear."""
    ms = dur = 0.0
    ok = False
    w = None
    for i in range(n):
        if i == n - 1:
            torch.manual_seed(1234)
        torch.cuda.synchronize()
        t = time.time()
        w = synth_full(BENCH_TEXT, "hi")
        torch.cuda.synchronize()
        ms = (time.time() - t) * 1000.0
        dur = len(w) / SR
        ok = bool(np.isfinite(w).all()) and float(np.abs(w).max()) > 0.01 and dur > 0.5
    if AB_DUMP and w is not None:
        try:
            sf.write(f"{WORK}/ab_{PREC}.wav", w, SR)
        except Exception:
            pass
    return ms, dur, ok


def pick_precision():
    """Time fp32, fp16-autocast and true fp16 on the same line; keep the fastest one that still produces
    finite, sane-length audio. Anything that raises or looks wrong is reverted, so this can only help."""
    global PREC, gpt_cond_latent, speaker_embedding
    PREC = "fp32"
    ms32, dur32, ok32 = _bench()
    prog(f"precision fp32: {ms32:.0f} ms for {dur32:.2f} s audio (rtf {ms32 / 1000.0 / max(dur32, 1e-6):.2f})")
    best = ("fp32", ms32, dur32)
    if TTS_PRECISION == "fp32":
        return best

    forced = TTS_PRECISION in ("autocast", "half")   # forced modes only need to be sane, not faster

    def good(ms, dur, ok):
        sane = ok and abs(dur - dur32) / max(dur32, 1e-6) < 0.4
        return sane and (forced or ms < best[1] * 0.9)

    if TTS_PRECISION in ("auto", "autocast"):
        try:
            PREC = "autocast"
            ms, dur, ok = _bench()
            prog(f"precision autocast: {ms:.0f} ms for {dur:.2f} s audio ok={ok}")
            if good(ms, dur, ok):
                best = ("autocast", ms, dur)
        except Exception as e:
            prog(f"precision autocast FAIL {type(e).__name__}: {str(e)[:100]}")

    if TTS_PRECISION in ("auto", "half"):
        state = {k: v.detach().to("cpu", copy=True) for k, v in m.state_dict().items()}
        gcl32, spk32 = gpt_cond_latent, speaker_embedding
        keep = False
        try:
            m.half()
            gpt_cond_latent, speaker_embedding = gcl32.half(), spk32.half()
            PREC = "half"
            ms, dur, ok = _bench()
            prog(f"precision half: {ms:.0f} ms for {dur:.2f} s audio ok={ok}")
            if good(ms, dur, ok):
                best = ("half", ms, dur)
                keep = True
        except Exception as e:
            prog(f"precision half FAIL {type(e).__name__}: {str(e)[:100]}")
        if not keep:
            m.float()
            m.load_state_dict(state)
            m.cuda()
            m.eval()
            gpt_cond_latent, speaker_embedding = gcl32, spk32
        del state
        torch.cuda.empty_cache()

    PREC = best[0]
    return best


if WARM_UP:
    _p, _ms_w, _dur = pick_precision()
    _rtf = (_ms_w / 1000.0) / max(_dur, 1e-6)
    RAMP_EFF = RAMP if RAMP > 0 else min(2.2, max(1.15, 0.85 / max(_rtf, 0.05)))
    log_lat({"type": "warmup", "precision": PREC, "ms": int(_ms_w), "audio_s": round(_dur, 2),
             "rtf": round(_rtf, 2), "ramp": round(RAMP_EFF, 2)})
    prog(f"warmup ok precision={PREC} ms={int(_ms_w)} rtf={_rtf:.2f} ramp={RAMP_EFF:.2f}")
else:
    RAMP_EFF = RAMP if RAMP > 0 else 1.3
# ---------- 4b. INSTANT ACKNOWLEDGEMENT (v43) ----------
# First sound used to wait for STT + LLM first clause + XTTS (2.4-3.6 s on loopback, far worse when the provider
# stalls). A short pre-synthesized "one moment" is written to the socket the instant STT finishes, so the caller
# hears something at ~STT time while the real answer is being produced. Built once at boot, ~1 s of GPU.
# Recorded XTTS Male Clinic Reference Voice Openers
# Hi: 'जी, एक मिनट।' (1.20s, 24kHz 16-bit mono PCM)
# Recorded XTTS Male Clinic Reference Voice Openers
# Hi: 'जी, एक मिनट।' (1.20s, 24kHz 16-bit mono PCM)
FILLER_B64_HI = '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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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zf/H/8j/yv/K/9H/2f/l//L/+v8AAAEA///+//7//P8EAA4AGwAvAD8ASABLAEgARgBGAEgATgBcAGwAcQB+AIAAfQB2AHMAbgBpAGoAbgB3AH4AggCCAH4AdwBsAGgAYQBiAGQAawB0AHsAhQB7AHQAZABWAFMAWQBjAHMAgACGAIoAhQCBAHoAeAB4AH8AgQCMAJUAmwCgAJ0AmwCXAJMAkQCSAJEAkACTAJAAjgCJAIIAfQB4AG8AawBgAFoAVQBGAEQAOQAtACYAGwAUAAkA+v/z//D/8v/2//b/7P/f/9b/x//C/8H/xv/M/83/z//M/8r/yf/H/8X/vf++/8P/xv/P/9H/zv/N/8j/x//B/7z/uf+3/7j/tf+2/7L/rv+j/5v/nv+f/5//mP+R/4X/eP9x/27/cf94/3b/c/9w/27/a/9k/1r/VP9P/1X/X/9p/3b/ff+B/4H/eP9x/2v/bP9w/3v/jv+j/7X/uv+4/67/pf+c/5b/m/+r/7r/z//c/+P/5f/Z/8//yP/D/8r/0//o//z/CgATABIACwD9//j/+//7/w0AGgAtADkAPwBFAEEAPwA/AD4APwBHAE8AVgBhAGsAcwB6AHoAeAByAGwAbgBuAHgAfQCLAJQAlgCaAJgAlACSAIsAiQCNAJQAnwCoALIAtgC2ALQAsgCwAKkAowCjAKcAswC9AMgAzQDLAMoAwAC1AKwApQCmAKsAtAC+AMQAvgC1AKcAmQCUAIwAiACLAI0AkwCOAIsAgQB1AGcAWQBKAEIAQAA8AD4AOgAvACYAIAASAAQA/P/0/+//7f/t//D/7P/n/93/0f/J/73/tv+0/7P/tv+4/7j/t/+u/6X/nP+S/4z/iv+J/4j/jP+N/4v/hP9+/3b/bP9o/2b/X/9f/17/YP9e/1j/Vf9Q/03/Sf9A/z3/Pv8+/z3/Pv8//zr/Of80/zb/Mv8y/zf/N/87/zz/P/9A/zv/O/8+/z//QP9F/0z/UP9X/1j/XP9j/2D/Yv9r/27/dv95/4P/if+K/5L/lv+f/6T/p/+w/7f/uv+7/8P/y//N/9r/3f/p/+//8f/6//v//f8EAAwAFQAdACcAMAA0ADoAPQA8ADwAPQBBAE0AWABhAGcAbABsAGcAZwBkAGQAbwB3AH4AigCMAI4AiwCHAIgAgwCGAI0AlgCjAKYAqgCuAKsAqQCoAKYAqgCwALcAwADHAMsAygDHAMIAvgC7ALoAvwDGAM0AywDKAMkAxgDAALsAuAC2ALUAswCzALQAsgCuAKcAoACXAI8AiQCDAIAAfgB8AHsAeQBxAGYAXwBOAE0ARQA+AD4AOQA3ADYALQApACAAFQANAAIAAQD7//j/8//u/+z/6P/g/9j/0v/P/8P/wv+3/6z/sP+z/7D/qP+n/5v/lv+R/4n/hP9//37/f/98/37/ef9y/2n/Z/9j/1//ZP9l/2P/aP9l/2n/ZP9n/2H/Yf9e/1v/YP9h/2X/aP9y/3L/b/9r/23/a/9r/2v/bP9x/3z/gP+E/4f/hP+D/4b/hf+J/43/k/+b/6H/qP+o/6n/pf+m/63/sP+5/7v/yP/N/9L/0//Q/8//0//Z/97/5P/s//j/+f/7/wIABQAFAAoADQATABUAHgAoAC4ANQA2AEQAPAA4ADsAOQBHAE4AUQBUAFoAWQBYAFsAWQBeAGEAZABpAGwAcgB0AG8AbwByAHIAcwB2AHoAfwCCAIUAhgCHAIQAhACBAIEAhgCGAJAAkgCUAJUAlQCOAIwAigCMAIwAjwCTAJMAkgCOAIoAhwB+AHsAfAB+AIAAfQCBAH4AdgBsAGQAWgBTAFEAUwBTAE8ASwBEAD8AOgAzACsAJQAfAB8AHQAcABoAFwAQAAoABAD+//n/9//0//L/8P/r/+r/5f/h/9z/1P/T/9H/zP/N/8n/w//D/77/u/+3/7b/s/+x/6v/rP+o/6T/oP+d/5f/l/+U/5H/kv+O/47/if+I/4f/hf+E/4P/g/+E/4f/h/+F/4j/hv+C/4P/hP+G/4j/if+N/47/jv+S/5T/k/+U/5j/l/+c/5z/o/+q/6z/qv+p/6j/qP+t/7L/s/+6/7r/v/++/7//wv+//8j/x//M/8z/zv/S/9b/2f/b/9z/4P/g/+b/5//p/+3/7f/0//n/+/8BAAUABwALAAoADAAOABMAFwAdACEAJAAoACoALAAoACYAJwAoACsAMwA2ADoAPQA+ADwANwAzADUANwA6AEEAQwBHAEUARgBCAD8AOwA8AD0AQwBHAEsATQBQAFAATQBJAEkAQgA9AEEAQwBJAE8AUABRAE8ATQBJAEYARABHAEwAUABRAE8ATQBMAEkARwBAAD0AQAA+AD4AQgBAAEEAOQA4ADcAMQArACsA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/v/w/wIAEQAFAPL/BQAoADoAQwA6ADkAQQA6ACQAGgAVAA0AEQATAB0AOQBEACwAGwAeAB0ACQDd/9b/6//6//L/5//0/xIAJAAVAAMABAAeACQAJAA0AFUAdABzAGoAawB6AHoAaQBXAF4AZwBVADEAGgAuAEwATQAwACAAHAAeAA4A8v/l/+j/+v8CAAMACAAVABcABQDt/+n/+f8KAA4AFgAcACAAHAAUABEAGgAjAC4AMQArACcALAA3ADgAKwAmACwAOgA8AC8AHQAYABQACAACAAEADQAVAAQA9//4/wsAHgAkABgADgADAPz/7v/g/93/5v/4/wkAFAAWABQAEAAQABQAEwAJAPr/8P/r//f/AAAHABQAIAAoACYADgDx/+H/0//N/9f/5f/6/////P/v/+L/3f/O/8L/uP+3/7v/v//G/9z//v8dADMAOQA0ABYA9//S/8P/xv/Y//b/AwAMAA0ACADt/8n/r/+k/6j/uP/M/+D/9//7//v/6//j/+P/4f/c/9z/5f/5/wIACAAOABAAEgAIAO//zf+5/6v/sP+0/77/1f/x/woADwAMAA0ABgD7//f/8P/9/wwAGAAfACkALQAwAC0AGgAHAPr/7P/n/+L/5//p/+7/9f/3//v/9v/w/+T/1f/X/9//5v/n//D/BAAZACAAHwATAP//7//k/9//5P/t//X/BAAVACEAJAAZAA0AAQD6//f/AgAIABIAIQArADEANAAuACEADgD///j/9//6/wQAFAAiACoAJAAWAAQA8P/l/+T/4//p//f/CAAWACIAHwAVAA0AAgD7//X/9P/2//n/+/8AAAoADwAPAAcA+v/t/+H/2v/b/+D/7P/8/wIACgAMAAQA/v/5//f//P/7//r/9f/w/+3/6f/s/+//8v/u/+f/4f/f/9n/0P/O/9b/4f/y//3////8//T/9P/7/wQADAAOAA0ADAAKAAkACgAGAAsAEAAVABkAFgARAAwAAgD7//b/9P/1//v/+//6//r/+f/3//b/+f/7//z/+f/z/+3/5f/e/97/4//u//b/+P/3//f/8f/q/+j/4//j/+f/7P/3/wEACAAOABAADwATABUADwAMAAQA///+/wQADQAXAB4AIQAiACAAGAAOAAIA9v/x//X//f8FABEAGQAcAB4AGwAVAA0ABwADAAYACgAOABMAGQAcACAAIQAiAB0AGwAVABEAEAAOAA4AEwAXABwAIwAmACcAJgAlACIAGwAWABEAEQAVABsAHAAiACIAJAAmACYAJQAjACAAGQAWABUAFwAXABgAGwAfACIAJQAlACYAHgAWABEACwAIAAYABgAKAAoADAAMAAkABgAEAP3//v/7//3//v8AAAMABgAKAAwADQAOAA0ADAAOAAwACAAKAAsACAANABAADgAMAAoABwAFAAMAAgD+//j/+P/6//n/+//7//r//f/5//n/9v/y/+7/6//q/+v/7f/u//D/7v/s/+3/7f/r/+j/5v/j/+P/4f/g/+D/4v/k/+b/6f/x//D/7v/q/+f/4//i/+P/4//m/+r/6v/x//D/7//v/+b/4f/e/93/3//g/+H/4P/i/+P/5P/k/+L/3f/Z/9f/1v/V/9b/1//Z/9//5v/q/+r/5f/i/97/3f/e/93/4//n/+j/7v/x//P/8//v/+v/7P/q/+z/7//x//D/8f/0//f/+P/6//n/9//1//T/8//w/+//7//w/+//8f/u/+r/6v/r/+v/7P/s/+v/7P/t//L/8P/w//L/9v/3//r///8BAAIAAwADAAIABAAHAAcACAAIAAoADAAMABAAEAAQABAAEgASAA8ADwANAAsACwANAA8ADwARABEAEAAQAA4ADwAPAAsACwANAAwADAAOAA4AEAARABEAEAASABEAEQAQAA4ADgANABAAEQASABUAFgAXABgAFwAVABIADwANAA4ADwAPABIAEQARABEAEQARAAwACwAHAAQAAgD//wAAAAAAAAAA//8BAAAA/v/7//n/9P/z//P/9P/3//n/+v8AAAEAAwAAAP7//f/7//v/+v/9/wAAAwAHAAkACgAHAAcABgABAAAAAAD9//v//P/8//3//P/9//v/+P/5//f/8//x//L/7//w//H/8f/0//b/9v/2//T/8v/y//L/8f/w//H/8v/2//f/+f/7//v/+v/5//b/9f/1//j/+P/4/////v/7//r/+//9//z//P/7//v/+//6//z//P/8//3/+f/6//n/+f/7//r/+v/6//n/+v/6//7//f/8//3/+v/7//v/+v/9//7/AQADAAYABQADAAIAAQAEAAUABQAIAAoACAAJAAoACgAJAAcABgAHAAYABgAGAAcABQAEAAUABwAHAAgABQADAAIAAgAAAP3//f/+//3//P/9//3//f/+/wAA///+//3//P/9//7/AQAAAAEABAAFAAYABQAGAAUABQAFAAUABgAIAAkABgAHAAoACgALAAsADAAMAAkABwAJAAcABAAEAAUAAwADAAUABgAEAAMAAQACAAIAAAAAAP//AAABAAMAAwADAAUABAAEAAMAAQADAAMAAwAEAAQABQAGAAgACQAHAAgABwAFAAMABAACAAEAAwACAAQABQAEAAIAAQACAAIAAAD///3//f/+/////f/8//z//P/9//3//f/8//r/+v/3//j/+v/7//7///8CAAMAAgAEAAQAAwADAAIAAgADAAUABgAIAAoACQAKAAoACgAFAAUABQADAAQAAwADAAQABQAFAAUABAACAAMAAAABAAIAAgAEAAEABAAFAAUABQAIAAkABgAHAAQABQAGAAYABwAJAAsACwALAAwACQAJAAkABQAGAAcACQAMAA8ADgAMAAoACwAKAAgABwAJAAkABwAHAAYABAAEAAUABAAEAAUABgADAAQABQACAAMAAQAAAAAABAAEAAMAAgACAAIAAgD/////AgABAAIAAgABAAAA/////////f/8/////v/+//v/+v/9//v//P/6//n/+v/6//n/+v/6//f/+P/4//b/+P/2//T/9f/1//X/8//x//P/8//y//P/8//x/+7/7f/u//D/8P/v/+7/7//u/+z/7v/u/+3/7f/v/+//7//u/+3/7//v//L/9P/x//H/7//w//H/8v/x//H/8P/w/+//8P/x/+//8f/v/+7/8P/s/+7/8v/w/+//8f/x//D/8f/w/+//7f/t/+z/7P/q/+z/7//w/+7/7f/v/+//8P/u/+r/7v/r/+7/7//w//H/8f/x//H/8f/z//T/9f/1//T/9f/2//b/9f/2//j/9//4//n/9v/3//b/9f/1//j/+P/3//j/+P/4//j/+P/3//f/9//4//n/+//8//z//P/+//7//f/+//3//f8AAAEAAAABAAIAAgAEAAUAAgADAAcABQAEAAYABAAFAAcACQAJAAcACAALAAgACQAJAAsACgAJAAkACQAIAAkACQAKAAwACgAJAAkACQAJAAwACAALAAoADAANAAsADgAOAAwADAAKAAwACgAOAA4ADgAPAA4ADwALAAgACAAHAAsADgANABAADgANAA0ADwAKAAkACwAJAAkACgAIAAkACwALAAkACwAKAAsACQAIAAkACAAIAAcABwAIAAgACgAKAAYAAwACAAMABAAGAAUABQADAAQABwAEAAQABQAEAAMAAwADAAMAAwABAAAAAwACAAIAAQACAAAA//////7/+//9//z//P/+//3//v/+/wAAAAD///7///////7//v//////AAD///3//P/8//7//f/+//3//f/+//7////+//7//v///wAAAAD+//7//v////////8AAP7//f///wEAAAD/////AAD//wAAAAAAAAEA///+//7//f/+//7//v/+//3//f/8//v//f/9//7//v///wAAAQAAAAAAAgD//wEAAwACAAMABAAFAAQABAAFAAYABgAGAAcABwAGAAQABQAHAAUABgAGAAUACAAIAAgACAAHAAcABwAEAAQACAAHAAUABwAHAAgACAAEAAUABgAEAAUABAAEAAIABQACAAEAAQAEAAIABAAEAAIAAwADAAAA/v/8/////f/9//7//f/6//r/+P/6//j/+P/6//r/9f/2//b/+v/4//f/+v/3//X/9f/2//b/9f/2//b/9f/1//T/9P/1//b/9P/y//H/8P/y//H/8//x//D/8P/u/+7/7//u/+7/7f/u/+v/7P/s/+n/6//q/+r/6//q/+v/6v/s/+r/6v/r/+f/6P/q/+n/6f/p/+j/6v/q/+f/6P/o/+r/6//o/+r/6P/l/+T/5//p/+n/6//r/+n/6f/p/+r/6f/r/+v/6v/p/+v/7P/v/+z/7f/t/+v/7P/v/+3/7P/t/+3/7P/s/+//8P/x//H/8v/z//T/9P/z//T/9f/2//X/8//3//j/9v/6//j/+f/7//v/+//7//7////9//3//f8AAP//AAD//wEAAgADAAMAAwADAAMABAAGAAUABwAIAAgABgAIAAgABwAIAAkACQAJAAkACwALAAoADQAOAA0ADgAMAA4ADgAMAA0AEAARABEAEAARABIAEQAQABIAEgAPABEAEgATABIAEwAUABQAEwATABUAFAASABIAEgAUABIAEwATABMAEwATABMAEQASABAAEgAQAA8AEAAOAA4ADgAPABAADQANAAsADAALAAsADAALAAoACwAKAAoADQAKAAoACwAKAAkABwAJAAcABwAGAAYABgAFAAQABQAEAAMABQAFAAAABAADAAEA//8AAP7/AAAAAAAA/v/8//3////+//3//f/9//7//v/9//z//P/6//r/+v/5//r/+//5//j/+P/2//X/9//3//b/9//3//f/9P/0//T/8//z//X/+P/2//b/9//2//f/9f/2//b/9f/1//P/9v/2//b/+P/1//T/9P/2//f/9f/3//X/9//2//b/9//3//f/9//5//n/9//3//f/9v/3//j/+v/6//n/+v/6//z/+v/6//3//v/9//3///////7//v/7//7//P/9/wEAAwABAAEAAQACAAIABQAFAAUABQAGAAcABQAFAAgACAAIAAgABwAFAAcACQAIAAkACQAHAAcABwAJAAYABgAFAAgACAAIAAsACgAJAAkABwAHAAcACQAIAAkACQAIAAkABgAJAAkABgAGAAcABwAEAAYABgAEAAUABgAHAAUABgAFAAQABgAGAAcACAAFAAUABgAGAAUABQAFAAYABQAFAAMABAADAAUABAACAAMAAgADAAEAAAACAP//AAABAAAA///+/////v///////P/9//z//f/7//v//P/6//z//P/8//v/+f/5//n/+f/3//b/9//4//j/+P/5//f/9f/3//X/9f/1//L/9f/0//b/9f/y//T/8//0//P/8//0//P/9P/z//T/8//0//X/9P/2//j/9v/1//X/9f/1//X/9v/1//X/9//4//b/9f/3//X/9//3//b/9v/3//f/9v/3//b/9v/1//T/8//y//P/8//z//b/9//2//b/9f/1//T/9P/1//X/9f/4//f/9v/2//f/+f/4//j/+P/3//f/+P/4//n/+v/6//j/+v/7//3//v/9//////8AAAAA//8DAAEAAgAEAAEAAgAEAAUABQAFAAYABQAGAAQABgAFAAUACgAJAAkACQAIAAgABwAIAAgABwAIAAgACAAKAAoACAAKAAoACAALAAsACQAKAAkACQAJAAgABwAFAAcACAAHAAcABQAGAAcABgAHAAYABgAHAAUABQAEAAQAAwAEAAYABQAEAAEAAQADAAQABgAHAAYABAAFAAYABgAGAAQAAwAEAAMABAAFAAMABgAEAAIAAgACAAAAAAADAAIAAQADAAMAAgACAAIAAgAAAP////8AAP7//v/9//3//v/8//3////+//z//P/9//z/+//9//z/+//8//v//P/6//v/+//6//z/+//8//z/+v/5//n/+v/6//n/+//5//j/+P/2//X/9v/2//T/9f/1//X/9P/0//P/8f/y//T/9P/1//b/9f/0//X/9v/2//X/9P/0//b/9P/1//b/+P/3//b/+P/4//n/+f/3//f/9//3//j/+v/6//n/+f/6//v/+f/5//n/+v/6//j/+f/4//j/+P/4//j/+f/4//n/+f/7//r/+//7//v//P/+//z/+v/8//3//P/9//3///8AAAEAAgABAAIAAQABAAAA//8BAAAABAAFAAMABgAHAAQAAgAEAAMAAgAGAAUABgAFAAQABwAIAAgACAAJAAgABgAFAAYABwAGAAcABgAGAAYABgAHAAcABAAFAAUABQAHAAcABgAGAAYACAAHAAYACAAGAAcABwAJAAgABwAHAAcABwAHAAcABwAGAAcABQAFAAMAAgABAAIAAAD//wEAAgABAAEAAwACAAIA//8AAAAAAQAAAAAAAAABAP7/+v/9//7//f/8//v/+v/6//v/+v/7//v/+P/3//f/+P/3//b/9v/1//f/9f/2//b/9P/z//P/9P/1//T/9P/0//T/9P/0//P/9P/y//D/8v/w//D/8f/x//H/8v/x//D/8f/x//D/8f/x//H/8P/x/+//7//w/+7/7//x/+//8P/w//D/8P/v//H/8f/x//L/8f/z//L/7//w//P/8//0//X/9P/1//f/9//1//X/9f/1//T/9f/2//f/9f/2//b/9//2//X/9//4//b/9//3//f/9f/3//b/9v/3//b/9v/5//n/9//4//f/9v/2//b/9v/2//b/9v/2//b/+P/5//z//f/7//z//v/9//z//v8AAP////////////8BAAEAAAABAAEAAAACAAIAAwAAAAQABgADAAMABAAHAAYABAAIAAYABQAHAAUABwAIAAcABgAIAAcABQAHAAgABwAJAAkACQAIAAkACQAIAAoACAAIAAkACAAJAAkACgAJAAoACAAIAAkACAAJAAoACwAKAAgACAAIAAkACQAKAAsACQAJAAgACAAKAAsACwAKAAoACwAKAAkACgAKAAkACQAJAAoACQAIAAkACgAHAAcABQAHAAcABwAIAAgABwAEAAUABAAEAAUAAwAFAAUABAAEAAYABwAEAAUABQAEAAYABQAEAAQABwAGAAQABgAFAAYABQAEAAMABAAEAAMAAQACAAIAAQADAAMAAgABAAQAAwACAAIAAgABAAEAAwAEAAMAAgADAAIAAQACAAMAAQAAAP////////7//////wAA///+//7//v/+////AAABAAEAAgABAAEAAQABAAMAAQADAAMAAwAEAAAAAgAEAAIAAwADAAYAAwD//wIAAAABAAEAAQACAAIABQAGAAQABAACAAIAAgADAAMAAwAEAAQAAwABAAIAAgACAAEAAgAGAAMABQAFAAMAAQD//wIAAgACAAMAAwADAAMAAgADAAIAAQD//wEA//8AAP///f/+//7/AAD///z//v/+//z//P/8//v/9//4//b/+P/4//b/9f/0//T/8//z//P/8f/y//D/8//0//P/8//x//P/8f/x//L/8f/x//H/8f/y//H/8P/w//D/7//w//D/8f/x//D/7//v/+//7//w/+//8P/w/+7/7//w//D/8P/v/+7/8P/x//H/8P/w/+3/7f/w/+3/7v/w/+//7v/w//D/7v/v/+7/7//v//D/8v/x//D/7v/t/+3/7P/t/+3/7f/t/+7/7//y//H/7//w//D/7//y//L/8P/y//H/8P/x//L/8f/x//L/9P/z//L/8v/y//P/8//y//L/8v/0//T/8//0//P/8//y//T/9P/z//L/8v/1//T/9//4//b/9f/1//j/+P/3//b/9f/2//X/9//5//n/+f/4//j/+P/5//j/+f/8//v/+v/8//3//P/9//3//v/9//3//f/9//z//P/8//7//f/8//3//v/+//v/+v/8//v/+//8//3//P/8//3//v/8//7//v/+///////+//7////+//7/////////AAD+///////+//z//v/+//z//f/+/////v8AAP///v///wAAAQABAAIAAQAAAAMAAgACAAIAAQACAAQABAACAAQABQADAAUABgAFAAYACQAHAAUABwAHAAgACgALAAsACQAMAA4ADAAMAAsADgAMAAsADAANAA0ADgANAA0ADgAPAA4ADgAOAA4AEAAPABEAEAASABEAEAATABIAEgARABEAEgATABcAFQAUABUAFgAWABIAEQATABIAFgAWABYAGAAWABgAFwAXABQAFAAXABYAFwAXABYAFwAYABgAGAAYABkAGAAaABkAGwAaABgAGQAYABkAGAAaABoAFgAWABYAFwAYABkAGQAYABcAGQAYABYAFgAWABUAFgAXABYAFgAUABIAEwAUABMAEgASABMAEwARABEAEAAPABEADgAMAA4ADAAMAAoACwAMAA0ADAALAA0ACwALAAwACwAMAA0ADwALAAoADAAKAAkABwAGAAYABQAGAAUABQAEAAIAAwADAAIAAgABAAIAAAAAAP///f/8//3//v/8//z//f/9//3/+//6//v/+//6//n/9v/1//b/9v/2//b/9f/2//P/8v/0//L/8f/x//D/8P/w//D/8v/z//D/8f/x/+7/7//w//D/7//w//D/7//v/+7/7//v//D/7//u/+7/7f/t/+3/6//s/+7/7//t/+z/7P/t/+z/7P/v/+7/7f/u/+3/7//t/+3/7v/v/+//8P/v/+7/7v/w/+7/7f/u/+//7v/x//D/7//w/+//7//s/+r/7f/s/+z/7v/t/+z/7f/s/+z/6v/r/+z/7P/q/+v/6v/r/+z/6//r/+3/7P/s/+v/6//s/+v/7P/q/+z/7f/q/+v/7f/s/+v/6//s/+z/6//s/+z/7P/r/+n/6v/r/+z/7P/t/+3/7P/t/+z/6v/s/+v/7P/t/+3/7f/u//D/7v/t/+//6//t/+7/7f/s/+z/6//s/+3/6v/t/+z/7v/v/+z/7//u/+v/6//u/+//7//x//L/8v/x//H/9P/y//b/9v/1//T/9v/4//r/+f/4//j/+P/5//z/+f/7//r/+v/5//j/+//8//z//f/9/////v//////AAABAAMAAAD//wIAAwADAAcABAAFAAYABgAFAAYACAAJAAcABwAJAAoACgALAAsADAANABAAEAAPAA4ADgAPAA8AEAASABEAEQAQABIAEAAQABMAEQAQABEAEgARABEAEgARABIAEwAUABIAEwAUABEAEgATABMAFgATABQAEwATABMAEwATABMAFAAUABUAFQAXABcAFgAXABUAGAAYABgAFQAVABQAFQAVABUAEwAVABUAFAARABMAEgASABAADgAQAA0ADgAPABAADwAMAA4ADQAMAAwADAAOAA0ADAANAAwADAAOAAsADAAMAAwADAAKAAsACgAMAAoACQAKAAoACQALAAkACAAKAAoABgAKAAsACQAIAAcABwAIAAcACAAHAAUABgAIAAYABQAHAAYACQAIAAcABgAGAAYABgAHAAUABgAGAAQAAwACAAAAAAACAAIAAgABAAAAAgAAAAAAAAD+//////8DAAIAAAACAAEAAwAAAAEAAQD//wAA/v8AAP////8CAP7//v/+/wAA///+/////v/+//3//f/+//7////+/////v/+//3//P/8//z//v///wAAAAAAAAAAAQAAAAAAAwAFAAUABAAGAAQABAACAAAAAgAAAAAABAAGAAQAAwADAAMAAwAGAAYABQAFAAYABgAEAAQABwAHAAYABgAEAAEAAgAEAAMABQAEAAIAAgACAAMAAQAAAP//AgABAAIAAwACAAEAAAD+//7//v////7////+//7////7//7//f/7//r/+//6//b/9//2//T/9v/1//j/9v/2//X/8v/0//T/9P/2//P/9P/2//T/9P/z//P/9P/0//T/8v/y//L/9P/0//L/8//y//P/8v/w//L/7//w//D/8P/u/+3/7v/t/+7/7v/r/+3/7P/s/+r/6//r/+n/7P/r/+3/7P/r/+z/7f/s/+v/6v/s/+3/7f/u//H/7//u/+//7//x//H/7f/w/+//8f/w/+3/7//v/+//7v/v/+7/7v/t/+//7f/s/+7/7//t//H/8v/x//D/8f/w//H/8f/x//D/8f/z//X/8v/z//T/8v/0//T/8//z//T/9f/0//b/8//2//b/8//z//L/8f/x//H/8v/y//P/8//1//P/8//x//H/8f/y//f/9f/y//P/8//1//P/8//0//L/8//z//T/9v/2//f/9f/0//X/+P/4//f/+f/5//j/+f/5//3//f/+/////v/+/wAA/v///wEAAgACAAUABAAFAAUABAAFAAQABQAGAAkACAAHAAgABgAFAAUAAgAEAAQABAAGAAgABwAGAAcABwAIAAoACAAHAAcABwAHAAUACAAHAAcABAAEAAQAAgACAAQABQAGAAUABgAFAAYABgAEAAQAAwAEAAQAAgAEAAIAAgACAAIAAgACAAMAAQACAAMAAwAEAAMABAAGAAQABAAFAAQAAwAFAAcABQAFAAYABgADAAQAAgAEAAUABQAHAAUABQAHAAcABwAGAAgABgAIAAcABwAIAAgACQAJAAcACAAIAAkACwAIAAsADAAJAAkACwAJAAkACQAIAAcACAAHAAcABgAHAAoACAAKAAkACgALAAoACQAHAAgABgAHAAoACQAJAAkACgAGAAUABQAFAAcACAAIAAgACAAKAAsACQAJAAsACgAJAAsACAALAAkACQAJAAsADAAIAAkACAAHAAgACAAIAAcABgAHAAYABgAGAAcABgAFAAQABQAFAAQABAAGAAUAAwAGAAcACAAGAAUABQAIAAYABwAKAAoABwAGAAcABQAFAAcABAAGAAcACAALAAsADAAKAAkACwAIAAoABwAKAAwACQAMAA0ACgAIAAkACgAJAAoACQAJAAgACQAKAAkACgAIAAcACQAGAAMABQADAAEAAQD+//3//f/9//3//f/7//v/+//5//n/+//4//n/9//7//j/9//7//n/+v/6//r/+v/5//r/+f/8//z/+v/8//r//P/5//n/+f/5//v/+P/4//n/+//8//z//f/8//v//P/7//v/+//7//r/+//6//r/+//8//z//P/8//3//f/8//z//f/8/wAAAAD///7//v8AAAEAAgABAAAAAQAAAP//AgABAAAAAgD//wIAAQD+/wAAAAD///7//P/+//n/+/8AAPz/+P/5//n/9//2//f/9v/2//X/9v/3//b/9v/z//L/8//y//L/8f/0//L/9f/1//T/9f/4//n/+v/5//z/+P/6//n/+P/6//v//v/8/wAA/f////7//P/9//7///////3//v/+//7//P/8//7//P/8//7//f/8//7//P/8//z//P/9/////v/////////+//7//v/+//7//f/8//7//v/9//3//P/8//z//f//////AQD///7//v////3//P/7//7/+//6//z/+//7//z/+//6//n/+v/5//n/+v/6//j/+v/6//f/9//5//r/+f/3//v/+P/4//n/+f/6//v/+f/7//3/+//5//z/+//7//3//P/8//3//P/+//z////8//z////8/////f/9//z//v/7//v//f/9//7///8CAAMAAQACAAIABAAFAAYACAAHAAkACAAJAAsACgAMAAoACgAOAAoADAALAAsADAAJAAsADQAMAAkACgAMAAgACQAJAAsACgAJAAoACQAIAAYABgAHAAUACAAGAAkABwAIAAcACAAIAAUABgAEAAQABgAFAAMABAAFAAYAAgAEAAQABQACAAAAAAAAAP//AAD9//z//P/8///////+//7/AAD+//z//f/9//z//f/+/////v/8//3//v/8//3////8//3/+//7//v/+v/9//7//v8AAP3/+//8//z//P/+////AAD//////v/+//3////8//3////+/////P/9/////f8AAP//AgAAAPz/AAD8////AQACAAMAAwAEAAcABQAFAAQAAgAAAAAA/////wEA///+//r/+v/6//r/+P/3//z/9//5//v/+v/6//j/+v/7//j/+//6//r/+//5//3/+//7//f/+f/3//j/9v/1//X/9P/3//j/9f/5//f/9v/3//f/9v/1//b/9P/1//f/9v/3//f/+P/3//f/+P/3//f/9v/6//j/+v/7//j/+f/4//f/+f/2//f/+P/3//n/+P/4//v/+//5//z//P8AAP////////3/AQABAAIAAwAGAAcAAgAEAAMAAgADAAEAAAAAAAEAAQD//wEA/v/+/wAA/f/+//3//P/7//v/+//7//r/+v/7//j/+P/6//f/+v/z//X/+P/2//n/9//3//j/+P/4//n/+P/2//b/9//0//j/9v/3//b/9v/2//X/8//1//X/9P/3//f/9f/2//X/9v/3//f/9v/1//j/+P/3//f/+v/4//n//P/8//3//f/8/////P8AAAIA//8AAAAAAAACAAAA///8/////v///wQABAAEAAQABAAFAAQAAwADAAgABgAHAAkADAAJAAsADwAMAAsACgAKAAoAAwAHAAcACgAIAAgADQAKAAsACQACAAkABgAIAAgACAAGAAkACwANAAsADQAPAA4ADwANAAsACwAJAAgACwALAAoACQAMAAkACAAIAAYABQAHAAYAAQADAAIABAAEAAIAAwABAAIA//8CAAEAAQAAAP7/AAAAAPz////+//3/AgAAAAAAAQAAAP//BAAEAAMABAAIAAgABgAHAAcABgAHAAkABwAHAAgACgAGAAcABAAIAAQAAgADAAAAAgADAAAABAADAAMAAgADAAMAAQABAAAAAgAAAP//AAD/////AAD///3/+//8//z//f/6//n/+v/7//r/+P/2//j/9v/5//v//P/+/////f/+//v/+v/7//v/+//8//z/+//7//z//v/+/wEAAgABAAEAAQABAAIA//8AAAEAAQAAAAIAAQD8////+//9//7/AAAAAP///f/+//7////+/////v/8//7//f/+//z/+f/5//v//P/8//z//f/9//v//f//////AAABAP//AwACAAIAAgACAAMABAACAAMAAwACAP//AgACAAEAAgABAP/////+//3//f/+//z////9//7/AAD///r/+v/9//r/+v/7//r/+//5//f/+v/3//f/9P/2//T/8v/2//L/9P/0//L/8//w/+//8P/u/+z/6//v/+3/8P/w//D/7//v//D/7v/x//H/8v/u//D/7//y//T/8//w//L/8f/y//T/9v/1//L/8//z//T/8//3//f/+//3//j/9v/3//j/+v/6//z//P/+//z/+f/7//z/+//6//7//v/9//v//P/+//n/+f/+//v/+/////3/+//7//z/+P/6//3//P///wEA/v/9//r/+f////3/+/////3//P/+//v//f/9//7//f/8////AQAAAAMAAwAFAAIAAwABAAEABAADAAQAAwACAAUABgACAAIAAQAFAAAAAwAFAAcABwAFAAgABQAFAAMAAgADAAMAAwAEAAMAAwAAAP7////9/wIA/P///wEAAAAAAP7//v/9//3/+//8//z//P/7//z//v/+//r//P/5//r//v/6//v/+v/6//r//P/9//r/+//8//7////+//3//P/8//7//f8DAAQABgAHAAQAAQACAAAAAgABAP7//////wEAAAAAAP3//v8AAAEA/f8BAAAA///+//3//v/8//v/AgABAAYACAAGAAgACwAKAAkADQAOABAAEgAPABIAEwAUABYAFgAWABkAGQAYABkAFwAYABcAGAAXABgAGQAaABwAHwAgACEAIAAeAB0AHgAdABkAIAAdAB4AIAAeAB4AHwAdABwAGwAaABgAFwAWABUAFgAXABUAFgAcABgAFwAXABQAEwAVABUAFQAWABMAFAARABMAEgAPAA0ADwAMAAwADAAMAAwACQAJAAoACQAHAAcACAACAAIAAwAFAAIA/f/9//n/9P/u/+z/7//q/+f/6f/o/+T/4//i/+D/2//a/9j/1//T/9P/0f/S/8//z//O/83/y//J/8f/xv/D/8X/w//C/8L/v/+//8D/wf+//8P/xP/B/8H/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'

# En: 'Sure. One moment, please.' (1.72s, 24kHz 16-bit mono PCM)
FILLER_B64_EN = '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6P/1//3/BgARABsAKgAxADAALAAfABAA+//u//D/+f/9//r/BgATABwAGwAKAPn/7//0//n/9P/x/+7/8P/w/+j/5v/p//H/8f/v/+z/6f/t//L/8//z//f//f/9//j/7v/q//D//f8KABIAGQAaABwAHQAVAA8ACQAIAA0ADgANAA0ACwANABIAEgAUABIAAwD0/+j/4f/l/+r/8P/7/wsAGgAjACIAGwAXAB4AJgAsACoAHgARAAoADAAOAAgAAQAAAP//BQADAPj/8v/r//D/AAAEAAMA+f/p/97/3P/l/+//9f/6//3//f/5//D/7f/v//z/DgAdACkAJwAcABEADAANABEAEwAHAP7//v8BAAUAAwAEAAgACwAPAAoAAwD6/+//6f/k/+j/+v8JABMAFwAcACUAJAAfABcADgAHAAcA/P/s/+b/3P/h/+L/3f/b/9r/3P/i/+3/+/8CAAAAAwABAAgADwARAA4ADgAWACAALAArACkAKAAnACUAIAAYAAUA9v/v/+3/9v/5//r/+//4/wAABwACAPT/5v/h/+T/6P/w//X/9v/7/wYADAARAAkA+v/t/+H/3//b/9n/2f/W/9X/0//Z/97/2//e/+D/5v/z//z//f/7//j//v8HAA4AFAAdACUALAAyADEALgAmAB0AGgAQAAkABQD+//f/9f/x//D/9P/2//b/9P/w/+b/2f/M/8X/xf/I/8v/zP/R/9z/5P/p//D/7//v/+//6//u//P/9f/+/wUADgAcACEAIAAVAAYA///6//7/AQD+//v/+v8CABAAFgAWABQADgAOAA4ACgAEAPf/8P/v//r/BwAQABMABQD2/+r/4//m/+D/4//p//D/AAAIABMAGgAgACUAJwAqACcAJAAdABEADwALAAoADQATACEALQAzADMAJwAWAAMA8v/l/97/3v/j/+j/9P/9//7/AgAAAPj/8//n/9r/0P/I/8z/2f/k//H//f8HABQAHwAgABsAFwAQAA0ACQADAP//AAABAAQADQAUABgAHgAcABkAHgAgACAAGgARAAwACAAPABQAGwAiAB8AHgAaABEABQD2/+n/4P/e/9z/3P/h/+P/7P/3//7/AQADAP7/9//0//T/9P/x/+3/6v/x//v/BgALAA0ADQAOABIADwALAAYAAQD9//z/AwAMABIAGQAfAB4AHgAdAB0AHgATAAYA+//u/+b/4f/i/+f/6P/p/+n/6P/k/+L/3f/c/97/5P/q/+7/7v/u//L/9v/7/wEABAAHAA0ADQANAA8AEQAOAA4ADQAJAAUA///7//v//P8BAAYABwAQABcAGgAcABkAFAARABEADwAMAAcABAACAAQABQAGAAIA9//q/97/2v/b/9z/3f/f/+P/6//w/+//6//n/+T/4//q//f///8EAAkADQAUABoAHgAeABcAEwAPAA0ACwAHAAcAAgAAAAQABgAEAP7/8//o/+X/5f/h/93/2v/b/+P/7f/3//j/+v/6//j///8GAAoACQADAPz//P/9/////f///////v8CAAIAAQD+//n/9v/1//b/9//6/wAACAASAB4AKAArACgAIAASAAgA/P/u/+H/2P/U/9j/3f/n/+7/7//w//L/8P/u/+z/5v/l/+b/6f/v//P/+P/+/wMABQAGAAgABgAEAAcABgAKAAsACAAGAAQAAwADAAQAAwAGAAkACwATABYAFQATAAsAAAD0/+v/4//b/9n/1v/a/+D/4//p/+v/7P/t//H/9P/3/wAABAAKABAAEgAXABkAGQAYABMAEwARABMAFAAXABsAHQAjACEAHQAVAAsACQAEAAAA///3//P/8f/0//r/+v/7//T/7f/q/+b/5P/c/9f/2f/e/+v/9P/6//z//v8CAAcAEgAXABsAHwAkACsAMQAyAC8ALAApACUAIwAcABQAEQAMAA8ADgAOAAsABAD4/+//5v/b/9L/yP/B/8H/x//O/9f/3P/d/97/3f/d/97/3//j/+D/4P/k/+f/7v/3/wAABQAKAA4ADwASABIAFAAaABwAHAAdABsAFAANAA0ADAAOABQAGwAkACgAKQAmACEAHQAUAAcA+v/r/+L/3P/a/9n/1v/V/9v/4v/q//D/8//x//H/8v/x//b/9//8/wMADwAWABoAHgAbABoAGAARAAoABwAEAAEAAQAEAAQABgAIAAkACgAIAAgAAgD+//n/9P/4//b/9P/0//L/9f/2//X/9P/y/+//7f/t/+v/6v/n/+L/4v/i/+X/5//p//P/+/8CAAkADAAQABIAFQAbABwAHgAeABsAFwARABAAFgAdACEAIQAfAB0AGgAVAA4ABQD7//b/8f/s/+n/4//d/93/4f/m//H/9P/1//j/+v/9//7//v/6//f/9P/0//T/+P/1//H/9P/5/wMADgAXABgAEwAOAAgAAAD5//P/9P/4//v/AQAIAAwAEAASABcAHQAgAB4AGwAZABIADAAJAAUAAwADAAUABAAEAAIA/f/6//T/8v/y//H/8f/u/+3/6v/n/+P/4P/d/+D/4v/h/+T/6//y//j//P8AAAUABwALAA4ADgAPABEAEgATABIADwAOAAsACgAIAAYAAwD8//v/9//4//r/+v/6//z/+//1//H/7v/p/+n/7//z//r/AQALABEAEQATABAADQAHAAQAAAD4//b/8v/s/+r/6//p/+X/5//n/+v/7v/w//H/8f/1//j/+v8DAAUABgAHAAoADAAQABUAEwAWABkAFgAUAA4ABgAAAPn/9//0//X/9v/2//X/8v/1//b/9P/y//D/8f/v//D/8v/0//n///8CAAUACAALABEAEgAUABgAGAAYABkAHAAaABQACwACAP///f/8//z/+v/4//n//P/9//r/9f/x/+7/7f/x//L/9f/1//j/AgAJAA8AEwAUABIADQALAAcAAwACAP///v8BAAMAAwADAAUABwAHAAYABQAFAAIAAgABAP3//P/4//X/9//5//7/AwAFAAoADgASABcAFQATABIADQAKAAUA///7//j/+P/9/wEABAAHAAYAAAABAAAA+v/2//L/8f/w//P/9P/0//P/8f/z//b/+/8DAAgACwAMAA8AEQAOAAoABAD9//b/8//s/+P/3v/a/9z/4v/k/+r/8v/2//r//v////7//f////7/AQADAAYACQALABAAEwAYABkAGQAaABcAEwAQAAwAAQD3//L/7//r/+n/6//s/+z/8P/x/+//7P/r/+r/6//r/+z/7v/w//H/8//1//b/+P/2//X/9v/0//T/9P/2//f/+P/8/wEABwAIAAsADAAKAAoACQAJAAsACwAQABMAFAATABAAEQANAAkACQAFAAEA/v/8//f/8v/u/+r/6v/p/+j/5f/k/+T/4v/i/+X/6//x//X/+//9/wEABgAHAAkACgALAA0ADwARABEAEgASABEAEgAPABAADwAMAAsACQAGAAAA/v/8//f/9f/1//P/8v/0//X/+f/8//z//f/9/wAAAQAAAAAAAAAFAAoADAAMAAoACQAIAAoADQAMAAsACAAHAAkABgADAAIA/v/9//3//v////z//P///wIABQAIAAwADQANAAoABgABAPr/9//z//P/9f/2//f//P8AAAEAAgAEAAMAAQD//wEA/v/8//v/+P/5//3/AQAEAAUABwAIAAoADQALAAwADAAJAAkABgADAAEAAAAAAAEAAwAFAAgACAAGAAcABQADAP///P/5//T/9P/w/+7/7v/t/+3/7P/u//T/9//+/wEAAwAGAAYABQACAAAA/v/9//j/9P/w/+v/6//u/+z/8f/4//v///8AAAIAAgD//wAA////////AAABAAMABQAIAA4AEgAWABcAGQAXABQAEwAMAAIA+v/1/+7/6//r/+v/7f/u//L/9P/0//X/9//0//H/9f/z//P/9f/0//P/9//5//n/+//7//3//////wEABgAFAAMAAwADAAQABgAHAAYABgAHAAkACwAKAAwADgALAAoACAAEAP///P/3//X/9f/y//D/7v/u/+7/7f/t/+v/7v/t/+//7//v/+3/7//y//X/+f/+////AQAHAAkACwAOABAAEgAVABcAGAAZABgAFwAYABQAEQAPAAsACQAEAAAA+//3//X/8f/w//H/8P/t/+3/7f/v//L/8f/z//T/9v/3//j/+v/6//z/AgAGAAgACAAIAAkADAANAA4AEAAOAA4ADgANAAoABgADAAMAAQADAAQABwAJAAwADQANAA8ADgAMAAcAAwD///j/8v/u/+r/6P/o/+r/6//s//D/8f/0//X/9P/y//P/9f/z//f/+P/6//3/AQAHAAwADwAPABIAFgAVABUAFgATABAADgALAAsACQAHAAgABQACAAEAAQD7//n/+P/0//X/8v/u/+v/6//r/+j/6v/p/+z/7//x//X/+P/8////BQAJAAoADgAOAA4ADgAOAA4ADgAMAAgABAAEAAQABAAFAAkACQAMAA8AEAAPAAwACwAMAAwACwALAAgABQABAAIABAAEAAUABQAEAAEA/v/9//j/9P/v/+z/6//r/+z/6//s/+3/8P/0//j//P8AAAEAAwAGAAcACAAKAAsACQAKAAwADQAMAAwADQAKAAoACQAJAAgABgADAAAA/P/5//X/8f/u/+3/7f/u/+3/7//w/+//8f/z//P/8v/0//L/8//0//P/8f/x//H/8//1//f/+P/5//z//v/+/wAAAgACAAIABAADAAMAAgADAAQABgAJAAkACwAPABEADwAQABEADgAKAAYAAgD+//v/+P/1//P/8v/y//D/8f/v/+7/7//t/+z/7P/v//H/8//y//P/9P/4//j/+v/+/wIAAwAGAAgABgAIAAgACAAJAAgACwAJAAcABgADAAIAAgAAAP7///8BAAIABAAIAAgABwAGAAUAAgABAP//+f/4//X/8v/z//P/8v/w//L/8//x//H/8v/x//P/9P/0//X/9f/6//v//v8BAAQABwAKAA8ADwAOAA8ADwAQAA0ADQANAAkABwAFAAIAAAD9//r/+P/3//b/9v/2//X/9//2//b/9f/2//X/9v/4//f/9//7//v//P/9////BAADAAMAAQACAAEA/v////7//v/9////AAACAAIABQAHAAoADAANABAAEAARABIAEgARAA4ACwAKAAkABgADAAEA/f/9//3/+//9//r/+f/3//T/8//x/+//8P/y//D/8v/1//f/+P/7////AQADAAcACgAKAAkABwAFAAUABQAEAAIAAAD///7//v/8//3//P/6//r/+//8//v/+v/5//r/+P/3//f/9//3//f/9v/5//j/9f/2//X/9v/3//X/9//1//X/9f/2//f/+P/4//n/+P/6//r//f/9////AQADAAMAAwAFAAYABQAHAAYABwAHAAgACwAKAAoACwAKAAoABwAFAAUABQAFAAEAAAD+//j/9f/1//L/8//0//P/9P/1//X/9//5//n/+v/8////AAACAAIAAwAEAAcABgAGAAkACwANAA0ACwALAAkACAALAAoACAAIAAYABAACAP//AAD+//z//P/+///////+/////f8AAP//AAD//wEAAAD+//3//v///////v/+////AQACAP7//v///wAA/////wAAAAD+//7//v////7//f///wEABAAEAAMAAwADAAUABAAGAAUABQADAAQAAwACAAIAAQACAAIAAQAAAAEA///8//3//f/9//v/+v/7//v/+v/6//v/+v/6//z//v///wIAAgAEAAQABAAFAAQABgADAAMAAgADAAIAAAAAAPv/+v/6//n/+v/6//r/+f/6//r/+v/8//3/////////AgADAAEAAQACAAQABgAIAAYABgAGAAYABwAFAAEAAAAAAP7//f/+//z/+//6//v//P/7//r//P/6//j//P/8//z//f/7//r//P/9//v//P/8//z//P/8//r//f/6//j/+P/5//j/+v/5//n/+//6//3/AAD//wEAAwADAAQABAAEAAIAAgD/////AAD+//7//P/8//r/+f/5//f/+v/3//j/+v/4//f/+P/6//v/+//9//z//f8AAP7///8AAAEA//8AAAEAAgADAAMAAwAGAAQAAgADAAMAAwACAAIAAAD//wEA/f/+/////f/7//r/+f/5//n/+P/5//n/+v/4//j/+P/3//n//f/////////+//7/AAD//wEABAADAAMABwAFAAYABgAFAAcABAAFAAUABQAFAAYABAAEAAYABgAGAAYABgAGAAQAAgAAAP7//P/8//z/+v/5//n/+f/4//r/+v/4//r/+//6//v//P/7//r//f/+//7//////wEAAwABAAEABQAFAAMAAwADAAQAAwAEAAUABQAFAAUACAAFAAQABAADAAQABAACAAEAAgABAP7////+//7//P/7//z//P/8//z//v///wAAAAAAAAEAAQAAAAIAAgADAAEAAQACAAIAAAAAAAIAAgAAAAAAAAABAP7///8CAAAAAgAAAAIAAgD+/////////wAAAAABAAEAAwAEAAMAAwABAAIAAAD//wAA/v////3//P/7//v/+//8//n/+v/9//v//P/8//z//P/8//7//v/8//3//v/9//z//P/8//z/+//6//v/+//8//z/+v/6//n/+//7//r//f/8//v//P/9//3/+//9//v/+//9//r/+//7//r/+v/5//n/+P/4//j/+P/5//n/+v/6//r/+v/6//z/+v/5//z/+//7//v//P/9//z//P/9///////+/wAAAgD/////AAABAAEAAQABAP7////9//7////9//z//P/9//7//v/9//7//f/+//v/+//8//v//P/9/////v/9//3//f/+//3///8BAAAAAAACAAIAAQAAAAAAAQAAAAAAAAAAAAAAAAD//wAAAAABAAEAAQACAAIAAAD//////v/8//3//v/9//3//P/9//z//v/9//z//f////7/AAAAAP7//f/+/////v////7//v8AAP3//v8BAAEA/v/+//////8AAP//AQABAAEAAQADAAIAAQABAAIAAwACAAEAAgADAAMAAQACAAMAAwACAAEAAQACAAEAAgADAAIAAgACAAIAAwACAAEAAgADAAIAAwABAAMAAwAAAAAAAgACAAAA//8AAAAA/f/+/wAA///+//3///////3//P/8//3//f/8//z//v/+/wAAAQAAAAAAAgABAP//AQACAAEAAQABAAIAAQABAAMAAQABAAMAAAAAAAAAAAD///////////7//v////7//P/7//z//P/5//r/+//5//v/+f/5//n/+P/5//j/+f/5//r/+f/6//3//f/9//7//P/+//3//f/9//3//////wAA/////wAA/v/+/wAA///+/wAAAAAAAP//AAD+//z//v/8//z//v/+//3//P/9//z//P/7//v//f/9//3//f/7//3//f/9//3//v////3//v/+//3//f/9//3//v////3///8AAP/////9/////f/8//3//v////7//v/+/////v/+/wAA/////wAAAAD+/wAAAQACAAAA//8AAAAAAQACAAAAAAAAAP//AAD+/wAAAQABAAIAAQACAAEAAAABAAEAAgACAAEAAAABAAEA//8BAAAAAAABAAEAAAAAAAAA///+//3//v///wAA/////wAAAAABAAAAAAD/////AAD//wAAAQAAAAAAAAAAAAAA/v8BAAAA/v///wAAAAD//wAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAEAAAABAAIAAgABAAAAAQABAAEAAgACAAIAAgACAAEAAQAAAAEAAAAAAAAA///+////AAAAAP//AAAAAP7//f/9//3//f/8//v//f/9//3//f////7//P/9//3//P/9//7///////7////+//7////+//////////7//P/9//3//f/7//v//f/8//z//f/8//r/+//8//n//P/9//z/+//5//v/+v/6//v/+v/6//z//f/8//v//f/8//7//f/8//3//f/+//7//v/9//7//v/8//z//P/7//z//f/+//7//f/9//3//P/7//v/+//6//v//v/8//v/+//7//v/+f/6//r/+f/5//j/+v/5//n/+//5//n/+f/6//r/+f/6//n/+v/6//v//P/9//7//f/9//z/+//7//v/+//7//z//f/9//z//P/8//3//P/8//3//v/+//3//v/8//z//P/5//v/+//6//z//f/9//v//P/+//7/AAD///////////7//P/+///////9//3//f/8//z//v/9//7//v/+//3//f8AAP///v///wAAAAD+/////v/9//7//v/9//7////+//7//v/+//7//P/+/////v/+////AAD9////AAD+////AAABAAAAAQAAAAAAAQABAAIAAQACAAIABAADAAEAAgACAAMAAgACAAIAAgACAAMAAgABAAIAAgADAAEAAQACAAIAAgAEAAMAAwACAAIAAgADAAMAAgACAAIAAgABAAIAAgACAAMAAwAEAAMAAgACAAMAAwADAAMABAAFAAQAAwACAAIAAgADAAIAAgABAAAAAQABAAEAAAD+/wAAAAAAAAAAAAABAAEAAgABAAEAAgACAAMAAgADAAMAAgABAAEAAgACAAEAAgABAAEAAgACAAIAAAACAAEAAgABAAEAAgACAAIAAAAAAP////////7//v/+//7////+/wAAAAD+///////+//7//v///////v////7//f/+////AQD/////AAD/////AAAAAAAAAAAAAP7///8BAAEAAgABAAEAAQABAAIAAQACAAEAAgACAAAAAQABAAEAAQABAAAA//8AAAAA/////wAAAgABAAAAAAAAAP7//v/+//3//P/9//z//f////3//f/9/////f/+/////f////3//f/+//7//f/7//3//f/8//z//P/9//7//v/+//3//v////7//v/+//7//v/9//7//v/9//v//P/9//3///8AAP7//f//////AAAAAP//////////AAAAAAAAAQAAAAAAAAABAAAA/////wAAAAABAAEAAAAAAAAAAgABAAEAAQACAAAA/v8AAAAAAAAAAAAAAQABAAAAAAD//wAAAAABAAEA//8BAAEAAgAAAAEA//8AAAEAAQABAAEAAQAAAAAAAQADAAEAAQABAAEAAQABAP//////////AAAAAAAA///9//7//P/8//3//P/8//v//P/9//7//v////3//f/+//7//v/+//3//v/+//3//v8AAP///P/9//3//f/9//z//v/8//3//f/8//z/+v/7//r/+v/7//r/+//5//r/+v/5//n/+//7//v/+v/5//n/+//6//r//P/8//z/+v/8//v//P/9//v//P/9//3//v/+//7//P/9//7///8AAP//AAD///7//////////v8AAP////8AAAEAAAABAAAAAAAAAAEAAAD//wIAAAD//////v///wAA/f/+///////////////+/////v///////f//////AAD9//z/AAD///////////////8AAAAAAAAAAAAAAAD//wEA///+//7///////3//f/9//3//P/9//3//f/8//z//f/8//3//P/7//z//P/7//z//f/8//z//f/+//7//f/9//7//v///////f/9//7///8AAAAA/v/9//3//f/9///////+/////v///////v///wAA/v/+////AAD//wAAAAAAAP//AAAAAP7//f/+////AAD/////AAAAAAEA///////////+////AQD///7//////wAA//8AAAAAAQAAAAAA//8AAP////////////8BAAAAAAAAAAAA//8BAAEA/////wAAAQABAAAAAAD///////8AAAEAAAAAAAEAAQAAAP////////////////7//v/+//7///////7//v8BAP///f/+//7///8AAAAAAAD/////AAABAAAAAQABAAEAAAAAAAEAAQABAAIAAQACAAIAAgABAAAAAQACAAAAAQD/////AAAAAAEAAgAAAP//AAABAAEAAgAAAAAAAAD//wAA/v///////v/+//7//f/+//7//v//////////////AAAAAP///v/9//7////////////+//7//v8AAAAA/////wAA///+/wAAAAD///7//v////7//////////v///wAA/v////7//f/+//3//f/9//3/+//7//z/+//6//v/+//7//v//P/7//r/+//5//n/+//7//v/+v/7//z/+//7//v//f/8//3//v/9//3//v8AAP////8AAP7////+//7//v/+//7//v/+//z/+//9//7//f/9//3//v/9//3//f/9//z//f/+//z//f/+//7///////3////+/////v/8//v//P/9//3//f/9/////P/9//7//f/9//3//f/8//v//P/+/////P/8//z/+//7//v/+//7//v//P/7//v/+//7//z//P/7//r/+v/5//r/+f/5//j/+f/7//r/+f/5//r/+v/4//r/+f/5//j/+P/6//j/+P/5//n/+f/6//r/+P/6//v/+v/5//r/+v/5//z/+//7//r/+//8//v/+f/7//v/+v/7//v/+//8//v/+v/6//v/+//7//r/+v/7//v/+//6//r/+//7//r/+v/6//r/+f/5//n/+v/7//n/+f/8//z/+v/7//3//f/8//3//f/9//3//P/8//7//v/9//7//v/+/////v/+/wAA/v8AAAAA/v8AAP//AQD//wAAAQD//wAAAQAAAP//AAD//wAAAAD+/wAA/////wAA//8BAAAA/v/+/////////wAAAAABAAAA//8CAAAAAQABAAEA//8BAAEAAgACAAEAAQAAAAAAAgAAAAEAAQAAAAAA//8AAAEAAQABAAEAAgAAAAAAAQABAAIAAgABAAAAAgADAAEAAwADAAMAAwADAAIAAwAEAAQAAwACAAQABAAEAAMABAAFAAUABgAGAAUABAADAAQAAwADAAQAAwACAAIABAACAAEAAwADAAEAAgADAAIAAgADAAIAAgADAAMAAwADAAMAAwADAAIAAgADAAEAAQACAAMAAwACAAMABAAEAAQABAAEAAQABQAEAAQABAAEAAQABAADAAIAAgADAAQABAADAAMABAABAAAAAgABAAAAAAAAAAIAAQAAAAEAAgABAAAAAQABAAAAAQACAAMAAwABAAMAAgACAAMAAQACAAIAAgACAAEAAgACAAMAAQAAAAIAAAAAAAEAAAAAAAIAAQD//wEAAgAAAP///v/+//7//v////7//f///wEAAAD//wEAAAABAAAA//8AAP///////////v///////v/+//7//P/9//3//v/+//3//f/9//z/+//7//v/+//8//3//P/6//r/+v/7//n/+f/6//j/+f/3//r/+f/4//n/9//3//j/+f/5//j/+v/4//n/+P/5//r/+v/7//v//P/8//v//P/8//z//f/9//7//v/9//3//f/+//7//v/////////+/////f/9//z/+v/7//v/+//8//7////9//7//////wEAAAD///////////3//////////f/+//7//v/9//7/AAAAAAEAAQABAAAAAgABAAIAAgADAAQAAgACAAIAAgADAAMAAwAEAAYABAAFAAcABgAGAAYABwAIAAcABwAIAAgABgAHAAgABgAGAAcACAAGAAcABgAHAAcABwAHAAYACAAIAAkACAAGAAgACAAHAAgACAAIAAgACAAIAAgACAAIAAoACQAIAAkACgAKAAkADAAKAAoACgAIAAkACQAIAAgACQAJAAkACQAIAAgACAAHAAgACAAGAAYABgAGAAUABgAFAAQABAACAAIAAQABAAIAAQACAAMAAgACAAMAAgACAAIAAQABAAAA///////////////////8//3//f/9//7//f/+//7///8AAP7////+//7//v/9//7//v8AAP3//f////7//v/+//////////////8AAAAA/v8BAAEAAAD//////v/+/wAA/v/+/wAA//8AAP7/AAD/////AAD//wEAAAABAAAA/////////v/9////AAAAAP//AAD+///////+//7//f/9//z//v/7//r/+//6//r/+v/4//n/+f/5//j/9//4//f/+P/3//b/9//3//j/9//2//X/9P/2//b/9v/2//b/9v/3//b/9//4//j/+P/4//f/+P/3//j/+P/3//j/9//2//j/+P/5//r/+f/6//n/+v/6//v/+//8//z//P/7//r/+//8//v//P/9//z//P/8//v//f/8//z//f/7//v//P/7//v/+//6//r/+v/4//j/+f/4//j/+P/2//f/9v/1//b/9v/0//T/9P/0//X/9f/2//b/9v/3//X/9//3//X/+P/3//j/+f/5//j/9//5//f/9//3//f/+P/4//j/9//5//r//P/8/////v8AAP///f/9//v//P/8//z/+//7//n/9//4//b/9f/z//T/9P/1//T/9v/5//f/9//6//r/+P/6//v//f/8//7//f/9//z/+f/7//r/+f/5//n/+P/3//b/9f/0//T/8//w//D/7v/s/+z/6v/p/+f/5//j/+T/4//i/+H/4f/h/+L/4//l/+f/7P/u//L/9v/7/wAABQAMABIAGgAhACgALwA2ADwAQABLAFEAVQBeAGQAawBwAHYAfACBAIUAiQCPAJMAlQCXAJkAmwCbAJsAngCdAJ0AnACZAJkAlgCTAJIAjwCLAIgAhAB+AHgAdABtAGgAYwBdAFYAUABLAEUAPwA7ADUAMQArACgAIQAfABUADwAOAAQA/v/2/+3/6f/f/9r/0v/M/8L/u/+z/6v/o/+a/5L/iv+C/3b/cP9k/1z/VP9J/0X/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wv++/8D/x//O/9P/1f/V/9P/yP+4/7H/s/+6/87/3P/1/wkAGgAgABsAFgANAAgAAgAAAP3/BQAMABEAEQALAA8ADgALAAYA///x/+b/3v/a/9n/3P/n/+7/+f///wIA+v/v/+j/3v/U/8v/zv/O/87/zf/N/9H/0v/U/9f/2f/W/9T/0//T/9X/2//j/+n/7P/s/+//7v/w//D/6//k/+L/5P/p//H/8//z/+z/6f/l/97/1v/J/7v/rv+q/6r/rv+w/6//rf+s/63/rf+p/6X/oP+c/5//qv+2/8L/zf/Z/+D/4P/h/+D/3//j/+n/8v/8/wgADwAUABkAGQAWABMADwAOAA8AFAAaAB0AIAAgAB4AGQAXABcAEQAQABAAEAAOAA0ADgALAAoACAADAP7//P/4//L/6//l/93/2f/X/9L/zv/G/77/u/+3/7f/uP+2/7b/tf+2/7f/uv+8/73/wP/F/8v/0P/W/93/4f/j/+P/5f/n/+b/6f/s/+7/9P/3//r/+//6//X/7v/r/+P/4f/d/9f/1f/U/9P/0//U/9b/1f/U/9T/0//T/9L/0v/Q/9D/0//U/9v/3v/e/97/3f/g/+H/4//g/+L/5P/j/+j/6//r/+v/6//q/+z/8f/y//X/+f/8//7/AQAEAAcACAAJAAoACwAQABQAGQAeACEAIwAmACYAJwAlACkAJQAlACMAJAAkACEAJQAlACYAIAAeAB8AHgAdABwAGwAZABcAFQAVABAADwANAA0ADAAOAA8ADwATABEAEgAUABQAFgAVABkAHAAdAB8AIgAlACQAJwApACwAMQAxADEAMgAyADEAMgAvAC8ALAAtACwAKgAqACgAJQAjAB4AGgAZABUAEgAQAA8ADQAMAA0ADAALAAsACgAFAAQAAQD+//7//f/+/wAAAQAEAAQABwAKAAgACQAKAAsACgAKAAkACAALAAsADgAPAA8ADwAPABAADQAPABEADQANAA0ADAAKAAgACQAIAAQAAwACAAAAAAABAP///v/+//7//P/6//j/+f/2//n/+//5//r//P/9//r/+v/4//j/+v/5//n//P/+//7//v/+//3///8AAAAAAQACAAIA/v/+//z/+f/6//r//v/+//v/+f/5//n/+f/4//b/9P/0//f/9//2//j/+f/2//j/+f/3//b/9v/3//b/9//4//j/+//8//r//f///wEA/v///wAA//8CAAMABgAGAAwADQAMAA0ADgAOAAsACwALAA0AEAAPAA0ADQAOAA8ADwANAA0ADQAMAAsACgAKAAoACgAIAAgABQAEAAMAAQABAP///f/9//3/+//6//v/+f/4//j/+P/4//n/+f/5//n/+P/2//b/9P/2//b/9//5//n/9//3//b/9//2//f/+P/3//b/9f/3//b/+P/2//X/9v/0//P/8v/z//L/7//w//D/7v/u/+3/7v/u/+r/5//p/+n/6f/q/+r/6v/r/+z/6v/m/+X/5P/i/9//4f/h/+D/4f/j/+P/4v/i/+P/4//i/+P/4f/g/+D/3//f/+H/4v/i/+P/4//k/+P/4v/j/+T/4//h/+X/5P/h/+P/4f/h/+H/4P/h/+L/4v/i/+H/4P/h/+P/5f/l/+T/4v/k/+X/5//n/+f/6f/s/+3/7v/v//L/7//x//X/8//0//T/+P/3//f/+f/5//n/+v/7//z//v/+//z//P/9//v//f/8//7////+/////v8AAAEAAQADAAEAAAD//wAAAgADAAIAAQACAAMABgAHAAgACAAJAAwACwALAA0ADAALAA4AEAAPABEAEwAUABMAFQATABMAEgASABEAEAASABMAFAAUABIAFAAVABYAFAAUABQAEwAUABQAFAASABIAEgAQABAAEAAQAA8ADgAPABAAEwATABMAEwATABIAEAAPABAADwASABIAEQASABIAFAATABIAEgASABMAEAASABMAEgARABAAEQARABIAEQAPAA4ADAAMAAwADQALAAoACgAIAAcABgAGAAgABwAEAAYABQADAAMAAgACAAEAAgABAAAAAAAAAAIAAQACAAEAAAACAAQAAQD//wAA//////////8AAAAA/////wAAAAD//wAA///+//7////+//7//v/9//z//P/9//z/+//8//z/+//9//v/+f/5//n/+f/7//r/+v/6//n/+v/6//v/+v/5//v/+v/5//r/+v/7//z//f/+//r/+//8//z//f/7//z/+//+//7//P/+//7////9//3/AAD+//////8CAAMAAgAFAAIAAAABAAEAAgABAAMABQAHAAkACAAJAAkACAAJAAcACQAIAAoACQAIAAwADAAKAAgACQAIAAgACgAIAAgABwAGAAYAAwACAAIAAAADAAIAAQACAAMAAgADAAIA/////wEAAAAAAAAA///+//3//v/9//7///////////8AAP///f/9//3//v/9////AAD+//7//f/+/////v/9//3//P/8//z/+//6//r/+v/6//n/+f/5//j/9v/2//f/9f/0//T/9P/z//L/8v/x/+//8f/w/+//8f/y//L/8f/0//T/9P/0//X/9//1//X/9f/2//b/9f/0//P/8//1//P/9P/z//P/9P/z//P/8v/z//T/8//z//P/8//x/+//8P/w//D/8P/v/+//8P/x/+//8P/x//D/8P/w//D/8f/y//D/7//v/+3/7//v//D/8f/v//D/7//u//D/8P/w//D/8P/x//H/8f/y//P/8f/y//L/8v/z//L/8//z//L/9P/0//P/9f/0//X/9P/z//P/9P/1//X/9v/2//f/+P/5//r/+f/5//v/+v/6//z/+//8//v//P/+//3//P/9//7//f/+/////P/9//3//P/7//z//f/9///////9//7//v/9//v/+//8//3//P/9//z//f/9//z//P/9//3//f/9//z//f///wAAAQAAAAEAAgACAAQABAAEAAUABQAFAAYABwAIAAUABwAJAAgACAAJAAsADAALAAwADAALAAoACQAJAAkACgAKAAkACgAIAAkACQAHAAoACQAJAAgABgAIAAcABwAFAAYABgAEAAQABAAEAAMAAwABAAIAAwAAAAAAAQABAAIAAwAEAAIAAQD//wIAAgACAAQABAAFAAMABAAGAAUABwAIAAcABgAIAAkACQAIAAcABwAFAAYACAAGAAUABQAFAAYABAAGAAYABAAGAAUABQAFAAMABAAFAAUABQAEAAIABQAGAAQABwAGAAYABwAFAAYABgAHAAcABwAGAAcACQAIAAgACAAJAAgACQAKAAoACQAIAAgABwAJAAkACQAJAAkACQAJAAgACQAMAAoACwAMAAsACwALAAwACwAMAAwADAAMAAsACwALAAwADAAMAAkACQAKAAkACgAKAAoACgAJAAkACQAIAAgACQAHAAcABwAIAAcABgAGAAUABQAGAAYABwAHAAcABwAFAAUABQAGAAUABgAFAAYABgAGAAYABQAHAAUABQAFAAMABAAEAAYABgAEAAQABQADAAQABAADAAMAAgABAP//AAAAAAAA///+/////v/9//3//f/7//3//P/5//z//f/6//j/9//4//j/9v/2//P/8v/0//X/9P/2//f/9v/4//b/9v/2//T/9v/1//X/9P/1//X/9P/y//T/8//z//T/9v/1//X/9v/1//P/8v/y//D/8f/y//T/8v/y//L/8f/y//D/8f/y//H/8v/x//P/8//y//P/8f/w//H/8v/x//H/8v/x//L/8f/w//H/8P/x//D/8f/x//D/8f/x//D/8v/y//P/8v/y//L/8//1//T/9f/2//f/9//0//f/9f/0//T/8v/z//L/8v/z//X/9f/z//P/9f/0//b/9v/1//X/9v/1//X/9//3//f/9f/1//X/9P/0//f/9//4//j/9//4//f/9//3//f/9//4//f/9v/2//b/9v/0//X/9v/2//f/9v/2//X/9f/0//P/9v/1//X/9v/0//b/9f/3//j/9//5//j/+P/4//j/9//3//f/+P/5//n/+f/6//v/+//6//r/+f/6//r/+f/6//n/+v/6//n/+f/6//r/+//6//z//f/7//v/+//5//n/+f/4//j/+P/2//f/9v/3//j/9//5//n/+f/7//r/+//6//n/+v/5//n/+f/6//r/+//7//r/+f/6//n/+f/5//n/+P/5//v/+P/6//3/+//8//v/+v/6//v//P/7//7//f/8//z//v////3//v/9//z//v/9//3//f/+//7/////////AAABAP7///8AAP7//v///wAA///+//////8CAAAAAQACAAMABQAEAAQABAADAAUAAwAFAAUABQAIAAkACgAHAAgABwAGAAgABQAJAAgABwAKAAoACwAHAAgACQAIAAoACQAJAAkACgAJAAgACQAIAAYACgAKAAgACQAKAAsACgAJAAgABwAKAAkACwAIAAgACQAKAAsACQAJAAgACQAKAAkACgALAAwADQAQAA4ADwAQAA0ADwARAAkACQASAAoAEAAJAAQABwAMAA0ACAAGAAMACQAIAAkABwADAAUABAACAAIAAwACAAUACgAFAAcACQALAAsAEAAGAAoAEgANAAUA/v8HABEAIQANAP//BAD//w8AEAAGAAYABgAKAA8ACwANAAcADgAGAAUACQAKAAoACQD8/wQABAD8//7/9/8JAAUA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/v8AAPz/+f/9//v//P/7//v//P/9//7/AAABAP3//v/9//7//v/8//v//P/+//7/////////AQD//wEAAQAAAP7////+////AAD//wEA//8AAAAAAwD///3//v///////v////7//v/////////////////////////+////AAD///7////+//3//f/+/////v/9//7//v/+//7//v/9//7///////7//v/+//7//v////7//v/////////+//7//v/+//7//v/////////////////+//7//v/+///////+//7//v/+//7//v///////v///wAA//////////////7//v///////v//////AAD////////+/////////////v///////////////////////v////////////7//v/+/////////////////////////////////////////////v/+//7///////////////////////////////////////7//v/+/////v///////////////////////////////v/+//7////+//7////////////////////+//7//////////v/+/////////////v/+//7/////////////////////////////////////////AAD////////+//7///////////////////////////////////////////////7//////////////////////////////////////////////////////////////////////////////////v/////////////////////////////////////////+//7//v///////////////////////////////////////////////////////////////////////////////////////////////////////v/+//7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v/+//////////////////7//v///////////////////////////////v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7//v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wAA///+/wAA//8AAAEA/v8BAA=='

FILLERS = {
    "hi": base64.b64decode(FILLER_B64_HI),
    "en": base64.b64decode(FILLER_B64_EN)
}
prog("FILLERS ready " + " ".join(f"{k}={len(v) / float((OUT_SR or SR) * 2):.2f}s" for k, v in FILLERS.items()))
# ---------- 5a. DUAL GPU XTTS (v83) ----------
# GPU 0: XTTS (m). GPU 1: Whisper STT (~1GB) + XTTS m2 (~3-4GB) = ~4-5GB of 16GB, very safe.
# LLM is API-only (Nvidia/Nemotron) -- it does NOT use local GPU. GPU 1 is nearly idle.
# With m2 on GPU 1: concurrent /say calls, and /turn 2-sentence replies synthesize in parallel -> ~half total_ms.
m2 = None
TTS_LOCK_1 = threading.Lock()
gpt_cond_latent_2 = None
speaker_embedding_2 = None
if N_GPU >= 2:
    try:
        prog("v83: loading m2 on cuda:1 (dual-GPU XTTS)...")
        m2 = Xtts.init_from_config(pre_cfg)
        m2.load_checkpoint(pre_cfg, checkpoint_path=pre_model_path, checkpoint_dir=run_dir,
                           vocab_path=pre_vocab, use_deepspeed=False)
        m2.to("cuda:1")
        if PREC == "half":
            m2.half()
        m2.eval()
        gpt_cond_latent_2 = gpt_cond_latent.to("cuda:1")
        speaker_embedding_2 = speaker_embedding.to("cuda:1")
        prog(f"m2 ready cuda:1 PREC={PREC} -- dual-GPU active")
        # v97: warm GPU 1 now — first live call must NOT pay CUDA kernel JIT on m2.
        # Both GPUs pre-cache their mel speaker latents at boot (Forensic Law, Baba 2026-10-04).
        try:
            _w2_t = time.time()
            with TTS_LOCK_1:
                with _prec_ctx_safe():
                    _w2 = _infer("नमस्ते।", "hi", gpt_cond_latent_2, speaker_embedding_2, model=m2)
            _w2_ms = int((time.time() - _w2_t) * 1000)
            _w2_dur = round(len(_w2["wav"]) / float(SR), 2)
            prog(f"v97: GPU 1 warm-infer ok  ms={_w2_ms}  audio={_w2_dur}s  latents_on_device=cuda:1")
            log_lat({"type": "warmup_gpu1", "ms": _w2_ms, "audio_s": _w2_dur})
        except Exception as _w2e:
            prog(f"v97: GPU 1 warm-infer FAIL (non-fatal): {type(_w2e).__name__}: {str(_w2e)[:120]}")
        say("LIVE M2_READY dual_gpu=1")
    except Exception as _m2e:
        m2 = None
        prog(f"m2 FAIL (single-GPU fallback): {type(_m2e).__name__}: {str(_m2e)[:120]}")
        say("LIVE M2_FAIL single_gpu_fallback=1")
# ---------- 5. STT on GPU 1: the listening leg ----------
# The laptop CPU transcribes at 5x-15x real time (measured), which makes a live loop impossible.
# Whisper sits on the second T4 so it never competes with XTTS for memory or compute.
whisper = None
if STT_ON:
    try:
        import faster_whisper  # noqa
    except Exception:
        pip("faster-whisper")
    try:
        from faster_whisper import WhisperModel
        _stt_gpu = int(STT_GPU) if STT_GPU != "" else (1 if N_GPU > 1 else 0)
        t_stt = time.time()
        whisper = None
        for _mn in dict.fromkeys([STT_MODEL, "large-v3-turbo", "small"]):
            try:
                whisper = WhisperModel(_mn, device="cuda", device_index=_stt_gpu, compute_type="float16")
                STT_MODEL = _mn
                break
            except Exception as _e:
                prog(f"STT model {_mn} FAIL {type(_e).__name__}: {str(_e)[:100]}")
        if whisper is None:
            raise RuntimeError("no whisper model could be loaded")
        try:   # warm: the first transcribe otherwise pays CUDA/cuDNN init on a live turn
            list(whisper.transcribe(np.zeros(16000, dtype=np.float32), language="hi", beam_size=1,
                                    without_timestamps=True)[0])
        except Exception:
            pass
        _stt_ms = int((time.time() - t_stt) * 1000)
        log_lat({"type": "stt_load", "model": STT_MODEL, "gpu": _stt_gpu, "ms": _stt_ms})
        report(f"STT_READY {STT_MODEL} cuda:{_stt_gpu}/float16 load_ms={_stt_ms}")
    except Exception as e:
        whisper = None
        report(f"STT_FAIL load {type(e).__name__}: {str(e)[:140]}")
else:
    report("STT_OFF")


# ---------- 5b. BRAIN: the engine decides what to say ----------
# HEAR audio -> Whisper (GPU 1) -> LLM (GPU 1, streamed) -> first clause goes to XTTS (GPU 0) while the LLM is still
# writing the rest. Nothing here is scripted: the reply text comes from the model, turn by turn, with chat history.
DEFAULT_PERSONA = (
    "You are a professional male clinical voice assistant for a medical clinic. "
    "CRITICAL GENDER AND VOICE LAW: Your voice is MALE. In Hindi, ALWAYS use MALE grammatical inflections. "
    "Always say 'मैं क्लिनिक से बोल रहा हूँ', 'मैं आपकी क्या मदद कर सकता हूँ?', 'मैं देखता हूँ', 'मैं बताता हूँ', 'करूँगा', 'बताऊँगा'. "
    "NEVER use female verb endings like 'सकती हूँ', 'बोल रही हूँ', 'करूँगी', 'बताऊँगी', 'बोलती हूँ'. "
    "You think independently and exercise professional clinical empathy, handling every patient call naturally and helpfully. "
    "Clinic Scope: General Medicine and Primary Family Healthcare (सामान्य चिकित्सा एवं पारिवारिक स्वास्थ्य). "
    "Treats common illnesses: fever (बुखार), cough, cold and flu (खांसी और जुकाम), viral fever (वायरल बुखार), "
    "headache (सिरदर्द), stomach aches, gas and indigestion (पेट दर्द और गैस), blood pressure, diabetes, seasonal allergies, "
    "and routine health checkups. "
    "Doctor availability: Dr. Sen is available today 6:00 PM to 8:00 PM (शाम छह से आठ बजे तक). "
    "Dr. Roy is available tomorrow 9:00 AM to 1:00 PM (सुबह नौ से दोपहर एक बजे तक). "
    "How to interact: Listen actively and address whatever the caller asks. "
    "If they ask what conditions the clinic treats or which doctor is available, answer them directly, helpfully and informatively. "
    "If they want an appointment, guide them smoothly and take their details (name, preferred time, phone number). "
    "If they share their name or number, acknowledge it warmly and confirm. "
    "Never repeat the same question like a loop; understand the caller's context dynamically. "
    "Speak in warm, conversational spoken Hindi (written in Devanagari script) or English to match the caller. "
    "Keep answers concise and natural for a phone call (one to two sentences). "
    "Safe clinical guidance: general advice only, never prescribe or alter medications, and advise urgent care for emergencies."
)
PERSONA = DEFAULT_PERSONA
if PERSONA_FILE and os.path.exists(PERSONA_FILE):
    try:
        PERSONA = open(PERSONA_FILE, encoding="utf-8").read().strip() or DEFAULT_PERSONA
    except Exception:
        pass
FALLBACK_HI = "माफ़ कीजिए, मैं समझ नहीं पाया। कृपया दोबारा कहिए।"
FALLBACK_EN = "Sorry, I didn't catch that. Could you say it again?"
HISTORY = []
tok = None
llm = None
LLM_DEV = None
AUTO_ENABLED = False


def _hf_token():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if t:
        return t
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        return None


def load_llm():
    """v36: provider mode needs no local weights -- the whole point of moving off the 3B. Nothing to load."""
    global tok, llm, LLM_DEV
    if LLM_PROVIDER == "api":
        tok = llm = None
        LLM_DEV = "provider"
        return
    from transformers import AutoTokenizer, AutoModelForCausalLM
    src = LLM_PATH or LLM_MODEL
    gpu = int(LLM_GPU) if LLM_GPU != "" else (1 if N_GPU > 1 else 0)
    ht = _hf_token()
    tok = AutoTokenizer.from_pretrained(src, token=ht)
    kw = dict(torch_dtype=torch.float16, device_map={"": gpu}, token=ht)
    if LLM_4BIT:
        try:
            import bitsandbytes  # noqa
        except Exception:
            pip("bitsandbytes")
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                       bnb_4bit_compute_dtype=torch.float16)
    llm = AutoModelForCausalLM.from_pretrained(src, **kw).eval()
    LLM_DEV = f"cuda:{gpu}"
def llm_stream(messages, max_new, trace=None, stop=None, key_i=0):
    """Yield text increments as the model writes them.

    v36: two engines behind one signature so nothing downstream (SpeechChunker, speak, auto_reply) changed.
      LLM_PROVIDER="api"   -> hosted OpenAI-compatible /chat/completions, stream=True, SSE "data:" lines.
                              Runs on the seat (Baba: SEAT BRAIN), so the provider's first token costs one
                              network round trip, not a laptop hop.
      LLM_PROVIDER="local" -> the v33 transformers path, unchanged.
    v42: `trace` (optional dict) receives absolute times llm_req / llm_headers / llm_first_tok, and the same
    three intervals go to lat() as llm_headers_ms / llm_first_tok_ms. The response is always closed, even when
    the caller abandons the generator (hang-up), so a dead call stops costing provider time.
    """
    t_req = time.time()
    if trace is not None:
        trace["llm_req"] = t_req
    if LLM_PROVIDER == "api":
        # v46: attempt 0 stays on NVIDIA; attempt 1 (the hedge) crosses to OpenRouter. Rotating NVIDIA keys
        # cannot beat an IP-level throttle -- the Kaggle egress IP is what is slow, not the credential.
        use_or = bool(key_i >= 1 and OR_KEYS and LLM_HEDGE_HOST == "openrouter")   # v67: see LLM_HEDGE_HOST
        base = OR_BASE if use_or else LLM_BASE
        model = OR_MODEL if use_or else (LLM_PATH or LLM_MODEL)
        body = {"model": model, "messages": messages, "max_tokens": max_new,
                "temperature": LLM_TEMP, "top_p": 0.9, "stream": True,
                # REASONING OFF (Baba's order). Measured on this model: with reasoning the reply arrives as
                # English meta-text ("Here's a thinking process: 1. Analyze...") in 2435 ms across 83 reasoning
                # chunks. With chat_template_kwargs.enable_thinking=false it answers straight in clean Hindi in
                # 611 ms with ZERO reasoning chunks. `enable_thinking` as a top-level param is rejected (HTTP 400
                # "Unsupported parameter"), so it has to go inside chat_template_kwargs.
                "chat_template_kwargs": {"enable_thinking": False}}
        hdrs = dict(HDRS)
        hdrs["Content-Type"] = "application/json"
        if use_or:
            # OpenRouter does not accept the NVIDIA-only extra params, so they are stripped for that host.
            body.pop("chat_template_kwargs", None)
            hdrs.update(OR_HEADERS_EXTRA)
            hdrs["Authorization"] = "Bearer " + OR_KEYS[(key_i - 1) % len(OR_KEYS)]
            if trace is not None:
                trace["llm_host"] = "openrouter"
        elif LLM_API_KEYS:
            hdrs["Authorization"] = "Bearer " + LLM_API_KEYS[key_i % len(LLM_API_KEYS)]
            if trace is not None:
                trace["llm_host"] = "nvidia"
        # EMPTY-ADVANCE (2026-10-03): the model ladder used to advance ONLY on HTTP 410 Gone.
        # The live failure is a different signature: HTTP 200 with ZERO content chunks
        # ("provider returned no content", script.py:1677). Measured from the Kaggle egress IP:
        # nemotron-3-ultra-550b-a55b emptied ~half of its attempts while
        # nemotron-3-nano-omni-30b-a3b-reasoning answered 2/2 with clean Devanagari
        # (out/model-firsttok.json, out/model-sweep.json). A key rotation cannot leave a flaky
        # MODEL, so a 200-with-nothing now advances the chain too. Streaming is unchanged: pieces
        # are yielded as they arrive, and the next model is tried only when one produced nothing.
        def _stream_one(_m):
            _body = dict(body)
            _body["model"] = _m
            if use_or:
                _body.pop("chat_template_kwargs", None)
            _resp = _llm_session().post(base, data=json.dumps(_body), headers=hdrs,
                                        timeout=(LLM_CONNECT_TIMEOUT, LLM_READ_TIMEOUT), stream=True)
            if _resp.status_code == 410 and not use_or:
                DEAD_MODELS.add(_m)
                print("LLM model %s returned 410 Gone -> marked dead" % _m, flush=True)
                try:
                    _resp.close()
                except Exception:
                    pass
                return
            if trace is not None:
                trace["llm_model"] = _m
            try:
                _resp.raise_for_status()
                _t_hd = time.time()
                lat("llm_headers_ms", (_t_hd - t_req) * 1000)
                if trace is not None:
                    trace["llm_headers"] = _t_hd
                _done = False
                for _rawline in _resp.iter_lines():
                    if stop is not None and stop.is_set():
                        break
                    if _done or not _rawline:
                        continue   # after [DONE] keep draining so the keep-alive connection can be reused
                    _line = _rawline.decode("utf-8", "replace") if isinstance(_rawline, (bytes, bytearray)) else str(_rawline)
                    if not _line.startswith("data:"):
                        continue
                    _data = _line[5:].strip()
                    if _data == "[DONE]":
                        _done = True
                        continue
                    if not _data:
                        continue
                    try:
                        _j = json.loads(_data)
                    except Exception:
                        continue
                    for _ch in (_j.get("choices") or []):
                        _piece = (_ch.get("delta") or {}).get("content")
                        if _piece:
                            if not _got[0]:
                                _t_ft = time.time()
                                lat("llm_first_tok_ms", (_t_ft - t_req) * 1000)
                                if trace is not None:
                                    trace["llm_first_tok"] = _t_ft
                            _got[0] = True
                            yield _piece
            finally:
                _resp.close()

        _cands = [OR_MODEL] if use_or else ([m_ for m_ in LLM_MODEL_CHAIN if m_ not in DEAD_MODELS] or list(LLM_MODEL_CHAIN))
        _got = [False]                    # list so the nested generator can set it (a bare bool would be shadowed)
        for _mi, _m in enumerate(_cands):
            _got[0] = False
            for _piece in _stream_one(_m):
                yield _piece
            if _got[0]:
                return
            if _mi < len(_cands) - 1:
                print("LLM model %s produced no content -> advancing model" % _m, flush=True)
            if stop is not None and stop.is_set():
                break
        raise RuntimeError("provider returned no content (models tried: %s)" % ",".join(_cands))
        return

    from transformers import TextIteratorStreamer
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt", add_special_tokens=False).to(LLM_DEV)
    streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True, timeout=LLM_TIMEOUT)
    err = {}

    def _gen():
        try:
            with torch.inference_mode():
                llm.generate(**inputs, max_new_tokens=max_new, do_sample=True, temperature=LLM_TEMP, top_p=0.9,
                             repetition_penalty=1.05, streamer=streamer, pad_token_id=tok.eos_token_id)
        except Exception as e:
            err["e"] = e
            streamer.on_finalized_text("", stream_end=True)   # unblock the reader

    th = threading.Thread(target=_gen, daemon=True)
    th.start()
    first = True
    for text in streamer:
        if first and text:
            first = False
            t_ft = time.time()
            lat("llm_first_tok_ms", (t_ft - t_req) * 1000)
            if trace is not None:
                trace["llm_headers"] = t_req
                trace["llm_first_tok"] = t_ft
        yield text
    th.join(timeout=5)
    if "e" in err:
        raise err["e"]


def _llm_stream_hedged_v63(messages, max_new, trace=None):
    """v43: first-token deadline + hedge. Attempt 0 starts at once; if no token has arrived after LLM_FIRST_TOK_SEC
    (or it errors) attempt 1 starts with the next key. The first attempt to produce a token wins and the other is
    cancelled. Raises only if both fail or nothing arrives within LLM_HARD_FIRST_SEC. Closing this generator
    (caller hung up) cancels both attempts."""
    if LLM_PROVIDER != "api" or not LLM_HEDGE:
        yield from llm_stream(messages, max_new, trace)
        return
    t0 = time.time()
    q = queue.Queue()
    stops = [threading.Event(), threading.Event()]
    trs = [{}, {}]

    def run(i):
        try:
            for piece in llm_stream(messages, max_new, trs[i], stop=stops[i], key_i=i):
                q.put((i, "tok", piece))
            q.put((i, "end", None))
        except Exception as e:
            q.put((i, "err", e))

    def start(i):
        threading.Thread(target=run, args=(i,), daemon=True).start()

    start(0)
    live, hedged, win = 1, False, None
    try:
        while True:
            if win is None:
                wait = (t0 + (LLM_HARD_FIRST_SEC if hedged else LLM_FIRST_TOK_SEC)) - time.time()
                wait = max(0.01, wait)
            else:
                wait = None
            try:
                i, kind, val = q.get(timeout=wait)
            except queue.Empty:
                if not hedged:
                    hedged = True
                    live += 1
                    start(1)
                    lat("llm_hedges", 1)
                    continue
                raise RuntimeError("provider: no first token in %s s" % LLM_HARD_FIRST_SEC)
            if kind == "tok":
                if win is None:
                    win = i
                    stops[1 - i].set()
                    if trace is not None:
                        trace.update(trs[i])
                        trace["llm_req"] = t0
                if i == win:
                    yield val
            elif kind == "end":
                if i == win:
                    return
            else:
                if i == win:
                    raise val
                live -= 1
                if win is None and live == 0:
                    if hedged:
                        raise val
                    hedged = True
                    live += 1
                    start(1)
                    lat("llm_hedges", 1)
    finally:
        for s_ in stops:
            s_.set()


# ===================== v64: script-guarded hedge (inserted by patch_v64.py) =====================
# v63 let whichever attempt produced the first token win. The hedge goes to OpenRouter's
# nemotron-3.5-lightning, which the brain sweep measured as romanised / poor Hindi; spoken through XTTS
# "hi" that is exactly "a language I do not understand". Now an attempt only wins once its first few
# letters are Devanagari (Hindi turns). A rejected attempt is cancelled and the other one is used; if
# both are rejected the caller hears FALLBACK_HI instead of garbage.
DEVA_MIN_LETTERS = int(os.environ.get("DEVA_MIN_LETTERS", "5"))
DEVA_MIN_FRAC = float(os.environ.get("DEVA_MIN_FRAC", "0.6"))


def _deva_stats(s):
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0, 0.0
    d = sum(1 for c in letters if "\u0900" <= c <= "\u097f")
    return len(letters), d / float(len(letters))


def llm_stream_hedged(messages, max_new, trace=None, need_deva=None):
    if LLM_PROVIDER != "api" or not LLM_HEDGE:
        yield from llm_stream(messages, max_new, trace)
        return
    if need_deva is None:
        need_deva = bool(messages and messages[0].get("role") == "system"
                         and "Devanagari script only" in str(messages[0].get("content", "")))
    t0 = time.time()
    q = queue.Queue()
    stops = [threading.Event(), threading.Event()]
    trs = [{}, {}]
    held = [[], []]
    dead = set()

    def run(i):
        try:
            for piece in llm_stream(messages, max_new, trs[i], stop=stops[i], key_i=i):
                q.put((i, "tok", piece))
            q.put((i, "end", None))
        except Exception as e:
            q.put((i, "err", e))

    def start(i):
        threading.Thread(target=run, args=(i,), daemon=True).start()

    def verdict(i, final):
        if not need_deva:
            return "accept"
        n, frac = _deva_stats("".join(held[i]))
        if n >= DEVA_MIN_LETTERS or (final and n > 0):
            return "accept" if frac >= DEVA_MIN_FRAC else "reject"
        return "accept" if final else "wait"

    start(0)
    live, hedged, win, rejected = 1, False, None, False
    try:
        while True:
            if win is None:
                wait = max(0.01, (t0 + (LLM_HARD_FIRST_SEC if hedged else LLM_FIRST_TOK_SEC)) - time.time())
            else:
                wait = None
            try:
                i, kind, val = q.get(timeout=wait)
            except queue.Empty:
                if not hedged:
                    hedged = True
                    live += 1
                    start(1)
                    lat("llm_hedges", 1)
                    continue
                raise RuntimeError("provider: no first token in %s s" % LLM_HARD_FIRST_SEC)
            if i in dead or (win is not None and i != win):
                continue
            if win is not None:
                if kind == "tok":
                    yield val
                elif kind == "end":
                    return
                else:
                    raise val
                continue
            if kind == "tok":
                held[i].append(val)
                v = verdict(i, False)
            elif kind == "end":
                v = verdict(i, True) if held[i] else "empty"
            else:
                v = "error"
            if v == "wait":
                continue
            if v == "accept":
                win = i
                stops[1 - i].set()
                if trace is not None:
                    trace.update(trs[i])
                    trace["llm_req"] = t0
                buf, held[i] = held[i], []
                for tk in buf:
                    yield tk
                if kind == "end":
                    return
                continue
            dead.add(i)
            stops[i].set()
            live -= 1
            if v == "reject":
                rejected = True
                lat("llm_script_rejects", 1)
                print("LLM script guard: attempt %d wrote non-Devanagari %r" % (i, "".join(held[i])[:60]), flush=True)
            if live == 0:
                if not hedged:
                    hedged = True
                    live += 1
                    start(1)
                    lat("llm_hedges", 1)
                elif rejected and need_deva:
                    yield FALLBACK_HI
                    return
                else:
                    raise (val if kind == "err" else RuntimeError("provider returned no usable content"))
    finally:
        for s_ in stops:
            s_.set()


_EMOJI = re.compile("[\U00010000-\U0010ffff☀-➿⬀-⯿️‍]")


def clean_llm_text(s):
    """Strip what a voice must not read aloud: emojis, markdown marks, line breaks."""
    s = _EMOJI.sub("", s)
    s = re.sub(r"[*_#`~>|]+", " ", s)
    return s.replace("\n", " ")


def build_messages(user_text, rlang):
    hint = ("This turn, reply in English." if rlang == "en"
            else "This turn, reply in simple spoken Hindi, Devanagari script only. You are MALE: use strictly MALE grammatical verb forms (e.g. कर सकता हूँ, बोल रहा हूँ, देखता हूँ; NEVER use feminine forms like कर सकती हूँ, बोल रही हूँ, बोलती हूँ).")
    sys_txt = PERSONA + "\n" + hint
    hist = HISTORY[-2 * LLM_HISTORY_TURNS:] if LLM_HISTORY_TURNS > 0 else []
    return [{"role": "system", "content": sys_txt}] + hist + [{"role": "user", "content": user_text}]


if AUTO_MODE:
    try:
        t_llm = time.time()
        load_llm()
        if LLM_PROVIDER == "api":
            AUTO_ENABLED = bool(LLM_BASE and LLM_API_KEYS)
            # v42: open the provider connection now (DNS + TCP + TLS + a 4-token completion) so the first real
            # turn does not pay for it. Failure here does not disable the brain; the first live turn retries.
            try:
                list(llm_stream_hedged([{"role": "user", "content": "नमस्ते"}], 4))
            except Exception as e:
                prog(f"BRAIN prewarm FAIL {type(e).__name__}: {str(e)[:100]}")
            _llm_ms = int((time.time() - t_llm) * 1000)
            log_lat({"type": "llm_load", "provider": LLM_BASE, "model": LLM_PATH or LLM_MODEL,
                     "mode": "api", "ms": _llm_ms, "key_set": bool(LLM_API_KEY)})
            report(json.dumps({"kind": "auto_state", "auto": AUTO_ENABLED, "provider": LLM_BASE,
                               "model": LLM_PATH or LLM_MODEL, "load_ms": _llm_ms}, ensure_ascii=True))
            prog(f"BRAIN ready {LLM_PATH or LLM_MODEL} via {LLM_BASE} load_ms={_llm_ms}")
        else:
            try:   # warm: first generate otherwise pays kernel init on a live turn
                list(llm_stream([{"role": "user", "content": "नमस्ते"}], 6))
            except Exception:
                pass
            AUTO_ENABLED = True
            _llm_ms = int((time.time() - t_llm) * 1000)
            log_lat({"type": "llm_load", "model": LLM_PATH or LLM_MODEL, "gpu": LLM_DEV, "ms": _llm_ms, "4bit": LLM_4BIT})
            report(json.dumps({"kind": "auto_state", "auto": True, "model": LLM_PATH or LLM_MODEL, "load_ms": _llm_ms},
                              ensure_ascii=True))
            prog(f"BRAIN ready {LLM_PATH or LLM_MODEL} on {LLM_DEV} load_ms={_llm_ms}")
    except Exception as e:
        AUTO_ENABLED = False
        report(json.dumps({"kind": "auto_state", "auto": False, "err": type(e).__name__ + ": " + str(e)[:140]},
                          ensure_ascii=True))
        prog(f"BRAIN load FAIL {type(e).__name__}: {str(e)[:120]} @{_where(e)} -- scripted LIVE_CALL still works")
        torch.cuda.empty_cache()
else:
    report(json.dumps({"kind": "auto_state", "auto": False, "err": "AUTO_MODE=0"}, ensure_ascii=True))


# ---------- 6. relay conversation: orders in (LIVE_CALL/HEAR/AUTO_*/LIVE_END), chunks out (LIVE_CHUNK/LIVE_DONE) ----------
# LIVE-READ (v30): live=1 makes the relay serve each big row (HEAR carries a base64 WAV) ONCE per
# (reader, body); small rows keep repeating. READER_ID is per boot, so two live seats never starve each other.
READER_ID = "seat-" + str(int(time.time())) + "-" + str(os.getpid())


def orders(limit=60):
    global DOOR
    if DOOR is None and gate() is None:
        return []
    try:
        q = (f"/say?token={urllib.parse.quote(RELAY_TOKEN)}&body={urllib.parse.quote(SELF_BODY)}"
             f"&limit={limit}&live=1&reader={urllib.parse.quote(READER_ID)}")
        t_p = time.time()
        r = json.loads(http_get(DOOR + q, 30).decode())
        lat("relay_poll_ms", _ms(t_p))   # v42: one orders poll (hot period 0.35 s, so this is also the pickup floor)
        return r.get("orders", [])
    except Exception:
        DOOR = None
        return []


def norm_lang(lang):
    return "en" if (lang or "").lower().split("-")[0].split("_")[0] == "en" else "hi"


def order_age_ms(at):
    """Age of an order in ms, supporting both numeric epoch and ISO-8601 strings."""
    if not at:
        return None
    try:
        v = float(at)
        if v > 1e12:
            v /= 1000.0
        if 1e9 < v < 4e9:
            return int((time.time() - v) * 1000)
    except Exception:
        pass
    try:
        from datetime import datetime, timezone
        s = str(at).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return int((datetime.now(timezone.utc) - dt).total_seconds() * 1000)
    except Exception:
        pass
    return None


def prep_pieces(piece, lang):
    """One piece as XTTS should read it: Hindi numerals spelled out, re-split if that pushed it over the limit."""
    p = hi_numbers(piece) if lang == "hi" else piece
    p = re.sub(r"\s+", " ", p).strip()
    limit = char_limit(lang)
    out = []
    while p:
        a, p = take_piece(p, limit)
        if a:
            out.append(a)
    return out
def speak(cid, lang, pieces, text_len, age_ms=None, label="call"):
    """Synthesize `pieces` (a list OR a lazy generator such as live LLM output) and ship each as a complete WAV.
    Returns a dict with timings and the text actually spoken.
    v42: each chunk record also carries post_ms (silence trim/collapse/resample) and enc_ms (WAV + base64)."""
    t_call = time.time()
    idx = 0
    first_ready_ms = None
    total_b = 0
    synth_ms = 0
    wait_ms = 0
    npieces = 0
    spoken = []
    tag = "first:" + cid
    out_sr = OUT_SR or SR
    try:
        it = iter(pieces)
        while True:
            t_wait = time.time()
            try:
                raw_piece = next(it)
            except StopIteration:
                break
            wait_ms += int((time.time() - t_wait) * 1000)
            for piece in prep_pieces(raw_piece, lang):
                npieces += 1
                spoken.append(piece)
                print(f"{label} {cid}: piece {npieces} ({len(piece)} chars, prec {PREC}, ramp {RAMP_EFF:.2f})", flush=True)
                t_piece = time.time()
                for raw in synth_iter(piece, lang):
                    gen_ms = int((time.time() - t_piece) * 1000)
                    synth_ms += gen_ms
                    t_pp = time.time()
                    arr = finish_audio(raw, piece, trim=(SYNTH_MODE == "full"))
                    post_ms = _ms(t_pp)
                    t_en = time.time()
                    buf = _wavbuf(arr, int(out_sr))
                    b64 = base64.b64encode(buf).decode()
                    enc_ms = _ms(t_en)
                    total_b += len(buf)
                    idx += 1
                    if first_ready_ms is None:
                        first_ready_ms = int((time.time() - t_call) * 1000)
                    marks = [b64[i:i + CHUNK_B64] for i in range(0, len(b64), CHUNK_B64)]
                    for k, mk in enumerate(marks):
                        say_async(f"LIVE_CHUNK {cid} {idx:03d}-{k + 1:02d}/{len(marks)}:{mk}", OUT_BODY,
                                  tag if (idx == 1 and k == 0) else None)
                    audio_s = len(arr) / max(int(out_sr), 1)
                    lat("relay_chunk_gen_ms", gen_ms)
                    lat("relay_chunk_post_ms", post_ms)
                    lat("relay_chunk_enc_ms", enc_ms)
                    log_lat({"type": "chunk", "cid": cid, "chunk": idx, "lang": lang, "chars": len(piece),
                             "audio_s": round(audio_s, 2), "gen_ms": gen_ms, "post_ms": post_ms, "enc_ms": enc_ms,
                             "rtf": round(gen_ms / 1000.0 / max(audio_s, 1e-6), 2),
                             "cum_ms": int((time.time() - t_call) * 1000), "first_ready_ms": first_ready_ms,
                             "wav_b": len(buf), "parts": len(marks)})
                    t_piece = time.time()
    except Exception as e:
        flush(10)
        detail = (str(e) or repr(e))[:120]
        where = _where(e)
        prog(f"CALL FAIL {cid} {type(e).__name__}: {detail} @{where}")
        log_lat({"type": "call_fail", "cid": cid, "err": detail, "where": where, "label": label})
        say(f"LIVE_FAIL {cid} {type(e).__name__} @{where}")
        return {"ok": False, "spoken": spoken, "first_sent_t": None, "first_ms": None}
    t_fl = time.time()
    flush()
    flush_ms = int((time.time() - t_fl) * 1000)
    sent = _sent.pop(tag, None)
    first_ms = int((sent - t_call) * 1000) if sent else first_ready_ms
    total_ms = int((time.time() - t_call) * 1000)
    lat("relay_first_ready_ms", first_ready_ms)
    lat("relay_first_sent_ms", first_ms)
    lat("relay_flush_ms", flush_ms)
    lat("relay_total_ms", total_ms)
    log_lat({"type": "call", "label": label, "cid": cid, "lang": lang, "chars": text_len, "pieces": npieces,
             "chunks": idx, "first_ready_ms": first_ready_ms, "first_ms": first_ms, "synth_ms": synth_ms,
             "llm_wait_ms": wait_ms, "flush_ms": flush_ms, "total_ms": total_ms, "b64_b": total_b,
             "order_age_ms": age_ms, "prec": PREC})
    say(f"LIVE_DONE {cid} chunks={idx} first_ms={first_ms} total_ms={total_ms} - play on laptop, live call lane")
    return {"ok": True, "first_ms": first_ms, "first_sent_t": sent, "spoken": spoken, "total_ms": total_ms,
            "synth_ms": synth_ms, "wait_ms": wait_ms, "idx": idx}


def do_call(cid, text, lang, age_ms=None):
    """Scripted path: speak exactly the text the laptop sent."""
    lang = norm_lang(lang)
    try:
        pieces = plan_pieces(text, lang)
    except Exception:
        pieces = [text[:char_limit(lang)]]
    return speak(cid, lang, pieces, len(text), age_ms, "call")


def auto_reply(cid, utext, rlang, t_hear0=None, stt_ms=None):
    """Autonomous path: the LLM decides the reply; each clause is voiced as soon as it is written."""
    t0 = time.time()
    rcid = "a" + cid
    chunker = SpeechChunker(rlang)
    msgs = build_messages(utext, rlang)
    marks = {}

    def pieces():
        for txt in llm_stream_hedged(msgs, LLM_MAX_NEW):
            marks.setdefault("tok", time.time())
            for p in chunker.feed(clean_llm_text(txt)):
                marks.setdefault("piece", time.time())
                yield p
        for p in chunker.finish():
            marks.setdefault("piece", time.time())
            yield p

    res = speak(rcid, rlang, pieces(), len(utext), label="auto")
    reply = " ".join(res.get("spoken", [])).strip()
    if res.get("ok") and not reply:
        do_call(rcid, FALLBACK_EN if rlang == "en" else FALLBACK_HI, rlang)
        reply = FALLBACK_EN if rlang == "en" else FALLBACK_HI
    elif res.get("ok"):
        HISTORY.extend([{"role": "user", "content": utext}, {"role": "assistant", "content": reply}])
        if LLM_HISTORY_TURNS > 0:
            del HISTORY[:-2 * LLM_HISTORY_TURNS]
        else:
            del HISTORY[:]
    base = t_hear0 or t0
    sent = res.get("first_sent_t")
    e2e = int((sent - base) * 1000) if sent else None
    llm_first_ms = int((marks["piece"] - t0) * 1000) if "piece" in marks else None
    lat("auto_llm_first_piece_ms", llm_first_ms)
    lat("auto_e2e_first_ms", e2e)
    log_lat({"type": "auto", "cid": cid, "lang": rlang, "user_chars": len(utext), "reply_chars": len(reply),
             "stt_ms": stt_ms, "llm_first_piece_ms": llm_first_ms, "first_ms": res.get("first_ms"),
             "e2e_first_ms": e2e, "ok": res.get("ok")})
    report(json.dumps({"cid": cid, "kind": "auto_reply", "reply": reply, "lang": rlang,
                       "llm_first_piece_ms": llm_first_ms, "first_ms": res.get("first_ms"), "e2e_first_ms": e2e},
                      ensure_ascii=True))   # no "text" key: the laptop must not mistake the reply for a transcript
def stt_lang(lang):
    """Bilingual STT: supports both English and Hindi.
    If 'en', transcribe in English.
    If 'hi', transcribe in Hindi.
    If 'auto' or not specified, return None so Whisper transcribes either language naturally.
    Cross-language hallucinations (Urdu, Arabic, Korean) are caught by the wrong-script gate below."""
    s = (lang or "").strip().lower().split("-")[0].split("_")[0]
    if s == "en":
        return "en"
    if s == "hi":
        return "hi"
    return None   # auto-detect English or Hindi naturally


STT_COUNT = 0


def wav_to_16k(raw):
    """Decode a WAV we were posted into the 16 kHz float32 array faster-whisper wants.

    The seat's PyAV predates what faster-whisper expects: its path/binary-IO branch calls
    av.open(metadata_errors=...), which raises "TypeError: open() got an unexpected keyword
    argument 'metadata_errors'" on every HEAR. Decoding here keeps the STT lane usable.
    """
    a, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    if getattr(a, "ndim", 1) > 1:
        a = a.mean(axis=1)
    return np.ascontiguousarray(resample(a, sr, 16000), dtype=np.float32)


# ==================== v84: THE NOISE GATE (Baba, 2026-10-03) ====================
# Baba's report: "this is due to constant hammering on the nvidia ... the noise". The mechanic,
# caught live in the handset log at 20:17 IST:
#     heard='अपुइंटमेंट, अपुइंटमेंट, अपुइंटमेंट, ... (x14)'
# That is Whisper HALLUCINATING on non-speech audio. Handed noise, faster-whisper does not return
# an empty string -- it emits boilerplate it has seen a thousand times ("appointment", "Thank you.",
# "अपुइंटमेंट"), usually repeated. The old gate was:
#     if want_auto and re.search(r"\w", text):
# so a hallucination sailed straight through: LLM call -> XTTS -> the handset SPEAKS the reply
# into its own mic -> the mic hears it -> another turn. That is the hammering: ~240 wasted LLM
# calls an hour (twice that with the hedge) from ONE parked phone with nothing but a knock in the
# room -- and it is what degraded our standing on the free tier (all keys slow equally = the IP).
# Two gates, both cheap:
#   1. ENERGY GATE before Whisper -- no speech-level energy in the upload means it cannot be an
#      utterance. Saves the GPU and stops the hallucination at its source.
#   2. HALLUCINATION GATE after Whisper -- a one-token repeat or known boilerplate is not speech.
# A dropped turn answers NOTHING: no LLM, no TTS, no playback. Silence IS the correct reply to
# noise, and it breaks the echo loop at the only place that matters.
NOISE_PEAK_MIN = float(os.environ.get("NOISE_PEAK_MIN", "0.02"))   # |x| peak of the upload
NOISE_RMS_MIN = float(os.environ.get("NOISE_RMS_MIN", "0.006"))    # rms of the upload
# A one-token transcript is dropped by default: out of the room it is nearly always noise, and the
# cost of the other choice is a ghost reply spoken into the mic (the hammering). It is a lever, not
# a verdict -- a clinic that needs bare "haan/na" answers sets this to 0.
HALLUC_DROP_SINGLE = os.environ.get("HALLUC_DROP_SINGLE", "0") == "1"
HALLUC_DROP = [0]        # dropped-turn counter, exposed at /say?probe=1

HALLUC_BOILER = (
    "thank you", "thanks for watching", "please subscribe", "subscribe", "amara.org",
    "subtitle", "subtitles", "transcription by", "एमारा", "उपशीर्षक", "झाल", "झाल झाल",
    "ご視聴", "ありがとうございました", "字幕", "시청해주셔서 감사합니다",
)
# NOTE: the "appointment"/"अपॉइंटमेंट" family is deliberately NOT in this list. A REAL clinic
# question ("अपॉइंटमेंट कैसे बुक करूँ?") contains that exact word, so matching on vocabulary would
# drop a genuine patient -- the worst possible failure. The observed noise artifact was the
# REPETITION ('अपुइंटमेंट x14'), and repetition is a SHAPE, so it is caught by the collapse rule
# below. Match shapes, never words a patient would legitimately say.


def _norm_tokens(text):
    """Lowercase word/number tokens; punctuation and Whisper's '#'-runs dropped."""
    t = (text or "").lower()
    t = re.sub(r"[^\w\u0900-\u097f]+", " ", t)
    return [w for w in t.split() if w]


def is_hallucination(text):
    """True when a transcript has the SHAPE Whisper produces on noise, not on speech.

    Measured shapes this catches (all seen live on this lane):
      'अपुइंटमेंट, अपुइंटमेंट, ... x14'  -> one token repeated   (consecutive collapse)
      'अपुइंटमेंट अपुइंटमेंट'             -> two-token repeat      (same rule)
      'a b a b a b a b'                 -> a two-word cycle      (tiny-vocabulary rule)
      'Thank you.'                       -> whole-transcript boilerplate
    A real question is many DIFFERENT words, so none of these fire on real speech. Boilerplate is
    only matched when it IS the whole transcript -- never as a substring -- so a patient asking
    about an appointment is safe.
    """
    toks = _norm_tokens(text)
    if not toks:
        return True
    # Specifically catch the known Whisper noise token 'झाल'
    if text.strip().replace("।", "").replace("?", "").replace(".", "").strip() in ("झाल", "झाल झाल"):
        return True
    _wrong_script = re.search(r"[\u0600-\u06FF\uAC00-\uD7A3\u3040-\u30FF\u4E00-\u9FFF]", text)
    if _wrong_script:
        return True
    if len(toks) == 1:
        if not HALLUC_DROP_SINGLE:
            return False
        common_valid_single = {"hello", "hi", "hey", "नमस्ते", "नमस्कार", "सुनिए", "डॉक्टर", "डॉ", "doctor", "help", "मदद", "हाँ", "नहीं", "yes", "no", "ok", "okay", "baba", "kilo", "you", "what", "who", "when", "why", "how", "sure", "fever", "cough", "cold", "appointment"}
        return toks[0] not in common_valid_single
    collapsed = [toks[0]]                  # collapse CONSECUTIVE repeats: a a a a -> [a]
    for w in toks[1:]:
        if w != collapsed[-1]:
            collapsed.append(w)
    if len(collapsed) == 1:
        return True                        # the x14 loop, and the 2x repeat, both die here
    if len(toks) >= 6 and len(set(toks)) <= 2:
        return True                        # one short phrase looped
    if len(toks) >= 8 and len(set(toks)) / float(len(toks)) < 0.3:
        return True                        # heavy repetition, wide
    if len(collapsed) <= 3:                # whole-transcript boilerplate only
        joined = " ".join(collapsed)
        for b in HALLUC_BOILER:
            if joined == b or joined.startswith(b + " ") or joined.endswith(" " + b):
                return True
    return False


def _noise_reason(a16):
    """(drop?, reason, peak, rms) -- the ENERGY GATE. Silence/noise cannot be an utterance."""
    if a16 is None or len(a16) == 0:
        return True, "empty", 0.0, 0.0
    peak = float(np.max(np.abs(a16)))
    rms = float(np.sqrt(np.mean(np.square(a16))))
    if peak < NOISE_PEAK_MIN or rms < NOISE_RMS_MIN:
        return True, "no_speech_energy", round(peak, 4), round(rms, 4)
    return False, "", round(peak, 4), round(rms, 4)
# ===============================================================================


def do_hear(otxt):
    """HEAR {"cid":..,"lang":..,"b64":<16000 Hz mono 16-bit wav>[,"auto":0]} -> transcribe on the T4 -> transcript
    report on /hear -> (AUTO) the on-seat brain answers by itself and speaks via LIVE_CHUNK.
    ensure_ascii keeps Devanagari intact."""
    global STT_COUNT
    t0 = time.time()
    cid, slang = "h" + str(int(time.time())), LANGUAGE
    try:
        j = json.loads(otxt[len("HEAR"):].strip())
        cid = str(j.get("cid") or cid)
        slang = stt_lang(j.get("lang"))
        raw = base64.b64decode(j.get("b64") or "")
        if not raw:
            report(json.dumps({"cid": cid, "text": "", "err": "empty_audio"}, ensure_ascii=True))
            return
        if KEEP_HEAR:
            with open(f"{WORK}/hear_{cid}.wav", "wb") as fh:
                fh.write(raw)
        if whisper is None:
            report(json.dumps({"cid": cid, "text": "", "err": "stt_unavailable"}, ensure_ascii=True))
            return
        t_dec = time.time()
        a16 = wav_to_16k(raw)
        dec_ms = _ms(t_dec)
        # v84 ENERGY GATE: no speech-level energy means the room, not a patient. Never spend GPU on
        # Whisper for it and never let noise become a turn -- this is the hammering Baba reported.
        _drop, _why, _pk, _rms = _noise_reason(a16)
        if _drop:
            HALLUC_DROP[0] += 1
            lat("noise_gate", 1)
            log_lat({"type": "noise_gate", "cid": cid, "reason": _why, "peak": _pk, "rms": _rms,
                     "audio_s": round(len(raw) / 32000.0, 2)})
            print(f"NOISE_GATE {_why} peak={_pk} rms={_rms} (no STT, no LLM, no reply)", flush=True)
            report(json.dumps({"cid": cid, "text": "", "err": _why, "peak": _pk, "rms": _rms,
                               "no_speech": True}, ensure_ascii=True))
            return
        t_tr = time.time()
        segs, info = whisper.transcribe(a16, language=stt_lang(slang), beam_size=STT_BEAM,
                                        vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300),
                                        without_timestamps=True, condition_on_previous_text=False,
                                        temperature=0.0, repetition_penalty=1.2, no_repeat_ngram_size=3,
                                        initial_prompt=(STT_PROMPT or None))
        text = " ".join(s.text for s in segs).strip()
        det_l = getattr(info, "language", None)
        if det_l in ("en", "hi"):
            slang = det_l
        tr_ms = _ms(t_tr)
        STT_COUNT += 1
        ms = int((time.time() - t0) * 1000)
        lat("stt_total_ms", ms)
        lat("stt_decode_ms", dec_ms)
        lat("stt_transcribe_ms", tr_ms)
        log_lat({"type": "stt", "cid": cid, "lang": slang, "audio_s": round(len(raw) / 32000.0, 2),
                 "ms": ms, "dec_ms": dec_ms, "transcribe_ms": tr_ms, "chars": len(text)})
        want_auto = bool(AUTO_MODE and AUTO_ENABLED and j.get("auto", 1) not in (0, False, "0"))
        report(json.dumps({"cid": cid, "text": text, "ms": ms, "lang": slang, "auto": want_auto}, ensure_ascii=True))
        # v84 HALLUCINATION GATE. Whisper on noise writes boilerplate, not silence -- answering it is
        # what made the handset hammer the provider and answer its own speaker in a loop. A dropped
        # turn gets NO llm call, NO tts, NO playback: silence is the correct reply to noise.
        if want_auto and text and is_hallucination(text):
            HALLUC_DROP[0] += 1
            lat("halluc_dropped", 1)
            log_lat({"type": "halluc", "cid": cid, "chars": len(text), "text": text[:120]})
            print(f"HALLUC_DROPPED {len(text)}ch {text[:60]!r} (no reply)", flush=True)
            report(json.dumps({"cid": cid, "text": text, "ms": ms, "lang": slang, "auto": False,
                               "err": "no_speech", "hallucination": True}, ensure_ascii=True))
            return
        if want_auto and re.search(r"\w", text):
            heard = slang or getattr(info, "language", None) or LANGUAGE
            auto_reply(cid, text, "en" if str(heard).lower().startswith("en") else "hi", t0, ms)
    except Exception as e:
        report(json.dumps({"cid": cid, "text": "", "err": type(e).__name__ + ": " + str(e)[:100]},
                          ensure_ascii=True))


def bye(reason):
    flush(10)
    up = int(time.time() - T0)
    log_lat({"type": "session", "reason": reason, "gpu_s": up, "calls": CALLS})
    say(f"LIVE_BYE {reason} gpu_s={up} calls={CALLS}")
    print(f"BYE {reason} gpu_s={up} calls={CALLS}", flush=True)
    sys.exit(0)


def _auto_state(**kw):
    d = {"kind": "auto_state", "auto": bool(AUTO_ENABLED)}
    d.update(kw)
    report(json.dumps(d, ensure_ascii=True))


def _brain_ready():
    """v36: in provider mode there are no local weights, so `llm` is legitimately None. The old guard
    (`if llm is None`) treated that as "not loaded" and AUTO_ASK answered with err=llm_not_loaded forever.
    Provider mode is ready when LLM_BASE is set; local mode is ready when the weights are loaded."""
    return bool(LLM_BASE and LLM_API_KEYS) if LLM_PROVIDER == "api" else llm is not None


def handle_auto(otxt):
    """AUTO_ON / AUTO_OFF / AUTO_RESET / AUTO_PERSONA <text> / AUTO_ASK {"cid":..,"text":..,"lang":..}"""
    global AUTO_ENABLED, PERSONA
    cmd, _, arg = otxt.partition(" ")
    arg = arg.strip()
    if cmd == "AUTO_ON":
        if not _brain_ready():
            _auto_state(err="llm_not_loaded")
        else:
            AUTO_ENABLED = True
            _auto_state()
    elif cmd == "AUTO_OFF":
        AUTO_ENABLED = False
        _auto_state()
    elif cmd == "AUTO_RESET":
        del HISTORY[:]
        _auto_state(reset=True)
    elif cmd == "AUTO_PERSONA":
        if arg:
            PERSONA = arg
            del HISTORY[:]
        _auto_state(persona_set=bool(arg))
    elif cmd == "AUTO_ASK":   # text in, no microphone: lets you test the brain straight from the relay
        try:
            j = json.loads(arg)
        except Exception:
            j = {"text": arg}
        text = str(j.get("text", "")).strip()
        qcid = str(j.get("cid") or "q" + str(int(time.time())))
        if not _brain_ready():
            _auto_state(err="llm_not_loaded")
        elif text:
            auto_reply(qcid, text, norm_lang(j.get("lang", LANGUAGE)))
# ---------- 7. DIRECT VOICE TUNNEL (v39, Baba 2026-10-02) ----------
# Baba's call: a ONE-TO-ONE phone<->seat conversation does not need the relay at all. The kernel binds a
# port, cloudflared exposes it from inside the kernel, and the phone POSTs mic audio straight to the seat and
# gets audio back in ONE round trip. The relay stays for the 100 sons; only the voice lane leaves it.
#
# WHY (measured, not assumed): a POST to the relay cost ~1336 ms before a single byte moved, because every
# arriving message rewrote a 70.3 MB order bank (LOCAL POST 1065-2109 ms vs LOCAL GET 2-4 ms on 127.0.0.1 --
# not the tunnel, our own disk). Nothing on this path touches order-bank.json, so that cost is zero here.
VOICE_TUNNEL = os.environ.get("VOICE_TUNNEL", "1") == "1"
VOICE_PORT = int(os.environ.get("VOICE_PORT", "8765"))
VOICE_URL = [None]          # filled once cloudflared prints its URL
voice_turns = [0]
voice_lock = threading.Lock()
LAST_TURN = {}    # v53: the last turn's verbatim brain text, served at GET /last so the TEXT can be judged
                  # separately from the VOICE. Ear alone cannot tell "the model wrote gibberish" from "XTTS
                  # spoke good text badly" -- those are different bugs with different fixes.
TRACES = collections.deque(maxlen=10)   # v42: the last 10 voice-turn traces, served at GET /lat
PROBE_WAV = [None]                      # v42: a synthetic caller utterance (16 kHz mono), served at GET /probe_wav


def _fetch_cloudflared():
    """Kaggle has internet egress, so the tunnel binary comes straight from Cloudflare's release."""
    exe = "/kaggle/working/cloudflared"
    if os.path.exists(exe):
        return exe
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    try:
        import urllib.request as _u
        with _u.urlopen(url, timeout=120) as r, open(exe, "wb") as fh:
            fh.write(r.read())
        os.chmod(exe, 0o755)
        return exe
    except Exception as e:
        prog(f"cloudflared download FAIL {type(e).__name__}: {str(e)[:90]}")
        return None


def _scan_url(path, secs=40):
    """cloudflared prints its trycloudflare URL once the tunnel is up."""
    import re as _re
    end = time.time() + secs
    pat = _re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    while time.time() < end:
        try:
            with open(path, "r", errors="replace") as fh:
                m = pat.search(fh.read())
            if m:
                return m.group(0)
        except Exception:
            pass
        time.sleep(1)
    return None


# >>> VOICE_HANDLER
class ClientGone(Exception):
    """The caller hung up mid-reply."""


class VoiceHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # v42: the header line, each PCM chunk and the trailer are separate small writes; with Nagle on, a write
    # that follows an un-ACKed one can sit up to ~40 ms (delayed ACK). Every ms before the first sound counts.
    disable_nagle_algorithm = True

    def log_message(self, *a):
        pass

    def _send_bytes(self, code, body, ctype):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            self.close_connection = True

    def _send(self, code, obj):
        self._send_bytes(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            return self._send(200, {"ok": True, "voice_url": VOICE_URL[0], "auto": bool(AUTO_ENABLED),
                                    "prec": PREC, "turns": voice_turns[0], "sr": int(OUT_SR or SR)})
        if path == "/lat":   # v42: rolling per-hop stats + the last 10 full turn traces
            return self._send(200, {"stats": lat_summary(), "recent_traces": list(TRACES)})
        if path == "/probe_wav" and PROBE_WAV[0]:   # v42: lets a remote probe client fetch a real utterance
            return self._send_bytes(200, PROBE_WAV[0], "audio/wav")
        if path == "/last":   # v53: the verbatim brain text of the last turn -- the TEXT bug and the VOICE
            # v84: the noise gate's proof of work. If noise_dropped climbs while stt_count stays
            # still, the energy gate is catching the room BEFORE Whisper and the hammering has stopped.
            return self._send(200, {"ok": True, "model": LLM_MODEL, "persona_chars": len(PERSONA),
                                    "last": LAST_TURN,
                                    "noise_dropped": HALLUC_DROP[0], "stt_count": STT_COUNT,
                                    "noise_gates": {"peak_min": NOISE_PEAK_MIN, "rms_min": NOISE_RMS_MIN}})
        if path.startswith("/ab_") and AB.get(path[1:].replace(".wav", "")):   # v54: the reference A/B clips
            return self._send_bytes(200, AB[path[1:].replace(".wav", "")], "audio/wav")
        if path == "/ab":   # v54: what the A/B produced
            return self._send(200, {"ok": True,
                                    "clips": {k: len(v) for k, v in AB.items()},
                                    "text_hi": AB_TEXT_HI, "text_en": AB_TEXT_EN,
                                    "ref": os.path.basename(ref)})
        # v57 -- THE DECISIVE TEST, and it costs one push.
        # Baba reported (2026-10-03) that the SAME father's voice spoke good Hindi on the night of
        # 10-02 and again at 14:33 that morning, when the speech was PRE-RENDERED: fixed, hand-written
        # clinic lines. He was right and I was wrong to blame the reference -- lines 566-571 here are
        # character-for-character identical to v31, temperature and conditioning are identical, and the
        # A/B Hindi sentence is a full natural sentence just like the pre-rendered ones. So the model
        # side did not regress.
        # That leaves ONE variable: the text. This endpoint speaks arbitrary text on demand so the exact
        # 02:41 demo line can be pushed through TODAY's kernel and compared against the original file,
        # with nothing else changed. Same ref, same temperature, same path -- only the text varies.
        #   GET /say?text=<devanagari>&lang=hi        -> wav
        #   GET /say?text=...&use_ref=0               -> XTTS built-in voice, for contrast
        #   GET /say?probe=1                          -> what /say would produce, without running it
        if path == "/selftest":   # v61: the diagnosis, served so it can be read without pulling logs
            return self._send(200, {"ok": True, "selftest_n": SELFTEST_N,
                                    "result": SELFTEST_RESULT, "synth_total": SYNTH_COUNT["n"],
                                    "ab": {k: len(v) for k, v in AB.items()}})
        if path == "/say":
            import urllib.parse as _up
            q = _up.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            txt = (q.get("text", [""])[0]).strip()
            lg = (q.get("lang", ["hi"])[0]).strip() or "hi"
            use_ref = (q.get("use_ref", ["1"])[0]).strip() not in ("0", "false", "no")
            spd = 1.35  # Baba Law (2026-10-04 02:02): "speed should always equal 1.35"
            if q.get("probe", ["0"])[0] in ("1", "true"):
                return self._send(200, {"ok": True, "chars": len(txt), "lang": lg,
                                        "use_ref": use_ref, "ref": os.path.basename(ref),
                                        "ref_full": ref, "temperature": TEMPERATURE,
                                        "synth_mode": SYNTH_MODE, "first_max_hi": FIRST_MAX_HI,
                                        "min_piece": MIN_PIECE, "out_sr": OUT_SR or SR, "sr": SR,
                                        "speed": 1.35, "speed_unsupported": SPEED_UNSUPPORTED["yes"]})
            if not txt:
                return self._send(400, {"error": "no text"})
            try:
                t0 = time.time()
                w = _synth(hi_numbers(txt) if lg == "hi" else txt, lg, use_ref, 1.35)
                arr = np.asarray(w, dtype=np.float32)
                sr_out = int(OUT_SR or SR)
                if OUT_SR and OUT_SR != SR:
                    arr = resample(arr, SR, OUT_SR)
                    sr_out = OUT_SR
                buf = _wavbuf(arr, sr_out)
                prog("SAY lang=%s ref=%s chars=%d audio=%.2fs gen=%dms" %
                     (lg, os.path.basename(ref), len(txt), len(arr) / float(sr_out),
                      (time.time() - t0) * 1000))
                return self._send_bytes(200, buf, "audio/wav")
            except Exception as e:
                return self._send(500, {"error": repr(e)[:300]})
        return self._send(404, {"error": "no route"})

    def do_POST(self):
        # v41: this entry point was accidentally deleted by an earlier edit (the 501 "Not Implemented" was
        # exactly that -- BaseHTTPRequestHandler answers 501 when do_POST is absent). It dispatches to the
        # streaming turn by default; VOICE_STREAM=0 restores the v39 blocking JSON reply for comparison.
        if self.path.split("?")[0] != "/turn":
            return self._send(404, {"error": "no route"})
        if os.environ.get("VOICE_STREAM", "1") == "1":
            return self._turn_stream()
        try:
            n = int(self.headers.get("Content-Length", "0"))
            j = json.loads(self.rfile.read(n).decode())
        except Exception as e:
            return self._send(400, {"error": "bad body", "detail": str(e)[:80]})
        with voice_lock:
            voice_turns[0] += 1
            cid = "v" + str(voice_turns[0])
        try:
            return self._send(200, voice_turn(j.get("b64") or "", j.get("cid") or cid,
                                              j.get("lang") or LANGUAGE, speed=1.35))
        except Exception as e:
            return self._send(500, {"error": type(e).__name__, "detail": str(e)[:120]})

    # ---- STREAMING TURN (v40) ----
    # v39 returned the WHOLE reply in one JSON body, so the phone heard nothing until the last byte landed:
    # measured 7102 ms wall for a reply the seat had finished at 5261 ms -- first sound was WORSE than the
    # relay lane (5870 ms) even though the kernel was 35% faster. The fix is to stop gathering: write a JSON
    # header line, then raw PCM as each clause is synthesized, chunked, so the caller starts playing the
    # moment the FIRST clause exists instead of the last.
    #
    # Wire format: <JSON header line>\n  <raw int16 PCM ...>  <JSON trailer line>\n   (all inside HTTP chunked).
    # The PCM is in-band, so a client must treat only the FIRST line as the header and look for the trailer
    # (it starts with {"end" or {"error") at the tail.
    def _chunk(self, data):
        """One chunked-encoding frame in ONE write. A dead socket raises ClientGone, never a raw BrokenPipe."""
        if not data:
            return
        try:
            self.wfile.write(b"%X\r\n" % len(data) + data + b"\r\n")
            self.wfile.flush()
        except OSError as e:   # BrokenPipeError / ConnectionResetError are OSError subclasses
            self.close_connection = True
            raise ClientGone() from e

    def _finish_chunks(self):
        try:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except OSError:
            self.close_connection = True

    def _turn_stream(self):
        t_in = time.time()
        tr = {"t_in": t_in}
        raw_body = None
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(n)
            if (self.headers.get("Content-Type", "") or "").lower().startswith("audio/"):
                raw_body = body   # v43: raw WAV upload, no base64 (25% fewer bytes)
                j = {"lang": self.headers.get("X-Lang") or LANGUAGE}
            else:
                j = json.loads(body.decode())
        except Exception as e:
            return self._send(400, {"error": "bad body", "detail": str(e)[:80]})
        tr["body_bytes"] = n
        tr["body_read_ms"] = _ms(t_in)          # remainder of the upload after the request headers arrived
        with voice_lock:
            voice_turns[0] += 1
            cid = "v" + str(voice_turns[0])
        t = time.time()
        try:
            raw = raw_body if raw_body is not None else base64.b64decode(j.get("b64") or "")
        except Exception:
            raw = b""
        tr["b64_ms"] = _ms(t)
        if not raw:
            return self._send(400, {"error": "empty_audio"})
        lang = norm_lang(j.get("lang") or LANGUAGE)
        turn_speed = 1.35  # Baba Law (2026-10-04 02:02): "speed should always equal 1.35"
        text, stt_ms = "", 0
        if whisper is not None:
            try:
                t = time.time()
                a16 = wav_to_16k(raw)
                tr["wavdec_ms"] = _ms(t)
            except Exception as e:
                return self._send(400, {"error": "bad_wav", "detail": str(e)[:80]})
            t = time.time()
            segs, _info = whisper.transcribe(a16, language=stt_lang(lang), beam_size=STT_BEAM,
                                          vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300),
                                          without_timestamps=True, condition_on_previous_text=False,
                                          temperature=0.0, repetition_penalty=1.2, no_repeat_ngram_size=3,
                                          initial_prompt=(STT_PROMPT or None))
            text = " ".join(s.text for s in segs).strip()
            if text and is_hallucination(text):
                print(f"TURN HALLUC_DROPPED: {text[:60]!r}", flush=True)
                text = ""
            det_l = getattr(_info, "language", None)
            if det_l in ("en", "hi"):
                lang = det_l
            stt_ms = _ms(t)
        tr["stt_ms"] = stt_ms

        out_sr = int(OUT_SR or SR)
        piece_i, synth_ms, total_audio_s = 0, 0, 0.0
        first_ready_ms, first_pcm_ms, gone, spoken = None, None, False, []
        first_answer_ms = None
        pieces = None
        pcs = []
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Cache-Control", "no-store, no-transform")   # v67: do not buffer or rewrite the stream
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("X-Voice-Cid", cid)
            self.end_headers()
            t_h = time.time()
            self._chunk(json.dumps({"cid": cid, "lang": lang, "sr": out_sr,
                                    "stt_ms": stt_ms, "heard": text, "speed": turn_speed}).encode() + b"\n")
            tr["header_write_ms"] = _ms(t_h)
            tr["header_sent_ms"] = _ms(t_in)
            t_prev_end = time.time()
            if not text:
                fb = FALLBACK_HI if lang == "hi" else FALLBACK_EN
                self._chunk(json.dumps({"end": True, "reply": fb,
                                        "total_ms": _ms(t_in)}).encode() + b"\n")
                self._finish_chunks()
                return
            fil = FILLERS.get(lang) if FILLER_ON else None
            if fil:   # v43: instant acknowledgement while the LLM + first clause are still being made
                t_f = time.time()
                self._chunk(fil)
                fa = len(fil) / float(out_sr * 2)
                total_audio_s += fa
                first_pcm_ms = _ms(t_in)
                pcs.append({"k": 0, "filler": True, "chars": 0, "audio_s": round(fa, 2),
                            "ready_ms": first_pcm_ms, "write_ms": _ms(t_f)})
                t_prev_end = time.time()
            pieces = stream_reply_pieces(text, lang, tr)
            # v94 PIPELINED DUAL-GPU STREAMING: A background producer thread drains the LLM generator
            # as tokens arrive, submitting pieces to GPU 0 / GPU 1 and putting (fut, piece, gidx) into a queue.
            # The HTTP handler thread consumes from the queue and streams the very first piece to the phone
            # IMMEDIATELY when GPU 0 finishes it, without waiting for the LLM monologue to finish!
            def _synth_piece_job(piece_, gidx_):
                arr_ = synth_full_on(piece_, lang, turn_speed, gidx_)
                return finish_audio(arr_, piece_, trim=(SYNTH_MODE == "full"))

            _use_dual = m2 is not None
            _pool = concurrent.futures.ThreadPoolExecutor(max_workers=2 if _use_dual else 1)
            _q = queue.Queue()

            def _llm_producer():
                try:
                    gpu_c = 0
                    for raw_piece in pieces:
                        for piece in prep_pieces(raw_piece, lang):
                            gidx = gpu_c % 2 if _use_dual else 0
                            gpu_c += 1
                            fut = _pool.submit(_synth_piece_job, piece, gidx)
                            _q.put((fut, piece, gidx))
                except Exception as ex:
                    _q.put(("EX", ex))
                finally:
                    _q.put(None)

            prod_th = threading.Thread(target=_llm_producer, daemon=True)
            prod_th.start()

            try:
                _pi = 0
                while True:
                    item = _q.get()
                    if item is None:
                        break
                    if isinstance(item, tuple) and item[0] == "EX":
                        raise item[1]
                    fut, piece, gidx = item
                    _pi += 1
                    piece_i += 1
                    spoken.append(piece)
                    t_y = time.time()
                    rec = {"k": _pi, "chars": len(piece), "yield_ms": int((t_y - t_in) * 1000),
                           "speed": turn_speed, "gpu": gidx}
                    tp = t_y
                    a = fut.result()   # wait for THIS piece; earlier pieces on the other GPU may already be done
                    synth_ms += int((time.time() - tp) * 1000)
                    if first_ready_ms is None:
                        first_ready_ms = _ms(t_in)
                    t_en = time.time()
                    pcm = np.clip(a * 32767.0, -32768, 32767).astype(np.int16).tobytes()
                    rec["enc_ms"] = _ms(t_en)
                    audio_s = len(pcm) / float(out_sr * 2)
                    total_audio_s += audio_s
                    t_w = time.time()
                    self._chunk(pcm)
                    rec["write_ms"] = _ms(t_w)
                    rec["audio_s"] = round(audio_s, 2)
                    rec["ready_ms"] = _ms(t_in)
                    if first_answer_ms is None:
                        first_answer_ms = rec["ready_ms"]
                    if first_pcm_ms is None:
                        first_pcm_ms = rec["ready_ms"]
                    pcs.append(rec)
            finally:
                _pool.shutdown(wait=False)
        except ClientGone:   # v70: was (ClientGone, OSError). requests.RequestException subclasses OSError, so an LLM
            gone = True      # failure (401, timeout) was silently treated as a hang-up: no trailer, no audio, empty WAV.
            self.close_connection = True
        except Exception as e:
            prog("TURN ERROR %s %s: %s @%s" % (cid, type(e).__name__, str(e)[:160], _where(e)))
            try:
                self._chunk(json.dumps({"error": type(e).__name__,
                                        "detail": str(e)[:120]}).encode() + b"\n")
            except ClientGone:
                gone = True
        finally:
            if pieces is not None:
                pieces.close()   # stops the LLM stream so a dead call costs nothing more

        total_ms = _ms(t_in)
        trace = build_trace(tr, pcs, first_answer_ms if first_answer_ms is not None else first_pcm_ms, total_ms)
        trace["first_pcm_ms"] = first_pcm_ms          # first byte of any audio (the filler, if on)
        trace["first_answer_ms"] = first_answer_ms    # first byte of the real reply
        lat("voice_first_answer_ms", first_answer_ms)
        trace["cid"] = cid
        TRACES.append(trace)
        lat("voice_body_read_ms", tr.get("body_read_ms"))
        lat("voice_stt_ms", stt_ms)
        lat("voice_header_sent_ms", tr.get("header_sent_ms"))
        lat("voice_llm_first_piece_ms", trace.get("llm_first_piece_ms"))
        lat("voice_first_pcm_ms", first_pcm_ms)
        lat("voice_total_ms", total_ms)
        lat("voice_stall_ms", trace.get("stall_ms"))
        if gone:
            print(f"voice {cid}: caller hung up after {piece_i} piece(s), {total_ms} ms", flush=True)
            log_lat({"type": "voice_stream_aborted", "cid": cid, "stt_ms": stt_ms,
                     "first_ready_ms": first_ready_ms, "first_pcm_ms": first_pcm_ms,
                     "pieces": piece_i, "total_ms": total_ms})
            return   # a half-spoken turn does not go into HISTORY

        reply = " ".join(spoken).strip()
        # v53 DEBUG: print what the brain actually WROTE, verbatim. Baba is right that the gibberish is the
        # model's text and not XTTS, and that cannot be settled by ear alone -- the reply text has to be
        # visible next to the audio. Also keep the last turn so GET /last can serve it.
        print("BRAIN_TEXT heard=%r reply=%r pieces=%d first_pcm=%s"
              % (text[:60], reply[:220], piece_i, first_pcm_ms), flush=True)
        try:
            LAST_TURN.clear()
            LAST_TURN.update({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                              "heard": text, "reply": reply, "pieces": piece_i,
                              "first_pcm_ms": first_pcm_ms, "cid": cid, "lang": lang})
        except Exception:
            pass
        if reply:
            HISTORY.extend([{"role": "user", "content": text},
                            {"role": "assistant", "content": reply}])
            if LLM_HISTORY_TURNS > 0:
                del HISTORY[:-2 * LLM_HISTORY_TURNS]
        log_lat({"type": "voice_stream", "cid": cid, "stt_ms": stt_ms,
                 "first_ready_ms": first_ready_ms, "first_pcm_ms": first_pcm_ms, "synth_ms": synth_ms,
                 "pieces": piece_i, "audio_s": round(total_audio_s, 2), "total_ms": total_ms, "chars": len(reply),
                 "stall_ms": trace.get("stall_ms"), "budget": trace.get("budget"),
                 "unaccounted_ms": trace.get("unaccounted_ms")})
        try:
            self._chunk(json.dumps({"end": True, "reply": reply, "pieces": piece_i,
                                    "first_ready_ms": first_ready_ms, "first_pcm_ms": first_pcm_ms,
                                    "synth_ms": synth_ms, "audio_s": round(total_audio_s, 2),
                                    "total_ms": total_ms, "trace": trace}).encode() + b"\n")
            self._finish_chunks()
        except ClientGone:
            pass
# <<< VOICE_HANDLER


def start_voice_tunnel():
    """Serve the voice lane on VOICE_PORT and publish it through our own cloudflared tunnel."""
    if not VOICE_TUNNEL:
        return None

    class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    try:
        srv = Server(("127.0.0.1", VOICE_PORT), VoiceHandler)
    except Exception as e:
        prog(f"VOICE server bind FAIL {type(e).__name__}: {str(e)[:90]}")
        return None
    threading.Thread(target=srv.serve_forever, daemon=True, name="voice-http").start()
    prog(f"VOICE server on 127.0.0.1:{VOICE_PORT}")
    try:   # v42: was `requests.get` -> NameError (the module is imported as _rq). No-proxy opener: this is loopback.
        _op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        _op.open(f"http://127.0.0.1:{VOICE_PORT}/health", timeout=10).read()
        prog("VOICE server self-check OK")
    except Exception as e:
        prog(f"VOICE self-check FAIL {type(e).__name__}: {str(e)[:80]}")

    exe = _fetch_cloudflared()
    if not exe:
        return None
    logf = "/kaggle/working/cf-voice.log"
    try:
        with open(logf, "w") as fh:
            subprocess.Popen([exe, "tunnel", "--url", f"http://127.0.0.1:{VOICE_PORT}",
                              "--no-autoupdate", "--logfile", logf],
                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except Exception as e:
        prog(f"VOICE cloudflared spawn FAIL {type(e).__name__}: {str(e)[:90]}")
        return None
    url = _scan_url(logf, 45)
    if url:
        VOICE_URL[0] = url
        prog(f"VOICE TUNNEL LIVE {url}")
        say(f"VOICE_TUNNEL {url}", retries=5)
        report(f"VOICE_TUNNEL {url}", retries=5)
        log_lat({"type": "voice_tunnel", "url": url, "port": VOICE_PORT})
    else:
        prog("VOICE cloudflared gave no URL in 45 s")
    return url


def synth_reply_wav(text, lang, speed=None):
    """Synthesize a whole reply and return WAV bytes. Does NOT touch the relay -- this is the direct path."""
    t0 = time.time()
    parts = []
    first_ready_ms = None
    synth_ms = 0
    npieces = 0
    for piece in plan_pieces(text, lang):
        npieces += 1
        tp = time.time()
        for raw in synth_iter(piece, lang, speed=speed):
            synth_ms += int((time.time() - tp) * 1000)
            arr = finish_audio(raw, piece, trim=(SYNTH_MODE == "full"))
            if first_ready_ms is None:
                first_ready_ms = int((time.time() - t0) * 1000)
            parts.append(arr)
    if not parts:
        return b"", 0, None, 0, 0, 0.0
    out_sr = OUT_SR or SR
    joined = parts[0] if len(parts) == 1 else np.concatenate(parts)
    return (_wavbuf(joined, int(out_sr)), int(out_sr), first_ready_ms, synth_ms,
            npieces, len(joined) / float(out_sr))


def llm_reply_text(user_text, rlang):
    """The streamed brain, collected into one string (no relay involvement)."""
    chunker = SpeechChunker(rlang)
    msgs = build_messages(user_text, rlang)
    out = []
    for txt in llm_stream_hedged(msgs, LLM_MAX_NEW):
        for p in chunker.feed(clean_llm_text(txt)):
            out.append(p)
    for p in chunker.finish():
        out.append(p)
    reply = " ".join(out).strip()
    if reply:
        HISTORY.extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}])
        if LLM_HISTORY_TURNS > 0:
            del HISTORY[:-2 * LLM_HISTORY_TURNS]
    return reply


def stream_reply_pieces(user_text, rlang, trace=None):
    """Yield speakable clauses AS the model writes them, so synthesis starts on clause 1 while the rest is still
    being generated. v40: this is what lets the phone hear the first clause instead of the whole reply.
    v42: `trace` gets llm_req / llm_headers / llm_first_tok (from llm_stream) and llm_first_piece (here); closing
    this generator closes the provider stream."""
    chunker = SpeechChunker(rlang)
    gen = llm_stream_hedged(build_messages(user_text, rlang), LLM_MAX_NEW, trace)
    sent = 0   # v43: one sentence, not a monologue
    try:
        for txt in gen:
            for p in chunker.feed(clean_llm_text(txt)):
                if trace is not None and "llm_first_piece" not in trace:
                    trace["llm_first_piece"] = time.time()
                yield p
                sent += 1
                if sent >= LLM_MAX_PIECES:
                    return
        for p in chunker.finish():
            if trace is not None and "llm_first_piece" not in trace:
                trace["llm_first_piece"] = time.time()
            yield p
            sent += 1
            if sent >= LLM_MAX_PIECES:
                return
    finally:
        gen.close()


def voice_turn(b64, cid, lang="hi", speed=None):
    """Phone -> seat -> phone in ONE round trip: mic wav (b64) -> Whisper -> LLM -> XTTS -> reply wav (b64).
    (Blocking v39 path, kept for VOICE_STREAM=0 comparisons.)"""
    t_in = time.time()
    raw = base64.b64decode(b64 or "")
    if not raw:
        return {"cid": cid, "error": "empty_audio"}
    lang = norm_lang(lang)
    if whisper is not None:
        segs, _i = whisper.transcribe(wav_to_16k(raw), language=stt_lang(lang), beam_size=STT_BEAM,
                                      vad_filter=False, without_timestamps=True,
                                      condition_on_previous_text=False, temperature=0.0,
                                      initial_prompt=(STT_PROMPT or None))
        text = " ".join(s.text for s in segs).strip()
    else:
        text = ""
    stt_ms = int((time.time() - t_in) * 1000)
    info = {"stt_ms": stt_ms, "heard": text, "cid": cid, "lang": lang}
    if not text:
        info["reply"] = FALLBACK_HI if lang == "hi" else FALLBACK_EN
        return info
    t_llm = time.time()
    reply = llm_reply_text(text, lang)
    llm_ms = int((time.time() - t_llm) * 1000)
    if not reply:
        reply = FALLBACK_HI if lang == "hi" else FALLBACK_EN
    wav, sr, first_ready, synth_ms, npieces, audio_s = synth_reply_wav(reply, lang, speed=speed)
    info.update({"reply": reply, "llm_ms": llm_ms, "first_ready_ms": first_ready, "synth_ms": synth_ms,
                 "pieces": npieces, "audio_s": round(audio_s, 2), "sr": sr,
                 "total_ms": int((time.time() - t_in) * 1000)})
    lat("voice_blocking_total_ms", info["total_ms"])
    log_lat({"type": "voice_turn", "cid": cid, "stt_ms": stt_ms, "llm_ms": llm_ms,
             "first_ready_ms": first_ready, "synth_ms": synth_ms, "pieces": npieces,
             "audio_s": round(audio_s, 2), "total_ms": info["total_ms"], "chars": len(reply)})
    return {"cid": cid, "lang": lang, "b64": base64.b64encode(wav).decode(), **info}


# >>> PROBE_CLIENT  (v42: phone-style timed client; stdlib-only, also shipped as probe_voice_client.py)
def _open(base_url, timeout=30):
    """Open a connection step by step so DNS, TCP and TLS are timed separately.
    Returns (http.client connection with the socket attached, dns_ms, tcp_ms, tls_ms)."""
    import http.client
    import ssl
    u = urllib.parse.urlparse(base_url)
    https = u.scheme == "https"
    host = u.hostname
    port = u.port or (443 if https else 80)
    t = time.time()
    socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    dns = _ms(t)
    t = time.time()
    sock = socket.create_connection((host, port), timeout=timeout)
    tcp = _ms(t)
    tls = 0
    if https:
        t = time.time()
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        tls = _ms(t)
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    conn = (http.client.HTTPSConnection if https else http.client.HTTPConnection)(host, port, timeout=timeout)
    conn.sock = sock
    return conn, dns, tcp, tls


def timed_health(base_url, n=5, timeout=20):
    """GET /health n times over ONE keep-alive connection. fresh_connect_ms = DNS+TCP+TLS; warm_ms = pure round trips."""
    out = {"url": base_url}
    conn, dns, tcp, tls = _open(base_url, timeout)
    out.update(dns_ms=dns, tcp_ms=tcp, tls_ms=tls, fresh_connect_ms=dns + tcp + tls)
    rtts = []
    try:
        for _ in range(n):
            t = time.time()
            conn.request("GET", "/health")
            resp = conn.getresponse()
            resp.read()
            rtts.append(_ms(t))
    finally:
        conn.close()
    out["first_rtt_ms"] = rtts[0] if rtts else None
    out["warm_ms"] = rtts[1:]
    return out


def timed_turn(base_url, wav_bytes, lang="hi", timeout=90):
    """Phone-style streamed POST /turn. Every *_ms is measured on THIS machine's clock, from before DNS (t0).
    The server's own view comes back in the trailer (`srv`), so outside_server_ms = client first PCM minus
    server first PCM = connect + TLS + upload + tunnel + download, the part no kernel-side log can see."""
    r = {"url": base_url, "ok": False}
    t0 = time.time()
    conn = None
    try:
        conn, r["dns_ms"], r["tcp_ms"], r["tls_ms"] = _open(base_url, timeout)
        r["connect_ms"] = _ms(t0)
        raw_mode = os.environ.get("PROBE_RAW", "1") == "1"   # v43: same upload the phone should use
        body = wav_bytes if raw_mode else json.dumps({"b64": base64.b64encode(wav_bytes).decode(), "lang": lang}).encode()
        r["req_kb"] = round(len(body) / 1024.0, 1)
        t_s = time.time()
        conn.putrequest("POST", "/turn")
        conn.putheader("Content-Type", "audio/wav" if raw_mode else "application/json")
        conn.putheader("X-Lang", lang)
        conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        t_sent = time.time()
        r["send_ms"] = int((t_sent - t_s) * 1000)
        resp = conn.getresponse()
        r["status"] = resp.status
        r["response_headers_ms"] = _ms(t0)                       # includes upload + server STT (headers go out after STT)
        r["server_wait_ms"] = int((time.time() - t_sent) * 1000)  # request fully sent -> response headers
        arrivals = []
        buf = bytearray()
        while True:
            d = resp.read1(65536)
            if not d:
                break
            arrivals.append((time.time(), len(d)))
            buf += d
        data = bytes(buf)
        if resp.status != 200:
            r["error_body"] = data[:300].decode("utf-8", "replace")
            return r
        nl = data.find(b"\n")
        hdr = {}
        try:
            hdr = json.loads(data[:nl].decode()) if nl >= 0 else {}
        except Exception:
            pass
        sr = int(hdr.get("sr") or 16000)
        lo = nl + 1
        cands = [i for i in (data.rfind(b'{"end"'), data.rfind(b'{"error"')) if i >= lo]
        hi = min(cands) if cands else len(data)
        r["end_missing"] = data.rfind(b'{"end"') < lo
        off = 0
        aud, hdr_t, first_t, last_t = [], None, None, None
        for t, n_ in arrivals:
            a, b = off, off + n_
            off = b
            if hdr_t is None and b > nl >= 0:
                hdr_t = t
            ov = max(0, min(b, hi) - max(a, lo))
            if ov > 0:
                if first_t is None:
                    first_t = t
                last_t = t
                aud.append((t - t0, ov / float(sr * 2)))
        gaps, stall = playback_stalls(aud)
        r["hdr_line_ms"] = int((hdr_t - t0) * 1000) if hdr_t else None
        r["first_pcm_ms"] = int((first_t - t0) * 1000) if first_t else None
        r["last_pcm_ms"] = int((last_t - t0) * 1000) if last_t else None
        r["end_ms"] = int((arrivals[-1][0] - t0) * 1000) if arrivals else None
        r["audio_s"] = round(sum(a for _, a in aud), 2)
        r["stall_ms"] = int(stall * 1000)
        r["reads"] = len(arrivals)
        r["heard"] = hdr.get("heard")
        r["sr"] = sr
        end_j = {}
        try:
            end_j = json.loads(data[hi:].split(b"\n", 1)[0].decode()) if hi < len(data) else {}
        except Exception:
            pass
        r["reply"] = end_j.get("reply")
        r["srv"] = end_j
        st = (end_j.get("trace") or {}) if isinstance(end_j, dict) else {}
        if r["first_pcm_ms"] is not None and st.get("first_pcm_ms") is not None:
            r["outside_server_ms"] = r["first_pcm_ms"] - st["first_pcm_ms"]
        r["ok"] = bool(first_t)
    except Exception as e:
        r["error"] = type(e).__name__ + ": " + str(e)[:140]
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    r["wall_ms"] = _ms(t0)
    return r
# <<< PROBE_CLIENT


# ---------- 8. LATENCY PROBE (v42) ----------
# Times every hop, three ways:
#   components : relay GET/POST, Whisper, LLM (headers -> first token -> first clause), XTTS at several piece
#                sizes, silence-trim / WAV / base64 cost.
#   loopback   : a full phone-style /turn against 127.0.0.1 = the seat's own work with the network removed.
#   tunnel     : the same turn through our own trycloudflare URL, from inside Kaggle (adds Cloudflare's edge).
# The caller utterance is synthesized by XTTS itself, so the probe needs no recorded file.
# NOT measured here: the phone's own radio and the phone->Cloudflare leg. Run probe_voice_client.py FROM THE
# PHONE'S NETWORK (laptop or Termux) for that; its outside_server_ms is exactly that missing number.
PROBE_Q_HI = "डॉक्टर साहब की टाइमिंग क्या है?"
PROBE_TTS_TEXT = ("नमस्ते, आपका स्वागत है। डॉक्टर साहब सुबह दस बजे से दोपहर एक बजे तक और शाम को पाँच बजे से आठ बजे तक "
                  "मिलते हैं। कृपया अपना नाम और फ़ोन नंबर बताइए, मैं आपका समय लिख लेता हूँ।")


def ensure_probe_wav():
    if PROBE_WAV[0]:
        return PROBE_WAV[0]
    arr = synth_full(PROBE_Q_HI, "hi")
    arr = resample(np.asarray(arr, dtype=np.float32).squeeze(), SR, 16000)
    PROBE_WAV[0] = _wavbuf(arr, 16000)
    return PROBE_WAV[0]


def _med(xs):
    xs = [x for x in (xs or []) if isinstance(x, (int, float))]
    return int(statistics.median(xs)) if xs else None


def _p_relay():
    out = {}
    t = time.time()
    d = gate()
    out["gate_ms"] = _ms(t)
    out["door"] = d
    if not d:
        out["error"] = "no relay door reachable"
        return out
    tok_q = urllib.parse.quote(RELAY_TOKEN)
    hs, ps, ss = [], [], []
    for _ in range(3):
        t = time.time()
        http_get(DOOR + "/health?token=" + tok_q, 20)
        hs.append(_ms(t))
    probe_reader = "probe-" + str(int(time.time()))   # NOT the seat's READER_ID: must not consume live HEAR rows
    for _ in range(3):
        t = time.time()
        http_get(DOOR + f"/say?token={tok_q}&body={urllib.parse.quote(SELF_BODY)}&limit=5&live=1"
                        f"&reader={probe_reader}", 30)
        ps.append(_ms(t))
    for i in range(2):
        t = time.time()
        _post("/say", OUT_BODY, f"LIVE PROBE ping {i + 1}")
        ss.append(_ms(t))
    out.update(health_get_ms=hs, poll_get_ms=ps, say_post_ms=ss)
    return out


def _p_stt(wav):
    if whisper is None:
        return {"error": "whisper unavailable"}
    t = time.time()
    a = wav_to_16k(wav)
    dec = _ms(t)
    runs, text = [], ""
    for _ in range(3):
        t = time.time()
        segs, _i = whisper.transcribe(a, language="hi", beam_size=STT_BEAM, vad_filter=False,
                                      without_timestamps=True, condition_on_previous_text=False, temperature=0.0,
                                      initial_prompt=(STT_PROMPT or None))
        text = " ".join(s.text for s in segs).strip()
        runs.append(_ms(t))
    return {"audio_s": round(len(a) / 16000.0, 2), "wavdec_ms": dec, "ms": runs, "heard": text}


def _p_llm():
    if not _brain_ready():
        return {"error": "brain not ready"}
    runs = []
    for _ in range(3):
        tr = {}
        t = time.time()
        try:
            ps = list(stream_reply_pieces(PROBE_Q_HI, "hi", tr))
        except Exception as e:
            runs.append({"error": type(e).__name__ + ": " + str(e)[:100], "total_ms": _ms(t)})
            continue
        total = _ms(t)

        def d(k):
            return int((tr[k] - tr["llm_req"]) * 1000) if (k in tr and "llm_req" in tr) else None
        runs.append({"headers_ms": d("llm_headers"), "first_tok_ms": d("llm_first_tok"),
                     "first_piece_ms": d("llm_first_piece"), "total_ms": total, "pieces": len(ps),
                     "chars": sum(len(p) for p in ps), "first_piece": ps[0] if ps else ""})
    return runs


def _p_tts():
    out = []
    out_sr = int(OUT_SR or SR)
    for cap, reps in ((FIRST_MAX_HI, 3), (60, 1), (100, 1), (char_limit("hi"), 1)):
        piece, _rest = take_piece(PROBE_TTS_TEXT, cap)
        gens, walls, raw = [], [], None
        for _ in range(reps):
            t = time.time()
            raw = synth_full(piece, "hi")
            walls.append(_ms(t))
            gens.append((getattr(_tl, "tts", None) or {}).get("gen_ms"))
        t = time.time()
        arr = finish_audio(raw, piece, trim=True)
        post = _ms(t)
        t = time.time()
        buf = _wavbuf(arr, out_sr)
        enc = _ms(t)
        t = time.time()
        base64.b64encode(buf)
        b64ms = _ms(t)
        raw_s = len(raw) / float(SR)
        out.append({"cap": cap, "chars": len(piece), "wall_ms": walls, "gen_ms": gens,
                    "raw_audio_s": round(raw_s, 2), "audio_s": round(len(arr) / float(out_sr), 2),
                    "rtf": round(_med(walls) / 1000.0 / max(raw_s, 1e-6), 2), "post_ms": post,
                    "wav_enc_ms": enc, "b64_ms": b64ms, "wav_kb": round(len(buf) / 1024.0, 1)})
    return out


def _p_loopback():
    wav = ensure_probe_wav()
    base = f"http://127.0.0.1:{VOICE_PORT}"
    return {"health": timed_health(base, 5), "turns": [timed_turn(base, wav, "hi") for _ in range(max(1, PROBE_TURNS))]}


def _p_tunnel():
    url = VOICE_URL[0]
    if not url:
        return {"error": "no tunnel url"}
    wav = ensure_probe_wav()
    return {"url": url, "health": timed_health(url, 5),
            "turns": [timed_turn(url, wav, "hi") for _ in range(max(1, PROBE_TURNS - 1))]}


def probe_lines(rep):
    """Human-readable summary of a probe report (also printed to the kernel log)."""
    L = []
    r = rep.get("relay")
    if isinstance(r, dict) and "error" not in r:
        L.append(f"relay      gate {r.get('gate_ms')} ms | health GET {r.get('health_get_ms')} | "
                 f"live poll GET {r.get('poll_get_ms')} | /say POST {r.get('say_post_ms')}")
    elif r:
        L.append(f"relay      {r}")
    s = rep.get("stt")
    if isinstance(s, dict) and "error" not in s:
        L.append(f"stt        {s.get('audio_s')} s audio | wav decode {s.get('wavdec_ms')} ms | transcribe {s.get('ms')} ms | heard: {s.get('heard')!r}")
    elif s:
        L.append(f"stt        {s}")
    q = rep.get("llm")
    if isinstance(q, list):
        for i, x in enumerate(q, 1):
            if "error" in x:
                L.append(f"llm run {i}  ERROR {x['error']} after {x.get('total_ms')} ms")
                continue
            L.append(f"llm run {i}  headers {x['headers_ms']} | first token {x['first_tok_ms']} | first clause {x['first_piece_ms']} | "
                     f"all {x['total_ms']} ms | {x['pieces']} piece(s), {x['chars']} chars")
    elif q:
        L.append(f"llm        {q}")
    t = rep.get("tts")
    if isinstance(t, list):
        for x in t:
            L.append(f"tts {x['cap']:>3}ch  piece {x['chars']:>3} chars -> {x['raw_audio_s']} s raw / {x['audio_s']} s after trim | "
                     f"gen {x['gen_ms']} ms (rtf {x['rtf']}) | trim {x['post_ms']} + wav {x['wav_enc_ms']} + b64 {x['b64_ms']} ms | {x['wav_kb']} KB")
    elif t:
        L.append(f"tts        {t}")
    for name in ("loopback", "tunnel"):
        blk = rep.get(name)
        if not isinstance(blk, dict):
            continue
        if "error" in blk:
            L.append(f"{name:<10} {blk['error']}")
            continue
        h = blk.get("health") or {}
        L.append(f"{name:<10} health: fresh connect {h.get('fresh_connect_ms')} ms (dns {h.get('dns_ms')} tcp {h.get('tcp_ms')} tls {h.get('tls_ms')}) | warm RTT {h.get('warm_ms')}")
        for i, tn in enumerate(blk.get("turns") or [], 1):
            if not tn.get("ok"):
                L.append(f"{name:<10} turn {i} FAILED {tn.get('error') or tn.get('error_body')}")
                continue
            st = (tn.get("srv") or {}).get("trace") or {}
            L.append(f"{name:<10} turn {i}: first sound {tn.get('first_pcm_ms')} ms | server says {st.get('first_pcm_ms')} ms | answer starts {st.get('first_answer_ms')} ms | "
                     f"outside server {tn.get('outside_server_ms')} ms | connect {tn.get('connect_ms')} | upload {tn.get('send_ms')} ms for {tn.get('req_kb')} KB | "
                     f"stalls {tn.get('stall_ms')} ms | total {tn.get('end_ms')} ms | audio {tn.get('audio_s')} s")
            if st.get("budget"):
                L.append("             first-sound budget: " + " + ".join(f"{k} {v}" for k, v in st["budget"]) +
                         f" + unaccounted {st.get('unaccounted_ms')} = {st.get('first_pcm_ms')} ms")
    return L


def probe_compact(rep):
    """A handful of numbers for the relay report and the log."""
    c = {"tag": rep.get("tag"), "prec": rep.get("prec")}
    try:
        r = rep.get("relay") or {}
        c.update(relay_health=_med(r.get("health_get_ms")), relay_poll=_med(r.get("poll_get_ms")), relay_say=_med(r.get("say_post_ms")))
        s = rep.get("stt") or {}
        c["stt"] = _med(s.get("ms")) if isinstance(s, dict) else None
        q = rep.get("llm")
        if isinstance(q, list):
            c["llm_errors"] = sum(1 for x in q if "error" in x)
            q = [x for x in q if "error" not in x]
            c.update(llm_headers=_med([x["headers_ms"] for x in q]), llm_first_tok=_med([x["first_tok_ms"] for x in q]),
                     llm_first_piece=_med([x["first_piece_ms"] for x in q]))
        t = rep.get("tts")
        if isinstance(t, list) and t:
            c.update(tts_first_piece_chars=t[0]["chars"], tts_first_piece_gen=_med(t[0]["gen_ms"]), tts_rtf=t[0]["rtf"])
        for name in ("loopback", "tunnel"):
            blk = rep.get(name) or {}
            if name == "tunnel" and blk.get("url"):
                c["tunnel_url"] = blk.get("url")
            turns = [x for x in (blk.get("turns") or []) if x.get("ok")]
            if turns:
                c[name + "_first_pcm"] = _med([x["first_pcm_ms"] for x in turns])
                c[name + "_outside_server"] = _med([x.get("outside_server_ms") for x in turns])
                c[name + "_stall"] = _med([x["stall_ms"] for x in turns])
            h = blk.get("health") or {}
            if h:
                c[name + "_warm_rtt"] = _med(h.get("warm_ms"))
                c[name + "_connect"] = h.get("fresh_connect_ms")
    except Exception as e:
        c["compact_err"] = type(e).__name__ + ": " + str(e)[:80]
    return c


def run_probe(tag="boot"):
    """Run every stage, never raising. Writes /kaggle/working/probe_report.json, logs, and reports one summary line."""
    t_all = time.time()
    saved_hist = list(HISTORY)       # loopback turns would otherwise leak into a real caller's history
    rep = {"tag": tag, "prec": PREC, "stage_ms": {}}
    prog(f"PROBE start tag={tag}")

    def stage(name, fn, *a):
        t = time.time()
        try:
            rep[name] = fn(*a)
        except Exception as e:
            rep[name] = {"error": type(e).__name__ + ": " + str(e)[:140], "where": _where(e)}
        rep["stage_ms"][name] = _ms(t)

    stage("wav", lambda: {"bytes": len(ensure_probe_wav())})
    wav = PROBE_WAV[0]
    stage("relay", _p_relay)
    if wav:
        stage("stt", _p_stt, wav)
    stage("llm", _p_llm)
    stage("tts", _p_tts)
    if VOICE_TUNNEL:
        stage("loopback", _p_loopback)
        if PROBE_TUNNEL:
            stage("tunnel", _p_tunnel)
    HISTORY[:] = saved_hist
    rep["probe_total_ms"] = _ms(t_all)
    rep["lat_stats"] = lat_summary()
    try:
        with open(WORK + "/probe_report.json", "w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=1)
    except Exception as e:
        print("probe_report write FAIL", e, flush=True)
    for line in probe_lines(rep):
        print("PROBE " + line, flush=True)
    comp = probe_compact(rep)
    log_lat({"type": "probe", **comp})
    report(json.dumps({"kind": "probe", **comp}, ensure_ascii=True))
    prog(f"PROBE done tag={tag} in {rep['probe_total_ms']} ms -> probe_report.json | " +
         " ".join(f"{k}={v}" for k, v in comp.items() if k not in ("tag", "prec") and v is not None)[:600])
    if tag == "boot":
        with _lat_lock:
            LAT_STATS.clear()   # live stats should describe real calls, not the probe
    return rep


start_voice_tunnel()
if PROBE_ON_BOOT:
    try:
        run_probe("boot")
    except Exception as e:
        prog(f"PROBE crashed {type(e).__name__}: {str(e)[:120]} @{_where(e)}")

T0 = time.time()
last_job = T0
last_beat = T0
last_lat_sum = T0
hot_until = T0 + HOT_WINDOW_SEC
CALLS = 0
seen = set()
baseline = True   # first poll silences history: never re-synthesize orders from earlier sessions
beats = 0
print(f"WARM body={SELF_BODY} poll={POLL_SEC}s hot={POLL_HOT_SEC}s", flush=True)
prog(f"WARM body={SELF_BODY} poll={POLL_SEC}s hot={POLL_HOT_SEC}s idle_kill={IDLE_KILL_MIN}m cap={HARD_CAP_MIN}m lang={LANGUAGE} "
     f"ref={os.path.basename(ref)} prec={PREC} ramp={RAMP_EFF:.2f} auto={AUTO_ENABLED}")
print("WARM", flush=True)

while True:
    t_poll = time.time()
    if beats % 100 == 0:
        print(f"POLL loop iteration {beats + 1}", flush=True)
    if t_poll - T0 > HARD_CAP_MIN * 60:
        bye("HARD_CAP")
    for o in orders():
        otxt = o.get("text", "") or ""
        key = (str(o.get("at", "")), hash(otxt))   # hash, not the text: HEAR rows are ~400 KB
        if key in seen:
            continue
        seen.add(key)
        age = order_age_ms(o.get("at"))
        if baseline or (age is not None and age > 30000):   # baseline or orders older than 30s are silenced
            continue
        if otxt.startswith("HEAR"):
            hot_until = time.time() + HOT_WINDOW_SEC
            do_hear(otxt)
            last_job = time.time()
            continue
        if otxt.startswith("AUTO_"):
            hot_until = time.time() + HOT_WINDOW_SEC
            handle_auto(otxt)
            last_job = time.time()
            continue
        if otxt.startswith("PROBE"):   # v42: re-run the whole latency probe on demand
            hot_until = time.time() + HOT_WINDOW_SEC
            try:
                run_probe("order")
            except Exception as e:
                prog(f"PROBE crashed {type(e).__name__}: {str(e)[:120]} @{_where(e)}")
            last_job = time.time()
            continue
        if otxt.startswith("WHERE_TUNNEL") or otxt.startswith("GET_TUNNEL"):
            say(f"VOICE_TUNNEL {VOICE_URL[0]}")
            report(f"VOICE_TUNNEL {VOICE_URL[0]}")
            continue
        if otxt.startswith("LIVE_END"):
            bye("RELAY_END")
        if not otxt.startswith("LIVE_CALL"):
            continue
        hot_until = time.time() + HOT_WINDOW_SEC
        payload = otxt[len("LIVE_CALL"):].strip()
        cid = f"c{int(time.time())}"
        ctext, lang = "", LANGUAGE
        try:
            j = json.loads(payload)
            cid = str(j.get("cid") or cid)
            ctext = str(j.get("text", "")).strip()
            lang = j.get("lang", LANGUAGE)
        except Exception:
            ctext = payload
        if not ctext:
            say(f"LIVE_REJECT {cid} empty text")
            continue
        CALLS += 1
        last_job = time.time()
        print(f"CALL {cid} len={len(ctext)} lang={norm_lang(lang)}", flush=True)   # print only: a relay post here delayed every reply
        do_call(cid, ctext, lang, age)
        last_job = time.time()
        hot_until = time.time() + HOT_WINDOW_SEC
    if baseline and len(seen) > 0:
        baseline = False
        prog(f"BASELINE done: {len(seen)} historical orders silenced")
    if time.time() - last_job >= IDLE_KILL_MIN * 60:
        bye("IDLE_KILL")
    beats += 1
    if time.time() - last_beat >= HEARTBEAT_SEC:
        last_beat = time.time()
        beat = f"LIVE_BEAT up={int(time.time() - T0)}s idle={int(time.time() - last_job)}s gpu_s={int(time.time() - T0)} polls={beats} tunnel={VOICE_URL[0]}"
        print(beat, flush=True)
        say_async(beat)
        if VOICE_URL[0]:
            say_async(f"VOICE_TUNNEL {VOICE_URL[0]}")
    if time.time() - last_lat_sum >= LAT_SUMMARY_SEC:   # v42: rolling per-hop stats into the latency log
        last_lat_sum = time.time()
        _sm = lat_summary()
        if _sm:
            log_lat({"type": "lat_summary", "stats": _sm})
    period = POLL_HOT_SEC if time.time() < hot_until else POLL_SEC
    time.sleep(max(0.0, period - (time.time() - t_poll)))
# v13 Baba run: Hindi digit spelling (num2words has no hi), hi limit 140, KILO_LANG env, failure location in relay msgs
# v14: STT on the T4 (faster-whisper). New order HEAR {cid,lang,b64} -> HEARD {cid,text,ms} report.
# v24: first poll silences history (baseline flag).
# v25: do_hear decodes WAVs itself (seat PyAV older than faster-whisper expects).
# v28: SYNTH_MODE=full -- each text piece synthesized COMPLETE; inference_stream slices ended mid-word.
# v29: SELF_BODY default LIVE-VOX1 so a stale seat from an earlier version is silent by construction.
# v30: orders() polls with live=1 + per-boot READER_ID (57x smaller steady-state read).
# v31: LATENCY PASS. (1) adaptive polling: 0.35 s while a conversation is live (was a fixed 2 s = ~1 s average
#      pickup lag). (2) persistent keep-alive HTTP sessions instead of a new TLS connection per request.
#      (3) uploads run on background threads: synthesis no longer blocks on ~12 sequential 50 KB POSTs, and the
#      synchronous "CALL" progress post that delayed every reply is now print-only. (4) short first piece + piece
#      sizes that ramp with the measured synth speed, so first audio waits for ~3 s of speech, not ~9 s, and the
#      next piece is ready before the previous one finishes playing. (5) startup self-benchmark picks the fastest
#      of fp32 / fp16-autocast / fp16 that still sounds sane, reverting on any failure. (6) lead/tail silence
#      trimmed per piece. (7) Whisper moved to GPU 1 and warmed up; HEAR no longer writes a WAV to disk and
#      skips timestamps/fallback re-decodes. (8) per-call log now splits first_ready_ms / first_ms (first part
#      actually posted) / synth_ms / flush_ms / order_age_ms so the next bottleneck is visible.
# v32: BRAIN. The engine now decides what to say: HEAR -> Whisper -> on-seat LLM (GPU 1, streamed) -> first clause to
#      XTTS (GPU 0) while the LLM is still writing the rest. Scripted LIVE_CALL still works unchanged. New orders:
#      AUTO_ON / AUTO_OFF / AUTO_RESET / AUTO_PERSONA <text> / AUTO_ASK {"text":..}. Transcript reports carry "auto":true
#      so the laptop knows not to send its own reply; the spoken text comes back as {"kind":"auto_reply","reply":..}.
#      TTS precision A/B: ab_fp32.wav / ab_autocast.wav / ab_half.wav (same line, same seed) are saved to /kaggle/working;
#      TTS_PRECISION=half|autocast forces a mode (kept whenever the audio is sane), =fp32 pins full precision.
# v36: provider brain (nemotron via NVIDIA API), internal-silence collapse, 16 kHz output, 90 KB chunks.
# v39: direct voice tunnel (cloudflared inside the kernel), IDLE_KILL 120 min / HARD_CAP 175 min.
# v40: streaming /turn (header line, then PCM per clause), FIRST_MAX_HI 26.
# v41: restored do_POST (its deletion was the 501 "Not Implemented").
# v42: (1) ClientGone: a hang-up mid-reply is one log line + a voice_stream_aborted record, the LLM stream is
#      closed, aborted turns stay out of HISTORY. (2) self-check no longer references an undefined `requests`.
#      (3) LATENCY PROBE: lat()/lat_summary() rolling stats, per-turn trace (body read, b64, wav decode, STT,
#      header write, LLM headers / first token / first clause, TTS lock wait, GPU gen, trim, PCM encode, socket
#      write, per-piece playback gap) returned in the /turn trailer and logged; GET /lat, GET /probe_wav;
#      boot probe + `PROBE` relay order -> probe_report.json; probe_voice_client.py measures from the caller's side.
#      (4) shared provider HTTP session + connection pre-warm (was: a new TLS connection per phone turn).
#      (5) TCP_NODELAY on the voice socket. (6) TTS_LOCK so overlapping turns cannot race XTTS.
# v43: (1) provider tail latency: 4 s connect / 8 s read timeouts, hedged 2nd request after 2.5 s without a token,
#      retry on error, both cancelled on hang-up. (2) one-sentence cap + 20-char first clause. (3) instant
#      acknowledgement pre-synthesized at boot; trace now reports first_pcm_ms (filler) AND first_answer_ms.
#      (4) Whisper large-v3-turbo with clinic prompt, falls back to small. (5) /turn accepts audio/wav bodies.
#      (6) API key from env / Kaggle Secret LLM_API_KEY (+ optional LLM_API_KEYS). (7) probe fixes.
# v67: LATENCY PASS (pipeline only; voice, speed, temperature, reference, SYNTH_MODE, OUT_SR, FIRST_MAX_HI, MIN_PIECE untouched).
#      (1) collapse_silence: per-sample Python loop -> numpy run boundaries, identical output.
#      (2) hedged LLM request: 2nd attempt goes to NVIDIA key 2 (same 120b model) instead of the OpenRouter model that v52
#          measured as slow and romanised; LLM_HEDGE_HOST=openrouter restores v66. Hedge deadline 1.8 s -> 1.2 s.
#      (3) /turn response sends Cache-Control: no-store, no-transform and X-Accel-Buffering: no (unverified; costs nothing).
