import sys
import os
import io
import re
import time
import json
import base64
import wave
import urllib.request
from contextlib import nullcontext
import numpy as np
from collections import deque

# Force UTF-8 on Windows consoles
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import modal

app = modal.App("kilo-voice-clinic")

# Production Container Image with local reference audio baked in
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")
    .pip_install(
        "torch",
        "transformers<4.44",
        "click",
        "faster-whisper",
        "accelerate",
        "sentencepiece",
        "fastapi[standard]",
        "requests",
        "scipy",
        "numpy",
        "nvidia-cublas-cu12",
        "nvidia-cudnn-cu12",
    )
    .env({
        "LD_LIBRARY_PATH": "/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib:/usr/local/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:/usr/local/lib/python3.11/site-packages/nvidia/cuda_nvrtc/lib:$LD_LIBRARY_PATH"
    })
)

# Spoken Hindi receptionist prompt: natural, warm North Indian cadence without canned wording.
CLINIC_SYSTEM_PROMPT = """आप 'शुगरडॉक्टर क्लिनिक' के फोन सहायक हैं। आपकी बोली सहज, गर्मजोशी भरी, और उत्तर भारतीय हिंदी जैसी होनी चाहिए—जैसे कोई समझदार इंसान फोन पर बात करता है, न कि कोई स्क्रिप्ट पढ़ता हुआ रोबोट।
क्लिनिक की महत्वपूर्ण जानकारी:
- मुख्य चिकित्सक: डॉक्टर लोटिका पुरोहित
- समय: सुबह नौ बजे से दोपहर दो बजे तक, और शाम पांच बजे से रात आठ बजे तक (सोमवार से शनिवार, रविवार बंद)
- परामर्श शुल्क: बिल्कुल निशुल्क (मुफ्त परामर्श)

अति-महत्वपूर्ण नियम:
1. देवनागरी हिंदी में बोलें। अंग्रेजी अक्षर न लिखें; जरूरत हो तो परिचित शब्द देवनागरी में लिखें।
2. समय और संख्याओं को केवल हिंदी शब्दों में ही लिखें (जैसे: नौ बजे, दो बजे, पांच बजे, आठ बजे, निशुल्क)। कभी भी अंक (digits जैसे 9:00, 2, 5 आदि) बिल्कुल न लिखें।
3. पहले कॉलर की बात का सीधा जवाब दें। आम तौर पर एक या दो छोटे वाक्य काफी हैं; सवाल के हिसाब से स्वाभाविक रूप से कम-ज्यादा बोलें।
4. बातचीत में हल्की मानवीय गर्मजोशी रखें। जरूरत के मुताबिक कभी "जी", "अच्छा", या "ज़रूर" कहें, मगर हर जवाब में वही तकिया-कलाम न दोहराएँ। प्रश्न को शब्दशः न दोहराएँ और स्वागत वाली तय पंक्ति हर बार न बोलें।
5. एक ही वाक्यांश बार-बार इस्तेमाल न करें। सहज और साफ बोलें, जरूरत से ज्यादा औपचारिक या उत्साही न बनें।
6. हर वाक्य को पूर्ण विराम (।) या प्रश्नवाचक चिह्न (?) पर समाप्त करें।
7. मार्कडाउन, बुलेट या इमोजी न लिखें।
8. अपने बारे में पूछने पर बताएं कि आप क्लिनिक के फोन सहायक हैं। मॉडल या निर्माता का नाम न बताएं।
9. क्लिनिक से बाहर की मांग पर बात न गढ़ें; साफ कहें कि आप क्लिनिक और अपॉइंटमेंट में मदद कर सकते हैं।
10. अपॉइंटमेंट मांगे जाने पर बुकिंग पूरी होने का दावा न करें; नाम और सुविधाजनक समय पूछें।
"""

# Keep conversational inference on the hosted provider. The Modal L4 is reserved
# for Whisper and XTTS so LLM weights cannot contend with speech synthesis VRAM.
VOICE_LLM_PROVIDER = "NVIDIA NIM"
VOICE_LLM_MODEL = "nvidia/nemotron-3-super-120b-a12b"
TTS_DEFAULT_SPEED = 1.2
TTS_MODEL = "magpie-tts-multilingual"
TTS_VOICE = "Magpie-Multilingual.HI-IN.Leo"
TTS_RATE_HZ = 22050
TTS_NVCF_URL = "https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com/v1/audio/synthesize_online"

HINDI_NUMBERS = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पांच",
    6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह",
    16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस",
    26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    31: "इकतीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस",
    36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चवालीस", 45: "पैंतालीस",
    46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन",
    56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ",
    66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर",
    76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उन्नासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी",
    86: "छियासी", 87: "सत्तासी", 88: "अठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे",
    96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे", 100: "सौ"
}

def num_to_hindi(n: int) -> str:
    if n in HINDI_NUMBERS:
        return HINDI_NUMBERS[n]
    return " ".join(HINDI_NUMBERS.get(int(d), d) for d in str(n))

