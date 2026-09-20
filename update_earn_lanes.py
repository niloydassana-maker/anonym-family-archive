import json
from datetime import datetime, timezone, timedelta

# Read current state
with open('D:\\anonym\\war-log\\earn-lanes.json', 'r') as f:
    state = json.load(f)

# Current timestamp in IST (UTC+5:30)
ist = timezone(timedelta(hours=5, minutes=30))
now_iso = datetime.now(ist).isoformat()

# Update last_tick
state['last_tick'] = now_iso

# IndusInd countdown - T-3 (Sep 21 is 3 days from Sep 18)
indusind_date = datetime(2026, 9, 21, 15, 0, tzinfo=ist)
days_left = (indusind_date - datetime.now(ist)).days

# Add action log entries
new_actions = [
    {
        "t": now_iso,
        "lane": "L1",
        "action": "DM-13..DM-30 drafted (all 30 variants in OUT-0918), send gated by viewed-signal/Baba eye only; 0 enrollments collected",
        "evidence": "war-log/roadmap/drafts/OUT-0918/agent-school-dm-pack.txt",
        "rs_pending": "999-2999",
        "rs_collected": 0
    },
    {
        "t": now_iso,
        "lane": "L2",
        "action": "P-queue check: P-11..P-20 submitted (24 today); P-21 V.Mathan Raj AWAITING GO; nudges HELD: P-2 Nithyasri (no viewed-signal), P-3 Achal (no viewed-signal), Saikat Barman (demo law); demos live: voice + dev",
        "evidence": "war-log/roadmap/drafts/OUT-0918/submit-queue-11.csv, nudge-ready.txt",
        "rs_pending": "25000-15000",
        "rs_collected": 0
    },
    {
        "t": now_iso,
        "lane": "L3",
        "action": "NVite watch: no-new-data skip law active (chat-screening, mobile/country-code, resume-upload-break, Akamai, Cloudflare = SKIP); target 3-5 applies/day; applies today: 5",
        "evidence": "war-log/evidence/L4/ nvite screenshots",
        "rs_pending": "interview call",
        "rs_collected": 0
    },
    {
        "t": now_iso,
        "lane": "L4",
        "action": "Premium board expiry watch: cancel decision Sep 27 (T-9), window ends ~mid-Oct; InMail 45 credits (8+ sends, 0 spent); Who-viewed 21 recruiters + 1 business (90d); Service Marketplace 10/10 submits ACTIVE; Talent Insights 404 RETRY-VIA-MENU; Campaign Manager PARKED; Learning ACTIVE; Rs 8k line frozen until L1 Rs >= 1999",
        "evidence": "todos.json id 49, war-log/earn-lanes.json",
        "rs_pending": "0",
        "rs_collected": 0
    },
    {
        "t": now_iso,
        "lane": "INDUSIND",
        "action": f"Conciliation T-3 countdown: Sep 21 3-4PM MS Teams from home, Rs 4,94,899, paper READY, NEVER-DEFER",
        "evidence": "war-log/earn-lanes.json indusind.paper=READY",
        "rs_pending": "494899",
        "rs_collected": 0
    }
]

state['action_log'].extend(new_actions)

# Update stale watchers if needed (they're already marked DEAD in last tick)
# No changes needed

# Write back
with open('D:\\anonym\\war-log\\earn-lanes.json', 'w') as f:
    json.dump(state, f, indent=2)

print("TICK_COMPLETE")
print(f"last_tick updated to: {now_iso}")
print(f"IndusInd T-{days_left} days")