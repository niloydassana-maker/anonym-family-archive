import urllib.request
import json
import time
import sys

# Force UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open(r"d:\anonym\say_namaste.wav", "rb") as f:
    audio_data = f.read()

url = "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/turn"
req = urllib.request.Request(
    url,
    data=audio_data,
    headers={"Content-Type": "audio/wav", "User-Agent": "rca-probe"},
    method="POST"
)

t0 = time.time()
print("=== PROBE 3: FULL COMPONENT TIMELINE OF LIVE /TURN ===")
with urllib.request.urlopen(req, timeout=35) as resp:
    t_conn = (time.time() - t0) * 1000
    print("1. Connection established: %.1f ms" % t_conn)
    
    # Read header
    hdr_line = resp.readline()
    t_hdr = (time.time() - t0) * 1000
    try:
        hdr = json.loads(hdr_line.decode("utf-8"))
        print("2. Header received: %.1f ms | Heard: %s" % (t_hdr, repr(hdr.get("heard"))))
    except Exception as e:
        print("2. Header parse err: %s | raw: %s" % (e, repr(hdr_line[:50])))
    
    # Stream chunks
    first_chunk_t = None
    total_audio = bytearray()
    trailer = None
    
    while True:
        chunk = resp.read(4096)
        if not chunk:
            break
        now = (time.time() - t0) * 1000
        if first_chunk_t is None and len(chunk) > 0 and not chunk.startswith(b'{"end":'):
            first_chunk_t = now
            print("3. FIRST AUDIO RECEIVED: %.1f ms (size: %d bytes)" % (first_chunk_t, len(chunk)))
        
        if b'{"end":' in chunk:
            idx = chunk.index(b'{"end":')
            total_audio.extend(chunk[:idx])
            trailer_str = chunk[idx:].decode("utf-8", errors="replace").strip()
            try:
                trailer = json.loads(trailer_str)
            except Exception:
                trailer = trailer_str
        else:
            total_audio.extend(chunk)

    total_t = (time.time() - t0) * 1000
    print("4. Turn completed: %.1f ms" % total_t)
    print("   Total audio bytes: %d (%.2f s of audio)" % (len(total_audio), len(total_audio)/48000.0))
    print("   Server Trailer: %s" % trailer)