def sanitize_hindi_for_xtts(text: str) -> str:
    if not text:
        return ""
    # Map common English clinic words to pure Devanagari Hindi
    subs = [
        (r"(?i)\bsugardoctor\s*clinic\b", "शुगरडॉक्टर क्लिनिक"),
        (r"(?i)\bsugardoctor\b", "शुगरडॉक्टर"),
        (r"(?i)\bclinic\b", "क्लिनिक"),
        (r"(?i)\bdr\.?\s*lotika\s*purohit\b", "डॉक्टर लोटिका पुरोहित"),
        (r"(?i)\bdr\.?\s*lotika\b", "डॉक्टर लोटिका"),
        (r"(?i)\bdr\.?\b", "डॉक्टर"),
        (r"(?i)\blotika\b", "लोटिका"),
        (r"(?i)\bpurohit\b", "पुरोहित"),
        (r"(?i)\bhello\b", "नमस्ते"),
        (r"(?i)\bhi\b", "नमस्ते"),
        (r"(?i)\bfree\b", "निशुल्क"),
        (r"(?i)\bconsultation\b", "परामर्श"),
        (r"(?i)\bappointment\b", "परामर्श"),
        (r"(?i)\bdoctor\b", "डॉक्टर"),
    ]
    for pat, rep in subs:
        text = re.sub(pat, rep, text)

    # Convert Devanagari digits to ASCII digits
    dev_digits = str.maketrans("०१२३४५६७८९", "0123456789")
    text = text.translate(dev_digits)
    # Expand times like 9:00 -> नौ, 9:30 -> नौ बजकर तीस मिनट
    text = re.sub(r'(\d+):00', lambda m: num_to_hindi(int(m.group(1))), text)
    text = re.sub(r'(\d+):(\d+)', lambda m: num_to_hindi(int(m.group(1))) + " बजकर " + num_to_hindi(int(m.group(2))) + " मिनट", text)
    # Expand all remaining digits to Hindi words (prevents num2words NotImplementedError)
    text = re.sub(r'\b\d+\b', lambda m: num_to_hindi(int(m.group(0))), text)
    text = re.sub(r'\d', lambda m: num_to_hindi(int(m.group(0))), text)

    # Strip any remaining Latin letters (so XTTS is NEVER tricked into English phonemizer / American accent)
    text = re.sub(r"[a-zA-Z]+", "", text)
    # Strip colons, dashes, markdown and noise
    text = re.sub(r'[:\-–—]+', ' ', text)
    text = text.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def provider_api_keys():
    # Modal injects secrets into the serving container, not the local deploy CLI.
    return [k.strip() for k in os.environ.get("NVIDIA_API_KEYS", "").split(",") if k.strip()]

