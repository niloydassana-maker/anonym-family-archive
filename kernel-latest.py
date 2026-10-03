# %% [code]
# %% [code]

# %% [code]
# KILO-VOICE-LIVE v102 (Pristine 800ms Studio-Quality Hindi/English Openers + 80ms Silence Collapse + Speed=1.35 Locked)
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
# v102 (Baba Law, 2026-10-04 04:30 IST): FILLER_ON=1 PERMANENT 800ms LATENCY GUARANTEE.
# Pre-baked studio-quality 24kHz Hindi ('जी, एक मिनट।') & English ('Sure, one moment.') openers.
# ZERO hallucination, ZERO gibberish, instant ~800ms response to caller before real reply begins.
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
FILLER_B64_HI = 'AQAAAAEAAAAAAAIAAAAAAAAAAQABAAAAAAAAAAAAAAABAP//AQABAAAAAAABAAAAAAAAAAAAAgAAAP//AQABAAAAAAAAAAEAAgABAAAAAAAAAAAAAQAAAAAAAAABAAAAAAABAAAAAAAAAAAAAQAAAAAAAAAAAAAAAQAAAAAAAQAAAAIAAQAAAAAAAQABAAAAAQABAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAEAAAAAAAAAAgAAAAEAAAAAAAEAAAAAAAAAAAABAAAAAAABAAAAAAAAAAEAAAAAAAAAAAABAAAAAAAAAAAAAAABAP//AAAAAAEAAQAAAAEAAAABAAEAAQABAAEAAAAAAAAAAAAAAAEAAQAAAAEAAAABAAEAAAAAAAAAAAAAAP//AAAAAP////////////////////8AAP//AAAAAP////8AAP////8AAP//AAD//wAAAAAAAAAA//8AAAAAAAAAAAAAAQAAAAAAAgABAAEAAAAAAAAAAQABAAAAAgAAAAAAAAABAAEAAQABAAAAAQAAAAEAAQAAAAEAAAACAAAAAQAAAAAAAQAAAAEA//8AAAAAAQABAAAAAgAAAAAAAQAAAAAA//8AAP7//v////3/AAD//wAAAAABAAMAAQADAAEAAgAAAAEAAwAAAAIA//8BAAAAAgACAAIABgACAAQABAADAAIAAgACAAEAAwABAAEAAAAAAP//AQAAAP/////+/////f/+//z////9////AAD+/wEA/v8BAP7/AAD+//7/AQD6//7/+//9//r//P/8//r//v/6//3/+//7//r/+//8//r//P/7//z//f/8//3//v/+//7///////7/AQAAAAAAAgAAAAMAAwAEAAQABwAHAAUACgAJAAsACwAOAA8AEgATABAAFgAVABcAGAAaABoAGgAdABwAHwAeACEAIgAjACQAJAAnACUAKAAmACcAKAAmACYAJgAlACEAIgAfABwAGQAUABEADAAJAAEA/v/5//L/7//p/+P/3P/W/9D/y//F/7//uv+z/67/qf+j/6D/mv+X/5H/jP+H/4H/f/94/3T/b/9q/2X/YP9e/1n/WP9U/1P/Uv9T/1P/Uv9W/1f/Xf9h/2f/cP94/4T/jv+b/6f/tv/F/9b/6P/7/w8AIQA4AEwAYwB5AI0ApgC7ANIA5wD9ABMBKQE+AVIBZwF6AY8BoQG2AcQB1AHlAfEBAAIMAhgCIwIuAjUCQAJHAk0CVwJdAmcCagJxAnQCdQJ1AnECawJhAlQCPwItAg8C8AHIAZgBaAErAesApABbAAsAt/9d/wH/of4//uD9fP0g/cH8aPwT/L/7dfsv++/6ufqI+l76Pvoi+hD6BfoD+gb6Dfoa+i/6Rfpi+oH6oPrK+u/6GvtG+3L7ofvR+wP8NPxp/Jz81/wP/U79kP3R/Rv+Zv62/gj/W/+z/wsAZgDHACkBjAH1AVwCxQIwA5cDAARsBNIEOwWgBQUGZQbCBhwHcAe7BwIIRQh9CLMI3AgECSIJNQlCCUAJOAkmCQ0J6gjHCJcIZAgzCPcHvweDB0UHAwe+BnoGLQbdBYkFLAXKBGEE7gNwA+0CWgLCAR8BcgC+/wD/P/54/a384PsY+0n6gvnA+AP4Ufeo9hL2f/UG9Zj0PPT087rzkPNz83HzcfOK863z2/MQ9FD0mPTe9DT1g/Xf9Tr2mPb09lL3r/cL+G/4zfgz+ZD5+Pla+r/6KvuT+wX8dfzs/GH94f1c/t/+a//0/4cAGAGvAUEC1gJsA/8DkwQoBbYFRgbRBlMH1wdTCMUIMQmUCewJQQqICssKBws0C14LgguZC6gLsAuuC6QLkwt/C1oLMgsFC8oKjApKCgEKrQlhCQ4JuQhqCB4I0QeJB00HAwfABn8GLQbaBYgFIwW5BFIE0wNMA8ECIwJ1AccABgA2/2b+iv2q/Mf74fr7+Rj5NPhY94b2tPX09ET0nPMP85jyMPLh8avxfvFj8WDxZPF08ZrxyfEA8kPyj/Ld8jDziPPj8z30mfT39FH1rvUR9nD21PY+96L3B/hv+Nv4SPm9+T76w/pT++r7h/wk/cX9af4S/8D/bgAgAdYBkQJPAw8EzgSHBTkG6QaTBzYI0whuCQMKjgoXC5ULAwxsDMwMGw1lDakN3Q0KDjMOSw5WDloOSw4vDg0O4A2nDWwNKQ3fDJEMNgzbC3wLGAu9CmoKFArFCYYJPwn2CLAIXgj7B5kHLAerBigGmAXxBEUEiQOuAsYB1ADM/7v+p/2I/Gb7S/ow+Rj4Cff79fb0A/Qd80jyjPHl8Ffw5O+I70PvE+/w7uXu7O787h7vUe+K783vG/Bm8LLwB/Fd8bfxGvJ+8uXyU/PC8zT0p/QW9Yr1AvZ89v72ivcb+Lf4X/kM+r76d/sx/PD8tv1+/kv/IgD9ANgBuQKZA3QETgUkBvMGvgeGCEgJBQq+CmkLBQyYDB4NlQ0FDm0Oyg4cD2cPpg/WD/UPCRAREAsQ/g/sD84PpA92Dz0P9Q6qDlcO8w2ODSoNwQxZDPsLoAtIC/kKrQpaCgAKnwk1Cb8IQgi6ByIHfwbOBQYFKAQ2Ay0CEwHy/8n+mv1l/C/7+vnD+I33YfY79R30E/Me8jrxb/C87yDvnu4z7tvtnO1x7VXtT+1i7YHtrO3l7SPuZu6u7vruSO+c7/LvUPC38CHxjvEA8nLy4/JW887zTPTS9GT1Afas9l73F/jX+Jr5X/os+wL83/zF/bT+p/+eAJQBiQJ/A3EEYAVPBjsHIwgNCfIJygqYC1oMDg24DVQO3g5fD9gPRBCoEP4QPRFuEZURrBGzEbIRoxGIEWkRQBEJEcYQeRAfEL4PWQ/pDnUOBg6RDRsNrQxEDN0LgAspC80KcAoNCp0JJQmeCAUIXwepBtsF/AQHBP0C4wG2AH3/PP7r/JP7Pvro+JD3RPb+9Lzzi/Jq8VfwXu9+7rvtGu2a7DXs7Ou6653rk+uY67Dr2+sQ7Fbsq+wD7Vztvu0f7n7u5e5O77jvLPCm8CTxpvEq8q7yM/O680f02fRy9Rv20faU92T4P/ke+gL77fvc/M/9yv7L/9YA6gEBAxgEKwU4Bj4HPwg8CTQKKAsZDAYN6A28Dn8PLRDJEFYR1RFJEq4SCRNXE5QTwBPdE+QT2BPCE50TbRMwE+oSmhI6Es0RVRHKEDAQkw/sDj4OnA38DFUMwQs0C54KGgqiCR0JnggtCKwHIgegBgsGaAW9BP4DLANJAk0BQAAr//79x/yK+zr65PiP9zH21vSH8zfy+fDU77juse3M7ADsTuvG6lzqDurh6c7p0+nz6SPqYuq66hnrgOv563js+eyB7RLun+4y78nvYfD78JbxL/LF8mHz+/OV9DX11PV59ij34vei+Gj5OfoS+/b75Pza/dX+0//SANcB3ALiA+0E+AUDBxIIHwkkCiALCgzpDL4Nhw5HD/wPqBBHEdoRXBLIEh0TXxOXE8ET4BP0E/kT8hPdE7cTehMuE9ISaxL9EYQR/xByENsPOA+PDt4NJg1qDLIL/wpXCr4JMAmsCDAIuwc+B7kGLgacBQcFcATaAzcDigLXAQ0BLgA2/yn+D/3u+8X6lflj+C73+/XJ9JrzbPJA8SXwH+8u7lfto+wN7JTrO+v76svqr+qp6rjq5Oon63/r5+tb7NPsSu3F7UDuv+5C79HvZvAA8aTxQvLc8m3z+fOB9Ab1kvUl9sT2cfcq+Or4r/lz+jj7Bvzb/Lj9o/6a/5oApAGwArYDsgSkBZIGegdkCE8JPgosCxYM+QzIDYYOLw/HD1EQ1hBVEccRMhKMEtISAxMgEyQTFRMEE+oSyxKsEoESShIIErERSRHSEEkQug8lD4sO6w1JDZ4M8As+C4UKywkQCV4IuAcjB5sGFwabBRkFlwQMBHgD5AJQArkBHwGFANv/Jf9g/of9oPyu+7X6tvmz+Kv3o/ab9Y/0hfOD8obxlfC17+PuLe6R7RHtr+xj7C7sDOz+6/3rEew47HTsyOwm7ZPtBO567u3uYu/e71fw2vBm8fbxhvIZ86rzNfS99ED1wvVJ9tr2d/cj+Nr4nflp+jf7AvzP/KX9gP5p/1oAUgFPAk0DTQRBBSwGDAflB7sIjQliCjEL/QvBDHwNKA7DDk8PxQ83EKMQBBFeEasR6hEaEjwSSBJCEi4SExLxEcgRlxFfERoRyhByEAoQlQ8UD4kO9Q1aDb8MGQxwC8EKDQpWCZsI3gcbB2MGsQUJBXAE3wNTA8gCQwK4ASwBnwASAIf/+v5v/t/9SP2r/AX8U/uY+tT5DflB+HH3ovbR9QX1PPR187Dy8fE58Yrw9O9r7/ruoe5f7jHuEe4G7gXuE+417mrusu4J727v2e9K8L/wNvGv8SryrfI388fzWfTt9IL1FPaf9ij3q/cv+Lb4QPnW+XD6E/u5+2D8Bf2o/U/+9v6i/1QAEQHSAZYCXwMeBNsEjgU4Bt4GfgcdCLkIVgntCYIKEQuPC/8LYwy+DBANYQ2vDfQNNQ5wDpsOuw7MDs4Oxg62DqEOgw5lDkAOFA7jDaYNZA0WDcQMbgwTDLILTQvoCnYKAgqKCQcJegjoB1IHrgYLBmsFwwQbBHgD1AIxApMB9QBcAMv/RP/H/lP+5v2C/ST9x/xv/Bb8vvtj+wz7sfpR+vH5hvkX+aL4Kfio9yX3pvYi9qP1JfWr9Dn00PNx8xnzzfKH8lTyL/IU8g3yF/It8lLyg/K/8gXzVfOz8xb0gPTw9GH11PVE9rv2L/eg9w74fvjs+Ff5yfk0+p76Cvt2++L7TPy6/Cn9n/0Z/pf+Gv+f/ykAtgBCAc8BXwLuAn0DDgSeBCwFuQVDBsQGPAeuBx0IhAjpCEwJqAkECloKrgr1Ci8LZwuXC7sL2gv3CwYMEgwgDCEMGAwEDOkLwAuRC2ILKgvrCqkKZwoiCtgJigk4Cd4IhAgsCM8HbAcPB7EGSwboBYEFEQWbBCIEoAMWA5QCDgKIAQQBggADAID/Av+E/gn+lP0p/cf8aPwV/Mv7h/tC+wL7xPqB+kP6CfrO+ZP5XPkl+ev4rfhu+Cn44PeZ91H3CvfF9oj2TvYX9uX1ufWS9W71WPVK9UP1TPVi9X/1n/XI9ff1K/Zk9qT26/Y094L30/cj+HL4wvgQ+V35rfn/+U/6pPr7+lL7p/sA/F38t/wS/Xb93P1C/rD+Jf+b/w8AiAAAAXsB8gFrAuUCXQPZA1AEygQ8Ba0FHQaFBucGSgenB/oHVgiqCOkILQl7CasJ0wkKCjIKSQpbCnEKfAp4Cm4KaQpbCjgKHAr8CdEJmQlfCSgJ6gihCFkIDwi4B2oHDAepBk4G8AV0BRMFuwRBBM4DbAMIA4gCDgKnAUkB0ABkAPz/lP8l/8j+af4J/rj9Vf0Y/bb8Zvwt/OP7nPtq+yX74Pre+r/6Wvoz+l/6FPrN+eD55Pmz+XP5e/mL+VL56/gx+Uv5sfjH+BP5z/iP+Mr4lvh9+Nr4qviD+Ob40/i2+C356Pj9+Gb5kvmY+aL5BPpM+jL6aPr7+s36O/ug+2L7qvuF/Fr8QPzr/Pz8Rv1//cT9Mv5B/k7+9P4a/yb/rP8hAPz/cAA9Af0AYQEPAi4CiwIsA18DkwPsA3QEqATCBFsFgAUfBfIFaQbLBUoGtwaJBpwGIAfZBsYGQQcvBxwHPQfuBksHHwdCBhgHJwc5Bh8GggbWBdMFAAYrBQMFLQX7BFwEHQSJBEwEHQOEA3IDmQI/A7ACwgGZAlgCOAG9AYMBdABHAYoB1v/X/xgB3f8C/5//iv/5/oD+2P6g/lT+xP3b/fD9RP34/Fv9cf2B/GT8p/yR/Jb7DPxm/Nn7ifvV+/T7Z/vS+4r7QPs5+2f77fou+7L7u/qz+vX6ffuN+wz7efsc/Jv7JvvR/Oz77Prd/C/90vtw/A/9s/xy/ej8kP2v/W39O/3J/en91P2D/jD+0/3u/aT/VP+M/tP+8v/I/8P/Qv/8/z4AuP+r/8z/5gCs/0kAVQDBACkAkgH3AO/+SAFYArYAqf8LAigB3f88ARgCRgDD/70C0AFi/18BCgITATABeAD6/0kDnAEv/1gCYwE7/vQBygK9/csC3wGP/+IClgCa/aQENASG+ywBIQUCAJwBTwUk/v7+9QTXAzb9PgGYBtUB5/25AJEFcQL1/fj8mQe2BA78MQN4BPb7rAKEBa7+KwNXASX6kAFiDIX6PflXC+T8hffbCjAC+/R0AyMIJPgp+xUHkgBx+kz7eAGcBcYAtfrBAMcEmgKR/s0BJALj/U7/lwHh/wL3IgKMByX35PeACeH60PaBCKX+ZvmwA5T/ivcIBSv/4Pfb/VcDHwF++5b+9PxBAi0BS/y0/84EKfi7+wYLzfyB/FcDQf/uAFgGVPzg+iwJdgOI+rr96QhVB8D4yfvqCHEBgP26BgD+CfneAk0JQv0j9XEG/Qbl9CwALgcq+XEAsQUx+aT74Qlh/tL0nQG6CHX4MfbtC9H9aPILCYoJ9O4S/j4Qn/Zg83YIXAdv8zj8lwm0/Zf3lP8rAZn/XwEy/pX79P1L/jP3KQUKBGf2iQFNAWz3e/xiB/r6SviPBg4A+/FqA+kLLfTK9wEHSwam9nT94wll/QD75/9bBnL8L/mUBA8BCP7MAqYBO/o7AtwGIADA+0/7jAObBhz9i/9PCd35l/iHDUMJX/QYAJMQ5vsm97UJOws/9wT8ogwBAvz9tAS9AVwCaQbe+gsEtQ44+Hz4bg/sB+T2WQE1B+ABBwbh/xn6nAKqAZIFjgKu9xoBYAvM/TrxsAk9EMv4d/PKBKEH2voxAFoBYvp0+XcLTwhg79L6uQejAVH8uPx+/nMCi/5B+tIDEAaE+uj6j/7j9GYG9giH9Ib7bAdx/UH1zgYmAR72V/8YAk38YAK1Atn3kP3nACT+Ufep/cH9y/m6A/r7PfUgAlYA1/UB/8T/9Prj/u8EcP0d/K3/BPwqB037O/ItB9cBM/fiAKsAeAB1AK79Ivvf/WcATfx9BbQE1vowAv8E1f/5+XH9Xw+j/zX8vgkW/m78TQd3B/XzFf+9DX8F1fgv+b0CjwkSB1H3AgAzAs8ISwRP9jT/CQqGCSX3eP/FCOP/Sf2bA04BG//7A9v9lwZoAef7OwtXB5b6uPyDEMICavTbBvj9GwHnDUIBs/nF/d4KhAAs93QLmQMw9ikD1A/z/TnteAYuBiL7Fwlz/VHyuwyqDBjqx/PLFiII9uug/RANYAOS+DrxNwHcDML5D/v4ASf7f/spAqX/uPV3AwQEd/zCAH77xv1b/Zj3jAhnBr7ykfoSBf3/F/mJAGr+jADNAEH0P/wvDID/p+/C/DMEdAVQAVT6dPKM/XcL/fry+3QJI/df+BUNTv1M9UID8QNv9MMD1QfK9BH/oQcOA/T5zPe7BnQJQvVu+zsDxgQOA3v91PvN/nUGWP8mAcX8sP08DLgFqe6hAWEP8/0Y+tX88QfIBqAEvvZ/AJAL+wCeAj38yvU3BrcXrPx59mcFKQPC/egBvgcFAY/9Y/kcCoMR/vz79TwC5AYCAlEAYgDpCtUBzfetASwHcQSt/LD9u/xXCVAPk/ik7vYCmBb6ABLmi/7MEqH8M/ge/+X9y/tpCbn/lvRVBEP+xfmg9wYJcAjL/aLxYvHQFOYEROen+LIXUQIo6zgGEAju+W79e/fCAEAPCAHj6a3zIhAVB7TztfSqBcz8w/IQAKcDuPqt/Jz+lvoQBKz9LPtF/hX7L/Z1C6QJvO6J/LEGEfzO9mMMcQAX8O8KhwsY7mT4nA5T/1T2uwDBCMT/+vrI9/AE8A0O+rr77wM/BW8JEPxN9FUDOQ1i/0b1sQsADAH9PP1M/PkEcAckAdADogefBfr32/btC6oOAvV577AbgR3/6KjqqhP7DAv4N/8jARsE1QWL/4UEGQzE9bbtMQwWDYj9wAL4/yUElQRS9CwAxhKPBSbzqvmXCZkQtPmN8kIF3QnL+e/22QatAjQDwPab/48N5f2E+BL5Lv6WAkT9+fxOCjUFtvyd9M333/19/9IEmf1L/0oEDgIM+uXxJf93DeX50fpmBQz/VftM+br/Bvwl/4X+wvQB/yv+XfiMAa0DaQOW8jvxmAhtBq3v5/XDD8wHKvEj9JUIjPj786/9QwZVDAPzu/KPBoIFEuxy+bgWTQHQ7rr/SAdXBGz6nfK4DWcQy/ej/MIG5/ng+hwMhAff9W8EZw35Aer6dfNFBawN8AmlAM7/VQGv/OEIfwQh+d4G0xcG+XHpUgp9E7z8O/PpDpUR9+/q83ITqQhG610A+R1mA+Dp4//vDGH/bfx4Bz//l/vuDoUDCPKp/eQSJwkD6mb4FBXWBn7z6f8dA7P9eQn/CEP0EPNsBOkM+gYO+V/5XwcrCKP07PmUDRX/dO/4CPkVqv3e6b/yqQ1kAgz0qQIoBFL30PpFBUP8zfgE/tMAhf4m9pkCrQIb8ur9KQHw+JH8+wPF95v4qARa+PX4rABABEcASvyz8Sb4vRP3CnHtX/A1CooINPc+818HwQ9E+hf2iwTCCIUBXu+O87kPHhAT98jvLQd7Dzr7O+u1An0QqAD1/9X9Wvg0A9ANVfk899sL9Ab7+UP69AkXDt71ivf1CmULzv3z77D/3AN0B1IEbfiNAzII1wA/+uoGufgu8Q0XiBv67pvnsRGnDwP4FvVwBbcZOAWf8zIBSgaJ/Pj73w54DJr8D/iN+qANdhIr9QLm2AaiG/IF+e+s/xgOcgDW/mP+KAe3A5/xYfbFBJ0RAQJX8DL3nP8WCeEEFvfe+OD+jwe+CXD2SfIqAVUDnADQ/Hn3xwJHCPT36PEX/xsCY/qd/pT+OPxQ/uv7HPrz+0UBdf66+UgAZP5n+AL8RviL/pIBy/Y4AckEd/VI+VUCe/ur+47/V/9w/D7+fwR6+aLycgGdDCH+mfEL+Yn+7gNNBEwBFgDe+Sb7SgA+/vUAeQdc/0L3SQFoDMYEmPic/Z8GLwxvAj/1gQQkDPACfQV8BLwB1wRKA+wDWwviBt79uQrOD14GHPwf9mANlhccA8z9KgdEDC8DUv6DCdYMpP/L+bgNyw0a/xsGaQXr/S0BXQurB+oCuwLT/nwDSP8A+tMAYQmUAMX4UAKj/678bP149P33YQXD/pLxl/rhAnP3MvLB89LzsPv0+j3vrvVu+7Pz0/Gv8x36gPar77fr1PABALD9Gvb89hb4E/er+Hfz/fG0+CoCzARK/XwBXgAS+Ln0z/1hCQgEwgGTCuYGR/1nAKoFTAPI/44HdAmDC5UNkwPDBOL/nvqDFKYWyvocAzIWzg7q/OD4qwRbFlsUy/6F/0IOUAt4AZ4E9AStD/cXLQWz+yAM9hBoAWQFfgsYCK0IIwn5B5gGMf9iAiUMgP7R+ugFdwzzBxr4ifiLA+b/6PpH90j2O/7/AuT8Le0P8Yb4GPKy7xDwkPRu+HbxyuqN7HfuzO8w8R/woOsR9tT2le7P7oLslvGp9qz95frD9jD1Kv5UAr/zh/nOAHYDIgHG+4YBQAZxBFkFLgeCAdQC2QmSBXMFXAoFCEkNkg+hA9X/+RJ+ENkB0gRYCBwUARQ8BUH8GAkSEV0JowJtAewPExPXB8kFsREOEGoGgQJCAN0HhA4jDj0HnwnhFIENn/dc81EHsxJTBh8FqRAbDRb8l/WN+NX49/8pBRoMLwdU+gH00O3I7PntpPXL94bwhfLg+7Dy6uI54RfpzO2U7GrtSPKT+Brsu+Jd7CLygOzL7HjzbPdt/rj+OfPS6y/3gvxm/LgAQALsB8QI5fsZ9uwACAVoAw0GXwyKDuENDQhX/gv+iw6QFkoF1QSLFZwVNgEBAw4TYQ68BTUE+hAGGL8Ktf8PDFAUGg3HDDQL3waTDRwPVwWYC6kPxgeVBxMMMgvDCBsE1gC9Cu4NRgcHBpAImwN9/J7+TAJdBZ0DMvzx/jIBJfk99n71HfSG9Hr0MO8S79P3O/YD7ULqdO0O7wzu7ugF6ADv4u1o7Fv0Q+9H5WjpmO7v8An2s/bo8+H9VP0A9fn6ePoW80n2rgTyCIQCEgDZAjcCxQGoBF8GMgxbCjQIeA2GD5cMxQepCOwKZQ++E34MLAZ7Cm8Q/A3QBqYJ1A6xDQsPEximFlQHKANeCSwMLwk+CuAPlhOIC/AC3QjuBRz/uAX2DuIOAA1nB6D78PgP/rMAUfutALIKmgVL+0j0zvQn8ijqHexm92P3fO/h8JLxzeip5H3lEON+5xfsHPAG8Zvq4ugh6GHmPuY37MHyuvZ9+Vn3iPb98wXzqvrd/i39iwORCFD/Tv46CLkHSQUVCaYLPA8KEn0Lggb6DWITcxHIEaQRqhC5E7gPpAfQD+UYog/DDngb6RlIDw8KLAZaBxYRrRLCEFMTTBMlDtkBDPxfA8sLGQtUEKAVvgmB/En3sPnS+/T+vQRuCpEJpf4L807ppuff63/xGPem9/31k+/j5ajixePp4ajgWOgC7s3wvO3U4YnhieT440jl4euZ8MX1x/r+9AH0JvKp7pvv6/jWBMMKnQfr/7MDjQOnABsAxghLFHETrhINFJYR8gnTEPkUGw/QFnEXMQ4BDRcQghHuGoQgshWJEAcP0gshDkQOUhHzGPsXHxG8DagFFv/qB8YRxhTLFAEPEgbV/RD29/uxB9AH0gZBB8cBa/cW76bob+tv9B32UfW58U3rIeWe3hHeEOTd5YTkRefH6Grk/eG03jHbhuIH6W/okuuV8ir0nPAw7yru0u0G9+gAUAUdBUYEswTS/cX/VwZhDbkT3RaTG5EVUhCzDeQPyhNWGIcerBgoEr8Q8hDFEjEbMh+pGVEUqA4TDNcMIg4oEeIWEBemEb8JtP5q/E8G6g0lEqsU8QtM/Zb3kPns+w4BCQZJCHICk/j78gTuHury7W348ffo8mTwO+hL4R3jGeiC6DvncuVA5DjmwekN5ZffnuYh7EfpN+kz7tfvNfPM94r07fLJ9gH7zP7gAVoDYgR7BWoDFwV1CmcNARAYE18ShBBhE+YP2g4ZFYQaRBn6EGwT5xeHFJ0T8RooFlIKYBCjE3YOnxC3FHsR/g/tDQIFrwAaCT4RZhA+DykJqwJa/df6eAG3BmUFrAP4Ajb7M/Te8mruIPBi9w34lfXY7afmdedi6m7ojeY16V7n4Oa75kjn3OcH47XgfOW37HXr7epQ8Rz0k/IR9LP0M/OW9lD9xQJ0A0wDEALBBKwI7wioDQoO6QxxEw8VuROAFvMVHhG/DhIU4BIpEXUbhyCvILwYWwtGArQEshKFF68c/B2bE3wIbv0Z+7399QkBF9kYxxCXA8b4dexX8qD/iAeUCisFQf8K8xrqL+Vx7TP4JPU09tr1aOy74XbjH+ZU5D3oxOsv60vpzusq6szlfOQ54z/pzfEU9lz10/V+96Dy//Ic9YD4tgI7CgEL3waHBFYAlwM3ClMLThSGGgcWWRMDFF8P4xC7Ey4Q0hm+HtcXGBzDG1oR8QzlCnkKCRQEHfEXoRVmEXMGTwDH/oQIjA9GEIQPKg1YBMPzrPLj+LP7LAVBDVwEM/Xv7ozq0uj16lDuOfYV/A7yJ+Vu4irfkN525FzsgO/87RXqOOSo4rvgROOf60fxJvaB+Tr0/uz98LL1CfnC/a8DyQahAxYGoAf0AoAD5guZD+sR2hU0FeAS4REvFTYVtBXIEXAQiRlcHUggJhtsEhILbAkzERESVBggHesVCg5OB88CMf/LBZYQcRWsEngH4/x89G/1bv1FBXUGyQHL+4rv4u6K8STuGfJM9NPx9OxW6wzoKOOT5zboY+YT5VTiRean6kDtTuyF54DjcuX76d/r9fVW/ZL5Ifcl+B/yA/FH/2UGCQpMC70IaQfzApQBeAeAE44TIxY1HUIQhAwaFrAVaxGaFF4VTBekIHUZYRA6D/4Idg+8GvsWTRIlExUQAAq9BRoGtQhFC1oPKhIVCyD+dvpn+4v9BQRaBqMA7fg59c70rvLA723xOfXq9gnweOby433jC+dM7DztU+h95SznhOQr5tTqEulS56jqdu55753vWPGM9bb35Pix9y32dvwvAqYFYAkOBUoB9gV/CSkLxA3IEpkVABRrEREQcxHDDpcRPxcqHEEgihb4DmcLNg0ZE/cVWxmSE0AQORBWDCQG4QXKDMkMrw+IDwAIWQGJ/O78Cv5VAWwFPwPj/Cf6ZvQl7ybw3O7g85n4KvKw6a3nYugt6B7qP+qz6PjnTOqY6+Po7ub95V7lPuy+807vC/Mc+MfyHfU7+cv4f/g4+2ABmgf0BY4DEwfPBvoG1QtsDhYNsxSSGF4SExJZEZcRHA4fERwaKxm+G/UXQg6lCZkJ2Q7GFDkX5RMlEr8MhQSnAF0Degz1EJ4Q3QxlA7n3XPhL/4MBzwUtBsz/ePZ48gLxM/DF8Tz1u/z59tPqfuXR40PmfOt78h7wquie5vflFOcA6enqze+48V3vfu6A7tnwefNV+BT9mvvD+e/3iPyPAy8E2wflB1IEMAc7CfILHRDqEP0RaBOmE+YOogxKEc8UcBrbGlUXChBiCN4OSQ/lERAbWRXnEEwPUghmAqADxQwrEkgRgw6jBR/8sPgV/XkGowc7BsUCc/nu81zvW/Hz9yL5TfgI9I/wNOrD41Xp9+x87brvz+0t6YTli+YE6fXrtO0O7aXtIu/o7czu3vN69mv68fkH9hP3cvlR/w0FlAe6CMsENADCAvIJyA+tEqAUPBGIDRYM3AvPETAQUxNlG3sYUBUmDAMIcAtcDgQVwBdJF88PvAjKBQoDcgjsCz8QNxWZC8UCvv+v+pH+ZgQ6B+AIwQHe+oT3Hvea9Nrz7PgB+C352fTO7MPqu+ik7ALxwfH57XvqPOtB6l7pEuyB7mHsq+6J8gfyXfOG9Dn1z/X89UX32PgN/Yb/OgAZAjEAXwGXBZwGuAj9CgoL7QqxDFEQ8g39CucPnA40C1AQvhdwFH0LTA21CvAIHhBDDoYQEhVECyQIPwiPAgEFbQr4DzkO7AesA9n+Iv6r/VEEcgruBXgCSftD9kD5ZvZW+AT/Wftc9uLxx+/Z8EfwjvKZ9OTzHfH37kzuYuxU7RHw2/QA9gvwbfDc8Zjxs/a3+dP4tvmt+Tv30vjS/MMA4wKEBK8FlAKcAP8C6wgrC9kLBA76DOMLywYeCFwMsAd+ENsWUxG3D4QHFwQWBk8KdhBYEVgTkAsFBdwFJgIeBvQKOA1UEFAKDgM8/s38cQG6BbMHvQYIBFP9nPnq+aP4xPmG/J79k/k89jTw2u3R8yXzf/OZ9L/wn++W7Sft5fDR8GXzePLi8NLyp+9r9ID3iPjH+Q74UflV9yv7//zP/EQCsgJUA5wDFQKmBJsFegbwCqcKpQtHDVAJHAnOCKsFlwiJEVwTcxD4D1IFkf52BR4LvxDEExwPuAY1Ad0ApARPCV4NlQ9+C3MGWQH3/Fr/nwSfB04JtAcJAoj7KfkB+6j7MQCvAIv8uPl887/wIvCD9OX4wPZk9eLwpu0m777ucu/U8tPzn/LF8qby9/Dl8c70pvdM+WP5N/jv97D5JPvd/Rr/zf4N/xsC+QOhA/IE8QczCB8D9gkfC/kGWAw8Cs4JYwXpB94Qiw7CD2AKbwaGB/8FTA2fDOIM2Q/CB60H5wQkBAMJlgqbEf8MWQa0Amn9qQOICCgJCAnTBsYCLPzA/Ar+LvxC/7gB7f8r96nwOPHz8G/25fqA+F71Fu/061vtb+4Y8cfzJfVo8+Hw1+7i7j3zfvb6+Aj5wvYI9hP3R/kg/JT9ZP7ZAI3/GP4QAAEDTwX0B0EJYgV5AyAF+QhsC50LJguiBW8DqwUFCqcSNQ6LB3UIRAK4A6gJzg03DkkKrgv7Aw8AywSLBbMLbA6JDrkJsf5yAV8BEgRIDeEIMQnUA3P96/3k/A8CeP+OAQAEpfpO9r/0jPRz9t35WPuf9oLzcfLA757wvfEl8nX0DPbU9djyvvC+8LzzS/jT+a74nfYF+KH62Ps+/nD8DPxy/4H+9QCjA94D+QRUA9wGBAdbAnkGkgYlCLIL+AhICWYCQgALBFoITRBrDDAM/QQC/Q0FiwPFCaIP5QqeCeIBkQE4AS4CjAs1DH0OHApVAXT+U/6RBbQHrwlYC88DagDa/cv7ef93/7ICPANe/Df4M/M79cr3Gfk0/CH4ZPWm8z3xbvHT8oj0+/RD9NjzVvM580/1y/cm9/H2p/cu9hv6s/wt/R3/kP1D/eH7HP4MAkoCTgVbBm0D/wEsAtcE5AY7BvIINAlaBsIEigK6BIMEmAOzDaIO6wYhBeb+RADTBPwHaw8uCtMGVwOx/U8E3QPIBqgOpg1tC54DAP/F/noCSApRDK8MIQe2AOb9e/1eASID0wV0BeMA1vsg9Jr0UflK+1D/aPzd9lPy+O2/8ab1r/ZX9uv0gPOY8IfwmPHH9Nf5//lF+GH1AvTO9D33jv5AADH+IP2x+0H8AP5qAQYDswUBB3ACmP9XAvICDAWYCdAI2wgcAioCLQiTAsgFwQbJBHMLjQqrBsgBtP/BA4gEWQo9DbQHdQQ5AkoEcgJcAw4LTAssDT0KHQP4AcsApwXXChINNQtnBP4CQQDFAGgCxgIKBrQADwCp/2j4Qfhe+H756/tU+lj47PRk8bHxS/Nb9Pb0wfQO89fxfvLY8ZfyM/V19873w/Wx9kv20vbZ+7f8Uv2//L367Pyc/oQALQRQBAwBTwEnAX0AtQS4B2QGawZyBiICPAQ/BIYEngn/AkAF6QY1Ao8JUwg2BwUFA/9YBIcD9geEDWwH8AbUA/ICJgTIBYILBAnTC0INygVpBbUDaATRCXcLdw3RCJQDdgOuAXcDbwQeBFEFVwOi/gv6F/i9+Ib7l/2n/JP5QvUm8X7ykfN68vv1u/RN9DfzmO5D8UTwsvKO9sD0efaa81X01/WC9h77C/kx+3D81fv5/jv81PxXAOEBegP3AuwAiAAZA7QEeAfMCNcE9gMYBEsEOAgiB8MGRAiiATMCOAnyB6YJaQtYAwMAIASdBpoIVAtJCqgDhwRgB7kCoAahCkYLMQ3bCCoG0QFRA28KBwqVC5II6wLGAkAD7ANIAqsDvwQgAPf+KfwJ98H68vzN+8T7rPb18wHyBfMX9wX0N/Sk85Xwr/Li8ZbwNvIR9fj1LfWh9STzHPPo9x/5fPkh+3D6BPtt/ET9V/6u/uMAhwFnAScD3wH3AZUFJQYIBToFfAWtBhwGrAWVBpIFwAbyBpoGmwapAo0A1gXaDLUJsweqBfL9CwLfBKcH9wt1BgYGbAOkATMEfQPyCU4MBQqECFwCPwKmAyMGjgyCCcoGMwbzAa8CzQLZAu0DGQTJAtf+s/0j+pP5K/wk+z387/kA+Cr3I/RT9JTzJvRs9bb0TPUX8ybxoPIf8lf0nff69PL0xfRh8w/5JfoD+Rr8iPmY+r793Pv2/Uz/HgGIAkwB3AIAAQUCqgRSBAgHyQUkBSAGLgWXBosGEQcTB0UFlQW6BvQDBQOQBrIEWQoxDMQDoQTy/koA/wiHB4gLiQn6Ai0CLQHiAkEF6Ak7DVoKLAeOAmQAOgNXBuIKEgvYB6sFbwJAATsAlAATA7UDpwSqAVn7qvgr9+H5Sv30+2D6xvYh9GXym/Ig9aPziPRN9ArxLPKl8GbwSfRp9BX1Z/Sm8wX0mPOp9k74Nfor+lz6qvsD+sj8Rv3h/jwCngHsAWgCpgIoAp4E7wXNBbYHOAfXBbkG/gcwB/4IEAp1CaEHtQbbCpcGlwXCCb8DFAPFA6wI9Q/ACGAHfgJp+3YD4QWqCzoOrgUDBAgAHgD9AVcDxwsqCxEKcgay/2sBCgDOBbcKHwk+Cf0BsgBEAMT9GwKdAscCcwJX/jL73/dU9lv6E/4Z/IH5ffaq8WHxxPP286X1EvbC8xnzxPCI71nxt/Mm97D2fPSX8pXyGfXE9nP63fl1+Dj6VvlP+738vPxX/0cA8gAVAuYBBgLmAtgEkgVRBn0H8gVXBhUG4QaICTMJcwo1CS0InQjjBbMIgApQBtYIWgj/AZ8DEgcwCqYLqwgjBPX+IwA1BAMHpwsQCAEC2wKg/3IAWAQVBUwImAeRBtgDy/9mAEECGQXcB7MH0QQbAkT/2/3R/qoA/gCQAkoChPyd+Pj1m/eY+rv8RPwx+Az2tfFi8cXzdPVw9rj1Dvaf8lLwFfF08uL0X/cw+P71BvUi9Ez0JPhm+mH8svzw+Sv7Gvu0+wsANQHfAkcDHgHGADcCHAQpB+gIZgcAB00FaASbB10JSgrVCY0IHAlcB+8G+QcGCHwIlAfKB6oFXQMOAvQECAu7CGAHYgNH/u8AxAPOB74I8wUuAoT/qgFhA7QCcgWBB80FxwXUAskADwF7AmcGQgdUBtMBVQBcANX+8QAOAOsA2wAb/vX82Ph29034Afny+qP6LvhI9YrzFPKp8S71G/cM9mH11vIo8ZfxqPO49vv32Pdn9s31Rva79635efsA/Rz8bvwH/ZP8Pv9CARUCwgSzA2wBGwMqBJsFrgdECAQJswdMBjoHXwf4CAkK5gmlCYoHUAe1BlIIHQmJBp8GHAWbBbYEgwMaBVwA8v8MA3QDAwdGBDr/BP/Z/Af/7gPHBEADVwBu/nP+VwDWAVkD9gNqA7kCiQE3AmUCTgKVBIgFOANnAmIBBwF6ApsALQA1AGP+ov42/9D8YPrp+Qb6g/oX+k35QfcC91j24/Qm9jL1b/WU9gv2CPaB9E3zbfVP93X4Mvlo+P33vfd5+fv6mPtq/LP9WP89/5f/rP4Y/ywCpQP6BFoGEwRpA1YFmQSuBjEIZQibCOwHEgjmBrsHUQiYCLcJYgjVB6oHvQb6B/YGBwbLBigFpQU2Bb0E+QMVApQDhQOiAYsBSAHP/4r/Yv8W/zf+rf+K/k78v/6R+0b92gDJ/6H/Rv1//FT7Yf0aAOEAVgFYAOr+2v1W/4b/8gBLAz8ECwKDALkA2P7UABYDJQNFAu8Akv/x/i7+A/4o/+b9H/7h/Jf6b/qk+aD5uPkb+T/4w/dB9/z2R/eQ9ur14vaN9qf2pPcK98n30vhs+Rz6mfoK+6v7WvzQ/eP+j/4lAPMAsgGtAtsCGQR9BDUFKQbqBtoGuQYRB40HUQjbCDgJVgjJB58HRQgQCTEJWghNBzAHcga+BjAHEAe9BhAGEQW2BCYERwNBBCUEkwNtAooB/AFTAAEADQH6/4f/ef8C/in9hvxv/Or8tfxp/Rv7r/pn/tv95v1G/Zr7rPrY+sL+dv9A/6j+N/1T/X/96P5X/x8B3gFQAOYAtP83/uX/1gC1AJsBJgHb/9b+8P18/Zb8g/2w/pn9bPzG+oD4kvjr+Tz6i/ki+SX4vvbt9+L3KfhI+KD3C/lu+BT5Vfo8+rv7N/xA/Db9CP1M/u//qwAsApICAwPVAmYDeQRgBb8GLQf1B6wHaQd+B7oHuAjtCHwJMwrjCUwJFgl4CMYIMgmzCBEJoAiiB5cGgAaVBpwFwwUZBWUE3ANBA2oDJALgAPL/PP8LAMz/pP6a/e37U/s//Zr/R/4b/Sj7m/gA++38+v0E/l/8GfsT+sH7kP0c/cL9Dv8m/jr9of0w/er8jP4N/yH/LwAB/iX9Mv5h/Jn8kf3K/UH+O/38+8b6cPmt+ff6GvvM++v6g/mR+S34N/f1+Ar6svm6+6r6pfgn+W/5U/u+/KP97v05/SP9Ef6X/igAzwHYAfQC2gIBA08DHATkBToGhwcYByYHewf3BhoIEwjKCAwJLQlcCTQIDQgWCNkHZQivCCgIrAfSBs4G8AVQBdoFIgXBBK8EBQSmAvwBCQJqARkBWQGDAJ7/5P61/jP/E/6x/Z798/zp/D38RfxI/Fr7B/ux+1779vkK+zz7i/sc/Tn8jPsT+9b6jfs//SD+xP08/a383vz2/OP97v7e/n7/MwBx/hv+wP4D/n7/OACJ/53/cv7o/XX+NP6b/mf+4/0f/rb9+vyO/Nj8S/x3/I/92fzf/Lv8OPyp/Lr8aP2R/bH9P/4U/u79s/42/5z/rwCuAMMACAF0AbcBTgKrA3EDfwM7BBkEcQRoBLQEeQUeBcIFGAagBZAFkAV6BbUF2AVvBYYFpwVXBcME4QR8BD0EUARxBKIEZgMqA1cDtwI+Am4ChwLsAVkBfwFMAQsALwBlANH/pf+v/+/+l/0x/vX97vyG/d79w/zB+yb9av0v/Un9A/1R/Cz7g/wO/YH9sf2E/GP8bfza/O78oP1e/tH9Mf7c/RD9Yv30/NT9wv5P/gL+Kv3U/Mr8qfz+/Or83vzk/D786vtk+9T6CfvV+xX81/vI+1T70/pJ+/375vsV/Tn9+fzY/bX9sP0e/rz/+f/d/5IBMgHNAAkCkAJ7AwMEcAT/BO4E2wW/BfgFkQf0BrgGIwgbCFoHlwd9CCMI0AdlCCYIAwhiBy8HywexBmwGjgbLBbQFTAQZBBgEzAK0AkACpQG9AOr/pP9W/0z+mf2T/Qv9T/zq+5P77Pr7+p36hPrQ+tj5c/n9+SX6I/pE+sf6cfpw+mr7R/vv+8v8s/w2/ff9Iv5H/jX//f+q/58AdQHOAIIBUQLyAe8B9gLJAqgCQAPrAnECnwKGAgcCdQJIAoIBBQEaAWYAl//d/0H/m/6X/iv+gP09/cH8GPzs+wX8v/tB+077I/u8+qP6oPoK+y777fpH+yD8vvud++H88PzP/JT9b/7B/iP/p//x/2MAKgF1Af0BYgPgAqUCJARMBJsDxwSKBSoFOAV4Bd4FQAV1BfQF8QVzBT4FXwW9BPcEpAShBFwEtQPJA/wC4wL7AloCAgLwAUUBcAB/AIIADwCH/5v/aP9A/lP+l/4a/vT9Uv5k/mX9if14/Tf9+v3L/ez9+/3T/Xr9ef19/i/+Tf4o///+o/6p/hr/bv+f/+T/PAD6/w4AJQAmAMkAcwB3APUAvwCWAFgAfgCwADUAjwCTAAcAzP/C/7H/GP9Y/y//uP66/oj+Hf7L/RT+AP5t/bb9mf0Q/a39vf2A/Ub9rv2H/Xz9lP5i/mT+n/7R/tz+Jf8EACIAagDdAJIAsgAtAVYB3gFAAicCFQLpAeIB/AEmAnkCZgILAsEBhgH1APUAOwESAZkASADv/y3/Af/F/s/+mP4U/uL9jP0Z/ej8Ev0Z/RP9Df3R/MP8+fzw/IP9Fv54/mH+o/4U/wX/4v+lAD8BmAHJAeMBYgIDA0kDIwS2BK4E0ARPBU0FSwW0Bb8F8gXwBZ4FtAVkBeAEzwS7BHcEWQQUBJgD9gKLAiYC2gHZAUoB8gCGAB0A1P+a/0v/9P4G/3P+Xv6h/uX9rf0U/qb9Z/3o/cj9Qv1m/Xz9P/07/Wr9R/0Y/Ub97fzS/D/9/vyS/A/9Cv1A/Ff8uPxz/Cf8SPw9/PP7sPvW+wT80vvV+6v71PsY/IT74Ptv/CT8V/zZ/Bf90/wY/d394v1F/sD+1/44/4T/4/9HALYA5wAyAc8B/gEZAnIC7AIeAz8DqgOxA5UD8wMBBFMEcgQpBHcEWAQoBEIEVgR7BDAEQgRMBLYDpwPAA70DigOAA10D6wLFAqYCmAKUAkECDgIAAoIBhQFCAQoBMwGBAGcApgAfAOT/EgDE/33/tv8QAFEA1/+y/9X/Mv/B/24AmgCYABUANAAYAAQAmgD8AAYB7wDgANIAdQB/AHgAtgD2ADsAHQD1/yb/1v7s/rr+D/6f/YX94/wn/Lj7c/sM+6r6lPp1+uL5Rfkx+Qv5Hvn++CP5e/kx+Sb5WPmp+c75NvoX+3j7tfvz+238+vxp/VX+/P6s//P/RwD+AFIB4QGIAjUDsQPsAxwEbgScBNMETQXHBfIFxQXQBdMFpAWzBfAFFQbsBbIFfgUcBdEEpgS0BIoESQTlA1sD/wKPAj0CMQL2AXQBGwGZABcAtv+M/0f///67/j/+6P2v/WT9JP0w/d38ofyy/F/8L/xO/CP8FPxV/GT8OPxW/I38h/y9/Br9XP2B/bH9Kv50/p/+M/9q/9P/RACPABcBcQHFAd4BTALKAv0CWgPpA9EDqQMFBCQENQRXBHMERAQYBPsDzwOvA1UDHAPaAnYCKwKnAUsB1wBqAO3/jv9D/7r+bP4H/rb9Df3S/Nf8cPx0/Gr8BPzM+9n7xvvl+1z8W/xw/LX8i/za/Bj9lv02/jb+nf7c/tr+Zv/p/ygAewDUAPsAQwGgAaYB3wEVAjkCYAKYApsCdwKJAoQCcgJNAnoCUAITAh0CwAFxAUwBIgEVAdcAlwBRAPP/tf+Q/2v/PP8W/9H+xf52/jz+N/4c/jD+BP4Z/hX+x/3i/Qj+CP4b/lL+cP6K/qX+j/7o/gT/Df94/7b/o/+3/xIAAgAtAF4AkACvAJ0AwAC9ALkA2gDyAPcA6QDPAMgAyQDHALgAmwCJAHkAVgBjAFgAMgAQAA8AAQDW//X/3v/N/97/tv+w/7H/pP/G/8H/0v++/8D/zv/N/woA9v8JABEAGAARABsATgBCAF8AZABVAFUAUQBqAIcAjABkAHUAXAA4AGsAUwBRAEcALwALAAAA9v/a//X/3v/G/6X/of+J/3r/of+I/3b/gv9e/1v/hP96/4D/q/+q/5z/wf/a//D/DwA4AFIAWQB1AKAAuwDkAAUBEwE1AU4BXgF+AZEBjQGqAacBuwG3AZ4BtAGbAYMBhwFwAUsBNQETAQIB2gCpAJAAcAA0AA4AFQDN/47/lP9Y/yf/Jf8A/9j+vP6v/pD+ef51/mX+UP5p/l/+SP5o/l3+Y/5y/o3+nv6e/sf+3P7s/v/+Hv9L/1H/fP+i/6j/u//c/wIABwAxAD8AQgBSAHIAeQBrAJoAhQCAAKUAlgCVAIgAfgB/AGkAcgBxAE4AVwA/ABMAKAAOAPb/CQD+/9j/z//W/6T/sf+3/6L/p/+b/5H/gv+O/4j/i/+W/4//d/9+/5L/d/+b/6X/iP+e/5b/mv+h/7H/wf+z/9n/1v/S/+j/7P8DAAMAJQA0ACIATgBNAGAAiACSAKoAqwC+ALkA2AD2AAMBIAEcASUBIAEyATgBSQFPATgBTwE+ATMBMgEtASgBCAEUAf0A2wDWAMgAtQCjAJIAawBhAEcAOwA0AB0ABwDj/9n/xv+8/7z/tf+p/4z/g/9y/2L/dv90/3D/av9W/0H/Ov89/zn/Rf9D/y//Iv8R//z++f7//gL/+P7t/tn+vv64/rX+sf62/rP+of6a/o/+gv6B/of+kf6P/ov+lv6L/oD+l/6i/pn+tf7Z/sX+5P76/t/+EP8h/zn/b/97/5r/n//D/9v/+P89AEUAhACWAKYA3ADeAB0BRgFqAY4BqAHMAckBAQIdAiMCXAJpAnACkgKSAowCrAKhAqUCvAKjAp4ClgKCAmwCYQJIAioCIALvAdQBuwGGAW8BTgEnAf8A1QC3AI0AZwBNACcAAADk/8n/qf+K/3X/Wf8//y3/E/8C/+7+3f7R/sH+s/6c/pf+j/51/nz+c/5e/l7+V/5Q/kP+Q/5C/jf+O/4y/jT+M/4r/jP+L/4v/jD+M/5A/j3+Rf5R/k3+WP5f/mr+fP6I/pv+o/62/sP+zv7w/gP/GP8t/0j/Xf9v/5f/rv/K/+j/BAAeADgAWQBtAJgAswDIAOwA/gAUATEBSwFcAXgBhQGVAa0BsgHDAc4B0wHbAeMB4AHeAeUB2AHcAdkBxwHCAbMBogGWAYoBdwFjAVMBPQEjARYBBQHjANcAwQCiAJQAfgBrAFkASwAyABsAGQD7/+7/8P/Z/83/wf+8/6f/nv+k/5T/lP+G/4D/ff9s/27/bv9n/17/Xf9Z/0z/S/9G/0j/Pf85/zv/Lv8u/yv/L/8k/yL/Iv8X/yT/Hv8e/yT/G/8c/yD/Kf8r/y7/O/85/zn/RP9O/1L/Yv9v/3L/e/+H/4n/nP+s/7D/xP/H/9P/3v/p//n/AQALABQAHwAkAC4APAA/AEEATwBSAFcAYABjAGgAbABwAG4AcgB5AHMAegB+AH0AfwB5AIIAfgB7AH4AfgB9AHkAfQB8AHgAcQB1AHUAbQBvAHEAaABoAGIAYgBkAFoAWgBaAFEASgBKAEUAQgA8ADoAOAAtACcAJAAbABkAEQAOAAgA/v/8//X/8//s/+r/4P/f/97/0v/U/9H/yf/F/8n/xf+9/8D/wP+1/7j/t/+3/7n/tP+y/7T/r/+y/7f/tP+5/7j/tv+4/73/u//E/8v/yv/M/9H/0//T/9//4//o/+j/8f/2//T/AwAEAAUACwAMABMAFwAcAB4AIQAgACAAJgAmACoAJwAoACoAJgAlACgAKAAlACcAJAAiABsAGwAaABwAGgAWABYADgAKAA4ACwAGAAgAAQAAAP///f/7//j/+v/1//P/9f/x//L/8//x//D/7v/w/+3/8P/x//L/9f/x/+//8v/y//P/9P/1//X/8//1//T/9f/1//T/9v/2//T/9P/y//P/8v/y//D/7P/t/+r/6//q/+n/6v/p/+b/6P/n/+P/6f/l/+b/5//p/+j/5//u/+v/7v/w//L/9P/0//f/+f/8//7/AQABAAMABgAIAAkADgAQAA8AFgAXABcAFwAZAB0AHQAhACEAIQAhACEAIQAiACUAJQAmACQAJAAmACQAJQAkACUAIwAiACYAIgAiACIAHwAhAB8AHgAeABsAGwAaABkAFwAXABUAEgATABEADwAOAAsACwALAAkABwAFAAIAAQABAP3////8//j/+v/2//L/8//y/+//7//s/+n/6f/o/+f/5//l/+P/4v/i/+H/4P/g/97/3v/c/97/3P/b/93/3f/d/9z/2//a/9v/2//e/93/3f/f/97/3//g/+D/4v/k/+T/5v/m/+j/6v/r/+z/7//v//H/9f/2//b/+v/6//z//v///wAAAAADAAQABgAHAAoACwALAAwADQAOAA8AEAARABMAFAAVABQAFQAVABYAFwAWABkAGAAXABcAFgAVABYAFgAUABQAEwAUABIAEgASAA8AEAAPAA0ADAAMAAwADAALAAoACAAIAAYABgAGAAQABAABAAIAAwABAAAAAQAAAAEAAAD+/wAA/f/+//7/+//8//r/+//7//r/+v/6//n/+P/5//j/9v/3//j/9v/4//b/9//5//f/+P/4//f/+f/6//r/+v/6//r/+P/6//v/+f/7//v/+//8//3//P/8//z//P/+//3////+//7//v////////////////////7/AAAAAAAAAQAAAAAA//////////8AAP//AAAAAP//AAD/////AAACAAEAAAAAAAAAAQAAAP//////////AAABAAAA//8AAAEA//8AAP////8AAP//AAAAAAEAAgABAAIAAQABAAIAAgACAAEAAgACAAMAAQABAAIAAgABAAAAAAAAAAEAAAABAAEAAAAAAAAAAAAAAAEAAQABAAEAAQAAAP//AQABAAAAAQAAAAAAAgABAAEAAgABAAEAAQACAAEAAAABAAAAAQAAAAIAAQABAAEAAQACAAEAAgAAAAEAAQAAAAAAAAABAAAAAAABAAEAAQAAAAAAAQABAAAA//8AAAAAAAACAAAAAQACAAAAAAABAAIAAQACAAEAAAAAAAIAAgABAAIAAQABAAIAAQACAAIAAAABAAIAAQABAAEAAAAAAAAA//8BAAEAAAAAAAEAAgABAP//AQAAAP//AAAAAAAAAAAAAAAAAgABAP//AAAAAAAAAAAAAAAA//8AAAEAAAAAAAEAAQACAAAA//8AAAAAAAAAAAAA/////wAAAQD//wAAAAAAAAEAAAAAAP//AAAAAAAA/////wAA//8BAAEAAAD//wEAAQABAAMAAQAAAAEAAQABAAIAAgACAAEAAgABAP//AQABAAAAAQACAAEAAAAAAAEAAgABAAIAAwACAAIAAAACAAEAAAABAAIAAQABAAEAAgABAAAAAgABAAAAAQAAAAEAAQAAAAEAAQABAAEAAAABAAIAAQAAAAEAAQAAAAEAAQABAAAAAAAAAAAAAAAAAAMAAQD/////AgADAAAAAQAAAAAAAgD//wAAAAAAAAEAAAABAAEAAAAAAAAAAgAAAAAAAAAAAAEAAQAAAAAAAAD//wEAAQABAP//AAABAAEAAAAAAAEAAAABAP//AAAAAAAAAgD//wEAAQD//wAAAAACAAIAAAD//wIAAgAAAAAA//8BAAAAAAACAAEAAQAAAAAAAQAAAAIAAAABAAIA//8AAAAAAAD//wAAAAAAAAEAAgABAAAAAQAAAAAAAQABAAAAAAD//wEAAwABAAIAAQABAAAAAgABAAAAAQAAAAAAAAACAAEAAAAAAAAAAQAAAAEAAAABAAIAAgABAAEAAAAAAAEAAAADAAEAAAABAP//AAAAAAEAAAADAAEA//8AAAAAAQAAAAAAAAACAAEAAAD//wEAAQAAAAAA//8BAAEAAgAAAAEAAgABAAEAAAAAAAAAAgABAAAAAAAAAAEAAQAAAAAAAAAAAAAAAAABAAEAAgABAAEAAQAAAAAAAgADAAAAAQACAP//AAAAAP//AgACAAEAAAAAAAIAAQABAAEAAAAAAAIAAAAAAAEAAAACAAEAAAABAAEAAAAAAAAAAAABAAAAAQABAAIAAgAAAAIAAQAAAAIAAQABAAEAAQAAAAEABAABAP7/AAABAAIAAAABAAIAAQAAAAEAAgABAAEAAgABAAAAAAAAAAEAAAAAAAEAAQAAAAAAAgABAAAAAgABAAAAAgAAAAAAAgAAAAAAAQABAAEAAQAAAAIAAAAAAAEAAQABAP//AQABAAAAAAAAAAEAAAD//wIAAAAAAAEAAQABAAAAAQAAAAEAAQAAAAIAAAAAAAAAAAABAAAAAQAAAAAAAwAAAAAAAAAAAAMAAQAAAAEAAAAAAAEAAQACAAAAAQABAP//AgAAAAAAAAAAAAEAAAABAAEAAgAAAAAAAQAAAAAAAAABAAIAAAAAAAIAAwABAAAAAAABAAEAAQADAAIAAQAAAAIAAQAAAAMAAQADAAEAAAAAAAEAAgABAP//AAAAAP//AgABAAAAAgAAAAEAAgAAAAAAAAAAAAEAAwABAAAAAgABAAEAAgABAAAAAQABAAAAAQABAAEAAAAAAAAAAAD//wEAAAAAAAIAAQACAAEAAAAAAAIAAQACAAAAAAABAAAAAAAAAAEAAAADAAEAAAAAAAEAAQABAAAAAAACAAEAAgAAAAEAAAAAAAAA//8AAAEAAQAAAAEAAAABAP//AAABAAAAAwAAAAEAAQACAAEAAQAAAAAAAAAAAAIA//8BAAEAAAAAAAEAAAD/////AQABAP////8BAAAAAAAAAAEAAQACAAEAAAABAAEAAQABAAAAAAABAAEAAQABAAEA//8BAAEAAAABAAAAAAABAAEAAQACAAAAAAACAAIAAQAAAAEAAAABAAEAAQAAAAEAAAABAAEAAQACAAEAAQD+/wAAAAABAAEAAAABAAEAAAABAAAAAQAAAAEAAAAAAAIAAAACAAEAAgABAAEAAAD//wEAAQACAAEAAQABAAEAAQAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAgACAAEAAQABAAAA//8AAAAAAgABAAAA//8AAAEAAQAAAAEAAQAAAAAAAQACAAAAAAABAAAAAQAAAAEAAwABAAIAAAAAAAIAAAABAAEAAAAAAAAAAQAAAAEAAAAAAAMAAAACAAEAAAAAAAAAAAABAAEAAAABAAEAAAAAAAIAAAABAAAAAAACAAIAAAABAAEAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQABAAEAAQABAAAAAAAAAP//AgAAAAAAAQD//wEAAAD/////AAAAAAAAAQAAAAAAAQAAAP//AAAAAAEAAQAAAAAA//8BAAEAAAABAAIAAAAAAAAAAAAAAAIAAQACAAEAAQAAAAAAAAABAAEAAQACAP//AQAAAAAAAQAAAAIAAQABAAEAAAAAAAAAAQAAAAAAAAAAAAAAAgAAAAAAAgAAAAAAAgABAAAAAAAAAAAAAQABAAEAAAAAAAEAAQABAAAAAgABAAEAAAAAAAAAAAABAAEAAAAAAAEAAQAAAAEAAAADAAAAAAAAAAAAAgAAAP//AQAAAAEAAQAAAAMAAAAAAAAAAAAAAAAAAAAAAAEAAQACAAAAAQAAAAAAAQAAAAAA//8AAAEAAQABAAIAAQABAAAAAAABAP//AQABAAEAAQABAAIAAAABAAEAAAAAAAIAAAABAAEAAAABAAAAAAAAAAAAAQACAAAA//8BAAAAAQAAAAIAAQABAAAAAAABAAAAAAAAAAAAAAABAAAAAgAAAAIAAAAAAAEA//8CAAEAAQAAAAEAAQACAAAAAAABAAAAAQABAAEAAAABAAEAAAAAAAAAAAABAAAAAAABAAAAAgAAAAEAAAAAAAAAAAACAAAAAAABAAAAAAABAAAAAQAAAAEAAAAAAAEAAQABAAAAAAAAAAAAAAACAAEAAAD//wEAAQABAAAA//8AAAAAAQAAAAEAAAAAAAEAAAABAAEAAQD//wAAAQABAAEAAAAAAAIAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAABAAEAAAAAAAAAAQAAAAAAAAAAAAEAAQAAAAEAAgAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAEAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAQAAAAAAAAAAAAAAAQAAAAAAAQAAAAAAAAD//wAAAAAAAAAAAAAAAAAAAQAAAAEAAAAAAAAAAAAAAAEAAgACAAEAAQAAAP//AQABAAAAAAACAAAAAAAAAAEAAgAAAAIAAQABAAEAAAAAAAAAAAAAAAEAAAAAAAEAAgAAAAAAAQAAAAAAAQABAAAAAQAAAAAAAAABAAEAAAAAAAEAAQABAAAAAAAAAP//AAAAAAAAAAABAAIAAAAAAAIAAQAAAAEAAAACAAEAAQABAP//AgAAAAAAAgAAAAAAAAABAAEAAAAAAAAAAQABAAAA//8AAAEAAQABAAAAAAAAAAAAAgABAAEA/////wEAAQABAAEAAQABAAAAAQABAAAAAgAAAAAAAQAAAAEAAAABAAAA//8AAAEAAAAAAAEAAAACAAAAAQABAAEAAgABAAAAAAAAAAEAAAAAAAEA//8BAAAAAAAAAAAAAQAAAAAAAAACAAEAAQAAAAIAAAAAAAAA//8AAAEAAgAAAAIAAAACAAAAAQAAAAAAAgAAAAAAAAACAAEAAQAAAAAAAAAAAAAA//8CAAIAAwAAAAAAAAAAAAAAAQADAAEAAAABAAAAAAD//wAAAQACAAIAAAAAAAAAAgAAAAAAAAAAAAEAAQABAAAAAAAAAAEAAAACAAEAAAAAAAEAAQAAAAIAAAAAAAEAAQABAAAAAQAAAAAAAAAAAAEAAQAAAAEAAQAAAAAAAQACAAAAAgABAAAAAgABAP//AQABAP//AAABAAAAAAABAAIAAQAAAAEAAAAAAAAAAAAAAAEAAAAAAAEAAAAAAAEAAQAAAAAAAAABAAAAAAAAAAEAAAABAAAAAQAAAAAAAQAAAAAAAAABAAAAAAAAAAAAAgAAAP//AAAAAAAAAAABAAIAAAAAAAEAAQAAAAMAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAQABAAAAAAAAAAAAAQAAAAEAAAAAAAEAAQABAAAAAQAAAAAAAQABAAAA//8AAAAAAQAAAAAAAAAAAAEAAgAAAAAAAAAAAAAAAgABAAAAAAAAAAAAAAABAAAAAAABAAAAAgAAAAEAAAAAAAEAAAAAAAEAAAAAAAEAAAACAAAAAAABAAAAAAAAAAAAAQACAAEAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAEAAAAAAAEAAAABAAAAAAAAAAAAAAABAAEAAAAAAAAAAAAAAAEAAAAAAAAAAAABAAIAAQAAAAAAAgAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAQAAAAEAAQABAAAAAAAAAAAAAQAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAABAAEAAAAAAAEAAQAAAAAAAAAAAP//AAAAAAAAAAABAAEAAAD//wEAAgAAAAAAAAABAAAAAQABAAEAAAAAAAEAAQAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAEAAgABAAAAAQAAAAAAAgABAP//AAAAAAAAAgABAAEAAQABAAAAAQAAAAAAAgABAAAAAAAAAAEAAAAAAAAAAQAAAAIAAAAAAAIAAQACAAAAAQAAAAAAAwACAAAAAAACAP//AAAAAAAAAQACAAAAAQAAAAEAAAAAAAEAAAABAAIAAAAAAAIAAAACAAAAAAABAAEAAAAAAAAAAAACAAAAAAABAAEAAgABAAAAAAAAAAIAAQAAAAAAAgAAAAAAAgACAAAA//8BAAAAAAABAAEAAQAAAAEAAQAAAAAAAQABAAAA//8AAAEAAAAAAAEAAAAAAAEAAQABAAEAAQACAAAAAQAAAAAAAgAAAAAAAQABAAEAAQAAAAIAAAAAAAAAAQACAP//AgABAAAAAAAAAAEAAAD//wIAAAAAAAAAAQABAAAAAgD//wEAAQAAAAIAAAAAAAAAAAACAAAAAAACAP//AwABAAAAAQAAAAIAAQAAAAIAAQAAAAEAAAACAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAABAAIAAQAAAAAAAAAAAAEAAAAAAAEAAAAAAAEAAgABAAEAAAABAAAAAAABAAEAAQAAAAAAAQAAAAEAAQABAAEAAAAAAAAAAQAAAAAAAQAAAAAAAQACAAAAAgAAAAAAAgAAAP//AAAAAAAAAgABAAEAAQAAAAEAAgAAAAAAAQABAAAAAAABAAIAAAD//wAAAAAAAAEA//8BAAIAAQABAAEAAAAAAAEAAAACAAAA//8CAAAAAAAAAAAAAQADAAEAAAAAAAAAAgABAAAAAAAAAAEAAAAAAAEAAAAAAAAAAAABAAEAAAAAAAAAAAABAAAAAAAAAAAAAQABAAAAAQACAAAAAQAAAAAAAQAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAABAAAAAAABAAAAAAAAAAAAAQABAAEA//8BAAEAAAAAAAEAAAD//wEAAQACAAEAAAABAAEAAAABAAAAAAAAAAAAAAAAAAEAAQD//wEAAQABAAIAAQAAAAAAAAAAAAIAAgAAAAEAAQAAAP//AAAAAAAAAAACAAAAAQAAAAEAAgAAAAEAAQABAAAAAAD//wAAAAAAAAAAAAAAAAEAAQAAAAAAAQABAAAAAQAAAAAAAQD//wAAAQABAAAAAAAAAAEAAQAAAAAAAQAAAAAAAgAAAAAAAAAAAAEAAQAAAAIAAAAAAAEAAAACAAAAAgABAAAAAQAAAAIAAQABAAEAAQAAAAAAAAABAAAAAQAAAAAAAAAAAAEAAAAAAAIAAAD//wIAAQACAAAAAAABAP//AQAAAAAAAAAAAAEAAAAAAAIAAgAAAAAAAQAAAAAAAAABAAEAAAAAAAEAAgAAAP//AAAAAAAAAAACAAEAAAAAAAAAAgD//wEAAQABAAEAAAAAAAAAAQAAAAAAAAAAAAAAAQACAAAAAQAAAAAAAgAAAAAAAAD//wEAAQAAAAEAAQAAAAEAAgABAAAAAQAAAAAAAQAAAAAA//8AAAAAAAAAAAIAAAAAAAIAAAABAAEAAQAAAAIAAAACAAEAAAABAAAAAAAAAAAAAAACAAAAAQAAAP//AAAAAAAAAAACAAAAAQAAAAEAAQABAAAA//8AAAEAAgAAAAEAAgABAAAAAAABAAEAAgABAAAAAAAAAAEAAAD//wAAAAAAAAEA//8AAAEAAgABAAAAAQAAAAEAAgACAAAAAQABAAAAAAAAAAAAAQACAAEAAAAAAAEAAAABAAAAAAAAAAMAAQAAAAIAAAACAAAAAQACAAEAAAAAAP//AAACAAAAAAABAAIAAgABAAEAAAAAAAIAAQAAAAEAAgABAAAAAwABAAAAAAAAAAEAAAABAAEAAQAAAAEAAgAAAAAAAQABAAAAAAAAAAEAAAAAAAAAAAAAAAAAAgAAAAAAAQABAAAAAQAAAAAAAgAAAAAAAQABAAEAAQAAAAIAAAAAAAAAAgABAAAAAgABAAAAAAABAAEAAAAAAAIAAAAAAAAAAQABAAAAAQAAAAAAAQAAAAIAAAD//wEAAAACAAAAAQACAAAAAgAAAAAAAQAAAAIAAQAAAAIAAAAAAAEAAQABAAAAAAAAAP//AgAAAAAAAAAAAAEA//8BAAEAAQAAAP//AAAAAAAAAAAAAAEAAAAAAAIAAgAAAAAAAQACAAAAAQACAAIAAQAAAAIAAQAAAAIAAQACAAEAAAAAAP//AAAAAAAA//8AAAAAAAABAAAAAgAAAAAAAQAAAAAAAQAAAAEAAQAAAAEAAQABAAAAAQABAAAAAQABAAAAAAABAAAAAQAAAAAAAAAAAAAAAAABAAEAAAABAAEAAAD//wAAAQABAAAA//8BAAAAAAAAAAEAAQACAAEAAAABAAAAAQAAAAEAAAABAAAAAQADAAEA/////wAAAAABAAEAAAAAAAAAAAACAAAAAQACAAEAAQABAAEAAQAAAAAAAQAAAAIAAAAAAAEAAQAAAAAAAQD//wAAAQADAAAAAAACAAEAAQAAAAAAAQAAAAAAAAAAAAIA//8BAAAAAAAAAP//AQAAAAAAAgACAP//AQAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACAAEAAgACAAEA//8AAAEAAQAAAAAAAAD//wEAAQAAAAAAAAD//wAAAQACAAAA//8CAAAAAQAAAAEAAgACAAEAAAABAAAAAAABAAAAAAAAAAEAAAAAAAEAAAACAAEAAAACAAAAAAAAAAAAAAABAAEAAAAAAAEA//8AAAIAAAAAAAAAAQABAAIAAQACAAEAAAABAAAA//8AAAAAAAABAAAAAAAAAAAAAQABAAEAAgAAAAAAAQAAAAAAAQAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAEAAAAAAAAAAAAAAAEAAAAAAAEAAAAAAAEAAQAAAAEAAQAAAAAAAAACAAAAAQABAAAAAgAAAAEAAAAAAAEAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAQACAAAAAQAAAAEAAQAAAAAAAAAAAAEAAQAAAAIAAQABAAAAAQABAP//AgACAAAAAQACAAEAAAABAAEAAAAAAAIAAAABAAEAAAABAAAAAAAAAAAAAQABAAAA//8BAAAAAAAAAAIAAQABAAAAAAABAAAAAQABAAAAAAACAAAAAgAAAAEAAAAAAAEA//8BAAEAAQABAAIAAQACAAAAAAABAAAAAQABAAAAAAABAAEAAAAAAAEAAAAAAAAAAAACAAAAAQD//wAAAAAAAAAAAAACAAEA//8BAAEAAAAAAAAAAQABAAEAAAABAAEAAgABAAAAAAABAAEAAAACAAEAAAAAAAEAAAABAAAA//8AAAAAAQAAAAEAAAAAAAEAAAABAAAAAQABAAAAAgACAAIAAAAAAAIAAgAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAQAAAAIAAQACAAEAAAAAAAAAAAAAAAAAAAAAAAAAAQABAAAAAQAAAAAAAQAAAAAAAAAAAAAAAQAAAAEAAQAAAAAAAAAAAAAAAgABAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAEAAQABAAAAAQAAAAAAAQABAAAAAAACAP////8AAAAAAQABAAEAAAAAAAEAAAAAAAEAAAAAAAIAAAAAAAIAAAAAAAEAAAAAAAAA//8AAAAAAAAAAAAAAAAAAAEAAQABAAEAAQAAAAAAAQABAAEAAQAAAAAAAgAAAP//AAAAAAAAAAABAAAAAAAAAAEAAAAAAAIAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAQAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQABAAEAAQAAAAAAAAABAAAAAAABAAAAAAAAAAEAAQAAAAEAAAABAAAAAAAAAAAAAQAAAAAAAAAAAAIAAQAAAAEAAAAAAAAAAQABAAAAAQAAAAAAAQAAAAAAAAAAAAEAAAABAAAAAQAAAAAAAAAAAAAAAAABAAEAAQAAAAIAAQAAAAAAAAACAAAAAQACAAEAAQAAAAEAAQAAAAIAAAACAAEAAAAAAAAAAgAAAAAAAAAAAAAAAQAAAAAAAQAAAAAAAAABAAAAAAAAAAAAAgAAAAEAAQAAAAAAAQABAAAAAgAAAAAAAAAAAAAA//8AAAAAAAAAAAEAAAAAAAEAAAACAAAAAAAAAAEAAQABAAAAAAAAAAAAAAAAAAEAAAACAAAAAAABAAAAAAAAAAAAAAACAAAAAQAAAAEAAAAAAAAAAAAAAAEAAgAAAAEAAAABAAAAAQAAAAAAAQAAAAAAAAACAAAAAAAAAAAAAAABAAEA//8BAAEAAAAAAAAAAAAAAAAAAAACAAAAAAABAAAAAAAAAAEAAAACAAEAAAACAAEAAQABAAAAAAABAAAAAAABAAEA//8AAAEAAAACAAAAAAAAAAEAAAACAAEAAAABAAIAAQAAAAEAAQABAAAAAQABAAIA//8AAAAAAQABAAEAAAD//wAAAAACAAEAAAABAAEAAAABAAAAAQAAAAEAAQAAAAIAAQABAAAAAgAAAAEAAAAAAAEAAQACAAAAAQABAAEAAgAAAAAAAQABAAEAAAAAAAAAAQAAAAAAAgACAAIAAQABAAEA//8AAAAAAQABAAAAAAAAAAEAAgAAAAAA//8AAAAAAQACAAAAAAABAAAAAQABAAEAAwABAAIAAAABAAEAAAABAAAAAAAAAAAAAQAAAAEAAAAAAAMAAAABAAEAAAABAP//AAABAAEAAAAAAAEAAAAAAAIAAAAAAAAA//8BAAIAAQACAAEAAQABAAAAAQAAAAAAAAAAAAAAAAAAAP//AQAAAAEAAgAAAP//AQAAAAAAAQAAAAAAAAAAAAAAAAD//wAAAAAAAAAAAQABAAAAAQAAAP//AAAAAAAAAAAAAAIAAAAAAAEAAAABAAAAAAAAAAAAAAAAAAIAAQACAAAAAQABAAAAAAABAAAAAQACAAAAAQAAAAAAAQAAAAEAAQABAAEAAAAAAAAAAQAAAAAAAAAAAAEAAgAAAAAAAgAAAAAAAgABAAAAAAAAAAEAAQAAAAEAAAAAAAEAAQABAAAAAgABAAEAAAAAAAAA//8BAAEAAAAAAAIAAQABAAAAAAADAAAAAQABAAAAAgAAAAAAAQAAAAIAAQAAAAMAAAAAAAAAAAAAAAAAAAAAAAEAAQACAAAAAAAAAAAAAQAAAAAA/////wIAAAAAAAEAAAABAAAAAQABAP//AQACAAEAAQABAAIAAQAAAAEAAAAAAAEAAAABAAEAAAABAAAAAAAAAAAAAQABAAAA//8BAAAAAQAAAAIAAQABAAAAAAACAAAAAAAAAP//AAABAAAAAgAAAAEAAAAAAAEA//8BAAEAAQAAAAEAAQACAAAAAAABAAAAAQABAAAAAAABAAEAAQAAAAAAAAABAAAAAAABAAAAAgD//wAAAAAAAAAAAAACAAEAAAABAAEAAAAAAAAAAQABAAEAAAAAAAAAAQAAAAAAAAAAAAEAAAACAAEAAAAAAAEAAAABAAAA//8AAAAAAQABAAIAAAAAAAEAAAABAAEAAQABAAAAAQACAAIAAAD//wIAAgAAAAEA//8AAAAAAAABAAAAAAAAAAEAAAAAAAEAAAACAAEAAAAAAAAAAQAAAP//AAAAAAEAAgABAAEAAgAAAAAAAgABAAAAAAAAAAAAAgABAAIAAQAAAAAAAAAAAAAAAgAAAAAAAAAAAAEAAAAAAAAAAQAAAAAAAAAAAAAAAQABAAAAAQAAAAAAAAACAAAAAQACAP//AAAAAAAAAgACAAEAAAAAAAEAAQAAAAEAAAAAAAIAAAABAAIAAAABAAIAAQABAAAAAAAAAAAAAQAAAAEA//8AAAEAAAABAAAAAQAAAP//AAAAAAEAAQABAAEAAgD/////AQD//wAAAQABAAAA//8AAAEAAAAAAAIAAQABAAAAAAAAAAAAAQAAAAAAAQAAAAAAAQD//wAAAAAAAAAAAQAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAQAAAAEAAQAAAAAAAAAAAAAAAQAAAAEAAgACAAEAAAAAAP//AQABAAAAAAACAP////8AAAAAAgAAAAIAAgABAAAAAAAAAAAAAAAAAAIAAAAAAAEAAgABAAAAAQAAAAAAAQABAAAAAAAAAP//AAACAAEAAAAAAAIAAAAAAAAAAAAAAAAAAQAAAP////8BAAEAAQAAAAIAAgAAAAEAAQACAAEAAQABAAAAAgAAAAAAAgAAAAEAAAABAAEAAAAAAAAAAQD//wAA/////wAAAQABAAAAAAD//wAAAQAAAAAA//8AAAAAAQABAAEAAQABAAAAAQABAP//AgAAAAAAAQAAAAEAAAABAAAA//8AAAEAAAAAAAEAAAACAAAAAQAAAAEAAgABAAAAAAABAAEAAAAAAAEAAAABAAAAAAAAAAAAAAAAAAAAAAACAAIAAQAAAAIA//8AAAAA//8AAAAAAgAAAAIAAQABAAAAAAAAAAAAAgAAAAAAAAACAAEAAAAAAAAAAAAAAP////8CAAIAAwABAAAAAAAAAAAAAQADAAEAAAABAP//AAAAAAAAAQABAAIAAAAAAAAAAQABAAAAAAABAAEAAQACAAAAAAAAAAEAAQACAAEAAAABAAEAAgAAAAMAAAAAAAEAAQACAAAAAQAAAAAAAAAAAAEAAQABAAEAAAAAAAAAAgACAAAAAgACAAAAAgAAAP//AAAAAP//AAABAAEAAAAAAAIAAQAAAAIAAAAAAAEAAQAAAAIAAAABAAMAAgADAAEAAgAAAAAAAAABAAAA//8BAAEAAQABAAAAAgABAAAAAQABAAEAAQACAAEAAAAAAAEAAwAAAAAAAAABAAAAAAACAAIAAAAAAAIAAQAAAAIAAAACAAIAAAAAAAEAAQAAAAAAAAABAAEAAwACAAAAAgAAAAAAAQABAAAAAAAAAAAAAwAAAAIAAQAAAAIAAQACAAAAAgAAAAAAAQABAAEAAAAAAAAAAQABAAEAAAAAAAIAAgABAAEAAQAAAAAAAgACAAAAAAACAAAAAAAAAAAAAgABAAAAAgABAAEAAAABAAAAAQABAAEAAQAAAAIAAAACAAEAAQABAAAAAQAAAAAAAAACAAAAAQACAAAAAgAAAP//AAAAAAEAAAAAAAEAAAAAAAAAAAABAAIAAQAAAAAAAQAAAAAAAgACAAAAAAABAAAAAgABAAEAAgADAAIAAAABAAAAAQAAAAAAAAABAAAAAQAAAAAAAAD//wEAAAABAAEAAgAAAAEAAQAAAAAAAAABAAAAAgABAAAAAQAAAAEAAQAAAAAAAQAAAAAAAAABAAAAAQAAAP//AAAAAAEAAAACAAAAAAABAAAAAAAAAAAAAQACAAEAAAAAAAEAAQAAAAAAAAAAAAEAAAABAAAAAAD//wAAAQABAAAAAQAAAAAAAAAAAAEAAAABAAAAAAAAAAEAAAAAAAAAAAAAAAEAAgABAAAAAgABAAAAAAAAAAAAAAACAAEAAAAAAAEAAQAAAAIAAQAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAgAAAAAAAAAAAAEAAQAAAAAAAQAAAAAAAAABAAAAAAAAAAEAAAAAAP//AAAAAAAAAAD//wEAAAAAAAEAAAAAAAEAAQAAAAAAAAABAAAAAAABAAEAAAAAAAAAAgAAAAEAAAABAAEAAAAAAAAAAQAAAAAAAAAAAAEAAQABAAAAAQAAAAAAAgABAP//AAAAAAAAAQABAAAAAQABAAAAAAAAAAAAAQABAAEAAAAAAAEAAAAAAAAAAQAAAAEA//8BAAEAAQACAAEAAgAAAAAAAQADAAAAAQACAP//AAAAAAEAAQACAAEAAAAAAAEAAAABAAEAAAABAAIAAAABAAIAAAACAAEAAQACAAEAAAABAAAAAAABAAAAAAABAAEAAgABAAAAAAABAAIAAgAAAAAAAgAAAAAAAgADAAAA/v8BAAAAAAABAAIAAQAAAAAAAgABAAAAAQABAAAA//8AAAIAAAABAAAAAAD//wAAAQAAAAEAAAACAAEAAAAAAAAAAgAAAAAAAQABAAEAAQAAAAIAAQABAAAAAgABAAAAAgABAAEAAAAAAAAAAAD//wIAAAAAAAEA//8BAAAAAQAAAAAAAQABAAIAAAD//wAAAAACAAAAAAABAAAAAgAAAAAAAQABAAEAAQAAAAIAAAAAAAIAAAACAAAAAAAAAAAAAQD//wAAAAABAAEAAAABAAIAAQAAAP//AAAAAAEAAAABAAEAAAAAAAEAAgABAAAAAAAAAAAAAQABAAIAAQAAAAAAAQABAAEAAQACAAEAAAAAAAAAAgAAAP//AQAAAAAAAQACAAAAAQABAAAAAgAAAAAAAAD//wEAAgABAAEAAQABAAAAAgABAAAAAQABAAAAAAABAAEAAAD/////AAAAAAEAAAABAAIAAQABAAEAAAAAAAEAAQABAAAA//8BAAAAAAAAAAAAAAADAAEAAAAAAAAAAgABAP//AAABAAAAAQAAAAEAAAAAAAAAAAAAAAEAAQD//wIAAAABAAAAAAAAAAAAAQABAAAA//8DAAAAAQAAAAAAAAAAAAEA//8BAAIAAAABAAEAAAAAAP//AAABAAAA//8BAAEAAAAAAP//AQACAAEAAAABAAAAAAAAAAEAAAAAAAAAAAABAAAA//8BAAAAAAACAAAAAAD//wAA//8BAAEAAQABAAEAAQAAAAIAAQABAAAAAAABAAIAAQABAAAAAQAAAP//AAAAAAAA//8BAAAAAAAAAAAAAgAAAAAAAQABAAAAAAD+/wAAAAABAAAAAAAAAAAAAAAAAAAAAQACAAEAAAAAAAAAAAD//wAAAAAAAAEAAAAAAAEAAAAAAAAAAgABAAAAAgABAAAAAAAAAAAAAQAAAAIAAAAAAAEAAQABAAAAAgAAAAAAAQABAAEAAAABAAAAAAABAAAAAQABAAAAAQAAAAAAAQAAAAAAAAAAAAIA//8AAAEAAAACAAAAAAABAP//AAAAAAAAAAABAAEA//8AAAIAAQAAAAEAAAAAAAEAAAABAAIAAQABAAAAAwABAAAAAAAAAAAAAAACAAAAAAAAAAAAAgABAAEAAQABAAEAAAD//wAAAQAAAAAAAAAAAAAAAgAAAAAAAQAAAAAAAQABAAAAAAAAAAAAAQABAAEAAQAAAAAAAQAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAEAAAACAAEAAAAAAAAAAAABAAAAAAABAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAACAAAAAQAAAAAAAAAAAAAA//8AAAEAAQAAAAEAAAABAAAAAAAAAP//AQABAAAA//8BAAEAAAAAAAAAAAAAAAEA//8BAAEAAQAAAAEAAAAAAAAAAQABAAAAAQABAAAAAAAAAAAAAQACAAEAAAAAAAAAAAABAAAAAAAAAAEAAAAAAAEAAAABAAAAAAABAAAAAAAAAAAAAAABAAAAAAABAAIAAQAAAAEAAAAAAAAAAQABAAEAAAAAAAAAAgABAAAAAAAAAAAA//8BAAEAAAAAAAAAAgAAAAAAAQABAAAAAAAAAAEAAAAAAAAAAAAAAAAAAQAAAAAAAQACAAAAAQAAAAAAAgAAAAAAAAABAAEAAAAAAAAAAAAAAAAAAgABAAAAAQABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABAAAAAQAAAAAAAQABAAAAAAAAAAAAAAAAAAAAAQACAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAEAAAABAAAAAAABAAAAAAAAAAAAAAAAAAEAAAAAAAEAAAAAAAEAAAAAAAAAAQABAAEAAAABAAEAAgAAAAAAAAAAAAAAAAACAAAAAAAAAAEAAQAAAAEAAQABAP//AAAAAAAAAQAAAAAAAAAAAAAAAQD//wAAAQAAAAAAAQAAAAAAAQAAAP//AAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAIAAAABAAEAAgAAAAAAAAACAAEAAQACAAIAAQAAAAEAAQABAAIAAQACAAEAAAAAAAAAAgAAAAAAAAAAAAEAAgABAAAAAQD//wAAAgABAAAAAQAAAAAAAgAAAAEAAQAAAAAAAQAAAAAAAgAAAAAAAAAAAAEAAAAAAAAAAAAAAAIAAAAAAAIAAAADAAAAAQABAAAAAgABAAAAAAABAAAAAAAAAAIAAAABAAAAAAAAAAAAAAAAAAAAAQACAAAAAQAAAAEAAQABAAAA//8AAAEAAQAAAAEAAQACAAAAAAABAAAAAgACAAAAAQABAAEAAQABAAEA//8BAAIAAAACAAEA//8BAAAAAAAAAAAAAgABAAAAAAABAAAAAQAAAAEAAQACAAEAAAAAAAAAAAABAAAAAAACAAAAAgABAAEAAAABAAEA//8BAAEAAQAAAAIAAQACAAAAAAABAAAAAgABAAAAAAACAAEAAAAAAAAAAAAAAP//AAABAAAAAQAAAAAAAAAAAAEAAAACAAEA//8CAAAAAAAAAAAAAgACAAEA//8BAAEAAQABAAAAAAABAAIAAAACAAIAAAAAAAEAAAACAAAAAAABAP//AQAAAAEAAAABAAIAAAABAP//AAABAAAAAgACAAIAAAAAAAIAAwAAAAAAAAAAAAEAAAACAAAAAAAAAAAAAQAAAAIAAQACAAEAAAAAAAAAAQAAAAAAAAAAAAEAAgABAAAAAgABAAEAAgAAAAAAAAAAAAEAAgABAAIAAQAAAAEAAgAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//8BAAEAAgABAAAAAAAAAAEAAQADAAAAAAACAP//AAAAAAAAAgACAAEAAAAAAAEAAQAAAAAAAAAAAAIAAAABAAIAAAAAAAIAAAABAAEAAAAAAAAAAAAAAAEAAAAAAAEAAQABAAAAAgABAAAAAQACAAEAAgABAAAAAgAAAP//AQAAAAEAAAABAAEA//8AAAAAAAAAAAEAAAABAAAA//8BAAAAAAABAAEAAAAAAAAAAAD//wAAAAAAAAEAAQAAAAAAAQAAAP//AAAAAAAAAAAAAAIAAAAAAAAAAQABAAEAAAAAAAEAAAABAAIAAgABAAAAAQABAP//AAABAAAAAAACAAAAAAAAAAEAAgAAAAEAAQABAAEAAAAAAAAAAAAAAAEAAAAAAAEAAQAAAAAAAQAAAAAAAQABAAAAAQAAAAAAAQABAAEAAAAAAAEAAQAAAAAAAgAAAAAAAAAAAAAAAAABAAIAAQAAAAMAAQABAP//AQACAAAAAQAAAAEAAgAAAAIAAQAAAAIAAAABAAEAAAAAAAAAAQAAAAAA//8AAAEAAAAAAAEAAAD//wEAAQABAAAAAAAAAAAAAQAAAAIAAAAAAAEAAAABAAEAAQAAAAEAAAD//wEAAAAAAAEAAAD//wEAAgAAAAAA//8BAAAAAAACAAEAAgAAAAAAAAAAAAIAAAABAAEAAAAAAAAAAAAAAAAA//8BAAAAAgABAAAAAQAAAAAAAQAAAAAAAQD//wEAAgAAAAIAAQABAAEAAgAAAAAAAgAAAAAAAAACAAEAAAAAAAAAAAAAAAEAAAABAAIAAgABAAEAAAABAAEAAAACAAAAAAABAAAAAAAAAAEAAAADAAIAAAAAAAAAAAAAAAAAAAACAAEAAAAAAAAAAAAAAAAAAAABAAIAAgABAAEAAQABAAAAAQAAAAAAAgABAAEAAAAAAAEAAAAAAAAAAAAAAAAA//8BAAMAAQABAAEAAQAAAAAAAgACAAAA//8BAP////8BAP//AQACAAEAAAAAAAEAAAABAAAAAAAAAAIAAAAAAAIAAAABAAAAAQABAAEAAAAAAAEAAAACAAAAAQABAAEAAgABAAEAAQACAAIAAgACAAEAAgABAAEAAwABAAAAAQAAAAEAAQABAAIAAQAAAAEAAgABAAAAAQABAAAAAAAAAAIAAAD//wAA//8AAAAAAAAAAP//AQABAP//AQAAAAAAAQD//wAAAAAAAAEAAAAAAAEAAAAAAAAAAQABAAEAAQABAAEAAQABAAEAAQABAAAAAQABAAAAAQAAAAEAAQD//wEAAQAAAAIA/////wAA//8AAP//AAAAAP//AAD/////////////////////AAD//wAAAAAAAAEAAAABAAEAAAABAAEAAQABAAIAAgABAAIAAQACAAIAAgACAAIAAgABAAIAAgACAAIAAgABAAAAAQABAAEAAwACAAEAAQAAAP3/BAAEAAAACQABAAAAAwD//wMAAQACAAIAAAADAAEAAQABAAIAAQACAAMAAQAEAAAABAD//wEADgAAAAYABwD4////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AgACAAYAAAADAAoADwAUAA0ADAARABcAFQAXACEAJwAtACgAJAAlACEAHAAjACkAKQAxAC8AIwAhACUAIAAYABcAHAAiAB4AEgAQABQADgAJAAkACAAIAAUABAADAP///v8CAAEA/v8AAP3/+/8AAAgABAADAAcABAAHAAAAAgAHAAYACAAHAAoAAAAAAAUAAQABAP7//v/6//f/+f/3//T/8v/2//f/8//w//P/9P/1//f/9P/4//X/8v/3//P/8f/0//r//f/7////+v/4//v/+P/9//z///8EAAAABQAEAAYAAAD8/wIAAAABAPz//f8AAAEAAgD8//3//v////3//f8AAAAA///8/wAAAAADAAMA/v/9//v//v8AAP//AAADAAcABAAFAAYABQAGAAUABQAHAAsADgAPAA8ABwAHAAwACAAJABAAEwALAAkADAAIAAgAAgAEAAUAAgABAPv/+v/1//b/+P/0//H/7f/x/+7/6//u//D/8v/t/+3/8f/x//D/8//5//r//P/9//7//v/9/wIAAwABAAcACAAHAAgACAAFAAMABwAIAAcAAwAAAAMAAAD///7/+v/8//r/+v/7//v/+//8//3/+//7////AgADAAcADwANAAQACAAMAAgAEAASAA4AEwAWABIAEQARAA8AFAATAAsAEAASAA0ADAAMAAkABgAGAAQAAwAJAAcAAQADAAIA//////7/+v8AAAMA/f/8//f/+v/+//b/+f8AAP3/+P/8//z///////H/9f/9//P/9f///wMA///6//r/9//2//r//P/8//3/AQACAAEA+v/4//3/+f/5/wMABgAAAP//AgD+/wAA/v/7////AAD+//7///////z/+v/+//3//P/+///////6//T/9/8EAP//9v/7//v/+f/9/wAAAwAGAAQABQALAAsACAALAA0ADgAYABcAEgAWABcAFwAbABwAFQAaAB8AGQAXABMAEwARAA0ACQANAAsABQAGAAMABwAGAP3//P/9//v//f///wEAAAAAAAMA+//5//r///8HAP7/AAACAP3//v////7/AwADAPj/+//7//j/+f/y//b/9//y//P/9f/x/+z/9f/2/+j/5v/u//P/8//u//b/+f/z//X/8f/0//b/9//1//T//P/9/////P/6//z/AAD9//n/AwD+//3/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8f/u/wMAFgD5//T///8KAPn/AwD9//X/DwABAPr/+v8FAAkA9//5/wUACAD1////CgDx/wsACgDx/wIAAAAFAAsA9//y/wkACAD6//v/AAARAP7/9f8EAP///f8CAP//9v8GABEA///y//v/AgAJAAYA8//0/wIAGgD//+L/CAAWAAAA8P/y/wkAFQD6/+///P8PABAA9f/2//3/AwAPAP7/7/8AAA4AAAD7/////v8KAPz/9/8JAAEA/f8AAPn//P8OAAEA9////wQAFQD0/+v/AgAIAAYA+/8DAPr/CgAJAPL//P8EAAMA9P8BAA0AAwD5//v/BQALAPz/7v8CAAYAAwADAP3/+v8CAAwA+v/z/wQADgD9//j/AAACAAUA9v8BAAkA+P8LAAIA8v8CAAUA///7//3/AgAQAP//7/8KAAMA+P///wMAAAABAPz/AgALAPT/AAAIAP3/AgD6////BQD9//7/BQABAAIA/P8EAAUA9P/8/wIABwACAP///f///wYA/v/7/wIABgD+//n/AAAFAAUAAAD4//7/BgACAAIA+v/4/wUACwD4//7/BgD4/wkA/v/2/wcAAgACAAYA9//2/wcABgAAAPr/AAAIAP3/+v8CAAgA+v/x/w0ABwD1/woAAgD0//7/DAADAPb/+/8EAAkA+v/+/wEABwD9//P/EgD//+//BQANAPn/+v8KAP///P/+/wkA///z/wgAAwDz/wkADADw////BwACAAAA9v8EAAUA/v/5/wIAEQD0//r/BgD//wYA9v8HAPv/+v8XAPn/8P8AAAsACgD9/+r/+f8hAAsA4v/1/xUAAgD9/wEA8v8HAAsA+//+//z/BwAFAPD/AwANAP//9//7/wYABQAFAPv/+//7/wcADAD3//f//v8HAA=='
FILLER_B64_EN = '//8AAP//AAAAAAEAAAABAAAAAAACAAAAAAAAAAAAAAABAAEAAAAAAAEAAQABAAEAAAAAAAAA//8BAAEAAQABAP//AAAAAAEAAAACAAEAAQAAAAAAAQAAAAAAAAABAP//AgABAP//AAAAAAAAAQAAAP//AQD+/wAAAgABAAEAAAAAAAAAAgAAAAAAAQD//wAAAQABAAEAAAD////////+/wAA//8BAAEAAgABAAAAAAD//wAAAQADAP//AAABAP//AQD//wAAAQABAAMAAAD//wEAAAABAAAAAAAAAAEAAAAAAAEAAAAAAAAA/v8AAAIAAAAAAAEAAAABAP7/AAABAP7/AgACAAIAAgABAAAAAgAAAP//AgAAAAIAAQD/////AQD//wAAAAAAAAAA/f8BAAEAAAABAAAAAAABAP//AAABAAEAAAAAAAMAAQAAAP7/AAABAP//AQAAAP7/AQACAP//AgD///z/AQACAAAA/f8CAAEA/v8BAP////8CAAQAAAAAAP7/AgACAP//AwD//wMABgD//wEAAAD/////+v8BAAYA//8BAAsAAAD7/wQAAgD+//7/AAD//wYA/P/8/wAAAAAHAPn//f8CAAIABQAEAPf//v/8//r/BgD//wUABwAFAPz/+P8CAAcA/v/3/wAAEAD6//3/DgD+//3/+f/8/wUAAwDz/wMAEAAOAPj/6v8DAA8AAwDv/wcABwD5/wAACQAMAPb/8P/+/w0AAgDz/w4ABwABAAEA9f/2//b/CgALAAgAAAADAPv///8GAOb/BwAWAO//AQAPAAAA8//+/wsABwAIAN7/DAAOAO3/DAAOAAQA3f/5/xQACgDo/xQAJQDy//f/5//r//3/CAD0/zAANQDW/+3/9f8FABYA4P/3/wYA7P8PABgAAwAbABMA2//i//P/7f8jAAwA1f8UAC0AJQDm/67/DQAXAAAAIAAKAP3/6P+6/+f/PwA7AC4A9P/b/9v/5P8pAOr/9f8OAAgA+P8MAFgA8f+2/8f/CABPADkAsv/V//P/wf8uAFgAZAC//+v/GQDB/7T/hv9zAKcA/f/S/9P/6v9RACYAxv/i/7D/u/8nAKIAQgCz/yQACgCt/5z/IwBGANb/HADu/x8A3f+4/5IAswCY/23/BwDH/3EA3/92/wwAagCRAGUA+P8Y/0L/2//5ANAATv+v/1AA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+/8GABIAHQAnADAAOQA9AEAAPwA7ADUALgAmABwAEwAGAP//+P/y/+//7f/u/+7/8v/2//7/BAAIAA4AEgAWABYAFgAVABAACwAGAP//+P/x/+z/5//k/+P/4v/m/+j/7f/1//z/AwAJABEAFQAXABkAGwAaABYAFAAPAAcABQD///z/+v/2//X/9//6//v/AwAGAAsAFAAZACEAIgAkACQAJAAiAB0AGwAVAA8ACQADAAAA+//8//v/+v/9////AAAEAAwADwAUABoAGwAeACIAIQAgAB8AGwAWABEACwAIAAEA/f/3//L/8f/u/+z/7f/w/+//8//1//j//v8AAP//AgAEAAIABAADAAEAAAD+//v/+P/3//P/8f/v/+//8P/u/+//8f/x//P/9P/0//j/+v/7//3//P/7//v/+f/2//b/8//v/+7/6//p/+r/6P/o/+v/6//r/+r/7P/u//D/8//1//X/9v/4//b/9v/1//X/9P/y/+//7v/t/+v/6v/q/+3/7P/r/+7/8v/0//X/9//4//j/+//8//r//P/5//f/9//1//b/9f/0//X/9P/z//X/9//5//3///8CAAYACAALAA0ADwARABAAEAAQAA8AEAAPAA0ADQAKAAsACwALAA4ADwARABMAGAAaAB4AIQAhACIAHwAhAB8AHgAcABkAGQAVABIAEAAOAA0ADQALAAwADAAMAA0ADQANAA0ADwANAA4ADAALAAoACAAHAAEAAQAAAP7/+//6//n/+P/3//b/+P/4//j/9//3//b/9v/3//X/8//y//D/7//u/+z/6//r/+r/6P/p/+b/5f/m/+j/6f/o/+v/7P/s/+7/7v/v//D/8P/w/+7/8P/x//D/8f/w//D/8f/y//D/8v/z//H/8v/0//b/9v/2//f/9//5//r/+v/+//z//f8AAP//AAABAAEAAQABAAIAAwADAAMABAAFAAYABQAFAAcABQAHAAcABwAJAAgACAAIAAgACAAIAAkACAAHAAYABgAGAAYABgAGAAUABQAHAAQAAwAEAAMABQAEAAQAAwADAAQAAwACAAMABAADAAEAAgADAAEAAQACAAQAAwABAAMABAABAAAA//8AAAAAAAABAP//AAABAAEAAQAAAAAAAAABAAEAAQAAAAAAAAAAAP//AAABAAAA/////wAAAAD///7///8AAAAAAQAAAAAA//8AAAEAAQACAAAAAAAAAAAA///+////AAD+//7//v/+/////v/9//3//f////7//v/+//7////+///////+//7//f/+/////f/9/////v8AAAAA//////7////+/wAA/v/9/wAA//8AAAAA//8AAP7///8AAAAAAAAAAAAAAAD//wAAAAD//wAAAAAAAAAAAAAAAAAAAAAAAAAA//8AAAAAAAAAAP////8AAAAA//8AAAEAAAAAAAAAAAAAAAAAAQACAAEA//8AAAAAAAD//wEAAQD//wAAAAAAAP////8AAAAA/////wAAAAD//wAAAAAAAAAAAAAAAP//AAAAAAAAAQD//////////wAA/////wEAAAAAAAAAAAAAAAAAAAABAAAAAAABAP//AAAAAAAAAQAAAAAAAAAAAAEAAQABAAIAAQABAAEAAQABAAEAAQAAAAAAAAAAAAAA//8AAAAAAAAAAAAAAQABAAAAAAABAAEAAQABAAEAAQAAAAAAAAAAAAAAAAD//wEAAAD//wAA////////AAABAAEAAAAAAAAAAQAAAAAAAQABAAIAAAAAAAAAAAAAAAAAAQD//wAA//8AAAAAAAAAAAAAAQAAAAAAAQABAAAAAAAAAAAAAQAAAAAAAAABAAAAAQD//wEAAAABAAEAAAD//wAAAAAAAAEAAAABAAAAAAAAAAAAAAABAAAAAQABAAAAAAAAAAEAAAD//wAAAAAAAAEAAAD//wAA//8AAAEAAAAAAAAAAgABAAAAAQAAAAEAAAABAAAAAQAAAAEAAgAAAAEAAAABAAAAAQABAAAAAgAAAAAAAAABAAEAAQAAAAAAAAAAAAEAAAABAAIAAQAAAAAAAQAAAAIAAAACAAIAAAACAAAAAQABAAEAAAADAAMAAQD//wAAAQAAAAAAAAACAAAAAQAAAAEAAAAAAAEAAAABAAEAAgAAAAEAAgABAAEAAAAAAAAAAgABAAAAAAAAAAEAAAAAAAAAAQAAAAEAAAAAAAEAAgABAAAAAQAAAAAAAwACAP//AAABAP//AAAAAAAAAQABAAIAAAAAAAIAAQABAAEAAAABAAMAAAABAAIAAQACAAEAAQACAAEAAAAAAAAAAAAAAAAAAQABAAEAAgABAAIAAQAAAAEAAQACAAIAAQAAAAEAAwAAAP//AAAAAAAAAAABAAEAAAD//wAAAQAAAAEAAQABAAEAAAAAAAAAAAAAAAEAAAAAAAAAAQABAP//AQABAAEAAQAAAAAAAgAAAAAAAQAAAAIAAAAAAAIAAAD//wAAAgAAAP//AQACAAEAAAAAAAIAAAAAAAIAAAAAAAEAAQABAAAAAQAAAAAAAQAAAAIAAAAAAAEAAAACAAAAAQABAAAAAwAAAAAAAAAAAAMAAQAAAAIAAAD//wEAAgACAP//AQABAAAAAQAAAAAAAAAAAAEAAQAAAAEAAgAAAAAAAAAAAAAAAAABAAIAAAAAAAIAAQAAAAAAAAACAAEAAQACAAIAAQAAAAIAAQAAAAMAAAACAAEAAAAAAAAAAgABAAAAAAAAAAAAAgABAAAAAgAAAAAAAgAAAAAAAAAAAAEAAgABAAEAAgABAAAAAgABAAAAAgAAAAAAAQABAAEAAAAAAAAAAAD//wEAAAABAAIAAQACAAEAAAAAAAEAAQACAAAA//8BAAAAAAAAAAEAAAACAAEAAAAAAAEAAQABAAAAAAACAAEAAQAAAAIAAQAAAAAA//8AAAAAAQAAAAAAAQABAP//AQABAAAAAgABAAAAAQACAAEAAQABAAAAAAABAAEA//8BAAEAAAAAAAAAAAAAAAAAAQABAAAA//8AAAAAAAAAAAEAAQADAAEAAAABAAEAAQABAAAAAAABAAEAAAABAAEA//8AAAEAAQABAAEAAAAAAAEAAAACAAAAAAABAAEAAQAAAAEAAQABAAAAAQAAAAEAAAABAAAAAAABAAAAAQD/////AAABAAEAAAABAAEAAAAAAAAAAAAAAAAAAAAAAAIA//8BAAEAAAAAAAAAAAAAAAAAAQACAAAAAgAAAAAAAgAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAgABAAEAAQABAAEA/////wAAAgABAAAA//8AAAIAAgAAAAAAAAAAAAAAAQACAAAAAAABAAAAAQAAAAEAAgABAAIAAAAAAAEAAAABAAAAAAAAAAAAAQAAAAEAAAAAAAIAAAABAAEAAAAAAP//AAABAAEAAAAAAAEAAAAAAAEAAAABAAEAAAABAAEAAAABAAEAAQAAAAAAAAAAAAAAAAABAAAAAAAAAAEAAQABAAEAAgABAAAAAAD/////AQABAAAAAAD//wAAAAAAAAAAAAAAAAEAAQAAAAAAAQAAAP//AAAAAAAA//8AAAEA//8AAAEAAAABAAAAAAAAAAAAAAAAAAIAAQACAAAAAAAAAAAAAAACAAEAAAACAAAAAQAAAAAAAQAAAAEAAQABAAEAAAAAAAAAAQABAAAAAAAAAAAAAgAAAAAAAgAAAAAAAgABAAAAAAAAAAAAAQD//wEAAQAAAAEAAQABAAAAAQAAAAEAAAAAAAAAAAABAAAAAAAAAAIAAQAAAAEAAAADAAEAAQABAAAAAQAAAAAAAQAAAAEAAQAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAQACAAAAAQAAAAAAAQABAAAA//8AAAEAAAAAAAEAAQABAAAAAQABAP//AgACAAEAAgABAAEAAAABAAIAAAAAAAIAAAABAAEAAAABAAAAAAAAAAAAAQABAP////8BAAAAAQAAAAIAAQABAAAAAAABAAAAAAABAAAAAAACAAAAAgAAAAIAAAAAAAEA//8BAAEAAQAAAAEAAQACAAAAAAABAAAAAQABAAAAAAABAAEAAAAAAAAAAAACAAAAAAACAAAAAQD//wEAAAAAAAAAAAACAAAAAAABAAAAAQAAAAAAAQAAAAEA//8AAAEAAQABAAAAAAAAAAAAAAACAAEAAAAAAAEAAQABAAAA//8AAAAAAQAAAAEAAAAAAAEAAAABAAAAAQABAAAAAQACAAIAAAAAAAIAAgAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAQAAAAEAAAACAAEAAAAAAAAAAQAAAAAAAAAAAAEAAgABAAAAAgAAAAAAAgAAAAAAAAD//wEAAgAAAAEAAQAAAAAAAQAAAAAAAgAAAAAAAAAAAAIAAAAAAAAAAQAAAAAAAQABAAAAAQABAAAAAQAAAAAAAQABAAAAAAACAP//AAAAAAAAAgABAAEAAAAAAAEAAQAAAAEAAAAAAAEAAAABAAIAAAAAAAMAAQABAAAAAAAAAAAAAAAAAAEA//8AAAEAAAABAAEAAQAAAP//AQABAAAAAQAAAAAAAwAAAP//AAAAAAEAAAABAAEAAAAAAAEAAAAAAAIAAAABAAAAAAAAAAEAAQAAAAAAAAAAAAEAAQD//wAAAAAAAAAAAQD//wAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAQAAAAEAAQAAAAAAAAAAAAEAAgABAAEAAQAAAP//AQABAAAAAQACAAAAAAAAAAEAAgAAAAIAAQABAAEAAAAAAAAAAAAAAAIAAAAAAAEAAQAAAAAAAQAAAAAAAQABAAAAAQAAAAAAAAAAAAEAAAABAAEAAQABAAAAAQAAAAEAAAAAAAAAAAACAAIAAAAAAAIAAQABAAEAAAACAAAAAAABAAAAAgAAAAAAAgAAAAEAAAABAAEAAAAAAAAAAQAAAAAA//8AAAIAAQABAAAAAAAAAAAAAgABAAAAAAAAAAEAAQACAAEAAQABAAAAAQABAAAAAgAAAAAAAQAAAAEA//8BAAEAAAAAAAEAAQAAAAAAAAACAAAAAQABAAEAAgAAAAAAAAAAAAEAAAAAAAEAAAABAAAAAAAAAAAAAAAAAAAAAQACAAAAAAAAAAIAAAABAAAA//8AAAEAAgAAAAEAAAACAAAAAgAAAAAAAgAAAAAAAAACAAEAAQAAAAAAAAAAAAAA/v8CAAIAAgAAAAAAAAAAAAAAAQADAAAAAAABAAAAAQAAAAAAAQADAAIAAAAAAAAAAgAAAAAAAAABAAEAAQABAP//AAAAAAEAAAABAAEAAQAAAAEAAQAAAAIAAAABAAAAAQABAAAAAQAAAAEAAAAAAAAAAQAAAAAAAQAAAAAAAQACAAAAAgABAAAAAgABAP//AAABAP//AAABAAAAAQABAAIAAAAAAAIAAQABAAEAAQAAAAIAAAABAAIAAQABAAEAAgAAAAAAAAAAAP//AAABAAEAAAABAAEAAQAAAAEAAQAAAAAAAQABAAEAAgAAAAAAAwAAAP//AAAAAAAAAAABAAEAAQAAAAIAAgAAAAEAAAABAAAAAAABAAEAAAAAAAAAAAD/////AgABAAAAAQABAAEAAgAAAAAAAQAAAAAAAgAAAAEAAQAAAAIAAAABAAAAAgAAAAAAAQACAAEAAAAAAAAAAQD//wEAAAAAAAEAAQABAAAAAQD//wAAAgABAAEAAAABAAAAAAABAAAAAQABAAEAAgABAAAAAQABAAIAAQAAAAIAAAAAAAEAAQACAAAAAQABAAAAAgABAAAAAAAAAAEAAAABAAAAAgAAAP//AAAAAAEAAAABAAEAAQAAAAIAAgAAAAAAAAACAAEAAQACAAEAAgABAAEAAQABAAIAAQACAAEAAAABAAEAAgABAAAAAQAAAP//AgABAAEAAgAAAAEAAQAAAAEAAAAAAAEAAgABAAAAAgABAAAAAQABAAAAAgABAAAAAgABAAIAAAAAAAAAAAAAAAEAAAABAAIAAQABAAEAAAAAAAEAAQACAAAA//8BAAAAAAAAAAAAAQADAAEAAAAAAAEAAQABAAEA//8BAAEAAQABAAEAAAAAAAAAAAAAAAAAAQAAAP//AAABAP//AQABAAAAAgAAAAAAAQADAAEAAQABAAAAAQAAAAAAAAABAAEAAAAAAAEAAAAAAAAAAAABAAAAAAABAAAAAQAAAAAAAQABAAIAAAABAAEAAQAAAAAAAAAAAAEAAAACAAEAAAAAAAEAAAABAAAAAAAAAAAAAAACAAEAAAABAAEAAQAAAAIAAAAAAAEAAAABAAIAAAABAAEAAQAAAAAAAQAAAAAAAAACAAAA//8AAAEAAQABAAAAAAABAAAAAAAAAAEAAAAAAAAAAAAAAAAAAQAAAAAAAQABAAEAAAAAAAAAAQAAAP//AQAAAAEAAAAAAAAAAQAAAAAAAgAAAAEAAgABAAEAAAAAAAAAAQAAAAAAAAAAAAEAAAAAAAAAAQAAAAAAAQACAAEAAAABAAAAAQAAAAEAAgACAAIAAAABAAEAAAABAAAAAAAAAP//AAAAAAEAAAABAAIAAAACAAAAAAAAAAAAAAABAAEAAAAAAAEAAAAAAAIAAAAAAAAAAAABAAEAAgACAAAAAQAAAAAAAAAAAAAAAAABAAAAAAAAAAEAAQAAAAEAAQAAAAAAAAAAAP//AgAAAAAAAQAAAAAAAAD/////AQAAAAEAAgABAAAAAQABAP//AAAAAAAAAAABAAEAAAAAAAEAAAAAAAAAAAAAAAAA//8AAAEAAAABAAEAAQAAAAAAAAABAAAAAAACAAEAAQAAAAEAAQABAAEAAQABAAEAAAAAAAAAAAAAAAAAAAAAAAEAAQAAAAAAAgAAAAAAAgABAAAAAAAAAAEAAgAAAAEAAQAAAAEAAQAAAAAAAgAAAAAAAAAAAAEAAAAAAAEAAAD//wIAAQAAAAEAAAADAAAAAQABAAAAAwAAAAAAAQD//wAAAAABAAIAAAABAAAAAQAAAAAAAAAAAAAAAQACAAAAAAD//wEAAQABAAAA//8AAAEAAgAAAAEAAAAAAAAAAQABAP//AgABAAAAAAABAAIAAAABAAAA//8AAAIAAAAAAAEAAAABAAAAAAAAAAAAAQABAAAA//8AAAAAAQD//wEAAQACAAEAAAAAAAAAAQABAAAAAAACAAAAAgAAAAEAAAAAAAEAAAABAAEAAQAAAAIAAAACAAAAAAABAP//AQAAAAAAAAABAAEAAAAAAAEAAAAAAAAA//8CAAAAAQABAAAAAAD//wAAAAACAAEA//8BAAAAAAAAAAAAAQABAAEAAAAAAAEAAQABAAEA//8AAAEAAAABAAEA//8AAAEAAQABAAAA//8AAAAAAQAAAAIAAAAAAAMAAAABAAAAAAAAAAAAAQABAAIAAAAAAAEAAgAAAAEAAAAAAAAAAAABAAAAAAAAAAEAAAAAAAEAAAABAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAQAAAAIAAQAAAAAAAQAAAAAAAQAAAAAAAAAAAAEAAAAAAAAAAAAAAAAA//8BAAEAAQAAAAAAAAAAAAAAAAACAAAAAAACAP//AAAAAAAAAQACAAEAAAAAAAAAAQAAAAAAAAAAAAEAAAABAAEAAAAAAAEAAAABAAAAAAAAAAAAAAAAAAEAAAAAAAEAAQAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAQAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAABAAAAAQAAAAAAAQAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAABAAEAAAAAAAAAAQAAAAEAAAAAAAAAAAAAAAEAAQAAAAAAAgAAAP//AQABAAEAAAABAAEAAAD//wEAAQAAAAIAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAQAAAAAAAQAAAAAAAQAAAAAAAQAAAAAAAAAAAAEAAAAAAAIAAgAAAAAAAQAAAAAAAQABAAAAAAAAAAAAAAAAAAEAAAAAAAAAAQABAAAAAQAAAAAAAgABAP//AAAAAAAAAAABAAAAAAABAAAAAQAAAAAAAAAAAAEAAAAAAAEAAAAAAAAAAAABAAAAAAAAAAAAAQAAAAAAAQABAAAAAAABAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQAAAAAAAAABAAAAAAABAAEAAgABAAEAAQAAAAEAAgACAAEAAQABAAEAAQAAAAAAAQABAAAAAQABAAAAAgAAAAAAAQAAAAEAAAAAAAEAAQABAAEAAgABAAAAAgABAAAAAgABAAAAAQABAAIAAAAAAP//AAAAAAAAAAABAAEAAQABAAAAAAAAAAEAAAACAAAA//8BAAAAAAAAAAAAAQACAAEAAAAAAAEAAgAAAAAAAAAAAAEAAQABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQAAAAEAAQACAAAAAQABAAEAAgAAAAAAAAABAAAAAAAAAAAAAAAAAAEAAAABAAAAAAABAAAAAAABAAAAAAAAAAIAAAABAAEAAAAAAAAAAQD//wAAAAABAAAAAQAAAAAAAQAAAAAAAAAAAAAAAAABAAEAAAABAAIAAQABAAEAAQAAAAEAAAABAAEAAAAAAAEAAQAAAAAAAAAAAAAAAAACAAAAAQAAAAAAAQAAAAEAAQACAAAAAAABAAEAAAABAAAA//8AAAAAAQABAP//AQAAAAAAAQAAAAAAAAAAAAEAAgABAAIAAQAAAAAAAAACAAAAAQAAAAAAAQAAAAAAAAABAAAAAQAAAAEAAAAAAAEAAAABAAAAAgAAAAAAAQABAAIAAAACAAAAAAAAAAAAAQACAAEAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAEAAQACAAAAAQACAAAAAAAAAAAAAAABAAEA//8AAAIAAQABAAIAAAAAAAEAAAABAAEAAQACAAEAAgAAAP//AAAAAAAAAQACAAAAAQAAAAEAAgAAAAIAAQABAAEAAAD//wAAAQABAAAAAAAAAAAAAgAAAAAAAQAAAP//AgAAAAAAAAAAAAAAAQABAAEAAAAAAAEAAQABAAAAAQAAAAAAAAAAAAAAAAABAAEAAAAAAAIAAQAAAAEAAAACAAEAAQABAAIAAAABAAEAAQABAAAAAQABAAEAAAAAAAAAAQAAAP//AAAAAAAAAQACAAAAAgAAAAAAAgABAAAAAAAAAAEAAgABAAEAAQABAAAAAQAAAAAAAgABAAAAAAAAAAEAAAAAAAAAAAAAAAEA//8BAAIAAQACAAEAAQAAAAAAAgADAAAAAAACAP//AAAAAAAAAQADAAEAAAAAAAEAAQABAAAAAAABAAEAAAAAAAIAAAACAAEAAAACAAIAAAAAAAAAAAACAAEAAAABAAIAAwACAAAAAAABAAEAAQAAAAEAAgAAAAAAAQACAAAA//8BAAAAAAAAAAEAAAAAAAAAAgABAP//AQAAAAEAAAAAAAEAAAABAAAAAAAAAAEAAAAAAAAAAAABAAAAAgAAAAAAAgAAAAAAAQABAAEAAQAAAAMAAQABAAAAAQABAP//AQABAP//AAAAAAEAAAAAAAEAAAAAAAAAAQABAAAAAQD//wAAAQAAAAEAAAAAAAEAAAACAAAAAAACAAAAAgABAAAAAQAAAAIAAQAAAAIAAAD//wEAAAABAAAAAAABAP//AQAAAAAAAAAAAAEAAAABAAEAAQAAAAAAAAAAAAEAAQAAAAEAAAABAAEAAgABAAAAAAABAAAAAQACAAIAAQAAAAEAAQAAAAIAAQABAAEAAAAAAAAAAgAAAP//AAAAAAAAAgABAAAAAgAAAAAAAgAAAAAAAQD//wAAAgAAAAEAAgAAAAAAAQABAAAAAQABAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAIAAQACAAEAAAAAAAEAAQABAAAA//8BAAAAAAD//wAAAAACAAEAAAABAAAAAQABAAAAAAACAAEAAQAAAAEAAAAAAAAA//8AAAEAAQAAAAEAAAABAP//AQABAAAAAgABAAAAAAACAAEAAQABAAEAAAAAAAEA//8CAAEAAAAAAAEAAAD//wAAAAABAAAA//8BAAAAAAAAAAAAAQACAAEAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAEA//8AAAEAAAACAAAA/////wAAAAABAAEAAAABAAEAAQABAAEAAAAAAAEAAQACAAEAAQABAAAAAQAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAgD//wAAAQABAAAAAAD//wEAAAABAAAAAAAAAAAAAQD//wAAAQADAP//AQAAAAAAAQD+/wAA//8AAAAAAAAAAAEAAQAAAAAAAgABAAAAAQABAAAAAAAAAAAAAQAAAAEAAAAAAAEAAQACAAAAAAAAAAAAAQABAAEAAAABAAAAAAAAAAAAAQABAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAIAAAACAAAAAAACAAAAAAAAAAAAAAAAAAEA//8AAAIAAAAAAAIAAAAAAAAAAAABAAEAAQABAAEAAgAAAAAA//8AAAAA//8CAAAAAAAAAAEAAgAAAAIAAQAAAAAAAAD//wAAAQAAAAAAAAAAAAAAAQAAAAAAAQAAAP//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CQABAPz/AQD///3//f/2//n//f/1//P/9v/2//X/8v/v//T/9v/w/+z/7//2//D/6f/w//P/7f/t/+//7f/t/+3/7v/t/+n/7f/y/+z/6v/u/+//7//u/+3/7v/v//L/8f/q//D/+P/0/+//8P/2//j/9f/x//f/+f/2//j/+P/6//r/+f/8//3/+//8//3///8AAPr/+/8EAAEA/P8AAP7/AAADAP3/+/8AAAEA/v///////v8BAAEA//////7//v8DAAEA+v/9/wMAAAD7////AAADAAYA/P/+/wgABAAAAAAAAgAHAAYA//8CAAYAAgADAAcABwADAAAACwAIAP//CAAJAAQABQAKAAgABAALAAsACAAGAAYADAAKAAUACQANAAQAAwAMAAYAAQAQABIACQAIAAsADgANAA0ACgANABAACQASABYACgALABIACwAHAA4AEAAMAA4ADgAJAAsADAAQAAkACgAQAAkACQAFAAoACQACAAYAAgADAP///v8FAP7/+v/8//r/9P/6//n/9P/6//D/8P/+//j/8f/3//j/+//4//H/8v/3//X/8P/4//n/9//1//P/+//+//n/+P8AAP7/+//3//b//P8AAP7/9P8AAAEA+f8EAP3//P/+//7/9f8AAAYA8v8AAAcA//8AAAQABQAAAAMA///5/wYAAQD4/wAABAD6/wIABQD+/wYAAgAGAAYABQACAAcACAABAAcAAwADAAQABgAEAAYAAwADAAgAAgAKAAoA+/8KAAsA+/8FAAoABQAGAAgAAwAJAA0A/////wsABQD//wQAAwD+/wgABQABAP7//f8GAAIABAADAAUAAAAJAA0ACQAFAAAACgAAAAIADQAGAP3/CAABAAUACgD8//7/+//+//f/+v/+//f/+P/y//3//f/1//f/AAD9//7/BAD0/wYABQD7////9/8IAAIA9f/9////BAD3//r/9P/1/xIA8f/0/wAA8//z//3/8//3//b/8P8BAO//8//7/wIA9f/5//v/AAAIAPj/5v8HABEA6f/6/wQA+v/y/wMAAwD3//n/AwACAA0A8//+/wUADAANAPP/GQANAPr/8v8MAOr/4v/6/wIA8//z/wIACAAOAAYAEAAbADIA+f8XABMAFQAqAHkA0QAZAW0BxgAfAIQAygBMACIAMABjADkAyv+s/+z/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CADz//v/EAABAPb/AwAEAAEA9P/9/wkABQD///f/CwD6//r/EAD1/wAABQD9//v//v8NAPf//f8CAAMABgD3/wAA/v8IAAAA8v8HAAEAAAD+////BgD7/wMAAgD8//v/CQAFAOz/AQAJAPv/AwAFAPf/AwATAPX/8v8GAPz/BQADAPb/BAAEAAMAAwD6////CQABAPb/+P8DAAQA/f8DAP3/BgAQAP//8//z/wgACgDz//f/CAAKAAMAAgABAPz///8AAP//+//7/wMACAAEAPz/AAAKAAAA9P/8/wYABAD5//v/BgABAAgACgDz////BAD8/wQA9v/5/wkABQADAP3/BwADAPj////y/wMADgAAAPj/+f8QAAMA+v8BAPv//f/6/wMADAD2//f/DQAIAPv/AAD///f//f8IAPv/8v8MAAkAAAD9//v/BgD+////+v/2/wgACAD5//r/CAAIAAAAAAD3//n/BwADAPv/9P/+/xUABgD2//v/BQAKAPz/9//3////DgD9//j/BgAEAAgAAwD1//v///8FAPz/+P8LAAIAAQAGAPz/AgD8/wIAAAD8/wEA+v8KAAAA9f8EAAsACQD2/+//DAAPAO//9v8EAA8A///2/wkA+/8EAAIA9/8IAPX/AgAJAP3////z/woAAgAAAAcA8f8AAAkAAQD+////9v/6/w8ACAD2//f/BwAGAPv/AAABAP7/+f8AAAkA/f/7////AAADAAgA/P/0/wIAAwD9////AwAAAPj/AAAJAAMA+P/4/wUABAD///7/+//+/wIAAwAEAPz/+v8CAAQAAgD9/wAA/P8AAAIAAAACAPz/AAAGAP7//v8CAAEA/P/+/wYAAAD9//7/BQD/////AQD//wQA+P8HAAMA+P8EAP3/BQABAPb/AwAGAAUA+v/+/wYA+v///wcA///1/wYABQABAAEA9/8FAAUA+/8AAAAA/P8AAAQA/v///wEAAwADAP3/AAABAP//+v8AAAQA/P8CAAQAAAD8/wAABQD9//n///8EAAMA/f/9//7/BAACAP//AQD7/wIA/v/+/wMA/f///wUA///7/wAABgABAPb//v8FAAMAAAD8//3/BQABAAEA///5/wQAAgAAAPz///8IAAEA/P/9/wIAAQD9/wMA///7/w=='

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
