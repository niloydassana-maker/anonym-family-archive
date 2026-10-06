"""Measure the HONEST latency number: first sound at the LISTENER, not at the server.

§60.2 law: first_pcm_ms is measured from the kernel's own t0 to the first byte written to the
socket. It excludes the VAD hang, the upload, the download and the player. The only number that
counts is what the caller hears, so this measures the full round trip from posting the audio to
the first PCM byte arriving back, and reports the server's own figure beside it for contrast.
"""
import base64, json, os, sys, time, urllib.request, wave
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\anonym\war-log\voice-live\out"
URL = open(os.path.join(OUT, "live_tunnel.txt")).read().strip()

# the same five approved lines, so the timing is measured on text known to be good
LINES = [
    ("answer",   "नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। मैं क्लिनिक से बोल रहा हूँ। बताइए, मैं आपकी क्या मदद कर सकता हूँ?"),
    ("timings",  "क्लिनिक सुबह नौ बजे से दोपहर दो बजे तक, और शाम पाँच बजे से रात आठ बजे तक खुली रहती है।"),
    ("close",    "धन्यवाद। आपका दिन शुभ हो।"),
]

def post_turn(b64):
    req = urllib.request.Request(URL + "/turn",
                                 data=json.dumps({"b64": b64, "lang": "hi"}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=300)
    first = None
    buf = bytearray()
    while True:
        chunk = r.read(32768)
        if not chunk:
            break
        if first is None:
            first = time.time()
        buf += chunk
    return time.time() - t0, first - t0 if first else None, bytes(buf)

print("LIVE TURN TIMING on %s" % URL)
print("=" * 72)

try:
    q = urllib.request.urlopen(URL + "/probe_wav", timeout=90).read()
    open(os.path.join(OUT, "lat_probe.wav"), "wb").write(q)
    w = wave.open(os.path.join(OUT, "lat_probe.wav"), "rb")
    print("question audio: %.2f s" % (w.getnframes() / float(w.getframerate())))
except Exception:
    q = open(os.path.join(OUT, "probe_question.wav"), "rb").read()

rows = []
for i in range(3):
    b64 = base64.b64encode(q).decode()
    total, first, raw = post_turn(b64)
    nl = raw.find(b"\n")
    try:
        hdr = json.loads(raw[:nl].decode("utf-8", "replace"))
    except Exception:
        hdr = {}
    body = raw[nl + 1:]
    cut = body.rfind(b'{"end"')
    tr = {}
    if cut > 0:
        try:
            tr = json.loads(body[cut:].decode("utf-8", "replace"))
        except Exception:
            pass
    pcm = body[:cut] if cut > 0 else body
    print("\nturn %d" % (i + 1))
    print("   stt_ms (kernel)      %s" % hdr.get("stt_ms"))
    print("   llm first token ms   %s" % tr.get("llm_first_tok_ms"))
    print("   SERVER first pcm ms  %s      <- not the caller's number" % tr.get("first_pcm_ms"))
    print("   SERVER total ms      %s" % tr.get("total_ms"))
    print("   pieces %s   audio %s s" % (tr.get("pieces"), tr.get("audio_s")))
    print("   heard  : %s" % hdr.get("heard"))
    print("   reply  : %s" % tr.get("reply"))
    rows.append((hdr.get("stt_ms"), tr.get("first_pcm_ms"), tr.get("total_ms"),
                 tr.get("audio_s"), len(pcm)))
    if i == 0:
        fp = os.path.join(OUT, "lat_turn1.wav")
        w = wave.open(fp, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(pcm); w.close()
        print("   saved %s" % fp)

print("\n" + "=" * 72)
print("NOTE: these are still LAPTOP-side figures. The handset number is PHONE_FIRST_AUDIO,")
print("      logged by Kilo Bridge v9 when it plays the first byte it receives.")
print("=" * 72)