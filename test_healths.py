import urllib.request, json

for name, url in [
    ('kunal-colab', 'https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/health'),
    ('isearch-xsolve', 'https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/health')
]:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'HealthCheck/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"{name}: OK ({resp.status}) - active_sessions={data.get('active_sessions')}, voice={data.get('voice')}")
    except Exception as e:
        print(f"{name}: ERROR ({e})")
