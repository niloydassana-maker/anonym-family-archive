import sys
import os
import io
import time
import json
import base64
import wave
import urllib.request
import numpy as np

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
        "torchaudio",
        "torchcodec",
        "transformers<4.44",
        "click",
        "coqui-tts",
        "faster-whisper",
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
    .add_local_file(
        r"D:\anonym\RESCUE-kaggle-reset\dataset-pull\clinic_reference.wav",
        remote_path="/root/clinic_reference.wav",
    )
    .add_local_file(
        r"D:\anonym\ji_ek_minat.wav",
        remote_path="/root/ji_ek_minat.wav",
    )
)

# Intelligent Voice Assistant Prompt
CLINIC_SYSTEM_PROMPT = """ROLE: You are Kilo, an intelligent and helpful voice assistant speaking on a live phone call.
When asked about Sugardoctor Clinic, you answer as the professional receptionist: Doctor is Dr. Lotika Purohit, Timings are 9:00 AM to 2:00 PM and 5:00 PM to 8:00 PM (Closed Sundays), Consultation is free.
When the caller asks any question, directly answer what was asked concisely, accurately, and politely in 1 to 2 short sentences.
LANGUAGE:
If the caller speaks in Hindi, reply in clear spoken Hindi (Devanagari script only, male verb forms).
If the caller speaks in English, reply in natural, concise English.
STYLE:
Directly answer the caller's specific question in 1 to 2 short sentences (maximum 20 words).
Never use bullet points, markdown, or emojis.
"""

NV_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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"
]

