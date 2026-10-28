import json, sqlite3, os

base = '../scratch/actions-discovery'

# Check receipts.jsonl
receipts_path = os.path.join(base, 'receipts.jsonl')
if os.path.exists(receipt_path):
    print(f'=== {receipt_path} ===')
    with open(receipt_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                phase = data.get('phase', '?')
                counts = data.get('counts', {})
                print(f'  phase={phase} qualified_fresh={data.get("qualified_fresh")} qualified_unique={data.get("qualified_unique")} dispatched={data.get("dispatched")}')
                print(f'    counts={counts}')
            except:
                pass
        print()

# Check discovery.sqlite3 for queue
db_path = os.path.join(base, 'discovery.sqlite3')
if os.path.exists(db_path):
    con = sqlite3.connect(db_path)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f'Tables in discovery.sqlite3: {tables}')
    con.close()
