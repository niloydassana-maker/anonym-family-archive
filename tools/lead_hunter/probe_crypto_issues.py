import os
import sys
import subprocess
import requests
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

tok = subprocess.check_output(["gh", "auth", "token"]).decode().strip()
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {tok}",
    "User-Agent": "CryptoProblemHunter/1.0"
}

queries = [
    'is:issue is:open "will pay" solana',
    'is:issue is:open "will pay" smart contract',
    'is:issue is:open "will pay" ethereum',
    'is:issue is:open "bounty" solana no:assignee',
    'is:issue is:open "bounty" "smart contract" no:assignee',
    'is:issue is:open "paying" solana',
    'is:issue is:open "paying" "smart contract"'
]

for q in queries:
    r = requests.get(
        "https://api.github.com/search/issues",
        headers=headers,
        params={"q": q, "sort": "updated", "order": "desc", "per_page": 5},
        timeout=15
    )
    if r.status_code != 200:
        print(f"[{r.status_code}] query: {q} -> {r.text[:120]}")
        continue
    items = r.json().get("items", [])
    print(f"\n=== Query: {q} (Found {r.json().get('total_count', 0)} total, showing {len(items)}) ===")
    for it in items:
        title = it.get("title", "")
        url = it.get("html_url", "")
        comments = it.get("comments", 0)
        repo = it.get("repository_url", "").split("repos/")[-1]
        user = (it.get("user") or {}).get("login", "")
        updated = it.get("updated_at", "")[:10]
        print(f"  * [{updated}] ({repo}) by @{user} (cmts: {comments}): {title}")
        print(f"    {url}")
