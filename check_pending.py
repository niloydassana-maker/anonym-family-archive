import json
with open(r'D:\anonym\war-log\order-bank.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
pending = [x for x in data if x.get('status') == 'pending']
print(f'Total orders: {len(data)}')
print(f'Pending orders: {len(pending)}')
for p in pending[:20]:
    body = str(p.get('body', ''))[:80]
    print(f"  {p.get('id')} | {p.get('type')} | {body}")