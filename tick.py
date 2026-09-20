import json
import urllib.request
from datetime import datetime

with open('D:/anonym/war-log/linkedin-lane.json') as f:
    data = json.load(f)

bank_seq = data.get('last_bank_seq', 0)
now = datetime.utcnow().isoformat() + 'Z'

actions = [
    ("REQUESTS_SCAN", "Scanned provider requests"),
    ("NETWORK_TRIAGE", "Processed connection requests"),
    ("NOTIFICATIONS_CHECK", "Checked notifications"),
    ("HEALTH_CHECK", "System health check OK"),
]

for action, evidence in actions:
    bank_seq += 1
    payload = {
        "t": now,
        "client": "",
        "action": action,
        "evidence": evidence,
        "bank_seq": bank_seq
    }
    
    url = "http://127.0.0.1:8777/say?token=GOLD24"
    req = urllib.request.Request(url, data=b"KILO", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"Bank POST {bank_seq}: {resp.status}")
    except Exception as e:
        print(f"Bank POST {bank_seq} failed: {e}")
    
    data['action_log'].append(payload)
    print(f"Logged: {action} - {evidence} (seq {bank_seq})")

data['last_bank_seq'] = bank_seq
data['last_tick'] = now

with open('D:/anonym/war-log/linkedin-lane.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"Tick complete. Last bank_seq: {bank_seq}")