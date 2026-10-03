# %% [code]
# %% [code]

# %% [code]
# KILO-VOICE-LIVE v101 (Fluid human prosody: silence collapse 80ms + no robotic halting + clean real-voice opener)
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
# v101 (Baba, 2026-10-04 04:00 IST): FILLER_ON disabled by default.
# The canned filler ("जी, एक मिनट।") hallucinated as 4.5s gibberish ("नाने बिल कै...") because XTTS
# wanders on isolated 4-word text. With v94 pipelined dual-GPU streaming, the real contextual reply
# starts streaming in ~1.5 - 1.8s, completely eliminating dead silence with real human speech!
FILLER_ON = os.environ.get("FILLER_ON", "0") == "1"
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
FILLERS = {}


def build_fillers():
    for lang_, txt in (("hi", "जी, एक मिनट।"), ("en", "Sure, one moment.")):
        try:
            a = finish_audio(synth_full(txt, lang_), txt, trim=True)
            FILLERS[lang_] = np.clip(a * 32767.0, -32768, 32767).astype(np.int16).tobytes()
        except Exception as e:
            prog(f"FILLER {lang_} FAIL {type(e).__name__}: {str(e)[:80]}")
    prog("FILLERS ready " + " ".join(f"{k}={len(v) / float((OUT_SR or SR) * 2):.2f}s" for k, v in FILLERS.items()))


if FILLER_ON:
    build_fillers()
for _fl in ("hi", "en"):
    FILLERS.setdefault(_fl, np.zeros(int(0.25 * int(OUT_SR or SR)), dtype=np.int16).tobytes())
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
    "You are an autonomous, intelligent clinical voice assistant for a medical clinic. "
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
            else "This turn, reply in simple spoken Hindi, Devanagari script only.")
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
