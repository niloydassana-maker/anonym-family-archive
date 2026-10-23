import json
from pathlib import Path
from collections import Counter

run_dir = Path(r"D:\anonym\deliverables\master_20261023T141238867952Z")
direct = json.loads((run_dir / "DIRECT_CONTACT_LEADS.json").read_text(encoding="utf-8"))
platform = json.loads((run_dir / "PLATFORM_APPLICATION_LEADS.json").read_text(encoding="utf-8"))
all_leads = json.loads((run_dir / "MASTER_500_LEADS.json").read_text(encoding="utf-8"))

print(f"Total Retained Leads: {len(all_leads)}")
print(f"Direct Contact Leads: {len(direct)}")
print(f"Platform Application Leads: {len(platform)}")

platforms = Counter(l.get("platform") for l in all_leads)
print("Platform Breakdown:", dict(platforms))

print("\n--- DIRECT CONTACT LEADS ---")
for i, l in enumerate(direct, 1):
    c = []
    if l.get("email"): c.append("Email: " + ", ".join(l["email"]))
    if l.get("linkedin"): c.append("LinkedIn: " + ", ".join(l["linkedin"]))
    if l.get("phone"): c.append("Phone: " + ", ".join(l["phone"]))
    print(f"{i}. {l.get('buyer_company') or l.get('buyer_real_name') or 'N/A'}")
    print(f"   Title: {l.get('title')}")
    print(f"   Platform: {l.get('platform')} | Location: {l.get('buyer_location')}")
    print(f"   Published: {l.get('created_at')}")
    print(f"   Contacts: {' | '.join(c)}")
    print(f"   URL: {l.get('source_url')}")
    print()

print("--- PLATFORM APPLICATION LEADS (SAMPLE BY SOURCE) ---")
by_plat = {}
for l in platform:
    p = l.get("platform")
    if p not in by_plat: by_plat[p] = []
    by_plat[p].append(l)

for p, items in by_plat.items():
    print(f"\nSource: {p} (Total: {len(items)}) - Top 3:")
    for item in items[:3]:
        budget = item.get("budget") or "N/A"
        print(f"  * {item.get('title')} | Budget: {budget} | Location: {item.get('buyer_location')} | URL: {item.get('source_url')}")
