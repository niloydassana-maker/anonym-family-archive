import json, time, sys

print("Watching order bank...", flush=True)
last_len = 0
for _ in range(15):
    try:
        with open(r'd:\anonym\war-log\order-bank.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        if last_len == 0:
            last_len = max(0, len(data) - 10)
        if len(data) > last_len:
            for row in data[last_len:]:
                txt = row.get('text', '')
                print(f"{row.get('at')}: {txt[:120]}", flush=True)
            last_len = len(data)
    except Exception as e:
        print("err", e, flush=True)
    time.sleep(3)
