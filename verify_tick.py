import json
with open(r'D:\anonym\war-log\linkedin-lane.json') as f:
    data = json.load(f)
print(f'last_tick: {data["last_tick"]}')
print(f'Total entries: {len(data["action_log"])}')
for e in data['action_log'][-4:]:
    print(f'  {e["t"]} - {e["action"]} - {e["evidence"]} - seq={e["bank_seq"]}')