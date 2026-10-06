import urllib.request, json, time, base64, wave

with open(r'd:\anonym\say_namaste.wav', 'rb') as f:
    wav_bytes = f.read()

payload = json.dumps({'b64': base64.b64encode(wav_bytes).decode('utf-8')}).encode('utf-8')
req = urllib.request.Request(
    'https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/turn',
    data=payload,
    headers={'Content-Type': 'application/json', 'X-Voice-Lang': 'hi'}
)
print("Connecting to Modal /turn...")
with urllib.request.urlopen(req, timeout=30) as resp:
    hdr = resp.readline().decode('utf-8')
    print("Header:", hdr.strip())
    pcm = resp.read()
    pat = b'{"end":'
    if pat in pcm:
        idx = pcm.index(pat)
        pcm = pcm[:idx]
    with wave.open(r'd:\anonym\test_namaste_turn.wav', 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm)
    print("Wrote test_namaste_turn.wav, length:", len(pcm))
