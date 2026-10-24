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
    "User-Agent": "UnattendedCryptoHunter/1.0"
}

# Queries targeting UNATTENDED, HIGHLY COMPLEX crypto problems
QUERIES = [
    'is:issue is:open comments:<=1 no:assignee -linked:pr "will pay" solana',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "willing to pay" solana',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "bounty" solana "rpc"',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "bounty" "jito"',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "will pay" "smart contract"',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "bounty" "anchor"',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "bounty" "mev"',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "will pay" "trading bot"',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "will pay" "solidity"',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "bounty" "race condition" crypto',
    'is:issue is:open comments:<=1 no:assignee -linked:pr "bounty" "memory leak" crypto',
]

FARM_REPOS = re.compile(
    r"bounty-plaza|devpool|airdrop|earn-ops|superteam|quest|radar|bounty-bot|awesome-|microcredit|dharma_swarm|test-repo",
    re.I
)

print("Starting hunt for UNATTENDED, HARD CRYPTO PROBLEMS (comments <= 1, no PRs)...", flush=True)

seen = set()
hard_problems = []

for q in QUERIES:
    print(f"\nSearching: {q}", flush=True)
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
    print(f"  -> Found {len(items)} items", flush=True)

    for it in items:
        url = it.get("html_url")
        if url in seen:
            continue
        seen.add(url)

        repo = it.get("repository_url", "").split("repos/")[-1]
        if FARM_REPOS.search(repo):
            continue

        user = (it.get("user") or {}).get("login", "")
        if "[bot]" in user:
            continue

        title = it.get("title", "")
        body = it.get("body") or ""
        comments = it.get("comments", 0)
        updated = it.get("updated_at")[:10]

        hard_problems.append({
            "repo": repo,
            "title": title,
            "url": url,
            "author": user,
            "comments": comments,
            "updated": updated,
            "body": body[:500].replace("\n", " ")
        })

    time.sleep(6)  # Paced to prevent secondary rate limits

print(f"\n=======================================================", flush=True)
print(f"FOUND {len(hard_problems)} UNATTENDED CRYPTO HARD PROBLEMS", flush=True)
print(f"=======================================================\n", flush=True)

for i, p in enumerate(hard_problems, 1):
    print(f"[{i:2d}] {p['repo']} by @{p['author']} (updated: {p['updated']}, cmts: {p['comments']})", flush=True)
    print(f"     Title: {p['title']}", flush=True)
    print(f"     URL: {p['url']}", flush=True)
    print(f"     Snippet: {p['body'][:200]}...\n", flush=True)
