import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\Admin\.gemini\antigravity-ide\brain\019e58aa-215d-4bdd-a4a8-46043bbdc91c\.system_generated\logs\transcript_full.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        idx = obj.get('step_index')
        if idx == 2412:
            print("=== STEP 2412 CONTENT ===")
            print(obj.get('content'))
            print("=== END ===")
            break
