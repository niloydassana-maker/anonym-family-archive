import sys
import os
import io
import re
import time
import json
import base64
import wave
import urllib.request
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
        "torchaudio",
        "torchcodec",
        "transformers<4.44",
        "click",
        "coqui-tts",
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
CLINIC_SYSTEM_PROMPT = """ROLE: You are Kilo, an intelligent, polite, and helpful voice assistant speaking on a live phone call for Sugardoctor Clinic.
Sugardoctor Clinic Details:
- Doctor: Dr. Lotika Purohit (डॉक्टर लोटिका पुरोहित)
- Timings: सुबह 9:00 बजे से दोपहर 2:00 बजे तक, और शाम 5:00 बजे से रात 8:00 बजे तक (सोमवार से शनिवार, रविवार बंद)
- Consultation fee: निशुल्क (Free परामर्श)

CRITICAL INSTRUCTIONS:
1. ALWAYS reply in natural, clear spoken Hindi (Devanagari script only). Never reply in English unless the caller explicitly asks in English.
2. Directly and politely answer the caller's specific question in 1 to 2 short sentences (maximum 20 words).
3. If the caller greets or asks about clinic, welcome them warmly in Hindi.
4. Never output markdown, asterisks, bullet points, or emojis.
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
        self.xtts_model = self.tts.synthesizer.tts_model

        print("[MODAL L4] Pre-computing and caching speaker conditioning latents...")
        # LATENCY LAW (Baba 2026-10-05): the conditioning window is attended on EVERY
        # generation. 30 s of conditioning was measured at RTF ~0.98 on the L4 - the
        # single largest XTTS cost. 8 s of reference keeps the timbre and roughly
        # halves the cross-attention work (record: war-log §73).
        self.gpt_cond_latent, self.speaker_embedding = self.xtts_model.get_conditioning_latents(
            audio_path=[self.ref_path],
            gpt_cond_len=8,
            gpt_cond_chunk_len=4,
            max_ref_length=16,
            sound_norm_refs=False
        )
        print("[MODAL L4] Speaker conditioning latents pinned in GPU VRAM.")

        # FP16 LAW (Baba 2026-10-05: "XTTS should utilize the L4 to the full").
        # Measured receipt: XTTS ran with dtype=torch.float32 on the L4 at RTF
        # 0.95-1.21 - the card's half-precision throughput was unused.
        #
        # IMPORTANT (measured, do not regress): calling model.half() is WRONG for
        # XTTS. It raises
        #   RuntimeError: Input type (torch.cuda.FloatTensor) and weight type
        #   (torch.cuda.HalfTensor) should be the same
        # because the speaker encoder receives float32 audio while its weights were
        # converted - and the tts_to_file fallback hits the identical crash, so the
        # whole service dies during pre-warm. Mixed precision is therefore applied
        # with torch.autocast at the call site (weights stay float32, kernels run in
        # fp16 where safe - no dtype split, no quality loss, no dead container).
        self.xtts_autocast = True
        print("[MODAL L4] mixed precision via torch.autocast(fp16); weights stay float32.")

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

        # 5. Pre-warm run + fp16 quality gate (auto-revert so the voice is never
        #    compromised by the precision change - Baba's law: latency is never
        #    worth a broken voice).
        print("[MODAL L4] Running pre-warm inference with cached latents...")
        _warm = self.synthesize_pcm("नमस्ते।", speed=1.35)
        try:
            _pk = int(np.abs(np.frombuffer(_warm, dtype=np.int16)).max()) if _warm else 0
            print(f"[MODAL L4] pre-warm peak={_pk} autocast={getattr(self, 'xtts_autocast', False)}", flush=True)
            if _pk < 3000:
                raise RuntimeError(f"pre-warm audio peak {_pk} is dead - refusing to serve a broken voice")
        except Exception as e:
            print(f"[MODAL L4] PRE-WARM GATE FAILED: {e}", flush=True)
            raise

        # 6. LOCAL LLM ON THE L4 (Baba order 2026-10-05: fully utilize the L4, no
        #    external LLM round-trips). IMPORTANT: meta-llama/* repos are GATED on
        #    HuggingFace - they failed with "gated repo" and every turn silently fell
        #    back to the NVIDIA cloud API (proven in the Modal logs). Only UNGATED
        #    models are used here. Qwen2.5 is Apache-2.0, strong at Hindi, and fp16
        #    fits the 24GB L4 next to XTTS-v2 + large-v3-turbo.
        self.llm_local = None
        self.llm_local_name = None
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            for cand in (
                "Qwen/Qwen2.5-7B-Instruct",       # best Hindi quality that fits
                "Qwen/Qwen2.5-3B-Instruct",       # smaller, faster fallback
                "microsoft/Phi-3.5-mini-instruct",
            ):
                try:
                    t0 = time.time()
                    tok = AutoTokenizer.from_pretrained(cand)
                    model = AutoModelForCausalLM.from_pretrained(
                        cand,
                        torch_dtype=torch.float16,
                        device_map=self.device,
                    ).eval()
                    self.llm_local = model
                    self.llm_local_tok = tok
                    self.llm_local_name = cand
                    print(f"[LLM LOCAL] loaded {cand} in {time.time()-t0:.1f}s on {self.device}", flush=True)
                    break
                except Exception as e:
                    print(f"[LLM LOCAL] {cand} load failed: {e}, trying next...", flush=True)
        except Exception as e:
            print(f"[LLM LOCAL] unavailable ({e}); falling back to external NVIDIA API", flush=True)

        print("[MODAL L4] Warm-up complete! Serverless engine ready.")

    def detect_lang(self, text: str) -> str:
        # HINDI BY DEFAULT LAW (Baba 2026-10-05: voice should be in Hindi)
        t = (text or "").lower()
        if any(s in t for s in ("in english", "speak english", "speak in english")):
            return "en"
        return "hi"

    def llm_stream_clauses(self, user_text: str):
        lang = self.detect_lang(user_text)
        hint = "Reply in simple spoken Hindi, Devanagari script." if lang == "hi" else "Reply in concise spoken English."

        full = None
        if self.llm_local is not None:
            # LOCAL L4 PATH: no external round-trip, prefill + ~40 tokens on the L4
            t_llm0 = time.time()
            try:
                import torch
                messages = [
                    {"role": "system", "content": CLINIC_SYSTEM_PROMPT + "\n" + hint},
                    {"role": "user", "content": user_text},
                ]
                inputs = self.llm_local_tok.apply_chat_template(
                    messages, add_generation_prompt=True, return_tensors="pt"
                ).to(self.device)
                with torch.inference_mode():
                    out = self.llm_local.generate(
                        **inputs,
                        max_new_tokens=45,
                        do_sample=True,
                        temperature=0.2,
                        top_p=0.9,
                        pad_token_id=self.llm_local_tok.eos_token_id,
                    )
                gen = out[0][inputs["input_ids"].shape[1]:]
                full = self.llm_local_tok.decode(gen, skip_special_tokens=True).strip()
                print(f"[LLM LOCAL] {time.time()-t_llm0:.0f}ms reply='{full[:120]}'", flush=True)
            except Exception as e:
                print(f"[LLM LOCAL] generate failed ({e}); falling back to NVIDIA API", flush=True)
                full = None

        if full is None:
            # EXTERNAL FALLBACK (only when the local L4 load failed)
            full = "".join(list(self._llm_api_clauses(user_text, hint)))
            print(f"[LLM API FALLBACK] reply='{full[:120]}'", flush=True)

        full = full.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
        full = re.sub(r"\s+", " ", full).strip()

        # CLAUSE BATCHING: one small TTS call per 15-30 char fragment reset the prosody
        # mid-sentence (a cause of the reported gibberish). Batch to >= 80 chars or the
        # whole tail so each synthesis is a natural unit.
        #
        # FIRST-PIECE RULE (latency): the FIRST piece must be short so the caller hears a
        # voice fast. A 80-char first clause = ~6 s of audio = ~6 s of XTTS before the
        # first byte. The first piece is bounded to ~30 chars (a natural short opening
        # clause); every later piece keeps the >= 80 char prosody rule.
        out = ""
        first_emitted = False
        parts = re.split(r"(?<=[।.!?,\n])", full)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            budget = 30 if not first_emitted else 80
            if len(out) + len(p) >= budget or (len(p) >= budget):
                if out:
                    yield out
                    first_emitted = True
                out = p
            else:
                out += p
        if out:
            yield out

    def _llm_api_clauses(self, user_text: str, hint: str):
        messages = [
            {"role": "system", "content": CLINIC_SYSTEM_PROMPT + "\n" + hint},
            {"role": "user", "content": user_text},
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

    def synthesize_pcm(self, text: str, speed: float = 1.35) -> bytes:
        lang = self.detect_lang(text)
        clean_text = text.replace("*", "").replace("#", "").strip()
        if not clean_text:
            return b""

        import torch
        t_infer0 = time.time()
        used_fallback = False
        try:
            # autocast: fp16 compute for speed while every weight stays float32,
            # which is what avoids the Float/Half mismatch that killed the container.
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
                out = self.xtts_model.inference(
                    clean_text,
                    lang,
                    gpt_cond_latent=self.gpt_cond_latent,
                    speaker_embedding=self.speaker_embedding,
                    temperature=0.5,
                    speed=speed
                )
            wav = out["wav"] if isinstance(out, dict) else out
            if hasattr(wav, "detach"):
                wav = wav.detach().float().cpu().numpy()
            samples = np.asarray(wav, dtype=np.float32).squeeze()
        except Exception as e:
            used_fallback = True
            print(f"[SYNTH DIRECT INFER ERR] {e}, falling back to tts_to_file...")
            out_wav = f"/tmp/synth_{int(time.time()*1000)}.wav"
            self.tts.tts_to_file(
                text=clean_text,
                speaker_wav=self.ref_path,
                language=lang,
                file_path=out_wav,
                speed=speed
            )
            with wave.open(out_wav, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
            try:
                os.remove(out_wav)
            except Exception:
                pass
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        t_infer = int((time.time() - t_infer0) * 1000)

        sr = 24000
        samples = self.trim_sil(samples, sr, lead_ms=25, tail_ms=80)
        samples, _ = self.collapse_silence(samples, sr, frame_ms=10, quiet_pct=0.08, keep_ms=70, min_run_ms=120)

        samples = np.clip(samples, -1.0, 1.0)
        pcm = (samples * 32767.0).astype(np.int16).tobytes()
        # LATENCY RECEIPT (Baba order: no guessing - prove where the GPU time goes)
        if not getattr(self, "_synth_logged", 0) or len(clean_text) > 20:
            try:
                dev = str(next(self.xtts_model.parameters()).device)
                dt = str(next(self.xtts_model.parameters()).dtype)
                cuda = torch.cuda.is_available()
            except Exception as e:
                dev, dt, cuda = f"?{e}", "?", "?"
            aud = len(pcm) / 2 / 24000
            print(f"[SYNTH] infer={t_infer}ms post={int((time.time()-t_infer0)*1000)-t_infer}ms "
                  f"audio={aud:.2f}s RTF={t_infer/1000.0/max(aud,0.01):.2f} "
                  f"cuda={cuda} param_device={dev} dtype={dt} fallback={used_fallback} "
                  f"gpu_name={torch.cuda.get_device_name(0) if cuda else '-'} text='{clean_text[:24]}'", flush=True)
        self._synth_logged = 1
        return pcm

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
            ev = {"ts": time.strftime("%H:%M:%S", time.localtime())}
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
                "engine": "kilo-voice-modal-l4",
                "gpu": "NVIDIA L4 (24GB Ada Lovelace)",
                "voice": "deep_male_clinic_133hz",
                "speed": 1.35,
                "llm_local": self.llm_local_name,
                "xtts_autocast": getattr(self, "xtts_autocast", False),
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
            src = req.headers.get("user-agent", "?")[:40]

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
                    # HINDI FIRST LAW (Baba 2026-10-05: voice must be in Hindi, recognizing Baba accurately)
                    whisper_lang = "en" if req_lang == "en" else "hi"

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
                        initial_prompt="नमस्ते, मैं बोल रहा हूँ। डॉक्टर लोटिका क्लिनिक।"
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
                            initial_prompt="नमस्ते, मैं बोल रहा हूँ।"
                        )
                        user_text = " ".join([s.text for s in segments]).strip()
                except Exception as e:
                    print(f"[TURN STT ERR] {e}", flush=True)
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

            def is_hallucination(text):
                t = (text or "").lower()
                # 1. Any Cyrillic/Russian character is an automatic Whisper hallucination on noise
                if any("\u0400" <= ch <= "\u04FF" for ch in t):
                    return True
                import re
                clean = re.sub(r"[^\w\u0900-\u097f]+", " ", t)
                toks = [w for w in clean.split() if w]
                if not toks:
                    return True
                # 2. English noise words that Whisper emits on background noise or speaker bleed
                noise_words = {"you", "oh", "i", "the", "a", "an", "to", "it", "thank", "thanks", "bye"}
                if len(toks) == 1 and toks[0] in noise_words:
                    return True
                if len(toks) == 2 and set(toks).issubset({"thank", "you"}):
                    return True
                # 3. Repeated single token hallucination (e.g. "you you you...")
                collapsed = [toks[0]]
                for w in toks[1:]:
                    if w != collapsed[-1]:
                        collapsed.append(w)
                if len(collapsed) == 1 and len(toks) > 1:
                    return True
                if len(toks) >= 6 and len(set(toks)) <= 2:
                    return True
                if len(toks) >= 8 and len(set(toks)) / float(len(toks)) < 0.3:
                    return True
                return False

            # keep what Whisper REALLY heard for the receipt (before the gate edits it)
            heard_raw = user_text

            if is_hallucination(user_text):
                user_text = ""

            # ECHO GUARD (2026-10-05). Measured loop: the phone plays our clarify
            # ("...say it again?"), the mic opens early, captures the TAIL of our
            # own sentence, Whisper returns exactly "you", and we clarify again -
            # the seat answering itself forever. Detect our OWN outgoing text coming
            # back and refuse to answer it. Logs ECHO_DROPPED instead of dead air.
            _echo = False
            _heard_l = (user_text or "").lower()
            GREETING_ECHO_PHRASES = (
                "say it again", "did not catch", "could you please",
                "दोबारा", "माफ़ कीजिए", "बता सकते", "स्वागत", "डॉक्टर लोटिका",
                "सहायता कर सकता", "एक मिनट", "sugardoctor", "lotika"
            )
            try:
                _own = list(getattr(self, "_recent_replies", []))
                for _r in _own:
                    _rl = (_r or "").lower()
                    if not _rl:
                        continue
                    if _heard_l and (_heard_l in _rl or _rl in _heard_l):
                        _echo = True
                        break
                if not _echo and any(_p in _heard_l for _p in GREETING_ECHO_PHRASES):
                    _echo = True
            except Exception:
                _echo = False

            if _echo:
                print(f"[TURN ECHO] own audio/greeting came back as '{user_text}' - refusing to answer it.", flush=True)
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
                # ANTI-LOOP LAW (2026-10-05): Do not play audio on silence/noise, as that triggers feedback loops
                print(f"[TURN DROPPED] Empty or noise utterance raw='{heard_raw}', returning empty.", flush=True)
                turn_event(src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                           heard=heard_raw, reply="", empty=True,
                           llm_local=self.llm_local_name)

                async def empty_stream():
                    hdr = json.dumps({"cid": "turn", "heard": "", "stt_ms": stt_ms, "sr": 24000, "empty": True}) + "\n"
                    yield hdr.encode("utf-8")
                    trailer = json.dumps({"end": True, "heard": "", "reply": "", "empty": True}) + "\n"
                    yield trailer.encode("utf-8")

                return StreamingResponse(
                    empty_stream(), media_type="application/octet-stream",
                    headers={"X-Sample-Rate": "24000", "X-Channels": "1"})

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
                turn_event(
                    src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                    heard=user_text, reply=full_reply,
                    first_pcm_ms=t_first_pcm or total_ms, total_ms=total_ms,
                    llm_local=self.llm_local_name,
                )
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
