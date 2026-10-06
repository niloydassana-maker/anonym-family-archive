import sys
import os
import urllib.request
import json
import time
import io
import wave
import numpy as np

# Force UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Use real audio from clinic reference (first 2 seconds)
ref_path = r"D:\anonym\RESCUE-kaggle-reset\dataset-pull\clinic_reference.wav"
bio = io.BytesIO()
with wave.open(ref_path, "rb") as wf:
    sr = wf.getframerate()
    frames = wf.readframes(int(sr * 2.0))
    with wave.open(bio, "wb") as out_wf:
        out_wf.setnchannels(1)
        out_wf.setsampwidth(2)
        out_wf.setframerate(sr)
        out_wf.writeframes(frames)
raw_wav = bio.getvalue()

url = "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/turn"
req = urllib.request.Request(url, data=raw_wav, headers={"Content-Type": "audio/wav"})

print(f"Connecting to live Modal L4 endpoint: {url}...")
t0 = time.time()
resp = urllib.request.urlopen(req, timeout=60)
t_conn = (time.time() - t0) * 1000

header_line = resp.readline().decode("utf-8")
t_first = (time.time() - t0) * 1000
header = json.loads(header_line)

body = resp.read()
t_end = (time.time() - t0) * 1000

trailer = {}
trailer_pat = b'{"end":'
idx = body.find(trailer_pat)
if idx != -1:
    pcm = body[:idx]
    try:
        trailer = json.loads(body[idx:].decode("utf-8").strip())
    except Exception:
        pass
else:
    pcm = body

print("\n=======================================================")
print("       EXACT MODAL L4 TOTAL LATENCY RECEIPT       ")
print("=======================================================")
print(f"Network Connect Latency:     {t_conn:.1f} ms")
print(f"Time to First Byte/Header:   {t_first:.1f} ms")
print(f"Heard from Caller:           '{header.get('heard')}'")
print(f"STT Latency (Whisper CUDA):  {header.get('stt_ms')} ms")
print(f"LLM Latency (Nemotron 120B): {trailer.get('llm_ms')} ms")
print(f"TTS Latency (XTTS L4 GPU):   {trailer.get('tts_ms')} ms")
print(f"Total Server Processing:     {trailer.get('total_ms')} ms")
print(f"Total End-to-End Wall Time:  {t_end:.1f} ms")
print(f"Assistant Reply:             '{trailer.get('reply')}'")
print(f"Audio Generated:             {len(pcm)/48000:.2f} s ({len(pcm)} bytes)")
print("=======================================================")
