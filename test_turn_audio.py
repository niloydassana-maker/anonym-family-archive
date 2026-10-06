import urllib.request, json, time, wave, base64, numpy as np

wav_file = 'd:/anonym/test_say.wav'
with open(wav_file, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
data = json.dumps({'b64': b64, 'lang': 'hi'}).encode()
tunnel = 'https://removing-welcome-clocks-provinces.trycloudflare.com'
req = urllib.request.Request(f'{tunnel}/turn?speed=1.35', data=data, headers={'Content-Type': 'application/json'})

print('Sending request to v104...')
t0 = time.time()
with urllib.request.urlopen(req) as resp:
    hdr = resp.readline().decode()
    t_hdr = time.time() - t0
    print(f'Header after {t_hdr*1000:.0f}ms: {hdr.strip()}')
    
    # Read first audio chunk timing
    chunk1 = resp.read(4096)
    t_first_sound = time.time() - t0
    print(f'FIRST SOUND RECEIVED AT {t_first_sound*1000:.0f}ms! (Size: {len(chunk1)} bytes)')
    
    rest = resp.read()
    raw_body = chunk1 + rest

pat = b'{"end"'
cut = raw_body.rfind(pat)
pcm = raw_body[:cut] if cut != -1 else raw_body
trailer = raw_body[cut:].decode('utf-8', errors='ignore') if cut != -1 else ''

print(f'Trailer: {trailer.strip()}')
print(f'Total audio received: {len(pcm)} bytes = {len(pcm)/48000:.2f}s in {(time.time()-t0)*1000:.0f}ms')

with wave.open('d:/anonym/v104_turn_out.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
