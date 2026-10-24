import os
import sys
import time
import requests
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

tok = os.environ.get("GITHUB_TOKEN") or "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"
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {tok}",
    "User-Agent": "EscrowCryptoHunter/1.0"
}

queries = [
    'is:issue is:open "algora.io" solana',
    'is:issue is:open "algora.io" web3',
    'is:issue is:open "algora.io" crypto',
    'is:issue is:open "algora.io" "smart contract"',
    'is:issue is:open "opire.dev" crypto',
    'is:issue is:open "opire.dev" solana',
    'is:issue is:open "bounty" "USDC" is:issue is:open -org:devpool-directory',
    'is:issue is:open "will pay" "SOL" is:issue is:open',
    'is:issue is:open "bounty" "SOL" is:issue is:open -org:devpool-directory'
]

seen = set()
results = []

for q in queries:
    print(f"Searching: {q}", flush=True)
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
    print(f"  -> Found {len(items)} items (Total in GitHub: {r.json().get('total_count', 0)})", flush=True)
    for it in items:
        url = it.get("html_url")
        if url in seen:
            continue
        seen.add(url)
        repo = it.get("repository_url", "").split("repos/")[-1]
        results.append({
            "repo": repo,
            "title": it.get("title"),
            "url": url,
            "author": it.get("user", {}).get("login"),
            "comments": it.get("comments"),
            "updated": it.get("updated_at")[:10],
            "body": (it.get("body") or "")[:400].replace("\n", " ")
        })
    time.sleep(6)

print(f"\nTotal unique candidates: {len(results)}\n", flush=True)
for i, r in enumerate(results, 1):
    print(f"[{i:2d}] {r['repo']} by @{r['author']} (updated: {r['updated']}, cmts: {r['comments']})", flush=True)
    print(f"     Title: {r['title']}", flush=True)
    print(f"     URL: {r['url']}", flush=True)
    print(f"     Snippet: {r['body'][:160]}...\n", flush=True)
