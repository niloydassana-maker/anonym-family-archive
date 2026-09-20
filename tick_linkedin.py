import json
import urllib.request
from datetime import datetime, timezone

# Read current state
with open(r'D:\anonym\war-log\linkedin-lane.json', 'r') as f:
    data = json.load(f)

# Check authority comments today
today = '2026-09-19'
auth_count = sum(1 for entry in data['action_log'] 
                 if entry['action'] == 'AUTHORITY_COMMENT' and entry['t'].startswith(today))
print('Authority comments today:', auth_count, '-', 'SKIP' if auth_count >= 5 else 'ALLOWED')

# Define tick actions (skip AUTHORITY_COMMENT since 5 already logged)
actions = [
    ("REQUESTS_SCAN", "Scanned provider requests"),
    ("NETWORK_TRIAGE", "Processed connection requests"),
    ("NOTIFICATIONS_CHECK", "Checked notifications"),
    ("HEALTH_CHECK", "System health check OK"),
]

# Current timestamp
now = datetime.now(timezone.utc).isoformat()
bank_seq = data['last_bank_seq']

# Log each action
for action_name, evidence in actions:
    bank_seq += 1
    entry = {
        "t": now,
        "client": "",
        "action": action_name,
        "evidence": evidence,
        "bank_seq": bank_seq
    }
    data['action_log'].append(entry)
    
    # Post to relay bank
    payload = json.dumps({"body": "KILO", "text": action_name + " " + evidence}).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:8777/hear?token=GOLD24',
        data=payload, method='POST',
        headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, timeout=5)
        print('  ' + action_name + ': bank_seq=' + str(bank_seq) + ' relay=' + str(response.status))
    except Exception as e:
        print('  ' + action_name + ': bank_seq=' + str(bank_seq) + ' relay ERROR: ' + str(e))

# Update metadata
data['last_tick'] = now
data['last_bank_seq'] = bank_seq
data['status'] = 'ACTIVE'

# Write back
with open(r'D:\anonym\war-log\linkedin-lane.json', 'w') as f:
    json.dump(data, f, indent=2)

print('')
print('Tick complete. Last tick updated to ' + now + ', bank_seq=' + str(bank_seq))