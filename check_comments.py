import json
with open(r'D:\anonym\war-log\linkedin-lane.json') as f:
    data = json.load(f)

today = '2026-09-19'
count = 0
for entry in data['action_log']:
    if entry['action'] == 'authority_comment_attempt' and entry['t'].startswith(today):
        count += 1
        print(f"  {entry['t']} - {entry['evidence']}")
print(f'Total authority comments today: {count}')