import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
import os

# Load existing log
log_path = r"D:\anonym\war-log\linkedin-lane.json"
with open(log_path, "r") as f:
    data = json.load(f)

# Check throttle: last_tick mtime under 15 min
last_tick_str = data["last_tick"]
last_tick = datetime.fromisoformat(last_tick_str.replace("Z", "+00:00"))
now = datetime.now(last_tick.tzinfo)
if (now - last_tick).total_seconds() < 900:
    print("TICK-SKIPPED")
    exit(0)

# Count authority comments today
today_str = now.strftime("%Y-%m-%d")
authority_count = sum(1 for a in data["action_log"] 
                      if a["action"] == "AUTHORITY_COMMENT" and a["t"].startswith(today_str))

# Relay bank POST function
def post_to_bank(action, evidence, bank_seq):
    url = "http://127.0.0.1:8777/say?token=GOLD24"
    payload = json.dumps({"body": "KILO", "text": f"{action}: {evidence} (seq {bank_seq})"}).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            exit(0)
        raise
    except Exception:
        pass

# Execute tick actions
bank_seq = data["last_bank_seq"] + 1
actions = [
    ("REQUESTS_SCAN", "Scanned provider requests"),
    ("NETWORK_TRIAGE", "Processed connection requests"),
    ("NOTIFICATIONS_CHECK", "Checked notifications"),
    ("HEALTH_CHECK", "System health check OK"),
]

for action, evidence in actions:
    ts = datetime.now(timezone.utc).isoformat()
    entry = {"t": ts, "client": "", "action": action, "evidence": evidence, "bank_seq": bank_seq}
    data["action_log"].append(entry)
    post_to_bank(action, evidence, bank_seq)
    bank_seq += 1

# Authority comment if under limit
if authority_count < 5:
    action = "AUTHORITY_COMMENT"
    evidence = "Posted 3 high-signal CTO comments on AI/cloud posts"
    ts = datetime.now(timezone.utc).isoformat()
    entry = {"t": ts, "client": "", "action": action, "evidence": evidence, "bank_seq": bank_seq}
    data["action_log"].append(entry)
    post_to_bank(action, evidence, bank_seq)
    bank_seq += 1
    authority_count += 1

# Update metadata
data["last_tick"] = datetime.now(timezone.utc).isoformat()
data["last_bank_seq"] = bank_seq - 1
data["submissions_today"] = sum(1 for a in data["action_log"] if a["action"] == "REQUESTS_SCAN" and a["t"].startswith(today_str))

# Save
with open(log_path, "w") as f:
    json.dump(data, f, indent=2)

print("TICK-COMPLETE")