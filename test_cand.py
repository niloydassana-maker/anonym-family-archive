import urllib.request, urllib.parse, wave, numpy as np

candidates = [
    ('haan_ji', 'हाँ जी!'),
    ('namaste_ji', 'नमस्ते, जी!'),
    ('ji_suniye', 'जी, सुनिए।'),
    ('ji_kahiye', 'जी, कहिए?'),
    ('ji_bataiye', 'जी बताइए, मैं सुन रही हूँ।'),
    ('haan_bataiye', 'हाँ, बताइए?'),
    ('ji_ek_second', 'जी, एक सेकंड रुकिए।'),
    ('haan_ji_kahiye', 'हाँ जी, कहिए?'),
]

for label, txt in candidates:
    url = 'https://marsh-pike-subcommittee-varying.trycloudflare.com/say?text=' + urllib.parse.quote(txt) + '&lang=hi'
    try:
        with urllib.request.urlopen(url) as r:
            w = r.read()
        dur = (len(w) - 44) / 48000.0
        fn = f'd:/anonym/cand_{label}.wav'
        with open(fn, 'wb') as f:
            f.write(w)
        print(f'{label}: {dur:.2f}s')
    except Exception as e:
        print(f'{label} err: {e}')
