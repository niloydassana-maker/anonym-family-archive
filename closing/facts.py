import csv
import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(r"D:\anonym")
FACTS_PATH = BASE / "closing" / "facts.json"

def compute_facts():
    facts = {}
    now = datetime.now().isoformat()

    # 1. Deals in deals.csv
    deals_file = BASE / "closing" / "deals.csv"
    deals = []
    if deals_file.exists():
        with open(deals_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            deals = list(reader)
    facts["deals_total"] = len(deals)
    facts["deals_advance_due"] = len([d for d in deals if d.get("stage") == "ADVANCE_DUE"])
    facts["total_advance_due_inr"] = sum(int(d.get("advance", 0)) for d in deals if d.get("stage") == "ADVANCE_DUE")
    facts["deals_list"] = [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "stage": d.get("stage"),
            "advance": d.get("advance"),
            "total": d.get("amount"),
            "last_touch_at": d.get("last_touch_at")
        }
        for d in deals
    ]

    # 2. Distinct proposal IDs in PROPOSALS.md
    proposals_file = BASE / "war-log" / "roadmap" / "PROPOSALS.md"
    distinct_proposals = set()
    if proposals_file.exists():
        content = proposals_file.read_text(encoding="utf-8")
        matches = re.findall(r"P-\d+", content)
        distinct_proposals = set(matches)
    facts["proposals_distinct_ids_count"] = len(distinct_proposals)
    facts["proposals_distinct_ids_sample_max"] = max(distinct_proposals, key=lambda x: int(x.split("-")[1])) if distinct_proposals else None

    # 3. SMTP sends count
    smtp_file = BASE / "war-log" / "hunt" / "smtp-sends.csv"
    if smtp_file.exists():
        with open(smtp_file, encoding="utf-8", newline="") as f:
            reader = list(csv.reader(f))
            hdr = reader[0] if reader else []
            data = reader[1:] if len(reader) > 1 else []
            facts["smtp_sends_total"] = len(data)
            facts["smtp_sends_cols_match"] = all(len(r) == len(hdr) for r in data)
    else:
        facts["smtp_sends_total"] = 0

    facts["generated_at"] = now
    return facts

if __name__ == "__main__":
    data = compute_facts()
    with open(FACTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"FACTS EMITTED: {FACTS_PATH}")
    print(json.dumps(data, indent=2))
