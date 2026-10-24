import requests
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://api.opire.dev/rewards"
try:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
except Exception as e:
    print(f"Opire API error: {e}")
    sys.exit(1)

items = data if isinstance(data, list) else data.get("rewards") or data.get("data") or []
print(f"Total Opire rewards fetched: {len(items)}\n", flush=True)

unclaimed = []
for it in items:
    # Skip if claimed
    if it.get("claimerUsers"):
        continue

    # Amount extraction
    val = 0
    if "pendingPrice" in it and isinstance(it["pendingPrice"], dict):
        val = it["pendingPrice"].get("value", 0) / 100.0
    elif "amount" in it and isinstance(it["amount"], dict):
        val = it["amount"].get("value", 0) / 100.0
    elif "price" in it and isinstance(it["price"], dict):
        val = it["price"].get("value", 0) / 100.0
    elif isinstance(it.get("amount"), (int, float)):
        val = it["amount"]

    issue_url = it.get("url") or (it.get("issue") or {}).get("url") or ""
    title = it.get("title") or (it.get("issue") or {}).get("title") or ""
    org = (it.get("organization") or {}).get("name") or ""
    proj = (it.get("project") or {}).get("name") or ""
    langs = it.get("programmingLanguages") or []

    unclaimed.append({
        "amount": val,
        "title": title,
        "url": issue_url,
        "repo": f"{org}/{proj}" if org and proj else "",
        "langs": langs
    })

unclaimed.sort(key=lambda x: x["amount"], reverse=True)

print(f"Unclaimed rewards ({len(unclaimed)} total):\n", flush=True)
for i, u in enumerate(unclaimed[:35], 1):
    print(f"[{i:2d}] ${u['amount']:>6.1f} | {u['repo']:<30} | {u['title'][:70]}", flush=True)
    print(f"     URL: {u['url']}", flush=True)
    if u['langs']:
        print(f"     Langs: {', '.join(u['langs'])}", flush=True)
    print("", flush=True)
