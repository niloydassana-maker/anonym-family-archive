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

with open(r"d:\anonym\say_namaste.wav", "rb") as f:
    in_wav_bytes = f.read()

url = "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/turn"
req = urllib.request.Request(
    url,
    data=in_wav_bytes,
    headers={"Content-Type": "audio/wav", "User-Agent": "kilo-test"}
)

print(f"Connecting to live Modal L4 endpoint: {url}...")
t0 = time.time()
resp = urllib.request.urlopen(req, timeout=90)

# 1. Read JSON header line
header_bytes = bytearray()
while True:
    b = resp.read(1)
    if not b or b == b'\n':
        break
    header_bytes.extend(b)
t_first = (time.time() - t0) * 1000
header = json.loads(header_bytes.decode("utf-8"))
print(f">>> [HEADER RECEIVED] Time to first response: {t_first:.1f} ms | Heard: '{header.get('heard')}'")

# 2. Stream PCM audio until trailer
audio_pcm = bytearray()
trailer = {}
trailer_pat = b'{"end":'

while True:
    chunk = resp.read(4096)
    if not chunk:
        break
    if trailer_pat in chunk:
        idx = chunk.index(trailer_pat)
        audio_pcm.extend(chunk[:idx])
        trailer_str = chunk[idx:].decode("utf-8", errors="replace").strip()
        try:
            trailer = json.loads(trailer_str)
        except Exception:
            pass
        break
    else:
        audio_pcm.extend(chunk)

t_total = (time.time() - t0) * 1000

# Save output WAV
out_wav_path = r"D:\anonym\modal_turn_output.wav"
with wave.open(out_wav_path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(24000)
    wf.writeframes(audio_pcm)

print("\n=======================================================")
print("          MODAL L4 LIVE /TURN BENCHMARK RECEIPT        ")
print("=======================================================")
print(f"Time to First Sound / Header: {t_first:.1f} ms")
print(f"Total Turn Time:              {t_total:.1f} ms")
print(f"Total PCM Bytes Received:     {len(audio_pcm)} bytes (~{len(audio_pcm)/48000:.2f}s audio)")
print(f"Whisper STT Time:             {trailer.get('stt_ms', header.get('stt_ms'))} ms")
print(f"Nemotron LLM Time:            {trailer.get('llm_ms')} ms")
print(f"XTTS TTS Time:                {trailer.get('tts_ms')} ms")
print(f"Transcribed Input:            '{trailer.get('heard', header.get('heard'))}'")
print(f"Assistant Reply:              '{trailer.get('reply')}'")
print(f"Output WAV File:              {out_wav_path}")
print("=======================================================")
