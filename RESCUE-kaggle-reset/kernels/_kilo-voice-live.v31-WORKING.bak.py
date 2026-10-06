# %% [code]
# KILO-VOICE-LIVE v1 — attended call engine: pre-warm father-xtts on a T4, poll the relay for LIVE_CALL orders,
# stream chunk wavs home, log per-chunk latency to latency_log.jsonl, auto-kill when idle so Kaggle quota stops.
# Law 15: hardware gate first. HEAVY WORK LAW: synthesis never touches the laptop. DEVA LAW: bn has no XTTS lane - hi-deva IS Baba's tongue.
import os, re, io, glob, json, time, base64, shutil, subprocess, sys, urllib.request, urllib.parse

RELAY_URL = os.environ.get("RELAY_URL", "https://kennedy-til-defend-artistic.trycloudflare.com")
RELAY_FALLBACKS = [c.strip() for c in os.environ.get("RELAY_FALLBACKS", "https://retrain-schnapps-upbeat.ngrok-free.dev").split(",") if c.strip()]
RELAY_TOKEN = os.environ.get("RELAY_TOKEN", "GOLD24")
SELF_BODY = os.environ.get("SELF_BODY", "LIVE-VOX1")
OUT_BODY = os.environ.get("OUT_BODY", "KILO")
VOICE_REF = os.environ.get("VOICE_REF", "father.wav")
# NOTE: plain LANGUAGE is a Linux locale variable (Kaggle sets it to "en_US"), so it must not be used here.
LANGUAGE = os.environ.get("KILO_LANG", "hi")
POLL_SEC = int(os.environ.get("POLL_SEC", "2"))
HEARTBEAT_EVERY = int(os.environ.get("HEARTBEAT_EVERY", "3"))
# Heartbeat by time, not by poll count: at POLL_SEC=2 a beat every 3 polls would flood the relay
# channel (30 rows) and push live chunks out of the read window.
HEARTBEAT_SEC = int(os.environ.get("HEARTBEAT_SEC", "60"))
IDLE_KILL_MIN = float(os.environ.get("IDLE_KILL_MIN", "10"))
HARD_CAP_MIN = float(os.environ.get("HARD_CAP_MIN", "120"))
GPT_COND_LEN = float(os.environ.get("GPT_COND_LEN", "10"))
GPT_MAX_NEW = int(os.environ.get("GPT_MAX_NEW", "500"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.4"))
WARM_UP = os.environ.get("WARM_UP", "1") == "1"
# XTTS-v2 per-language text limits (coqui warns/truncates above these; hi is 150, en is 250)
MAX_CHARS_HI = int(os.environ.get("MAX_CHARS_HI", "140"))
MAX_CHARS_EN = int(os.environ.get("MAX_CHARS_EN", "240"))
CHUNK_B64 = 50000
# v28: FULL per-piece synthesis is the default (see stream_chunks). Xtts.inference_stream() cuts
# audio into ~0.9 s fixed slices and roughly half of them end mid-word (measured: tail RMS
# 0.10-0.26). Playing a slice as its own file makes every turn truncate abruptly. "stream" keeps
# the old behaviour for experiments only.
SYNTH_MODE = os.environ.get("SYNTH_MODE", "full")
STT_ON = os.environ.get("STT_ON", "1") == "1"
STT_MODEL = os.environ.get("STT_MODEL", "small")
STT_BEAM = int(os.environ.get("STT_BEAM", "1"))
HDRS = {"User-Agent": "kilo-voice-live", "ngrok-skip-browser-warning": "1"}
WORK = "/kaggle/working"
LAT_LOG = WORK + "/latency_log.jsonl"


def doors():
    return [RELAY_URL] + RELAY_FALLBACKS


DOOR = None


def gate():
    global DOOR
    for c in doors():
        try:
            req = urllib.request.Request(c + "/health?token=" + urllib.parse.quote(RELAY_TOKEN), headers=HDRS)
            r = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
            if r.get("ok"):
                DOOR = c
                return c
        except Exception:
            pass
    return None


def say(text, body=OUT_BODY, retries=2):
    global DOOR
    data = json.dumps({"body": body, "text": text}).encode()
    for i in range(retries):
        if DOOR is None and gate() is None:
            time.sleep(5)
            continue
        try:
            req = urllib.request.Request(DOOR + "/say?token=" + urllib.parse.quote(RELAY_TOKEN), data=data, headers=HDRS)
            urllib.request.urlopen(req, timeout=60).read()
            return True
        except Exception:
            DOOR = None
            time.sleep(5)
    return False


def prog(msg):
    print(msg, flush=True)
    say("LIVE " + msg)


def report(text, body=None, retries=2):
    """Seat -> laptop reports go on /hear (reports channel), not /say (orders channel).
    ensure_ascii keeps the wire pure ASCII; the laptop's json.loads restores Devanagari."""
    global DOOR
    data = json.dumps({"body": body or SELF_BODY, "text": text}).encode()
    for i in range(retries):
        if DOOR is None and gate() is None:
            time.sleep(5)
            continue
        try:
            req = urllib.request.Request(DOOR + "/hear?token=" + urllib.parse.quote(RELAY_TOKEN),
                                         data=data, headers=HDRS)
            urllib.request.urlopen(req, timeout=60).read()
            return True
        except Exception:
            DOOR = None
            time.sleep(5)
    return False


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
prog("nvidia-smi: " + smi.replace("\n", " | "))
import torch as _gate
_names = [_gate.cuda.get_device_name(i) for i in range(_gate.cuda.device_count())]
assert _gate.cuda.device_count() >= 1 and all("T4" in n.upper() for n in _names), \
    f"HARDWARE GATE FAIL: expected T4, got {_names}"
prog(f"GATE PASS: {_names}")


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
if not pre_cfg_path:
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
m.cuda()
# m.half()  # disabled - causes dtype mismatch with inference_stream
m.eval()
prog("model loaded fp32")

# ref audio
ref = None
if VOICE_REF:
    stem = os.path.splitext(os.path.basename(VOICE_REF))[0]
    hits = glob.glob(f"/kaggle/input/**/{stem}*.wav", recursive=True)
    ref = hits[0] if hits else None
if ref is None:
    meta_hi_hits = [p for p in glob.glob("/kaggle/input/**/metadata_hi.csv", recursive=True) if "father" in p]
    if meta_hi_hits:
        first = None
        for line in open(meta_hi_hits[0], encoding="utf-8"):
            if "|" in line:
                first = os.path.basename(line.split("|", 1)[0])
                break
        if first:
            stem = os.path.splitext(first)[0]
            hits = glob.glob(f"/kaggle/input/**/{stem}*.wav", recursive=True)
            ref = hits[0] if hits else None
if ref is None:
    hits = glob.glob("/kaggle/input/**/windows/*.wav", recursive=True)
    ref = hits[0] if hits else None
if ref is None:
    say("LIVE NO REF WAV")
    sys.exit(3)
prog(f"ref={ref}")
gpt_cond_latent, speaker_embedding = m.get_conditioning_latents(audio_path=[ref])
prog("conditioning latents ready")

import numpy as np
import soundfile as sf

SR = int(getattr(pre_cfg, "output_sample_rate", 24000) or 24000)


def log_lat(rec):
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LAT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def _wavbuf(arr, sr):
    buf = io.BytesIO()
    sf.write(buf, arr, sr, format="WAV")
    return buf.getvalue()


# ---------- 3. text prep: Hindi numbers + splitting ----------
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


def split_text(text, max_chars):
    """Split text into pieces <= max_chars: sentence boundaries first (. ! ? । ॥),
    then commas/spaces for over-long sentences, then pack pieces back together."""
    text = (text or "").strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?।॥])\s+", text)
    pieces = []
    for s in sentences:
        s = s.strip()
        while len(s) > max_chars:
            cut = max(s.rfind(",", 0, max_chars), s.rfind(" ", 0, max_chars))
            if cut <= 0:
                cut = max_chars - 1
            pieces.append(s[:cut + 1].strip())
            s = s[cut + 1:].strip()
        if s:
            pieces.append(s)
    chunks, current = [], ""
    for p in pieces:
        if current and len(current) + len(p) + 1 > max_chars:
            chunks.append(current)
            current = p
        else:
            current = (current + " " + p) if current else p
    if current:
        chunks.append(current)
    return chunks


