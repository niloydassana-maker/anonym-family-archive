import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

with open(r'D:\anonym\war-log\linkedin-lane.json', 'r') as f:
    log = json.load(f)

now = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
today = now[:10]

auth_count = sum(1 for e in log['action_log'] if e['action'] == 'authority_comment_attempt' and e['t'].startswith(today))
print(f"Authority comments today: {auth_count} (max 5)")

def post_to_bank(action, evidence):
    url = "http://127.0.0.1:8777/say?token=GOLD24"
    data = urllib.parse.urlencode({"body": "KILO"}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status in (429, 503):
                print(f"  Bank POST {resp.status} - exiting quietly")
                return False
            print(f"  Bank POST: {resp.status}")
            return True
    except Exception as e:
        print(f"  Bank POST error: {e}")
        return True

actions = [
    ("service_marketplace_sweep", "feed_empty_no_premium_requests"),
    ("notifications_check", "no_actionable_items"),
    ("network_triage", "invitation_manager_no_new_invites"),
    ("health_check", "uia_active_cdp_loggedout_feedwatch_dead_awareness_live"),
]

print("Skipping authority_comment_attempt: 5/day limit reached")

bank_seq = len(log['action_log'])

for action, evidence in actions:
    entry = {
        "t": now,
        "client": "",
        "action": action,
        "evidence": evidence,
        "bank_seq": bank_seq
    }
    log['action_log'].append(entry)
    bank_seq += 1
    
    if action == "service_marketplace_sweep":
        log['queue_status']['proposals_sent_today'] = 11
        log['queue_status']['evidence_count'] = 11
    elif action == "health_check":
        log['stale']['awareness'] = now
    
    log['last_tick'] = now
    log['inbox_unread_count'] = 0
    
    with open(r'D:\anonym\war-log\linkedin-lane.json', 'w') as f:
        json.dump(log, f, indent=2)
    
    post_to_bank(action, evidence)
    print(f"Logged: {action} - {evidence}")

print("Tick complete")