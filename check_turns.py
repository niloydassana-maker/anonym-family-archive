import urllib.request, json, sys

sys.stdout.reconfigure(encoding='utf-8')
url = 'https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/lastturns'
with urllib.request.urlopen(url) as resp:
    data = json.loads(resp.read().decode())
    if isinstance(data, str):
        data = json.loads(data)
    for x in data:
        print(f"[{x.get('ts')}] heard: {repr(x.get('heard'))} | reply: {repr(x.get('reply'))} | echo={x.get('echo')} empty={x.get('empty')}")