@app.cls(
    gpu="l4",
    image=image,
    scaledown_window=300,  # Keep warm for 5 minutes of idle conversation
    timeout=600,
    secrets=[modal.Secret.from_name("nvidia-voice-inference")],
)
class KiloVoiceService:
    @modal.enter()
    def setup(self):
        import os
        import torch
        from faster_whisper import WhisperModel

        os.environ["COQUI_TOS_AGREED"] = "1"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[MODAL L4] Initializing Kilo Voice Engine on {self.device}...")

        # Preload nvidia cublas/cudnn shared libraries with RTLD_GLOBAL
        import ctypes
        import glob
        for libdir in [
            "/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib",
            "/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib",
            "/usr/local/lib/python3.11/site-packages/nvidia/cuda_runtime/lib",
        ]:
            for so in glob.glob(f"{libdir}/*.so*"):
                try:
                    ctypes.CDLL(so, mode=ctypes.RTLD_GLOBAL)
                except Exception:
                    pass

        # Hindi synthesis uses NVIDIA's Hindi-capable Magpie model through NVCF.
        # XTTS-v2's published language list does not include Hindi; round-trip
        # checks confirmed its streamed Hindi output was frequently unintelligible.
        print(f"[TTS PROVIDER] NVIDIA NIM / {TTS_MODEL} / {TTS_VOICE}", flush=True)

        # Load Faster-Whisper on the Modal L4 with CUDA validation & CPU fallback.
        print("[MODAL L4] Loading Faster-Whisper large-v3-turbo...")
        try:
            self.whisper = WhisperModel("large-v3-turbo", device=self.device, compute_type="float16")
            dummy_pcm = np.zeros(16000, dtype=np.float32)
            list(self.whisper.transcribe(dummy_pcm, beam_size=1)[0])
            print("[MODAL L4] Faster-Whisper on CUDA float16 validated successfully!")
        except Exception as e:
            print(f"[MODAL L4] Faster-Whisper CUDA failed ({e}), falling back to CPU float32...")
            self.whisper = WhisperModel("large-v3-turbo", device="cpu", compute_type="float32")

        # Warm the provider route at boot and fail early if API credentials or
        # Hindi synthesis are unavailable. The phone still owns its instant filler.
        print("[TTS PROVIDER] Running Hindi pre-warm...")
        _warm = self.synthesize_pcm("नमस्ते।", speed=TTS_DEFAULT_SPEED)
        try:
            _pk = int(np.abs(np.frombuffer(_warm, dtype=np.int16)).max()) if _warm else 0
            print(f"[TTS PROVIDER] pre-warm peak={_pk} bytes={len(_warm)}", flush=True)
            if _pk < 3000:
                raise RuntimeError(f"pre-warm audio peak {_pk} is dead - refusing to serve a broken voice")
        except Exception as e:
            print(f"[MODAL L4] PRE-WARM GATE FAILED: {e}", flush=True)
            raise

        # Provider-only inference: NVIDIA hosts both Nemotron text and Magpie TTS;
        # the Modal L4 remains dedicated to Whisper STT.
        self.llm_local = None
        self.llm_local_name = None
        self.sessions = {}
        print(f"[LLM PROVIDER] {VOICE_LLM_PROVIDER} / {VOICE_LLM_MODEL}", flush=True)

        print("[MODAL L4] Warm-up complete! Serverless engine ready.")

    def detect_lang(self, text: str) -> str:
        # HINDI BY DEFAULT LAW (Baba 2026-10-05: voice should be in Hindi)
        t = (text or "").lower()
        if any(s in t for s in ("in english", "speak english", "speak in english")):
            return "en"
        return "hi"

    def llm_stream_clauses(self, user_text: str, history: list = None):
        lang = self.detect_lang(user_text)
        hint = "Reply in simple spoken Hindi, Devanagari script." if lang == "hi" else "Reply in concise spoken English."
        t0 = time.time()
        emitted = 0
        # Stream complete sentences to the Hindi-capable provider TTS. Character slicing mid-sentence was
        # resetting prosody and made the reply sound clipped and robotic.
        for clause in self._llm_api_clauses(user_text, hint, history=history):
            clause = sanitize_hindi_for_xtts(clause)
            if not clause:
                continue
            # Streaming providers can occasionally append an orphan one-character
            # fragment after a complete sentence. Do not voice that fragment.
            if emitted and len(re.sub(r"[^\w\u0900-\u097f]+", "", clause)) <= 1:
                print(f"[LLM PROVIDER TAIL DROPPED] orphan fragment='{clause}'", flush=True)
                continue
            emitted += 1
            if emitted == 1:
                print(f"[LLM PROVIDER FIRST CLAUSE] {int((time.time()-t0)*1000)}ms model={VOICE_LLM_MODEL} text='{clause[:100]}'", flush=True)
            yield clause
        print(f"[LLM PROVIDER STREAM] {time.time()-t0:.2f}s clauses={emitted}", flush=True)

    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None):
        messages = [
            {"role": "system", "content": CLINIC_SYSTEM_PROMPT + "\n" + hint},
        ]
        if history:
            # Latency guard: cap history to last 6 messages (~200 tokens) so prefill latency overhead is <15ms
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": user_text})
        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 90,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        data = json.dumps(payload).encode("utf-8")

        keys = provider_api_keys()
        if not keys:
            raise RuntimeError("Modal secret nvidia-voice-inference must provide NVIDIA_API_KEYS")
        for key in keys:
            buf = ""
            emitted = False
            key_t0 = time.time()
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    first_token = True
                    punct = ("।", ".", "?", "!", "\n", ";")
                    for line in resp:
                        line = line.decode("utf-8", errors="replace").strip()
                        if not line.startswith("data: ") or line[6:].strip() == "[DONE]":
                            continue
                        try:
                            j = json.loads(line[6:])
                            choices = j.get("choices") or []
                            delta = choices[0].get("delta", {}).get("content") or "" if choices else ""
                        except Exception:
                            continue
                        delta = delta.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
                        if not delta:
                            continue
                        if first_token:
                            print(f"[LLM PROVIDER FIRST TOKEN] {int((time.time()-key_t0)*1000)}ms model={VOICE_LLM_MODEL}", flush=True)
                            first_token = False
                        buf += delta
                        while buf:
                            stops = [buf.find(mark) for mark in punct if buf.find(mark) >= 0]
                            if not stops:
                                break
                            cut = min(stops) + 1
                            part, buf = buf[:cut].strip(), buf[cut:].lstrip()
                            if part:
                                emitted = True
                                yield part
                    if buf.strip():
                        part = buf.strip()
                        if part[-1] not in "।.!?":
                            part += "।"
                        emitted = True
                        yield part
                    return
            except Exception as e:
                if emitted:
                    print(f"[LLM PROVIDER PARTIAL] {type(e).__name__}; retaining streamed text without retry", flush=True)
                    if buf.strip():
                        part = buf.strip()
                        if part[-1] not in "।.!?":
                            part += "।"
                        yield part
                    return
                print(f"[LLM STREAM FAIL] {e}, trying next provider key...", flush=True)
                continue

        if user_text and self.detect_lang(user_text) == "hi":
            yield "नमस्ते! मैं डॉक्टर लोटिका के क्लिनिक से बोल रहा हूँ।"
            yield "बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
        else:
            yield "Hello, this is Sugardoctor Clinic. How can I help you today?"

    def trim_sil(self, a, sr=24000, lead_ms=25, tail_ms=80):
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

    def collapse_silence(self, arr, sr=24000, frame_ms=10, quiet_pct=0.08, keep_ms=70, min_run_ms=120):
        """Frame-based RMS silence collapse: cuts long dead pauses between words down to 70ms."""
        if arr.size == 0:
            return arr, 0.0
        frame_len = int(sr * frame_ms / 1000)
        num_frames = len(arr) // frame_len
        if num_frames == 0:
            return arr, 0.0

        rms = np.array([np.sqrt(np.mean(arr[i*frame_len:(i+1)*frame_len]**2)) for i in range(num_frames)])
        peak_rms = float(np.max(rms)) or 1.0
        thresh = quiet_pct * peak_rms

        quiet_frames = rms < thresh
        keep_frames = max(int(keep_ms / frame_ms), 1)

        out_frames = []
        run_len = 0

        for idx, q in enumerate(quiet_frames):
            chunk = arr[idx*frame_len : (idx+1)*frame_len]
            if q:
                run_len += 1
                if run_len <= keep_frames:
                    out_frames.append(chunk)
            else:
                run_len = 0
                out_frames.append(chunk)

        if num_frames * frame_len < len(arr):
            out_frames.append(arr[num_frames * frame_len:])

        res = np.concatenate(out_frames)
        removed_s = (len(arr) - len(res)) / float(sr)
        return res, removed_s

    def synthesize_pcm(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", postprocess: bool = True,
        collapse_pauses: bool = False, temperature: float = 0.65,
    ) -> bytes:
        chunks = list(self.synthesize_pcm_stream(text, speed=speed))
        pcm = b"".join(chunks)
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        if postprocess and samples.size:
            samples = self.trim_sil(samples, 24000, lead_ms=20, tail_ms=60)
        if collapse_pauses and samples.size:
            samples, _ = self.collapse_silence(samples, 24000, frame_ms=10,
                                                quiet_pct=0.08, keep_ms=180, min_run_ms=300)
        out = np.clip(samples, -1.0, 1.0)
        result = (out * 32767.0).astype(np.int16).tobytes()
        duration = len(result) / 48000.0
        print(f"[NVIDIA MAGPIE TTS] wall_pcm={duration:.2f}s bytes={len(result)} "
              f"speed={speed:.2f} provider={TTS_MODEL} voice={TTS_VOICE}", flush=True)
        return result

    def synthesize_pcm_stream(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", stream_chunk_size: int = 10,
        temperature: float = 0.65,
    ):
        """Stream Hindi LPCM from NVIDIA Magpie and apply pitch-preserving tempo."""
        import subprocess
        import threading
        import uuid

        if not text or not text.strip():
            return
        lang = self.detect_lang(text)
        if lang == "hi":
            clean_text = sanitize_hindi_for_xtts(text)
            language_code = "hi-IN"
            voice = TTS_VOICE
        else:
            clean_text = text.strip()
            language_code = "en-US"
            voice = "Magpie-Multilingual.EN-US.Leo"
        if clean_text[-1] not in "।.!?":
            clean_text += "।" if language_code == "hi-IN" else "."
        speed = min(1.5, max(0.8, float(speed)))
        boundary = "----KiloVoice" + uuid.uuid4().hex
        fields = {
            "text": clean_text,
            "language": language_code,
            "voice": voice,
            "encoding": "LINEAR_PCM",
            "sample_rate_hz": str(TTS_RATE_HZ),
        }
        multipart = bytearray()
        for name, value in fields.items():
            multipart.extend((f"--{boundary}\r\n"
                              f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                              f"{value}\r\n").encode("utf-8"))
        multipart.extend(f"--{boundary}--\r\n".encode("ascii"))
        keys = provider_api_keys()
        if not keys:
            raise RuntimeError("Modal secret nvidia-voice-inference must provide NVIDIA_API_KEYS")

        response = None
        errors = []
        for key in keys:
            req = urllib.request.Request(
                TTS_NVCF_URL,
                data=bytes(multipart),
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Accept": "audio/pcm",
                },
                method="POST",
            )
            try:
                response = urllib.request.urlopen(req, timeout=45)
                break
            except Exception as exc:
                code = getattr(exc, "code", "network")
                errors.append(str(code))
        if response is None:
            raise RuntimeError("NVIDIA Magpie TTS request failed across provider keys: "
                               + ",".join(errors))

        # The NVIDIA endpoint streams signed 16-bit mono LPCM at 22.05 kHz.
        # ffmpeg's atempo filter applies the requested pace while preserving
        # pitch, then resamples to the phone's existing 24 kHz PCM contract.
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "s16le", "-ar", str(TTS_RATE_HZ), "-ac", "1", "-i", "pipe:0",
            "-af", f"atempo={speed:.4f}", "-ar", "24000", "-ac", "1",
            "-f", "s16le", "pipe:1",
        ]
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, bufsize=0)
        pump_error = []
        provider_bytes = 0

        def pump_provider():
            nonlocal provider_bytes
            try:
                with response:
                    while True:
                        part = response.read(4096)
                        if not part:
                            break
                        provider_bytes += len(part)
                        proc.stdin.write(part)
                        proc.stdin.flush()
            except Exception as exc:
                pump_error.append(exc)
            finally:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

        pump = threading.Thread(target=pump_provider, name="magpie-provider-stream", daemon=True)
        t0 = time.time()
        pump.start()
        output_bytes = 0
        first_ms = None
        stream_completed = False
        try:
            while True:
                part = proc.stdout.read(8192)
                if not part:
                    stream_completed = True
                    break
                output_bytes += len(part)
                if first_ms is None:
                    first_ms = int((time.time() - t0) * 1000)
                    print(f"[NVIDIA MAGPIE FIRST PCM] {first_ms}ms voice={voice} "
                          f"lang={language_code} tempo={speed:.2f}", flush=True)
                yield part
        finally:
            if not stream_completed:
                try:
                    response.close()
                except Exception:
                    pass
                if proc.poll() is None:
                    proc.kill()
            pump.join(timeout=10)
            if proc.poll() is None:
                proc.wait(timeout=10)
        stderr = proc.stderr.read().decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 or output_bytes == 0:
            detail = stderr or (str(pump_error[0]) if pump_error else "no output")
            raise RuntimeError(f"Magpie/ffmpeg synthesis failed: {detail[:300]}")
        audio_s = output_bytes / 48000.0
        wall_ms = int((time.time() - t0) * 1000)
        print(f"[NVIDIA MAGPIE STREAM] wall={wall_ms}ms provider_bytes={provider_bytes} "
              f"audio={audio_s:.2f}s out_bytes={output_bytes} speed={speed:.2f}", flush=True)

    @modal.asgi_app()
    def web(self):
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, StreamingResponse

        web_app = FastAPI(title="Kilo Voice Clinic - Modal L4 Production")

        self.turn_events = deque(maxlen=25)
        self.last_audio = b""  # AUDIO EVIDENCE (2026-10-05): keep the most recent
        # uploaded utterance in memory so the house can pull exactly what the seat
        # heard. This is what settles "phone sends good audio vs phone sends noise".

        def turn_event(**kw):
            ev = {
                "ts": time.strftime("%H:%M:%S", time.localtime()),
                "llm_provider": VOICE_LLM_PROVIDER,
                "llm_model": VOICE_LLM_MODEL,
            }
            ev.update(kw)
            self.turn_events.append(ev)

        @web_app.get("/lastturns")
        def lastturns():
            return json.dumps(list(self.turn_events))

        @web_app.get("/last_audio")
        def last_audio():
            from fastapi.responses import Response
            return Response(content=self.last_audio, media_type="audio/wav")

        @web_app.get("/health")
        def health():
            return {
                "ok": True,
                "engine": "kilo-voice-modal-l4-whisper-nvidia-tts",
                "gpu": "NVIDIA L4 (Whisper STT)",
                "stt_device": str(self.device),
                "voice": TTS_VOICE,
                "speed": TTS_DEFAULT_SPEED,
                "llm_local": self.llm_local_name,
                "llm_provider": VOICE_LLM_PROVIDER,
                "llm_model": VOICE_LLM_MODEL,
                "tts_provider": "NVIDIA NIM",
                "tts_model": TTS_MODEL,
                "tts_voice": TTS_VOICE,
                "tts_stream_api": True,
                "tts_output_sample_rate_hz": 24000,
                "tts_tempo_pitch_preserving": TTS_DEFAULT_SPEED,
                "phone_local_filler_bytes": 0,
                "phone_local_greeting": False,
                "stt_language_mode": "Whisper auto-detect unless explicit hi/en",
                "conversation_cache": True,
                "active_sessions": len(getattr(self, "sessions", {})),
            }

        @web_app.post("/say")
        async def say(req: Request):
            data = await req.json()
            text = data.get("text", "")
            speed = float(data.get("speed", TTS_DEFAULT_SPEED))
            # Keep accepting legacy probe fields while the phone transitions to Magpie.
            precision = str(data.get("precision", "provider"))
            postprocess = bool(data.get("postprocess", True))
            collapse_pauses = bool(data.get("collapse_pauses", False))
            speed = min(1.5, max(0.8, speed))
            if not text:
                return JSONResponse({"error": "No text provided"}, status_code=400)
            
            t0 = time.time()
            pcm = self.synthesize_pcm(text, speed, precision=precision, postprocess=postprocess,
                                      collapse_pauses=collapse_pauses)
            gen_ms = int((time.time() - t0) * 1000)
            audio_s = len(pcm) / 2 / 24000
            rtf = gen_ms / 1000.0 / max(audio_s, 0.01)

            return StreamingResponse(
                io.BytesIO(pcm),
                media_type="audio/pcm",
                headers={
                    "X-Gen-Ms": str(gen_ms),
                    "X-Sample-Rate": "24000",
                    "X-Channels": "1",
                    "X-Audio-Duration-S": f"{audio_s:.3f}",
                    "X-RTF": f"{rtf:.3f}",
                    "X-TTS-Speed": str(speed),
                    "X-TTS-Provider": "NVIDIA NIM",
                    "X-TTS-Model": TTS_MODEL,
                    "X-TTS-Voice": TTS_VOICE,
                    "X-TTS-Postprocess": str(postprocess).lower(),
                    "X-TTS-Trim-Edges": str(postprocess).lower(),
                    "X-TTS-Collapse-Pauses": str(collapse_pauses).lower(),
                }
            )

        @web_app.post("/turn")
        async def turn(req: Request):
            import re
            t_turn0 = time.time()
            content_type = req.headers.get("content-type", "")
            no_fill = req.query_params.get("no_fill", "0") == "1"
            try:
                turn_speed = float(req.query_params.get("speed", TTS_DEFAULT_SPEED))
            except ValueError:
                turn_speed = TTS_DEFAULT_SPEED
            turn_speed = min(1.5, max(0.8, turn_speed))
            src = req.headers.get("user-agent", "?")[:40]

            body = await req.body()
            user_audio_bytes = b""
            if "json" in content_type:
                try:
                    j = json.loads(body.decode("utf-8"))
                    audio_b64 = j.get("b64") or j.get("audio_b64") or ""
                    user_audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
                    direct_text = (j.get("text", "") or j.get("user_text", "")).strip()
                except Exception as e:
                    print(f"[TURN JSON ERR] {e}")
                    direct_text = ""
            else:
                user_audio_bytes = body
                direct_text = ""

            # SESSION & CALL IDENTIFICATION (Twilio CallSid or client session)
            j_dict = j if ("json" in content_type and "j" in locals() and isinstance(j, dict)) else {}
            session_id = (
                req.headers.get("X-Call-Sid") or
                req.headers.get("X-Twilio-CallSid") or
                req.headers.get("X-Session-ID") or
                req.headers.get("X-Caller-ID") or
                req.query_params.get("CallSid") or
                req.query_params.get("call_sid") or
                req.query_params.get("session_id") or
                req.query_params.get("caller") or
                j_dict.get("call_sid") or
                j_dict.get("session_id") or
                (getattr(req.client, "host", None) if hasattr(req, "client") and req.client else "default_session")
            )
            reset_session = req.query_params.get("reset", "0") == "1" or j_dict.get("reset") is True

            now = time.time()
            if not hasattr(self, "sessions"):
                self.sessions = {}
            stale_keys = [k for k, v in self.sessions.items() if now - v.get("last_seen", 0) > 600]
            for k in stale_keys:
                self.sessions.pop(k, None)

            if reset_session or session_id not in self.sessions:
                self.sessions[session_id] = {"history": [], "last_seen": now}

            sess = self.sessions[session_id]
            # 5-minute idle timeout: clear history for a new phone call
            if now - sess.get("last_seen", 0) > 300:
                sess["history"] = []
            sess["last_seen"] = now
            session_history = list(sess.get("history", []))

            # STT
            user_text = direct_text
            stt_ms = 0
            if user_audio_bytes:
                t_stt0 = time.time()
                try:
                    with wave.open(io.BytesIO(user_audio_bytes), "rb") as wf:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        sr = wf.getframerate()
                        frames = wf.readframes(wf.getnframes())
                    
                    if sampwidth == 2:
                        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    else:
                        samples = np.frombuffer(frames, dtype=np.float32)
                    if channels > 1:
                        samples = samples.reshape(-1, channels).mean(axis=1)
                    
                    if sr != 16000:
                        from scipy.signal import resample
                        target_len = int(len(samples) * 16000 / sr)
                        samples = resample(samples, target_len).astype(np.float32)
                    else:
                        samples = np.ascontiguousarray(samples, dtype=np.float32)

                    # DIGITAL AGC (Baba 2026-10-05): Normalize incoming audio to boost faint phone mics
                    max_amp = float(np.abs(samples).max()) if len(samples) else 0.0
                    if 0.0025 <= max_amp < 0.6:
                        # AEC/NS can leave detected handset speech below 2.5% full scale.
                        # Boost it before Whisper, retaining VAD and transcript noise gates.
                        gain = min(12.0, 0.65 / max_amp)
                        samples = np.ascontiguousarray(samples * gain, dtype=np.float32)

                    # Auto-detect language (supports both Hindi and English naturally)
                    j_lang = j.get("lang", "") if ("json" in content_type and "j" in locals() and isinstance(j, dict)) else ""
                    req_lang = (req.headers.get("X-Voice-Lang", "") or req.query_params.get("lang", "") or j_lang).strip().lower()
                    # Respect explicit overrides; auto means Whisper actually detects the
                    # spoken language. The old code forced every non-English request to hi,
                    # which damaged short English/Hinglish utterances from the phone.
                    if req_lang in ("hi", "hi-in", "hindi"):
                        whisper_lang = "hi"
                    elif req_lang in ("en", "en-us", "english"):
                        whisper_lang = "en"
                    else:
                        whisper_lang = None

                    # STT QUALITY (RCA-1 fix #2, Baba 2026-10-05): beam_size=1 (greedy)
                    # invents words on accented Hinglish ("वेगारी", "प्रूट" receipts).
                    # beam 5 gives real alternatives. The initial_prompt biases Hindi
                    # decoding toward clinic vocabulary instead of Bengali phonetics.
                    _stt_kw = dict(
                        beam_size=5,
                        vad_filter=False,
                        without_timestamps=True,
                        condition_on_previous_text=False,
                        temperature=0.0,
                        repetition_penalty=1.2,
                        no_repeat_ngram_size=3,
                        initial_prompt=(
                            "नमस्ते, हेलो। डॉक्टर, क्लिनिक, अपॉइंटमेंट, टाइमिंग।"
                            if whisper_lang == "hi" else None
                        ),
                    )

                    segments, info = self.whisper.transcribe(
                        samples,
                        language=whisper_lang,
                        **_stt_kw
                    )
                    user_text = " ".join([s.text for s in segments]).strip()
                    det_l = getattr(info, "language", "")
                    det_prob = getattr(info, "language_probability", None)
                    has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in user_text)
                    # bn = Bengali (Baba's mother tongue leaks into auto-detect and Whisper
                    # then outputs Bengali phonetics in Devanagari = "gibberish" Hindi).
                    if (det_l in ("ur", "mr", "ne", "pa", "bn") or has_arabic) and whisper_lang != "en":
                        # re-transcribe forced to clean Hindi Devanagari
                        segments, info = self.whisper.transcribe(
                            samples,
                            language="hi",
                            **_stt_kw
                        )
                        user_text = " ".join([s.text for s in segments]).strip()
                        det_l = getattr(info, "language", "hi")
                        det_prob = getattr(info, "language_probability", None)
                except Exception as e:
                    print(f"[TURN STT ERR] {e}", flush=True)
                    det_l = "error"
                    det_prob = None
            else:
                det_l = "text"
                det_prob = None
            if user_audio_bytes:
                stt_ms = int((time.time() - t_stt0) * 1000)

            # AUDIO RECEIPT (2026-10-05): "Whisper hears 'you'" can mean two very
            # different faults - a bad model, or a near-silent upload. Log the actual
            # signal level so the question is answered by measurement, not guesswork.
            sig_dur = sig_peak = sig_rms = 0
            try:
                if user_audio_bytes:
                    # keep this utterance for the /last_audio evidence lane (bounded)
                    self.last_audio = user_audio_bytes[:320044]
                    with wave.open(io.BytesIO(user_audio_bytes), "rb") as wf:
                        _ch = wf.getnchannels(); _sr = wf.getframerate(); _sw = wf.getsampwidth()
                        _fr = wf.readframes(wf.getnframes())
                    if _sw == 2:
                        _a = np.frombuffer(_fr, dtype=np.int16).astype(np.float32)
                        if _ch > 1:
                            _a = _a.reshape(-1, _ch).mean(axis=1)
                        sig_dur = round(len(_a) / max(_sr, 1), 2)
                        sig_peak = int(np.abs(_a).max()) if len(_a) else 0
                        sig_rms = int(np.sqrt(((_a ** 2).mean()))) if len(_a) else 0
            except Exception as _e:
                print(f"[SIG ERR] {_e}", flush=True)

            print(f"[TURN RECEIVED] src={src} bytes={len(user_audio_bytes)} dur={sig_dur}s peak={sig_peak} rms={sig_rms} | STT: {stt_ms}ms | Heard: '{user_text}' | LLM_local={bool(self.llm_local)}", flush=True)

            greetings = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "प्रणाम", "हाय", "hi", "सुनिए", "हाँ", "हा", "ji", "जी"}

            def is_hallucination(text):
                t = (text or "").lower()
                # 1. Any Cyrillic/Russian character is an automatic Whisper hallucination on noise
                if any("\u0400" <= ch <= "\u04FF" for ch in t):
                    return True
                clean = re.sub(r"[^\w\u0900-\u097f]+", " ", t)
                toks = [w for w in clean.split() if w]
                if not toks:
                    return True

                # WHITELIST: Greetings and affirmations must NEVER be flagged as hallucinations!
                if set(toks).issubset(greetings) or any(w in greetings for w in toks):
                    return False

                # 2. English & noise words that Whisper emits on background hum/noise or speaker bleed
                noise_words = {
                    "you", "oh", "i", "the", "a", "an", "to", "it", "thank", "thanks", "bye",
                    "झाल", "झाला", "झाली", "झाले", "क्लिका", "कळिका", "टिक", "हूँ", "हूं"
                }
                if len(toks) == 1 and toks[0] in noise_words:
                    return True
                if len(toks) == 2 and (
                    set(toks).issubset({"thank", "you"}) or
                    set(toks).issubset({"कर", "दो"}) or
                    set(toks).issubset({"टिक", "टिक"}) or
                    all(w in noise_words for w in toks)
                ):
                    return True

                # 3. Repeated single token hallucination (e.g. "you you you...")
                collapsed = [toks[0]]
                for w in toks[1:]:
                    if w != collapsed[-1]:
                        collapsed.append(w)
                if len(collapsed) == 1 and len(toks) > 2:
                    return True
                if len(toks) >= 6 and len(set(toks)) <= 2:
                    return True
                if len(toks) >= 8 and len(set(toks)) / float(len(toks)) < 0.3:
                    return True
                return False

            # keep what Whisper REALLY heard for the receipt (before the gate edits it)
            heard_raw = user_text

            drop_reason = ""
            if is_hallucination(user_text):
                drop_reason = "whisper_noise_or_hallucination"
                user_text = ""
            elif user_audio_bytes and sig_peak < 100 and user_text:
                clean = re.sub(r"[^\w\u0900-\u097f]+", " ", user_text.lower())
                toks = [w for w in clean.split() if w]
                if not any(w in greetings for w in toks):
                    drop_reason = "low_signal_peak"
                    print(f"[TURN DROPPED] sig_peak={sig_peak} below speech threshold (100), dropping transcript.", flush=True)
                    user_text = ""

            # ECHO GUARD: Only suppress if caller's audio is an echo of our own outgoing sentence
            _echo = False
            _heard_l = (user_text or "").lower().strip()
            if _heard_l and len(_heard_l) >= 8:
                try:
                    for _r in list(getattr(self, "_recent_replies", [])):
                        _rl = (_r or "").lower().strip()
                        if _rl and (_heard_l in _rl or _rl in _heard_l):
                            _echo = True
                            break
                except Exception:
                    _echo = False

            if _echo:
                print(f"[TURN ECHO] own audio came back as '{user_text}' - refusing to answer it.", flush=True)
                turn_event(src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                           heard=heard_raw, reply="", echo=True,
                           llm_local=self.llm_local_name)

                async def echo_stream():
                    hdr = json.dumps({"cid": "turn", "heard": heard_raw,
                                      "stt_ms": stt_ms, "sr": 24000,
                                      "echo": True}) + "\n"
                    yield hdr.encode("utf-8")
                    trailer = json.dumps({"end": True, "heard": heard_raw,
                                          "reply": "", "echo": True,
                                          "stt_ms": stt_ms,
                                          "total_ms": int((time.time() - t_turn0) * 1000)}) + "\n"
                    yield trailer.encode("utf-8")

                return StreamingResponse(
                    echo_stream(), media_type="application/octet-stream",
                    headers={"X-Sample-Rate": "24000", "X-Channels": "1"})

            if not user_text:
                # If the handset has already captured a speech-length segment with
                # measurable energy, a Whisper noise/hallucination rejection must
                # not become silent dead air. Ask for one repeat in the same Magpie
                # voice. Truly empty/very quiet or sub-second uploads remain silent;
                # echo turns are handled by the separate echo guard above.
                if not drop_reason:
                    drop_reason = "empty_transcript"
                clarify = bool(user_audio_bytes) and sig_dur >= 0.9 and sig_peak >= 180 and sig_rms >= 24
                if clarify:
                    clarify_text = "माफ़ कीजिए, आपकी आवाज़ साफ़ नहीं आई। कृपया एक बार फिर कहिए।"
                    print(f"[TURN CLARIFY] reason={drop_reason} dur={sig_dur}s peak={sig_peak} rms={sig_rms}", flush=True)

                    async def clarify_stream():
                        import asyncio
                        t_clarify = time.time()
                        hdr = json.dumps({"cid": "turn", "heard": heard_raw, "stt_ms": stt_ms,
                                          "sr": 24000, "clarification": True}) + "\n"
                        yield hdr.encode("utf-8")
                        pcm = b""
                        try:
                            pcm = await asyncio.to_thread(self.synthesize_pcm, clarify_text, turn_speed)
                            if pcm:
                                if not hasattr(self, "_recent_replies"):
                                    self._recent_replies = deque(maxlen=5)
                                self._recent_replies.append(clarify_text)
                                yield pcm
                        except Exception as e:
                            print(f"[TURN CLARIFY TTS FAIL] {type(e).__name__}: {e}", flush=True)
                        total_ms = int((time.time() - t_turn0) * 1000)
                        first_pcm_ms = int((time.time() - t_clarify) * 1000) if pcm else None
                        turn_event(src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                                   heard=heard_raw, reply=clarify_text if pcm else "",
                                   clarification=True, empty=not bool(pcm), drop_reason=drop_reason,
                                   signal_peak=sig_peak, signal_rms=sig_rms,
                                   first_pcm_ms=first_pcm_ms, total_ms=total_ms,
                                   llm_local=self.llm_local_name, tts_speed=turn_speed)
                        trailer = json.dumps({"end": True, "heard": heard_raw,
                                              "reply": clarify_text if pcm else "",
                                              "clarification": True, "empty": not bool(pcm),
                                              "first_pcm_ms": first_pcm_ms, "stt_ms": stt_ms,
                                              "total_ms": total_ms}) + "\n"
                        yield trailer.encode("utf-8")

                    return StreamingResponse(
                        clarify_stream(), media_type="application/octet-stream",
                        headers={"X-Sample-Rate": "24000", "X-Channels": "1",
                                 "X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

                print(f"[TURN DROPPED] empty/quiet segment raw='{heard_raw}' dur={sig_dur}s peak={sig_peak} rms={sig_rms}; no clarification audio", flush=True)
                turn_event(src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                           heard=heard_raw, reply="", empty=True, drop_reason=drop_reason,
                           signal_peak=sig_peak, signal_rms=sig_rms, signal_duration=sig_dur,
                           llm_local=self.llm_local_name)

                async def empty_stream():
                    hdr = json.dumps({"cid": "turn", "heard": heard_raw, "stt_ms": stt_ms,
                                      "sr": 24000, "empty": True, "drop_reason": drop_reason}) + "\n"
                    yield hdr.encode("utf-8")
                    trailer = json.dumps({"end": True, "heard": heard_raw, "reply": "", "empty": True,
                                          "drop_reason": drop_reason}) + "\n"
                    yield trailer.encode("utf-8")

                return StreamingResponse(
                    empty_stream(), media_type="application/octet-stream",
                    headers={"X-Sample-Rate": "24000", "X-Channels": "1"})

            # FAST GREETING PATH (<600ms feel latency):
            # If caller says "hello", "hello hello", "नमस्ते", respond immediately with warm Hindi clinic greeting.
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\w\u0900-\u097f]+", " ", user_text.lower()).split())
            if clean_user_toks and clean_user_toks.issubset({"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}):
                is_pure_greeting = True

            async def stream_generator():
                import asyncio
                import queue
                import threading

                async def stream_tts(text):
                    pieces = queue.Queue(maxsize=2)
                    stopped = threading.Event()
                    finished = object()

                    def put_item(item):
                        while not stopped.is_set():
                            try:
                                pieces.put(item, timeout=0.1)
                                return True
                            except queue.Full:
                                continue
                        return False

                    def produce():
                        try:
                            for pcm_part in self.synthesize_pcm_stream(text, speed=turn_speed):
                                if not put_item(pcm_part):
                                    return
                        except Exception as e:
                            put_item(e)
                        finally:
                            put_item(finished)

                    worker = threading.Thread(target=produce, daemon=True)
                    worker.start()
                    try:
                        while True:
                            item = await asyncio.to_thread(pieces.get)
                            if item is finished:
                                break
                            if isinstance(item, Exception):
                                raise item
                            yield item
                    finally:
                        stopped.set()

                # 1. Header line for BridgeService
                hdr = json.dumps({"cid": "turn", "heard": user_text, "stt_ms": stt_ms, "sr": 24000}) + "\n"
                yield hdr.encode("utf-8")
                await asyncio.sleep(0.001)

                # 2. Pipelined clause streaming: as clauses are ready, synthesize & yield immediately
                total_spoken = []
                t_first_pcm = None

                if is_pure_greeting:
                    fast_pieces = [
                        "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                    ]
                    for fast_clause in fast_pieces:
                        total_spoken.append(fast_clause)
                        async for pcm in stream_tts(fast_clause):
                            if not pcm:
                                continue
                            if t_first_pcm is None:
                                t_first_pcm = int((time.time() - t_turn0) * 1000)
                                print(f"[STREAM FIRST AUDIO FAST GREETING] {t_first_pcm}ms | Piece: '{fast_clause}'", flush=True)
                            yield pcm
                            await asyncio.sleep(0.001)
                else:
                    for clause in self.llm_stream_clauses(user_text, history=session_history):
                        clause_clean = clause.strip()
                        if not clause_clean:
                            continue
                        total_spoken.append(clause_clean)
                        async for pcm in stream_tts(clause_clean):
                            if not pcm:
                                continue
                            if t_first_pcm is None:
                                t_first_pcm = int((time.time() - t_turn0) * 1000)
                                print(f"[STREAM FIRST AUDIO] {t_first_pcm}ms | Piece: '{clause_clean}'", flush=True)
                            yield pcm
                            await asyncio.sleep(0.001)

                full_reply = " ".join(total_spoken)
                if not hasattr(self, "_recent_replies"):
                    self._recent_replies = deque(maxlen=5)
                if full_reply:
                    self._recent_replies.append(full_reply)
                    sess["history"].append({"role": "user", "content": user_text})
                    sess["history"].append({"role": "assistant", "content": full_reply})
                    # Sliding window: keep max 8 messages (4 user-assistant pairs) to protect latency
                    sess["history"] = sess["history"][-8:]
                    sess["last_seen"] = time.time()

                total_ms = int((time.time() - t_turn0) * 1000)
                turn_event(
                    src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                    heard=user_text, reply=full_reply,
                    first_pcm_ms=t_first_pcm or total_ms, total_ms=total_ms,
                    llm_local=self.llm_local_name, tts_speed=turn_speed,
                    stt_language=det_l, stt_language_probability=det_prob,
                )
                trailer = json.dumps({
                    "end": True,
                    "heard": user_text,
                    "reply": full_reply,
                    "first_pcm_ms": t_first_pcm or total_ms,
                    "stt_ms": stt_ms,
                    "total_ms": total_ms,
                    "session_id": str(session_id),
                    "history_turns": len(sess.get("history", [])) // 2,
                }) + "\n"
                yield trailer.encode("utf-8")

            return StreamingResponse(
                stream_generator(),
                media_type="application/octet-stream",
                headers={
                    "X-Sample-Rate": "24000",
                    "X-Channels": "1",
                    "X-Accel-Buffering": "no",
                    "Cache-Control": "no-cache"
                }
            )

        return web_app