def stream_chunks(text, lang, cond_len):
    """Yield the audio for ONE text piece.

    SYNTH_MODE=full (default): Xtts.inference() synthesizes the piece COMPLETE, ending in
    silence -- one group per piece, so the laptop plays whole sentences, never fragments.
    SYNTH_MODE=stream: the old inference_stream() path, kept for experiments.
    """
    if SYNTH_MODE == "full":
        out = m.inference(text, lang, gpt_cond_latent=gpt_cond_latent,
                          speaker_embedding=speaker_embedding, temperature=TEMPERATURE)
        wav = out["wav"] if isinstance(out, dict) else out
        return iter([np.asarray(wav).squeeze()])
    # Xtts.inference_stream yields ONE audio tensor per chunk (not a (chunk, sr) tuple).
    return m.inference_stream(text, lang, gpt_cond_latent=gpt_cond_latent,
                              speaker_embedding=speaker_embedding,
                              temperature=TEMPERATURE)


def stream_chunks_long(text, lang, cond_len):
    """Prep text, split to the language's char limit, stream each piece through XTTS, yield audio tensors."""
    if lang == "hi":
        text = hi_numbers(text)
    limit = char_limit(lang)
    pieces = split_text(text, limit) or [text[:limit]]
    print(f"stream_chunks_long: {len(pieces)} pieces for {len(text)} chars (limit {limit})", flush=True)  # print only: no relay call mid-stream
    for piece in pieces:
        for audio in stream_chunks(piece, lang, cond_len):
            yield audio


