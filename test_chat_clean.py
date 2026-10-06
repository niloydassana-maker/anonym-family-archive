import urllib.request, json, sys

url = 'https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/api/chat'
req = urllib.request.Request(
    url,
    data=json.dumps({'text': 'नमस्ते, क्लिनिक कब खुलता है?', 'session_id': 'test_check'}).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'User-Agent': 'Test/1.0'}
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print('STATUS:', resp.status)
        print('AUDIO_B64_LEN:', len(res.get('audio_b64', '')))
        print('AUDIO_URL:', res.get('audio_url'))
        # Write reply to file so encoding doesn't break
        with open('d:/anonym/last_reply.txt', 'w', encoding='utf-8') as f:
            f.write(res.get('reply', ''))
        print('REPLY written to last_reply.txt successfully!')
except Exception as e:
    print('ERROR:', e)
