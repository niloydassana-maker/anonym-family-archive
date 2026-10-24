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
    "User-Agent": "AlgoraCryptoHunter/1.0"
}

# Algora exact markers: 'bounty •' or 'bounty funded' or label '💎 Bounty'
queries = [
    'label:"💎 Bounty" is:issue is:open solana',
    'label:"💎 Bounty" is:issue is:open crypto',
    'label:"💎 Bounty" is:issue is:open "smart contract"',
    'label:"💎 Bounty" is:issue is:open web3',
    'label:"💎 Bounty" is:issue is:open rust',
    'label:"💎 Bounty" is:issue is:open python'
]

print("Searching Algora-funded bounties on GitHub...\n", flush=True)

seen = set()
results = []

for q in queries:
    print(f"Query: {q}", flush=True)
    try:
        r = requests.get(
            "https://api.github.com/search/issues",
            headers=headers,
            params={"q": q, "sort": "updated", "order": "desc", "per_page": 15},
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
        url = it.get("html_url")
        if url in seen:
            continue
        seen.add(url)
        repo = it.get("repository_url", "").split("repos/")[-1]
        labels = [l.get("name", "") for l in it.get("labels", [])]
        results.append({
            "repo": repo,
            "title": it.get("title"),
            "url": url,
            "labels": labels,
            "comments": it.get("comments"),
            "updated": it.get("updated_at")[:10],
            "body": (it.get("body") or "")[:300].replace("\n", " ")
        })
    time.sleep(6)

print(f"\n=======================================================", flush=True)
print(f"TOTAL UNIQUE ALGORA BOUNTIES FOUND: {len(results)}", flush=True)
print(f"=======================================================\n", flush=True)

for i, r in enumerate(results, 1):
    print(f"[{i:2d}] {r['repo']} (updated: {r['updated']}, cmts: {r['comments']})", flush=True)
    print(f"     Title: {r['title']}", flush=True)
    print(f"     URL: {r['url']}", flush=True)
    print(f"     Labels: {', '.join(r['labels'])}", flush=True)
    print(f"     Snippet: {r['body'][:160]}...\n", flush=True)
