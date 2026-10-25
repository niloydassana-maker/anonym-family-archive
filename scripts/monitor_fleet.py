import os
import sys
import time
import json
import urllib.request
from datetime import datetime

# Enforce UTF-8 line buffering on Windows console
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DOOR = "https://omniroute-relay.omniroute-fleet-kd.workers.dev"
TOKEN = "GOLD24"

def fetch_ledger(body, limit=10):
    try:
        url = f"{DOOR}/say?body={body}&token={TOKEN}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("orders", [])
    except Exception as e:
        return [{"text": f"Error: {e}"}]

def render_dashboard():
    os.system("cls" if os.name == "nt" else "clear")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    print("=" * 80)
    print(f"⚡ 5-ENGINE KAGGLE FLEET LIVE LOG STREAM  |  {now_str}")
    print(f"Permanent Door: {DOOR}")
    print("=" * 80)

    # 1. Engine Registrations
    regs = fetch_ledger("ENGINE_REGISTRATION", limit=5)
    print("\n[1] ACTIVE KAGGLE ENGINES:")
    if regs:
        for r in regs:
            print(f"  🟢 {r.get('text', '')}")
    else:
        print("  (Awaiting engine handshakes...)")

    # 2. Task Claims
    claims = fetch_ledger("BOUNTY_CLAIM", limit=8)
    print("\n[2] LIVE TASK CLAIMS:")
    if claims:
        for c in claims[-6:]:
            print(f"  ⚡ {c.get('text', '')}")
    else:
        print("  (No active claims)")

    # 3. Execution Results
    results = fetch_ledger("BOUNTY_RESULT", limit=8)
    print("\n[3] ENGINE VERDICTS & PRs:")
    if results:
        for res in results[-6:]:
            txt = res.get("text", "")
            icon = "✅" if "SUCCESS" in txt or "PR_OPENED" in txt else "❌"
            print(f"  {icon} {txt}")
    else:
        print("  (No execution verdicts yet)")

    # 4. Pending Queue
    tasks = fetch_ledger("BOUNTY_TASK", limit=8)
    print(f"\n[4] UNCONTESTED QUEUE ({len(tasks)} in buffer):")
    if tasks:
        for t in tasks[-5:]:
            try:
                td = json.loads(t.get("text", "{}"))
                print(f"  📦 [{td.get('task_id', '')[:25]}] {td.get('repo')}#{td.get('issue_number')} - {td.get('title', '')[:45]}")
            except Exception:
                print(f"  📦 {t.get('text', '')[:70]}")
    else:
        print("  (Queue empty - dispatcher scanning...)")

    print("\n" + "=" * 80)
    print("Press Ctrl+C to exit log stream | Streaming update every 3s...")

def main():
    while True:
        try:
            render_dashboard()
            time.sleep(3)
        except KeyboardInterrupt:
            print("\nLog stream stopped.")
            break
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    main()
