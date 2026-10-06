#!/usr/bin/env python3
"""Pre-render the clinic demo lines on the free GPU seat and save one WAV per line.

Why pre-render: the seat generates at ~2.3-2.8x real time, so a live call would stall on
generation. Rendering the fixed turns cost nothing (free Kaggle GPU) and makes the demo call
instant and immune to the seat's run-to-run variance.

Posts one line at a time and reassembles immediately: the relay only exposes the last 20
reports, so batching all lines at once would lose chunks.
"""
import base64
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import soundfile as sf

TOK = "GOLD24"
RELAY = "http://127.0.0.1:8777"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# The demo turns, in the order a call plays them. Words (not digits) for the times, because the
# seat spells digits via its Hindi number helper.
# GENDER LAW: the clinic voice is male, so every first-person verb must be masculine
# (बोल रहा हूँ / कर सकता हूँ -- never रही / सकती). Baba caught a feminine line on the male voice.
LINES = [
    ("demo-answer", "नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। मैं क्लिनिक से बोल रहा हूँ। बताइए, मैं आपकी क्या मदद कर सकता हूँ?"),
    ("demo-timings", "क्लिनिक सुबह नौ बजे से दोपहर दो बजे तक, और शाम पाँच बजे से रात आठ बजे तक खुली रहती है।"),
    ("demo-booking", "जी, आपका अपॉइंटमेंट कल सुबह ग्यारह बजे डॉक्टर लोतिका पुरोहित के साथ तय हो गया है। धन्यवाद।"),
    ("demo-callback", "जी, आपका नंबर दर्ज हो गया है। हम थोड़ी देर में कॉल करके समय बता देंगे।"),
    ("demo-close", "धन्यवाद। आपका दिन शुभ हो।"),
]


def dev(s):
    return sum(1 for c in s if 0x900 <= ord(c) <= 0x97F)


def post(line):
    body = json.dumps({"body": "LIVE-VOICE", "text": line}, ensure_ascii=True).encode("ascii")
    req = urllib.request.Request(f"{RELAY}/say?token={TOK}", data=body,
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=30).read().decode()


def orders():
    url = f"{RELAY}/say?token={TOK}&body=KILO&limit=40"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode()).get("orders", [])


def reports():
    """Chunks and LIVE_DONE land on different channels depending on how the seat emits them,
    so merge every candidate channel and dedupe."""
    seen, out = set(), []
    for path, key in (("hear", "reports"), ("say", "orders")):
        for body in ("KILO", "LIVE-VOICE"):
            url = f"{RELAY}/{path}?token={TOK}&body={body}"
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    rows = json.loads(r.read().decode()).get(key, [])
            except Exception:
                continue
            for x in rows:
                k = (x.get("at"), (x.get("text") or "")[:120])
                if k in seen:
                    continue
                seen.add(k)
                out.append(x)
    return out


def wait_done(cid, timeout=180):
    end = time.time() + timeout
    while time.time() < end:
        for o in orders():
            t = o.get("text") or ""
            if t.startswith(f"LIVE_DONE {cid}"):
                return t
            if t.startswith("LIVE_FAIL") or t.startswith("LIVE_CRASH"):
                return t
        time.sleep(5)
    return None


def assemble(cid, dst):
    pat = re.compile(rf"LIVE_CHUNK {re.escape(cid)} (\d+)-(\d+)/(\d+):(.+)")
    groups = {}
    for rep in reports():
        m = pat.match((rep.get("text") or "").strip())
        if m:
            groups.setdefault(int(m.group(1)), {})[int(m.group(2))] = m.group(4)
    if not groups:
        return None
    segs, sr = [], None
    for ci in sorted(groups):
        parts = groups[ci]
        raw = b"".join(base64.b64decode(parts[p]) for p in sorted(parts))
        try:
            a, s = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
            sr = sr or s
            segs.append(a)
        except Exception as e:
            print(f"  group {ci} unreadable: {type(e).__name__}")
    if not segs:
        return None
    audio = np.concatenate(segs)
    sf.write(dst, audio, sr)
    return len(audio) / sr, sr, len(groups)


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    lines = [(c, t) for c, t in LINES if not only or c in only]
    results = []
    for cid, text in lines:
        # CID_SUFFIX keeps a re-render from matching a stale LIVE_DONE of the same cid.
        post_cid = cid + os.environ.get("CID_SUFFIX", "")
        if dev(text) == 0:
            print(f"{cid}: SKIP no devanagari")
            continue
        line = "LIVE_CALL " + json.dumps({"cid": post_cid, "lang": "hi", "text": text}, ensure_ascii=True)
        r = post(line)
        print(f"\n--- {cid} (as {post_cid}) posted chars={len(text)} dev={dev(text)} resp={r[:60]}")
        done = wait_done(post_cid)
        print(f"    {done or 'TIMEOUT'}")
        dst = os.path.join(OUT, f"{cid}.wav")
        got = assemble(post_cid, dst)
        if got:
            dur, sr, ng = got
            print(f"    SAVED {os.path.basename(dst)} {dur:.2f}s sr={sr} groups={ng} "
                  f"bytes={os.path.getsize(dst)}")
            results.append((cid, dur, ng, os.path.getsize(dst)))
        else:
            print("    ASSEMBLE FAILED")
        time.sleep(3)

    print("\n=== PRERENDER SUMMARY ===")
    for cid, dur, ng, by in results:
        print(f"{cid:14} {dur:5.2f}s groups={ng} bytes={by}")
    print(f"total {len(results)}/{len(lines)} lines rendered")
    return 0 if results else 2


if __name__ == "__main__":
    sys.exit(main())
