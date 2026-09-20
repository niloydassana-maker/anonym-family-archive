import json
data = json.load(open(r'D:\anonym\war-log\earn-lanes.json', 'r', encoding='utf-8'))
print('last_tick:', data['last_tick'])
print('actions_count:', len(data['action_log']))
for a in data['action_log'][-6:]:
    print(f'  [{a["lane"]}] {a["action"][:120]}...')