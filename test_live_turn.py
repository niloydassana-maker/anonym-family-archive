import urllib.request, json, time, wave

url = "https://removing-welcome-clocks-provinces.trycloudflare.com/turn"
print(f"Connecting to {url} ...", flush=True)

with open(r"d:\anonym\say_namaste.wav", "rb") as f:
    audio_data = f.read()

t0 = time.time()
req = urllib.request.Request(
    url,
    data=audio_data,
    headers={
        "Content-Type": "audio/wav",
        "X-Voice-Lang": "hi",
        "User-Agent": "test-client"
    },
    method="POST"
)

with urllib.request.urlopen(req, timeout=30) as resp:
    print(f"Connected in {(time.time() - t0)*1000:.0f} ms. Reading chunks...", flush=True)
    chunks = []
    first_chunk_time = None
    all_bytes = bytearray()
    
    while True:
        line = resp.readline()
        if not line:
            break
        try:
            sz = int(line.strip().split(b";")[0], 16)
        except Exception:
            break
        if sz == 0:
            break
        raw = resp.read(sz)
        resp.read(2) # CRLF
        
        now = time.time()
        if first_chunk_time is None:
            first_chunk_time = now
            print(f"First chunk ({sz} bytes) received at {(now - t0)*1000:.0f} ms!", flush=True)
        
        # Check if json or audio
        try:
            j = json.loads(raw.decode('utf-8'))
            print("JSON Chunk:", j, flush=True)
        except Exception:
            print(f"Audio Chunk: {len(raw)} bytes at {(now - t0)*1000:.0f} ms", flush=True)
            all_bytes.extend(raw)

print(f"Total audio bytes: {len(all_bytes)} ({(time.time() - t0)*1000:.0f} ms)", flush=True)
if len(all_bytes) > 0:
    out_path = r"d:\anonym\v104_turn_test.wav"
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(all_bytes)
    print(f"Saved {out_path}", flush=True)