if WARM_UP:
    tw = time.time()
    nw = 0
    for _ch in stream_chunks("फ़ादर, योर सन।", "hi", 6):
        nw += 1
    wm = int((time.time() - tw) * 1000)
    log_lat({"type": "warmup", "chunks": nw, "ms": wm})
    prog(f"warmup ok chunks={nw} ms={wm}")


# ---------- 4. STT on the T4: the listening leg (v14) ----------
# The laptop CPU transcribes at 5x-15x real time (measured), which makes a live loop impossible.
# The GPU here is already paid for and idle between calls, so Whisper runs on the seat instead.
whisper = None
if STT_ON:
    try:
        import faster_whisper  # noqa
    except Exception:
        pip("faster-whisper")
    try:
        from faster_whisper import WhisperModel
        t_stt = time.time()
        whisper = WhisperModel(STT_MODEL, device="cuda", compute_type="float16")
        _stt_ms = int((time.time() - t_stt) * 1000)
        log_lat({"type": "stt_load", "model": STT_MODEL, "ms": _stt_ms})
        report(f"STT_READY {STT_MODEL} cuda/float16 load_ms={_stt_ms}")
    except Exception as e:
        whisper = None
        report(f"STT_FAIL load {type(e).__name__}: {str(e)[:140]}")
else:
    report("STT_OFF")


# ---------- 5. relay conversation: orders in (LIVE_CALL/LIVE_END), chunks out (LIVE_CHUNK/LIVE_DONE) ----------
# LIVE-READ (v30, 2026-10-02): a HEAR order carries a base64 WAV (~426 KB text), so the LIVE-VOX1
# channel reached 8,246,888 bytes in 44 rows. This loop polls every POLL_SEC (2 s), so the seat was
# re-downloading all of it on every poll over a PUBLIC tunnel -- measured 12-13 s/poll against
# POLL_SEC=2, and one honest public fetch died with IncompleteRead having read only 1.18 MB. live=1
# makes the relay serve each big row ONCE per (reader, body); small rows (LIVE_CHUNK is 50 KB text)
# keep repeating, so chunk discovery never depends on an ack. READER_ID is per boot, so two live
# seats can never starve each other's turn.
READER_ID = "seat-" + str(int(time.time())) + "-" + str(os.getpid())


def orders(limit=60):
    global DOOR
    if DOOR is None and gate() is None:
        return []
    try:
        q = (f"/say?token={urllib.parse.quote(RELAY_TOKEN)}&body={urllib.parse.quote(SELF_BODY)}"
             f"&limit={limit}&live=1&reader={urllib.parse.quote(READER_ID)}")
        r = json.loads(urllib.request.urlopen(urllib.request.Request(DOOR + q, headers=HDRS), timeout=30).read().decode())
        return r.get("orders", [])
    except Exception:
        DOOR = None
        return []


def norm_lang(lang):
    return "en" if (lang or "").lower().split("-")[0].split("_")[0] == "en" else "hi"


