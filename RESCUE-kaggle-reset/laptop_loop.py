"""LAPTOP-SIDE LOOP -- no phone at all.

1. GET  /probe_wav  -> a Hindi clinic question, synthesised by the kernel's own XTTS
2. POST /turn       -> the full turn: Whisper -> Nemotron -> XTTS
3. the streamed PCM is written to answer.wav here on the laptop
4. play it with the laptop's own audio so Baba hears EXACTLY what XTTS produced

If answer.wav is clean, the phone pipeline is at fault. If it is gibberish, XTTS/the text is at fault.
"""
import base64, json, os, shutil, subprocess, sys, time, urllib.request, urllib.error, wave
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:8777"
OUT = r"D:\anonym\war-log\voice-live\out"

def alive(url):
    try:
        return True, json.loads(urllib.request.urlopen(url + "/health", timeout=25).read().decode())
    except Exception as e:
        return False, str(e)[:70]

def tunnels():
    try:
        d = json.loads(urllib.request.urlopen("%s/hear?body=KILO&limit=40&token=GOLD24" % BASE,
                                              timeout=30).read().decode("utf-8", "replace"))
    except Exception:
        return []
    out = set()
    for g in d.values():
        for r in g:
            t = r.get("text", "")
            if "VOICE_TUNNEL" in t:
                out.add(t.split("VOICE_TUNNEL", 1)[1].strip())
    return sorted(out)

url = None
print("waiting for a LIVE tunnel (the kernel is booting) ...")
for attempt in range(24):
    for u in tunnels():
        ok, info = alive(u)
        if ok:
            print("  ALIVE %s" % u)
            print("        %s" % json.dumps(info)[:140])
            url = u
            break
    if url:
        break
    print("  none yet (%d/24)" % (attempt + 1))
    time.sleep(12)

if not url:
    print("NO LIVE TUNNEL after the wait")
    raise SystemExit(2)

open(os.path.join(OUT, "live_tunnel.txt"), "w").write(url)

# --- 1. question audio ---
qpath = os.path.join(OUT, "probe_question.wav")
try:
    raw = urllib.request.urlopen(url + "/probe_wav", timeout=90).read()
    open(qpath, "wb").write(raw)
    print("\nquestion from the kernel: %d bytes" % len(raw))
except Exception as e:
    shutil.copy(r"D:\anonym\voice-corpus\wav\wa_PTT-20260910-WA0000.wav", qpath)
    print("\n/probe_wav unavailable (%s); using a laptop clip" % e)

# --- 2. the turn ---
b64 = base64.b64encode(open(qpath, "rb").read()).decode()
req = urllib.request.Request(url + "/turn", data=json.dumps({"b64": b64, "lang": "hi"}).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
t0 = time.time()
raw = urllib.request.urlopen(req, timeout=300).read()
print("turn: %d bytes in %.0f ms" % (len(raw), (time.time() - t0) * 1000))

nl = raw.find(b"\n")
hdr = json.loads(raw[:nl].decode("utf-8", "replace"))
body = raw[nl + 1:]
cut = body.rfind(b'{"end"')
tr = json.loads(body[cut:].decode("utf-8", "replace")) if cut > 0 else {}
pcm = body[:cut] if cut > 0 else body

print("\n=== WHISPER HEARD ===\n   %s" % hdr.get("heard"))
print("\n=== NEMOTRON WROTE (verbatim) ===\n   %s" % tr.get("reply", "(none)"))
print("\n=== TIMINGS ===")
for k in ("pieces", "first_pcm_ms", "synth_ms", "audio_s", "total_ms", "chars"):
    if k in tr:
        print("   %-14s %s" % (k, tr[k]))
tt = tr.get("trace") or {}
for k in ("llm_host", "llm_headers_ms", "llm_first_tok_ms", "llm_first_piece_ms", "stt_ms"):
    if k in tt:
        print("   trace.%-10s %s" % (k, tt[k]))

# the kernel's own view of the text, via /last
try:
    last = json.loads(urllib.request.urlopen(url + "/last", timeout=30).read().decode())
    print("\n=== GET /last ===")
    print("   model       : %s" % last.get("model"))
    print("   persona len : %s" % last.get("persona_chars"))
    L = last.get("last") or {}
    for k in ("ts", "heard", "reply", "pieces", "first_pcm_ms"):
        if k in L:
            print("   %-12s %s" % (k, str(L[k])[:200]))
except Exception as e:
    print("\n/last failed:", e)

apath = os.path.join(OUT, "answer_raw_xtts.wav")
w = wave.open(apath, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
w.writeframes(pcm); w.close()
print("\nanswer wav: %s  %d bytes  %.2f s" % (apath, len(pcm), len(pcm) / 2 / 24000.0))

FF = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffplay.exe"
print("\nplaying in 3 s on the LAPTOP speakers (phone not involved) ...")
time.sleep(3)
try:
    subprocess.Popen([FF, "-nodisp", "-autoexit", apath])
    print("  playing:", apath)
except Exception as e:
    print("  ffplay failed:", e)