@app.cls(
    gpu="l4",
    image=image,
    scaledown_window=300,  # Keep warm for 5 minutes of idle conversation
    timeout=600,
)
class KiloVoiceService:
    @modal.enter()
    def setup(self):
        import os
        import torch
        from TTS.api import TTS
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

        # 1. Reference voice baked in image
        self.ref_path = "/root/clinic_reference.wav"

        # 2. Extract PCM bytes from baked filler WAV
        with wave.open("/root/ji_ek_minat.wav", "rb") as wf:
            self.filler_pcm = wf.readframes(wf.getnframes())

        # 3. Load XTTS-v2
        print("[MODAL L4] Loading XTTS-v2 model...")
        self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to(self.device)

        # 4. Load Faster-Whisper with CUDA validation & CPU fallback
        print("[MODAL L4] Loading Faster-Whisper large-v3-turbo...")
        try:
            self.whisper = WhisperModel("large-v3-turbo", device=self.device, compute_type="float16")
            dummy_pcm = np.zeros(16000, dtype=np.float32)
            list(self.whisper.transcribe(dummy_pcm, beam_size=1)[0])
            print("[MODAL L4] Faster-Whisper on CUDA float16 validated successfully!")
        except Exception as e:
            print(f"[MODAL L4] Faster-Whisper CUDA failed ({e}), falling back to CPU float32...")
            self.whisper = WhisperModel("large-v3-turbo", device="cpu", compute_type="float32")

        # 5. Pre-warm run
        print("[MODAL L4] Running pre-warm inference...")
        self.tts.tts_to_file(
            text="नमस्ते।",
            speaker_wav=self.ref_path,
            language="hi",
            file_path="/tmp/warmup.wav",
            speed=1.35
        )
        print("[MODAL L4] Warm-up complete! Serverless engine ready.")

    def detect_lang(self, text: str) -> str:
        has_devanagari = any("\u0900" <= ch <= "\u097F" for ch in text)
        return "hi" if has_devanagari else "en"

    def llm_stream_clauses(self, user_text: str):
        lang = self.detect_lang(user_text)
        hint = "Reply in simple spoken Hindi, Devanagari script." if lang == "hi" else "Reply in concise spoken English."
        messages = [
            {"role": "system", "content": CLINIC_SYSTEM_PROMPT + "\n" + hint},
            {"role": "user", "content": user_text}
        ]
        payload = {
            "model": "meta/llama-3.2-11b-vision-instruct",
            "messages": messages,
            "max_tokens": 50,
            "temperature": 0.2,
            "stream": True
        }
        data = json.dumps(payload).encode("utf-8")

        for key in NV_KEYS:
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    buf = ""
                    punct = {"।", ".", "?", "!", "\n"}
                    for line in resp:
                        line = line.decode("utf-8", errors="replace").strip()
                        if line.startswith("data: ") and not line.endswith("[DONE]"):
                            try:
                                j = json.loads(line[6:])
                                delta = j["choices"][0]["delta"].get("content") or ""
                                delta = delta.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
                                buf += delta
                                if any(p in buf for p in punct) or ("," in buf and len(buf) >= 20) or len(buf) >= 35:
                                    part = buf.strip()
                                    if part:
                                        yield part
                                    buf = ""
                            except Exception:
                                pass
                    if buf.strip():
                        yield buf.strip()
                    return
            except Exception as e:
                print(f"[LLM STREAM FAIL] {e}, trying next key...")
                continue

        # Fallback
        if lang == "en":
            yield "Hello, this is Sugardoctor Clinic. How can I help you today?"
        else:
            yield "नमस्ते! मैं डॉक्टर लोटिका के क्लिनिक से बोल रहा हूँ।"
            yield "बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"

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

    def synthesize_pcm(self, text: str, speed: float = 1.35) -> bytes:
        lang = self.detect_lang(text)
        out_wav = f"/tmp/synth_{int(time.time()*1000)}.wav"
        clean_text = text.replace("*", "").replace("#", "").strip()
        if not clean_text:
            return b""
        self.tts.tts_to_file(
            text=clean_text,
            speaker_wav=self.ref_path,
            language=lang,
            file_path=out_wav,
            speed=speed
        )
        with wave.open(out_wav, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sr = wf.getframerate()
        try:
            os.remove(out_wav)
        except Exception:
            pass

        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        samples = self.trim_sil(samples, sr, lead_ms=25, tail_ms=80)
        samples, _ = self.collapse_silence(samples, sr, frame_ms=10, quiet_pct=0.08, keep_ms=70, min_run_ms=120)

        samples = np.clip(samples, -1.0, 1.0)
        pcm = (samples * 32767.0).astype(np.int16).tobytes()
        return pcm

    @modal.asgi_app()
    def web(self):
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, StreamingResponse

        web_app = FastAPI(title="Kilo Voice Clinic - Modal L4 Production")

        @web_app.get("/health")
        def health():
            return {
                "ok": True,
                "engine": "kilo-voice-modal-l4",
                "gpu": "NVIDIA L4 (24GB Ada Lovelace)",
                "voice": "deep_male_clinic_133hz",
                "speed": 1.35,
                "filler_bytes": len(self.filler_pcm)
            }

        @web_app.post("/say")
        async def say(req: Request):
            data = await req.json()
            text = data.get("text", "")
            speed = float(data.get("speed", 1.35))
            if not text:
                return JSONResponse({"error": "No text provided"}, status_code=400)
            
            t0 = time.time()
            pcm = self.synthesize_pcm(text, speed)
            gen_ms = int((time.time() - t0) * 1000)

            return StreamingResponse(
                io.BytesIO(pcm),
                media_type="audio/pcm",
                headers={
                    "X-Gen-Ms": str(gen_ms),
                    "X-Sample-Rate": "24000",
                    "X-Channels": "1"
                }
            )

        @web_app.post("/turn")
        async def turn(req: Request):
            t_turn0 = time.time()
            content_type = req.headers.get("content-type", "")
            no_fill = req.query_params.get("no_fill", "0") == "1"

            body = await req.body()
            user_audio_bytes = b""
            if "json" in content_type:
                try:
                    j = json.loads(body.decode("utf-8"))
                    audio_b64 = j.get("b64") or j.get("audio_b64") or ""
                    user_audio_bytes = base64.b64decode(audio_b64)
                except Exception as e:
                    print(f"[TURN JSON ERR] {e}")
            else:
                user_audio_bytes = body

            # STT
            user_text = ""
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

                    # Auto-detect language (supports both Hindi and English naturally)
                    j_lang = j.get("lang", "") if ("json" in content_type and "j" in locals() and isinstance(j, dict)) else ""
                    req_lang = (req.headers.get("X-Voice-Lang", "") or req.query_params.get("lang", "") or j_lang).strip().lower()
                    whisper_lang = req_lang if req_lang in ("hi", "en") else None

                    segments, info = self.whisper.transcribe(
                        samples,
                        beam_size=1,
                        language=whisper_lang,
                        vad_filter=False,
                        without_timestamps=True,
                        condition_on_previous_text=False,
                        temperature=0.0,
                        repetition_penalty=1.2,
                        no_repeat_ngram_size=3,
                        initial_prompt=None
                    )
                    user_text = " ".join([s.text for s in segments]).strip()
                    det_l = getattr(info, "language", "")
                    has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in user_text)
                    if det_l in ("ur", "mr", "ne", "pa") or has_arabic:
                        # Auto-detected South Asian speech in Urdu/Arabic script -> re-transcribe in clean Hindi Devanagari
                        segments, info = self.whisper.transcribe(
                            samples,
                            beam_size=1,
                            language="hi",
                            vad_filter=False,
                            without_timestamps=True,
                            condition_on_previous_text=False,
                            temperature=0.0,
                            repetition_penalty=1.2,
                            no_repeat_ngram_size=3,
                            initial_prompt=None
                        )
                        user_text = " ".join([s.text for s in segments]).strip()
                except Exception as e:
                    print(f"[TURN STT ERR] {e}", flush=True)
                stt_ms = int((time.time() - t_stt0) * 1000)

            print(f"[TURN RECEIVED] Audio bytes: {len(user_audio_bytes)} | STT: {stt_ms}ms | Heard: '{user_text}'", flush=True)

            def is_hallucination(text):
                t = (text or "").lower()
                import re
                t = re.sub(r"[^\w\u0900-\u097f]+", " ", t)
                toks = [w for w in t.split() if w]
                if not toks:
                    return True
                if len(toks) == 1:
                    common_valid = {"hello", "hi", "hey", "नमस्ते", "नमस्कार", "सुनिए", "डॉक्टर", "डॉ", "doctor", "help", "मदद", "हाँ", "नहीं", "yes", "no", "ok", "okay"}
                    return toks[0] not in common_valid
                collapsed = [toks[0]]
                for w in toks[1:]:
                    if w != collapsed[-1]:
                        collapsed.append(w)
                if len(collapsed) == 1:
                    return True
                if len(toks) >= 6 and len(set(toks)) <= 2:
                    return True
                if len(toks) >= 8 and len(set(toks)) / float(len(toks)) < 0.3:
                    return True
                return False

            if is_hallucination(user_text):
                user_text = ""

            if not user_text:
                print("[TURN DROPPED] Empty or noise utterance, returning empty.", flush=True)
                async def empty_stream():
                    hdr = json.dumps({"cid": "turn", "heard": "", "stt_ms": stt_ms, "sr": 24000, "empty": True}) + "\n"
                    yield hdr.encode("utf-8")
                    trailer = json.dumps({"end": True, "heard": "", "reply": "", "empty": True}) + "\n"
                    yield trailer.encode("utf-8")
                return StreamingResponse(empty_stream(), media_type="application/octet-stream")

            async def stream_generator():
                import asyncio
                # 1. Header line for BridgeService
                hdr = json.dumps({"cid": "turn", "heard": user_text, "stt_ms": stt_ms, "sr": 24000}) + "\n"
                yield hdr.encode("utf-8")
                await asyncio.sleep(0.001)

                # 2. Pipelined clause streaming: as LLM emits clauses, synthesize & yield immediately
                total_spoken = []
                t_first_pcm = None
                for clause in self.llm_stream_clauses(user_text):
                    clause_clean = clause.strip()
                    if not clause_clean:
                        continue
                    total_spoken.append(clause_clean)
                    pcm = self.synthesize_pcm(clause_clean, speed=1.35)
                    if pcm:
                        if t_first_pcm is None:
                            t_first_pcm = int((time.time() - t_turn0) * 1000)
                            print(f"[STREAM FIRST AUDIO] {t_first_pcm}ms | Piece: '{clause_clean}'", flush=True)
                        yield pcm
                        await asyncio.sleep(0.001)

                full_reply = " ".join(total_spoken)
                total_ms = int((time.time() - t_turn0) * 1000)
                trailer = json.dumps({
                    "end": True,
                    "heard": user_text,
                    "reply": full_reply,
                    "first_pcm_ms": t_first_pcm or total_ms,
                    "stt_ms": stt_ms,
                    "total_ms": total_ms
                }) + "\n"
                yield trailer.encode("utf-8")

            return StreamingResponse(
                stream_generator(),
                media_type="application/octet-stream",
                headers={
                    "X-Sample-Rate": "24000",
                    "X-Channels": "1"
                }
            )

        return web_app