def do_call(cid, text, lang):
    lang = norm_lang(lang)
    t_call = time.time()
    idx = 0
    first_ms = None
    total_b = 0
    try:
        it = stream_chunks_long(text, lang, GPT_COND_LEN)
        while True:
            t_prev = time.time()
            try:
                chunk = next(it)
            except StopIteration:
                break
            sr = SR
            gen_ms = int((time.time() - t_prev) * 1000)
            if first_ms is None:
                first_ms = int((time.time() - t_call) * 1000)
            if hasattr(chunk, "float"):
                arr = chunk.float().cpu().numpy().squeeze()
            else:
                arr = np.asarray(chunk).squeeze()
            buf = _wavbuf(arr, int(sr))
            b64 = base64.b64encode(buf).decode()
            total_b += len(buf)
            idx += 1
            marks = [b64[i:i + CHUNK_B64] for i in range(0, len(b64), CHUNK_B64)]
            for k, mk in enumerate(marks):
                say(f"LIVE_CHUNK {cid} {idx:03d}-{k + 1:02d}/{len(marks)}:{mk}")
            log_lat({"type": "chunk", "cid": cid, "chunk": idx, "lang": lang, "chars": len(text),
                     "audio_s": round(len(arr) / max(int(sr), 1), 2), "gen_ms": gen_ms,
                     "cum_ms": int((time.time() - t_call) * 1000), "first_ms": first_ms, "wav_b": len(buf)})
    except Exception as e:
        detail = (str(e) or repr(e))[:120]
        where = _where(e)
        prog(f"CALL FAIL {cid} {type(e).__name__}: {detail} @{where}")
        log_lat({"type": "call_fail", "cid": cid, "err": detail, "where": where})
        say(f"LIVE_FAIL {cid} {type(e).__name__} @{where}")
        return
    log_lat({"type": "call", "cid": cid, "lang": lang, "chars": len(text), "chunks": idx,
             "first_ms": first_ms, "total_ms": int((time.time() - t_call) * 1000), "b64_b": total_b})
    say(f"LIVE_DONE {cid} chunks={idx} first_ms={first_ms} total_ms={int((time.time() - t_call) * 1000)} - play on laptop, live call lane")


def stt_lang(lang):
    """Whisper wants a real language code ('bn' is valid for whisper even though XTTS has no bn lane).
    lang='auto' -> None -> let Whisper detect."""
    s = (lang or "").strip().lower().split("-")[0].split("_")[0]
    if s == "auto":
        return None
    return s if len(s) == 2 else LANGUAGE


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
    if sr != 16000:
        try:
            from scipy.signal import resample_poly
            from math import gcd
            g = gcd(int(sr), 16000)
            a = resample_poly(a, 16000 // g, sr // g)
        except Exception:
            n = int(len(a) * 16000 / sr)
            a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a)
    return np.ascontiguousarray(a, dtype=np.float32)


def do_hear(otxt):
    """HEAR {"cid":..,"lang":..,"b64":<16000 Hz mono 16-bit wav>} -> transcribe on the T4
    -> HEARD {"cid":..,"text":..,"ms":..} report on /hear. ensure_ascii keeps Devanagari intact."""
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
        path = f"{WORK}/hear_{cid}.wav"
        with open(path, "wb") as fh:
            fh.write(raw)
        if whisper is None:
            report(json.dumps({"cid": cid, "text": "", "err": "stt_unavailable"}, ensure_ascii=True))
            return
        segs, _info = whisper.transcribe(wav_to_16k(raw), language=slang, beam_size=STT_BEAM,
                                         vad_filter=False)
        text = " ".join(s.text for s in segs).strip()
        STT_COUNT += 1
        ms = int((time.time() - t0) * 1000)
        log_lat({"type": "stt", "cid": cid, "lang": slang, "audio_s": round(len(raw) / 32000.0, 2),
                 "ms": ms, "chars": len(text)})
        report(json.dumps({"cid": cid, "text": text, "ms": ms, "lang": slang}, ensure_ascii=True))
    except Exception as e:
        report(json.dumps({"cid": cid, "text": "", "err": type(e).__name__ + ": " + str(e)[:100]},
                          ensure_ascii=True))


def bye(reason):
    up = int(time.time() - T0)
    log_lat({"type": "session", "reason": reason, "gpu_s": up, "calls": CALLS})
    say(f"LIVE_BYE {reason} gpu_s={up} calls={CALLS}")
    print(f"BYE {reason} gpu_s={up} calls={CALLS}", flush=True)
    sys.exit(0)


