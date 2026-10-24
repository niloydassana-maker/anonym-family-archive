import os
import sys
import time
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

tok = os.environ.get("GITHUB_TOKEN") or "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"
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {tok}",
    "User-Agent": "DeepCryptoHunter/1.0"
}

# Queries targeting real developers stuck on difficult crypto issues
queries = [
    'is:issue is:open "solana" "transaction failed" "will pay"',
    'is:issue is:open "solana" "rpc" "will pay"',
    'is:issue is:open "solana" "bounty" "simulation failed"',
    'is:issue is:open "anchor" "error" "bounty"',
    'is:issue is:open "jito" "bundle" "bounty"',
    'is:issue is:open "smart contract" "revert" "will pay"',
    'is:issue is:open "solidity" "bug" "bounty" comments:0..2',
    'is:issue is:open "dex" "swap" "will pay" crypto'
]

print("Executing Deep Crypto Hunter for real developers stuck on hard problems...\n", flush=True)

found = []
for q in queries:
    print(f"Query: {q}", flush=True)
    try:
        r = requests.get(
            "https://api.github.com/search/issues",
            headers=headers,
            params={"q": q, "sort": "updated", "order": "desc", "per_page": 10},
            timeout=15
        )
    except Exception as e:
        print(f"  [error] {e}", flush=True)
        time.sleep(6)
        continue

    if r.status_code != 200:
        print(f"  [status {r.status_code}] {r.text[:100]}", flush=True)
        time.sleep(6)
        continue

    items = r.json().get("items", [])
    print(f"  -> Found {len(items)} items (Total: {r.json().get('total_count', 0)})", flush=True)
    for it in items:
        repo = it.get("repository_url", "").split("repos/")[-1]
        owner = repo.split("/")[0]
        # Ignore known spam orgs
        if owner.lower() in ("devpool-directory", "superteam", "gitcoinco", "clankernation"):
            continue
        found.append({
            "repo": repo,
            "title": it.get("title"),
            "url": it.get("html_url"),
            "author": it.get("user", {}).get("login"),
            "comments": it.get("comments"),
            "updated": it.get("updated_at")[:10],
            "body": (it.get("body") or "")[:350].replace("\n", " ")
        })
    time.sleep(6)

print(f"\n=======================================================", flush=True)
print(f"FOUND {len(found)} TARGET ISSUES", flush=True)
print(f"=======================================================\n", flush=True)

for i, f in enumerate(found, 1):
    print(f"[{i:2d}] {f['repo']} by @{f['author']} (cmts: {f['comments']}, upd: {f['updated']})", flush=True)
    print(f"     Title: {f['title']}", flush=True)
    print(f"     URL: {f['url']}", flush=True)
    print(f"     Snippet: {f['body'][:180]}...\n", flush=True)
