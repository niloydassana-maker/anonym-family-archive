import urllib.request, json

# Test 1: GET /
req = urllib.request.Request('https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/')
with urllib.request.urlopen(req, timeout=45) as resp:
    html = resp.read().decode('utf-8')
    print('TEST 1 (HTML): STATUS =', resp.status, '| LEN =', len(html), '| HAS_LANG_TOGGLE =', 'lang-toggle-btn' in html)

# Test 2: Greeting check
req = urllib.request.Request(
    'https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/api/chat',
    data=json.dumps({'text': 'hello', 'session_id': 'verify_greeting'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    reply = res.get('reply', '')
    with open('d:/anonym/verify_greeting_out.txt', 'w', encoding='utf-8') as f:
        f.write(reply)
    has_wrong = 'आप कैसे मदद कर सकते हैं' in reply
    has_correct = 'मैं आपकी क्या सहायता कर सकता हूँ' in reply
    print('TEST 2 (GREETING): STATUS =', resp.status, '| AUDIO_LEN =', len(res.get('audio_b64', '')))
    print('  Wrong phrase present:', has_wrong)
    print('  Correct phrase present:', has_correct)

# Test 3: Follow-up doctor check
req = urllib.request.Request(
    'https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/api/chat',
    data=json.dumps({'text': 'I want to talk to a doctor', 'session_id': 'verify_doc'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    reply_doc = res.get('reply', '')
    with open('d:/anonym/verify_doc_out.txt', 'w', encoding='utf-8') as f:
        f.write(reply_doc)
    print('TEST 3 (DOCTOR TALK): STATUS =', resp.status, '| AUDIO_LEN =', len(res.get('audio_b64', '')))
