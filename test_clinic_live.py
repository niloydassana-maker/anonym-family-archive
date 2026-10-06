import sys
import urllib.request
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = 'https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/turn'
questions = [
    'नमस्ते',
    'क्लिनिक का समय क्या है?',
    'मुख्य डॉक्टर कौन हैं?',
    'परामर्श की फीस क्या है?'
]

for q in questions:
    req = urllib.request.Request(
        url,
        data=json.dumps({'text': q}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'kilo-live-test'}
    )
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        hdr = resp.readline().decode('utf-8').strip()
        pcm = resp.read()
        dt = (time.time() - t0) * 1000
        print(f"Q: '{q}' | Time: {dt:.0f}ms | Bytes: {len(pcm)} | Hdr: {hdr}")
    except Exception as e:
        print(f"Q: '{q}' | ERR: {e}")
