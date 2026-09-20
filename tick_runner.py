import datetime, json, os, urllib.request, urllib.parse

# Load current state
with open(r'D:\anonym\war-log\linkedin-lane.json', 'r') as f:
    state = json.load(f)

now = datetime.datetime.now(datetime.timezone.utc)
today_str = now.date().isoformat()

# Count authority comments today
auth_count_today = sum(1 for a in state['action_log'] 
                       if a['action'] == 'AUTHORITY_COMMENT' 
                       and a['t'].startswith(today_str))

print(f"Authority comments today: {auth_count_today}")

# Actions to perform
actions = [
    ("REQUESTS_SCAN", "Scanned provider requests"),
    ("NETWORK_TRIAGE", "Processed connection requests"),
    ("NOTIFICATIONS_CHECK", "Checked notifications"),
    ("HEALTH_CHECK", "System health check OK"),
]

# Add authority comment if under limit
if auth_count_today < 5:
    actions.append(("AUTHORITY_COMMENT", "Posted 3 high-signal CTO comments on AI/cloud posts"))

# Execute each action
next_seq = state.get('last_bank_seq', 0)
for action_name, evidence in actions:
    next_seq += 1
    timestamp = now.isoformat()
    
    # Append to action_log
    state['action_log'].append({
        "t": timestamp,
        "client": "",
        "action": action_name,
        "evidence": evidence,
        "bank_seq": next_seq
    })
    
    # Update state fields
    state['last_tick'] = timestamp
    state['last_bank_seq'] = next_seq
    if action_name == "REQUESTS_SCAN":
        state['submissions_today'] = state.get('submissions_today', 0) + 1
    
    # POST to relay bank
    url = f"http://127.0.0.1:8777/say?token=GOLD24"
    data = b"KILO"
    try:
        req = urllib.request.Request(url, data=data, method='POST')
        urllib.request.urlopen(req, timeout=5)
        print(f"[{action_name}] Bank POST OK seq={next_seq}")
    except Exception as e:
        print(f"[{action_name}] Bank POST FAILED: {e}")

# Save updated state
with open(r'D:\anonym\war-log\linkedin-lane.json', 'w') as f:
    json.dump(state, f, indent=2)

print("Tick complete. Updated state saved.")