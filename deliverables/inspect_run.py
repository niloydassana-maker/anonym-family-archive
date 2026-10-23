import json
from pathlib import Path

run_dir = Path(r"D:\anonym\deliverables\master_20261023T140242031990Z")

print("=== DIRECT CONTACT LEADS ===")
direct = json.loads((run_dir / "DIRECT_CONTACT_LEADS.json").read_text(encoding="utf-8"))
print(f"Total direct: {len(direct)}")
for i, x in enumerate(direct, 1):
    contacts = []
    if x.get("email"): contacts.append(f"email: {x['email']}")
    if x.get("linkedin"): contacts.append(f"linkedin: {x['linkedin']}")
    if x.get("phone"): contacts.append(f"phone: {x['phone']}")
    if x.get("whatsapp_number"): contacts.append(f"whatsapp: {x['whatsapp_number']}")
    print(f"#{i} [{x.get('platform')}] {x.get('buyer_company') or x.get('buyer_real_name') or 'N/A'}")
    print(f"    Title: {x.get('title')}")
    print(f"    Location: {x.get('buyer_location')}")
    print(f"    Created: {x.get('created_at')}")
    print(f"    Contacts: {', '.join(contacts)}")
    print(f"    URL: {x.get('source_url')}")
    print()

print("=== PLATFORM APPLICATION LEADS (SAMPLE FIRST 15) ===")
platform = json.loads((run_dir / "PLATFORM_APPLICATION_LEADS.json").read_text(encoding="utf-8"))
print(f"Total platform: {len(platform)}")
for i, x in enumerate(platform[:15], 1):
    print(f"#{i} [{x.get('platform')}] {x.get('buyer_company') or x.get('buyer_real_name') or 'N/A'}")
    print(f"    Title: {x.get('title')}")
    print(f"    Budget: {x.get('budget')}")
    print(f"    Location: {x.get('buyer_location')}")
    print(f"    Created: {x.get('created_at')}")
    print(f"    URL: {x.get('source_url')}")
    print()
