import json
data = json.load(open('D:/anonym/war-log/order-bank.json', 'r', encoding='utf-8'))
brain_msgs = [d for d in data if d.get('to') == 'KILO' and ('HEARTBEAT' in d.get('text', '') or 'heartbeat' in d.get('text', '').lower() or 'BRAIN_CELL' in d.get('text', '') or 'brain' in d.get('text', '').lower()) and 'AWARENESS' not in d.get('text', '')]
print(f'Brain heartbeats: {len(brain_msgs)}')
for d in brain_msgs[-10:]:
    print(f'{d["at"]}: {d["text"][:100]}')