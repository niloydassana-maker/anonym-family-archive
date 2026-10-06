import urllib.request, urllib.parse, wave, numpy as np

tests = [
    ("haa_ji", "हाँ जी, सुन रही हूँ।"),
    ("namaste", "नमस्ते, मैं आपकी कैसे मदद कर सकती हूँ?"),
    ("ji_bataiye", "जी, बताइए।")
]

for label, t in tests:
    url = 'https://empirical-finally-engagement-admissions.trycloudflare.com/say?text=' + urllib.parse.quote(t) + '&lang=hi'
    try:
        with urllib.request.urlopen(url) as r:
            w = r.read()
        dur = (len(w) - 44) / 48000.0
        filename = f'd:/anonym/say_{label}.wav'
        with open(filename, 'wb') as f:
            f.write(w)
        print(f'{label} -> {dur:.2f}s audio, saved to {filename}')
    except Exception as e:
        print(f'{label} -> Error: {e}')