T0 = time.time()
last_job = T0
last_beat = T0
CALLS = 0
seen = set()
baseline = True   # first poll silences history: never re-synthesize orders from earlier sessions
beats = 0
print(f"WARM body={SELF_BODY} poll={POLL_SEC}s", flush=True)
prog(f"WARM body={SELF_BODY} poll={POLL_SEC}s idle_kill={IDLE_KILL_MIN}m cap={HARD_CAP_MIN}m lang={LANGUAGE} ref={os.path.basename(ref)}")
print("WARM", flush=True)

while True:
    print(f"POLL loop iteration {beats + 1}", flush=True)
    now = time.time()
    if now - T0 > HARD_CAP_MIN * 60:
        bye("HARD_CAP")
    for o in orders():
        key = str(o.get("at", "")) + "|" + str(o.get("text", ""))
        if key in seen:
            continue
        seen.add(key)
        if baseline:
            continue
        otxt = o.get("text", "") or ""
        if otxt.startswith("HEAR"):
            do_hear(otxt)
            last_job = time.time()
            continue
        if otxt.startswith("LIVE_END"):
            bye("RELAY_END")
        if not otxt.startswith("LIVE_CALL"):
            continue
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
        prog(f"CALL {cid} len={len(ctext)} lang={norm_lang(lang)}")
        do_call(cid, ctext, lang)
        last_job = time.time()
    if baseline:
        baseline = False
        prog(f"BASELINE done: {len(seen)} historical orders silenced")
    if time.time() - last_job >= IDLE_KILL_MIN * 60:
        bye("IDLE_KILL")
    beats += 1
    if time.time() - last_beat >= HEARTBEAT_SEC:
        last_beat = time.time()
        beat = f"LIVE_BEAT up={int(time.time() - T0)}s idle={int(time.time() - last_job)}s gpu_s={int(time.time() - T0)} polls={beats}"
        print(beat, flush=True)
        say(beat)
    time.sleep(POLL_SEC)
# v13 Baba run: Hindi digit spelling (num2words has no hi), hi limit 140, KILO_LANG env, failure location in relay msgs
# v14: STT on the T4 (faster-whisper). Laptop CPU measured 4.9x-15.4x real time, which forbids a live loop;
#      the GPU is already paid for and idle between calls. New order HEAR {cid,lang,b64} -> HEARD {cid,text,ms} report.
# v24: first poll now silences history (baseline flag) - the seat used to re-synthesize every historical
#      LIVE_CALL on boot, burning ~5 min of GPU quota per session.
# v25: do_hear decodes WAVs itself and passes a 16k array. Every HEAR used to die with
#      "TypeError: open() got an unexpected keyword argument 'metadata_errors'" (seat PyAV older
#      than faster-whisper expects), so the STT lane had never actually transcribed anything.
# v28: SYNTH_MODE=full (default) -- each text piece is synthesized COMPLETE with Xtts.inference()
#      instead of inference_stream(). Measured on 8 streamed slices of a demo line: every slice
#      was 0.89-0.93 s and half of them ended mid-word (tail RMS 0.10-0.26). The laptop played
#      slices as separate files, so each turn ended abruptly mid-word (Baba's report, 2026-10-02).
#      One complete WAV per piece = whole sentences on the phone, natural endings, no fragments.
# v29: SELF_BODY default moved to LIVE-VOX1. Pushing a new kernel version does NOT stop the running
#      session at once, so the old seat kept polling and BOTH seats answered cid live-v28-t1 --
#      v28's complete 9-part piece and v27's 0.9 s slices landed under the same group numbers
#      (001-05/9 vs 003-01/2). A seat now only hears orders on its own channel, so a stale seat
#      from any earlier version is silent by construction.
#      Door: the ngrok static domain began answering 403 at 2026-10-02 22:17Z (agent still joining,
#      edge refusing), which silenced both seats with no crash report -- a seat that cannot reach
#      the relay cannot even report that it is blind. RELAY_URL is now the fresh cloudflared quick
#      tunnel to :8777 and the ngrok domain is the fallback, per the LIFELINE LAW (tunnel failproof).
# v30: orders() polls with live=1 + a per-boot READER_ID. Verified against the live relay: the
#      LIVE-VOX1 read fell from 8,524,299 b (45 rows) to 422,294 b on the first poll (24 stale big
#      rows dropped, backlog cleared in one cycle) and 148,578 b (20 rows) at steady state -- 57x
#      smaller, so the seat's poll is no longer the slowest part of a turn. The relay keeps big rows
#      for readers that do not pass live=1 (the laptop rehearsal lane is untouched, still 45 rows).