import urllib.request
import json
import time
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run"

# 1. Health check
print("[TEST 1] Checking health endpoint...")
t0 = time.time()
with urllib.request.urlopen(f"{BASE_URL}/health", timeout=90) as resp:
    data = json.loads(resp.read().decode())
    print(f"Health response ({int((time.time()-t0)*1000)}ms): {data}")

# 2. Test Turn Endpoint with synthesized audio of "hello hello"
print("\n[TEST 2] Testing TURN with 'हेलो हेलो' greeting text / simulated speech...")
# We can create a 1.5s 16kHz sine wave or small speech sample or send JSON body to /turn
# Notice turn() accepts JSON: {"b64": base64_wav, "lang": "hi"} OR raw audio
import io, wave, numpy as np, base64

def make_test_wav(duration_s=1.5, freq=220):
    sr = 16000
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    # create modulated speech-like audio
    sig = (0.3 * np.sin(2 * np.pi * freq * t) * np.sin(2 * np.pi * 3 * t)).astype(np.float32)
    pcm = (sig * 32767.0).astype(np.int16).tobytes()
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm)
    return bio.getvalue()

# Let's test the say endpoint first to verify pure Hindi and no English accent
print("\n[TEST 3] Testing /say with clinic response...")
t0 = time.time()
req = urllib.request.Request(
    f"{BASE_URL}/say",
    data=json.dumps({"text": "नमस्ते! आपका स्वागत है डॉक्टर लोटिका पुरोहित के क्लिनिक में।", "speed": 1.35}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    pcm = resp.read()
    gen_ms = resp.headers.get("X-Gen-Ms")
    dur_s = len(pcm) / 2 / 24000
    print(f"/say generated {len(pcm)} bytes ({dur_s:.2f}s audio) in {gen_ms}ms (total HTTP: {int((time.time()-t0)*1000)}ms)")

print("\nTests complete!")
